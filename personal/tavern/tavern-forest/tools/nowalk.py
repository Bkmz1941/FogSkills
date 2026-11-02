# Зона запрета хода «глубокая вода»: по рельефу уровня, где глубина под уровнем воды ≥ DEPTH.
# python3 -I nowalk.py "<уровень.json>" [--write] [--depth 0.5]
# Кромка воды не двигается; в воду можно зайти, пока глубина меньше DEPTH.
import json, sys, math, shutil, datetime, collections, copy

src = sys.argv[1]; WRITE = '--write' in sys.argv
DEPTH = float(sys.argv[sys.argv.index('--depth') + 1]) if '--depth' in sys.argv else 0.5
KIND = 23
SLUG = 'deep_water'
d = json.load(open(src))
cs = d['cellSize']; skirt = d['skirt'] * cs
MX = d['gridOriginX'] - cs / 2 - skirt; MZ = d['gridOriginZ'] - cs / 2 - skirt
NX = round(d['gridWidth'] * cs + 2 * skirt) + 1; NZ = round(d['gridHeight'] * cs + 2 * skirt) + 1
h = [int(v) / 1000 for v in d['heights'].split(',')]
assert len(h) == NX * NZ
FINE = cs / 6
CORNER_X = d['gridOriginX'] - cs / 2; CORNER_Z = d['gridOriginZ'] - cs / 2
assert abs(CORNER_X / FINE - round(CORNER_X / FINE)) < 1e-6 and abs(CORNER_Z / FINE - round(CORNER_Z / FINE)) < 1e-6


def H(x, z):
    fx = x - MX; fz = z - MZ
    ix = min(max(int(math.floor(fx)), 0), NX - 2); iz = min(max(int(math.floor(fz)), 0), NZ - 2)
    tx = min(max(fx - ix, 0.0), 1.0); tz = min(max(fz - iz, 0.0), 1.0)
    a = h[iz * NX + ix]; b = h[iz * NX + ix + 1]; c = h[(iz + 1) * NX + ix]; e = h[(iz + 1) * NX + ix + 1]
    return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + e * tx) * tz


squares = set()
shore = []
for w in d['water']:
    LV = w['level']
    sx = min(max(int(round(w['x'] - MX)), 0), NX - 1); sz = min(max(int(round(w['z'] - MZ)), 0), NZ - 1)
    seen = set(); q = collections.deque()
    if h[sz * NX + sx] < LV:
        q.append((sx, sz)); seen.add((sx, sz))
    while q:
        x, z = q.popleft()
        for nx, nz in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
            if 0 <= nx < NX and 0 <= nz < NZ and (nx, nz) not in seen and h[nz * NX + nx] < LV:
                seen.add((nx, nz)); q.append((nx, nz))
    if not seen:
        print('вода без узлов ниже уровня', w); continue
    xs = [p[0] for p in seen]; zs = [p[1] for p in seen]
    x0 = MX + min(xs) - 1; x1 = MX + max(xs) + 1; z0 = MZ + min(zs) - 1; z1 = MZ + max(zs) + 1
    for fz in range(int(math.floor(z0 / FINE)), int(math.ceil(z1 / FINE)) + 1):
        cz = (fz + 0.5) * FINE
        for fx in range(int(math.floor(x0 / FINE)), int(math.ceil(x1 / FINE)) + 1):
            cx = (fx + 0.5) * FINE
            node = (int(round(cx - MX)), int(round(cz - MZ)))
            if node not in seen: continue
            depth = LV - H(cx, cz)
            if depth >= DEPTH: squares.add((fx, fz))
            elif depth > -0.05 and depth < 0.05: shore.append((cx, cz))
    print('вода уровень %.2f: узлов под водой %d, квадратов зоны %d' % (LV, len(seen), len(squares)))

if not squares:
    print('зона пуста'); sys.exit(1)

# полоса, куда зайти можно: от кромки до зоны
sq = squares
def dist_to_zone(x, z, rmax=12.0):
    best = rmax
    fx0 = int(math.floor(x / FINE)); fz0 = int(math.floor(z / FINE))
    k = int(math.ceil(rmax / FINE))
    for dz in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if (fx0 + dx, fz0 + dz) in sq:
                dd = math.hypot((fx0 + dx + 0.5) * FINE - x, (fz0 + dz + 0.5) * FINE - z)
                if dd < best: best = dd
    return best
import random
random.seed(1)
sample = random.sample(shore, min(300, len(shore)))
dists = sorted(dist_to_zone(x, z) for x, z in sample)
if dists:
    print('полоса входа от кромки до запрета, м: мин %.1f  медиана %.1f  макс %.1f' % (dists[0], dists[len(dists) // 2], dists[-1]))

# runs
rows = collections.defaultdict(list)
for fx, fz in squares: rows[fz].append(fx)
fine = []
for fz in sorted(rows):
    xs = sorted(rows[fz]); start = xs[0]; n = 1
    for a, b in zip(xs, xs[1:]):
        if b == a + 1: n += 1; continue
        fine.append({'x': start, 'z': fz, 'n': n, 'y': 0.0, 'g': True}); start = b; n = 1
    fine.append({'x': start, 'z': fz, 'n': n, 'y': 0.0, 'g': True})

# cells 3 м: где зоной накрыта хотя бы половина
counts = collections.Counter()
for fx, fz in squares:
    cx = (fx + 0.5) * FINE; cz = (fz + 0.5) * FINE
    counts[(int(math.floor((cx - CORNER_X) / cs)), int(math.floor((cz - CORNER_Z) / cs)))] += 1
cells = []
for (ix, iz), n in sorted(counts.items()):
    if n < 18: continue
    wx = CORNER_X + (ix + 0.5) * cs; wz = CORNER_Z + (iz + 0.5) * cs
    cells.append({'x': wx, 'y': H(wx, wz) + 0.1, 'z': wz})

template = copy.deepcopy(d['zones'][0])
for k in ('cells', 'fine', 'events', 'marks'):
    template[k] = []
template.update({'name': 'Глубокая вода', 'slug': SLUG, 'cr': 0.85, 'cg': 0.22, 'cb': 0.2, 'kind': KIND, 'strong': True,
                 'fireSpread': False, 'temp': float('nan'), 'attackers': '', 'exits': '', 'signal': 2, 'view': 2.0,
                 'note': 'запрет хода там, где глубина ≥ %.2f м; скрипт nowalk.py' % DEPTH,
                 'cells': cells, 'fine': fine})
for k in ('fog', 'fire', 'wind'):
    if k in template: template[k] = False
d['zones'] = [z for z in d['zones'] if z.get('slug') != SLUG] + [template]
print('квадратов %d (%.0f м²), прогонов %d, клеток 3 м %d' % (len(squares), len(squares) * FINE * FINE, len(fine), len(cells)))
xs = [s[0] for s in squares]; zs = [s[1] for s in squares]
print('охват x %.1f..%.1f  z %.1f..%.1f' % (min(xs) * FINE, (max(xs) + 1) * FINE, min(zs) * FINE, (max(zs) + 1) * FINE))

if WRITE:
    bak = src + '.bak-before-nowalk-' + datetime.datetime.now().strftime('%d%m')
    if not __import__('os').path.exists(bak): shutil.copyfile(src, bak)
    json.dump(d, open(src, 'w', encoding='utf-8'), ensure_ascii=False)
    print('записано', src, 'бэкап', bak)
else:
    print('сухой прогон, без записи (--write)')
