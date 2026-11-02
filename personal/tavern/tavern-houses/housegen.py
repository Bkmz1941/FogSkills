#!/usr/bin/env python3
"""Генерация домов «Таверны» (пока коттедж): коробка дома по плану, комнаты с обстановкой, проверка.

python3 housegen.py learn ["Котедж 104"]        выучить коттедж: комнаты, наборы «что на чём», высоты настенного → learned.json, plans/cottage104.json
python3 housegen.py passport <уровень>          паспорт дома: этажи, комнаты с типами, что стоит в каждой
python3 housegen.py build <план.json> <имя>      собрать уровень <имя>.json по плану (коробка + обстановка)
       … --objects-from "Котедж 104"            вместо генерации обстановки — скопировать объекты дома из уровня-источника 1:1
       … --box                                  только коробка, без обстановки
python3 housegen.py new <имя> [--seed N] [--nx 4] [--nz 5] [--floors 2] [--porch W|E|S|N] [--no-void] [--dry]
                                                 новый коттедж по случайному плану; план ложится рядом в plans/<имя>.json
python3 housegen.py check <уровень>             оффлайн-проверка дома в файле уровня (стены, комнаты, мебель) — вердикт HOUSE ok/FAIL
python3 housegen.py edit <уровень> <команда…>   правка обстановки: list | remove <№> | move <№> <dx> <dz> [yaw] | rotate <№> <yaw> | add <комната> <id> [wall:N|S|E|W|center|corner] | swap <№> <id>
python3 housegen.py counts <уровень>            счётчики файла

Мир: клетка 3 м, стена на ребре (толщина 0,25), уровень L = верх плиты (0, 3, 6). Спина объекта смотрит в +Z своей
системы: yaw 0 → +Z (север), 90 → +X (восток), 180 → −Z (юг), 270 → −X (запад). Габариты и флаги дефов — catalog.json
(снимок мостом, catalog_dump.py); правила посадки и наборы — learned.json (снято с коттеджа командой learn).
Уровни Ильи (level1, «Котедж 104» и прочие не house_*) этот скрипт НИКОГДА не перезаписывает.
"""
import collections, copy, json, math, pathlib, random, sys

HERE = pathlib.Path(__file__).resolve().parent
LEVELS = pathlib.Path.home() / '.config/unity3d/DefaultCompany/Tavern/levels'
TEMPLATE_LEVEL = 'Котедж 104'
CS, HALF, LVL_H = 3.0, 0.125, 3.0
FACADE, INNER, TILE = 'WoodPlank002', 'WoodPlank001', 'BathSquareTile'
FLOOR_OAK, FLOOR_TILE, ATTIC_DECK, UNDER = 'CottageFloorOak', 'BathFloorTile', 'BathDeckDark', 'Laminate001'
SOCLE_HEX, TILE_PLINTH_HEX = '#94694F', '#F2F0EB'
STYLE_NONE = {'kind': 0, 'h': 0.0, 'd': 0.0, 'r': 0.0}
STYLE_SOCLE = {'kind': 1, 'h': 0.32, 'd': 0.12, 'r': 0.5}
DOOR_WOOD, DOOR_STEEL, DOOR_GLASS = 7, 8, 9
DOOR_MAT = {DOOR_WOOD: 1, DOOR_STEEL: 4, DOOR_GLASS: 3}
WIN_WHITE, WIN_PVC = 0, 2
SIDES = ('N', 'S', 'E', 'W')
SIDE_YAW = {'N': 0.0, 'E': 90.0, 'S': 180.0, 'W': 270.0}
SIDE_DIR = {'N': (0, 1), 'S': (0, -1), 'E': (1, 0), 'W': (-1, 0)}
OPP = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
CLAD = {INNER: 0.10, FACADE: 0.10, TILE: 0.02, '': 0.10}
SEAT_GAP, CUT_GAP = 0.15, 0.01
TALL = 1.3
FLAT_IDS = {'home_rug_1', 'home_rug_6', 'home_bath_rug_dogs', 'spawn_marker', 'curtain_drapes', 'blind_venetian'}
SEAT_IDS = ('chair', 'stool', 'armchair')
TABLE_IDS = ('table', 'desk')
ROOM_FINISH = {'bathroom': (TILE, FLOOR_TILE)}
PROTECTED = ('level1', 'Котедж', 'Test', 'Sandbox', 'Глава', 'Черное', 'Комнаты', 'Зомби', 'Одежда', 'Предметы', 'Продукты', 'Свет', 'Двери', 'debug_', 'forest', 'crown', 'night_build')

_cat = _learned = _tpl = None


def catalog():
    global _cat
    if _cat is None:
        _cat = json.loads((HERE / 'catalog.json').read_text())['items']
    return _cat


def learned():
    global _learned
    if _learned is None:
        p = HERE / 'learned.json'
        _learned = json.loads(p.read_text()) if p.exists() else {'kits': {}, 'wall_h': {}, 'gap': {}, 'look': {}, 'keep_plinth': []}
    return _learned


def load_level(name):
    return json.loads((LEVELS / (name + '.json')).read_text().replace('NaN', 'null'))


def templates():
    global _tpl
    if _tpl is None:
        p = HERE / 'templates.json'
        if p.exists():
            _tpl = json.loads(p.read_text())
        else:
            d = load_level(TEMPLATE_LEVEL)
            _tpl = {'wall': d['walls'][0], 'floor': d['floors'][0], 'door': d['doors'][0], 'window': d['windows'][0],
                    'stair': d['stairs'][0], 'roof': d['roofs'][0], 'zone': [z for z in d['zones'] if z.get('slug') == 'house_zone1'][0],
                    'object': [o for o in d['objects'] if o['id'] == 'home_bed'][0],
                    'head': {k: d[k] for k in ('version', 'cellSize', 'gridWidth', 'gridHeight', 'gridAnchored', 'gridOriginX', 'gridOriginZ',
                                               'baseWidth', 'baseHeight', 'baseOriginX', 'baseOriginZ', 'paintMinX', 'paintMinZ', 'paintPxPerM',
                                               'floorTexture', 'floorTileSize', 'floorBlockTexture', 'wallTexture', 'ceilTexture', 'structTileSize', 'creatureGear')}}
            _tpl['zone']['cells'], _tpl['zone']['fine'], _tpl['zone']['marks'], _tpl['zone']['events'] = [], [], [], []
            o = _tpl['object']
            for k, v in list(o.items()):
                if isinstance(v, list): o[k] = []
            o.update({'id': '', 'number': 0, 'carrierId': '', 'carrierNode': '', 'sizeW': 0.0, 'sizeD': 0.0, 'sizeH': 0.0, 'sizeP': 0.0,
                      'keepPlinth': False, 'pcSet': False, 'scSet': False, 'palette': -1, 'pattern': 0, 'partCol': '', 'expiry': 0, 'title': '', 'slug': '',
                      'owner': '', 'tel': '', 'shot': '', 'count': -1, 'weightKg': -1.0, 'cellCharge': -2.0, 'wax': -1.0, 'bathFoamLeft': -1.0,
                      'powerOn': True, 'switchOn': True, 'open': False, 'locked': False, 'fireLit': False})
            p.write_text(json.dumps(_tpl, ensure_ascii=False, indent=1))
    return _tpl


def v3(x, y, z): return {'x': float(x), 'y': float(y), 'z': float(z)}


def floor_of(y):
    """Этаж объекта по его y: напольные на L, настенные до L+2,3, потолочные на L+2,8."""
    return int(math.floor((y + 0.15) / LVL_H))


def rot(yaw, x, z):
    a = math.radians(yaw); c, s = math.cos(a), math.sin(a)
    return (x * c + z * s, -x * s + z * c)


def norm_yaw(y): return y % 360.0


def side_of_yaw(yaw):
    y = round(norm_yaw(yaw) / 90.0) % 4
    return ('N', 'E', 'S', 'W')[y]


# ───────────────────────────── сетка и уровень ─────────────────────────────

class Grid:
    def __init__(self, head):
        self.ox, self.oz = head['gridOriginX'], head['gridOriginZ']
    def cx(self, i): return self.ox + i * CS
    def cz(self, j): return self.oz + j * CS
    def cell_of(self, x, z): return (int(math.floor((x - self.ox) / CS + 0.5)), int(math.floor((z - self.oz) / CS + 0.5)))


class Edge:
    """Ребро между клетками. ('x', i, j): между (i,j) и (i,j+1) — стена вдоль X (spansX), сторона A = +Z = (i,j+1).
    ('z', i, j): между (i,j) и (i+1,j) — стена вдоль Z, сторона A = +X = (i+1,j)."""
    @staticmethod
    def between(a, b):
        (i, j), (i2, j2) = a, b
        if i == i2 and j2 == j + 1: return ('x', i, j)
        if i == i2 and j2 == j - 1: return ('x', i, j2)
        if j == j2 and i2 == i + 1: return ('z', i, j)
        if j == j2 and i2 == i - 1: return ('z', i2, j)
        raise ValueError('клетки не соседи: %s %s' % (a, b))

    @staticmethod
    def of_side(cell, side):
        i, j = cell
        return {'N': ('x', i, j), 'S': ('x', i, j - 1), 'E': ('z', i, j), 'W': ('z', i - 1, j)}[side]

    @staticmethod
    def world(grid, e):
        k, i, j = e
        if k == 'x': return grid.cx(i), grid.cz(j) + CS / 2, True
        return grid.cx(i) + CS / 2, grid.cz(j), False

    @staticmethod
    def cells(e):
        k, i, j = e
        return ((i, j), (i, j + 1)) if k == 'x' else ((i, j), (i + 1, j))   # (B, A)


class Level:
    def __init__(self, name, head=None):
        t = templates()
        self.name = name
        self.head = copy.deepcopy(head or t['head'])
        self.grid = Grid(self.head)
        self.walls, self.floors, self.doors, self.windows, self.stairs, self.roofs, self.zones, self.objects = [], [], [], [], [], [], [], []
        self._numbers = collections.Counter()
        self._door_n = 0

    def wall(self, e, L, a, b):
        """a/b = (paint, plinth, plinthHex, plinthStyle) для сторон A и B."""
        t = templates()
        x, z, spans_x = Edge.world(self.grid, e)
        w = copy.deepcopy(t['wall'])
        w.update({'pos': v3(x, L - 0.01 + 1.506, z), 'scale': v3(CS, 3.012, 0.25) if spans_x else v3(0.25, 3.012, CS), 'spansX': spans_x,
                  'colorHex': '', 'material': 0, 'railing': False, 'fence': False, 'fenceOld': False,
                  'paintA': a[0], 'paintB': b[0], 'plinthA': a[1], 'plinthB': b[1], 'plinthHexA': a[2], 'plinthHexB': b[2],
                  'plinthStyleA': dict(a[3]), 'plinthStyleB': dict(b[3])})
        w['_edge'] = e
        self.walls.append(w)
        return w

    def find_wall(self, e, L):
        for w in self.walls:
            if w.get('_edge') == e and abs(w['pos']['y'] - (L + 1.496)) < 0.05: return w
        return None

    def opening(self, kind, e, L, style, open_=False, offset=0.0, locked=False, key=''):
        t = templates()
        w = self.find_wall(e, L)
        if w is None: raise ValueError('нет стены под проём %s на уровне %s' % (e, L))
        self.walls.remove(w)
        x, z, spans_x = Edge.world(self.grid, e)
        rec = copy.deepcopy(t[kind])
        rec.update({'pos': v3(x, L, z), 'spansX': spans_x, 'wallSaved': True, 'wallMaterial': 0, 'wallColorHex': '',
                    'wallPaintA': w['paintA'], 'wallPaintB': w['paintB'], 'wallPlinthA': w['plinthA'], 'wallPlinthB': w['plinthB'],
                    'wallPlinthHexA': w['plinthHexA'], 'wallPlinthHexB': w['plinthHexB'],
                    'wallPlinthStyleA': dict(w['plinthStyleA']), 'wallPlinthStyleB': dict(w['plinthStyleB'])})
        if kind == 'door':
            self._door_n += 1
            rec.update({'locked': locked, 'open': open_, 'material': DOOR_MAT.get(style, 1), 'style': style, 'peepInside': True,
                        'paintA': '', 'paintB': '', 'keyCode': key, 'slug': 'door_%d' % self._door_n, 'swingPositive': True, 'swingOneWay': False,
                        'turned': False, 'mark': '', 'markPositive': True, 'frameHex': '', 'leafHex': ''})
            self.doors.append(rec)
        else:
            rec.update({'style': style, 'open': False, 'paintA': w['paintA'], 'paintB': w['paintB'], 'offset': float(offset), 'inside': -1,
                        'paintHex': '', 'trimHex': '', 'dirty': False})
            self.windows.append(rec)
        rec['_edge'] = e
        return rec

    def slab(self, cell, L, top=FLOOR_OAK, bottom=UNDER, ceiling=False, sx=CS, sz=CS, dx=0.0, dz=0.0):
        t = templates()
        f = copy.deepcopy(t['floor'])
        f.update({'pos': v3(self.grid.cx(cell[0]) + dx, L - 0.1, self.grid.cz(cell[1]) + dz), 'scale': v3(sx, 0.2, sz), 'material': 0, 'ceiling': ceiling,
                  'colorHex': '', 'paintA': top, 'paintB': bottom, 'sideXp': '', 'sideXn': '', 'sideZp': '', 'sideZn': '',
                  'plXp': False, 'plXn': False, 'plZp': False, 'plZn': False, 'plHexXp': '', 'plHexXn': '', 'plHexZp': '', 'plHexZn': ''})
        f['_cell'] = tuple(cell)
        self.floors.append(f)
        return f

    def stair(self, a, b, L, landing=True, top=FLOOR_OAK, side=INNER):
        """Лестница по клеткам a → b (соседи по одной оси): корень на стыке, подъём от a к b."""
        t = templates()
        (i, j), (i2, j2) = a, b
        x = (self.grid.cx(i) + self.grid.cx(i2)) / 2; z = (self.grid.cz(j) + self.grid.cz(j2)) / 2
        yaw = 90.0 if i2 > i else 270.0 if i2 < i else 0.0 if j2 > j else 180.0
        s = copy.deepcopy(t['stair'])
        s.update({'pos': v3(x, L, z), 'rotY': yaw, 'riseCells': 1, 'lengthCells': 1 if landing else 2, 'material': 0, 'visual': '',
                  'paintL': side if not landing else '', 'paintR': side, 'paintT': top, 'plinthL': False, 'plinthR': landing, 'plinthHexL': '', 'plinthHexR': '',
                  'colorHex': '', 'landing': landing, 'paintB': side, 'plinthB': False, 'plinthHexB': ''})
        s['_cells'] = (tuple(a), tuple(b))
        self.stairs.append(s)
        return s

    def roof(self, cells, L, style=0):
        t = templates()
        xs = [self.grid.cx(i) for i, j in cells]; zs = [self.grid.cz(j) for i, j in cells]
        nx = int(round((max(xs) - min(xs)) / CS)) + 1; nz = int(round((max(zs) - min(zs)) / CS)) + 1
        r = copy.deepcopy(t['roof'])
        r.update({'pos': v3((max(xs) + min(xs)) / 2, L, (max(zs) + min(zs)) / 2), 'cellsX': nx, 'cellsZ': nz, 'style': style, 'partCol': '', 'dirty': False})
        self.roofs.append(r)
        return r

    def zone(self, name, slug, L, cells, kind=2, color=(0.45, 0.65, 0.9)):
        t = templates()
        z = copy.deepcopy(t['zone'])
        z.update({'name': name, 'slug': slug, 'cr': color[0], 'cg': color[1], 'cb': color[2], 'kind': kind, 'strong': True, 'fireSpread': False,
                  'temp': float('nan'), 'attackers': '', 'exits': '', 'note': '', 'fog': False, 'fogStrong': True, 'fire': False, 'fireStrong': True, 'wind': False,
                  'cells': [v3(self.grid.cx(i), L + 0.1, self.grid.cz(j)) for i, j in cells], 'fine': [], 'marks': [], 'events': []})
        self.zones.append(z)
        return z

    def obj(self, oid, x, y, z, yaw=0.0, **fields):
        t = templates()
        o = copy.deepcopy(t['object'])
        self._numbers[oid] += 1
        o.update({'id': oid, 'pos': v3(x, y, z), 'rotY': float(norm_yaw(yaw)), 'rotX': 0.0, 'rotZ': 0.0, 'number': self._numbers[oid]})
        look = learned().get('look', {}).get(oid)
        if look: o.update(look)
        if oid in learned().get('keep_plinth', []): o['keepPlinth'] = True
        o.update(fields)
        self.objects.append(o)
        return o

    def data(self, player=None):
        d = dict(self.head)
        d.update({'sceneName': self.name, 'slug': self.name, 'nameEn': '', 'aiBrief': '', 'aiTriggers': '', 'aiEvents': '', 'aiMonsters': '', 'aiRules': '', 'aiOffscreen': '',
                  'heights': '', 'carved': [], 'holes': [], 'decor': [], 'water': [], 'storyEvents': [],
                  'player': player or {'saved': False, 'worn': [], 'containers': []}})
        strip = lambda lst: [{k: v for k, v in r.items() if not k.startswith('_')} for r in lst]
        d['walls'], d['floors'], d['doors'], d['windows'], d['stairs'] = strip(self.walls), strip(self.floors), strip(self.doors), strip(self.windows), strip(self.stairs)
        d['roofs'], d['zones'], d['objects'] = strip(self.roofs), strip(self.zones), strip(self.objects)
        return d

    def write(self, player=None):
        if any(self.name.startswith(p) for p in PROTECTED) or not self.name.startswith('house_'):
            raise SystemExit('имя уровня должно начинаться с house_ (уровни Ильи не перезаписываем): ' + self.name)
        path = LEVELS / (self.name + '.json')
        text = json.dumps(self.data(player), ensure_ascii=False, indent=2, allow_nan=True)
        path.write_text(text)
        return path


