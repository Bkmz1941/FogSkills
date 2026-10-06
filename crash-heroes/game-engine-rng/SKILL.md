---
name: game-engine-rng
description: «game-engine-rng» — новый движок под новую игру Crash Heroes, репо ~/Documents/Work/CrashGames/game-engine-rng (gitlab.agg.one crash-heroes/backend/game-engine-rng). Node 24 + TypeScript без сборки, ws, Docker; слои config / services / web / resources (domain — по мере надобности) как в интеграции Lucky. Активируй ВСЕГДА при работе с этим репо и по «новый движок», «новая игра», «rng-движок», «game-engine-rng». Серверы, API, старые движки и seamless — скил crash-games, он нужен рядом.
---

# game-engine-rng — движок новой игры

Старт 2026-09-18. Отдельный проект, **не часть** монорепы старых движков
(`crash-heroes-backend-game-engine`). Всё про серверы, Laravel API, админку,
seamless-интеграцию и старые движки — в скиле `crash-games`; здесь только этот репо.

| | |
|---|---|
| Локально | `~/Documents/Work/CrashGames/game-engine-rng` |
| Remote | `git@gitlab.agg.one:crash-heroes/backend/game-engine-rng.git` |
| Ветки | **`dev`** (отслеживает `origin/dev`) — рабочая; `main` — `0a78bcd` Initial commit от GitLab. Первый коммит ядра — `64ae969 project init` (Илья, 18.09 15:05) |
| CI | нет |
| Деплой | **образ в Docker Hub с версией, на сервер — руками**, runbook — раздел «Деплой»; dev развёрнут 18.09 |

**Состояние на 23.09:** `dev` == `origin/dev` == **`6013e54`** «Rename get_coeffs to coefficients,
flatten the state reply and release 0.1.11» (см. журнал 23.09); до него **`59aa095`** «Call the losing round result
lose instead of crash and release 0.1.10»; до него `bef3de8` и `9ba4a5f`/`b5bb8c3` (попап
истории), `93eb3b3` (в истории только коэффициент), `628138e` (0.1.9), `e027489`; до него `4607ee7` (команды истории) и `e82d444`
(переименование игра/раунд). На dev выкачен образ **0.1.11** (23.09), там же api-core `1cef263` и
админка `fbd56c2` — всё с новым неймингом (см. «Нейминг: игра и раунд») и с инфой по броску.

## Игра — «Хоккеист»

**Главный источник — ТЗ «Dice RNG для Crash Games»** (Google Doc, конспект в
`DESIGN.md`): бросок двух d6, проигрыш **только 1-1 / 3-3 / 5-5**, RTP 97 %, 49
раундов, коэффициенты `0.97 / (11/12)^N`. Макет — визуал; где расходится, прав ТЗ.

Движок пишем под игру **«Хоккеист»**: **верхняя линия** макета «Хоккеист ·
полный флоу» (нижняя — другой скин того же флоу, не наш). Полное описание,
экраны, нестыковки макета и выводы для движка — **`DESIGN.md`** рядом с этим
файлом; нарезка экранов — `design/screens/*.jpg`, оригинал SVG —
`design/hockey-flow.svg` (только на T714, не в git).

Коротко: игрок ставит сумму и жмёт Play → бросают два кубика → пока не выпал
дубль, раунды выигрываются и кф растёт (1.06 → 1.15 → 1.25 в макете) → игрок
либо «Забрать», либо бросает дальше; дубль — ставка проиграна. **У каждого
игрока своя игра**, а не общий раунд на всех, как у старых крашей.

## Правила

- **Коммит и пуш — только по прямой команде Ильи** в текущем разговоре, каждая
  команда = один коммит. Сделал работу → оставил в дереве → сказал, что готово.
- **README — только команды** (Илья 18.09 сам срезал его до блока команд).
  Протокол, структуру, правила TypeScript в README не дописывать — они здесь.
- Коммиты как во всех репо Crash Heroes: **английский, одна строка-заголовок,
  без тела, без `Co-Authored-By` и любых упоминаний ИИ.**
- IDE Ильи (WebStorm) **сама добавляет новые файлы в индекс**. Если создавал и
  удалял файлы — в индексе остаются мёртвые записи (`AD` в `git status`);
  перед тем как отчитаться, выровнять `git add -A` (это не коммит).
- **Временные файлы в `src/` не создавать** — Илья видит их в IDE и спрашивает,
  что это (18.09: `_watch_probe.ts`). Пробы — в scratchpad или правкой-откатом.
- **Комментариев не пишем вообще** (Илья 18.09: «не пишем комменты»). Ни в
  `.ts`, ни в `Dockerfile`, `docker-compose.yml`, `tsconfig.json`, `.env.example`;
  ни doc-комментариев, ни «почему». Объяснения — в README и в этом скиле.
  Сообщения логов и ошибок протокола — по-английски.
- **Типы живут рядом со своим конфигом**, отдельной `web/models/` нет (Илья:
  «HttpHandler унеси в server.config», «message.ts унеси в конфиг сокетов»):
  `HttpHandler` — в `server.config.ts`, `SocketMessage`/`SocketHandler` — в
  `socket.config.ts`. **Типы — внизу файла, после класса** (так их переставил
  Илья). HTTP-конфиг от сокетного не зависит: его ответ — `Record<string, unknown>`.
- Одноразовые константы Илья встраивает по месту (18.09: `SHUTDOWN_GRACE_MS` →
  `3000` прямо в `setTimeout`). Константу заводить, только если значение
  используется больше одного раза.

## Стек и принятые решения (18.09)

| решение | почему |
|---|---|
| **Node 24** (`node:24-alpine`, `engines >=22.18`) | LTS; версия закреплена — у старого движка не была |
| **TypeScript 7 без сборки** | Илья: «давай typescript сразу». Node сам срезает типы на лету (type stripping, без флагов с 22.18). Нет `dist/`, sourcemap-ов и tsx; `tsc --noEmit` только проверяет типы. `typescript` — dev-зависимость, в образ не попадает |
| ESM, `"type": "module"`, алиас `"#src/*": "./src/*"` | как `#src/*.mjs` у старого движка, но **без расширения в шаблоне** — см. грабли №5 |
| `ws` — единственная runtime-зависимость | нативного WebSocket-сервера в Node нет. `dotenv`/`axios`/`uuid` старого движка заменяются на `--env-file-if-exists`, `fetch`, `crypto.randomUUID` |
| **Контейнер сразу** (Dockerfile + compose) | Илья: «давай контейнер сразу» |
| **Слои `domain / services / web / resources`** | Илья: «как в котлине или лаки интеграции» (`lucky-api/src/modules/integrations`) |
| Тесты — `node:test`, `*.spec.ts` в `src/resources/tests/` | как в Lucky (`resources/tests/`, `.spec.ts`); без jest/vitest |
| HTTP `/health` и WebSocket на одном порту | healthcheck контейнера и будущий `smoke.sh` без вебсокет-клиента; один порт — одна `location` в nginx |

**Что такое `.mjs`** (Илья спрашивал): расширение «этот файл — ES-модуль»
(`import`/`export`), в отличие от `.cjs`/CommonJS (`require`). Нужно было старому
движку, потому что у него `"type": "commonjs"`. Здесь `"type": "module"` + `.ts`,
так что `.mjs` не используется.

### Правила TypeScript без сборки

Node только **срезает** типы, ничего не трансформирует. Отсюда
(`erasableSyntaxOnly` + `verbatimModuleSyntax` в `tsconfig.json` ловят всё это на
`npm run typecheck`):

- в импортах **обязательно расширение `.ts`**: `import ServerConfig from '#src/config/server.config.ts'`;
- типы — только через `import type {...}`, иначе рантайм ищет несуществующий экспорт;
- **нельзя** `enum`, `namespace`, `constructor(private x: T)` — вместо enum объект
  `as const` (см. `Logger.LEVELS`), поля класса объявляются явно;

## Команды

```bash
cp .env.example .env            # один раз

docker compose up -d --build    # собрать и запустить; сервис называется crash-engine-rng
docker compose logs -f
docker compose down
docker compose watch            # правка src/ → sync + рестарт в контейнере

npm ci
npm run dev                     # локально, с --watch
npm start
npm test                        # node --test "src/resources/tests/**/*.spec.ts"
npm run typecheck               # tsc --noEmit

curl http://127.0.0.1:3100/health
npx wscat -c ws://127.0.0.1:3100      # {"type":"ping"}
```

Окружение (`src/config/core.config.ts`, проверяется на старте — кривой `.env` роняет процесс
сразу): **`GAME_UUID`** (обязателен, см. «Игра по uuid»), `HOST` (`127.0.0.1`; в контейнере принудительно `0.0.0.0`), `PORT`
(`3100` — **заглушка**, по конвенции Crash Heroes порт = `3000 + GAME_ID`, dev
`4000 +`), `LOG_LEVEL` (`info`). Сервис в compose — **`crash-engine-rng`** (переименовал Илья; для
`docker compose ps -q crash-engine-rng`, `logs`, `exec`). Compose требует `.env` (`env_file: .env`, без
`required: false`) — без него `up` падает сразу, а не контейнер после старта.
Compose публикует порт только на `127.0.0.1` — наружу, как у старых движков,
должен смотреть nginx.

## Локальный запуск вместе с API и админкой

Цель — в админке указать адрес движка и увидеть, жив ли он (Илья 18.09).

**Как устроено у Ильи локально:** api-core в докере по
`crash-heroes-backend-api-core/docker-compose.dev.yml` (контейнер `…-mini_backend-1`,
`:8000`, сеть `crash-heroes-backend-api-core_minigames_net`, база `minigames_db`,
БД `crashgames`); админка — `npm run dev` на `:5173`, в `.env.local` (правка не
закоммичена) `VITE_API_URL=http://localhost:8000/api`.

**Движок сидит в сети API.** В `docker-compose.yml` сеть `minigames_net` объявлена
`external: true`, `name: crash-heroes-backend-api-core_minigames_net`. Илья сначала
добавил просто `networks: minigames_net`, но compose приклеивает имя проекта —
получилась отдельная `game-engine-rng_minigames_net`, и API движок не видел.
Следствие: **api-core надо поднять первым**, иначе `up` движка упадёт «network
not found».

**Адрес движка в админке — `http://crash-engine-rng:3100`** (имя сервиса compose).
`http://127.0.0.1:3100` не годится: изнутри контейнера API это сам контейнер API.

**Порядок:**
1. `cd crash-heroes-backend-api-core && docker compose -f docker-compose.dev.yml up -d`
2. в движке `.env`: `GAME_UUID` = `games.uuid` игры в **этой** базе
   (`SELECT uuid FROM games WHERE sys_name='test_rng'`); сейчас `a2c68a94-…`, id 18;
3. `docker compose up -d --build` в `game-engine-rng`;
4. админка → тип игры «Crash RNG» в селекторе → раздел **«RNG-игры»**
   (`/rng/games`) → у игры «Адрес движка» → колонка живости.

**Проверки по шагам (18.09 все прошли):**
```bash
curl -s http://127.0.0.1:3100/health                                   # с хоста
docker exec crash-heroes-backend-api-core-mini_backend-1 \
  curl -s -m 3 http://crash-engine-rng:3100/health                    # из контейнера API
docker exec crash-heroes-backend-api-core-mini_backend-1 php artisan tinker --execute \
  'echo json_encode(app(App\Services\Rng\RngEngineHealthService::class)->check(App\Models\Game::where("uuid","<uuid>")->firstOrFail()));'
# → {"alive":true,"reason":null,"http_status":200,"latency_ms":6,"uptime":10}
```

**Контракт `/health` с API** (`App\Services\Rng\RngEngineHealthService`):
`GET {engine_url}/health`, таймаут 2 с; живой = `200` + `{status:'ok', uptime:<int>}`.
Причины отказа, как их показывает админка: `not_configured` «Адрес не задан»,
`unreachable` «Не отвечает», `http_error` «Ошибка HTTP», `bad_response` «Некорректный
ответ». **Поля `/health` не переименовывать без правки API**; `uptime` должен быть целым.
**`game_uuid` из `/health` убран 21.09** (движок `41da07c`, api-core `b523841` «Stop
checking the game uuid in the RNG engine health response») — сверки игры по ответу
`/health` больше нет, причина `game_uuid_mismatch` не возвращается (мёртвый ярлык остался
в админке, `RngGameHealthCell.tsx`). Порядок правки был обратный правилу «сначала
принимающая сторона»: движок уехал первым, поэтому между 21.09 10:17 и выкаткой
`b523841` живость на деве показала бы `game_uuid_mismatch`.

API-сторона (всё в рабочих деревьях, не закоммичено, делалось параллельно в
другой сессии): api-core — `routes/api/v2/admin/rng.php` (`GET /v2/admin/rng/games`,
`PATCH …/{uuid}` с `engine_url`, `GET …/{uuid}/health`, только superadmin),
миграция `2026_09_18_100002_add_engine_url_to_games_table`; admin-panel —
`src/pages/rng-games/`, пункт меню «RNG-игры» виден, когда в селекторе выбран
тип `crash-rng`.

## Деплой — как делаем (runbook, делать ровно так)

Решение Ильи 18.09: «деплой движка через докерхаб и руками будем обновлять»;
«как мы делаем деплой опиши в скиле и тоже так будешь делать». Образец — Olimp
segmenter (`arcanegaming/olimp-segmentation`, `docker build --platform
linux/amd64 … && docker push`, на сервере `docker compose pull`).

