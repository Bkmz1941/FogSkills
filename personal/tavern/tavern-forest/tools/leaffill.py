# Опавшие листья под лиственными деревьями (Илья 01.11: «давай листья добавим на 104 уровень, раскидай их»).
# python3 -I leaffill.py <level.json> [out.json | --write]. Запреты — как у vegfill.py (вода, дорога, дома, предметы).
import json, sys, math, random, shutil, collections, datetime, os

src = sys.argv[1]
WRITE = '--write' in sys.argv
rnd = random.Random(111)
d = json.load(open(src))

# ---------- рельеф ----------
cs = d['cellSize']; skirt = d['skirt'] * cs
MX = d['gridOriginX'] - cs / 2 - skirt; MZ = d['gridOriginZ'] - cs / 2 - skirt
NX = round((d['gridWidth'] * cs + 2 * skirt)) + 1; NZ = round((d['gridHeight'] * cs + 2 * skirt)) + 1
hv = [int(v) / 1000 for v in d['heights'].split(',')]
assert len(hv) == NX * NZ

def node(ix, iz):
    ix = min(max(ix, 0), NX - 1); iz = min(max(iz, 0), NZ - 1)
    return hv[iz * NX + ix]

def H(x, z):
    fx = x - MX; fz = z - MZ; ix = math.floor(fx); iz = math.floor(fz); tx = fx - ix; tz = fz - iz
    a = node(ix, iz) * (1 - tx) + node(ix + 1, iz) * tx
    b = node(ix, iz + 1) * (1 - tx) + node(ix + 1, iz + 1) * tx
    return a * (1 - tz) + b * tz

X0, Z0 = MX + 0.4, MZ + 0.4
X1, Z1 = MX + NX - 1 - 0.4, MZ + NZ - 1 - 0.4

# вода: узлы ниже -0.35 мокрые; расстояние до воды по сетке 1 м (BFS)
WET = -0.35
wetd = [99] * (NX * NZ)
q = collections.deque()
for i, v in enumerate(hv):
    if v < WET: wetd[i] = 0; q.append(i)
while q:
    i = q.popleft(); ix, iz = i % NX, i // NX
    if wetd[i] >= 8: continue
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        jx, jz = ix + dx, iz + dz
        if 0 <= jx < NX and 0 <= jz < NZ:
            j = jz * NX + jx
            if wetd[j] > wetd[i] + 1: wetd[j] = wetd[i] + 1; q.append(j)

def water_dist(x, z):
    return wetd[min(max(round(z - MZ), 0), NZ - 1) * NX + min(max(round(x - MX), 0), NX - 1)]

# ---------- покраска: дорожки/камень ----------
from PIL import Image
pnames = ['Grass004', 'Ground037', 'Ground054', 'Ground103', 'Leaves001', 'Moss001', 'Mud001', 'Path001',
          'StoneBig', 'StoneGrey', 'StoneRiver', 'StoneWhite']
pmaps = [Image.open(src.replace('.json', '_paint.png' if m == 0 else f'_paint{m + 1}.png')).convert('RGBA') for m in range(3)]
PW, PH = pmaps[0].size; ppm = d['paintPxPerM']; pmx, pmz = d['paintMinX'], d['paintMinZ']
ppx = [m.load() for m in pmaps]
PATHY = {'Ground037', 'Ground103', 'Ground054', 'Mud001', 'Path001', 'StoneBig', 'StoneGrey', 'StoneRiver', 'StoneWhite'}

def pathy(x, z):
    ix = int((x - pmx) * ppm); iz = int((z - pmz) * ppm)
    if not (0 <= ix < PW and 0 <= iz < PH): return 0
    row = PH - 1 - iz; s = 0
    for m in range(3):
        p = ppx[m][ix, row]
        for c in range(4):
            if pnames[m * 4 + c] in PATHY: s += p[c]
    return s / 255

# ---------- запретные места ----------
def bbox(pts, pad):
    if not pts: return None
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    return (min(xs) - pad, min(zs) - pad, max(xs) + pad, max(zs) + pad)

struct = [(w['pos']['x'], w['pos']['z']) for w in d['walls'] + d['floors']]
nonveg = [(o['pos']['x'], o['pos']['z']) for o in d['objects']
          if not o['id'].startswith(('veg', 'deco', 'env_highway', 'robin'))]
houses = []
for cx, cz in ((33, -26), (12, 105)):
    pts = [p for p in struct + nonveg if abs(p[0] - cx) < 16 and abs(p[1] - cz) < 16]
    houses.append(bbox(pts, 0))
