"""Стенд комбинаций стройки на уровне «Комнаты (test)» (Илья 22.10: «построй сам разные комбинации:
1, 2, 3 комнаты внутри одного этажа; 1, 2, 3, 4 этажа с лестницами — чтобы тестировать разные комбинации»).

python3 combos_level.py            дописать здания в файл уровня (старые здания стенда не трогает, свои пересобирает)
python3 combos_level.py --dry      только посчитать
python3 combos_level.py --remove   убрать свои здания

Числа элементов — BUILD.md «СБОРКА УРОВНЯ ФАЙЛОМ»; записи копируются с живых записей стенда (стена, плита, дверь, лестница).
Своя зона — всё с x ≥ COMBO_X: клетки i ≥ 29 (здания Ильи стоят западнее −37,5). Этаж f — уровень f·3.

Ряд A (один этаж, без потолка): A1 — 1 комната 3×3; A2 — 2 комнаты через стену с дверью; A3 — 3 комнаты буквой Г (окно на север).
Ряд F (4×3 клетки, лестницы с площадкой по углам как в night_level.py, на каждом этаже 2 комнаты с дверью):
F2 — 2 этажа, верх открыт; F3 — 3 этажа, верх накрыт потолком; F4 — 4 этажа, верх открыт.
"""
import json, pathlib, shutil, sys, copy

LEVEL = pathlib.Path.home() / '.config/unity3d/DefaultCompany/Tavern/levels/Комнаты (test).json'
CS = 3.0
COMBO_I = 29
DOOR_STYLE = 3


def v3(x, y, z): return {'x': float(x), 'y': float(y), 'z': float(z)}


class Stand:
    def __init__(self, d):
        self.d = d
        self.ox, self.oz = d['gridOriginX'], d['gridOriginZ']
        self.tw = copy.deepcopy(d['walls'][0]); self.tf = copy.deepcopy(d['floors'][0])
        self.td = copy.deepcopy(d['doors'][0]); self.ts = copy.deepcopy(d['stairs'][0])
        self.walls, self.floors, self.doors, self.windows, self.stairs, self.zones = [], [], [], [], [], []

    def cx(self, i): return self.ox + i * CS
    def cz(self, j): return self.oz + j * CS
    def edge_x(self, i, j): return self.cx(i), self.oz + (j + 0.5) * CS      # ребро (i,j)|(i,j+1), стена вдоль X
    def edge_z(self, i, j): return self.ox + (i + 0.5) * CS, self.cz(j)      # ребро (i,j)|(i+1,j), стена вдоль Z

    def slab(self, i, j, L, ceiling):
        f = copy.deepcopy(self.tf); f['pos'] = v3(self.cx(i), L - 0.1, self.cz(j)); f['scale'] = v3(CS, 0.2, CS); f['ceiling'] = ceiling
        self.floors.append(f)

    def wall(self, x, z, L, spans_x):
        for w in self.walls:
            if abs(w['pos']['x'] - x) < 1e-3 and abs(w['pos']['z'] - z) < 1e-3 and abs(w['pos']['y'] - (L - 0.01 + 1.506)) < 0.01: return w
        w = copy.deepcopy(self.tw); w['pos'] = v3(x, L - 0.01 + 1.506, z); w['spansX'] = spans_x
        w['scale'] = v3(CS, 3.012, 0.25) if spans_x else v3(0.25, 3.012, CS)
        self.walls.append(w); return w

    def door(self, x, z, L):
        w = self.wall(x, z, L, None)
        self.walls.remove(w)
        rec = copy.deepcopy(self.td); rec['pos'] = v3(x, L, z); rec['spansX'] = w['spansX']; rec['open'] = False; rec['locked'] = False
        rec['style'] = DOOR_STYLE; rec['slug'] = ''; rec['wallSaved'] = True
        self.doors.append(rec)

    def window(self, x, z, L):
        w = self.wall(x, z, L, None)
        self.walls.remove(w)
        self.windows.append({'pos': v3(x, L, z), 'spansX': w['spansX'], 'style': 2, 'open': False, 'paintA': '', 'paintB': '', 'offset': 0.0,
                             'wallSaved': True, 'wallMaterial': 0, 'wallColorHex': '', 'wallPaintA': '', 'wallPaintB': '',
                             'wallPlinthA': False, 'wallPlinthB': False, 'wallPlinthHexA': '', 'wallPlinthHexB': '',
                             'wallPlinthStyleA': {'kind': 0, 'h': 0.0, 'd': 0.0, 'r': 0.0}, 'wallPlinthStyleB': {'kind': 0, 'h': 0.0, 'd': 0.0, 'r': 0.0},
                             'inside': 0, 'paintHex': '', 'trimHex': '', 'dirty': False})

    def stair(self, i_entry, i_land, j, L):
        s = copy.deepcopy(self.ts); s['pos'] = v3(self.ox + (min(i_entry, i_land) + 0.5) * CS, L, self.cz(j))
        s['rotY'] = 90.0 if i_land > i_entry else 270.0; s['riseCells'] = 1; s['lengthCells'] = 1; s['landing'] = True; s['visual'] = ''
        self.stairs.append(s)

    def zone(self, name, cells):
        self.zones.append({'name': name, 'slug': '', 'cr': 1.0, 'cg': 1.0, 'cb': 1.0, 'kind': 2, 'strong': True, 'fireSpread': False,
                           'temp': float('nan'), 'attackers': '', 'exits': '', 'cells': [v3(self.cx(i), 0.1, self.cz(j)) for i, j in cells]})

    def box(self, cells, L):
        """Периметр множества клеток на уровне L: стена на каждом ребре, за которым клетки нет."""
        cs = set(cells)
        for (i, j) in cs:
            if (i + 1, j) not in cs: self.wall(*self.edge_z(i, j), L, False)
            if (i - 1, j) not in cs: self.wall(*self.edge_z(i - 1, j), L, False)
            if (i, j + 1) not in cs: self.wall(*self.edge_x(i, j), L, True)
            if (i, j - 1) not in cs: self.wall(*self.edge_x(i, j - 1), L, True)

    def floor_cells(self, cells, L, ceiling, holes=()):
        for (i, j) in cells:
            if (i, j) in holes: continue
            self.slab(i, j, L, ceiling)


