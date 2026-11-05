#!/usr/bin/env python3
"""Кадр жизни существ (скил tavern-regress-life, LF-F; Илья 05.11: «упор и тесты на фпс от новых механик»).

python3 life_fps_probe.py [кадров]   в play, уровень Ильи как есть (не менять): профайлер редактора за N кадров
                                     (по умолчанию 150 — на уровнях > 20 тыс. объектов больше нельзя, P1111) и пороги
                                     по маркерам Cozy.Life: self-мс и мусор на кадр. Код 1 — порог превышен.

Пороги — с запасом над замером 05.11 «Котедж 104» (57 тыс. объектов, Валера в кругу дел):
  LifeRulesRunner.Update  0.061 мс, 20 Б/кадр   (до починки CreaturesNow — 0.100 мс и 10 021 Б/кадр)
  CreaturePlan.Update     0.099 мс, 824 Б/кадр  (до — 1 622 Б/кадр)
Замер шумный: уровень ещё грузится первые ~60 с после play (GridCursor создаёт объекты) — мерить после.
"""
import re, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).parent
LIMITS = {  # маркер: (мс self, байт мусора на кадр)
    'LifeRulesRunner.Update': (0.25, 1024),
    'CreaturePlan.Update': (0.40, 4096),
    'SpeechBubbles.Update': (0.20, 512),
}


def main():
    frames = sys.argv[1] if len(sys.argv) > 1 else '150'
    out = subprocess.run(['python3', str(HERE / 'gc_probe.py'), 'profile', frames], capture_output=True, text=True, timeout=600).stdout
    if 'frames=' not in out:
        print('профайлер не ответил:\n' + out[-800:]); return 1
    ms, gc = {}, {}
    section = None
    for line in out.splitlines():
        if line.startswith('--- self ms'): section = 'ms'; continue
        if line.startswith('--- GC bytes'): section = 'gc'; continue
        for name in LIMITS:
            if name + '()' not in line: continue
            m = re.match(r'\s*([\d.]+)\s*(ms|B)', line)
            if not m: continue
            (ms if section == 'ms' else gc)[name] = float(m.group(1))
    print(out.splitlines()[0])
    bad = 0
    for name, (lim_ms, lim_b) in LIMITS.items():
        a, b = ms.get(name, 0.0), gc.get(name, 0.0)
        ok = a <= lim_ms and b <= lim_b
        bad += not ok
        print(('✓' if ok else '✗') + f' {name}: {a:.3f} мс (порог {lim_ms}), {b:.0f} Б/кадр (порог {lim_b})')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
