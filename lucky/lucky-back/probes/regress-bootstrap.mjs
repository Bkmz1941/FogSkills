// Setup of an isolated regression stand on dev or prod. Safe to re-run: every step reuses what exists.
// Usage: LUCKY_ROOT_EMAIL=... LUCKY_ROOT_PASSWORD=... node regress-bootstrap.mjs dev|prod
// Project "Regress" (active, public client key, project admin), provider "Regress Provider" (its own key pair
// and a cabinet account), one approved and active game linked to the project, a player with a cash balance.
// Everything the regression needs lands in ~/.config/lucky-regress/<env>.env (0600). Nothing secret is printed.
import { randomBytes } from "node:crypto";
import { chmodSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const env = process.argv[2];
const API = { local: "http://127.0.0.1:18080", dev: "https://dev2.api.luckyserver.pro", prod: "https://api.luckyserver.pro" }[env];
if (!API) throw new Error("usage: regress-bootstrap.mjs local|dev|prod");
const dir = join(homedir(), ".config", "lucky-regress");
const file = join(dir, `${env}.env`);

const secret = () => `Rg-${randomBytes(12).toString("hex")}`;
const list = (payload) => Array.isArray(payload) ? payload : Array.isArray(payload?.data) ? payload.data : [];
async function call(method, path, { token, publicKey, body, allow = [] } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  if (publicKey) headers["X-Public-Key"] = publicKey;
  const res = await fetch(API + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json().catch(() => null);
  if (!res.ok && !allow.includes(res.status)) throw new Error(`${method} ${path} -> ${res.status} ${JSON.stringify(data).slice(0, 300)}`);
  console.log(`${res.ok ? "ok" : "skip"} ${method} ${path} ${res.status}`);
  return data;
}

const root = (await call("POST", "/v1/root/auth/login", { body: { email: process.env.LUCKY_ROOT_EMAIL, password: process.env.LUCKY_ROOT_PASSWORD } })).access_token;

let project = list(await call("GET", "/v1/root/projects", { token: root })).find(row => row.slug === "regress");
project ??= await call("POST", "/v1/root/projects", { token: root, body: {
  name: "Regress", slug: "regress", primary_domain: `regress-${env}.luckyserver.pro`,
  default_currency: "USD", default_locale: "en", supported_currencies: ["USD"], supported_locales: ["en"],
} });
if (project.status !== "active" || project.demo_mode !== true) await call("PATCH", `/v1/root/projects/${project.id}`, { token: root, body: { status: "active", demo_mode: true } });
const clientKey = await call("POST", `/v1/root/projects/${project.id}/client-keys`, { token: root, body: { name: `regress ${new Date().toISOString()}` } });

const adminEmail = `regress-admin-${env}@agg.one`;
const adminPassword = secret();
const existingAdmin = list(await call("GET", `/v1/root/projects/${project.id}/admins`, { token: root })).find(row => row.email === adminEmail);
if (existingAdmin) await call("PATCH", `/v1/root/projects/${project.id}/admins/${existingAdmin.id}/password`, { token: root, body: { password: adminPassword } });
else await call("POST", `/v1/root/projects/${project.id}/admins`, { token: root, body: { name: "Regress admin", email: adminEmail, password: adminPassword } });

let provider = list(await call("GET", "/v1/root/game-providers", { token: root })).find(row => row.slug === "regress-provider");
provider ??= await call("POST", "/v1/root/game-providers", { token: root, body: { slug: "regress-provider", name: "Regress Provider", project_ids: [project.id] } });
await call("POST", `/v1/root/game-providers/${provider.id}/projects`, { token: root, body: { project_ids: [project.id] }, allow: [400, 409] });
const keys = await call("POST", `/v1/root/game-providers/${provider.id}/keys`, { token: root });

const cabinetEmail = `regress-provider-${env}@agg.one`;
const cabinetPassword = secret();
const existingCabinet = list(await call("GET", `/v1/root/game-providers/${provider.id}/admins`, { token: root })).find(row => row.email === cabinetEmail);
if (existingCabinet) await call("PATCH", `/v1/root/game-providers/${provider.id}/admins/${existingCabinet.id}/password`, { token: root, body: { password: cabinetPassword } });
else await call("POST", `/v1/root/game-providers/${provider.id}/admins`, { token: root, body: { name: "Regress provider", email: cabinetEmail, password: cabinetPassword } });

let game = list(await call("GET", `/v1/root/games?provider_id=${provider.id}`, { token: root })).find(row => row.external_id === "regress-game");
game ??= await call("POST", "/v1/root/games", { token: root, body: {
  provider_id: provider.id, external_id: "regress-game", slug: "regress-provider-regress-game", title: "Regress Game", category: "crash",
} });
if (game.provider_status !== "approved") await call("POST", `/v1/root/games/${game.id}/moderation`, { token: root, body: { status: "approved" } });
if (game.is_active !== true) await call("PATCH", `/v1/root/games/${game.id}`, { token: root, body: { is_active: true } });

const admin = (await call("POST", "/v1/project/auth/login", { body: { email: adminEmail, password: adminPassword } })).access_token;
await call("POST", "/v1/project/game-providers", { token: admin, body: { provider_ids: [provider.id] }, allow: [400, 404, 409] });
await call("POST", "/v1/project/games", { token: admin, body: { game_ids: [game.id] }, allow: [400, 404, 409] });
const linkedProvider = list(await call("GET", "/v1/project/game-providers", { token: admin })).find(row => row.id === provider.id);
const linkedGame = list(await call("GET", "/v1/project/games", { token: admin })).find(row => row.id === game.id);
if (!linkedProvider || !linkedGame) throw new Error("the provider or the game is not linked to the project");
const hidden = await call("PATCH", `/v1/project/games/${game.id}`, { token: admin, body: { is_active: false } });
if (hidden.is_active !== false) throw new Error("the regress game is still shown on the storefront");

const playerEmail = `regress-player-${env}-${Date.now()}@agg.one`;
const playerPassword = secret();
const registered = await call("POST", "/v1/auth/register", { publicKey: clientKey.public_key, body: {
  locale: "en", currency: "USD", email: playerEmail, password: playerPassword, password_confirmation: playerPassword,
} });
const playerId = registered.client.id;
await call("POST", `/v1/project/finance/users/${playerId}/transactions`, { token: admin, body: {
  direction: "credit", amount: "1000", currency: "USD", balance_code: "cash", comment: "regress seed",
} });

mkdirSync(dir, { recursive: true, mode: 0o700 });
writeFileSync(file, [
  `LUCKY_API=${API}`,
  `PROJECT_ID=${project.id}`,
  `PUBLIC_KEY=${clientKey.public_key}`,
  `PROVIDER_ID=${provider.id}`,
  `PROVIDER_PUBLIC_KEY=${keys.public_key}`,
  `PROVIDER_PRIVATE_KEY=${keys.private_key}`,
  `GAME_ID=${game.id}`,
  `PROVIDER_PID=${linkedProvider.public_id}`,
  `GAME_PID=${linkedGame.public_id}`,
  `ADMIN_EMAIL=${adminEmail}`,
  `ADMIN_PASSWORD=${adminPassword}`,
  `PLAYER_ID=${playerId}`,
  `PLAYER_EMAIL=${playerEmail}`,
  `PLAYER_PASSWORD=${playerPassword}`,
  `CABINET_EMAIL=${cabinetEmail}`,
  `CABINET_PASSWORD=${cabinetPassword}`,
  "",
].join("\n"), { mode: 0o600 });
chmodSync(file, 0o600);
console.log(`stand ready: ${file}`);
