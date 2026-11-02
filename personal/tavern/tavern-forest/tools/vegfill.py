# Котедж 104: заполнить проплешины растительности по всей карте и по краям (юбке),
# развести тесные деревья, перемешать варианты. python3 -I vegfill.py <level.json> [--write]
import json, sys, math, random, shutil, collections, datetime

src = sys.argv[1]
WRITE = '--write' in sys.argv
rnd = random.Random(3110)
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
before = collections.Counter(fam(p['id']) for p in plants)

# ---------- 1. тесные деревья: развести (только короткие записи; полные с насестом не трогаем) ----------
TREE_MIN_OLD = 2.6
th = Hash(4)
for o in objs:
    if fam(o['id']) in ('tree', 'spruce'): th.add(o['pos']['x'], o['pos']['z'])
drop = set()
for i, p in enumerate(plants):
    if fam(p['id']) in ('tree', 'spruce'):
        if th.any(p['x'], p['z'], TREE_MIN_OLD): drop.add(i)
        else: th.add(p['x'], p['z'])
plants = [p for i, p in enumerate(plants) if i not in drop]
removed_trees = len(drop)

# ---------- номера ----------
maxn = collections.Counter()
for p in plants: maxn[p['id']] = max(maxn[p['id']], p['n'])
for o in objs: maxn[o['id']] = max(maxn[o['id']], o['number'])
def nextn(i): maxn[i] += 1; return maxn[i]

# ---------- шум ----------
def vnoise(seed, scale):
    r = random.Random(seed); tab = {}
    def g(ix, iz):
        k = (ix, iz)
        if k not in tab: tab[k] = random.Random(hash((seed, ix, iz)) & 0xffffffff).random()
        return tab[k]
    def f(x, z):
        fx, fz = x / scale, z / scale; ix, iz = math.floor(fx), math.floor(fz); tx, tz = fx - ix, fz - iz
        tx = tx * tx * (3 - 2 * tx); tz = tz * tz * (3 - 2 * tz)
        a = g(ix, iz) * (1 - tx) + g(ix + 1, iz) * tx; b = g(ix, iz + 1) * (1 - tx) + g(ix + 1, iz + 1) * tx
        return a * (1 - tz) + b * tz
    return f
n_open = vnoise(11, 28)      # поляны / чаща
n_spruce = vnoise(12, 40)    # где больше ёлок
n_flower = vnoise(13, 9)     # пятна цветов
n_kind = vnoise(14, 6)       # какой цветок в пятне
n_grass = vnoise(15, 7)      # какая трава в пятне

# ---------- 2. вариативность существующих коротких записей ----------
def pick_variant(f, x, z):
    if f == 'grass_tuft': return vid('veg_grass_tuft', rnd.randint(1, 4))
    if f == 'grass_bush': return vid('veg_grass_bush', rnd.randint(1, 3))
    if f == 'flower':
        k = int(n_kind(x, z) * 5) % 5 + 1
        return vid('veg_flower', k if rnd.random() < 0.75 else rnd.randint(1, 5))
    if f == 'bush':
        n = rnd.choice((1, 2, 3, 5, 1, 2, 3, 5, 4)); return vid('veg_bush', n)   # ягодный реже
    if f == 'fern': return vid('veg_fern', rnd.randint(1, 3))
    if f == 'mushroom': return vid('veg_mushroom', rnd.randint(1, 4))
    if f == 'pebble': return vid('veg_pebble_brown' if rnd.random() < 0.3 else 'veg_pebble', rnd.randint(1, 4))
    if f == 'tree': return vid('veg_tree', rnd.randint(1, 5))
    if f == 'spruce': return vid('veg_spruce', rnd.randint(1, 3))
    return None

remixed = 0
for p in plants:
    f = fam(p['id'])
    if f in ('grass_tuft', 'grass_bush', 'flower', 'bush', 'fern', 'mushroom', 'pebble', 'tree', 'spruce'):
        if f == 'pebble' and 'brown' in p['id']: continue
        nid = pick_variant(f, p['x'], p['z'])
        if nid and nid != p['id']:
            p['id'] = nid; p['n'] = nextn(nid); remixed += 1

# ---------- индексы занятости ----------
trees = Hash(5); bushes = Hash(3); grass = Hash(1.5); small = Hash(2); bigs = Hash(4)
for p in plants:
    f = fam(p['id']); x, z = p['x'], p['z']
    if f in ('tree', 'spruce'): trees.add(x, z)
    elif f == 'bush': bushes.add(x, z)
    elif f in ('grass_tuft', 'grass_bush', 'flower', 'fern'): grass.add(x, z)
    elif f in ('fallen_tree', 'log', 'boulder_smooth'): bigs.add(x, z)
    else: small.add(x, z)
for o in objs:
    f = fam(o['id']); x, z = o['pos']['x'], o['pos']['z']
    if f in ('tree', 'spruce'): trees.add(x, z)
    elif f == 'bush': bushes.add(x, z)
    elif f: small.add(x, z)

added = collections.Counter(); new = []
def put(i, x, z, yoff=-0.1, r=None):
    new.append({'id': i, 'x': round(x, 4), 'y': round(H(x, z) + yoff, 4), 'z': round(z, 4),
                'r': round(rnd.uniform(0, 360) if r is None else r, 3), 'n': nextn(i)})
    added[fam(i)] += 1

def candidates(step):
    pts = []
    z = Z0
    while z <= Z1:
        x = X0
        while x <= X1:
            pts.append((x + rnd.uniform(0, step), z + rnd.uniform(0, step))); x += step
        z += step
    rnd.shuffle(pts); return pts

