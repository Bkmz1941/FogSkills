# Туман над водой у границы карты: водные клетки сетки в полосе BAND от края — зона Fog + клубы env_fog
# на зеркале воды. Наружные STRONG клеток — сильный туман, дальше к берегу — слабый (мягкая кромка).
# python3 -I lake_fog.py <level.json> [--write]   (бэкап .bak-before-lakefog-ДДММ)
# python3 -I lake_fog.py <level.json> --remove [--write]   снять обе зоны и клубы в их клетках (бэкап .bak-before-lakefog-remove-ДДММ)
import json, math, sys, shutil, datetime, collections
PATH = sys.argv[1]; WRITE = '--write' in sys.argv; REMOVE = '--remove' in sys.argv
BAND, STRONG = 6, 4
d = json.load(open(PATH, encoding='utf-8'))
if REMOVE:
    # Клубы снимаем по клеткам зон (как RemoveZone → FillZoneVolumes(false) в игре); клубы вне
    # клеток зон не трогаем — их считаем и показываем, снимать в игре или руками.
    zs = [z for z in d['zones'] if z.get('slug') in ('fog_lake', 'fog_lake_soft')]
    cells = {(round(c['x'], 2), round(c['z'], 2)) for z in zs for c in z.get('cells') or []}
    before = len(d['objects'])
    d['objects'] = [o for o in d['objects'] if not (o['id'].startswith('env_fog') and (round(o['pos']['x'], 2), round(o['pos']['z'], 2)) in cells)]
    d['zones'] = [z for z in d['zones'] if z not in zs]
    left = collections.Counter(o['id'] for o in d['objects'] if o['id'].startswith('env_fog'))
    print(f"снято зон {len(zs)} ({', '.join(z['slug'] + ' ' + str(len(z.get('cells') or [])) for z in zs)}), клубов {before - len(d['objects'])}; осталось клубов вне их клеток {dict(left) or 0}")
    if WRITE:
        bak = PATH + '.bak-before-lakefog-remove-' + datetime.date.today().strftime('%d%m'); shutil.copy2(PATH, bak); print('бэкап', bak)
        json.dump(d, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False); print('записано', PATH)
    sys.exit(0)
cs = d['cellSize']; sk = d['skirt'] * cs; W, H = d['gridWidth'], d['gridHeight']; ox, oz = d['gridOriginX'], d['gridOriginZ']
MX = ox - cs / 2 - sk; MZ = oz - cs / 2 - sk; NX = round(W * cs + 2 * sk) + 1; NZ = round(H * cs + 2 * sk) + 1
hv = [int(v) / 1000 for v in d['heights'].split(',')]
def node(ix, iz): return hv[min(max(iz, 0), NZ - 1) * NX + min(max(ix, 0), NX - 1)]
def ground(x, z):
    fx = x - MX; fz = z - MZ; ix = math.floor(fx); iz = math.floor(fz); tx = fx - ix; tz = fz - iz
    return (node(ix, iz) * (1 - tx) + node(ix + 1, iz) * tx) * (1 - tz) + (node(ix, iz + 1) * (1 - tx) + node(ix + 1, iz + 1) * tx) * tz
LEVEL = d['water'][0]['level'] if d.get('water') else -0.6
def wet(i, j):
    cx, cz = ox + i * cs, oz + j * cs
    return sum(1 for dx in (-1, 0, 1) for dz in (-1, 0, 1) if ground(cx + dx, cz + dz) < LEVEL - 0.05) >= 5
edge = lambda i, j: min(i, j, W - 1 - i, H - 1 - j)
strong = [(i, j) for i in range(W) for j in range(H) if edge(i, j) < STRONG and wet(i, j)]
weak = [(i, j) for i in range(W) for j in range(H) if STRONG <= edge(i, j) < BAND and wet(i, j)]
taken = {(round(o['pos']['x'], 2), round(o['pos']['z'], 2)) for o in d['objects'] if o['id'].startswith('env_fog')}
def zone(name, slug, kind, cells, rgb, strong_):
    return {"name": name, "slug": slug, "cr": rgb[0], "cg": rgb[1], "cb": rgb[2], "kind": kind, "strong": strong_,
            "fireSpread": False, "temp": float("nan"), "attackers": "", "exits": "", "signal": 2, "view": 2.0,
            "cells": [{"x": ox + i * cs, "y": 0.1, "z": oz + j * cs} for i, j in cells], "fine": [], "note": "",
            "marks": [], "events": [], "fog": False, "fogStrong": strong_, "fire": False, "fireStrong": True, "wind": False}
old = [z for z in d['zones'] if z.get('slug') in ('fog_lake', 'fog_lake_soft')]
d['zones'] = [z for z in d['zones'] if z.get('slug') not in ('fog_lake', 'fog_lake_soft')]
d['zones'].append(zone("Туман над озером", "fog_lake", 4, strong, (0.62, 0.72, 0.82), True))
d['zones'].append(zone("Туман над озером: кромка", "fog_lake_soft", 4, weak, (0.75, 0.82, 0.9), False))
added = collections.Counter()
for cells, fid in ((strong, 'env_fog'), (weak, 'env_fog_weak')):
    for i, j in cells:
        x, z = ox + i * cs, oz + j * cs
        if (round(x, 2), round(z, 2)) in taken: continue
        d['objects'].append({"pos": {"x": x, "y": max(ground(x, z), LEVEL) + 0.1, "z": z}, "rotY": 0.0, "id": fid, "number": 0})
        added[fid] += 1
sides = collections.Counter('восток' if i >= W - BAND else 'юг' if j < BAND else 'север' if j >= H - BAND else 'запад' for i, j in strong + weak)
print(f"уровень воды {LEVEL:.2f}; сильный туман {len(strong)} клеток, слабый {len(weak)}; по сторонам {dict(sides)}; заменено старых зон {len(old)}")
print("клубов добавлено", dict(added), "объектов стало", len(d['objects']))
if WRITE:
    bak = PATH + '.bak-before-lakefog-' + datetime.date.today().strftime('%d%m'); shutil.copy2(PATH, bak); print('бэкап', bak)
    json.dump(d, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False); print('записано', PATH)
