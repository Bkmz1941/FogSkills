"""Брифинг по багам: правила из граблей и инварианты по области, линт формата.

python3 bugs.py                 области с числом записей и инвариантов
python3 bugs.py <область>       правила граблей, инварианты и проверки области
python3 bugs.py P042            запись целиком
python3 bugs.py --lint          формат PITFALLS.md и INVARIANTS.md (код 1, если красное)
"""
import re, sys, pathlib

GAME = pathlib.Path.home() / '.claude/skills/tavern-game'
REG = pathlib.Path.home() / '.claude/skills/tavern-regress'
PITFALLS = GAME / 'PITFALLS.md'
INVARIANTS = REG / 'INVARIANTS.md'

AREAS = {
    'процесс': 'редактор Unity, MCP, компиляция, тесты, git, параллельные сессии, зонды',
    'блендер': 'сцены и экспорт Blender → FBX → Unity: геометрия, оси, узлы, материалы, params',
    'габариты': 'коллайдеры, bounds, пивоты, сетка',
    'наведение': 'луч курсора, выделение, клики, выбор части и вложенного',
    'осмотр': 'режим осмотра: камера, гейты осмотра',
    'части': 'подвижные детали: створки, ящики, рычаги, тумблеры',
    'контейнеры': 'слоты, закрытые секции, вложенность, стопки, раскладки',
    'постановка': 'куда и как ставится: опора, пересечения, снапы, кит, стена',
    'перенос': 'предмет в руке: видимость, матч, призрак, подача',
    'жидкости': 'LiquidVolume: уровень, грань, налив, кран, слив',
    'обводка': 'контур выделения и наведения',
    'рендер': 'материалы, шейдеры, свет, очереди, z-fighting',
    'приборы': 'тумблеры, питание, вода, индикаторы, статус «Работает»',
    'дефы': 'ObjectDef, каталог, категории, узлы, бар',
    'сейв': 'сохранение и загрузка уровня',
    'ui': 'HUD, карточки, попапы, подписи',
    'готовка': 'продукты, состояния, раскладки еды, блюда',
}
REQUIRED = ('Симптом', 'Причина', 'Правило')
HEAD = re.compile(r'^## (P\d{3}) · ([^·]+?) · (.+)$')
FIELD = re.compile(r'^- \*\*(Симптом|Причина|Решение|Правило|Защита)[^*]*\*\*\s*(.*)$')
PREF = re.compile(r'P\d{3}')


def parse_pitfalls(path=None):
    entries, cur, fenced, last = [], None, False, None
    for line in (path or PITFALLS).read_text(encoding='utf-8').splitlines():
        if line.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEAD.match(line)
        if m:
            cur = {'id': m.group(1), 'areas': [a.strip() for a in m.group(2).split(',')],
                   'title': m.group(3).strip(), 'fields': {}, 'raw': [line]}
            entries.append(cur)
            last = None
            continue
        if line.startswith('## '):
            cur = None
            continue
        if cur is None:
            continue
        cur['raw'].append(line)
        f = FIELD.match(line)
        if f:
            last = f.group(1)
            cur['fields'][last] = f.group(2).strip()
        elif last and line.startswith('  '):
            cur['fields'][last] += ' ' + line.strip()
    return entries


def parse_invariants():
    rows = []
    for line in INVARIANTS.read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 5 and cells[0].isdigit():
            rows.append({'n': int(cells[0]), 'areas': [a.strip() for a in cells[1].split(',')],
                         'rule': cells[2], 'check': cells[3], 'refs': PREF.findall(cells[4]),
                         'broke': cells[5] if len(cells) > 5 else ''})
    return rows


