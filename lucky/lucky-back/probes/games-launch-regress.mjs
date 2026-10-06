// Launch regression of real provider games on the isolated stand: links the given providers' games to the Regress
// project hidden from the storefront, then for every game checks player launch, guest demo and that the game URL opens.
// Usage: node games-launch-regress.mjs dev|prod "<provider name>" ["<provider name>" ...]
// Reads ~/.config/lucky-regress/<env>.env; never prints a secret or a launch URL. Exit code 1 on any failure.
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const [envName, ...providerNames] = process.argv.slice(2);
const cfg = Object.fromEntries(readFileSync(join(homedir(), ".config", "lucky-regress", `${envName}.env`), "utf8")
  .split("\n").filter(Boolean).map(line => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]));
const API = cfg.LUCKY_API;
async function call(method, path, { token, publicKey, body } = {}) {
  const h = {};
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  if (publicKey) h["X-Public-Key"] = publicKey;
  const res = await fetch(API + path, { method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => null) };
}
const rows = r => (Array.isArray(r.body) ? r.body : r.body?.data ?? r.body?.items ?? []);
const player = (await call("POST", "/v1/auth/login", { publicKey: cfg.PUBLIC_KEY, body: { email: cfg.PLAYER_EMAIL, password: cfg.PLAYER_PASSWORD, locale: "en" } })).body?.access_token;
const admin = (await call("POST", "/v1/project/auth/login", { body: { email: cfg.ADMIN_EMAIL, password: cfg.ADMIN_PASSWORD } })).body?.access_token;
if (!player || !admin) throw new Error("stand login failed");

const providerCatalog = rows(await call("GET", "/v1/project/game-providers/catalog", { token: admin })).filter(p => providerNames.includes(p.name));
if (providerCatalog.length) await call("POST", "/v1/project/game-providers", { token: admin, body: { provider_ids: providerCatalog.map(p => p.id) } });
const catalog = rows(await call("GET", "/v1/project/games/catalog", { token: admin }));
const wanted = catalog.filter(g => providerNames.some(n => g.provider === n));
console.log(`catalog rows for ${providerNames.join(", ")}: ${wanted.length}`);
if (wanted.length) await call("POST", "/v1/project/games", { token: admin, body: { game_ids: wanted.map(g => g.id) } });
const linked = rows(await call("GET", "/v1/project/games", { token: admin })).filter(g => wanted.some(w => w.id === g.id));
for (const g of linked.filter(g => g.is_active !== false)) await call("PATCH", `/v1/project/games/${g.id}`, { token: admin, body: { is_active: false } });

const opens = async url => {
  try { const r = await fetch(url, { redirect: "follow", signal: AbortSignal.timeout(20000) }); return r.status; } catch (e) { return `error ${e.cause?.code ?? e.name}`; }
};
let failures = 0;
const results = [];
for (const g of linked) {
  const route = `/v1/core/providers/${g.provider_public_id}/games/${g.public_id}`;
  const launch = await call("POST", `${route}/launch`, { token: player, publicKey: cfg.PUBLIC_KEY });
  let demo = await call("POST", `${route}/demo`, { publicKey: cfg.PUBLIC_KEY });
  while (demo.status === 429) { await new Promise(r => setTimeout(r, 30000)); demo = await call("POST", `${route}/demo`, { publicKey: cfg.PUBLIC_KEY }); }
  const launchUrl = launch.body?.link;
  const demoUrl = demo.body?.link;
  const launchOpen = launchUrl ? await opens(launchUrl) : "-";
  const demoOpen = demoUrl ? await opens(demoUrl) : "-";
  const ok = launch.status === 201 && Boolean(launchUrl) && launchOpen === 200;
  const demoOk = demo.status === 201 && Boolean(demoUrl) && demoOpen === 200;
  if (!ok || !demoOk) failures++;
  results.push({ game: g.title, provider: g.provider, launch: `${launch.status}${launchUrl ? "" : ` ${launch.body?.code ?? (launch.body?.unavailable ? "unavailable" : "no url")}`} → ${launchOpen}`, demo: `${demo.status}${demoUrl ? "" : ` ${demo.body?.code ?? (demo.body?.unavailable ? "unavailable" : "no url")}`} → ${demoOpen}` });
  console.log(`${ok && demoOk ? "PASS" : "FAIL"} ${g.provider} / ${g.title}  launch ${results.at(-1).launch}  demo ${results.at(-1).demo}`);
}
console.log(`\n${linked.length - failures}/${linked.length} games pass`);
process.exit(failures ? 1 : 0);
