#!/usr/bin/env python3
"""Разворот экспортированной модели: объект, который прижимается к стене,
обязан приехать в игру задом к стене, а не лицом.

Сцены в BlenderWork собраны в кадре «комната = −z», а импорт Unity даёт корню
FBX поворот (270,0,0), из-за чего авторская +z становится объектной −z. Значит
сцена обязана звать `flip(root)` при `params['export']`. Забыли вызов — модель
уезжает ЗЕРКАЛЬНО: у раковины ящики выезжают в стену, у унитаза бачок смотрит
в комнату (P472). Глазами это не ловится: в Blender и в рендере модель
выглядит правильной.

Замер идёт по экспортированному FBX в headless-Blender, редактор не нужен —
пробу можно гонять и пока другая сессия сидит в play.

Связь координат (сверено замером 18.09 через оба конца):
    локальная координата ноды в Unity == координата ноды в Blender,
    z в кадре ОБЪЕКТА == −y в Blender.
Отсюда правило: нода у СТЕНЫ обязана иметь в Blender y < 0, нода, смотрящая
в КОМНАТУ, — y > 0.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/export_facing_probe.py
Код возврата 1, если хоть одна нода смотрит не туда.
"""
import os
import subprocess
import sys

BLENDER = '/media/ilya/T714/Tools/blender-4.2.3-linux-x64/blender'
FURNITURE = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/Furniture'

# модель → нода → куда смотрит: 'wall' (к стене) или 'room' (в комнату)
EXPECT = {
    'homeToilet': {'Tank': 'wall', 'Bowl': 'room'},
    'homeBath': {'WallBack': 'wall', 'WallFront': 'room'},
    'homeBathroomSink': {'Back': 'wall', 'TapBody': 'wall', 'DrawerTop': 'room', 'DrawerBottom': 'room'},
    'homeBathroomMirror': {'Body': 'wall', 'Glass': 'room', 'Shelf': 'room', 'LightBar': 'room'},
    'homeBathroomCabinet': {'Back': 'wall', 'DoorL': 'room', 'DoorR': 'room', 'Divider': 'room'},
    # у трубы-кривой (Coil) начало координат в нуле, судить можно только по патрубкам и кронштейнам
    'homeTowelRail': {'StubB': 'room', 'StubT': 'room', 'BracketL1': 'room', 'StubBFlange': 'wall', 'StubTFlange': 'wall', 'BracketL1Flange': 'wall', 'BracketR6Flange': 'wall'},
    'homeLaundryBasket': {'Lid': 'wall', 'HingeL': 'wall', 'HingeR': 'wall', 'LidKnob': 'room'},
    # эталоны, на которых правило и выведено: они в игре стоят верно
    'homeWallCabinet': {'Back': 'wall', 'DoorL': 'room', 'DoorR': 'room'},
    'hallwayRack': {'Mount_Hook0': 'wall', 'DoorL': 'room', 'DoorR': 'room'},
}

INNER = r'''
import bpy, sys
path = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=path)
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    print('NODE %s %.4f' % (o.name, o.location.y))
'''


def measure(model):
    path = os.path.join(FURNITURE, model + '.fbx')
    if not os.path.exists(path):
        return None
    out = subprocess.run([BLENDER, '-b', '--python-expr', INNER, '--', path],
                         capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        if line.startswith('NODE '):
            _, name, y = line.split()
            got[name] = float(y)
    return got


def main():
    bad = 0
    for model in sorted(EXPECT):
        got = measure(model)
        if got is None:
            print('%-20s НЕТ FBX — пропуск' % model)
            continue
        for node, side in sorted(EXPECT[model].items()):
            if node not in got:
                print('%-20s %-14s НОДЫ НЕТ' % (model, node))
                bad += 1
                continue
            y = got[node]
            ok = (y < 0) if side == 'wall' else (y > 0)
            bad += 0 if ok else 1
            print('%s %-20s %-14s %-5s y=%+.3f' % ('  ' if ok else '⚠ ', model, node, side, y))
    print('EXPORT_FACING', 'ok' if bad == 0 else 'брак нод: %d' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
