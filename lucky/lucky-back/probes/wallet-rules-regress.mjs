// Wallet account rules and the bonus wallet, on a regress stand: node wallet-rules-regress.mjs dev|prod|local.
// Reads ~/.config/lucky-regress/<env>.env; accounts come from the project admin API, no database access.
// Moves only the regress player's money: a manual top-up, bets and wins through the regress provider.
import { createHmac, randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const envName = process.argv[2];
const cfg = Object.fromEntries(readFileSync(join(homedir(), ".config", "lucky-regress", `${envName}.env`), "utf8")
  .split("\n").filter(Boolean).map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]));
let passed = 0, failed = 0;
const check = (label, ok, note = "") => { ok ? passed++ : failed++; console.log(`${ok ? "PASS" : "FAIL"} ${label}${note ? `  // ${note}` : ""}`); };
async function call(method, path, { token, publicKey, body, headers = {} } = {}) {
  const h = { ...headers };
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  if (publicKey) h["X-Public-Key"] = publicKey;
  const res = await fetch(cfg.LUCKY_API + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => null) };
}
const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
const provider = (route, body) => {
  const path = `/v1/external/game-provider/${route}`;
  const sign = createHmac("sha256", cfg.PROVIDER_PRIVATE_KEY).update(["POST", path, canonical({}), canonical(body)].join("\n")).digest("hex");
  return call("POST", path, { body, headers: { "x-api-key": cfg.PROVIDER_PUBLIC_KEY, "x-sign": sign } });
};

console.log(`== ${envName}: wallet account rules and the bonus wallet`);
const player = (await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body?.access_token;
const admin = (await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body?.access_token;
check("player and project admin login", Boolean(player && admin));
const accounts = async () => {
  const r = await call("GET", `/v1/project/balances/users/${cfg.PLAYER_ID}`, { token: admin });
  const out = {};
  for (const balance of r.body?.balances ?? []) {
    if (balance.currency !== "USD" || !["cash", "cash_bonus"].includes(balance.balance_code)) continue;
    for (const account of balance.accounts ?? []) out[`${balance.balance_code}.${account.type}`] = Number(account.amount);
  }
  return out;
};
const delta = (before, after) => Object.fromEntries(Object.keys(after).map(key => [key, +(after[key] - (before[key] ?? 0)).toFixed(2)]).filter(([, value]) => value !== 0));
const select = (code) => call("POST", "/v1/core/balances/select", { token: player, publicKey: cfg.PUBLIC_KEY, body: { balance_code: code } });
const session = async () => (await call("POST", `/v1/core/providers/${cfg.PROVIDER_PID}/games/${cfg.GAME_PID}/sessions`, { token: player, publicKey: cfg.PUBLIC_KEY })).body?.session;
const credit = (code, amount) => call("POST", `/v1/project/finance/users/${cfg.PLAYER_ID}/transactions`, { token: admin, body: { direction: "credit", amount, currency: "USD", balance_code: code, comment: "wallet rules regress" } });
const stamp = Date.now();

await select("cash");
let before = await accounts();
check("the regress player has a cash_bonus wallet with accounts", "cash_bonus.pending" in before && "cash_bonus.available" in before, Object.keys(before).join(","));
let r = await credit("cash", "20.00");
let d = delta(before, await accounts());
check("manual credit 20 lands in cash pending", r.status === 201 && d["cash.pending"] === 20 && Object.keys(d).length === 1, `${r.status} ${JSON.stringify(d)}`);

let s = await session();
before = await accounts();
const bet = { session: s, betId: `rules-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await provider("bet", { ...bet, txId: randomUUID(), amount: "1000" });
d = delta(before, await accounts());
check("bet 10 is taken from pending first", d["cash.pending"] === -10 && !("cash.available" in d), JSON.stringify(d));
before = await accounts();
await provider("win", { ...bet, txId: randomUUID(), amount: "1500" });
d = delta(before, await accounts());
check("win 15 lands in cash available", d["cash.available"] === 15 && Object.keys(d).length === 1, JSON.stringify(d));

before = await accounts();
const lost = { session: s, betId: `rules-lost-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await provider("bet", { ...lost, txId: randomUUID(), amount: "1000" });
await provider("win", { ...lost, txId: randomUUID(), amount: "0" });
d = delta(before, await accounts());
check("a lost bet never touches available", d["cash.pending"] === -10 && !("cash.available" in d), JSON.stringify(d));
before = await accounts();
const cancelled = { session: s, betId: `rules-cancel-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await provider("bet", { ...cancelled, txId: randomUUID(), amount: "1000" });
await provider("win", { ...cancelled, txId: randomUUID(), amount: "1000", cancel: true });
d = delta(before, await accounts());
check("bet and its cancel leave every account as it was", Object.keys(d).length === 0, JSON.stringify(d));

before = await accounts();
r = await credit("cash_bonus", "30.00");
d = delta(before, await accounts());
check("manual credit 30 to the bonus wallet lands in its pending", r.status === 201 && d["cash_bonus.pending"] === 30 && Object.keys(d).length === 1, `${r.status} ${JSON.stringify(d)}`);
r = await select("cash_bonus");
check("the bonus wallet can be made active", r.body?.active_balance_code === "cash_bonus", String(r.body?.active_balance_code));
r = await call("POST", "/v1/core/balances/deposit", { token: player, publicKey: cfg.PUBLIC_KEY, body: { amount: "10.00" } });
check("a deposit to the bonus wallet is refused", r.status === 400 || r.status === 503, `${r.status} ${r.body?.error?.message ?? ""}`);
s = await session();
before = await accounts();
const bonusBet = { session: s, betId: `rules-bonus-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await provider("bet", { ...bonusBet, txId: randomUUID(), amount: "1000" });
d = delta(before, await accounts());
check("a bet on the bonus wallet is taken from it", d["cash_bonus.pending"] === -10 && Object.keys(d).length === 1, JSON.stringify(d));
before = await accounts();
const bonusWin = randomUUID();
await provider("win", { ...bonusBet, txId: bonusWin, amount: "2500" });
d = delta(before, await accounts());
check("win 25 on a bonus bet: 10 back to bonus pending, 15 to cash available", d["cash_bonus.pending"] === 10 && d["cash.available"] === 15 && Object.keys(d).length === 2, JSON.stringify(d));
before = await accounts();
r = await provider("rollback", { session: s, txId: bonusWin });
d = delta(before, await accounts());
check("rolling that win back reverses both wallets", r.status === 201 && d["cash_bonus.pending"] === -10 && d["cash.available"] === -15, `${r.status} ${JSON.stringify(d)}`);

r = await select("cash");
check("back on the cash wallet", r.body?.active_balance_code === "cash", String(r.body?.active_balance_code));
console.log(`== ${envName}: ${passed}/${passed + failed} passed`);
process.exitCode = failed ? 1 : 0;
