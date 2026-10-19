"""Замер «тонкого»: печатает куски меша (островки), у которых малая сторона < 3,5 см.
По FBX:   blender -b --python ~/.claude/skills/tavern-objects/islands.py -- Assets/Game/Resources/<папка>/<корень>.fbx [ещё.fbx …]
По сцене: blender -b --python ~/.claude/skills/tavern-objects/islands.py -- <ключ реестра pipeline.py> [ещё ключи …]
          (сцена собирается как на экспорт, меряются меши под корнями записи; FBX в игру не пишется)
"""
import bpy, bmesh, sys, os
from collections import Counter

BW = '/media/ilya/T714/Unity/Tavern-fresh/BlenderWork'
args = sys.argv[sys.argv.index('--') + 1:]


def scene_meshes(key):
    sys.path.insert(0, BW)
    from pipeline import OBJECTS, load_params, run_scene
    spec = OBJECTS[key]
    run_scene(spec, load_params(spec, hide=True))
    roots = spec['roots'] if not callable(spec['roots']) else spec['roots'](load_params(spec))
    out = []
    for name in roots:
        rt = bpy.data.objects.get(name)
        if rt is None:
            print('NO ROOT', name)
            continue
        out += [ob for ob in rt.children_recursive if ob.type == 'MESH']
    return out


for f in args:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if f.lower().endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=f)
        objects = [ob for ob in bpy.data.objects if ob.type == 'MESH']
    else:
        objects = scene_meshes(f)
    thin = Counter()
    total = 0
    for ob in objects:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        seen = set()
        for v in bm.verts:
            if v.index in seen:
                continue
            stack = [v]; seen.add(v.index); pts = []
            while stack:
                a = stack.pop(); pts.append(a.co.copy())
                for e in a.link_edges:
                    b = e.other_vert(a)
                    if b.index not in seen:
                        seen.add(b.index); stack.append(b)
            xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
            dims = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)])
            total += 1
            if dims[0] < 0.035 and dims[1] > 0.0:
                thin[(ob.name, round(dims[0], 3), round(dims[1], 2), round(dims[2], 2))] += 1
        bm.free()
    print('FILE', os.path.basename(f), 'islands', total, 'thin', sum(thin.values()))
    for k, n in sorted(thin.items(), key=lambda kv: kv[0][1])[:14]:
        print('   ', n, 'x', k)
