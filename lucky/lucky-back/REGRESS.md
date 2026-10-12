# Регресс интеграции игрового провайдера на живом стенде

Два скрипта в `~/.claude/skills/lucky-back/probes/`, оба печатают PASS/FAIL и
выходят с кодом 1 при любом провале. Ключи не печатают.

| Скрипт | Что проверяет | Что нужно на входе |
|---|---|---|
| `game-provider-regress.mjs` | деньги: `user/info`, `bet`, `win` (в том числе с `cancel`), `rollback` | ключи провайдера + живой launch-токен |
| `provider-catalog-regress.mjs` | каталог и модерация: загрузка, гейт, approve/decline, revoke, удаление рутом | ключи провайдера + Bearer рут-админа |
| `admin-transactions-regress.mjs <env>` | строки списка транзакций админки против кошельков: 21 операция (ручные начисление/списание, ставка, выигрыш, проигрыш, отмена, бонусная ставка, бонусный выигрыш целиком в `cash`, откат) — у каждой новой строки кошелёк, тип, сумма, Balance before/after = сумма счетов этого кошелька, движения по счетам в деталях; цепочка до/после внутри каждого кошелька; история игрока по `balance_code` | стенд `<env>.env` |
| `games-launch-regress.mjs <env> "<провайдер>"…` | живые игры провайдеров: привязывает их к проекту `Regress` скрытыми, по каждой — запуск игроком, демо, ссылка открывается (200). Демо 30/мин — проба ждёт на 429 | стенд `<env>.env`; рут один раз открывает проекту доступ к провайдеру (`POST /v1/root/game-providers/:id/projects`, только добавляет) |

**Контракт сменился 2026-09-11, дважды.** Первой правкой `player/info` и
отдельный `cancel` удалены, появились `user/info`, `win` с флагом `cancel` и
`POST games/{id}/revoke` вместо `DELETE games/{id}`. Второй, вечерней:

- `PATCH games/{id}` (включение и выключение) **удалён целиком**. `is_active`
  теперь только наш, меняется рутом через `PATCH /root/games/{id}`. Вместе с
  эндпоинтом ушли коды `game_revoked` и `game_not_approved`.
- **Отзыв только помечает.** `revoke` ставит `revoked` и больше не делает
  ничего: выключатель, привязки к проектам и плитки на опубликованной главной
  остаются на месте. Игрока это не задевает — гейт `provider_status =
  'approved'` держит и так, — зато вёрстка проекта переживает отзыв.
- Поле сессии называется `session` везде; `sessionToken` и `timestamp` в
  `user/info` больше не принимаются.
- **Запаса после истечения сессии нет.** `user/info`, `bet` и `win` отказывают
  сразу по `expires_at`; у `rollback` срока по-прежнему нет вовсе.

Оба скрипта переписаны под это; прогоны старше 11.09 сравнивать нельзя.

---

## 0. Регресс-стенды dev и prod — ВСЕГДА гонять на них (с 2026-09-24)

Решение Ильи 24.09: на деве и проде заведены изолированные стенды, регресс внутренних и внешних запросов
гоняется **только на них**, живые проекты и провайдер `crash-games` не трогаем. На проде так можно без
отдельной команды: деньги, комиссия и игроки стенда ни с кем не пересекаются.

| Что | На каждой среде |
|---|---|
| проект | `Regress` (slug `regress`), USD, en, свой публичный ключ `pk_…` |
| админ проекта | `regress-admin-<env>@agg.one` |
| провайдер | `Regress Provider` (slug `regress-provider`), своя пара ключей, свой кошелёк комиссии; `api_endpoint` пустой — запуск и демо отвечают `unavailable: true` |
| кабинет провайдера | `regress-provider-<env>@agg.one` |
| игра | `Regress Game` (`external_id` `regress-game`, crash), одобрена и включена, добавлена в проект, **на витрине НЕ показывается** — см. правило ниже |
| игрок | `regress-player-<env>-<время>@agg.one` (актуальный — в `<env>.env`), USD cash; прогон сам доливает 1000, если меньше 200 |
| демо | у проекта стенда `demo_mode: true` (ставит bootstrap), прогон проверяет `features.demo_play_enabled` и гостевое `/demo` |
| комиссия | игра стенда 10%: прогон сам ставит её через кабинет провайдера перед проверкой (все живые игры с 24.09 — 0%) |

