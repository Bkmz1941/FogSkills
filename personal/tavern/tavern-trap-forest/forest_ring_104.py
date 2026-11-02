import json, sys, os, math, shutil, datetime, collections

path = os.path.expanduser('~/.config/unity3d/DefaultCompany/Tavern/levels/Котедж 104.json')
WRITE = '--write' in sys.argv
D, T, S, GAP = 10, 2, 9, 1
ROAD_PAD = 1
WATER_PAD = 1
d = json.load(open(path, encoding='utf-8'))
W, H, cs, ox, oz = d['gridWidth'], d['gridHeight'], d['cellSize'], d['gridOriginX'], d['gridOriginZ']
skirt = d['skirt'] * cs
MX = ox - cs / 2 - skirt; MZ = oz - cs / 2 - skirt
NX = round(W * cs + 2 * skirt) + 1; NZ = round(H * cs + 2 * skirt) + 1
h = [int(v) / 1000 for v in d['heights'].split(',')]
cell = lambda x, z: (int(round((x - ox) / cs)), int(round((z - oz) / cs)))

wet = set()
for w in d['water']:
    LV = w['level']
    sx, sz = int(round(w['x'] - MX)), int(round(w['z'] - MZ))
    seen = {(sx, sz)}; q = collections.deque([(sx, sz)])
    while q:
        x, z = q.popleft()
        for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if 0 <= n[0] < NX and 0 <= n[1] < NZ and n not in seen and h[n[1] * NX + n[0]] < LV:
                seen.add(n); q.append(n)
    for (x, z) in seen:
        wet.add(cell(MX + x, MZ + z))

road = {cell(o['pos']['x'], o['pos']['z']) for o in d['objects'] if o['id'].startswith('env_highway')}
pad = lambda s, r: {(i + a, j + b) for (i, j) in s for a in range(-r, r + 1) for b in range(-r, r + 1)}
no_water = pad(wet, WATER_PAD)
no_road = pad(road, ROAD_PAD)

plant = lambda i: i.startswith(('veg_', 'deco_stick', 'env_fog'))
busy = {cell(o['pos']['x'], o['pos']['z']) for o in d['objects'] if not plant(o['id'])}
busy |= {cell(w['pos']['x'], w['pos']['z']) for w in d['walls']}

ring_all = {(i, j) for i in range(D, W - D) for j in range(D, H - D)
            if min(i - D, j - D, W - D - 1 - i, H - D - 1 - j) < T}
ring = {c for c in ring_all if c not in no_water and c not in no_road}

def clean(c):
    i, j = c
    return all((i + a, j + b) not in busy for a in range(-S, S + 1) for b in range(-S, S + 1))

working = {c for c in ring if clean(c)}

e = D + T + GAP
mi, mj = W // 2, H // 2
sides = {
    'запад': [(e, j) for j in range(e, H - e - 1)],
    'восток': [(W - 2 - e, j) for j in range(e, H - e - 1)],
    'юг': [(i, e) for i in range(e, W - e - 1)],
    'север': [(i, H - 2 - e) for i in range(e, W - e - 1)],
}
exits = {}
for name, line in sides.items():
    mid = mi if name in ('юг', 'север') else mj
    best = None
    for (i, j) in sorted(line, key=lambda c: abs((c[0] if name in ('юг', 'север') else c[1]) - mid)):
        sq = [(i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)]
        if all(c not in no_water and c not in no_road and clean(c) for c in sq):
            best = sq; break
    if best: exits[name] = best
    print('выход', name, best[0] if best else 'НЕТ места')

grid = []
for j in range(H - 1, -1, -1):
    row = ''
    for i in range(W):
        c = (i, j)
        ch = '.'
        if c in wet: ch = '~'
        if c in road: ch = '#'
        if any(c in v for v in exits.values()): ch = 'E'
        elif c in working: ch = 'O'
        elif c in ring: ch = 'o'
        elif c in ring_all: ch = 'x'
        if c in busy and ch in '.oO': ch = '*'
        row += ch
    grid.append(row)
open(os.path.join(os.path.dirname(__file__), 'ring_map.txt'), 'w').write('\n'.join(grid))
print('кольцо полное %d, после воды и дороги %d, с переносом (чисто ±%d) %d' % (len(ring_all), len(ring), S, len(working)))
print('вырезано: вода %d, дорога %d' % (len([c for c in ring_all if c in no_water]), len([c for c in ring_all if c in no_road and c not in no_water])))

if not WRITE:
    sys.exit(0)
tpl = dict(name='', slug='', cr=1.0, cg=1.0, cb=1.0, kind=0, strong=True, fireSpread=False, temp=float('nan'),
           attackers='', exits='', signal=2, view=2.0, note='', marks=[], events=[], fog=False, fogStrong=True,
           fire=False, fireStrong=True, wind=False, cells=[], fine=[])
vec = lambda c: {'x': ox + c[0] * cs, 'y': 0.1, 'z': oz + c[1] * cs}
outs = [dict(tpl, name='Выход из леса: ' + s, slug='forest_out_%d' % n, kind=22, cr=0.55, cg=0.85, cb=0.45,
             cells=[vec(c) for c in sq]) for n, (s, sq) in enumerate(exits.items(), 1)]
entry = dict(tpl, name='Вход в лес: край карты', slug='forest_in_edge', kind=21, cr=0.25, cg=0.6, cb=0.3,
             exits=','.join(z['slug'] for z in outs), cells=[vec(c) for c in sorted(ring)])
d['zones'] = [z for z in d['zones'] if z['kind'] not in (21, 22)] + [entry] + outs
bak = path + '.bak-before-forest-' + datetime.date.today().strftime('%d%m')
if not os.path.exists(bak): shutil.copy2(path, bak)
json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
print('записано, бэкап', bak)
