import json, math, random, os
random.seed(7)
OUT = os.path.dirname(os.path.abspath(__file__)) + '/db'
marks, roads, strokes, areas = [], [], [], []
T = 1791700000000
def mid(p, n): return p + str(n).zfill(4)
def mark(kind, x, y, rot=0):
    m = {'kind': kind, 'x': round(x, 3), 'y': round(y, 3)}
    if rot: m['rot'] = int(rot) % 360
    marks.append(m)
def road(kind, pts, ws):
    flat = [round(v, 4) for p in pts for v in p]
    if isinstance(ws, (int, float)): ws = [ws] * len(pts)
    roads.append({'kind': kind, 'pts': flat, 'ws': [round(w, 4) for w in ws], 'w': ws[-1], 'w0': ws[0] if kind == 'river' else None, 't': T + len(roads)})
def stroke(color, size, pts, erase=False):
    strokes.append({'color': color, 'size': size, 'erase': erase, 'pts': [round(v, 4) for p in pts for v in p], 't': T + len(strokes)})
def area(name, color, pts):
    areas.append({'name': name, 'color': color, 'pts': [round(v, 4) for p in pts for v in p], 't': T + len(areas)})
COS30 = math.cos(math.pi / 6)
def rot_along(dx, dy):
    # rotation that lays a bridge/pier span along the world direction (dx, dy); the map is drawn with y up
    want = math.atan2(-dy, dx)
    best, ba = 9, 0
    for a in range(0, 360):
        r = math.radians(a); X, Y = math.cos(r), math.sin(r)
        sx, sy = (X - Y) * COS30, (X + Y) * 0.5
        d = abs(((math.atan2(sy, sx) - want + math.pi / 2) % math.pi) - math.pi / 2)
        if d < best: best, ba = d, a
    return ba
def rot_face(dx, dy):
    # rotation that turns a house's door side (+Y) toward the world direction (dx, dy)
    want = math.atan2(-dy, dx)
    best, ba = 9, 0
    for a in range(0, 360):
        r = math.radians(a); X, Y = -math.sin(r), math.cos(r)
        sx, sy = (X - Y) * COS30, (X + Y) * 0.5
        d = abs(((math.atan2(sy, sx) - want + math.pi) % (2 * math.pi)) - math.pi)
        if d < best: best, ba = d, a
    return ba
