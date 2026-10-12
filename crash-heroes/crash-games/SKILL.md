---
name: crash-games
description: «Crash Heroes» — краш-игры: серверы 78.141.216.99 (прод) и 167.233.24.119 (дев), *.crash-heroes.com, Laravel Octane + движки на pm2, MySQL. Четыре репо в ~/Documents/Work/CrashGames — crash-heroes-backend-api-core (Laravel API), crash-heroes-backend-game-engine (Node-движки + calc/slot на Python), admin-panel (React-админка), catalog-app (Framework7/Vue лобби = демо-сайт и мобилка); карта каждого внутри. Пятый репо — новый движок game-engine-rng — описан в отдельном скиле game-engine-rng. Активируй ВСЕГДА при работе с любым из них и с seamless-интеграцией Lucky↔краши. ОБЯЗАТЕЛЬНО по «проверь игры» (= прогнать smoke.sh на обоих серверах). Также «что с апи крашей», «раунды встали», «ничего не сломали?», «демо-сайт», «каталог игр».
---

# Crash Heroes — инфраструктура и бэкенд

## Серверы

| | PROD | DEV |
|---|---|---|
| Доступ | `admin@78.141.216.99` | `admin@167.233.24.119` |
| Hostname | `crash-heroes` (оба) | `crash-heroes` |
| Диск | 150 ГБ | 150 ГБ |
| RAM | 7.8 ГБ | — |
| БД | `minigames_db` / `minigames_user` | `dev_minigames_db` / `dev_minigames_user` |

Вход по ключу, sudo без пароля. Креды БД — в `/home/admin/crashgames/minigames-admin-back/.env`
(`DB_USERNAME` / `DB_PASSWORD` / `DB_DATABASE`). В скил и в гит их НЕ выносим.

Ключи (Ильи `id_ed25519`/it@agg.one и отдельный Claude `claude_ed25519`), ssh-алиасы
`crash-prod`/`crash-dev` и сводка доступов — репо `git@github.com:Bkmz1941/work-skills.git`
(локально `~/Documents/Work/work-skills/`, `access/ACCESS.md`; на новой машине —
`./install.sh`). Этот скилл там — копия: после правок запускать `sync.sh`.
**Клона `work-skills` на этой машине нет** (проверено 14.09 и 18.09) — `sync.sh`
не запустить, синхронизировать копию при следующей возможности.

Движки крашей наружу — через **`server.`**: на dev файл
`/etc/nginx/conf.d/dev.server.crashgames.app.conf` (`server_name
dev.server.crashgames.app dev.server.crash-heroes.com`), по `location /<GAME_ID>` →
`127.0.0.1:40<GAME_ID>` с `Upgrade`/`Connection "upgrade"`, `proxy_read_timeout
86400` (с 18.09 там же `location /<games.uuid>` с `rewrite`, срезающим префикс, →
`127.0.0.1:3100` — движок «Хоккеиста»: WS на `/<uuid>`, HTTP на `/<uuid>/<путь>`); `location /` отвечает текстом имени; сертификат общий с API
(`dev.api.crash-heroes.com`, SAN включает `dev.server.crash-heroes.com`); прочитан
18.09. На проде аналогично `server.crash-heroes.com` → `30<GAME_ID>` (файл не
перечитывали). **Слоты** наружу не выведены — клиент ходит в API, API в
`slot_service`.

Домены (конфиги в `/etc/nginx/conf.d/<домен>.conf`, по файлу на домен):
`api.` (Laravel Octane), `admin.` (статика админки), `games.`, `app.`, `demo.`,
`server.` и корневой `crash-heroes.com` (лендинг).

## Сервисы

| Что | Где | Чем управляется |
|---|---|---|
| Laravel Octane (Swoole) | prod `127.0.0.1:8001`, 4 воркера; dev `:8002`, 12 воркеров + 6 task; `--max-requests=5000` | systemd `minigames-admin-back.service` |
| nginx | 80/443 | конфиги в **`/etc/nginx/conf.d/`**, не в `sites-enabled` |
| MySQL | 8.4.10, `3306` | systemd |
| Redis | `127.0.0.1:6379` | systemd |
| 13 игровых движков (Node) | prod `127.0.0.1:3001…3017`, dev `4001…4017` (WS) | **pm2**, systemd `pm2-admin.service` |
| calc_service (Flask) | prod `0.0.0.0:5000`, dev `:6000` | pm2, имя «Prod/Dev CrashGames API» |
| slot_service (Flask) | prod `0.0.0.0:5500`, dev `:6500` | pm2, имя «Prod/Dev Slots API» |
| Reverb (WS) | nginx `api.…/reverb` → `127.0.0.1:8080` (dev `:8888`) | **не запущен нигде и не нужен** — решение 14.09: удалить целиком, чек-лист в TODO |
| integration-worker | `queue:work redis --queue=integration --max-time=3600` | supervisor; **перезапускается каждый час** по `max-time`, uptime < 1 ч — норма |

pm2 живёт под nvm: `source ~/.nvm/nvm.sh` перед любой командой `pm2`, иначе «command not found».

## Правила работы

**Комментариев в коде не пишем** (Илья 18.09, повторил и для api-core: «комментарии не
пишем») — ни docblock, ни `//`; объяснения — в скиле, CHANGELOG, спеке.

**Коммиты — всегда на английском и только заголовок.** Без тела сообщения,
без объяснений, без списков изменений. Одна строка. Это касается всех
репозиториев проекта: бэкенда, движков и админки.

**Без следов ассистента в коммитах.** Не добавлять трейлер `Co-Authored-By`,
не писать «generated with Claude Code» и любые другие упоминания ИИ — ни в
сообщении коммита, ни в описании MR, ни в ченжлоге.

**Тесты `crash-heroes-backend-api-core` на локальной базе НЕ запускать.**
Feature-тесты на `RefreshDatabase`, отдельной тестовой базы нет (sqlite в
`phpunit.xml` закомментирован, `.env.testing` нет) → `php artisan test` делает
`migrate:fresh` на базе из `.env` и стирает все локальные данные. 18.09 так
снесли локальную `crashgames` (docker `minigames_db`) — восстанавливали
`migrate:fresh` + сидерами. Перед тестами — спросить Илью; свою правку
проверять в tinker внутри `DB::beginTransaction()` … `DB::rollBack()`. Всё, что
стирает или откатывает базу (`migrate:fresh`/`refresh`/`rollback`, `db:wipe`,
`db:seed` на живой базе — `DefaultGameTypesSeeder` сбрасывает настройки типов),
— только по прямой команде Ильи.

## Каталоги и репозитории

```
/home/admin/crashgames/
├── minigames-admin-back/     Laravel  → crash-heroes-backend-api-core
├── minigames-admin-front/    сборка админки (nginx отдаёт статику отсюда)
├── minigames-server/         движки   → crash-heroes-backend-game-engine
│   ├── app_service/          Node, main.mjs (игровой цикл)
│   ├── calc_service/         Python, server_calculator.py
│   ├── slot_service/         Python, slot_server.py
│   └── ecosystem.config.js   конфиг pm2 всех 15 приложений
├── logs/                     логи pm2 (output_N.log / error_N.log), ~2 ГБ
├── games/<slug>/             сборки игр (HTML5: index.html, scripts/, styles/, assets/) → games.<домен>/<slug>/
│                             balloonfly beerfest booblejump breezetease clownfest creepyclown
│                             dunecopter fatguy icefish olimphockey sharkcage smashhockey (краши)
│                             fallout wildwest (слоты); на dev ещё fake/ (тестовая)
├── demo/                     сборка catalog-app, «Crash Heroes Demo»  → demo.<домен>
├── app/                      сборка catalog-app, «Crash Heroes Catalog» (F7+Capacitor) → app.<домен>
├── landing/                  Next.js-экспорт лендинга «Crash Games» → crash-heroes.com (только прод)
├── minigames-admin-front.old/  остаток от 17.08 (прод)
└── ~/deploy-backups/         бэкапы перед ручными правками
```

В `~/` на серверах лежат помощники: `smoke.sh`, `gzip_logs.sh`, `sign-external.sh`
(dev), `*.bundle` (следы деплоя бандлом) и **`resync.sh`** — разовый скрипт переливки
базы со старого хоста `88.218.169.48`, **содержит пароли MySQL открытым текстом**.
Не `cat`-ить в чат, по-хорошему удалить.

**Сборки самих игр ни в одном репозитории нет** — приходят от фронтов игр готовыми
файлами, на серверах лежат только в `games/`. Игра открывается по `games.link` из
таблицы `games` (`https://games.crash-heroes.com/<slug>`), slug ≠ `sys_name`:
`hockey_classic` → `smashhockey`, `creepy_clown` → `creepyclown`, id 8 в pm2
зовётся ScaryClown.

### Репозитории

| Что | Локальный клон (`~/Documents/Work/CrashGames/`) | Remote (`gitlab.agg.one`) | Разработка → прод | CI |
|---|---|---|---|---|
| Бэкенд API (Laravel) | `crash-heroes-backend-api-core` | `crash-heroes/backend/crash-heroes-backend-api-core` | **`develop`** → `main` | да, rsync + migrate + octane:reload |
| Движки игр | `crash-heroes-backend-game-engine` | `crash-heroes/backend/…-game-engine` | `develop` → `main` | да, перезапуск только изменившегося |
| **Админка (фронт)** | **`admin-panel`** | **`crash-heroes/frontend/admin-panel`** | **`dev`** → `main` | да, статика rsync |
| Каталог / демо / мобилка | `catalog-app` | `crash-heroes/frontend/catalog-app` | `dev` → `main` (`dev` мёртв с 01.2026, Titov коммитит прямо в `main`) | **нет**, `www/` копируется руками |
| **Новый движок под новую игру** | `game-engine-rng` — **свой скил `game-engine-rng`** | `crash-heroes/backend/game-engine-rng` | пока только `main` | **нет** |

> Ветки называются по-разному: у бэкенда `develop`, у админки и каталога `dev`.
> Пуш в `main` любого из трёх репо с CI = **автоматический релиз на прод**, без
> ручного гейта.
>
> **Состояние на 2026-09-18** (после `git fetch`, рабочие деревья чистые):
> - бэкенд — чекаут `develop` `d47d514`, `origin/main` `25d9a68`: **в `develop`
>   на 1 коммит больше** (`bet_error`, на прод не катился). Позже 18.09 +`dbeb932`
>   (RNG-игры), `17c7f17`, `e069c39`, **`55b3018`** (RNG-сессия на `/game/url` + таблицы
>   `game_rng_*`, запушен по команде Ильи, **на dev выкачен CI**) и 21.09 +`b523841`
>   (снята сверка `game_uuid` в health rng-движка, **на dev выкачен CI**) — `develop`
>   впереди `main` на 6, на прод не катилось;
> - движки — чекаут `develop` `b5b1a6b`, `origin/main` `142f570`: **то же, +1**;
> - админка — чекаут `main` `5e3720e`, `origin/dev` `cec6d3d` целиком влит. Позже 18.09
>   чекаут `dev`, +`c51f81b` (раздел RNG-игр) — `dev` впереди `main` на 1;
> - каталог — чекаут `main` `98f5ea0`, **разошёлся с `origin/main`**: 1 локальный
>   незапушенный (`console.log`) и 2 чужих впереди (`b2fe7e3`, `cdccb4c`
>   «fix(): fix cards», Titov, 02.09). Перед любой работой — `pull --rebase`.
>   «Заморожен с 06.2026» больше неверно.

Подробная карта каждого репозитория — следующий раздел.

## Карта репозиториев — что про что

Ревизия 2026-09-14. Один продукт, четыре роли: **API** (Laravel) — правда о
деньгах, игроках и настройках; **движки** (Node + Python) — раунды и коэффициенты;
**админка** (React) — бэк-офис; **каталог** (Vue + Framework7) — лобби игрока,
оно же демо-сайт и мобильное приложение. Ниже — что где лежит и на какие грабли
не наступать. Seamless-интеграция с Lucky описана отдельно ниже, здесь её нет.

### `crash-heroes-backend-api-core` — Laravel API

Laravel 10, PHP 8.2, Octane/Swoole, Sanctum, Reverb (не используется), MySQL 8.4,
Redis. `composer.json` так и называется `laravel/laravel`. 828 коммитов с 06.2023
(скелет — Vladimir Igonin, с 2025 практически всё — Илья). 76 миграций
2024-04 → 2026-09.

**Маршруты** (`routes/api/api.php` + `routes/api/v2/admin/{players,projects,rounds}.php`,
префикс `/api`, `RateLimiter` **отключён**, CORS `*`):