def counts(d):
    return 'стены=%d полы=%d двери=%d окна=%d лестницы=%d крыши=%d зоны=%d объекты=%d' % (
        len(d['walls']), len(d['floors']), len(d['doors']), len(d['windows']), len(d['stairs']), len(d['roofs']), len(d['zones']), len(d['objects']))


# ───────────────────────────── геометрия объектов ─────────────────────────────

class Item:
    """Поставленный объект: деф каталога + корень + yaw; след (axis-aligned bbox) считается от габарита каталога."""
    def __init__(self, oid, x, y, z, yaw, L, room=None, fields=None):
        self.id, self.x, self.y, self.z, self.yaw, self.L, self.room = oid, x, y, z, norm_yaw(yaw), L, room
        self.fields = fields or {}
        c = catalog().get(oid) or {}
        self.w, self.d, self.h = c.get('w') or 0.3, c.get('d') or 0.3, c.get('h') or 0.3
        self.cx, self.cz, self.y0 = c.get('cx') or 0.0, c.get('cz') or 0.0, c.get('y0') or 0.0
        self.mount = c.get('mount', 'Floor')
        self.side = None
        self.t = None

    @property
    def flat(self): return self.id in FLAT_IDS or self.h < 0.08

    def rect(self):
        pts = [rot(self.yaw, self.cx + sx * self.w / 2, self.cz + sz * self.d / 2) for sx in (-1, 1) for sz in (-1, 1)]
        xs = [self.x + p[0] for p in pts]; zs = [self.z + p[1] for p in pts]
        return (min(xs), min(zs), max(xs), max(zs))

    def center(self):
        dx, dz = rot(self.yaw, self.cx, self.cz)
        return (self.x + dx, self.z + dz)

    def top(self): return self.y + self.y0 + self.h

    def along_width(self):
        """Протяжённость следа вдоль стены (ширина w ложится вдоль стены при любом yaw кратном 90)."""
        return self.w


def overlaps(r1, r2, margin=0.0):
    return not (r1[2] + margin <= r2[0] or r2[2] + margin <= r1[0] or r1[3] + margin <= r2[1] or r2[3] + margin <= r1[1])


def obb_overlap(a, b, tol=0.0):
    """Пересечение двух повёрнутых прямоугольников (SAT) с допуском tol по глубине захода."""
    def corners(it):
        return [(it.x + p[0], it.z + p[1]) for p in (rot(it.yaw, it.cx + sx * it.w / 2, it.cz + sz * it.d / 2) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)))]
    ca, cb = corners(a), corners(b)
    for poly in (ca, cb):
        for i in range(4):
            x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % 4]
            nx, nz = -(z2 - z1), (x2 - x1)
            ln = math.hypot(nx, nz) or 1.0
            nx, nz = nx / ln, nz / ln
            pa = [x * nx + z * nz for x, z in ca]; pb = [x * nx + z * nz for x, z in cb]
            if max(pa) - tol <= min(pb) or max(pb) - tol <= min(pa): return False
    return True


def rect_inside(r, box, tol=0.02):
    return r[0] >= box[0] - tol and r[1] >= box[1] - tol and r[2] <= box[2] + tol and r[3] <= box[3] + tol


# ───────────────────────────── дом из плана ─────────────────────────────

class Room:
    def __init__(self, name, rtype, cells, floor, level):
        self.name, self.type, self.cells, self.floor, self.L = name, rtype, set(map(tuple, cells)), floor, level
        self.holes = set()
        self.items = []
        self.doors = []      # (edge, side, door-record)
        self.windows = []    # (edge, side, record)
        self.open_edges = set()
        self.walls = {}      # edge -> True
        self.stair = None

    @property
    def finish(self):
        return ROOM_FINISH.get(self.type, (INNER, FLOOR_OAK))

    def bbox_cells(self):
        us = [c[0] for c in self.cells]; vs = [c[1] for c in self.cells]
        return min(us), min(vs), max(us), max(vs)


def wall_side_spec(paint, plinth, hex_, style): return (paint, plinth, hex_, style)


def inner_spec(room):
    paint = room.finish[0]
    return wall_side_spec(paint, True, TILE_PLINTH_HEX if paint == TILE else '', STYLE_NONE)


def facade_spec(ground):
    return wall_side_spec(FACADE, ground, SOCLE_HEX if ground else '', STYLE_SOCLE if ground else STYLE_NONE)


class House:
    """Собранный дом: уровень + комнаты по этажам (для обстановки и проверок)."""
    def __init__(self, plan, level):
        self.plan, self.level = plan, level
        self.rooms = []          # все комнаты всех этажей
        self.by_floor = collections.defaultdict(list)
        self.i0, self.j0 = plan.get('i0', 49), plan.get('j0', 48)

    def cell(self, u, v): return (self.i0 + u, self.j0 + v)

    def room_at(self, cell, floor):
        for r in self.by_floor[floor]:
            if tuple(cell) in r.cells: return r
        return None

    def find_room(self, name):
        for r in self.rooms:
            if r.name == name: return r
        raise KeyError('нет комнаты ' + name)


def build_house(plan, name):
    """План → Level с коробкой (стены, плиты, проёмы, лестницы, крыша, зоны, маркер) и список комнат."""
    lv = Level(name, plan.get('head'))
    h = House(plan, lv)
    floors = plan['floors']
    nfl = len(floors)
    for f, fl in enumerate(floors):
        L = f * LVL_H
        for rd in fl['rooms']:
            r = Room(rd['name'], rd['type'], [h.cell(u, v) for u, v in rd['cells']], f, L)
            r.holes = set(h.cell(u, v) for u, v in rd.get('holes', []))
            h.rooms.append(r); h.by_floor[f].append(r)
        fl['_open'] = set(tuple(sorted((tuple(h.cell(*a)), tuple(h.cell(*b))))) for a, b in fl.get('open', []))
    # лестницы и дырки над ними
    for f, fl in enumerate(floors):
        st = fl.get('stair')
        if st:
            a, b = h.cell(*st['cells'][0]), h.cell(*st['cells'][1])
            room = h.room_at(a, f)
            room.stair = (a, b, st.get('landing', True))
            if f + 1 < nfl:
                up = h.room_at(a, f + 1) or h.room_at(b, f + 1)
                if up: up.holes.update({a, b})
    # стены и плиты
    for f, fl in enumerate(floors):
        L = f * LVL_H
        ground = f == 0
        footprint = {}
        for r in h.by_floor[f]:
            for c in r.cells: footprint[c] = r
        for c, r in footprint.items():
            if c not in r.holes:
                top = r.finish[1]
                below = h.room_at(c, f - 1) if f > 0 else None
                bottom = (below.finish[0] if below else INNER) if f > 0 else UNDER
                if f > 0 and below is None: bottom = FACADE
                lv.slab(c, L, top=top, bottom=bottom, ceiling=f > 0)
        done = set()
        for c, r in footprint.items():
            for side in SIDES:
                e = Edge.of_side(c, side)
                if e in done: continue
                n = (c[0] + SIDE_DIR[side][0], c[1] + SIDE_DIR[side][1])
                rn = footprint.get(n)
                if rn is r: continue
                if rn is not None and tuple(sorted((c, n))) in fl['_open']:
                    r.open_edges.add(e); rn.open_edges.add(e); done.add(e); continue
                done.add(e)
                cb, ca = Edge.cells(e)
                rb, ra = footprint.get(cb), footprint.get(ca)
                a = inner_spec(ra) if ra else facade_spec(ground)
                b = inner_spec(rb) if rb else facade_spec(ground)
                lv.wall(e, L, a, b)
                r.walls[e] = True
                if rn: rn.walls[e] = True
        # проёмы
        for dd in fl.get('doors', []):
            a, b = h.cell(*dd['a']), h.cell(*dd['b'])
            e = Edge.between(a, b)
            rec = lv.opening('door', e, L, dd.get('style', DOOR_WOOD), open_=dd.get('open', False))
            for c in (a, b):
                r = footprint.get(c)
                if r:
                    side = side_between(c, a if c != a else b)
                    r.doors.append((e, side, rec)); r.walls.pop(e, None)
        for dd in fl.get('ext_doors', []):
            c = h.cell(*dd['cell']); e = Edge.of_side(c, dd['side'])
            rec = lv.opening('door', e, L, dd.get('style', DOOR_STEEL), open_=dd.get('open', False), key=dd.get('key', ''))
            r = footprint[c]; r.doors.append((e, dd['side'], rec)); r.walls.pop(e, None)
            if dd.get('entrance'): h.entrance = (c, dd['side'], f)
        for wd in fl.get('windows', []):
            c = h.cell(*wd['cell']); e = Edge.of_side(c, wd['side'])
            rec = lv.opening('window', e, L, wd.get('style', WIN_WHITE), offset=wd.get('offset', 0.0))
            r = footprint[c]; r.windows.append((e, wd['side'], rec)); r.walls.pop(e, None)
        # лестница этажа
        st = fl.get('stair')
        if st:
            a, b = h.cell(*st['cells'][0]), h.cell(*st['cells'][1])
            room = h.room_at(a, f)
            lv.stair(a, b, L, landing=st.get('landing', True), top=room.finish[1])
        # ограждение дырок стенами по плану (доп. стены)
        for ww in fl.get('walls', []):
            a, b = h.cell(*ww['a']), h.cell(*ww['b'])
            e = Edge.between(a, b)
            ra, rb = footprint.get(a), footprint.get(b)
            if lv.find_wall(e, L): continue
            lv.wall(e, L, inner_spec(ra or rb), inner_spec(rb or ra))
            for r in (ra, rb):
                if r: r.walls[e] = True; r.open_edges.discard(e)
    # крыльцо и балкон
    porch = plan.get('porch')
    if porch:
        cells = [h.cell(u, v) for u, v in porch['cells']]
        for c in cells: lv.slab(c, 0.0, top=FLOOR_OAK, bottom=UNDER, ceiling=False)
        if plan.get('balcony', True) and nfl > 1:
            for c in cells: lv.slab(c, LVL_H, top=FLOOR_OAK, bottom=FACADE, ceiling=True)
        h.porch_cells = cells
    # потолок над верхним этажом и крыша
    top_cells = set()
    for r in h.by_floor[nfl - 1]: top_cells |= r.cells
    all_cells = set()
    for r in h.rooms: all_cells |= r.cells
    Ltop = nfl * LVL_H
    for c in sorted(top_cells):
        below = h.room_at(c, nfl - 1)
        lv.slab(c, Ltop, top=ATTIC_DECK, bottom=below.finish[0] if below else INNER, ceiling=True)
    lv.roof(sorted(all_cells), Ltop, style=plan.get('roof', {}).get('style', 0))
    for f in range(nfl):
        cells = set()
        for r in h.by_floor[f]: cells |= r.cells
        lv.zone('Дом' if f == 0 else '', 'house_zone%d' % (f + 1), f * LVL_H, sorted(cells))
    # спавн — снаружи перед входом
    c, side, f = h.entrance
    dx, dz = SIDE_DIR[side]
    sx, sz = lv.grid.cx(c[0]) + dx * (CS if not porch else 2 * CS + 1.0), lv.grid.cz(c[1]) + dz * (CS if not porch else 2 * CS + 1.0)
    lv.obj('spawn_marker', sx, -0.1, sz, SIDE_YAW[OPP[side]])
    return h


