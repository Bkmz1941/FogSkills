# Lucky — бэк (API)

## Репозиторий

`~/Documents/Work/Lucky/lucky-api` (в GitLab — `lucky/luckyserverpro`) —
обычное NestJS + Fastify + TypeORM приложение (Postgres). Бизнес-модули в
`src/modules/{auth,catalog,clients,content,front,health,integrations,projects,transactions}`,
инфраструктура в `src/config` и `src/database`, контракт-типы в
`src/shared/index.ts` (копируются в lucky-admin). Монорепа распущена
2026-08-12; вся обвязка (docs, deploy/ansible, infra, tools) в `others/`.
Свой CLAUDE.md + `others/docs/` — читать их, не переизобретать. Ветка `dev`
→ дев-деплой.

С 2026-08-13 рантайм — **Node.js 24 + npm** (Bun убран полностью: скрипты
`node`/`node --env-file=.env`, `package-lock.json` вместо `bun.lock`, образы
`dhi.io/node:24-debian13(-dev)`, verify-джоба CI на `node:24`). Команды —
`npm install` / `npm run build|dev|test|typecheck|lint|migration:run`.
Зафиксированные при переезде версии: `fastify@5.11.0` (точный пин — иначе
задваиваются типы с `@nestjs/platform-fastify`), `@fastify/static@^10`,
override `js-yaml@^5.2.2` под `@nestjs/swagger`.

**Чекаут/БД старше 2026-08-13 не апгрейдится**: история миграций сквошнута —
локальную базу пересоздать (`docker compose down -v` → `up -d postgres` →
`npm run build` → `npm run migration:run`, сиды нальют валюты и root-админа),
`node_modules` удалить и поставить npm-ом, в `.env` обязателен
`AUTH_JWT_SECRET` (≥32 символов). Подробный порядок — в верхнем блоке
`CHANGELOG.md` репозитория.

## Стек на сервере

`~/luckyserver-dev/` — docker compose:

- `postgres` — postgres:16-bookworm, 127.0.0.1:5433, volume
  `luckyserver-dev-postgres-data`
- `migrate` — one-shot, накатывает миграции, api ждёт его успешного выхода
- `api` — 127.0.0.1:8081, healthcheck `/v1/health`

Образ `luckyserveragg/luckyserver:api-latest-dev` (приватный Docker Hub,
login на сервере настроен). Конфиг — `.env` рядом с compose (значения не
выводить). Аплоады: bind-mount `/var/lib/luckyserver-dev/uploads`
(владелец **uid 1000** — юзер node-образа; было 65532 до переезда с Bun,
при EACCES на загрузке лого — проверить chown), nginx отдаёт их по
`dev2.api.../uploads/`. В `.env` обязателен
`PUBLIC_API_URL=https://dev2.api.luckyserver.pro` — иначе ссылки на аплоады
собираются как `http://` (за nginx `request.protocol` = http) и публичный
bootstrap их отбрасывает (`safeAssetUrl` пускает только https).

Перезапуск/обновление: `cd ~/luckyserver-dev && docker compose up -d`
(pull новых образов — `docker compose pull` перед этим).

**Дев-диск забивается образами — деплой падает на pull.** 2026-09-10 джоба
`deploy_dev` упала на шаге «Pull API image»:
`failed to extract layer … no space left on device`. Диск был на 93% (38 ГБ
всего), при этом `docker system df` показывал 130 образов, 31.6 ГБ, из них
**29.25 ГБ мусорных (92%)** — висячие образы от каждой сборки CI; основной объём
лежит в `/var/lib/containerd` (26 ГБ), а не в `/var/lib/docker`. Лечится
`docker system prune` (93% → 57%), после чего деплой доводится руками:
`cd ~/luckyserver-dev && docker compose pull && docker compose up -d` — образ CI
уже собрал и запушил, повторять сборку не нужно. После полного цикла стало 27%.
Диагностика: `df -h /`, `docker system df`, `sudo du -sh /var/lib/containerd`.
Прод в тот же день был чист (150 ГБ, 20%), витрина 79 ГБ, 7% — проблема только
дев-специфичная, из-за частых сборок на маленьком диске.

