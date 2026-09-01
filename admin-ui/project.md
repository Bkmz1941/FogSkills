---
name: project
description: Детали проекта-потребителя `nexus-frontend-react-admin-panel` (админка Olimp) — стек, структура, как он использует Admin-ui.
---

# `nexus-frontend-react-admin-panel` (Olimp Admin Panel)

**Путь:** `/home/ilya/Documents/Work/Olimp/nexus-frontend-react-admin-panel`
**Пакет:** `olimp` (private)
**Основная ветка для PR:** `main`. Текущая рабочая ветка — `dev`.

## Стек

- React 19, Vite 7
- TanStack Router, TanStack Query, TanStack Table
- Tailwind v4 + shadcn (потреблённые компоненты в `components/ui` и `components/agg`)
- Radix UI (диалоги, popover, dropdown, tabs, ...)
- Keycloak (`keycloak-js`) — авторизация
- Casbin / casbin.js — авторизация по ролям
- i18next + react-i18next — локализация
- Sentry (`@sentry/react`)
- React Hook Form + Zod, ky (HTTP), sonner (тосты), motion, next-themes

## Структура `src/`

```
src/
  Main.tsx
  api/                     — клиенты + сгенерированный swagger (npm run generate:api)
  assets/
  components/
    ui/                    — shadcn-компоненты (часть скопирована из @agg/admin-ui)
      custom/              — CustomDialog, CustomInput, CustomTabs
    agg/                   — обёртки (better-*, dropdown, calendar, field, table, ...)
      layout/
    shared/                — прикладные виджеты страниц
      table/               — Table.tsx, Pagination, TableActionsCell, ColumnHeader,
                             ButtonRefresh, TableLoadingRaw
      table/filters/       — TableFilterCalendar.tsx, TableFilterVersions.tsx
      search/              — SearchCollapsible
      dialog/
      Copyable, EmptyPagePlaceholder, FieldEditable, FieldInfoVertical,
      MultiSelectBadge, PageHeadSection, PlatformIcon, RouterLink,
      ServiceRolesBadges, TagBadge
    root/, layout/
  pages/                   — content, debug, errors, password-change, projects,
                             register, users
  queries/                 — react-query определения
  shared/
    hooks/, providers/, utils/
  constants/, lib/, styles/, types/
```

## Скрипты

- `npm run dev` — Vite dev на 3000.
- `npm run build:dev`, `npm run build:main` — сборки.
- `npm run generate:api` — генерация типов из swagger (`scripts/swagger`).
- `npm run lint`, `npm run lint:fix`, `npm run prettier:fix`.
- Husky + lint-staged настроены: pre-commit делает eslint --fix.

## Связь с `@agg/admin-ui`

- Компоненты «приезжают» в `src/components/ui` и `src/components/agg` через shadcn-registry либы (см. [library.md](library.md)).
- Прикладные виджеты, специфичные для админки (фильтры таблицы, шаренные плейсхолдеры), живут в `src/components/shared/*` и собираются из `agg/*`.
- В админке уже есть свои `TableFilterCalendar` и `TableFilterVersions` (`src/components/shared/table/filters/`) — отдельные компоненты под конкретные колонки. Нового **общего** компонента-контейнера фильтров пока нет.

## Конвенции разработки

### Формы — react-hook-form + Zod + `Controller` (стандарт проекта)

- Формы в проекте строятся на **react-hook-form + Zod** (`useForm` с `zodResolver`, поля через `<Controller>`). Это сквозная конвенция: ~28 файлов используют `Controller` (projects, content/banners/stories, users, screens, register, password-change, content-forms), и форма создания витрины (`PageCreateShowcase`) — в этом же ряду.
- **Любой новый/переписываемый экран-форма делается через RHF + `Controller`**, а не через локальный `useState` по полям. Если встречается экран на голом `useState` (например, раньше `TabContentShowcaseSettings` на view витрины) — это аномалия, её приводят к RHF, а не наоборот.
- Валидность гейтит сабмит (`formState.isValid`), ошибки полей показываются из `fieldState.error`. Схема — Zod, переиспользуется между связанными экранами где возможно.

### Доменные select-компоненты — form-агностичны

- `AggMultiSelectWrapper` (`components/agg/multi-select-wrapper.tsx`) и доменные обёртки выбора **не знают про react-hook-form**: контракт только `value` / `onChange` (+ `onBlur`). Импортировать RHF внутрь таких компонентов нельзя.
- К форме их подключает **внешний `Controller`** (`field.value`/`field.onChange`/`field.onBlur` + `fieldState`). Благодаря этому один и тот же компонент работает на любом экране-форме.
- `AggMultiSelectWrapper` — единый оркестратор выбора: `trigger` (`add` кнопка / `edit` карандаш), `surface` (`popover` — коммит сразу / `modal` — черновик + Сохранить), контент-дропдаун передаётся как `children` и читает выбор через `useMultiSelect()`. Он заменяет доменные `SelectAppsDropdown`/`LanguagesSelect`/`SegmentsSelect`/`SelectTagsField` и модалки `DialogEdit*`.
- Call-site **не передаёт стили/раскладку выпадашки** (ширины, паддинги): ширину поповера владеет сам wrapper, внутренние паддинги — контент-компонент.

### Стиль письма (комментарии, тексты, сообщения)

- **Дефис — всегда короткий `-` (U+002D).** Не используем длинное тире `—` (U+2014) и среднее `–` (U+2013) нигде: ни в комментариях, ни в UI-текстах/заглушках, ни в локалях (`ru.json`/`en.json`), ни в коммитах. Это сквозное правило проекта.
- **Без пояснительной прозы в комментариях.** Не пишем болтливые комментарии, пересказывающие код (`// Default ...`, `// Readonly: ...`, `// Chips reflect ...`). Код должен читаться сам. Допустимы: реальные `TODO`/`FIXME`, `eslint-*`/`@ts-*`-директивы и короткий JSDoc у публичного API, если он добавляет смысл.

### Скелетоны (loading state)

- **У скелетона никогда нет границы.** В скелетон-компонентах не используем `border`/`border-*` — ни рамку карточки, ни разделители. Форму задаём через `rounded-*`, `bg-*`, при необходимости `shadow-*`, но не бордером.
- Скелетон повторяет раскладку реального компонента (та же сетка/размеры), заменяя контент на `<Skeleton/>`-плейсхолдеры. Co-located рядом с фичей (`*Skeleton.tsx`); общий для нескольких фич — в `components/shared/*`.

## Окружение

- Node 20+ рекомендуется.
- Локальный Keycloak в Docker (см. README): realm `Olimp`, client `admin`.
- `.env`: `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`.
