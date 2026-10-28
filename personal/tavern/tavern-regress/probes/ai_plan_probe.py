#!/usr/bin/env python3
"""Проба исполнителя планов существ (CreaturePlan) БЕЗ модели — в play.

python3 ai_plan_probe.py [зона] [--keep]

План подаётся прямо в CreaturePlan.Run (то, что пульт делает после ответа
модели): appear в маркер A → go к маркеру B → wait 1 с → vanish. Ждёт до 90 с
и сверяет: существо появилось у маркера A, дошло до B (в 1,5 м), исчезло.
Второй случай — план поверх плана: пока идёт к B, подать «wait 2 с» — Describe
обязан сказать «(потом вернётся к плану …)», после — продолжить к B.

Зона — любая зона монстров с ≥ 2 клетками (по умолчанию первая с маркерами
или sectant_zone_1); маркеры пробы ставятся временно (номера 91/92) и снимаются
в finally. Существо probe_sectant удаляется в finally. Код 1 — красное.
На время пробы «думает каждые» = 0 (модель не вмешивается), после — возвращается.
Защита P987 (ночь 08.10, ilya-f7).
"""
import json, pathlib, subprocess, sys, time

MCP = pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
WHO = 'probe_sectant'
MA, MB = 91, 92  # свои номера, если у автора в зоне нет двух маркеров