def seg_hit(p1, p2, q1, q2):
    d = (p2[0]-p1[0])*(q2[1]-q1[1]) - (p2[1]-p1[1])*(q2[0]-q1[0])
    if abs(d) < 1e-12: return None
    t = ((q1[0]-p1[0])*(q2[1]-q1[1]) - (q1[1]-p1[1])*(q2[0]-q1[0])) / d
    u = ((q1[0]-p1[0])*(p2[1]-p1[1]) - (q1[1]-p1[1])*(p2[0]-p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1: return (p1[0]+t*(p2[0]-p1[0]), p1[1]+t*(p2[1]-p1[1]), p2[0]-p1[0], p2[1]-p1[1])
    return None
def crossings(a, b):
    out = []
    for i in range(len(a)-1):
        for j in range(len(b)-1):
            h = seg_hit(a[i], a[i+1], b[j], b[j+1])
            if h and all(math.hypot(h[0]-o[0], h[1]-o[1]) > 0.05 for o in out): out.append(h)
    return out


import glob
def village(cx, cy, n, spread, street):
    placed = []
    tries = 0
    while len(placed) < n and tries < 500:
        tries += 1
        x, y = cx + random.uniform(-spread, spread), cy + random.uniform(-spread * 0.55, spread * 0.55)
        if any(math.hypot(x - a, y - b) < 0.2 for a, b in placed): continue
        # keep off the street itself
        if min(math.hypot(x - p[0], y - p[1]) for p in street) < 0.1: continue
        if min(math.hypot(x - p[0], y - p[1]) for p in WET) < 0.22: continue
        if min(math.hypot(x - p[0], y - p[1]) for p in DRY) < 0.1: continue
        placed.append((x, y))
        nearest = min(street, key=lambda p: math.hypot(x - p[0], y - p[1]))
        mark('izba', x, y, rot_face(nearest[0] - x, nearest[1] - y))
    return placed
def dense(pts, step=0.05):
    out = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; n = max(1, int(math.hypot(b[0]-a[0], b[1]-a[1]) / step))
        out += [(a[0] + (b[0]-a[0]) * k / n, a[1] + (b[1]-a[1]) * k / n) for k in range(n)]
    return out + [pts[-1]]
NOW = '../now'
def loadc(c): return [json.load(open(p)) for p in glob.glob(f'{NOW}/{c}/*.json')]
ex_marks, ex_roads, ex_strokes, ex_areas = loadc('marks'), loadc('roads'), loadc('strokes'), loadc('areas')
ZONE = [(ex_areas[0]['pts'][i], ex_areas[0]['pts'][i+1]) for i in range(0, len(ex_areas[0]['pts']), 2)]
UP_END = (-5.438, 2.7913); DOWN_START = (-1.5357, -2.8264); ROAD_END = (-0.8401, -1.3104)
# --- water: continue Ilya's river up and down, a stream from Чёрное озеро
up = [(-8.7, 4.55), (-7.6, 4.2), (-6.5, 3.55), UP_END]
road('river', up, [0.1, 0.12, 0.14, 0.16])
down = [DOWN_START, (-1.05, -3.75), (-0.1, -4.55), (1.2, -5.2), (2.8, -5.6)]
road('river', down, [0.288, 0.29, 0.3, 0.31, 0.32])
river = up + [(-4.7132, 1.3691), (-3.8504, 0.9434), (-2.9818, 0.5548), (-2.8704, -0.548), (-2.6167, -1.1064), (-1.8457, -1.6864)] + down
lake_c = (-5.75, -3.7)
stream = [(-4.95, -3.35), (-3.9, -2.95), (-2.8, -2.6), (-1.652, -2.4)]
road('river', stream, [0.04, 0.045, 0.05, 0.055])
stroke('#3D6A80', 0.8, [(-6.5, -3.45), (-6.0, -3.15), (-5.35, -3.25), (-5.05, -3.65), (-5.3, -4.1), (-5.95, -4.2), (-6.45, -3.95), (-6.5, -3.45)])
stroke('#3D6A80', 0.65, [(-6.05, -3.65), (-5.45, -3.65)])
stroke('#1E3646', 0.4, [(-6.1, -3.65), (-5.75, -3.6), (-5.45, -3.75)])
stroke('#D2BE8C', 0.08, [(-4.95, -3.85), (-4.85, -4.05), (-5.05, -4.25)])
# --- roads
road('road', [ROAD_END, (-0.2, -1.5), (0.3, -1.62)], [0.075, 0.075, 0.08])
highway = [(0.65, -6.2), (0.45, -3.6), (0.3, -1.62), (0.2, 0.6), (0.0, 2.7), (0.05, 4.4), (0.3, 6.2)]
road('road', highway, 0.1)
for h in crossings(highway, river):
    mark('bridge5', h[0], h[1], rot_along(h[2], h[3]))
LC = (0.05, 4.4)
road('road', [(-1.5, 4.3), (-0.7, 4.35), LC, (0.9, 4.45), (1.7, 4.5)], 0.08)
road('road', [(-0.75, 3.75), (-0.7, 4.35), (-0.65, 5.0)], 0.06)
road('road', [(0.85, 3.85), (0.9, 4.45), (0.95, 5.05)], 0.06)
olh = [(-1.5, 4.3), (-2.6, 4.55), (-3.9, 4.75), (-5.2, 4.85), (-6.3, 4.85), (-7.6, 5.05)]
road('road', olh, 0.06)
zar = [(0.2, 1.3), (1.2, 1.45), (2.1, 1.5), (3.0, 1.45)]
road('road', zar, 0.06)
oz = [(0.42, -3.25), (-0.6, -3.55), (-1.9, -3.75), (-3.3, -4.05), (-4.5, -4.25)]
road('road', oz, 0.06)
for h in crossings(oz, river) + crossings(oz, stream):
    mark('bridge2', h[0], h[1], rot_along(h[2], h[3]))
road('road', [(1.7, 4.5), (2.3, 4.2), (2.75, 3.85)], 0.04)
# --- Лихово
mark('church', -0.55, 4.75)
stroke('#8A8A80', 0.32, [(-0.25, 4.38), (0.45, 4.42)])
for x, y in [(0.6, 4.8), (0.6, 4.02), (-0.3, 3.95), (1.35, 4.8), (1.45, 4.1), (-1.1, 3.95)]:
    mark('townhouse', x, y)
mark('busstop', 0.22, 4.15, rot_face(1, 0))
mark('busstop', 0.5, -1.45, rot_face(1, 0))
mark('sawmill', 1.7, 5.3, 20)
for x, y in [(-1.35, 4.75), (-1.25, 5.15), (-0.25, 5.25), (0.55, 5.35), (1.55, 3.75), (-0.25, 3.55), (0.55, 3.6)]:
    mark('izba', x, y, rot_face(LC[0] - x, LC[1] - y))
WET = dense(river) + dense(stream) + [(lake_c[0] + dx * 0.1, lake_c[1] + dy * 0.1) for dx in range(-9, 10) for dy in range(-6, 7)]
DRY = dense(highway) + dense(zar) + dense(oz) + dense(olh)
v_olh = village(-6.4, 5.25, 9, 0.8, dense(olh[3:]))
v_zar = village(2.1, 1.55, 7, 0.7, dense(zar[1:]))
v_oz = village(-4.1, -4.45, 5, 0.45, dense(oz[2:]))
mark('cross', -2.3, 4.7)
mark('cross', 1.0, 1.6)
mark('cross', 0.65, -2.4)
mark('cross', -0.5, -1.25)
mark('pier', -4.95, -3.75, rot_along(1, -0.3))
mark('cottage', -6.95, -3.4, rot_face(1, -0.3))
mark('hill', 2.9, 3.65)
mark('tower', 2.9, 3.7)
stroke('#B5A25E', 0.45, [(-7.4, 5.95), (-6.4, 6.0), (-5.5, 5.85)])
stroke('#8AA05A', 0.4, [(1.6, 2.2), (2.7, 2.25)])
stroke('#B5A25E', 0.35, [(-2.6, -4.55), (-1.8, -4.6)])
area('Лихово', '#C0392B', [(-1.75, 3.35), (2.1, 3.35), (2.2, 5.6), (-1.75, 5.6)])
area('Ольховка', '#D98E2B', [(-7.6, 4.6), (-5.2, 4.55), (-5.2, 5.6), (-7.6, 5.7)])
area('Заречье', '#4F9B5E', [(1.25, 1.05), (3.1, 1.05), (3.1, 2.0), (1.25, 2.0)])
area('Озерки', '#8E5AA8', [(-4.75, -4.85), (-3.25, -4.85), (-3.25, -3.95), (-4.75, -3.95)])
area('Маячная гора', '#9A9A9A', [(2.45, 3.25), (3.35, 3.25), (3.35, 4.1), (2.45, 4.1)])
area('Чёрное озеро', '#3B5BA5', [(-6.75, -4.45), (-4.85, -4.45), (-4.85, -2.95), (-6.75, -2.95)])
area('Остановка «пов. Сосны»', '#E2C044', [(0.35, -1.85), (0.95, -1.85), (0.95, -1.2), (0.35, -1.2)])
json.dump({'marks': marks, 'roads': roads, 'strokes': strokes, 'areas': areas}, open(os.path.dirname(OUT) + '/base.json', 'w'), ensure_ascii=False)
print(len(marks), len(roads), len(strokes), len(areas))
print('olh x river', crossings(olh, river), 'zar', crossings(zar, river))