def side_between(c, n):
    for s, (dx, dz) in SIDE_DIR.items():
        if (c[0] + dx, c[1] + dz) == tuple(n): return s
    raise ValueError


# ───────────────────────────── обстановка ─────────────────────────────

class RoomGeom:
    """Комната как прямоугольник со стенами по сторонам: пробеги стен, двери, окна, зоны у дверей, лестница."""
    def __init__(self, house, room):
        self.h, self.r = house, room
        g = house.level.grid
        u0, v0, u1, v1 = room.bbox_cells()
        self.box = [g.cx(u0) - CS / 2, g.cz(v0) - CS / 2, g.cx(u1) + CS / 2, g.cz(v1) + CS / 2]
        self.inner = list(self.box)
        self.segments = {s: [] for s in SIDES}
        self.door_zones = []
        self.blocked = []
        self.tile = room.finish[0] == TILE
        walls = house.level.walls
        for c in sorted(room.cells):
            for side in SIDES:
                e = Edge.of_side(c, side)
                n = (c[0] + SIDE_DIR[side][0], c[1] + SIDE_DIR[side][1])
                if n in room.cells: continue
                kind = 'open'
                if e in room.walls: kind = 'wall'
                for (de, ds, _) in room.doors:
                    if de == e: kind = 'door'
                for (we, ws, _) in room.windows:
                    if we == e: kind = 'window'
                along = g.cx(c[0]) if side in ('N', 'S') else g.cz(c[1])
                self.segments[side].append((along - CS / 2, along + CS / 2, kind, c))
                if kind in ('door', 'open'):
                    depth = 1.6 if kind == 'door' else 1.0
                    w = 0.85 if kind == 'door' else CS / 2
                    self._add_zone(side, along, w, depth, c)
        for side in SIDES:
            segs = self.segments[side]
            if segs and all(s[2] != 'open' for s in segs):
                if side == 'S': self.inner[1] = self.box[1] + HALF
                if side == 'N': self.inner[3] = self.box[3] - HALF
                if side == 'W': self.inner[0] = self.box[0] + HALF
                if side == 'E': self.inner[2] = self.box[2] - HALF
        for c in room.holes:
            self.blocked.append((g.cx(c[0]) - CS / 2, g.cz(c[1]) - CS / 2, g.cx(c[0]) + CS / 2, g.cz(c[1]) + CS / 2, 'hole'))
        if room.stair:
            a, b, landing = room.stair
            for c in (a, b):
                self.blocked.append((g.cx(c[0]) - CS / 2, g.cz(c[1]) - CS / 2, g.cx(c[0]) + CS / 2, g.cz(c[1]) + CS / 2, 'stair'))
            dx, dz = b[0] - a[0], b[1] - a[1]
            # подход к низу марша — клетка перед входом поперёк подъёма свободна на 1,2 м
            ax, az = g.cx(a[0]), g.cz(a[1])
            if dx != 0: self.blocked.append((ax - CS / 2, az - CS / 2 - 1.2, ax + CS / 2, az - CS / 2, 'stair_in'))
            else: self.blocked.append((ax - CS / 2 - 1.2, az - CS / 2, ax - CS / 2, az + CS / 2, 'stair_in'))

    def _add_zone(self, side, along, half_w, depth, c):
        g = self.h.level.grid
        if side == 'S': self.door_zones.append((along - half_w, self.box[1], along + half_w, self.box[1] + depth))
        if side == 'N': self.door_zones.append((along - half_w, self.box[3] - depth, along + half_w, self.box[3]))
        if side == 'W': self.door_zones.append((self.box[0], along - half_w, self.box[0] + depth, along + half_w))
        if side == 'E': self.door_zones.append((self.box[2] - depth, along - half_w, self.box[2], along + half_w))

    def face(self, side):
        return {'S': self.box[1] + HALF, 'N': self.box[3] - HALF, 'W': self.box[0] + HALF, 'E': self.box[2] - HALF}[side]

    def runs(self, side, low_ok=False):
        """Пробеги стены стороны side, где можно ставить спиной: список (t0, t1). Окно — только для низкого."""
        out = []
        for (t0, t1, kind, c) in sorted(self.segments[side]):
            ok = kind == 'wall' or (kind == 'window' and low_ok)
            if ok and out and abs(out[-1][1] - t0) < 1e-6: out[-1] = (out[-1][0], t1)
            elif ok: out.append((t0, t1))
        door_ts = [((t0 + t1) / 2) for (t0, t1, kind, c) in self.segments[side] if kind == 'door']
        res = []
        for (t0, t1) in out:
            cuts = [(t0, t1)]
            for dt in door_ts:
                nxt = []
                for (a, b) in cuts:
                    if dt + 0.95 <= a or dt - 0.95 >= b: nxt.append((a, b)); continue
                    if a < dt - 0.95: nxt.append((a, dt - 0.95))
                    if dt + 0.95 < b: nxt.append((dt + 0.95, b))
                cuts = nxt
            res.extend(cuts)
        return res

    def windows_on(self, side):
        return [((t0 + t1) / 2, c) for (t0, t1, kind, c) in self.segments[side] if kind == 'window']

    def doors_on(self, side):
        return [((t0 + t1) / 2, c) for (t0, t1, kind, c) in self.segments[side] if kind == 'door']

    def has_wall(self, side):
        return any(k == 'wall' for (_, _, k, _) in self.segments[side])

    def corner_solid(self, side, end, t):
        """Угол в конце пробега стены side: координата t лежит у края комнаты, а соседняя сторона там — стена или окно."""
        edge = {('S', 'low'): self.box[0], ('S', 'high'): self.box[2], ('N', 'low'): self.box[0], ('N', 'high'): self.box[2],
                ('W', 'low'): self.box[1], ('W', 'high'): self.box[3], ('E', 'low'): self.box[1], ('E', 'high'): self.box[3]}[(side, end)]
        if abs(t - edge) > 0.2: return False
        other = {('S', 'low'): 'W', ('S', 'high'): 'E', ('N', 'low'): 'W', ('N', 'high'): 'E',
                 ('W', 'low'): 'S', ('W', 'high'): 'N', ('E', 'low'): 'S', ('E', 'high'): 'N'}[(side, end)]
        along = self.face(side)
        for (t0, t1, kind, c) in self.segments[other]:
            if t0 - 0.2 <= along <= t1 + 0.2: return kind in ('wall', 'window')
        return False


