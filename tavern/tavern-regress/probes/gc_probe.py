"""Мусор и ВРЕМЯ кадра: базовый замер и A/B-скан по «тикающим» типам (в play, редактор свой).

python3 gc_probe.py                 базовый замер: мусор (среднее, пик) и кадр (мс среднее, p95, пик) за 120 кадров
python3 gc_probe.py scan [кадров]   выключать типы с Update/LateUpdate/FixedUpdate по одному и мерить дельту мусора и мс
Потолка кадров в игре с 10.09 нет (FrameRateConfig: targetFrameRate = -1, Илья: «давай снимем»),
замер это подтверждает явно: при потолке «Main Thread» мерил бы ожидание, а не работу.
Пробник живёт в игре: Assets/Modules/Grid/GcProbe.cs (Begin/Result/ListTicking/SetEnabled).
Между выключением и замером ждётся окно кадров; каждый тип включается обратно в finally.
"""
import json, subprocess, sys, time, pathlib

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line); return (d.get('data') or {}).get('result') or d.get('message')
    except Exception:
        return out.stdout[-200:]


def measure(frames):
    run('Cozy.Grid.GcProbe.Begin(%d); return "ok";' % frames)
    time.sleep(frames / 60.0 + 1.0)
    for _ in range(20):
        res = run('return Cozy.Grid.GcProbe.Result;')
        if res and str(res).startswith('avg='):
            parts = dict(p.split('=') for p in str(res).split())
            return int(parts['avg']), int(parts['max']), float(parts.get('ms', 0)), float(parts.get('p95', 0))
        time.sleep(1)
    return None, None, None, None


def uncap(on):
    run('UnityEngine.Application.targetFrameRate = -1; return "ok";')


def main():
    if not str(run('return UnityEngine.Application.isPlaying;')).lower().startswith('true'):
        print('не в play'); sys.exit(1)
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    uncap(True)
    try:
        if len(sys.argv) < 2 or sys.argv[1] != 'scan':
            avg, mx, ms, p95 = measure(frames)
            print(f'мусор на кадр: среднее {avg} Б, пик {mx} Б; кадр: {ms:.2f} мс среднее, p95 {p95:.2f} мс ({frames} кадров, без потолка)')
            return
        types = [t for t in str(run('return Cozy.Grid.GcProbe.ListTicking();')).split(';') if t]
        print(f'тикающих типов: {len(types)}')
        base, _, bms, _ = measure(frames)
        base2, _, bms2, _ = measure(frames)
        print(f'база: {base} Б/кадр, {bms:.2f} мс (повтор {base2} Б, {bms2:.2f} мс)')
        bms = (bms + bms2) / 2
        rows = []
        for t in types:
            name, cnt = t.split(':')
            try:
                run('return Cozy.Grid.GcProbe.SetEnabled("%s", false);' % name)
                time.sleep(0.5)
                avg, mx, ms, p95 = measure(frames)
            finally:
                run('return Cozy.Grid.GcProbe.SetEnabled("%s", true);' % name)
            if avg is None:
                continue
            rows.append((bms - ms, base - avg, name, cnt, avg, ms))
            print(f'  {name} ×{cnt}: без него {ms:.2f} мс (дельта {bms - ms:+.2f} мс), {avg} Б/кадр (дельта {base - avg:+d})')
        rows.sort(reverse=True)
        print('=== главные источники (дельта к базе, мс за кадр) ===')
        for dms, d, name, cnt, avg, ms in rows[:15]:
            print(f'{dms:+7.2f} мс {d:+8d} Б  {name} ×{cnt}')
    finally:
        uncap(False)


if __name__ == '__main__':
    main()
