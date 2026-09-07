# Lucky — storefront (витрина казино, дев)

## Новый фронт: lucky-storefront (с 2026-08-19)

Новый фронт витрины — репозиторий `lucky/lucky-storefront` на gitlab.agg.one,
локально `~/Documents/Work/Lucky/lucky-storefront`. Ветки: `main` (initial
commit), рабочая — `dev`, feature-ветки вида `mcdx/lsr-…`. Vite SPA
(`npm run build:dev` → `dist/`), без докера. Идёт на смену brobrocasino;
всё ниже про brobrocasino — прежний фронт.

### Прод: brobro.casino на 144.31.40.52 (с 2026-08-21)

- **Хостинг**: сервер `lucky-prod` (144.31.40.52), nginx-статика из
  `/home/admin/brobro-casino/dist` (SPA-fallback, `/assets/` immutable-кэш на
  год), домены `brobro.casino` + `www.brobro.casino` (DNS уже сюда), серт
  Let's Encrypt `brobro.casino` (certbot --nginx, без email как на дев-хостах,
  redirect 80→443, автопродление таймером). `/home/admin` выставлен 751 (o+x),
  каталоги 755 — иначе www-data не пройдёт в home. Эталон вхоста в репо:
  `infra/nginx/brobro.casino.conf`.
- **CI (ветка `main`)**: `build_prod` (`npm ci && build:prod`) → `deploy_prod`
  (rsync `dist/` с `--delete` в `admin@$SERVER_HOST:/home/admin/brobro-casino/dist/`).
  Переменные окружения **prod** в GitLab: `SERVER_HOST`(=144.31.40.52) +
  `SSH_PRIVATE_KEY_BASE64` (декод с `tr -d '[:space:]'`). Ветка `dev` — прежний
  дев-деплой (`SSH_PRIVATE_KEY_DEV_BASE64`, storefront.luckyserver.pro).
  Тег `legacy-last` = старый `main` (init), релиз — `0.9.3`.
- **`.env.prod`**: `APP_API_BASE_URL=https://api.luckyserver.pro`,
  `APP_PUBLIC_KEY=pk_dHuWZjOP1QmdOCmxPcPxq0M5` (клиентский ключ прод-проекта
  «BroBro Casino», id `30465ae8-7626-46c4-a7f2-f990d19a49f0`, primary_domain
  brobro.casino, status active), `APP_CURRENCY=USD`, `APP_LOCALE=en`,
  `APP_DEFAULT_TIME_ZONE=Europe/Moscow`, `APP_VERSION=0.9.3`.
- **Проект на проде создан с нуля** (прод-API на 178.105.17.213, чистая БД):
  root'ом `POST /v1/root/projects` (slug brobro-casino) + `POST
  /v1/root/projects/:id/client-keys` (`{name:"storefront"}` → pk_). Публичный
  bootstrap: `GET /v1/cms/bootstrap?locale=en&currency=USD&time_zone=Europe/Moscow`
  с заголовком `X-Public-Key: pk_...` (обязательны locale/currency/time_zone,
  иначе 400). **Проект-админа у прод-проекта пока НЕТ** — контент дефолтный,
  витрина показывает оболочку; для наполнения нужен project-admin (создать
  root'ом) и публикация секций.

- **Хостинг (дев)**: сервер `lucky-server-dev` 178.104.243.232 (НЕ brobro-dev!).
  DNS storefront.luckyserver.pro переведён сюда; nginx-статика из
  `/home/admin/lucky-storefront-dev/dist` (SPA-fallback, `/assets/` —
  immutable-кэш на год), серт certbot `storefront.luckyserver.pro`.
  Эталон nginx-конфига лежит в репо: `infra/nginx/storefront.luckyserver.pro.conf`.
- **CI (ветка dev)**: build (node:24, `npm ci && npm run build:dev`) → deploy
  (alpine, rsync `dist/` с `--delete` в
  `admin@$SERVER_HOST:/home/admin/lucky-storefront-dev/dist/`). Статика,
  рестартов не нужно. Переменные в GitLab заведены Ильёй **на окружение
  `dev`** (у deploy-джоба `environment: dev`): `SERVER_HOST`
  (=178.104.243.232) и `SSH_PRIVATE_KEY_DEV_BASE64` (пара к ключу
  `deploy@gitlab` из authorized_keys admin).
- В репо остался стейловый `.deploy/deploy.conf` от старого
  docker-пайплайна white-label-front — не использовать.

### Запуск игр и история транзакций (с 2026-08-19)

- **Запуск игры — по публичным id.** Тайл CMS ведёт на
  `/games/{providerPublicId}/{gamePublicId}` (с 20.08; раньше
  `/providers/{p}/games/{g}`; `href` тайла собирает бэк в
  `public-content-contract.service.ts`, витрина только держит роут
  `ROUTES.game`), страница встраивает игру
  в iframe; вызов `POST
  /v1/core/providers/{providerPublicId}/games/{gamePublicId}/launch` (uuid-роут
  на бэке убран).
- **История транзакций — из API с курсорами.** Список Recent transactions
  грузится из `GET /v1/core/balances/transactions`; пагинация keyset — в запрос
  идёт `limit` + `before`/`after`, кнопки ходят по `prev_cursor`/`next_cursor`
  из ответа. **`page` слать нельзя** — бэк отвечает `400 UNSUPPORTED_FIELDS`
  (на этом ловилась задеплоенная витрина до выката курсорной версии). Код —
  `src/api/balances/balancesApi.ts`, `PageBalance.tsx`,
  `queries/balances/useTransactionsQuery.ts`.

## Репозиторий (brobrocasino, прежний фронт)

`lucky/brobrocasino` на gitlab.agg.one, локально
`~/Documents/Work/Lucky/brobrocasino`. Vite SPA (React 19, TanStack
Router/Query, ky, Tailwind 4) — стек как в lucky-admin. SSR/Next.js и
BFF-прокси убраны 2026-08-13: браузер ходит в API напрямую
(`APP_API_BASE_URL` + заголовок `X-Public-Key`, запекаются в билд из
`.env.dev`/`.env.prod`; переменные `APP_*` из окружения CI перекрывают
env-файлы). Docker/ansible из репо удалены.

## Сервер 95.216.163.101 (`brobro-dev`, Ubuntu 24.04)

- SSH: `admin@95.216.163.101`, ключ `~/.ssh/id_ed25519` строго с
  `IdentitiesOnly=yes` (иначе Too many authentication failures), sudo без
  пароля. Node на сервере НЕТ — и не нужен.
- Дев витрины: https://storefront.luckyserver.pro — nginx раздаёт статику
  из `/var/www/storefront-dev/dist` (владелец admin, каталоги 755),
  SPA-fallback `try_files $uri /index.html`, `/assets/` — immutable-кэш на
  год, `index.html` — no-cache. Серт Let's Encrypt (certbot --nginx).
- Legacy на этом же сервере: docker-контейнер `brobrocasino`
  (127.0.0.1:3001, старый Next.js-билд) за nginx `dev.brobro.casino` +
  каталоги `~/brobrocasino`, `~/white-label-front-release`. Репо больше не
  собирает docker-образ — контейнер заморожен, сносить только по команде
  Ильи.

## CI (lucky/brobrocasino, ветка dev)

Как в админке: build (node:24, `npm ci && npm run build:dev`) → deploy
(alpine, rsync `dist/` с `--delete` в
`admin@$SERVER_HOST_DEV:/var/www/storefront-dev/dist/`). Рестартов не
нужно — статика. Переменные проекта: `SSH_PRIVATE_KEY_DEV_BASE64` (ключ
`deploy@gitlab`, есть в authorized_keys admin) и `SERVER_HOST_DEV`
(=95.216.163.101) — остались от старого docker-пайплайна.

## Локальная разработка

`.env.local` (gitignored): `APP_API_BASE_URL=http://localhost:8080` +
`APP_PUBLIC_KEY` локального проекта из БД lucky-api. На 2026-08-13 локальный
и дев API ещё не отдают CORS-заголовки — ждёт рефакторинга бэка.

