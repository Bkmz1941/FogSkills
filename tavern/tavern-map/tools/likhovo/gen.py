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

# --- water: river Сосновка (NW -> SE), a stream from Чёрное озеро, the lake itself
river = [(-5.2, 2.3), (-4.1, 1.95), (-3.0, 1.2), (-2.0, 0.75), (-1.0, 0.35), (0.0, 0.05), (1.1, -0.35), (2.2, -0.55), (3.2, -1.2), (4.1, -2.3), (5.2, -2.9)]
road('river', river, [0.05, 0.06, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16])
stream = [(-2.35, -2.0), (-2.05, -1.3), (-1.75, -0.6), (-1.45, -0.05), (-1.2, 0.42)]
road('river', stream, [0.04, 0.035, 0.035, 0.04, 0.045])
lake_c = (-2.95, -2.55)
stroke('#3D6A80', 0.75, [(-3.7, -2.3), (-3.2, -2.05), (-2.6, -2.15), (-2.3, -2.55), (-2.55, -2.95), (-3.15, -3.05), (-3.65, -2.8), (-3.7, -2.3)])
stroke('#3D6A80', 0.6, [(-3.3, -2.5), (-2.75, -2.5)])
stroke('#1E3646', 0.38, [(-3.35, -2.5), (-3.0, -2.45), (-2.7, -2.6)])
stroke('#D2BE8C', 0.08, [(-2.2, -2.75), (-2.1, -2.95), (-2.3, -3.15)])

# --- roads
highway = [(0.35, -4.3), (0.25, -2.6), (0.15, -1.4), (0.0, 0.05), (-0.1, 0.9), (-0.1, 1.5), (0.0, 2.4), (0.15, 3.1), (0.35, 4.3)]
road('road', highway, 0.1)
for h in crossings(highway, river):
    mark('bridge5', h[0], h[1], rot_along(h[2], h[3]))
# Лихово streets
road('road', [(-1.4, 3.0), (-0.6, 3.05), (0.15, 3.1), (1.0, 3.15), (1.7, 3.2)], 0.08)
road('road', [(-0.75, 2.45), (-0.7, 3.05), (-0.65, 3.7)], 0.06)
road('road', [(0.9, 2.55), (1.0, 3.15), (1.05, 3.75)], 0.06)
# to Ольховка (west) and on to the village street
olh = [(-0.1, 1.5), (-1.0, 1.6), (-1.9, 1.75), (-2.6, 1.85), (-3.1, 2.15), (-3.8, 2.35), (-4.6, 2.75)]
road('road', olh, 0.06)
# to Заречье (east)
zar = [(-0.1, 0.9), (0.9, 1.0), (1.9, 0.95), (2.8, 0.85), (3.8, 0.95)]
road('road', zar, 0.06)
# to Озерки (west of the highway, south) by the lake
oz = [(0.25, -2.6), (-0.5, -2.75), (-1.2, -2.85), (-1.9, -2.95)]
road('road', oz, 0.06)
# forest track Ольховка -> Озерки, crosses the river and the stream: wooden bridges
track = [(-2.6, 1.85), (-2.75, 1.2), (-2.85, 0.6), (-2.55, -0.4), (-2.2, -1.3), (-1.9, -2.2), (-1.85, -2.9)]
road('road', track, 0.045)
for h in crossings(track, river) + crossings(track, stream):
    mark('bridge2', h[0], h[1], rot_along(h[2], h[3]))
# «Сосны»: stop on the highway, dirt road to the cottage by the river
road('road', [(0.15, -1.4), (0.8, -1.55), (1.45, -1.35), (1.9, -1.05)], 0.05)
# path from Лихово up Маячная гора
road('road', [(1.7, 3.2), (2.4, 3.15), (2.95, 3.0)], 0.04)

