"""Брифинг по багам: правила из граблей и инварианты по области, линт формата.

python3 bugs.py                 области с числом записей и инвариантов
python3 bugs.py <область>       КОРОТКИЙ брифинг: чем проверить сейчас, инварианты одной строкой, грабли заголовками
python3 bugs.py <область> --full  то же, но правила и защиты граблей целиком (длинно: постановка — 80 КБ)
python3 bugs.py 148             инвариант целиком
python3 bugs.py P042            запись граблей целиком
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
    'погода': 'стихии: огонь, туман, ветер, дождь — объёмы клетки, зоны, петли анимации, цена кадра',
    'звук': 'слышимость: GameSfx, приглушение по этажам и комнатам, громкость и выравнивание клипов, голоса существ и стихий',
    'стычки': 'кинематографичная стычка: наезд камеры, замедление, варианты действий, предпросмотр исхода, развязка',
    'монстры': 'существа мира: безумцы, ворона, сова — модели, спавн, поведение, насест и полёт',
    'персонаж': 'герой: модель, движение, присед, лазание, урон от падения, руки и поза',
    'анимация': 'клипы героя и существ: позы, переходы, сид клипа, корень и тело',
    'камера': 'камера игры: слежение, наезд, осмотр, просвет крон',
    'видимость': 'что видно: этажный гейт, срез стен, чёрные зоны, дальний радиус',
    'одежда': 'вещи на герое и сложенные: ткань из тела, веса, слоты',
    'стройка': 'стены, плиты, крыши, окна, двери, лестницы — сетка дома',
    'зоны': 'зоны уровня: события, условия, объёмы',
    'выкладка': 'предметы внутри контейнера и друг на друге: мойка, миска, камин',
    'локализация': 'Loc, en.json, перевод строк кода',
    'производительность': 'цена кадра: перебор объектов, доп. камеры, мусор в памяти',
    'ии': 'ИИ-жизнь: модель и сервер, пульт AiConsole, правила уровня LifeRules, планы существ CreaturePlan',
}
ALIASES = {
    'UI': 'ui', 'анимации': 'анимация', 'туман': 'погода', 'свет': 'рендер', 'существа': 'монстры',
    'ИИ': 'ии', 'модель': 'ии', 'правила': 'ии', 'попапы': 'ui', 'тесты': 'процесс', 'дебаг': 'ui', 'листы': 'постановка',
    'оси': 'блендер', 'импорт': 'блендер', 'вид': 'видимость', 'дебаг': 'ui',
}


def norm_areas(text):
    return [ALIASES.get(a.strip(), a.strip()) for a in text.split(',')]
REQUIRED = ('Симптом', 'Причина', 'Правило')
HEAD = re.compile(r'^## (P\d{3}) · ([^·]+?) · (.+)$')
PENDING = re.compile(r'⏳|не проверен[оа] в игре|живьём не проверен', re.IGNORECASE)
FIELD = re.compile(r'^- \*\*(Симптом|Причина|Решение|Правило|Защита)[^*]*\*\*\s*(.*)$')
PREF = re.compile(r'P\d{3}')
PROBE_FILE = re.compile(r'`(?:[A-Za-z_0-9./-]*/)?([a-z_0-9]+\.(?:py|cs))`')
PROBE_PATH = re.compile(r'`([A-Za-z_0-9./-]+\.(?:py|cs))`')
CELL = re.compile(r'(?<!\\)\|')
PROJECT = pathlib.Path('/media/ilya/T714/Unity/Tavern-fresh')
RULE_NO = re.compile(r'правил[оа]\s+(\d+[a-z]?)')
TEST_NAME = re.compile(r'`([A-Za-zА-Яа-яЁё]+Tests)(?:\.[^`]+)?`')
# области, где крит-сценарий Ильи «положить на землю» гоняется всегда
DROP_AREAS = ('постановка', 'перенос', 'сейв', 'габариты', 'наведение')


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
            cur = {'id': m.group(1), 'areas': norm_areas(m.group(2)),
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
        cells = [c.strip() for c in CELL.split(line.strip().strip('|'))]
        if len(cells) >= 5 and cells[0].isdigit():
            rows.append({'n': int(cells[0]), 'areas': norm_areas(cells[1]),
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
        if PENDING.search(e['fields'].get('Решение', '') + ' ' + e['fields'].get('Защита', '')):
            warnings.append(f"{e['id']}: ⏳ починка НЕ ПРОВЕРЕНА в игре — проверить пробой при первом свободном play и снять ⏳")
    nums = [int(e['id'][1:]) for e in entries]
    if nums and nums != sorted(nums):
        warnings.append('номера идут не по порядку')
    problems += lint_copies(entries)
    seen_n = set()
    for line in INVARIANTS.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^\|\s*(\d+)\s*\|', line)
        if not m:
            continue
        cells = CELL.split(line.strip().strip('|'))
        if len(cells) != 6:
            problems.append(f"инвариант {m.group(1)}: колонок {len(cells)}, нужно 6 — брифинг такую строку не видит")
    for r in rows:
        if r['n'] in seen_n:
            problems.append(f"инвариант {r['n']}: номер повторяется")
        seen_n.add(r['n'])
        for path in PROBE_PATH.findall(r['check']):
            if is_probe_ref(path) and not probe_exists(path):
                warnings.append(f"инвариант {r['n']}: зонда {path} нет на диске")
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


def headline(rule, limit=110):
    t = rule.lstrip('⭐ ').strip()
    i = t.find(': ')
    if 40 <= i <= 140:
        t = t[:i]
    elif len(t) > limit:
        cuts = [j for j in (t.find('. ', 40), t.find(' — ', 40), t.find('; ', 40)) if j > 0]
        if cuts:
            t = t[:min(cuts)]
    t = t.rstrip(' :—.;')
    return t if len(t) <= limit else t[:limit - 1] + '…'


SERVICE_FILES = ('check_all.py', 'cycle.py', 'measure.py', 'bugs.py', 'compile_check.py', 'mcp_call.py')


def probe_exists(path):
    name = path.split('/')[-1]
    places = (REG / 'probes' / name, GAME / 'probes' / name, PROJECT / path, REG / path, GAME / path)
    return any(x.exists() for x in places)


def is_probe_ref(path):
    name = path.split('/')[-1]
    return name not in SERVICE_FILES and ('probe' in name or path.startswith('probes/') or path.startswith('BlenderWork/'))


def check_tag(check):
    tags = []
    rules = sorted(set(RULE_NO.findall(check)), key=lambda r: int(re.match(r'\d+', r).group()))
    if rules:
        tags.append('правило ' + ','.join(rules))
    elif 'invariants_play' in check:
        tags.append('invariants_play')
    tags += sorted(set(f for f in PROBE_FILE.findall(check) if f != 'invariants_play.py' and f not in SERVICE_FILES))
    tests = sorted(set(TEST_NAME.findall(check)))
    if tests:
        tags.append('тест ' + ', '.join(tests))
    elif 'тест' in check.lower() or 'EditMode' in check:
        tags.append('тест')
    if not tags:
        tags.append('глазами' if 'глазами' in check else 'замер разово')
    return '; '.join(tags)


def show_area(area, entries, rows, full=False):
    if area not in AREAS:
        print(f'неизвестная область «{area}»; есть:', ', '.join(AREAS))
        return 1
    if full:
        return show_area_full(area, entries, rows)
    print(f'=== {area}: {AREAS[area]}')
    inv = [r for r in rows if area in r['areas']]
    hits = [e for e in entries if area in e['areas']]
    rules, files, tests, eyes = set(), set(), set(), 0
    for r in inv:
        rules.update(RULE_NO.findall(r['check']))
        files.update(f for f in PROBE_PATH.findall(r['check']) if f.split('/')[-1] != 'invariants_play.py' and is_probe_ref(f))
        tests.update(TEST_NAME.findall(r['check']))
        if not RULE_NO.findall(r['check']) and not PROBE_FILE.findall(r['check']) and not TEST_NAME.findall(r['check']):
            eyes += 1
    print('--- Чем проверить сейчас')
    probes = str(REG / 'probes')
    if area in DROP_AREAS:
        print(f'  python3 {probes}/transfer_probe.py --run      # крит-сценарий Ильи: взять → нести → на землю → на плоскость → взять снова (свой play)')
    if rules:
        nums = ','.join(sorted(rules, key=lambda r: int(re.match(r'\d+', r).group())))
        print(f'  python3 {probes}/invariants_play.py           # правила {nums}; читать три части «счётчики :: жалобы :: не проверялось»')
    for f in sorted(files, key=lambda x: x.split('/')[-1]):
        name = f.split('/')[-1]
        shown = probes + '/' + name if (REG / 'probes' / name).exists() else str(PROJECT / f) if (PROJECT / f).exists() else f
        kind = 'python3 ' if name.endswith('.py') else 'execute_code ← '
        print(f'  {kind}{shown}' + ('' if probe_exists(f) else '   # ⚠ файла нет на диске'))
    if tests:
        print('  EditMode: ' + ', '.join(sorted(tests)) + '   (python3 ' + probes + '/cycle.py tests — вне play)')
    print(f'  python3 {probes}/check_all.py                 # всё разом после правки')
    if eyes:
        print(f'  ⚠ {eyes} инвариант(ов) области держатся только глазами или разовым замером — см. строки ниже')
    print(f'--- Инварианты ({len(inv)}) — одной строкой; целиком: bugs.py <номер>')
    for r in inv:
        refs = ' ' + ','.join(r['refs']) if r['refs'] else ''
        print(f" {r['n']:>3}. {headline(r['rule'])}  [{check_tag(r['check'])}]{refs}")
    print(f'--- Грабли ({len(hits)}) — заголовки; целиком: bugs.py P###, все правила: --full')
    for e in hits:
        tag = '' if e['areas'][0] == area else f" (главная: {e['areas'][0]})"
        print(f"{e['id']} {e['title']}{tag}")
    return 0


def show_area_full(area, entries, rows):
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


def show_invariant(n, rows):
    for r in rows:
        if r['n'] == n:
            print(f"инвариант {n} · {', '.join(r['areas'])}")
            print('  ' + r['rule'])
            print('  Чем проверяется: ' + r['check'])
            print('  Грабли: ' + (', '.join(r['refs']) or '—') + '; ломалось: ' + (r['broke'] or '—'))
            return 0
    print(f'инварианта {n} нет')
    return 1


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
    if arg.isdigit():
        sys.exit(show_invariant(int(arg), rows))
    sys.exit(show_area(arg, entries, rows, full='--full' in sys.argv))


if __name__ == '__main__':
    main()
