"""Цикл проверки правок в редакторе одной командой (Илья 01.09 разрешил сессиям самим stop/play).

python3 cycle.py status            play / compiling / текущий и стартовый уровень
python3 cycle.py stop [--force]    выйти из play (уровень запоминается); откажет, если живой уровень разошёлся с файлом
python3 cycle.py compile           refresh + компиляция, ждать готовности, показать ошибки консоли
python3 cycle.py tests             EditMode-тесты (только вне play), красные — списком
python3 cycle.py play              войти в play и вернуть уровень, который был при stop
                                   ⛔ АРГУМЕНТ-УРОВЕНЬ ЗАПРЕЩЁН (Илья 15.09): уровень в редакторе
                                   один на всех и принадлежит ему, сессия его не меняет (инвариант 184)
python3 cycle.py probes            живые пробы: invariants_play, level_roundtrip, reach_probe, slot_gate_probe, kitchen_rules_probe, sink_wash_probe, drink_button_probe
python3 cycle.py all [уровень]     stop → compile → tests → play → probes; код 1, если что-то красное

Перед stop предупредить соседей (SESSIONS.md): у них может идти проба в play.
"""
import json, subprocess, sys, time, pathlib

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
REG = pathlib.Path.home() / '.claude/skills/tavern-regress/probes'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
STATE = REG / '.cycle_level'
GAME_SCENE = 'Assets/Scenes/level1.unity'


def mcp(tool, payload):
    out = subprocess.run(['python3', MCP, tool, json.dumps(payload)], capture_output=True, text=True,
                         timeout=600, cwd=PROJECT)
    text = out.stdout.strip()
    line = text.splitlines()[-1] if text else '{}'
    try:
        return json.loads(line)
    except Exception:
        return {'raw': text[-400:]}


def run(code):
    d = mcp('execute_code', {"action": "execute", "code": code})
    return (d.get('data') or {}).get('result') if isinstance(d, dict) else None


def state():
    res = run('return UnityEngine.Application.isPlaying + "|" + UnityEditor.EditorApplication.isCompiling'
              ' + "|" + Cozy.Grid.LevelIO.CurrentLevelName + "|" + UnityEditor.EditorApplication.isPaused;')
    if not res or '|' not in str(res):
        return None, None, None, None
    p, c, lvl, paused = (str(res).split('|') + ['', '', '', ''])[:4]
    return p.lower().startswith('t'), c.lower().startswith('t'), lvl, paused.lower().startswith('t')


