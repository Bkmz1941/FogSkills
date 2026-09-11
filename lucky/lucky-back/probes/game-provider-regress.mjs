// Регресс seamless-wallet коллбэков Lucky (/v1/external/game-provider/*) против живого стенда.
// Запуск на сервере или локально: node game-provider-regress.mjs [/tmp/probe-input]
// Файл входа — три строки: public_key провайдера, private_key провайдера, launch_token живой сессии.
// Проверки каталога (23-31) заводят собственную игру regress-* и удаляют её за собой; чужих игр не трогают.
// ONLY=catalog — прогнать только каталог: сессия ему не нужна, хватает двух строк входа (ключи провайдера).
// Ключи не печатаются. Переменная LUCKY_API переопределяет базовый URL (по умолчанию dev2).
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";

const [publicKey, privateKey, session] = readFileSync(process.argv[2] ?? "/tmp/probe-input", "utf8").trim().split("\n");
const BASE = process.env.LUCKY_API ?? "https://dev2.api.luckyserver.pro";
const CATALOG_ONLY = process.env.ONLY === "catalog";

const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
const sign = (method, path, body) => createHmac("sha256", privateKey).update([method, path, canonical({}), canonical(body)].join("\n")).digest("hex");

// opts.signOver — объект, по которому считать подпись (по умолчанию само тело);
// opts.raw — сырое тело строкой; opts.headers — переопределить заголовки;
// opts.method — глагол (метод входит в подписываемую строку, по умолчанию POST).
async function call(route, body, opts = {}) {
  const method = opts.method ?? "POST";
  const path = `/v1/external/game-provider/${route}`;
  const raw = opts.raw ?? JSON.stringify(body);
  const headers = opts.headers ?? { "x-api-key": publicKey, "x-sign": opts.wrongSign ? "0".repeat(64) : sign(method, path, opts.signOver ?? body) };
  const res = await fetch(BASE + path, { method, headers: { "Content-Type": "application/json", ...headers }, body: raw });
  return { status: res.status, body: await res.json().catch(() => null) };
}

const id = (p) => `${p}-${Date.now()}-${Math.floor(Math.random() * 1e4)}`;
const results = [];
function check(label, r, ok, note = "") {
  const pass = ok(r);
  results.push(pass);
  console.log(`${pass ? "PASS" : "FAIL"} ${label.padEnd(44)} ${r.status} ${JSON.stringify(r.body ?? null).slice(0, 120)}${note ? "  // " + note : ""}`);
  return r;
}
const info = async () => call("player/info", { sessionToken: session, timestamp: Math.floor(Date.now() / 1000) });
const bal = (r) => BigInt(r.body?.balance ?? "0");
const code = (r, c) => r.body?.error?.code === c;
const same = (a, b) => canonical(a ?? {}) === canonical(b ?? {});

function summary() {
  const failed = results.filter((p) => !p).length;
  console.log(`\n${results.length - failed}/${results.length} PASS${failed ? `, ${failed} FAIL` : ""}`);
  process.exit(failed ? 1 : 0);
}

