#!/usr/bin/env python3
"""Диалоги персонажей: игра → дашборд. Источник правды — Assets/Game/Resources/Dialogs/<id>.json (RU+EN).

python3 sync_from_game.py [dashboard.html]   по умолчанию — dashboard.html рядом со скилом
Переписывает у персонажей P.<dashboard>.dialog (prompt, tic, groups со строками [игрок, ответ, from, to], phases, likes, dislikes)
и английские пары в TR.
Публикация — как обычно (скил tavern-dashboard, «Как править»)."""
import glob, json, os, sys
GAME = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/Dialogs/'
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dashboard.html')
s = open(path).read()
i, j = s.index('const TR='), s.index(';\nlet LANG=')
tr = json.loads(s[i + 9:j])
base = s.index('const P={')
done = []
for f in sorted(glob.glob(GAME + '*.json')):
    d = json.load(open(f))
    pid = d.get('dashboard') or d['id']
    groups, order = [], {}
    for p in d['pairs']:
        g = p['group']['ru']
        if g not in order:
            order[g] = len(groups); groups.append([g, []])
            tr.setdefault(g, p['group']['en'])
        groups[order[g]][1].append([p['player']['ru'], p['reply']['ru'], p.get('from', 0), p.get('to', 5)])
        tr[p['player']['ru']] = p['player']['en']; tr[p['reply']['ru']] = p['reply']['en']
    for key in ('tics', 'phases', 'likes', 'dislikes'):
        for t in d.get(key, []):
            if t['ru']: tr[t['ru']] = t['en']
    for key in ('openers', 'busy', 'leave'):
        for t in d.get(key, []):
            if t['ru']: tr[t['ru']] = t['en']
    for l in d.get('lines', []):
        tr[l['ru']] = l['en']
        for t in l.get('byPhase', []):
            if t['ru']: tr[t['ru']] = t['en']
    for it in d.get('interests', []):
        tr[it['name']['ru']] = it['name']['en']
        for q in it['asks']: tr[q['ru']] = q['en']
    for r in d.get('requests', []):
        for k in ('name', 'ask', 'thanks'):
            if r[k]['ru']: tr[r[k]['ru']] = r[k]['en']
    feel = lambda t, good: [t['ru'], (1 if good else -1) * (abs(t.get('points', 0)) or 1), t.get('when', '')]
    tr[d['prompt']['ru']] = d['prompt']['en']
    dlg = {'prompt': d['prompt']['ru'], 'tic': [t['ru'] for t in d['tics']], 'groups': groups,
           'phases': [t['ru'] for t in d.get('phases', [])], 'likes': [feel(t, True) for t in d.get('likes', [])],
           'dislikes': [feel(t, False) for t in d.get('dislikes', [])],
           'scale': d.get('scale', 0) or 20, 'dayGain': d.get('dayGain', 0) or 6,
           'interests': [[it['name']['ru'], it.get('points', 2), [q['ru'] for q in it['asks']]] for it in d.get('interests', [])],
           'openers': [t['ru'] for t in d.get('openers', [])], 'busy': [t['ru'] for t in d.get('busy', [])], 'leave': [t['ru'] for t in d.get('leave', [])],
           'lines': [[l['id'], l['ru'], [t['ru'] for t in l.get('byPhase', [])]] for l in d.get('lines', [])],
           'requests': [[r['name']['ru'], r['ask']['ru'], r['thanks']['ru'], r.get('points', 2), r.get('from', 0), r.get('item', ''), r.get('story', False)] for r in d.get('requests', [])]}
    a = s.index('\n ' + pid + ':{', base)
    e = s.index('\n  ends:', a)
    k = s.find('\n  dialog:', a, e)
    line = '\n  dialog:' + json.dumps(dlg, ensure_ascii=False) + ','
    s = s[:k] + line + s[s.index('\n', k + 1):] if k >= 0 else s[:e] + line + s[e:]
    done.append(pid)
i, j = s.index('const TR='), s.index(';\nlet LANG=')
s = s[:i] + 'const TR=' + json.dumps(tr, ensure_ascii=False) + s[j:]
open(path, 'w').write(s)
print('синхронизировано:', ', '.join(done))
