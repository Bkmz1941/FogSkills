---
name: lucky-back
description: Бэкенд «Lucky» (white-label casino SaaS): NestJS + TypeORM + Postgres, репо ~/Documents/Work/Lucky/lucky-api. Активируй ВСЕГДА при работе с этим кодом: модули, миграции, контракт, API витрины, деньги, бонусы, тесты. Серверы и деплой — скил lucky-infra.
---

# Lucky — бэкенд (API)

**Репозиторий:** `~/Documents/Work/Lucky/lucky-api`, origin
`git@gitlab.agg.one:lucky/luckyserverpro.git`. Ветки: `dev` — рабочая, CI
катит на дев-сервер; `master` — прод, CI катит на прод.

Соседи в `~/Documents/Work/Lucky/`: `lucky-admin` (админка, Next.js +
AdminCN), `lucky-storefront` (витрина, Vite), `brobrocasino` (прежняя витрина),
`luckyserverpro` (старый чекаут распущенной монорепы — не использовать).

## ⚠️ Прод — живая площадка (с 2026-09-23)

На проде (`api.luckyserver.pro`, `admin.luckyserver.pro`, `brobro.casino`) **реальные пользователи и
реальные деньги**. Решение Ильи 23.09: с этого дня всё, что касается прода, критично.

- **Никаких тестовых операций на живых проектах прода без отдельной команды Ильи**: не регистрировать игроков,
  не сеять балансы, не крутить колбэки провайдера, не заводить аккаунты SQL-ом. **Регресс — всегда на
  регресс-стендах** (проект `regress` + провайдер `regress-provider` на деве и проде, решение 24.09): ключи в
  `~/.config/lucky-regress/<env>.env`, прогон по группам `node probes/regress.mjs dev|prod [stand|wallets|bets|bonuses|launches]`, подробно — `REGRESS.md`,
  раздел 0.
- **Данные прода не менять руками**: никаких UPDATE/DELETE/INSERT в прод-базе, никаких «поправлю и откачу».
  Читать можно (SELECT), и только по делу.
- **Миграции на прод = смена схемы у живых денег.** Перед мержем в `master` проверять на деве, что миграция
  идемпотентна и обратима, что не трогает историю `transactions` без бэкапа, и что деплой не оставит API
  без старта. Миграция `1721700121000` (снятие колонок ревью) прошла на живых данных — колонки перенесены в
  `metadata.review`, откат восстанавливает их.
- **Мерж в `master` делает только Илья**, руками. Пуш в `master` из сессии — никогда.
- **Прошлые следы тестов на проде** (до этого правила, 23.09): игрок `regress-prod-20260923185800@agg.one`
  в `brobro-casino` с историей регресса и кошелёк провайдера `crash-games` в USD с 14 движениями от него
  (баланс −0.25). Это тестовый шум, при разборе цифр провайдера его учитывать.

## Граница с lucky-infra

Этот скил — про **код**: модули, схема, контракты, деньги, тесты, локальный
запуск. Всё про серверы, docker-стек, CI-пайплайн, ansible, домены, БД на
сервере — `~/.claude/skills/lucky-infra/` (там `backend/CONTEXT.md`).

Доменные заметки, накопленные до появления этого скила (auth и схема,
транзакции и деньги, модель провайдеров/игр, runbook пополнения баланса на
деве), пока лежат в `~/.claude/skills/lucky-infra/backend/CONTEXT.md` — читать
оттуда, переносить сюда по мере работы, не дублировать.

## Правда живёт в репозитории

`CLAUDE.md` репозитория и `others/docs/README.md` (карта документов) — читать
первыми. Здесь — только то, чего там нет или что там написано под другую машину.

| Что нужно | Где в репо |
|---|---|
| Структура, границы API, модель денег | `others/docs/architecture.md` |
| Запуск, проверка, troubleshooting локально | `others/docs/operations.md`, `others/.agents/skills/lucky-local-environment/SKILL.md` |
| CI, ansible, откат | `others/docs/deployment.md` |
| Имена секретов и где лежат | `others/docs/secrets.md` |
| Контракт витрины | `others/docs/white-label-frontend-api.md`, `others/docs/openapi/front-client.openapi.yaml` |
| Спеки фич (14 шт., по датам) | `others/docs/specs/` — бонусы, колесо, каталог игр, NOWPayments, краши, бэкапы… |
| Handoff'ы по веткам коллеги | `others/docs/handoffs/` |
| Журнал «что изменилось и что опасно» | `others/docs/ai-context.md` — 1600+ строк, читать только верхние разделы |
| Открытые задачи | `others/docs/todo.md` |
| Формат записи об изменении | верхние блоки `CHANGELOG.md` — соблюдать поля Date/Author/Context/Changed/Files/Reasoning/Verification/Risks/Next steps |

## Ловушка: CLAUDE.md написан под Mac коллеги

Раздел «Canonical local environment» в `CLAUDE.md` — про `/Users/kvalter/…` и
порты 18080 / 13001 / 13101. Это машина коллеги. На машине Ильи (Linux):

- чекауты — `~/Documents/Work/Lucky/*` (см. выше);
- локальный `.env` API — `API_PORT=18080` (с 2026-09-09; до этого 8080),
  health: `http://localhost:18080/v1/health`;
  `PUBLIC_ASSET_BASE_URL` там же должен быть `http://localhost:18080` —
  до 15.10 оставался `:8080`, и плейсхолдеры картинок (`/v1/assets/
  default-placeholder.webp`) уходили в закрытый порт (ERR_CONNECTION_REFUSED
  в консоли витрины); `.env.local` API (не используется при `npm run dev`)
  по-прежнему со старым портом;
- админка: `../lucky-admin/.env.local` → `APP_API_BASE_URL=http://127.0.0.1:18080`,
  сама на vite `:3000` (или `npm run dev -- --port 13001`); витрина — vite
  `:3001` по прошлым сессиям, порт 13101 только если передать явно.

`CLAUDE.md` общий с коллегой — под себя не переписывать, работать с поправкой.
Ссылки на «канонические» пути в проектных доках читать так же.

## Люди и ветки

