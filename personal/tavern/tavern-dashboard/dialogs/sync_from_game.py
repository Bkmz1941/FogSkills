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
BEHAVIOR = os.path.expanduser('~/Documents/Fog/Behavior/')

def night_windows(cid):
    """Окна [night talk 21:00-08:00] из правил персонажа: ["21:00–08:00", …] без повторов."""
    import re
    f = BEHAVIOR + cid + '.txt'
    if not os.path.exists(f): return []
    out = []
    for m in re.finditer(r'\[(?:night talk|sleepy talk|ночной разговор|сонный разговор)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', open(f).read()):
        w = m.group(1) + '–' + m.group(2)
        if w not in out: out.append(w)
    return out

def tense_rules(cid):
    """[[зона, секунды, [действия…]]] из правил персонажа: «- [tense talk in Z]:» и «- [tense talk in Z 15s]:» + строки под ним."""
    import re
    f = BEHAVIOR + cid + '.txt'
    if not os.path.exists(f): return []
    out, cur = [], None
    rx = re.compile(r'^-\s*\[(?:tense talk in|forbidden talk in|напряж[её]нный разговор в)\s+(\S+?)(?:\s+(\d+)\s*(?:s|с|сек))?\]:\s*$')
    for raw in open(f):
        m = rx.match(raw.strip())
        if m: cur = [m.group(1), int(m.group(2) or 0), []]; out.append(cur); continue
        t = raw.strip()
        if cur is not None and t.startswith('[') and not t.startswith('- '): cur[2].append(t); continue
        if t: cur = None
    return out
done = []
for f in sorted(glob.glob(GAME + '*.json')):
    d = json.load(open(f))
    pid = d.get('dashboard') or d['id']
    groups, order = [], {}
    tense = []   # пары запретной зоны (05.11) — отдельная ось рядом с фазами, не в «Записанных фразах»
    night = []   # ночные пары (05.11) — своя вкладка «Ночь»
    for p in d['pairs']:
        if p.get('night') and not p.get('tense'):
            night.append([p['player']['ru'], p['reply']['ru'], p.get('from', 0), p.get('to', 5)])
            tr[p['player']['ru']] = p['player']['en']; tr[p['reply']['ru']] = p['reply']['en']
            continue
        if p.get('tense'):
            tense.append([p['player']['ru'], p['reply']['ru'], p.get('from', 0), p.get('to', 5)])
            tr[p['player']['ru']] = p['player']['en']; tr[p['reply']['ru']] = p['reply']['en']
            continue
        g = p['group']['ru']
        if g not in order:
            order[g] = len(groups); groups.append([g, []])
            tr.setdefault(g, p['group']['en'])
        groups[order[g]][1].append([p['player']['ru'], p['reply']['ru'], p.get('from', 0), p.get('to', 5)])
        tr[p['player']['ru']] = p['player']['en']; tr[p['reply']['ru']] = p['reply']['en']
    for pr in d.get('problems', []):
        for k in ('name', 'when'):
            if pr.get(k, {}).get('ru'): tr[pr[k]['ru']] = pr[k]['en']
        for k in ('about', 'solved', 'blamed'):
            for t in pr.get(k, []):
                if t['ru']: tr[t['ru']] = t['en']
    for key in ('tics', 'phases', 'likes', 'dislikes', 'tensePhases', 'nightPhases'):
        for t in d.get(key, []):
            if t['ru']: tr[t['ru']] = t['en']
    for t in d.get('unanswered', []):
        if t.get('ru'): tr[t['ru']] = t.get('en', '')
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
           'requests': [[r['name']['ru'], r['ask']['ru'], r['thanks']['ru'], r.get('points', 2), r.get('from', 0), r.get('item', ''), r.get('story', False)] for r in d.get('requests', [])],
           # «Типовые шаблоны» (04.11): [вопрос (player.ru), варианты ru[], варианты en[], ответы по фазам [[ответ, from, to]]]
           'unanswered': [[t.get('ru', ''), t.get('then', '')] for t in d.get('unanswered', [])],
           'examples': [[e['q'], e.get('ru', []), e.get('en', []), [[p['reply']['ru'], p.get('from', 0), p.get('to', 5)] for p in d['pairs'] if p['player']['ru'] == e['q'] and not p.get('tense')]] for e in d.get('examples', [])],
           # «Запретные зоны» (05.11): пары tense, тон по фазам, правила [tense talk in …] из Behavior/<id>.txt
           'cid': d['id'], 'tense': {'pairs': tense, 'phases': [t['ru'] for t in d.get('tensePhases', [])], 'rules': tense_rules(d['id'])},
           # «конфиг» персонажа (Илья 05.11: «вынеси ещё в дашборд конфиг») — правила поведения из Behavior/<id>.txt как есть
           'config': open(BEHAVIOR + d['id'] + '.txt').read() if os.path.exists(BEHAVIOR + d['id'] + '.txt') else '',
           # «Возможные проблемы» (05.11): [id, название, когда, вещь, about[6], solved[6], blamed[6]]
           'problems': [[pr['id'], pr['name']['ru'], pr.get('when', {}).get('ru', ''), pr.get('thing', ''),
                         [t['ru'] for t in pr.get('about', [])], [t['ru'] for t in pr.get('solved', [])], [t['ru'] for t in pr.get('blamed', [])]]
                        for pr in d.get('problems', [])],
           'night': {'pairs': night, 'phases': [t['ru'] for t in d.get('nightPhases', [])], 'windows': night_windows(d['id'])}}
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
