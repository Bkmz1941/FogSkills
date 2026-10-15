# Lucky — админка

## Репозиторий

`lucky/lucky-admin` на gitlab.agg.one, локально ожидается рядом с бэком:
`~/Documents/Work/Lucky/lucky-admin` (Next.js, статик-билд). Типы API-контракта
копируются вручную из `lucky-api/packages/shared/src/index.ts` в
`src/shared/index.ts` админки.

## На сервере

`~/lucky-admin-dev/app/` — статик-билд SPA (`dist/`) + `server.js` —
мини-сервер node: только раздаёт статику. Прокси `/api` нет (убран
2026-08-12): браузер ходит в API напрямую по `APP_API_BASE_URL`,
запечённому в билд (`.env.dev` → `https://dev2.api.luckyserver.pro`);
CORS отдаёт сам API (`main.ts` отражает любой Origin); CORS-блок на nginx
API-домена убран 2026-08-13, лежит только в
`/etc/nginx/sites-available/luckyserver-dev2.bak-20260813` (проверено 2026-09-09).
Конфиг — `~/lucky-admin-dev/.env`: `NODE_ENV`, `HOSTNAME=127.0.0.1`,
`PORT=3002`.

Запущена **user-юнитом** systemd `lucky-admin-dev` (не системным!), linger
для admin включён — переживает ребут и закрытие SSH-сессий.

## Транзакции, провайдеры и удаление проекта (с 2026-08-19)

- **Раздел «Транзакции»** есть у суперадмина (все проекты) и внутри проекта (то
  же, минус фильтр проектов) — общий `FinanceWorkspace`. Колонки: ID, юзер
  (email над uuid, кликабельно), провайдер (из `metadata.provider`), scope, тип,
  баланс до / сумма / баланс после (одинаковый белый вес), дата `YYYY-MM-DD`,
  шестерёнка «Детали». Поиск клиентский (`navigate`, крестик очищает) с
  `placeholderData: keepPreviousData` — таблица обновляется на месте, без
  полноэкранного лоадера. Попап деталей: провайдер/игра из снапшота meta, ID и
  External ID с тултипами, Launch token (`metadata.launch_token`, с 20.08; раньше
  «Session»), Round/Bet id, Bet number, порядок баланс до → сумма →
  баланс после, табы Запрос/Ответ. Длинные тире по всему разделу заменены на
  дефисы.
- **Игровые провайдеры у проект-админа УБРАНЫ (20.08, коммит `2cd4d8d`)** —
  остался только каталог Games (см. ниже): страниц `/project/game-providers*`
  больше нет, из проектного API используется лишь `GET /v1/project/game-providers`
  (фильтр в «Транзакциях»). Бэк при добавлении игры сам линкует её провайдера
  (`5ea124b` в lucky-api), каталог показывает игры всех провайдеров с доступом
  от рута. Рутовый раздел Game Providers (доступ проектам) не менялся. В
  билдере приостановленные игры помечены (красная рамка, тултип-причина),
  показан read-only публичный URL игры `/games/{p}/{g}` (с 20.08; раньше
  `/providers/{p}/games/{g}`).
- **Раздел «Games» у проект-админа = каталог (20.08, коммит `ae9838d`):**
  `/project/games` сразу рисует «Games» — карточную сетку по провайдерам с
  тумблером Add/Added (изменение применяется сразу, на кнопке спиннер и
  disabled на время запроса). Плоский список подключённых игр и маршрут
  `/project/games/add` **убраны** (были в `5a2d42e`, жили один день):
  тумблер покрывает и добавление, и удаление. Компонент каталога —
  `ProjectGamesCatalog.tsx` (бывший `ProjectGamesAddPage`). API прежнее:
  `GET /v1/project/games/catalog`, `POST/DELETE /v1/project/games`;
  `useProjectGamesQuery` (список подключённых) остался — его читают Dashboard,
  Content и Transactions. Бэк при добавлении игры сам линкует провайдера,
  каталог показывает игры всех провайдеров с доступом от рута. **Локальный запуск на дев:** `npm run dev -- --mode dev`
  (порт 3000, `.env.dev` → `APP_API_BASE_URL=https://dev2.api.luckyserver.pro`;
  без `--mode dev` vite берёт `.env.local` → `127.0.0.1:8080`).
- **Удаление проекта** — как у игровых провайдеров: простая правая кнопка на
  вкладке Overview без рамки «Danger zone». Список Accounts на Overview (таблица
  имя/email/роль/статус + «Sign in as») **оставлен** — 19.08 его убирали как дубль
  вкладки Accounts, 20.08 Илья попросил вернуть.

