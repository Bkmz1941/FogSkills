# claude-skills

Скиллы для Claude Code, хранятся на этом внешнем диске (T714), чтобы работать на разных машинах. Это ЕДИНОЕ место хранения — в `~/.claude/skills` и в проектах лежат только симлинки сюда.

## Скиллы

- `tavern-game` — контекст и журнал решений игры «Таверна» (DESIGN_LOG.md — единый источник истины, слит из двух копий 2026-07-18)
- `tavern-cooking` — готовка в «Таверне» (еда, рецепты, кухонные объекты, голод); дополняет `tavern-game`, модуль `Assets/Modules/Cooking`
- `shinobi-council` — формат ответов «Совет шиноби»
- `admin-ui` — библиотека компонентов admin-ui

## Как подключить на новой машине

Claude Code ищет скиллы в `~/.claude/skills/<имя>/`. Диск exFAT — симлинки НА нём создавать нельзя, но симлинки С домашней папки НА него работают:

### Linux
```bash
for s in tavern-game tavern-cooking shinobi-council; do
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
