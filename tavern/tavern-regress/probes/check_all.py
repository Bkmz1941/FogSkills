"""Один прогон: линт граблей, компиляция, тесты EditMode, живые пробы (инварианты, крит-сценарий «положить», круг сейва, позы, наклон, кадр). Печатает вердикт.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/check_all.py
"""
import json, subprocess, sys, time

GAME = '/home/ilya/.claude/skills/tavern-game'
REG = '/home/ilya/.claude/skills/tavern-regress'
MCP = GAME + '/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'


def mcp(tool, payload):
    out = subprocess.run(['python3', MCP, tool, json.dumps(payload)],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        return json.loads(line)
    except Exception:
        return {}


def editor_state():
    d = mcp('execute_code', {"action": "execute", "code":
            'return UnityEngine.Application.isPlaying + "|" + UnityEditor.EditorApplication.isCompiling;'})
    res = (d.get('data') or {}).get('result') or '|'
    play, comp = (res.split('|') + ['', ''])[:2]
    return play.lower().startswith('t'), comp.lower().startswith('t')


def lint():
    out = subprocess.run(['python3', REG + '/probes/bugs.py', '--lint'],
                         capture_output=True, text=True, timeout=60)
    tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
    print('грабли:', tail[-1] if tail else 'нет ответа')
    for line in tail:
        if 'КРАСНОЕ' in line:
            print('   ', line.strip())
    return out.returncode == 0


def probes_lint():
    out = subprocess.run(['python3', REG + '/probes/probes_lint.py'], capture_output=True, text=True, timeout=60)
    lines = [l for l in out.stdout.strip().split('\n') if l.strip()]
    print('ссылки проб:', lines[-1] if lines else 'нет ответа')
    for line in lines[:-1]:
        print('   ', line[:300])
    return out.returncode == 0


def compile_check():
    out = subprocess.run(['python3', PROJECT + '/compile_check.py'],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    ok = 'КОМПИЛЯЦИЯ ЧИСТАЯ' in out.stdout
    print('компиляция:', 'чисто' if ok else 'ОШИБКИ')
    if not ok:
        for line in out.stdout.split('\n'):
            if 'FAIL' in line or 'error CS' in line:
                print('   ', line.strip()[:150])
    return ok


def tests():
    started = mcp('run_tests', {"mode": "EditMode"})
    job = (started.get('data') or {}).get('job_id')
    if not job:
        print('тесты: не стартовали —', (started.get('data') or {}).get('error') or started.get('message'))
        return None
    for _ in range(40):
        time.sleep(6)
        d = (mcp('get_test_job', {"job_id": job, "include_failed_tests": True}).get('data') or {})
        status = d.get('status')
        if status in ('succeeded', 'completed', 'failed'):
            fails = (d.get('progress') or {}).get('failures_so_far') or []
            done = (d.get('progress') or {}).get('completed')
            if status == 'failed' and not fails:
                print('тесты: не запустились —', d.get('error'))
                return None
            print(f'тесты: {done} прогнано, красных {len(fails)}')
            for f in fails:
                print('   ПРОВАЛ:', f['full_name'])
                print('      ', f['message'][:160].replace('\n', ' '))
            return not fails
    print('тесты: не дождался результата')
    return None


def restore_scene():
    """Тест-раннер уводит редактор на свою БЕЗЫМЯННУЮ сцену и не всегда возвращает
    игровую — даже когда прогон дошёл до конца (P309, повтор 12.09). Play на ней
    поднимает только синглтоны: ни уровня, ни HUD, ни персонажа."""
    d = mcp('execute_code', {"action": "execute", "code":
            'var sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene();'
            'if (UnityEngine.Application.isPlaying) return "play|" + sc.path;'
            'if (sc.path == "Assets/Scenes/level1.unity") return "ок|" + sc.path;'
            'if (sc.path != "") return "чужая|" + sc.path;'
            'var back = UnityEditor.SceneManagement.EditorSceneManager.OpenScene('
            '"Assets/Scenes/level1.unity", UnityEditor.SceneManagement.OpenSceneMode.Single);'
            'return "вернул|" + back.path;'})
    res = (d.get('data') or {}).get('result') or '|'
    state, path = (res.split('|') + ['', ''])[:2]
    if state == 'вернул':
        print('сцена: раннер оставил редактор на БЕЗЫМЯННОЙ пустой сцене — вернул', path, '(P309)')
    elif state == 'чужая':
        print('сцена: редактор на', path, '— не игровая, проверь перед play (P309)')
    elif state == 'play':
        print('сцена: редактор в play на', path or 'БЕЗЫМЯННОЙ — это P309, останови play и открой level1.unity')
    else:
        print('сцена: игровая, ок')
    return state in ('ок', 'вернул')


def probe(name, *args):
    out = subprocess.run(['python3', REG + '/probes/' + name] + list(args),
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
    line = tail[-1] if tail else 'нет ответа'
    # ⭐ Жалобы живут ПОСЛЕ ' :: ', а счётчики перед ним занимают полтысячи
    # символов — прежний срез на 200 резал ровно то, ради чего проба и нужна.
    # 13.09 замерено: на forest100 счётчики 509 символов, значит check_all НИ
    # РАЗУ не показал ни одной жалобы инвариантов. Счётчики жмём, жалобы — нет.
    head, sep, rest = line.partition(' :: ')
    if sep:
        line = (head[:110] + '…' if len(head) > 110 else head) + ' :: ' + rest
    print(name + ':', line[:1400])
    return tail


def main():
    print('=== проверка «всё, что работало, работает» ===')
    ok_lint = lint()
    ok_probes = probes_lint()
    ok_compile = compile_check()
    probe('export_facing_probe.py')
    play, compiling = editor_state()
    print('редактор: play =', play, ', компилируется =', compiling)
    ok_tests = None
    if not play:
        ok_tests = tests()
        restore_scene()
    else:
        print('тесты: пропущены — редактор в play')
    if play:
        probe('invariants_play.py')
        probe('transfer_probe.py', '--run')
        probe('level_roundtrip.py')
        probe('posture_probe.py')
        probe('tilt_probe.py')
        probe('gc_probe.py', 'check')
    else:
        print('живые пробы: пропущены — нужен play')
    print('=== итог ===')
    print('грабли:', 'ок' if ok_lint else 'КРАСНОЕ')
    print('ссылки проб:', 'ок' if ok_probes else 'КРАСНОЕ — защита умерла, чинить пробу')
    print('компиляция:', 'ок' if ok_compile else 'КРАСНОЕ')
    print('тесты:', 'ок' if ok_tests else ('КРАСНОЕ' if ok_tests is False else 'не прогнаны'))
    print('живые пробы: смотри строки выше')
    sys.exit(0 if ok_lint and ok_probes and ok_compile and ok_tests is not False else 1)


if __name__ == '__main__':
    main()