async function catalogChecks() {
  // 23-31. каталог провайдера: POST/DELETE/PATCH на /games.
  // Работаем только со своей одноразовой игрой: чужие игры на стенде не трогаем.
  const gameId = id("regress");
  const item = {
    id: gameId,
    sys_name: gameId.replace(/-/g, "_"),
    name: "Regress Probe",
    type: "crash",
    cover_url: "https://dev.api.crash-heroes.com/storage/games/covers/balloon-fly-site.png",
  };
  const list = (v) => JSON.stringify(v ?? null);

  const before = check("22a. games: список до загрузки", await call("games", undefined, { method: "GET", signOver: {} }), (r) => r.status === 200 && typeof r.body?.total === "number" && Array.isArray(r.body?.games));

  check("23. games: загрузка новой игры", await call("games", { games: [item] }), (r) => r.status === 200 && r.body?.total === 1 && r.body?.created === 1 && r.body?.updated === 0);
  check("24. games: повтор обновляет, не создаёт", await call("games", { games: [{ ...item, name: "Regress Probe 2" }] }), (r) => r.status === 200 && r.body?.created === 0 && r.body?.updated === 1);
  check("25. games: категория провайдера вместо нашей → 400", await call("games", { games: [{ ...item, type: "crash-games" }] }), (r) => r.status === 400 && code(r, "invalid_request"), "type — категория Lucky, не провайдера");
  check("26. games: без cover_url → 400", await call("games", { games: [{ id: item.id, sys_name: item.sys_name, name: item.name, type: "crash" }] }), (r) => r.status === 400 && code(r, "invalid_request"));
  check("27. games: выключение", await call("games", { id: gameId, is_active: false }, { method: "PATCH" }), (r) => r.status === 200 && r.body?.id === gameId && r.body?.is_active === false);
  check("28. games: включение", await call("games", { id: gameId, is_active: true }, { method: "PATCH" }), (r) => r.status === 200 && r.body?.is_active === true);
  check("29. games: статус неизвестной игры → 404", await call("games", { id: "no-such-game", is_active: false }, { method: "PATCH" }), (r) => r.status === 404 && code(r, "unknown_game"));
  check("29a. games: новая игра видна в списке", await call("games", undefined, { method: "GET", signOver: {} }), (r) => r.status === 200 && r.body.total === before.body.total + 1 && r.body.games.some((g) => g.id === gameId && g.name === "Regress Probe 2" && g.type === "crash" && g.is_active === true), `было ${before.body?.total}`);

  check("30. games: удаление + not_found", await call("games", { ids: [gameId, "no-such-game"] }, { method: "DELETE" }), (r) => r.status === 200 && list(r.body?.deleted) === list([gameId]) && list(r.body?.not_found) === list(["no-such-game"]) && list(r.body?.in_use) === list([]));
  check("30a. games: список вернулся к исходному", await call("games", undefined, { method: "GET", signOver: {} }), (r) => r.status === 200 && r.body.total === before.body.total && !r.body.games.some((g) => g.id === gameId));

  check("31. games: удалённая игра больше не находится", await call("games", { id: gameId, is_active: true }, { method: "PATCH" }), (r) => r.status === 404 && code(r, "unknown_game"));

  // 32-33. Необязательные: ветка in_use на настоящей игре.
  // PLAYED_GAME_ID=<id у провайдера> задавать ТОЛЬКО для игры, у которой точно есть
  // сессии, иначе она будет удалена по-настоящему. Проверить заранее:
  //   select g.external_id, count(s.id) from game_provider_games g
  //   left join game_sessions s on s.game_id = g.id group by 1 order by 2 desc;
  // Шаг 33 оставляет игру включённой.
  const played = process.env.PLAYED_GAME_ID;
  if (played) {
    check("32. games: удаление сыгранной игры → in_use", await call("games", { ids: [played, "no-such-game"] }, { method: "DELETE" }), (r) => r.status === 200 && list(r.body?.in_use) === list([played]) && list(r.body?.deleted) === list([]), "БД держит её через ON DELETE RESTRICT");
    check("33. games: сыгранная игра осталась", await call("games", { id: played, is_active: true }, { method: "PATCH" }), (r) => r.status === 200 && r.body?.id === played && r.body?.is_active === true);
  }
}

if (CATALOG_ONLY) {
  await catalogChecks();
  summary();
}

// 0. исходный баланс
const start = check("0. player/info", await info(), (r) => r.status === 200 && typeof r.body?.balance === "string");
let expected = bal(start);

// 1-4. ставка, повтор, конфликт, выигрыш
const round = id("round"), betA = id("bet"), txA = id("tx");
const b1 = check("1. ставка 100", await call("bet", { session, txId: txA, amount: "100", betId: betA, roundId: round }), (r) => r.status === 201 && bal(r) === expected - 100n);
expected -= 100n;
check("2. повтор ставки: тот же ответ", await call("bet", { session, txId: txA, amount: "100", betId: betA, roundId: round }), (r) => r.status === 201 && same(r.body, b1.body), "processedTxId/createdAt/balance совпадают");
check("3. повтор с другой суммой", await call("bet", { session, txId: txA, amount: "999", betId: betA, roundId: round }), (r) => r.status === 409 && code(r, "idempotency_conflict"));
check("4. выигрыш 150", await call("win", { session, txId: id("tx"), amount: "150", betId: betA, roundId: round }), (r) => r.status === 201 && bal(r) === expected + 150n);
expected += 150n;

// 5-6. ставка и отмена
const betB = id("bet");
check("5. ставка 100 для отмены", await call("bet", { session, txId: id("tx"), amount: "100", betId: betB, roundId: id("round") }), (r) => r.status === 201 && bal(r) === expected - 100n);
expected -= 100n;
check("6. отмена 100", await call("cancel", { session, txId: id("tx"), amount: "100", betId: betB, roundId: round }), (r) => r.status === 201 && bal(r) === expected + 100n);
expected += 100n;

