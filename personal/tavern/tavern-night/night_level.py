"""Ночной уровень одним файлом: коробка дома в N этажей с лестницами с площадкой, проёмами,
отделкой, плинтусом и цоколем — по числам `GridCursor.Blocks.cs` (BUILD.md, «СБОРКА УРОВНЯ ФАЙЛОМ»).

python3 night_level.py [имя] [--floors 5] [--dry]   собрать <имя>.json в папку уровней (по умолчанию night_build)
python3 night_level.py --check <имя>                 сверить счётчики файла с задуманным
python3 night_level.py <имя> --layout c --floors 3  вариант C (28.09): обычные марши без площадки, кухня с навесными
python3 night_level.py <имя> --layout b --floors 4  вариант B (27.09): другие углы лестниц, кухня под окнами, ванная с ванной, комнаты 2×2

Дом 4×3 клетки, этажи 0..N-1 (уровни 0, 3, 6, …), крыша над последним. Лестницы с площадкой
чередуются по углам: чётный этаж — клетки (0,0)→(1,0) на +X, нечётный — (3,2)→(2,2) на −X.
Дырка в перекрытии — над обеими клетками следа; выход с площадки — вбок, как у Ильи в level1.
Мебели тут нет: её ставит `night_place.py` через настоящий пайплайн постановки в play.
"""
import json, math, pathlib, sys

LEVELS = pathlib.Path.home() / '.config/unity3d/DefaultCompany/Tavern/levels'
CS = 3.0
ORIGIN_X, ORIGIN_Z = -51.0, -51.0
GRID = 50
HOUSE_I0, HOUSE_J0 = 15, 15
NX, NZ = 4, 3

FACADE, INNER, TILE = 'WoodPlank002', 'WoodPlank001', 'BathSquareTile'
FLOOR, TILE_FLOOR, CEIL = 'Laminate001', 'BathFloorTile', 'BathDeckDark'
SOCLE_HEX, BASE_HEX = '#94694F', '#F2F0EB'
STYLE_NONE = {'kind': 0, 'h': 0.0, 'd': 0.0, 'r': 0.0}
STYLE_SOCLE = {'kind': 1, 'h': 0.32, 'd': 0.0, 'r': 0.0}
DOOR_WOOD, DOOR_STEEL = 7, 8
WIN_WHITE, WIN_PVC = 0, 2


def v3(x, y, z): return {'x': float(x), 'y': float(y), 'z': float(z)}


def cx(i): return ORIGIN_X + (HOUSE_I0 + i) * CS
def cz(j): return ORIGIN_Z + (HOUSE_J0 + j) * CS