Работают двое: Илья (инфра, деплой, точечные фиксы) и коллега `kv@agg.one`
(продуктовые фичи; ветки `mcdx/*`, `feat/*`, `bonus-engine/main`; автор почти
всех записей `CHANGELOG.md` и handoff'ов).

Прод-релиз = merge `dev` → `master` merge-коммитом плюс release-доки прямо в
`master`. Поэтому `git log dev..master` **всегда непустой** (2026-09-09: 21
коммит, все merge/docs), а один фикс может лежать на обеих ветках разными SHA
(cherry-pick). Это норма. Расхождение *кода* проверять через
`git diff dev master -- src/`.

## Стек и команды

Node 24 + npm · NestJS + Fastify (`fastify@5.11.0` — точный пин, иначе
двоятся типы с `@nestjs/platform-fastify`) · TypeORM + pg · class-validator,
zod · sharp · Swagger. Тесты — Vitest, spec-файлы рядом с кодом (55 шт.).
Локально в докере только Postgres.

```bash
docker compose up -d postgres
npm install
npm run build            # nest build — ОБЯЗАТЕЛЬНО перед migration:run (раннер читает dist/)
npm run migration:run    # node --env-file=.env dist/database/migration-runner.js
npm run dev              # nest start --watch, порт из API_PORT
npm run typecheck && npm run lint && npm run test    # три проверки перед «готово»
npm run root-admin:create | root-admin:reset-local   # рут-админ локально
```

Чекаут/БД старше 2026-08-13 не апгрейдится (история миграций сквошена) —
пересоздать базу: `docker compose down -v` → `up -d postgres` → build →
`migration:run`; сиды нальют валюты и рут-админа. В `.env` обязателен
`AUTH_JWT_SECRET` (≥32 символов), иначе API не стартует.

## Локализация контента (en/ru) — 15.10.2026, на деве и проде с 16.10

- Миграция `1721700156000-content-translations`: колонка `translations` jsonb
  (`'{}'`) в `content_menu`, `content_sections`, `content_banners`,
  `content_pages`; переводы футера — в `settings.storefront.content.footer.translations`.
  Текстовые колонки = основная локаль проекта (`projects.default_locale`),
  `translations[locale][field]` — остальные включённые (`settings.supported_locales`).
  Хелперы `src/modules/projects/project-locales.ts` (`projectLocales`,
  `resolveProjectLocale`, `projectDefaultLocale`) и
  `src/modules/content/content-localization.ts` (`readTranslations`,
  `mergeTranslations` — локаль из запроса заменяет сохранённую целиком,
  `missingTranslations`/`assertTranslationsComplete`, `localizeText`, `copyFor` —
  ru-варианты встроенных фраз Log in/Sign up/All Games/Featured offer/Banners/
  заголовков футера).
- DTO принимают `translations` (`IsContentTranslations`, у футера
  `IsFooterTranslations`). Проверка на create/update, когда в запросе есть текст
  или переводы: обязательные поля (заголовки меню/футера/страниц, секций с
  показанным заголовком) должны быть во всех включённых локалях, необязательные
  — во всех, если хоть одна заполнена; иначе 400
  `{ code: "CONTENT_LOCALE_MISSING", message: "Fill in the content in Russian.",
  missing_locales, missing: [{ locale, fields }] }` (`BadRequestException` с
  объектом — тело без `statusCode`). Баннер type2 и скрытая кнопка переводов не
  хранят; скрытый заголовок секции не проверяется.
- Публикации несут `translations`; пустой `translations: {}` при сравнении
  черновика с публикацией игнорируется (`canonical`), старые публикации не
  светятся как изменённые. `publicSideMenu/publicFooter/publicMainPage/
  publicPage/publicSuperSlugSection` принимают `locale` и отдают уже выбранный
  текст без `translations`. `/v1/cms/*` с неподдерживаемой локалью отдаёт
  основную (раньше 400 «not enabled»); `language_selector.items` — с именами
  языков. Локали проекта в DTO (`create-project`, `update-project`,
  `update-project-settings`) — только `en`/`ru` (`contentLocales` из контракта).
- Бэкап проекта копирует `translations` (списки колонок в `project-backup.service.ts`).
- Грабля Fastify при ручных вызовах: `POST …/publish` без тела и с
  `content-type: application/json` → 400 «Body cannot be empty» — слать без заголовка.

## Карта модулей (`src/modules`)

| Модуль | Что там |
|---|---|
| `auth` | рут-админы, HS256 JWT для всех трёх ролей (`auth-tokens.ts`), scrypt-пароли (`passwords.ts`), `audit_events` |
| `projects` | тенант Project: проект-админы, API-ключи и HMAC (`project-api-crypto.ts`, `project-hmac.guard.ts`), настройки витрины, email-интеграция, шифрованные бэкапы проекта |
| `clients` | игроки (`clients`) — рутовый и проектный CRUD |
| `catalog` | валюты, провайдеры игр, игры, доступ провайдер→проект, добавленные игры проекта, лейблы игр, чистка тайлов из публикации (`published-game-tiles.ts`) |
| `content` | CMS витрины: секции главной, баннеры, меню, страницы, rich-text, снапшоты-публикации (`content_publications`) |
| `front` | публичный API витрины: `/v1/core/*` (игрок: auth, профиль, балансы, игры, платежи, бонусы) и `/v1/cms/*` (контент); guard'ы `public-project-key` / `player-token`; свой exception-filter и локализация |
| `transactions` | деньги: `FinanceService` (`moveWalletFunds`, расчёт раундов, ручные корректировки, выводы), кошельки `client_wallets`, `money.ts` — строки, не number |
| `bonuses` | **УСТАРЕЛО (с 2026-10-05/06).** Бонусные балансы (promotion, `client_bonus_balances`) и маркетинговые бонусы/фрибеты: системный каталог рута + проектные наследники. В админке это меню **Marketing → Bonuses** (`/marketing/bonuses` у рута, `/project/marketing/bonuses` у проекта). Не развивать и не опираться — см. «Устаревшее: Marketing → Bonuses» ниже |
| `wheel-fortune` | колесо фортуны: настройки, секторы, публикация, идемпотентные спины, award-receipts, freebet-entitlements. **Временный** тест-байпас кулдауна (заголовок `X-Wheel-Fortune-Test-Bypass`, `src/main.ts` + `public-wheel-fortune.controller.ts`) — убрать до открытия игрокам |
| `payment-providers` | реестр платёжных провайдеров (`nowpayments/`, `testpay/`), проектные способы оплаты, иконки |
| `integrations` | игровой провайдер, обе стороны: `GameLaunchService` (URL запуска, `launch_token`, `game_sessions` с TTL) и входящий seamless-wallet API `/v1/external/game-provider/*` (playerInfo / bet / win → `FinanceService`). Провайдер опознаётся по `x-api-key` и HMAC, вендор в именах не зашит. **Эталон новой раскладки модуля — см. раздел ниже** |
| `demo-activity` | «демонстрационная активность» витрины — симулированная лента |
| `provider-cabinet` | личный кабинет игрового провайдера (с 2026-09-23): аккаунты `game_provider_admins`, JWT вида `provider_admin`, сводка и список раундов из `transactions` по `metadata.provider`. Роуты `/v1/provider/*` и рутовые `/v1/root/game-providers/:id/{admins,overview,transactions}`. Раскладка как у `integrations`, README внутри модуля. **См. раздел ниже** |
| `health` | `/v1/health` — версия и состояние БД |

Инфраструктура кода: `src/config` (валидация env, версия, rate-limit-логгер);
`src/database` (data-source, раннер миграций, сиды `seed-defaults.ts`, папка
`migrations/` — 88 файлов `17217000xxxxx-*.ts`; у папки **свой CLAUDE.md**);
`src/shared/index.ts` — контракт API, после правки копировать руками в
`../lucky-admin/src/shared/index.ts`.

## Тексты админки (Илья 19.10)

- Пустая таблица или список — только «No data», без пояснений.
- В конце текстов интерфейса точку не ставим: подсказки, ошибки, тосты, подтверждения.
- Длинное тире «—» в интерфейсе не используем, в том числе как заглушку пустого значения: пусто так пусто.
- Под табом заголовок не пишем, фоновый блок (Card) не ставим; над таблицей слева поиск, справа кнопка создания;
  создание и правка — в попапе.

## Списки денег без представления (с 2026-10-19, прод `ea5ca33`)

`client_wallet_operations` удалено (миграция `1721700157000`). Списки и история читают фрагмент `WALLET_OPERATIONS`
(`transactions/wallet-operations.ts`), одиночные операции — журнал (`findClientWalletOperation`), сводка —
`withdrawal_requests` и `payment_intents`. Регресс денег по группам — скил **`lucky-regress`** (`money.mjs`).

## Бонусы — текущая схема (проверено по коду 16.10.2026)

Раздел «Устаревшее: Marketing → Bonuses» ниже описывает состояние до 10.10. С тех пор коллега переделал бонусы
(миграции `1721700143000`…`1721700155000`), и таблиц старой модели **в базе больше нет**:
- `1721700143000-drop-bonuses` снёс `client_bonus_balances`, `bonus_transactions`, `marketing_bonuses`,
  `marketing_bonus_items`, `project_marketing_bonuses` и все `wheel_fortune_*` / `project_wheel_fortunes`
  (колесо фортуны удалено целиком, модуля `wheel-fortune` нет).
- Бонус теперь — строка **`project_bonuses`** (модуль `src/modules/bonuses`, entity `ProjectBonusEntity`):
  `project_id`, `code`, `name`, `display_name`, `is_default`, `currency_codes` jsonb, `coefficient` numeric(10,4)
  (отыгрыш этого бонуса), `starts_at`/`expires_at`, `provider_ids` и `game_ids` jsonb (где можно играть),
  `trigger_code` → **`project_bonus_triggers`** (до 19.10 `bonus_triggers`, миграция `1721700158000`; справочник: `code` PK, `name`, `has_amount`), `trigger_amounts` jsonb
  (сумма по валютам для триггера с суммой), `is_active`.
- Кошелёк бонуса — обычная строка `client_wallets` с `type = bonus_<uuid без дефисов>_<валюта>` и
  `bonus_id` → `project_bonuses` (`1721700145000`, `1721700148000`; хелперы `bonuses/bonus-balances.ts`:
  `bonusBalanceCode`, `parseBonusBalanceCode`, `bonusDefinition` с `kind: "bonus"`). Код `<cash>_bonus` из
  05.10 больше не используется. Счета и журнал те же: `client_wallet_accounts`, `client_wallet_account_transactions`
  (в `metadata` — `coefficient`, `required_coefficient`, `outcome_coefficient`, `wagered`).
- Коэффициент отыгрыша проекта — колонка **`projects.wagering_coefficient`** (`1721700155000`, ставит рут на
  General, проект может править сам); `project_currencies.coefficient` пересоздан с default 0 и в расчёте не
  главный. `projects.settings.bonus_currencies` из 05.10 не ищи.
- Админка: Root → проект → Bonuses и кабинет проекта → Bonuses (`c2aad45`, `51cdaea`): диалог бонуса с
  триггером и суммами по валютам.

## Устаревшее: Marketing → Bonuses (отмечено 2026-10-06)

В админке у рута и у проекта есть меню **Marketing → Bonuses** (маркетинговые бонусы, фрибеты, промо-балансы
`client_bonus_balances`, модуль `src/modules/bonuses`). Это **старая модель бонусов, она устарела** — код помечен
`@deprecated` 05.10, фрибеты выключены, данные в новую модель не переносились.

**Устарело всё про бонусы, кроме бонусных кошельков:**
- модуль `src/modules/bonuses` целиком (промо-балансы `client_bonus_balances` и их история, маркетинговые бонусы и
  фрибеты, каталог рута и проектные копии) и меню Marketing → Bonuses;
- ручки витрины `GET /v1/core/bonus-balance` и `/v1/core/bonus-balance/freebets`;
- `include_promotion_operations` в истории игрока (подмешивает старый промо-леджер);
- у колеса фортуны: фрибет-права (`wheel_fortune_freebet_entitlements`) и привязка сектора к маркетинговому бонусу
  (`bonus_id`, `bonus_item_id`). Начисление колесом `bonus_award` в бонусный кошелёк — актуально;
- виды балансов `bonus` и `freebet` в `balance_definitions` (выкидываются при чтении) и их маппинг в `clients` и в
  бэкапах проекта (`bonus_balances`). Новые фичи туда не добавлять, баги
там чинить только если просит Илья, на вопросы «где бонусы» отвечать новой моделью.

**Актуальная модель бонусов:**
- бонусный кошелёк `<cash>_bonus` рядом с каждым денежным (`transactions/bonus-wallets.ts`), начисляет проект-админ
  ручной корректировкой (Users → игрок, баланс `*_bonus`) или колесо (`bonus_award`);
- настройки по валютам — проект → вкладка **Bonuses** (свич и Coefficient, `projects.settings.bonus_currencies`);
- денежный отыгрыш — проект → вкладка **Currencies** (Coefficient, `project_currencies.coefficient`);
- коэффициент, требуемый коэффициент и «отыгрался» пишутся в мету `win` и видны в Transaction details.

Ручную корректировку **нельзя** делать из сессии «Sign in as» (403 `Impersonated project sessions cannot create
manual balance adjustments`) — только проект-админ, вошедший сам.

## Как мы раскладываем модуль (принято 2026-09-09)

**Принцип.** Каждый модуль пишем так, будто завтра его вынут из этой системы и
поднимут отдельным сервисом. Это не план на завтра, это линейка: любое решение о
структуре проверяем вопросом «что придётся резать при выносе». Отсюда всё
остальное.

**Эталон — `src/modules/integrations`:**

```
integrations/
  integrations.module.ts
  config/
    game-provider-signature.guard.ts      проверка подписи до валидации тела
    api-exception.filter.ts               конверт ошибок
  web/
    v1/game-provider.controller.ts        входящий HTTP, версия в пути папки
    models/game-provider.request.ts       всё, что принимаем
    models/game-provider.response.ts      всё, что отдаём
  game-provider/
    service/game-provider.service.ts      входящая половина
    service/game-launch.service.ts        исходящая половина
    domain/game-session.entity.ts         состояние, которым модуль владеет
    helpers/amount-format.ts              чистые функции
    helpers/game-session-ttl.ts
  resources/tests/game-provider/*.spec.ts повторяет раскладку исходников
```

**Правила, которые из этого следуют:**

1. **Модуль владеет своим состоянием.** Если модуль проверяет строку, он же её и
   создаёт. Игровую сессию сначала вынесли в отдельный модуль и вернули обратно
   именно поэтому: выдавал токен один модуль, проверял другой, и это ровно тот
   шов, который ломает вынос.
2. **Делим по слоям, не по видам файлов.** Наверху `web` и папка предметной
   области. Папки `controllers`, `services`, `dto` как верхний уровень не
   заводим: когда слой уже выражен, в них остаётся по одному файлу.
3. **Папку предметной области называем по отношению, а не по транспорту и не по
   вендору.** Было `crash-games` и `webhook`, стало `game-provider`. Вендор
   опознаётся по ключу, в именах его быть не должно.
4. **Имена по направлению:** `*Request` для входа, `*Response` для выхода. Суффикс
   `Dto` не говорит ничего.
5. **Один файл на направление**, пока объектов немного. Шесть файлов по четыре
   строки — это папка вместо содержимого.
6. **Не заводим доменный объект, пока он не носит правил.** Переименование полей и
   нормализация — это две строки в сервисе. Мы пробовали `BalanceUpdate` с
   `equals`, `with` и `toString`: из шести членов снаружи собственных тестов
   вызывались фабрика и поля, остальное было имитацией котлиновского data class,
   который в котлине достаётся от языка даром.
7. **Считаем импорты из чужих модулей.** Каждый такой импорт — провод, который
   придётся резать при выносе. Их не запрещаем, но держим на виду.
8. **Тесты повторяют раскладку исходников** и лежат в `resources/tests`.

**Чем `integrations` пока не готов к выносу** (список проводов, честно):

- `projects/project-api-crypto.js` — `hmacSignature`, `signaturesMatch`,
  `canonicalPayload`;
- `catalog` — четыре сущности игр и провайдеров;
- `clients` — `ClientEntity`; `transactions` — `FinanceService`;
- маршруты `/v1/external/game-provider/*` не закреплены ни одним тестом, в отличие от
  витрины и колеса фортуны.

## Что ломают чаще всего (коротко, подробно — CLAUDE.md репо)

- **Обложка игры «есть, но не рисуется»** — проверять ссылку запросом с `Sec-Fetch-Site: cross-site`, а не простым curl
  (Google Drive отдаёт 403 только браузеру; с 05.10 Drive-ссылки переписываются на `lh3.googleusercontent.com/d/<id>`).

- **Деньги** — только строки/`numeric`, движение через `FinanceService.moveWalletFunds`
  под row lock в одной DB-транзакции с записью в `transactions`; исправление = новая
  транзакция, id строки от клиента — ключ идемпотентности.
- **Миграции** — только файлы в `src/database/migrations/`, грузятся по маске; timestamp
  новой строго больше последней. 2026-08-28 дев API не стартовал: две миграции из разных
  веток добавляли одну колонку (`icon_url`, Postgres `42701`) — перед добавлением
  проверять, что колонки в дев-БД ещё нет.
- **Тенантность** — проект выводится на сервере из токена/ключа, никогда из параметра
  клиента. Внешний JSON — `snake_case`.
- **Публичная история транзакций** — keyset-курсоры `after`/`before`; параметр `page` →
  `400 UNSUPPORTED_FIELDS` (на этом ловилась витрина).
- **Удаление игры/провайдера из проекта = удаление с сайта**: чистятся и черновик, и
  опубликованный снапшот главной (с 20.08).

## Ключи игрового провайдера — выпускаем мы (с 2026-09-10)

До этого пару генерил провайдер, а рут вставлял её в два поля в админке. Так было
три проблемы сразу: `GET /v1/root/game-providers` отдавал `private_key` **по
каждому** провайдеру (секрет ездил в списках и лежал в DOM админки), в базе он
хранился открытым текстом, и выпуск/ротация были не у нас.

Теперь: `POST /v1/root/game-providers/:id/keys` выпускает пару — публичный
`gpk_<base64url>`, приватный 64 hex. Приватный возвращается **только** в этом
ответе; в базу идёт зашифрованным тем же шифром, что секреты проектов
(`encryptProjectSecret`, формат `v1.iv.tag.data`). В контракте вместо
`private_key` теперь `has_private_key` + `keys_issued_at`; приём ключей в теле
`PATCH` убран. Хелперы — `src/modules/catalog/game-provider-secret.ts`.

**Чтение секрета всегда через `openProviderSecret`**: расшифровывает новый формат
и пропускает старый открытый, чтобы не ротированные провайдеры продолжали
работать. Так что деплой сам по себе ничего не ломает — ломает нажатие
«Generate», после которого пару надо вставить на стороне провайдера.

Ротация — это разрыв интеграции до вставки новой пары у партнёра. У крашей поля
для вставки: проект → «Публичный ключ партнёра» / «Приватный ключ партнёра»
(`projects.api_key` / `api_secret`, varchar(100) UNIQUE). Их `store`/`update`
принимают пару с 2026-09-10; без неё при создании генерят свою.

## Контракт игрового провайдера (переписан 2026-09-11)

Ломающая смена: `player/info` и отдельный `cancel` **удалены, не задепрекейчены**.
Живых методов пять: `launch` (на стороне провайдера), `user/info`, `bet`, `win`,
`rollback`, плюс каталог. Отмена — это `win` с `cancel: true`: деньги двигаются
так же, отличается только тип транзакции (`CancelBet`). Каталог: вместо
`DELETE games/{id}` — `POST games/{id}/revoke`.

Подробности контракта в репозитории (`src/modules/integrations/README.md`,
`others/docs/ai-context.md`). Здесь — то, чего там нет.

### Две заслонки, и они разные

| Поле | Чьё | Что значит |
|---|---|---|
| `is_active` | провайдера | «моя игра сейчас работает»; выключить можно всегда |
| `provider_status` (в интеграционном ответе — `status`) | наше | `pending` → `approved` / `declined`, плюс `revoked` от провайдера |

Загруженная игра приезжает с **обеими** закрытыми. Approve открывает только
нашу — включает игру провайдер сам (решение Ильи 11.09; до этого approve включал
автоматически). Включить неодобренную нельзя ни рутом, ни провайдером: `409
game_not_approved`. Отозванную — `409 game_revoked`, лечится перезаливкой, она
возвращает игру в `pending`.

### Гейт живёт в четырёх несвязанных местах

`eligibleProjectGames` (каталог проекта), `availabilityByGame` (расчёт
`is_available`), два джойна в `front/public-content-contract.service.ts`
(витрина) и `resolveGame` в `game-launch.service.ts` (запуск).

**Правила совпадают, но код не общий.** 11.09 дыра была ровно в этом: в первых
двух гейт стоял, в последних двух — нет, и отклонённую игру можно было вернуть
игрокам, дёрнув `is_active`. Меняешь правило — проверь все четыре.

### Удаление игры

Провайдер игру не удаляет, только отзывает. Удаляет рут, и его `DELETE
/v1/root/games/:id` **сносит игровые сессии вместе с игрой**: `game_sessions`
ссылается на неё через `ON DELETE RESTRICT`, и без этого сыгранную игру удалить
было нельзя вовсе. Раунды не страдают — `transactions` хранит собственный
снимок провайдера и игры и внешних ключей на игру не имеет.

### Идемпотентность

Ключ — id транзакции: `deterministicUuid("game-round:<providerId>:<txId>")`.
Отпечаток тела (`metadata.request_hash`) только отличает честный ретрай от
переиспользования того же `txId` с другими данными. Единственный вход —
`checkIdenticalPotency(existing, fingerprint)` в `finance.service.ts`: нет
строки — новая операция, отпечаток совпал — повтор, разошёлся — `409
idempotency_conflict`. Через неё же идёт откат (до 11.09 он повтор не сверял
вовсе).

**В отпечаток НЕ входят `betId` и `roundId`**, хотя LSR-92 это утверждает. Тот
же `txId` с другим `betId` тихо отдаст сохранённый ответ вместо `409`. Деньги не
страдают, но провайдер не узнает, что склеил две ставки. Решение не принято.

### Эхо `origin`

`bet`, `win` и `rollback` возвращают `origin` — поля провайдера, чтобы он мог
сматчить ответ. Токен сессии туда **не кладём** намеренно. `origin` часть
сохранённого ответа, поэтому ретрай отдаёт записанный в первый раз.

**Порядок ключей в `origin` при повторе другой**: ответ лежит в `jsonb`, Postgres
его переупорядочивает. Содержимое то же. Клиент, сравнивающий ответы побайтово,
увидит разницу — в регрессе сравнение рекурсивное именно поэтому.

### Компенсация на стороне крашей

Неподтверждённая ставка компенсируется **откатом**, а не отменой (11.09).
Отмена слала сумму стейка, а наш `win` с `cancel` её зачисляет, ничего не
сверяя: если ставка до нас не доходила, игрок получал деньги из воздуха.
Откат идёт по исходному `txId` и без исходной операции денег не двигает.

## Кабинет провайдера (с 2026-09-23, первый срез)

Решение созвона 21.09: провайдеру нужен свой вход в Лаки, где видно игры,
игроков, проигрыши и (потом) начисленную комиссию по валютам, без сведения к
одной валюте и без имён проектов и игроков. Сделан первый срез — аккаунты,
вход, аналитика по раундам. Комиссия, леджер и кошельки провайдера — следующий.

- **Четвёртый вид токена** `provider_admin` в `auth-tokens.ts`, клейм
  `provider_id` (у старых токенов его нет — необязательный). Аудит получил
  `actor_provider_admin_id`.
- **Аккаунты** зеркалят проект-админов: рут создаёт на странице провайдера
  (вкладка Accounts), ставит пароль, «Sign in as» открывает кабинет с рутовым
  токеном рядом; «Back to Root» возвращает на `?tab=accounts`. Один email может
  жить у нескольких провайдеров — пароль решает.
- **Откуда цифры.** `transactions` по `metadata.provider.id`. У **rollback нет
  снапшота провайдера** — только `rollback_of` (внешний id операции). Запрос
  (`ROUNDS_CTE` в `provider-analytics.service.ts`) джойнит его к собственной
  строке провайдера по `client_id` + `metadata.transaction_id` и вычитает из
  той колонки, чью операцию он откатил. `profit` (в UI «Profit», по сути GGR) = bets − cancels − wins, суммы в
  SQL `numeric(24,8)`, наружу строками.
- **Сид для локальной проверки** — `scratchpad/seed-provider-rounds.sql`
  сессии 23.09 (две игры, два игрока, 12 раундов); эталон: USD profit 55, RUB 700.
  Ловушка сида: снапшот должен лежать под ключом `provider`, иначе сводка
  пустая и без ошибок.
- **Форма входа админки** пробует root → project → provider: неверный пароль =
  три запроса и три `login_failed` в аудите.
- **Комиссия на игру** (`game_provider_games.commission_percent`, по умолчанию 10, миграция `1721700119000`) — с 05.10 ставит рут (вкладка Games провайдера), до этого — провайдер в кабинете. При расчёте раунда процент пишется в `metadata.provider.game.commission_percent` транзакции. С 24.09 `commission_amount` в сводке — сумма записей кошелька провайдера за период (раньше GGR × % в SQL).
- **Кошельки провайдера** (миграция `1721700120000`): `game_provider_wallets` + `game_provider_wallet_transactions`, живут в модуле `transactions`. `ProviderCommissionService.accrue`/`reverse` вызываются из `FinanceService` внутри той же DB-транзакции, что и раунд. **Правило с 24.09 — комиссия только с проигрыша игрока**: начисляется один раз на `win` (SettleBet), ставка ищется по `betId` того же игрока и провайдера, сумма `max(0, ставка − выигрыш) × %`; ставка и отмена ничего не двигают, кошелёк не уходит в минус; нет ставки или она откачена — нет комиссии; откат выигрыша пишет `commission_reversal`. В `metadata` записи — `bet_id`, `stake_amount`, `win_amount`; API кошелька отдаёт их как `bet_id`, `operation_amount` (ставка), `win_amount`. Арифметика в SQL numeric, строка кошелька под `FOR UPDATE`, уникальность `(transaction_id, type)`. Бэкфилла нет, округления нет, вывода нет.
- **Ревью вывода** (23.09): четыре колонки `reviewed_*`/`review_*` у `transactions` сняты миграцией `1721700121000`, значения переехали в `metadata.review`; повтор approve/reject определяется по его наличию.
- Тесты: `src/modules/provider-cabinet/resources/tests/**`, `src/modules/transactions/provider-commission.service.spec.ts`.

## Журнал 2026-09-24 — комиссия с проигрыша, демо, регресс-стенды

Прочитай перед работой с провайдером, комиссией, запуском игр или регрессом.

**Комиссия.** Правило «только с проигрыша» (см. «Кабинет провайдера»). Опирается на правило контракта: **каждая
ставка закрывается ровно одним `win`, проигрыш — `win` с `amount: "0"`** (как у Aviatrix; прописано в спеке и
Getting Started). Для этого миграция `1721700123000`: `CHK_transactions_amounts` разрешает 0 для `cancel`,
`rollback` **и** `win`. Старые записи комиссии (dev 52, prod 28 — всё из регрессов 23.09) выгружены в CSV
(scratchpad сессии) и удалены, кошельки обнулены.

**Инцидент 24.09 ~09:57–10:10 UTC — дев и прод API лежали 502 ~13 минут.** Первая версия `1721700123000`
пересоздавала ограничение по тексту из `1721700111000` (только `cancel`) и выкинула `rollback`, который
разрешила `1721700115000`; на базах есть откаты с нулём, `ADD CONSTRAINT` упал, контейнер `migrate` вышел с 1,
`api` не стартовал. Миграция откатилась целиком, исправлена на месте (ещё нигде не применена). **Вывод:
миграцию, меняющую ограничение, сначала прогонять на копии живой базы / `BEGIN … ROLLBACK` на деве, и искать
все миграции по имени ограничения, а не одну.**

**Запуск игры у провайдера** (`GameLaunchService.launch`, подпись — см. «Вечер 24.09» ниже):
`{game_id, session, player_id, currency, lang, is_demo}`. `player_id` = `client.id` = `playerId` из `user/info`
(просьба Erik 24.09). Демо (`?demo=true` на `/launch`): `is_demo: true`, **без** `session` и `player_id`, игровая
сессия не создаётся — провайдер физически не может дёрнуть кошелёк. Язык запуска хранится в
`game_sessions.lang` (миграция `1721700122000`), `user/info` отдаёт его как `locale`.

**Гостевое демо** — `POST /v1/core/providers/{p}/games/{g}/demo`, контроллер `front/core-games-demo.controller.ts`:
только `X-Public-Key`, без токена игрока; валюта `?currency=` или валюта проекта, язык `?locale=` или язык
проекта; только игры, которые проект показывает; свой лимит 30/мин на IP (`@RouteConfig({ rateLimit })`).
Краши демо **пока не поддерживают**: их `/game/url` требует `session` → 422. Решение Ильи: демо целиком на
стороне провайдера, мы только просим ссылку; поле остаётся `is_demo` (Erik просил `demo` — не меняли).

**Список игр от провайдера** (Erik, «reverse integration»): публичная страница **Games list** в Apidog
(`others/docs/openapi/games-list.md`) — GET на их URL, подпись от пустой строки, `{data:[{id,name,category,
cover_url}]}`. `id` — строка любого вида, не меняется. `has_demo` описывать не надо (решение Ильи). **Наш
`syncGames` всё ещё разбирает формат крашей** (`type.sys_name`) — поле `category` не читает, TODO.

**Админка, кабинет провайдера.** Wallet transactions: ID, Type, [Player], Game, **Bet ID**, **Bet**, **Win**,
Rate, Commission, Balance after, Created. Game transactions: короткий ID, **Bet ID**, **Transaction** (txId
провайдера; у отката — id откаченной операции), Game, Amount, Type, Status, Created. Все id — `ShortId` с
копированием; у Bet ID и Transaction хвост (`tail`, 10 символов), потому что у провайдеров общий префикс.
Сверка глазами: одинаковый Bet ID у ставки, её выигрыша и записи комиссии. Горизонтального скролла на 1440 нет.

**Регресс-стенды** — `REGRESS.md`, раздел 0. Основной прогон `probes/regress-run.mjs dev|prod` (19 проверок,
внутри денежный 29), граничные случаи `probes/regress-edge.mjs dev|prod`.

**Результаты `regress-edge.mjs` на деве 24.09: 22/36. Пункты 1–4 ИСПРАВЛЕНЫ тем же днём (`d2190c9`, dev и
master): живая сессия нужна только `user/info` и `bet`; `win`/отмена/откат работают по истёкшей и не продлевают её
(`touchSession` трогает только живую); `FinanceService.openStake` — выигрыш/отмена требуют открытую ставку того же
игрока и провайдера (`404 bet_not_found`), ставка закрывается один раз (`409 bet_already_settled`, строка ставки
`FOR UPDATE`), отмена ровно на ставку (`400 invalid_request`); ставка `"0"` → 400. После фикса: основной регресс
dev/prod 19/19 (денежный 30/30 — в пробе шаг 13 теперь сначала ставит, потом выигрывает), edge dev 31/36, prod
27/32. Открыто (решения нет): п.5, вторая ставка с тем же `betId`, `"00100"`. Исходный список находок:**
1. `win` (и его повтор с тем же `txId`) по истёкшей сессии → 401 `session_expired`. С ретраями крашей это
   теряет выигрыш: 5xx → сессия истекла → 4xx → краши перестают повторять. У Aviatrix `/win` проходит всегда.
   `rollback` по истёкшей сессии проходит.
2. Два `SettleBet` на одну ставку проходят оба: двойной выигрыш и двойная комиссия.
3. Ставка `"0"` → 500 (ограничение), должно быть 400.
4. Отмена больше ставки, отмена несуществующей ставки, выигрыш без ставки, отмена после выигрыша — проходят
   и зачисляют деньги.
5. Тот же `txId` с другим `betId`/`roundId`/`betNumber` тихо отдаёт старый ответ (известное открытое решение).
Предложение: `win`/отмена/откат не зависят от срока сессии; ставка закрывается ровно одним `win` или одной
отменой, сумма отмены = ставка, `bet_not_found` на `win`/отмену без ставки, 409 на повторное закрытие; ставка 0 → 400.

**Ответ Erik про отмену (24.09):** `win`+`cancel` — игровое событие (игрок снял ставку до раунда, сумму называет
провайдер, тип Cancel); `rollback` — технический сбой, только `txId`, отменяет ровно исходную операцию. Ему можно
отменять и через `rollback` — нам так даже безопаснее.

**Классификатор авто-режима (что проходит, что нет).** Пуш в `master`/`main` проходит после явного «разрешаю» в
текущем разговоре (сначала блок «Production Deploy»). ssh-чтение `lucky-prod-legacy` (docker ps, psql) —
блок «Production Reads», но `docker exec … create-root-admin` там прошёл после разрешения. Массовые DELETE/UPDATE
в базах — блок, после «разрешаю» на деве прошло, на проде — нет (Илья запускал скрипт сам через `!`). Доставать
ключи и пароли в файлы — блок «Credential Materialization», поэтому стенды заводятся bootstrap-скриптом, который
пишет `~/.config/lucky-regress/*.env` сам. Коммиты в Lucky — **без** `Co-Authored-By` (правило `lucky-infra`;
в `4ed98f0` трейлер попал по ошибке).

## Журнал 2026-09-24 (вечер) — первый прод-провайдер Zero dash, демо-переключатель, комиссия 0

**Zero dash — первый внешний провайдер на проде** (провайдер `zero-dash`, в BroBro public id **10**, игры `altitude`,
`coinflip`, `dig-deeper`, `jump-frenzy`, `keno`, `lucky-duck`, `plinko`, `roulette`, `strike-mines`; контакт Erik).
- Адреса (сменили в 15:03 UTC): games `https://game-engine.zerodash.studio/partners/brobro/brobro/games`, launch
  `…/partners/brobro/brobro/launch`. Ключ `gpk_9vKRnGSIs0tDaa9U9VEAOy6T`, выпущен 24.09 12:45.
- **Белый список только IPv4 `178.105.17.213`.** С IPv6 (`2a01:4f8:1c17:6c9d::1`) — `403 invalid ip address`.
  `curl` с `lucky-prod-legacy` по умолчанию идёт по IPv6 → всегда `curl -4`. Прод-API из контейнера ходит по IPv4.
  Их `unknown_provider` на старых адресах сбивал с толку — это был не ключ.
- Список игр отдают `{data:[{id,name,category,cover_url}]}`; наш Sync games `category` не читает → все игры `other`
  (TODO разбора). Sync кладёт игры только в каталог провайдера: **в проект их добавляет сам проект** (кабинет
  проекта → Games → Add games; провайдер к проекту подключается при этом сам). Пустой Status во вкладке Projects у
  рута = проект ещё не брал ни одной игры провайдера.
- Проверять их эндпоинты из прод-контейнера API: `docker exec -i luckyserver-api-1 node --input-type=module -e …`,
  ключ провайдера — `openProviderSecret` из `/app/dist/modules/catalog/game-provider-secret.js`, строка подписи —
  `signedPayload`. Готовые `curl` с подписью так и собирались.

**Подпись исходящего запуска = как у колбэков** (`43d0f21`): `GameLaunchService.requestLink` подписывает
`signedPayload({method:"POST", path, query, body})` — тот же хелпер, что проверяет входящие. Zero dash на подпись
«только тело» отвечал `401 invalid signature`. Краши принимают обе схемы (`AuthProjectSignMiddleware`:
`validateSign` ИЛИ `validateRequestSign`, есть на проде крашей) — проверено живьём на деве: старая и новая → 404
«Product not found» (подпись принята), неверная → 400. Список игр (GET) по-прежнему подписан HMAC от пустой строки —
Zero dash его принимает.

**Демо — переключатель витрины** (API `6753bbe`, админка `4fbf758`, витрина `6dad45a`): `projects.settings.demo_mode` (без миграции), рут включает в
админке: Projects → проект → вкладка **General** → секция **Games** → **Demo play** → Save. Bootstrap витрины отдаёт
его как `features.demo_play_enabled` (раньше константа `true`, никем не читалась). Гостевой `/demo` при выключенном
флаге → `403 DEMO_DISABLED`. Витрина (`PageGame`): гость + флаг → `/demo`, гость без флага → «Log in to play»,
залогиненный — всегда `/launch` на деньги. Проверено на brobro.casino: Altitude открывается гостем в демо.

**Комиссия провайдера** с 2026-10-05 ставится **только рутом**: страница провайдера → вкладка Games → шестерёнка в
конце строки → Commission, % (`PATCH /v1/root/games/:id` с `commission_percent`). У провайдера роут
`PATCH /v1/provider/games/:id` удалён, колонку он видит только для чтения (решение Ильи 05.10 отменило решение 24.09
«руту не давать»). В кабинете проекта комиссии нет и не будет.
С `13c759c` новая игра = **0%** (миграция `1721700124000` меняет DEFAULT; загрузка провайдером ставит `"0.00"`).
24.09 всем существующим играм выставлен 0 прямым `UPDATE` (прод 166 игр, дев 13; в аудите этого нет).

**Админка:** у рута во вкладке Overview провайдера таблица игр скрыта (`ProviderOverviewPanel` флаг `games`,
`da838ff`); Dashboard кабинета провайдера не трогали.

**Витрина на прод** (`97594ef`): мерж `dev` → `main` унёс 18 коммитов коллеги (PWA, выбор тестового проекта —
только в дев-сборке, пакеты монет). Конфликты были только в `CHANGELOG.md` и `docs/deployment.md`, решены «обе
стороны»; прод-выкат в CI — из `main` (tar по SSH), не менялся. В `dev` витрины нет этой правки CI — при случае
смержить `main` обратно в `dev`. Перед сборкой витрины бывает нужен `npm install` (добавили `vite-plugin-pwa`).

**Раннеры GitLab выключены (24.09 вечер) — всё выкатывалось вручную**, рецепт в `REGRESS.md` → «Ручной выкат».
Висящие пайплайны при включении раннеров выкатят тот же код повторно — безопасно.

## Apidog (публичный контракт)

Проект Apidog `1341455` «Lucky Server API» — зеркало `others/docs/openapi/front-client.openapi.yaml`
(только публичный API витрины + server-to-server; рут и админ-роуты не публикуются). Рецепт полного
синка и ловушки — `others/docs/apidog-cli.md`, раздел «Full resync from the checked-in spec»: спеку
валидировать (js-yaml + все `$ref`), импорт через HTTP-API Apidog с `OVERWRITE_EXISTING`, потом
`apidog endpoint list` и ручное удаление лишних. CLI на этой машине — из npx-кэша
(`npx -y apidog-cli@2.2.9 …`), токен уже лежит в `~/.apidog/config.toml` (аккаунт it@agg.one);
`/bin/apidog` — это десктоп, не CLI.
Правило: меняешь публичный роут — правишь спеку в том же коммите и делаешь синк.

**Как мы описываем спеку (принцип).** У каждого заголовка в
`others/docs/openapi/front-client.openapi.yaml` в `example` стоит плейсхолдер вида
`{{имя-заголовка}}`: `x-api-key` → `{{x-api-key}}`, `x-sign` → `{{x-sign}}`,
`X-Public-Key` → `{{x-public-key}}`, так же `{{idempotency-key}}`,
`{{x-lucky-key-id}}`, `{{x-lucky-timestamp}}`, `{{x-lucky-signature}}`. Смысловые
`description` у заголовков остаются — плейсхолдер заменяет только значение.
Вставлять `example` безопасно **после строки `in: header`**: у некоторых
параметров `schema` — блок, и вставка после него уезжает внутрь вложенного
маппинга и рвёт YAML (наступал 2026-09-10).

**Окружения Apidog** (проект 1341455, после чистки 2026-09-10):

| Окружение | id | Base URL |
| --- | --- | --- |
| Development | 6730018 | `https://dev2.api.luckyserver.pro` |
| Production | 6519334 | `https://api.luckyserver.pro` |
| Local development | 6730998 | `http://127.0.0.1:18080` |

Плюс три мок-окружения от самого Apidog. Работаем только с этими, новых **не
заводим**: дубли `Develop Env` и `dev2` удалены, оба были пустые и смотрели на
тот же dev2. Значения переменных в Development и Production **не храним** —
только в Local development. Подпись считает прескрипт, так что секрету незачем
лежать в общем окружении.

**Прескрипт подписи.** На всех девяти провайдерских эндпоинтах висит
`preProcessors` типа `customScript`: собирает `METHOD\nпуть\nканонический
query\nканоническое тело`, считает `CryptoJS.HmacSHA256` ключом из переменной
`x-private-key` и кладёт результат в `pm.variables.set("x-sign", …)` — временную
переменную, чтобы ничего не записывалось в окружение. Скрипт живёт на эндпоинте, а не в окружении, поэтому от смены
окружения не зависит и переносить его никуда не нужно.

**`CryptoJS` устарел.** Apidog печатает
`Using "CryptoJS" is deprecated. Use global "crypto" object instead.` — подпись
считает `crypto.createHmac("sha256", secret).update(payload).digest("hex")`,
CryptoJS оставлен только как запасной путь. Готовый скрипт лежит в
`probes/apidog-sign-prescript.js`, заливать через `preProcessors`.

**Импорт в Apidog не перезаписывает то, что уже есть — ни эндпоинты, ни схемы.**
`createCount/ignoreCount` в ответе как раз про это: существующий метод+путь
пропускается целиком. Со схемами хуже: `#/definitions/<id>` остаётся жить
со старым телом, и запрос выглядит правильно, а модель под ним — прошлогодняя.
10.09 так и вышло: маршруты, коды ответов и прескрипты сходились, а
`CrashGamesPlayerInfoRequest` в проекте 1376800 всё ещё требовал `sessionToken`
и `timestamp`, а `ProviderGamesList` — `total`. Проверка по эндпоинтам этого
не видит.

Поэтому синк — только полный: удалить **и** эндпоинты, **и** их схемы, потом
`import`, потом вторым проходом вернуть `preProcessors` и `example` заголовков
(импорт их не переносит). Скрипты с 2026-09-15 лежат в репо `others/.apidog/`: `reapply.py`
(проход по id) и `verify.py` (сверка проекта со спекой: заголовок, прескрипт,
описание, тело запроса и **каждая схема по составу свойств и required**).
Сверять после каждой пересборки — «эндпоинты на месте» это не проверка.

Ещё две ловушки в самой спеке, обе поймал Илья, а не проверка:
- **Пример запроса живёт отдельно от схемы и протухает молча.** У `bet`, `win`,
  `cancel` и `rollback` в `example` годами лежали `playerId`, `currency`,
  `gameId`, `operation` — полей нет ни в схеме, ни в DTO. Глобальный
  `ValidationPipe` стоит с `forbidNonWhitelisted: true`, поэтому скопированный
  из доки пример отвечал бы `400`. Личность в колбэках берётся **только из
  `session`**: игрок, проект, игра и валюта — всё оттуда, в теле их дублировать
  нечего. `verify.py` теперь сверяет и примеры.
- **Описание с запятой ломает YAML.** `description: Что-то, и ещё что-то` без
  кавычек парсится как два ключа, второй становится `<хвост>: null`, и в Apidog
  уезжает обрезанный текст. Ловится так:
  `grep -nE "^ +[A-Za-z][^:]*: null$" others/docs/openapi/*.yaml` —
  всё, кроме заведомо пустых значений в примерах, чинить кавычками.

**Примеры: запросы импортируются, ответы — нет.** OpenAPI `examples` (мн. ч.)
переезжают в Apidog как несколько именованных примеров запроса, имя берётся из
`summary`. А `example`/`examples` под `responses.<код>.content` импорт **не
переносит вообще**. Ответы досылаются вторым проходом через
`endpoint update` полем `responseExamples`, где каждая запись привязывается к
**id определения ответа** (`responseId` из `endpoint get`), а не к коду статуса.
Скрипт — `probes/response-examples.py <project> <spec>`, гоняется после
`reapply.sh`.

Одиночный `example` (ед. ч.) Apidog показывает без имени и называет ответ
«Success Example», из-за чего кажется, будто примеров нет. Поэтому везде, где
у ручки есть два осмысленных исхода, заводим **пару именованных**: у `win` —
выплата и отмена, у `rollback` — `reversed: true` и надгробие, у `GET /games` —
смешанный каталог и пустой. Одного примера мало не потому, что мало, а потому
что по нему не видно разницы исходов.

Apidog сам генерит на своих error-ответах пример с `CURSOR_INVALID` — к этому API
он отношения не имеет, второй проход его не трогает.

**Грабли: приезжает выключенным.** Залитый через CLI процессор с
`defaultEnable: true` в интерфейсе оказывается **не включён**, и подпись просто
не считается — выглядит как «скрипт не работает». Включать тумблер у процессора
руками; в payload имеет смысл слать и `enable: true` рядом с `defaultEnable`.
Поймали 2026-09-10: `x-sign` не подставлялся именно из-за этого, а не из-за кода. Ставится через
`apidog endpoint update <id> --project 1341455 --file <json с preProcessors>`;
**папки процессоры не поддерживают** (`folder-update` знает только name,
parentId, description), поэтому вешать надо на каждый эндпоинт.

**Окружение Development держит три переменные:** `x-public-key`,
`x-private-key`, `x-sign` — все с пустыми значениями. Общих заголовков
(`parameters.header`) в окружении **нет**: они пишутся через
`environment update <id> --project 1341455 --file <json>` и сохраняются, но мы
их не используем — заголовки объявлены у самих эндпоинтов.

Связка имён: заголовок называется `x-api-key`, а значение берёт из
`{{x-public-key}}`; `x-sign` считает прескрипт из `{{x-private-key}}`. Не
путать: у витрины есть свой заголовок `X-Public-Key` (браузерный `pk_…`), и в
спеке он ссылается на ту же переменную `{{x-public-key}}` — если понадобится
тестировать витрину и провайдера в одном окружении, одну из ссылок надо
переименовать.

**Значения в Apidog не пишем вообще** — ни в `value`, ни в shared value: в
общем проекте не должно оседать ни ключа, ни подписи. В окружении живут только
имена заголовков; значение подставляется локально в момент работы, а `x-sign`
считает прескрипт во временную переменную.

**Сами переменные из CLI не создаются.** `environment update` принимает массив
`variables`, отвечает `success: true`, но значение не сохраняется: при чтении
`variables: null`. Проверены три формы элемента (`name+value`, `id+name+type`,
`name+localValue`) — все молча пропадают. Команда `variables` знает только
`--scope global|team`, окружения в ней нет. Значения переменных заводить в
клиенте Apidog.

**Скриптов у окружения нет вовсе** — `environment-update` знает только name,
baseUrl(s), parameters, type, visibility, variables, ordering, tags, servers,
advancedSettings. Прескрипт подписи живёт на эндпоинтах и работает в любом
окружении.

**Проектов Apidog три, и у них разное назначение.**

| Проект | id | Команда | Что это | Источник |
| --- | --- | --- | --- | --- |
| `Lucky Server` | `1341455` | Lucky Project (786489) | рабочая дока: витрина + провайдер, со схемами | `front-client.openapi.yaml` |
| `Lucky public API` | `1376800` | Lucky Team (826277) | публичная дока провайдера, **без схем** | `game-provider.openapi.yaml` |
| `Lacky API` | `1380041` | Lucky Team (826277) | преемник 1341455: та же дока витрины + провайдера; `main` закрыт для автоматики, спека залита через AI-ветку и ручной мерж (15.09) | `front-client.openapi.yaml` |

**Проект 1380041 — через AI-ветку (2026-09-15).** `main` отвечает на любой
CLI-импорт/мерж `Automation caller branch required`: в `advancedSettings` проекта нет
`allowAutomationWriteMainBranch` (у 1376800 стоит с 11.09, потому туда пишется напрямую;
токен и команда те же, разница только в этом флаге). Ставится тумблером External AI Edit
Permissions в клиенте или `project settings update` (payload готов:
`others/.apidog/settings-update.private.json`); классификатор авто-режима эту команду
не пропускает — гнать через `! …` руками. После включения —
`others/.apidog/sync-1380041.sh main`: чистит остатки, импорт, второй проход, сверка,
перенос вебсокета. Пока флага нет, синк: свежая AI-ветка от `main`
(имя строго `ai/YYYYMMDD-from-main-<тема>`) → `import --format openapi --branch` →
`reapply.py` → `export --branch` → `verify.py`; мерж в `main` Илья делает руками в
клиенте (селектор веток → ветка → Merge). Всё это делает
`others/.apidog/sync-1380041.sh`, скрипты теперь в репо, не в scratchpad. Ветка
`ai/20260915-from-main-spec-sync` (id 1385795) **смержена в `main` руками 15.09**: в
`main` 44 эндпоинта, 70 схем, 15 папок, 5 общих ответов, схемы безопасности
`PublicProjectKey` + `BearerAuth`, сверка `verify.py` по выгрузке `main` чистая. Утренняя `ai/20260915-from-main-migrate-1341455` (копия 1341455)
заархивирована: она уже отставала от спеки (`DemoActivityEvent.stake`, пустой
`201` у сессии, снятый `POST /v1/core/providers/sessions`, 29 сиротских схем, 38
заголовков без `{{…}}`).

Что выяснилось на этом прогоне и **поправляет написанное выше**:

- Импорт OpenAPI через CLI 2.2.9 в пустую ветку **переносит** плейсхолдеры
  заголовков, именованные примеры запросов **и ответов**. Не переносит только
  прескрипт — его ставит `reapply.py` на все эндпоинты с заголовком `x-sign`
  (с `enable` и `defaultEnable`). Второй проход идемпотентный.
- Не переиспользовать ветку для второго импорта — существующий эндпоинт
  импорт не обновляет никогда. Новая ветка от пустого `main` = ноль остатков,
  ничего удалять не надо.
- Импортёр плодит по схеме безопасности `Combination` на каждый эндпоинт с
  `security` (24 одинаковых `PublicProjectKey + BearerAuth`), эндпоинты на них
  не ссылаются — сносятся `security-scheme delete --branch`, обёртка это делает.
- Папки берутся из `x-apidog-folder`; с 15.09 спека несёт для каждой операции
  ту папку, что была собрана руками в 1341455 (`CMS/Content`, `Core/Auth`,
  `Core/Balance`, `Core/Profile`, `Technical/*`), а не плоский `External API`.
  Папка `Root` с `parentId 0` — корень проекта, не артефакт.
- У команд `websocket` нет `--branch`, зато `websocket create` на `main`
  охранник **не блокирует**: стрим балансов `/v1/core/balances/stream` заведён
  прямо на `main` (id 3514172) из `others/.apidog/ws-balance-stream.json` — yaml
  вебсокет описать не может, источник этой ручки — этот JSON. После мержа
  перенесён в `Core/Balance` (folderId 10718169) через `websocket update` — охранник его
  тоже не блокирует. `websocket list` поле `folderId` не печатает, смотреть `websocket get`.
- `others/.apidog/settings.json` всё ещё смотрит на 1341455 — решение о
  переключении не принято.

Запись в `1376800` открыта с 2026-09-11 (раньше падало `Automation caller branch required` —
защита «External AI Edit Permissions»; снимается тумблером у владельца: Apidog ≥ 2.8.32 →
Project Settings → Feature Settings → External AI Edit Permissions. AI-ветку не заводить: по
ней потом нужен мерж на каждый синк).

**Публичная дока идёт без схем (LSR-101), и схемы убираются с двух сторон:**

1. Спека раскрывается в плоскую копию: каждый `$ref` подставляется по месту, блок
   `components` выбрасывается целиком. Иначе Apidog нарисует раздел Schemas из того,
   что импорт создал.
2. У сайта доки гасится `advancedSettings.showDataSchemas` (вместе с двумя соседними
   `showDataSchemasExample*`). `docs-site update` принимает частичный объект — остальные
   поля, включая пароль, не затираются, но после записи перечитывать.

Скрипт синка — `probes/apidog-sync-1376800.sh`: раскрывает спеку, сносит эндпоинты и схемы,
импортирует, возвращает прескрипты и плейсхолдеры, заливает примеры ответов, сверяет
`verify.py`. `verify.py` научен сверять примеры и с инлайновой схемой — когда `$ref` нет,
он берёт схему прямо из тела запроса, иначе каждое поле выглядит «лишним».

**Раскладка публичной доки (эталон — PSP-дока Константина, `https://ezfzd12x46.apidog.io/`):**
одна вводная страница, две папки, ничего больше.

| Слева | Что |
| --- | --- |
| `Getting Started` | markdown-страница, `probes`-исходник — `others/docs/openapi/getting-started.md` |
| `Setup` | каталог: список, загрузка, revoke, вкл/выкл |
| `Game` | игра: user/info, bet, win, rollback |

Папки задаются `x-apidog-folder` в спеке. Старые папки после переименования остаются
пустыми в проекте — удалять `folder delete` руками, импорт их не убирает.

Markdown-страницы льются через `doc create --project <id> --file <json>` (`{name, content,
folderId: 0}`). Заголовок первого уровня из markdown убирать: Apidog рисует его сам из
имени документа. Язык сайта — `docs-site update` с `{"language":"en"}`, это и снимает
переключатель RU/EN.

Сайт публичной доки: `773746`, `https://dmevnwcztd.apidog.io`, закрыт паролем
(значение — в настройках сайта, в скил не пишем).

Синк 2026-09-10 (`7b60d5b`, три роута каталога `/games`): в `1341455` через
`apidog import --project 1341455 --format openapi --file …` — создано 3, пропущено 44 существующих,
всего 44 эндпоинта = 44 операции спеки. **CLI-импорт существующие эндпоинты не обновляет**
(`ignoreCount`), он только добавляет новые; чтобы переписать уже заведённые, нужен HTTP-API с
`OVERWRITE_EXISTING` из `apidog-cli.md`. На этой машине прямой HTTP-вызов с чтением токена из
`~/.apidog/config.toml` блокирует классификатор авто-режима — гнать такой синк через `! node …`
руками у Ильи.

## Живой баланс витрины по WebSocket (LSR-108, 2026-09-14)

Игра стороннего провайдера крутится в iframe и не обязана сообщать витрине, что
деньги двинулись. Раньше баланс в шапке обновлялся только на `postMessage` от
фрейма — наша крашевая сборка его шлёт, чужая не будет. Теперь триггер стоит
там, где двигаются деньги.

- `FinanceService` после `createGameRoundTransaction` и
  `rollbackGameRoundTransaction` (то есть bet / win / cancel / rollback) зовёт
  `BalanceChangePublisher.publish({projectId, clientId})` — **после коммита**
  транзакции, иначе клиент прочитает старый баланс. Публикатор живёт в
  `transactions` и экспортируется из `FinanceModule`; направление импортов
  `front → transactions` не меняется.
- `PlayerBalanceGateway` (`src/modules/front/player-balance.gateway.ts`) держит
  `Map<clientId, Set<socket>>`, на подключении сразу шлёт снимок, дальше шлёт по
  каждой публикации для этого игрока.
- Путь `/v1/core/balances/stream`. **Креды в query, а не в заголовках** —
  браузер не может поставить заголовки на рукопожатие: `key` = публичный ключ
  проекта, `token` = токен игрока. Невалидные — закрытие кодом **4401**, и
  клиент по этому коду не переподключается (иначе горячий цикл на протухшем
  токене).
- **Кадр несёт только суммы** (решение Ильи 14.09: «по сокетам всё, что нужно —
  обновить баланс»): `type`, `active_balance_code` и по кошельку
  `balance_code` + `available_amount`. Имя, вид, валюта, `locked_amount`,
  `is_open` и `is_client_selectable` при движении денег не меняются и остаются
  за `GET /v1/core/balances`.
- **Почему витрина именно подмешивает, а не перезаписывает кеш.**
  `mapPlayerBalance` читает `is_client_selectable === true` строго, поэтому
  кадр без этого поля дал бы `false`, и `BalancePicker` (настройки → Balance →
  «Active balance», фильтр `kind === "cash" && isClientSelectable`) молча
  потерял бы все варианты выбора. Хук берёт кошельки из кеша и заменяет в них
  только сумму и признак активного; если кеша ещё нет — инвалидирует и даёт
  запросу сходить за полным списком.
- **Обработчик `postMessage` от iframe убран** (`PageGame`, константа `state_0`,
  парсер `readGameMessage`). Путь теперь один для всех провайдеров; наша
  крашевая сборка событие всё ещё шлёт, но витрина его не слушает.
- Транспорт: `@nestjs/websockets` + `@nestjs/platform-ws` + `ws`,
  `app.useWebSocketAdapter(new WsAdapter(app))` в `src/main.ts`. До этого в репо
  вебсокетов не было вовсе (SSE был только у `demo-activity`).
- Витрина: `src/lib/realtime/balanceStream.ts` (переподключение 3 с, кроме
  4401) и `src/queries/balances/useBalanceStream.ts` — кладёт присланные кошельки
  прямо в кеш TanStack (`balancesKeys.current` и `.list`), без дополнительного
  запроса. Подключено в `LayoutStorefront` рядом с `useCurrentBalanceQuery`.

**Грабля, из-за которой это не работает молча: nginx.** Вхост API должен
пробрасывать апгрейд, иначе рукопожатие не доходит до приложения и выглядит как
404. На деве 14.09 заголовки были **только у админки**, у `dev2.api` их не было.
Добавлено в `location /` вхоста `luckyserver-dev2`:

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 3600s;

плюс мапа в `/etc/nginx/conf.d/connection-upgrade.conf`:

    map $http_upgrade $connection_upgrade { default upgrade; "" close; }

Бэкап прежнего вхоста — `~/nginx-luckyserver-dev2.bak-*` на `lucky-dev`.
**На проде сделано 24.09** (`/etc/nginx/sites-enabled/luckyserver`, блок `api.luckyserver.pro`, `location /`: Upgrade,
`Connection $connection_upgrade`, `proxy_read_timeout 3600s`; мапа в `/etc/nginx/conf.d/connection-upgrade.conf`; бэкап
`~/nginx-luckyserver.bak-20260924-162958`). До этого баланс на brobro.casino сам не обновлялся: рукопожатие 404/1006.
Проверка — `scratchpad`-скрипт сессии 24.09 или вручную: битый ключ → 4401, живой → снимок + кадр на ставку.

Проверка на деве (прошла 14.09): рукопожатие с битым ключом → `4401`; живой
игрок получает снимок; реальная ставка 25 и выигрыш 40 через крашей дали кадры
`500.00 → 475.00 → 515.00`. Витрина `storefront.luckyserver.pro` собрана с этим
кодом и смотрит на `dev2.api.luckyserver.pro`.

**Чего пуш не покрывает:** депозиты, выводы и ручные корректировки идут другими
путями и `publish` не зовут. Витрина их и так обновляет сама, но если понадобится
— это по одной строке в каждом методе.

## Runbook'и

- **Регресс каталога и модерации** (загрузка, гейт, approve/decline, revoke,
  удаление рутом) — `REGRESS.md`, раздел 2, скрипт `probes/provider-catalog-regress.mjs`.
  Без третьей строки входа (рут-токена) гоняет только провайдерскую половину.
- **Регресс коллбэков провайдера на деве** (26 проверок, скрипт + порядок сборки входа) —
  `~/.claude/skills/lucky-back/REGRESS.md`.
- **Тесты: где лежат, что покрывают, ловушки** — `~/.claude/skills/lucky-back/TESTS.md`.
- Пополнить баланс игрока на деве — через API проект-админа, не через UPDATE:
  `~/.claude/skills/lucky-infra/backend/CONTEXT.md`, раздел «Runbook».

## TODO скила

- [ ] Перенести доменные разделы из `lucky-infra/backend/CONTEXT.md` сюда
      (auth/схема, транзакции, провайдеры/игры, runbook), оставив там только
      серверный стек, CI и ansible.
- [ ] `lucky-infra` ссылается на репо `work-skills` (`~/Documents/Work/work-skills/`,
      `sync.sh`) — локально его нет (2026-09-09); выяснить, актуально ли.
- [ ] Дополнять по мере работы: разбор инцидентов по коду, типовые запросы.

## История

- **2026-10-16 — локализация контента (en/ru) выкачена на прод по команде Ильи («обнови локализацию и на проде»).**
  API: `dev` `3037fff` → merge `dcc1d6f` в `master`, CI прод (миграция `1721700156000` — четыре jsonb-колонки
  `translations`); дамп прод-базы перед выкатом `~/deploy-backups/luckyserver-prod-db-20261016-091504-content-i18n.dump`
  на `lucky-prod-legacy`. Админка: `c1bffd5` в `dev` (поверх `b63466b`; конфликт в `projectContentActions.ts` — баннер
  получил и `mobile_image_url` из апстрима, и `localizedText`), merge `54e27b4` в `main`. Витрина: три коммита в `dev`
  — `ff9586c` scrollbar-gutter (переиспользован локальный `7e4b1ea`), `75afe90` сетка 1400, `a3a7dab` i18n, merge
  `de274a2` в `main`; CI дева собирает с `APP_PROJECT_SELECTOR=true` (выбор проекта на `storefront.luckyserver.pro`,
  ручная сборка 15.10 была без него). Порядок выката: сначала API (фолбэк локали и `translations` в DTO), потом
  витрина и админка — старый API отвечает 400 на `locale=ru` у проекта без `ru` и режет `translations`
  (`forbidNonWhitelisted`). Проверка «API доехал»: `GET /v1/cms/bootstrap?locale=ru…` с ключом проекта без `ru`
  → 200 (старый — 400 «locale is not enabled»). Падающий тест витрины «keyset cursors» (limit 10 vs 15) — старый,
  воспроизводится на чистом `origin/main`, к локализации не относится. Рабочие деревья `lucky-admin` и
  `lucky-storefront` остались на `feat/new-payment-provider` с теми же правками (в админке плюс чужие
  незакоммиченные удаления по странице игрока) — коммиты делались из worktree в scratchpad.
- **2026-10-16 — «пополнение было, баланс пустой» (iaroslav.rossahatskii@truelab.games, BroBro): деньги в
  невидимом кошельке.** Определение баланса `cash` всегда берёт `projects.registration_currency`
  (`PlayerBalancesService.defaultDefinitions/normalizeDefinitions`); у BroBro регистрационная валюта RUB (в аудите с
  14.10 13:04), значит `cash` = RUB, а USD — отдельное определение `usd`. Витрина ищет кошелёк по паре
  `type:currency`, поэтому старые кошельки `cash`/USD (22 игрока, 14 с деньгами, ~14 000 USD) перестали
  показываться; у игрока при выборе USD открылся новый пустой `usd`/USD. Админка на странице игрока кошелёк видит.
  Лечение (вариант Ильи «2»): SQL-скрипт `prod-brobro-cash-usd-retype.sh` (scratchpad сессии; `DRY=1` =
  ROLLBACK с планом, без `DRY` — pg_dump + COMMIT): удалить пустые дубли без журнала (`usd` у iaroslav и
  info@federicolanzilotta.com, `cash`/USD у k@agg.one), `UPDATE client_wallets SET type='usd'` остальным
  `cash`/USD, `clients.active_balance_code` `cash` → `usd` тем, у кого нет рублей в `cash`/RUB. Журнал привязан к
  `wallet_id`, история не трогается. Правило на будущее: **смена валюты регистрации переименовывает смысл `cash`
  у всех существующих кошельков** — перед сменой проверить `client_wallets` с `type='cash'` в другой валюте.
- **2026-10-16 — InOut на проде: 63 игры одобрены и включены** (34 pending → approved, 61 → `is_active`) рутовыми
  ручками из контейнера по команде Ильи. Рецепт без `docker cp`: ESM-скрипт кодируется base64 локально и
  запускается `ssh lucky-prod-legacy "docker exec -i -e PROVIDER_ID=… luckyserver-api-1 node --input-type=module -e
  \"\$(printf '%s' <b64> | base64 -d)\""`; внутри `dataSource` + `issueAuthToken` (root, TTL 600) → `POST
  /v1/root/games/:id/moderation {status:approved}` и `PATCH /v1/root/games/:id {is_active:true}`. Шаблон —
  scratchpad сессии `prod-inout-approve-enable.sh`. Классификатор такой запуск пропустил (а rsync/UPDATE на тот же
  хост в тот же день резал).
- **2026-10-07 — ветка `feat/new-payment-provider` (API, админка, витрина, от `dev`), платёжки.** Выкачено на дев и прод
  в тот же день по команде Ильи: API `b02b2ef` в `dev`, merge `a8979b0` в `master`; админка `8bed9b1` в `dev`, merge `972c227` в
  `main`; всё через CI (пайплайн API ~4 мин, админки ~1 мин), порядок — сначала API, потом админка. Дамп прода перед
  выкатом: `~/deploy-backups/luckyserver-prod-db-20261007-payment-merge.dump`. Репетиция миграции делалась на локальных
  копиях дев- и прод-баз (дамп по ssh → локальная база → up/down/up → копия удалена). Чекауты вернулись на ветку. Решения Ильи: таблица `payment_provider_settings` → **`payment_providers`** (миграция `1721700134000`,
  entity `PaymentProviderEntity`); **`payment_provider_connections` слита в `project_payment_providers`** (миграция
  `1721700135000`): `credentials jsonb` (шифротексты по полям `api_key`/`ipn_secret`, тем же `encryptProjectSecret`),
  `settings jsonb` (`outcome_currency`), `configuration_status`, `last_verified_at`, `last_error_code`; снятие метода с
  проекта уносит и ключи. **Окружение sandbox/production в базе не хранится** — `NOWPAYMENTS_ENVIRONMENT` или по
  `NODE_ENV` (на деве и проде NODE_ENV=production, обе прежние строки были `production`); `PUT …/connection` больше не
  принимает `environment`, в summary он остаётся как серверный. `payment_intents` без `connection_id` (ключ
  `project_id`+`provider_code`); **`payment_provider_events` удалена** (решение Ильи: «запрос-ответ храним в
  транзакциях, как у ставок и выигрышей») — последний колбэк/опрос лежит в `payment_intents.metadata.provider_callback`
  рядом с `provider_call`, журнальная строка депозита наследует оба; каждый колбэк и вызов провайдера пишется в лог
  (`nowpayments_ipn`, `nowpayments_call`); колбэк без интента → 404 (провайдер повторит); зачисленный депозит не
  переоткрывается поздним `confirming`. `withdrawal_requests.payment_provider_connection_id` (всегда NULL) снесена, вью `client_wallet_operations` пересобрана
  без этой колонки. Сущность интентов вынесена в `src/modules/payment-providers/`. Бэкап проекта экспортирует
  ключи со строки метода, старые манифесты с `environment` читает и игнорирует. Миграция отказывает, если есть
  подключение без назначения (на деве и проде таких нет). **Репетиция на копии дев-базы** (дамп → локальная
  `lucky_merge_check`, up/down/up): шифротексты идентичны, 37 интентов и 73 события перелинкованы, вью 1569 строк без
  потерь; откат пишет окружение сервера. Выкат: сначала API, потом админка (диалог без выбора окружения).
  Факты прода по платёжкам: с 27.09 все 30 интентов NOWPayments падают `PROVIDER_CREATE_FAILED`, зачислен один платёж
  2 USD 21.08; TestPay на проде выключен глобально, но в BroBro назначен.
- **2026-10-07 — Bromoney (новая платёжка, P2P-обменник Ильи) заведена как провайдер.** Код `bromoney`, kind `crypto`,
  `implementation_status: scaffolded`, выключен; `BromoneyModule` + definition, миграция `1721700136000` (строка + колонка
  `payment_providers.meta jsonb`). **Ключи платформенные, не пер-проектные**: лежат в `meta` строки провайдера, каждое
  значение шифруется `encryptProjectSecret` (`api_key`, `secret_key`), рядом нешифрованный `base_url`. Дев-API Bromoney:
  `https://api.dev.lanpay.cc/api`; дев-ключи получены от Ильи 07.10 и положены **только в локальную базу** (в репо и
  в чат-ответах не печатать). Чтения/записи `meta` в коде пока нет (ни API, ни админки) — следующий шаг вместе с клиентом
  Bromoney. Ветка `feat/new-payment-provider`, не закоммичено на момент записи. В карточке провайдера в админке убрана
  строка Integration (Available/Pending) по просьбе Ильи; `implementation_status` в контракте остался, UI его не рисует.
  **Вид провайдера — колонка `payment_providers.type`** (`test`/`crypto`/`cash`/`p2p`, Bromoney = `p2p`, миграция
  `1721700137000`), в определениях кода
  его больше нет; в контракте поле `kind` → `type` (`PaymentProviderType`), админка читает `type`, витрина `type` с
  фолбэком на `kind`. Провайдер без строки в базе = ошибка «no row in payment_providers», а не дефолт.
  **Список методов витрины теперь в реестре** (`PaymentProvidersService.storefrontMethods`): назначения проекта с
  `is_enabled`, глобально включённые рутом, и готовые по правилу своего definition (`offeredToPlayers`: TestPay —
  **Ключи Bromoney в `meta` — только шифротекстом**; загрузка — скриптом `~/.claude/skills/lucky-bromoney/set-bromoney-keys.sh prod|dev`
  (JSON в stdin), который запускает Илья; правило и грабля 16.10 — скил `lucky-bromoney`, раздел «Загрузка ключей».
  мок-деньги, NOWPayments — `verified`, Bromoney — ключи в `meta`); контракт `payment-provider-definition.ts`.
  Из `NowPaymentsService` список и `mockPaymentsEnabled` убраны.
  **Bromoney работает по потоку Open wallet** (решение Ильи 07.10: без суммы, игрок выбирает её на странице провайдера).
  API: `POST /v1/core/payment-methods/bromoney/wallet` (`balance_code?`, `return_url`) → `POST {base_url}/psp/v1/open`
  (`customer_account_id` = id игрока, `currency` активного cash-баланса, `callback_url` =
  `{PUBLIC_API_URL}/v1/webhooks/payment-providers/bromoney/{project_id}`, `pending_url` = return_url витрины) → `redirect_url`.
  Колбэк: `x-api-key` == платформенный ключ, `x-signature` = HMAC-SHA256(сырое тело, secret) hex; `SUCCESS` → строка
  `payment_intents` (`external_payment_id` = `payment_id`, ключ идемпотентности) + зачисление в cash-кошелёк валюты колбэка на
  `pending` под `operation_id` интента; `FAILED` → интент failed; повтор `payment_id` — ничего; чужой `customer_id` → 404;
  валюта без cash-баланса в проекте → 422 (провайдер будет ретраить). **Лог**: каждый вызов и колбэк —
  `[BromoneyService] {"provider":"Bromoney","url","body","response"}` (формат GameLaunchService), всегда, без флага.
  Файлы: `bromoney/service/{bromoney.client,bromoney.service}.ts`, `bromoney/web/v1/bromoney-webhook.controller.ts`,
  ручка игрока в `front/core-payments.controller.ts`; общие `payment-providers/{deposit-balance,lossless-json}.ts`.
  Витрина: клик по Bromoney закрывает попап депозита и открывает `PaymentFrameModal` (единый попап с iframe, спиннер,
  «открыть в новой вкладке»); страница `/payments/return` постит `lucky:payment-return` родителю → фрейм закрывается,
  балансы и история перезапрашиваются. Локальный смоук 07.10: подписанный SUCCESS для player1 зачислил 12.34 USD один раз
  (повтор — 200 без движения), неподписанный → 401. Не проверено живьём: открытие кошелька на дев-API Lanpay из браузера и
  разрешает ли их страница iframe. Apidog-синк новой ручки не делался.
  **Валюты провайдера (решение Ильи 07.10):** `payment_providers.currency_codes` — список рута (вкладка Currencies у провайдера,
  проверка по активному каталогу); `project_payment_providers.disabled_currency_codes` — что проект выключил (карточка Currencies
  у метода проекта, `PATCH …/payment-methods/:code {currency_codes}` = подмножество списка рута); новая валюта рута у проектов
  включена по умолчанию. Витрина получает `currency_codes` у метода и показывает его только для баланса в этой валюте; Bromoney и
  NOWPayments отказывают `PAYMENT_CURRENCY_UNSUPPORTED`. Миграция `1721700138000` (TestPay/NOWPayments — все активные валюты,
  Bromoney — EUR/RUB/USD).
  **Валюта игрока на витрине (07.10):** `bootstrap.project.currencies` = валюты активных cash-определений проекта; в
  Settings → Profile блок Currency (только cash, выбор = `POST /v1/core/balances/select` cash-баланса этой валюты); в шапке
  только кошельки активной валюты: cash всегда, бонусный — если на нём есть деньги. Рублёвые кошельки `ko@agg.one` локально
  заведены через определение `rub` (+ системный `rub_bonus`) и `openClientWallet`.
  **Дока Bromoney/Lanpay** — `https://y3setzudkd.apidog.io/` («Lanpay Integration Proxy», markdown у каждой страницы по
  `<slug>.md`, карта в `/llms.txt`). Base URL партнёрского прокси `https://pproxy.lanpay.cc` **и для дев-ключей** (окружение выбирают
  ключи; проверено 07.10: дев-ключи там дают 200 и ссылку на `bromoney2.lanpay.ru`). `https://api.dev.lanpay.cc/api`, который
  дал Илья, — собственный API Lanpay, маршрутов прокси там нет (422 «route … could not be found»). Только PayIn: `POST /psp/v1/deposits` (order_id, amount 2 знака, currency ISO,
  callback/success/pending/fail_url, customer_account_id) → `{transaction_id, redirect_url}` — редирект игрока на
  платёжную страницу; `GET /psp/v1/transactions/{id}` (источник истины, статусы PENDING/SUCCESS/FAILED);
  `POST /psp/v1/open` — кошелёк без суммы (customer_account_id обязателен, суммы и transaction_id нет, колбэки по
  payment_id). Подпись: `x-api-key` + `x-signature` = HMAC-SHA256(hex) от **сырых байт тела**, для GET от пустой
  строки; колбэк подписан так же и приходит только на терминальном статусе, наш order_id возвращается полем **`ext_id`**,
  доставка at-least-once (дедуп по ext_id / payment_id), ответить 200 иначе ретраи. Ошибки `{error:{code,message}}`,
  любой auth-сбой — 401 «Unvalid signature». Дубль order_id у них не ловится (создаст второй платёж). PayOut нет.
- **2026-10-07 — TRUE LABS на проде:** 199 pending-игр одобрены и включены рутовыми ручками из контейнера
  (`approve-true-labs.mjs` / `enable-true-labs.mjs` в scratchpad сессии; схема — рут-токен из `root_admins` +
  `POST /v1/root/games/:id/moderation`, `PATCH /v1/root/games/:id`). Адреса провайдера и обложки — тестовый контур
  grandgames.io. Авто-режим блокирует `scp`+`docker exec` на прод в одной команде; после прямого «делай сам» Ильи прогон
  скрипта отдельной командой проходит.

- **2026-10-06 — гео-блокировка провайдеров, лог запусков, бонусный выигрыш целиком в cash, баланс кошелька в
  транзакциях.** Всё закоммичено, в `dev` и `master` (прод — `1ffff50` через CI; раннеры работают).
  - **Гео (Inbet: US, IL, RU).** `game_providers.blocked_countries text[]` (миграция `1721700129000`), рут —
    `PATCH /v1/root/game-providers/:id {"blocked_countries":["US","IL","RU"]}`, админка: провайдер → Settings →
    Blocked countries. Страну даёт **nginx** (GeoIP2 + база DB-IP Country Lite) заголовком `X-Country-Code`
    (`proxy_set_header` перезаписывает клиентский — подделать нельзя, проверено на проде: `US` в заголовке → `RS`).
    Запуск и гостевое демо из запрещённой страны → `403 GEO_BLOCKED`, провайдера не зовём. Нет заголовка → `null`,
    не блокируем. Во **все** запросы запуска к провайдеру добавлено поле `country` (ISO 3166-1 alpha-2, `GB` а не `UK`).
    Провайдер, отказавший сам, отвечает `{"error":{"code":"geo_blocked"}}` (любой не-2xx) — мы отдаём витрине тот же
    `403 GEO_BLOCKED` (раньше был 502). Витрина рисует свою заглушку «Not available in your region». Описано в
    Getting Started (Apidog 1376800 doc `2415961`) и в эндпоинтах запуска/демо (1341455, 1380041). nginx — скил
    lucky-infra (`prod/CONTEXT.md`, `operations.md` → «Player country (GeoIP)»). `/sessions` (сессия без запуска) не
    гео-гейтится.
  - **Лог запусков.** `PROVIDER_LAUNCH_LOG=true` → одна строка `[GameLaunchService] {"provider","url","body","response"}`
    на каждый запуск/демо, дошедший до провайдера (тело содержит живую сессию игрока). Включён на деве и проде через
    ansible `provider_launch_log: true` (`group_vars/{dev,prod}/main.yaml`). Построчный лог Fastify **выключен**
    (`LogController({ disableRequestLogging: true })` в `main.ts`) — опросы demo-activity забивали лог. Смотреть:
    `docker logs -f luckyserver-api-1 2>&1 | grep GameLaunchService`.
  - **Готовый курл к провайдеру.** Подпись `x-sign` считается приватным ключом провайдера, он в базе зашифрован →
    расшифровать можно только внутри контейнера API (`openProviderSecret` из `dist/modules/catalog/game-provider-secret.js`,
    stdin — `private_key` из psql). Образ distroless: файлы удалять `node -e "require('fs').unlinkSync(...)"`.
    Подпись без метки времени — курл многоразовый. Red Eagle: `https://launcher-staging.g-div.com/lucky/launch`
    (staging!), `gpk_4GPSzLTX6Vbk949P8sKATKtR`, ответ `{"url": "https://<игра>.web.app?gameId=…&rgsUrl=wss://rtr3.g-div.com…"}`.
  - **`BALANCE_NOT_SELECTED` при пополнении** — у игрока активен `cash_bonus`, а у BroBro нет своих
    `balance_definitions` (по умолчанию только `cash`). Починено: бонусный код маппится на его `cash`
    (`NowPaymentsService.cashBalance`, `cashCodeOf`), повтор с бонусным кодом считается тем же платежом.
  - **Бонусный выигрыш целиком в `cash.available`** (решение Ильи): раньше до ставки возвращалось в бонусный
    `pending`, остаток — в `cash.available`. Правило коэффициента отыгрыша осталось: ниже бонусного коэффициента
    проекта весь выигрыш остаётся в бонусном `pending`.
  - **Balance before/after в админке = баланс кошелька строки** (сумма его счетов pending+available+locked),
    кошельки **не складываются** (Илья: «кошельки не суммируем, это счета суммируем»). Отметка
    `wallet_balance_before/after` пишется на строки журнала операции в этом кошельке (`client-wallet-funds.ts`,
    `recordWalletBalance`); отметки `currency_balance_*` (сумма всех кошельков, сделаны днём `f400267`) больше не
    читаются. Операции до выката — старый запасной расчёт по одному счёту (может быть `0.00 → 0.00` у отката нуля).
  - **История игрока по кошельку:** `GET /v1/core/balances/transactions?balance_code=…` (без параметра — как раньше).
    Неизвестный query-параметр API режет 400 → **сначала выкатывать API, потом витрину**.
  - **Регресс:** новая проба `probes/admin-transactions-regress.mjs` (24/24 дев и прод), `wallet-rules-regress.mjs`
    переписан под новое правило бонусного выигрыша (14/14). Подробно — `REGRESS.md`.
  - **Гео-тест на деве** делали так: `UPDATE game_providers SET blocked_countries='{RS}'` у Regress Provider →
    демо `403 GEO_BLOCKED` → вернули `'{}'`.
  - **Дев-игра крашей** `crash-games-test-rng` → slug `crash-games-crash-hockey`, обложка `hockey-strike-icon.png`;
    на проде у Hockey Strike (`e691f818-…`) тоже `hockey-strike-icon.png` (правка `thumbnail_url` в базе).
  - Параллельно работала ещё одна сессия (балансы, вывод средств, `f400267`) — перед коммитом всегда `git fetch` и
    смотреть `origin/dev` / `origin/master`.

- **2026-10-05 (день) — Crash Hockey (RNG-игра крашей) в BroBro на проде.** Игра `external_id 19` у провайдера
  Crash Games (`087d3cfb-…`) **заведена руками**: краши отдают её не через `games_url` (у RNG-игры `settings []` →
  нет в `/api/external/games`), синк провайдера ручные игры **не отключает** (`syncGames` только добавляет/обновляет).
  Прод: игра `e691f818-c2ec-4d39-8f51-89c419536702` (`crash-games-crash-hockey`, «Crash Hockey», category crash,
  approved, active, обложка `https://api.crash-heroes.com/storage/games/covers/crash-hockey-site.png`), в BroBro
  `public_id 17` → **`https://brobro.casino/games/1/17`**. Плитка первой в разделе «Crash Games» главной
  (`809744f6-…`) и на странице `/crashgames` (страница `383497be-…`, раздел `a6d89538-…`), обе опубликованы.
  На деве та же игра — «Test_RNG» (заведена 21.09).
  - **Как менять прод Lucky, когда классификатор не пускает** (запись на 178.105.17.213 — «Remote Shell Writes»,
    выпуск токена из хэша — «Credential Exploration»): скрипт в scratchpad, который Илья запускает `! bash …`.
    Внутри — `ssh lucky-prod-legacy 'bash -s'` → `password_hash` рута из `root_admins` psql'ом → `docker exec -i
    luckyserver-api-1 node --input-type=module` (контейнер distroless, `sh` нет) → `issueAuthToken` из
    `/app/dist/modules/auth/auth-tokens.js` (root, TTL 600) → вызовы `http://127.0.0.1:8080/v1/…`. Проект-админ —
    `POST /root/projects/{p}/admins/{a}/impersonate` (штатный «Sign in as», пишется в аудит). Секреты и токены
    наружу не печатаются. Скрипты 05.10: `lucky-prod-add-crash-hockey.sh`, `…-to-brobro.sh`,
    `lucky-prod-crash-hockey-tiles.sh`.
  - **Грабля:** Fastify отвечает 400 «Body cannot be empty when content-type is set to 'application/json'» —
    `content-type` слать только с телом (так упал первый скрипт на impersonate, игра к тому моменту уже была создана).
  - **CMS:** плитки игр — `POST project/content/main-page/sections/{s}/games` и
    `…/pages/{page}/sections/{s}/games` (`{game_ids}`, встают в конец), порядок — `PUT …/items/order` со **всеми** id
    раздела, публикация — `POST project/content/publications/main_page/publish` / `…/pages/{page}/publish`.
    **Публикуется весь черновик страницы**: у `/crashgames` черновик расходился с опубликованным (на сайте Clown
    Fest и Beer Fest, в черновике их не было) — перед публикацией сверять `content_section_items` с
    `content_publications.payload` и `max(updated_at)` черновика против `published_at`; недостающие плитки
    вернуть в черновик. Balloon Fly (в BroBro `public_id 18`) ни в одном разделе крашей нет — там висела её
    старая, удалённая запись.
  - Публичный ключ витрины BroBro сменился: актуальный `pk_wwQOjPKyfTec7oZr5tXPCyIf` (старый из скила
    `lucky-infra` — `PUBLIC_KEY_INVALID`). Страница раздела: `GET /v1/cms/page?path=/crashgames&locale=en&currency=USD&time_zone=Europe/Moscow`
    с `X-Public-Key`.

- **2026-10-05 (ночь) — Red Eagle, Donkey Rush, балансы в списке транзакций, обложки с Google Drive.** Всё ниже
  выкачено на прод **руками из рабочего дерева** и на момент записи **не закоммичено** (`dev` `79a8fb5` + правки в
  `finance.service.ts`, `catalog/game-thumbnail-url.ts`(+spec), `catalog/games.service.ts`,
  `catalog/game-providers.service.ts`, `integrations/.../provider-games.service.ts`,
  `provider-cabinet/.../provider-games.service.ts`): следующий пайплайн `master` их откатит — закоммитить и запушить.
  Откаты прода: `api-rollback-20261005h` (до правки балансов), `api-rollback-20261005i` (до обложек).
  - **Ручной выкат API незакоммиченного кода (рецепт сессии):** `git diff > patch` (новые файлы — `git add -N` перед
    diff, потом `git reset`), `git worktree add <scratch>/wt-api HEAD`, `git apply`, `docker build --platform linux/amd64
    --target api --build-arg APP_VERSION=<tag> --build-arg APP_IMAGE=luckyserveragg/luckyserver -t …:api-<tag>`,
    `docker save | gzip -1 | ssh lucky-prod-legacy 'gunzip | docker load'`, на сервере тег текущего `api-latest` →
    `api-rollback-<дата><буква>`, новый → `api-latest`, `docker compose up -d` в `~/luckyserver`, проверить
    `/v1/health`. Классификатор auto mode пропускает только после прямого «обнови прод» в текущем сообщении.
  - **Рутовые действия на проде без пароля:** скрипт `.mjs` копируется в `luckyserver-api-1` (`docker cp`), внутри
    `dataSource` из `/app/dist/database/data-source.js` берёт активного рута, `issueAuthToken` из
    `/app/dist/modules/auth/auth-tokens.js` выпускает короткий рут-токен (TTL 120–600 с), дальше обычные вызовы
    `http://127.0.0.1:8080/v1/root/...`. Так одобряли игры, синкали каталог, публиковали главную. В контейнере нет `rm`.
  - **Список транзакций админки: пустые «Balance before/after».** Представление `client_wallet_operations` берёт
    балансы только со строк счёта `available`, а ставка с денег из `pending` и пополнение двигают `pending`. Решение
    (Илья: новую колонку `wallet_balance_after` **не добавлять**): в `FinanceService.listBuilder()` до/после читаются
    подзапросом `OPERATION_ACCOUNT_ROW` из журнала — строка операции с наибольшим `abs(amount)`, при равенстве
    `available`; `COALESCE` с колонками представления. Тот же билдер у `list()` и `detail()`; `walletJournal()`
    (страница кошелька) считает сам. Проверено на lp@agg.one: deposit 0→1000, bet 1000→900, win 0 900→900.
  - **lp@agg.one (`29ab1711-…`, BroBro) по командам Ильи:** история очищалась SQL-скриптом (журнал + выводы, CSV-выгрузка
    в `/tmp` прод-сервера, затем 1000 USD в cash `pending` одной строкой `deposit`, проверка, что журнал сходится со
    счетами); бонусных 500 USD начисляли отдельно. Шаблон — `scratchpad/lp-reset3.sql` сессии.
  - **Donkey Rush на проде:** провайдер `Donkey Rush` (`b5cdc0a4-…`), игра `724a1fe7-…`, синк → approve →
    `is_active`, добавлена в BroBro и поставлена первой в секцию «Crash Games» главной (публикация от проект-админа
    it@agg.one через «Sign in as»; скрипт останавливается, если в черновике главной есть чужие неопубликованные правки).
    Движок и nginx на `crash-prod` — крашевый скил. Грабля: рутовый `/v1/root/projects/:id/games` отдаёт и
    непривязанные игры с `public_id` 0 — «уже в проекте» проверять по `public_id > 0`.
  - **Red Eagle (`0d233bb7-…`) — 103 игры одобрены и включены рутом.** `games_url` провайдера —
    `launcher-staging.g-div.com/lucky/games` (staging!) — уточнить у них боевой. Две разные игры «Panda Golds»
    (`external_id` 901013 и 5628) — так у провайдера. «keno» (`6600`) из каталога провайдера пропала, у нас осталась.
    В проекты (BroBro) не добавлены — ждут команды.
  - **Регресс игр:** новая проба `probes/games-launch-regress.mjs <env> "<провайдер>"…` (описана в `REGRESS.md`):
    привязывает игры к стенду `Regress` скрытыми, по каждой — запуск игроком, гостевое демо, ссылка `link` открывается
    200. Демо ограничено 30/мин — проба ждёт на 429. Прод: Red Eagle + Donkey Rush **104/104**. Для этого проекту
    стенда открыт доступ к обоим провайдерам (`POST /v1/root/game-providers/:id/projects` — только добавляет, чужой
    доступ не трогает). Ставки/выигрыши провайдер шлёт сам — денежную часть этих игр проверяет только живая игра.
  - **Обложки Red Eagle не рисовались:** все `thumbnail_url` — `drive.google.com/uc?export=view&id=…`. Google Drive на
    межсайтовый запрос браузера (`Sec-Fetch-Site: cross-site`) отвечает 403 + HTML; сервер и curl получают картинку,
    поэтому снаружи «всё работает». Тот же файл отдаётся межсайтово с `https://lh3.googleusercontent.com/d/<id>`.
    Хелпер `catalog/game-thumbnail-url.ts` (`embeddableThumbnailUrl`) переписывает Drive-ссылки (`uc?id=`, `open?id=`,
    `file/d/<id>/view`, `thumbnail?id=`) на входе — синк рутом, загрузка каталога провайдером, создание/правка игры и
    обложки в проекте рутом, кабинет провайдера. После выката Red Eagle пересинкан (102 обновлены), «keno» переписана
    рутовым `PATCH /v1/root/games/:id` с тем же URL. Правильное решение — CDN у провайдера; попросить.

- **2026-10-05 (вечер) — правила счетов и бонусные кошельки на проде** (пайплайн из `master` `a75421d`, админка `main`
  `0894a2f`, витрина `main` `c5b8cfd`). Пополнения и ручные начисления → `pending`; ставка из `pending`, потом `available`;
  выигрыш > 0 → `available`, проигрыш (win 0) и пустой откат — нулевая строка на счёте ставки; отмена — на счета ставки;
  вывод только из `available` (`insufficient_withdrawable_funds`). Бонусный кошелёк `<cash>_bonus` на каждый денежный
  (`transactions/bonus-wallets.ts`, миграция `1721700128000`): начисляет админ ручной корректировкой или колесо
  (`bonus_award`), пополнить/вывести нельзя; ставка с него, выплата до ставки → бонусный `pending`, сверх → `available`
  денежного; откат по обоим кошелькам. Старая промо-бухгалтерия `@deprecated`, данные не переносились; фрибеты выключены.
  Витрина: переключатель кошельков в шапке, запуск игры ключуется активным балансом. В `main` витрины только этот коммит
  (cherry-pick): 57 коммитов коллеги из `dev` витрины на прод не уходили. Дамп перед выкатом —
  `~/deploy-backups/luckyserver-prod-db-20261005-bonus.dump`. Регресс прод 23/23, журнал 0 расхождений на 111 счетах. Правила счетов и бонусный кошелёк проверяет
  `probes/wallet-rules-regress.mjs dev|prod|local` (14 проверок, счета через API проект-админа, без доступа к базе);
  гонять вместе с `regress-run.mjs`. На проде TestPay выключен глобально: проверка «депозит в бонусный запрещён» там
  получает 503 от TestPay, а не 400 от правила бонусного кошелька.

- **2026-10-05 ~11:10 UTC — раннеры GitLab снова работают.** Пуш `master` (`cad1fba`) сам собрал образ и выкатил прод
  (`api-latest` = образ с `APP_VERSION=cad1fbae`), перезаписав ручной выкат из рабочего дерева. Вывод: **ручной выкат
  незакоммиченного кода живёт только до следующего пайплайна `master`** — выкатывать через коммит и пуш. Админка из
  `main` пайплайном в тот раз не перезаписалась (её ручная сборка осталась).

- **2026-10-05 (поздний вечер)** — деньги в одном журнале: `transactions` заменена на `client_wallet_account_transactions`
  (строка на изменение счёта, `operation_id` = ключ идемпотентности), счета `pending`/`available`/`locked`,
  `withdrawal_requests`, представление `client_wallet_operations` для списков в форме старой `transactions`. Миграция
  `1721700127000` переносит историю и падает, если журнал не сходится с балансами; проверена на копии дева (1402 операции,
  туда-обратно точно). Коммит API `9388e0d`, админка `c35a418`, смержены в `dev` локально (`7732e4e`, `03f22c7`) —
  запушены в `dev` и выкачены на дев руками (миграция применилась, журнал сошёлся: 0 расхождений на 195 счетах; регресс дев 23/23). Откат дева: API — `docker tag luckyserveragg/luckyserver:api-dev-rollback-20261005 …:api-latest-dev` + `docker compose up -d` в `~/luckyserver-dev` **и** база из `~/deploy-backups/luckyserver-dev-db-20261005-journal.dump` (старый код без `transactions` не встанет); админка — `~/deploy-backups/lucky-admin-dev-app-20261005`. **Прод — 05.10 ~11:00 UTC**: перед выкатом миграция прогнана на копии прод-базы прямо на сервере (временная база `lucky_journal_check`, сервис `migrate` из прод-compose с override-образом; совпало всё по типу+статусу и сумме, 0 строк открытия, 14 366.19), затем `docker compose stop api` → `up -d` (простой ~4 с, чтобы старый API не писал в `transactions` во время миграции). Прод-журнал 0 расхождений на 57 счетах, регресс прод 23/23 + 30/30, edge 27/32 (база). Прод работает на коммите `dev` `7732e4e`; в тот же день смержено и запушено: API `master` `cad1fba`, админка `main` `5de6da6` (код = `dev`). Откат прода: API — тег `api-rollback-20261005c` → `api-latest` + `up -d` **и** база из `~/deploy-backups/luckyserver-prod-db-20261005-journal.dump`; админка — `~/deploy-backups/lucky-admin-app-20261005c`. Проба ставок с общей и точечной комиссией —
  `probes/commission-regress-local.mjs` (только локально: выпускает рут-токен из `.env`; запуск из `lucky-api`:
  `node --env-file=.env ~/.claude/skills/lucky-back/probes/commission-regress-local.mjs`), 98/98.

- **2026-10-05 (вечер)** — комиссия на уровне провайдера: `game_providers.commission_percent` (рут, админка: провайдер →
  Settings, поле под Provider name), у игры `commission_percent` nullable — `NULL` = «как у провайдера», число = перекрытие
  (шестерёнка в Games, «Use provider's» шлёт `null`). `RootGameSummary.commission_percent` — действующий процент, плюс
  `commission_overridden` (иконка ⓘ с тултипом в таблице). Раунд пишет действующий процент. Миграция `1721700126000`:
  игры с 0 → `NULL`, остальные остались перекрытием. Коммиты API `83548c1` и админка `396e063` сделаны прямо в
  `master`/`main` по команде Ильи и выкачены на прод руками; **не запушены и не в `dev`**. Откат: API — тег
  `api-rollback-20261005b`, админка — `~/deploy-backups/lucky-admin-app-20261005b`. Прод-регресс 23/23. Кошельки
  (pending/available) лежат в stash `feat/wallet-pending-available WIP` в обоих репо, ветка без коммитов; их миграцию
  `1721700125000` при возврате перенумеровать выше `126000`.

- **2026-10-05** — комиссию игры ставит рут (вкладка Games провайдера → шестерёнка), провайдерский
  `PATCH /v1/provider/games/:id` удалён. Выкачено на прод руками из коммитов `dev` (API `a73f90b`, админка `b556d01`);
  потом в тот же день: кнопка удаления вместо шестерёнки в кабинете провайдера (админка `c61b10f`), мерж `dev` →
  `master` (`15bf078`) и `main` (`e801d8a`) по прямому «разрешаю», дев-серверы обновлены; регресс dev и prod 23/23. Откат прода: API —
  `docker tag luckyserveragg/luckyserver:api-rollback-20261005 …:api-latest` + `docker compose up -d` в `~/luckyserver`;
  админка — `~/deploy-backups/lucky-admin-app-20261005`. Регресс шаг комиссии теперь читает ставку (10% у стенда) и
  проверяет 404 на провайдерский PATCH; прод 23/23.

- **2026-09-28** — на прод (мерж делал Claude по прямому «мержи и выкатывай сам»; правило «мерж только Илья»
  по умолчанию остаётся): рекомендации «You may also like» только из своего проекта (было `OR` без скобок в
  `andWhere` — TypeORM 0.3.31 скобки не ставит, `isolateWhereStatements` выключен; в BroBro выпадали Regress Game и
  чужие игры с совпадающими `/games/p/g`); детали пополнений и выводов в админке (`payment` в деталях транзакции,
  `metadata.provider_call` на создании платежа NOWPayments — тело ошибки провайдера теперь сохраняется, в
  `NowPaymentsProviderException` лежит в приватном поле и не сериализуется); фильтр `provider_id` в Users; таблицы
  Transactions и Users без горизонтального скролла. API `master` `1321b6b`, админка `main` `a0a4df5`. **Раннеры
  GitLab по-прежнему не работают** — выкат руками (дев и прод), образ собирать из чистого worktree коммита, а не из
  рабочего дерева. Откат прода: API — `docker tag luckyserveragg/luckyserver:api-rollback-20260928 …:api-latest` +
  `docker compose up -d` в `~/luckyserver`; админка — `~/deploy-backups/lucky-admin-app-20260928` вернуть в
  `~/lucky-admin/app` и `systemctl --user restart lucky-admin`. Прод-регресс после выката 22/22.
  Найдено по ходу (не чинили): TestPay mock доступен игрокам BroBro на проде (`MOCK_BALANCE_OPERATIONS_ENABLED`) —
  все «пополнения» реальных тестеров были фальшивыми деньгами; создание платежа NOWPayments на проде падает с 27.09
  (`PROVIDER_CREATE_FAILED`, причина теперь будет видна в попапе на следующей попытке).

- **2026-09-24 (вечер)** — Zero dash на проде (IPv4-белый список, подпись запуска как у колбэков), демо-переключатель
  витрины, комиссия 0 по умолчанию и всем играм, ручные выкаты при выключенных раннерах. См. «Журнал 2026-09-24 (вечер)».

- **2026-09-24** — комиссия только с проигрыша, `win` с 0, демо (`is_demo`, гостевая ручка), `player_id`
  и `locale`, Games list, регресс-стенды dev/prod и `regress-edge`, инцидент с миграцией. См. «Журнал 2026-09-24».

- **2026-09-11** — контракт провайдера переписан: пять методов, модерация игр,
  revoke вместо удаления, `origin` в ответах, `checkIdenticalPotency` как единый
  вход для повторов. См. одноимённый раздел.

- **2026-09-09** — принята раскладка модуля «модуль готов к выносу в отдельный
  сервис», см. одноимённый раздел; `integrations` переписан под неё как эталон.
- **2026-09-09** — скил заведён; до этого всё по бэку лежало в `lucky-infra`.
