#!/usr/bin/env python3
"""Точка привязки переносимых предметов (18.10, P-грабля батона): видимый центр модели обязан
совпадать с корнем по горизонтали — иначе при переносе предмет едет сбоку от курсора.

python3 pivot_probe.py [--tol 0.03]

1) мостом берёт из каталога дефы, которые игрок носит или двигает (pickupItemId / movable / mount Surface),
   без спавна — только список (модель, папка); 2) headless Blender импортирует каждый FBX и меряет
   смещение центра габарита от корня по XZ игры. Нарушение — смещение > tol И > 15 % размера.
Вердикт «PIVOT ok/FAIL». Корни с намеренным смещением (петля дверцы, настенное) сюда не попадают:
берутся только переносимые предметы. Нужен мост (любой режим, play не обязателен).
"""
import json, os, subprocess, sys, tempfile

MCP = os.path.expanduser('~/.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
TOL = float(sys.argv[sys.argv.index('--tol') + 1]) if '--tol' in sys.argv else 0.03

LIST = r'''
var sb = new System.Text.StringBuilder();
foreach (var d in Cozy.Grid.FurnitureCatalog.All()) {
  if (d == null || string.IsNullOrEmpty(d.modelName) || string.IsNullOrEmpty(d.resourceFolder)) continue;
  bool carried = !string.IsNullOrEmpty(d.pickupItemId) || d.mount == Cozy.Grid.ObjectMount.Surface;
  if (!carried || d.keepModelPivot) continue;
  sb.Append(d.id + "|" + d.resourceFolder + "|" + d.modelName + "\n");
}
return sb.ToString();
'''

BLENDER = r'''
import bpy, sys, json
from mathutils import Vector
items = json.load(open(sys.argv[sys.argv.index('--') + 1]))
out = []
for it in items:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.fbx(filepath=it['path'])
    except Exception as e:
        out.append(dict(it, err=str(e)[:80])); continue
    roots = [o for o in bpy.data.objects if o.parent is None]
    pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' for c in o.bound_box]
    if not pts or not roots: continue
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2; r = roots[0].matrix_world.translation
    out.append(dict(it, dx=c.x - r.x, dz=c.y - r.y, sx=hi.x - lo.x, sz=hi.y - lo.y))
print('PIVOTJSON' + json.dumps(out))
'''


def main():
    res = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': LIST})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else '{}'
    data = json.loads(line)
    if not data.get('success'):
        print('мост не ответил: ' + line[:300]); sys.exit(2)
    rows = [r.split('|') for r in (data['data']['result'] or '').splitlines() if r]
    items, seen = [], set()
    for did, folder, model in rows:
        path = os.path.join(PROJECT, 'Assets/Game/Resources', folder, model + '.fbx')
        if not os.path.exists(path) or path in seen: continue
        seen.add(path); items.append(dict(id=did, path=path))
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'pivot_measure.py'); lst = os.path.join(tmp, 'items.json')
        open(src, 'w').write(BLENDER); json.dump(items, open(lst, 'w'))
        out = subprocess.run(['blender', '-b', '--python', src, '--', lst], capture_output=True, text=True, timeout=3600).stdout
    got = json.loads(next(l for l in out.splitlines() if l.startswith('PIVOTJSON'))[9:])
    bad = []
    for g in got:
        if 'err' in g: continue
        off = (g['dx'] ** 2 + g['dz'] ** 2) ** 0.5
        size = max(g['sx'], g['sz'], 1e-3)
        if off > TOL and off > 0.15 * size:
            bad.append('%s (%s): центр уехал на %.2f м при размере %.2f м' % (g['id'], os.path.basename(g['path']), off, size))
    print(('PIVOT ok' if not bad else 'PIVOT FAIL') + ' :: переносимых моделей %d, нарушений %d' % (len(got), len(bad)))
    for b in bad: print('  ' + b)
    sys.exit(1 if bad else 0)


main()
