---
name: tavern-regress-life
description: РЕГРЕСС ДЕЙСТВИЙ ЛЮДЕЙ «Таверны» (имитация жизни правилами, с 05.11) — круг дел и возврат в круг, группы по времени ([at 09:30] еда, [at 21:00] ночлег), сесть/есть/пить, раскладушка и сон с клипами кровати, пробуждение шумом и светом, выключатель/генератор/шкаф, двери ключом (запереть за собой, клип ключа), [look] перед делом и стрелки маркеров, проблемы-модификатор (швабра), занятое место/помеха на пути, кадр (fps) новых механик. Отдельный скил по слову Ильи 05.11 («запиши всё в скил + регресс», «упор и тесты на фпс от новых механик»). Активируй ПЕРЕД и ПОСЛЕ правки `CreaturePlan*.cs`, `CreatureLoopAct.cs`, `CreatureFood.cs`, `CreatureMop.cs`, `CreatureSmoke.cs`, `LifeRules*.cs` (не общение), `Behavior/*.txt`; на «Валера не садится», «не спит», «не закрыл дверь», «стоит и не идёт», «застрял», «тормозит Валера». Общение — tavern-regress-talk, зоны и маркеры — tavern-regress-zones, общий — tavern-regress.
---

# Регресс действий людей

Заведён 05.11 (ночь). Кейсы — `CASES.md` (коды LF-…). Домен — `tavern-life` (`ACTIONS_PAUSE.md` — журнал захода 04–05.11, `LIFE.md` §0), правила Валеры — `~/Documents/Fog/Behavior/valera.txt` (правка — всегда и в файле, и в игре: `behavior_apply.py valera`).

## Как гонять

1. **Тесты:** редактор вне play → `python3 ~/.claude/skills/tavern-regress/probes/cycle.py compile` → `cycle.py tests` (классы `LifeRulesParseTests`, `LifeActionsTests`, `SeatsAndBedsTests`). Илья в play с несохранённым — НЕ останавливать (cycle.py stop откажет, `--force` не использовать), только `offline_build.py`.
2. **Разбор правил Валеры:** `behavior_apply.py valera --check` (или раздел «Скрипты людей» F1 → ИИ): 0 непонятых строк.
3. **Play:** `mcp_call.py execute_code` — `CreaturePlan.Of(go)`/`Current`, `Step`, `Index`, `_stack.Count`; часы — `Weather.Hour` (скачок часов будит группы `[at …]`, после — вернуть всё, что сдвинулось: раскладушку, дверь).
4. **Кадр:** `python3 ~/.claude/skills/tavern-regress/probes/life_fps_probe.py` — в play, через ~60 с после входа (уровень догружается): пороги self-мс и мусора на кадр по маркерам `LifeRulesRunner`, `CreaturePlan`, `SpeechBubbles`; код 1 — превышен. Группа LF-F.
5. **Разбор правил:** `rules_fp.py <out>` до и после правки `LifeRules.Parse*.cs` / `LifeRules.Talk.cs` — снимок посимвольно (в корпусе и скрипты `~/Documents/Fog/Behavior/*.txt`); нужна `offline_build.py`.
6. **Общение живьём:** `talk_probe.cs` (через `mcp_call.py execute_code`) — ~30 кейсов TK, гонять дважды подряд (второй прогон ловит «Опять вы?» после «Стереть»).

⚠️ НЕ запускать `debug_panel_probe.py snap` на «Котедж 104» (57 тыс. объектов): 05.11 редактор убит OOM (P1316); теперь проба сама отказывает > 20 тыс. объектов.

## Что важно знать

- `ResetStep` зовётся на КАЖДОМ `Next` — вставание с места только при прерывании (шаг не `KeepsSeat`).
- Реакции глобальной группы `[valera_1]:` срабатывают только на базовом плане (`Outranks`): поверх пробного плана их нет.
- Круг после прерывания продолжается с того же шага (`_loopAt`), группы `[at HH:MM]` — один раз при переходе через время.
- Жесты с позой (`PosedStep`: work, pick floor, smoke, eat/drink стоя) начинаются лицом к месту последнего `[look]` (≤ 5 м) или по стрелке маркера.
