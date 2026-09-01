---
name: library
description: Детали репозитория `@agg/admin-ui` — структура, скрипты, registry, релизный процесс.
---

# `@agg/admin-ui` — UI-либа

**Путь:** `/home/ilya/Documents/Work/Admin-ui`
**Имя пакета:** `@agg/admin-ui`
**Текущая версия (на момент описания):** 0.3.1 — версия меняется, перед релизом смотри `package.json`.

## Стек

- React 19 + Vite 7
- TypeScript 5.9
- Tailwind CSS v4 (`@tailwindcss/vite`, `@tailwindcss/postcss`, `tw-animate-css`)
- shadcn-style registry (`shadcn` 3.8, `style: "new-york"`, base color `zinc`)
- Radix UI (`radix-ui`, `@radix-ui/react-select`, `@radix-ui/react-slot`)
- Storybook 10 (`@storybook/react-vite`, addons: a11y, docs, vitest)
- React Hook Form + Zod
- TanStack Query, TanStack Table
- date-fns, react-day-picker, react-dropzone, lucide-react, react-icons

## Структура `src/`

```
src/
  App.tsx                  — dev-обвязка
  main.tsx
  components/
    ui/                    — низкоуровневые shadcn-компоненты
    agg/                   — обёртки компании
      layout/              — header-dropdown, mock-link и пр.
  registry/
    new-york/ui/<name>/    — исходники, которые публикует registry
  storybook/               — оформление сторибука
  styles/global.css        — Tailwind entry
  hooks/, lib/, queries/, @types/
  docs/                    — index.mdx, registry.mdx
```

## Ключевые файлы

- `registry.json` — описание всех публикуемых компонентов (`name`, `type`, `files`, `target`, `dependencies`, `registryDependencies`). Каждый новый компонент регистрируется здесь.
- `components.json` — конфиг shadcn (style new-york, alias `@/components`, `@/lib/utils`, ...).
- `.storybook/` — конфиг витрины.
- `eslint.config.js`, `.prettierrc` — линт и формат.

## Скрипты

- `npm run dev:ui` — dev-сервер Vite.
- `npm run storybook:dev` — Storybook на 6006.
- `npm run storybook:build` — сборка Storybook.
- `npm run registry:build` — сборка registry (shadcn).
- `npm run lint`, `npm run lint:fix`, `npm run format:check`.

## Релиз

1. `npm version patch|minor|major` — поднять версию в `package.json`.
2. `git tag X.Y.Z`.
3. `git push origin X.Y.Z`.
4. CI/CD публикует пакет автоматически (см. `.gitlab-ci.yml`).

## Конвенции

- При добавлении компонента — обязательно: файл в `registry/new-york/ui/<name>/<name>.tsx`, запись в `registry.json`, экспорт/обёртка в `components/agg/`, story в Storybook.
- Если компонент зависит от другого registry-компонента — указываем `registryDependencies: ["@agg/<name>"]` или `["@shadcn/<name>"]`.
- Иконки — `lucide-react` (в `components.json` зафиксировано).
