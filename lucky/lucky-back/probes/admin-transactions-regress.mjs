// Admin transaction rows against the wallets they moved, on a regress stand: node admin-transactions-regress.mjs dev|prod|local.
// Every step runs a real operation, then checks the newest row of the project admin list: its wallet (balance_code),
// type, amount, and Balance before/after = that wallet's accounts summed before/after. Wallets are never added up.
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

console.log(`== ${envName}: admin transaction rows against wallet balances`);
const player = (await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body?.access_token;
const admin = (await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body?.access_token;
check("player and project admin login", Boolean(player && admin));

const wallets = async () => {
  const r = await call("GET", `/v1/project/balances/users/${cfg.PLAYER_ID}`, { token: admin });
  const out = {};
  for (const balance of r.body?.balances ?? []) {
    if (balance.currency !== "USD") continue;
    out[balance.balance_code] = +(balance.accounts ?? []).reduce((sum, account) => sum + Number(account.amount), 0).toFixed(2);
  }
  return out;
};
const rows = async (limit = 3) => {
  const r = await call("GET", `/v1/project/finance/transactions?client_id=${cfg.PLAYER_ID}&limit=${limit}`, { token: admin });
  return r.body?.data ?? r.body?.items ?? r.body?.transactions ?? [];
};
const select = (code) => call("POST", "/v1/core/balances/select", { token: player, publicKey: cfg.PUBLIC_KEY, body: { balance_code: code } });
const session = async () => (await call("POST", `/v1/core/providers/${cfg.PROVIDER_PID}/games/${cfg.GAME_PID}/sessions`, { token: player, publicKey: cfg.PUBLIC_KEY })).body?.session;
const manual = (direction, code, amount) => call("POST", `/v1/project/finance/users/${cfg.PLAYER_ID}/transactions`, { token: admin, body: { direction, amount, currency: "USD", balance_code: code, comment: "admin transactions regress" } });
const money = (value) => (value === null || value === undefined ? null : +Number(value).toFixed(2));

// Runs one operation and checks the newest admin row against the wallet it names.
async function step(label, expect, run) {
  const before = await wallets();
  const result = await run();
  const after = await wallets();
  const [row] = await rows(1);
  const code = row?.balance_code;
  const problems = [];
  if (!row) problems.push("no row");
  else {
    if (expect.type && row.type !== expect.type) problems.push(`type ${row.type} != ${expect.type}`);
    if (expect.wallet && code !== expect.wallet) problems.push(`wallet ${code} != ${expect.wallet}`);
    if (expect.amount !== undefined && money(row.amount) !== expect.amount) problems.push(`amount ${row.amount} != ${expect.amount}`);
    if (money(row.balance_before) !== before[code]) problems.push(`before ${row.balance_before} != wallet ${code} ${before[code]}`);
    if (money(row.balance_after) !== after[code]) problems.push(`after ${row.balance_after} != wallet ${code} ${after[code]}`);
    const entries = (row.entries ?? []).filter((entry) => entry.balance_code === code && (row.type !== "win" || Number(entry.amount) >= 0));
    const moved = +entries.reduce((sum, entry) => sum + Number(entry.amount), 0).toFixed(2);
    if (!entries.length) problems.push("no account entries in the details");
    else if (moved !== +(after[code] - before[code]).toFixed(2)) problems.push(`entries move ${moved} != ${+(after[code] - before[code]).toFixed(2)}`);
    for (const other of Object.keys(after)) if (other !== code && !(expect.touches ?? []).includes(other) && before[other] !== after[other]) problems.push(`wallet ${other} moved ${before[other]} -> ${after[other]}`);
  }
  check(label, problems.length === 0, problems.length ? problems.join("; ") : `${code} ${row.balance_before} -> ${row.balance_after} (${row.type} ${row.amount})`);
  return { result, row, before, after };
}

const stamp = Date.now();
const startedAt = new Date(stamp - 1000).toISOString();
await select("cash");
let s = await session();
check("session opened on cash", Boolean(s));

await step("manual credit 20 to cash", { type: "manual_credit", wallet: "cash", amount: 20 }, () => manual("credit", "cash", "20.00"));
const cashBet = { session: s, betId: `adm-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await step("bet 10 on cash", { type: "bet", wallet: "cash", amount: 10 }, () => provider("bet", { ...cashBet, txId: randomUUID(), amount: "1000" }));
await step("win 15 on cash", { type: "win", wallet: "cash", amount: 15 }, () => provider("win", { ...cashBet, txId: randomUUID(), amount: "1500" }));
const lost = { session: s, betId: `adm-lost-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await step("bet 10 on cash, then lost", { type: "bet", wallet: "cash", amount: 10 }, () => provider("bet", { ...lost, txId: randomUUID(), amount: "1000" }));
const zero = await step("zero win closes the lost bet, nothing moves", { type: "win", wallet: "cash", amount: 0 }, () => provider("win", { ...lost, txId: randomUUID(), amount: "0" }));
check("zero win: before equals after", money(zero.row?.balance_before) === money(zero.row?.balance_after));
const cancelled = { session: s, betId: `adm-cancel-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await step("bet 10 on cash, to be cancelled", { type: "bet", wallet: "cash", amount: 10 }, () => provider("bet", { ...cancelled, txId: randomUUID(), amount: "1000" }));
await step("cancel returns 10 to cash", { type: "cancel", wallet: "cash", amount: 10 }, () => provider("win", { ...cancelled, txId: randomUUID(), amount: "1000", cancel: true }));
await step("manual debit 5 from cash", { type: "manual_debit", wallet: "cash", amount: 5 }, () => manual("debit", "cash", "5.00"));

await step("manual credit 30 to the bonus wallet", { type: "manual_credit", wallet: "cash_bonus", amount: 30 }, () => manual("credit", "cash_bonus", "30.00"));
let r = await select("cash_bonus");
check("bonus wallet selected", r.body?.active_balance_code === "cash_bonus", String(r.body?.active_balance_code));
s = await session();
const bonusBet = { session: s, betId: `adm-bonus-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await step("bet 10 on the bonus wallet", { type: "bet", wallet: "cash_bonus", amount: 10 }, () => provider("bet", { ...bonusBet, txId: randomUUID(), amount: "1000" }));
const bonusWinTx = randomUUID();
const bonusWin = await step("win 25 on a bonus bet goes whole to cash", { type: "win", wallet: "cash", amount: 25 }, () => provider("win", { ...bonusBet, txId: bonusWinTx, amount: "2500" }));
check("bonus win leaves the bonus wallet as it was", bonusWin.before.cash_bonus === bonusWin.after.cash_bonus, `${bonusWin.before.cash_bonus} -> ${bonusWin.after.cash_bonus}`);
await step("rollback of that win takes 25 back from cash", { type: "rollback", wallet: "cash", amount: 25 }, () => provider("rollback", { session: s, txId: bonusWinTx }));
const bonusLost = { session: s, betId: `adm-bonus-lost-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await step("bet 5 on the bonus wallet, then lost", { type: "bet", wallet: "cash_bonus", amount: 5 }, () => provider("bet", { ...bonusLost, txId: randomUUID(), amount: "500" }));
await step("zero win on a bonus bet stays on the bonus wallet", { type: "win", wallet: "cash_bonus", amount: 0 }, () => provider("win", { ...bonusLost, txId: randomUUID(), amount: "0" }));
const bonusCancel = { session: s, betId: `adm-bonus-cancel-${stamp}`, roundId: `round-${stamp}`, betNumber: "1" };
await step("bet 5 on the bonus wallet, to be cancelled", { type: "bet", wallet: "cash_bonus", amount: 5 }, () => provider("bet", { ...bonusCancel, txId: randomUUID(), amount: "500" }));
await step("cancel returns 5 to the bonus wallet", { type: "cancel", wallet: "cash_bonus", amount: 5 }, () => provider("win", { ...bonusCancel, txId: randomUUID(), amount: "500", cancel: true }));

r = await select("cash");
check("back on the cash wallet", r.body?.active_balance_code === "cash", String(r.body?.active_balance_code));
const page = await rows(40);
const chains = {};
let broken = 0;
const runRows = [...page].reverse().filter((row) => row.created_at >= startedAt);
for (const row of runRows) {
  if (!row.balance_code || row.balance_before === null) continue;
  const previous = chains[row.balance_code];
  if (previous !== undefined && money(row.balance_before) !== previous) broken++;
  chains[row.balance_code] = money(row.balance_after);
}
check("each wallet's rows chain: before = the previous row's after on the same wallet", broken === 0, `${broken} breaks over ${runRows.length} rows of this run`);
const history = await call("GET", "/v1/core/balances/transactions?limit=50&balance_code=cash_bonus", { token: player, publicKey: cfg.PUBLIC_KEY });
check("player history of the bonus wallet holds only bonus rows", history.status === 200 && (history.body?.transactions ?? []).every((t) => t.balance_code === "cash_bonus"), `${history.status} ${(history.body?.transactions ?? []).length} rows`);
console.log(`== ${envName}: ${passed}/${passed + failed} passed`);
process.exitCode = failed ? 1 : 0;
