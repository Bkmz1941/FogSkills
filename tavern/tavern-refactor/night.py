"""Ночной рефакторинг одной командой: метрики кода, кадр в сборке, точки отката без коммитов.

python3 night.py metrics [--save]                 размер базы, длинные методы, большие классы, повторы;
                                                  --save дописывает строку в METRICS.md
python3 night.py fps [уровни…] [--dev] [--no-build] [--frames N] [--runs N] [--save «заметка»]
                                                  собрать прод (или дев) сборку и померить кадр на уровнях
                                                  ключом -level, НЕ трогая уровень редактора;
                                                  по умолчанию все живые сейвы из папки уровней
python3 night.py verify <метка>                   ОБЕ половины проверки одной командой: stop → компиляция → тесты →
                                                  play → 15 с → живые пробы → отпечаток панели дебага → правила стычки;
                                                  `verify base` снимает базу ночи, любая другая метка сверяется с ней
python3 night.py report                           отчёт утром: кадр и код «база ночи → после ночи» из METRICS.md, шаги ночи
python3 night.py step begin <имя> <файлы…>        открыть шаг: запомнить файлы (чужой грязный — отказ)
python3 night.py step add <файлы…>                добавить файлы в открытый шаг
python3 night.py step end «что сделано»           закрыть шаг: патч в .git/night/, строка в журнале
python3 night.py step undo                        откатить последний закрытый шаг (если файлы не менялись после)
python3 night.py step drop                        бросить открытый шаг, вернув файлы как были на begin
python3 night.py step list                        шаги ночи
python3 night.py step commit                      ⛔ ТОЛЬКО по команде Ильи: закоммитить шаги по одному
python3 night.py step archive                     начать новую ночь: шаги и патчи прошлой — в .git/night/<дата>/

Коммитить без слова Ильи нельзя (CLAUDE.md, 15.09), поэтому точка отката — шаг: снимок файлов
в объектах git до и после, патч рядом. Утром «коммить» превращается в историю по шагам.
"""
import datetime, hashlib, json, os, pathlib, re, signal, subprocess, sys, time

PROJECT = pathlib.Path('/media/ilya/T714/Unity/Tavern-fresh')
SKILL = pathlib.Path(__file__).resolve().parent
METRICS = SKILL / 'METRICS.md'
NIGHT = PROJECT / '.git' / 'night'
STEPS = NIGHT / 'steps.json'
LEVELS = pathlib.Path.home() / '.config/unity3d/DefaultCompany/Tavern/levels'
MCP = pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py'
CYCLE = pathlib.Path.home() / '.claude/skills/tavern-regress/probes/cycle.py'
SCRATCH = NIGHT / 'fps'


def git(*args, check=True, env=None, text=True):
    out = subprocess.run(['git', *args], cwd=PROJECT, capture_output=True, text=text, env=env)
    if check and out.returncode != 0:
        raise SystemExit('git %s: %s' % (' '.join(args), out.stderr.strip()))
    return out.stdout.strip() if text else out.stdout


# ---------------------------------------------------------------- метрики кода

TYPE_RE = re.compile(r'\b(class|struct|interface|record|enum)\s+(\w+)')
SKIP_DUP = re.compile(r'^(\{|\}|\};|\);|using .*;|namespace .*|else|break;|return;|continue;|default:|\[.*\])$')