**Разрешения.** Деплой (пуш образа, правки на сервере, перезапуск) — **только по
команде Ильи в текущем разговоре**, как коммит и пуш в git. «Сделай деплой на
dev» не означает прод. Прод ещё ни разу не разворачивали — сначала проверить там
Docker, группу `docker`, логин в Docker Hub, свободный порт (см. «Серверы»).

### Что где

| что | где |
|---|---|
| образ | `arcanegaming/crash-engine-rng:<версия>` в Docker Hub, **репо приватный** |
| версия | `version` в `package.json` (выложено: `0.1.0`, `0.1.1` — 18.09, `0.1.2`–`0.1.5` — 21.09, `0.1.6`–`0.1.10` — 22.09, `0.1.11` — 23.09, **`0.1.12`** — 24.09 (`win` с 0 на проигрыш), dev) |
| серверный compose | `docker-compose.server.yml` в репо → на сервере `~/crashgames/crash-engine-rng/docker-compose.yml` |
| серверный `.env` | `~/crashgames/crash-engine-rng/.env` (chmod 600): `ENGINE_VERSION`, `GAME_UUID`, `LOG_LEVEL`, `DB_HOST/PORT/DATABASE/USERNAME/PASSWORD`, `DICE_STREAM_URL` — **только на сервере**, в git нет |
| сеть | **`network_mode: host`** с 0.1.1 (MySQL и dicestream — на `127.0.0.1` хоста); `HOST: 127.0.0.1` в compose — иначе 3100 открылся бы наружу; `ports:` убран |
| контейнер | **`crash-engine-rng-1`** (`container_name`), порт `127.0.0.1:3100` |
| адрес в админке | `http://127.0.0.1:3100` (Octane на хосте; локально — `http://crash-engine-rng:3100`) |

**Правила:** `latest` не используем никогда (Илья: «latest не ок, надо прям
версию писать»); выложенную версию **не перезаливать** тем же тегом — любая
правка = новая версия; compose без `ENGINE_VERSION` не стартует
(`${ENGINE_VERSION:?…}`). Серверный compose: **`restart: always`** (Илья: «чтобы перезапускался сам
всегда»; поднимается и после падения процесса, и после ребута, даже если до
этого остановлен руками), ротация логов `json-file 10m × 3` (авария 15.08 — логи
съели диск), без внешней сети. Docker **не** перезапускает `unhealthy`-контейнер
(только упавший процесс); процесс сам выходит на `uncaughtException`, а от
зависания защитил бы только `autoheal` — не добавлен. Проверено локально:
`kill -9` процесса внутри → `RestartCount 1`, снова `healthy`.

### Шаги выкладки

```bash
# 0. локально, в ~/Documents/Work/CrashGames/game-engine-rng: тесты и типы зелёные
timeout 60 npm test && npx tsc --noEmit

# 1. новая версия
npm version patch --no-git-tag-version          # 0.1.1 → 0.1.2; package.json коммитить по команде
V=$(node -p "require('./package.json').version")

# 2. образ в Docker Hub и проверка, что он там
docker build --platform linux/amd64 -t arcanegaming/crash-engine-rng:$V .
docker push arcanegaming/crash-engine-rng:$V
docker manifest inspect arcanegaming/crash-engine-rng:$V > /dev/null && echo ok

# 3. только если менялся docker-compose.server.yml: сначала diff с серверной копией, потом залить
ssh admin@167.233.24.119 'cat ~/crashgames/crash-engine-rng/docker-compose.yml' | diff - docker-compose.server.yml
scp docker-compose.server.yml admin@167.233.24.119:/home/admin/crashgames/crash-engine-rng/docker-compose.yml

# 4. на сервере: сменить версию, подтянуть, пересоздать
ssh admin@167.233.24.119
cd ~/crashgames/crash-engine-rng
sed -i "s/^ENGINE_VERSION=.*/ENGINE_VERSION=$V/" .env      # $V подставить руками
docker compose pull && docker compose up -d

# 5. проверка
docker ps --filter name=crash-engine-rng-1                # (healthy) через ~10 с
curl -s http://127.0.0.1:3100/health                      # status ok + uptime
docker logs --tail 5 crash-engine-rng-1                   # Started | {… "game":"<uuid>"}
# и в админке «RNG-игры» → «Работает», либо тем же сервисом, что зовёт админка:
cd ~/crashgames/minigames-admin-back && php artisan tinker --execute \
  'echo json_encode(app(App\Services\Rng\RngEngineHealthService::class)->check(App\Models\Game::where("sys_name","test_rng")->firstOrFail()));'
```

**Откат:** вернуть прежнюю `ENGINE_VERSION` в `.env` → `docker compose up -d`.
**Простой** при `up -d` — около секунды (контейнер пересоздаётся).

### Клиент — по WebSocket прямо в движок, как краши, путь = uuid игры

**Итоговое решение Ильи 18.09: «сделай так же [как краши] для новой игры, только
через uuid».** Клиент игры держит WebSocket с движком через общий nginx `server.`
— так же, как 13 старых крашей, но путь — **`games.uuid`**, а не `GAME_ID`:

| кто | адрес |
|---|---|
| клиент игры (dev) | **`wss://dev.server.crash-heroes.com/a2c69d5c-074d-4574-9262-58fce37fba72`** |
| клиент игры (прод) | `wss://server.crash-heroes.com/<uuid игры в базе прода>` — не заведено |
| API → движок (живость в админке) | `http://127.0.0.1:3100` в `games.engine_url` — внутренний, как был |

- **nginx dev**: в общий `/etc/nginx/conf.d/dev.server.crashgames.app.conf` (там же
  `/1…/17` старых движков) добавлен `location /<uuid>` (+ `rewrite`, см. ниже) →
  `proxy_pass http://127.0.0.1:3100` с теми же заголовками, что у соседей (`X-Forwarded-For`,
  `Host`, `Upgrade`/`Connection "upgrade"`, `proxy_read_timeout 86400`), вставлен
  перед `listen 443 ssl`. Бэкап до правки —
  `~/deploy-backups/dev.server.crashgames.app.conf.20260918-140808`. Новых DNS и
  сертификатов не нужно — домен и сертификат общие (`dev.api…`, SAN `dev.server…`).
- Проверено снаружи 18.09: WS по uuid → `ping` → `pong`; старая игра `/1` отдаёт
  `rates` как раньше.
- **Префикс `/<uuid>` срезается** первой строкой блока: `rewrite ^/<uuid>/?(.*)$ /$1
  break;` → `/<uuid>/health` доходит до движка как `/health`, `/<uuid>` — как `/`
  (WS). Без него (первая версия блока) снаружи `…/<uuid>/health` давал 404 от движка:
  `proxy_pass` без URI передаёт путь как есть, а роуты движка точные. У старых
  движков HTTP нет — им было всё равно. Второй бэкап до правки —
  `~/deploy-backups/dev.server.crashgames.app.conf.20260918-141714`.
- Снаружи работает (18.09): `curl https://dev.server.crash-heroes.com/<uuid>/health`
  → 200 с `game_uuid`; неизвестный путь → 404 движка; WS и на `/<uuid>`, и на
  `/<uuid>/` → `pong`; старая `/1` → 101. **Новые HTTP-роуты движка снаружи
  доступны как `https://dev.server.crash-heroes.com/<uuid>/<путь>`.** CORS нет —
  понадобится, если браузер со страницы игры будет ходить в HTTP движка.
- **Новая игра / новая база** = свой uuid → свой `location`. Uuid у каждой базы
  свой (сидер его не фиксирует), поэтому на проде путь будет другим.
- **Следствие:** как у старых движков, проверку игрока и деньги **делает движок
  через api-core** (у старых — `GET server/games/{id}/player?token=`, `POST
  server/round`). Для «Хоккеиста» эти эндпоинты ещё предстоит спроектировать.
  Клиентские сообщения — по модели `{type, data}` через `SocketConfig`.

**История решения 18.09** (чтобы не ходить по кругу): поддомен
`dev.rng.crash-heroes.com` + CORS → откат; «через API, как слоты» → принято, но
после разбора, как устроены краши, Илья выбрал WS как у крашей, путь по uuid.

### Первый запуск на новом сервере

1. Docker и Compose есть (`docker compose version`); `admin` в группе `docker`
   (`sudo usermod -aG docker admin`, перезайти) — тогда всё без `sudo`.
2. `docker login -u dockerhub@agg.one` **от `admin`** с токеном **Read-only**
   (не «Public Repo Read-only» — см. грабли ниже); проверка —
   `docker manifest inspect arcanegaming/crash-engine-rng:<версия>`.
3. В базе сервера есть тип `crash-rng` и игра (на dev заведены 18.09 точечно —
   **`DefaultGameTypesSeeder` на dev/проде не запускать**, сбрасывает настройки
   крашей; см. скил `crash-games`). `GAME_UUID` — `games.uuid` **этой** базы:
   `php artisan tinker --execute 'echo App\Models\Game::where("sys_name","test_rng")->value("uuid");'`.
4. `mkdir -p ~/crashgames/crash-engine-rng`, залить compose (шаг 3), создать `.env`
   с `ENGINE_VERSION`, `GAME_UUID`, `LOG_LEVEL=info`; порт 3100 свободен
   (`ss -ltn | grep :3100`).
5. `docker compose pull && docker compose up -d`, проверка (шаг 5), в админке
   адрес `http://127.0.0.1:3100`.

### Серверы

- **dev 167.233.24.119 — 0.1.11 с 23.09 ~10:39 UTC** (22.09 — 0.1.6–0.1.10, 21.09 — 0.1.2 и 0.1.5).
  Docker 26.1.5 (Debian 13, x86_64), Compose 2.26.1; `admin` в группе `docker`; логин Docker
  Hub — в `/home/admin/.docker/config.json` (токен Read-only). `.env`: `ENGINE_VERSION=0.1.2`,
  `GAME_UUID=a2c69d5c-074d-4574-9262-58fce37fba72` (`test_rng` в базе dev), `DB_*` —
  **скопированы из `.env` api-core** (`127.0.0.1:3306`, `dev_minigames_db`, юзер
  `dev_minigames_user` — отдельного MySQL-юзера движку **не заводили**, TODO),
  `DICE_STREAM_URL=ws://127.0.0.1:18080/ws/events` (dicestream — docker `rng-dice-app-1` на
  том же сервере). Контейнер `healthy`, `restart: always`, `network_mode: host`, 3100 — только
  `127.0.0.1`. Бэкапы до правки: `~/deploy-backups/crash-engine-rng.{docker-compose.yml,env}.20260918-174228`.
  Проверено: `/health` снаружи 200; WS с чужой сессией → `Session not found` / 4401 (БД
  читается); лог `Dice Stream connected`; админка `RngEngineHealthService` → `alive: true`
  (72 мс); `smoke.sh` dev — зелёный. **Полный раунд на dev не прогоняли:** сессия нужна
  настоящая — запуск из Lucky dev (иначе `/user/info` у Lucky не узнает `launch_token`).
- **прод 78.141.216.99 — 0.1.12 с 28.09 ~09:16 UTC.** Docker поставлен 28.09 (`docker.io` 26.1.5 +
  `docker-compose` из Debian 13, `admin` в группе `docker`); **логина в Docker Hub на проде нет** — образ
  перенесён `ssh dev 'docker save <img>' | ssh prod 'docker load'` (так и обновлять, либо залогиниться).
  Игра в прод-базе заведена точечно: тип `crash-rng` (id 3), игра id 19 «Crash Hockey» `crash_hockey`,
  **uuid тот же, что на dev** (`a2c69d5c-…`), `link https://games.crash-heroes.com/crashhockey` (тестовый UI с
  dev, `dev.server` заменён на `server`), `engine_url http://127.0.0.1:3100`, `settings []` → **в партнёрский
  `GET /api/external/games` не попадает** (`checkSettingsValid` требует `settings.mode`). `.env` —
  `DB_*` из `.env` api-core (`minigames_user`), `DICE_STREAM_URL=wss://dicestream.crash-heroes.com/ws/events`
  (dicestream — Кости, на 167.233.24.119, не трогаем). nginx: `location /<uuid>` в
  `server.crash-heroes.com.conf` перед `/17`, бэкап `~/deploy-backups/server.crash-heroes.com.conf.20260928-091632`.
  Проверено: `healthy`, `Dice Stream connected`, `/health` изнутри и снаружи, `RngEngineHealthService` alive
  18 мс, WS снаружи `Session not found` + 4401, `smoke.sh` прод зелёный по играм.

### Грабли деплоя

- **Токен «Public Repo Read-only» не видит приватные репо.** Логин проходит
  («Login Succeeded»), pull — `denied … may require 'docker login'`. Диагностика
  без раскрытия токена: запросить
  `https://auth.docker.io/token?service=registry.docker.io&scope=repository:<repo>:pull`
  с `Authorization: Basic <auth из config.json>` и напечатать только claim
  `access` из JWT: `[]` — прав нет, `[{actions:[pull]…}]` — есть. 18.09 так и было.
- **`docker login` без `sudo` и `sudo docker compose pull`** — разные пользователи:
  креды у `admin`, pull идёт от root без кредов → `denied`. Лечится группой
  `docker` (или `sudo docker --config /home/admin/.docker …`).
- Анонимный `denied` Docker Hub одинаков для «образа нет» и «репо приватный» —
  проверять залогиненным клиентом.
- Имя контейнера по умолчанию — `<папка>-<сервис>-1` →
  `crash-engine-rng-crash-engine-rng-1`; поэтому `container_name`.

## Профиль и деньги — сделано (18.09; коммит `039aacd` в `dev`, запушен; команды bet/win/cancel и переименование partner → external — в индексе)