woodpile = bbox([p for p in nonveg if 25 < p[0] < 35 and 33 < p[1] < 43], 0)
busstop = (-84, -9, -74, 5)
singles = [p for p in nonveg if not any(b[0] - 1 <= p[0] <= b[2] + 1 and b[1] - 1 <= p[1] <= b[3] + 1
                                       for b in houses + [woodpile, busstop] if b)]
ROAD = (-74.5, -64.5)

def box_dist(b, x, z):
    if b is None: return 99
    dx = max(b[0] - x, 0, x - b[2]); dz = max(b[1] - z, 0, z - b[3]); return math.hypot(dx, dz)

def free(x, z, big):
    """big: 0 трава/мелочь, 1 куст/камень, 2 дерево/бревно"""
    if not (X0 <= x <= X1 and Z0 <= z <= Z1): return False
    wd = water_dist(x, z)
    if wd < (1 if big == 0 else 3 if big == 1 else 4): return False
    if H(x, z) < WET + 0.05: return False
    road_pad = (0, 2.0, 3.0)[big]
    if ROAD[0] - road_pad < x < ROAD[1] + road_pad: return False
    if pathy(x, z) > (0.35 if big == 0 else 0.1): return False
    if big and any(pathy(x + dx, z + dz) > 0.5 for dx, dz in ((1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5))): return False
    for b in houses:
        if b and box_dist(b, x, z) < (2.0, 7.0, 9.0)[big]: return False
    if box_dist(woodpile, x, z) < (1.0, 3.0, 4.0)[big]: return False
    if box_dist(busstop, x, z) < (0.0, 2.0, 4.0)[big] or (busstop[0] <= x <= busstop[2] and busstop[1] <= z <= busstop[3]): return False
    for sx, sz in singles:
        if math.hypot(sx - x, sz - z) < (1.0, 2.0, 3.0)[big]: return False
    return True

# ---------- семейства ----------
def fam(i):
    for k in ('fallen_tree', 'spruce', 'tree', 'grass_bush', 'grass_tuft', 'boulder_smooth', 'bush', 'flower',
              'fern', 'pebble', 'rock', 'mushroom', 'log', 'stick', 'butterfly'):
        if k in i: return k
    return None

def vid(base, n): return base if n == 1 else f'{base}_{n}'

class Hash:
    def __init__(s, c): s.c = c; s.g = collections.defaultdict(list)
    def add(s, x, z, tag=None): s.g[(math.floor(x / s.c), math.floor(z / s.c))].append((x, z, tag))
    def near(s, x, z, r):
        k = math.ceil(r / s.c); cx, cz = math.floor(x / s.c), math.floor(z / s.c)
        for dx in range(-k, k + 1):
            for dz in range(-k, k + 1):
                for p in s.g.get((cx + dx, cz + dz), ()):
                    if (p[0] - x) ** 2 + (p[1] - z) ** 2 < r * r: yield p
    def any(s, x, z, r):
        for _ in s.near(x, z, r): return True
        return False


plants = d['plants']; objs = d['objects']
PILE, LEAF = 'veg_leaves', 'veg_fallen_leaf'
PILES, SHAPES = 4, 4
# --piles-only — докинуть только кучки; --pile-k K — множитель числа кучек (Илья 01.11: «кучки не такие плотные —
# больше площадь, и раскидай на уровне больше их»: кучки в Blender вдвое шире, кладутся реже друг к другу).
PILES_ONLY = '--piles-only' in sys.argv
PILE_K = float(sys.argv[sys.argv.index('--pile-k') + 1]) if '--pile-k' in sys.argv else 1.0
PILE_GAP = 2.4
if PILES_ONLY: rnd.seed(112)   # второй проход — своя случайность, иначе повторил бы первый
# Повторный прогон не плодит листья: уже лежащие листья скрипт не трогает и рядом не кладёт.
maxn = collections.Counter()
for p in plants: maxn[p['id']] = max(maxn[p['id']], p['n'])
for o in objs: maxn[o['id']] = max(maxn[o['id']], o.get('number') or 0)
def nextn(i): maxn[i] += 1; return maxn[i]

def deciduous(i): return i.startswith('veg_tree') and 'swing' not in i
trees = [(p['x'], p['z']) for p in plants if deciduous(p['id'])] + \
        [(o['pos']['x'], o['pos']['z']) for o in objs if deciduous(o['id'])]
th = Hash(4)
for x, z in trees: th.add(x, z)
lh = Hash(2)
for p in plants:
    if p['id'].startswith((PILE, LEAF)): lh.add(p['x'], p['z'], 'pile' if p['id'].startswith(PILE) else 'leaf')

