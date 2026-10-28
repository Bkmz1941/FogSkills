#!/usr/bin/env python3
"""Сверка стыка двух роликов стычки: python3 crow_seamdiff.py a.json b.json

a — последний кадр Crow_Brace, b — первый кадр развязки. Всё, кроме угла
камеры, обязано быть нулём: угол держится в пределах 0.003° (округление).
"""
import json, math, sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])
d = lambda u, v: math.sqrt(sum((x - y) ** 2 for x, y in zip(u, v)))
print('птица, позиция     : %.5f игровых м' % d(a['crow_loc'], b['crow_loc']))
print('птица, поворот     : %.3f°' % max(
    abs(math.degrees(x - y)) for x, y in zip(a['crow_rot'], b['crow_rot'])))
print('голова человека    : %.5f игровых м' % d(a['head'], b['head']))
print('поза, худшая кость : %.5f' % max(
    max(abs(x - y) for x, y in zip(q, b['bones'][n]))
    for n, q in a['bones'].items() if n in b['bones']))
print('камера, позиция    : %.5f' % d(a['cam_loc'], b['cam_loc']))
print('камера, направление: %.4f°' % math.degrees(math.acos(max(-1.0, min(1.0,
    sum(x * y for x, y in zip(a['cam_fwd'], b['cam_fwd'])))))))
print('камера, фокусное   : %.1f → %.1f мм' % (a['lens'], b['lens']))
