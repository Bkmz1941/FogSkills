# Lucky — storefront (витрина казино, дев)

## Новый фронт: lucky-storefront (с 2026-08-19)

**Сетка десктопа (с 15.10, решение Константина в чате с Ильёй):** контейнер
`lg:max-w-[1448px]` с полями `p-6`/`sm:px-6` (24 px) → внутри 1400 = боковое
меню 180 (`SIDEBAR_WIDTH` в `src/components/ui/sidebar.tsx`) + зазор 20
(`gap-5`) + контент 1200. До этого было 1526 = 164 + 24 + 1290. Три места с
одним контейнером, менять синхронно: `layout/LayoutStorefront.tsx`,
`layout/StorefrontHeader.tsx`, `shared/storefront/StorefrontSkeletons.tsx`.
Ниже `lg` контейнер 1240 не трогали. Проверка: `npx vite dev --mode dev --host
127.0.0.1 --port 13101` (обычный `vite dev` без `--mode` не видит `.env.dev`,
переменные с префиксом `APP_`, и витрина пишет «Unable to reach the server»),
в DevTools при ширине окна ≥1448 мерить `div.container.flex-1`,
`[data-slot=sidebar-gap]` и `[data-slot=sidebar-inset]`.

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

### Журнал 2026-10-06 — витрина (дев и прод, всё через cherry-pick в `main`)

- Заглушка «Not available in your region» на `403 GEO_BLOCKED` при запуске (`gamesApi.ts`).
- Попап пополнения не прыгает по высоте: заглушка загрузки в форме будущей формы, загрузка монет/минимума — текстом
  на кнопке.
- Отступы: шапка и контент по 24px с обеих сторон (убран `lg:pr-4`), меню сдвинуто `md:-ml-4` — иконки под логотипом;
  на `main` у блока языка `md:px-0`.
- Пополнение/вывод — попап поверх текущей страницы, без перехода на `/deposit` (раньше игра размонтировалась).
  Маршруты `/deposit`, `/withdrawal` работают по ссылке; без входа — вход, потом попап.
- Шапка: «+» внутри блока баланса слева, на бонусном кошельке «+» нет; клик по сумме всегда открывает выпадашку
  кошельков, внизу пункт **History** → `/balance`.
- Страница баланса: только кошелёк из шапки (иконка, сумма, валюта; у cash справа Deposit/Withdraw, у бонусного
  кнопок нет), история по выбранному кошельку (`balance_code`), по 15 со стрелками по краям без номеров, «Loading…»
  вместо скелетонов, без метки «Bonus» в истории, карточки без растягивания (`content-start` у `main` и вкладки —
  грид на всю высоту растягивал карточки, это и были «огромные отступы»).
- Из настроек профиля убран блок Balance (на `dev` ещё пункт меню и маршрут `/settings/balance`).
- Локально «как на проде»: worktree `origin/main` + `.env.prod`, `npx vite dev --mode prod --host 127.0.0.1 --port
  13101` — ходит в боевой API с ключом BroBro (вход и деньги — настоящие).
- Параллельная сессия пушила в те же ветки (балансы, вывод) — перед push `git fetch` + `rebase origin/main`.

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

### Ручная выкладка на дев и прод (без CI) — 15.10.2026

По команде Ильи («обнови сайт дев прод и краши») сборки `build:dev`/`build:prod` из чистого worktree выложены
`rsync --delete` туда же, куда кладёт CI: `lucky-dev:/home/admin/lucky-storefront-dev/dist/` и
`lucky-prod:/home/admin/brobro-casino/dist/`; перед этим бэкап `tar czf ~/deploy-backups/<site>-dist-<stamp>.tgz`.
16.10 сетка 1400 и `scrollbar-gutter` закоммичены в `dev` (`75afe90`, `ff9586c`) и смержены в `main` (`de274a2`)
вместе с локализацией — с этого момента CI снова источник правды для дева и прода.

⚠ Грабля: у `admin` на дев/прод-серверах umask ограничительный (в ssh-сессии `0007`), и `rsync -rltz --chmod=D755,F644`
**без `-p`** положил новые файлы как `640` → nginx (www-data) получил `open() … Permission denied`, сайты ~5 минут
отдавали 403 на `/assets/*.js|css` (index.html при этом 200 — файл старый). Лечение: `find dist -type f -exec chmod 644`,
`-type d … 755`. Правильно: `rsync -a --chmod=D755,F644 …` (`-a` включает `-p`, без него `--chmod` игнорируется) и
сразу после выкладки проверять не только index.html, а `curl -o /dev/null -w '%{http_code}' …/assets/index-*.css`.
На крашах umask `0002` и та же команда дала 644 — не показатель.