Рестарт (ровно так делает CI — юнит должен оставаться user-level):

```bash
XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user restart lucky-admin-dev
```

Логи: `XDG_RUNTIME_DIR=/run/user/$(id -u) journalctl --user -u lucky-admin-dev`.

## CI (lucky/lucky-admin)

С 2026-08-21 (коммит `98fb7e0`) — две ветки: `dev` → `build_dev`
(`build:dev`) → `deploy_dev` (rsync `dist-deploy/` в
`admin@$SERVER_HOST:lucky-admin-dev/app/` с `--delete` + рестарт user-юнита
`lucky-admin-dev`); `main` → `build_prod` (`build:prod`, `.env.prod`:
`APP_API_BASE_URL=https://api.luckyserver.pro`, `ADMIN_PORT=3000`,
`APP_VERSION=0.9.2`) → `deploy_prod` (в `lucky-admin/app/`, юнит
`lucky-admin`). `SERVER_HOST` и `SSH_PRIVATE_KEY_BASE64` — scoped по GitLab
environments `dev`/`prod` (dev → 178.104.243.232, **prod → 178.105.17.213**).
Тег `legacy-last` = `main` до мержа dev (059da30). На проде: `~/lucky-admin/`,
user-юнит `lucky-admin` (:3000, за nginx `admin.luckyserver.pro`), Node 24 —
подготовлено 21.08, старый контейнер `luckyserver-admin-1` снесён; детали и
вход (root `admin@luckyserver.pro`, пароль = дев) — `prod/CONTEXT.md`.

## Доступ

- URL: https://dev2.admin.luckyserver.pro (nginx → 127.0.0.1:3002).
- Вход: root-юзер `admin@luckyserver.pro`, пароль
  `fSpwZz7mZf4gtbptAtfHjrlYugmXpef9` (дев; Илья разрешил хранить здесь —
  заходить с ним). Аккаунты живут в БД бэка (`root_users`) — создание новых
  описано в `backend/CONTEXT.md`.

## Локализация контента (en/ru) — 15.10.2026, не закоммичено

- Локали проекта (General в проекте и у рута, New project): только `en`/`ru`
  (`contentLocales` из контракта); API режет остальное `@IsIn`.
- `PageProjectContent` оборачивает контент в `ContentLocalesProvider`
  (`supported_locales` + `default_locale` проекта). Каждая форма с текстом
  (`MenuFields`, `SocialFields`, `SitemapFields`, `BannerFields`, `SectionFields`,
  `TextBlockFields`, `PageLayoutFields`, `DisclaimerFields`,
  `FooterSectionSettingsDialog`) вызывает `useLocaleSwitch()` и рендерит
  `<LocaleSwitcher>` (выпадашка «Localization», на всю ширину строки, скрыта при
  одной локали) и `<LocaleFields>` — по инпуту на локаль, видна только выбранная,
  остальные `hidden`, но смонтированы и уходят в FormData. Имена полей:
  основная локаль — обычное имя (`title`), прочие — `translations[ru][title]`
  (`translationFieldName`). `RichTextEditor` принимает `htmlName`/`textName`.
- Действия (`projectContentActions.ts`) читают локали из скрытых полей
  `content_locales`/`content_default_locale`, `localizedText(form, fields)`
  проверяет правило API (обязательные поля везде, необязательные — везде, если
  хоть где-то заполнено) и кидает `ContentLocaleError`; `act()` превращает его и
  400 `CONTENT_LOCALE_MISSING` от API в `{ error, missingLocales }`.
  `ContentEditorDialog` отдаёт `missingLocales` через `ContentDialogStateContext`:
  триггер `aria-invalid` (красная обводка), текущая локаль красным, в списке
  «Russian — fill in» красным с обводкой, форма сама переключается на первую
  недостающую. Скрытый заголовок секции (`show_title` выкл) переводов не требует.
- Футер: переводы дисклеймера и заголовков секций живут в
  `footer_settings.translations[locale]`, API сливает их по полю, не по локали.
- Контракт `src/shared/index.ts`: перенесены только типы локализации; дрейф по
  ставкам/коэффициентам (`coefficient` удалён в API, админка ещё читает) остался —
  полная копия сломала бы typecheck админки.
- Проверка 15.10 локально (проект Debug project #1 с включённым `ru`): Save без
  русского → ошибка и подсветка, с русским → сохранилось, витрина на ru показала
  перевод.