**Кошелёк RNG-игрока — заводим, как api-core** (Илья: «копируем поведение пока — пусть
создаётся в момент получения инфы по игроку, если нету»; прежнее «кошельков не
заводим» отменено — без кошелька не записать журнал: `player_external_transactions.wallet_id`
NOT NULL + FK).

- **`profile`** (`web/v1/profile.handler.ts` → `services/profile.service.ts`): сессия + проект
  из БД → `POST projects.api_user_info {session: launch_token}` с подписью, таймаут 2 с
  → `parseUserInfo` (плоский или `data`, обязательны `playerId`, `currency`; `balance` → строка,
  иначе `'0'`). Первый раз (`game_sessions.player_id` пуст): проверка валюты в
  `currencies` (`Currency not supported`), затем под `GET_LOCK('rng-player:<project>:<playerId>')`
  в транзакции — игрок (как `PlayerCreateService::createExternal`: `role regular`,
  `client_type external_project`, `name = external_id = playerId`, `token` uuid…), кошелёк
  валюты (создать с балансом или обновить баланс), активный кошелёк (`is_active = (id = ?)`),
  `players.game_currency`, `can_play_for_money = 1`, привязка сессии (`player_id`,
  `external_player_id`, `currency`). Повторно — обновить баланс зеркала. Ответ `{balance,
  currency}`. Ошибки клиенту — `SocketError` (`{type:'error', data:{request:'profile',
  message}}`, соединение живо): `Profile unavailable` (нет адреса / сеть / не 2xx / битый
  ответ — причина в WARN), `Currency not supported`.
- **`SocketConfig`**: обработчик получает второй аргумент `{sessionId}`; `SocketError` из
  обработчика → ошибка клиенту своим текстом, прочие исключения → `Internal error` + ERROR.
- **`services/external.service.ts`**: `signRequest` = `ProjectSignHelper::signRequest` байт в
  байт (тест с эталоном из PHP, в т.ч. слэш, кириллица, query не входит), `post()` на `fetch`
  с таймаутом.
- **`services/wallet.service.ts`** — копия `PartnerWalletService` + `SeamlessWalletGateway` +
  `PartnerOperationRetryJob`:
  - `bet(sessionId, amountMinor, betId, roundId, betNumber)` → `accepted` (зеркало
    баланса) / `declined` (4xx) / `not_confirmed` (сеть/5xx → сразу `rollback {session, txId
    ставки}` своей строкой, `amount 0`);
  - `win(…, cancel=false)` → `api_win`, при `cancel` тип `cancel` и `cancel: true`;
  - журнал `player_external_transactions` в формате PHP: `uuid` = `txId`, `service partner`,
    `wallet_id` кошелька валюты сессии, `amount` минорные, `request` (у ставок `amount` —
    **строкой**, как `MoneyHelper::toMinorUnits`), `status awaited → completed/canceled`,
    `attempts` `[{at: 'YYYY-MM-DDTHH:MM:SS+00:00', url, http, ms, error≤300}]` (последние 20),
    `last_error ≤190`, `ext_id = processedTxId`, `balance_after`, `allowed_at`; таймаут 10 с;
    `retryable` = сеть(0) / 429 / 5xx кроме 501;
  - **воркер** `startRetries()` (в `main.ts`, раз в 1 с; `stopRetries()` при остановке):
    строки `awaited` типов `win/cancel/rollback` **только своей игры** (`game_sessions → games.uuid =
    GAME_UUID` — строки крашей не трогает), срок по лестнице `1,2,5,15,60,300,900,1800,3600,10800,43200`
    с от `updated_at` по `attempts_count`; ни разу не отправленные — не раньше 60 с (не
    перехватить запрос в пути). Всё из БД → переживает рестарт. `bet` не ретраится (как PHP;
    неподтверждённая ставка так и остаётся `awaited`, её закрывает `rollback`).
  - Требует привязанного игрока: без `profile` — `WalletError('Profile required')`.
  - **Команды сокета `bet` / `win` / `cancel`** (Илья: «добавь команды сокетам на бет, вин,
    cancel»; `web/v1/wallet.handler.ts` → `WalletService.placeBet` / `settle`):
    `bet {amount}` → `{bet_id, status: accepted|declined|not_confirmed, balance}` (`bet_id`
    генерит сервер, `roundId = betId`, `betNumber '1'`); `win {bet_id, amount}` и `cancel
    {bet_id}` → `{bet_id, status: completed|awaited|canceled, balance}`. `amount` — целое > 0,
    **минорные единицы** (как у оператора). **Защита (моя, Илья не возражал):** win/cancel
    только по принятой ставке этой сессии, один раз на ставку (`Bet already settled`),
    cancel = сумма ставки с сервера, win ≤ ставка × 68.9305 (`Win exceeds the maximum payout`),
    параллельный второй settle по той же ставке — `Bet is being settled` (in-memory, движок один
    на игру). Ошибки — `Invalid amount`, `Invalid bet_id`, `Bet not found`, `Profile required`.
    Предупреждал Илью: по ТЗ клиент шлёт игровые действия (start/continue/cashout), а сумму
    выплаты считает сервер — эти команды временно заменяют игру.
- **Тестовый оператор** `src/resources/tests/support/fake-operator.ts` (в образ не попадает):
  проверяет подпись, `/user/info` → `op-player-1`, RUB; `/bet`, `/win`, `/rollback` с балансом и
  идемпотентностью по `txId`; сценарии по `betId`: `decline-…` → 402, `down-…` → 503,
  `flaky-…` (win) → 503 дважды; `/rollback` → 503 дважды на `txId`. Запуск:
  `docker run -d --name fake-operator --network crash-heroes-backend-api-core_minigames_net
  -v <репо>:/app:ro -w /app -e API_KEY=gpk_local_test -e SECRET=<секрет проекта>
  node:24-alpine node src/resources/tests/support/fake-operator.ts`; у локального проекта
  «Local test partner» (id 2) адреса `http://fake-operator:4000/{user/info,bet,win,rollback}`.
- **Прогон 18.09 (всё сошлось):** profile → игрок id 4 + кошелёк RUB 100000, повтор и новый
  запуск без дублей, оператор лёг → `Profile unavailable`; деньги — bet ok, win ok, decline →
  `canceled`, down → `not_confirmed` + rollback дотянут воркером (503 → 200), flaky win — 3
  попытки воркером, cancel ok; зеркало 101000 = 100000 − 1000 + 1500 + 300 + 200.
- **На dev** движок ходит в MySQL юзером api-core (`dev_minigames_user`). Для отдельного юзера
  нужны: SELECT `projects` (с секретами), `currencies`, `games`; SELECT/INSERT/UPDATE `players`,
  `player_wallets`, `game_sessions`, `player_external_transactions`; SELECT/INSERT/UPDATE/DELETE
  `game_rng_rounds`, `game_rng_steps` — TODO.

## Нейминг: игра и раунд (22.09, переименование во всех репо)

Команда Ильи 22.09: «делаем движок, надо переделать все нейминги что тут что в апи в
таблцах и админках. Уровень/level/ставка — round. Раунд/round — game». То есть:

| было | стало | что это |
|---|---|---|
| раунд / `round` | **игра** / `game` | партия игрока от ставки до «Забрать» или краха |
| уровень / `level`, затем `bet` | **раунд** / `round` | один бросок двух костей, лестница 1–49 |
| шаг / `step` | **раунд** | то же самое, слово «шаг» больше не употребляем |

Как это легло по слоям:

- **движок**: `domain/game.ts` (`MAX_ROUND`, `multiplier(round)`, `payout(amount, round)`),
  `services/game.service.ts` (`GameService`, `GameError`, `GameView`, `GameStatus`,
  `GameRow.wonRound`), `web/v1/game.handler.ts` (`registerGameHandlers`),
  тест `resources/tests/domain/game.spec.ts`;
- **протокол**: `round_id` → **`game_id`**, `bet` → **`round`**, `state` → `{game: вид | null}`;
  ошибки `Game already active`, `No active game`, `Game is busy` (остальные не менялись);
- **БД** (миграция api-core `2026_09_22_100001_rename_game_rng_rounds_to_games_and_steps_to_rounds`):
  `game_rng_rounds` → **`game_rng_games`** (`level` → `round`), `game_rng_steps` →
  **`game_rng_rounds`** (`round_id` → `game_id`, `level` → `round`). Имена индексов и
  внешних ключей остались от прежних таблиц — они нигде не используются;
- **api-core**: модели `GameRngGame` (партия) и `GameRngRound` (бросок); ресурсы
  `RngGameResource` (партия), `RngRoundResource` (бросок), `RngGameOperationResource`,
  `RngEngineResource` (каталог); `resolved_rng_round` → `resolved_rng_game`;
- **роуты api-core**: каталог игр `v2/admin/rng/games` → **`v2/admin/rng/engines`**
  (`…/{uuid}`, `…/{uuid}/health`), партии игроков — **`v2/admin/rng/games`** и
  `v2/admin/rng/games/{uuid}`;
- **админка**: раздел «Игры» (каталог с адресом движка) → **«Движки»** `/rng/engines`
  (`pages/rng-engines/`), раздел «Раунды» → **«Игры»** `/rng/games` (`pages/rng-games/`),
  внутри карточки игры таблица «Раунды»; фильтр по игре каталога — «Все движки»;
- **тестовый UI**: `game` вместо `round` в состоянии, «Раунд N» — номер броска;
- **Apidog** «Game socket v1» (3514439) — описание переписано под новые имена.

**Что НЕ переименовано и почему:** контракт с оператором (`betId`, `roundId`, `betNumber`
в теле `/bet`, `/win`, `/rollback`) и колонки `player_external_transactions`
(`round_uuid`, `bet_id`) — это внешний seamless-контракт, общий с крашами и Lucky;
таблица `games` и колонка `game_id` в `game_rng_games` — это каталог игр api-core.

Разделы ниже написаны до 22.09 и местами говорят «раунд» про игру и «уровень/шаг» про
раунд — читать с этой таблицей в руках.

## Раунд и шаги — сделано (18.09, сессия `crashgames-98`; движок `2a993ce` в `dev`, api-core `55b3018` в `develop`, оба запушены и на dev; на dev образ 0.1.2 с 21.09)

**Решения Ильи 18.09** (заменяют прямые команды `bet`/`win`/`cancel` — они удалены вместе с
`wallet.handler.ts`, `WalletService.placeBet`/`settle`):
- **Раунд** = игра игрока от ставки до «Забрать» или проигрыша (не бросок, как в ТЗ/макете!).
  Внутри раунда — **шаги** (уровни 1–49), шаг = один бросок. В отличие от крашей раунд у
  каждого игрока свой и кончается его действием.
- **Деньги: один `bet` оператору на старте** (`betId = roundId = uuid раунда`, `betNumber '1'`),
  шаги денег не двигают, `win` на `cash_out`, после 49-го выигранного шага — авто-выкуп.
  Проигрыш — ничего не шлём.
- **Кости — из потока dicestream** (`DICE_STREAM_URL`, dev `wss://dicestream.crash-heroes.com/ws/events`):
  берём **первый `dice.roll`, пришедший через 3 с после запроса** (прошлый брать нельзя —
  поток открыт всем, игрок знал бы исход). Поток недоступен / броска нет 5 с → `Dice unavailable`, шаг не
  делается, **внутренним RNG не подменяем** (ТЗ).
- **Кости клиенту отдаём, `roll_id` — нет** (Илья: «roll_id не надо возвращать») —
  `step {level, result, dice_1, dice_2}` в событии `result` и в `state`; `roll_id` только в БД (Илья сначала: «в ответе значения кубиков не пишем», затем в тот же
  вечер: «значения кубиков тоже надо возвращать» — действует второе). Всё событие
  источника — в БД (`game_rng_steps.roll`).
- **Результат шага — отдельным событием** (Илья: «результат должен приходить отдельным
  событием, будет пауза между ставкой и результатом»): `start` / `continue` **отвечают сразу**
  (`rolling: true`, оба `can_*` false — экран «Бой»), затем сервер шлёт `{type:'result',
  data:<вид раунда со step>}` **без `id`** — **через 3–4 с после ответа** (Илья: «задержка
  между ставкой и результатом давай 3 секунды», затем «результат не должен быть известен
  эти 3 секунды»): `throwDice` ждёт `sleep(3000)` и **только потом** берёт первый бросок
  потока после этого момента — исхода до 3 с не существует нигде, ни у клиента, ни в БД
  (проверено: нажатие 17:27:38, `generated_at` броска 17:27:41.744). Первая версия брала
  бросок сразу и придерживала 3 с — отменено. Пока бросок не решён, `state` отдаёт снимок
  ответа (`rolling` Map), а не БД. Бросок в сессии
  один за раз — `id` не нужен. Сбой потока посреди броска → вместо `result` событие
  `{type:'error', data:{request, message:'Dice unavailable'}}`, раунд на прежнем уровне.
  Пока идёт бросок — прочие команды раунда `Round is busy`, `state` показывает `rolling: true`
  (замок сессии держится до конца броска: `exclusive()` + `release.keep()/now()`).
  `SocketClient` получил `push(type, data)` — первое серверное сообщение не в ответ на запрос.

