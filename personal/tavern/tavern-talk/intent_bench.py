#!/usr/bin/env python3
"""Проверка сопоставления по смыслу (tavern-talk, регресс TK-I): тот же запрос, что Talk.AskIntent в игре, через
живую модель (llama-server :11435 игры), точность по набору intent_cases/<id>.json.

python3 intent_bench.py                 — valera, ru
python3 intent_bench.py valera -v       — показать каждый случай
python3 intent_bench.py valera --runs 3 — каждый случай 3 раза (модель с temperature 0 должна совпадать)

Список вопросов строится КАК Talk.IntentList: вопросы по порядку пар (player.ru), «(например: …)» — первые
IntentExamples=4 примера examples[].ru. Шаблон — Resources/Talk/intent_ru.txt. Меняешь одно — меняй другое."""
import json, os, re, sys, time, urllib.request
GAME = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources'
HERE = os.path.dirname(os.path.abspath(__file__))
URL = 'http://127.0.0.1:11435/v1/chat/completions'
EXAMPLES = 4

def questions(d):
    qs, seen = [], set()
    ex = {e['q']: e.get('ru', []) for e in d.get('examples', [])}
    for p in d['pairs']:
        if p.get('tense'): continue   # пары запретной зоны — свой список (Talk.Set), в обычном разговоре их нет
        k = p['player']['ru']
        if k in seen: continue
        seen.add(k); qs.append((k, ex.get(k, [])))
    return qs

def intent_list(qs):
    out = []
    for i, (shown, ex) in enumerate(qs):
        line = f'{i + 1}. {shown}'
        if ex: line += ' (например: ' + '; '.join(ex[:EXAMPLES]) + ')'
        out.append(line)
    return '\n'.join(out)

def ask(prompt, say):
    body = json.dumps({'model': 'local', 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': say}],
                       'stream': False, 'temperature': 0, 'max_tokens': 6, 'repeat_penalty': 1.15}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = json.load(r)['choices'][0]['message']['content'] or ''
    text = text.split('</think>')[-1]
    m = re.search(r'\d+', text)
    return (int(m.group()) if m else -1), text.strip()

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    who = args[0] if args else 'valera'
    verbose = '-v' in sys.argv
    runs = int(sys.argv[sys.argv.index('--runs') + 1]) if '--runs' in sys.argv else 1
    d = json.load(open(f'{GAME}/Dialogs/{who}.json'))
    qs = questions(d)
    keys = [q for q, _ in qs]
    tpl = open(f'{GAME}/Talk/intent_ru.txt').read()
    lst = intent_list(qs)
    cases = json.load(open(f'{HERE}/intent_cases/{who}.json'))['cases']
    ok = total = 0; slow = 0.0; bad = []
    for c in cases:
        want = 0 if c['expect'] == 0 else keys.index(c['expect']) + 1
        prompt = tpl.replace('{0}', lst).replace('{1}', c.get('before', '')).replace('{2}', c['say'])
        for _ in range(runs):
            t = time.time(); got, raw = ask(prompt, c['say']); slow = max(slow, time.time() - t)
            total += 1
            if got == want: ok += 1
            else: bad.append((c['say'], want, got, raw))
            if verbose: print(('✓' if got == want else '✗'), c['say'], '→', got, keys[got - 1] if 0 < got <= len(keys) else '', '| ждали', want)
    for say, want, got, raw in bad:
        print(f'✗ «{say}» ждали {want} {keys[want-1] if want else "свободный"} — модель {got} {keys[got-1] if 0 < got <= len(keys) else repr(raw)}')
    print(f'итог: {ok}/{total} = {100 * ok // max(1, total)}%, самый долгий ответ {slow:.1f} с, вопросов {len(qs)}, длина запроса {len(tpl.replace("{0}", lst))} симв.')
    sys.exit(0 if ok == total else 1)

main()
