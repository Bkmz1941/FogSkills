"""Старт сессии одним экраном: мост Unity, редактор, оба репозитория, свежие записи.

python3 ~/.claude/skills/tavern-regress/probes/start.py
"""
import json, re, socket, subprocess, pathlib

SK = pathlib.Path.home() / '.claude/skills'
GAME = SK / 'tavern-game'
REG = SK / 'tavern-regress'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
SKILLS_REPO = '/media/ilya/T714/claude-skills'
MCP_PORT = 8090
EDITOR_LOG = pathlib.Path.home() / '.config/unity3d/Editor.log'


def sh(cmd, cwd=None):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=cwd).stdout.rstrip('\n')
    except Exception as e:
        return f'(ошибка: {e})'


def mcp_state():
    try:
        with socket.create_connection(('127.0.0.1', MCP_PORT), timeout=1):
            pass
    except OSError:
        return '❌ Unity MCP: down — порт %d никто не слушает. Window → MCP for Unity → Start (порт %d, не 8080: там CockroachDB)' % (MCP_PORT, MCP_PORT)
    out = sh(f'python3 {GAME}/mcp_call.py execute_code \'{{"action":"execute","code":"return UnityEngine.Application.isPlaying + \\"|\\" + UnityEditor.EditorApplication.isCompiling;"}}\'', cwd=PROJECT)
    line = out.strip().splitlines()[-1] if out.strip() else '{}'
    try:
        res = (json.loads(line).get('data') or {}).get('result') or ''
    except Exception:
        res = ''
    if '|' not in res:
        return f'✅ мост по HTTP на {MCP_PORT}, но execute_code не ответил: {out[:120]}'
    play, comp = res.split('|')[:2]
    return f'✅ Unity MCP: connected — play={play.lower()}, compiling={comp.lower()}'


def gpu_state():
    renderer = ''
    try:
        for l in EDITOR_LOG.read_text(encoding='utf-8', errors='replace').splitlines():
            if l.startswith('Renderer:'):
                renderer = l[len('Renderer:'):].strip()
    except OSError:
        return '⚠️ GPU: Editor.log не прочитан'
    if 'NVIDIA' in renderer.upper():
        return f'✅ GPU: {renderer}'
    return (f'❌ GPU: редактор рендерит на «{renderer or "?"}» — драйвер NVIDIA не загружен, кадр и замеры не считаются '
            '(P568: sudo apt install linux-modules-nvidia-580-open-generic-hwe-24.04 + перезагрузка)')


def last_headers(path, n, pattern=r'^## '):
    heads = [l for l in path.read_text(encoding='utf-8').splitlines() if re.match(pattern, l)]
    return heads[-n:]


def main():
    print('=== Таверна: старт сессии ===')
    print(mcp_state())
    print(gpu_state())
    print('blender:', 'запущен' if sh('pgrep -x blender').strip() else 'не запущен')
    print()
    print('--- игра', PROJECT)
    print('незакоммичено файлов:', sh('git status --porcelain | wc -l', cwd=PROJECT).strip())
    print(sh("git log -4 --format='  %h %ad %s' --date='format:%d.%m %H:%M'", cwd=PROJECT))
    print('--- скилы', SKILLS_REPO)
    print('незакоммичено файлов:', sh('git status --porcelain | wc -l', cwd=SKILLS_REPO).strip(),
          '(чужие M не трогать: tavern-regress/SESSIONS.md)')
    print(sh("git log -3 --format='  %h %ad %s' --date='format:%d.%m %H:%M'", cwd=SKILLS_REPO))
    print()
    print('--- последние решения (DESIGN_LOG)')
    for h in last_headers(GAME / 'DESIGN_LOG.md', 5):
        print(' ', h[3:110])
    print('--- последние грабли (PITFALLS)')
    for h in last_headers(GAME / 'PITFALLS.md', 3, r'^## P\d{3} '):
        print(' ', h[3:110])
    inv = [l for l in (REG / 'INVARIANTS.md').read_text(encoding='utf-8').splitlines() if re.match(r'^\| \d+ \|', l)]
    print(f'инвариантов: {len(inv)}; линт:', sh(f'python3 {REG}/probes/bugs.py --lint | tail -n 1'))
    open_md = GAME / 'OPEN.md'
    if open_md.exists():
        n = sum(1 for l in open_md.read_text(encoding='utf-8').splitlines() if l.startswith('- [ ]'))
        print(f'вопросов Илье открыто: {n} (tavern-game/OPEN.md)')
    print()
    print('дальше: ListAgents — кто рядом; bugs.py <область> — перед задачей; SESSIONS.md — правила соседства')


if __name__ == '__main__':
    main()