def run(code):
    out = subprocess.run(['python3', str(MCP), 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
    except Exception:
        raise SystemExit('мост не ответил: ' + out.stdout[-500:])
    if not d.get('success'):
        raise SystemExit('ОШИБКА моста: ' + json.dumps(d, ensure_ascii=False)[:1200])
    return (d.get('data') or {}).get('result')


def cs(s):
    return json.dumps(s, ensure_ascii=False)


def pick_zone(wanted):
    code = ('var best = (Cozy.Grid.ZonePiece)null; foreach (var z in Cozy.Grid.ZonePiece.All) { if (z == null || !Cozy.Grid.ZonePiece.IsCreatures(z.kind) || z.Cells.Count < 2) continue; '
            'if (%s.Length > 0 && z.DisplaySlug == %s) return z.DisplaySlug; if (best == null || z.Cells.Count > best.Cells.Count) best = z; } '
            'return best == null ? "" : best.DisplaySlug;') % (cs(wanted), cs(wanted))
    return run(code)


def set_marks(zone):
    """Два маркера пробы: если в зоне уже есть ≥ 2 маркера автора — берём два самых
    далёких из них (AddMark не ставит второй маркер на занятую клетку); иначе ставим
    свои 91/92 на первую клетку и самую дальнюю от неё. Возвращает (A, B, описание)."""
    code = ('var z = Cozy.Grid.ZonePiece.BySlug(%s); var ms = z.Marks; if (ms.Count >= 2) { int ia = 0, ib = 1; float best = -1f; for (int i = 0; i < ms.Count; i++) for (int j = i + 1; j < ms.Count; j++) { float d = (ms[i].cell - ms[j].cell).sqrMagnitude; if (d > best) { best = d; ia = i; ib = j; } } '
            'return ms[ia].number + "," + ms[ib].number + "|" + Mathf.Sqrt(best).ToString("0.0") + " м, маркеры автора"; } '
            'var a = z.Cells[0]; var b = a; float bd = -1f; foreach (var c in z.Cells) { float d = (c - a).sqrMagnitude; if (d > bd) { bd = d; b = c; } } '
            'z.RemoveMark(%d); z.RemoveMark(%d); z.AddMark(%d, a); z.AddMark(%d, b); return "%d,%d|" + Mathf.Sqrt(bd).ToString("0.0") + " м, свои";') % (cs(zone), MA, MB, MA, MB, MA, MB)
    r = run(code)
    nums, note = r.split('|', 1)
    a, b = (int(x) for x in nums.split(','))
    return a, b, note


def start_plan(zone, ma, mb):
    code = (''
            'var steps = new Cozy.Life.PlanStep[] { new Cozy.Life.PlanStep { @do = "appear", zone = %s, mark = %d }, new Cozy.Life.PlanStep { @do = "go", zone = %s, mark = %d, run = false }, new Cozy.Life.PlanStep { @do = "wait", seconds = 1f }, new Cozy.Life.PlanStep { @do = "vanish", mode = "now" } }; '
            'return "run: " + Cozy.Life.CreaturePlan.Run(%s, steps, false);') % (cs(zone), ma, cs(zone), mb, cs(WHO))
    return run(code)


def push_wait():
    code = ('var steps = new Cozy.Life.PlanStep[] { new Cozy.Life.PlanStep { @do = "wait", seconds = 2f } }; '
            'return "run2: " + Cozy.Life.CreaturePlan.Run(%s, steps, false);') % cs(WHO)
    return run(code)


def state(mb):
    code = ('var io = Cozy.Grid.InteractiveObject.BySlug(%s); if (io == null) return "нет"; var z = Cozy.Grid.ZonePiece.BySlug(%s); Vector3 b; z.MarkCell(%d, out b); '
            'return io.transform.position.ToString("0.0") + " | до B " + Vector3.Distance(io.transform.position, b).ToString("0.0") + " | " + Cozy.Life.CreaturePlan.Describe(io);')
    return lambda zone: run(code % (cs(WHO), cs(zone), mb))


def cleanup(zone, own):
    run(('var io = Cozy.Grid.InteractiveObject.BySlug(%s); if (io != null) { Cozy.Grid.LevelIO.Unsaved.Remove(io); UnityEngine.Object.Destroy(io.gameObject); } '
         'var z = Cozy.Grid.ZonePiece.BySlug(%s); if (z != null && %s) { z.RemoveMark(%d); z.RemoveMark(%d); } return "clean";') % (cs(WHO), cs(zone), 'true' if own else 'false', MA, MB))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    keep = '--keep' in sys.argv
    zone = pick_zone(args[0] if args else 'sectant_zone_1')
    if not zone:
        print('КРАСНОЕ: нет зоны монстров с клетками'); return 1
    red = []
    own = False
    think = run('float t = Cozy.Creatures.Sectant.ThinkSeconds; Cozy.Creatures.Sectant.ThinkSeconds = 0f; return t.ToString(System.Globalization.CultureInfo.InvariantCulture);')
    try:
        ma, mb, note = set_marks(zone)
        own = ma == MA
        st = state(mb)
        print('зона', zone, '| маркеры', ma, mb, note)
        r = start_plan(zone, ma, mb)
        print(r)
        if r != 'run: ':
            red.append('план не принят: ' + str(r))
            return 1
        appeared = walked = stacked = vanished = False
        t0 = time.time()
        while time.time() - t0 < 90:
            s = st(zone)
            print('%5.1f с  %s' % (time.time() - t0, s))
            if s == 'нет':
                if appeared:
                    vanished = True; break
            else:
                appeared = True
                if 'идёт к маркеру %d' % mb in s and not stacked and time.time() - t0 > 2:
                    print(push_wait())
                    stacked = True
                    s2 = st(zone)
                    print('   после плана поверх:', s2)
                    if 'потом вернётся' not in s2:
                        red.append('план поверх плана не встал в стек: ' + s2)
                if 'стоит' in s or 'до B 0.' in s or 'до B 1.' in s:
                    walked = True
            time.sleep(1.0)
        if not appeared: red.append('существо не появилось')
        if not walked: red.append('не дошло до маркера B')
        if not vanished: red.append('не исчезло за 90 с')
    finally:
        run('Cozy.Creatures.Sectant.ThinkSeconds = %sf; return "think back";' % think)
        if not keep:
            cleanup(zone, own)
    if red:
        print('КРАСНОЕ:', '; '.join(red)); return 1
    print('ЗЕЛЁНОЕ: appear → go → стек → wait → vanish'); return 0


if __name__ == '__main__':
    sys.exit(main())