## CI (gitlab.agg.one, lucky/luckyserverpro)

verify → build (образ `api-latest-dev` → Docker Hub) → deploy (ansible).
Прод: ветка **`master`** → `build_prod` (`api-<sha>` + `api-latest`) →
`deploy_prod` (`--limit luckyserver_prod`).

- `deploy_dev`/`deploy_prod` объявляют environments `dev`/`prod`; на них
  скоупятся `SSH_PRIVATE_KEY_BASE64` (deploy-ключ) и **`SERVER_HOST`** (с
  2026-08-21, коммит `a8b9a0d`: dev → 178.104.243.232, **prod → 178.105.17.213**;
  передаётся как `ansible_host` и перекрывает vault-инвентарь — в нём тот же
  прод-хост, коммит `24c2e3e`). `DEV_DEPLOY_HOST`/`SERVER_HOST_PROD` убраны.
  Прод-стек на 178.105.17.213: `~/luckyserver/`, 127.0.0.1:8080/5432, БД чистая
  с 21.08 (легаси-БД рядом `luckyserver_legacy_20260821-1301` + дамп в
  `~/backups/`), root-админ засижен из vault. Подробно — `prod/CONTEXT.md`.
- Раннер k8s: `/builds` world-writable → ansible **игнорирует ansible.cfg**,
  поэтому `ANSIBLE_HOST_KEY_CHECKING: "False"` задан в variables джобы — не
  убирать.
- **Пайплайн дева может молча не доехать.** 10.09 две подряд правки на `dev`
  (15:31 и 15:32) не дали нового образа: тег `api-latest-dev` в Docker Hub
  остался от предыдущего коммита, `docker compose pull` тянул тот же дайджест,
  и дев продолжал отдавать старый контракт, пока прод уже был новым. `default:
  interruptible: true` гасит пайплайн предыдущего пуша, так что частые пуши в
  `dev` — штатный способ это словить.
  **Как проверить**, что дев реально на нужном коде: не по `/v1/health`
  (там версия из `package.json`, а не sha) и не по `docker image inspect`
  (метки коммита не проставляются), а **по маршруту**, который появился или
  исчез в нужном коммите: `404` против `401` отличает «нет роута» от «роут
  есть, гард отбил». Сводно — сравнить наборы путей `/docs-json` дева и прода.
  **Как починить без пуша**, когда `dev` и `master` содержат одинаковый `src/`
  (проверить: `git diff origin/dev origin/master -- src/` пусто) и между
  коммитами нет новых миграций: на дев-сервере взять прод-образ и надеть на
  дев-тег —
  ```bash
  docker pull luckyserveragg/luckyserver:api-latest
  docker tag  luckyserveragg/luckyserver:api-latest \
              luckyserveragg/luckyserver:api-latest-dev
  cd /home/admin/luckyserver-dev && docker compose up -d --no-deps api
  ```
  Следующий успешный `build_dev` перезапишет тег сам. Пересобрать образ
  локально нельзя: база — `dhi.io/node:24-debian13` (Docker Hardened Images),
  нужен `docker login dhi.io` с CI-кредами.

## Ansible (`others/deploy/ansible`)

- `hosts.yaml` и `group_vars/*/vault.yaml` — vault-encrypted
  (`luckyserver_dev` → 178.104.243.232, `luckyserver_prod` → 178.105.17.213;
  CI перекрывает `SERVER_HOST` тем же значением). Плейновые переменные —
  `group_vars/dev/main.yaml` и (с 21.08) `group_vars/prod/main.yaml`
  (`app_version`, `public_api_url`; бывший `group_vars/prod.yaml` переехал в
  `group_vars/prod/vault.yaml`). Админ-контейнера в деплое больше нет вообще —
  вырезан 2026-08-12. Прод-vault: `root_dir /home/admin/luckyserver`, порты
  5432/8080, `storage_dir /var/lib/luckyserver/uploads`, `compose_project_name
  luckyserver`, `mock_balace_ops: true`(!), `root_admin_email/password` заданы 21.08
  (root `admin@luckyserver.pro`, пароль = дев) — сид сработал на чистой БД.