**Regress Game никогда не выставляем на витрину** (Илья 28.09: «никогда не выставляем её»). В проекте Regress
она лежит с `project_games.is_active = false`: так она пропадает из главной и каталогов, а запуск, демо и
сессии работают (`GameLaunchService.resolveGame` смотрит только на `public_id` привязки и на `is_active` самой
игры). Выключает её админ проекта: `PATCH /v1/project/games/<game id> {"is_active": false}`. Bootstrap делает это
сам после привязки и падает, если флаг не встал. `regress-run.mjs` проверяет, что на главной стенда её нет.
**Не путать** с `is_active` самой игры (`PATCH /v1/root/games/:id`): его выключать нельзя, иначе запуск отвечает
404. 28.09 выключена через API на обеих средах (dev `54e5b433-…`, prod `00f17856-…`), регресс после этого
dev 22/22, prod 22/22.

**Ключи и пароли** — в `~/.config/lucky-regress/dev.env` и `prod.env` (права 600, вне git): `LUCKY_API`,
`PROJECT_ID`, `PUBLIC_KEY`, `PROVIDER_ID`, `PROVIDER_PUBLIC_KEY`, `PROVIDER_PRIVATE_KEY`, `GAME_ID`, `PROVIDER_PID`,
`GAME_PID`, `ADMIN_*`, `PLAYER_*`, `CABINET_*`. В этот файл скила значения не пишем: скилы синкаются в
git-репо `work-skills`. Скрипты читают файл сами и ничего секретного не печатают.

**Заведены 24.09 на обеих средах** (dev: проект `c92bbb8d-…`, провайдер `54817a3f-…`; prod: проект `2794c183-…`,
провайдер `0735d2f0-…`). Первые прогоны: dev 19/19, prod 19/19 (денежный регресс 29/29, комиссия 1.00 / 0.60 / нет / нет).

**Служебный рут** — `regress-root@agg.one` на деве и проде, заведён ради bootstrap. Пароль нигде не хранится:
перед повторным bootstrap ему ставится новый случайный прямо в той же команде (в контейнере API
`hashPassword` из `/app/dist/modules/auth/passwords.js` + `UPDATE root_admins SET password_hash … WHERE email =
'regress-root@agg.one'` через `pg`, как 24.09 на деве; на проде контейнер `luckyserver-api-1` на `lucky-prod-legacy`).
`create-root-admin.js` второй раз не сработает — пользователь уже есть.

**Пересоздать или починить стенд:** `regress-bootstrap.mjs` повторяемый — находит проект, провайдера, админов и игру
по slug/почте, активирует проект (публичный ключ работает только у `active`, новый проект — `draft`), выпускает
новый публичный ключ и пару ключей провайдера, меняет пароли админов, регистрирует нового игрока
`regress-player-<env>-<время>@agg.one` и переписывает `<env>.env`. Вручную Илья может запустить
`! bash ~/.claude/skills/lucky-back/probes/regress-bootstrap.sh <env>` со своим рутом.

**Прогон (сколько угодно раз):**

    node ~/.claude/skills/lucky-back/probes/regress-run.mjs dev
    node ~/.claude/skills/lucky-back/probes/regress-run.mjs prod

Что проверяет: health; вход игрока, админа проекта и кабинета провайдера; балансы; обычный запуск и
гостевое демо (с ключом и без); игровая сессия; `user/info` с `locale`; весь денежный регресс
`game-provider-regress.mjs`; комиссию на проигрыше по кабинету провайдера (проигрыш 10.00 → 1.00, частичный
10.00/4.00 → 0.60, выигрыш и отмена → нет записи). Код выхода 1 при любом FAIL.