class Furnisher:
    def __init__(self, house, rng):
        self.h, self.lv, self.rng = house, house.level, rng
        self.geoms = {r.name: RoomGeom(house, r) for r in house.rooms}
        self.placed = {r.name: [] for r in house.rooms}
        self.report = []

    # ─── низкоуровневая посадка
    def gap_for(self, oid):
        c = catalog().get(oid) or {}
        g = learned().get('gap', {}).get(oid)
        if g is not None: return g
        if c.get('mount') == 'Wall': return 0.0
        return SEAT_GAP

    def wall_root(self, geom, oid, side, t, gap=None, wall_mount=False):
        """Корень объекта спиной к стене side с центром следа на координате t вдоль стены."""
        c = catalog()[oid]
        w, d, cx, cz = c['w'] or 0.3, c['d'] or 0.3, c['cx'] or 0.0, c['cz'] or 0.0
        yaw = SIDE_YAW[side]
        clad = 0.02 if geom.tile else 0.10
        g = (clad if wall_mount else self.gap_for(oid)) if gap is None else gap
        n = SIDE_DIR[side]
        face = geom.face(side)
        back_off = cz + d / 2
        ox, oz = rot(yaw, cx, 0.0)
        if side in ('N', 'S'):
            z = face - n[1] * (g + back_off); x = t - ox
        else:
            x = face - n[0] * (g + back_off); z = t - oz
        return x, z, yaw

    def fits(self, room, item, allow_zone=False, margin=0.03, ignore=()):
        return self.why_not(room, item, allow_zone, margin, ignore) is None

    def why_not(self, room, item, allow_zone=False, margin=0.03, ignore=()):
        geom = self.geoms[room.name]
        r = item.rect()
        if not rect_inside(r, geom.inner, tol=0.03): return 'вне комнаты'
        if not item.flat:
            for b in geom.blocked:
                if overlaps(r, b[:4]): return 'лестница' if b[4].startswith('stair') else 'проём в полу'
            if not allow_zone:
                for zn in geom.door_zones:
                    if overlaps(r, zn): return 'зона двери'
            for other in self.placed[room.name]:
                if other in ignore or other.flat or other.mount in ('Wall', 'Ceiling', 'Surface'): continue
                if overlaps(r, other.rect(), margin): return 'упёрся в ' + other.id
        self._last_why = None
        return None

    def commit(self, room, item, note=''):
        self.placed[room.name].append(item)
        room.items.append(item)
        rec = self.lv.obj(item.id, item.x, item.y, item.z, item.yaw, **item.fields)
        item.rec = rec
        self.report.append('%-12s %-30s %s' % (room.name, item.id, note))
        return item

    # ─── приёмы
    def front_clear(self, room, item, depth):
        n = SIDE_DIR[side_of_yaw(item.yaw)]
        r = item.rect()
        zone = (r[0], r[1] - depth, r[2], r[1]) if n == (0, 1) else (r[0], r[3], r[2], r[3] + depth) if n == (0, -1) else (r[0] - depth, r[1], r[0], r[3]) if n == (1, 0) else (r[2], r[1], r[2] + depth, r[3])
        geom = self.geoms[room.name]
        if not rect_inside(zone, geom.inner, tol=0.05): return False
        for b in geom.blocked:
            if overlaps(zone, b[:4]): return False
        for other in self.placed[room.name]:
            if other.flat or other.mount in ('Wall', 'Ceiling', 'Surface'): continue
            if overlaps(zone, other.rect()): return False
        return True

    def at_wall(self, room, oid, sides=None, corner=None, low_ok=None, want_t=None, gap=None, prefer_blind=True, allow_zone=False, front=0.0, avoid_doors=False):
        geom = self.geoms[room.name]
        c = catalog()[oid]
        tall = (c['h'] or 0) >= TALL
        if low_ok is None: low_ok = not tall
        w = c['w'] or 0.3
        cands = []
        u0, v0, u1, v1 = room.bbox_cells()
        long_sides = ('N', 'S') if (u1 - u0) > (v1 - v0) else ('E', 'W') if (v1 - v0) > (u1 - u0) else SIDES
        order = list(sides) if sides else sorted(SIDES, key=lambda sd: (-max([t1 - t0 for (t0, t1) in geom.runs(sd, low_ok)] or [0]), 0 if sd in long_sides else 1, 1 if geom.doors_on(sd) else 0))
        if avoid_doors: order = sorted(order, key=lambda sd: 1 if geom.doors_on(sd) else 0)
        for side in order:
            for (t0, t1) in geom.runs(side, low_ok):
                if t1 - t0 < w + 0.06: continue
                ts = []
                if want_t is not None:
                    ts = [max(t0 + HALF + w / 2 + 0.03, min(t1 - HALF - w / 2 - 0.03, want_t))]
                else:
                    lo, hi, mid = t0 + HALF + w / 2 + 0.05, t1 - HALF - w / 2 - 0.05, (t0 + t1) / 2
                    if corner == 'any':
                        ts = [tt for tt, e_, ok in sorted(((lo, 'low', geom.corner_solid(side, 'low', t0)), (hi, 'high', geom.corner_solid(side, 'high', t1))), key=lambda q: 0 if q[2] else 1)]
                    elif corner == 'low': ts = [lo, mid, hi]
                    elif corner == 'high': ts = [hi, mid, lo]
                    else: ts = [mid]
                    k = 0.5
                    while mid - k >= lo:
                        ts += [mid - k, mid + k]; k += 0.5
                    ts += [lo, hi]
                has_win = bool(geom.windows_on(side))
                for t in ts:
                    cands.append((side, t, has_win))
        if corner == 'any':
            def solid_first(cnd):
                side_, t_, _ = cnd
                for (t0, t1) in geom.runs(side_, low_ok):
                    if t0 <= t_ <= t1:
                        if geom.corner_solid(side_, 'low', t0) and abs(t_ - (t0 + HALF + w / 2 + 0.05)) < 0.01: return 0
                        if geom.corner_solid(side_, 'high', t1) and abs(t_ - (t1 - HALF - w / 2 - 0.05)) < 0.01: return 0
                return 1
            cands = sorted(cands, key=solid_first)
        fallback = None
        for side, t, has_win in cands:
            x, z, yaw = self.wall_root(geom, oid, side, t, gap)
            it = Item(oid, x, room.L, z, yaw, room.L, room)
            it.side, it.t = side, t
            if self.fits(room, it, allow_zone=allow_zone):
                if front and not self.front_clear(room, it, front):
                    if fallback is None: fallback = it
                    continue
                return self.commit(room, it, 'стена %s t=%.2f' % (side, t))
        if fallback is not None:
            return self.commit(room, fallback, 'стена %s t=%.2f (тесно спереди)' % (fallback.side, fallback.t))
        self.report.append('%-12s %-30s НЕ ВСТАЛ (стена: %s)' % (room.name, oid, self._why_summary(room, oid, cands, gap)))
        return None

    def _why_summary(self, room, oid, cands, gap):
        geom = self.geoms[room.name]
        reasons = collections.Counter()
        for side, t, has_win in cands[:40]:
            x, z, yaw = self.wall_root(geom, oid, side, t, gap)
            it = Item(oid, x, room.L, z, yaw, room.L, room)
            reasons[self.why_not(room, it) or 'ок'] += 1
        return 'нет пробега' if not cands else ', '.join('%s×%d' % (k, v) for k, v in reasons.most_common(3))

    def corner_module(self, room, oid, prefer=None):
        """Угловой модуль (крыло влево): для угла NE — стена E, NW — N, SE — S, SW — W; левый торец в углу."""
        geom = self.geoms[room.name]
        c = catalog()[oid]
        w, d = c['w'], c['d']
        corners = prefer or ['NE', 'NW', 'SE', 'SW']
        for cn in corners:
            side = {'NE': 'E', 'NW': 'N', 'SE': 'S', 'SW': 'W'}[cn]
            other = {'NE': 'N', 'NW': 'W', 'SE': 'E', 'SW': 'S'}[cn]
            runs = geom.runs(side, False); runs2 = geom.runs(other, False)
            if not runs or not runs2: continue
            end_t = geom.face(other)
            run = max(runs, key=lambda r: r[1]) if other in ('N', 'E') else min(runs, key=lambda r: r[0])
            if other in ('N', 'E'):
                if abs(run[1] - end_t) > 0.2 or run[1] - run[0] < w: continue
                t = end_t - 0.02 - w / 2
            else:
                if abs(run[0] - end_t) > 0.2 or run[1] - run[0] < w: continue
                t = end_t + 0.02 + w / 2
            run2 = max(runs2, key=lambda r: r[1]) if side in ('N', 'E') else min(runs2, key=lambda r: r[0])
            need = d + SEAT_GAP
            if side in ('N', 'E'):
                if abs(run2[1] - geom.face(side)) > 0.2 or run2[1] - run2[0] < need: continue
            else:
                if abs(run2[0] - geom.face(side)) > 0.2 or run2[1] - run2[0] < need: continue
            x, z, yaw = self.wall_root(geom, oid, side, t)
            it = Item(oid, x, room.L, z, yaw, room.L, room)
            it.side, it.t, it.corner = side, t, cn
            if self.fits(room, it):
                return self.commit(room, it, 'угол %s' % cn)
        self.report.append('%-12s %-30s НЕ ВСТАЛ (угол)' % (room.name, oid))
        return None

    def beside(self, room, oid, anchor, direction=None, gap=0.08, gap_wall=None):
        """Рядом с anchor вдоль той же стены (direction: 'low'/'high' по координате вдоль стены, None — обе)."""
        if anchor is None or anchor.side is None: return None
        geom = self.geoms[room.name]
        c = catalog()[oid]
        w = c['w']
        ar = anchor.rect()
        if anchor.side in ('N', 'S'): a_lo, a_hi = ar[0], ar[2]
        else: a_lo, a_hi = ar[1], ar[3]
        runs = geom.runs(anchor.side, low_ok=(c['h'] or 0) < TALL)
        def backed(t):
            return any(t0 - 0.05 <= t - w / 2 and t + w / 2 <= t1 + 0.05 for (t0, t1) in runs)
        dirs = [direction] if direction else self.rng.sample(['low', 'high'], 2)
        dirs = sorted(dirs, key=lambda dr: 0 if backed((a_lo - gap - w / 2) if dr == 'low' else (a_hi + gap + w / 2)) else 1)
        for dr in dirs:
            t = (a_lo - gap - w / 2) if dr == 'low' else (a_hi + gap + w / 2)
            x, z, yaw = self.wall_root(geom, oid, anchor.side, t, gap_wall)
            it = Item(oid, x, room.L, z, yaw, room.L, room)
            it.side, it.t = anchor.side, t
            if self.fits(room, it, margin=0.0):
                return self.commit(room, it, 'рядом с %s (%s)' % (anchor.id, dr))
        self.report.append('%-12s %-30s НЕ ВСТАЛ (рядом с %s)' % (room.name, oid, anchor.id))
        return None

    def wing_end(self, room, oid, anchor):
        """У торца крыла углового модуля: на второй стене угла, сразу за концом крыла."""
        if anchor is None or getattr(anchor, 'corner', None) is None: return None
        geom = self.geoms[room.name]
        other = {'NE': 'N', 'NW': 'W', 'SE': 'E', 'SW': 'S'}[anchor.corner]
        c = catalog()[oid]; w = c['w']
        ar = anchor.rect()
        if other in ('N', 'S'):
            end_lo, end_hi = ar[0], ar[2]
            t = (end_lo - 0.02 - w / 2) if anchor.side == 'E' else (end_hi + 0.02 + w / 2)
        else:
            end_lo, end_hi = ar[1], ar[3]
            t = (end_lo - 0.02 - w / 2) if anchor.side == 'N' else (end_hi + 0.02 + w / 2)
        x, z, yaw = self.wall_root(geom, oid, other, t)
        it = Item(oid, x, room.L, z, yaw, room.L, room)
        it.side, it.t = other, t
        if self.fits(room, it, margin=-0.02):
            return self.commit(room, it, 'за крылом %s' % anchor.id)
        return self.at_wall(room, oid, sides=[other])

    def free(self, room, oid, at=(0.5, 0.5), yaw=None, jitter=0.0, allow_zone=False):
        geom = self.geoms[room.name]
        x0, z0, x1, z1 = geom.inner
        if yaw is None: yaw = self.rng.choice([0, 90, 180, 270]) if self.rng else 0
        c = catalog()[oid]
        fx, fz = at
        base = (x0 + (x1 - x0) * fx, z0 + (z1 - z0) * fz)
        tries = [(0, 0)] + [(dx, dz) for k in (0.5, 1.0, 1.5, 2.0, 2.5) for dx in (-k, 0, k) for dz in (-k, 0, k)]
        for dx, dz in tries:
            jx = self.rng.uniform(-jitter, jitter) if jitter else 0.0
            jz = self.rng.uniform(-jitter, jitter) if jitter else 0.0
            cx0, cz0 = rot(yaw, c['cx'] or 0.0, c['cz'] or 0.0)
            it = Item(oid, base[0] + dx + jx - cx0, room.L, base[1] + dz + jz - cz0, yaw, room.L, room)
            if self.fits(room, it, allow_zone=allow_zone):
                return self.commit(room, it, 'свободно %.2f,%.2f' % (fx, fz))
        self.report.append('%-12s %-30s НЕ ВСТАЛ (свободно)' % (room.name, oid))
        return None

    def front(self, room, oid, anchor, dist=0.15, face=True, shift=0.0, allow_zone=False):
        """Перед anchor (со стороны его лица), лицом к нему, если face."""
        if anchor is None: return None
        c = catalog()[oid]
        n = SIDE_DIR[side_of_yaw(anchor.yaw)]
        acx, acz = anchor.center()
        ar = anchor.rect()
        front_dist = (ar[3] - ar[1]) / 2 if n[1] else (ar[2] - ar[0]) / 2
        yaw = norm_yaw(anchor.yaw + (180 if face else 0))
        ccx, ccz = rot(yaw, c['cx'] or 0.0, c['cz'] or 0.0)
        along = (-n[1], n[0])
        for extra in (0.0, 0.3, 0.6, -0.3, 0.9):
            cx = acx - n[0] * (front_dist + dist + c['d'] / 2 + extra) + along[0] * shift
            cz = acz - n[1] * (front_dist + dist + c['d'] / 2 + extra) + along[1] * shift
            it = Item(oid, cx - ccx, room.L, cz - ccz, yaw, room.L, room)
            if self.fits(room, it, allow_zone=allow_zone, ignore=(anchor,) if c['h'] < 0.1 else ()):
                return self.commit(room, it, 'перед %s' % anchor.id)
        self.report.append('%-12s %-30s НЕ ВСТАЛ (перед %s)' % (room.name, oid, anchor.id))
        return None

    def around(self, room, oid, anchor, n=3, dist=0.1):
        """Стулья вокруг стола: с четырёх сторон, лицом к столу, n штук."""
        if anchor is None: return []
        out = []
        acx, acz = anchor.center(); ar = anchor.rect()
        c = catalog()[oid]
        for side in ['S', 'N', 'E', 'W'][:4]:
            if len(out) >= n: break
            dx, dz = SIDE_DIR[side]
            half = (ar[3] - ar[1]) / 2 if dz else (ar[2] - ar[0]) / 2
            yaw = SIDE_YAW[side]
            ccx, ccz = rot(yaw, c['cx'] or 0.0, c['cz'] or 0.0)
            cx = acx + dx * (half + dist + c['d'] / 2); cz = acz + dz * (half + dist + c['d'] / 2)
            it = Item(oid, cx - ccx, room.L, cz - ccz, yaw, room.L, room)
            if self.fits(room, it): out.append(self.commit(room, it, 'стул с %s' % side))
        return out

    def on(self, room, oid, host, dx=0.0, dz=0.0, dyaw=0.0, top=None, **fields):
        if host is None: return None
        ox, oz = rot(host.yaw, dx, dz)
        y = host.L + (top if top is not None else host.top() - host.L)
        it = Item(oid, host.x + ox, y, host.z + oz, host.yaw + dyaw, room.L, room, fields)
        it.host = host
        return self.commit(room, it, 'на %s' % host.id)

    def kit(self, room, host):
        """Выученный набор хозяина: всё, что в коттедже стояло на нём / в нём, с теми же относительными смещениями."""
        if host is None: return []
        kit = learned().get('kits', {}).get(host.id)
        if not kit: return []
        out = []
        made = {}
        for rec in kit:
            dx, dz = rot(host.yaw, rec['rel'][0], rec['rel'][2])
            fields = dict(rec.get('fields', {}))
            if rec.get('carrierId'):
                cdx, cdz = rot(host.yaw, rec['carrierRel'][0], rec['carrierRel'][2])
                fields.update({'carrierId': rec['carrierId'], 'carrierNode': rec['carrierNode'],
                               'carrierPos': v3(host.x + cdx, host.L + rec['carrierRel'][1], host.z + cdz),
                               'localPos': v3(*rec['localPos']), 'localRotY': rec['localRotY']})
            it = Item(rec['id'], host.x + dx, host.L + rec['rel'][1], host.z + dz, host.yaw + rec['dyaw'], room.L, room, fields)
            it.host = host
            out.append(self.commit(room, it, 'набор %s' % host.id))
        return out

    def wall_item(self, room, oid, side=None, t=None, h=None, anchor=None, dt=0.0, near=None, radius=1.3):
        """Настенный: на стене side у координаты t (или над anchor со сдвигом dt, или рядом с near на любой стене),
        на высоте h (по умолчанию — выученная с коттеджа, иначе wallHeight дефа)."""
        geom = self.geoms[room.name]
        c = catalog()[oid]
        if h is None: h = learned().get('wall_h', {}).get(oid, c.get('wall_height') or 1.6)
        if anchor is not None and anchor.side:
            side = anchor.side
            ar = anchor.rect()
            t = ((ar[0] + ar[2]) / 2 if side in ('N', 'S') else (ar[1] + ar[3]) / 2) + dt
        sides = [side] if side else list(SIDES)
        w = c['w']
        ncx, ncz = near.center() if near is not None else (None, None)
        for s in sides:
            for (t0, t1) in geom.runs(s, low_ok=False):
                if t1 - t0 < w + 0.05: continue
                base = t
                if near is not None:
                    base = ncx if s in ('N', 'S') else ncz
                    if base < t0 - radius or base > t1 + radius: continue
                if base is None: base = (t0 + t1) / 2
                steps = (0.3, 0.6) if t is not None else (0.5, 1.0, 1.5, 2.0, 2.5)
                tries = [base] + [base + k * sgn for k in steps for sgn in (-1, 1)]
                for tt in tries:
                    tt = max(t0 + HALF + w / 2 + 0.02, min(t1 - HALF - w / 2 - 0.02, tt))
                    x, z, yaw = self.wall_root(geom, oid, s, tt, wall_mount=True)
                    it = Item(oid, x, room.L + h, z, yaw, room.L, room)
                    it.side, it.t = s, tt
                    if self._wall_conflict(room, it, s, near, radius, ncx, ncz): continue
                    return self.commit(room, it, 'стена %s h=%.2f' % (s, h))
        self.report.append('%-12s %-30s НЕ ВСТАЛ (настенный)' % (room.name, oid))
        return None

    def _wall_conflict(self, room, it, s, near, radius, ncx, ncz):
        rr = it.rect()
        for other in self.placed[room.name]:
            if other.mount == 'Wall' and other.side == s:
                orr = other.rect()
                lo1, hi1 = (orr[0], orr[2]) if s in ('N', 'S') else (orr[1], orr[3])
                lo2, hi2 = (rr[0], rr[2]) if s in ('N', 'S') else (rr[1], rr[3])
                vert = not (other.y + other.y0 + other.h < it.y + it.y0 or it.y + it.y0 + it.h < other.y + other.y0)
                if vert and not (hi1 < lo2 or hi2 < lo1): return True
            if other.mount == 'Floor' and not other.flat and other.top() > it.y + it.y0 + 0.25 and other.side == s:
                if overlaps(rr, other.rect()): return True
        if near is not None:
            icx, icz = it.center()
            if math.hypot(icx - ncx, icz - ncz) > radius: return True
        return False

    def by_door(self, room, oid, h=None):
        geom = self.geoms[room.name]
        for side in SIDES:
            for (dt, c) in geom.doors_on(side):
                for off in (0.75, -0.75):
                    for (t0, t1) in geom.runs(side, low_ok=False):
                        if t0 <= dt + off <= t1:
                            it = self.wall_item(room, oid, side=side, t=dt + off, h=h)
                            if it: return it
        return self.wall_item(room, oid, h=h)

    def under_window(self, room, oid):
        geom = self.geoms[room.name]
        for side in SIDES:
            for (wt, c) in geom.windows_on(side):
                x, z, yaw = self.wall_root(geom, oid, side, wt)
                it = Item(oid, x, room.L, z, yaw, room.L, room); it.side, it.t = side, wt
                if self.fits(room, it): return self.commit(room, it, 'под окном %s' % side)
        return None

    def at_windows(self, room, oid):
        geom = self.geoms[room.name]
        out = []
        for side in SIDES:
            for (wt, c) in geom.windows_on(side):
                x, z, yaw = self.wall_root(geom, oid, side, wt, gap=self.gap_for(oid))
                it = Item(oid, x, room.L, z, yaw, room.L, room); it.side, it.t = side, wt
                it.fields = {}
                out.append(self.commit(room, it, 'на окне %s' % side))
        return out

    def ceiling(self, room, oid):
        geom = self.geoms[room.name]
        cells = sorted(room.cells - room.holes)
        g = self.lv.grid
        groups = []
        if len(cells) <= 6:
            groups = [cells]
        else:
            u0, v0, u1, v1 = room.bbox_cells()
            mid = (u0 + u1) / 2 if (u1 - u0) >= (v1 - v0) else None
            if mid is not None: groups = [[c for c in cells if c[0] <= mid], [c for c in cells if c[0] > mid]]
            else:
                mv = (v0 + v1) / 2
                groups = [[c for c in cells if c[1] <= mv], [c for c in cells if c[1] > mv]]
        out = []
        for grp in groups:
            if not grp: continue
            x = sum(g.cx(c[0]) for c in grp) / len(grp); z = sum(g.cz(c[1]) for c in grp) / len(grp)
            it = Item(oid, x, room.L + 2.8, z, 90.0, room.L, room)
            out.append(self.commit(room, it, 'потолок'))
        return out

    # ─── комнаты
    def furnish(self):
        for r in self.h.rooms:
            fn = getattr(self, 'room_' + r.type, None)
            if fn: fn(r)
            self.room_common(r)
        self.rails_and_outdoors()
        return self.report

    def room_common(self, r):
        if r.type in ('attic',): return
        self.ceiling(r, 'lamp_ceiling_modern')
        if r.doors: self.by_door(r, 'wall_switch_toggle' if r.type == 'kitchen' else 'wall_switch')

    def room_living(self, r):
        rng = self.rng
        sofa = self.at_wall(r, 'sofa_corner_left', corner='any')
        if sofa is None: sofa = self.at_wall(r, 'sofa_modern')
        tv_stand = None
        if sofa and sofa.side:
            tv_stand = self.at_wall(r, 'home_tv_stand', sides=[OPP[sofa.side]], want_t=sofa.t)
        if tv_stand is None: tv_stand = self.at_wall(r, 'home_tv_stand')
        if tv_stand:
            self.wall_item(r, 'home_tv', anchor=tv_stand, h=1.33)
            self.kit(r, tv_stand)
        fire = self.at_wall(r, 'home_fireplace', sides=[s for s in SIDES if sofa is None or s != sofa.side])
        self.kit(r, fire)
        self.kit(r, sofa)
        side_t = self.beside(r, 'side_table', sofa, gap=0.15)
        self.kit(r, side_t)
        if sofa: self.front(r, 'home_rug_6', sofa, dist=0.2)
        shelving = self.at_wall(r, 'home_shelving', corner='any')
        self.kit(r, shelving)
        self.free(r, 'home_plant_8', at=(0.9, 0.1), yaw=180, jitter=0.2)
        self.free(r, 'cardboard_box', at=(0.15, 0.6), yaw=rng.uniform(0, 360), jitter=0.3)
        if r.doors:
            rack = self.at_wall(r, 'hallway_rack', want_t=None, corner='any', low_ok=False, allow_zone=False)
            self.wall_item(r, 'home_hall_mirror', h=0.1) if rack else None
        self.wall_item(r, 'home_painting_1')
        self.wall_item(r, 'wall_socket')
        self.at_windows(r, 'blind_venetian')
        self.under_window(r, 'home_radiator')
        self.wall_item(r, 'lamp_fairy_curtain')
        if r.stair:
            a, b, landing = r.stair
            self.stair_rail(r, a, b)
        self.at_wall(r, 'pipe_valve', corner='any')

    def stair_rail(self, r, a, b):
        g = self.lv.grid
        sr = learned().get('stair_rail')
        if not sr: return
        x = (g.cx(a[0]) + g.cx(b[0])) / 2; z = (g.cz(a[1]) + g.cz(b[1])) / 2
        yaw = 90.0 if b[0] > a[0] else 270.0 if b[0] < a[0] else 0.0 if b[1] > a[1] else 180.0
        dx, dz = rot(yaw, sr['rel'][0], sr['rel'][2])
        it = Item('stair_rail', x + dx, r.L + sr['rel'][1], z + dz, yaw + sr['dyaw'], r.L, r)
        it.flat_override = True
        self.placed[r.name].append(it); r.items.append(it)
        it.rec = self.lv.obj(it.id, it.x, it.y, it.z, it.yaw)
        self.report.append('%-12s %-30s перила лестницы' % (r.name, 'stair_rail'))

    def room_kitchen(self, r):
        cab = self.corner_module(r, 'home_sink_cabinet_corner')
        if cab:
            self.kit(r, cab)
            wall_cab = self.wall_item(r, 'home_wall_cabinet_corner_wide', side=cab.side, t=cab.t)
            if wall_cab:
                wall_cab.corner = cab.corner
                self.kit(r, wall_cab)
            fridge = self.beside(r, 'home_fridge', cab, gap=0.05)
            self.kit(r, fridge)
            stove = self.wing_end(r, 'home_stove', cab)
            self.kit(r, stove)
            if stove: self.wall_item(r, 'home_wall_clock_1', anchor=stove, h=2.14)
        else:
            sink_cab = self.at_wall(r, 'home_sink_cabinet', corner='any')
            self.kit(r, sink_cab)
            stove = self.beside(r, 'home_stove', sink_cab); self.kit(r, stove)
            fridge = self.beside(r, 'home_fridge', stove or sink_cab); self.kit(r, fridge)
        table = self.free(r, 'table_round', at=(0.5, 0.35), yaw=90)
        if table:
            self.around(r, 'home_kitchen_chair', table, n=3)
            rug = self.free(r, 'home_rug_1', at=(0.5, 0.35), yaw=90)
            self.kit(r, table)
        self.wall_item(r, 'shelf_plank')
        self.at_windows(r, 'blind_venetian')
        for k in range(self.rng.randint(1, 3)):
            self.free(r, 'cardboard_box', at=(0.85, 0.1), yaw=self.rng.uniform(0, 360), jitter=0.5)
        self.free(r, 'water_bottle', at=(0.1, 0.85), yaw=0, jitter=0.2)
        self.free(r, 'water_bottle', at=(0.12, 0.8), yaw=45, jitter=0.2)

    def room_bedroom(self, r):
        bed = self.at_wall(r, 'home_bed', corner='any', low_ok=False)
        self.kit(r, bed)
        bt = self.beside(r, 'home_bedside_table', bed, gap=0.08)
        self.kit(r, bt)
        if bt:
            self.wall_item(r, 'home_wall_sconce', anchor=bt)
            self.wall_item(r, 'wall_socket', anchor=bt, h=0.9)
        wardrobe = self.at_wall(r, 'home_wardrobe_room', corner='any', low_ok=False, avoid_doors=True)
        desk = self.at_wall(r, 'home_work_desk', low_ok=True, front=1.3)
        if desk:
            self.front(r, 'home_desk_chair', desk, dist=0.1)
            self.kit(r, desk)
        shelving = self.at_wall(r, 'home_shelving', corner='any') if len(r.cells) >= 6 else None
        self.kit(r, shelving)
        if bed: self.front(r, 'home_rug_6', bed, dist=0.1)
        self.wall_item(r, 'home_painting_2', anchor=bed)
        self.under_window(r, 'home_radiator')
        self.at_windows(r, 'curtain_drapes')
        st = self.free(r, 'side_table_round', at=(0.1, 0.9), yaw=180, jitter=0.2)
        self.kit(r, st)
        self.free(r, 'cardboard_box', at=(0.5, 0.5), yaw=self.rng.uniform(0, 360), jitter=0.4)

    def room_study(self, r):
        desk = self.at_wall(r, 'home_work_desk', low_ok=True, front=1.3)
        if desk:
            self.front(r, 'home_desk_chair', desk, dist=0.1)
            self.kit(r, desk)
        shelving = self.at_wall(r, 'home_shelving', corner='any')
        self.kit(r, shelving)
        self.at_wall(r, 'home_wardrobe_room', corner='any', low_ok=False)
        self.free(r, 'home_plant_8', at=(0.85, 0.85), yaw=0, jitter=0.2)
        self.free(r, 'home_rug_1', at=(0.5, 0.5), yaw=0)
        self.wall_item(r, 'home_painting_4')
        self.under_window(r, 'home_radiator')
        self.at_windows(r, 'curtain_drapes')

    def room_storage(self, r):
        shelving = self.at_wall(r, 'home_shelving', corner='any'); self.kit(r, shelving)
        for k in range(self.rng.randint(2, 4)):
            self.free(r, 'cardboard_box', at=(self.rng.uniform(0.2, 0.8), self.rng.uniform(0.2, 0.8)), yaw=self.rng.uniform(0, 360))
        self.free(r, 'bucket', at=(0.2, 0.2), yaw=0, jitter=0.2)
        self.at_windows(r, 'blind_venetian')

    def room_bathroom(self, r):
        bath = self.at_wall(r, 'home_bath', corner='any')
        self.kit(r, bath)
        toilet = self.at_wall(r, 'home_toilet', corner='any', sides=[s for s in SIDES if bath is None or s != bath.side], avoid_doors=True)
        self.kit(r, toilet)
        washer = self.beside(r, 'home_washer', toilet, gap=0.12) if toilet else None
        if washer is None: washer = self.at_wall(r, 'home_washer', corner='any')
        self.kit(r, washer)
        sink = self.at_wall(r, 'home_bathroom_sink', sides=[s for s in SIDES if (bath is None or s != bath.side)])
        if sink is None: sink = self.at_wall(r, 'home_bathroom_sink')
        self.kit(r, sink)
        if sink: self.wall_item(r, 'home_bathroom_mirror', anchor=sink, h=1.5)
        if washer: self.beside(r, 'home_laundry_basket', washer, gap=0.1)
        console = self.at_wall(r, 'bath_console', corner='any'); self.kit(r, console)
        if toilet: self.wall_item(r, 'bath_paper_holder', near=toilet)
        if bath: self.front(r, 'home_bath_rug_dogs', bath, dist=0.1)
        cab = self.wall_item(r, 'home_bathroom_cabinet'); self.kit(r, cab)
        self.wall_item(r, 'bath_shelf')
        self.wall_item(r, 'home_towel_rail')
        hooks = self.wall_item(r, 'bath_hook')
        if hooks: self.kit(r, hooks)
        self.free(r, 'bath_bucket', at=(0.15, 0.15), yaw=self.rng.uniform(0, 360), jitter=0.2)

    def room_hall(self, r):
        self.free(r, 'cardboard_box', at=(0.2, 0.3), yaw=self.rng.uniform(0, 360), jitter=0.3)
        self.wall_item(r, 'lamp_wall_garland')
        self.at_windows(r, 'blind_venetian')
        self.under_window(r, 'home_radiator')
        self.wall_item(r, 'home_painting_1')

    def room_void(self, r): pass

    def rails_and_outdoors(self):
        """Перила вдоль дырок (проём над гостиной) и балкона, столбы и фонари крыльца, мебель крыльца и балкона."""
        g = self.lv.grid
        rail_len = 1.5
        for r in self.h.rooms:
            for c in r.holes:
                if r.stair and c in r.stair[:2]: pass
                for side in SIDES:
                    dx, dz = SIDE_DIR[side]
                    n = (c[0] + dx, c[1] + dz)
                    if n in r.holes or n not in r.cells: continue
                    if r.stair and n in r.stair[:2] and c in r.stair[:2]: continue
                    self._rail_run(r, c, side, n, rail_len)
        porch = getattr(self.h, 'porch_cells', None)
        plan = self.h.plan
        if porch:
            pr = plan['porch']
            side = pr['side']
            cells = porch
            # столбы по наружным углам крыльца, фонари под балконом, лавка и урна
            xs = [g.cx(c[0]) for c in cells]; zs = [g.cz(c[1]) for c in cells]
            x0, x1, z0, z1 = min(xs) - CS / 2, max(xs) + CS / 2, min(zs) - CS / 2, max(zs) + CS / 2
            outer = {'W': x0, 'E': x1, 'S': z0, 'N': z1}[side]
            if side in ('W', 'E'):
                ox = outer + (0.3 if side == 'W' else -0.3)
                for zz in (z0 + 0.35, z1 - 0.35): self.lv.obj('column_post', ox, 0.0, zz, 0.0)
                for zz in (z0 + 0.9, z1 - 0.9): self.lv.obj('lamp_pendant_lantern', outer + (0.7 if side == 'W' else -0.7), 2.8, zz, 285.0)
                inner_x = (x1 if side == 'W' else x0)
                bx = inner_x + (-0.75 if side == 'W' else 0.75)
                self.lv.obj('bench_modern_3', bx, 0.0, z0 + 1.9, 90.0 if side == 'W' else 270.0)
                self.lv.obj('trash_bin_modern_2', bx, 0.0, z0 + 0.45, 90.0)
            else:
                oz = outer + (0.3 if side == 'S' else -0.3)
                for xx in (x0 + 0.35, x1 - 0.35): self.lv.obj('column_post', xx, 0.0, oz, 0.0)
                for xx in (x0 + 0.9, x1 - 0.9): self.lv.obj('lamp_pendant_lantern', xx, 2.8, outer + (0.7 if side == 'S' else -0.7), 285.0)
                inner_z = (z1 if side == 'S' else z0)
                bz = inner_z + (-0.75 if side == 'S' else 0.75)
                self.lv.obj('bench_modern_3', x0 + 1.9, 0.0, bz, 0.0 if side == 'S' else 180.0)
                self.lv.obj('trash_bin_modern_2', x0 + 0.45, 0.0, bz, 0.0)
            if plan.get('balcony', True) and len(plan['floors']) > 1:
                L = LVL_H
                for c in cells:
                    for s in SIDES:
                        dx, dz = SIDE_DIR[s]
                        n = (c[0] + dx, c[1] + dz)
                        if n in cells: continue
                        if s == OPP[side]: continue   # сторона у дома
                        self._rail_cell_edge(c, s, L, rail_len)
                cx = sum(xs) / len(xs); cz = sum(zs) / len(zs)
                rc = self.lv.obj('rocking_chair', cx + (0.3 if side == 'W' else -0.3), L, z1 - 1.3, 60.0)
                st = self.lv.obj('side_table_round', cx + 0.55, L, z1 - 2.4, 60.0)
                host = Item('side_table_round', st['pos']['x'], L, st['pos']['z'], 60.0, L)
                for rec in learned().get('kits', {}).get('side_table_round', []):
                    dx, dz = rot(60.0, rec['rel'][0], rec['rel'][2])
                    self.lv.obj(rec['id'], host.x + dx, L + rec['rel'][1], host.z + dz, 60.0 + rec['dyaw'], **rec.get('fields', {}))
                for k in range(2):
                    self.lv.obj('cardboard_box', cx + self.rng.uniform(-0.3, 0.6), L, z0 + 0.9 + k * 0.6, self.rng.uniform(0, 45))

    def _rail_run(self, r, hole, side, walk, rail_len):
        g = self.lv.grid
        x, z = g.cx(walk[0]), g.cz(walk[1])
        if side == 'N': zz = z - CS / 2 + 0.15; pts = [(x - 0.75, zz), (x + 0.75, zz)]; yaw = 0.0
        elif side == 'S': zz = z + CS / 2 - 0.15; pts = [(x - 0.75, zz), (x + 0.75, zz)]; yaw = 0.0
        elif side == 'E': xx = x - CS / 2 + 0.15; pts = [(xx, z - 0.75), (xx, z + 0.75)]; yaw = 90.0
        else: xx = x + CS / 2 - 0.15; pts = [(xx, z - 0.75), (xx, z + 0.75)]; yaw = 90.0
        for (px, pz) in pts:
            self.lv.obj('edge_rail', px, r.L, pz, yaw)
        self.report.append('%-12s %-30s перила у проёма %s' % (r.name, 'edge_rail', side))

    def _rail_cell_edge(self, c, side, L, rail_len):
        g = self.lv.grid
        x, z = g.cx(c[0]), g.cz(c[1])
        if side == 'N': zz = z + CS / 2 - 0.15; pts = [(x - 0.75, zz), (x + 0.75, zz)]; yaw = 0.0
        elif side == 'S': zz = z - CS / 2 + 0.15; pts = [(x - 0.75, zz), (x + 0.75, zz)]; yaw = 0.0
        elif side == 'E': xx = x + CS / 2 - 0.15; pts = [(xx, z - 0.75), (xx, z + 0.75)]; yaw = 90.0
        else: xx = x - CS / 2 + 0.15; pts = [(xx, z - 0.75), (xx, z + 0.75)]; yaw = 90.0
        for (px, pz) in pts: self.lv.obj('edge_rail', px, L, pz, yaw)


