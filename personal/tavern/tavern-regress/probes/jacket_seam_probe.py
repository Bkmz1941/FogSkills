"""Куртка на герое: воротник не выходит сквозь капюшон, капюшон — замкнутая оболочка (INVARIANTS 139, P343).

Headless Blender по двум файлам одежды: Т-поза `JacketStand_V1_Cut` в humanClothes.blend
(источник экспорта) и позированные `JacketStand_V1_J1_Cut` (стойка) / `_JW_Cut` (ходьба)
в humanJacket.blend по кадрам. Объект — воротник + капюшон одним куском; делится на
компоненты связности (капюшон — тот, что ниже). Проверки:
  behind — вершины воротника ПОЗАДИ поверхности капюшона (луч сзади по −y на той же
           высоте): ждём 0. Так воротник и просвечивал сквозь капюшон (12.09).
  open   — граничные рёбра у капюшона: ждём 0 (односторонний капюшон в игре отсекался
           задними гранями, и сквозь дыры был виден воротник).
  tris   — воротник+капюшон не выше бюджета экспорта `JacketStand_V1_Cut` (иначе
           децимация переделает шов).
Запуск: python3 ~/.claude/skills/tavern-regress/probes/jacket_seam_probe.py — последняя строка «ok» или «КРАСНОЕ …».
"""
import json, os, re, subprocess, sys, tempfile

BLENDER = '/media/ilya/T714/Tools/blender-5.2.2-linux-x64/blender'
WORK = '/media/ilya/T714/Unity/Tavern-fresh/BlenderWork'
FILES = [('Library/humanClothes.blend', 'JacketStand_V1_Cut', [None]),
         ('Library/humanJacket.blend', 'JacketStand_V1_J1_Cut', [1, 20, 40, 60, 80]),
         ('Library/humanJacket.blend', 'JacketStand_V1_JW_Cut', [2, 15, 30, 45, 55])]
src = open(os.path.join(WORK, 'human_skin_garment_export.py'), encoding='utf-8').read()
BUDGET = int(re.search(r"'JacketStand_V1_Cut': (\d+)", src).group(1))
INNER = r'''
import bpy, json, sys
from mathutils import Vector, bvhtree
name, frames = %r, %r
ob = bpy.data.objects[name]
out = []
for frame in frames:
    if frame is not None:
        bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    em = ob.evaluated_get(dg).to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in em.vertices]
    faces = [list(f.vertices) for f in em.polygons]
    parent = list(range(len(verts)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for f in faces:
        for a, b in zip(f, f[1:]):
            ra, rb = find(a), find(b)
            if ra != rb: parent[ra] = rb
    groups = {}
    for i in range(len(verts)):
        groups.setdefault(find(i), []).append(i)
    hood_c = min(groups, key=lambda c: min(verts[i].z for i in groups[c]))
    hv = set(groups[hood_c]); sv = [i for c, g in groups.items() if c != hood_c for i in g]
    hood_f = [f for f in faces if f[0] in hv]
    stand_f = [f for f in faces if f[0] not in hv]
    edges = {}
    for f in hood_f:
        for a, b in zip(f, f[1:] + f[:1]):
            edges[(min(a, b), max(a, b))] = edges.get((min(a, b), max(a, b)), 0) + 1
    open_edges = sum(1 for n in edges.values() if n == 1)
    bvh = bvhtree.BVHTree.FromPolygons(verts, hood_f)
    behind = []
    for i in sv:
        v = verts[i]
        hit = bvh.ray_cast(Vector((v.x, 0.9, v.z)), Vector((0.0, -1.0, 0.0)), 1.5)
        if hit[0] is not None and v.y - hit[0].y > 0.0005:
            behind.append(round((v.y - hit[0].y) * 1000, 1))
    tris = sum(len(f) - 2 for f in faces)
    out.append({'frame': frame, 'behind': len(behind), 'behind_max_mm': max(behind) if behind else 0.0,
                'open_edges': open_edges, 'tris': tris, 'components': len(groups)})
    ob.evaluated_get(dg).to_mesh_clear()
print('PROBE ' + json.dumps(out))
'''
rows = []
for blend, name, frames in FILES:
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(INNER % (name, frames))
        script = f.name
    out = subprocess.run([BLENDER, '-b', os.path.join(WORK, blend), '--python', script],
                         capture_output=True, text=True, timeout=600)
    os.unlink(script)
    line = [l for l in out.stdout.split('\n') if l.startswith('PROBE ')]
    if not line:
        print('КРАСНОЕ: нет ответа от Blender для', name, out.stderr[-400:])
        sys.exit(1)
    for r in json.loads(line[0][6:]):
        r['object'] = name
        rows.append(r)
        print('%-24s кадр %-4s воротник позади капюшона %d (макс %.1f мм), открытых рёбер капюшона %d, компонентов %d, тр. %d'
              % (name, r['frame'], r['behind'], r['behind_max_mm'], r['open_edges'], r['components'], r['tris']))
bad = [r for r in rows if r['behind'] or r['open_edges'] or r['components'] != 2 or r['tris'] > BUDGET]
print(('КРАСНОЕ: %d замеров из %d' % (len(bad), len(rows))) if bad else ('ok: %d замеров, бюджет %d' % (len(rows), BUDGET)))
sys.exit(1 if bad else 0)
