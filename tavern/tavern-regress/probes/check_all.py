"""Один прогон: линт граблей, компиляция, тесты EditMode, живые пробы. Печатает вердикт.

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


def probe(name):
    out = subprocess.run(['python3', REG + '/probes/' + name],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
    print(name + ':', tail[-1][:200] if tail else 'нет ответа')
    return tail


def main():
    print('=== проверка «всё, что работало, работает» ===')
    ok_lint = lint()
    ok_compile = compile_check()
    play, compiling = editor_state()
    print('редактор: play =', play, ', компилируется =', compiling)
    ok_tests = None
    if not play:
        ok_tests = tests()
    else:
        print('тесты: пропущены — редактор в play')
    if play:
        probe('invariants_play.py')
        probe('level_roundtrip.py')
        probe('posture_probe.py')
    else:
        print('живые пробы: пропущены — нужен play')
    print('=== итог ===')
    print('грабли:', 'ок' if ok_lint else 'КРАСНОЕ')
    print('компиляция:', 'ок' if ok_compile else 'КРАСНОЕ')
    print('тесты:', 'ок' if ok_tests else ('КРАСНОЕ' if ok_tests is False else 'не прогнаны'))
    print('живые пробы: смотри строки выше')
    sys.exit(0 if ok_lint and ok_compile and ok_tests is not False else 1)


if __name__ == '__main__':
    main()
