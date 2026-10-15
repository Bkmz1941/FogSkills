// Project cabinet settings and finance actions, on a regress stand: node admin-regress.mjs dev|prod|local.
// Currencies tab (coefficient, offering), registration currency on General, project deposit, withdrawal review,
// payments/bets history split. Restores the stand's registration currency and offered currencies at the end.
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const envName = process.argv[2];
const cfg = Object.fromEntries(readFileSync(join(homedir(), ".config", "lucky-regress", `${envName}.env`), "utf8")
  .split("\n").filter(Boolean).map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]));
let passed = 0, failed = 0;
const check = (label, ok, note = "") => { ok ? passed++ : failed++; console.log(`${ok ? "PASS" : "FAIL"} ${label}${note ? `  // ${note}` : ""}`); };
async function call(method, path, { token, publicKey, body } = {}) {
  const h = {};
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  if (publicKey) h["X-Public-Key"] = publicKey;
  for (let attempt = 0; ; attempt++) {
    const res = await fetch(cfg.LUCKY_API + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
    if (res.status === 429 && attempt < 4) {
      await new Promise((resolve) => setTimeout(resolve, (Number(res.headers.get("retry-after")) || 15) * 1000 + 500));
      continue;
    }
    return { status: res.status, body: await res.json().catch(() => null) };
  }
}

console.log(`== ${envName}: project cabinet settings and finance`);
const player = (await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body?.access_token;
const admin = (await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body?.access_token;
check("player and project admin login", Boolean(player && admin));
if (!player || !admin) { process.exitCode = 1; process.exit(); }

const settings = async () => (await call("GET", "/v1/project/settings", { token: admin })).body?.project;
const saveSettings = (project, extra) => call("PATCH", "/v1/project/settings", { token: admin, body: {
  name: project.name, primary_domain: project.primary_domain, default_theme: project.default_theme, primary_color: project.primary_color,
  secondary_color: project.secondary_color, default_locale: project.default_locale, supported_locales: project.supported_locales,
  timezone: project.timezone, ...extra,
} });
const currencies = async () => (await call("GET", "/v1/project/currencies", { token: admin })).body?.data ?? [];
const offer = (code, isOffered) => call("PUT", `/v1/project/currencies/${code}`, { token: admin, body: { is_offered: isOffered } });
const cashAccounts = async () => {
  const r = await call("GET", `/v1/project/balances/users/${cfg.PLAYER_ID}`, { token: admin });
  const cash = (r.body?.balances ?? []).find((balance) => balance.balance_code === "cash" && balance.currency === "USD");
  return Object.fromEntries((cash?.accounts ?? []).map((account) => [account.type, Number(account.amount)]));
};

const original = await settings();
const originalCurrencies = await currencies();
check("project currencies carry Root's coefficient", originalCurrencies.length > 0 && originalCurrencies.every((item) => typeof item.coefficient === "string"), originalCurrencies.map((item) => `${item.code}:${item.coefficient}`).join(","));
const registration = original?.registration_currency;
const spare = originalCurrencies.find((item) => item.code !== registration);

if (spare && registration) {
  let r = await offer(spare.code, true);
  check(`offering ${spare.code} switches it on for players`, r.status === 200 && r.body?.is_offered === true, String(r.status));
  r = await saveSettings(original, { registration_currency: spare.code });
  check(`General moves the registration currency to ${spare.code}`, r.status === 200 && (await settings())?.registration_currency === spare.code, String(r.status));
  r = await saveSettings(original, { registration_currency: "ZZZ" });
  check("General refuses a currency the project does not offer", r.status === 400, String(r.status));
  r = await offer(spare.code, false);
  const moved = await settings();
  const firstOffered = (await currencies()).filter((item) => item.is_offered).map((item) => item.code).sort()[0];
  check("switching off the registration currency moves registration to the first offered one", r.status === 200 && moved?.registration_currency === firstOffered, `${r.status} ${moved?.registration_currency} first=${firstOffered}`);
  await saveSettings(original, { registration_currency: registration });
  for (const item of originalCurrencies) await offer(item.code, item.is_offered);
  const restored = await settings();
  const restoredOffered = (await currencies()).map((item) => `${item.code}:${item.is_offered}`).join(",");
  check("the stand's registration currency and offers are restored", restored?.registration_currency === registration && restoredOffered === originalCurrencies.map((item) => `${item.code}:${item.is_offered}`).join(","), `${restored?.registration_currency} ${restoredOffered}`);
} else console.log("SKIP registration currency  // the Regress project has a single currency");

let before = await cashAccounts();
let r = await call("POST", "/v1/project/finance/deposits", { token: admin, body: { client_id: cfg.PLAYER_ID, currency: "USD", amount: "12.00" } });
let after = await cashAccounts();
check("a project deposit lands in cash pending", r.status === 201 && r.body?.type === "deposit" && +(after.pending - before.pending).toFixed(2) === 12 && after.available === before.available, `${r.status} ${r.body?.type} ${before.pending}->${after.pending}`);
r = await call("POST", "/v1/project/finance/deposits", { token: admin, body: { client_id: cfg.PLAYER_ID, currency: "USD", amount: "-1" } });
check("a project deposit refuses a bad amount", r.status === 400, String(r.status));

await call("POST", "/v1/core/balances/select", { token: player, publicKey: cfg.PUBLIC_KEY, body: { balance_code: "cash" } });
before = await cashAccounts();
if (before.available >= 1) {
  r = await call("POST", "/v1/core/balances/withdrawal-requests", { token: player, publicKey: cfg.PUBLIC_KEY, body: { amount: "1.00", balance_code: "cash" } });
  const requestId = r.body?.id;
  after = await cashAccounts();
  check("a withdrawal request locks the amount", r.status === 201 && +(after.locked - before.locked).toFixed(2) === 1, `${r.status} locked ${before.locked}->${after.locked}`);
  const history = await call("GET", "/v1/core/balances/transactions?operations=payments&limit=10", { token: player, publicKey: cfg.PUBLIC_KEY });
  const row = (history.body?.data ?? history.body?.transactions ?? []).find((item) => item.id === requestId);
  check("Operation history shows the withdrawal with its request status", row?.type === "withdrawal" && row?.status === "pending_review", `${row?.type} ${row?.status}`);
  r = await call("POST", `/v1/project/finance/withdrawals/${requestId}/reject`, { token: admin, body: { confirmation_password: "wrong-password", reason_code: "regress" } });
  check("a review with a wrong password is refused", r.status === 403, String(r.status));
  r = await call("POST", `/v1/project/finance/withdrawals/${requestId}/reject`, { token: admin, body: { confirmation_password: cfg.ADMIN_PASSWORD, reason_code: "regress" } });
  const released = await cashAccounts();
  check("rejecting the withdrawal returns the amount to available", r.status === 201 && r.body?.status === "rejected" && released.locked === before.locked && released.available === before.available, `${r.status} ${r.body?.status}`);
} else console.log("SKIP withdrawal review  // no available cash");

r = await call("GET", "/v1/core/balances/transactions?operations=bets&limit=25", { token: player, publicKey: cfg.PUBLIC_KEY });
const betTypes = new Set((r.body?.data ?? r.body?.transactions ?? []).map((row) => row.type));
check("Bet history lists only game operations", r.status === 200 && [...betTypes].every((type) => ["bet", "win", "cancel", "rollback"].includes(type)), [...betTypes].join(","));
r = await call("GET", "/v1/core/balances/transactions?operations=payments&limit=25", { token: player, publicKey: cfg.PUBLIC_KEY });
const payTypes = new Set((r.body?.data ?? r.body?.transactions ?? []).map((row) => row.type));
check("Operation history lists only payments and manual operations", r.status === 200 && [...payTypes].every((type) => ["deposit", "withdrawal", "manual_credit", "manual_debit"].includes(type)), [...payTypes].join(","));
r = await call("GET", "/v1/core/balances/transactions?operations=everything", { token: player, publicKey: cfg.PUBLIC_KEY });
check("an unknown history filter is refused", r.status === 400, String(r.status));

console.log(`== ${envName}: ${passed}/${passed + failed} passed`);
process.exitCode = failed ? 1 : 0;
