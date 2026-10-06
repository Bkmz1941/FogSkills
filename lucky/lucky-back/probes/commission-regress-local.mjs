// Bet cases under the provider-wide commission and a per-game override, on the local
// regress stand. Run from lucky-api: node --env-file=.env <this file>. Prints no secrets.
import { createHmac, randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { dataSource } from "/home/ilya/Documents/Work/Lucky/lucky-api/dist/database/data-source.js";
import { issueAuthToken } from "/home/ilya/Documents/Work/Lucky/lucky-api/dist/modules/auth/auth-tokens.js";

const cfg = Object.fromEntries(readFileSync(join(homedir(), ".config", "lucky-regress", "local.env"), "utf8")
  .split("\n").filter(Boolean).map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]));
const API = cfg.LUCKY_API;
let passed = 0, failed = 0;
const check = (label, ok, note = "") => { ok ? passed++ : failed++; console.log(`${ok ? "PASS" : "FAIL"} ${label}${note ? `  // ${note}` : ""}`); };
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

await dataSource.initialize();
const [rootAdmin] = await dataSource.query("SELECT id, password_hash FROM root_admins LIMIT 1");
const root = issueAuthToken({ subject: rootAdmin.id, kind: "root", passwordHash: rootAdmin.password_hash, ttlSeconds: 900 }).token;
const player = (await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body?.access_token;
const admin = (await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body?.access_token;
const cabinet = (await call("POST", "/v1/provider/auth/login", { body: { email: cfg.CABINET_EMAIL, password: cfg.CABINET_PASSWORD } })).body?.access_token;
check("logins (root, player, project admin, provider cabinet)", Boolean(root && player && admin && cabinet));

const rootProvider = async () => ((await call("GET", "/v1/root/game-providers", { token: root })).body?.data ?? []).find(p => p.id === cfg.PROVIDER_ID);
const providerBefore = await rootProvider();
const gameBefore = (await call("GET", `/v1/root/games/${cfg.GAME_ID}`, { token: root })).body;
console.log(`stand before: provider ${providerBefore?.commission_percent}%, game ${gameBefore?.commission_percent}% (own: ${gameBefore?.commission_overridden})`);

const top = await call("POST", `/v1/project/finance/users/${cfg.PLAYER_ID}/transactions`, { token: admin, body: { direction: "credit", amount: "500", currency: "USD", balance_code: "cash", comment: "commission regress top-up" } });
check("top up the player with 500", top.status === 201, String(top.status));
const gameRoute = `/v1/core/providers/${cfg.PROVIDER_PID}/games/${cfg.GAME_PID}`;
const session = (await call("POST", `${gameRoute}/sessions`, { token: player, publicKey: cfg.PUBLIC_KEY })).body?.session;
check("game session", Boolean(session));
const balance = async () => Number((await provider("user/info", { session })).body?.balance);
const walletEntries = async () => {
  const r = await call("GET", "/v1/provider/wallet-transactions?limit=100", { token: cabinet });
  return Array.isArray(r.body?.data) ? r.body.data : [];
};
const providerWallet = async () => {
  const r = await call("GET", "/v1/provider/wallets", { token: cabinet });
  return Number((r.body?.data ?? []).find(w => w.currency === "USD")?.balance ?? 0);
};
const snapshotPercent = async (txId) => {
  const [row] = await dataSource.query("SELECT metadata -> 'provider' -> 'game' ->> 'commission_percent' AS percent FROM client_wallet_account_transactions WHERE metadata ->> 'transaction_id' = $1 LIMIT 1", [txId]);
  return row?.percent ?? null;
};
const money = (value) => value.toFixed(8);

const configs = [
  { name: "общая 5%, игра наследует", provider: "5", game: null, percent: 5 },
  { name: "общая 5%, у игры своя 12.5%", provider: "5", game: "12.5", percent: 12.5 },
  { name: "общая 5%, у игры своя 0%", provider: "5", game: "0", percent: 0 },
  { name: "общая сменилась на 8%, игра наследует", provider: "8", game: null, percent: 8 },
];
const cases = [
  { name: "проигрыш", stake: 1000, win: 0 },
  { name: "частичный выигрыш", stake: 1000, win: 400 },
  { name: "в ноль", stake: 1000, win: 1000 },
  { name: "крупный выигрыш", stake: 1000, win: 2500 },
  { name: "отмена ставки", stake: 1000, win: 1000, cancel: true },
];
let firstLostTx = null;

for (const config of configs) {
  console.log(`\n== ${config.name}`);
  const setProvider = await call("PATCH", `/v1/root/game-providers/${cfg.PROVIDER_ID}`, { token: root, body: { commission_percent: config.provider } });
  const setGame = await call("PATCH", `/v1/root/games/${cfg.GAME_ID}`, { token: root, body: { commission_percent: config.game } });
  check("настройка применена", setProvider.status === 200 && setGame.status === 200 && Number(setGame.body?.commission_percent) === config.percent && setGame.body?.commission_overridden === (config.game !== null),
    `provider ${setProvider.body?.commission_percent}, game ${setGame.body?.commission_percent} own=${setGame.body?.commission_overridden}`);
  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;

  for (const c of cases) {
    const base = { session, betId: `cr-${stamp}-${c.name}`, roundId: `round-${stamp}`, betNumber: "1" };
    const winTx = randomUUID();
    const before = await balance();
    const walletBefore = await providerWallet();
    const bet = await provider("bet", { ...base, txId: randomUUID(), amount: String(c.stake) });
    const win = await provider("win", { ...base, txId: winTx, amount: String(c.win), ...(c.cancel ? { cancel: true } : {}) });
    const after = await balance();
    const expected = Math.max(0, c.stake - c.win) / 100 * config.percent / 100;
    const entry = (await walletEntries()).find(e => e.transaction_id === winTx && e.type === "commission");
    const walletAfter = await providerWallet();
    check(`${c.name}: ставка и расчёт приняты, баланс ${before} → ${after}`, bet.status === 201 && win.status === 201 && after === before - c.stake + c.win, `${bet.status}/${win.status}`);
    check(`${c.name}: комиссия ${expected ? money(expected) : "нет"}`,
      expected ? entry?.amount === money(expected) && Number(entry?.commission_percent) === config.percent : !entry,
      entry ? `${entry.amount} при ${entry.commission_percent}%` : "записи нет");
    check(`${c.name}: кошелёк провайдера +${money(expected)}`, Math.abs(walletAfter - walletBefore - expected) < 1e-9, `${walletBefore} → ${walletAfter}`);
    if (!c.cancel) check(`${c.name}: в раунде записан процент ${config.percent}`, Number(await snapshotPercent(winTx)) === config.percent, String(await snapshotPercent(winTx)));
    if (c.name === "проигрыш" && config === configs[0]) firstLostTx = winTx;
  }

  // Rolling back a settled loss takes the commission back; a rolled-back bet cannot be settled.
  const base = { session, betId: `cr-${stamp}-rollback`, roundId: `round-${stamp}`, betNumber: "1" };
  const winTx = randomUUID();
  await provider("bet", { ...base, txId: randomUUID(), amount: "1000" });
  await provider("win", { ...base, txId: winTx, amount: "400" });
  const beforeRollback = await balance();
  const walletBeforeRollback = await providerWallet();
  const rollback = await provider("rollback", { session, txId: winTx });
  const reversal = (await walletEntries()).find(e => e.transaction_id === winTx && e.type === "commission_reversal");
  const expected = 6 * config.percent / 100;
  check("откат выигрыша 4: игроку −4, комиссия сторнирована", rollback.status === 201 && rollback.body?.reversed === true && (await balance()) === beforeRollback - 400
    && (expected ? reversal?.amount === money(-expected) : !reversal) && Math.abs((await providerWallet()) - walletBeforeRollback + expected) < 1e-9,
    `${rollback.status} reversal ${reversal?.amount ?? "нет"}`);
  const betTx = randomUUID();
  const lone = { session, betId: `cr-${stamp}-rolled-bet`, roundId: `round-${stamp}`, betNumber: "1" };
  await provider("bet", { ...lone, txId: betTx, amount: "1000" });
  const beforeBetRollback = await balance();
  const betRollback = await provider("rollback", { session, txId: betTx });
  const lateWin = await provider("win", { ...lone, txId: randomUUID(), amount: "0" });
  check("откат ставки: +10 вернулось, расчёт по ней → 404 bet_not_found", betRollback.status === 201 && (await balance()) === beforeBetRollback + 1000 && lateWin.status === 404 && lateWin.body?.error?.code === "bet_not_found",
    `${betRollback.status} / ${lateWin.status} ${lateWin.body?.error?.code}`);
  const twice = { session, betId: `cr-${stamp}-twice`, roundId: `round-${stamp}`, betNumber: "1" };
  await provider("bet", { ...twice, txId: randomUUID(), amount: "1000" });
  await provider("win", { ...twice, txId: randomUUID(), amount: "0" });
  const again = await provider("win", { ...twice, txId: randomUUID(), amount: "0" });
  check("второй расчёт той же ставки → 409, комиссия не задвоилась", again.status === 409 && again.body?.error?.code === "bet_already_settled", `${again.status} ${again.body?.error?.code}`);
}

console.log("\n== снимок процента");
const old = (await walletEntries()).find(e => e.transaction_id === firstLostTx && e.type === "commission");
check("ранний раунд сохранил 5% после смены общей на 8%", Number(old?.commission_percent) === 5 && Number(await snapshotPercent(firstLostTx)) === 5, `${old?.commission_percent}`);

const [{ mismatched }] = await dataSource.query("SELECT count(*)::int AS mismatched FROM client_wallet_accounts a LEFT JOIN (SELECT account_id, sum(amount) s FROM client_wallet_account_transactions GROUP BY 1) j ON j.account_id = a.id WHERE a.amount <> COALESCE(j.s, 0)");
check("журнал сходится со всеми счетами", mismatched === 0, `расхождений ${mismatched}`);

await call("PATCH", `/v1/root/game-providers/${cfg.PROVIDER_ID}`, { token: root, body: { commission_percent: providerBefore.commission_percent } });
await call("PATCH", `/v1/root/games/${cfg.GAME_ID}`, { token: root, body: { commission_percent: gameBefore.commission_overridden ? gameBefore.commission_percent : null } });
const providerAfter = await rootProvider();
const gameAfter = (await call("GET", `/v1/root/games/${cfg.GAME_ID}`, { token: root })).body;
check("стенд возвращён как был", providerAfter.commission_percent === providerBefore.commission_percent && gameAfter.commission_percent === gameBefore.commission_percent && gameAfter.commission_overridden === gameBefore.commission_overridden,
  `provider ${providerAfter.commission_percent}%, game ${gameAfter.commission_percent}% own=${gameAfter.commission_overridden}`);
await dataSource.destroy();
console.log(`\n${passed}/${passed + failed} passed`);
process.exitCode = failed ? 1 : 0;
