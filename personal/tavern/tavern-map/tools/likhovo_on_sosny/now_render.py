import json, glob, os, sys
from PIL import Image, ImageDraw
D = 'now'
def load(c): return {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(f'{D}/{c}/*.json')}
marks, roads, strokes, areas = load('marks'), load('roads'), load('strokes'), load('areas')
xs = [m['x'] for m in marks.values()] + [v for r in roads.values() for v in r['pts'][0::2]] + [v for s in strokes.values() for v in s['pts'][0::2]]
ys = [m['y'] for m in marks.values()] + [v for r in roads.values() for v in r['pts'][1::2]] + [v for s in strokes.values() for v in s['pts'][1::2]]
print('bbox', min(xs), max(xs), min(ys), max(ys))
X0, X1, Y0, Y1 = min(xs) - 0.5, max(xs) + 0.5, min(ys) - 0.5, max(ys) + 0.5
K = 200
W, H = int((X1 - X0) * K), int((Y1 - Y0) * K)
def px(x, y): return ((x - X0) * K, (Y1 - y) * K)
img = Image.new('RGBA', (W, H), (59, 87, 64, 255))
L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for s in sorted(strokes.values(), key=lambda s: s.get('t', 0)):
    p = s['pts']; q = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]; w = max(1, int(s['size'] * K))
    m = Image.new('L', (W, H), 0); g = ImageDraw.Draw(m)
    if len(q) > 1: g.line(q, fill=255, width=w, joint='curve')
    for a in q: g.ellipse([a[0]-w/2, a[1]-w/2, a[0]+w/2, a[1]+w/2], fill=255)
    col = (0, 0, 0, 0) if s.get('erase') else tuple(int(s['color'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
    L.paste(Image.new('RGBA', (W, H), col), (0, 0), m)
img.alpha_composite(L); g = ImageDraw.Draw(img)
for r in roads.values():
    p = r['pts']; q = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]; w = max(2, int(max(r.get('ws') or [r['w'] or 0.1]) * K))
    g.line(q, fill=(86, 135, 160) if r['kind'] == 'river' else (94, 93, 90), width=w, joint='curve')
    g.text(q[0], r['kind'][0], fill=(255, 255, 0))
for a in areas.values():
    p = a['pts']; q = [px(p[i], p[i+1]) for i in range(0, len(p), 2)]
    g.polygon(q, outline=(74, 144, 194)); g.text(q[0], 'zone', fill=(255, 255, 255))
for m in marks.values():
    u, v = px(m['x'], m['y']); k = m['kind']
    r = {'hill': 30, 'cottage': 9}.get(k, 4 if k in ('tree', 'fir') else 7)
    col = {'tree': (110, 160, 70), 'fir': (40, 90, 50), 'cottage': (220, 60, 60), 'hill': (124, 149, 80)}.get(k, (255, 0, 255))
    g.ellipse([u-r, v-r, u+r, v+r], fill=col if k != 'hill' else None, outline=col if k == 'hill' else (0, 0, 0))
    if k not in ('tree', 'fir'): g.text((u + 8, v - 6), k, fill=(255, 255, 255))
for x in range(int(X0), int(X1) + 1):
    u, _ = px(x, 0); g.line([(u, 0), (u, 8)], fill=(255, 255, 255)); g.text((u + 2, 10), str(x), fill=(255, 255, 255))
for y in range(int(Y0), int(Y1) + 1):
    _, v = px(0, y); g.line([(0, v), (8, v)], fill=(255, 255, 255)); g.text((10, v - 5), str(y), fill=(255, 255, 255))
img.save('now.png')
for r in roads.values(): print(r['kind'], r['pts'], r.get('ws'))
