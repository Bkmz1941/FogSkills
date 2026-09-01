"""Цикл проверки правок в редакторе одной командой (Илья 01.09 разрешил сессиям самим stop/play).

python3 cycle.py status            play / compiling / текущий уровень
python3 cycle.py stop              выйти из play (уровень запоминается)
python3 cycle.py compile           refresh + компиляция, ждать готовности, показать ошибки консоли
python3 cycle.py tests             EditMode-тесты (только вне play), красные — списком
python3 cycle.py play [уровень]    войти в play и вернуть уровень (по умолчанию тот, что был при stop)
python3 cycle.py probes            живые пробы: invariants_play, level_roundtrip
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
    res = run('return UnityEngine.Application.isPlaying + "|" + UnityEditor.EditorApplication.isCompiling + "|" + Cozy.Grid.LevelIO.CurrentLevelName;')
    if not res or '|' not in str(res):
        return None, None, None
    p, c, lvl = (str(res).split('|') + ['', '', ''])[:3]
    return p.lower().startswith('t'), c.lower().startswith('t'), lvl


def wait_state(play=None, compiling=False, seconds=120):
    for _ in range(seconds // 2):
        p, c, _ = state()
        if p is not None and (play is None or p == play) and c == compiling:
            return True
        time.sleep(2)
    return False


def cmd_status():
    p, c, lvl = state()
    if p is None:
        print('мост не отвечает'); return False
    print(f'play={p} compiling={c} уровень={lvl or "—"}')
    return True


def cmd_stop():
    p, c, lvl = state()
    if p is None:
        print('мост не отвечает'); return False
    if lvl:
        STATE.write_text(lvl)
    if not p:
        print('уже не в play'); return True
    mcp('manage_editor', {"action": "stop"})
    ok = wait_state(play=False, seconds=60)
    print('stop:', 'ок' if ok else 'не дождался выхода из play')
    return ok


def cmd_compile():
    mcp('refresh_unity', {"mode": "force", "scope": "scripts", "compile": "request", "wait_for_ready": True})
    ok = wait_state(play=False, compiling=False, seconds=240)
    errs = mcp('read_console', {"action": "get", "types": ["error"], "count": 20})
    data = errs.get('data') if isinstance(errs, dict) else None
    items = (data or {}).get('items') or (data or {}).get('messages') or []
    comp = [m for m in items if 'error CS' in json.dumps(m, ensure_ascii=False)]
    print('компиляция:', 'готово' if ok else 'не дождался', f'| ошибок CS в консоли: {len(comp)}')
    for m in comp[:10]:
        print('   ', json.dumps(m, ensure_ascii=False)[:200])
    return ok and not comp


def cmd_tests():
    p, c, _ = state()
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
    p, c, _ = state()
    if p:
        print('сцена: в play открыта не игровая сцена — сначала stop'); return False
    res = run('var sc = UnityEditor.SceneManagement.EditorSceneManager.OpenScene("%s"); return sc.path;' % GAME_SCENE)
    ok = res == GAME_SCENE
    print('сцена: открыта', GAME_SCENE if ok else f'НЕ открылась ({res})')
    return ok


def cmd_play(level=None):
    level = level or (STATE.read_text().strip() if STATE.exists() else '')
    p, c, _ = state()
    if not p:
        if not ensure_game_scene():
            return False
        mcp('manage_editor', {"action": "play"})
        if not wait_state(play=True, seconds=90):
            print('play: не дождался входа'); return False
        time.sleep(3)
    alive = run('return (Cozy.Grid.GridCursor.I != null) + "|" + (Cozy.Grid.PlayerRef.GameObject != null);')
    if str(alive) != 'True|True':
        print('play: КРАСНОЕ — нет GridCursor или игрока (сцена ' + active_scene() + ')'); return False
    if level:
        res = run('var d = Cozy.Grid.LevelIO.Load("%s"); if (d == null) return "нет уровня"; Cozy.Grid.GridCursor.I.RestoreLevel(d); return "загружен " + Cozy.Grid.LevelIO.CurrentLevelName;' % level)
        print('play: вошли, уровень:', res)
    else:
        print('play: вошли (уровень не задан)')
    return True


def cmd_probes():
    ok = True
    for name in ('invariants_play.py', 'level_roundtrip.py'):
        out = subprocess.run(['python3', str(REG / name)], capture_output=True, text=True, timeout=300, cwd=PROJECT)
        tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
        last = tail[-1] if tail else 'нет ответа'
        print(name + ':', last[:220])
        if 'КРАСНОЕ' in last or 'сдвиг' in last.lower() or 'потер' in last.lower() or 'объектов=0' in last:
            print('    КРАСНОЕ: мир пустой или проба не дошла до объектов'); ok = False
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
        sys.exit(0 if cmd_probes() else 1)
    if arg == 'all':
        ok = cmd_stop() and cmd_compile()
        t = cmd_tests() if ok else None
        ok = ok and (t is not False)
        ok = cmd_play(lvl) and ok
        ok = cmd_probes() and ok
        print('=== итог:', 'зелёное' if ok else 'КРАСНОЕ')
        sys.exit(0 if ok else 1)
    print(__doc__)


if __name__ == '__main__':
    main()