# ───────────────────────────── разбор уровня: комнаты и паспорт ─────────────────────────────

ROOM_SIGNS = [('bathroom', {'home_bath', 'home_toilet', 'home_bathroom_sink', 'home_washer'}),
              ('kitchen', {'home_stove', 'home_fridge', 'home_sink_cabinet_corner', 'home_sink_cabinet'}),
              ('bedroom', {'home_bed'}),
              ('living', {'sofa_corner_left', 'sofa_modern', 'home_fireplace', 'home_tv_stand'}),
              ('study', {'home_work_desk', 'home_desk'}),
              ('hall', {'hallway_rack', 'home_hall_mirror', 'edge_rail'})]
SKIP_PREFIX = ('veg_', 'env_', 'tree', 'grass')


class Parsed:
    """Дом из файла уровня: клетки с плитами, стены/проёмы по рёбрам, комнаты заливкой, объекты по комнатам."""
    def __init__(self, d):
        self.d = d
        self.grid = Grid(d)
        self.levels = {}
        self.slabs = collections.defaultdict(set)     # L -> cells
        self.walls = collections.defaultdict(set)     # L -> edges
        self.doors = collections.defaultdict(dict)    # L -> edge -> rec
        self.windows = collections.defaultdict(dict)
        for f in d['floors']:
            L = round(f['pos']['y'] + 0.1, 1)
            if f['scale']['x'] > 2.9 and f['scale']['z'] > 2.9:
                self.slabs[L].add(self.grid.cell_of(f['pos']['x'], f['pos']['z']))
            else:
                self.slabs[L].add(self.grid.cell_of(f['pos']['x'], f['pos']['z']))
        for w in d['walls']:
            L = round(w['pos']['y'] - 1.496, 1)
            self.walls[L].add(self.edge_of(w['pos']['x'], w['pos']['z'], w['spansX']))
        for o in d['doors']:
            L = round(o['pos']['y'], 1); self.doors[L][self.edge_of(o['pos']['x'], o['pos']['z'], o['spansX'])] = o
        for o in d['windows']:
            L = round(o['pos']['y'], 1); self.windows[L][self.edge_of(o['pos']['x'], o['pos']['z'], o['spansX'])] = o
        self.stairs = [(round(s['pos']['y'], 1), s) for s in d['stairs']]
        self.rooms = []
        self.find_rooms()

    def edge_of(self, x, z, spans_x):
        g = self.grid
        if spans_x:
            i = int(round((x - g.ox) / CS)); j = int(math.floor((z - g.oz) / CS))
            return ('x', i, j)
        i = int(math.floor((x - g.ox) / CS)); j = int(round((z - g.oz) / CS))
        return ('z', i, j)

    def barrier(self, L, e):
        return e in self.walls[L] or e in self.doors[L] or e in self.windows[L]

    def house_cells(self):
        """Клетки под домом: те, что на любом уровне внутри стен (есть стена на каком-то ребре рядом)."""
        out = set()
        for L in list(self.walls) + list(self.doors) + list(self.windows):
            for e in list(self.walls.get(L, ())) + list(self.doors.get(L, {})) + list(self.windows.get(L, {})):
                for c in Edge.cells(e): out.add(c)
        if out:
            i0, i1 = min(c[0] for c in out), max(c[0] for c in out); j0, j1 = min(c[1] for c in out), max(c[1] for c in out)
            for L, cells in self.slabs.items():
                for c in cells:
                    if i0 <= c[0] <= i1 and j0 <= c[1] <= j1: out.add(c)
        return out

    def find_rooms(self):
        hc = self.house_cells()
        for L in sorted(set(self.slabs) | set(self.walls)):
            if L < -0.5: continue
            cells = set(c for c in self.slabs[L] if c in hc) | set(c for c in hc if self.has_wall_around(L, c))
            seen = set()
            for c in sorted(cells):
                if c in seen: continue
                comp, stack, leak = set(), [c], False
                while stack:
                    cur = stack.pop()
                    if cur in comp: continue
                    comp.add(cur)
                    for side in SIDES:
                        e = Edge.of_side(cur, side)
                        n = (cur[0] + SIDE_DIR[side][0], cur[1] + SIDE_DIR[side][1])
                        if self.barrier(L, e): continue
                        if n not in cells: leak = True; continue
                        stack.append(n)
                seen |= comp
                if leak and not all(x in self.slabs[L] for x in comp): continue
                self.rooms.append({'L': L, 'cells': comp, 'open': leak, 'objects': []})
        objs = [o for o in self.d['objects'] if not o['id'].startswith(SKIP_PREFIX)]
        for o in objs:
            L = floor_of(o['pos']['y']) * LVL_H
            c = self.grid.cell_of(o['pos']['x'], o['pos']['z'])
            for r in self.rooms:
                if abs(r['L'] - L) < 0.1 and c in r['cells']:
                    r['objects'].append(o); break
        for r in self.rooms:
            ids = set(o['id'] for o in r['objects'])
            r['type'] = 'empty'
            for t, signs in ROOM_SIGNS:
                if ids & signs: r['type'] = t; break
            if r['type'] == 'empty' and len(r['cells']) >= 6 and r['L'] >= 5.5: r['type'] = 'attic'
            if r['open'] and r['type'] in ('empty', 'hall'): r['type'] = 'porch' if r['L'] < 0.5 else 'balcony'

    def has_wall_around(self, L, c):
        return any(Edge.of_side(c, s) in self.walls[L] or Edge.of_side(c, s) in self.doors[L] or Edge.of_side(c, s) in self.windows[L] for s in SIDES)

    def passport(self):
        lines = []
        g = self.grid
        for r in sorted(self.rooms, key=lambda r: (r['L'], min(r['cells']))):
            cells = sorted(r['cells'])
            us = [c[0] for c in cells]; vs = [c[1] for c in cells]
            lines.append('этаж %d (y=%g): %-9s %2d кл. x %g..%g z %g..%g%s' % (r['L'] / LVL_H, r['L'], r['type'], len(cells),
                         g.cx(min(us)) - 1.5, g.cx(max(us)) + 1.5, g.cz(min(vs)) - 1.5, g.cz(max(vs)) + 1.5, ' (открыта наружу)' if r['open'] else ''))
            cnt = collections.Counter(o['id'] for o in r['objects'])
            lines.append('      ' + ', '.join('%s×%d' % (k, v) if v > 1 else k for k, v in sorted(cnt.items())))
        return '\n'.join(lines)


