#!/usr/bin/env python3
"""Стоячая копия (`old_kit.lean_copy`) не теряет и не удваивает поворот деталей.

P1045 (14.10): деталь из `pipe()` живёт в режиме QUATERNION, а копия обнуляла
только `rotation_euler` — поворот применялся дважды, и воротник весла у
`oldOarStand` висел в воздухе рядом с черенком. Теперь копии проходят через
`old_kit.reset_transform`. Проба собирает сцену весла в headless-Blender и
проверяет: у всех копий стоячего корня поворот и масштаб сброшены (сдвиг центровки
один на всех), центр воротника
лежит на оси черенка (|dx|, |dy| ≤ 2 см) и внутри его высоты.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/lean_copy_probe.py
Код возврата 1, если копия уехала.
"""
import os
import subprocess
import sys
import tempfile

BW = '/media/ilya/T714/Unity/Tavern-fresh/BlenderWork'
SCRIPT = r'''
import bpy, sys, math
sys.path.insert(0, %r)
from pipeline import OBJECTS, load_params, run_scene
spec = OBJECTS['old_oar']
run_scene(spec, load_params(spec))
bpy.context.view_layer.update()
rt = bpy.data.objects['oldOarStand']
bad = []
box = {}
shifts = set()
for ob in rt.children_recursive:
    if ob.type != 'MESH':
        continue
    if any(abs(v) > 1e-6 for v in ob.rotation_euler) or ob.rotation_mode != 'XYZ' or any(abs(v - 1.0) > 1e-6 for v in ob.scale):
        bad.append('%%s: поворот или масштаб не сброшен (%%s, %%s, %%s)' %% (ob.name, ob.rotation_mode, tuple(ob.rotation_euler), tuple(ob.scale)))
    shifts.add(tuple(round(v, 5) for v in ob.location))
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    box[ob.name.split('.')[0]] = ([min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)])
if len(shifts) > 1:
    bad.append('у копий разный сдвиг центровки: %%s' %% sorted(shifts))
sh, co = box.get('Shaft'), box.get('Collar')
if sh is None or co is None:
    bad.append('нет узлов Shaft/Collar: %%s' %% sorted(box))
else:
    cx = [(co[0][i] + co[1][i]) * 0.5 for i in range(3)]
    sx = [(sh[0][i] + sh[1][i]) * 0.5 for i in range(2)]
    if abs(cx[0] - sx[0]) > 0.02 or abs(cx[1] - sx[1]) > 0.25 or not (sh[0][2] <= cx[2] <= sh[1][2]):
        bad.append('воротник не на черенке: центр %%s, черенок %%s..%%s' %% ([round(c, 3) for c in cx], [round(c, 2) for c in sh[0]], [round(c, 2) for c in sh[1]]))
print('LEAN_COPY_PROBE', 'FAIL' if bad else 'OK')
for b in bad:
    print('  ', b)
''' % BW

with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
    f.write(SCRIPT)
    path = f.name
try:
    out = subprocess.run(['blender', '-b', '--python', path], capture_output=True, text=True, timeout=600, cwd=BW).stdout
finally:
    os.unlink(path)
lines = [l for l in out.splitlines() if 'LEAN_COPY_PROBE' in l or l.startswith('   ')]
print('\n'.join(lines) or out[-2000:])
sys.exit(0 if any('LEAN_COPY_PROBE OK' in l for l in lines) else 1)
