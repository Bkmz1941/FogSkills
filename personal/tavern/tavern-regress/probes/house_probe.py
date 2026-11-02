#!/usr/bin/env python3
"""Генерация домов (HOUSES.md, HG-…): оффлайн, без Unity, ничего не пишет.
Эталон «Котедж 104» читается и обязан быть HOUSE ok; план коттеджа даёт коробку с теми же счётчиками;
случайные дома по сидам собираются и проходят check; уровни Ильи защищены от записи.

python3 house_probe.py            вердикт HOUSE-PROBE ok / FAIL (список причин)
"""
import io, json, pathlib, random, sys, contextlib

HG = pathlib.Path.home() / '.claude/skills/tavern-houses'
sys.path.insert(0, str(HG))
import housegen as hg

bad = []


def expect(cond, msg):
    if not cond: bad.append(msg)


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def main():
    ref = hg.TEMPLATE_LEVEL
    try:
        d = hg.load_level(ref)
    except FileNotFoundError:
        print('HOUSE-PROBE SKIP: нет файла эталона', ref); return 0
    # HG-R01..R03: паспорт эталона
    p = hg.Parsed(d)
    types = sorted((r['L'], r['type'], len(r['cells'])) for r in p.rooms)
    expect((0.0, 'kitchen', 6) in types, 'HG-R01: кухня 6 клеток не найдена: %s' % types)
    expect(any(t == (3.0, 'bathroom', 4) for t in types), 'HG-R01: ванная 4 клетки не найдена')
    expect(any(t == (3.0, 'bedroom', 4) for t in types), 'HG-R02: спальня этажа 1 не найдена')
    expect(any(t[0] == 0.0 and t[2] == 14 for t in types), 'HG-R01: гостиная+кабинет 14 клеток не найдены')
    attic = [r for r in p.rooms if r['type'] == 'attic']
    expect(attic and not attic[0]['objects'], 'HG-R03: на чердаке не должно быть объектов (лампы этажа 1 попали на чердак?)')
    # HG-C01: эталон зелёный
    ok, reasons = quiet(hg.check, d, True)
    expect(ok, 'HG-C01: эталон красный: ' + '; '.join(reasons[:5]))
    # HG-R04: защита уровней Ильи
    try:
        hg.Level('level1').write(); expect(False, 'HG-R04: write в level1 не отказал')
    except SystemExit:
        pass
    # HG-B01, B02: коробка по плану коттеджа
    plan = json.loads((HG / 'plans' / 'house_cottage.json').read_text())
    h = hg.build_house(plan, 'house_probe_tmp')
    box = h.level.data()
    got = tuple(len(box[k]) for k in ('walls', 'floors', 'doors', 'windows', 'stairs', 'roofs'))
    expect(got == (39, 63, 7, 5, 1, 1), 'HG-B01: коробка коттеджа %s, ждали (39, 63, 7, 5, 1, 1)' % (got,))
    ref_counts = tuple(len(d[k]) for k in ('walls', 'floors', 'doors', 'windows', 'stairs', 'roofs'))
    expect(got == ref_counts, 'HG-B01: коробка %s ≠ оригинал %s' % (got, ref_counts))
    # HG-F01..F05: обстановка генератора на плане коттеджа
    fz = hg.Furnisher(h, random.Random(1)); rep = fz.furnish()
    gen = h.level.data()
    ok, reasons = quiet(hg.check, gen, True)
    expect(ok, 'HG-F: house_cottage_gen красный: ' + '; '.join(reasons[:5]))
    misses = [l for l in rep if 'НЕ ВСТАЛ' in l]
    expect(len(misses) <= 6, 'HG-F: слишком много отказов посадки (%d): %s' % (len(misses), misses[:4]))
    # HG-B05: случайные планы
    for seed, nx, nz in ((1, 4, 5), (2, 4, 4), (3, 5, 5), (4, 5, 6), (5, 4, 6)):
        try:
            pl = hg.random_plan(seed=seed, nx=nx, nz=nz)
            hh = hg.build_house(pl, 'house_probe_tmp')
            hg.Furnisher(hh, random.Random(seed)).furnish()
            ok, reasons = quiet(hg.check, hh.level.data(), True)
            expect(ok, 'HG-B05/F: сид %d (%d×%d) красный: %s' % (seed, nx, nz, '; '.join(reasons[:4])))
        except Exception as e:
            expect(False, 'HG-B05: сид %d (%d×%d) упал: %s' % (seed, nx, nz, e))
    lvl_dir = hg.LEVELS
    expect(not (lvl_dir / 'house_probe_tmp.json').exists(), 'проба записала файл house_probe_tmp.json — не должна')
    line = 'HOUSE-PROBE ok: эталон зелёный, коробка %s, генератор и 5 сидов зелёные' % (got,) if not bad else 'HOUSE-PROBE FAIL (%d): ' % len(bad) + ' || '.join(bad)
    print(line)
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
