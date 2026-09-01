---
name: admin-ui
description: Контекст работы с экосистемой Admin-UI компании — приватная либа компонентов `@agg/admin-ui` (репо `Admin-ui`) и потребитель этой либы — админка `nexus-frontend-react-admin-panel` (Olimp). Активируй когда пользователь работает в `/home/ilya/Documents/Work/Admin-ui` или `/home/ilya/Documents/Work/Olimp/nexus-frontend-react-admin-panel`, обсуждает компоненты `agg/*`, добавление/публикацию компонентов в либу, перенос фич между админкой и либой, либо когда показывает скрины из `~/Pictures/Screenshots/Admin-UI/*`.
---

# Admin-UI (экосистема)

Это **связка двух репозиториев**: общая UI-либа и конкретный потребитель. Большинство задач пользователя проходят через эту пару — поэтому при работе с одним всегда держи в голове второй.

## Два репозитория

### 1. `Admin-ui` — UI-либа `@agg/admin-ui`
- Путь: `/home/ilya/Documents/Work/Admin-ui`
- Подробности: см. [library.md](library.md)
- Раздаёт компоненты через **shadcn-style registry** (`registry.json` + `npm run registry:build`), не через классический npm-импорт. Компоненты копируются в потребителя командой `npx shadcn add ...`.
- Витрина — Storybook (`npm run storybook:dev`).
- Релиз: `npm version` → `git tag X.Y.Z` → `git push origin X.Y.Z`, дальше CI.

### 2. `nexus-frontend-react-admin-panel` — админка Olimp
- Путь: `/home/ilya/Documents/Work/Olimp/nexus-frontend-react-admin-panel`
- Подробности: см. [project.md](project.md)
- Потребляет компоненты Admin-ui (раскопированные в `src/components/agg/*` и `src/components/ui/*`).
- Стек: React 19 + Vite, TanStack Router/Query/Table, Tailwind v4, Keycloak, i18next.

## Соглашения по слоям компонентов

И в либе, и в админке действует одинаковая схема папок:

- `src/components/ui/*` — низкоуровневые shadcn-компоненты (`button`, `input`, `select`, ...). Минимально кастомизированные. Менять с осторожностью — это база.
- `src/components/agg/*` — «обёртки» компании поверх `ui/*` (`better-button`, `better-input`, `better-badge`, `select-button`, `dropdown`, `calendar`, `field`, ...). **По умолчанию импорт идёт отсюда**, а не из `ui/*`.
- `src/components/shared/*` (только в админке) — прикладные виджеты для конкретных страниц, собранные из `agg/*` (например, `shared/table/*`).

Правило: компонент уровня домена (например, `TableFilter`) собирается из `agg/*`. Если потребуется новый низкоуровневый примитив — сначала появляется в `ui/`, потом обёртка в `agg/`.

## Когда писать в либу, а когда в админке

- **В либу (`Admin-ui`)** — если компонент переиспользуем за пределами одной страницы и не завязан на доменные сущности проекта. Примеры: `better-button`, `dropdown`, `calendar`, потенциально `TableFilter`.
- **В админку** — если компонент нужен только тут или тащит в зависимости доменные query/типы (например, `ServiceRolesBadges`, конкретные `pages/*`). Лежит в `src/components/shared/*`.

При сомнении — спрашивай пользователя; перенос компонента из админки в либу делается отдельной задачей (с регистрацией в `registry.json` и Storybook-историей).

## Workflow «добавил компонент в либу»

1. Создаёшь файл в `src/registry/new-york/ui/<name>/<name>.tsx`.
2. Дублируешь экспорт (или имеешь его) в `src/components/agg/<name>.tsx` для локальной разработки/Storybook.
3. Регистрируешь в `registry.json` (`name`, `target: components/agg/<name>.tsx`, `dependencies`, `registryDependencies`).
4. Пишешь story в Storybook.
5. Поднимаешь версию (`npm version patch|minor|major`), создаёшь тег, пушишь тег — CI публикует.
6. В админке обновляешь через `npx shadcn add ...` (или ручным копированием — уточнить у пользователя).

## Спеки конкретных компонентов

- [TableFilter](components/table-filter.md) — контейнер фильтров для таблицы (Classical/Simple, +N overflow, двухпанельный FilterDropdown). В разработке.

## Скриншоты-задачи

Пользователь часто кидает специ-скрины из `~/Pictures/Screenshots/Admin-UI/<ComponentName>/` — это макеты дизайнера для нового/правленного компонента. Алгоритм:

1. Прочитать **все** скрины в папке (они описывают разные состояния и edge-cases).
2. Сначала зафиксировать поведение текстом (состояния, переходы, исключения), потом обсуждать API/реализацию.
3. Решить вместе с пользователем, в либу это идёт или в админку.
