"""Одетый герой: игровое тело против штанов — кожа не выходит сквозь ткань (INVARIANTS 53, P203).

Headless Blender: импортирует игровой FBX тела и Clothes/JeansM.fbx, режет оба
срезами по высоте (шаг 0.1 м, ±1 см) и по 24 углам, сравнивает максимальный
радиус кожи с максимальным радиусом ткани от центра кожи. Зазор < -2 мм —
красное. Полоса промежности (0.78–0.86) не считается: там две ноги сходятся
и срез не про радиус.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/worn_jeans_probe.py
"""
import os, subprocess, sys, tempfile

BLENDER = '/media/ilya/T714/Tools/blender-4.2.3-linux-x64/blender'
RES = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/'
INNER = r'''
import bpy, math
from mathutils import Vector
RES = %r
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=RES + 'Models/HumanCharacterDummy_M_Skin.fbx')
skin = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
bpy.ops.import_scene.fbx(filepath=RES + 'Clothes/JeansM.fbx')
pants = bpy.data.objects['Pants']
dg = bpy.context.evaluated_depsgraph_get()
def wv(ob):
    e = ob.evaluated_get(dg)
    return [ob.matrix_world @ v.co for v in e.data.vertices]
sv, pv = wv(skin), wv(pants)
NB = 24
red = 0
for z in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.9, 1.0]:
    for side in (-1, 1):
        if z >= 0.8 and side > 0:
            continue
        def pick(verts):
            band = [v for v in verts if abs(v.z - z) < 0.01]
            return band if z >= 0.8 else [v for v in band if (v.x > 0) == (side > 0)]
        s = pick(sv); p = pick(pv)
        if not s or not p:
            continue
        cx = sum(v.x for v in s)/len(s); cy = sum(v.y for v in s)/len(s)
        def rmax(verts):
            acc = {}
            for v in verts:
                a = int(((math.atan2(v.y - cy, v.x - cx) + math.pi) / (2*math.pi)) * NB) %% NB
                acc[a] = max(acc.get(a, 0.0), math.hypot(v.x - cx, v.y - cy))
            return acc
        sa, pa = rmax(s), rmax(p)
        gaps = [(a, pa[a] - sa[a]) for a in sa if a in pa]
        bad = [(a, g) for a, g in gaps if g < -0.002]
        red += len(bad)
        worst = min(g for _, g in gaps) if gaps else 0.0
        print('SLICE z=%%.2f side=%%+d gap_min=%%+.4f bad=%%d/%%d %%s' %% (z, side, worst, len(bad), len(gaps),
              ' '.join('a%%d:%%+.3f' %% (a, g) for a, g in bad)))
print('VERDICT', 'RED %%d' %% red if red else 'GREEN')
''' % RES

def main():
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(INNER)
        path = f.name
    try:
        out = subprocess.run(['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=6G',
                              BLENDER, '-b', '-P', path], capture_output=True, text=True, timeout=600)
    finally:
        os.unlink(path)
    lines = [l for l in out.stdout.splitlines() if l.startswith(('SLICE', 'VERDICT'))]
    print('\n'.join(lines) if lines else out.stdout[-2000:] + out.stderr[-2000:])
    return 0 if any(l == 'VERDICT GREEN' for l in lines) else 1

if __name__ == '__main__':
    sys.exit(main())
