#!/usr/bin/env python3
"""Правила персонажа: файл → уровень И игра, всегда вместе (Илья 04.11: «обновляй и в игре и в файле — давай
запомним, что сразу и там и там обновляем всегда»).

python3 behavior_apply.py valera                     → ~/Documents/Fog/Behavior/valera.txt в раздел «Скрипты людей»
python3 behavior_apply.py sectant --section 4        → в раздел с этим номером (0..7, без 6 — глобальные)
python3 behavior_apply.py valera --level "Котедж 104"
python3 behavior_apply.py valera --no-live          ← только файл уровня (в игре код ещё старый)
python3 behavior_apply.py valera --export            ← обратно: текст раздела из уровня в файл (если правили в игре)

Что делает: (1) копия уровня *.bak-before-behavior-<id>-ЧЧММ; (2) текст файла — в aiScripts[раздел], тот же текст
вычищается из других разделов, где лежал (перенос), aiRules пересобирается как LevelIO.JoinScripts; (3) если Unity
в play на этом уровне — те же разделы в живую игру (LevelIO.AiScripts + JoinScripts + план существа заново) и
проверка правил раздела. Разделы (HudUI.Ai.ScriptTitles): 0 сектантов, 1 погоды, 2 ворон, 3 безумных, 4 сценария,
5 технические, 6 глобальные (не в уровне), 7 людей."""
import json, os, re, subprocess, sys, time

BEH = os.path.expanduser('~/Documents/Fog/Behavior')
LEVELS = os.path.expanduser('~/.config/unity3d/DefaultCompany/Tavern/levels')
MCP = os.path.expanduser('~/.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
PEOPLE, GLOBAL = 7, 6
TITLES = ['сектантов', 'погоды', 'ворон', 'безумных', 'сценария', 'технические', 'глобальные', 'людей']

def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT).stdout.strip()
    try:
        d = json.loads(out.splitlines()[-1])
        return (d.get('data') or {}).get('result') if d.get('success') else None
    except Exception:
        return None

def cs(s): return json.dumps(s, ensure_ascii=False)

MARK = '#> '   # Cozy.Grid.LevelScriptParts: скрипт внутри раздела начинается строкой «#> имя»

def split_parts(text):
    parts, name, buf = [], '', []
    for line in (text or '').replace('\r', '').split('\n'):
        if line.startswith(MARK):
            parts.append([name, '\n'.join(buf).rstrip('\n')]); name, buf = line[len(MARK):].strip(), []
        else: buf.append(line)
    parts.append([name, '\n'.join(buf).rstrip('\n')])
    return parts

def join_parts(parts):
    out = ''
    for i, (name, text) in enumerate(parts):
        if i == 0:
            if text.strip(): out += text.rstrip('\n') + '\n\n'
            continue
        out += MARK + name + '\n' + text.rstrip('\n') + '\n\n'
    return out.rstrip('\n')

