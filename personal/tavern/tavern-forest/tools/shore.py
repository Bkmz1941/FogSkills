# Берег озера: плавный вход в воду по всему берегу, пологий пляж у песка, песок полосой у кромки.
# python3 -I shore.py "<уровень.json>" [--write]
# Линия воды НЕ двигается: вода = заливка узлов ниже уровня от точки налива (WaterBody), меняется только
# профиль по обе стороны изолинии уровня воды. Растения на изменённом рельефе едут за землёй.
import json, sys, math, random, shutil, collections, datetime
from PIL import Image

src = sys.argv[1]; WRITE = '--write' in sys.argv
d = json.load(open(src))
cs = d['cellSize']; skirt = d['skirt'] * cs
MX = d['gridOriginX'] - cs / 2 - skirt; MZ = d['gridOriginZ'] - cs / 2 - skirt
NX = round(d['gridWidth'] * cs + 2 * skirt) + 1; NZ = round(d['gridHeight'] * cs + 2 * skirt) + 1
h = [int(v) / 1000 for v in d['heights'].split(',')]
assert len(h) == NX * NZ
LV = d['water'][0]['level']          # −0.6
BED = min(h)                         # дно −2.4
BAND = 34.0                          # дальше этого от кромки ничего не трогаем

# ---------- кромка: точки пересечения изолинии LV по рёбрам сетки ----------
pts = []
for iz in range(NZ):
    for ix in range(NX):
        a = h[iz * NX + ix] - LV
        for jx, jz in ((ix + 1, iz), (ix, iz + 1)):
            if jx >= NX or jz >= NZ: continue
            b = h[jz * NX + jx] - LV
            if (a < 0) != (b < 0):
                t = a / (a - b)
                pts.append((MX + ix + (jx - ix) * t, MZ + iz + (jz - iz) * t))
G = collections.defaultdict(list)
for i, (x, z) in enumerate(pts): G[(math.floor(x / 4), math.floor(z / 4))].append(i)

def nearest(x, z, rmax=BAND):
    best = None; bd = rmax * rmax; k = math.ceil(rmax / 4); cx, cz = math.floor(x / 4), math.floor(z / 4)
    for r in range(0, k + 1):           # кольцами — обычно хватает ближних
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if max(abs(dx), abs(dz)) != r: continue
                for i in G.get((cx + dx, cz + dz), ()):
                    px, pz = pts[i]; dd = (px - x) ** 2 + (pz - z) ** 2
                    if dd < bd: bd = dd; best = i
        if best is not None and (r * 4) ** 2 > bd: break
    return best, math.sqrt(bd)

# ---------- шум ----------
def vnoise(seed, scale):
    tab = {}
    def g(ix, iz):
        k = (ix, iz)
        if k not in tab: tab[k] = random.Random(hash((seed, ix, iz)) & 0xffffffff).random()
        return tab[k]
    def f(x, z):
        fx, fz = x / scale, z / scale; ix, iz = math.floor(fx), math.floor(fz); tx, tz = fx - ix, fz - iz
        tx = tx * tx * (3 - 2 * tx); tz = tz * tz * (3 - 2 * tz)
        return (g(ix, iz) * (1 - tx) + g(ix + 1, iz) * tx) * (1 - tz) + (g(ix, iz + 1) * (1 - tx) + g(ix + 1, iz + 1) * tx) * tz
    return f
n_len = vnoise(21, 22)     # пологость вдоль берега
n_edge = vnoise(22, 3.5)   # рваный край песка
n_edge2 = vnoise(23, 1.3)
n_beach = vnoise(24, 20)   # чередование пляж / лес вдоль берега (участки ~20–40 м)

# ---------- пляжи: центр на кромке, радиус ядра ----------
def shore_point(x, z): return pts[nearest(x, z, 60)[0]]
BEACHES = [(shore_point(113.5, -36.0), 13.0, 1.0)]    # пляж Ильи (песок 31.10) — всегда пляж
BEACH_SHARE = 0.59   # порог шума: выше — пляж; ~40 % кромки в песке, остальное — лес к воде
def beach_of(px, pz):
    t = min(1.0, max(0.0, (n_beach(px, pz) - BEACH_SHARE) / 0.14))
    b = t * t * (3 - 2 * t)
    for (cx, cz), core, k in BEACHES:
        dd = math.hypot(px - cx, pz - cz)
        t = 1.0 if dd <= core else max(0.0, 1 - (dd - core) / 7.0)
        b = max(b, k * t * t * (3 - 2 * t))
    return b

# ---------- профиль ----------
def herm(t, p0, p1, m0, m1):
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1