**Граничные случаи** — `node ~/.claude/skills/lucky-back/probes/regress-edge.mjs dev|prod`: повторы после
потерянного ответа (bet/win/cancel/rollback ×3, повтор через паузу, другой порядок ключей, тот же `txId` с
другими полями, 10 параллельных), дубли по смыслу (второй bet/SettleBet по одному `betId`, отмена после выигрыша,
отмена больше ставки, отмена и выигрыш без ставки), порядок (откат раньше выигрыша, откат закрытой ставки,
параллельные откат и выигрыш), сессии (только dev: сессия стенда «стареет» `UPDATE game_sessions …` через psql),
кривые суммы и граница баланса, переигрывание подписи. Строки `[rule?]` проверяют ещё не принятое правило
(поведение Aviatrix). Первый прогон 24.09 на деве — 22/36; после фикса `d2190c9` — dev 31/36, prod 27/32 (на проде нет
блока про сессии). Разбор в `SKILL.md`, «Журнал 2026-09-24». Есть и стенд `local` (`regress-bootstrap.mjs local`, API на
`127.0.0.1:18080`, служебный рут `regress-root-local@agg.one`) — гонять пробы до коммита.

## 1. Деньги — `game-provider-regress.mjs`

22 проверки. Вход — файл из трёх строк: `public_key` провайдера,
`private_key` провайдера, `launch_token` живой сессии. Сессия должна быть
**живой**: с 11.09 запаса после `expires_at` нет, просроченная сессия валит
прогон на нулевой проверке.

| № | Проверка | Ожидание |
|---|---|---|
| 0, 22 | `user/info` до и после | 200, баланс сходится с расчётом по шагам |
| 1–4 | ставка, повтор, повтор с другой суммой, выигрыш | 201 / тот же ответ / 409 `idempotency_conflict` / 201 |
| 5–6 | ставка и отмена (`win` + `cancel:true`) | деньги вернулись |
| 7–9 | ставка, откат, повтор отката | `reversed:true`, повтор отдаёт тот же ответ |
| 10–11 | откат неизвестной операции, опоздавшая ставка | 201 `reversed:false`, затем 409 `already_rolled_back` |
| 12 | откат **отмены** | списывает обратно, а не зачисляет второй раз |
| 13 | откат **выигрыша** | списывает выигрыш |
| 14–15 | лишнее поле в теле | подписано целиком → 400 `invalid_request`; подписаны только известные поля → 401 `invalid_signature` |
| 16–17 | сумма из 31 цифры, битый JSON | 400 `invalid_request`, не 500 |
| 18–20 | неверная подпись, без заголовков, чужой токен | 401 / 401 `missing_signature` / 404 `unknown_session` |
| 21 | пять одинаковых ставок параллельно | один `processedTxId`, списание одно |
| 21a–21c | `origin` в ответе | поля провайдера на месте, токена сессии нет, повтор отдаёт записанный первым |

### Порядок запуска на деве (пройден целиком 2026-09-11)

Гонять можно **с локальной машины**, ничего на сервер копировать не нужно —
скрипт ходит по HTTPS. Проект один: `storefront-luckyserver-pro` (он же «BroBro
Casino»), только у него подключён провайдер и добавлены игры.

1. **Ключи провайдера.** Приватный ключ у нас зашифрован, но та же пара лежит на
   стороне крашей — оттуда и брать, не печатая:
   ```bash
   ssh crash-dev 'cd ~/crashgames/minigames-admin-back && php artisan tinker --execute="
     \$p = \App\Models\Project::where(\"api_user_info\",\"like\",\"%luckyserver%\")->first();
     echo \$p->api_key.PHP_EOL.\$p->api_secret.PHP_EOL;"' > /tmp/keys
   ```
2. **Публичный ключ проекта** (браузерный `pk_…`, не секрет):
   ```sql
   select k.key_id from project_api_keys k join projects p on p.id=k.project_id
   where p.slug='storefront-luckyserver-pro' and k.key_type='public_client' and k.revoked_at is null limit 1;
   ```
