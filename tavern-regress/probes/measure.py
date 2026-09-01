"""Характеризующий замер: прогнать зонд (.cs для execute_code) в play и сохранить строки в файл.

python3 measure.py hover_probe.cs /путь/hover_before.txt
python3 measure.py pose_probe.cs  /путь/pose_after.txt
Потом: diff before after — пустой дифф = поведение не изменилось. Между замерами сцену не трогать.
"""
import json, re, subprocess, sys, pathlib

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'


def main():
    probe, out = sys.argv[1], sys.argv[2]
    code = pathlib.Path(probe).read_text(encoding='utf-8')
    code = re.sub(r'"/tmp/[^"]+\.txt"', json.dumps(out), code)
    r = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                       capture_output=True, text=True, timeout=900, cwd=PROJECT)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '{}'
    try:
        d = json.loads(line); res = (d.get('data') or {}).get('result') or d.get('message')
    except Exception:
        res = r.stdout[-300:]
    n = sum(1 for _ in open(out, encoding='utf-8')) if pathlib.Path(out).exists() else 0
    print(f'{pathlib.Path(probe).name}: {str(res)[:200]} | строк в {out}: {n}')


if __name__ == '__main__':
    main()