def main():
    who = sys.argv[1]
    level = opt('--level', 'Котедж 104')
    path = f'{LEVELS}/{level}.json'
    raw = open(path).read()
    d = json.loads(raw)
    scripts = list(d['aiScripts'])
    while len(scripts) < 8: scripts.append('')
    if '--export' in sys.argv:
        sec = int(opt('--section', next((i for i, t in enumerate(scripts) if f'[{who}_' in t), PEOPLE)))
        parts = split_parts(scripts[sec])
        own = next((t for n, t in parts if n == who), None)
        open(f'{BEH}/{who}.txt', 'w').write((own if own is not None else scripts[sec]).rstrip('\n') + '\n')
        print(f'раздел {sec} «{TITLES[sec]}» → {BEH}/{who}.txt'); return
    text = open(f'{BEH}/{who}.txt').read().replace('\r', '').rstrip('\n')
    sec = int(opt('--section', PEOPLE))
    if sec == GLOBAL: sys.exit('раздел 6 — глобальные правила, не уровень')
    moved = []
    spawn_rx = re.compile(r'\[spawn\]\[[^\]]*\b' + re.escape(who) + r'_\d')
    for i, t in enumerate(scripts):
        if i == GLOBAL or not t.strip(): continue
        parts = split_parts(t)
        keep = []
        for k, (n, body) in enumerate(parts):
            # прежнее место этого персонажа: его именной скрипт в чужом разделе или «общее» с его спавном — убрать
            stale = (n == who and i != sec) or (k == 0 and body.strip() and (body.strip() == text.strip() or spawn_rx.search(body) and f'[{who}_' in body))
            if stale: moved.append(i); body = '' if k == 0 else None
            if body is not None: keep.append([n, body])
        scripts[i] = join_parts(keep)
    parts = split_parts(scripts[sec])
    found = False
    for p_ in parts:
        if p_[0] == who: p_[1] = text; found = True
    if not found: parts.append([who, text])
    scripts[sec] = join_parts(parts)
    joined = ''.join(t.rstrip('\n') + '\n\n' for i, t in enumerate(scripts) if t.strip() and i != GLOBAL)
    # правим только два поля текста, остальной файл (24 МБ, числа как у Unity) не трогаем
    i0 = raw.index('"aiScripts": [')
    i1 = raw.index(']', i0)
    while True:
        try: json.loads(raw[i0 + len('"aiScripts": '):i1 + 1]); break
        except Exception: i1 = raw.index(']', i1 + 1)
    new = raw[:i0] + '"aiScripts": ' + cs(scripts) + raw[i1 + 1:]
    r0 = new.index('"aiRules": "') + len('"aiRules": ')
    r1 = r0 + len(cs(d['aiRules']))
    assert new[r0:r1] == cs(d['aiRules']), 'aiRules записан не так, как ждали — правка остановлена'
    new = new[:r0] + cs(joined) + new[r1:]
    check = json.loads(new)
    assert check['aiScripts'][sec] == scripts[sec] and check['aiRules'] == joined
    bak = f'{path}.bak-before-behavior-{who}-{time.strftime("%H%M")}'
    open(bak, 'w').write(raw)
    open(path, 'w').write(new)
    print(f'уровень «{level}»: {who}.txt → раздел {sec} «{TITLES[sec]}», скрипт «#> {who}»' + (f', убран из разделов {moved}' if moved else '') + f'; копия {os.path.basename(bak)}')
    if '--no-live' in sys.argv:
        print('игра: --no-live — живую игру не трогал (новый синтаксис ждёт перекомпиляции)'); return
    state = run('return UnityEngine.Application.isPlaying + "|" + Cozy.Grid.LevelIO.CurrentLevelName;')
    if not state or not state.startswith('True|'):
        print('игра: Unity не в play — живой уровень загрузит правила из файла при входе'); return
    if state.split('|', 1)[1] != level:
        print(f'игра: в play другой уровень ({state.split("|", 1)[1]}) — не трогал'); return
    code = 'var s = Cozy.Grid.LevelIO.AiScripts;\n'
    for i in range(len(scripts)):
        if i != GLOBAL and i < 8: code += f'if ({i} < s.Length) s[{i}] = {cs(scripts[i])};\n'
    code += ('Cozy.Grid.LevelIO.JoinScripts();\n'
             f'foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.SystemSlug.StartsWith({cs(who + "_")})) Cozy.Life.CreaturePlan.Restart(io);\n'
             'Cozy.Life.LifeRules.Applied("правила из Behavior");\n'
             f'return Cozy.Life.LifeRules.CheckScripts({sec});')
    res = run(code)
    if res is None: print('игра: не применилось (мост не ответил)'); return
    bad = [l for l in res.split('\n') if l.startswith('✗')]
    print('игра: применено; ' + (res.split('\n')[-1] if res else ''))
    for l in bad: print('  ' + l[:220])

main()