def lint(entries, rows):
    problems, warnings = [], []
    seen = set()
    for e in entries:
        if e['id'] in seen:
            problems.append(f"{e['id']}: номер повторяется")
        seen.add(e['id'])
        for a in e['areas']:
            if a not in AREAS:
                problems.append(f"{e['id']}: неизвестная область «{a}»")
        for f in REQUIRED:
            if not e['fields'].get(f):
                problems.append(f"{e['id']}: нет поля «{f}»")
        if not e['fields'].get('Решение'):
            warnings.append(f"{e['id']}: без «Решение»")
        if not e['fields'].get('Защита'):
            warnings.append(f"{e['id']}: без «Защита»")
    nums = [int(e['id'][1:]) for e in entries]
    if nums and nums != sorted(nums):
        warnings.append('номера идут не по порядку')
    problems += lint_copies(entries)
    seen_n = set()
    for r in rows:
        if r['n'] in seen_n:
            problems.append(f"инвариант {r['n']}: номер повторяется")
        seen_n.add(r['n'])
        for a in r['areas']:
            if a not in AREAS:
                problems.append(f"инвариант {r['n']}: неизвестная область «{a}»")
        for ref in r['refs']:
            if ref not in seen:
                problems.append(f"инвариант {r['n']}: ссылка на {ref}, которого нет")
    return problems, warnings


def lint_copies(entries):
    """Скилы-спутники держат ВЫБОРКУ из общего реестра дословной копией.
    Копия, разошедшаяся с оригиналом, — это две правды об одном баге, и
    расходятся они молча. Проверяется каждый `*/PITFALLS.md`, кроме общего."""
    origin = {e['id']: '\n'.join(e['raw']).strip() for e in entries}
    out = []
    root = PITFALLS.resolve().parent.parent
    for path in sorted(root.glob('*/PITFALLS.md')):
        if path.resolve() == PITFALLS.resolve():
            continue
        skill = path.parent.name
        for e in parse_pitfalls(path):
            body = '\n'.join(e['raw']).strip()
            if e['id'] not in origin:
                out.append(f"{skill}: копия {e['id']} есть, а в общем реестре её нет")
            elif body != origin[e['id']]:
                out.append(f"{skill}: копия {e['id']} разошлась с оригиналом")
    return out


def show_area(area, entries, rows):
    if area not in AREAS:
        print(f'неизвестная область «{area}»; есть:', ', '.join(AREAS))
        return 1
    print(f'=== {area}: {AREAS[area]}')
    inv = [r for r in rows if area in r['areas']]
    print(f'--- Инварианты ({len(inv)})')
    for r in inv:
        refs = ' ' + ','.join(r['refs']) if r['refs'] else ''
        print(f" {r['n']:>2}. {r['rule']}  [{r['check']}]{refs}")
    hits = [e for e in entries if area in e['areas']]
    print(f'--- Правила из граблей ({len(hits)})')
    for e in hits:
        tag = '' if e['areas'][0] == area else f" (главная: {e['areas'][0]})"
        print(f"{e['id']} {e['title']}{tag}")
        print(f"     Правило: {e['fields'].get('Правило', '—')}")
        if e['fields'].get('Защита'):
            print(f"     Защита: {e['fields']['Защита']}")
    checks = sorted({r['check'] for r in inv})
    print('--- Чем проверять после правки')
    for c in checks:
        print(' ', c)
    print('  python3 ~/.claude/skills/tavern-regress/probes/check_all.py')
    return 0


def show_entry(pid, entries):
    for e in entries:
        if e['id'] == pid:
            print('\n'.join(e['raw']).rstrip())
            return 0
    print(f'{pid} не найден')
    return 1


def show_areas(entries, rows):
    print(f'{"область":<12} {"записей":>7} {"инвар.":>6}  описание')
    for a, d in AREAS.items():
        n = sum(1 for e in entries if a in e['areas'])
        k = sum(1 for r in rows if a in r['areas'])
        print(f'{a:<12} {n:>7} {k:>6}  {d}')
    print(f'всего записей: {len(entries)}, инвариантов: {len(rows)}')


def main():
    entries, rows = parse_pitfalls(), parse_invariants()
    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg == '--lint':
        problems, warnings = lint(entries, rows)
        for w in warnings:
            print('  предупреждение:', w)
        for p in problems:
            print('  КРАСНОЕ:', p)
        print(f'линт: записей {len(entries)}, инвариантов {len(rows)}, '
              f'ошибок {len(problems)}, предупреждений {len(warnings)}')
        sys.exit(1 if problems else 0)
    if not arg:
        show_areas(entries, rows)
        sys.exit(0)
    if PREF.fullmatch(arg):
        sys.exit(show_entry(arg, entries))
    sys.exit(show_area(arg, entries, rows))


if __name__ == '__main__':
    main()