class House:
    def __init__(self, floors):
        self.floors = floors
        self.walls, self.slabs, self.doors, self.windows, self.stairs, self.roofs, self.zones, self.objects = [], [], [], [], [], [], [], []
        self.expect = {}

    def slab(self, i, j, level, top=FLOOR, bottom=CEIL, ceiling=None):
        if ceiling is None: ceiling = level > 0
        self.slabs.append({'pos': v3(cx(i), level - 0.1, cz(j)), 'scale': v3(CS, 0.2, CS), 'material': 0, 'ceiling': ceiling,
                           'colorHex': '', 'paintA': top, 'paintB': bottom, 'sideXp': '', 'sideXn': '', 'sideZp': '', 'sideZn': '',
                           'plXp': False, 'plXn': False, 'plZp': False, 'plZn': False, 'plHexXp': '', 'plHexXn': '', 'plHexZp': '', 'plHexZn': ''})

    # Сторона A — +Z у стены вдоль X (spansX) и +X у стены вдоль Z; B — противоположная (BUILD.md, окно#1).
    def wall(self, x, z, level, spans_x, a, b):
        pa, pla, hexa, sta = a
        pb, plb, hexb, stb = b
        scale = v3(CS, 3.012, 0.25) if spans_x else v3(0.25, 3.012, CS)
        self.walls.append({'colorHex': '', 'pos': v3(x, level - 0.01 + 1.506, z), 'scale': scale, 'spansX': spans_x, 'material': 0,
                           'paintA': pa, 'paintB': pb, 'railing': False, 'fence': False, 'plinthA': pla, 'plinthB': plb,
                           'plinthHexA': hexa, 'plinthHexB': hexb, 'plinthStyleA': dict(sta), 'plinthStyleB': dict(stb)})
        return self.walls[-1]

    def edge_x(self, i, j):  # ребро между (i,j) и (i,j+1): стена вдоль X
        return cx(i), ORIGIN_Z + (HOUSE_J0 + j + 0.5) * CS
    def edge_z(self, i, j):  # ребро между (i,j) и (i+1,j): стена вдоль Z
        return ORIGIN_X + (HOUSE_I0 + i + 0.5) * CS, cz(j)

    def opening(self, kind, wall, level, **extra):
        self.walls.remove(wall)
        rec = {'pos': v3(wall['pos']['x'], level, wall['pos']['z']), 'spansX': wall['spansX'],
               'wallSaved': True, 'wallMaterial': 0, 'wallColorHex': '', 'wallPaintA': wall['paintA'], 'wallPaintB': wall['paintB'],
               'wallPlinthA': wall['plinthA'], 'wallPlinthB': wall['plinthB'], 'wallPlinthHexA': wall['plinthHexA'], 'wallPlinthHexB': wall['plinthHexB'],
               'wallPlinthStyleA': dict(wall['plinthStyleA']), 'wallPlinthStyleB': dict(wall['plinthStyleB'])}
        if kind == 'door':
            rec.update({'locked': False, 'open': False, 'cr': 0.28, 'cg': 0.5, 'cb': 1.0, 'material': 4 if extra['style'] == DOOR_STEEL else 1,
                        'style': extra['style'], 'peepInside': True, 'paintA': '', 'paintB': '', 'keyCode': ''})
            self.doors.append(rec)
        else:
            rec.update({'style': extra['style'], 'open': False, 'paintA': wall['paintA'], 'paintB': wall['paintB'], 'offset': extra.get('offset', 0.0)})
            self.windows.append(rec)
        return rec

    def stair(self, i_entry, i_land, j, level, plus_x):
        x = ORIGIN_X + (HOUSE_I0 + min(i_entry, i_land) + 0.5) * CS
        self.stairs.append({'pos': v3(x, level, cz(j)), 'rotY': 90.0 if plus_x else 270.0, 'riseCells': 1, 'lengthCells': 1, 'material': 0,
                            'visual': '', 'paintL': '', 'paintR': INNER, 'paintT': FLOOR, 'plinthL': False, 'plinthR': False,
                            'plinthHexL': '', 'plinthHexR': '', 'colorHex': '', 'landing': True, 'paintB': INNER})

    def march(self, i_low, i_high, j, level):
        # Обычный марш без площадки на 2 клетки: корень на стыке двух клеток (середина марша), низ у i_low, верх у i_high.
        x = ORIGIN_X + (HOUSE_I0 + min(i_low, i_high) + 0.5) * CS
        self.stairs.append({'pos': v3(x, level, cz(j)), 'rotY': 90.0 if i_high > i_low else 270.0, 'riseCells': 1, 'lengthCells': 2, 'material': 0,
                            'visual': '', 'paintL': INNER, 'paintR': INNER, 'paintT': FLOOR, 'plinthL': False, 'plinthR': False,
                            'plinthHexL': '', 'plinthHexR': '', 'colorHex': '', 'landing': False, 'paintB': INNER})

    def roof(self, level):
        self.roofs.append({'pos': v3((cx(0) + cx(NX - 1)) * 0.5, level, (cz(0) + cz(NZ - 1)) * 0.5), 'cellsX': NX, 'cellsZ': NZ})

    def zone(self, name, level, cells):
        self.zones.append({'name': name, 'slug': '', 'cr': 1.0, 'cg': 1.0, 'cb': 1.0, 'kind': 2, 'strong': True, 'fireSpread': False,
                           'temp': float('nan'), 'attackers': '', 'cells': [v3(cx(i), level + 0.1, cz(j)) for i, j in cells],
                           'fog': False, 'fogStrong': True, 'fire': False, 'fireStrong': True, 'wind': False})

    def obj(self, oid, x, y, z, rot=0.0):
        self.objects.append({'pos': v3(x, y, z), 'rotY': float(rot), 'rotX': 0.0, 'rotZ': 0.0, 'id': oid, 'locked': False, 'open': False,
                             'cr': 0.0, 'cg': 0.0, 'cb': 0.0, 'access': [], 'powerOn': True, 'powerZones': [], 'switchTargets': [], 'switchOn': True,
                             'puzzleSeq': '', 'puzzlePos': 0, 'puzzleSolved': False, 'pcSet': False, 'pcr': 0.0, 'pcg': 0.0, 'pcb': 0.0, 'items': [],
                             'carrierId': '', 'carrierNode': '', 'carrierPos': v3(0, 0, 0), 'localPos': v3(0, 0, 0), 'localRotY': 0.0, 'height': 0.0,
                             'crownWidth': 0.0, 'crownHeight': 0.0, 'crownShift': 0.0, 'count': -1, 'liquidKind': '', 'liquidL': 0.0, 'cook': '',
                             'widthAdd': 0.0, 'sizeW': 0.0, 'sizeD': 0.0, 'sizeH': 0.0, 'dirt': 0.0, 'greased': False, 'sauced': False, 'liquidMix': '',
                             'switchesOn': [], 'groupMate': -1, 'groupTitle': '', 'burn': 0, 'perchOn': False, 'perchH': 0.0, 'perchLen': 0.0,
                             'perchThick': 0.0, 'perchYaw': 0.0, 'crowActive': False, 'crowNear': False, 'fireLit': False, 'pattern': 0,
                             'cellCharge': -2.0, 'palette': -1})


