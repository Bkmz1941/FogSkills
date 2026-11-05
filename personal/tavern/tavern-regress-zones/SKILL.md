---
name: tavern-regress-zones
description: РЕГРЕСС ЗОН «Таверны» — зоны и их маркеры-точки: размер маркера, соседство, имена точек, перенос зажатием, стрелка направления (R), захват маркера ниже поверхности зоны, сохранение в уровне; подзоны в правилах существ ([while player in], [player left], [sees player touching in], [hears player in], [tense talk in]), охрана подзоны после реакции и разговора, точки в шагах ([go]/[unfold]/[put back]/[sit] по имени и стрелке). Отдельный скил по слову Ильи 05.11 («и для зон отдельный регресс скил»). Активируй ПЕРЕД и ПОСЛЕ правки `ZonePiece*.cs`, `GridCursor.Zones.cs`, `HudUI.Zones.cs`, `LevelIO` (ZoneData/MarkData), `LifeRules.Talk.cs` (подзоны), `CreaturePlan` (Spot/SpotYaw); на «маркер не двигается», «маркер не ставится», «стрелка», «зона», «подзона», «он ушёл из ларька». Общий регресс — tavern-regress; общение — tavern-regress-talk.
---

# Регресс зон и маркеров

Заведён 05.11. Кейсы — `CASES.md` (коды ZN-…), тесты — `Assets/Tests/EditMode/ZoneMarksTests.cs` (+ `ZoneKindCanonTests`, `LifeRulesParseTests` для подзон).

## Как гонять

1. **Тесты:** редактор вне play → `python3 ~/.claude/skills/tavern-regress/probes/cycle.py compile` → `cycle.py tests` (классы `ZoneMarksTests`, `ZoneKindCanonTests`). Пока Илья в play с несохранённым — не останавливать, только `offline_build.py`.
2. **Play (⏳ в CASES):** через `mcp_call.py execute_code`: зона `ZonePiece.All.First(z => z.DisplaySlug == "monster_zone_1")`, `MarkList()`, `MarkCell`, `MarkYaw`, `MarkUnder`; уровень в файле — `~/.config/unity3d/DefaultCompany/Tavern/levels/<уровень>.json`, `zones[].marks[]` (`n`, `at`, `nrm`, `name`, `yaw`).
3. **Правка файла уровня руками** — только с копией `*.bak-…` и текстом (отступы 4, без пересохранения всего файла); в play живое состояние правится отдельно (`RenameMark`, `AddMark`), иначе сохранение уровня Ильёй затрёт.

## Что важно знать

- `ZonePiece.MarkShare` = 0,3 клетки (3 м): круг 0,9 м, соседний маркер ближе 0,45 м не ставится (`MarkNear`). До 05.11 было 0,6 — `AddMark` молча отказывал ближе 0,9 м.
- `MarkNear` сверяет ЭТАЖ, `MarkUnder` — нет (в пределах клетки по высоте): для захвата курсором и в режиме «Маркеры».
- Стрелка: `Mark.yaw` (−1 — нет), `TurnMark` шагом `MarkTurnStep` 45°, в файле `MarkData.yaw` (старые файлы без поля — −1).
- Охрана подзоны: `LifeRules._guarding` — застал героя в подзоне (увидел, одёрнул, говорил) → `[while player in]` держится без зрения до выхода.