# --- Лихово (посёлок, центр округи)
mark('church', -0.55, 3.45)
stroke('#8A8A80', 0.32, [(-0.2, 3.05), (0.5, 3.12)])
for x, y, r in [(0.6, 3.5, 0), (0.62, 2.72, 0), (-0.3, 2.65, 0), (1.35, 3.5, 0), (1.45, 2.8, 0), (-1.1, 2.65, 0)]:
    mark('townhouse', x, y, r)
mark('busstop', 0.3, 2.85, rot_face(1, 0))
mark('busstop', 0.45, -1.3, rot_face(-1, 0))
mark('sawmill', 1.75, 3.95, 20)
for x, y in [(-1.35, 3.45), (-1.25, 3.85), (-0.25, 3.95), (0.55, 4.05), (1.55, 2.45), (-0.25, 2.25), (0.55, 2.3)]:
    mark('izba', x, y, rot_face(0.15 - x, 3.1 - y))
# --- villages
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
WET = dense(river) + dense(stream) + [(lake_c[0] + dx * 0.1, lake_c[1] + dy * 0.1) for dx in range(-8, 9) for dy in range(-5, 6)]
DRY = dense(highway) + dense(track) + dense(zar) + dense(oz) + dense(olh)
v_olh = village(-3.6, 2.4, 9, 0.75, dense(olh[3:]))
v_zar = village(2.85, 0.95, 7, 0.7, dense(zar[2:]))
v_oz = village(-1.45, -2.9, 5, 0.45, dense(oz[1:]))
mark('cross', -2.4, 2.0)
mark('cross', 1.55, 1.05)
mark('cross', -0.15, -2.45)
mark('cross', 1.2, -1.25)
mark('pier', -2.25, -2.85, rot_along(1, -0.2))
mark('pier', 2.15, -0.75, rot_along(0.1, -1))
mark('cottage', 1.98, -0.92, rot_face(-1, -0.5))
stroke('#D2BE8C', 0.12, [(1.85, -1.0), (2.1, -0.95)])
mark('cottage', -4.4, -2.0, rot_face(1, -0.4))
# --- Маячная гора with the tower
mark('hill', 3.35, 2.95)
mark('tower', 3.35, 3.0)
# --- fields and meadows by the villages
stroke('#B5A25E', 0.45, [(-4.3, 3.25), (-3.5, 3.35), (-2.8, 3.15)])
stroke('#8AA05A', 0.4, [(2.4, 1.6), (3.4, 1.65)])
stroke('#B5A25E', 0.35, [(-0.9, -3.35), (-0.3, -3.4)])
stroke('#8AA05A', 0.3, [(1.9, 2.3), (2.5, 2.2)])
# --- zones with names
area('Лихово', '#C0392B', [(-1.75, 2.15), (2.15, 2.15), (2.25, 4.25), (-1.75, 4.25)])
area('Ольховка', '#D98E2B', [(-4.7, 2.3), (-3.3, 1.85), (-2.45, 2.05), (-2.45, 2.85), (-4.7, 3.0)])
area('Заречье', '#4F9B5E', [(1.9, 0.45), (3.9, 0.5), (3.9, 1.4), (1.9, 1.35)])
area('Озерки', '#8E5AA8', [(-2.05, -3.3), (-0.75, -3.3), (-0.75, -2.45), (-2.05, -2.45)])
area('«Сосны»', '#4A90C2', [(1.55, -1.3), (2.4, -1.25), (2.4, -0.62), (1.55, -0.62)])
area('Маячная гора', '#9A9A9A', [(2.9, 2.55), (3.85, 2.55), (3.85, 3.45), (2.9, 3.45)])
area('Чёрное озеро', '#3B5BA5', [(-3.9, -3.25), (-2.1, -3.25), (-2.1, -1.9), (-3.9, -1.9)])
json.dump({'marks': marks, 'roads': roads, 'strokes': strokes, 'areas': areas}, open(os.path.dirname(OUT) + '/base.json', 'w'), ensure_ascii=False)
print(len(marks), len(roads), len(strokes), len(areas))
