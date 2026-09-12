// Регресс каталога и модерации игр провайдера против живого стенда.
// Запуск: node provider-catalog-regress.mjs [/tmp/catalog-input]
// Вход — три строки: public_key провайдера, private_key провайдера, Bearer рут-админа.
// Третья строка необязательна: без неё гоняется только провайдерская половина,
// а проверки модерации и удаления пропускаются (рут нужен именно для них).
// PROVIDER_ID — uuid провайдера (нужен для рутовых проверок каталога проекта).
// PLAYED_GAME_ID — необязательный: id игры с игровыми сессиями, проверяет удаление сыгранной.
// LUCKY_API переопределяет базовый URL (по умолчанию локальный стенд).
// Скрипт заводит собственные игры regress-* и убирает их за собой. Ключи не печатает.
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";

const [publicKey, privateKey, rootToken] = readFileSync(process.argv[2] ?? "/tmp/catalog-input", "utf8").trim().split("\n");
const BASE = process.env.LUCKY_API ?? "http://localhost:18080";
const PROVIDER_ID = process.env.PROVIDER_ID ?? "";
const PLAYED_GAME_ID = process.env.PLAYED_GAME_ID ?? "";

const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
const sign = (method, path, body) => createHmac("sha256", privateKey).update([method, path, canonical({}), canonical(body)].join("\n")).digest("hex");

/** Запрос от имени провайдера: подпись считается по методу, пути и телу. */
async function provider(route, body, opts = {}) {
  const method = opts.method ?? "POST";
  const path = `/v1/external/game-provider/${route}`;
  // Без тела не шлём и content-type: Fastify отбивает пустое тело при application/json.
  const headers = { "x-api-key": publicKey, "x-sign": sign(method, path, body ?? {}) };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => null) };
}

