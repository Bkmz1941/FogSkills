// Project bonuses and their wagering, on a regress stand: node bonus-regress.mjs dev|prod|local.
// Reads ~/.config/lucky-regress/<env>.env. Creates its own bonuses in the Regress project (switched off at the end),
// moves only the regress player's money: manual credits, bets and wins through the regress provider.
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
  for (let attempt = 0; ; attempt++) {
    const res = await fetch(cfg.LUCKY_API + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
    if (res.status === 429 && attempt < 4) {
      await new Promise((resolve) => setTimeout(resolve, (Number(res.headers.get("retry-after")) || 15) * 1000 + 500));
      continue;
    }
    return { status: res.status, body: await res.json().catch(() => null) };
  }
}
const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
const provider = (route, body) => {
  const path = `/v1/external/game-provider/${route}`;
  const sign = createHmac("sha256", cfg.PROVIDER_PRIVATE_KEY).update(["POST", path, canonical({}), canonical(body)].join("\n")).digest("hex");
  return call("POST", path, { body, headers: { "x-api-key": cfg.PROVIDER_PUBLIC_KEY, "x-sign": sign } });
};

console.log(`== ${envName}: project bonuses and wagering`);
const player = (await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body?.access_token;
const admin = (await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body?.access_token;
check("player and project admin login", Boolean(player && admin));
if (!player || !admin) { process.exitCode = 1; process.exit(); }

const stamp = Date.now();
const codeOf = (bonus) => `bonus_${bonus.id.replace(/-/g, "")}_usd`;
const accounts = async () => {
  const r = await call("GET", `/v1/project/balances/users/${cfg.PLAYER_ID}`, { token: admin });
  const out = {};
  for (const balance of r.body?.balances ?? []) {
    if (balance.currency !== "USD") continue;
    const key = balance.balance_code === "cash" ? "cash" : balance.kind === "bonus" ? balance.balance_code : null;
    if (!key) continue;
    for (const account of balance.accounts ?? []) out[`${key}.${account.type}`] = Number(account.amount);
  }
  return out;
};
const delta = (before, after) => Object.fromEntries([...new Set([...Object.keys(before), ...Object.keys(after)])]
  .map(key => [key, +((after[key] ?? 0) - (before[key] ?? 0)).toFixed(2)]).filter(([, value]) => value !== 0));
const named = (d, code) => Object.fromEntries(Object.entries(d).map(([key, value]) => [key.replace(code, "bonus"), value]));
const select = (code) => call("POST", "/v1/core/balances/select", { token: player, publicKey: cfg.PUBLIC_KEY, body: { balance_code: code } });
const sessionOn = () => call("POST", `/v1/core/providers/${cfg.PROVIDER_PID}/games/${cfg.GAME_PID}/sessions`, { token: player, publicKey: cfg.PUBLIC_KEY });
const manual = (direction, code, amount) => call("POST", `/v1/project/finance/users/${cfg.PLAYER_ID}/transactions`, { token: admin, body: { direction, amount, currency: "USD", balance_code: code, comment: "bonus regress" } });
const createBonus = (input) => call("POST", "/v1/project/bonuses", { token: admin, body: { name: `Regress bonus ${stamp}`, display_name: "Regress bonus", currency_codes: ["USD"], coefficient: "2", starts_at: null, expires_at: null, provider_ids: [], game_ids: [], ...input } });
const patchBonus = (id, input) => call("PATCH", `/v1/project/bonuses/${id}`, { token: admin, body: input });
let round = 0;
async function play(sessionToken, stake, win, extra = {}) {
  const bet = { session: sessionToken, betId: `bonus-${stamp}-${++round}`, roundId: `bonus-round-${stamp}-${round}`, betNumber: "1" };
  const placed = await provider("bet", { ...bet, txId: randomUUID(), amount: stake });
  const settled = win === null ? null : await provider("win", { ...bet, txId: randomUUID(), amount: win, ...extra });
  return { placed, settled };
}
const created = [];

let r = await call("GET", "/v1/project/bonuses", { token: admin });
const fallback = (r.body?.data ?? []).find((bonus) => bonus.is_default);
check("the project has its default bonus", Boolean(fallback && fallback.code === "default"), fallback ? `${fallback.code} ${fallback.currency_codes.join(",")}` : String(r.status));
if (fallback) {
  r = await call("DELETE", `/v1/project/bonuses/${fallback.id}`, { token: admin });
  check("the default bonus cannot be deleted", r.status === 409, String(r.status));
  r = await patchBonus(fallback.id, { code: `renamed_${stamp}` });
  check("the default bonus keeps its system name", r.status === 409, String(r.status));
}

r = await createBonus({ code: `regress_${stamp}` });
const bonus = r.body;
check("a bonus is created with three names, USD, coefficient 2, unlimited, every game", r.status === 201 && bonus?.code === `regress_${stamp}` && bonus?.display_name === "Regress bonus" && bonus?.coefficient === "2.0000" && bonus?.is_live === true, `${r.status} ${bonus?.coefficient}`);
if (!bonus?.id) { console.log(`== ${envName}: ${passed}/${passed + failed} passed`); process.exitCode = 1; process.exit(); }
created.push(bonus.id);
const code = codeOf(bonus);
r = await createBonus({ code: `regress_${stamp}` });
check("a second bonus with the same system name is refused", r.status === 409, String(r.status));
r = await createBonus({ code: `regress_bad_${stamp}`, starts_at: "2030-01-02T00:00:00Z", expires_at: "2030-01-01T00:00:00Z" });
check("a bonus that ends before it starts is refused", r.status === 400, String(r.status));
r = await createBonus({ code: `regress_cur_${stamp}`, currency_codes: ["ZZZ"] });
check("a currency the project does not have is refused", r.status === 400, String(r.status));

await select("cash");
let before = await accounts();
r = await manual("credit", code, "50.00");
let d = named(delta(before, await accounts()), code);
check("manual credit 50 to the bonus lands in bonus pending only", r.status === 201 && d["bonus.pending"] === 50 && Object.keys(d).length === 1, `${r.status} ${JSON.stringify(d)}`);
before = await accounts();
r = await call("POST", "/v1/project/finance/deposits", { token: admin, body: { client_id: cfg.PLAYER_ID, currency: "USD", amount: "10.00", bonus_id: bonus.id } });
d = named(delta(before, await accounts()), code);
check("a deposit with bonus_id lands in bonus pending as a manual credit", r.status === 201 && r.body?.type === "manual_credit" && d["bonus.pending"] === 10 && Object.keys(d).length === 1, `${r.status} ${r.body?.type} ${JSON.stringify(d)}`);

r = await call("GET", "/v1/core/balances", { token: player, publicKey: cfg.PUBLIC_KEY });
const listed = (r.body?.balances ?? []).find((balance) => balance.balance_code === code);
check("the player sees the bonus balance under its player name, selectable", listed?.kind === "bonus" && listed?.balance_name === "Regress bonus" && listed?.is_client_selectable === true && Number(listed?.available_amount) === 60, JSON.stringify(listed ?? null));
r = await select(code);
check("the player selects the bonus balance", r.body?.active_balance_code === code, String(r.body?.active_balance_code));
r = await call("POST", "/v1/core/balances/withdrawal-requests", { token: player, publicKey: cfg.PUBLIC_KEY, body: { amount: "1.00", balance_code: code } });
check("a withdrawal from the bonus balance is refused", r.status >= 400 && r.status < 500, String(r.status));

r = await sessionOn();
const session = r.body?.session;
check("a game the bonus covers opens on the bonus balance", r.status === 201 && Boolean(session), String(r.status));

before = await accounts();
let game = await play(session, "1000", "1500");
d = named(delta(before, await accounts()), code);
check("win below the coefficient (x1.5 < x2) returns to bonus pending", game.placed.status < 300 && game.settled.status < 300 && d["bonus.pending"] === 5 && !("cash.available" in d) && !("cash.pending" in d), JSON.stringify(d));
before = await accounts();
game = await play(session, "1000", "2000");
d = named(delta(before, await accounts()), code);
check("win exactly at the coefficient (x2) pays into cash available, stake included", d["bonus.pending"] === -10 && d["cash.available"] === 20 && Object.keys(d).length === 2, JSON.stringify(d));
before = await accounts();
game = await play(session, "1000", "3000");
d = named(delta(before, await accounts()), code);
check("win above the coefficient (x3) pays into cash available", d["bonus.pending"] === -10 && d["cash.available"] === 30 && Object.keys(d).length === 2, JSON.stringify(d));
before = await accounts();
game = await play(session, "1000", "0");
d = named(delta(before, await accounts()), code);
check("a lost bonus bet takes from the bonus and never touches cash", d["bonus.pending"] === -10 && Object.keys(d).length === 1, JSON.stringify(d));
before = await accounts();
game = await play(session, "1000", "1000", { cancel: true });
d = named(delta(before, await accounts()), code);
check("a bonus bet and its cancel leave every account as it was", Object.keys(d).length === 0, JSON.stringify(d));
before = await accounts();
game = await play(session, "100000", null);
d = named(delta(before, await accounts()), code);
check("a bonus bet above the bonus balance is refused and moves nothing", game.placed.status >= 400 && Object.keys(d).length === 0, `${game.placed.status} ${JSON.stringify(d)}`);

r = await call("GET", "/v1/core/balances/transactions?operations=bets&limit=20&balance_code=" + code, { token: player, publicKey: cfg.PUBLIC_KEY });
const betTypes = new Set((r.body?.data ?? r.body?.transactions ?? []).map((row) => row.type));
check("bet history of the bonus lists only game operations", r.status === 200 && betTypes.size > 0 && [...betTypes].every((type) => ["bet", "win", "cancel", "rollback"].includes(type)), [...betTypes].join(","));
r = await call("GET", "/v1/core/balances/transactions?operations=payments&limit=20&balance_code=" + code, { token: player, publicKey: cfg.PUBLIC_KEY });
const payTypes = new Set((r.body?.data ?? r.body?.transactions ?? []).map((row) => row.type));
check("operation history of the bonus lists the credits, no bets", r.status === 200 && payTypes.has("manual_credit") && ![...payTypes].some((type) => ["bet", "win"].includes(type)), [...payTypes].join(","));

r = await patchBonus(bonus.id, { is_active: false });
check("switching the bonus off freezes it", r.status === 200 && r.body?.is_live === false, String(r.status));
before = await accounts();
game = await play(session, "1000", null);
d = named(delta(before, await accounts()), code);
check("a bet on a frozen bonus is refused and moves nothing", game.placed.status >= 400 && Object.keys(d).length === 0, `${game.placed.status} ${JSON.stringify(game.placed.body)?.slice(0, 120)}`);
r = await manual("credit", code, "5.00");
check("a credit to a frozen bonus is refused", r.status === 400, String(r.status));
r = await call("GET", "/v1/core/balances", { token: player, publicKey: cfg.PUBLIC_KEY });
const frozen = (r.body?.balances ?? []).find((balance) => balance.balance_code === code);
check("a frozen bonus is not selectable and the player falls back to cash", frozen?.is_client_selectable === false && r.body?.active_balance_code !== code, `${frozen?.is_client_selectable} ${r.body?.active_balance_code}`);
r = await patchBonus(bonus.id, { is_active: true });
r = await select(code);
check("switching it back on makes it selectable again", r.body?.active_balance_code === code, String(r.body?.active_balance_code));
before = await accounts();
r = await patchBonus(bonus.id, { expires_at: new Date(Date.now() - 60000).toISOString() });
const current = await call("GET", "/v1/core/balances/current", { token: player, publicKey: cfg.PUBLIC_KEY });
check("an ended bonus is frozen and the player's active balance falls back to cash", r.status === 200 && r.body?.is_live === false && (current.body?.balance_code ?? current.body?.balance?.balance_code) === "cash", `${r.status} ${JSON.stringify(current.body)?.slice(0, 80)}`);
game = await play(session, "1000", null);
d = named(delta(before, await accounts()), code);
check("an open game session on the ended bonus cannot bet", game.placed.status === 403 && Object.keys(d).length === 0, `${game.placed.status} ${JSON.stringify(d)}`);
r = await patchBonus(bonus.id, { expires_at: null });
check("removing the end brings it back", r.status === 200 && r.body?.is_live === true, String(r.status));

r = await call("GET", "/v1/project/game-providers", { token: admin });
const other = (r.body?.data ?? []).find((item) => item.id !== cfg.PROVIDER_ID);
if (other) {
  r = await createBonus({ code: `regress_other_${stamp}`, provider_ids: [other.id] });
  const narrow = r.body;
  if (narrow?.id) created.push(narrow.id);
  await manual("credit", codeOf(narrow), "5.00");
  await select(codeOf(narrow));
  const refused = await sessionOn();
  check("a bonus for another provider refuses to open the regress game (BONUS_GAME_NOT_ALLOWED)", refused.status === 403 && JSON.stringify(refused.body).includes("BONUS_GAME_NOT_ALLOWED"), `${refused.status} ${other.name}`);
  r = await patchBonus(narrow.id, { game_ids: [cfg.GAME_ID] });
  const allowed = await sessionOn();
  check("adding the regress game to that bonus lets it open", r.status === 200 && allowed.status === 201, `${r.status} ${allowed.status}`);
  await manual("debit", codeOf(narrow), "5.00");
} else console.log("SKIP game restriction  // the Regress project has no second provider");

r = await call("POST", "/v1/project/bonuses", { token: admin, body: { code: `regress_later_${stamp}`, name: "Later", display_name: "Later", currency_codes: ["USD"], coefficient: "1", starts_at: new Date(Date.now() + 86400000).toISOString(), expires_at: null, provider_ids: [], game_ids: [] } });
if (r.body?.id) created.push(r.body.id);
const later = r.body;
r = later?.id ? await manual("credit", codeOf(later), "5.00") : { status: 0 };
check("a bonus that has not started refuses credits", later?.is_live === false && r.status === 400, `${later?.is_live} ${r.status}`);

before = await accounts();
const rest = Number(before[`${code}.pending`] ?? 0) + Number(before[`${code}.available`] ?? 0);
if (rest > 0) await manual("debit", code, rest.toFixed(2));
d = named(delta(before, await accounts()), code);
check("the rest of the bonus is debited back to zero", rest === 0 || d["bonus.pending"] === -rest, `${rest} ${JSON.stringify(d)}`);
r = await call("DELETE", `/v1/project/bonuses/${bonus.id}`, { token: admin });
check("a bonus players hold cannot be deleted", r.status === 409, String(r.status));
r = await call("GET", "/v1/project/bonuses", { token: admin });
const listedBonus = (r.body?.data ?? []).find((item) => item.id === bonus.id);
check("the bonus list counts the player", listedBonus?.players === 1, String(listedBonus?.players));

r = await call("GET", "/v1/project/bonus-triggers", { token: admin });
if (r.status === 200) {
  check("the trigger list has Registration", (r.body?.data ?? []).some((item) => item.code === "registration"), (r.body?.data ?? []).map((item) => item.code).join(","));
  r = await createBonus({ code: `regress_signup_${stamp}`, trigger_code: "registration" });
  const signup = r.body;
  if (signup?.id) created.push(signup.id);
  check("a bonus takes the Registration trigger", r.status === 201 && signup?.trigger_code === "registration", `${r.status} ${signup?.trigger_code}`);
  r = await createBonus({ code: `regress_badtrigger_${stamp}`, trigger_code: "no_such_trigger" });
  check("an unknown trigger is refused", r.status === 400, String(r.status));
  const email = `regress-signup-${envName}-${stamp}@agg.one`;
  r = await call("POST", "/v1/auth/register", { publicKey: cfg.PUBLIC_KEY, body: { email, password: `Pw-${stamp}-regress`, password_confirmation: `Pw-${stamp}-regress`, locale: "en", currency: "USD" } });
  const freshId = r.body?.client?.id;
  const detail = freshId ? await call("GET", `/v1/project/users/${freshId}`, { token: admin }) : null;
  const attached = (detail?.body?.balances ?? []).find((balance) => signup?.id && balance.balance_code === codeOf(signup));
  check("registration attaches the Registration bonus to the new player, empty", attached?.kind === "bonus" && Number(attached?.available_amount) === 0, `${r.status} ${detail?.status} ${attached ? attached.available_amount : "no bonus wallet"}`);
} else console.log(`SKIP registration trigger  // GET /v1/project/bonus-triggers ${r.status}`);

for (const id of created) await patchBonus(id, { is_active: false });
r = await select("cash");
check("back on the cash wallet, regress bonuses switched off", r.body?.active_balance_code === "cash", String(r.body?.active_balance_code));
console.log(`== ${envName}: ${passed}/${passed + failed} passed`);
process.exitCode = failed ? 1 : 0;
