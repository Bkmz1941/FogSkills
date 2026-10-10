import json, math, random
from PIL import Image, ImageDraw
random.seed(11)
d = json.load(open('base.json'))
X0, X1, Y0, Y1 = -5.2, 5.2, -4.4, 4.5
K = 120
W, H = int((X1 - X0) * K), int((Y1 - Y0) * K)
def px(x, y): return ((x - X0) * K, (Y1 - y) * K)
mask = Image.new('L', (W, H), 0); dm = ImageDraw.Draw(mask)
for r in d['roads']:
    p = r['pts']; pts = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]
    w = max(r['ws']) + 0.08
    dm.line(pts, fill=255, width=int(w * K), joint='curve')
    for q in pts: dm.ellipse([q[0]-w*K/2, q[1]-w*K/2, q[0]+w*K/2, q[1]+w*K/2], fill=255)
for s in d['strokes']:
    p = s['pts']; pts = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]
    w = s['size'] + 0.06
    if len(pts) > 1: dm.line(pts, fill=255, width=int(w * K), joint='curve')
    for q in pts: dm.ellipse([q[0]-w*K/2, q[1]-w*K/2, q[0]+w*K/2, q[1]+w*K/2], fill=255)
def inpoly(x, y, P):
    c = False
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[i-1]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c = not c
    return c
zones = [[(a['pts'][i], a['pts'][i+1]) for i in range(0, len(a['pts']), 2)] for a in d['areas'] if a['name'] not in ('Маячная гора', 'Чёрное озеро')]
RAD = {'izba': 0.13, 'townhouse': 0.2, 'church': 0.25, 'sawmill': 0.3, 'cottage': 0.2, 'hill': 0.4, 'tower': 0.2, 'busstop': 0.08, 'cross': 0.07, 'pier': 0.18, 'bridge2': 0.3, 'bridge5': 0.3}
obst = [(m['x'], m['y'], RAD.get(m['kind'], 0.15)) for m in d['marks']]
R = 0.17
trees, pts = [], []
for _ in range(120000):
    x, y = random.uniform(X0 + 0.15, X1 - 0.15), random.uniform(Y0 + 0.15, Y1 - 0.15)
    # a few natural clearings
    if math.hypot(x - 3.9, y + 3.3) < 0.5 or math.hypot(x + 4.2, y + 0.6) < 0.45 or math.hypot(x - 1.0, y + 3.4) < 0.4: continue
    u, v = px(x, y)
    if mask.getpixel((int(u), int(v))): continue
    if any(inpoly(x, y, P) for P in zones): continue
    if any(math.hypot(x - a, y - b) < r for a, b, r in obst): continue
    if any((x - a) ** 2 + (y - b) ** 2 < R * R for a, b in pts): continue
    pts.append((x, y)); trees.append({'kind': 'fir' if random.random() < 0.6 else 'tree', 'x': round(x, 3), 'y': round(y, 3)})
d['trees'] = trees
json.dump(d, open('full.json', 'w'), ensure_ascii=False)
print('trees', len(trees))
# preview
img = Image.new('RGB', (W, H), (59, 87, 64)); g = ImageDraw.Draw(img)
for s in d['strokes']:
    p = s['pts']; q = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]; w = s['size']
    col = tuple(int(s['color'][i:i+2], 16) for i in (1, 3, 5))
    if len(q) > 1: g.line(q, fill=col, width=int(w*K), joint='curve')
    for a in q: g.ellipse([a[0]-w*K/2, a[1]-w*K/2, a[0]+w*K/2, a[1]+w*K/2], fill=col)
for r in d['roads']:
    p = r['pts']; q = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]; w = max(2, int(max(r['ws']) * K))
    g.line(q, fill=(86, 135, 160) if r['kind'] == 'river' else (94, 93, 90), width=w, joint='curve')
for a in d['areas']:
    p = a['pts']; q = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]
    g.polygon(q, outline=tuple(int(a['color'][i:i+2], 16) for i in (1, 3, 5)))
    g.text(q[0], a['name'], fill=(255, 255, 255))
for t in trees:
    u, v = px(t['x'], t['y']); r = 3
    g.ellipse([u-r, v-r, u+r, v+r], fill=(40, 90, 50) if t['kind'] == 'fir' else (110, 160, 70))
COL = {'izba': (139, 90, 54), 'townhouse': (176, 100, 74), 'church': (240, 235, 220), 'sawmill': (60, 55, 52), 'cottage': (201, 154, 98), 'hill': (124, 149, 80), 'tower': (200, 40, 40), 'busstop': (226, 192, 68), 'cross': (122, 86, 56), 'pier': (156, 116, 72), 'bridge2': (156, 116, 72), 'bridge5': (216, 212, 204)}
for m in d['marks']:
    u, v = px(m['x'], m['y']); r = {'hill': 18, 'church': 7, 'sawmill': 8, 'townhouse': 6}.get(m['kind'], 4)
    g.ellipse([u-r, v-r, u+r, v+r], fill=COL.get(m['kind'], (255, 0, 255)), outline=(0, 0, 0))
img.save('preview.png')