def outer(inside_paint, ground):
    """(снаружи, внутри): фасад с цоколем на земле и без плинтуса выше; внутри плинтус всегда."""
    out = (FACADE, ground, SOCLE_HEX if ground else '', STYLE_SOCLE if ground else STYLE_NONE)
    inn = (inside_paint, True, BASE_HEX if inside_paint == TILE else '', STYLE_NONE)
    return out, inn


def inner(paint_a=INNER, paint_b=INNER):
    return ((paint_a, True, BASE_HEX if paint_a == TILE else '', STYLE_NONE), (paint_b, True, BASE_HEX if paint_b == TILE else '', STYLE_NONE))


# План этажа: ключ — этаж (0..), значение — что на нём стоит. Лестница чётного этажа — (0,0)→(1,0) на +X,
# нечётного — (3,2)→(2,2) на −X; дырка над её следом на следующем уровне; ограждение дырки —
# стена по дальней линии следа и стена у входной клетки, выход с площадки вбок остаётся открытым.
def stair_cells(f):
    return [(0, 0), (1, 0)] if f % 2 == 0 else [(3, 2), (2, 2)]


def build(name, floors):
    h = House(floors)
    bath_cells = {(0, 2), (1, 2)}
    for f in range(floors):
        L = f * CS
        holes = set(stair_cells(f - 1)) if f > 0 else set()
        tiles = bath_cells if f == 1 else set()
        for i in range(NX):
            for j in range(NZ):
                if (i, j) in holes: continue
                h.slab(i, j, L, top=TILE_FLOOR if (i, j) in tiles else FLOOR, bottom=CEIL, ceiling=f > 0)
        ground = f == 0
        # периметр: юг (j=0, сторона B наружу), север (j=NZ-1, A наружу), запад (i=0, B наружу), восток (A наружу)
        for i in range(NX):
            x, z = h.edge_x(i, -1)
            o, n = outer(TILE if f == 1 and (i, 0) in tiles else INNER, ground)
            h.wall(x, z, L, True, n, o)
            x, z = h.edge_x(i, NZ - 1)
            o, n = outer(TILE if f == 1 and (i, NZ - 1) in tiles else INNER, ground)
            h.wall(x, z, L, True, o, n)
        for j in range(NZ):
            x, z = h.edge_z(-1, j)
            o, n = outer(TILE if f == 1 and (0, j) in tiles else INNER, ground)
            h.wall(x, z, L, False, n, o)
            x, z = h.edge_z(NX - 1, j)
            o, n = outer(INNER, ground)
            h.wall(x, z, L, False, o, n)
        # ограждение дырки лестницы этажом ниже
        if f > 0:
            if (f - 1) % 2 == 0:
                x, z = h.edge_z(1, 0); h.wall(x, z, L, False, *inner())      # дальняя линия следа (1,0)|(2,0)
                x, z = h.edge_x(0, 0); h.wall(x, z, L, True, *inner())       # входная клетка (0,0)|(0,1)
            else:
                x, z = h.edge_z(1, 2); h.wall(x, z, L, False, *inner())      # дальняя линия (2,2)|(1,2)
                x, z = h.edge_x(3, 1); h.wall(x, z, L, True, *inner())       # входная клетка (3,2)|(3,1)
        # внутренние стены этажа
        if f == 0:
            for j in range(NZ):                                             # прихожая | кухня-гостиная
                x, z = h.edge_z(1, j); w = h.wall(x, z, L, False, *inner())
                if j == 1: h.opening('door', w, L, style=DOOR_WOOD)
        elif f == 1:
            for i in (0, 1):                                                # ванная (0..1, 2)
                x, z = h.edge_x(i, 1); w = h.wall(x, z, L, True, *inner(TILE, INNER))
                if i == 1: h.opening('door', w, L, style=DOOR_WOOD)
            x, z = h.edge_z(1, 2); w = h.wall(x, z, L, False, *inner(INNER, TILE))
            x, z = h.edge_z(1, 1); w = h.wall(x, z, L, False, *inner())      # прихожая | спальня
            h.opening('door', w, L, style=DOOR_WOOD)
        elif f == 3:
            for i in (0, 1):                                                # кладовка (0..1, 2)
                x, z = h.edge_x(i, 1); w = h.wall(x, z, L, True, *inner())
                if i == 0: h.opening('door', w, L, style=DOOR_WOOD)
            x, z = h.edge_z(1, 2); h.wall(x, z, L, False, *inner())
        # лестница на следующий этаж
        if f < floors - 1:
            a, b = stair_cells(f)
            h.stair(a[0], b[0], a[1], L, plus_x=(f % 2 == 0))
        # проёмы наружу
        def outer_wall(i, j, side):
            if side == 'S': x, z = h.edge_x(i, -1)
            elif side == 'N': x, z = h.edge_x(i, NZ - 1)
            elif side == 'W': x, z = h.edge_z(-1, j)
            else: x, z = h.edge_z(NX - 1, j)
            for w in h.walls:
                if abs(w['pos']['x'] - x) < 1e-3 and abs(w['pos']['z'] - z) < 1e-3 and abs(w['pos']['y'] - (L + 1.496)) < 0.01:
                    return w
            raise SystemExit('нет стены %s %s %s этаж %d' % (i, j, side, f))
        if f == 0:
            h.opening('door', outer_wall(2, 0, 'S'), L, style=DOOR_STEEL)
            h.opening('window', outer_wall(3, 0, 'S'), L, style=WIN_WHITE, offset=0.48)
            h.opening('window', outer_wall(2, 2, 'N'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(3, 1, 'E'), L, style=WIN_WHITE, offset=-0.48)
            h.opening('window', outer_wall(0, 2, 'W'), L, style=WIN_PVC, offset=0.0)
        elif f == 1:
            h.opening('window', outer_wall(3, 2, 'N'), L, style=WIN_WHITE, offset=-0.18)
            h.opening('window', outer_wall(0, 2, 'N'), L, style=WIN_WHITE, offset=0.0)
            h.opening('window', outer_wall(2, 0, 'S'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(3, 0, 'S'), L, style=WIN_WHITE, offset=0.48)
            h.opening('window', outer_wall(3, 1, 'E'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(0, 1, 'W'), L, style=WIN_WHITE, offset=0.48)
        elif f == 2:
            h.opening('window', outer_wall(2, 2, 'N'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(3, 2, 'N'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(1, 0, 'S'), L, style=WIN_WHITE, offset=0.0)
            h.opening('window', outer_wall(3, 0, 'S'), L, style=WIN_WHITE, offset=-0.48)
            h.opening('window', outer_wall(3, 1, 'E'), L, style=WIN_WHITE, offset=0.0)
            h.opening('window', outer_wall(0, 1, 'W'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(0, 2, 'W'), L, style=WIN_PVC, offset=0.0)
        elif f == 3:
            h.opening('window', outer_wall(2, 2, 'N'), L, style=WIN_WHITE, offset=0.48)
            h.opening('window', outer_wall(1, 0, 'S'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(3, 0, 'S'), L, style=WIN_WHITE, offset=0.0)
            h.opening('window', outer_wall(3, 1, 'E'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(0, 1, 'W'), L, style=WIN_WHITE, offset=-0.48)
        else:
            h.opening('window', outer_wall(1, 2, 'N'), L, style=WIN_WHITE, offset=0.0)
            h.opening('window', outer_wall(2, 0, 'S'), L, style=WIN_PVC, offset=0.0)
            h.opening('window', outer_wall(3, 1, 'E'), L, style=WIN_WHITE, offset=0.0)
    # потолок последнего этажа и крыша
    top = floors * CS
    for i in range(NX):
        for j in range(NZ):
            h.slab(i, j, top, top=CEIL, bottom=CEIL, ceiling=True)
    h.roof(top)
    h.zone('Ночной дом', 0, [(i, j) for i in range(NX) for j in range(NZ)])
    h.obj('spawn_marker', cx(2), -0.1, cz(0) - 4.0, 0.0)
    return h


# Вариант B (27.09): лестницы в других углах — чётный этаж (3,2)→(2,2) на −X, нечётный (0,0)→(1,0) на +X;
# кухня в ЮЗ углу под окнами, ванная с ванной и стиралкой в ЮВ, комнаты 2×2, шкаф-купе, диван и кровать под окнами.
def stair_cells_b(f):
    return [(3, 2), (2, 2)] if f % 2 == 0 else [(0, 0), (1, 0)]


def build_b(name, floors):
    h = House(floors)
    bath = {1: {(2, 0), (3, 0)}}
    for f in range(floors):
        L = f * CS
        holes = set(stair_cells_b(f - 1)) if f > 0 else set()
        tiles = bath.get(f, set())
        for i in range(NX):
            for j in range(NZ):
                if (i, j) in holes: continue
                h.slab(i, j, L, top=TILE_FLOOR if (i, j) in tiles else FLOOR, bottom=CEIL, ceiling=f > 0)
        ground = f == 0
        for i in range(NX):
            x, z = h.edge_x(i, -1); o, n = outer(TILE if (i, 0) in tiles else INNER, ground); h.wall(x, z, L, True, n, o)
            x, z = h.edge_x(i, NZ - 1); o, n = outer(TILE if (i, NZ - 1) in tiles else INNER, ground); h.wall(x, z, L, True, o, n)
        for j in range(NZ):
            x, z = h.edge_z(-1, j); o, n = outer(TILE if (0, j) in tiles else INNER, ground); h.wall(x, z, L, False, n, o)
            x, z = h.edge_z(NX - 1, j); o, n = outer(TILE if (NX - 1, j) in tiles else INNER, ground); h.wall(x, z, L, False, o, n)
        if f > 0:
            if (f - 1) % 2 == 0:
                x, z = h.edge_z(1, 2); h.wall(x, z, L, False, *inner())      # дальняя линия (2,2)|(1,2)
                x, z = h.edge_x(3, 1); h.wall(x, z, L, True, *inner())       # входная клетка (3,2)|(3,1)
            else:
                x, z = h.edge_z(1, 0); h.wall(x, z, L, False, *inner())      # дальняя линия (1,0)|(2,0)
                x, z = h.edge_x(0, 0); h.wall(x, z, L, True, *inner())       # входная клетка (0,0)|(0,1)
        if f == 1:
            for i in (2, 3):                                                # ванная (2..3, 0)
                x, z = h.edge_x(i, 0); w = h.wall(x, z, L, True, *inner(INNER, TILE))
                if i == 2: h.opening('door', w, L, style=DOOR_WOOD)
            x, z = h.edge_z(1, 0); h.wall(x, z, L, False, *inner(TILE, INNER))
            x, z = h.edge_x(1, 0); h.wall(x, z, L, True, *inner())           # лестница | спальня
            x, z = h.edge_z(1, 1); w = h.wall(x, z, L, False, *inner())      # спальня 2×2 | коридор
            h.opening('door', w, L, style=DOOR_WOOD)
        elif f == 2:
            x, z = h.edge_z(1, 1); w = h.wall(x, z, L, False, *inner())      # гостиная | кабинет 2×2
            h.opening('door', w, L, style=DOOR_WOOD)
            x, z = h.edge_x(2, 1); h.wall(x, z, L, True, *inner())           # кабинет | площадка
        elif f == 3:
            x, z = h.edge_z(1, 0); w = h.wall(x, z, L, False, *inner())      # кабинет | спальня
            h.opening('door', w, L, style=DOOR_WOOD)
            x, z = h.edge_z(1, 1); h.wall(x, z, L, False, *inner())
        if f < floors - 1:
            a, b = stair_cells_b(f)
            h.stair(a[0], b[0], a[1], L, plus_x=(f % 2 == 1))
        def outer_wall(i, j, side):
            if side == 'S': x, z = h.edge_x(i, -1)
            elif side == 'N': x, z = h.edge_x(i, NZ - 1)
            elif side == 'W': x, z = h.edge_z(-1, j)
            else: x, z = h.edge_z(NX - 1, j)
            for w in h.walls:
                if abs(w['pos']['x'] - x) < 1e-3 and abs(w['pos']['z'] - z) < 1e-3 and abs(w['pos']['y'] - (L + 1.496)) < 0.01:
                    return w
            raise SystemExit('нет стены %s %s %s этаж %d' % (i, j, side, f))
        OPEN = {
            0: [('door', 0, 1, 'W', DOOR_STEEL, 0.0), ('window', 0, 0, 'S', WIN_PVC, 0.0), ('window', 1, 0, 'S', WIN_WHITE, 0.0),
                ('window', 3, 0, 'S', WIN_WHITE, 0.0), ('window', 3, 1, 'E', WIN_PVC, 0.0), ('window', 1, 2, 'N', WIN_WHITE, 0.0),
                ('window', 0, 2, 'N', WIN_PVC, 0.0)],
            1: [('window', 0, 2, 'N', WIN_WHITE, 0.0), ('window', 1, 2, 'N', WIN_PVC, 0.0), ('window', 0, 1, 'W', WIN_WHITE, 0.0),
                ('window', 2, 0, 'S', WIN_PVC, 0.0), ('window', 3, 1, 'E', WIN_WHITE, 0.0)],
            2: [('window', 0, 1, 'W', WIN_PVC, 0.0), ('window', 0, 2, 'W', WIN_WHITE, 0.0), ('window', 1, 2, 'N', WIN_WHITE, 0.48),
                ('window', 2, 0, 'S', WIN_WHITE, 0.0), ('window', 3, 0, 'S', WIN_PVC, 0.0), ('window', 3, 1, 'E', WIN_WHITE, 0.0)],
            3: [('window', 3, 0, 'S', WIN_WHITE, 0.0), ('window', 3, 1, 'E', WIN_PVC, 0.0), ('window', 0, 0, 'S', WIN_PVC, 0.0),
                ('window', 0, 1, 'W', WIN_WHITE, 0.0), ('window', 0, 2, 'N', WIN_WHITE, 0.0)],
        }
        for kind, i, j, side, style, off in OPEN.get(f, []):
            if kind == 'door': h.opening('door', outer_wall(i, j, side), L, style=style)
            else: h.opening('window', outer_wall(i, j, side), L, style=style, offset=off)
    top = floors * CS
    for i in range(NX):
        for j in range(NZ):
            h.slab(i, j, top, top=CEIL, bottom=CEIL, ceiling=True)
    h.roof(top)
    h.zone('Ночной дом B', 0, [(i, j) for i in range(NX) for j in range(NZ)])
    h.obj('spawn_marker', cx(0) - 4.0, -0.1, cz(1), 90.0)
    return h


# Вариант C (28.09): обычные марши без площадки на 2 клетки — этаж 0 (1,2)→(2,2) на +X вдоль северной стены,
# этаж 1 (2,0)→(1,0) на −X вдоль южной; выход сверху прямо вперёд. Кухня вдоль глухой южной стены с навесными.
MARCH_C = {0: ((1, 2), (2, 2)), 1: ((2, 0), (1, 0))}


def build_c(name, floors):
    h = House(floors)
    for f in range(floors):
        L = f * CS
        holes = set(MARCH_C.get(f - 1, ())) if f > 0 else set()
        for i in range(NX):
            for j in range(NZ):
                if (i, j) in holes: continue
                h.slab(i, j, L, top=FLOOR, bottom=CEIL, ceiling=f > 0)
        ground = f == 0
        for i in range(NX):
            x, z = h.edge_x(i, -1); o, n = outer(INNER, ground); h.wall(x, z, L, True, n, o)
            x, z = h.edge_x(i, NZ - 1); o, n = outer(INNER, ground); h.wall(x, z, L, True, o, n)
        for j in range(NZ):
            x, z = h.edge_z(-1, j); o, n = outer(INNER, ground); h.wall(x, z, L, False, n, o)
            x, z = h.edge_z(NX - 1, j); o, n = outer(INNER, ground); h.wall(x, z, L, False, o, n)
        if f == 1:                                                          # ограждение дырки марша (1,2)-(2,2)
            for i in (1, 2):
                x, z = h.edge_x(i, 1); h.wall(x, z, L, True, *inner())
            x, z = h.edge_z(0, 2); h.wall(x, z, L, False, *inner())         # у нижнего конца марша
        elif f == 2:                                                        # ограждение дырки марша (2,0)-(1,0)
            for i in (1, 2):
                x, z = h.edge_x(i, 0); h.wall(x, z, L, True, *inner())
            x, z = h.edge_z(2, 0); h.wall(x, z, L, False, *inner())         # у нижнего конца марша
        if f in MARCH_C and f < floors - 1:
            lo, hi = MARCH_C[f]
            h.march(lo[0], hi[0], lo[1], L)
        def outer_wall(i, j, side):
            if side == 'S': x, z = h.edge_x(i, -1)
            elif side == 'N': x, z = h.edge_x(i, NZ - 1)
            elif side == 'W': x, z = h.edge_z(-1, j)
            else: x, z = h.edge_z(NX - 1, j)
            for w in h.walls:
                if abs(w['pos']['x'] - x) < 1e-3 and abs(w['pos']['z'] - z) < 1e-3 and abs(w['pos']['y'] - (L + 1.496)) < 0.01:
                    return w
            raise SystemExit('нет стены %s %s %s этаж %d' % (i, j, side, f))
        OPEN = {
            0: [('door', 3, 1, 'E', DOOR_STEEL, 0.0), ('window', 0, 0, 'S', WIN_PVC, 0.0), ('window', 3, 0, 'S', WIN_WHITE, 0.0),
                ('window', 0, 1, 'W', WIN_WHITE, 0.0), ('window', 3, 2, 'N', WIN_PVC, 0.0), ('window', 0, 2, 'N', WIN_WHITE, 0.0)],
            1: [('window', 0, 0, 'S', WIN_WHITE, 0.0), ('window', 0, 1, 'W', WIN_PVC, 0.0), ('window', 3, 0, 'E', WIN_WHITE, 0.0),
                ('window', 3, 2, 'N', WIN_WHITE, 0.0)],
            2: [('window', 0, 1, 'W', WIN_WHITE, 0.0), ('window', 3, 1, 'E', WIN_PVC, 0.0), ('window', 1, 2, 'N', WIN_WHITE, 0.0)],
        }
        for kind, i, j, side, style, off in OPEN.get(f, []):
            if kind == 'door': h.opening('door', outer_wall(i, j, side), L, style=style)
            else: h.opening('window', outer_wall(i, j, side), L, style=style, offset=off)
    top = floors * CS
    for i in range(NX):
        for j in range(NZ):
            h.slab(i, j, top, top=CEIL, bottom=CEIL, ceiling=True)
    h.roof(top)
    h.zone('Ночной дом C', 0, [(i, j) for i in range(NX) for j in range(NZ)])
    h.obj('spawn_marker', cx(3) + 4.0, -0.1, cz(1), 270.0)
    return h


def write(name, h, template):
    d = json.loads(json.dumps(template))
    d['sceneName'] = name; d['slug'] = name
    d['walls'], d['floors'], d['doors'], d['windows'], d['stairs'] = h.walls, h.slabs, h.doors, h.windows, h.stairs
    d['objects'], d['zones'], d['roofs'], d['decor'], d['holes'], d['carved'] = h.objects, h.zones, h.roofs, [], [], []
    d['heights'] = ''
    text = json.dumps(d, ensure_ascii=False, indent=2, allow_nan=True).replace('NaN', 'NaN')
    return text


def counts(d):
    return 'стены=%d полы=%d двери=%d окна=%d лестницы=%d объекты=%d зоны=%d крыши=%d' % (
        len(d['walls']), len(d['floors']), len(d['doors']), len(d['windows']), len(d['stairs']), len(d['objects']), len(d['zones']), len(d['roofs']))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    name = args[0] if args else 'night_build'
    floors = int(sys.argv[sys.argv.index('--floors') + 1]) if '--floors' in sys.argv else 5
    if '--check' in sys.argv:
        d = json.load(open(LEVELS / (name + '.json')))
        print(name + ':', counts(d)); return
    template = json.load(open(LEVELS / 'level1.json'))
    template = {k: template[k] for k in ('version', 'cellSize', 'gridWidth', 'gridHeight', 'gridAnchored', 'gridOriginX', 'gridOriginZ',
                                         'baseWidth', 'baseHeight', 'baseOriginX', 'baseOriginZ', 'paintMinX', 'paintMinZ', 'paintPxPerM',
                                         'floorTexture', 'floorTileSize', 'floorBlockTexture', 'wallTexture', 'ceilTexture', 'structTileSize', 'player')}
    layout = sys.argv[sys.argv.index('--layout') + 1] if '--layout' in sys.argv else 'a'
    h = {'b': build_b, 'c': build_c}.get(layout, build)(name, floors)
    text = write(name, h, template)
    d = json.loads(text.replace('NaN', 'null'))
    print(name + ':', counts(d), '| этажей', floors)
    if '--dry' in sys.argv: return
    path = LEVELS / (name + '.json')
    if path.exists() and 'level1' in name: raise SystemExit('level1 не перезаписываем')
    path.write_text(text)
    print('записан', path)


if __name__ == '__main__':
    main()
