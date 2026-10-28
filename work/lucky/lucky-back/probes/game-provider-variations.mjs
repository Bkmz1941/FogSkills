// Вариации сверх основного регресса: две живые сессии ОДНОГО игрока на разных играх.
// Вход /tmp/var-input — четыре строки: public_key провайдера, private_key провайдера,
// launch_token сессии A, launch_token сессии B. Ключи и токены не печатает.
// Собрать вход (клиент — тестовый игрок, у которого две открытые сессии):
//   select public_key from game_providers where slug='crash-heroes' and is_active limit 1;
//   select private_key from game_providers where slug='crash-heroes' and is_active limit 1;
//   select launch_token from game_sessions where client_id='<uuid>' and closed_at is null order by created_at desc limit 1;
//   select launch_token from game_sessions where client_id='<uuid>' and closed_at is null order by created_at asc  limit 1;
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
const [publicKey, privateKey, sessA, sessB] = readFileSync("/tmp/var-input", "utf8").trim().split("\n");
const BASE = "https://dev2.api.luckyserver.pro";
const canonical = (o) => JSON.stringify(Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]))).replace(/\//g, "\\/");
async function call(route, body, method = "POST") {
  const path = `/v1/external/game-provider/${route}`;
  const sign = createHmac("sha256", privateKey).update([method, path, canonical({}), canonical(body)].join("\n")).digest("hex");
  const res = await fetch(BASE + path, { method, headers: { "Content-Type": "application/json", "x-api-key": publicKey, "x-sign": sign }, body: JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => null) };
}
const id = (p) => `${p}-${Date.now()}-${Math.floor(Math.random() * 1e4)}`;
const info = (s) => call("player/info", { sessionToken: s, timestamp: Math.floor(Date.now() / 1000) });
const show = (l, r) => console.log(l.padEnd(50), r.status, JSON.stringify(r.body).slice(0, 150));

const a0 = await info(sessA), b0 = await info(sessB);
show("player/info сессия A (Shark Cage)", a0);
show("player/info сессия B (Balloon Fly)", b0);
console.log("  тот же игрок:", a0.body?.playerId === b0.body?.playerId, "| тот же баланс:", a0.body?.balance === b0.body?.balance);

const txB = id("tx"), betB = id("bet"), roundB = id("round");
show("ставка 100 в сессии B", await call("bet", { session: sessB, txId: txB, amount: "100", betId: betB, roundId: roundB }));
const a1 = await info(sessA);
show("player/info сессия A после ставки в B", a1);
console.log("  кошелёк общий:", BigInt(a0.body.balance) - 100n === BigInt(a1.body.balance));

const r = await call("bet", { session: sessA, txId: txB, amount: "100", betId: betB, roundId: roundB });
show("тот же txId, но из сессии A", r);
console.log("  вердикт:", r.status === 409 ? "конфликт идемпотентности" : r.status === 201 ? "вернул сохранённый ответ" : "иное");

const a2 = await info(sessA);
show("итоговый баланс", a2);
console.log("  деньги не ушли дважды:", a1.body.balance === a2.body.balance);