3. **Тестовый игрок.** Не гонять на живых: у `test999@agg.one` уже размазана история.
   `POST /v1/auth/register` с `X-Public-Key` → `access_token`, id сразу в `client.id`.
   Тело: `{locale, currency, email, password, password_confirmation}` — без `currency`
   ответ `INVALID_CURRENCY`, а не ошибка валидации, и это сбивает.
4. **Пополнить** через проект-админа `brobro-admin@luckyserver.pro` (пароль —
   `lucky-infra/storefront/CONTEXT.md`), логин `POST /v1/project/auth/login`:
   `POST /v1/project/finance/users/<clientId>/transactions`
   `{"direction":"credit","amount":"1000","currency":"USD","balance_code":"cash","comment":"…"}` → 201.
   Поле комментария называется **`comment`**, не `note`: с `note` приходит 400 `property note should not exist`,
   игрок остаётся с нулём, и первая же ставка валит прогон на `insufficient_funds` (наступал 23.09).
   Impersonate рутом не подходит — 403.
5. **Сессия.** Проще не `launch` (он требует, чтобы провайдер ответил ссылкой), а
   отладочный роут. С 11.09 он носит авторизацию самого запуска:
   `POST /v1/core/providers/<providerPublicId>/games/<gamePublicId>/sessions`
   с `X-Public-Key` и Bearer **игрока** (не проект-админа), id в пути, **тела нет**
   → 201 `{session}`. Сессия выписывается на того, кто зовёт, и ни на кого больше.
   Важно: не слать `Content-Type: application/json` без тела — Fastify ответит
   `400 Body cannot be empty`. Пары id взять так:
   ```sql
   select pgp.public_id as provider_pid, pg.public_id as game_pid, g.title
   from project_games pg join game_provider_games g on g.id=pg.game_id
   join projects p on p.id=pg.project_id
   join project_game_providers pgp on pgp.project_id=p.id and pgp.game_provider_id=g.game_provider_id
   where p.slug='storefront-luckyserver-pro' and pg.is_active order by pg.public_id;
   ```
6. **Вход** — файл из трёх строк: публичный ключ, приватный ключ, `session`.
   **Прогнать**: `LUCKY_API=https://dev2.api.luckyserver.pro node probes/game-provider-regress.mjs <input>`.

Если что-то собирать SQL-ом через ssh: кавычки не экранируются, только файлом —
`scp q.sql lucky-dev:/tmp/ && ssh lucky-dev '… psql … < /tmp/q.sql'`.

---

## 2. Каталог и модерация — `provider-catalog-regress.mjs`

30 проверок (16 без рут-токена). Вход — три строки: `public_key`, `private_key`, Bearer рут-админа.
Переменные: `LUCKY_API` (по умолчанию `http://localhost:18080`), `PROVIDER_ID`
(включает проверку каталога проекта), `PLAYED_GAME_ID` (включает проверку 25).

Скрипт заводит собственные игры `regress-<метка>-*` и **убирает их за собой**,
чужих не трогает.

| № | Проверка | Ожидание |
|---|---|---|
| 01–03a | загрузка новой игры, повтор | 201; игра приезжает `pending` и выключенной; повтор меняет имя, статус не трогает |
| 04–07 | категория провайдера, без `cover_url`, дубль `providerId`, пустой список | 400 `invalid_request` |
| 08 | `PATCH games/{id}` провайдером | 404 — выключателя у провайдера больше нет |
| 10 | игра до одобрения в каталоге проекта | `is_available: false` |
| 11 | approve | `approved`, но `is_active` **не трогается**: одобрение и включение — разные решения |
| 12–12a | рут включает одобренную | 200, игра действительно включилась |
| 13–14 | decline, затем попытка включить рутом | `declined` + выключена / 409 |
| 15–16 | decline → approve, неизвестный статус | 201 / 400 |
| 17–18a | revoke, повтор, пустой объект вместо пустого тела | 200; строка на месте со `status: revoked`, **выключатель тот же, что был до отзыва** |
| 19–21 | revoke чужого id, отозванная в каталоге проекта, модерировать отозванную | 404 `unknown_game` / `is_available: false` / 409 |
| 22–22a | перезаливка отозванной | поля обновились, статус остался `revoked` |
| 23–24 | удаление рутом, повторное удаление | 204 / 404 |
| 25 | удаление **сыгранной** игры (только с `PLAYED_GAME_ID`) | 204, сессии уходят вместе с игрой |

