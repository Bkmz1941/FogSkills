#!/usr/bin/env python3
"""Уникальность номеров объектов в файлах уровней (P1261, инвариант 649).

Илья 01.11: «у нас продублировались приборы названия — раздели плз нейминги». Копия дома на «Котедже 104»
повторила пары (id, number) оригинала — 216 пар; выключатель копии мог включать лампу оригинала.

Правило: внутри уровня пара (id, number) у полных объектов (`objects`) уникальна — КРАСНОЕ. Дубли (id, n) у коротких
записей растений (`plants`) — предупреждение: на «Котедже 104» их 35 с 31.10 (лесной скил), вреда не замечено. Оффлайн, без Unity, по всем `levels/*.json`; служебные `_*.json` пропускаются.
Последняя строка — итог для check_all: «ЗЕЛЁНОЕ …» или «КРАСНОЕ … :: подробности».
"""
import collections
import glob
import json
import os
import sys

LEVELS = os.path.expanduser('~/.config/unity3d/DefaultCompany/Tavern/levels')


def dups(path):
    """→ (дубли полных объектов, дубли растений)."""
    data = json.load(open(path, encoding='utf-8'))
    objs = collections.Counter((o.get('id', ''), o['number']) for o in data.get('objects', []) if 'number' in o)
    plants = collections.Counter((p.get('id', ''), p.get('n')) for p in data.get('plants', []) if 'n' in p)
    # Растение может лежать и полной записью (насест вороны) — его номер в общем ряду своего id.
    both = collections.Counter(plants)
    for key, k in objs.items():
        if key in plants:
            both[key] += k
    hard = [(k, n) for k, n in objs.items() if n > 1]
    soft = [(k, n) for k, n in both.items() if n > 1 and (k, n) not in hard]
    return hard, soft


def main():
    bad, warn = [], []
    total = 0
    for path in sorted(glob.glob(os.path.join(LEVELS, '*.json'))):
        name = os.path.basename(path)
        if name.startswith('_'):
            continue
        try:
            hard, soft = dups(path)
        except Exception as e:  # битый файл — сказать и идти дальше
            print('пропуск', name, e)
            continue
        total += 1
        fmt = lambda found: ', '.join('%s#%s×%d' % (k[0], k[1], n) for k, n in found[:5])
        if hard:
            bad.append('%s: %d пар (%s)' % (name, len(hard), fmt(hard)))
            print(name, 'объекты: дублей', len(hard), fmt(hard))
        if soft:
            warn.append('%s: %d' % (name, len(soft)))
            print(name, 'растения (предупреждение, P1261): дублей', len(soft), fmt(soft))
    tail = (' ; растения с дублями: ' + ', '.join(warn)) if warn else ''
    if bad:
        print('КРАСНОЕ: дубли (id, number) объектов в %d из %d уровней :: %s%s' % (len(bad), total, ' | '.join(bad), tail))
        sys.exit(1)
    print('ЗЕЛЁНОЕ: уровней %d, дублей (id, number) у объектов нет%s' % (total, tail))


if __name__ == '__main__':
    main()
