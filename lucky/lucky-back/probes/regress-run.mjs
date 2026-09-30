// Full regression on the isolated stand made by regress-bootstrap.mjs.
// Usage: node regress-run.mjs dev|prod
// Reads ~/.config/lucky-regress/<env>.env; prints PASS/FAIL, never a secret. Exit code 1 on any failure.
import { createHmac, randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const envName = process.argv[2];
const cfg = Object.fromEntries(readFileSync(join(homedir(), ".config", "lucky-regress", `${envName}.env`), "utf8")
  .split("\n").filter(Boolean).map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]));
const API = cfg.LUCKY_API;
const results = [];
const check = (label, ok, note = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${label}${note ? `  // ${note}` : ""}`); return ok; };

async function call(method, path, { token, publicKey, body, headers = {} } = {}) {
  const h = { ...headers };
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  if (publicKey) h["X-Public-Key"] = publicKey;
  const res = await fetch(API + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => null) };
}
const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
const provider = (route, body) => {
  const path = `/v1/external/game-provider/${route}`;
  const sign = createHmac("sha256", cfg.PROVIDER_PRIVATE_KEY).update(["POST", path, canonical({}), canonical(body)].join("\n")).digest("hex");
  return call("POST", path, { body, headers: { "x-api-key": cfg.PROVIDER_PUBLIC_KEY, "x-sign": sign } });
};

console.log(`== ${envName}: internal`);
check("health", (await call("GET", "/v1/health")).body?.status === "ok");

const playerLogin = await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } });
const player = playerLogin.body?.access_token;
check("player login", Boolean(player), String(playerLogin.status));

const adminLogin = await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } });
const admin = adminLogin.body?.access_token;
check("project admin login", Boolean(admin), String(adminLogin.status));

const cabinetLogin = await call("POST", "/v1/provider/auth/login", { body: { email: cfg.CABINET_EMAIL, password: cfg.CABINET_PASSWORD } });
const cabinet = cabinetLogin.body?.access_token;
check("provider cabinet login", Boolean(cabinet), String(cabinetLogin.status));

const cash = async () => {
  const r = await call("GET", "/v1/core/balances", { token: player, publicKey: cfg.PUBLIC_KEY });
  const wallets = Array.isArray(r.body?.balances) ? r.body.balances : [];
  return Number(wallets.find(w => w.balance_code === "cash")?.available_amount ?? NaN);
};
let balance = await cash();
check("player balances", Number.isFinite(balance), `cash ${balance}`);
if (balance < 200) {
  const topUp = await call("POST", `/v1/project/finance/users/${cfg.PLAYER_ID}/transactions`, { token: admin, body: { direction: "credit", amount: "1000", currency: "USD", balance_code: "cash", comment: "regress top-up" } });
  check("top up the player", topUp.status === 201, String(topUp.status));
  balance = await cash();
}

const gameRoute = `/v1/core/providers/${cfg.PROVIDER_PID}/games/${cfg.GAME_PID}`;
const launch = await call("POST", `${gameRoute}/launch`, { token: player, publicKey: cfg.PUBLIC_KEY });
check("launch answers without a provider endpoint", launch.status === 201 && launch.body?.unavailable === true, String(launch.status));
const bootstrap = await call("GET", "/v1/cms/bootstrap?locale=en&time_zone=UTC", { publicKey: cfg.PUBLIC_KEY });
check("storefront bootstrap says demo play is on", bootstrap.body?.features?.demo_play_enabled === true, String(bootstrap.status));
const demo = await call("POST", `${gameRoute}/demo`, { publicKey: cfg.PUBLIC_KEY });
check("guest demo without a player token", demo.status === 201 && demo.body?.unavailable === true, String(demo.status));
check("guest demo refuses without a public key", (await call("POST", `${gameRoute}/demo`)).status === 401);
const home = await call("GET", "/v1/cms/page?locale=en&time_zone=UTC&path=/", { publicKey: cfg.PUBLIC_KEY });
check("regress game is not shown on the storefront", home.status === 200 && !JSON.stringify(home.body).includes("Regress Game"), String(home.status));

const sessionRes = await call("POST", `${gameRoute}/sessions`, { token: player, publicKey: cfg.PUBLIC_KEY });
const session = sessionRes.body?.session;
check("game session", Boolean(session), String(sessionRes.status));

console.log(`== ${envName}: provider callbacks`);
const info = await provider("user/info", { session });
check("user/info carries locale", info.status === 200 && info.body?.locale === "en", JSON.stringify(info.body ?? null).slice(0, 80));

const tmp = mkdtempSync(join(tmpdir(), "lucky-regress-"));
try {
  writeFileSync(join(tmp, "input"), `${cfg.PROVIDER_PUBLIC_KEY}\n${cfg.PROVIDER_PRIVATE_KEY}\n${session}\n`, { mode: 0o600 });
  const probe = join(dirname(fileURLToPath(import.meta.url)), "game-provider-regress.mjs");
  try {
    process.stdout.write(execFileSync("node", [probe, join(tmp, "input")], { env: { ...process.env, LUCKY_API: API }, encoding: "utf8" }));
    check("money regression (game-provider-regress.mjs)", true);
  } catch (error) {
    process.stdout.write(String(error.stdout ?? ""));
    check("money regression (game-provider-regress.mjs)", false);
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

console.log(`== ${envName}: commission on the player's loss`);
const rate = await call("PATCH", `/v1/provider/games/${cfg.GAME_ID}`, { token: cabinet, body: { commission_percent: "10" } });
check("provider sets the stand game commission to 10%", rate.status === 200 && rate.body?.commission_percent === "10.00", String(rate.status));
const stamp = Date.now();
const cases = [
  { name: "lost", stake: "1000", win: "0", expected: "1.00000000" },
  { name: "partial", stake: "1000", win: "400", expected: "0.60000000" },
  { name: "won", stake: "1000", win: "2500", expected: null },
  { name: "cancelled", stake: "1000", win: "1000", cancel: true, expected: null },
];
for (const c of cases) {
  const base = { session, betId: `regress-${stamp}-${c.name}`, roundId: `round-${stamp}`, betNumber: "1" };
  c.winTx = randomUUID();
  const bet = await provider("bet", { ...base, txId: randomUUID(), amount: c.stake });
  const win = await provider("win", { ...base, txId: c.winTx, amount: c.win, ...(c.cancel ? { cancel: true } : {}) });
  check(`${c.name}: bet and settle`, bet.status === 201 && win.status === 201, `${bet.status}/${win.status}`);
}
const ledger = await call("GET", "/v1/provider/wallet-transactions?limit=50", { token: cabinet });
const entries = Array.isArray(ledger.body?.data) ? ledger.body.data : [];
for (const c of cases) {
  const entry = entries.find(e => e.transaction_id === c.winTx);
  const got = entry?.amount ?? null;
  check(`${c.name}: commission ${c.expected ?? "none"}`, got === c.expected, `got ${got}${entry ? `, stake shown ${entry.operation_amount}` : ""}`);
}

const failed = results.filter(ok => !ok).length;
console.log(`== ${envName}: ${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