/** Запрос от имени рута. */
async function root(path, { method = "GET", body } = {}) {
  const headers = { Authorization: `Bearer ${rootToken}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}/v1${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => null) };
}

const results = [];
function check(label, r, ok, note = "") {
  const pass = ok(r);
  results.push({ pass, label });
  console.log(`${pass ? "PASS" : "FAIL"} ${label.padEnd(52)} ${r.status} ${JSON.stringify(r.body ?? null).slice(0, 110)}${note ? "  // " + note : ""}`);
  return r;
}
const code = (r, c) => r.body?.error?.code === c;
const listed = async (gameId) => (await provider("games", undefined, { method: "GET" })).body?.games?.find((g) => g.id === gameId);

const stamp = `${Date.now()}-${Math.floor(Math.random() * 1e4)}`;
const item = (n) => ({
  providerId: `regress-${stamp}-${n}`,
  sys_name: `regress_${stamp}_${n}`,
  name: `Regress Probe ${n}`,
  type: "crash",
  cover_url: "https://dev.api.crash-heroes.com/storage/games/covers/balloon-fly-site.png",
});

async function run() {
  // --- загрузка каталога ---------------------------------------------------
  const first = item(1);
  check("01 upload: новая игра принята", await provider("games", { games: [first] }), (r) => r.status === 201);

  const created = await listed(await ourId(first.providerId));
  check("02 upload: приезжает pending и выключенной", { status: 200, body: created },
    (r) => r.body?.status === "pending" && r.body?.is_active === false, "гейт: провайдер не решает, что увидит проект");

  check("03 upload: повтор обновляет, статус не трогает", await provider("games", { games: [{ ...first, name: "Regress Probe 1b" }] }), (r) => r.status === 201);
  check("03a upload: имя обновилось, статус прежний", { status: 200, body: await listed(created.id) },
    (r) => r.body?.name === "Regress Probe 1b" && r.body?.status === "pending");

  check("04 upload: категория провайдера вместо нашей → 400", await provider("games", { games: [{ ...item(2), type: "crash-games" }] }),
    (r) => r.status === 400 && code(r, "invalid_request"));
  check("05 upload: без cover_url → 400", await provider("games", { games: [(({ cover_url, ...rest }) => rest)(item(3))] }),
    (r) => r.status === 400 && code(r, "invalid_request"));
  check("06 upload: два одинаковых providerId в одном теле → 400", await provider("games", { games: [item(4), { ...item(4) }] }),
    (r) => r.status === 400 && code(r, "invalid_request"));
  check("07 upload: пустой список → 400", await provider("games", { games: [] }), (r) => r.status === 400 && code(r, "invalid_request"));

  // --- гейт до одобрения ---------------------------------------------------
  check("08 gate: провайдерского выключателя больше нет", await provider(`games/${created.id}`, { is_active: true }, { method: "PATCH" }),
    (r) => r.status === 404, "PATCH games/{id} удалён 11.09: is_active целиком наш");
  if (PROVIDER_ID && rootToken) {
    check("10 gate: проекту неодобренная игра недоступна", await root(`/root/projects/${await anyProject()}/games`),
      (r) => !(r.body?.data ?? []).some((g) => g.id === created.id && g.is_available), "is_available считает гейт");
  }

  // --- модерация -----------------------------------------------------------
  if (rootToken) {
  check("11 moderate: approve не включает игру сам", await root(`/root/games/${created.id}/moderation`, { method: "POST", body: { status: "approved" } }),
    (r) => r.status === 201 && r.body?.provider_status === "approved" && r.body?.is_active === false, "одобрение и включение — два разных решения");
  check("12 gate: включает рут", await root(`/root/games/${created.id}`, { method: "PATCH", body: { is_active: true } }), (r) => r.status === 200);
  check("12a gate: и игра действительно включилась", { status: 200, body: await listed(created.id) },
    (r) => r.body?.is_active === true && r.body?.status === "approved");
  check("13 moderate: decline гасит игру", await root(`/root/games/${created.id}/moderation`, { method: "POST", body: { status: "declined" } }),
    (r) => r.status === 201 && r.body?.provider_status === "declined" && r.body?.is_active === false);
  check("14 gate: отклонённую не включить и руту", await root(`/root/games/${created.id}`, { method: "PATCH", body: { is_active: true } }),
    (r) => r.status === 409, "дыра, найденная 11.09");
  check("15 moderate: передумать можно, decline → approve", await root(`/root/games/${created.id}/moderation`, { method: "POST", body: { status: "approved" } }),
    (r) => r.status === 201 && r.body?.provider_status === "approved");
  check("16 moderate: неизвестный статус → 400", await root(`/root/games/${created.id}/moderation`, { method: "POST", body: { status: "maybe" } }), (r) => r.status === 400);
  }

  // --- отзыв ---------------------------------------------------------------
  const switchBeforeRevoke = (await listed(created.id))?.is_active;
  check("17 revoke: игра остаётся, статус revoked", await provider(`games/${created.id}/revoke`, undefined), (r) => r.status === 200);
  check("17a revoke: строка на месте, выключатель не тронут", { status: 200, body: await listed(created.id) },
    (r) => r.body?.status === "revoked" && r.body?.is_active === switchBeforeRevoke,
    "с 11.09 отзыв только помечает: ни выключателя, ни размещений, ни плиток он не трогает");
  check("18 revoke: повтор не ошибка", await provider(`games/${created.id}/revoke`, undefined), (r) => r.status === 200);
  check("18a revoke: пустой объект вместо пустого тела тоже принимается", await provider(`games/${created.id}/revoke`, {}), (r) => r.status === 200,
    "клиент, который всегда шлёт application/json, должен слать {}");
  check("19 revoke: чужой или несуществующий id → 404", await provider("games/00000000-0000-4000-8000-000000000000/revoke", undefined),
    (r) => r.status === 404 && code(r, "unknown_game"));
  if (PROVIDER_ID && rootToken)
    check("20 gate: отозванная игра проекту недоступна", await root(`/root/projects/${await anyProject()}/games`),
      (r) => !(r.body?.data ?? []).some((g) => g.id === created.id && g.is_available), "гейт держит, даже когда выключатель открыт");
  if (rootToken) check("21 moderate: отозванную модерировать нельзя", await root(`/root/games/${created.id}/moderation`, { method: "POST", body: { status: "approved" } }), (r) => r.status === 409);
  check("22 revoke: перезаливка принимается", await provider("games", { games: [{ ...first, name: "Regress Probe 1c" }] }), (r) => r.status === 201);
  check("22a revoke: поля обновились, статус остался revoked", { status: 200, body: await listed(created.id) },
    (r) => r.body?.status === "revoked" && r.body?.name === "Regress Probe 1c",
    "с 11.09 sync не трогает модерацию: спрятать игру перезаливкой нельзя");

  // --- удаление рутом ------------------------------------------------------
  if (!rootToken) {
    console.log("\n— рут-токена нет: модерация и удаление пропущены, проба остаётся отозванной —");
    await parkProbe(created.id);
    return summary();
  }
  check("23 delete: рут удаляет игру", await root(`/root/games/${created.id}`, { method: "DELETE" }), (r) => r.status === 204);
  check("23a delete: игра пропала из каталога провайдера", { status: 200, body: (await listed(created.id)) ?? null }, (r) => r.body === null);
  check("24 delete: повторное удаление → 404", await root(`/root/games/${created.id}`, { method: "DELETE" }), (r) => r.status === 404);

  if (PLAYED_GAME_ID) {
    check("25 delete: сыгранная игра удаляется вместе с сессиями", await root(`/root/games/${PLAYED_GAME_ID}`, { method: "DELETE" }),
      (r) => r.status === 204, "FK_game_sessions_game стоит RESTRICT — баг 11.09");
  }

  await cleanup();
  summary();
}

/** Наш uuid по id провайдера: листинг отдаёт оба. */
async function ourId(providerId) {
  const list = await provider("games", undefined, { method: "GET" });
  return list.body?.games?.find((g) => g.providerId === providerId)?.id;
}

/** Без рута удалить нельзя — оставляем пробу отозванной и говорим об этом вслух. */
async function parkProbe(gameId) {
  await provider(`games/${gameId}/revoke`, undefined);
  console.log(`оставлена отозванная проба: ${gameId} — удалить рутом, когда будет токен`);
}

async function anyProject() {
  const r = await root("/root/projects");
  return (r.body?.data ?? r.body ?? [])[0]?.id ?? "";
}

/**
 * Убираем за собой всё, что завели этим прогоном, и НЕ молчим о неудаче:
 * первый прогон 11.09 тихо оставил игру, потому что уборка падала тем же
 * способом, что и проверки.
 */
async function cleanup() {
  if (!rootToken) return;
  const list = await provider("games", undefined, { method: "GET" });
  const mine = (list.body?.games ?? []).filter((g) => String(g.providerId).startsWith(`regress-${stamp}`));
  const stuck = [];
  for (const game of mine) {
    const res = await root(`/root/games/${game.id}`, { method: "DELETE" });
    if (res.status !== 204) stuck.push(`${game.id} (${res.status})`);
  }
  if (mine.length) console.log(`\nубрано за собой: ${mine.length - stuck.length}/${mine.length}`);
  if (stuck.length) {
    console.log(`НЕ УБРАНО: ${stuck.join(", ")}`);
    results.push({ pass: false, label: "cleanup: остались игры прогона" });
  }
}

function summary() {
  const failed = results.filter((r) => !r.pass);
  console.log(`\n${results.length - failed.length}/${results.length} PASS${failed.length ? `, ${failed.length} FAIL` : ""}`);
  for (const f of failed) console.log(`  FAIL ${f.label}`);
  process.exit(failed.length ? 1 : 0);
}

run().catch((error) => {
  console.error("прогон упал:", error?.message ?? error);
  process.exit(1);
});
