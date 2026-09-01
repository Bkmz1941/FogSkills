# claude-skills

Скиллы для Claude Code, хранятся на этом внешнем диске (T714), чтобы работать на разных машинах. Это ЕДИНОЕ место хранения — в `~/.claude/skills` и в проектах лежат только симлинки сюда.

## Скиллы

Игра «Таверна» — четыре скила, у каждого своя роль (разделение 2026-09-01):

- `tavern-game` — память решений: доменные справочники (BUILD/VIEW/CHARACTER/MONSTERS/UI/ARCHITECTURE/ATTRIBUTES), `PITFALLS.md` (история багов), `DESIGN_LOG.md` (хронология), `history/` (журналы аудитов и правок UI)
- `tavern-cooking` — готовка (еда, рецепты, жидкости, посуда), модуль `Assets/Modules/Cooking`; всегда рядом с `tavern-game`
- `tavern-regress` — контроль регрессий: инварианты, карта покрытия, `probes/check_all.py` одним прогоном, порядок разбора красного
- `tavern-ideas` — идейный помощник: вкус Ильи, отвергнутое с причинами, приёмы движка; включается только по зову

Остальное:

- `crash-games`, `lucky-infra`, `poker-infra`, `debug-panel` — инфраструктура рабочих проектов
- `shinobi-council` — формат ответов «Совет шиноби»
- `admin-ui` — библиотека компонентов admin-ui
- `vitriny-tz` — не подключён симлинком (архивный)

## Как подключить на новой машине

Claude Code ищет скиллы в `~/.claude/skills/<имя>/`. Диск exFAT — симлинки НА нём создавать нельзя, но симлинки С домашней папки НА него работают:

### Linux
```bash
for s in tavern-game tavern-cooking tavern-regress tavern-ideas crash-games lucky-infra poker-infra debug-panel shinobi-council admin-ui; do
  ln -s /media/<user>/T714/claude-skills/$s ~/.claude/skills/$s
done
```

(Замени `<user>` на своё имя пользователя. Точка монтирования может отличаться — проверь `df -h` или `lsblk`.)

### macOS
```bash
ln -s /Volumes/T714/claude-skills/shinobi-council ~/.claude/skills/shinobi-council
```

(macOS обычно монтирует внешние диски в `/Volumes/<имя>`.)

### Windows (WSL)
```bash
ln -s /mnt/<буква>/claude-skills/shinobi-council ~/.claude/skills/shinobi-council
```

## Проверка
```bash
ls -la ~/.claude/skills/shinobi-council/SKILL.md
```
Если файл читается — Claude Code увидит скилл.

## Если переехал на машину без диска
Симлинк "висит" (broken). Claude Code просто не загрузит скилл, ошибки не будет. Подключи диск — и снова работает.