def rect(i0, j0, w, h): return [(i, j) for i in range(i0, i0 + w) for j in range(j0, j0 + h)]


def row_a(s, j0):
    # A1: одна комната
    a1 = rect(31, j0, 3, 3)
    s.floor_cells(a1, 0, False); s.box(a1, 0); s.door(*s.edge_x(32, j0 - 1), 0); s.zone('A1: 1 комната', a1)
    # A2: две комнаты через стену, дверь между ними и наружу
    a2 = rect(36, j0, 6, 3)
    s.floor_cells(a2, 0, False); s.box(a2, 0)
    for j in range(j0, j0 + 3): s.wall(*s.edge_z(38, j), 0, False)
    s.door(*s.edge_z(38, j0 + 1), 0); s.door(*s.edge_x(37, j0 - 1), 0); s.zone('A2: 2 комнаты', a2)
    # A3: три комнаты буквой Г
    r1, r2, r3 = rect(44, j0, 3, 3), rect(47, j0, 3, 3), rect(47, j0 + 3, 3, 3)
    a3 = r1 + r2 + r3
    s.floor_cells(a3, 0, False); s.box(a3, 0)
    for j in range(j0, j0 + 3): s.wall(*s.edge_z(46, j), 0, False)
    for i in range(47, 50): s.wall(*s.edge_x(i, j0 + 2), 0, True)
    s.door(*s.edge_z(46, j0 + 1), 0); s.door(*s.edge_x(48, j0 + 2), 0); s.door(*s.edge_x(45, j0 - 1), 0)
    s.window(*s.edge_x(48, j0 + 5), 0); s.zone('A3: 3 комнаты', a3)


def tower(s, i0, j0, floors, roofed, name):
    cells = rect(i0, j0, 4, 3)
    def stair_cells(f): return [(i0, j0), (i0 + 1, j0)] if f % 2 == 0 else [(i0 + 3, j0 + 2), (i0 + 2, j0 + 2)]
    for f in range(floors):
        L = f * CS
        holes = set(stair_cells(f - 1)) if f > 0 else set()
        s.floor_cells(cells, L, f > 0, holes); s.box(cells, L)
        for j in range(j0, j0 + 3): s.wall(*s.edge_z(i0 + 1, j), L, False)
        s.door(*s.edge_z(i0 + 1, j0 + 1), L)
        if f > 0:
            if (f - 1) % 2 == 0: s.wall(*s.edge_x(i0, j0), L, True)
            else: s.wall(*s.edge_x(i0 + 3, j0 + 1), L, True)
        if f < floors - 1:
            a, b = stair_cells(f); s.stair(a[0], b[0], a[1], L)
        if f == 0: s.door(*s.edge_x(i0 + 2, j0 - 1), 0)
        else: s.window(*s.edge_x(i0 + 2, j0 + 2), L)
    if roofed: s.floor_cells(cells, floors * CS, True)
    s.zone(name, cells)


def strip(d):
    lim = d['gridOriginX'] + (COMBO_I - 0.5) * CS
    for k in ('walls', 'floors', 'doors', 'windows', 'stairs'):
        d[k] = [e for e in d.get(k, []) if e['pos']['x'] < lim]
    d['zones'] = [z for z in d.get('zones', []) if not (z.get('kind') == 2 and z.get('cells') and all(c['x'] >= lim for c in z['cells']))]


def main():
    d = json.load(open(LEVEL))
    strip(d)
    if '--remove' not in sys.argv:
        s = Stand(d)
        row_a(s, 24)
        tower(s, 31, 30, 2, False, 'F2: 2 этажа, верх открыт')
        tower(s, 37, 30, 3, True, 'F3: 3 этажа, потолок')
        tower(s, 43, 30, 4, False, 'F4: 4 этажа, верх открыт')
        d['walls'] += s.walls; d['floors'] += s.floors; d['doors'] += s.doors; d['windows'] = d.get('windows', []) + s.windows
        d['stairs'] += s.stairs; d['zones'] += s.zones
        print('своих: стены=%d плиты=%d двери=%d окна=%d лестницы=%d зоны=%d' % (len(s.walls), len(s.floors), len(s.doors), len(s.windows), len(s.stairs), len(s.zones)))
    print('итого: стены=%d плиты=%d двери=%d окна=%d лестницы=%d зоны=%d' % (len(d['walls']), len(d['floors']), len(d['doors']), len(d['windows']), len(d['stairs']), len(d['zones'])))
    if '--dry' in sys.argv: return
    bak = pathlib.Path('/tmp/claude-1000/-home-ilya/70844c55-db36-46ed-a464-c77a2320bc49/scratchpad') / 'rooms_test.before-combos.json'
    if not bak.exists(): shutil.copy(LEVEL, bak)
    LEVEL.write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=True))
    print('записано', LEVEL)


if __name__ == '__main__':
    main()
