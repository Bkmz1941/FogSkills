import json, subprocess, sys, pathlib
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
src = sys.argv[1]
code = pathlib.Path(src).read_text() if len(src) < 200 and pathlib.Path(src).exists() else src
out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                     capture_output=True, text=True, timeout=600, cwd=PROJECT)
text = out.stdout.strip()
line = text.splitlines()[-1] if text else '{}'
try:
    d = json.loads(line)
    r = (d.get('data') or {}).get('result')
    if r is None:
        print(json.dumps(d, ensure_ascii=False)[:4000])
    else:
        print(r)
except Exception:
    print(text[-4000:])
