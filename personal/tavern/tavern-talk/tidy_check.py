#!/usr/bin/env python3
"""Правило 16 скила tavern-talk: реплики персонажей без точки в конце и без длинных тире.
python3 tidy_check.py            — проверить все Dialogs/*.json (код выхода 1, если есть нарушения)
python3 tidy_check.py --fix      — почистить автоматически (тире → запятая; потом ПРОСМОТРЕТЬ глазами)"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidy import tidy, texts
ROOT = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/Dialogs'
fix = '--fix' in sys.argv
bad = 0
for f in sorted(glob.glob(ROOT + '/*.json')):
    d = json.load(open(f))
    for o, k in texts(d):
        n = tidy(o[k])
        if n != o[k]:
            bad += 1
            print(f'{os.path.basename(f)}: «{o[k]}» → «{n}»')
            if fix: o[k] = n
    if fix: open(f, 'w').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
# правило 19: фразы персонажа в правилах — только #id с byPhase и английским
import re
BEH = os.path.expanduser('~/Documents/Fog/Behavior')
for f in sorted(glob.glob(BEH + '/*.txt')):
    who = os.path.splitext(os.path.basename(f))[0]
    dlg = os.path.join(ROOT, who + '.json')
    if not os.path.exists(dlg): continue
    lines = {l['id']: l for l in json.load(open(dlg)).get('lines', [])}
    for n, line in enumerate(open(f).read().split('\n'), 1):
        code = line.split('#', 1)[0] if '[' in line.split('#', 1)[0] else line
        for m in re.finditer(r'\[(shout|say|talk|end talk)\s+([^\]]*)\]', line):
            arg = m.group(2).strip()
            if m.group(1) == 'talk' and arg in ('topic', '', 'тема', 'вопрос'): continue
            if not arg: continue
            if not arg.startswith('#'):
                bad += 1; print(f'{os.path.basename(f)}:{n}: фраза текстом «{arg}» — нужна реплика #id с byPhase (правило 19)'); continue
            lid = arg[1:].split()[0]
            l = lines.get(lid)
            if l is None:
                bad += 1; print(f'{os.path.basename(f)}:{n}: реплики #{lid} нет в Dialogs/{who}.json'); continue
            bp = l.get('byPhase', [])
            if len(bp) < 6 or any(not t.get('ru') or not t.get('en') for t in bp) or not l.get('en'):
                bad += 1; print(f'{os.path.basename(f)}:{n}: #{lid} — нет всех 6 фаз или английского (правило 19)')
print('чисто' if bad == 0 else f'нарушений: {bad}' + (' — исправлено, просмотри тире глазами' if fix else ''))
sys.exit(1 if bad and not fix else 0)