# ───────────────────────────── обучение на коттедже ─────────────────────────────

def learn(name=TEMPLATE_LEVEL):
    d = load_level(name)
    cat = catalog()
    p = Parsed(d)
    objs = [o for o in d['objects'] if not o['id'].startswith(SKIP_PREFIX)]
    house = p.house_cells()
    inside = [o for o in objs if p.grid.cell_of(o['pos']['x'], o['pos']['z']) in house or o['id'] in ('edge_rail', 'rocking_chair', 'side_table_round', 'column_post', 'lamp_pendant_lantern', 'bench_modern_3', 'trash_bin_modern_2')]
    wall_h, gap, look, keep = {}, {}, {}, set()
    for o in inside:
        c = cat.get(o['id'])
        if not c: continue
        L = floor_of(o['pos']['y']) * LVL_H
        if c['mount'] == 'Wall': wall_h.setdefault(o['id'], round(o['pos']['y'] - L, 2))
        if o.get('keepPlinth'): keep.add(o['id'])
        lk = {k: o[k] for k in ('pcSet', 'pcr', 'pcg', 'pcb', 'scSet', 'scr', 'scg', 'scb', 'palette', 'pattern', 'partCol', 'powerOn', 'switchOn') if k in o}
        if lk.get('pcSet') or lk.get('scSet') or lk.get('palette', -1) >= 0 or lk.get('partCol') or lk.get('pattern'):
            look.setdefault(o['id'], lk)
    # зазоры напольных до стены
    for o in inside:
        c = cat.get(o['id'])
        if not c or c['mount'] != 'Floor' or c['w'] is None or o.get('carrierId'): continue
        rot_ = o['rotY'] % 360
        if min(abs(rot_ - a) for a in (0, 90, 180, 270, 360)) > 1: continue
        L = floor_of(o['pos']['y']) * LVL_H
        bx, bz = math.sin(math.radians(rot_)), math.cos(math.radians(rot_))
        dd = c['d']; back = c['cz'] + dd / 2
        wx, wz = o['pos']['x'] + bx * back, o['pos']['z'] + bz * back
        best = None
        for e in list(p.walls[L]) + list(p.doors[L]) + list(p.windows[L]):
            x, z, sx = Edge.world(p.grid, e)
            if abs(bx) > 0.5 and sx: continue
            if abs(bz) > 0.5 and not sx: continue
            if abs(bx) > 0.5:
                if abs(z - o['pos']['z']) > 1.6: continue
                s = 1 if bx > 0 else -1; gp = ((x - HALF * s) - wx) * s
            else:
                if abs(x - o['pos']['x']) > 1.6: continue
                s = 1 if bz > 0 else -1; gp = ((z - HALF * s) - wz) * s
            if -0.5 < gp < 0.4 and (best is None or abs(gp) < abs(best)): best = gp
        if best is not None and o['id'] not in gap:
            gap[o['id']] = round(max(0.0, best), 3) if abs(best - SEAT_GAP) > 0.03 else SEAT_GAP
    # наборы: всё, что лежит в следе хозяина выше его пола и ниже верха+0,8, или привязано цепочкой carrierId
    hosts = [o for o in inside if cat.get(o['id'], {}).get('mount') in ('Floor', 'Wall') and (cat[o['id']]['h'] or 0) > 0.3 and not o.get('carrierId')]
    kits = {}
    taken = set()
    by_key = {id(o): o for o in objs}
    for host in sorted(hosts, key=lambda o: (cat[o['id']]['w'] * cat[o['id']]['d'])):
        hid = host['id']
        if hid in kits or hid in ('edge_rail', 'stair_rail', 'column_post', 'home_radiator', 'curtain_drapes', 'blind_venetian', 'hallway_rack'): continue
        hc = cat[hid]
        hyaw = host['rotY']
        hi = Item(hid, host['pos']['x'], host['pos']['y'], host['pos']['z'], hyaw, host['pos']['y'])
        rct = hi.rect()
        members = []
        for o in objs:
            if o is host or id(o) in taken: continue
            oc = cat.get(o['id'])
            if not oc or oc['mount'] in ('Floor', 'Ceiling') and not o.get('carrierId'): continue
            if oc['mount'] == 'Wall' and hc['mount'] != 'Wall' and not o.get('carrierId'): continue
            x, z, y = o['pos']['x'], o['pos']['z'], o['pos']['y']
            if floor_of(y) != floor_of(host['pos']['y']): continue
            in_rect = rct[0] - 0.05 <= x <= rct[2] + 0.05 and rct[1] - 0.05 <= z <= rct[3] + 0.05
            above = host['pos']['y'] + min(0.3, (hc['h'] or 0.3) * 0.5) <= y <= hi.top() + 0.9
            if (in_rect and above) or o.get('carrierId') == hid and abs(y - host['pos']['y']) < 3:
                members.append(o)
        if not members: continue
        chain = True
        while chain:
            chain = False
            for o in objs:
                if id(o) in taken or o in members or o is host: continue
                if o.get('carrierId') and any(m['id'] == o['carrierId'] and abs(m['pos']['x'] - o['carrierPos']['x']) < 0.05 and abs(m['pos']['z'] - o['carrierPos']['z']) < 0.05 for m in members):
                    members.append(o); chain = True
        members.sort(key=lambda o: objs.index(o))
        recs = []
        for m in members:
            taken.add(id(m))
            rel = rot(-hyaw, m['pos']['x'] - host['pos']['x'], m['pos']['z'] - host['pos']['z'])
            rec = {'id': m['id'], 'rel': [round(rel[0], 4), round(m['pos']['y'] - host['pos']['y'], 4), round(rel[1], 4)], 'dyaw': round((m['rotY'] - hyaw) % 360, 2)}
            fields = {k: m[k] for k in ('items', 'count', 'liquidKind', 'liquidL', 'cook', 'pattern', 'palette', 'pcSet', 'pcr', 'pcg', 'pcb', 'fireLit', 'wax', 'cellCharge', 'expiry', 'open', 'switchOn', 'powerOn') if k in m}
            rec['fields'] = fields
            if m.get('carrierId'):
                crel = rot(-hyaw, m['carrierPos']['x'] - host['pos']['x'], m['carrierPos']['z'] - host['pos']['z'])
                rec.update({'carrierId': m['carrierId'], 'carrierNode': m['carrierNode'], 'carrierRel': [round(crel[0], 4), round(m['carrierPos']['y'] - host['pos']['y'], 4), round(crel[1], 4)],
                            'localPos': [m['localPos']['x'], m['localPos']['y'], m['localPos']['z']], 'localRotY': m['localRotY']})
            recs.append(rec)
        kits[hid] = recs
    stair_rail = None
    for o in inside:
        if o['id'] == 'stair_rail' and p.stairs:
            L, s = p.stairs[0]
            rel = rot(-s['rotY'], o['pos']['x'] - s['pos']['x'], o['pos']['z'] - s['pos']['z'])
            stair_rail = {'rel': [round(rel[0], 3), round(o['pos']['y'] - s['pos']['y'], 3), round(rel[1], 3)], 'dyaw': round((o['rotY'] - s['rotY']) % 360, 1)}
    out = {'source': name, 'wall_h': wall_h, 'gap': gap, 'look': look, 'keep_plinth': sorted(keep), 'kits': kits, 'stair_rail': stair_rail}
    (HERE / 'learned.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    global _learned
    _learned = out
    print('выучено: настенных высот %d, зазоров %d, расцветок %d, наборов %d (%d предметов), keepPlinth %d' % (
        len(wall_h), len(gap), len(look), len(kits), sum(len(v) for v in kits.values()), len(keep)))
    for k, v in kits.items(): print('   набор %-30s %s' % (k, ', '.join(r['id'] for r in v)))
    return out


# ───────────────────────────── проверка ─────────────────────────────

def check(name, verbose=True):
    d = name if isinstance(name, dict) else load_level(name)
    cat = catalog()
    p = Parsed(d)
    bad, info = [], []
    # 1. стены на рёбрах, без дублей, проём не рядом со стеной на том же ребре
    seen = set()
    for w in d['walls']:
        x, z, sx = w['pos']['x'], w['pos']['z'], w['spansX']
        onx = abs(((x - p.grid.ox) / CS) - round((x - p.grid.ox) / CS)) < 1e-3
        onz = abs(((z - p.grid.oz) / CS) - round((z - p.grid.oz) / CS)) < 1e-3
        halfx = abs(((x - p.grid.ox) / CS) % 1 - 0.5) < 1e-3; halfz = abs(((z - p.grid.oz) / CS) % 1 - 0.5) < 1e-3
        if sx and not (onx and halfz): bad.append('стена не на ребре: %.2f,%.2f spansX' % (x, z))
        if not sx and not (halfx and onz): bad.append('стена не на ребре: %.2f,%.2f spansZ' % (x, z))
        key = (round(x, 2), round(z, 2), round(w['pos']['y'], 1))
        if key in seen: bad.append('двойная стена %s' % (key,))
        seen.add(key)
        if abs(w['scale']['y'] - 3.012) > 0.01 and abs(w['scale']['y'] - 3.008) > 0.01: bad.append('высота стены %s' % w['scale']['y'])
    for L in p.doors:
        for e in p.doors[L]:
            if e in p.walls[L]: bad.append('дверь и стена на одном ребре %s L=%s' % (e, L))
    for L in p.windows:
        for e in p.windows[L]:
            if e in p.walls[L]: bad.append('окно и стена на одном ребре %s L=%s' % (e, L))
            cb, ca = Edge.cells(e)
            hc = p.house_cells()
            if (cb in p.slabs[L]) and (ca in p.slabs[L]) and p.has_wall_around(L, cb) and p.has_wall_around(L, ca):
                pass
    # 2. комнаты закрыты (кроме чердака/крыльца), типы и обязательная обстановка
    need = {'bedroom': ['home_bed'], 'kitchen': ['home_stove', 'home_fridge'], 'bathroom': ['home_toilet'], 'living': ['sofa_corner_left|sofa_modern']}
    for r in p.rooms:
        ids = collections.Counter(o['id'] for o in r['objects'])
        if r['open'] and r['type'] not in ('attic', 'empty'): bad.append('комната %s на y=%g не закрыта стенами' % (r['type'], r['L']))
        for req in need.get(r['type'], []):
            if not any(ids.get(x) for x in req.split('|')): bad.append('в %s (y=%g) нет %s' % (r['type'], r['L'], req))
        if r['type'] in ('bedroom', 'kitchen', 'living', 'bathroom', 'study') and not ids.get('lamp_ceiling_modern'): bad.append('в %s (y=%g) нет лампы' % (r['type'], r['L']))
    # 3. мебель: внутри дома, без пересечений напольных, настенные у стены, поверхностные на хозяине
    floor_items = []
    hc = p.house_cells()
    hosts_near = []
    for h in d['objects']:
        hcat = cat.get(h['id'])
        if not hcat or hcat['mount'] not in ('Floor', 'Wall') or (hcat['h'] or 0) < 0.3 or hcat['w'] is None: continue
        if p.grid.cell_of(h['pos']['x'], h['pos']['z']) not in hc: continue
        hosts_near.append(Item(h['id'], h['pos']['x'], h['pos']['y'], h['pos']['z'], h['rotY'], 0))
    for o in d['objects']:
        c = cat.get(o['id'])
        if not c or o['id'].startswith(SKIP_PREFIX) or c['w'] is None: continue
        cell = p.grid.cell_of(o['pos']['x'], o['pos']['z'])
        if cell not in hc: continue
        L = floor_of(o['pos']['y']) * LVL_H
        in_room = any(abs(r['L'] - L) < 0.1 and cell in r['cells'] and not r['open'] for r in p.rooms)
        if not in_room: continue
        it = Item(o['id'], o['pos']['x'], o['pos']['y'], o['pos']['z'], o['rotY'], L)
        if c['mount'] == 'Floor' and not it.flat and not o.get('carrierId') and o['id'] not in ('stair_rail', 'edge_rail'):
            floor_items.append((it, o))
        if c['mount'] == 'Wall' and not c.get('snap_to') and not c.get('host_only'):
            near = False
            bdx, bdz = rot(it.yaw, 0.0, it.cz + it.d / 2)
            bx, bz = it.x + bdx, it.z + bdz
            for e in list(p.walls[L]) + list(p.doors[L]) + list(p.windows[L]):
                x, z, sx = Edge.world(p.grid, e)
                if sx and abs(z - bz) < 0.3 and abs(x - bx) < 1.6: near = True
                if not sx and abs(x - bx) < 0.3 and abs(z - bz) < 1.6: near = True
            if not near: bad.append('настенный %s (%.1f,%.1f,%.1f) не у стены' % (o['id'], o['pos']['x'], o['pos']['y'], o['pos']['z']))
        if c['mount'] == 'Surface' and not o.get('carrierId'):
            if o['pos']['y'] - L < 0.2: continue
            held = False
            for hi in hosts_near:
                if abs(hi.x - o['pos']['x']) > 3 or abs(hi.z - o['pos']['z']) > 3: continue
                rct = hi.rect()
                lo = hi.y + 0.1 if hi.mount == 'Floor' else hi.y - 0.1
                if rct[0] - 0.1 <= o['pos']['x'] <= rct[2] + 0.1 and rct[1] - 0.1 <= o['pos']['z'] <= rct[3] + 0.1 and lo <= o['pos']['y'] <= hi.top() + 0.9: held = True; break
            if not held: bad.append('поверхностный %s (%.1f,%.1f,%.1f) без опоры' % (o['id'], o['pos']['x'], o['pos']['y'], o['pos']['z']))
    for i in range(len(floor_items)):
        a, oa = floor_items[i]
        ra = a.rect()
        # сквозь стену
        for e in p.walls[a.L]:
            x, z, sx = Edge.world(p.grid, e)
            if sx and ra[1] < z - 0.11 and ra[3] > z + 0.11 and ra[0] < x + CS / 2 - 0.02 and ra[2] > x - CS / 2 + 0.02:
                bad.append('%s (%.1f,%.1f) сквозь стену %s' % (a.id, a.x, a.z, e))
            if not sx and ra[0] < x - 0.11 and ra[2] > x + 0.11 and ra[1] < z + CS / 2 - 0.02 and ra[3] > z - CS / 2 + 0.02:
                bad.append('%s (%.1f,%.1f) сквозь стену %s' % (a.id, a.x, a.z, e))
        for j in range(i + 1, len(floor_items)):
            b, ob = floor_items[j]
            if abs(a.L - b.L) > 0.1: continue
            if a.id == 'sofa_corner_left' or b.id == 'sofa_corner_left': continue
            seat_table = (any(k in a.id for k in SEAT_IDS) and any(k in b.id for k in TABLE_IDS)) or (any(k in b.id for k in SEAT_IDS) and any(k in a.id for k in TABLE_IDS))
            if seat_table: continue
            if overlaps(ra, b.rect(), -0.1) and obb_overlap(a, b, tol=0.1):
                bad.append('пересечение %s (%.1f,%.1f) и %s (%.1f,%.1f)' % (a.id, a.x, a.z, b.id, b.x, b.z))
    # 4. лестницы: дырка в перекрытии над обеими клетками
    for (L, s) in p.stairs:
        g = p.grid
        yaw = s['rotY'] % 360
        dx, dz = (1, 0) if abs(yaw - 90) < 1 else (-1, 0) if abs(yaw - 270) < 1 else (0, 1) if yaw < 1 or yaw > 359 else (0, -1)
        x, z = s['pos']['x'], s['pos']['z']
        a = g.cell_of(x - dx * CS / 2, z - dz * CS / 2); b = g.cell_of(x + dx * CS / 2, z + dz * CS / 2)
        up = L + LVL_H
        for c in (a, b):
            if c in p.slabs.get(up, set()): bad.append('над лестницей нет дырки: клетка %s на y=%g' % (c, up))
    # 5. все комнаты достижимы от входа (двери/лестницы)
    info.append('комнат: %d' % len(p.rooms))
    report = '\n'.join(info + bad)
    verdict = 'HOUSE ok' if not bad else 'HOUSE FAIL (%d)' % len(bad)
    if verbose:
        print(p.passport())
        print(report)
        print(verdict, '|', counts(d))
    return not bad, bad


# ───────────────────────────── случайный план коттеджа ─────────────────────────────

def random_plan(seed=1, nx=4, nz=5, floors=2, porch='W', void=True):
    rng = random.Random(seed)
    nx = nx or rng.choice([4, 4, 5]); nz = nz or rng.choice([4, 5, 5, 6])
    k = min(3, nz - 2)                       # глубина кухни по v
    entry_v = nz // 2
    plan = {'seed': seed, 'nx': nx, 'nz': nz, 'i0': 49, 'j0': 48, 'floors': [], 'roof': {'style': 0}}
    band = 2
    rest = list(range(band, nx))
    g0 = {'rooms': [
        {'name': 'гостиная', 'type': 'living', 'cells': [[u, v] for u in range(band) for v in range(nz)]},
        {'name': 'кухня', 'type': 'kitchen', 'cells': [[u, v] for u in rest for v in range(k)]},
        {'name': 'кабинет', 'type': rng.choice(['bedroom', 'study']), 'cells': [[u, v] for u in rest for v in range(k, nz)]}],
        'doors': [{'a': [band - 1, k - 1], 'b': [band, k - 1], 'style': DOOR_WOOD, 'open': True},
                  {'a': [band - 1, k], 'b': [band, k], 'style': DOOR_WOOD, 'open': rng.random() < 0.5}],
        'ext_doors': [{'cell': [0, entry_v], 'side': 'W', 'style': DOOR_STEEL, 'open': False, 'entrance': True, 'key': '100'}],
        'stair': {'cells': [[0, nz - 1], [1, nz - 1]], 'landing': True},
        'windows': []}
    win = g0['windows']; ext_doors = g0['ext_doors']
    def add_win(cell, side, p=0.6):
        if any(w['cell'] == list(cell) and w['side'] == side for w in win): return
        if any(dd['cell'] == list(cell) and dd['side'] == side for dd in ext_doors): return
        if rng.random() < p: win.append({'cell': list(cell), 'side': side, 'style': rng.choice([WIN_WHITE, WIN_WHITE, WIN_PVC]), 'offset': rng.choice([0.0, 0.48, -0.48])})
    add_win([0, 0], 'S', 0.9); add_win([nx - 1, 0], 'S', 0.9)
    for u in range(band, nx): add_win([u, nz - 1], 'N', 0.5)
    add_win([band, nz - 1], 'N', 1.0)
    for v in range(nz): add_win([nx - 1, v], 'E', 0.35)
    for v in range(nz):
        if v != entry_v and v != nz - 1: add_win([0, v], 'W', 0.3)
    plan['floors'].append(g0)
    if floors > 1:
        hall_cells = [[u, v] for u in range(band) for v in range(2, nz)]
        holes = [[0, nz - 1], [1, nz - 1]] + ([[0, nz - 2]] if void and nz >= 5 else [])
        g1 = {'rooms': [
            {'name': 'ванная', 'type': 'bathroom', 'cells': [[u, v] for u in range(band) for v in range(2)]},
            {'name': 'холл', 'type': 'hall', 'cells': hall_cells, 'holes': holes},
            {'name': 'комната', 'type': rng.choice(['study', 'storage', 'bedroom']), 'cells': [[u, v] for u in rest for v in range(k)]},
            {'name': 'спальня', 'type': 'bedroom', 'cells': [[u, v] for u in rest for v in range(k, nz)]}],
            'doors': [{'a': [0, 1], 'b': [0, 2], 'style': DOOR_WOOD, 'open': rng.random() < 0.7},
                      {'a': [band - 1, k - 1], 'b': [band, k - 1], 'style': DOOR_WOOD, 'open': rng.random() < 0.5},
                      {'a': [band - 1, k], 'b': [band, k], 'style': DOOR_WOOD, 'open': True}],
            'ext_doors': [{'cell': [0, entry_v], 'side': 'W', 'style': DOOR_GLASS, 'open': True}],
            'walls': [{'a': [1, nz - 1], 'b': [2, nz - 1]}],
            'windows': []}
        win = g1['windows']; ext_doors = g1['ext_doors']
        add_win([1, 0], 'S', 0.4)
        for u in range(band, nx): add_win([u, 0], 'S', 0.5); add_win([u, nz - 1], 'N', 0.6)
        add_win([band, nz - 1], 'N', 1.0)
        for v in range(nz): add_win([nx - 1, v], 'E', 0.4)
        add_win([0, 2], 'W', 0.5); add_win([0, nz - 1], 'N', 0.5)
        plan['floors'].append(g1)
    plan['porch'] = {'side': 'W', 'cells': [[-1, v] for v in range(max(0, entry_v - 1), min(nz, entry_v + 2))]}
    plan['balcony'] = floors > 1
    if porch != 'W': plan = transform_plan(plan, porch)
    return plan


def transform_plan(plan, porch):
    """Повернуть план так, чтобы крыльцо смотрело на сторону porch (из W)."""
    nx, nz = plan['nx'], plan['nz']
    if porch == 'E':
        f = lambda u, v: [nx - 1 - u, v]; fs = {'W': 'E', 'E': 'W', 'N': 'N', 'S': 'S'}; nnx, nnz = nx, nz
    elif porch == 'S':
        f = lambda u, v: [v, u]; fs = {'W': 'S', 'E': 'N', 'N': 'E', 'S': 'W'}; nnx, nnz = nz, nx
    elif porch == 'N':
        f = lambda u, v: [v, nx - 1 - u]; fs = {'W': 'N', 'E': 'S', 'N': 'E', 'S': 'W'}; nnx, nnz = nz, nx
    else:
        return plan
    out = copy.deepcopy(plan); out['nx'], out['nz'] = nnx, nnz
    for fl in out['floors']:
        for r in fl['rooms']:
            r['cells'] = [f(u, v) for u, v in r['cells']]
            if 'holes' in r: r['holes'] = [f(u, v) for u, v in r['holes']]
        for dd in fl.get('doors', []): dd['a'], dd['b'] = f(*dd['a']), f(*dd['b'])
        for dd in fl.get('walls', []): dd['a'], dd['b'] = f(*dd['a']), f(*dd['b'])
        for dd in fl.get('ext_doors', []): dd['cell'] = f(*dd['cell']); dd['side'] = fs[dd['side']]
        for wd in fl.get('windows', []): wd['cell'] = f(*wd['cell']); wd['side'] = fs[wd['side']]
        if fl.get('stair'): fl['stair']['cells'] = [f(u, v) for u, v in fl['stair']['cells']]
        for a, b in fl.get('open', []): pass
    out['porch']['cells'] = [f(u, v) for u, v in out['porch']['cells']]; out['porch']['side'] = fs[out['porch']['side']]
    return out


def copy_objects(h, source):
    """Обстановка 1:1 из уровня-источника: всё внутри коробки дома, на крыльце и балконе, кроме растительности,
    стихий и предметов на земле снаружи; маркер спавна — оригинальный."""
    src = load_level(source)
    g = h.level.grid
    cells = set()
    for r in h.rooms: cells |= r.cells
    cells |= set(getattr(h, 'porch_cells', []))
    xs = [g.cx(i) for i, j in cells]; zs = [g.cz(j) for i, j in cells]
    x0, x1, z0, z1 = min(xs) - CS / 2 - 0.4, max(xs) + CS / 2 + 0.4, min(zs) - CS / 2 - 0.4, max(zs) + CS / 2 + 0.4
    h.level.objects = [o for o in h.level.objects if o['id'] != 'spawn_marker']
    n = 0
    for o in src['objects']:
        if o['id'].startswith(SKIP_PREFIX) or o['id'].startswith('deco_'): continue
        x, y, z = o['pos']['x'], o['pos']['y'], o['pos']['z']
        if o['id'] == 'spawn_marker':
            h.level.objects.append(copy.deepcopy(o)); continue
        if not (x0 <= x <= x1 and z0 <= z <= z1): continue
        if y < -0.05 and not (x0 + 0.4 <= x <= x1 - 0.4 and z0 + 0.4 <= z <= z1 - 0.4): continue
        h.level.objects.append(copy.deepcopy(o)); n += 1
    return n


def generate(plan, name, seed=1, dry=False, furnish=True, objects_from=None):
    h = build_house(plan, name)
    rep = []
    if objects_from:
        rep = ['скопировано объектов из «%s»: %d' % (objects_from, copy_objects(h, objects_from))]
    elif furnish:
        fz = Furnisher(h, random.Random(seed))
        rep = fz.furnish()
    d = h.level.data()
    print(name + ':', counts(d))
    if not dry:
        path = h.level.write()
        print('записан', path)
    return h, rep


# ───────────────────────────── правка обстановки ─────────────────────────────

def edit(name, args):
    if not name.startswith('house_'): raise SystemExit('правим только house_*: ' + name)
    path = LEVELS / (name + '.json')
    d = json.loads(path.read_text().replace('NaN', 'null'))
    cat = catalog()
    objs = d['objects']
    cmd = args[0] if args else 'list'
    def show():
        p = Parsed(d)
        for n, o in enumerate(objs):
            if o['id'].startswith(SKIP_PREFIX): continue
            room = ''
            for r in p.rooms:
                if abs(r['L'] - floor_of(o['pos']['y']) * LVL_H) < 0.1 and p.grid.cell_of(o['pos']['x'], o['pos']['z']) in r['cells']: room = r['type']
            print('%3d %-30s %-9s (%.2f, %.2f, %.2f) yaw %.0f%s' % (n, o['id'], room, o['pos']['x'], o['pos']['y'], o['pos']['z'], o['rotY'], ' ← в ' + o['carrierId'] if o.get('carrierId') else ''))
    if cmd == 'list': show(); return
    def move_with_kit(n, dx, dz, dyaw=0.0):
        host = objs[n]
        hx, hz, hy = host['pos']['x'], host['pos']['z'], host['rotY']
        group = [host] + [o for o in objs if o is not host and abs(o['pos']['y'] - host['pos']['y']) < 3 and abs(o['pos']['x'] - hx) < 3 and abs(o['pos']['z'] - hz) < 3 and (
            o.get('carrierId') == host['id'] or (cat.get(o['id'], {}).get('mount') in ('Surface',) and within(host, o)))]
        for o in group:
            rx, rz = rot(dyaw, o['pos']['x'] - hx, o['pos']['z'] - hz)
            o['pos']['x'], o['pos']['z'] = hx + rx + dx, hz + rz + dz
            o['rotY'] = (o['rotY'] + dyaw) % 360
            if o.get('carrierId'):
                cx_, cz_ = rot(dyaw, o['carrierPos']['x'] - hx, o['carrierPos']['z'] - hz)
                o['carrierPos']['x'], o['carrierPos']['z'] = hx + cx_ + dx, hz + cz_ + dz
        return len(group)
    def within(host, o):
        hi = Item(host['id'], host['pos']['x'], host['pos']['y'], host['pos']['z'], host['rotY'], 0)
        r = hi.rect()
        return r[0] - 0.05 <= o['pos']['x'] <= r[2] + 0.05 and r[1] - 0.05 <= o['pos']['z'] <= r[3] + 0.05 and host['pos']['y'] <= o['pos']['y'] <= hi.top() + 0.9
    if cmd == 'remove':
        n = int(args[1]); host = objs[n]
        group = [host] + [o for o in objs if o is not host and (o.get('carrierId') == host['id'] and abs(o['carrierPos']['x'] - host['pos']['x']) < 0.05 or within(host, o))]
        for o in group: objs.remove(o)
        print('снесено %d (вместе с набором)' % len(group))
    elif cmd == 'move':
        n, dx, dz = int(args[1]), float(args[2]), float(args[3]); dyaw = float(args[4]) if len(args) > 4 else 0.0
        print('сдвинуто объектов:', move_with_kit(n, dx, dz, dyaw))
    elif cmd == 'rotate':
        n, yaw = int(args[1]), float(args[2])
        print('повёрнуто объектов:', move_with_kit(n, 0.0, 0.0, yaw - objs[n]['rotY']))
    elif cmd in ('add', 'swap'):
        plan_path = HERE / 'plans' / (name + '.json')
        if not plan_path.exists(): raise SystemExit('нет плана ' + str(plan_path) + ' — add/swap работают по плану дома')
        plan = json.loads(plan_path.read_text())
        h = build_house(plan, name)
        fz = Furnisher(h, random.Random(0))
        # уже стоящее — как занятое
        p = Parsed(d)
        for r in h.rooms:
            for o in objs:
                c = cat.get(o['id'])
                if not c or c['w'] is None: continue
                L = floor_of(o['pos']['y']) * LVL_H
                if abs(L - r.L) > 0.1 or p.grid.cell_of(o['pos']['x'], o['pos']['z']) not in r.cells: continue
                it = Item(o['id'], o['pos']['x'], o['pos']['y'], o['pos']['z'], o['rotY'], r.L, r)
                it.side = side_of_yaw(o['rotY']) if c['mount'] in ('Floor', 'Wall') else None
                fz.placed[r.name].append(it)
        fz.lv.objects = []
        if cmd == 'swap':
            n, oid = int(args[1]), args[2]
            old = objs[n]
            room = next(r for r in h.rooms if abs(r.L - floor_of(old['pos']['y']) * LVL_H) < 0.1 and p.grid.cell_of(old['pos']['x'], old['pos']['z']) in r.cells)
            edit(name, ['remove', str(n)])
            d = json.loads(path.read_text().replace('NaN', 'null')); objs = d['objects']
            fz.placed[room.name] = [it for it in fz.placed[room.name] if not (abs(it.x - old['pos']['x']) < 0.01 and abs(it.z - old['pos']['z']) < 0.01)]
            c = cat[oid]
            it = fz.at_wall(room, oid, sides=[side_of_yaw(old['rotY'])], want_t=(old['pos']['x'] if side_of_yaw(old['rotY']) in ('N', 'S') else old['pos']['z'])) if c['mount'] == 'Floor' else fz.wall_item(room, oid, side=side_of_yaw(old['rotY']))
            if it: fz.kit(room, it)
        else:
            rname, oid = args[1], args[2]; how = args[3] if len(args) > 3 else 'wall'
            room = h.find_room(rname)
            c = cat[oid]
            if how.startswith('wall:'): it = fz.at_wall(room, oid, sides=[how.split(':')[1]])
            elif how == 'center': it = fz.free(room, oid, at=(0.5, 0.5))
            elif how == 'corner': it = fz.at_wall(room, oid, corner='any')
            elif c['mount'] == 'Wall': it = fz.wall_item(room, oid)
            else: it = fz.at_wall(room, oid)
            if it: fz.kit(room, it)
        for o in fz.lv.objects:
            o['number'] = 1 + sum(1 for x in objs if x['id'] == o['id'])
            objs.append({k: v for k, v in o.items() if not k.startswith('_')})
        print('\n'.join(fz.report))
    else:
        raise SystemExit('неизвестная команда ' + cmd)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=True))
    print('записан', path)