def wait_state(play=None, compiling=False, seconds=120):
    for _ in range(seconds // 2):
        p, c, _, _ = state()
        if p is not None and (play is None or p == play) and c == compiling:
            return True
        time.sleep(2)
    return False


def cmd_status():
    p, c, lvl, paused = state()
    if p is None:
        print('мост не отвечает'); return False
    start = run('return Cozy.Grid.LevelIO.DevDefaultLevel;') or ''
    line = f'play={p} compiling={c} уровень={lvl or "—"} стартовый={start or "—"}'
    if paused:
        line += ' ПАУЗА РЕДАКТОРА'
    if start and lvl and start != lvl:
        line += ' ⚠ стартовый и текущий разошлись'
    print(line)
    return True


def unsaved():
    code = (REG / 'unsaved_check.cs').read_text(encoding='utf-8')
    res = str(run(code) or 'НЕ СОХРАНЕНО: проба не ответила')
    return None if res.startswith('СОХРАНЕНО') else res


def cmd_stop():
    p, c, lvl, _ = state()
    if p is None:
        print('мост не отвечает'); return False
    if lvl:
        STATE.write_text(lvl)
    if not p:
        print('уже не в play'); return True
    diff = unsaved()
    if diff and '--force' not in sys.argv:
        print('stop: ОТКАЗ — ' + diff + ' (P843: несохранённое у Ильи пропадёт; сохранить уровень или --force)')
        return False
    mcp('manage_editor', {"action": "stop"})
    ok = wait_state(play=False, seconds=60)
    print('stop:', 'ок' if ok else 'не дождался выхода из play')
    return ok


def cmd_compile():
    mcp('refresh_unity', {"mode": "force", "scope": "all", "compile": "request", "wait_for_ready": True})
    ok = wait_state(play=False, compiling=False, seconds=240)
    errs = mcp('read_console', {"action": "get", "types": ["error"], "count": 20})
    data = errs.get('data') if isinstance(errs, dict) else None
    items = data if isinstance(data, list) else ((data or {}).get('items') or (data or {}).get('messages') or [])
    comp = [m for m in items if 'error CS' in json.dumps(m, ensure_ascii=False)]
    print('компиляция:', 'готово' if ok else 'не дождался', f'| ошибок CS в консоли: {len(comp)}')
    for m in comp[:10]:
        print('   ', json.dumps(m, ensure_ascii=False)[:200])
    return ok and not comp


def cmd_tests():
    p, c, _, _ = state()
    if p:
        print('тесты: редактор в play, сначала stop'); return None
    started = mcp('run_tests', {"mode": "EditMode"})
    job = (started.get('data') or {}).get('job_id') if isinstance(started, dict) else None
    if not job:
        print('тесты: не стартовали —', json.dumps(started, ensure_ascii=False)[:300]); return None
    for _ in range(30):
        d = (mcp('get_test_job', {"job_id": job, "include_failed_tests": True, "wait_timeout": 30}).get('data') or {})
        status = d.get('status')
        if status in ('succeeded', 'completed', 'failed'):
            prog = d.get('progress') or {}
            fails = prog.get('failures_so_far') or []
            done = prog.get('completed')
            if status == 'failed' and not fails and not done:
                print('тесты: не запустились —', d.get('error')); return None
            print(f'тесты: {done} прогнано, красных {len(fails)}')
            for f in fails:
                print('   ПРОВАЛ:', f.get('full_name'))
                print('      ', str(f.get('message', ''))[:200].replace('\n', ' '))
            ensure_game_scene()
            return not fails
    print('тесты: не дождался результата'); return None


def active_scene():
    return run('return UnityEngine.SceneManagement.SceneManager.GetActiveScene().path;') or ''


def ensure_game_scene():
    for _ in range(30):
        if active_scene() == GAME_SCENE:
            return True
        time.sleep(2)
    p, c, _, _ = state()
    if p:
        print('сцена: в play открыта не игровая сцена — сначала stop'); return False
    res = run('var sc = UnityEditor.SceneManagement.EditorSceneManager.OpenScene("%s"); return sc.path;' % GAME_SCENE)
    ok = res == GAME_SCENE
    print('сцена: открыта', GAME_SCENE if ok else f'НЕ открылась ({res})')
    return ok


def resume():
    """Снять паузу редактора и убедиться, что кадры идут.

    Прогон тестов оставляет редактор на паузе, и живая проба в таком мире
    молча меряет замерший кадр: числа выглядят как регрессия правки (P405).
    """
    run('UnityEditor.EditorApplication.isPaused = false; return "снял";')
    first = run('return Time.frameCount;')
    time.sleep(1)
    second = run('return Time.frameCount;')
    try:
        return int(second) > int(first)
    except (TypeError, ValueError):
        return False


def cmd_play(level=None):
    """Войти в play и НЕ ТРОГАТЬ УРОВЕНЬ.

    ⛔ Сессия уровень в редакторе не меняет — он один на все сессии и
    принадлежит Илье (инвариант 184, P422). Раньше `play` грузил уровень,
    запомненный при `stop`, и этого хватало, чтобы подменить чужой: память
    протухала, и лес сменялся полигоном атаки. Уровень поднимает сам редактор
    авто-загрузкой.
    """
    if level:
        print('play: уровень аргументом ЗАПРЕЩЁН — «%s» не загружаю (инвариант 184).' % level)
        print('      Нужен другой уровень для проверки — попроси Илью, не переключай сам.')
    p, c, _, _ = state()
    if not p:
        if not ensure_game_scene():
            return False
        mcp('manage_editor', {"action": "play"})
        if not wait_state(play=True, seconds=90):
            print('play: не дождался входа'); return False
        time.sleep(3)
    if not resume():
        print('play: КРАСНОЕ — кадры не идут, мир заморожен'); return False
    alive = run('return (Cozy.Grid.GridCursor.I != null) + "|" + (Cozy.Grid.PlayerRef.GameObject != null);')
    if str(alive) != 'True|True':
        print('play: КРАСНОЕ — нет GridCursor или игрока (сцена ' + active_scene() + ')'); return False
    print('play: вошли, уровень редактора:', state()[2] or '—', '(не трогал)')
    return True


def cmd_probes(level=None):
    ok = True
    if not resume():
        print('пробы: КРАСНОЕ — кадры не идут, мир заморожен'); return False
    before = state()[2]
    for name in ('invariants_play.py', 'level_roundtrip.py', 'reach_probe.py', 'slot_gate_probe.py', 'kitchen_rules_probe.py', 'sink_wash_probe.py', 'sink_rim_probe.py', 'drink_button_probe.py', 'drape_probe.py'):
        out = subprocess.run(['python3', str(REG / name)], capture_output=True, text=True, timeout=300, cwd=PROJECT)
        tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
        last = tail[-1] if tail else 'нет ответа'
        print(name + ':', last[:220])
        if 'КРАСНОЕ' in last or 'сдвиг' in last.lower() or 'потер' in last.lower() or 'объектов=0' in last:
            print('    КРАСНОЕ: мир пустой или проба не дошла до объектов'); ok = False
    after = state()[2]
    want = level or before
    if want and after != want:
        print(f'    КРАСНОЕ: текущий уровень после проб «{after}», ожидался «{want}» — проба подменила уровень'); ok = False
    return ok


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else 'status'
    lvl = sys.argv[2] if len(sys.argv) > 2 else None
    if arg == 'status':
        sys.exit(0 if cmd_status() else 1)
    if arg == 'stop':
        sys.exit(0 if cmd_stop() else 1)
    if arg == 'compile':
        sys.exit(0 if cmd_compile() else 1)
    if arg == 'tests':
        r = cmd_tests(); sys.exit(0 if r else 1)
    if arg == 'play':
        sys.exit(0 if cmd_play(lvl) else 1)
    if arg == 'probes':
        sys.exit(0 if cmd_probes(lvl) else 1)
    if arg == 'all':
        ok = cmd_stop() and cmd_compile()
        t = cmd_tests() if ok else None
        ok = ok and (t is not False)
        ok = cmd_play(lvl) and ok
        ok = cmd_probes(lvl) and ok
        print('=== итог:', 'зелёное' if ok else 'КРАСНОЕ')
        sys.exit(0 if ok else 1)
    print(__doc__)


if __name__ == '__main__':
    main()