## Проект на dev2 и брендинг (2026-08-13)

- Проект «BroBro Casino» живёт на dev2-бэке (id
  `39506f3d-6e33-47a4-856a-58a32dad85d2`, primary domain
  storefront.luckyserver.pro). `.env.dev` витрины смотрит на
  `https://dev2.api.luckyserver.pro`.
- Аккаунт админа проекта: `brobro-admin@luckyserver.pro` /
  `Br0Bro!Dev2Admin42` (дев). Рут тоже может: Projects → Accounts →
  «Sign in as».
- Лого грузится в панели проекта: Settings → General → Project logo
  (конвертируется в 512×128 WebP, пишется в `projects.settings.storefront.
  config.assets.logo_url`). Публичный bootstrap отдаёт только https-URL.
- Витрина на JWT: логин/регистрация возвращают `access_token`, фронт хранит
  его в localStorage (`lucky_player_token`) и шлёт `Authorization: Bearer`;
  кук больше нет.

## Сессия 2026-08-13: что сделано

1. **Next.js/SSR выброшен полностью** → Vite 7 SPA. BFF-прокси `/api/[...path]`
   удалён — браузер ходит в API напрямую с `X-Public-Key`. ORIGIN_OVERRIDE и
   привязка к домену исчезли вместе с прокси.
2. **Архитектура как в lucky-admin**: `api/<домен>` (ky) → `queries/<домен>`
   (TanStack Query hooks + Actions) → `pages/<домен>/Page*.tsx`; layout в
   `components/layout`, роуты кодом в `lib/tanstack-routes`, константы в
   `constants/`. Монолит storefront-page.tsx (1543 строки) распилен.
   Самописные кэши заменены QueryClient (bootstrap staleTime Infinity,
   страницы + keepPreviousData, баланс через setQueryData).
3. **Env**: `APP_API_BASE_URL`, `APP_PUBLIC_KEY`, `APP_CURRENCY`,
   `APP_LOCALE` (env приоритетнее браузера), `APP_DEFAULT_TIME_ZONE`
   (браузер приоритетнее env). `.env.dev`/`.env.prod` в репо, `.env.local`
   гитигнорен. Переменные окружения сборки (CI) перекрывают env-файлы.
4. **Docker/ansible/Makefile/server.js удалены из репо** — чистая статика.
5. **JWT**: sessionStore (localStorage `lucky_player_token` + expires),
   Bearer в ky beforeRequest, 401 → сброс сессии, токен сохраняется из
   login/register/password-change/reset-confirm. Кук-авторизации нет.
   Idempotency-Key убран (бэк не читал).
6. **Дев-хостинг поднят с нуля**: nginx-статика + certbot на brobro-dev,
   CI build+rsync (см. выше). В lucky-api починены: владелец uploads
   (uid 1000), `PUBLIC_API_URL` на dev2 (+ зафиксирован в ansible-шаблоне
   env.tpl/group_vars — иначе деплой затирал).
7. Тесты API-клиента: 8 штук в `src/api/storefrontApi.test.ts` (node --test,
   мок fetch по pathname, JWT-семантика).