- Vault-пароль: GCP Secret Manager `luckyserver-ansible-vault-pass`
  (проект `lucky-server-501916`); в CI — `$ANSIBLE_VAULT_PASS`. Пароль не
  хранить в скиле/репо; расшифровка — только во временные файлы вне рабочего
  дерева.
- Всегда `--limit luckyserver_dev` / `luckyserver_prod`. Без sudo — плейбук работает от admin. Прод-релиз = merge `dev` → `master` + push (тег `legacy-last` = состояние master до 21.08).
- Плейбук рендерит `.env` и compose из шаблонов и делает `up -d` — ручные
  правки этих файлов на сервере перезатираются деплоем, фиксируй их в репо.

## Версия API

`/v1/health` отдаёт `APP_VERSION`: рендерится из `app_version`
(`group_vars/dev/main.yaml`) через `env.tpl` (сейчас 0.9.1); если переменная
не задана — остаётся SHA коммита, вшитый CI в образ при сборке.

## БД и root-юзеры

- Postgres: только 127.0.0.1:5433, креды в `~/luckyserver-dev/.env` на
  сервере. `docker exec luckyserver-dev-postgres-1 psql -U <user> -d <db>`.
- Админские аккаунты — таблица `root_admins` (до 2026-08-13 — `root_users`), пароли scrypt (формат из
  `dist/auth/passwords.js` (в старых образах — `apps/api/dist/auth/passwords.js`): `scrypt$16384$8$1$<salt>$<key>`,
  base64url, соль 16 байт, ключ 64 байта; хелпер —
  `dist/modules/auth/passwords.js`).
- Сидинг автоматический (`src/database/seed-defaults.ts`, после миграций в
  migrate-джобе и на буте): валюты USD/EUR/RUB/KZT при пустом каталоге и
  root-админ из `ROOT_ADMIN_EMAIL`/`ROOT_ADMIN_PASSWORD` при пустой
  `root_admins`. Живые данные сиды не трогают.

## Auth и схема (с 2026-08-13)

- Авторизация полностью stateless: root, project-admin и игроки получают
  HS256 JWT (`src/modules/auth/auth-tokens.ts`); таблиц сессий и кук нет.
  Отзыв токена — только через смену пароля (claim `pwd` — отпечаток хэша).
- Обязательная env `AUTH_JWT_SECRET` (≥32 символов): рендерится `env.tpl` из
  vault-переменной `auth_jwt_secret` (в vault dev и prod уже есть). Без неё
  API не стартует. Опциональные `root_admin_email`/`root_admin_password` в
  vault включают автосид root-админа на пустой базе.
- Схема после большой чистки 2026-08-13: **22 доменные таблицы** по модулям
  (`project_*`, `client_*` вкл. `client_wallets`, `transactions`,
  `content_*`, каталоги `games`/`game_providers`/`currencies`,
  `root_admins`, `audit_events`). Леджера, сессий, нонсов, email-шаблонов и
  publish-снапшотов нет. Контент разнесён: `content_banners` — баннеры
  проекта (project_id, target_url), `content_section_items` — только
  кастомные элементы (kind game|promo); секция `banners` хранит настройки
  (banner_type). История миграций сквошнута в 23 файла `17217…`
  (schema-only; данные — в сидах). Дев-БД живёт на этой истории; прод ещё на
  legacy-схеме до отдельного решения.
- Контент публикуется: `content_publications` (снапшот jsonb на пару
  проект+секция: side_menu/main_page/footer). Админка правит живые строки —
  это черновик; витрина отдаёт снапшот. `POST
  /v1/project/content/publications/:section/{publish,revert}`; в workspace
  приходит `publication.{section}.{has_changes,published_at}`.