### Витрина Crash Heroes — games.crash-heroes.com (сервер крашей 78.141.216.99)

- Тот же lucky-storefront, проект прод-Lucky **«Crash Heroes Catalogue»**. CI нет — выкладка руками.
- nginx `/etc/nginx/conf.d/games.crash-heroes.com.conf`: `/`, `/assets/`, `pwa-*`, `wheel-fortune-tent.png` и SPA-фолбэк
  — из `/home/admin/crashgames/storefront/current` (симлинк на `releases/<sha>-<дата>`); папки игр (`/fatguy/`…) — из
  `/home/admin/crashgames/games`.
- Сборка: worktree `origin/main` + `.env.prod`, но `APP_PUBLIC_KEY` = ключ проекта Crash Heroes (взять из текущего
  бандла `current/assets/index-*.js`), `APP_DEFAULT_TIME_ZONE=UTC`, `APP_PWA_ENABLED=false`, `APP_PWA_NAME`/`SHORT_NAME`
  `Crash Heroes`. В `index.html` руками: `<title>Crash Heroes</title>`, description `Crash Heroes casino.`, убрать
  `manifest` и `registerSW.js`; `sw.js`, `workbox-*`, `registerSW.js`, `manifest.webmanifest` не выкладывать.
- Выкладка: rsync в `releases/<sha>-<дата>/`, `ln -sfn … current.new && mv -T current.new current`. Откат — симлинк
  на прошлый релиз. Проверка: `/`, бандл, SPA-маршрут, `/fatguy/`, `/crashhockey/` = 200.
- Журнал: 15.10 `8503c9f-grid-20261015` — `origin/main` (= dev = main, `8503c9f`) + сетка 1400 (меню 180 / зазор 20 /
  контент 1200, контейнер 1448) + тот же незакоммиченный `scrollbar-gutter: stable`; собрано из чистого worktree в
  scratchpad (`git worktree add --detach`, `node_modules` симлинком, правки наложены точечно `sed`-ом, НЕ `git diff`
  рабочего дерева — в нём 38 чужих незакоммиченных файлов локализации с импортом `@/lib/i18n`, которого в `main` нет,
  сборка падает). В тот же день та же сборка руками выложена на дев и прод (см. «Ручная выкладка» ниже).
  22.09 `e512044` (первый); 14.10 `3bda9c9`, затем `a754055`, `f4ce5b2`, `5ccd9ad` (= main/dev, по команде
  Ильи); 14.10 вечер `5ccd9ad-scrollbar-20261014` — `origin/main` + незакоммиченный фикс `scrollbar-gutter: stable` на
  `html` в `src/styles/styles.css` (лого в шапке прыгало между `/balance` и `/settings`: скроллбар появлялся и
  контейнер `mx-auto` перецентрировался). Сборка: worktree + `.env.prod.local` (`APP_PUBLIC_KEY` из живого бандла,
  `APP_DEFAULT_TIME_ZONE=UTC`, `APP_PWA_NAME`/`SHORT_NAME`), `node_modules` симлинком из основного чекаута при
  одинаковом package-lock; `index.html` правится после сборки (title/description, убрать manifest и registerSW).
  Переменной `APP_PWA_ENABLED` в vite.config нет — PWA-файлы просто не выкладываются.

## Заголовки в светлой теме — 16.10.2026 (`5c44898` dev / merge `a294198` main)

Илья включил светлую тему на brobro.casino: заголовки секций, текстового блока и футера пропали (белые на белом).
Причина — правило `.storefront-frame :where(h1…h6) { color: #ffffff }` в `src/styles/styles.css` (`0b3b6a3`, 24.08):
**не в слое**, поэтому било и Tailwind-утилиты (`text-white` на баннерах оно же и перекрывало), и тему. Теперь оно
в `@layer base` с `var(--foreground)`: утилиты снова сильнее, в тёмной теме визуально ничего не изменилось. Подпись
вторичного баннера (`SecondaryPromoBanner`) переведена с `text-background` на `text-white` — там всегда тёмный
градиент, а `text-background` в тёмной теме дал бы чёрный текст, как только правило перестало его перекрывать.
Проверка на живом сайте без сборки: в DevTools удалить правило из styleSheets и добавить `<style>@layer base{…}</style>`.
Напоминание: в `styles.css` после `@import 'tailwindcss'` любые свои правила вне `@layer` перекрывают утилиты.