**Протокол** (`web/v1/game.handler.ts` → `services/game.service.ts`, имена с 22.09):
`start {amount}` (ставка + первый раунд; сам зовёт `ProfileService.get`, если у сессии нет
игрока), `continue` (оба → сразу ответ, потом событие `result`), `cash_out` (отвечает сразу,
без события), `state` → **вид игры прямо в `data`**, без игры — `data: null` (с 23.09; до того
`{game: вид | null}`). Вид игры: `game_id,
status (active|lost|cashed_out|declined|not_confirmed), amount, currency, round, rolling, multiplier,
win (сколько сейчас в игре / зачислено / 0; было `payout`), balance, can_continue, can_cash_out,
dice {result: win|crash, dice_1, dice_2} | null [, cash_out_status
на выкупе (было `payout_status`)]`. Ошибки: `Invalid amount`, `Game already active`, `No active game`, `Nothing to
cash out`, `Game is busy`, `Dice unavailable`, `Profile unavailable`, `Currency not supported`.
Если после принятой ставки поток лёг — придёт событие `Dice unavailable`, игра `active` на
раунде 0, клиент шлёт `continue`. Висящая запись раунда без результата (процесс упал посреди
броска) удаляется перед следующим броском этой игры.

**`round` в ответе — текущий раунд с 1** (Илья: «надо с 1 начинать сразу», «чтобы
multiplier был сразу»): бросаемый или только что брошенный; `multiplier` — его коэффициент,
есть уже в ответе на `start` (1 / 1.0582); при проигрыше `round` = проигранный раунд.
`win` — по последнему **выигранному** (пока бросок в полёте — ещё предыдущий, до первой
победы 0). **В БД `game_rng_games.round` — последний выигранный**
(в коде `GameRow.wonRound`), текущий считается в `view()`: `rolling || lost ? won + 1 :
max(won, 1)`. `state` во время броска отдаёт `dice: null`. Проверено вживую 18.09.

**`next_multiplier` убран** (Илья 18.09): следующий коэффициент фронт берёт из `coefficients`
(до 23.09 — `get_coeffs`) по `level + 1`.

**Суммы — в минорных единицах, целыми** (Илья: «в минорных так и возвращать фронту»):
`amount: 1000` = 10.00 ₽, `win: 1058` = 10.58 ₽; фронт делит на 100. `win` = ставка ×
коэф. последнего выигранного уровня **от исходной ставки** (таблица накопительная, не
перемножать: 1000 → 1058 → 1154 → 1259), дробь копейки отбрасывается один раз в движке —
показанное = зачисленное. Поля переименованы (Илья: «переименовывай»): `payout` → `win`,
`payout_status` → `cash_out_status`; колонка БД `game_rng_rounds.payout` не менялась.
**`balance` в виде раунда нет** (Илья: «он не нужен тут в ответе», «лучше валюту верни») —
вместо него `currency` (валюта раунда = валюта сессии у оператора, все суммы в её минорных
единицах); баланс фронт берёт командой `profile`.

**Файлы:** `domain/game.ts` (`MAX_ROUND`, `isCrash` — только 1-1/3-3/5-5, `multiplier(round)`,
`payout` — `amount × коэф` на BigInt, **округление вниз**), `services/dice.service.ts`
(клиент потока на глобальном `WebSocket` Node, не `ws`; реконнект раз в 1 с; `next()` —
промис на следующий бросок, один бросок получают все, кто ждал в этот момент),
`services/game.service.ts`, `SessionService.touch()` (продление `expires_at` на игровых
действиях, в БД не чаще раза в минуту). Замок — in-memory по сессии (`Game is busy`) +
`UNIQUE(game_id, round)` в БД.

**Таблицы** — миграция api-core `2026_09_18_100003_create_game_rng_rounds_table`,
поверх неё `2026_09_22_100001_rename_game_rng_rounds_to_games_and_steps_to_rounds`:
**`game_rng_games`** (uuid, game_id, game_session_id, player_id, currency, amount, round,
payout, status, finished_at) и **`game_rng_rounds`** (game_id, round, roll_id, dice_1,
dice_2, result, multiplier, roll json — всё событие источника: стол, партия, номер хода,
игроки, время; запись раунда создаётся **в момент нажатия**, результат дописывается по
приходу броска).

**Событие `result` вживую (18.09):** ответ `start` за 25 мс (`rolling`), `continue`/`cash_out`
в это время — `Round is busy`, `state` — `rolling: true`, `result` через 338 мс; `continue` →
`result` через ~1 с → `cash_out` 808 (баланс 100549 → 101357); раунд до краха на 6-м шаге —
`result` со `status: lost`.

**Проверено 18.09:** `tsc` 0, тесты **40/40**; вживую на локальном стенде (dicestream dev +
fake-operator): старт → шаг ~1 с → повторный старт `Round already active` → два `continue`
разом — второй `Round is busy` → выкуп на 3-м уровне 1259 → `state` null; раунд до краха на
22-м шаге (3-3, сверено с `GET /api/rolls/{roll_id}` dicestream), 6-6 засчитан выигрышем;
журнал оператора: bet+win у выкупленного, только bet у проигранного.

**Не решено / помнить:**
- **Таблицы расходятся с решением Ильи из скила `crash-games`** («rng-игры пишут в таблицы
  крашей» — под это сделана админка RNG): движок пишет в `game_rng_games`/`game_rng_rounds`,
  в разделах крашей их не видно. Выбрать с Ильёй: админка из `game_rng_*` или движок в
  `game_crash_*`;
- округление выплаты — сделано вниз, **Илья не подтверждал** (макет противоречит сам себе);
- Max Bet / Max Payout из ТЗ не проверяются; `idempotency_key` из ТЗ не сделан (замок только
  in-memory + уникальность уровня);
- одновременно нажавшие игроки получают один и тот же бросок;
- раунд, застрявший в `betting` (процесс упал посреди ставки), не чистится — новый старт он
  не блокирует;
- у dicestream нет авторизации (чтение и поток открыты; закрыты ли start/stop — не проверено).
- **Выкачено на dev 18.09 вечером** (см. «Серверы»): миграция `game_rng_*` применена CI
  api-core, движок на сети хоста, поток — `ws://127.0.0.1:18080/ws/events`; 21.09 образ
  обновлён до 0.1.2. Осталось: отдельный MySQL-юзер движку; полный раунд на dev — из
  настоящего запуска Lucky; прод.

## Исход раунда — `win` / `lose` (22.09)

Замечание Константина через Илью: «у тебя 2 статуса сейчас win / crash, должно быть win /
lose». Проверил, как у соседей: **в крашах статуса исхода нет вообще** —
`game_crash_bets` хранит только `coefficient` и `win` (ноль = проиграл), а
`game_crash_rounds.state` — жизненный цикл раунда числом `0/1/2`; у слотов в
`game_slot_bets` тоже нет статуса. То есть равняться было не на что, а `crash` выбивался
из нашего же `game_rng_games.status = lost`.

Заменено везде (Илья: «замени да плз», вариант `lose`, не `lost`): движок — `isCrash` →
`isLose`, тип `Dice.result` и `RoundView.result` = `'win' | 'lose'`; api-core —
`GameRngRound::RESULT_CRASH` → `RESULT_LOSE`, миграция
`2026_09_22_100002_rename_crash_result_to_lose_in_game_rng_rounds` переписывает уже
записанные строки (`crash` → `lose`, down возвращает); админка — тип, цвет и подпись
«Дубль» → «Проигрыш»; тестовый UI — классы `.lose` и подпись «· проигрыш»; описание в
Apidog. Статус игры `lost` не трогали.

## История игр — команды `history` и `game` (22.09)

Илья: «на тестовый UI + движок и команды, типо кликаем на историю и можем там по каждому
раунду посмотреть стату, типо попап открывается, как в дизе», затем «давай ещё команду в
сокетах на получение истории — последние 10».