### Как собрать вход локально

```bash
printf '<пароль>' | npm run root-admin:reset-local -- --email admin@local.test   # NODE_ENV=development
TOKEN=$(curl -s -X POST localhost:18080/v1/root/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@local.test","password":"<пароль>"}' | jq -r .access_token)
curl -s -X POST localhost:18080/v1/root/game-providers/<PROVIDER_ID>/keys -H "Authorization: Bearer $TOKEN" \
  | jq -r '.public_key, .private_key' > /tmp/catalog-input
echo "$TOKEN" >> /tmp/catalog-input
PROVIDER_ID=<uuid> node probes/provider-catalog-regress.mjs /tmp/catalog-input
```

Приватный ключ отдаётся **только** в ответе на выпуск — перевыпуск рвёт
интеграцию до вставки новой пары у партнёра, на живом стенде так не делать.

### Проверка 25: игра с сессиями

Ради неё нужна игра, на которую ссылается `game_sessions`. Локально фикстура
собирается SQL-файлом (кавычки через ssh не переживают):

```sql
insert into game_sessions (launch_token, project_id, client_id, game_id, expires_at)
select 'regress-' || substr(md5(random()::text),1,12), c.project_id, c.id, '<GAME_ID>', now() + interval '30 minutes'
from clients c limit 1;
```

Клиента при необходимости завести так же: `insert into clients (project_id, email)
values ('<PROJECT>', 'regress@local.test');` — без `email` падает `CHK_clients_identity`.

---

## Кабинет провайдера на деве (с 2026-09-23)

У провайдера `crash-games` на деве заведён аккаунт кабинета `provider@luckyserver.pro`
(вставлен SQL-ом 23.09, хеш из `dist/modules/auth/passwords.js`; пароль сменить из рутовой
вкладки Accounts или тем же SQL). Через него: `POST /v1/provider/auth/login`, `GET /v1/provider/overview`,
`/wallets`, `/wallet-transactions`. Прогон денежного регресса 23.09 прошёл 29/29 и начислил комиссию в
кошелёк провайдера (10% на Test_RNG) — это и есть живая проверка накопления.

## Прод (прогон 2026-09-23, 29/29) — на живых проектах БОЛЬШЕ НЕ ГОНЯТЬ, только на стенде из раздела 0

**С 23.09 прод — живая площадка с реальными игроками. Денежный регресс на проде запрещён без отдельной
команды Ильи** (см. `SKILL.md`, «Прод — живая площадка»). Ниже — как это делалось в последний раз, для истории
и на случай явного указания.

Хост прод-API и БД — `ssh lucky-prod-legacy` (178.105.17.213), контейнер `luckyserver-postgres-1`;
`lucky-prod` (144.31.40.52) это только статика витрины, базы там нет. Ключи провайдера — на `crash-prod`,
проект `\App\Models\Project::find(2)` («Lucky server»). Публичный ключ `brobro-casino` берётся тем же SQL,
что на деве, крашевые игры под `provider_pid=1` (Beer Fest — `1/16`). Проект-админа нет, посев баланса —
подписанный `win`, и с 23.09 у него есть побочный эффект: **комиссия провайдера списывается в его кошелёк**
(10% от посева). Сеять по минимуму, регрессу хватает 500 минорных единиц (5.00 USD): минус 0.50 в кошельке
`crash-games`, ставки регресса возвращают часть обратно. Не сеять тысячи.

## Ручной выкат, когда раннер GitLab не работает (23.09, 24.09)