## Локализация витрины (en/ru) — на деве и проде с 16.10.2026

Сделано 14.10 (сессия + 4 сабагента), доведено и проверено 15.10; 16.10 по команде
Ильи закоммичено в `dev` коммитом `a3a7dab` (отдельно от сетки `75afe90` и
scrollbar `ff9586c`), merge `de274a2` в `main`, выкачено CI на оба сервера.
Рабочее дерево `feat/new-payment-provider` всё ещё держит те же правки
незакоммиченными — коммиты делались из worktree в scratchpad.

- Модуль `src/lib/i18n/i18n.tsx`: `I18nProvider` (обёрнут в `Main.tsx` поверх
  QueryClientProvider), хук `useTranslate()` → `{ t, language, setLanguage }`
  для компонентов, функция `translate(key, params)` для не-React кода (ky-клиент,
  мапперы, хелперы — вызывать в момент рендера/запроса, не на уровне модуля).
  Языки `en`/`ru`, дефолт `en`, выбор: localStorage `storefront-language` →
  `navigator.language` → `en`. Подстановка `{name}`. Словари грузятся
  `import.meta.glob("/src/locales/*/*.json", eager)`, ключи плоские
  `домен.раздел.ключ`, файл = домен: `auth, balance, common, content, games,
  layout, payments, settings` (по 8 файлов в `src/locales/en` и `ru`,
  388 ключей, наборы ключей идентичны, параметры совпадают).
- Переведено 42 файла (все `src/pages`, layout, shared-компоненты, `ui/sidebar`
  и `ui/carousel` (sr-only), kyClient, cmsMappers — **только fallback-тексты**,
  CMS-контент не трогается). Переключатель языка: **внизу левого меню**
  (Select с флагом, `SidebarLanguageSwitcher` в `StorefrontSidebar.tsx`, виден
  и гостю; Илья 15.10: «слева снизу — выбор языка») и Settings → Preferences
  (сегмент English/Русский). Кнопка-флаг в футере страницы, которую сделала
  сессия 14.10, убрана 15.10 по этой же правке.
- ⚠ **Главная для гостя после переключения на ru выглядит английской — это
  ожидаемо**, Илья 15.10 принял это за «локализация не работает»: всё видимое
  там (меню слева, баннеры, текстовые блоки, Log in/Sign up) — CMS-контент.
  Русский виден в окне входа, настройках, балансе, пополнении, нижней навигации.
- **С 15.10 (вечер) CMS-контент идёт за языком интерфейса**: `browserContext()`
  шлёт `locale = currentUiLanguage()` (из `src/lib/i18n/language.ts`, без
  Vite-кода, чтобы node-тесты импортировали хелперы), `I18nProvider` получает
  `onLanguageChange` → `queryClient.invalidateQueries()` (Main.tsx), и меню,
  страницы, футер перезапрашиваются. API отдаёт перевод, если локаль включена
  в проекте, иначе основную локаль (400 больше нет). `APP_LOCALE` на запросы не
  влияет. Контент-модель с переводами — `lucky-back/SKILL.md`, раздел
  «Локализация контента», админка — `admin/CONTEXT.md`.
- Было до 15.10: **CMS-контент (меню, баннеры, текстовые блоки, подписи кнопок Log in/Sign up
  из bootstrap) приходил с API на своём locale** (`browserContext()`:
  `APP_LOCALE` → `navigator.language`) и от переключателя не зависит. Слать
  язык интерфейса как `locale` в API нельзя вслепую: `front-storefront.service`
  отдаёт 400 «The requested locale is not enabled for this project», если
  локали нет в `supported_locales` проекта. Связка «язык UI → locale CMS» —
  открытый вопрос, решения Ильи нет.
- Проверка: `node <scratchpad>/i18n-check.mjs <repo>` (ключи словаря vs строки
  в коде, en vs ru), `npm run typecheck`, `npx eslint src`,
  `npx vite build --mode dev --outDir <tmp>`; в браузере
  `localStorage.setItem('storefront-language','ru')` + reload. 15.10 локально
  (API 18080, витрина 13101) проверены: главная, модалка авторизации
  (регистрация с своим паролем), настройки (все три раздела, переключение
  языка на лету в обе стороны), баланс, модалка пополнения — всё по-русски,
  ошибок в консоли нет. В локальной БД остался тестовый игрок
  `i18n-check@example.com` (Debug project #1).