- Таблиц 22: убраны `client_email_changes` (весь флоу смены email) и
  `client_cms_installations` (вместе с `POST /v1/cms/store`), добавлены
  `content_banners` и `content_publications`. `project_email_integrations`
  оставлен осознанно — это отправитель писем каждого проекта.
- Загрузки лежат в `storage` (локально) и `/storage` (в контейнерах).
- SSH: `ssh lucky-dev` / `ssh lucky-prod` (алиасы в ~/.ssh/config с
  IdentitiesOnly — иначе агент перебирает ключи и сервер рвёт соединение).
- CORS открыт полностью (main.ts отражает любой Origin,
  `Allow-Credentials: true`); механизма `allowed_origins`/`ADMIN_ORIGINS`
  больше нет. Ограничений на размеры загружаемых изображений нет (остались
  формат/5MB/4096px).

## Транзакции и деньги (с 2026-08-19)

Seamless-интеграция с крашами: краши — провайдер игр, Лаки — оператор со
счётом. Расчёт раунда приходит вебхуком (`crash-games-webhook.service`) в
`FinanceService.applyGameRoundSettlement`. Ключевые решения по модели данных:

- **Снапшот провайдера и игры — в `metadata`, а не FK.** Транзакция раунда
  хранит `metadata.provider = { id, name, game: { id, name } }` плюс `bet_id`,
  `round_id`, `bet_number`, `transaction_id` (внешний id от партнёра, бывший
  `external_transaction_id`/`external_transaction_uuid`), `launch_token` (токен,
  выданный Лаки при запуске игры, = `game_sessions.launch_token`; до 20.08 ключ и
  колонка звались `session`, миграция `1721700066000` переписала ключ в
  существующих строках; по нему ищет поиск транзакций), `request`, `response`.
  Снапшот **durable**: удаление провайдера/игры не рушит историю.
- **Колонка `transactions.provider_id` ДРОПНУТА** (миграция `1721700063000`,
  вместе с `FK_transactions_provider`). Фильтр и выборки читают провайдера из
  jsonb (`metadata -> 'provider' ->> 'id'`/`'name'`), есть expression-индекс
  `IDX_transactions_meta_provider`. Контракт `FinancialTransactionSummary`
  не изменился — `provider_id`/`provider_name` теперь из meta. Причина дропа:
  FK был `ON DELETE SET NULL`, при удалении провайдера связь терялась; снапшот
  надёжнее.
- **`balance_before`/`balance_after`** (nullable `numeric(24,8)`, миграция
  `1721700056000`) пишутся на **всех** денежных путях в едином стиле: расчёт
  раунда, зачисление депозита NOWPayments, заявка на вывод (available→locked),
  ручная корректировка, mock-операции. Значения снимаются с кошелька внутри той
  же DB-транзакции, что и движение средств. Существующие данные забэкфиллены
  (по цепочке per-wallet, pending-депозиты оставлены null).
- **Тип `cancel`** — первого класса (`CHECK` в миграции `1721700055000`), рядом
  с `bet`/`win`, для партнёрского `CancelBet`. Раньше отмена писалась как
  выигрыш.
- **История транзакций игрока (публичный API):** `GET
  /v1/core/balances/transactions`, авторизованный, **keyset-курсоры** по
  `(created_at, id)`. Ответ несёт `prev_cursor`/`next_cursor` (base64url
  `created_at::text`+id), клиент ходит `?after=` (старее) или `?before=`
  (новее), **никогда `page`** — `page` теперь `400 UNSUPPORTED_FIELDS` (на этом
  ловилась витрина). Приватные ручные корректировки (`visible_to_client:false`)
  исключены.

## Провайдеры, игры и проекты (модель «добавлено/нет», с 2026-08-19)

Переключатели on/off с проектной стороны убраны — модель фактическая
(миграция `1721700061000`):

- `games` → переименована в `game_provider_games`.
- `game_provider_project_access` — рут выдал проекту видимость провайдера.
- `project_game_providers` = «проект добавил провайдера» (колонки
  `is_added`/`is_enabled` убраны); `project_games.is_enabled` убран — добавленная
  игра просто живая. Отзыв доступа рутом каскадит: добавление и подключения игр
  проекта удаляются.