def prof(s, L, W):
    """s<0 — суша (до 0 на −L), s>0 — вода (до дна на W). Гладкий, без излома на кромке."""
    drop = 0.0 - LV                       # 0.6 над водой
    k = 2 * drop / L                      # уклон у кромки
    if s <= -L: return 0.0
    if s <= 0:
        t = (s + L) / L; return -drop * t * t
    if s >= W: return BED
    return herm(s / W, LV, BED, -k * W, 0.0)

def old_prof(s):
    return max(BED, min(0.0, -0.25 * (s + 2.4)))

def params(px, pz):
    v = n_len(px, pz); b = beach_of(px, pz)
    L = 6.0 + 3.0 * v; W = 18.0 + 8.0 * v              # лесной берег: 6–9 м суши, 18–26 м до дна
    L = L * (1 - b) + 15.0 * b; W = W * (1 - b) + 40.0 * b  # пляж: 15 м пологой суши, 40 м мелководья
    return L, W, b

PCACHE = {}
def params_i(i):
    if i not in PCACHE: PCACHE[i] = params(*pts[i])
    return PCACHE[i]

def avg_params(cx, cz, r):
    # дно: параметры усреднены по участку кромки радиуса r — без «лучей» от стыка пляж/лес
    k = math.ceil(r / 4); gx, gz = math.floor(cx / 4), math.floor(cz / 4); sl = sw = sb = sw8 = 0.0
    for dx in range(-k, k + 1):
        for dz in range(-k, k + 1):
            for i in G.get((gx + dx, gz + dz), ()):
                px, pz = pts[i]; dd = math.hypot(px - cx, pz - cz)
                if dd > r: continue
                w = 1 - dd / r; L, W, b = params_i(i); sl += w * L; sw += w * W; sb += w * b; sw8 += w
    return (sl / sw8, sw / sw8, sb / sw8) if sw8 else params(cx, cz)

# ---------- новый рельеф ----------
newh = h[:]; sfield = {}; changed = 0
for iz in range(NZ):
    for ix in range(NX):
        x, z = MX + ix, MZ + iz
        i, dist = nearest(x, z)
        if i is None: continue
        o = h[iz * NX + ix]
        wet = o < LV
        s = dist if wet else -dist
        px, pz = pts[i]
        L, W, b = params(px, pz) if not wet else avg_params(px, pz, 4.0 + 0.6 * dist)
        sfield[(ix, iz)] = (s, b)
        if (not wet and dist > L + 0.5) or (wet and o <= BED + 1e-3 and dist > W + 0.5): continue
        nv = o - old_prof(s) + prof(s, L, W) if not wet else prof(s, L, W)
        if not wet and o > 0.05:            # холм у воды: только мягкий спуск к кромке, не срезаем
            nv = min(o, max(nv, o - 0.6))
        nv = max(nv, LV + 0.02) if not wet else min(nv, LV - 0.02)
        nv = max(BED, nv)
        if abs(nv - o) > 1e-3: newh[iz * NX + ix] = nv; changed += 1

# мягкое сглаживание в полосе (знак относительно воды сохраняется)
for it in range(8):                     # суша — 2 прохода, дно — 8 (иначе «лучи» на стыке пляж/лес)
    sm = newh[:]
    for (ix, iz), (s, b) in sfield.items():
        if not (0 < ix < NX - 1 and 0 < iz < NZ - 1) or abs(s) > 30: continue
        if it >= 2 and s < 1.0: continue
        o = h[iz * NX + ix]
        acc = sum(newh[(iz + dz) * NX + ix + dx] for dx in (-1, 0, 1) for dz in (-1, 0, 1)) / 9
        v = 0.5 * newh[iz * NX + ix] + 0.5 * acc
        v = max(v, LV + 0.02) if o >= LV else min(v, LV - 0.02)
        sm[iz * NX + ix] = v
    newh = sm

def H(arr, x, z):
    fx = x - MX; fz = z - MZ; ix = min(max(math.floor(fx), 0), NX - 2); iz = min(max(math.floor(fz), 0), NZ - 2)
    tx, tz = fx - ix, fz - iz
    a = arr[iz * NX + ix] * (1 - tx) + arr[iz * NX + ix + 1] * tx
    c = arr[(iz + 1) * NX + ix] * (1 - tx) + arr[(iz + 1) * NX + ix + 1] * tx
    return a * (1 - tz) + c * tz

def S(x, z):
    ix, iz = round(x - MX), round(z - MZ)
    return sfield.get((ix, iz))