| группа | префикс | кто ходит | авторизация | контроллеры (`app/Http/Controllers/API/`) |
|---|---|---|---|---|
| admin | `/admin` | админка | `POST auth` (логин по полю `name`, хотя тело шлёт `email`) → Sanctum-токен **без срока**; часть — `admin.superadmin` | `Admin/*`: Currency, Projects, Player, Wallet/Admin{Deposit,Withdrawal,Transaction,ExternalTransaction}, Game, Round, GameTypeSettings, Metrics, Account |
| v2/admin | `/v2/admin` | админка | `auth:sanctum` | `V2/Admin/*` (players aggregate/bets/block, rounds, projects), у всех метод `run` |
| app | `/app` | каталог, Telegram mini-app, мобилки, сборки игр | публичные `token`, `auth`, `games/{g}/init`, `telegram/validate`; остальное `auth.player` (`PlayerAuth`: Bearer = `players.token` или `sess_…` → `GameSessionResolver`); `wallet/*` ещё `player.allow-money-operations` | `App/*`: AppController (auth по `source`, `device_id` расшифровывается RSA), Player, Leaderboard, GamesCategory, Banners, Wallet/* |
| v1/app | `/v1/app/games` | фронты слотов | `auth.player` | `GamesSlotController` → `SlotsGameService` → `SLOTS_SERVER_HOST` (slot_service) |
| server | `/server` | движки | **никакой** — только то, что Octane слушает 127.0.0.1; токен игрока в query/body | `Server/GameCrashRoundController::action` (switch по `action`), `Server/PlayerController` (`getPlayer`, `secret_bonus`), `Server/Game/ServerGameController` (`getGame`, `getGamePlayer`) |
| external | `/external` | партнёр (Lucky), Lanpay, Telegram-бот | `projects.sign` (`x-api-key` → `projects.api_key`, `x-sign` = HMAC-SHA256 тела, две вариации по слэшам); `callback/lanpay` — **без auth**; `telegram/*` — `auth.hmac` (SHA-512, общий `HMAC_SECRET_KEY`) | `External/IntegrationController` (`gameUrl`, `getGames`), `CallbackController`, `TelegramController` |

`PlayerAuth` на **каждый** запрос делает `UPDATE players SET logged_at` — фоновая
нагрузка вдобавок к `COUNT(*)` из `RoundObserver`.

**`app/`:** `Models` (21), `Services` (44 — вся логика: `TransactionService`,
`AccountService`, `RoundService`, `CurrencyService`, `Admin/MerchantAccess`,
`CrashGames/*`, `Slots/*`, `App/Wallet/{Deposit,Withdrawal}`,
`External/{Lanpay,Telegram,Payment,Integration}`, `LeaderboardService`,
`CryptoService`), `Repositories` (тонкие query-классы), `Observers` (4), `Jobs`
(1), `Console/Commands` (3), `Enums` (15), `Utils/MoneyHelper` (bcmath,
minor/major), `Utils/ProjectSignHelper` (подписи наружу),
`Exceptions/Transformer` (своя цепочка исключение → JSON), `Concerns`
(`HasQueryBuilderLikes/Sorts` — поиск и сортировка из query).

**Домен.**
- `Player` — `project_id`, `external_id` (device_id / telegram id), `token`
  (вечный uuid, **переиздаётся** при каждом `auth`/`token`/`init`), `role`
  (bot/guest/regular/tester/demo), `client_type` (telegram/demo/web/android/ios/
  postman/external_project…), `game_currency`, `can_play_for_money`, `is_dev`.
- `Project` — `is_internal`, `code`, `api_key`/`api_secret` (nullable, выдаёт
  партнёр), `api_user_info`/`api_bet`/`api_win`/`api_rollback`.
  `Project::innerId()` кэшируется 300 с.
- `User` — админы: `role` superadmin | merchant, `project_id`, `merchant_role`
  owner | finance | technical. Изоляция мерчанта — статический
  `Services/Admin/MerchantAccess`, размазан по контроллерам условиями
  `if (MerchantAccess::isMerchantRequest())`.
- `GameType` (`crash-games` id 1, `slots` id 2; `settings.algorithm` — параметры
  генератора коэффициентов, `settings.pages` — какие разделы показывает
  админка). `Game` — `sys_name` unique, `link` (URL сборки), `settings.mode`
  classic | arcade; для arcade `details.resource` (кошелёк-ресурс с `max` и
  расписанием refill: сердца) и `details.score` (очки), `multiplier`.
  Arcade сейчас — `olimp_hockey` (12) и `hockey` (15), multiplier 100.
  Слоты `wild_west` (13) и `fallout` (14) — `type_id 2`.
- `GameCrashRound` (`game_crash_rounds`) — `sequence_id`, `external_id` (uuid
  движка `GAME_ID_unixSec`), `state` 0/1/2, `bank_round`, `coefficient`,
  `players/prizes/profit`. `GameCrashBet` (`game_crash_bets`) — `bet/win` в
  **minor USD**, `bet_native/win_native` в валюте игрока, `rate_to_usd`,
  `bet_id` = номер ставки в раунде (1/2). `GameSlotBet` — слоты.
- Деньги внутренних игроков: `PlayerWallet` — строка на валюту (`GEM`, `RUB`,
  `XTR`, `GEM_DEMO`, `SCORE_N`/`RES_N` для arcade), одна `is_active`, агрегаты
  `deposit/bets/wins/profit/withdraw/balance` в minor units.
  `PlayerTransaction` — `scope` (award/round/spin/external/inner/admin/project)
  + `type` (start/bet/cancel/win/deposit/withdrawal…), `balance_before/amount/
  balance_after`, `meta.bet_id`. Пишет только `TransactionService::makeTransaction`
  под `lockForUpdate`; **баланс = `SUM(amount)` по транзакциям**, колонка
  `wallet.balance` перезаписывается этой суммой (отсюда несовместимость с
  зеркалом seamless). Бонусы там же: `awardStart` (GEM 10 000, XTR/GEM_DEMO
  9 999), `awardDaily` (GEM 500), `awardSecret` (дёргает движок через
  `server/player action=secret_bonus`), `refillArcadeResources`.
  Кошельки создаёт `PlayerObserver::created` по `client_type`.
  `Player::welcomeBonusUsed()` — `SETNX` в Redis.
- Банк казино: `Account` (одна строка «Банк»), `AccountTransaction`
  (scope external/virtual/manual/round) — `AccountTransactionObserver` инкрементит
  `accounts.current`; пишется в `AccountService::finishGameCrashRound` на
  `finish_round` от движка. Это те самые 29 млн строк. `AccountHistory` — снимки
  для графика в админке.
- Платежи: `PlayerExternalTransaction` (`service` lanpay | telegram | partner,
  `type` deposit/withdraw/bet/win/cancel/rollback, `status` draft/created/awaited/
  approved/completed/canceled/expired). Депозит — `WalletDepositService` (Lanpay,
  Telegram Stars в XTR, inner), вывод — `WalletWithdrawalService` (draft → confirm
  → Lanpay), Apple IAP — `ApplePurchaseService::verify`. Лидерборд —
  `leaderboard_player_rates`.

**Фоновое.** Observers: `PlayerObserver` (кошельки + стартовый бонус),
`RoundObserver::created` (только `sequence_id = COUNT(*)`), `BetObserver`
(created/updated/deleted → `roundBet/roundWin/roundCancel` + `updateRoundStats`;
для arcade переключает кошелёк на score), `AccountTransactionObserver`.
`Events/Round/*` реализуют `ShouldBroadcast`, но **нигде не диспатчатся**.
Jobs: только `PartnerOperationRetryJob` (очередь `integration`). Команды:
`arcade:resources:refill` (единственная в scheduler, `dailyAt('00:00')`),
`wallet:switch`, `app:update-leaderboard-command` (не в расписании, `usort`
с булевым компаратором). **Cron `schedule:run` на серверах нет** — refill
ресурсов arcade не выполняется. Лог-каналы: `round` (~39 МБ/сутки на каждом
сервере: тайминги `finishGameCrashRound` и ответы на каждый раунд), `external`,
`wallet_*`, `inapp-purchase-apple`, `arcade-refill-resources`.

**Конфиги.** `config/integration.php` (TTL сессии 25 мин), `config/keys.php`
(RSA-пара в `storage/keys/`, публичный закоммичен), `config/wallet.php` (главная
валюта `RUB`), `config/telegram.php` ← `BOT_TOKEN` (платежи) **и параллельно**
`config/app.php` → `telegram.*` ← `TELEGRAM_BOT_TOKEN` (валидация WebApp) — два
источника токена, при настройке окружения задавать оба. `.env.example` отстаёт
от `config/`. `env()` вне config в `CurrencyService:20`,
`AuthProjectSignMiddleware:34`, `CheckIsPlayerDeveloper:20` — при `config:cache`
вернут null.

**Тесты и локалка.** `tests/`: `Feature/MerchantAccessLayerTest` (4),
`Feature/PartnerRollbackTest` (6, `Http::fake`), два Example. Все feature —
`RefreshDatabase`, sqlite в `phpunit.xml` закомментирован → **тесты делают
`migrate:fresh` на MySQL из `.env`** (`DB_DATABASE=crashgames`, docker
`minigames_db`) и **стирают локальные данные** — см. «Правила работы»; без
базы всё красное. Docker только для локалки, два несовместимых варианта
(`docker-compose.yaml` — php-fpm + nginx + Dragonfly; `docker-compose.dev.yml`
— frankenphp + redis), оба не про Octane. Сидеры: админ `crashgames`, «Банк»,
типы, 15 игр, валюты (GEM_DEMO, GEM, XTR, RUB, KZT — **USD нет**, см. журнал
21.08), проект `Inner`.

`CHANGELOG.md` — русский, записи `## YYYY-MM-DD — заголовок` с блоками
Контекст / Причина / Изменено / Файлы / Выкат. Последняя запись 2026-08-20;
**коммиты 21.08–11.09 в нём не отражены**. `README.md` устарел целиком —
описывает удалённую схему `api_get_balance`/`/api/external/auth`.

**Грабли, не описанные в других разделах.**
1. `POST /api/app/wallet/withdraw` сломан на уровне класса: `WalletController`
   импортирует `App\Services\External\ExternalTransactionService`, которого нет.
2. `Player::switchBlock()` содержит `dd("switchBlock")` (`app/Models/Player.php:351`).
3. `AllowMoneyOperations` читается наоборот: `isAllowMakeMoneyOperation()`
   возвращает **блок**, middleware кидает исключение, если он есть.
4. Три разных `PlayerWalletService` (`Services/App/Wallet`, `Services/Player/Waller`
   [sic], `Services/PlayerWallet`); в `PlayerTransactionType` и `DEPOSITE`, и
   `DEPOSIT`.
5. `storage/logs/laravel.log` **отслеживается гитом** (попал в `6a8e205`, каталог
   без `.gitignore`) — растёт с каждым прогоном тестов.
6. Мёртвое: `Resources/Admin/RoundResource`, `PlayerOldResource`,
   `Events/Round/*`, `CheckIsPlayerDeveloper`, `CRUDRepository`.
7. `Player::getProfitAttribute` и `getTotalBetsWins` считают агрегаты по
   `game_crash_bets` на лету — N+1 на списках админки.
8. Ветка `origin/Pavel/Dev` (02.2026, `AdminRoundsService`, список раундов через
   ORM) — на 97 коммитов позади, `AdminRoundsController` с тех пор переписан;
   считать мёртвой.

### `crash-heroes-backend-game-engine` — движки

Монорепо из трёх независимых сервисов. 299 коммитов с 05.2023 (Igonin), в 2026
ведёт Илья. `main == develop`, тегов нет. Ни одного теста ни в одном сервисе.

| | `app_service` | `calc_service` | `slot_service` |
|---|---|---|---|
| стек | Node ESM (`.mjs`), `ws` 8, `axios` | Python, Flask 3.1 | Python, Flask 3.1, numpy, pandas |
| запуск | `node --env-file .env src/main.mjs`, по процессу на игру | `server_calculator.py --port --log` | `slot_server.py --port` |
| env | `HOST`, `PORT`, `GAME_ID`, `UPDATE_INTERVAL_MS=50`, `API_URL` (`http://127.0.0.1:8001/api/`, dev `:8002`), `CALC_SERVICE` (`http://127.0.0.1:5000/`, dev `:6000/`) | — | — |
| venv | — | `calc_service/venv`, ставится на сервере | `slot_service/venv` |

Версия Node не закреплена (CI собирает на `node:22-alpine`); `.pyc` в репо от
cpython-39. `ecosystem.config.js` / `dev-ecosystem.config.js` — одинаковая
структура, разные префиксы имён, порты, `API_URL`; секции `deploy` в них
устарели (github `minigames-agg`), реальный деплой — rsync из CI.

**Игра → id → порт → pm2** (`GAME_ID` = `games.id` в БД):

| id | pm2 (prod / dev) | порт prod / dev | slug сборки |
|---|---|---|---|
| 1 | Prod 1 BallonFly / Dev 1 BallonFly | 3001 / 4001 | balloonfly |
| 2 | … 2 SharkCage | 3002 / 4002 | sharkcage |
| 3 | … 3 ClownFest | 3003 / 4003 | clownfest |
| 4 | … 4 FatGuy | 3004 / 4004 | fatguy |
| 5 | … 5 IceFish | 3005 / 4005 | icefish |
| 6 | … 6 BoobleJump | 3006 / 4006 | booblejump |
| 7 | … 7 BeerFest | 3007 / 4007 | beerfest |
| 8 | … 8 ScaryClown | 3008 / 4008 | creepyclown |
| 11 | … 11 Breeze Tease | 3011 / 4011 | breezetease |
| 12 | … 12 Olimp Hockey (arcade) | 3012 / 4012 | olimphockey |
| 15 | … 15 Hockey (arcade) | 3015 / 4015 | hockey |
| 16 | … 16 Hockey Classic | 3016 / 4016 | smashhockey |
| 17 | **`17 DunaCopter`** на проде (без `Prod `), Dev 17 DunaCopter | 3017 / 4017 | dunecopter |

id 9, 10, 13, 14 движков не имеют (13/14 — слоты). Все 13 процессов — **один и
тот же `main.mjs`**, различие только `GAME_ID`/`PORT`; вся специфика (режим
arcade, множитель, `Coef_2_sec`/`Coef_15_sec`, банк) приходит из Laravel.

**`app_service/src/`:** `main.mjs` (297 строк — WS-сервер, обработчик сообщений,
`setInterval` игрового цикла, глобальные `currentRound`, `bank`, `ratesHistory`,
`creatingRoundLock`); `external.mjs` (`apiGetPlayer(token)`, попутно патчит
`String.prototype.toHHMMSS`, от которого зависит `Round.getDurationTime()`);
`models/round.class.mjs` (`Round`: состояния `BETS 0 / RUN 1 / WAITING 2 /
FINISHED 3`, ставки, выплаты); `models/player/player.class.mjs`;
`services/round-service.class.mjs` (создание раунда + репозиторий на каждое
событие); `services/client-message-service/*` (`BetMessageHandler`,
`CancelMessageHandler`, `JumpMessageHandler`; `auth`/`rates`/`balance`/`info`
остались в `main.mjs`); `services/game-version-service.class.mjs` (синглтон,
помнит `version` из **последнего** `auth` любого клиента);
`http/repository/http-round-repository.class.mjs` (`update` → `POST
{API_URL}server/round`, `getRoundCoef` → calc); `enums/round-action.mjs`
(`create_round`, `store_bet`, `remove_bet`, `remove_bets`, `store_take`,
`store_takes`, `update_round`, `finish_round`).

**Жизненный цикл раунда.** `uuid = GAME_ID_unixSec`.
1. Создание: `create_round` в Laravel → `round_id`; всем клиентам
   `resetBetsData()` и **без await** `updateClientData` — GET игрока на каждого
   подключённого (в т.ч. анонимного → `Player not found` в логе Laravel;
   `smoke.sh` даёт по 2 такие строки за прогон).
2. `BETS` — 5 с. 3. `RUN` — `update_round` (до 100 попыток по 100 мс, потом
   `process.exit(1)`), из ответа `settings` → calc `/calculate` + `/get_coefs`;
   коэффициент ступенькой из таблицы `coefs[t]`; стоп при `rate >= coef`, `rate >=
   100` или `runElapsed > 30 с` (страховка 03.2026). Формула времени в `runRound`
   накопительная — полёт нелинеен относительно реального времени, 40 «расчётных
   секунд» ≈ 16 с реальных. 4. `WAITING` — 5 с, `ratesHistory.unshift(rate)`
   (20 штук). 5. `FINISHED` → `finish_round`.

**Протокол WS** (JSON, сокет = игрок). При подключении `{success, id}`.
Клиент → сервер: `auth {token, version?}` → ответ `auth {balances{main,
secondary}, blocks, interval}`; `bet {set, bet_id}` → `bet {success, bet_id}`
(проверка только `balances.main.balance >= set`, локально вычитает);
`cancel {bet_id | all_bets}`; `jump {bet_id | all_bets}` (только в RUN, выигрыш
`rate * bet`, в `secondary` при arcade); `rates` → `{rates: "2.31 1.05 …"}`
(строка через пробел, 20 последних, **без авторизации**); `balance`; `info`.
Сервер → клиент каждый тик (только с `player.token`): `tick {step, state,
rate, countdown, game_uuid, player{jump, bets[], balances, blocks}}`.

**В Laravel** два эндпоинта, оба без серверной авторизации: `GET
server/games/{GAME_ID}/player?token=` и `POST server/round` с `action`.
Каждое событие ставки — **два** POST подряд (`store_*` + `update_round`).
`bank` — процессный счётчик, обнуляется рестартом.

**`calc_service`** (переписан 03.2026, Titov): `POST /calculate`
(`{Expectation, TotalBets, MaxAccount, CurrentAccount, MaxDrawDown%,
MaxDrawDownRound%, Coef_2_sec, Coef_15_sec}` → `{crash_time, coef}`), `POST
/get_coefs` (таблица 401 точка, шаг 0.1 с до 40 с), `GET /rng_status`. Кривая
`c(t) = 1 + α·t^β` через точки (2, Coef_2_sec) и (15, Coef_15_sec); `p(c) =
(μ+1)/c`, `μ = Expectation` (−0.04 ⇒ RTP 96 %); потолок `c_max = 1 +
MaxDrawDownRound/TotalBets` — коэффициент ограничен банком. RNG —
`os.urandom`, self-test, лимит 1000 вызовов/с, аудит в `--log`. Зовёт его только
`app_service`. При ошибке 500 с **полным traceback** в теле.

**`slot_service`** — отдельный продукт, генератор исходов слота 5×3, с крашами
не связан: `POST /setup` (строит таблицу исходов из `slot_settings.json`,
`symbols.json`, `combinations.json`; **недетерминирована между рестартами**;
вызывается сам на старте), `POST /place_bet {bet_size}` → матрица 3×5 и
`fin_result`. `bank_file.json` — банк слота (`current_max`, `current`,
`max_drawdown_pct`), перезаписывается целиком после каждой ставки, в rsync
исключён — **создаётся на сервере руками**, без него `/place_bet` падает 400.
Исход выбирается `np.random.choice` (не CSPRNG). Клиент — Laravel
`SlotsGameService`.

**Грабли движка.**
1. **`all_bets` действует на всех игроков раунда**: `Round.cancelBets(player)`
   обнуляет `bets.list` целиком, `takeAllWinnings(player)` выплачивает по
   **каждой** ставке в раунде вызывающему (`round.class.mjs:196-252`). При одном
   игроке на процесс незаметно.
2. `GameVersionService` — процессный синглтон: клиент с `version != 1` ломает
   `getInfo` всем.
3. uuid раунда с точностью до секунды; если Laravel не вернул `round_id`, цикл
   создаёт раунд каждые 50 мс (`persistenceId === null`), тиков нет.
4. `SIGTERM` только логируется — pm2 добивает по `kill_timeout`; `exit` пишет
   `FATAL Exit` при штатном выходе.
5. Ставка до `auth` → `TypeError` → `{type:'bet', message:'Error…'}`; `blocks` из
   Laravel сервером не проверяются.
6. `.env.example` устарел (`API_URL` без `/api/` и слэша — склейка даст
   `…:8000server/round`). `LOGS_PATH`/`NODE_ENV` кодом не читаются.
7. Мёртвое: `postHttpsJSON`, `HttpPlayerRepository`, `apiGetGame`, `apiGetBonus`,
   `Round.drop`, `random`/`seedrandom`, `lodash`, `axios-retry`.

### `admin-panel` — админка

React 19, react-router 7 (импорты вперемешку из `react-router` и
`react-router-dom`), Vite 6 + SWC, TS 5.7, Tailwind 4, TanStack Query 5 + Table 8,
`ky`, react-hook-form + zod 4, shadcn (`components.json`, style `new-york`) +
**приватный реестр `@agg`** (`pages.agg.one/frontend-libs/admin-ui`, нужен
`REGISTRY_TOKEN`) — оттуда `src/components/agg/*` (`AggTable`). Пакетный
менеджер **npm** (`bun.lockb` мёртв с 02.2026). `.nvmrc` v22, CI собирает на
`node:24`. Husky pre-commit → lint-staged. 158 коммитов с 09.2025 (Maxim
Spiridonov, coolstory), с 07.2026 — Илья.

**Структура `src/`:** `main.tsx` — все маршруты; `components/routing/`
(`public-routes`, `private-routes` — гейт по типу игры); `components/layout/`
(шапка «Mini Games», сайдбар с **селектором типа игры**); `components/ui/` (28
shadcn), `components/agg/`, `components/common/` (старый `DataTable`, фильтры);
`lib/api/` (`api-client.ts` — `ky.extend({prefixUrl: VITE_API_URL})`, Bearer из
`localStorage['token']` (JSON-строка), `afterResponse` парсит **каждый** ответ
как JSON; по домену `endpoints.ts` + `types.ts`); `queries/` (TanStack-хуки);
`pages/<раздел>/` (`page-*.tsx`, `components/`, `hooks/use*Filters.ts`,
`schemas/*SearchParamsSchema.ts` — **фильтры живут в URL**);
`providers/TypeIdProvider.tsx` (`localStorage['typeId']`, дефолт `'1'`, уходит
почти во все запросы).

**Разделы:**

| маршрут | что | эндпоинты |
|---|---|---|
| `/login` | форма «User name / Password» (поле `email`) | `admin/auth` |
| `/rounds` | сводка `AggregateTable` + список раундов; фильтр игра/даты, сортировка | `admin/games/rounds/aggregate`, `v2/admin/rounds`, `admin/games?typeId` |
| `/rounds/:gameId/:id` | карточка раунда + ставки | `admin/games/{g}/rounds/{r}[/bets]` |
| `/users`, `/users/:id` | игроки, блокировка, ставки игрока | `v2/admin/players[/{id}[/bets|/block/switch]]` |
| `/deposits` | пополнения, только чтение | `admin/wallets/deposits` |
| `/transactions` | вкладки **Внутренние / Внешние**; у внешних диалог «Детали» с аккордеоном попыток (url, http, ms, error), табы Запрос/Ответ, строки Crash session / Launch token; keyset-пагинация `cursor`/`direction`; поиск только по точным значениям | `admin/wallets/transactions[/external]` |
| `/statistics` | график банка, пользователи, метрики; **имена игр захардкожены** в `UserMetrics.tsx` | `admin/account/history`, `admin/metrics` |
| `/settings` | `typeId === '1'` → `CrashGamesForm` (коэф. на 2 и 15 с, ожидание, просадки, демо-режим), иначе `SlotsForm` | `admin/settings/{typeId}[/reset]` |
| `/currencies` | CRUD валют | `admin/currencies` |
| `/projects` | проекты-партнёры: имя, «Внутренний проект», ключи `gpk_…`/секрет, URL user-info / bet / win / rollback | `admin/projects` |

Ролей в UI **нет**: один тип пользователя, любой залогиненный видит всё
(мерчантская изоляция — только на бэке). Разделы users/roles/merchants/games
существуют лишь в ветке `sandbox/dev-admin2-redesign` (61 коммит Полины,
06–08.2026, на моках, отстаёт от `main` на 55 коммитов — в лоб не сливать).
`pages/withdrawals/*` — мёртвый код (маршрут снят).

**Окружения:** `.env.dev` и `.env.local` → `https://dev.api.crash-heroes.com/api`,
`.env.main` → `https://api.crash-heroes.com/api`; выбираются `vite build --mode
dev|main` (`build:dev`/`build:main`). **Обычный `npm run build` без mode берёт
dev-API из `.env.local`**, поэтому `scripts/check-api-url.mjs` после сборки
проверяет, что нужный URL попал в `dist/`. Все три `.env.*` закоммичены force
(в `.gitignore`), секретов нет.

**CI** (`.gitlab-ci.yml`): только `dev` и `main`; `node:24`, `npm ci`, `npm run
build:dev|build:main` (**`tsc -b` и eslint в CI не запускаются** — они только в
скрипте `build`), артефакт `dist/`; деплой `alpine` + rsync `--delete` в
`/home/admin/crashgames/minigames-admin-front/`, до 5 попыток. `SERVER_HOST` и
`SSH_PRIVATE_KEY_BASE64` — переменные GitLab по environment.
`.github/workflows/` — реликт первого коммита, не работает.

**Грабли:** `afterResponse` роняет не-JSON ответы (HTML от nginx при 408/502)
непонятной ошибкой парсинга; `clearAccessToken` — переприсваиваемая переменная,
no-op до первого `useAccessToken`; два табличных движка (новое — на `AggTable`);
сортировка раундов по `duration/coefficient/prizes/profit` вешает MySQL на 30 с
(см. грабли и TODO); интерфейс по-русски без i18n, часть заголовков английские;
`yup` в зависимостях не используется.

### `catalog-app` — каталог, демо-сайт, мобилка

**Что это:** лобби игрока «Crash Heroes Catalog» — Framework7 8 + Vue 3 + Vite 5
+ TypeScript, Capacitor 6 (iOS/Android), workbox (PWA). Показывает баннеры,
категории игр, лидерборд, профиль и кошелёк; саму игру открывает в
**`<iframe>` внутри f7-popup** по `game.link` из API. **WebSocket каталог не
открывает** — его открывает сборка игры внутри iframe. Сгенерирован
framework7-cli (`framework7.json`, template `tabs`). 132 коммита с 08.2024
(Ilya Titov, Valery Shcherbinin). На ревизии 14.09 считался замороженным с
2026-06-09, но `fetch` 18.09 принёс в `origin/main` два коммита Титова от
02.09 («fix(): fix cards») — **репо живой, перед работой подтягивать**. CI нет.

**Два таргета** (`src/targets/origin/` и `src/targets/demo/`, каждый — корень
Vite со своим `index.html`, `core/app.ts`, `core/routes.ts`, `.env`,
`manifest.json`): `origin` — полноценный продукт (Telegram Mini App + iOS/Android
+ web; GEM/RUB/XTR, Apple IAP, LanPay, Telegram Stars) → `app.<домен>`; `demo` —
его копия для `demo.<домен>` (`client_type=demo`, `game_currency=GEM_DEMO`,
бонусов нет). Копипаста: 26 файлов отличаются в основном импортами, фиксы делать
дважды, уже разошлись (`close()` в origin зовёт `f7.popup.close`, в demo — нет).
Общий код — `src/global/`: `services/service-app/ServiceApp.ts` (синглтон-DI
`ServiceApp.of().service<T>("key")`), `service-api/ServiceApi.ts` (fetch-обёртка,
`{success,data}`), `services/data/*` (стор на Vue `ref()`: auth, games, banners,
categories, leaderboard, balance-operations), `service-telegram/`
(initData, safe-area, `openInvoice`), `service-inapp-purchase/` (продукты
`coins100/500/1000/10000`, верификация `/api/app/purchase/apple/verify`),
`service-errors/` (401 → сброс токена и реинициализация), `repositories/`,
`models/` (class-transformer, `lodash-humps-ts` snake→camel).
Роуты: `/mobile/games|leaderboard|profile|balance-operations|history-balance-operations`,
`/desktop/games|leaderboard|profile` (выбор по `innerWidth > 600`).

**API** — всё `/api/app/*`: `token`, `auth` (Telegram), `profile`,
`profile/avatars`, `balance`, `deposit/demo`, `banners`, `categories`,
`categories/{id}/games`, `leaderboard`, `wallet/history|deposit|withdraw/*`,
`purchase/apple/verify`. **Авторизация web:** `device_id = crypto.randomUUID()`
в localStorage → RSA публичным ключом `APP_PUBLIC_KEY` (node-forge) → `GET
/api/app/token?device_id=<base64>` (demo: `&client_type=demo&game_currency=GEM_DEMO`)
→ `token` → `Authorization: Bearer`. В Telegram — `POST /api/app/auth` с `initData`.

**Запуск игры** (`targets/*/popups/popup-game/PopupGameController.ts::generateGameURL`):
`game.link + '?' + params`. Вне Telegram — `authToken=<players.token>&bets=2&loaded=true`;
в Telegram — `type=telegram`, токен уходит `postMessage` в iframe после события
`ready` (`{gameParams:{token,bets,loaded}, userProfile}`). Всегда `safeAreaTop/Bottom`,
`tgContentSafeAreaInset*`, `currency=<gameCurrency>`. **`balanceFraction` и
`closeIcon` здесь нет** — их добавляет только `GameLaunchService::makeGameUrl`
для партнёрских сессий. Обратный канал: `message` из iframe — `{event:
'close'|'ready'}`, `redirect: 'payment'` → попап Telegram Stars.

**Окружения и сборка.** `demo.config.js` ≈ `origin.config.js` (`root`/`envDir` =
`src/targets/<target>`, `envPrefix: 'APP'`, `outDir: www/`); окружение выбирает
**npm-скрипт**: `dev`/`build` → origin, `dev:demo`/`build:demo` → demo;
`build-capacitor-ios|android` → `cap copy`. Переменные `APP_API_BASE_URL`,
`APP_PUBLIC_KEY`, `APP_FIREBASE_*`, `APP_TARGET_TYPE`. Грабля: `.env` есть только
в `src/targets/origin/` (не в гите) и в нём `APP_TARGET_TYPE=demo` — демо-сайт,
похоже, собирается origin-таргетом с типом demo; `src/targets/demo/.env`
отсутствует, `build:demo` соберётся с пустыми `APP_*`. Деплой руками: `www/`
копируется в `/home/admin/crashgames/demo` или `app`.

**Мобильные сборки** реальные: `capacitor.config.ts` `appId com.crashheroes`;
iOS `MARKETING_VERSION 1.0.2` build 3, только портрет; Android
`applicationId` **`fanbattle.ru`** (след другого проекта), versionCode 1.
**В гит закоммичен keystore** (`android/*.keystore`) и `.idea/`.

**Грабли:** `ServiceApi.ts` — `import * as console from "console"` (Node-модуль
в браузере), GET при не-401 ошибке молча `null`; `ServerResponse.ts` тянет
мусорные автоимпорты из `@capacitor/assets` и `dom7`; Firebase инициализируется
всегда, хотя чтение настроек из Firestore закомментировано; workbox ждёт
`.core`/`.styles`, Vite выпускает `.js`/`.css` → JS/CSS не в precache;
`index.html` обоих таргетов ссылается на `/src/targets/origin/manifest.json`
(dev-путь); `alert(e)` в отладке; UI по-русски без i18n; незакоммиченный
`console.log(url)` в `demo/.../PopupGameController.ts:67`.

## Новый движок — `game-engine-rng` (старт 2026-09-18)

Движок под новую игру — **отдельный репо и отдельный скил `game-engine-rng`**
(`~/Documents/Work/CrashGames/game-engine-rng`, remote
`crash-heroes/backend/game-engine-rng`). Стек, архитектура, команды, открытые
вопросы, точки стыковки с этой системой и список «чего не повторять из старого
движка» — всё там. Здесь остаётся только то, что касается серверов и остальных
четырёх репо; когда новому движку понадобится строка в `games`, серверный
эндпоинт Laravel, порт/nginx или место в `smoke.sh` — правки этой стороны
записывать сюда.

## Как работают игры

Игрок открывает **демо-сайт** (`demo.` / `dev.demo.`) — это SPA-оболочка. Она грузит
сборку конкретной игры с `games.` и открывает вебсокет на `server.<домен>/<gameId>`,
где nginx проксирует на движок `127.0.0.1:300<gameId>`.

Движок (`app_service/src/main.mjs`) крутит вечный `setInterval` с шагом
`UPDATE_INTERVAL_MS = 50` мс: создаёт раунд, шлёт тики, завершает, создаёт следующий.
Раунд длится ~14 секунд. Каждый созданный раунд он пишет в API
(`POST /api/server/round` на Octane), оттуда — в `game_crash_rounds`.

**Протокол вебсокета** (типы: `auth`, `bet`, `cancel`, `info`, `jump`, `rates`, `tick`):

| Что | Нужна авторизация | Зачем |
|---|---|---|
| `{success:true, id}` при подключении | нет | движок принял соединение |
| `{"type":"rates"}` → история коэффициентов | **нет** | ← этим и проверяем живость |
| `{"type":"tick"}` (шлёт сервер) | **да** | тики идут только клиентам с `player.token` |
| `auth` / `bet` / `jump` / `cancel` | да | игровые действия |

> Ключевой момент для любых проверок: **тики анонимно не увидеть** — в `main.mjs`
> broadcast идёт только при `client.player && client.player.token`. Поэтому живость
> меряем через `rates`, а не через `tick`.

## Проверка живости (после любых правок)

> **По фразе «проверь игры» — сразу запускай это на ОБОИХ серверах и отчитывайся.**
> Ничего не уточняй: если среда не названа, проверяются и прод, и dev.

`smoke.sh` — лежит рядом с этим скилом и на обоих серверах в `~/smoke.sh`.
Среду определяет сам, код возврата 0 = всё хорошо.

```bash
ssh admin@78.141.216.99  '~/smoke.sh'   # прод
ssh admin@167.233.24.119 '~/smoke.sh'   # dev
```

Занимает ~50 секунд (основное — пауза 35 c между замерами коэффициентов).
Переменные: `RATES_GAP` (пауза, по умолчанию 35), `WAIT_SEC` (таймаут вебсокета, 12).

Проверяет:
1. **Сайты** — `demo`, `api`, `admin`, `games`
2. **Вебсокет каждой игры** — приветствие + два замера `rates` с паузой:
   история коэффициентов обязана пополниться
3. **БД** — по каждой игре последние 10 раундов: свежесть (< 2 мин) и
   `COUNT(DISTINCT coefficient) >= 2`
4. **pm2** — все online, рестарты не копятся
5. **Диск** — меньше 85%

Пункты 2 и 3 намеренно дублируют друг друга с разных сторон: **был случай, когда
коэффициент переставал меняться**. «Сайт отвечает 200» и «процесс online» такое
не ловят — движок может крутиться, отдавая одно и то же значение. Живой замер через
публичный вебсокет ловит это снаружи, проверка по БД — изнутри.

Обновить скрипт на серверах после правки:
```bash
for h in 78.141.216.99 167.233.24.119; do
  ssh admin@$h 'cat > ~/smoke.sh && chmod +x ~/smoke.sh' < ~/.claude/skills/crash-games/smoke.sh
done
```

Две вещи, которые выглядят как поломка, но норма: `games.<домен>/` отдаёт **403**
(нет индекса каталога — проверять надо конкретную сборку, `/fatguy/`), и счётчик
рестартов `pm2-logrotate` растёт от каждого `pm2 set`.

## Что важно знать (грабли)

1. **Раунды крутятся непрерывно, независимо от ставок.** На проде 12.5 млн раундов,
   но с игроками (`players > 0`) — всего ~18 тыс, то есть **0.15%**. Любой запрос
   с фильтром `players > 0` без подходящего индекса перебирает миллионы строк.

2. **`sequence_id` = `COUNT(*)` по игре.** `RoundObserver::created` на каждый новый
   раунд делает `SELECT COUNT(*) FROM game_crash_rounds WHERE game_id = N` —
   436–582 мс по ~1 млн строк, ~4 раза в минуту на игру. Постоянная фоновая нагрузка.
   **Следствие:** любое удаление старых раундов отматывает счётчик назад → дубли номеров.

3. **`octane max_execution_time = 30`** (`config/octane.php`). Запрос дольше 30 с →
   Swoole убивает воркер `SIGKILL` → nginx отдаёт **408**. В `storage/logs/swoole_http.log`
   это видно как `abnormal exit, status=0, signal=9`. Воркеров всего 4.

4. **`innodb_buffer_pool_size = 128 МБ`** — дефолт MySQL, при базе ~9 ГБ. Почти любой
   промах мимо кеша уходит на диск.

5. **`pm2-admin.service` = `Type=forking` + `PIDFile=~/.pm2/pm2.pid`.** Если диск полон,
   pm2 не может записать pid-файл → systemd не видит старта → таймаут 90 с → kill →
   бесконечный цикл рестартов (доходило до 934). Симптом: сервис `activating`/`failed`,
   при этом процессы то поднимаются, то умирают.

6. **Логи движков пишут `[DEBUG] Round tick` каждые 50 мс** (`UPDATE_INTERVAL_MS: 50`).
   Это 99.3% строк, ~260 МБ в сутки на игру. Уровень логирования в
   `app_service/src/services/logger.class.mjs` **не фильтруется вообще** — `debug()`
   всегда пишет в stdout, `NODE_ENV=production` игнорируется.

7. Зависший запрос не умирает от того, что клиент отвалился по 408 — он продолжает
   грузить MySQL. При разборе тормозов **сначала убей висящие запросы**, иначе замеры врут.

## Игровые сессии внешней интеграции

Модель: краши — провайдер игр, партнёр (Lucky) — оператор, у которого живут
игроки и деньги. Контракт списан с Aviatrix Seamless Wallet API
(`docs.aviatrix.bet`, Cloudflare пускает только через `r.jina.ai/<url>`).

### Как это работает сейчас (2026-08-18, схема переделана)

> Решение от 17.08 «оставить в ссылке вечный `players.token`» **отменено**.
> Причина: с общим токеном нельзя понять, в какой из открытых вкладок играет
> игрок — пять кликов по игре у партнёра дают пять сессий, а токен один.

**В ссылку уходит сессия.** `authToken = game_sessions.crash_session`, вид
`sess_<uuid>`. Префикс обязателен: в этом же поле у внутренних игроков едет
вечный `players.token`, и по префиксу бэк выбирает таблицу без перебора.
Константа и хелперы — `GameSession::TOKEN_PREFIX`, `makeToken()`,
`isSessionToken()`.

Фронты игр пересобирать **не понадобилось** — параметр так и называется
`authToken`, для них это просто другая строка.

**Параметры ссылки сессионной игры** (`GameLaunchService::makeGameUrl`, только
партнёрский `/game/url`): `authToken=sess_…&bets=2&loaded=true&balanceFraction=true&closeIcon=false`.
Последние два добавлены 20.08 по договорённости с фронтом игр — интеграционная
версия открывается с дробной частью баланса (у партнёра центы) и без иконки
закрытия; у внутренних игроков их нет. (Сначала уходило `balanceFraction=false`,
уточнено Ильёй в тот же день.)

Полная цепочка запуска:

    игрок жмёт игру у Лаки
      → POST /v1/core/games/{gameId}/launch (x-public-key + JWT игрока)
      → Лаки создаёт свою сессию, зовёт наш POST /api/external/game/url
        тело { game_id, session }  (до 11.09 — sessionToken; старое имя
        принимается как запасное, см. журнал 14.09)
      → мы создаём game_sessions, отдаём ссылку с sess_-токеном
      → игра открывается, идёт в /api/app/profile
      → GameSessionResolver видит префикс, находит сессию, при первом
        обращении зовёт партнёрский /user/info (до 11.09 — /playerInfo), заводит игрока,
        заполняет player_id / external_player_id / currency и зеркалит баланс
      → движок авторизует тот же токен через GET server/games/{id}/player
      → тики идут

**`GameSessionResolver` подключён в шести местах** — их действительно шесть,
и пропуск любого ломает не то, что ожидаешь:

| место | что сломается без него |
|---|---|
| `PlayerAuth` | Bearer для `/api/app/*` |
| `PlayerController::getProfile` | ищет ещё и по `token_id` из query |
| `ServerGameController` | **авторизация движка** → нет тиков, коэффициент стоит |
| `ServerPlayerController` (2 места) | серверные методы игрока |
| `GameCrashRoundController::getPlayerFromRequest` | **денежный путь** |
| `AppController` | поиск по `token_id` |

**`game_id` вместо `sys_name`.** В теле `/game/url` поле называется `game_id` и
содержит числовой `games.id`. У Лаки в `games.external_id` лежит тот же id.
`sys_name` принимается для совместимости, но обе стороны переехали.

**Колонки сессии (с 20.08):** `crash_session` — наш `sess_`-токен, уходит в
браузер (до 20.08 `session_local`); `launch_token` — токен партнёра, выданный
при запуске игры, наружу не попадает (до 20.08 `session_external`). У Лаки
колонка `game_sessions.launch_token` и ключ `metadata.launch_token` в
транзакции расчёта (раньше `session`). Wire-контракт **с 11.09 везде `session`**:
`/game/url`, `/user/info`, `/bet`, `/win`, `/rollback` (до того `/game/url` и
`/playerInfo` принимали `sessionToken`). В админках: у нас в
деталях внешней транзакции строки «Crash session» и «Launch token» (ресурс
отдаёт плоские `crash_session` / `launch_token`, поиск ищет по обеим), у Лаки в
деталях транзакции — «Launch token».

### Деньги: seamless

Локальный кошелёк сессионного игрока — **зеркало, а не счёт**. Правда живёт у
партнёра.

- ставка → `POST api_bet`, выигрыш → `POST api_win`. **Два разных «отката»,
  не путать** (проверено по коду 14.09):
  - *игрок сам снял ставку до старта раунда* (`remove_bet`, `remove_bets`) →
    `PartnerWalletService::cancel()` → **тот же `api_win`** с суммой ставки и
    полем **`cancel: true`**; у нас тип `cancel`, у Lucky `WinRequest.cancel`
    → `CancelBet`. Отдельного URL для этого нет и не нужно;
  - *ставка не подтвердилась* (таймаут/5xx на `/bet`) → `rollback()` →
    `POST api_rollback {session, txId}` (с 11.09, см. ниже).
  Поля `operation` (`SettleBet`/`CancelBet`), `playerId`, `gameId`, `currency`
  из тела **убраны 09.09**;
- `txId` генерим мы, это ключ идемпотентности: повтор не двигает деньги второй
  раз и возвращает тот же баланс. `txId` = **uuid строки журнала**
  `player_external_transactions` (отдельной колонки `tx_id` нет, она дублировала
  `uuid`);
- зеркало пишется **прямым присваиванием** из поля `balance` партнёрского
  ответа (по контракту оно обязательное в каждом ответе `/bet` и `/win`);
- **локальных транзакций у сессионного игрока нет.** `BetObserver` разведён:
  `roundBet` / `roundWin` / `roundCancel` не вызываются, если у игрока живая
  сессия. Гейт — `GameSession::liveForPlayer()`;
- проверку достаточности средств для сессионных игроков не делаем — решает
  партнёр.

**Почему без локальных транзакций (грабли, пойманные 18.08).** `TransactionService`
считает баланс **цепочкой от предыдущих транзакций**, а не из колонки кошелька.
У нового партнёрского игрока цепочки нет, поэтому `balance_before` вышел `0`,
ставка 100 дала `-100`, и это затёрло зеркальную тысячу. Дальше вторую ставку
в том же раунде отклонила проверка средств — молча. Вывод: **зеркало
присваиванием несовместимо с цепочкой транзакций**, они не могут писать в один
кошелёк.

**Журнал операций** — `player_external_transactions`, `service = partner`,
типы `bet` / `win` / `cancel`. Там же `balance_after` (баланс по версии
партнёра), `attempts` (json с `at/http/ms/error` **и url запроса**),
`attempts_count`, `last_error`, `bet_id`, `round_uuid`, `ext_id`
(партнёрский `processedTxId` из ответа — обратная ссылка на их запись).
Индексы `pet_service_status_index`, `pet_bet_id_index`.

**Тело `/bet` и `/win` (с 09.09):** `txId` (uuid строки журнала), `betId`,
`roundId`, `betNumber` (номер ставки внутри раунда, 1/2), `amount` (**minor
units**, `MoneyHelper::toMinorUnits`), `session` (= `launch_token` партнёра).
Игрок, игра и валюта у партнёра выводятся из `session`. На **ретраях** `/win`
зеркало обновляется из ответа так же, как на первой попытке. Ставка на крашах
создаётся до похода к партнёру (`wasRecentlyCreated`) и удаляется, если партнёр
отказал.

**Rollback (с 11.09, `d804f7a`).** Если `/bet` отказал непонятно (таймаут,
`5xx` — списание могло пройти), шлём `POST api_rollback {session, txId}`, где
`txId` — uuid исходной ставки. Это **отдельная строка журнала** типа `rollback`
с `amount 0`, своим uuid и `game_session_id`; ретраится по общей лестнице.
До 09.09 компенсацией был `CancelBet` в `/win`, 09–11.09 — отдельный `api_cancel`
(колонка добавлена и через два дня удалена миграцией
`2026_09_11_100001_rename_api_player_info_and_drop_api_cancel`).
Тесты — `tests/Feature/PartnerRollbackTest.php`.

**Подпись исходящих (с 09.09, `ProjectSignHelper::signRequest`):**
`HMAC-SHA256(secret, "METHOD\n/path\n{}\n<ksort-json тела>")` — метод и путь
входят в подпись, перехваченное тело нельзя переиграть на другой эндпоинт.
**Входящие** `/api/external/*` по-прежнему проверяются по одному телу
(`AuthProjectSignMiddleware`, `ProjectSignHelper::sign`). Причина — так подписывает сама
Лаки: её вызов провайдера (`game-launch.service.ts:104`) — `hmacSignature(secret,
canonicalPayload(body))`, только тело; а её **входящие** (`game-provider-signature.guard.ts`
→ `signedPayload`) — `METHOD\n/path\n{query}\n{body}`. **Грабля 18.09:** скрипт
подписи из Apidog-коллекции **Lucky** (метод+путь) не подходит к нашему
`/api/external/game/url` → `Invalid authentication signature`; для нашего API в
Postman подписывать `canonical(body)`. **Сделано 18.09 (по «2» Ильи), в рабочем
дереве `develop`, не закоммичено:** `AuthProjectSignMiddleware` принимает **обе**
схемы — сначала «только тело» (как раньше, Лаки не ломается), затем
`validateRequestSign`: `ProjectSignHelper::signRequest(method, getPathInfo(), body,
secret, query())` (у `signRequest` новый необязательный `$query`, исходящие вызовы
не изменились). Спека `docs/openapi-external.yaml` описывает обе. Проверено на
локальном API: скрипт из Apidog проходит, «только тело» — 200, неверная подпись и
подпись от другого пути — 400, query подписывается. Дальше при желании — перевести
вызов Лаки на метод+путь (принимающая сторона уже готова). Закоммичено и запушено
`e069c39` «Accept the method and path signature scheme on incoming external
requests» (18.09, CI → dev); docblock в `validateRequestSign` убран следующей правкой.
- **`/api/external/game/url` для RNG-игр отдаёт сессию** (18.09, в рабочем дереве,
  ждёт команды на коммит): `GameLaunchService::findGame` для типа `crash-rng`
  не требует `link` и `settings.mode`; `IntegrationController::gameUrl` при пустом
  `link` отвечает `{"session": "sess_…"}` вместо `{"url": …}`; ретрай с тем же
  `session` отдаёт ту же сессию; краш-игры — как раньше. Спека описывает `session`.
  Локально проверено: `test_rng` (**id 18 локально, 19 на dev**) → 200 `session`.
  `GET /api/external/games` RNG-игру без ссылки по-прежнему не показывает.
  **`game_id` принимает `id` или `uuid`** (Илья: «для rng — uuid, можно или id или
  uuid»): `findGame` — цифры → `id`, `Str::isUuid` → `games.uuid` (регистр не важен),
  иначе `sys_name` (совместимость). Спека обновлена. Локально: uuid, UPPER-uuid, id,
  `sys_name` → 200; чужой uuid → 404; краш-игра по uuid → `url`.
  **У RNG-сессий нет приставки `sess_`** (Илья: «для rng убираем, старое не ломаем»):
  `GameLaunchService::launch` для `crash-rng` пишет в `crash_session` голый uuid,
  у крашей — `sess_…` как раньше. Следствие: **`GameSessionResolver` RNG-сессию не
  узнает** (он ветвится по `isSessionToken`), `/api/app/*` с ней не работает — и не
  должен; эндпоинт, по которому движок получает игрока по RNG-сессии, должен искать
  `game_sessions.crash_session` напрямую, без опоры на приставку. `~/sign-external.sh` на
dev считает только тело — годится **только для входящих**, для проверки ключей в
сторону Лаки он больше не подходит.

> Разделение: **у нас журнал операций, у партнёра — счёт.** `account_transactions`
> остаётся навсегда для внутренних игроков, партнёрские туда не попадают.

**Ретраи по правилам Aviatrix:** повтор только на `5xx` (кроме `501`) и `429`,
на `4xx` — никогда. С 11.09 (`94863bd`): `PartnerOperationRetryJob` — `$tries = 0`
(**бесконечно**), очередь **`integration`** (раньше уходила в `default`, которую
воркер не слушал), лестница `1s, 2s, 5s, 15s, 1m, 5m, 15m, 30m, 1h, 3h, 12h` и
дальше по 12 ч. Redis (`QUEUE_CONNECTION=redis`), воркер
`crashgames-integration-worker` под supervisor (`--queue=integration
--max-time=3600`, перезапуск раз в час — норма).

Асимметрия: **`/win` и `/rollback` ретраятся** (мы должны деньги или
подтверждение отката), **`/bet` — нет**. Не дошло — ставка отклоняется, а если
отказ был непонятный — сразу `rollback` с `txId` ставки.

### Настройки проекта

`projects`: `is_internal` (boolean, **новый проект по умолчанию внутренний**),
`api_key` / `api_secret` (nullable с 10.09, выдаёт партнёр), `api_user_info`
(до 11.09 `api_player_info`; миграция заодно заменила `/player/info` →
`/user/info` в существующих URL), `api_bet`, `api_win`, `api_rollback`.
У Lucky это `POST …/external/game-provider/{user/info,bet,win,rollback}`.
Старые `api_get_balance` /
`api_post_balance` **удалены вместе со всей асинхронной схемой** — джобы
`IntegrationPlayersGetBalanceJob` / `IntegrationPlayersUpdateBalanceJob` и их
вызовы в наблюдателях снесены.

`Project::innerId()` читает `is_internal`, а не сравнивает имя со строкой
`'Inner'` — раньше переименование проекта в админке молча ломало создание
внутренних игроков.

В админке у внутреннего проекта скрыты ключи и все четыре адреса —
переключатель управляет видимостью. Удаление проекта с живыми `game_sessions`
починено 10.09 (`756637b`).

### Ключи и проекты — где легко ошибиться

**С 2026-09-10 пару выпускает Lucky, а не мы.** У них в админке провайдера
(вкладка Integration) кнопка «Generate»: публичный `gpk_…`, приватный 64 hex,
приватный показывается один раз. Обе половины вставляются у нас в проект —
поля «Публичный ключ партнёра» / «Приватный ключ партнёра» (`projects.api_key`
и `api_secret`, varchar(100) UNIQUE). `store` и `update` проекта принимают их с
того же дня; если при создании не передали — генерим свои, как раньше.
Повторное нажатие «Generate» у них = ротация: до вставки новой пары у нас
подпись не сойдётся в обе стороны.

Пары ключей две, и они разные по направлению:

| направление | чем подписывается | чем проверяется |
|---|---|---|
| Лаки → краши | `game_providers.public_key` / `private_key` | `projects.api_key` / `api_secret` |
| краши → Лаки | те же `projects.api_key` / `api_secret` | `game_providers.public_key` / `private_key` |

То есть **пара должна совпадать с обеих сторон**. На деве провайдер
`crash-heroes` был подписан ключами проекта **2**, а тестировали мы проектом
**5** — сессии копились под 5, а реальный запуск лёг бы под 2. 18.08 Илья
перевесил провайдера на ключи проекта 5.

Быстрая проверка, что ключи сходятся: подписать пустое тело секретом проекта и
дёрнуть любой метод Лаки. `Player not found` — подпись принята,
`Unknown provider key` / `Invalid signature` — нет.

Помощник для подписи лежит на дев-сервере крашей:

    ~/sign-external.sh <project_id> '<json-тело>'

печатает готовые `x-api-key` и `x-sign`. Секрет наружу не отдаём никогда — он
только ключ HMAC. `api_key` — uuid с дефисами, `api_secret` — 64 hex без
дефисов; их путают.

## Документация внешнего API (Apidog)

**Проект в Apidog: `CrashGames API`, id `1347186`.** (Соседние проекты Ильи:
`Lucky Server` 1341455, `Lucky-api` 1230941 — не перепутать.)

Обновляю коллекцию сам, через уже установленный и авторизованный CLI
(`apidog` 2.2.9, аккаунт `it@agg.one`). **Токен нигде не хранится и не нужен** —
CLI держит сессию сам, проверка: `apidog whoami`. Если Илья присылает новый
токен в чат — не сохранять его в файлы и не использовать, работать через
залогиненный CLI.

    apidog project list                                    # найти проект
    apidog endpoint list --project 1347186                 # что сейчас в коллекции
    apidog import --project 1347186 --format openapi \
      --file docs/openapi-external.yaml                    # залить спеку

Импорт мержит по методу+пути: существующие обновляются, новые создаются.
**Удалённые из кода методы импорт не убирает** — их надо гасить руками
(`apidog endpoint delete <id> --project 1347186`), иначе партнёр будет видеть
в доке несуществующий эндпоинт.

Общие правила работы с Apidog — в скиле `apidog` (порядок записи, модули,
окружения, прескрипты подписи, WebSocket, чего CLI не умеет). Упоминавшегося
раньше `agg-api-handling` на этой машине нет.

Спека живёт в репозитории бэкенда: `docs/openapi-external.yaml`, отдаётся по
`https://dev.api.crash-heroes.com/api/docs/external.yaml` (и та же ссылка без
`dev.` на проде). Пути в спеке — **полные** (`/api/external/game/url`), а
`servers` — только хост: так они совпадают с тем, как эндпоинты заведены в
коллекции. У Laravel генератора спеки нет (в отличие от Lucky, где её строит
NestJS на `/docs-json`), поэтому **спека правится руками**.

**Правило: меняешь что-либо в `routes/api/api.php` внутри группы `external`
или формат её запросов/ответов — в том же коммите правишь спеку.** Это касается
новых полей в теле, новых кодов ошибок, переименований, смены заголовков.
Забыл — дока молча устареет, и Ilya будет тестить по несуществующему контракту.

Проверка перед коммитом:

    python3 -c "import yaml; yaml.safe_load(open('docs/openapi-external.yaml')); print('ok')"

После деплоя убедиться, что отдаётся:

    curl -s -o /dev/null -w '%{http_code}\n' https://dev.api.crash-heroes.com/api/docs/external.yaml

Тексты ошибок в спеке и в `app/Http/Responses/External/IntegrationError.php`
должны совпадать дословно — они взяты из доки Aviatrix, партнёр разбирает их
по строке.

## Runbook'и

### Деплой кода на сервер (гит-бандлом) — УСТАРЕЛО

> **С 17.08 на серверах нет `.git`** (снесён при переходе на CI, бэкап в
> `~/deploy-backups/git-metadata-*.tgz`), поэтому бандл-деплой ниже больше не
> работает. Актуальный путь: push в `develop` (dev) или `main` (прод) → CI
> делает rsync + `migrate --force` + `octane:reload`. Ручной аварийный вариант —
> скопировать изменённые файлы поверх `/home/admin/crashgames/minigames-admin-back/`
> и `php artisan config:clear && php artisan octane:reload`. Раздел оставлен как
> история.

**На серверах нет приватных ssh-ключей** — ни на проде, ни на dev. `git pull` оттуда
невозможен в принципе: `Permission denied (publickey)`, а на проде вдобавок не было
gitlab в `known_hosts`. Пробросить агент тоже не выйдет: в `~/.ssh/config` у Ильи
стоит `IdentityAgent ~/.1password/agent.sock`, а `ForwardAgent` пробрасывает
`SSH_AUTH_SOCK`, где нужного ключа нет.

Историю переносят **бандлом** (в `~/` на проде лежат `backend-main.bundle`,
`sign-callbacks-main.bundle` — следы этого же способа).

```bash
# 1. локально: инкрементальный бандл от коммита, который стоит на сервере
cd ~/Documents/Work/CrashGames/crash-heroes-backend-api-core
SRV=$(ssh admin@78.141.216.99 'cd /home/admin/crashgames/minigames-admin-back && git rev-parse HEAD')
git bundle create /tmp/backend-main.bundle $SRV..main
git bundle verify /tmp/backend-main.bundle

# 2. перенос
scp /tmp/backend-main.bundle admin@78.141.216.99:~/backend-main-new.bundle

# 3. на сервере: СНАЧАЛА проверить бандл и загрузить историю,
#    и только потом трогать рабочее дерево
ssh admin@78.141.216.99
cd /home/admin/crashgames/minigames-admin-back
git bundle verify ~/backend-main-new.bundle
git fetch ~/backend-main-new.bundle main:refs/remotes/bundle/main
git log -1 --format='%h %s' refs/remotes/bundle/main    # убедиться, что коммит тот

# 4. бэкап всего, что изменено вручную, затем сброс
mkdir -p ~/deploy-backups/pre-pull-$(date +%Y%m%d-%H%M%S)
git status --porcelain
git reset --hard refs/remotes/bundle/main

# 5. миграции и ОБЯЗАТЕЛЬНО перезагрузка Octane
php artisan migrate --force
php artisan config:clear && php artisan route:clear
php artisan octane:reload

# 6. проверка
~/smoke.sh
```

> **Порядок важен.** Один раз я снял локальные правки до проверки доступа, `pull`
> упал на host key, и прод на несколько секунд остался с кодом двухдневной давности —
> без фикса гонки. Спас бэкап, сделанный шагом раньше. Сначала убеждаемся, что
> история доступна, потом трогаем файлы.

> **Без `octane:reload` деплой не считается.** Код живёт в памяти воркеров: файлы
> обновятся, а приложение продолжит работать на старой копии. Новый маршрут в такой
> ситуации отдаёт 500.

### Сжатие архивов логов

**В pm2-logrotate 3.0.0 настройка `compress` не работает.** В окружении процесса
`compress='true'`, `parseBool` её понимает, ошибок в логе модуля нет - но ротация
всё равно кладёт несжатые `.log`. Перезапуск модуля не помогает.

Поэтому сжимаем отдельно, скриптом по cron (есть на обоих серверах):

```bash
~/gzip_logs.sh                      # разовый прогон
crontab -l | grep gzip_logs         # */10 * * * *
```

Скрипт трогает только архивы (`*__ГГГГ-ММ-ДД_ЧЧ-ММ-СС.log`) и только старше 5 минут,
чтобы не поймать файл, который модуль ещё пишет. Живые `output_N.log` не трогает:
в них пишут открытые дескрипторы pm2.

Эффект: архивы сжимаются примерно в 5 раз. Без этого при `retain 7` набиралось бы
~3.6 ГБ на машину вместо ~400 МБ.

### Диск забился логами
```bash
source ~/.nvm/nvm.sh
pm2 flush                                   # если процессы живы
# либо, точечно (pm2 пишет в режиме append, truncate безопасен):
for f in /home/admin/crashgames/logs/output_*.log; do truncate -s 0 "$f"; done
df -h /
```
Ротация уже настроена (см. ниже) — если снова растёт, проверь, жив ли модуль:
`pm2 list | grep logrotate`.

### Диагностика «апи не работает»
```bash
df -h /                                     # переполнение диска — причина №1
systemctl status pm2-admin minigames-admin-back
source ~/.nvm/nvm.sh && pm2 list
sudo journalctl -u minigames-admin-back -n 40   # лог запросов Octane
tail -40 /home/admin/crashgames/minigames-admin-back/storage/logs/swoole_http.log
```

### Поймать медленный SQL
```bash
E=/home/admin/crashgames/minigames-admin-back/.env
export MYSQL_PWD=$(grep -m1 '^DB_PASSWORD=' $E | cut -d= -f2- | tr -d '"')
M="mysql -h127.0.0.1 -uminigames_user minigames_db -B"
$M -e "SELECT id,time,state,LEFT(info,200) FROM information_schema.processlist
       WHERE info IS NOT NULL AND command<>'Sleep'\G"
