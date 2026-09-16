#!/usr/bin/env python3
"""Обмотка граней у экспортированных моделей: каждое ребро замкнутого меша два
соседних полигона обязаны обходить в ПРОТИВОПОЛОЖНЫХ направлениях. Ребро,
пройденное дважды в одну сторону, — вывернутая грань: Unity отсекает её как
обратную, и с этой стороны модель просвечивает насквозь (P443: задний колпак
корпуса вороны, видно только в атаке сзади).

Запуск: python3 ~/.claude/skills/tavern-regress/probes/mesh_winding_probe.py [файлы .fbx/.blend]
Без аргументов — четыре птицы из Resources/Props. Код возврата 1, если хоть у
одного меша есть такие рёбра.
"""
import os
import subprocess
import sys
import tempfile

BLENDER = '/media/ilya/T714/Tools/blender-4.2.3-linux-x64/blender'
PROPS = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/Props'
DEFAULT = [os.path.join(PROPS, n + '.fbx') for n in ('Crow_Sit', 'Crow_Stand', 'Owl_Sit', 'Owl_Stand')]

INNER = r'''
import bpy, sys
from collections import Counter
path = sys.argv[sys.argv.index('--') + 1]
if path.lower().endswith('.fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
else:
    bpy.ops.wm.open_mainfile(filepath=path)
bad_total = 0
for o in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
    seen = Counter()
    for p in o.data.polygons:
        vs = list(p.vertices)
        for i in range(len(vs)):
            seen[(vs[i], vs[(i + 1) % len(vs)])] += 1
    dup = sum(1 for c in seen.values() if c > 1)
    bad_total += dup
    mark = '⚠' if dup else ' '
    print('WIND %s %-12s граней %4d, рёбер дважды в одну сторону %d' % (mark, o.name, len(o.data.polygons), dup))
print('WIND_TOTAL', bad_total)
'''


def check(path):
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(INNER)
        script = f.name
    try:
        out = subprocess.run([BLENDER, '-b', '--python', script, '--', path],
                             capture_output=True, text=True, timeout=180).stdout
    finally:
        os.unlink(script)
    lines = [l for l in out.splitlines() if l.startswith('WIND')]
    total = next((int(l.split()[1]) for l in lines if l.startswith('WIND_TOTAL')), -1)
    return total, [l[5:] for l in lines if not l.startswith('WIND_TOTAL')]


def main():
    files = sys.argv[1:] or DEFAULT
    failed = 0
    for path in files:
        total, rows = check(path)
        print('%s: %s' % (os.path.basename(path), 'ок' if total == 0 else 'вывернутых рёбер %d' % total))
        for r in rows:
            if '⚠' in r or total < 0:
                print('   ', r)
        if total != 0:
            failed += 1
    print('обмотка: %d файлов, брак в %d' % (len(files), failed))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