- **`history {limit?}`** → **массив прямо в `data`** (Илья: «в data не надо "games": [, сразу
  список»), как у `coefficients`: `[{game_id, status, amount, currency, round, multiplier, win,
  started_at, finished_at}]` — сыгранные игры (`lost` и `cashed_out`) этого игрока в этой
  игре, новые первыми. `limit` по умолчанию **10**, максимум 50, иначе `Invalid limit`.
- **`game {game_id}`** → вид игры + `rounds: [{round, result, dice_1, dice_2, multiplier,
  win, roll}]`, где `roll` — **всё событие dicestream целиком** из БД (`roll_id`,
  `table_slot_id`, `table_instance_id`, `sequence_no`, `player_1`, `player_2`,
  `active_player_id`, `generated_at`, `published_at`, `generator_version`). Чужая игра —
  `Game not found`, пустой или не-строковый id — `Invalid game_id`.
- **`roll_id` в живом виде игры по-прежнему не отдаём** (решение 18.09) — он появляется
  только в истории, когда игра уже сыграна и подсказать ничего не может. Отметил это Илье.
- Обе команды сами дотягивают профиль, если у сессии ещё нет игрока (`withPlayer()`), —
  иначе `history` сразу после подключения приходил бы пустым: клиент шлёт `profile` и
  `history` одним пакетом, и порядок ответов не гарантирован (на это и напоролся).
- **Выкачено на dev 22.09** (движок `e027489`, образ **0.1.8**, тестовый UI в
  `~/crashgames/games/testrng/`): контейнер `healthy`, `/health` 200, `RngEngineHealthService`
  `alive: true` 96 мс, снаружи WS отвечает `Session not found` + 4401, в образе обе команды
  на месте. **Живьём на деве history не проверить** — живых сессий нет, нужен настоящий
  запуск из Lucky; локально всё зелёное (регресс 30/30).
- Тестовый UI: чипы «История игр» кликабельны → попап. **Формат попапа задан скриншотом
  Ильи** (карточка «Экспресс №…» из букмекерского интерфейса, `~/Pictures/Screenshots/
  Screenshot from 2026-09-22 15-20-31.png`): шапка «Игра № <8 симв.> · статус» с точкой
  состояния и датой, три плитки **Сумма / Коэф. выкупа / Выигрыш**, лента кубиков — по
  чипу на раунд (дубль красный, выбранный синий, клик переключает), ниже карточка
  выбранного раунда: «Раунд N · Коэф. раунда», пояснение, ID партии с «копировать»,
  «Раунд N/M» и стол, «Бросок #<ход>» с кубиками и временем, ID броска с «копировать»,
  выигрыш раунда, «Спортсмен 1/2» с именем и id, у бросавшего — пометка «бросает».
  Блока с видео из макета у нас нет: dicestream видео не отдаёт. Попап до 560 px, тема
  светлая как весь UI. Закрывается крестиком, кликом по фону и Esc. История грузится с
  сервера при подключении и после каждой законченной игры, а не копится в памяти вкладки.
- **Чипы истории — только коэффициент** (Илья: «в истории игр если проигрыш кэф рисуй, и у
  выигрыша тоже ток кэф»): зелёный у выкупа, красный у проигрыша; сумма выигрыша, статус,
  число раундов и id — в подсказке. У проигранной игры `history` отдаёт **кф того раунда, на
  котором выпал дубль** (`multiplier(round + 1)`), у выкупленной — кф выкупа; раньше у
  проигрыша был `null` и рисовался прочерк. Статусы в заголовке попапа — «Победил»,
  «Проиграл», «В игре», «Ставка отклонена», «Ставка не подтверждена», «Ставка».

## Протокол сокетов — правила (18.09)

**Спека протокола — в Apidog** (занесла сессия `crashgames-98` 18.09 по моему описанию):
проект **1381870 «Crash Heroes»**, модуль **«Game engine RNG» (1458545)**, ветка main —
WebSocket «Game socket v1» (id 3514439: `/v1?session={{session}}`, рукопожатие, коды
закрытия, конверт, ping/profile/get_coeffs и раунд start/continue/cash_out/state (18.09 заменили
bet/win/cancel), статус developing); HTTP «Create game session» (id 43843737: `POST {{api_core_url}}/api/external/game/url`,
прескрипт подписывает `METHOD\n/path\n{query}\n{body}`, постскрипт кладёт `session` в
окружение); HTTP «Health» (id 43843656). Окружения Local Env (127.0.0.1:3100 / api-core :8000,
`a2c68a94-…`) и Develop Env (dev.server… / `a2c69d5c-…`, dev.api…); приватные ключи Илья
вписывает сам. **Правило: меняется протокол (новые команды start/continue/cashout, `code` в
ошибках, поля ответов) — в том же шаге отправить дельту `crashgames-98` (или обновить Apidog
самому), иначе спека молча устареет.**

**Синк 2026-09-21** (делал я, всё перечитано после записи):
- `Game socket v1` (3514439) — описание переписано целиком: рукопожатие и коды
  закрытия, конверт с обязательным `id`, **вид раунда с `bet` и `balance`**,
  отложенный `result` с `id` запроса, `get_coeffs` массивом прямо в `data`,
  деньги (один `bet` на раунд, `rollback` на неподтверждённую, выкуп брошенного
  раунда) и список ошибок. Сохранённое сообщение в `requestBody` не тронуто —
  update шёл только полем `description`. До этого там лежала шпаргалка из семи
  строк запросов, ответы не описывались вовсе.
- `Health` (43843656) — из схемы 200 убран `game_uuid`, осталось `{status, uptime}`.
- `Create game session` (43843737) — ответ 200 теперь `url` **или** `session`
  (`url`, когда у игры заполнен `games.link`), постскрипт `save-session` научен
  доставать `session` из query этой ссылки, иначе окружение перестало бы
  заполняться после правки api-core. Не путать с проектом `CrashGames API` (1347186) —
там внешний HTTP API api-core. Как вести Apidog (порядок записи, окружения, прескрипт,
сокеты) — скил `apidog`.

- **Адрес с версией:** `wss://<домен>/<uuid игры>/v1?session=<id>` (nginx срезает
  `/<uuid>` → движок видит `/v1`; локально `ws://127.0.0.1:3100/v1?session=…`).
  Движок принимает **только `/v1`** (`const PATH` в `socket.config.ts`); иначе
  сообщение `{type:'error', data:{message:'Unsupported protocol version'}}` и
  `close(4400)` — до проверки сессии, без БД. Решение Ильи: «у нас ещё v1 — давай в
  ссылке на подключение это указывать». Появится v2 — отдельный набор команд на `/v2`.
- **Единый конверт** (Илья: «структура единая на всё»): запрос `{id, type, data?}`,
  ответ **`{id?, type, data}`** — `data` в ответе есть всегда. **Тип ответа = тип
  запроса** (Илья: «на входе и выходе одинаковый»): обработчик возвращает **только
  `data`** (`undefined` — ответа нет), `SocketConfig.dispatch` собирает конверт сам.
  `ping` → `{"type":"ping","data":{}}` (Илья сначала хотел `data:"pong"`, после разбора
  best practice — объект: `data` всегда объект, чтобы расширять без поломки клиентов).
  Ошибки — отдельный тип `error` (`data.message`, у упавшего обработчика ещё
  `data.request`).
- **`id` запроса — обязателен** (Илья: «давай id добавим», «число пусть будет», «давай
  обязательный»): **только целое число** (`Number.isSafeInteger`); у нас нет
  уведомлений — каждое сообщение клиента ждёт ответа. Ответ и ошибка по запросу
  несут тот же `id` первым полем; нет `id` / строка / дробь / объект → `Invalid
  message` без `id` (если `id` валиден, а сломано другое — ошибка с `id`). Серверные сообщения, не привязанные к запросу (отказ по
  сессии/версии, будущие пуши), — без `id`. `idempotency_key` из ТЗ — деловой ключ
  Continue/Cash Out, `id` — транспортный; значение может совпадать.
- **Серверного heartbeat больше нет** (Илья 18.09 вечером: «почему у меня сессия сокетов через
  30 секунд будто умирает, убери это»). Был: ping-кадр раз в 30 с, не ответил pong до следующего
  такта — `terminate()` (1006). Apidog на ping-кадры не отвечает, поэтому его соединения рвались
  через 30–60 с. Убраны `beat()`, `silent`, `heartbeatMs`, обработчик `pong`, тест. Зомби-соединения
  живут не дольше сессии: таймер `watch()` закрывает сокет `4401 Session expired` (25 мин без
  игровых действий). Проверено: клиент с `autoPong: false` жив через 70 с. JSON-`ping` клиента
  остался.
- **Best practice, ещё не сделано:** машинный `code` в ошибках (`session_expired`…) —
  с первыми игровыми командами.
- Коды закрытия: `4400` версия, `4401` сессия, `1011` сбой (БД), `1001` остановка сервера.

## Команда `coefficients` (18.09 как `get_coeffs`; переименована 23.09)

Клиент → `{"type":"coefficients"}` → `{"type":"coefficients","data":[1.0582, 1.1544,
…, 68.9305]}` — массив **прямо в `data`**, все 49 коэффициентов выкупа, **только колонка Cash Out** из ТЗ
(Илья: «кэфы статичны, колонка Cash Out нужна только»), индекс = раунд − 1. Таблица —
`src/domain/coefficients.ts`, handler — `web/v1/coefficients.handler.ts`
(`registerCoefficientsHandler`; до 23.09 `coeffs.handler.ts`); тест `resources/tests/domain/coefficients.spec.ts`
сверяет каждое значение с `round(0.97 / (11/12)^N, 4)` — опечатка при правке не
пройдёт. Handler — `web/v1/coeffs.handler.ts`. Проверено вживую. **ТЗ игры — в
`DESIGN.md`, раздел «ТЗ Dice RNG»**: там проигрыш только 1-1/3-3/5-5, RTP 97 %, 49
раундов, Math Version, Max Bet, idempotency — сверяться с ним при любой игровой логике.

## Авторизация при подключении — сделано (18.09, коммит `de161a6` в `dev`, не запушен)

Клиент подключается **`wss://<домен>/<uuid игры>?session=<id>`** (`id` — то, что
вернул `/api/external/game/url`; у RNG — голый uuid). Решение Ильи: проверять при
коннекте, не первым сообщением.

- `SocketConfig` берёт `session` из URL, до конца проверки сообщения клиента ждут
  (`await authorized`). Отказ — **закрытие `4401`** с причиной: `Session required` /
  `Session not found` / `Wrong game` (сессия чужой игры, в т.ч. `sess_…` крашей) /
  `Session expired` (`expires_at` прошёл или `closed_at` не пуст). Сбой БД — `1011
  Internal error` + ERROR в лог.
  **Перед закрытием движок шлёт причину сообщением** (Илья: «если невалидно, надо
  отвечать сообщением почему»): `{type:'error', data:{message:'<причина>'}}`, затем
  `close(4401, '<причина>')` — причина и в `onmessage`, и в `onclose`; так же при
  истечении на открытом соединении. Не рвём рукопожатие 401-м: браузер тогда видит
  только безликий 1006.
- **`SessionService`** (`services/session.service.ts`, `mysql2` через
  `config/db.config.ts` → `DbConfig.pool`): `open(id)` — проверка + продление
  `expires_at = NOW() + INTERVAL SESSION_TTL_MINUTES MINUTE`, `last_seen_at`,
  `updated_at`; `check(id)` — только проверка. **Вся арифметика времени в MySQL**
  (`NOW()`, `TIMESTAMPDIFF`) — у Laravel `timezone UTC`, у MySQL `SYSTEM` = UTC
  (сверено локально 18.09; на серверах сверить перед выкладкой).
- **Таймер на соединение** до конца срока → `check()`: продлили в другом месте —
  перезавести, нет — `4401 Session expired`. Продление сейчас **только при
  подключении**; `ping` не продлевает (решение: иначе забытая вкладка держит
  сессию вечно); игровые действия будут продлевать (в памяти, запись в БД не чаще
  раза в минуту).
- Окружение: `DB_HOST`, `DB_PORT`(3306), `DB_DATABASE`, `DB_USERNAME` —
  обязательны, `DB_PASSWORD`, `SESSION_TTL_MINUTES`(25, как
  `INTEGRATION_SESSION_TTL_MINUTES` api-core). Локально — `mini_database`,
  `crashgames`, `admin` (тот же, что у api-core; `.env` в gitignore).
- Тесты 16/16: `socket.config.spec` подменяет `SessionService` фейком (`good`,
  `short` 50 мс, `renewed`, неизвестная) — БД в тестах не нужна.
- Сквозь локальный стенд 18.09: сессия из `/game/url` → подключение, `ping`→`pong`,
  срок 60 → 1500 с; без сессии / чужая / `sess_` краша / просроченная → 4401 с
  нужной причиной.
- **Перед выкладкой на dev:** образ `0.1.0` на dev БД не знает; новому нужны
  `DB_*` в серверном `.env`, отдельный MySQL-юзер (SELECT `game_sessions`, `games`;
  UPDATE `game_sessions`) и `network_mode: host` в `docker-compose.server.yml`
  (MySQL на сервере слушает `127.0.0.1`).

## Авторизация и деньги — итоговое разделение (18.09, ждёт подтверждения деталей)

Илья после колебаний («странно — надо через php таки идти», затем «делаем так же, но
ставки не через бэк-кор — я же могу сам в бд писать и запросы внешнему проекту
делать»):

| шаг | кто |
|---|---|
| оператор → `POST /api/external/game/url` (HMAC, обе схемы подписи; `game_id` = id или uuid) → `{session: "<uuid>"}` | **api-core** (18.09: RNG-игра без ссылки отдаёт `session`, **без приставки `sess_`**) |
| клиент → движок `{type:'auth', data:{session}}` | **движок** |
| первый вход: `/user/info` оператора, создание игрока | **api-core** (`GameSessionResolver`; движок спрашивает его по сессии) |
| ставки/выигрыши → `/bet`, `/win`, `/rollback` оператора | **движок напрямую** |
| журнал операций, данные игры в MySQL | **движок напрямую** |

Деньги в движке обязаны повторить контракт PHP: подпись `signRequest`
(`METHOD\n/path\n{}\n<ksort-json>`), ключи/адреса из `projects`, `launch_token` из
`game_sessions`; **ставка подтверждается клиенту только после ответа оператора**
(грабля старого движка); `/bet` без ретраев, неясный отказ → `rollback`; `/win` и
`/rollback` — бесконечные ретраи 1s…12h на 5xx/429, **переживающие рестарт**
(источник — статус строки в БД, свой воркер в движке; PHP-очередь `integration` их
не увидит); `txId` = uuid строки журнала; зеркало баланса из `balance` ответа.
Предложено: журнал — существующая `player_external_transactions` в формате PHP
(видно в админке «Внешние»); таблицы игры — миграциями api-core, пишет движок;
отдельный MySQL-юзер; на сервере `network_mode: host`. **Ждёт ответа Ильи.**

### Предыдущие варианты (справка)

**Поворот (Илья, позже 18.09): не device_id, а как интеграция крашей с Лаки** —
«авторизация по приват/публик ключу и HMAC, запрос сервер-сервер к апи,
возвращается ссылка; ссылки пока нет — вернём сессию и с ней работаем с
движком; сможем всё на движке?» — **да, всё в движке, без PHP.** Предложено
(ждёт подтверждения):

1. **Запуск, сервер оператора → движок:** `POST https://dev.server.crash-heroes.com/<uuid>/api/external/game/url`
   — путь как у крашей (`/api/external/game/url`), чтобы клиент Лаки работал без
   правок: у провайдера `apiEndpoint = https://dev.server.crash-heroes.com/<uuid>`.
   Заголовки `x-api-key` (= `projects.api_key`) и `x-sign`; тело `{game_id, session}`
   (`session` — launch-токен оператора). Проверка подписи — как
   `AuthProjectSignMiddleware`: `HMAC-SHA256(api_secret, json тела с ksort
   верхнего уровня)`, два варианта — со слэшами `\/` (PHP) и без (JSON.stringify),
   `hash_equals` → в Node `timingSafeEqual`. Ответ пока `{session: 'sess_<uuid>'}`
   вместо `{url}`.
2. **Сессия — строка в `game_sessions`** (та же таблица, что у крашей: `crash_session`
   UNIQUE = `sess_<uuid>`, `launch_token` UNIQUE, `project_id`, `game_id`, `player_id`,
   `external_player_id`, `currency`, `expires_at`, `last_seen_at`, `closed_at`);
   повторный запуск с тем же `launch_token` — переиспользовать (как
   `GameLaunchService::reuse`); TTL 25 мин (`integration.session_ttl_minutes`).
   **JWT не нужен** — непрозрачный `sess_` в БД, его же понимают `GameSessionResolver`
   и админка.
3. **Клиент → движок с `sess_…`** (WS: первое сообщение `{type:'auth',
   data:{session}}`; HTTP: `Authorization: Bearer`).
4. **Первое обращение:** движок → оператор `POST projects.api_user_info
   {session: launch_token}`, подпись как `ProjectSignHelper::signRequest`:
   `HMAC-SHA256(secret, "METHOD\n/path\n{}\n<ksort-json тела, {} для пустого>")` →
   игрок, баланс, валюта → найти/создать `players` (`client_type external_project`,
   `project_id` оператора, `external_id` = id игрока у оператора) → дописать в
   `game_sessions` `player_id`/`external_player_id`/`currency`. Баланс — зеркалом из
   ответа, кошельков нет.
5. Ставки позже — `/bet`, `/win`, `/rollback` оператора (журнал —
   `player_external_transactions`, как у крашей).

Нужно в движке: POST с JSON и **сырым телом** для подписи, ошибки текстами
`IntegrationError` (Aviatrix, партнёр парсит по строке), `mysql2` + MySQL-юзер (SELECT
`projects`, `games`; INSERT/UPDATE `game_sessions`, `players`), на сервере
`network_mode: host`.
Ниже — предыдущие варианты (device_id), оставлены как справка.

Задача Ильи: «простая по device_id: создаём или используем существующего
пользователя, от бэка возвращаем JWT; предпочёл бы вообще без бэка PHP».
**Решено: база — единая, текущая MySQL api-core** («чтобы единая была»): игроки те
же, что в лобби и админке; отдельную БД для RNG не заводим.

**Решено: кошельков и денег у нас нет** (Илья: «мы не будем тут заводить кошелёк»,
«будем как игра в Лаки — ходить во внешнюю систему за профилем»). Мы — провайдер
игры: профиль и баланс — во внешней системе по seamless-контракту, как краши ↔
Лаки (`/user/info`, `/bet`, `/win`, `/rollback`, HMAC `x-api-key`/`x-sign`). Движок
при auth создаёт **только строку `players`** (без кошельков и бонуса),
`client_type = external_project` — в Laravel это и значит «деньги снаружи»
(`PlayerObserver` для него кошельков не заводит). Адреса и ключи партнёра — из
`projects` той же базы (`api_user_info`/`api_bet`/`api_win`/`api_rollback`,
`api_key`/`api_secret`). **Открыто (спрошено 18.09):** какая внешняя система на этом
этапе и тот же ли контракт; что отдаём ей вместо launch-сессии при входе по
device_id; к какому проекту относить игроков. Блок ниже про повтор кошельков и
`awardStart` в Node — **неактуален**, оставлен как справка о Laravel.

Предложено Ильёй ещё не подтверждено (ждёт ответа — тип игрока, создание в Node,
TTL): движок ходит в MySQL напрямую под отдельным пользователем с минимальными
правами (`mysql2`); схема — **только миграциями Laravel**; `POST /<uuid>/auth
{device_id}` → `GET_LOCK` → поиск `players.external_id` во внутреннем проекте →
если нет, в одной транзакции повторить создание как в Laravel → JWT (HS256, `sub` =
`players.uuid`, 7 дней, `JWT_SECRET`, библиотека `jose`); WS — первым сообщением
`{type:'auth', data:{token}}`, не `?token=` (URL попадает в логи nginx).

**Что делает Laravel при создании игрока — это придётся повторить в Node:**
- `AppController` (`GET /api/app/token?device_id=<RSA>` и `games/{g}/init`):
  `Player::create` c `uuid`, `role` (`AppAuthService::getPlayerRole(client_type)`),
  `project_id = Project::innerId()` (`is_internal`), `name`, `external_id` =
  расшифрованный device_id, `game_currency`, `avatar_id 1`, `logged_at`, потом
  `setRandomName()`; при каждом входе — новый `players.token` (uuid), `client_type`,
  `client_version`.
- `PlayerObserver::created`: `external_project` — ничего; **`demo` — один кошелёк
  `GEM_DEMO` (active) + `awardStart`**; остальные — `GEM`, `RUB` (неактивные) и
  `XTR` (active) + `awardStart`.
- `TransactionService::awardStart`: `GEM_DEMO` 9999×100, `GEM` 1 000 000, `XTR`
  9999×100 — через `makeTransaction` под `withWalletLock`: `balance_before` из
  цепочки, `balance_after`, запись в `player_transactions`, пересчёт агрегатов
  кошелька (`updateDeposit`/`updateBalance`). Цепочку ломать нельзя (грабля 18.08).
- **`players.external_id` — индекс НЕ уникальный** (`players_external_id_index`) →
  одновременный вход с одним device_id может создать двух игроков; в Node нужен
  `GET_LOCK`/аналог. Уникальный индекс на проде без проверки дублей не ставить.
- RSA-шифрование device_id в лобби защиты не даёт (публичный ключ у любого клиента);
  device_id = пароль гостя — годится для демо-денег, не для реальных.
- MySQL на серверах слушает `127.0.0.1` хоста → движку в докере нужен
  `network_mode: host` (и тогда `HOST=127.0.0.1`); локально — `mini_database:3306`
  в общей сети с API.

## Игра по uuid

Движок указывает свою игру **по `games.uuid` из api-core, не по `id`** (Илья
18.09: «работая с игровым движком указывать будем уид из сервер кора… не айди»).
Env `GAME_UUID`, обязателен, проверяется форматом uuid и приводится к нижнему
регистру; процесс без него не стартует
(`GAME_UUID must be a games.uuid from api-core`).

**Текущий uuid: `a2c68a94-4ea3-4086-9364-b1bb7dde9548`** — Илья создал его 18.09;
он же в `.env.example` и в тестах. Судя по работе в api-core, это игра «Test RNG»
(`sys_name` `test_rng`, тип `Crash RNG` / `crash-rng`), но в какой базе он
заведён (локальная, dev) — не уточнялось.

Сторона api-core **на 18.09 не закоммичена** (подробно — скил `crash-games`,
журнал 18.09): миграция `2026_09_18_100001_add_uuid_to_games_table`, `Game` с
`HasUuids`, тип `crash-rng`, сидер `DefaultGamesRngSeeder`.

> Грабля: сидер uuid **не фиксирует** — `HasUuids` генерирует новый на каждой
> базе. Поэтому `GAME_UUID` у каждого окружения свой: взять из
> `SELECT uuid FROM games WHERE sys_name='test_rng'` нужной базы. Если нужен
> одинаковый uuid везде — прописать его в сидере явно.

Порт по-прежнему `3100`: конвенция старых движков «порт = `3000 + games.id`» сюда
не переносится, пока не решено, как движок будет деплоиться.

## Архитектура

Настраивает и поднимает всё `config/`, связывает — `main.ts`. Обработчики
сообщений — `web/`, модель игры (когда появится) — `domain/`.

```
src/
├── main.ts                   точка входа и сборка: CoreConfig → Logger → ServerConfig →
│                             SocketConfig(server.http) → registerHealthController(server, config) →
│                             start(). SIGINT/SIGTERM, uncaughtException/
│                             unhandledRejection → socket.stop(), затем server.stop()
├── config/                   ПРАВИЛО Ильи: файл `<имя>.config.ts` = `<Имя>Config`
│   ├── core.config.ts        CoreConfig {host, port, logLevel, gameUuid} + loadCoreConfig(env).
│   │                         Имя `core` дал Илья (было config.ts → main.config.ts)
│   ├── server.config.ts      HttpHandler + ServerConfig: http.Server (публичное поле `http`),
│   │                         `get(path, handler)` + приватный `handle()`: обработчик
│   │                         вернул объект → 200, нет пути/не GET → 404, исключение
│   │                         → 500 + ERROR в лог (иначе уронило бы процесс);
│   │                         start()/stop(). Путь сравнивается с `req.url` целиком —
│   │                         `/health?x=1` даст 404. В лог `Started` пишет uuid игры
│   └── socket.config.ts      SocketConfig + внизу SocketMessage {type, data?} (одна
│                             модель на вход и на ответ), SocketHandler, isObject,
│                             isSocketMessage.
│                             SocketConfig: WebSocketServer({server: http}) на том же
│                             порту; `on(type, handler)` + приватный `dispatch()`
│                             (JSON → handler по `type`, ловит исключения);
│                             stop(): кадр 1001 всем, глухих — terminate() через 3 с.
│                             ЕДИНСТВЕННОЕ место с `import ... from 'ws'`
├── services/
│   └── logger.service.ts     Logger с порогом уровня (LOG_LEVEL реально фильтрует)
├── web/
│   └── v1/health.controller.ts  registerHealthController(server, config): GET /health →
│   │                         {status:'ok', uptime} — контракт с API, см. выше. Вынесен из ServerConfig 18.09
│   │                         по просьбе Ильи
└── resources/tests/config/   core / server / socket.config.spec.ts (PORT=0)
```

**Принцип Ильи (18.09): «убери всё лишнее и не нужное сейчас».** Ничего на
вырост: нет использования сегодня — нет кода. По этому принципу в тот же день
убраны `EngineConfig` (тонкая обёртка — связывание ушло в `main.ts`), сообщение
`info`, поля `version` и `GAME_ID` в конфиге, `.nvmrc`, `restart:` в compose,
лишние опции `tsconfig`. Затем Илья велел «убрать пока сокеты совсем», а следом —
вернуть их «отдельным конфигом по нашей модели». Вернулись **урезанными**: нет
приветствия `{success, id}`, нет `domain/Client` и учёта клиентов (для остановки
хватает `wss.clients`), обработчик получает только сообщение, `pong` без `time`.

**Возвращать по мере надобности:**
- `domain/Client` (id + функция доставки, `Map<Client, WebSocket>`, обработчик
  получает `(client, msg)`) — с первым сообщением, которому нужен отправитель
  (`auth`, `bet`). Приветствие старого движка — `{success: true, id}`;
- `GAME_ID` — когда появится клиент Laravel API;
- игровой цикл — в `services/` (напр. `game.service.ts`), связывает `main.ts`,
  отдельный `Engine` не заводить.

**Куда что класть.** Сущности и правила игры (раунд, ставка, игрок) → `domain/`.
Логика и внешние клиенты (RNG, клиент Laravel API, сервис раунда) →
`services/*.service.ts`. Новый HTTP-путь → `web/v1/<имя>.controller.ts` с
`register…Controller(server, deps)` и `server.get(...)`, вызывается в `main.ts` и
в тесте. Сокет-сообщения — `socket.on(type, handler)`; служебный `ping` встроен
в конструктор `SocketConfig` (Илья: «убери это в конфиг сокетов» — имя
`system.handler.ts` трижды вызвало вопрос «это сокеты?»). Куда класть игровые
сокет-обработчики (`auth`, `bet`) — решить с Ильёй, когда появятся. Типы — в файле своего конфига. Именование файлов — по роли, как в Lucky
(`*.config.ts`, `*.service.ts`, `*.handler.ts`, `*.spec.ts`), суффикс `.class`
старого движка не используем.

**Протокол — единая модель сообщения** (Илья 18.09: «пока абстрактную модель —
просто единая»; конкретные сообщения игры и формат с `id` запроса отложены):

```
{ "type": string, "data"?: object }
```

- одна модель **в обе стороны**: запросы клиента, ответы, ошибки, будущие пуши;
- `type` — что за сообщение; `data` — полезная нагрузка, форма у каждого `type`
  своя и пока не фиксируется;
- **строго**: любые поля верхнего уровня, кроме `type`/`data`, `data` не-объект
  (массив, `null`, строка) → отказ. Иначе `{"type":"bet","amount":100}` молча
  потерял бы `amount`;
- ошибки: не JSON → `{type:'error', data:{message:'Invalid JSON'}}`; не по модели →
  `…'Invalid message'`; нет обработчика → `…'Unknown message type'`; исключение в
  обработчике → `{type:'error', data:{request:<type>, message:'Internal error'}}`,
  соединение живёт, в лог — `ERROR` со стеком;
- приветствия при подключении **нет** (18.09 добавлено `{type:'connected',
  status:'ok'}` и в тот же час убрано Ильёй); `ping` → `{type:'pong'}` (встроен
  в `SocketConfig`).

Предлагалось и **пока не принято**: `id` запроса в конверте
(`{id, type, data}`, сервер возвращает `id` в ответе — сопоставление ответа с
запросом среди тиков) и машинный `error.code`. Вернуться, когда появятся первые
игровые сообщения.

**Остановка и таймер 3 с** (Илья спрашивал «зачем»; был константой
`SHUTDOWN_GRACE_MS`, теперь `3000` в `SocketConfig.stop()`):
- **HTTP таймер не нужен.** Node ≥ 19 в `http.close()` сам закрывает
  простаивающие keep-alive соединения. Проверено 18.09: при висящем keep-alive
  сервер вышел за 21 мс — поэтому в `ServerConfig` таймера нет.
- **Сокетам нужен.** Открытое WS-соединение само не закрывается и держит
  `http.close()`. Вежливо закрываем кадром `1001`; клиент, не ответивший на него,
  держал бы остановку **30 с** (`closeTimeout` в `ws`), а Docker убивает процесс
  через 10 с. Поэтому `SocketConfig.stop()` рвёт глухих через 3 с. Проверено:
  клиент, сделавший рукопожатие руками и замолчавший, задержал выход на 3007 мс.
- **Порядок в `main.ts`: сначала `socket.stop()`, потом `server.stop()`** — иначе
  HTTP-сервер ждёт открытые сокеты.
- `docker compose down` — 0.35 с. В compose стоит `init: true`.

## Регресс

Живой прогон по сокету через api-core и поддельного оператора — **`REGRESS.md`
рядом с этим файлом**: 26 проверок (протокол, деньги, declined, not_confirmed с
роллбэком, протухшая сессия и чистка брошенных раундов), скрипт
`probes/regress.ts` в репозитории, порядок подъёма стенда и грабли — там же.
Первый зелёный прогон 2026-09-21, 26/26.

`npm test` — это другое: юнит-тесты на чистые функции и конфиги, БД и сеть не
трогают.

## Проверено 18.09

- `tsc --noEmit` — 0 ошибок; `npm test` — **12/12** (core 3 — в т.ч. обязательный
  `GAME_UUID`, server 4 — 200/404/500/дубль пути, socket 5 — ping, `data`
  доходит до обработчика, 6 видов нарушения модели, упавший обработчик,
  «stop() закрывает соединение кодом 1001»);
- локальный запуск: `/health` 200, SIGTERM → exit 0; см. «Остановка»;
- контейнер: `healthy` через ~6 с, работает под пользователем `node`, Node
  `v24.21.0`, в образе только `ws`; тесты, `tsconfig`, README в
  образ не попадают (`.dockerignore`);
- `docker compose watch`: правка в `src/` → SIGTERM → штатный stop → старт через
  ~0.5 с; `resources/tests/` из watch исключён.

## Грабли

1. **`docker compose watch` держит эксклюзивный лок проекта**: второй `watch` →
   `cannot take exclusive lock for project`. `compose down` при живом `watch`
   уносит контейнер из-под него.
2. `npm run typecheck | tail` — код возврата будет от `tail`. Проверять
   `npx tsc --noEmit; echo $?`.
3. `pgrep -f '<шаблон>'` внутри `bash -c` находит **сам себя** (шаблон есть в
   собственной командной строке) — цикл `until ! pgrep -f …` вечный.
   18.09 так повисла фоновая задача на 3 минуты.
4. Дефолтные шаблоны `node --test` не видят `*.spec.ts` — поэтому в скрипте
   `test` явный glob. Новый каталог тестов вне `src/resources/tests/` в прогон
   не попадёт.
5. **WebStorm при переносе файла удваивал расширение в импортах** —
   `'#src/config/config.ts.ts'`, причём во всех файлах проекта разом. Причина —
   шаблон алиаса `"#src/*.ts": "./src/*.ts"`: IDE считала `.ts` частью шаблона и
   дописывала его к пути, где оно уже есть. 18.09 алиас заменён на
   `"#src/*": "./src/*"` (для Node и `tsc` это то же самое). Если после
   рефакторинга в IDE `typecheck` сыпет `TS2307 Cannot find module` — первым
   делом `grep -rn "ts\.ts'" src`.
6. Илья правит и двигает файлы в IDE **параллельно с сессией**. Перед правкой
   файла, который давно не читал, — перечитать; сломанное рефакторингом чинить,
   а его раскладку не откатывать.
7. **`node:test` без таймаута висит вечно**, если тест ждёт сообщение, которое не
   придёт. 18.09: Илья убрал приветствие, а хелпер `connect()` в тесте его ждал —
   `npm test` завис, фоновая задача ушла за 120 с. Прогонять `timeout 60 npm test`;
   если повторится — добавить `--test-timeout` в скрипт `test`.
8. **Запущенный через `up -d` контейнер правок не видит** — только после
   `up -d --build` или под `docker compose watch`. 18.09 контейнер Ильи продолжал
   слать уже убранное приветствие.
9. **Python-правка «на месте» обнуляет файл:** `open(p, 'w').write(open(p).read())` —
   `open(p, 'w')` усекает файл **до** чтения. 18.09 так был стёрт
   `socket.config.spec.ts` (тестов стало 10 вместо 21); восстановлен из индекса
   `git show :<путь>`. Писать через `with open(p, 'w') as f: f.write(s)` с заранее
   прочитанным `s`; после правки тестов смотреть на **число** тестов, а не только на
   `fail 0`.

## Открытые вопросы

- [~] **что за игра**: «Хоккеист», Dice RNG — по ТЗ (`DESIGN.md`): проигрыш 1-1/3-3/5-5, RTP 97 %,
      49 раундов, коэффициенты зашиты. Не решено: округление выкупа, таблицы игры
      (экспресс и броски) и команды start/continue/cashout;
- [ ] протокол WS: совместим со сборками старых игр (`auth`/`bet`/`cancel`/`jump`/
      `rates`/`tick`) или новый;
- [ ] коэффициенты/RNG: существующий `calc_service` (Flask) или своё;
- [ ] кто делает фронт игры;
- [ ] seamless (`sess_`-игроки партнёра) с первого дня или позже;
- [x] **деплой** — через Docker Hub и руками, runbook в «Деплой»; dev развёрнут 18.09;
- [ ] прод — не разворачивали;
- [ ] ветки и CI: у остальных репо `develop` → `main`, пуш в `main` = прод.

## Точки стыковки с существующей системой

Подробности и источники — скил `crash-games`.

1. **Игра = строка `games`** в базе API (`id` = `GAME_ID`, `sys_name` unique,
   `type_id`, `link` на сборку, `settings.mode`). Тип игры (`game_types`) задаёт
   параметры алгоритма и `settings.pages`; форма настроек в админке выбирается
   по `typeId` (`'1'` → `CrashGamesForm`, иначе `SlotsForm`) — третий тип
   потребует третьей формы.
2. **Laravel для движка — два эндпоинта без серверной авторизации** (защита —
   только `127.0.0.1`): `GET server/games/{id}/player?token=` и `POST
   server/round` с `action`. Заточены под краш-раунд (`game_crash_rounds`,
   `game_crash_bets`, `AccountService::finishGameCrashRound`). Другая механика =
   свои таблицы и контроллер, как у слотов (`GameSlotBet`, `v1/app/games` →
   `SlotsGameService`).
3. **Токен игрока движок не разбирает**: `authToken` из ссылки — `players.token`
   или `sess_<uuid>`, оба резолвит Laravel (`GameSessionResolver`, шесть мест).
   Новый серверный эндпоинт без резолвера = партнёрские игроки без тиков.
4. **Деньги.** Внутренний игрок — только `TransactionService::makeTransaction`;
   сессионный — только `SeamlessWalletGateway` (`bet` → `accepted/declined/
   not_confirmed`, `win`, `cancel`, `rollback`), гейт
   `GameSession::liveForPlayer()`. Партнёру — minor units.
5. **Инфра старых движков:** pm2 под nvm, процесс на игру, порт `3000+id` (dev
   `4000+id`) на `127.0.0.1`, снаружи `server.<домен>/<gameId>` через nginx
   (конфиг не перечитывали — проверить, общий шаблон или `location` на игру).
6. **CI-образец:** сборка в контейнере → артефакт → `rsync -c` → перезапуск
   только изменившегося. Пуш в `main` = прод без ручного гейта.
7. **`smoke.sh` эту игру не увидит**: список id он берёт из `GAME_ID:` в
   `minigames-server/ecosystem.config.js`, живость меряет сообщением `rates` и
   свежестью `game_crash_rounds`. Нужно дописать (у нас для этого есть `/health`).
8. **Запуск игры:** каталог открывает `game.link + ?authToken=…&bets=2&loaded=true&currency=…`
   в iframe; партнёрская ссылка добавляет `balanceFraction=true&closeIcon=false`.
9. **Живость — API спрашивает движок сам, по запросу админки** (сделано в
   API 18.09, не закоммичено). Движку передаётся **uuid игры** (`games.uuid`,
   не `id`). Адрес движка — `games.engine_url` (задаётся руками, у старых игр
   `NULL`). API делает `GET {engine_url}/health`, таймаут 2 с, и считает игру
   живой, только если ответ 200 и тело `{status:'ok', uptime:<int>}`.
   **`game_uuid` из ответа убран 21.09** (движок `41da07c`, api-core `b523841`):
   сверки игры по `/health` больше нет, `game_uuid_mismatch` не возвращается.
   Сквозная проверка после выкатки 0.1.2 — `alive: true`, 96 мс.

## Чего не повторять из старого движка

| грабля старого движка | что с этим здесь |
|---|---|
| логгер без фильтра уровня, `DEBUG` на каждый тик — 260 МБ/сутки на игру, 15.08 положило прод | `Logger` с порогом, `LOG_LEVEL` — **сделано** |
| `SIGTERM` только логируется, pm2 добивает по таймауту | штатная остановка — **сделано** |
| обработчики без `try/catch`: непойманный reject рвёт раунд всем | `SocketConfig.dispatch` ловит, `main.ts` ловит остальное — **сделано** |
| состояние клиента полями на сокете (`ws.player`), поиск сокета перебором `wss.clients` | с первым сообщением, которому нужен отправитель, — `domain/Client` + `Map<Client, WebSocket>` |
| версия Node не закреплена, ни одного теста | `engines` + образ `node:24-alpine`, `node:test` — **сделано** |
| ставка подтверждается клиенту **до** ответа бэка | помнить при протоколе ставок |
| `all_bets` действует на всех игроков раунда | помнить |
| процессный синглтон с состоянием одного клиента (`GameVersionService`) | состояние клиента — только в `Client` |
| uuid раунда с точностью до секунды; создание раунда каждые 50 мс, когда Laravel молчит | помнить при игровом цикле |
| `bank` — счётчик в памяти процесса, обнуляется рестартом | помнить |
| два POST в Laravel на каждое событие ставки; запрос игрока на анонимных клиентов | помнить при клиенте API |

## Журнал

### 2026-09-18 — старт
Илья создал репо и попросил «стартовый кор и запуск сервера» в формате старого
движка, с контейнером и короткими командами в README. По ходу: перешли с `.mjs`
на TypeScript («давай typescript сразу»), затем переложили код из `core/` в
слои `domain / services / web / resources` («как в котлине или лаки интеграции»),
суффиксы файлов — по роли. Затем Илья сам перенёс `config.ts` и `engine.ts` в
`src/config/`; рефакторинг IDE сломал импорты (грабли №5) — починено, алиас
изменён, перепроверено: `tsc` 0, тесты 6/6, контейнер `healthy`. Следом он же перенёс туда `server.ts` и роутер и попросил назвать
роутер `SocketConfig` (`socket.config.ts`, поле `socketConfig`) — сделано.
Последним шагом: «назови все конфиги .config и основной main.config» —
`config.ts`→`main.config.ts` (`MainConfig`, `loadMainConfig`), `engine.ts`→
`engine.config.ts` (`EngineConfig`), `server.ts`→`server.config.ts`
(`ServerConfig`); тест конфига переехал в `resources/tests/config/`. Затем Илья
сам переименовал `main.config` → `core.config` (`CoreConfig`) и на вопрос
«можно упростить?» велел «убрать всё лишнее и не нужное сейчас» — см. принцип
в «Архитектуре». Последнее за день: «убери пока сокеты совсем» — проект сведён
к HTTP-серверу с `/health`: 4 файла в `src/` без тестов, runtime-зависимостей
нет, `tsc` 0, тесты 4/4. Попутно убран `SHUTDOWN_GRACE_MS` из HTTP (см.
«Остановка»). И сразу: «давай ещё раз отдельным конфигом сделаем сокеты, по
нашей модели» — `config/socket.config.ts` + `web/models/message.ts` +
`web/v1/system.handler.ts` (ping) + тест; таймер вернулся уже в `SocketConfig`
с настоящей причиной. Итог дня: `tsc` 0, тесты 8/8, контейнер `healthy`,
`ping`→`pong` по WS, `down` 0.35 с. Последним — «вынеси в отдельный контроллер
/health»: `web/v1/health.controller.ts`, у `ServerConfig` появился
`get(path, handler)` (404/500 обрабатывает он); тесты 10/10, контейнер
`healthy`. Затем: «не пишем комменты» — вычищены отовсюду; типы перенесены в
файлы своих конфигов, `web/models/` удалена; движок привязан к игре по
`GAME_UUID` (`a2c68a94-…`), `.env` в compose обязателен. `tsc` 0, тесты 11/11,
контейнер `healthy`, в логе старта uuid игры. Под конец `Payload` и
`SocketMessage` слиты в один `SocketMessage`, `ping` перенесён в `SocketConfig`,
`system.handler.ts` удалён. Илья закоммитил ядро (`64ae969 project init`,
ветка `dev`), срезал README до команд, переименовал сервис compose в
`crash-engine-rng`. После коммита приветствие `connected` было добавлено и
сразу убрано Ильёй; тест сокетов возвращён к версии без него. Затем — единая
модель сообщения `{type, data?}` (строгая), тесты 12/12. В индексе. Илья прислал
дизайн «Хоккеист · полный флоу» — верхняя линия наша; разобран в `DESIGN.md`,
экраны нарезаны в `design/screens/`. Затем — связка с админкой: `game_uuid` в
`/health`, движок в сети API (`external`), адрес `http://crash-engine-rng:3100`;
сквозная проверка API → движок `alive: true`. Тесты 12/12.

### 2026-09-23 — `coefficients` вместо `get_coeffs`, `state` без обёртки `game`

Две команды Ильи: «замени get_coeffs на coefficients, чтобы грамматически верно» и «в ответе
state убери "game": {, сразу в data пиши», затем «коммить и пуш, обнови дев» и «и дев ui обнови».
**Коммит `6013e54`** «Rename get_coeffs to coefficients, flatten the state reply and release
0.1.11» (`dev`, запушен). **Выкачено на dev 23.09 ~10:39 UTC** по runbook'у: образ
`arcanegaming/crash-engine-rng:0.1.11` (`docker push` прошёл из сессии), бэкап `.env` в
`~/deploy-backups/crash-engine-rng.env.20260923-*`, `ENGINE_VERSION=0.1.11`, `compose pull && up -d`;
тестовый UI — в `~/crashgames/games/testrng/index.html` (бэкап `~/deploy-backups/testrng-index.html.20260923-*`),
md5 совпал. Проверено: контейнер `healthy` на 0.1.11, `/health` 200 изнутри и снаружи через nginx,
в образе `socket.on('coefficients')` и плоский `state`, лог `Dice Stream connected`,
`RngEngineHealthService` → `alive: true` 159 мс, `dev.games…/testrng/` 200 с новым UI, снаружи
`wss://…/<uuid>/v1?session=bogus` → `Session not found` + 4401. Полную игру на деве не гонял —
нужен настоящий запуск из Lucky.

- Команда сокета `get_coeffs` → **`coefficients`**; ответ как был — массив 49 коэффициентов
  прямо в `data`. Handler переименован в тон домену: `web/v1/coeffs.handler.ts` →
  `coefficients.handler.ts`, `registerCoeffsHandler` → `registerCoefficientsHandler`
  (`git mv`, чтобы IDE не оставила мёртвую запись в индексе).
- `state` → вид игры **прямо в `data`**, без игры — **`data: null`** (по аналогии с
  `history`: «в data не надо "games": [»). `SocketConfig.dispatch` `null` из обработчика
  отдаёт как есть (ответа нет только на `undefined`), так что конверт `{id, type, data}`
  сохраняется. Это второй после `history`/`coefficients` случай, где `data` — не объект.
- Обновлены юнит-тест сокетов, регресс-проба `probes/regress.ts`, тестовый UI
  (`applyGame(msg.data)`; заодно `applyGame` перестал падать на `view.status` при `null` —
  раньше на подключении без игры это давало TypeError в консоли), REGRESS.md и описание
  «Game socket v1» в Apidog (3514439, только поле `description`, сохранённое сообщение
  `continue` в `requestBody` не тронуто). **Грабля:** до этой правки описание там всё ещё
  было со старыми именами (`round_id`, `bet`, «Round view», `Round is busy`), хотя журнал 22.09
  утверждает, что его переписали под `game`/`round`; `updatedAt` было 22.09 17:33 — похоже,
  переписанная версия не сохранилась или её перекрыла ручная правка списка сообщений.
  Сейчас описание приведено к живому протоколу целиком (game_id, round, `win|lose`,
  `history`/`game`, полный список ошибок из кода).
- Проверено: `tsc` 0, `npm test` **40/40**. Живой регресс не гонял.
- **Старый движок не тронут:** в `crash-heroes-backend-game-engine` есть похожий по имени
  HTTP-эндпоинт calc_service `POST /get_coefs` (одна `f`) — это другая вещь, его никто не
  переименовывал.
- **Клиентам игры** (фронт «Хоккеиста», Apidog-сообщения, чужие пробы) при обновлении
  движка нужно перейти на `coefficients` и читать `state` из `data` напрямую — старое имя
  команды теперь отвечает `Unknown message type`.

### 2026-09-22 (вечер) — инфа по броску в админке

Разбор созвона 21.09 с Константином (расшифровка — Google Doc `1Mda81F…`, экспорт лежал
у Ильи в `~/tz-rng.txt`; документ закрыт, забрать может только Илья — мои попытки через
`gcloud auth print-access-token` режет классификатор). Из списка задач созвона Илья выбрал
«данные по броску» и сказал делать **сначала только в админке**, а как должно выглядеть —
смотреть в UI самого дайс-сервиса.

- **Источник данных — свой**: движок с 18.09 пишет всё событие целиком в `game_rng_rounds.roll`,
  api-core отдаёт его в ресурсе. В дайс за историей ходить не нужно, api-core и движок не трогали.
- **Спека дайса** (Apidog, ветка `ai/20260918-from-main-dicestream` 1387874): `GET /api/rolls`,
  `/api/rolls/{roll_id}`, `/api/tables`, `/api/tables/{table_slot_id}`, `/api/generator/*` —
  схемы ответов пустые, Константин обещал добавить. Живой ответ: `roll_id`, `table_slot_id`,
  `table_instance_id`, `sequence_no`, `player_1`/`player_2` (id + name), `active_player_id`,
  `dice_1/2`, `generated_at`, `published_at`, `generator_version`.
- **Образец вида — `https://dicestream.crash-heroes.com/`**: таблица Event stream (GENERATED,
  ROLL, TABLE, PLAYERS, SEQ, RES, новые сверху) и блок Tables с активными партиями.
- **Сделано в админке** (`74e7dc8`, ветка `dev`, CI выкатил): Dice stream — таблица с теми же
  колонками и новыми бросками сверху (закрывает пункт 07:00), автоскролла вниз больше нет;
  в карточке игры у раундов появились Стол, Ход, Участники, «Время броска» теперь
  `generated_at` события; клик по идентификатору броска открывает карточку с полной
  информацией по столу, партии и участникам (активный помечен) — первый шаг к «разделу по
  столу» из пункта 29:23. Файлы: `pages/rng-games/utils/rollEvent.ts`,
  `components/RngRollModal.tsx`.
- **Проверено на деве** глазами (креды админки — у Ильи): поток идёт, у настоящей игры из
  Lucky (проект «Lucky server», 100 USD) видно стол TBL-002, ход 20, участников Luca Reed /
  Milan Cole и карточку броска. Кстати, эта игра — первая полная на деве из настоящего
  запуска Lucky: старт 14:03, брошена, чистка выкупила её в 14:28 на 105.82 USD.
- **Потом (там же 22.09):** команды `history` / `game` и попап истории в тестовом UI —
  раздел «История игр» выше; регресс вырос до 30 проверок, юнит-тесты до 40.
- **Осталось из созвона:** возврат незавершённой ставки (сейчас игра без выигранных раундов
  закрывается как `lost`), срок сессии 30 минут против наших 25, статус `pending` вместо
  `rolling`, обогащение ответа движка данными броска (ждёт полей от Константина), раздел
  «Столы» поверх `GET /api/tables`, переезд структуры Apidog. Переименование «QEF» (так
  Константин прочитал `get_coeffs`) — **сделано 23.09**, команда теперь `coefficients`.

### 2026-09-22 — переименование: игра и раунд

Команда Ильи: «делаем движок, надо переделать все нейминги что тут что в апи в таблцах и
админках: Уровень/level/ставка — round, Раунд/round — game; начни с движка тут и тестового
UI, потом обновляй». Таблица соответствий и разбор по слоям — раздел «Нейминг: игра и
раунд» выше. По ходу Илья попросил поправить и визуал тестового UI, и «обновить весь дев».

- **Движок**: файлы `domain/round.ts` → `game.ts`, `services/round.service.ts` →
  `game.service.ts`, `web/v1/round.handler.ts` → `game.handler.ts`,
  `tests/domain/round.spec.ts` → `game.spec.ts`; протокол `round_id` → `game_id`,
  `bet` → `round`, `state` → `{game}`, ошибки `Game …`. `tsc` 0, тесты 39/39, живой
  регресс 26/26 — дважды: на старых таблицах и после миграции.
- **Тестовый UI**: состояние `game`, «Раунд N» = номер броска, «История игр», пустая
  история больше не показывает кракозябры (`content: '???'` → «пока пусто»). Прокликан
  в браузере на локальном стенде: ставка → бросок → выкуп 105,82, баланс сошёлся.
- **Вопрос, который пришлось решать с Ильёй:** в админке уже был раздел «Игры» (каталог
  `games` с адресом движка), и имя «игра» оказалось занято. Выбран вариант «каталог →
  Движки»: `/rng/engines` + `v2/admin/rng/engines`, а партии игроков заняли `/rng/games`
  и `v2/admin/rng/games`.
- **api-core**: миграция переименования (MySQL 8 `RENAME COLUMN`, применена локально),
  модели/ресурсы/контроллеры/роуты (см. раздел «Нейминг»), `resolved_rng_game` в
  журнале внешних операций. Эндпоинты проверены токеном локально: `rng/engines`,
  `rng/games`, `rng/games/{uuid}` — поля `round`, `rounds_count`, `rounds`, summary `games`.
- **Админка**: `pages/rng-games` → `pages/rng-engines`, `pages/rng-rounds` →
  `pages/rng-games`, очереди запросов, типы, фильтры, подписи («Движки», «Игры», «Раунд»,
  «Раундов»); `tsc` 0, eslint 0. Вживую не смотрел — в браузере нет сессии админки.
- **Apidog**: описание «Game socket v1» (3514439) переписано под новые имена, сохранённое
  сообщение не тронуто.
- **Коммиты и дев** (по команде Ильи «делай коммит и пуш, потом регрес», затем «обнови весь
  дев»): движок `e82d444` (`dev`), api-core `1cef263` (`develop`), админка `58fdadb` (`dev`) —
  запушены. Порядок выкатки: образ **0.1.6** в Docker Hub (на этот раз `docker push` прошёл
  из сессии, классификатор не резал) → CI api-core прокатил миграцию на дев (~11:56 UTC) →
  `ENGINE_VERSION=0.1.6`, `compose pull && up -d` → тестовый UI в `~/crashgames/games/testrng/`
  (бэкап прежнего в `~/deploy-backups/testrng-index.html.*`) → админку CI выкатил сам.
  Проверено на деве: `/health` 200 и `RngEngineHealthService` `alive: true` 112 мс; снаружи
  `wss://dev.server…/<uuid>/v1?session=bogus` → сообщение `Session not found` + 4401; в бандле
  админки `rng/engines` вместо `rng/rounds`; `smoke.sh` — «всё работает». Полную игру на деве
  по-прежнему не прогнать: нужен настоящий запуск из Lucky.

### 2026-09-21 — 0.1.2 на dev, `game_uuid` из `/health` убран

Команда Ильи «коммить и пуш, обнови дев до актуального состояния, и бд». Коммитить
оказалось нечего: `dev` уже был запушен (`41da07c`, 10:17). Зато нашлось расхождение —
этот коммит убрал `game_uuid` из `/health`, а `RngEngineHealthService` в api-core его
сверял строго, то есть выкатка образа как есть показала бы в админке «Не совпал
game_uuid» на живом движке. По выбору Ильи правили сторону api-core.

- api-core **`b523841`** «Stop checking the game uuid in the RNG engine health response»
  (`develop`, запушен, CI выкатил на dev ~09:10 UTC) — ветка `game_uuid_mismatch` удалена.
- движок **`4cf9395`** «Release the engine version 0.1.2» (`dev`, запушен); тесты 39/39,
  `tsc` 0; образ `arcanegaming/crash-engine-rng:0.1.2` собран `--platform linux/amd64`.
- **`docker push` запретил классификатор auto-режима** («Create Public Surface» —
  приватности репо он не видит). Обходить не стал: Илья запушил образ сам по
  `! docker push arcanegaming/crash-engine-rng:0.1.2`, сверено по digest
  `sha256:dc4dfc0e…`. **На будущее: этот шаг runbook'а придётся отдавать Илье**, пока
  нет правила в permissions.
- Выкатка по runbook'у: бэкап `.env` в `~/deploy-backups/crash-engine-rng.env.*`,
  `ENGINE_VERSION=0.1.2`, `docker compose pull && up -d`. Контейнер `healthy` за ~14 с.
- Проверено: `/health` локально и снаружи (`{"status":"ok","uptime":…}` без `game_uuid`),
  лог `Dice Stream connected`, `RngEngineHealthService` → `alive: true` 96 мс,
  WS снаружи `wss://dev.server.crash-heroes.com/<uuid>/v1?session=bogus` → 101, сообщение
  `{"type":"error","data":{"message":"Session not found"}}`, закрытие `4401` (значит
  nginx, путь `/v1` и чтение `game_sessions` из MySQL работают), `smoke.sh` dev зелёный.
- **БД dev трогать не пришлось:** `migrate:status` — всё `Ran`, последняя
  `2026_09_18_100003_create_game_rng_rounds_table` [21]; новых миграций с 18.09 нет.

## 2026-09-24 — `win` с 0 на проигрыш (0.1.12)

Lucky считает комиссию провайдера с проигрыша в момент `win`, поэтому каждая игра обязана закрываться `win`.
`GameService.settleLoss(sessionId, gameUuid)` шлёт `wallet.win(session, 0, uuid, uuid, '1')` при проигрышном
броске (`resolve`) и при автозакрытии брошенной игры без выигранных бросков (`closeAbandoned`); ошибки только
логируются, ретраи — общий `retryDue`. Коммиты `c6d3423` + `0009037 Release 0.1.12` в `dev`, образ
`arcanegaming/crash-engine-rng:0.1.12` выкачен на dev (`ENGINE_VERSION` в `.env`). До выката на деве крутился
0.1.11 — «win с 0 не пришёл» объяснялось именно этим: **CI у репо нет, коммит ≠ выкат**.

## 2026-10-05 — настоящий фронт «Crash Hockey» на проде, подготовка к Lucky prod

Команда Ильи: «перенести на прод движок rng, обновить краши админку и апи, подготовить всё, чтобы на проде крашей
и Лаки можно было играть в новый движок, разрешаю всё».

- **Движок на проде уже был актуален**: 0.1.12 (== `origin/dev`, новых коммитов нет), `healthy`, поток костей
  `wss://dicestream.crash-heroes.com` живой (бросок 13:50:47 UTC), снаружи `…/<uuid>/health` 200 и WS
  `Session not found` + 4401. Перевыкатывать было нечего.
- **Фронт игры**: на деве 05.10 10:16 выложена настоящая сборка «Crash Hockey» (React, 144 файла, 35 МБ;
  **исходников на машине нет** — только сборка). Хост движка зашит в бандл одной строкой
  `var qv={host:"dev.server.crash-heroes.com",publicKey:"<games.uuid>"}` (`scripts/index-*.js`); сессию берёт
  из `?session=` (ровно один параметр). На прод перенесена копией с заменой хоста на `server.crash-heroes.com`
  (uuid на проде тот же). Старый тестовый UI — `~/deploy-backups/crashhockey-testui.20261005-135031.tgz` на проде.
  Проверено: `games.crash-heroes.com/crashhockey/` + JS/CSS/шрифты → 200.
  **Новую сборку с дева на прод переносить так же** (или попросить у авторов сборку с прод-хостом).
- api-core прода == `main` по файлам запуска (`GameLaunchService` для `crash-rng` отдаёт `link?session=<uuid>`).
- В Lucky prod игру 19 через синк не получить (`settings []` → нет в `/api/external/games`); заводится root'ом
  `POST /v1/root/games` (external_id `19`, slug `crash-games-crash-hockey`, category `crash`) и добавляется в
  BroBro. Синк провайдера ручные игры не отключает. Запись на прод Lucky классификатор не дал — скрипт
  `lucky-prod-add-crash-hockey.sh` (scratchpad сессии 05.10) запускает Илья.
- **Итог 05.10 (вечер): игра доступна в BroBro на проде** — `https://brobro.casino/games/1/17`, плитка первой в
  «Crash Games» главной и на `/crashgames` (детали Lucky — скил `lucky-back`, «История» 05.10).
- **Адреса прода «Crash Hockey»:** фронт `https://games.crash-heroes.com/crashhockey/` (оператор получает
  `…/crashhockey?session=<uuid>` из `POST https://api.crash-heroes.com/api/external/game/url`, `game_id` = `19` или
  uuid); WS `wss://server.crash-heroes.com/a2c69d5c-074d-4574-9262-58fce37fba72/v1?session=…`; health
  `https://server.crash-heroes.com/a2c69d5c-…/health`; `engine_url` `http://127.0.0.1:3100`; кости
  `wss://dicestream.crash-heroes.com/ws/events`. **`games.id` 19 и uuid одинаковые на деве и проде.**
- **Обложка** `crash-hockey-site.png` (600×600, скругление 38 px, как у соседних `*-site.png`): собрана из ассетов
  сборки (`assets/ui/loading-background.webp`, кроп y 430–1180, синий градиент снизу, «CRASH HOCKEY» шрифтом
  Inter 900 из `assets/fonts`), лежит в `storage/app/public/games/covers/` api-core **на проде и деве** →
  `https://api.crash-heroes.com/storage/games/covers/crash-hockey-site.png`. Своей обложки у авторов игры нет —
  если пришлют, просто заменить файл.
- Полную игру с реальными деньгами на проде ещё никто не проходил.