# ---------- 3. деревья: не ближе 5 м к любому дереву ----------
TREE_MIN = 5.0
for x, z in candidates(2.5):
    if trees.any(x, z, TREE_MIN) or not free(x, z, 2): continue
    if bushes.any(x, z, 1.8) or bigs.any(x, z, 3): continue
    op = n_open(x, z)
    if rnd.random() > (0.85 if op < 0.6 else 0.2): continue      # поляны остаются светлее
    sp = n_spruce(x, z)
    if rnd.random() < 0.15 + 0.55 * sp: put(vid('veg_spruce', rnd.randint(1, 3)), x, z)
    else: put(vid('veg_tree', rnd.randint(1, 5)), x, z)
    trees.add(x, z)

# ---------- 4. кусты ----------
for x, z in candidates(2.0):
    if bushes.any(x, z, 4.0) or trees.any(x, z, 2.0) or bigs.any(x, z, 2.5) or not free(x, z, 1): continue
    if rnd.random() > 0.3: continue
    put(vid('veg_bush', rnd.choice((1, 2, 3, 5, 1, 2, 3, 5, 4))), x, z); bushes.add(x, z)

# ---------- 5. крупное: поваленные деревья, брёвна, валуны ----------
def line_clear(x, z, ang, half):
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for t in [k * 0.75 for k in range(-int(half / 0.75), int(half / 0.75) + 1)]:
        px, pz = x + sa * t, z + ca * t
        if not free(px, pz, 2) or trees.any(px, pz, 1.4) or bushes.any(px, pz, 1.4) or bigs.any(px, pz, 2.5): return False
    return True

fallen_n = log_n = 0
for x, z in candidates(9.0):
    roll = rnd.random()
    if roll < 0.05:
        ang = rnd.uniform(0, 360)
        if line_clear(x, z, ang, 4.0): put(vid('veg_fallen_tree', rnd.randint(1, 3)), x, z, r=ang); bigs.add(x, z); fallen_n += 1
    elif roll < 0.09:
        ang = rnd.uniform(0, 360)
        if line_clear(x, z, ang, 1.8): put('veg_log', x, z, r=ang); bigs.add(x, z); log_n += 1
    # гладкие валуны (veg_boulder_smooth) — для воды, в лес НЕ ставить (Илья 31.10)

# ---------- 6. трава сплошным покровом в проплешинах (и на краях) ----------
GR = 1.05
for x, z in candidates(0.85):
    if grass.any(x, z, GR) or trees.any(x, z, 0.7) or bushes.any(x, z, 0.9) or bigs.any(x, z, 1.6): continue
    if not free(x, z, 0): continue
    if rnd.random() > 0.9: continue
    near_tree = trees.any(x, z, 3.0)
    fl = n_flower(x, z)
    if fl > 0.72 and not near_tree and rnd.random() < 0.7:
        k = int(n_kind(x, z) * 5) % 5 + 1
        i = vid('veg_flower', k if rnd.random() < 0.8 else rnd.randint(1, 5))
    elif near_tree and rnd.random() < 0.18:
        i = vid('veg_fern', rnd.randint(1, 3))
    elif rnd.random() < 0.16:
        i = vid('veg_grass_bush', rnd.randint(1, 3))
    else:
        g = int(n_grass(x, z) * 4) % 4 + 1
        i = vid('veg_grass_tuft', g if rnd.random() < 0.6 else rnd.randint(1, 4))
    put(i, x, z); grass.add(x, z)

# ---------- 7. мелочь: грибы под деревьями, галька и камешки, галька у берега ----------
for x, z in candidates(2.2):
    if small.any(x, z, 1.6) or not free(x, z, 0): continue
    wd = water_dist(x, z)
    if wd <= 3 and rnd.random() < 0.5:
        put(vid('veg_pebble_brown' if rnd.random() < 0.4 else 'veg_pebble', rnd.randint(1, 4)), x, z, yoff=-0.08)
    elif trees.any(x, z, 2.2) and not trees.any(x, z, 0.6) and rnd.random() < 0.12:
        put(vid('veg_mushroom', rnd.randint(1, 4)), x, z)
    elif rnd.random() < 0.035:
        put(vid('veg_pebble_brown' if rnd.random() < 0.3 else 'veg_pebble', rnd.randint(1, 4)), x, z, yoff=-0.08)
    elif rnd.random() < 0.02 and not trees.any(x, z, 1.0):
        put(vid('veg_rock', rnd.choice((1, 2, 7, 8, 9, 10))), x, z)   # только мелкие, не стенки
    else:
        continue
    small.add(x, z)

# ---------- проверка и запись ----------
allp = plants + new
tt = [(p['x'], p['z']) for p in allp if fam(p['id']) in ('tree', 'spruce')] + \
     [(o['pos']['x'], o['pos']['z']) for o in objs if fam(o['id']) in ('tree', 'spruce')]
chk = Hash(4); [chk.add(x, z) for x, z in tt]
close = sum(1 for x, z in tt if sum(1 for _ in chk.near(x, z, 2.6)) > 1)
print('было растений', len(d['plants']), '→ стало', len(allp))
print('убрано тесных деревьев', removed_trees, '; перемешано вариантов', remixed)
print('добавлено', sum(added.values()), dict(added.most_common()))
print('поваленные', fallen_n, 'брёвна', log_n)
print('деревьев ближе 2.6 м после (полные записи с насестом)', close)
d['plants'] = allp
if WRITE:
    bak = src + '.bak-before-vegfill-' + datetime.date.today().strftime('%d%m')
    shutil.copy2(src, bak); print('бэкап', bak)
    with open(src, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False)
    print('записано', src)
else:
    json.dump(d, open(sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else '/dev/null', 'w'), ensure_ascii=False)