# ---------- песок (Ground054 = карта 0, канал B) ----------
pm = d['paintPxPerM']; pmx, pmz = d['paintMinX'], d['paintMinZ']
files = [src.replace('.json', '_paint.png' if m == 0 else f'_paint{m + 1}.png') for m in range(3)]
ims = [Image.open(f).convert('RGBA') for f in files]; P = [im.load() for im in ims]; PW, PH = ims[0].size
SAND = (0, 2)
old_sand = new_sand = 0
for row in range(PH):
    z = pmz + (PH - 1 - row + 0.5) / pm
    if z < MZ or z > MZ + NZ - 1: continue
    for col in range(PW):
        x = pmx + (col + 0.5) / pm
        if x < MX or x > MX + NX - 1: continue
        sb = S(x, z)
        if sb is None or abs(sb[0]) > 23: continue
        i, dist = nearest(x, z, 25)
        if i is None: continue
        s = dist if H(h, x, z) < LV else -dist          # точное расстояние до кромки, без ступенек сетки
        p = list(P[0][col, row])
        old_sand += p[2] > 127
        b = beach_of(*pts[i])
        a = 0.0
        if b > 0.02:
            # суша: ширина пляжа 2.5–5 м с рваным краем; вода: песок виден на мелководье до ~5 м
            width = (2.5 + 2.5 * n_edge(x, z) + 0.8 * (n_edge2(x, z) - 0.5)) * b
            if s <= 0: a = max(0.0, min(1.0, (width + s) / 1.2))
            else: a = max(0.0, min(1.0, 1 - s / (5.0 * b + 0.01))) * 0.85
            a *= min(1.0, b * 1.6)
        A = int(round(255 * a))
        if A == p[2] and A == 0: continue
        if A > 0:
            keep = 1 - a
            for m in range(3):
                q = list(P[m][col, row])
                for c in range(4):
                    if (m, c) != SAND: q[c] = int(q[c] * keep)
                if m == 0: q[2] = A
                P[m][col, row] = tuple(q)
        else:
            p[2] = 0; P[0][col, row] = tuple(p)
        new_sand += A > 127

# ---------- растения ----------
plants = d['plants']; kept = []; moved = removed = 0
rnd = random.Random(3111)
def sand_at(x, z):
    col = int((x - pmx) * pm); row = PH - 1 - int((z - pmz) * pm)
    return P[0][col, row][2] / 255 if 0 <= col < PW and 0 <= row < PH else 0
for p in plants:
    x, z = p['x'], p['z']
    dh = H(newh, x, z) - H(h, x, z)
    if H(newh, x, z) < LV + 0.05: removed += 1; continue
    sa = sand_at(x, z)
    if sa > 0.45 and 'pebble' not in p['id'] and 'rock' not in p['id']: removed += 1; continue
    if abs(dh) > 1e-3: p['y'] = round(p['y'] + dh, 4); moved += 1
    kept.append(p)
for o in d['objects']:
    x, z = o['pos']['x'], o['pos']['z']
    dh = H(newh, x, z) - H(h, x, z)
    if abs(dh) > 1e-3 and o['id'].startswith(('veg', 'deco')): o['pos']['y'] += dh; moved += 1
# ---------- у воды: галька на пляжах, лес до кромки на лесных участках ----------
maxn = collections.Counter()
for p in kept: maxn[p['id']] = max(maxn[p['id']], p['n'])
for o in d['objects']: maxn[o['id']] = max(maxn[o['id']], o['number'])
PATHY = [(0, 1), (0, 3), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]   # Ground037/103, Mud, Path, Stone*
def pathy(x, z):
    col = int((x - pmx) * pm); row = PH - 1 - int((z - pmz) * pm)
    if not (0 <= col < PW and 0 <= row < PH): return 1
    return sum(P[m][col, row][c] for m, c in PATHY) / 255
class Hash:
    def __init__(s, c): s.c = c; s.g = collections.defaultdict(list)
    def add(s, x, z): s.g[(math.floor(x / s.c), math.floor(z / s.c))].append((x, z))
    def any(s, x, z, r):
        k = math.ceil(r / s.c); cx, cz = math.floor(x / s.c), math.floor(z / s.c)
        return any((a - x) ** 2 + (b - z) ** 2 < r * r for dx in range(-k, k + 1) for dz in range(-k, k + 1)
                   for a, b in s.g.get((cx + dx, cz + dz), ()))
def fam(i):
    for k in ('spruce', 'tree', 'grass_bush', 'grass_tuft', 'bush', 'flower', 'fern'):
        if k in i: return k
