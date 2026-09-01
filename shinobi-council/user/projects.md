# Проекты Ильи (доступ к коду)

Папки на машине Ильи, к которым у нас есть доступ для чтения и анализа. Не модифицируем без явной просьбы.

## Olimp-CMS — основной проект

**Путь:** `~/Documents/Work/Olimp-CMS`

**Тип:** многосервисный backend-воркспейс (микросервисы).

**Стек:**
- Kotlin + Gradle (Kotlin DSL, `build.gradle.kts` в каждом сервисе)
- gRPC + Protobuf (по libraries: `grpc-utils`, `protobuf-utils`)
- MariaDB через jOOQ (`cms-maria-jooq-connector`)
- JVM

**Сервисы (каждый — отдельный Gradle-проект):**
- `auth/` — авторизация
- `content/` — контент-сервис
- `users/` — пользователи
- `projects/` — проекты
- `docs/` — документация / docs-сервис

**Общие библиотеки:** `libraries/cms-maria-jooq-connector`, `libraries/connectors`, `libraries/grpc-utils`, `libraries/protobuf-utils`, `libraries/utils`, `libraries/versions`

**Важно:** в корне лежит `CLAUDE.md` — проектные инструкции. **Перед любой работой с этим репо читать в первую очередь его** + указанные там файлы из `claude/`:
- `claude/README.md` — навигация
- `claude/project.md` — обзор сервисов
- `claude/patterns.md` — единый стиль кода
- `claude/tasks/<активная>.md` — контекст текущей задачи
- `claude/stack.md`, `architecture.md`, `conventions.md`, `errors.md`, `team.md` — по необходимости

**Ключевые правила работы (из CLAUDE.md):**
- Стиль единый между сервисами — сверять новый код с существующими через grep
- Маленькие шаги, одна фича за раз
- **Не писать код без явного подтверждения от Ильи**
- Критиковать и не поддакивать
- Русский язык в общении и в комментариях кода

---

## BattleWorld — личный pet-проект

**Путь:** `/media/ilya/T714/Unity/BattleWorld`

**Тип:** 2D настольная игра на Unity (вдохновлена Battle for Rokugan / L5R). Делает **один**. Идёт ~2 месяца.

**Стек:**
- Unity 2D (Built-in Render Pipeline)
- Target: WebGL + Linux
- C# (Plain C# по умолчанию, MonoBehaviour редко)
- Input: "Both" (Old + New Input System)
- Server: Kotlin + Ktor + WebSocket (`server/`)
- До 2 игроков

**В корне:** `CLAUDE.md` — проектные конвенции (Game Flow Spec, UI Principles, Multiplayer, Conventions).

**Проектный скилл:** `.claude/skills/battleworld-dev/` — создан 2026-04-19 с Какаши в 1-на-1.

**Отключение Совета в проекте:** `.claude/settings.json` содержит `"permissions.deny": ["Skill(shinobi-council)"]` — в этом проекте персонажи Совета не активируются, чтобы не мешать работе.

**Главная боль:** "каждый раз спотыкаюсь о мелкие описания" — решается через `rules/pitfalls.md` скилла.

**Важные решения (уже зафиксировано в скилле):**
- Рефактор `Token` → `Card` для карт в руке (чтобы не путать с физическими токенами на провинциях).
- UI — полностью через код (`UIPalette`, `UITextureGen`), минимум Editor.
- JSON — парсинг через regex, без сторонних библиотек.
