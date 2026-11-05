#!/usr/bin/env python3
"""Правки фраз с дашборда → игра (Илья 04.11: «в дашборде в ответах добавь редактор»).
Claude Code базу дашборда не читает (организация владельца не пускает), поэтому страница выгружает правки файлом:
кнопка «Выгрузить правки файлом» → ~/Downloads/dashboard_edits*.json (берётся самый свежий).

python3 pull_edits.py              — показать, что будет перенесено
python3 pull_edits.py --apply      — перенести в Assets/Game/Resources/Dialogs/<id>.json (персонаж — по полю dashboard)
Потом: tavern-talk/tidy_check.py (точки/тире), sync_from_game.py, публикация, и Илья жмёт «Очистить перенесённые»."""
import glob, json, os, sys
GAME = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/Dialogs/'
files = sorted(glob.glob(os.path.expanduser('~/Downloads/dashboard_edits*.json')), key=os.path.getmtime)
if not files: sys.exit('нет ~/Downloads/dashboard_edits*.json — на дашборде «Выгрузить правки файлом»')
edits = json.load(open(files[-1]))
apply = '--apply' in sys.argv
by_pid = {}
for f in glob.glob(GAME + '*.json'):
    d = json.load(open(f)); by_pid[d.get('dashboard') or d['id']] = (f, d)
T = lambda ru, en: {'ru': ru, 'en': en}
done, miss, touched = [], [], set()
for e in edits:
    pid, kind, q = e.get('pid'), e.get('kind'), e.get('q', '')
    if pid not in by_pid: miss.append(f'нет персонажа {pid}'); continue
    f, d = by_pid[pid]; fr, to = int(e.get('from', 0)), int(e.get('to', 0)); ru, en = e.get('ru', '').strip(), e.get('en', '').strip()
    ok = False
    if kind == 'reply':
        for p in d['pairs']:
            if p['player']['ru'] == q and p.get('from', 0) == fr and p.get('to', 5) == to:
                p['reply'] = T(ru, en or p['reply'].get('en', '')); ok = True
    elif kind == 'line':
        for l in d.get('lines', []):
            if l['id'] != q: continue
            bp = l.get('byPhase') or []
            if fr == to and fr < len(bp): bp[fr] = T(ru, en or bp[fr].get('en', '')); ok = True
            elif not bp: l['ru'], l['en'] = ru, en or l.get('en', ''); ok = True
    elif kind in ('busy', 'leave', 'unanswered'):
        arr = d.get(kind, [])
        if fr < len(arr): arr[fr]['ru'] = ru; arr[fr]['en'] = en or arr[fr].get('en', ''); ok = True
    elif kind == 'examples':
        for x in d.get('examples', []):
            if x['q'] == q:
                x['ru'] = [t.strip() for t in ru.split('\n') if t.strip()]
                x['en'] = [t.strip() for t in (e.get('en') or '').split('\n') if t.strip()]; ok = True
    (done if ok else miss).append(f'{pid} · {kind} · {q} · {fr}-{to}: «{ru[:60]}»')
    if ok: touched.add(f)
print(f'файл {files[-1]}: правок {len(edits)}')
for x in done: print('  ✓', x)
for x in miss: print('  ✗ не нашёл:', x)
if apply:
    for f in touched:
        d = by_pid[[k for k, v in by_pid.items() if v[0] == f][0]][1]
        open(f, 'w').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    print('перенесено в игру:', ', '.join(os.path.basename(f) for f in touched) or 'ничего')
else:
    print('(показ; перенести — --apply)')