trees, bushes, grass = Hash(5), Hash(4), Hash(1.5)
orig = Hash(3)
for p in kept: orig.add(p['x'], p['z'])
for p in kept:
    f = fam(p['id'])
    (trees if f in ('tree', 'spruce') else bushes if f == 'bush' else grass if f else Hash(1)).add(p['x'], p['z'])
for o in d['objects']:
    if fam(o['id']) in ('tree', 'spruce'): trees.add(o['pos']['x'], o['pos']['z'])
def vid(base, n): return base if n == 1 else f'{base}_{n}'
added = collections.Counter()
def put(i, x, z, yoff=-0.1):
    maxn[i] += 1
    kept.append({'id': i, 'x': round(x, 4), 'y': round(H(newh, x, z) + yoff, 4), 'z': round(z, 4),
                 'r': round(rnd.uniform(0, 360), 3), 'n': maxn[i]}); added[i.split('_')[1]] += 1
cands = []
for (ix, iz), (s0, b0) in sfield.items():
    if -8.5 < s0 < 0.5:
        for _ in range(3): cands.append((MX + ix + rnd.uniform(-0.5, 0.5), MZ + iz + rnd.uniform(-0.5, 0.5)))
rnd.shuffle(cands)
for x, z in cands:
    i, dist = nearest(x, z, 12)
    if i is None or H(newh, x, z) < LV + 0.04: continue
    s = -dist; b = beach_of(*pts[i]); sa = sand_at(x, z)
    if pathy(x, z) > 0.3: continue
    if s < -1.5 and not orig.any(x, z, 4.5): continue   # расчищено руками (тропа к воде) — не засаживать
    if sa > 0.3:                                        # пляж: редкая галька у воды
        if s > -2.5 and rnd.random() < 0.03 and not grass.any(x, z, 1.2):
            put(vid('veg_pebble_brown' if rnd.random() < 0.5 else 'veg_pebble', rnd.randint(1, 4)), x, z, -0.08); grass.add(x, z)
        continue
    if b > 0.35: continue                              # трава за песком остаётся как была
    # лесной берег: трава до самой воды, папоротник и кусты, деревья с 2,5 м
    if s < -2.5 and not trees.any(x, z, 5.0) and rnd.random() < 0.5:
        put(vid('veg_spruce', rnd.randint(1, 3)) if rnd.random() < 0.35 else vid('veg_tree', rnd.randint(1, 5)), x, z); trees.add(x, z); continue
    if s < -1.0 and not bushes.any(x, z, 3.5) and not trees.any(x, z, 1.8) and rnd.random() < 0.25:
        put(vid('veg_bush', rnd.choice((1, 2, 3, 5, 1, 2, 3, 5, 4))), x, z); bushes.add(x, z); continue
    if grass.any(x, z, 0.85) or trees.any(x, z, 0.7) or bushes.any(x, z, 0.9): continue
    r = rnd.random()
    if r < 0.12 and s < -0.8: i2 = vid('veg_fern', rnd.randint(1, 3))
    elif r < 0.30: i2 = vid('veg_grass_bush', rnd.randint(1, 3))
    elif r < 0.33: i2 = vid('veg_flower', rnd.randint(1, 5))
    else: i2 = vid('veg_grass_tuft', rnd.randint(1, 4))
    put(i2, x, z); grass.add(x, z)
added = sum(added.values()), dict(added)
d['plants'] = kept

# ---------- проверки ----------
wet0 = sum(v < LV for v in h); wet1 = sum(v < LV for v in newh)
flip = sum((a < LV) != (b < LV) for a, b in zip(h, newh))
print('узлов рельефа изменено', changed, '; мокрых было/стало', wet0, wet1, '; сменили сторону', flip)
print('песок (px > 50 %) было', old_sand, 'стало', new_sand, f'({old_sand / 16:.0f} → {new_sand / 16:.0f} м²)')
print('растений: поднято/опущено', moved, 'убрано с песка/кромки', removed, 'у воды добавлено', added)
bl = sum(1 for q in pts if beach_of(*q) > 0.5); print(f'кромка в песке {bl / len(pts):.0%}')
d['heights'] = ','.join(str(int(round(v * 1000))) for v in newh)
out = src if WRITE else sys.argv[2]
if WRITE:
    tag = '.bak-before-shore-' + datetime.date.today().strftime('%d%m')
    shutil.copy2(src, src + tag)
    for f in files: shutil.copy2(f, f + tag)
    print('бэкап', tag)
json.dump(d, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
for m, im in enumerate(ims):
    im.save(out.replace('.json', '_paint.png' if m == 0 else f'_paint{m + 1}.png'))
print('записано', out)