def strip_code(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        nx = src[i + 1] if i + 1 < n else ''
        if c == '/' and nx == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j; continue
        if c == '/' and nx == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', src[i:j])); i = j; continue
        if c == '"' or (c in '@$' and nx == '"') or (c in '@$' and nx in '@$' and i + 2 < n and src[i + 2] == '"'):
            k = i
            verbatim = False
            while src[k] != '"':
                verbatim |= src[k] == '@'
                k += 1
            if src.startswith('"""', k):
                j = src.find('"""', k + 3)
                j = n if j < 0 else j + 3
            else:
                j = k + 1
                while j < n:
                    if verbatim and src[j] == '"' and j + 1 < n and src[j + 1] == '"':
                        j += 2; continue
                    if not verbatim and src[j] == '\\':
                        j += 2; continue
                    if src[j] == '"' or (not verbatim and src[j] == '\n'):
                        j += 1; break
                    j += 1
            out.append('""' + re.sub(r'[^\n]', ' ', src[i:j])[2:]); i = j; continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'" and src[j] != '\n':
                j += 2 if src[j] == '\\' else 1
            j = min(j + 1, n)
            out.append("''" + ' ' * max(0, j - i - 2)); i = j; continue
        out.append(c); i += 1
    return ''.join(out)


def classify(header, parent):
    h = re.sub(r'^\s*(\[[^\]]*\]\s*)+', '', header).strip()
    if h.startswith('namespace') or re.match(r'^namespace\b', h):
        return 'ns', None
    m = TYPE_RE.search(h)
    if m and '(' not in h[:m.start()] and '=' not in h[:m.start()]:
        return 'type', m.group(2)
    if parent != 'type':
        return 'block', None
    if '=>' in h or '(' not in h:
        return 'member', None
    depth, eq = 0, False
    for ch in h:
        if ch in '(<[':
            depth += 1
        elif ch in ')>]':
            depth -= 1
        elif ch == '=' and depth == 0:
            eq = True
    if eq:
        return 'member', None
    name = re.search(r'([\w.~]+)\s*(<[^()]*>)?\s*\(', h)
    return 'method', (name.group(1) if name else h[:40])


def scan_file(path):
    src = path.read_text(encoding='utf-8', errors='replace')
    code = strip_code(src)
    methods, types = [], []
    stack = []
    header_start = 0
    line = 1
    for i, ch in enumerate(code):
        if ch == '\n':
            line += 1
            continue
        if ch in ';{}':
            if ch == '{':
                header = code[header_start:i]
                lead = len(header) - len(header.lstrip())
                start_line = line - header.count('\n') + header[:lead].count('\n')
                parent = stack[-1][0] if stack else None
                kind, name = classify(header, parent)
                stack.append((kind, name, start_line))
            elif ch == '}' and stack:
                kind, name, start_line = stack.pop()
                length = line - start_line + 1
                if kind == 'method':
                    owner = next((s[1] for s in reversed(stack) if s[0] == 'type'), '?')
                    methods.append((length, '%s.%s' % (owner, name), path, start_line))
                elif kind == 'type' and not any(s[0] == 'type' for s in stack):
                    types.append((name, length))
            header_start = i + 1
    return methods, types, src.count('\n') + 1, src.splitlines()


def cs_files():
    return sorted(p for p in (PROJECT / 'Assets').rglob('*.cs') if '/Tests/' not in str(p))


def duplicates(texts, window=8, repeats=3):
    seen = {}
    sig_lines = {}
    for path, lines in texts.items():
        sig = [(i + 1, l.strip()) for i, l in enumerate(lines)]
        sig = [(n, s) for n, s in sig if s and not s.startswith('//') and not SKIP_DUP.match(s)]
        sig_lines[path] = sig
        for k in range(len(sig) - window + 1):
            key = hashlib.md5('\n'.join(s for _, s in sig[k:k + window]).encode()).hexdigest()
            seen.setdefault(key, []).append((path, k))
    hot = {key: occ for key, occ in seen.items() if len(occ) >= repeats}
    marks = set()
    for occ in hot.values():
        path, k = occ[0]
        marks.add((path, k, len(occ)))
    groups = []
    for path, k, count in sorted(marks, key=lambda m: (str(m[0]), m[1])):
        if groups and groups[-1][0] == path and groups[-1][2] == k - 1 and groups[-1][3] == count:
            groups[-1][2] = k
            continue
        groups.append([path, k, k, count])
    result = []
    for path, a, b, count in groups:
        sig = sig_lines[path]
        result.append((count, b - a + window, path, sig[a][0]))
    return sorted(result, key=lambda g: (-g[1] * g[0]))


def rel(path):
    return str(path).replace(str(PROJECT) + '/', '')


def metrics(save):
    files = cs_files()
    all_methods, classes, total, texts = [], {}, 0, {}
    for f in files:
        methods, types, lines, text = scan_file(f)
        all_methods += methods
        total += lines
        texts[f] = text
        for name, length in types:
            entry = classes.setdefault(name, [0, 0])
            entry[0] += length
            entry[1] += 1
    all_methods.sort(key=lambda m: -m[0])
    over60 = [m for m in all_methods if m[0] > 60]
    over100 = [m for m in all_methods if m[0] > 100]
    dups = duplicates(texts)
    biggest = sorted(((len(t), f) for f, t in texts.items()), reverse=True)[:12]
    print('C# без тестов: %d файлов, %d строк; методов %d' % (len(files), total, len(all_methods)))
    print('методов > 60 строк: %d, > 100: %d' % (len(over60), len(over100)))
    print('\n--- самые длинные методы')
    for length, name, path, line in all_methods[:25]:
        print('%4d  %-55s %s:%d' % (length, name, rel(path), line))
    print('\n--- самые большие файлы')
    for length, path in biggest:
        print('%5d  %s' % (length, rel(path)))
    print('\n--- самые большие классы (сумма партиалов)')
    for name, (length, parts) in sorted(classes.items(), key=lambda c: -c[1][0])[:12]:
        print('%5d  %-30s партиалов %d' % (length, name, parts))
    print('\n--- повторы: блоки ≥8 значимых строк, встреченные ≥3 раз (%d групп)' % len(dups))
    for count, length, path, line in dups[:15]:
        print('  ×%d  %d строк  %s:%d' % (count, length, rel(path), line))
    if save:
        top = all_methods[0]
        row = '| %s | %s | %d | %d | %d | %d | %s %d | %d | %s |' % (
            datetime.date.today().isoformat(), save_who(), len(files), total, len(over60), len(over100),
            top[1], top[0], len(dups), save if isinstance(save, str) else '')
        append_row('## Код', row)
        print('\nстрока записана в', METRICS)


def save_who():
    return os.environ.get('NIGHT_WHO', '—')


def append_row(section, row):
    lines = METRICS.read_text(encoding='utf-8').splitlines()
    at = lines.index(section)
    end = at + 1
    while end < len(lines) and not lines[end].startswith('## '):
        end += 1
    last = max(i for i in range(at, end) if lines[i].startswith('|'))
    lines.insert(last + 1, row)
    METRICS.write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------- кадр в сборке

def mcp_run(code):
    out = subprocess.run(['python3', str(MCP), 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        return (json.loads(line).get('data') or {}).get('result')
    except Exception:
        return None


def build(dev):
    marker = 'linux' if dev else 'linux_prod'
    req = PROJECT / 'BuildRequests' / (marker + '.request')
    playing = str(mcp_run('return UnityEngine.Application.isPlaying;')).lower().startswith('t')
    if playing:
        print('редактор в play — выхожу, сборка в play не идёт')
        subprocess.run(['python3', str(CYCLE), 'stop'], timeout=180)
    started = time.time()
    req.parent.mkdir(exist_ok=True)
    req.write_text('night.py\n')
    print('сборка %s: жду вотчер редактора…' % ('дев' if dev else 'прод'), flush=True)
    for _ in range(900):
        for suffix in ('.done', '.failed'):
            f = PROJECT / 'BuildRequests' / (marker + suffix)
            if f.exists() and f.stat().st_mtime > started:
                text = f.read_text().strip()
                print('сборка:', text)
                return suffix == '.done'
        time.sleep(2)
    print('сборка не закончилась за 30 минут')
    return False


def live_levels():
    return sorted(p.stem for p in LEVELS.glob('*.json'))


def measure(exe, level, frames):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    log = SCRATCH / ('%s.log' % re.sub(r'\W+', '_', level))
    if log.exists():
        log.unlink()
    proc = subprocess.Popen([str(exe), '-gcprobe', str(frames), '-level', level, '-loadtiming', '-screen-fullscreen', '0',
                             '-screen-width', '1280', '-screen-height', '720', '-logFile', str(log)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    result, loaded = None, None
    started = time.time()
    START.clear()
    try:
        for _ in range(240):
            time.sleep(0.5)
            sample_rss(proc.pid)
            if not log.exists():
                continue
            text = log.read_text(errors='replace')
            m = re.search(r'\[level\] (.+)', text)
            if m:
                loaded = m.group(1).strip()
                START.setdefault('level_s', round(time.time() - started, 1))
            m = re.search(r'RestoreLevel (\d+) мс', text)
            if m:
                START['restore_ms'] = int(m.group(1))
            m = re.search(r'\[boot\] t=(\S+) frame=(\d+)', text)
            if m:
                START['boot_s'] = float(m.group(1))
            m = re.search(r'\[mem\] (.+)', text)
            if m:
                START['mem'] = m.group(1).strip()
            m = re.search(r'\[gc\] (avg=\S+ max=\S+ frames=\S+ ms=\S+ p95=\S+ msmax=\S+)', text)
            if m:
                result = dict(p.split('=') for p in m.group(1).split())
                START['phases'] = phases_of(text)
                break
            if proc.poll() is not None:
                break
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
    return result, loaded


START = {}


def sample_rss(pid):
    try:
        for line in open('/proc/%d/status' % pid):
            if line.startswith('VmRSS:'):
                START['rss_mb'] = int(line.split()[1]) // 1024
            elif line.startswith('VmHWM:'):
                START['peak_mb'] = int(line.split()[1]) // 1024
    except OSError:
        pass


def phases_of(text):
    m = re.search(r'RestoreLevel \d+ мс\n((?:  \S+ +[\d.]+ мс\n)+)', text)
    if not m:
        return ''
    rows = re.findall(r'  (\S+) +([\d.]+) мс', m.group(1))
    rows.sort(key=lambda r: -float(r[1]))
    return ' '.join('%s=%s' % (n, v) for n, v in rows[:4])


def fps(args):
    dev = '--dev' in args
    frames, runs, note = 600, 2, None
    levels = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--frames':
            frames = int(args[i + 1]); i += 2; continue
        if a == '--runs':
            runs = int(args[i + 1]); i += 2; continue
        if a == '--save':
            note = args[i + 1] if i + 1 < len(args) and not args[i + 1].startswith('--') else ''
            i += 2 if note else 1
            continue
        if not a.startswith('--'):
            levels.append(a)
        i += 1
    levels = levels or live_levels()
    if '--no-build' not in args:
        print('СБОРКА ЗАПРЕЩЕНА: Илья 27.09 — «пока в редакторе всегда работаем», сборку он не просил. '
              'Собирать игру только по его прямой команде; замер кадра — по готовой сборке с --no-build или в редакторе.')
        return 1
    exe = PROJECT / 'Builds' / ('Linux' if dev else 'LinuxProd') / 'Tavern.x86_64'
    kind = 'дев' if dev else 'прод'
    rows = []
    starts = []
    print('\n%-12s %-6s %8s %7s %7s %9s %6s' % ('уровень', 'прогон', 'кадр мс', 'p95', 'пик', 'мусор Б', 'FPS'))
    for level in levels:
        got = []
        for r in range(runs):
            res, loaded = measure(exe, level, frames)
            if not res:
                print('%-12s %-6d нет строки [gc] — смотри %s' % (level, r + 1, SCRATCH))
                continue
            if loaded and loaded != level:
                print('%-12s открылся ДРУГОЙ уровень: %s — замер не считается' % (level, loaded))
                continue
            ms, p95, mx, avg = float(res['ms']), float(res['p95']), float(res['msmax']), int(res['avg'])
            got.append((ms, p95, mx, avg))
            print('%-12s %-6d %8.2f %7.2f %7.2f %9d %6.0f' % (level, r + 1, ms, p95, mx, avg, 1000 / ms), flush=True)
            start = dict(START)
            starts.append((level, start))
            print('%-12s        старт: уровень через %s с, загрузка %s мс (%s), кадр [gc] на %s с; RSS %s МБ, пик %s МБ' % (
                '', start.get('level_s', '?'), start.get('restore_ms', '?'), start.get('phases', '—'),
                start.get('boot_s', '?'), start.get('rss_mb', '?'), start.get('peak_mb', '?')), flush=True)
            if start.get('mem'):
                print('%-12s        память: %s' % ('', start['mem']), flush=True)
        if got:
            ms = sum(g[0] for g in got) / len(got)
            p95 = sum(g[1] for g in got) / len(got)
            mx = max(g[2] for g in got)
            avg = sum(g[3] for g in got) // len(got)
            rows.append((level, ms, p95, mx, avg))
    if note is not None and rows:
        commit = git('rev-parse', '--short', 'HEAD')
        dirty = len([l for l in git('status', '--porcelain').splitlines() if l.strip()])
        for level, ms, p95, mx, avg in rows:
            append_row('## Кадр в сборке', '| %s | %s | %s | %s | %.2f | %.2f | %.2f | %d | %.0f | %s+%d | %s |' % (
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), save_who(), kind, level, ms, p95, mx, avg,
                1000 / ms, commit, dirty, note))
        seen = set()
        for level, start in starts:
            if level in seen or 'restore_ms' not in start:
                continue
            seen.add(level)
            append_row('## Старт и память в сборке', '| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s+%d | %s |' % (
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), save_who(), kind, level,
                start.get('level_s', '?'), start.get('restore_ms', '?'), start.get('boot_s', '?'),
                start.get('peak_mb', '?'), start.get('rss_mb', '?'), start.get('mem', '—').replace('|', '/'), commit, dirty, note))
        print('\nстроки записаны в', METRICS)
    return 0


# ---------------------------------------------------------------- проверка шага

REG = pathlib.Path.home() / '.claude/skills/tavern-regress/probes'
PROBES = NIGHT / 'probe'
SETTLE = 15


def sh(args, timeout=900):
    out = subprocess.run(['python3', *[str(a) for a in args]], capture_output=True, text=True, timeout=timeout, cwd=PROJECT)
    return out.stdout + out.stderr


SLEEPING = re.compile(r' :: НЕЧЕГО БЫЛО ПРОВЕРЯТЬ[^:]*(?=( :: |$))')


def stable(lines):
    return [SLEEPING.sub('', l) for l in lines if not l.startswith('gc_probe.py:') and not l.startswith('редактор:')]


def level_now():
    """Уровень, открытый в редакторе: у живых проб и отпечатков база СВОЯ на каждый
    уровень. Ночью 17→18.09 Илья сменил уровень после `verify base`, и все следующие
    шаги краснели на «живых пробах» не по своей вине (327 объектов против 378)."""
    out = sh([CYCLE, 'status'], 60)
    m = re.search(r'уровень=(.*?) стартовый=', out)
    name = (m.group(1).strip() if m else '') or 'без_уровня'
    return re.sub(r'[^0-9A-Za-zА-Яа-яЁё_#-]+', '_', name)


def compare(name, label, text):
    PROBES.mkdir(parents=True, exist_ok=True)
    (PROBES / ('%s_%s.txt' % (name, label))).write_text(text)
    level = level_now()
    base = PROBES / ('%s_base@%s.txt' % (name, level))
    if label == 'base' or not base.exists():
        base.write_text(text)
        return None, ('база записана (%s)' % level) if label == 'base' else ('базы для уровня «%s» не было — записана сейчас, сверка со следующего шага' % level)
    a = stable(base.read_text().splitlines())
    b = stable(text.splitlines())
    if a == b:
        return True, 'совпало (%d строк)' % len(b)
    import difflib
    delta = [d for d in difflib.unified_diff(a, b, lineterm='', n=0) if d[:1] in '+-' and d[:3] not in ('+++', '---')]
    return False, 'РАСХОЖДЕНИЕ %d строк: %s' % (len(delta), ' | '.join(delta[:6])[:600])


def verify(args):
    label = args[0] if args else datetime.datetime.now().strftime('%H%M')
    rows = []

    def row(name, ok, text):
        mark = '✅' if ok else ('❌' if ok is False else '➖')
        rows.append('%s %-14s %s' % (mark, name, text))
        print(rows[-1], flush=True)

    sh([CYCLE, 'stop'], 300)
    out = sh([CYCLE, 'compile'])
    ok = 'ошибок CS в консоли: 0' in out
    row('компиляция', ok, out.strip().splitlines()[-1] if out.strip() else 'нет ответа')
    if not ok:
        return 1
    out = sh([CYCLE, 'tests'])
    tail = [l for l in out.strip().splitlines() if l.strip()]
    row('тесты', 'красных 0' in out, ' '.join(tail[-3:])[:300])
    out = sh([CYCLE, 'play'], 300)
    row('play', 'вошли' in out, out.strip().splitlines()[-1] if out.strip() else 'нет ответа')
    if 'вошли' not in out:
        # Сосед остановил play посреди цепочки (ночь 17→18.09): пробы по мёртвому
        # редактору дают мусор, который выглядит как регрессия шага.
        print('ИТОГ: ЦЕПОЧКА СОРВАНА — play не поднялся (чужой stop или компиляция); пробы не гонялись, повторить verify')
        return 2
    time.sleep(SETTLE)
    out = sh([REG / 'check_all.py'])
    if 'play=True' not in sh([CYCLE, 'status'], 60):
        print('ИТОГ: ЦЕПОЧКА СОРВАНА — play выключили во время живых проб; сверка не делалась, повторить verify')
        return 2
    live = [l for l in out.splitlines() if l.split(':')[0].endswith('.py')]
    ok, text = compare('check', label, '\n'.join(live))
    red = [l for l in live if 'КРАСНОЕ' in l or 'ЗАЩИТА МЕРТВА' in l]
    row('живые пробы', (ok is not False) and not red, text if not red else '; '.join(red)[:600])
    out = sh([REG / 'debug_panel_probe.py', 'snap', 'night_' + label], 600)
    snap = pathlib.Path.home() / '.cache/tavern-probes' / ('debug_panel_night_%s.txt' % label)
    ok, text = compare('debug_panel', label, snap.read_text() if snap.exists() else out)
    row('панель дебага', ok, text)
    out = sh([REG / 'encounter_probe.py', 'rules'], 300)
    ok, text = compare('encounter_rules', label, out)
    row('правила стычки', ok, text)
    bad = [r for r in rows if r.startswith('❌')]
    print('ИТОГ:', 'зелёное' if not bad else 'КРАСНОЕ — %d' % len(bad))
    return 1 if bad else 0


# ---------------------------------------------------------------- отчёт

def table_rows(section):
    lines = METRICS.read_text(encoding='utf-8').splitlines()
    at = lines.index(section)
    rows = []
    for l in lines[at + 1:]:
        if l.startswith('## '):
            break
        if l.startswith('|') and not l.startswith('|---') and not l.startswith('| когда') and not l.startswith('| дата'):
            rows.append([c.strip() for c in l.strip('|').split('|')])
    return rows


def report(args):
    today = args[0] if args else datetime.date.today().isoformat()
    fps_rows = [r for r in table_rows('## Кадр в сборке') if r[0].startswith(today)]
    code_rows = [r for r in table_rows('## Код') if r[0].startswith(today)]
    print('## Кадр в сборке, %s' % today)
    by = {}
    for r in fps_rows:
        by.setdefault((r[2], r[3]), []).append(r)
    for (kind, level), rs in sorted(by.items()):
        first, last = rs[0], rs[-1]
        if first is last:
            print('- %s %s: %s мс (%s FPS) — %s' % (kind, level, first[4], first[8], first[10]))
        else:
            print('- %s %s: %s → %s мс, FPS %s → %s (%s → %s)' % (kind, level, first[4], last[4], first[8], last[8], first[10], last[10]))
    print('\n## Код')
    if len(code_rows) >= 2:
        a, b = code_rows[0], code_rows[-1]
        print('- строк %s → %s, методов >60: %s → %s, >100: %s → %s, самый длинный: %s → %s' % (a[3], b[3], a[4], b[4], a[5], b[5], a[6], b[6]))
    elif code_rows:
        print('- ' + ' | '.join(code_rows[0]))
    steps = [s for s in load_steps() if s['status'] == 'done']
    print('\n## Шаги (%d, коммита нет — на «коммить»: `night.py step commit`)' % len(steps))
    for s in steps:
        print('%d. %s' % (s['n'], s.get('msg', s['name'])))
    rolled = [s for s in load_steps() if s['status'] in ('undone', 'dropped')]
    if rolled:
        print('\nОткачено: ' + '; '.join('%d %s' % (s['n'], s['name']) for s in rolled))
    return 0


# ---------------------------------------------------------------- шаги ночи

def load_steps():
    return json.loads(STEPS.read_text()) if STEPS.exists() else []


def save_steps(steps):
    NIGHT.mkdir(parents=True, exist_ok=True)
    STEPS.write_text(json.dumps(steps, ensure_ascii=False, indent=1))


def blob_now(path):
    full = PROJECT / path
    return git('hash-object', '-w', str(full)) if full.exists() else None


def blob_head(path):
    out = subprocess.run(['git', 'rev-parse', 'HEAD:' + path], cwd=PROJECT, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def mode_of(path):
    full = PROJECT / path
    return '100755' if full.exists() and os.access(full, os.X_OK) and full.suffix in ('.py', '.sh') else '100644'


def normalize(path):
    p = pathlib.Path(path)
    if p.is_absolute():
        p = p.resolve().relative_to(PROJECT)
    return str(p)


def mine_after(steps, path):
    for s in reversed(steps):
        if s['status'] == 'done' and path in s['files']:
            return s['files'][path]['after']
    return None


def claim(steps, step, paths, force):
    bad = []
    for raw in paths:
        path = normalize(raw)
        now = blob_now(path)
        clean = now == blob_head(path)
        mine = now is not None and now == mine_after(steps, path)
        if not (clean or mine or force):
            bad.append(path)
            continue
        step['files'][path] = {'before': now, 'after': None, 'mode': mode_of(path)}
        if path.endswith('.cs') and now is None:
            meta = path + '.meta'
            step['files'].setdefault(meta, {'before': None, 'after': None, 'mode': '100644'})
    return bad


def step_patch(step):
    env = dict(os.environ, GIT_INDEX_FILE=str(NIGHT / 'index.tmp'))
    subprocess.run(['git', 'read-tree', 'HEAD'], cwd=PROJECT, env=env, check=True)
    for path, f in step['files'].items():
        if f['before']:
            subprocess.run(['git', 'update-index', '--add', '--cacheinfo', '%s,%s,%s' % (f['mode'], f['before'], path)],
                           cwd=PROJECT, env=env, check=True)
        else:
            subprocess.run(['git', 'update-index', '--force-remove', path], cwd=PROJECT, env=env, check=True)
    paths = list(step['files'])
    subprocess.run(['git', 'add', '--intent-to-add', '--', *[p for p in paths if (PROJECT / p).exists()]],
                   cwd=PROJECT, env=env, check=False, capture_output=True)
    patch = subprocess.run(['git', 'diff', '--binary', '--', *paths], cwd=PROJECT, env=env,
                           capture_output=True, text=True).stdout
    stat = subprocess.run(['git', 'diff', '--stat', '--', *paths], cwd=PROJECT, env=env,
                          capture_output=True, text=True).stdout
    (NIGHT / 'index.tmp').unlink(missing_ok=True)
    return patch, stat


def restore(path, blob):
    full = PROJECT / path
    if blob is None:
        full.unlink(missing_ok=True)
        return
    full.write_bytes(git('cat-file', 'blob', blob, text=False))


def step(args):
    if not args:
        print(__doc__); return 1
    cmd, rest = args[0], args[1:]
    steps = load_steps()
    opened = next((s for s in steps if s['status'] == 'open'), None)
    force = '--force' in rest
    rest = [r for r in rest if r != '--force']
    if cmd == 'begin':
        if opened:
            raise SystemExit('шаг «%s» ещё открыт: step end или step drop' % opened['name'])
        if len(rest) < 2:
            raise SystemExit('step begin <имя> <файлы…>')
        new = {'n': len(steps) + 1, 'name': rest[0], 'status': 'open', 'files': {},
               'started': datetime.datetime.now().isoformat(timespec='minutes'), 'head': git('rev-parse', 'HEAD')}
        bad = claim(steps, new, rest[1:], force)
        if bad:
            raise SystemExit('шаг не открыт — файлы грязные и не мои (чужая правка?): ' + ', '.join(bad))
        steps.append(new)
        save_steps(steps)
        print('шаг %d «%s» открыт: %s' % (new['n'], new['name'], ', '.join(new['files'])))
        return 0
    if cmd == 'add':
        if not opened:
            raise SystemExit('открытого шага нет')
        bad = claim(steps, opened, rest, force)
        if bad:
            raise SystemExit('не добавлены — грязные и не мои: ' + ', '.join(bad))
        save_steps(steps)
        print('в шаге %d: %s' % (opened['n'], ', '.join(opened['files'])))
        return 0
    if cmd == 'end':
        if not opened:
            raise SystemExit('открытого шага нет')
        opened['msg'] = ' '.join(rest) or opened['name']
        for path, f in opened['files'].items():
            f['after'] = blob_now(path)
        opened['files'] = {p: f for p, f in opened['files'].items() if f['before'] != f['after']}
        if not opened['files']:
            steps.remove(opened)
            save_steps(steps)
            print('шаг ничего не изменил — выброшен')
            return 0
        patch, stat = step_patch(opened)
        name = '%02d-%s.patch' % (opened['n'], re.sub(r'[^\w-]+', '_', opened['name']))
        (NIGHT / name).write_text(patch)
        opened['patch'] = name
        opened['status'] = 'done'
        opened['ended'] = datetime.datetime.now().isoformat(timespec='minutes')
        save_steps(steps)
        print('шаг %d закрыт → .git/night/%s\n%s' % (opened['n'], name, stat))
        return 0
    if cmd in ('undo', 'drop'):
        target = opened if cmd == 'drop' else next((s for s in reversed(steps) if s['status'] == 'done'), None)
        if not target:
            raise SystemExit('нечего откатывать')
        for path, f in target['files'].items():
            now = blob_now(path)
            if cmd == 'undo' and now != f['after']:
                raise SystemExit('%s менялся после шага — откатывать руками по патчу %s' % (path, target.get('patch')))
        for path, f in target['files'].items():
            restore(path, f['before'])
        target['status'] = 'undone' if cmd == 'undo' else 'dropped'
        save_steps(steps)
        print('шаг %d «%s» откачен: %s' % (target['n'], target['name'], ', '.join(target['files'])))
        return 0
    if cmd == 'list':
        for s in steps:
            print('%2d  %-8s %-40s %s  %s' % (s['n'], s['status'], s['name'][:40], s.get('ended', s['started']),
                                            ', '.join(pathlib.Path(p).name for p in s['files'])))
            if s.get('msg'):
                print('    ', s['msg'])
        return 0
    if cmd == 'archive':
        if opened:
            raise SystemExit('шаг «%s» ещё открыт: step end или step drop' % opened['name'])
        if not steps:
            print('архивировать нечего')
            return 0
        stamp = (steps[0].get('started') or datetime.datetime.now().isoformat(timespec='minutes')).replace(':', '')
        folder = NIGHT / stamp
        folder.mkdir(parents=True, exist_ok=True)
        for s_ in steps:
            if s_.get('patch') and (NIGHT / s_['patch']).exists():
                (NIGHT / s_['patch']).rename(folder / s_['patch'])
        STEPS.rename(folder / 'steps.json')
        waiting = [s_ for s_ in steps if s_['status'] == 'done' and not s_.get('commit')]
        print('ночь %s в архиве: шагов %d, из них не закоммичено %d%s' % (
            stamp, len(steps), len(waiting), ' — их правки остаются в рабочем дереве' if waiting else ''))
        return 0
    if cmd == 'commit':
        if git('diff', '--cached', '--name-only'):
            raise SystemExit('в индексе уже что-то лежит — сначала разобраться, чьё это')
        todo = [s for s in steps if s['status'] == 'done' and not s.get('commit')]
        for s in todo:
            for path, f in s['files'].items():
                head = blob_head(path)
                if head != f['before']:
                    raise SystemExit('шаг %d: %s в HEAD не совпадает со снимком «до» — коммит по шагам не собрать'
                                     % (s['n'], path))
                if f['after']:
                    git('update-index', '--add', '--cacheinfo', '%s,%s,%s' % (f['mode'], f['after'], path))
                else:
                    git('update-index', '--force-remove', path)
            msg = s['msg'] + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
            subprocess.run(['git', 'commit', '-q', '-m', msg], cwd=PROJECT, check=True)
            s['commit'] = git('rev-parse', '--short', 'HEAD')
            save_steps(steps)
            print('%s  %s' % (s['commit'], s['msg']))
        return 0
    print(__doc__)
    return 1


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 0
    if args[0] == 'metrics':
        rest = args[1:]
        save = False
        if '--save' in rest:
            k = rest.index('--save')
            save = rest[k + 1] if k + 1 < len(rest) else True
        metrics(save)
        return 0
    if args[0] == 'fps':
        return fps(args[1:])
    if args[0] == 'step':
        return step(args[1:])
    if args[0] == 'verify':
        return verify(args[1:])
    if args[0] == 'report':
        return report(args[1:])
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
