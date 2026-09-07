"""Здоровье доменных файлов скилов: размер, оглавление, даты в заголовках, разделы-гиганты.

python3 skills_lint.py            отчёт по доменным файлам (код 0)
python3 skills_lint.py --strict   код 1, если есть предупреждения
"""
import re, sys, pathlib

SK = pathlib.Path.home() / '.claude/skills'
DOMAIN = ['tavern-game/BUILD.md', 'tavern-game/VIEW.md', 'tavern-game/WEATHER.md', 'tavern-game/BLENDER.md',
          'tavern-game/CHARACTER.md',
          'tavern-game/MONSTERS.md', 'tavern-game/UI.md', 'tavern-game/ARCHITECTURE.md',
          'tavern-game/ATTRIBUTES.md', 'tavern-cooking/COOKING.md']
# Список НЕ зашивается: скилы заводятся и вырезаются (одежда, руки — 07–08.09),
# а зашитый список молча перестаёт считать новые и врёт про бюджет.
SKILLS = None  # заполняется поиском при запуске
DATE = re.compile(r'20\d\d-\d\d-\d\d|\b\d\d\.\d\d\b')
BIG_KB = 40
SKILLS_BUDGET_KB = 50


def sections(lines):
    heads = [i for i, l in enumerate(lines) if l.startswith('## ')]
    out = []
    for k, i in enumerate(heads):
        j = heads[k + 1] if k + 1 < len(heads) else len(lines)
        body = '\n'.join(lines[i:j])
        out.append((lines[i][3:], len(body.encode()) // 1024, sum(1 for l in lines[i:j] if l.startswith('### '))))
    return out


def report(rel):
    p = SK / rel
    lines = p.read_text(encoding='utf-8').split('\n')
    secs = sections(lines)
    kb = p.stat().st_size // 1024
    toc = any(re.search(r'Что где|Оглавлен|\| Раздел \|', l) for l in lines[:80])
    dated = [t for t, _, _ in secs if DATE.search(t)]
    big = [(t, s) for t, s, _ in secs if s > BIG_KB]
    orphans = sum(h3 for t, _, h3 in secs if DATE.search(t))
    warns = []
    if not toc and len(secs) >= 8:
        warns.append('нет оглавления')
    if dated:
        warns.append(f'{len(dated)} разделов с датой в заголовке (история в домене)')
    if big:
        warns.append('разделы больше %d КБ: ' % BIG_KB + ', '.join(f'«{t[:40]}» {s} КБ' for t, s in big))
    if orphans:
        warns.append(f'{orphans} подразделов под датированными заголовками')
    print(f'{rel:<32} {kb:4d} КБ  разделов {len(secs):3d}  ' + ('ок' if not warns else '; '.join(warns)))
    return warns


def main():
    strict = '--strict' in sys.argv
    total = 0
    for rel in DOMAIN:
        total += len(report(rel))
    # Считаем ДВЕ разные вещи, потому что грузятся они по-разному: `tavern-game`
    # поднимается в любой сессии по игре, остальные — только когда их позвали.
    # Бюджет — на всегда-часть; смешивать их в одно число значит врать себе.
    skills = sorted(SK.glob('tavern-*/SKILL.md'))
    always = [f for f in skills if f.parent.name == 'tavern-game']
    always_kb = sum(f.stat().st_size for f in always) // 1024
    rest_kb = sum(f.stat().st_size for f in skills) // 1024 - always_kb
    line = (f'SKILL.md: всегда {always_kb} КБ (tavern-game), по требованию ещё '
            f'{rest_kb} КБ на {len(skills) - len(always)} скилов')
    if always_kb > SKILLS_BUDGET_KB:
        line += f' — всегда-часть больше бюджета {SKILLS_BUDGET_KB} КБ'
        total += 1
    print(line)
    print(f'предупреждений: {total}')
    sys.exit(1 if strict and total else 0)


if __name__ == '__main__':
    main()