**API** (один образ на прод и дев, если `dev` == `master` по коду):
```bash
cd ~/Documents/Work/Lucky/lucky-api && git checkout master && git pull --ff-only && make build && git checkout dev
# теги: api-<sha>, api-latest (прод), api-latest-dev (дев); push в Docker Hub отсюда не работает (denied)
docker save luckyserveragg/luckyserver:api-latest     | gzip -1 | ssh lucky-prod-legacy 'gunzip | docker load'
ssh lucky-prod-legacy 'cd ~/luckyserver && docker compose up -d'          # migrate → api, проверить (healthy)
docker save luckyserveragg/luckyserver:api-latest-dev | gzip -1 | ssh lucky-dev 'gunzip | docker load'
ssh lucky-dev 'cd ~/luckyserver-dev && docker compose up -d'
```
Проверка: `docker ps -a | grep -E "(api|migrate)-1"`, `docker logs <migrate>` («Applied N migration(s)»),
`docker inspect -f '{{.Created}}' <api>`. Образ distroless — код проверять `docker exec … node -e`.

**Админка** — то же, что `.deploy` в `.gitlab-ci.yml`:
```bash
npm run build:prod   # для дева: build:dev
mkdir -p dist-deploy && cp -r dist dist-deploy/dist && cp server.js dist-deploy/server.js
tar -C dist-deploy -cf - . | ssh lucky-prod-legacy "set -e; A=lucky-admin; rm -rf \$A/app.new \$A/app.old; mkdir -p \$A/app.new; tar -C \$A/app.new -xf -; [ -d \$A/app ] && mv \$A/app \$A/app.old; mv \$A/app.new \$A/app; rm -rf \$A/app.old; XDG_RUNTIME_DIR=/run/user/\$(id -u) systemctl --user restart lucky-admin"
# дев: хост lucky-dev, A=lucky-admin-dev, юнит lucky-admin-dev. На прод-хосте тоже есть СТАРЫЙ lucky-admin-dev — не трогать.
```
Проверка: новый `index-*.js` в `https://admin.luckyserver.pro/`; страницы — ленивые чанки (`PageProjectDetail-*.js`),
искать строку в них, а не во входном файле.

**Как понять, что новый код уже работает, без доступа к GitLab:** по поведению (например, `win` 0 без ставки →
`bet_not_found`; bootstrap стенда `demo_play_enabled`), либо время создания контейнера против времени пуша.

## Грабли

- **Пустое тело при `application/json`.** `POST games/{id}/revoke` тела не имеет.
  Клиент, который всегда ставит `Content-Type: application/json`, получит
  `400 invalid_request` от Fastify («Body cannot be empty…»). Либо не ставить
  заголовок, либо слать `{}` — проверка 18a закрепляет оба пути.
- **Отзыв больше не убирает игру с витрины.** С 11.09 гейт пропускает `approved`
  **и** `revoked`: отозванная игра остаётся у проектов, на витрине и запускается.
  Держит гейт только `pending` и `declined`. Список один на всех — `OFFERED_GAME_STATUSES`
  в `src/modules/catalog/offered-game-statuses.ts`, руками статусы больше нигде не пишутся.
- **Перезаливка не двигает модерацию.** `sync` обновляет поля и не трогает
  `provider_status`: спрятать игру связкой «отозвать и залить снова» нельзя.
  Обратная сторона — у `revoked` сейчас нет выхода, `moderate` отозванную игру
  отбивает с 409.
- **Отзыв ничего не сносит.** До 11.09 `revoke` гасил игру и удалял её плитки из
  опубликованной главной каждого проекта — вёрстку приходилось собирать заново.
  Теперь он только помечает строку; что плитки переживают отзыв, закреплено
  юнит-тестом в `provider-games.service.spec.ts`, живой пробой это не покрыто
  (нужен проект с публикацией).
- **Гейт живёт в четырёх местах**, и они не связаны между собой: каталог проекта
  (`eligibleProjectGames`), расчёт `is_available`, джойны витрины в
  `public-content-contract.service.ts` и резолв при запуске игры. 11.09 дыра была
  ровно в том, что в первых двух гейт стоял, а в последних двух — нет.
- **Прогон на деве меняет данные.** Скрипт убирает свои игры, но проверки 11–15
  трогают модерацию, а 23–25 удаляют. На стенде с живыми проектами это заметно.