// 7-9. ставка, откат, повтор отката
const betC = id("bet"), txC = id("tx");
check("7. ставка 100 для отката", await call("bet", { session, txId: txC, amount: "100", betId: betC, roundId: id("round") }), (r) => r.status === 201 && bal(r) === expected - 100n);
expected -= 100n;
const r8 = check("8. откат ставки: деньги вернулись", await call("rollback", { session, txId: txC }), (r) => r.status === 201 && r.body?.reversed === true && bal(r) === expected + 100n);
expected += 100n;
check("9. повтор отката: тот же ответ", await call("rollback", { session, txId: txC }), (r) => r.status === 201 && same(r.body, r8.body));

// 10-11. надгробие
const txGhost = id("tx");
check("10. откат неизвестной операции", await call("rollback", { session, txId: txGhost }), (r) => r.status === 201 && r.body?.reversed === false && bal(r) === expected);
check("11. опоздавшая ставка с тем же txId", await call("bet", { session, txId: txGhost, amount: "100", betId: id("bet"), roundId: round }), (r) => r.status === 409 && code(r, "already_rolled_back"));

// 12. откат отмены списывает обратно, а не зачисляет второй раз
const betD = id("bet"), txCancelD = id("tx");
check("12a. ставка 100", await call("bet", { session, txId: id("tx"), amount: "100", betId: betD, roundId: id("round") }), (r) => r.status === 201);
expected -= 100n;
check("12b. отмена 100", await call("cancel", { session, txId: txCancelD, amount: "100", betId: betD, roundId: round }), (r) => r.status === 201 && bal(r) === expected + 100n);
expected += 100n;
check("12c. откат отмены: минус 100", await call("rollback", { session, txId: txCancelD }), (r) => r.status === 201 && r.body?.reversed === true && bal(r) === expected - 100n);
expected -= 100n;

// 13. откат выигрыша списывает выигрыш
const txWinE = id("tx");
check("13a. выигрыш 150", await call("win", { session, txId: txWinE, amount: "150", betId: id("bet"), roundId: id("round") }), (r) => r.status === 201 && bal(r) === expected + 150n);
expected += 150n;
check("13b. откат выигрыша: минус 150", await call("rollback", { session, txId: txWinE }), (r) => r.status === 201 && r.body?.reversed === true && bal(r) === expected - 150n);
expected -= 150n;

// 14-15. подпись считается по сырому телу
const known = { session, txId: id("tx"), amount: "100", betId: id("bet"), roundId: id("round") };
check("14. лишнее поле, подписано целиком → 400", await call("bet", { ...known, extra: "x" }), (r) => r.status === 400 && code(r, "invalid_request"), "подпись прошла, отбила валидация");
check("15. лишнее поле, подписаны только известные → 401", await call("bet", { ...known, txId: id("tx"), extra: "x" }, { signOver: known }), (r) => r.status === 401 && code(r, "invalid_signature"));

// 16-20. границы и ошибки
check("16. сумма из 31 цифры → 400, не 500", await call("bet", { session, txId: id("tx"), amount: "1" + "0".repeat(30), betId: id("bet"), roundId: id("round") }), (r) => r.status === 400 && code(r, "invalid_request"));
check("17. битый JSON → 400", await call("bet", {}, { raw: "{not json", headers: { "x-api-key": publicKey, "x-sign": "0".repeat(64) } }), (r) => r.status === 400 && code(r, "invalid_request"));
check("18. неверная подпись → 401", await call("bet", { ...known, txId: id("tx") }, { wrongSign: true }), (r) => r.status === 401 && code(r, "invalid_signature"));
check("19. без заголовков → 401", await call("bet", { ...known, txId: id("tx") }, { headers: {} }), (r) => r.status === 401 && code(r, "missing_signature"));
check("20. чужой токен сессии → 404", await call("bet", { ...known, session: "f".repeat(64), txId: id("tx") }), (r) => r.status === 404 && code(r, "unknown_session"));

// 21. пять одинаковых ставок параллельно списывают один раз
const txF = id("tx"), bodyF = { session, txId: txF, amount: "100", betId: id("bet"), roundId: id("round") };
const parallel = await Promise.all(Array.from({ length: 5 }, () => call("bet", bodyF)));
expected -= 100n;
const ids = new Set(parallel.map((r) => r.body?.processedTxId));
check("21. параллельный повтор: один processedTxId", parallel[0], () => parallel.every((r) => r.status === 201) && ids.size === 1, `${parallel.map((r) => r.status).join(",")}`);

// 22. итоговый баланс сходится с ожиданием
check("22. player/info = ожидаемый баланс", await info(), (r) => r.status === 200 && bal(r) === expected, `ожидалось ${expected}`);

await catalogChecks();
summary();