# ───────────────────────────── CLI ─────────────────────────────

def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return
    cmd = a[0]
    if cmd == 'learn':
        learn(a[1] if len(a) > 1 else TEMPLATE_LEVEL)
    elif cmd == 'passport':
        p = Parsed(load_level(a[1])); print(p.passport())
    elif cmd == 'counts':
        print(a[1] + ':', counts(load_level(a[1])))
    elif cmd == 'build':
        plan = json.loads(pathlib.Path(a[1]).read_text())
        seed = int(a[a.index('--seed') + 1]) if '--seed' in a else plan.get('seed', 1)
        src = a[a.index('--objects-from') + 1] if '--objects-from' in a else None
        h, rep = generate(plan, a[2], seed=seed, dry='--dry' in a, furnish='--box' not in a, objects_from=src)
        print('\n'.join(rep))
    elif cmd == 'new':
        name = a[1]
        opt = lambda k, d: a[a.index(k) + 1] if k in a else d
        seed = int(opt('--seed', 1))
        plan = random_plan(seed=seed, nx=int(opt('--nx', 0)), nz=int(opt('--nz', 0)), floors=int(opt('--floors', 2)), porch=opt('--porch', 'W'), void='--no-void' not in a)
        (HERE / 'plans').mkdir(exist_ok=True)
        (HERE / 'plans' / (name + '.json')).write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        h, rep = generate(plan, name, seed=seed, dry='--dry' in a)
        print('\n'.join(rep))
    elif cmd == 'check':
        ok, bad = check(a[1])
        sys.exit(0 if ok else 1)
    elif cmd == 'edit':
        edit(a[1], a[2:])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