def vnoise(seed, scale):
    r = random.Random(seed); g = {}
    def val(ix, iz):
        k = (ix, iz)
        if k not in g: g[k] = random.Random(hash((seed, ix, iz))).random()
        return g[k]
    def f(x, z):
        fx, fz = x / scale, z / scale; ix, iz = math.floor(fx), math.floor(fz); tx, tz = fx - ix, fz - iz
        tx = tx * tx * (3 - 2 * tx); tz = tz * tz * (3 - 2 * tz)
        a = val(ix, iz) * (1 - tx) + val(ix + 1, iz) * tx
        b = val(ix, iz + 1) * (1 - tx) + val(ix + 1, iz + 1) * tx
        return a * (1 - tz) + b * tz
    return f
n_fall = vnoise(17, 18.0)   # где листопад гуще: от 0,4 до 1,6 к среднему

def vid(base, n): return base if n == 1 else f'{base}_{n}'
new = collections.Counter()
def put(base, k, x, z):
    i = vid(base, k)
    plants.append({'id': i, 'x': round(x, 3), 'y': round(H(x, z) - 0.1, 3), 'z': round(z, 3),
                   'r': round(rnd.uniform(0, 360), 1), 'n': nextn(i)})
    lh.add(x, z, 'pile' if base == PILE else 'leaf'); new[base] += 1

# Для листьев дом — только стены и полы (+0,5 м), а не рамка двора с предметами, как у vegfill:
# иначе деревья во дворе (гирлянды, сад) оставались без листьев.
walls_box = []
for cx, cz in ((33, -26), (12, 105)):
    walls_box.append(bbox([p for p in struct if abs(p[0] - cx) < 16 and abs(p[1] - cz) < 16], 0))

def leaf_free(x, z, pile=False):
    # Одиночный лист может лежать на тропинке (осень), но не на асфальте, не в воде и не в доме.
    if not (X0 <= x <= X1 and Z0 <= z <= Z1): return False
    if water_dist(x, z) < 1 or H(x, z) < WET + 0.05: return False
    if ROAD[0] < x < ROAD[1]: return False
    for b in walls_box:
        if b and box_dist(b, x, z) < 0.5: return False
    if pile and pathy(x, z) > 0.35: return False   # кучки — не на тропинке
    for sx, sz in singles:
        if math.hypot(sx - x, sz - z) < (1.0 if pile else 0.6): return False
    return True

for tx, tz in trees:
    k = 0.4 + 1.2 * n_fall(tx, tz)
    # кучки: в среднем ~0,8 на дерево, 0,9–3,0 м от ствола, не ближе 1,6 м к другой кучке
    piles = sum(1 for _ in range(3) if rnd.random() < min(0.95, 0.27 * k * PILE_K))
    for _ in range(piles):
        for _try in range(6):
            a = rnd.uniform(0, math.tau); r = rnd.uniform(1.0, 4.5)
            x, z = tx + math.cos(a) * r, tz + math.sin(a) * r
            if leaf_free(x, z, True) and not any(t == 'pile' for _, _, t in lh.near(x, z, PILE_GAP)):
                put(PILE, rnd.randint(1, PILES), x, z); break
    # одиночные: в среднем ~1,6 на дерево, 0,5–4,5 м (дальше — реже), не ближе 0,5 м к листу
    leaves = 0 if PILES_ONLY else sum(1 for _ in range(4) if rnd.random() < 0.4 * k)
    for _ in range(leaves):
        for _try in range(6):
            a = rnd.uniform(0, math.tau); r = 0.5 + 4.0 * rnd.random() ** 1.6
            x, z = tx + math.cos(a) * r, tz + math.sin(a) * r
            if leaf_free(x, z) and not lh.any(x, z, 0.5):
                put(LEAF, rnd.randint(1, SHAPES), x, z); break

d['plants'] = plants
print('лиственных деревьев', len(trees), '| добавлено', dict(new), '| растений', len(plants))
out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
if WRITE:
    bak = src + '.bak-before-leaffill-' + datetime.date.today().strftime('%d%m')
    k = 2
    while os.path.exists(bak):   # не затирать бэкап прошлого прохода
        bak = src + '.bak-before-leaffill%d-' % k + datetime.date.today().strftime('%d%m'); k += 1
    shutil.copyfile(src, bak); print('бэкап', bak)
    json.dump(d, open(src, 'w'), ensure_ascii=False, indent=4); print('записано', src)
elif out:
    json.dump(d, open(out, 'w'), ensure_ascii=False, indent=4); print('результат', out)