- Каталог провайдеров проекта = доступ минус добавленные; `POST
  /v1/project/games` добавляет игру. Все per-game/per-provider toggle-эндпоинты
  удалены. **С 20.08 (`5ea124b`):** `GET /v1/project/games/catalog` и проверка в
  `POST /v1/project/games` берут игры всех активных провайдеров с доступом
  (`game_provider_project_access`), а не только залинкованных; добавление игры
  само создаёт `project_game_providers` (следующий provider public id) в той же
  транзакции — у проект-админа отдельного шага «добавить провайдера» больше нет
  (раздел убран из админки). Удаление игры линк провайдера не трогает.
- **Удаление игры/провайдера из проекта = удаление с сайта (20.08).** Раньше
  `removeProjectGame` чистил тайлы только в черновике (`content_section_items`),
  а опубликованный снапшот главной (`content_publications.payload`,
  `section=main_page`) не трогал — витрина лишь прятала тайл фильтром «игра
  подключена», и при повторном добавлении он возвращался, а следующий Publish
  молча его выкидывал. Теперь хелпер `catalog/published-game-tiles.ts`
  (`removeGameTilesFromPublication`) вычищает тайлы и из публикации в той же
  транзакции (bump `published_at` — инвалидирует курсоры секций), зовётся из
  `removeProjectGame`, `removeFromProject` и рутового `unlinkProject`; в аудите
  `published_items_removed`. Черновик и публикация совпадают → «нет изменений»;
  вернул игру — тайлы ставятся в билдере заново.
- **Запуск игры — по публичным id:** `POST
  /v1/core/providers/:providerPublicId/games/:gamePublicId/launch` (uuid-роут
  убран).
- **Удаление проекта:** `DELETE /v1/root/projects/:projectId` (204) — в одной
  транзакции чистит `payment_intents` → `transactions` → `client_wallets` →
  `clients` (порядок RESTRICT), затем сам проект (CASCADE), пишет аудит
  `root.project.deleted`.

## Runbook: пополнить баланс игрока на деве (ручная корректировка)

Запрос вида «пополни <email> на деве на N». Делается через API от имени
проект-админа (не через прямой UPDATE в БД — иначе не будет транзакции,
`balance_before/after` и аудита):

1. Найти клиента и кошелёк в дев-БД (креды не печатать — берём из env контейнера):
   `ssh lucky-dev 'docker exec luckyserver-dev-postgres-1 sh -c "psql -U \$POSTGRES_USER -d \$POSTGRES_DB -X -c \"select c.id, c.project_id, p.name, cur.code, w.balance_code, w.available_amount from clients c join projects p on p.id=c.project_id left join client_wallets w on w.client_id=c.id left join currencies cur on cur.id=w.currency_id where lower(c.email)=lower('"'"'EMAIL'"'"');\""'`
2. `POST /v1/project/auth/login` `{email,password}` проект-админа нужного
   проекта (BroBro Casino — `brobro-admin@luckyserver.pro`, пароль в
   `storefront/CONTEXT.md`, строкой ниже email) → `access_token`. **Impersonate
   рутом не подходит**: `createManualBalanceAdjustment` отвечает 403 «Impersonated
   project sessions cannot create manual balance adjustments» (проверено 2026-09-09).
3. `POST /v1/project/finance/users/<clientId>/transactions` с Bearer:
   `{"direction":"credit","amount":"9999","currency":"USD","balance_code":"cash","comment":"...","is_private":false}`
   (`amount` — строка, `debit` для списания, `is_private:true` прячет строку
   из истории игрока). Ответ 201, `type: manual_credit`, `balance_before/after`.
4. Проверить `client_wallets.available_amount` в БД.

Прецедент: 2026-08-21 lcpatron@yandex.ru (BroBro Casino) +9999 USD/cash.
Прецедент: 2026-09-09 test999@agg.one (BroBro Casino) +1000 USD/cash, tx `1eb1d367…`.