- **Порядок ключей в `jsonb` не сохраняется.** Ответ лежит в `metadata.response`,
  Postgres переупорядочивает ключи, и повтор отдаёт `origin` в другом порядке при
  том же содержимом. Сравнивать ответы только рекурсивно — побайтовое сравнение
  даёт ложный FAIL (наступал 11.09).
- **На проде нет проект-админа.** У боевого проекта `brobro-casino` его просто не
  завели (см. `lucky-infra/storefront/CONTEXT.md`), поэтому ручной транзакцией
  игрока там не пополнить, а рут-токен прода недоступен. Рабочий обход: посадить
  баланс обычным провайдерским `win` на нужную сумму — он идёт через ту же
  финансовую механику и оставляет нормальную запись, в отличие от SQL-вставки в
  кошелёк, которую делать нельзя. Цепочка целиком: register → сессия отладочным
  роутом → `win`-посев → прогон.
- **Публичные ключи проектов**: дев `storefront-luckyserver-pro`, прод
  `brobro-casino`. Пары `provider_pid`/`game_pid` для прода брать тем же SQL, но с
  фильтром по `game_provider_id` нужного провайдера: у боевого проекта несколько
  провайдеров, и у каждого своя нумерация.
- **Рут-токен дева достать нельзя** — пароль в ansible-vault, а его чтение
  блокирует классификатор авто-режима. Либо Илья отдаёт токен, либо каталожный
  регресс гоняется без третьей строки (провайдерская половина, 18 проверок).

## Последние зелёные прогоны

