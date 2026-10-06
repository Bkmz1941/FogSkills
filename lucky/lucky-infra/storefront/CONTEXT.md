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
  год — **отменено 2026-10-05**, см. ниже), домены `brobro.casino` + `www.brobro.casino` (DNS уже сюда), серт
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
  `APP_PUBLIC_KEY=pk_dHuWZjOP1QmdOCmxPcPxq0M5` (**на 05.10 отозван** — витрина ходит с `pk_wwQOjPKyfTec7oZr5tXPCyIf`) (клиентский ключ прод-проекта
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

### Кэш в браузере (с 2026-10-05, по указанию Ильи)

На обоих серверах витрины (дев `lucky-dev`
`/etc/nginx/sites-available/storefront.luckyserver.pro`, прод `lucky-prod`
`/etc/nginx/sites-available/brobro.casino`) `/assets/` и `location /` отдают
блок Ильи: `add_header Last-Modified $date_gmt;` + `Cache-Control "no-store,
no-cache, must-revalidate, proxy-revalidate, max-age=0"` + `expires off` +
`etag off` — браузер ничего не хранит и каждый раз качает текущую сборку
(было `expires 1y` + `immutable`, из-за чего у игроков висел старый JS после
выкатки 05.10). Бэкапы прежних конфигов — `/home/admin/*.nginx.bak-20261005*`.
Эталоны в репо — `infra/nginx/*.conf`.

### Журнал 2026-10-05 — правки витрины (дев и прод)

**`dev` и `main` разошлись.** На 05.10 в `dev` было ~54 коммита kvaggone, которых нет в `main` (мобильный шелл:
вкладки, Konsta, профиль, селектор проектов, PWA). При этом **`dev` откатывает то, что есть на проде**: гостевое демо
на странице игры (`6dad45a`, `mode = demo`) и прод-джобу CI (`BROBRO_DEPLOY_HOST=144.31.40.52` + `setfacl` для
www-data — в `dev` деплой прода снова через `$SERVER_HOST` + rsync). **Полный мерж `dev` → `main` не делать** без
решения Ильи (05.10 он выбрал «только правка»). Порядок для любой правки «в прод и дев сразу»: коммит в `dev` →
`git worktree add --detach <scratchpad>/sf-main origin/main` → `cherry-pick` (конфликты обычно в
`LayoutStorefront.tsx` — у `dev` там `hasSidebar`, — и в доках: на `main` доки старее, брать версию `main`) →
`typecheck` + `eslint` + `build:prod` (node_modules — симлинком из основной копии) → `git push origin HEAD:main`
→ дождаться бандла на `brobro.casino` (grep характерного класса в `index-*.js`) → `git worktree remove`.

**Грабля: параллельная сессия коммитит чужие незакоммиченные правки.** 05.10 16:46 коммит «Drop the Wheel of
Fortune…» (`583a691` main / `59816cf` dev) унёс мою недоделанную правку отступа баланса (`pr-px`) на прод — у суммы
пропал отступ справа без стрелки. Перед своим коммитом — `git log origin/<ветка> -- <файл>` и `git diff`, не
считать рабочее дерево только своим.

Что сделано (всё на дев и прод):
- **Мобилка/планшет, страница игры** (`de0d21d` dev / `a308ec3` main): ниже `lg` (1024) на `/games/…` только шапка
  и iframe во весь экран — без паддингов контейнера, сайдбара (`contents max-lg:hidden`), футера и блока под игрой;
  высота `100svh − шапка` (3.5rem + safe-area ниже `md`, 4rem на `md…lg`); `body` получает `padding-bottom` под
  нижнее меню только через `body:has(.mobile-bottom-navigation)` (меню на странице игры не рендерится). Грабля:
  `max-lg:p-0` не перебивает `sm:p-6 sm:py-8` — паддинги контейнера на странице игры включаются только с `lg:`.
- **Десктоп, ширина как у bets.io** (`592dbd8` / `368b5a4`): от `lg` шелл до **1526px** = 24 поле + 164 сайдбар +
  24 gap + **до 1298 контент** + **16 поле справа** (`lg:max-w-[1526px] lg:pr-4`), по центру на широких; шапка и
  скелетон загрузки той же ширины. Замер bets.io: сайдбар 206 (с 1248px), поле 16, контент max 1298, вся связка
  1536 по центру.
- **Кэш** — см. раздел выше; в репо `c8a33e1` / `5d23dd5` (на `main` только `infra/nginx`), потом блок Ильи
  `no-store…` — правка эталонов и доков **не закоммичена**.
- **Баланс в шапке** (`d6e66c3` / `4927a31`): сумма и стрелка выбора кошелька — один блок, подсветка на контейнере
  (`hover:bg-muted active:bg-muted has-[[aria-expanded=true]]:bg-muted`), у ссылки и стрелки своя подсветка
  выключена (`hover/aria-expanded/dark:hover:bg-transparent`); отступ суммы `px-2 not-last:pr-px` — 1px справа
  только когда есть стрелка (`WalletSwitcher` возвращает `null` при ≤1 кошельке, тогда отступы 8/8).
- Удалены комментарии, которые я добавлял в код (Илья: «убери комменты если добавлял»).

Проверка вёрстки: `vite preview --mode dev` на 127.0.0.1:13199 + chrome-devtools `emulate`/`resize_page` и замер
`getBoundingClientRect`. Грабли: PWA service worker отдаёт старый бандл — снять
(`navigator.serviceWorker.getRegistrations()` → `unregister`, `caches.delete`); вкладка после мобильной эмуляции
остаётся в масштабе — открывать новую страницу в новом `isolatedContext`. Баланс в шапке виден только
залогиненному — проверять его глазами нечем без игрока.

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
