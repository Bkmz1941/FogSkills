# claude-skills

Скиллы для Claude Code, хранятся на этом внешнем диске (T714), чтобы работать на
разных машинах. Это ЕДИНОЕ место хранения — в `~/.claude/skills` и в проектах
лежат только симлинки сюда.

## Раскладка: папка на проект, скилы внутри

```
claude-skills/
  tavern/          игра «Таверна»
    tavern-game/       память решений и доменные справочники
    tavern-cooking/    готовка: еда, рецепты, жидкости, посуда
    tavern-regress/    инварианты, покрытие, зонды, check_all.py
    tavern-ideas/      вкус, отвергнутое, сырые мысли (только по зову)
    tavern-refactor/   как рефакторим: протокол, приёмы, цели
  crash-heroes/    crash-games/      инфраструктура краш-игр
  lucky/           lucky-infra/      Lucky Server, деплой и CI
  poker/           poker-infra/      OlimpBet Poker, контейнеры и серты
  personal/        shinobi-council/  формат ответов «Совет шиноби»
```

### ⚠️ Почему симлинки всё равно ПЛОСКИЕ

Claude Code **не сканирует `~/.claude/skills` вглубь**: скил обязан быть папкой
первого уровня, и имя папки — это имя команды. Поэтому вложенность живёт только
здесь, в репозитории, а в `~/.claude/skills` лежат плоские симлинки, каждый
указывает внутрь своей проектной папки:

```
~/.claude/skills/tavern-game -> .../claude-skills/tavern/tavern-game
~/.claude/skills/crash-games -> .../claude-skills/crash-heroes/crash-games
```

Отсюда два правила:

1. **Переносишь скил в другую проектную папку — обязательно перелинкуй.** Иначе
   симлинк повиснет и скил молча пропадёт из сессий, без всякой ошибки.
2. **Внутри скилов пути пишутся через `~/.claude/skills/<имя>/`**, а не через
   путь в репозитории. Все зонды так и написаны, поэтому перекладка папок их не
   ломает.

## Перед коммитом

```bash
cp tavern/tavern-regress/probes/pre-commit.sh .git/hooks/pre-commit
```

Хук гоняет `bugs.py --lint` (красное останавливает коммит) и печатает здоровье
доменных файлов.

## Как подключить на новой машине

Диск exFAT — симлинки НА нём создавать нельзя, но симлинки С домашней папки НА
него работают.

```bash
R=/media/<user>/T714/claude-skills
mkdir -p ~/.claude/skills
for s in tavern-game tavern-cooking tavern-regress tavern-ideas tavern-refactor; do
  ln -sfn $R/tavern/$s ~/.claude/skills/$s
done
ln -sfn $R/crash-heroes/crash-games   ~/.claude/skills/crash-games
ln -sfn $R/lucky/lucky-infra          ~/.claude/skills/lucky-infra
ln -sfn $R/poker/poker-infra          ~/.claude/skills/poker-infra
ln -sfn $R/personal/shinobi-council   ~/.claude/skills/shinobi-council
```

Замени `<user>` на своё имя пользователя. Точка монтирования может отличаться —
проверь `df -h` или `lsblk`. На macOS диск обычно в `/Volumes/T714`, в WSL — в
`/mnt/<буква>`.

## Проверка

```bash
for l in ~/.claude/skills/*; do
  [ -f "$l/SKILL.md" ] && echo "ok   $(basename $l)" || echo "БИТО $(basename $l)"
done
```

Все строки `ok` — Claude Code увидит скилы. `БИТО` значит, что симлинк указывает
в никуда: чаще всего скил переехал в другую проектную папку, реже — не подключён
диск.

## Если переехал на машину без диска

Симлинк «висит» (broken). Claude Code просто не загрузит скил, ошибки не будет.
Подключи диск — и снова работает.

## История

- **2026-09-07** — разложено по проектным папкам, до этого всё лежало плоско в
  корне. Тогда же удалены `debug-panel`, `admin-ui`, `vitriny-tz` — по решению
  Ильи; восстановимы из истории git.