- 2026-10-12, **дев и прод** — `games-launch-regress.mjs prod "Red Eagle" "Donkey Rush"` **104/104**, `regress-run.mjs` **30/30** на обоих стендах. Дев без рута стенда: одноразовый игрок BroBro dev (`POST /v1/auth/register`, валюта регистрации там `RUB`, `USD` отвечает `INVALID_CURRENCY`) запускает все 10 игр проекта (9 Crash-Games + Donkey Rush) — ссылки 200; демо у BroBro dev выключено (`DEMO_DISABLED`, настройка проекта). Regress на деве имеет доступ только к `Regress Provider`; открыть `Crash-Games`/`donkey-rush` нужен рут (`POST /v1/root/game-providers/:id/projects`), сброс пароля `regress-root@agg.one` через контейнер классификатор авто-режима блокирует. Найдено и починено: гостевое демо любой игры Crash Games на проде падало `502 Provider responded with status 400: Invalid request` — старый роут крашей `game/url` требовал `session`; с `api-core` `88b4de2` (main) демо открывается (Beer Fest 201 → 200). Hockey Strike (crash-rng) вдобавок требует демо в самом движке — `game-engine-rng` 0.1.14 (`45efe66`), на деве выкачен и проверен по WebSocket, на прод катится руками.
- 2026-10-12 вечер, **дев и прод** (регресс игр, ставок и кошельков по команде Ильи): `regress-run` 30/30 и 30/30, `games-launch-regress prod` 104/104, BroBro dev 10/10 запусков, `wallet-rules-regress` 14/14 на обоих, `regress-edge` dev 31/36 и prod 27/32 (ровно базовая линия 24.09: четыре `[rule?]` и `bet amount "00100"`), `admin-transactions-regress` 24/24 на обоих **после правки пробы**: с `2477781` (06.10 вечером, «List the account a win's stake came from») строка выигрыша в `entries` несёт ещё и проводку ставки с другого счёта (например `cash/pending −10` при выплате в `available`), поэтому для `win` проба суммирует только неотрицательные проводки; до правки она падала на «win 15 on cash: entries move 5 != 15» на обеих средах.

- 2026-10-06, **дев и прод**, `admin-transactions-regress.mjs` — **24/24** на обоих, `wallet-rules-regress.mjs` (переписан под «бонусный выигрыш целиком в cash available») — **14/14** на обоих. API `7d5a792` / `1ffff50`: Balance before/after в админке — баланс кошелька строки (сумма его счетов), кошельки не складываются. Строки до выката (до 06.10 ~14:00 UTC) показывают старый расчёт по одному счёту — на деве откат 05.10 с суммой 0 рисуется `0.00 → 0.00`.

- 2026-10-05, **прод**, `games-launch-regress.mjs prod "Red Eagle" "Donkey Rush"` — **104/104** (103 Red Eagle + Donkey Rush): запуск игроком, демо, ссылка 200. Проекту `Regress` открыт доступ к обоим провайдерам, игры привязаны с `is_active = false`.

- 2026-09-14, дев, крашевый `25d9a68` — деньги **29/29** на игроке
  `regress-1789…@agg.one` (проект BroBro Casino / `storefront-luckyserver-pro`,
  пополнен 1000 USD через проект-админа). Каталог и модерация **16/16**
  (провайдерская половина, без рут-токена). Прогон после того, как краши стали
  принимать поле `session` в `/game/url` (см. крашевый скил, журнал 14.09).
  Провайдер на Lucky dev — `crash-games` id `5898787c-8120-44e2-8aec-83c26a5cc2d6`,
  пары id: `provider_pid 1` / `game_pid 3` (Beer Fest) и далее. Осталась
  отозванная проба `35e1ff2a-277d-4ae6-8956-91ff48bc06d5` — удалить рутом,
  когда будет токен; тестовый игрок с ~30 операциями остаётся в дев-книгах.
  Прод не гоняли (денежная проба оставляет фейкового игрока в боевых книгах —
  делать только по отдельной просьбе).

- 2026-09-11 вечер, дев, `01e10bb` — деньги **29/29** на игроке
  `regress-1789140…@agg.one` (BroBro Casino, 1000 USD). Первый прогон после того,
  как поле сессии стало только `session`, а запас после `expires_at` убрали.
- 2026-09-11, дев, `0e4fcae` — деньги **29/29** на игроке `regress-1789127189@agg.one`
  (проект BroBro Casino, пополнен на 1000 USD). Прогон оставляет после себя
  историю: 13 ставок, 12 отмен, 4 выигрыша — удобно смотреть в админке.
- 2026-09-11 вечер, дев, `538cd5c` — каталог **16/16** на пробе, переписанной под
  гейт с `revoked` и под `sync`, который не двигает модерацию. Осталась проба
  `f984311d-61c2-42ba-82ef-72f586638a1f`. На проде та же сборка проверена точечно:
  отзыв и перезаливка оставляют `revoked`.
- 2026-09-11 вечер, **прод** — деньги **29/29** на игроке
  `regress-probe-1789145677@agg.one` (проект `brobro-casino`, игра `provider_pid 1`
  / `game_pid 2` «Breeze Tease»). Прогон оставляет в боевых книгах фейкового
  игрока, посевной `win` на 50 USD и около тридцати операций; итоговый баланс 47.50.
- 2026-09-11 вечер, **прод**, `bd4eb9c` — каталог и модерация **16/16**
  (провайдерская половина). Ключи боевого провайдера — проект `2` «Lucky server»
  на `crash-prod`, там же, где девовские, но в другом проекте. Осталась отозванная
  проба `3ee5de49-2856-4534-adeb-5db0135f1868` — удалить рутом. Боевой прогон
  заводит ровно одну игру: приезжает `pending` и выключенной, игрокам не видна.
- 2026-09-11 вечер, дев, `01e10bb` — каталог и модерация **16/16** (провайдерская
  половина, без рут-токена), первый прогон после удаления `PATCH games/{id}`.
  Проверки 08 (эндпоинта нет → 404) и 17a (отзыв не трогает выключатель) — ровно
  про эту правку. Осталась отозванная проба `9842799a-156e-42c2-a968-81f00e65830a`:
  удалить рутом, когда будет токен.
- 2026-09-11, дев — каталог и модерация **18/18** (провайдерская половина, без рут-токена);
  нумерация та, что была до удаления эндпоинта.
- 2026-09-11, локально, `b598e74` — каталог и модерация **30/30**, вместе с
  удалением сыгранной игры.

**Откаты в админке видны как `rollback`** — с 11.09 у них свой тип транзакции
(миграция `1721700115000`), метаданные `rollback_of` и `reversed` остались.