# убить висящие
$M -N -e "SELECT id FROM information_schema.processlist
          WHERE command<>'Sleep' AND time>10 AND info IS NOT NULL" |
  while read id; do $M -e "KILL QUERY $id;"; done
```

### Чистка БД (скрипты лежат на серверах)
- `~/purge_old_rounds.sh` — пакетное удаление раундов старше отсечки + `game_crash_bets`
  + `account_transactions(scope='round')`. Порядок обязателен: FK `bets_round_id_foreign`
  **без** `ON DELETE CASCADE`. Удаляет по PK (`id <= граница`), а не по дате —
  у `account_transactions` нет индекса на `created_at`. `DRYRUN=1` — только посчитать.
- `~/renumber_sequence.sh` — плотная перенумерация `sequence_id` в 1..N по каждой игре.
  **Игровые процессы надо остановить** (`pm2 stop 0..12`), иначе новые раунды попадут
  между построением карты и её применением.

## Журнал: 2026-08-16

### Авария — API прода лежал ~30 часов
**Цепочка:** логи `output_*.log` выросли до 8.2 ГБ × 13 = 108 ГБ (ротации не было
вообще: ни конфига в `/etc/logrotate.d`, ни модуля `pm2-logrotate`, ни cron) →
15 авг 13:03 диск 100% → pm2 не смог записать `pm2.pid` → systemd убивал и
перезапускал сервис каждые 90 с (счётчик дошёл до 934) → все 15 приложений легли.

**Сделано на обоих серверах:**
- Освобождено 108 ГБ (прод, 100% → 25%) и 112 ГБ (dev, 96% → 17%).
- Поднят pm2, `pm2-admin.service` приведён в `active (running)`, `pm2.pid` на месте.
- Установлен и настроен `pm2-logrotate`: `max_size 100M`, `retain 7`, `compress`,
  `workerInterval 30`, `rotateInterval "0 0 * * *"`. Ротация проверена — работает.
- Добавлена страховка `/etc/logrotate.d/crashgames` (`size 1G`, `copytruncate`,
  `rotate 3`) — только на живые файлы, архивы pm2-logrotate не трогает.

### Админка раундов отваливалась по 408
`GET /api/v2/admin/rounds` висел 31 с и падал. Причина не в скорости SQL:
MySQL складывал в буфер сортировки **все 15 колонок для каждой из 18 тыс строк-кандидатов**
(фильтр `players > 0`), вместо 11 нужных → не укладывался в `max_execution_time`.

**Сделано (в репо + на проде):**
- `b7a70f6` — миграция: индекс `(players, started_at, game_id)`.
- `b611569` — `AdminRoundsController`: отложенный джойн, сортировка и пагинация
  подзапросом по одному `id`. Применяется только когда `$orderBy` начинается с `gr.`
  (в режиме мерчанта сортировка может ссылаться на алиасы вычисляемых полей).
- Оба запушены в `develop`. На проде применены вручную (`php artisan migrate`
  + файл + `octane:reload`), в таблице `migrations` запись есть — повторный деплой холостой.
- **Результат: 408 за 31 с → 200 за 0.15 с.**

### Чистка БД на dev
Отсечка — 2 месяца (`2026-06-16`). Удалено: раунды 13.50M → 4.35M,
`account_transactions` 26.87M → 8.66M, ставки по старым раундам. Прод **не трогали**.

Побочный эффект: `sequence_id` (см. грабли №2) отмотался назад — новые раунды пошли
с ~334 556, у выживших номера доходили до 1 000 546.

**Исправлено плотной перенумерацией** (`~/renumber_sequence.sh`, 3.5 минуты, игры стояли ~4 мин):
все 13 игр приведены к `1..N`, дублей стало 0 (было 291 — старые гонки, ещё до чистки).
Поскольку `COUNT(*)` снова равен максимуму, существующий генератор продолжает
выдавать корректные номера **без правки кода**. Это же решение годится и для прода
после чистки — но только как разовая заплатка: гонка при одновременном создании
раундов остаётся, её лечит только фикс генератора (см. TODO).

## Журнал: 2026-08-17

### `GET /api/admin/games/rounds/aggregate` отваливался по 408
Тот же почерк, что и у списка раундов, но причина другая — **план был правильным**:
старт от `game_crash_bets` (~31k строк), `game_crash_rounds` и `games` по `PRIMARY`.
Убивал объём случайного чтения: 30k обращений к таблице раундов на 5.7 ГБ при
буферном пуле 128 МБ.

Джойн к раундам был нужен только чтобы дойти до `games.type_id`. Но у
`game_crash_bets` есть собственная `game_id` — проверено на проде: **0 расхождений
с `game_crash_rounds.game_id` на 31 693 строках, сирот нет**; покрыта индексом
`bets_bet_complex_index`. Запрос перестроен от таблицы ставок, джойн к раундам
остался только для фильтра по датам.

`08b51d1` — `RoundController::aggregateInfo`. Результаты сверены со старым запросом:
совпадают по всем агрегатам. **408 за 31 c → 200 за 0.2 c** (без дат), 0.13 c (по игре),
**2.4 c с фильтром дат** — там джойн к раундам сохраняется, это остаточное слабое место.

> Общий вывод по обоим случаям: при буферном пуле в 128 МБ **любые ~20–30 тыс
> случайных обращений к `game_crash_rounds` съедают 10–30 секунд**. Если запрос
> тормозит, считай не строки результата, а обращения к строкам таблицы.

## Журнал: релиз 2026-08-17

`12e3f96` — мерж `develop` в `main` и раскатка на прод.

Перед переносом выяснилось, что **`main` и `develop` разошлись в обе стороны**:
в `main` было 9 коммитов, которых нет в `develop`. Копирование файлов молча
сбросило бы приветственный бонус (на проде 9999, в develop 50), вернуло бы убранный
`awardStart()` и переименовало генерируемые имена игроков с английских на русские.
Поэтому перенос сделан мержем, а не копированием; после мержа сверены все четыре
точки расхождения.

Данные прода: пересчитаны цепочки балансов, **2962 битые из 50 366 → 0**,
балансы всех 10 739 кошельков сходятся с суммой транзакций.

> Перед любым переносом файлов на прод: `diff` прод-версии с локальной. Прод живёт
> на `main`, разработка в `develop`, и они регулярно расходятся.

## Журнал: CI и поиск, 2026-08-17

### CI в GitLab
Админка (`dev`/`main`) и бэкенд (`develop`/`main`) катятся пайплайнами.
Схема — сборка в контейнере, артефакт, `rsync` на сервер. **Контейнеры живут только
в CI**: серверы остаются без Docker, туда приезжают готовые файлы.

Грабли, на которые наступили:
- образ `composer:2` приезжает с PHP 8.5, а lock рассчитан на 8.1-8.4 - берём
  `php:8.2-cli`, ровно как на серверах (8.2.31), и доставляем `ext-bcmath`;
- `bootstrap/cache` исключён из rsync, поэтому после первого деплоя там остался
  список пакетов с Collision, а vendor приехал с `--no-dev` - `artisan` переставал
  запускаться совсем. Деплой чистит кеш и делает `package:discover`;
- **зелёная джоба ещё не значит, что деплой попал куда надо**: `SERVER_HOST` в
  окружении `prod` содержал дев-адрес, и прод-пайплайн дважды раскатал на dev.
  Поймали сверкой времени изменения файлов на обоих серверах;
- без `octane:reload` деплой не считается: новый маршрут отдаёт 500, потому что
  воркеры держат старый код в памяти.

`.git` с серверов удалён (бэкапы в `~/deploy-backups/git-metadata-*.tgz`): rsync
ходит мимо него, и `git status` показывал сотни ложных изменений.

`APP_ENV` задавался **в systemd-юните** (`Environment=APP_ENV=local`), а не в `.env` -
правка файла не действовала, не помогал ни `config:clear`, ни рестарт сервиса.
Теперь прод `production`, dev `dev`.

### Поиск в транзакциях: 7.8 с -> 0.66 с
Причина была не в `LIKE`, хотя он там был. Убийца - **`OR` из коррелированных
`EXISTS`**: `whereHas` по игроку, проекту, кошельку, игре и раунду через
`meta.bet_id`. При `OR` оптимизатор не берёт индекс ни по одной ветке, сканирует все
50 тысяч транзакций и на каждой выполняет подзапросы с JSON-извлечением. И всё это
дважды - для страницы и для `COUNT`.

> Ловушка при диагностике: тот же подзапрос **отдельно** отрабатывает за 208 мс, и
> по этому замеру я снял с него подозрение. Внутри `OR` он ведёт себя иначе. Мерить
> надо форму запроса целиком, а не ветку в отрыве.

Лечение: строка поиска сначала превращается в списки id дешёвыми индексными
запросами (игроки, ставки), затем идут простые сравнения и `IN`. Валюта - отдельным
некоррелированным подзапросом, он материализуется один раз.
Замер на боевой базе до деплоя: 3131 мс -> 222 мс.

Поиск теперь только по **точным** значениям: кусок uuid ввести нельзя, нужен целиком.

## Журнал: 2026-08-18 — seamless-интеграция и CI движка

Большой день, три пласта работы. Всё **только на dev**, прод не тронут: бэкенд
крашей на `main` (`8231efc`), а вся работа в `develop`.

### CI движка игр

У `crash-heroes-backend-game-engine` не было пайплайна вовсе. Сделан по образцу
бэкенда, но с поправкой на три сервиса: `app_service` (Node, 13 процессов),
`calc_service` и `slot_service` (Python, каждый под своим venv).

- `node_modules` собирается в контейнере и едет артефактом; **venv так нельзя** —
  в него зашиты абсолютные пути, зависимости ставятся на сервере;
- **перезапускается только изменившееся.** Три независимые группы: игры, калк,
  слот. Что менялось — определяем по отчёту самого `rsync`, а не по истории
  коммитов: он показывает разницу между сборкой и сервером, поэтому не врёт
  после неудачного деплоя;
- для этого `rsync` идёт с `-c`. Без сверки по контрольной сумме CI каждый раз
  делает свежий checkout, у всех файлов новое время модификации, и «изменённым»
  оказывается весь репозиторий — 1450 файлов вместо 36;
- **удаление каталога изменением не считается** (кроме `node_modules`, где
  каталог = пакет). Иначе пустой каталог-наследие `calc_service/app/` дёргал
  калк, от которого зависят все 13 игр;
- игры перезапускаются **по одной с паузой 5 с** — рестарт рвёт текущий раунд,
  лучше потерять его в одной игре, чем в тринадцати;
- деплой-каталог полон живого состояния, которого нет в репозитории: venv
  (85 и 166 МБ), `slot_service/bank_file.json`, `node_modules` и **правленные
  руками ecosystem-конфиги**. Всё в `--exclude`; `--delete` исключённое не трогает.

Попутно закоммичены `package-lock.json` (был явно в `.gitignore`) и оба
`requirements.txt` — без них `npm ci` невозможен, а CI ставил бы не то, что на
проде. Ecosystem-конфиги в гите приведены к реальности серверов (пути были
`/var/www/...`, на машинах `/home/admin/...`), но **из раскатки исключены**.

Проверено вживую: холостой деплой (менялся только `.gitlab-ci.yml`, он в
исключениях) не перезапустил ничего — счётчики pm2 не сдвинулись.

### Внешняя интеграция переведена на seamless

Схема целиком описана выше в разделе про игровые сессии. Кратко, что сделано:

- сессия уехала **в ссылку** (`sess_`-префикс), решение от 17.08 отменено;
- `/playerInfo`, `/bet`, `/win` реализованы у Лаки; на крашах — клиент
  партнёрского кошелька, журнал операций, очередь ретраев;
- старая асинхронная схема **удалена полностью**;
- `game_id` вместо `sys_name`, колонки сессии переименованы;
- админка: вкладки «Внутренние / Внешние» в транзакциях, группировка фильтра
  проектов, переключатель внутреннего проекта.

**Первая настоящая ставка прошла 18.08 в 16:56** — у Лаки списалось 100.00,
остаток 900.00, в журнале строка с `balance_after`. Цепочка от launch у партнёра
до тиков в игре сработала целиком.

### Три поломки за день, все поучительные

**1. `cid` — сняли поле не с той стороны первым.** Убрал необязательное поле
`cid` из тела `/playerInfo` у крашей и из DTO у Лаки, но **закоммитил только
крашевую половину**. Краши перестали слать, Лаки продолжил требовать →
`400` → игрок не заводится → профиль 401 → движок не авторизуется → **коэффициент
не идёт**. Симптом был максимально далёк от причины.

> Правило: **сначала принимающая сторона перестаёт требовать поле и
> раскатывается, потом отправляющая перестаёт его слать.** Тогда любое
> промежуточное состояние рабочее. И `git status` перед тем, как считать
> задачу закрытой.

**2. Резолвер подключили не везде.** Профиль работал, а игра стояла: движок
авторизуется своим путём (`GET server/games/{id}/player`), и там оставался
прямой поиск по `players.token`. Тики рассылаются только клиентам с
выставленным `player.token` — отсюда живая ссылка, рабочий профиль и застывший
коэффициент.

**3. Локальная транзакция затёрла зеркало** — см. грабли в разделе про деньги.

### Диагностический приём, который сработал

Три независимых показания сходятся быстрее, чем чтение кода:

1. **код ответа** того звена, что ниже симптома (не игра, а эндпоинт движка);
2. **состояние данных** (`player_id NULL` в сессии → ломается привязка, а не авторизация);
3. **лог с текстом чужой ошибки** — в клиенте партнёра логируется тело ответа,
   и оно назвало поле `cid`.

По отдельности каждое допускало несколько объяснений, вместе — только одно.

### Прочее

- Apidog: в `CrashGames API` обновлён `/game/url` (**импорт не перезаписывает
  существующий метод** — надо удалять эндпоинт и заливать заново, id при этом
  меняется); в `Lucky Server` (1341455) залиты `playerInfo` / `bet` / `win`
  срезом из живой спеки `dev2.api.luckyserver.pro/docs-json`;
- `smoke.sh` исправлен: во втором пункте печатался **самый старый** коэффициент
  из 20 хранимых (`ratesHistory.unshift()` кладёт свежий в начало), поэтому на
  живой игре отчёт выглядел как «залипло». Теперь печатается `n[0]`;
- `game_providers.launch_url` у Лаки указывал на удалённый `/api/external/auth` —
  запуск игры не мог работать в принципе.

## Журнал: 2026-08-19 — доводка seamless и демо-9999 на прод

Два независимых пласта. Seamless — только на dev; демо-9999 — единственное, что
уехало на **прод** сегодня.

### Seamless: связка ставок и раундов

Закрыты пункты из плана прошлой сессии (см. чек-лист ниже):

- **`txId` = uuid строки журнала.** Отдельная колонка `tx_id` убрана — дублировала
  `uuid`. Ключ идемпотентности не изменился по смыслу.
- **`ext_id` = партнёрский `processedTxId`** из ответа — обратная ссылка на запись
  партнёра, кладём при первом успешном ответе.
- **Первичные ключи в теле** `/bet` и `/win`: `betId`, `roundId`, `gameId`,
  `betNumber` (раунд-скоупный, 1/2). Теперь строка у партнёра привязана к ставке
  и раунду — есть чем сверять спор.
- **url запроса** пишется в `attempts`, **тело запроса и `ext_id`** отдаются в
  ресурсе внешней транзакции (для админки).
- **Зеркало на ретраях.** `/win` при повторе обновляет зеркало из ответа так же,
  как на первой попытке (раньше ретрай деньги досылал, а зеркало не двигал).
  Компенсирующий `CancelBet` при неясном отказе `/bet` сделан устойчивым
  (переживает перезапуск воркера); ставка создаётся до похода к партнёру и
  удаляется при отказе.

У Лаки соответственно: тип `cancel` первого класса, снапшот провайдера/игры и
первичные ключи в `metadata` транзакции (детали — скил `lucky-infra`).

### Демо-игроки: 9999 сразу, выкачено на прод

Регистрация с `demo.` / `dev.demo.crash-heroes.com` должна давать 9999 сразу; на
деве показывался 0.

**Грабли (стоит помнить).** `AppController::getPlayer` создавал `Player` **без**
`client_type` → `PlayerObserver::created` шёл в ветку по умолчанию, начислял
бонус на неактивный `XTR`, а `switchActiveWallet` делал активным пустой
`GEM_DEMO` → игрок видел 0. Симптом (0 на балансе) далёк от причины (пропущенное
поле при создании). Починка: передавать `client_type` в `Player::create` +
`awardStart` для `GEM_DEMO` начисляет `9999 * 100`. Игроку 173 поправлено руками.

**Выкат.** По прямому указанию Ильи на **прод** ушли только два коммита
(`ccfb56e`, `ed82636`) cherry-pick'ом в `main` + `octane:reload`; проверено, что
mtime файла на проде свежее перезагрузки octane и что правка только на проде, не
на деве. Остальной seamless на прод не катился.

## Журнал: 2026-08-20 — переименование сессий (`crash_session` / `launch_token`)

По просьбе Ильи приведены к одному имени обе сессии в двух системах, чтобы в
обеих админках один и тот же токен назывался одинаково:

- **краши, БД:** `game_sessions.session_local` → `crash_session`,
  `session_external` → `launch_token` (миграция
  `2026_08_20_100001_rename_game_session_columns_to_crash_session_and_launch_token`,
  обычный `renameColumn`, данные не трогаются). Модель, `GameLaunchService`,
  `GameSessionResolver`, `PartnerPlayerInfoService`, `PartnerWalletService`,
  поиск и ресурс внешних транзакций в админке переведены на новые имена; ресурс
  отдаёт плоские `crash_session` / `launch_token` вместо объекта `session`.
  Коммит `3ce4798` (develop). Админка: строки «Crash session» / «Launch token» в
  деталях внешней транзакции, коммит `687f056` (dev).
- **Лаки:** `game_sessions.session` → `launch_token` (миграция `1721700066000`,
  она же переписывает ключ `metadata.session` → `metadata.launch_token` в
  существующих транзакциях), поиск транзакций ищет по `metadata->>'launch_token'`.
  Коммит `717f70d` (lucky-api dev, после ребейза на origin/dev); админка — строка «Launch token» в деталях
  транзакции, коммит `b0e7718` (lucky-admin dev).
- **Wire-контракт не трогали** (`sessionToken` в `/game/url` и `/playerInfo`,
  `session` в `/bet`/`/win`) — иначе пришлось бы катить обе стороны синхронно.
  Если решим переименовать и его — это отдельная согласованная выкатка.
- Запушено 20.08 в dev/develop всех четырёх репо; после деплоя нужен
  `php artisan migrate --force` + `octane:reload` на крашах, а у Лаки — проверить,
  что миграция `1721700066000` применилась при деплое.

## Журнал: релиз 2026-08-21 — seamless на прод

### Догон: внешние сессии на проде падали 401 — не было валюты USD
После включения seamless на проде игра по партнёрской сессии (Лаки) не
авторизовывалась: `GET /api/app/profile?token_id=sess_…` → 401, у
`game_sessions` `player_id/currency/last_seen_at = NULL`. Партнёр отдаёт игрока
с `currency: USD`, а в проде крашей в `currencies` **USD не было** (на деве
есть). `GameSessionResolver::attachPlayer` → `CurrencyService::byCode('USD')`
= null → `Log::warning('валюта USD не заведена')` и `return null` → игрок не
создаётся. Логи молчали, т.к. `storage/logs/laravel.log` на проде нет
(логирование в другое место) — диагностировал прогоном резолвера через
`php artisan tinker --execute`. Подписанный `/playerInfo` с прода к Лаки при
этом отдавал 200 (ключи/эндпоинт в порядке — интеграцию Илья настроил верно).
**Фикс (2026-08-21):** создал USD как на деве (`Dollars`, `$`, chips [1,3,5],
`rate_to_usd 1.0`) + `php artisan cache:clear` (каталог валют кэшируется
`file`-драйвером **forever** — `CurrencyService`, ключ в `CACHE_KEY`; без сброса
не подхватится). После — профиль сессий 200, игрок заводится, `player_id`
пишется. Вывод: **для любого партнёра его валюты должны существовать в
`currencies` на проде крашей**; если появится EUR и т.п. — добавить так же.


Мержи `develop`→`main` (бэк) и `dev`→`main` (админка), раскатка через CI на
прод 78.141.216.99. Движок: `main`==`develop`==`142f570` (исходники на проде
совпадают — деплой не требовался).

- **Бэк** (`2ca8fa4`): develop +48 / main +2 (демо-9999 cherry-pick'и 19.08,
  0 конфликтов). 12 seamless-миграций применились через CI (`migrate --force`
  + `octane:reload`). `projects`: `is_internal` — Inner=1, «Lucky server»=0,
  test=0; добавлены `api_player_info/api_bet/api_win`; удалены legacy
  `api_get_balance/api_post_balance`. **Прод-мина проверена заранее:** внешней
  активности на проде 0 (0 `player_external_transactions`, `game_sessions`
  не было) → живой поток не порван. Legacy-урлы проекта 2 забэкаплены:
  `~/deploy-backups/projects-pre-seamless-20260821-15013*.sql` на проде.
- **Админка** (`687f056`): dev +27, ff. Статика через CI.
- **smoke.sh на проде — зелёный** после деплоя: 13 игр живы, коэффициенты
  меняются, pm2 16/16, диск 26%.
- CI прод-переменные крашей рабочие (в отличие от Lucky, где прод
  `SSH_PRIVATE_KEY_BASE64` битый). `docs/external.yaml` отдаётся (200).
- Интеграцию Lucky↔краши (провайдер, ключи, sync-games) Илья делал сам;
  на проде Lucky провайдер «Crash Games» → `api.crash-heroes.com/api/external/game/url`.

## Журнал: 2026-09-09…11 — контракт партнёра v2 (user/info, rollback, подпись)

Три дня правок бэка и админки вслед за переделкой контракта на стороне Lucky
(там: «session field standardization», rollback, переименование player info).
Всё через `develop` → `main`, на прод уехало CI 11.09 (~13:44 UTC, миграции
применены на обоих серверах, `octane:reload` прошёл). CHANGELOG **не обновлён**.

- `5b57c73` — тело `/bet`/`/win` сведено к `txId, betId, roundId, betNumber,
  amount, session`; подпись `signRequest(method, path, body)`; отдельный
  `cancel()` и колонка `api_cancel`. `444d6c9` — user-info подписывается своим
  URL, `661c521` — валюта операции из сессии.
- `505f8fa`, `e5e6706` — ключи `api_key`/`api_secret` принимаются от партнёра,
  свои больше не генерируются (nullable). `756637b` — удаление проекта с
  сессиями. `48f68e3` — из user-info убран `timestamp`.
- `e0e8c3b` — `api_player_info` → `api_user_info`, `PartnerPlayerInfoService` →
  `PartnerUserInfoService`, `api_cancel` удалён. `d804f7a` — компенсация
  неподтверждённой ставки = `rollback` на `api_rollback`, тип `rollback` в
  журнале. `94863bd`/`569a989` — ретраи в очередь `integration`, бесконечно.
  `6a8e205` — rollback своей строкой + `PartnerRollbackTest`; **сюда же случайно
  попал `storage/logs/laravel.log`** (тестовый лог, теперь tracked).
- Админка: `540d2d6`, `07d9fe4` (поля ключей партнёра сверху, генерация убрана),
  `aa2d881`, `cec6d3d` (URL user-info, поле rollback), релиз `5e3720e`.
- На проде после релиза: 2 проекта внешних (`Lucky server` id 2 — все четыре URL
  и ключи заполнены; `test` id 3 — только ключ), 60 сессий, 83 партнёрские
  операции (60 bet / 23 win, все `completed`), последняя 10.09. На dev — 173
  операции, в т.ч. 10 `cancel` (август) и 1 `rollback` (11.09 12:23, прошёл).
- Незакоммиченный хвост в `api-core`: `GameUrlRequest` + `GameLaunchService`
  переводят входящий `/game/url` с `sessionToken` на `session` (старое имя
  принимается через `prepareForValidation`). Спека `docs/openapi-external.yaml`
  под это **не правлена** — по правилу выше её нужно менять тем же коммитом.

## Журнал: 2026-09-14 — ревизия репозиториев и серверов

Сессия без правок кода: изучены все четыре репо (см. «Карта репозиториев»),
прогнан `smoke.sh` и снят статус обоих серверов. **Оба зелёные**: 13 игр живы,
коэффициенты меняются, pm2 16/16, очереди пустые, `failed_jobs` 0, висящих
SQL нет, nginx без 5xx/408, сертификаты до 29.11.2026, fail2ban активен.
Код на серверах совпадает с локальным `main` по md5 (`routes/api/api.php`,
`ServerGameController`, `composer.lock`, `main.mjs`, `server_calculator.py`).

| | prod | dev |
|---|---|---|
| uptime | 58 дней | 74 дня |
| диск | 28 % (40 / 150 ГБ) | 21 % |
| `game_crash_rounds` | 14.3 млн, 7.26 ГБ (16.08 было 12.5) | 7.2 млн |
| `account_transactions` | 29.0 млн, 4.13 ГБ | 13.0 млн |
| раундов / ставок за сутки | 77 218 / 80 | 77 277 / 0 |
| игроков | 3 969 | 191 |
| `innodb_buffer_pool_size` | 128 МБ (не поднят) | 128 МБ |
| Octane | 4 воркера :8001, `APP_DEBUG=false` | 12 + 6 task :8002, `APP_DEBUG=true` |
| `LOG_LEVEL` | debug | debug |
| `storage/logs` | 256 МБ | 327 МБ |
| ядро | 6.12.95, доступно 6.12.107 | 6.12.88, доступно 6.12.107 |
| `pm2-admin.service` | active, pid совпадает | **inactive**, демон мимо systemd (TODO) |

Что выяснилось нового:
- **Запуск игр из Lucky сломан на обоих серверах с 11.09.** Lucky в тот день
  перешёл в `/game/url` на поле `session` (`01e10bb`, master и dev), а краши
  требовали `sessionToken` → `400 Invalid request` (проверено подписанным
  запросом на dev; на проде запусков после 10.09 просто не было, поэтому в
  логах пусто). Фикс `25d9a68` («Accept the partner session field on game url
  and keep sessionToken as a fallback») закоммичен в `develop`, ff в `main`,
  спека `docs/openapi-external.yaml` в том же коммите (`session` обязательное,
  `sessionToken` deprecated). **Запушено и раскатано CI 14.09** на dev и прод:
  проверено подписанным запросом — оба хоста отдают 200 и на `session`, и на
  старом `sessionToken`, `smoke.sh` зелёный. Осталось: перезалить спеку в
  Apidog (проект 1347186).
- **Регресс Lucky↔краши на dev — зелёный (14.09).** Денежная проба
  `game-provider-regress.mjs` **29/29** (user/info, bet, идемпотентность, win,
  отмена через `win+cancel`, rollback ставки/отмены/выигрыша, подпись, битые
  тела, гонки), каталог и модерация `provider-catalog-regress.mjs` **16/16**
  (провайдерская половина, рут-токен в vault недоступен). Прогонялись **на
  crash-dev** (ключ провайдера не выносится с сервера — классификатор режет
  materialization приватного ключа) против `dev2.api.luckyserver.pro`. Как
  готовить вход — `lucky-back/REGRESS.md`.
- **Оба сервера просят перезагрузку** (`/var/run/reboot-required`, по 5–7
  ядер в очереди, 20–23 пакета к обновлению). Перезагрузка = минута простоя
  игр; на dev заодно вернёт pm2 под systemd. Делать по согласованию.
- В `laravel-*.log` по 300–350 `ERROR` в сутки — это **сканеры ботов** (404 на
  `sitemap.xml`, `bitrix/`, `.env`; nginx их режет `access forbidden by rule`)
  плюс `Player not found` из `ServerGameController:29` — движок дёргает
  `GET server/games/{id}/player` на каждого подключённого клиента при создании
  раунда, в том числе на анонимного; `smoke.sh` сам оставляет 2 такие строки.
  Всплеск 108 штук 10.09 и 66 на dev 09.09 — тесты интеграции (`Undefined
  variable $url` в `playerInfo` — починено `444d6c9`). Реальных ошибок нет.
- Канал `round` пишет ~39 МБ/сутки на каждом сервере (тайминги
  `finishGameCrashRound` + полный ответ на каждый раунд) при `LOG_LEVEL=debug`.
  С `daily` (14 дней) это ~550 МБ, не критично, но шум.
- Reverb сконфигурирован в nginx (`/reverb` → 8080 / 8888), но **не запущен
  ни на одном сервере** и в коде не используется (`Events/Round/*` не
  диспатчатся). **Решение Ильи 14.09: Reverb неактуален, удалить** — чек-лист
  в TODO.
- `schedule:run` в cron нет ни на одном сервере → `arcade:resources:refill`
  (сердца в хоккеях) **не выполняется** с момента переезда с supervisor
  (`supervisor_scheduler.log` на dev кончился 02.07).
- Нумерация `sequence_id` здорова: на проде у всех 13 игр `count == max`, на dev
  у игр 11 и 15 `max = count − 1` (следы гонок, не растёт).
- `/home/admin/crashgames/games/` на проде обновлялись 04.09 (все краши),
  `olimphockey` — 25.05, слоты — 24.07; на dev есть тестовая `fake/` (31.08).
  Сборки игр в репозиториях не живут.
- Прод: `~/resync.sh` с паролями открытым текстом; `minigames-admin-front.old`
  от 17.08 можно удалить.

## Журнал: 2026-09-18 — сверка репо, старт нового движка

Сессия без правок кода. `git fetch` по всем четырём репо, сверка md5 с
серверами, правка скила.

- **`bet_error` закоммичен и запушен ещё 14.09** (бэк `d47d514`, движок
  `b5b1a6b`, оба в `develop`) — скил ошибочно держал его «в рабочем дереве».
  На dev раскатан (md5 совпали), **на проде нет**; порядок релиза — в TODO.
- **`catalog-app` не заморожен:** в `origin/main` два коммита Титова от 02.09,
  которых 14.09 не было видно (не делали `fetch`). Локальный `main` разошёлся:
  1 свой незапушенный / 2 чужих.

  > Вывод: ревизию репозитория начинать с `git fetch`. Вывод «заморожен» был
  > сделан по локальной копии `origin/*` трёхмесячной давности.
- Клона `work-skills` на машине по-прежнему нет — копия скила не синхронизирована.
- Чтение `/etc/nginx/conf.d/` на dev по ssh **заблокировал классификатор**
  auto-режима («Production Reads»), хотя md5-сверка файлов на обоих серверах
  прошла. Если nginx-конфиги понадобятся — Илья запускает команду сам через
  `! ssh …` или добавляет правило в permissions.
- **Илья завёл новый проект — движок под новую игру**, репо
  `game-engine-rng`. В тот же день написано стартовое ядро (Node 24 +
  TypeScript без сборки, `ws`, Docker, слои `domain/services/web/resources`).
  По просьбе Ильи описание вынесено **в отдельный скил `game-engine-rng`**;
  точки стыковки и «чего не повторять» переехали туда же.
- **`games.uuid` в api-core — в работе, НЕ закоммичено** (рабочее дерево
  `develop`, 18.09). Новый движок `game-engine-rng` указывает свою игру по
  `games.uuid`, а не по `id` (решение Ильи). Что лежит:
  - миграция `2026_09_18_100001_add_uuid_to_games_table`: колонка `uuid` nullable
    после `id` → заполнение существующих строк `Str::orderedUuid()` → `NOT NULL`
    + уникальный индекс `games_uuid_unique`; `down` снимает индекс и колонку;
  - `Game`: `use HasUuids` + `uniqueIds(): ['uuid']` (первичный ключ остаётся
    числовым `id`), `@property string $uuid`, `whereUuid`;
  - `DefaultGameTypesSeeder`: третий тип `Crash RNG` / `crash-rng`;
  - новый `DefaultGamesRngSeeder` (подключён в `DatabaseSeeder`): игра «Test RNG»,
    `sys_name` `test_rng`, `link` пустой, `settings` пустые. Uuid сидер **не
    фиксирует** — на каждой базе свой;
  - заодно снова изменён tracked `storage/logs/laravel.log` (грабли №5 карты).
  Движок заведён на uuid `a2c68a94-4ea3-4086-9364-b1bb7dde9548`.
  **Учесть до выката:** админка выбирает форму настроек по `typeId === '1'`,
  иначе `SlotsForm` — у типа `crash-rng` (id 3) будет форма слотов; а
  `settings` у игры пустые, тогда как `Game::checkSettingsValid()` требует
  `settings.mode`.
- **Закоммичено и запушено в dev (18.09, по команде Ильи):** api-core `dbeb932`
  «Add RNG games with a uuid, an engine URL and an admin health check» в
  `develop` (uuid + `engine_url` у `games`, тип `crash-rng`, сидер `test_rng`,
  `RngEngineHealthService`, маршруты `GET /v2/admin/rng/games`, `PATCH …/{uuid}`,
  `GET …/{uuid}/health`, только superadmin); admin-panel `c51f81b` «Add the RNG
  games section with the engine URL and its health status» в `dev` (раздел
  «RNG-игры» `/rng/games`, виден при выбранном типе `crash-rng`). Работу писали
  параллельные сессии; перед коммитом — `php -l` + `route:list` в контейнере,
  у админки `tsc -b` + `eslint` + `prettier` + `build:dev`; поймана и убрана одна
  ошибка (неиспользуемый импорт `FormDescription`). **Не закоммичены намеренно:**
  `storage/logs/laravel.log` и `.env.local` админки (`localhost:8000`).
  **CI раскатил на dev в 13:37**: миграции `2026_09_18_*` — batch 20, маршрут
  отвечает 401 без токена, статика админки обновлена. `main` не трогали.
- **Грабля: `DefaultGameTypesSeeder` НЕ запускать на dev/проде.** Он для
  каждого типа делает `firstOrCreate` **и `resetSettings()`** — у `crash-games`
  это перезапишет `algorithm` (expectation −0.04, просадки 20/40, кф 1.2/8) и
  `demo_mode`. CI сидеры не гоняет, поэтому на dev **типа `crash-rng` и игры
  `test_rng` нет**. Заводить точечно: тип — `GameType::firstOrCreate(['sys_name'
  => 'crash-rng'], ['name' => 'Crash RNG', 'settings' => []])` в tinker, затем
  `php artisan db:seed --class=DefaultGamesRngSeeder --force` (он
  `updateOrCreate` по `sys_name`). **На dev сделано 18.09 (Илья, по инструкции):**
  тип `crash-rng` и игра `test_rng` есть, uuid игры на dev —
  `a2c69d5c-074d-4574-9262-58fce37fba72`.
- **На dev-сервере есть Docker** (26.1.5 Debian, Compose 2.26.1) — строки выше
  «серверы без Docker» для dev неверны; `admin` не в группе `docker`. Движок
  `game-engine-rng` там **развёрнут 18.09**: образ `arcanegaming/crash-engine-rng:0.1.0`
  из Docker Hub, контейнер `crash-engine-rng-1` на `127.0.0.1:3100`, `admin` теперь
  в группе `docker`. Runbook деплоя — скил `game-engine-rng`, раздел «Деплой».
- **Архитектура «Хоккеиста» — WS как у крашей, путь = `games.uuid`** (итог 18.09):
  клиент → `wss://dev.server.crash-heroes.com/<uuid>` → движок `127.0.0.1:3100`;
  в `dev.server.crashgames.app.conf` добавлен `location /a2c69d5c-…` (бэкап
  `~/deploy-backups/dev.server.crashgames.app.conf.20260918-140808`). Промежуточные
  варианты в тот же день откачены: поддомен `dev.rng` (nginx удалён), «через API,
  как слоты».

### API под новую игру (`crash-rng`), 18.09 — закоммичено (`dbeb932`, `17c7f17`, `55b3018`), на dev

Всё только для типа `crash-rng`, старые игры не тронуты.
- Тип `crash-rng` в `DefaultGameTypesSeeder` (`GameType::CRASH_RNG`), настройки
  пустые → в админке у типа нет страниц. Сидер `DefaultGamesRngSeeder` — одна
  «Test RNG» (`test_rng`, `link ""`, `settings []`), в партнёрский `getGames`
  не попадает (`checkSettingsValid` = false).
- `games.uuid` (после `id`, unique, `HasUuids` с `uniqueIds() = ['uuid']` —
  `id` остаётся ключом) — его получает движок. `games.engine_url` (nullable).
- Админка, только суперадмин: `GET /api/v2/admin/rng/games` — список rng-игр;
  `GET /api/v2/admin/rng/games/{uuid}/health` → `{uuid, alive, reason,
  http_status, latency_ms, uptime, checked_at}`, `reason`: `not_configured` /
  `unreachable` / `http_error` / `bad_response` (`game_uuid_mismatch` был убран
  21.09 вместе со сверкой uuid — `b523841`; в админке остался мёртвый ярлык
  `RngGameHealthCell.tsx`). Живой = `200` + `{status:'ok', uptime:<int>}`.
  Не rng или нет такого uuid → 404 «Game not found.». Контракт `/health` — в
  скиле `game-engine-rng`, пункт 9 точек стыковки.
  `PATCH /api/v2/admin/rng/games/{uuid}` — частичный `{name, sys_name,
  engine_url}` (`sys_name` `[a-z0-9_]`, unique; `engine_url` http(s) или null;
  422 — `{data:null, error}` с русскими именами полей). Выборка rng-игр —
  scope `Game::crashRng()`. Раздел в админке делает сессия `admin-panel`.
- `RngEngineHealthService` ходит в движок из процесса API: на серверах
  `engine_url` — `http://127.0.0.1:<порт>`; локально API в docker, и
  `127.0.0.1` там — сам контейнер.
- **Решение Ильи 18.09: rng-игры пишут в таблицы крашей** (`game_crash_rounds`,
  `game_crash_bets`, транзакции) — `GameType::getRelations()` для `crash-rng`
  отдаёт то же, что для `crash-games`. Проекты и валюты в rng-меню — общие.
  Отбор «только rng» включается `typeId` = id `crash-rng`
  (`GameType::isCrashRng()`), для других типов код прежний: `v2/admin/rounds`
  и `admin/games/{g}/rounds` (раньше только `typeId 1`), `v2/admin/players`
  (inner join на ставки rng-игр), `v2/admin/players/{id}` (раньше всегда тип 1),
  `…/{id}/bets`, `admin/wallets/transactions` (по `meta.bet_id` и кошельку
  игры) и `…/external` (по `game_session_id` → `game_sessions.game_id`).
  **Грабля на будущее:** старое меню (тип 1) эти таблицы по типу не фильтрует
  в игроках, карточке, ставках игрока и транзакциях — как только появятся
  rng-ставки, они попадут и туда. Раунды и агрегат фильтруют по
  `games.type_id`, там чисто. Чинить — отдельной правкой старых путей.

## Журнал: 2026-09-18 (вечер) — раунды «Хоккеиста» и выкатка на dev

Сессия `crashgames-98`, по командам Ильи. Подробно про движок — скил `game-engine-rng`,
раздел «Раунд и шаги».

- **api-core `55b3018`** «Hand out RNG game sessions on game url and add the RNG round
  tables» (`develop`, запушен, CI выкатил на dev ~17:44 UTC): для `crash-rng` без ссылки
  `/external/game/url` отдаёт `{session: <uuid>}` (без `sess_`), `game_id` = id | uuid |
  sys_name; миграция `2026_09_18_100003_create_game_rng_rounds_table` — `game_rng_rounds`
  (раунд игрока: ставка → выкуп/проигрыш) и `game_rng_steps` (броски: кости, `roll_id`,
  событие dicestream). Применена на dev (проход 21).
- **Движок 0.1.1 на dev**: раунды, кости из dicestream (`ws://127.0.0.1:18080`), событие
  `result` через 3–4 с, сеть хоста, `DB_*` — юзер api-core. `smoke.sh` dev после выкатки —
  зелёный (13 игр, pm2 16/16).
- **Расхождение, не решено:** выше записано «решение Ильи 18.09: rng-игры пишут в таблицы
  крашей» (`game_crash_rounds`/`game_crash_bets`, под это сделана админка `17c7f17`), а
  движок пишет в **отдельные** `game_rng_rounds`/`game_rng_steps` (сессия `crashgames-98` о
  решении не знала). Итог: раунды «Хоккеиста» в админке RNG **не видны**. Нужно выбрать:
  админку читать из `game_rng_*` или движок писать в таблицы крашей (там раунд общий и
  один коэффициент — модель «раунд → шаги» ложится плохо). Транзакции оператора
  (`player_external_transactions`) видны в «Внешних» как раньше.
- Apidog: проект 1381870, модуль «Game engine RNG» — окружения Local/Develop, «Create game
  session» (прескрипт подписи), сокет «Game socket v1» с протоколом раунда (скил `apidog`).

## Журнал: 2026-09-24 — `win` с 0 на проигрыш (Lucky берёт комиссию с проигрыша)

Lucky перешёл на комиссию провайдера **только с проигрыша**, считает её в момент `win`. Правило контракта (как у
Aviatrix): **каждая ставка закрывается ровно одним `win`, проигрыш — `win` с `amount` `"0"`**. До этого краши на
проигрыш не слали ничего.

- **api-core** `f3aaacf` + `eb2184c` (в `develop` и `main`, выкачены CI на dev и прод 24.09):
  `SeamlessWalletGateway::settleLosses($round)` вызывается в `finish_round` (в `try/catch`, логирует в канал
  `round`). Находит в `player_external_transactions` партнёрские `bet` этого раунда (`round_uuid` = `round.id`) со
  статусом `completed`, по которым нет `win`/`cancel`; если локальная ставка (`game_crash_bets`, id = `bet_id`)
  есть и `win == 0` — пишет строку `win` с `amount 0` через `PartnerWalletService::loss()` (новый `record()` без
  отправки) и кладёт в очередь `PartnerOperationRetryJob`. `amount` в теле **строкой `'0'`** — числом Lucky
  отвечал 400 (`eb2184c`). Удалённые (`remove_bets`) и выкупленные «всё сразу» (`store_takes`) ставки пропускает.
- Проверка в tinker на локальной базе (в транзакции с откатом, `Queue::fake`): проигранная ставка получила
  `win` 0, выигранная и ставка с `win` в ретраях — нет, повторный проход не дублирует.
- **Известные дыры, не чинили:** `remove_bets` (отменить все) и `store_takes` (забрать все) **вообще не ходят к
  партнёру** — деньги у игрока остаются списаны / выигрыш не зачисляется. Плюс `all_bets` в движке задевает
  ставки всех игроков раунда.
- **RNG-движок** `game-engine-rng` 0.1.12 (dev, 24.09): `win` с 0 при проигрышном броске и при автозакрытии
  брошенной игры без выигранных бросков (`GameService.settleLoss`). См. скил `game-engine-rng`.
- `/api/external/game/url` крашей **требует `session`** → демо-запуск Lucky (`is_demo: true`, без `session`)
  получит 422. Лишние поля (`is_demo`, `player_id`, `currency`, `lang`) в обычном запуске пропускаются. Демо у
  крашей — отдельная задача: при `is_demo` не требовать `session`, отдавать ссылку на игру в демо (`GEM_DEMO`).
- **smoke 24.09:** прод и дев зелёные. Утром на проде падал пункт вебсокетов: сервер резолвил
  `server.crash-heroes.com` в `200.58.119.215` (`getent hosts`), к вечеру само прошло — кэш резолвера.
- На деве вручную (по «разрешаю») переотправлены отклонённые `win` 0 по ставкам 692/693 (строки журнала 315/316):
  выставлен `request.amount = "0"`, статус `awaited`, `PartnerOperationRetryJob::dispatch`.

## TODO

### Планы по seamless (следующая сессия)

- [x] **`operation` в `/win` — отмена пишется у Лаки как выигрыш.** Сделано 19.08:
      у Лаки заведён тип транзакции `cancel` первого класса, возврат больше не
      выглядит выплатой в отчётности.
- [x] **`betId` и `roundId` принимаются и выбрасываются.** Сделано 19.08: `betId`,
      `roundId`, `gameId`, `betNumber` уходят в теле и складываются в `metadata`
      транзакции у Лаки; строка привязана к ставке и раунду.
- [ ] **Не решено, убирать ли:** `timestamp` в `/playerInfo` (0 использований,
      как был `cid`), ветка `data`-обёртки в разборе ответа партнёра (Лаки
      отвечает плоским объектом), приём `sys_name` в `game_id` (обе стороны
      переехали на числовой id).
- [x] **Админка, вкладка «Внешние».** Сделано 19.08: scope «Раунд» для
      bet/win/cancel, колонка External id, `txId`=uuid, попап «Детали» с
      аккордеоном попыток (сортировка свежие-первыми, успешная развёрнута) и
      табами Запрос/Ответ, url запроса в шапке попытки. Осталось: фильтр «только
      неуспешные» (`onlyFailed` на бэке уже есть) — без него застрявшее в ретраях
      не найти.
- [~] **Продление сессии пингом.** Наша краш-сессия скользит по обращениям
      фронта (`GameSessionResolver`, троттл 60 с, окно 25 мин). Партнёрская
      сессия (Лаки, 30 мин от launch) раньше не продлевалась вообще; **19.08**
      сделано: **успешный `bet`/`win` продлевает Lucky-сессию** — вебхук расчёта
      двигает `expires_at` = now + `GAME_SESSION_TTL_MINUTES` (30) у живой сессии
      клиента по этой игре (`crash-games-webhook.service.ts::extendSession`).
      Важно: сам расчёт по сроку сессии **не гейтится** (гейт по `expires_at`
      только в `playerInfo`), так что протухшая сессия ставку не ломает — это про
      консистентность записи. **Остаётся дыра:** кто смотрит и не ставит, вебхуков
      не шлёт → Lucky-сессия не продлевается → протухнет у партнёра. Полный фикс —
      периодический `/playerInfo` как heartbeat (только он видит присутствие без
      ставок).
- [ ] **Absolute-потолок сессии 12 часов** — обсуждался, не сделан.
- [ ] **Что делать с проектом 5.** Провайдер у Лаки сейчас на его ключах, но
      проект 2 «Lucky server» тоже жив и на нём висят старые данные. Нужно
      выбрать один и убрать второй, иначе снова разъедется.
- [x] **Прод.** Seamless выкачен 21.08, контракт v2 — 11.09 (см. журналы).
- [ ] **Прод-джоба CI движка** написана (`.gitlab-ci.yml`, ветка `main`,
      автомат по пушу), но **ни разу не запускалась** — `origin/main` движка
      стоит на `142f570` с 18.08. Первым её запустит релиз `b5b1a6b`
      (`bet_error`, с 14.09 ждёт в `develop`). Первый прогон — под присмотром:
      раскатка на прод перезапустит 13 игр по одной.
- [x] **`25d9a68` запушен и раскатан** (14.09, dev+прод): запуск из Lucky
      работает, `smoke.sh` зелёный. Осталось: `apidog import` спеки в проект
      1347186; позже, когда Lucky точно не шлёт `sessionToken`, убрать запасное
      имя из `GameUrlRequest` и спеки.
- [ ] **Удалить отозванную пробу каталога** `35e1ff2a-277d-4ae6-8956-91ff48bc06d5`
      на Lucky dev рутом (осталась от регресса 14.09, у `revoked` нет выхода без
      рут-токена).
- [ ] **`CHANGELOG.md` бэкенда** — дописать 21.08–11.09 (ключи партнёра,
      user/info, rollback, ретраи).
- [ ] **Убрать `storage/logs/laravel.log` из гита** (`git rm --cached` +
      `storage/logs/.gitignore` с `*` / `!.gitignore`).
- [ ] **Перезагрузить оба сервера** (ядро, `reboot-required`), заодно проверить,
      что pm2 на dev поднимется под `pm2-admin.service`. Простой игр ~1 мин.
- [ ] **`schedule:run` в cron** на обоих серверах (`* * * * * php artisan
      schedule:run`) — иначе `arcade:resources:refill` не работает.
- [ ] **Удалить `~/resync.sh` на проде** (пароли открытым текстом, разовая
      переливка со старого хоста давно сделана) и `minigames-admin-front.old`.
- [ ] **`sign-external.sh` на dev** — добавить режим `signRequest` (метод + путь),
      чтобы проверять ключи в сторону Lucky.
- [ ] **Удалить Reverb целиком** (решение 14.09, он неактуален). Что снести:
      - репо: `laravel/reverb` из `composer.json` (+ `composer update`),
        `config/reverb.php`, `App\Providers\BroadcastServiceProvider` из
        `config/app.php`, `app/Events/Round/{RoundCreated,RoundUpdated,RoundFinished}.php`
        (не диспатчатся), `app/Concerns/InteractsWithBroadcastChannels.php`,
        случайный автоимпорт `use Laravel\Reverb\Loggers\Log` в
        `App/Banners/BannersController.php` и `BannerRepository.php` (без него
        пакет не удалить — классы перестанут грузиться; заменить на
        `Illuminate\Support\Facades\Log` или убрать),
        `REVERB_*` из `.env.example`; `BROADCAST_DRIVER=log` оставить;
      - серверы (оба): `location /reverb` в
        `/etc/nginx/conf.d/api.crash-heroes.com.conf` и
        `dev.api.crashgames.app.conf` + `nginx -t && reload`; в `.env`
        `BROADCAST_DRIVER=reverb` → `log` и восемь `REVERB_*`, затем
        `config:clear` + `octane:reload`; `storage/logs/supervisor_reverb_worker.log`
        (4 МБ, последняя запись 01.07).
      Порядок: сначала серверные `.env` и nginx (ничего не сломается — сервис и
      так не работает), потом код через `develop` → `main`.
- [ ] **Сломанный `POST /api/app/wallet/withdraw`** (класс
      `ExternalTransactionService` не существует) и `dd()` в
      `Player::switchBlock()` — проверить, нужны ли эти пути каталогу/мобилке.
- [ ] **`README.md` бэкенда** переписать или свести к ссылке на спеку — описывает
      удалённую схему.
- [ ] **`catalog-app`**: `console.log(url)` в демо-таргете закоммичен 14.09 по
      просьбе Ильи (`98f5ea0`, не запушен) — при следующем касании убрать;
      решить, нужен ли отдельный `.env` для demo-таргета, вынести keystore из гита.
      18.09: локальный `main` разошёлся с `origin/main` (1 свой / 2 чужих от
      02.09) — сначала `pull --rebase`.
- [ ] **`admin-panel`**: удалить влитые ветки `feature/fix-layout`,
      `feature/update-tables`, `fix/various-fixes`; решить судьбу
      `sandbox/dev-admin2-redesign` и `feature/icon-click-pointer-changes`.


- [~] **У движка нет канала для отказа — ставка подтверждается до похода на бэк.**
      **Сделано 14.09, закоммичено и запушено в `develop` обоих репо**
      (бэк `d47d514` «Return the partner bet verdict to the engine on
      store_bet», движок `b5b1a6b` «Tell the player over the socket when the
      partner did not confirm a bet»). **На dev раскатано CI** — 18.09 md5
      `main.mjs` и `SeamlessWalletGateway.php` на crash-dev совпали с
      `develop`. **На проде нет**: там md5 другие, `main` обоих репо позади на
      этот один коммит. Релиз = мерж `develop` → `main` в обоих репо; бэк
      катить **первым** (старый движок ответ `store_bet` просто игнорирует,
      поэтому промежуточное состояние рабочее), движок вторым — это и будет
      первый запуск его прод-джобы. Что сделано:
      `SeamlessWalletGateway::bet` теперь возвращает статус
      `accepted` / `declined` / `not_confirmed` вместо `bool`; `store_bet`
      отдаёт его движку в ответе (`data.bet.status`); `RoundService.handleBet`
      возвращает ответ, а слушатель `on('bet')` в `main.mjs` при
      `not_confirmed` шлёт **тому же сокету** сообщение
      `{type:'bet_error', bet_id, round_uuid, reason:'not_confirmed', message}`
      и обёрнут в `try/catch` (раньше непойманный reject убивал процесс).
      Решения Ильи по объёму: фантомную ставку в `bets.list` **не чистим**
      (что делать — решает фронт), сообщение шлём **только** на
      `not_confirmed` (на `declined` молчим), гейт по версии протокола **не
      делаем** — `GameVersionService` процессный синглтон и протёк бы между
      игроками. Тесты: `PartnerRollbackTest` 6/6.
      Осталось от исходного пункта:

      **Исходная проблема:** 
      `Round.makeBet()` кладёт ставку в список и эмитит событие, `BetMessageHandler`
      тут же отвечает клиенту `{type:'bet', success:true}` и списывает зеркало
      баланса — всё это **до** того, как бэк вообще спросят. Ответ бэка движок не
      читает: `RoundService.handleBet()` игнорирует результат, а `POST /api/server/round`
      всегда отдаёт 200 (все ветки отказа — голый `break`).
      **Следствие для seamless:** отказ партнёра (нет средств, нет живой сессии)
      выглядит в игре как принятая ставка. Игрок видит списание, в БД ставки нет,
      баланс отскакивает на следующем раунде. Проверено 2026-08-18: из двух ставок
      в раунде вторая была отклонена и **не оставила следа вообще**.
      Плюс если бэк начнёт отвечать честным 4xx — `handleBet` без `try/catch`,
      слушатель `eventEmitter.on('bet')` тоже, непойманный реджект на Node 23
      убивает процесс, и **раунд рвётся у всех в этой игре**.
      Лечится версией протокола в движке (`API_VERSION=2`): читать ответ, откатывать
      локальную ставку, слать `{type:'bet', success:false}`, обернуть денежные
      обработчики в `try/catch`. Отдельно нужен способ показать «перезапустите игру» —
      существующие сборки понимают только `success:false`.

- [ ] **pm2-admin.service на dev рассинхронизирован.** Юнит `enabled`, но `inactive (dead)`
      и журнал пуст: демон PM2 поднят руками 2 июля и работает 46 суток мимо systemd.
      Игры при этом живы (16/16), `dump.pm2` на месте, так что после ребута всё
      восстановится. Опасность в другом: `systemctl stop/restart pm2-admin` на dev
      сейчас не управляет реальными процессами. Чинится перезапуском демона под
      юнитом — это минута простоя игр на dev, делать по согласованию.
- [ ] **Сортировки админки.** Живы только `started_at` и `players`. Виснут по 30 с:
      `created_at`, `duration`, `coefficient`, `prizes`, `profit` — уходят в старый план
      `Using temporary; Using filesort` с перебором ~1 млн строк на игру. Клик по такому
      заголовку душит базу (один раз уже уронил игры). Нужны индексы с тем же
      префиксом `players`.
- [ ] **`sequence_id` через `COUNT(*)`** (грабли №2). Согласованное решение:
      `MAX(sequence_id)+1` + индекс `(game_id, sequence_id)`. Снимет постоянную нагрузку
      и разблокирует чистку прода. Отдельно есть гонка при одновременном создании
      раундов — на dev она дала 291 дубль до всякой чистки.
- [ ] **`aggregate` с фильтром дат — 2.4 с.** Единственный оставшийся путь, где
      сохраняется джойн к `game_crash_rounds` (фильтр по `started_at`). Пока терпимо,
      но будет расти вместе с таблицей. Лечится поднятием buffer pool; менять фильтр
      на `game_crash_bets.created_at` нельзя — это другая семантика (время ставки,
      а не начала раунда).
- [ ] **`innodb_buffer_pool_size` 128 МБ → 3 ГБ.** Меняется онлайн через
      `SET PERSIST`, рестарт MySQL не нужен. Обсуждалось также `--workers` Octane 4 → 8
      (правка systemd-юнита + рестарт, ~5 с простоя).
- [ ] **LOG_LEVEL=debug на проде** - понизить до `info`. Учитывая, что 15.08 диск
      забился логами под ноль, подробный уровень в бою лишний.
- [ ] **Накатить на dev** миграцию с индексом и новый `AdminRoundsController` —
      сейчас они только на проде, среды разошлись.
- [ ] **Сжатие в pm2-logrotate.** Обходим скриптом по cron. Стоит проверить более
      свежую версию модуля или заменить его на системный logrotate с `copytruncate`.
- [ ] **Чистка БД прода** (8.28 млн раундов + 16.44 млн `account_transactions` старше
      2 месяцев). **Заблокировано** до фикса `sequence_id`, иначе повторится история dev.
      Проверено 2026-08-16: нумерация на проде сейчас **здорова** — у всех 13 игр
      `count == max`, плотно `1..N`, ни дублей, ни дыр. Ломать её чисткой не надо.
      Если чистить всё же раньше фикса генератора — сразу после удаления прогнать
      `~/renumber_sequence.sh` с остановленными игровыми процессами.
- [ ] **Уровень логирования движков.** `logger.class.mjs` не фильтрует по уровню;
      `Round tick` на `DEBUG` каждые 50 мс. Ротация проблему прячет, но не решает.
- [ ] `game_crash_bets` на проде — всего 31.6 тыс строк при 12.5 млн раундов.
      Проверить, ожидаемо ли это (похоже, да: играют мало), или ставки теряются.

## Журнал: 2026-10-05 — RNG «Crash Hockey» к игре на проде

- Прод крашей: движок RNG 0.1.12 уже стоял (с 28.09), настоящий фронт «Crash Hockey» перенесён с дева с заменой
  хоста (детали — скил `game-engine-rng`, журнал 05.10). Игра id 19 `crash_hockey`, проект 2 «Lucky server» с
  прод-URL Lucky.
- **Админка**: `origin/main` уже содержит весь `dev` (последний мерж 28.09) — релиза не требовалось.
- **api-core**: `develop` впереди `main` только на Donkey Rush (коммиты kvaggone 26–27.09: тип `donkey-rush`,
  миграция `2026_09_26_120000_register_donkey_rush_game` создаёт игру с `link ''` и `settings.mode classic`,
  `/api/external/lucky/*`, `game_sessions.is_demo`). **На прод не катили намеренно**: движка Donkey Rush на
  проде нет, а игра с `mode classic` попала бы в `/api/external/games` и синк Lucky prod подтянул бы
  неработающую игру. Релизить вместе с движком Donkey Rush, по решению Ильи.
- В рабочем дереве api-core чужая незакоммиченная работа: `GameRngBet`, миграция
  `2026_09_28_100001_create_game_rng_bets_and_add_state_to_rng_games` — движок 0.1.12 её не использует, не трогали.

## Журнал: 2026-10-05 (вечер) — Donkey Rush на проде

- **api-core**: `develop` → `main` мержем через отдельный worktree (`bccd034`, только 7 коммитов Donkey Rush), CI
  выкатил на прод ~14:34 UTC: миграции `2026_09_26_120000_register_donkey_rush_game` и
  `2026_09_26_130000_add_demo_to_game_sessions` — batch 10. Чужое незакоммиченное в рабочем дереве api-core
  (`GameRngBet`, миграция `2026_09_28_100001_…`) не тронуто.
- **Движок**: репо `crash-heroes/backend/donkey-rush`, код в ветке `mcdx/donkey-rush-engine` (`6633d6d`; в `main`
  репо только Initial commit). На прод скопирован `git archive` в `/home/admin/crashgames/donkey-rush`, собран и
  поднят `SHARED_ENV_FILE=/home/admin/crashgames/crash-engine-rng/.env DONKEY_RUSH_IMAGE=donkey-rush:prod-6633d6d
  docker compose -f docker-compose.server.yml up -d --build` → контейнер `donkey-rush-1`, `127.0.0.1:3200`, кости
  из прод-сервиса `wss://dicestream.crash-heroes.com` (из общего env RNG-движка).
- **nginx** `server.crash-heroes.com.conf`: `location /ce60c59a-bfd9-4213-bd43-356c7afaf3b3` → `:3200` с rewrite и
  `Content-Security-Policy: frame-ancestors 'self' https://brobro.casino https://www.brobro.casino` (без него
  iframe Lucky упирается в `X-Frame-Options SAMEORIGIN`). Бэкап — `~/deploy-backups/server.crash-heroes.com.conf.20261005-143612`.
- **Игра** id 20 `donkey_rush`: `link` и `engine_url` = `https://server.crash-heroes.com/ce60c59a-…/`.
- **Связка с Lucky прод**: провайдер Lucky `donkey-rush` (`b5cdc0a4-…`, игры/запуск → `api.crash-heroes.com/api/external/lucky/{games,game/url}`),
  проект крашей **4 «Lucky Server Donkey Rush»** с прод-колбэками Lucky; пара ключей выпущена Lucky и передана
  трубой между серверами без вывода. Проект 2 не трогали. В BroBro игра добавлена (провайдер 12, игра 1,
  `brobro.casino/games/12/1`), комиссия 0%. Гостевое демо — 200. smoke прод: всё зелёное, кроме старых
  6 рестартов ScaryClown (с 28.09, не связано).
- Обложки игр для оператора — `storage/app/public/games/covers/<slug>-site.png` api-core (`https://api.crash-heroes.com/storage/games/covers/…`);
  05.10 добавлена `crash-hockey-site.png` (прод и дев). Все 13 прежних обложек отвечают 200.
- Итог 05.10: Crash Hockey (id 19) играется из BroBro — `https://brobro.casino/games/1/17`; адреса прода — скил
  `game-engine-rng`, журнал 05.10.

## Журнал: 2026-10-06 — обложка Hockey Strike

- Обложки лежат в `/home/admin/crashgames/minigames-admin-back/storage/app/public/games/covers/` (не в `app/` —
  `find` по `*/storage/...` находит симлинк), на проде 78.141.216.99 и деве 167.233.24.119.
- Новая обложка Hockey Strike — присланный Ильёй файл как есть (1254×1254, 2,7 МБ): `hockey-strike-icon.png`
  (+ копией `hockey-strike-site.png`). Старая сгенерированная `crash-hockey-site.png` удалена (ни Lucky, ни базы
  крашей на неё не ссылались — проверено), бэкапы в `~/deploy-backups/`. Новое имя файла — чтобы не ловить кэш
  браузеров. В Lucky прод и дев у игры `thumbnail_url` → `…/covers/hockey-strike-icon.png`.
- В Lucky дев игра `crash-games-test-rng` переименована в `crash-games-crash-hockey` (правка slug в базе).
- Илья: обложку надо было ставить **именно присланным файлом**, без ресайза и скругления.


## Журнал: 2026-10-12 — «Хоккей не работает на деве»: фронт Crash Hockey принимает только USD

- Симптом: из Lucky dev игра открывается, сокет подключается (101), профиль проходит, но экран
  «Соединение прервано. Ответ сервера не соответствует поддерживаемому формату» и ни одной игры в
  `game_rng_games`. Бэк при этом исправен: прямой зонд сокета с той же сессией (`start 100` →
  `result` → `cash_out`, баланс у Lucky dev двинулся) прошёл.
- Причина: сборка фронта `games/crashhockey/scripts/index-CJBJJze_.js` (одна и та же на деве и
  проде, 05.10) жёстко проверяет `currency === "USD"` в ответах `profile`, `state`, `history`
  (ветка `invalid-data`). Игрок Lucky dev `players.id 217` (создан 12.10 14:05) — **RUB**, все
  прежние dev-игроки RNG (206–215) были USD. На проде игрок USD, поэтому там играется.
- Что делать: либо фронт игры учит не-USD валюты (формат, чипы, проверки), либо для тестов на
  деве нужен USD-игрок Lucky. Движок и api-core трогать не надо.
- Зонд сокета лежит в scratchpad сессии (`rng-probe.mjs` / `rng-start.mjs`, Node 22+ со
  встроенным `WebSocket`): конверт `{id:<целое>, type, data?}`, строковый `id` даёт
  `Invalid message`.
