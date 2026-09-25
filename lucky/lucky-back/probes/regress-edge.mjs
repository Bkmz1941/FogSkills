// Edge cases of the provider callbacks on the regression stand: retries, duplicates, order, sessions, bad input.
// Usage: node regress-edge.mjs dev|prod   (session-expiry cases run on dev only: they age the stand session in the DB)
// PASS/FAIL against the intended rule; lines marked [rule?] check a rule that is not decided yet (Aviatrix behaviour).
import { createHmac, randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const envName = process.argv[2];
const cfg = Object.fromEntries(readFileSync(join(homedir(), ".config", "lucky-regress", `${envName}.env`), "utf8")
  .split("\n").filter(Boolean).map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]));
const API = cfg.LUCKY_API;
const results = [];
const check = (label, ok, note = "") => { results.push({ label, ok }); console.log(`${ok ? "PASS" : "FAIL"} ${label}${note ? `  // ${note}` : ""}`); return ok; };
const info = (label, note) => console.log(`INFO ${label}  // ${note}`);

async function http(method, path, { token, publicKey, body, raw, headers = {} } = {}) {
  const h = { ...headers };
  if (body !== undefined || raw !== undefined) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  if (publicKey) h["X-Public-Key"] = publicKey;
  const res = await fetch(API + path, { method, headers: h, body: raw ?? (body === undefined ? undefined : JSON.stringify(body)) });
  return { status: res.status, body: await res.json().catch(() => null) };
}
const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
const signFor = (route, body) => createHmac("sha256", cfg.PROVIDER_PRIVATE_KEY).update(["POST", `/v1/external/game-provider/${route}`, canonical({}), canonical(body)].join("\n")).digest("hex");
const cb = (route, body, { raw, sign } = {}) => http("POST", `/v1/external/game-provider/${route}`, { body: raw === undefined ? body : undefined, raw, headers: { "x-api-key": cfg.PROVIDER_PUBLIC_KEY, "x-sign": sign ?? signFor(route, body) } });
const code = (r) => r.body?.error?.code ?? r.status;
const same = (a, b) => a.body?.processedTxId === b.body?.processedTxId && a.body?.balance === b.body?.balance && a.body?.createdAt === b.body?.createdAt;

const player = (await http("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body.access_token;
const admin = (await http("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body.access_token;
const cabinet = (await http("POST", "/v1/provider/auth/login", { body: { email: cfg.CABINET_EMAIL, password: cfg.CABINET_PASSWORD } })).body.access_token;
const gameRoute = `/v1/core/providers/${cfg.PROVIDER_PID}/games/${cfg.GAME_PID}`;
const newSession = async () => (await http("POST", `${gameRoute}/sessions`, { token: player, publicKey: cfg.PUBLIC_KEY })).body.session;
let session = await newSession();
const balance = async (s = session) => BigInt((await cb("user/info", { session: s })).body?.balance ?? "-1");
if (await balance() < 50000n) await http("POST", `/v1/project/finance/users/${cfg.PLAYER_ID}/transactions`, { token: admin, body: { direction: "credit", amount: "1000", currency: "USD", balance_code: "cash", comment: "regress edge top-up" } });

let n = 0;
const ids = () => { n += 1; const tag = `${Date.now()}-${n}`; return { betId: `edge-${tag}`, roundId: `round-${tag}`, betNumber: "1" }; };
const bet = (b, amount = "100", s = session) => cb("bet", { session: s, txId: randomUUID(), amount, ...b });
const win = (b, amount = "100", extra = {}, s = session) => cb("win", { session: s, txId: randomUUID(), amount, ...b, ...extra });
const ledger = async () => {
  const r = await http("GET", "/v1/provider/wallet-transactions?limit=100", { token: cabinet });
  return Array.isArray(r.body?.data) ? r.body.data : [];
};
const commissionsFor = async (betId) => (await ledger()).filter(e => e.bet_id === betId);

console.log(`== ${envName}: retries after a lost answer`);
for (const kind of ["bet", "win", "cancel", "rollback"]) {
  const b = ids();
  await bet(b);
  const txId = randomUUID();
  let body = { session, txId, amount: "100", ...b, ...(kind === "cancel" ? { cancel: true } : {}) };
  if (kind === "bet") body = { session, txId, amount: "100", ...ids() };
  if (kind === "rollback") {
    const betTx = randomUUID();
    await cb("bet", { session, txId: betTx, amount: "100", ...ids() });
    body = { session, txId: betTx };
  }
  const route = kind === "cancel" ? "win" : kind;
  const before = await balance();
  const first = await cb(route, body);
  const second = await cb(route, body);
  const third = await cb(route, body);
  const after = await balance();
  const moved = after - before;
  const expected = kind === "bet" ? -100n : 100n;
  check(`${kind}: 3 identical calls answer the same and move money once`, first.status === 201 && same(first, second) && same(first, third) && moved === expected, `moved ${moved}`);
}

{
  const b = ids(); const txId = randomUUID(); const body = { session, txId, amount: "100", ...b };
  const first = await cb("bet", body);
  await bet(ids()); await bet(ids());
  const later = await cb("bet", body);
  check("retry after other operations returns the original balance", same(first, later), `first ${first.body?.balance}, retry ${later.body?.balance}`);
  const reordered = JSON.stringify(Object.fromEntries(Object.entries(body).reverse()));
  const again = await cb("bet", body, { raw: reordered });
  check("retry re-serialised in another key order is the same request", same(first, again), String(again.status));
  for (const field of ["betId", "roundId", "betNumber", "amount"]) {
    const changed = { ...body, [field]: field === "amount" ? "200" : `${body[field]}-x` };
    const r = await cb("bet", changed);
    check(`[rule?] same txId with another ${field} is a conflict`, r.status === 409, `${r.status} ${code(r)}`);
  }
}

{
  const b = ids(); await bet(b);
  const txId = randomUUID(); const body = { session, txId, amount: "150", ...b };
  const before = await balance();
  const wins = await Promise.all(Array.from({ length: 10 }, () => cb("win", body)));
  const afterWins = await balance();
  check("10 parallel identical wins: one credit", new Set(wins.map(r => r.body?.processedTxId)).size === 1 && afterWins - before === 150n, `moved ${afterWins - before}`);
  const rb = await Promise.all(Array.from({ length: 10 }, () => cb("rollback", { session, txId })));
  const afterRb = await balance();
  check("10 parallel identical rollbacks: one reversal", new Set(rb.map(r => r.body?.processedTxId)).size === 1 && afterRb - afterWins === -150n, `moved ${afterRb - afterWins}`);
}

console.log(`== ${envName}: duplicates by meaning`);
{
  const b = ids();
  const first = await bet(b); const second = await bet(b);
  check("[rule?] a second bet with the same betId is refused", first.status === 201 && second.status >= 400, `${second.status} ${code(second)}`);
}
{
  const b = ids(); await bet(b, "1000");
  const w1 = await win(b, "0"); const w2 = await win(b, "0");
  const entries = await commissionsFor(b.betId);
  check("[rule?] a second SettleBet on one bet is refused", w1.status === 201 && w2.status >= 400, `${w2.status} ${code(w2)}`);
  check("one bet never pays commission twice", entries.filter(e => e.type === "commission").length <= 1, `${entries.length} entries`);
}
{
  const b = ids(); await bet(b);
  await win(b, "150");
  const c = await win(b, "100", { cancel: true });
  check("[rule?] a cancel after the win on the same bet is refused", c.status >= 400, `${c.status} ${code(c)}`);
}
{
  const b = ids(); await bet(b, "100");
  const before = await balance();
  const c = await win(b, "10000", { cancel: true });
  const after = await balance();
  check("a cancel cannot return more than the stake", c.status >= 400 || after - before <= 100n, `${c.status}, moved ${after - before}`);
  const orphan = ids();
  const b2 = await balance();
  const c2 = await win(orphan, "500", { cancel: true });
  const a2 = await balance();
  check("a cancel of a bet that never came moves no money", c2.status >= 400 || a2 === b2, `${c2.status} ${code(c2)}, moved ${a2 - b2}`);
}

console.log(`== ${envName}: out-of-order`);
{
  const b = ids(); const winTx = randomUUID();
  const rb = await cb("rollback", { session, txId: winTx });
  const late = await cb("win", { session, txId: winTx, amount: "100", ...b });
  check("rollback before the win, then the late win is refused", rb.status === 201 && rb.body?.reversed === false && late.status === 409, `${late.status} ${code(late)}`);
}
{
  const b = ids();
  const before = await balance();
  const w = await win(b, "700");
  const after = await balance();
  check("[rule?] a win for a bet that never came is refused (Aviatrix: Bet not found)", w.status >= 400 && after === before, `${w.status} ${code(w)}, moved ${after - before}`);
}
{
  const b = ids(); const betTx = randomUUID();
  await cb("bet", { session, txId: betTx, amount: "1000", ...b });
  await win(b, "0");
  const withCommission = (await commissionsFor(b.betId)).length;
  const rb = await cb("rollback", { session, txId: betTx });
  const entries = await commissionsFor(b.betId);
  info("rollback of a bet that was already settled as lost", `rollback ${rb.status} reversed=${rb.body?.reversed}; commission entries ${withCommission} -> ${entries.length}, types ${entries.map(e => e.type).join(",") || "none"}`);
}
{
  const b = ids(); const betTx = randomUUID();
  await cb("bet", { session, txId: betTx, amount: "100", ...b });
  const before = await balance();
  const [rb, w] = await Promise.all([cb("rollback", { session, txId: betTx }), win(b, "150")]);
  const after = await balance();
  const expected = (rb.body?.reversed ? 100n : 0n) + (w.status === 201 ? 150n : 0n);
  check("parallel rollback of the bet and its win: balance matches what was answered", after - before === expected, `rollback ${rb.status}/${rb.body?.reversed}, win ${w.status}, moved ${after - before}`);
}

console.log(`== ${envName}: sessions`);
if (envName === "dev" || envName === "local") {
  const s = await newSession();
  const b = ids();
  await bet(b, "100", s);
  const wb = ids(); await bet(wb, "100", s);
  const winTx = randomUUID(); const winBody = { session: s, txId: winTx, amount: "150", ...wb };
  const firstWin = await cb("win", winBody);
  const ageSql = `UPDATE game_sessions SET expires_at = now() - interval '1 minute' WHERE launch_token = '${s.replace(/[^a-z0-9]/gi, "")}';`;
  let aged = false;
  try {
    if (envName === "local") execFileSync("sh", ["-c", "cd ~/Documents/Work/Lucky/lucky-api && docker exec -i luckyserverpro-postgres-1 psql -U \"$(grep -E '^DATABASE_USER(NAME)?=' .env | head -1 | cut -d= -f2)\" -d \"$(grep -E '^DATABASE_NAME=' .env | cut -d= -f2)\" -At"], { input: ageSql, encoding: "utf8" });
    else execFileSync("ssh", ["lucky-dev", "docker exec -i luckyserver-dev-postgres-1 sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -At'"], { input: ageSql, encoding: "utf8" });
    aged = true;
  } catch (error) { info("session expiry", `could not age the session: ${error.message.split("\n")[0]}`); }
  if (aged) {
    const lateWin = await win(b, "150", {}, s);
    check("[rule?] a win after the session expired is still paid (Aviatrix)", lateWin.status === 201, `${lateWin.status} ${code(lateWin)}`);
    const retry = await cb("win", winBody);
    check("a retry of an already paid win after expiry returns the stored answer", same(firstWin, retry), `${retry.status} ${code(retry)}`);
    const lateBet = await bet(ids(), "100", s);
    check("a bet after the session expired is refused", lateBet.status >= 400, `${lateBet.status} ${code(lateBet)}`);
    const lateRb = await cb("rollback", { session: s, txId: winTx });
    check("[rule?] a rollback after the session expired still works", lateRb.status === 201, `${lateRb.status} ${code(lateRb)}`);
  }
} else {
  info("sessions", "expiry cases run on dev only");
}

console.log(`== ${envName}: bad input`);
for (const amount of ["0", "00100", " 100", "1e3", "-1", "", "10.5"]) {
  const r = await bet(ids(), amount);
  check(`bet amount ${JSON.stringify(amount)} is a clean 4xx`, r.status >= 400 && r.status < 500, `${r.status} ${code(r)}`);
}
{
  const current = await balance();
  const over = await bet(ids(), String(current + 1n));
  check("a bet over the balance is refused and moves nothing", over.status >= 400 && await balance() === current, `${over.status} ${code(over)}`);
  const all = ids();
  const exact = await bet(all, String(current));
  check("a bet of exactly the whole balance is taken", exact.status === 201 && await balance() === 0n, `${exact.status}`);
  await win(all, String(current), { cancel: true });
  check("the whole balance comes back on cancel", await balance() === current);
}
{
  const b = ids(); await bet(b);
  const w = await win({ ...b, roundId: `${b.roundId}-other` }, "150");
  info("win with another roundId than its bet", `${w.status} ${code(w)}`);
  const noNumber = await cb("bet", { session, txId: randomUUID(), amount: "100", betId: ids().betId, roundId: "r" });
  info("bet without betNumber", `${noNumber.status} ${code(noNumber)}`);
}
{
  const body = { session, txId: randomUUID(), amount: "100", ...ids() };
  const sign = signFor("bet", body);
  const replayNewTx = await cb("bet", { ...body, txId: randomUUID() }, { sign });
  check("an old signature does not cover a new txId", replayNewTx.status === 401, `${replayNewTx.status} ${code(replayNewTx)}`);
}

const failed = results.filter(r => !r.ok);
console.log(`== ${envName}: ${results.length - failed.length}/${results.length} passed`);
for (const r of failed) console.log(`   failed: ${r.label}`);
process.exit(failed.length ? 1 : 0);
