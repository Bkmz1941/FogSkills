"""Один прогон: линт граблей, компиляция, тесты EditMode, живые пробы (инварианты, крит-сценарий «положить», круг сейва, позы, наклон, кадр). Печатает вердикт.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/check_all.py
"""
import json, re, pathlib, subprocess, sys, time

GAME = '/home/ilya/.claude/skills/tavern-game'
REG = '/home/ilya/.claude/skills/tavern-regress'
MCP = GAME + '/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'


def mcp(tool, payload):
    out = subprocess.run(['python3', MCP, tool, json.dumps(payload)],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        return json.loads(line)
    except Exception:
        return {}


def editor_state():
    d = mcp('execute_code', {"action": "execute", "code":
            'return UnityEngine.Application.isPlaying + "|" + UnityEditor.EditorApplication.isCompiling;'})
    res = (d.get('data') or {}).get('result') or '|'
    play, comp = (res.split('|') + ['', ''])[:2]
    return play.lower().startswith('t'), comp.lower().startswith('t')


def lint():
    out = subprocess.run(['python3', REG + '/probes/bugs.py', '--lint'],
                         capture_output=True, text=True, timeout=60)
    tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
    print('грабли:', tail[-1] if tail else 'нет ответа')
    for line in tail:
        if 'КРАСНОЕ' in line:
            print('   ', line.strip())
    return out.returncode == 0


def probes_lint():
    out = subprocess.run(['python3', REG + '/probes/probes_lint.py'], capture_output=True, text=True, timeout=60)
    lines = [l for l in out.stdout.strip().split('\n') if l.strip()]
    print('ссылки проб:', lines[-1] if lines else 'нет ответа')
    for line in lines[:-1]:
        print('   ', line[:300])
    return out.returncode == 0


# ⭐ 22.10 (ilya-de, P1198): шаблонный `[Bb]uild/` в .gitignore прятал Assets/Modules/Grid/Build — новые исходники
# не попадали в коммиты. Под Assets игнорируемых исходников быть не должно (кроме _Recovery и токена TelegramBot.json).
IGNORED_OK = ('Assets/_Recovery/', 'Assets/Game/Resources/TelegramBot.json')
SOURCE_EXT = ('.cs', '.shader', '.asmdef', '.json', '.fbx', '.png', '.prefab', '.asset', '.unity', '.meta')


def ignored_sources():
    out = subprocess.run(['git', 'status', '--ignored', '--short', '--', 'Assets'], capture_output=True, text=True, timeout=120, cwd=PROJECT)
    bad = []
    for line in out.stdout.splitlines():
        if not line.startswith('!!'):
            continue
        path = line[3:].strip().strip('"')
        if path.startswith(IGNORED_OK) or not path.endswith(SOURCE_EXT):
            continue
        bad.append(path)
    print('игнор под Assets:', 'ок' if not bad else 'КРАСНОЕ — %d файлов скрыты от коммита (P1198): %s' % (len(bad), ', '.join(bad[:6])))
    return not bad


def compile_check():
    out = subprocess.run(['python3', PROJECT + '/compile_check.py'],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    ok = 'КОМПИЛЯЦИЯ ЧИСТАЯ' in out.stdout
    print('компиляция:', 'чисто' if ok else 'ОШИБКИ')
    if not ok:
        for line in out.stdout.split('\n'):
            if 'FAIL' in line or 'error CS' in line:
                print('   ', line.strip()[:150])
    return ok


def tests():
    started = mcp('run_tests', {"mode": "EditMode"})
    job = (started.get('data') or {}).get('job_id')
    if not job:
        print('тесты: не стартовали —', (started.get('data') or {}).get('error') or started.get('message'))
        return None
    for _ in range(40):
        time.sleep(6)
        d = (mcp('get_test_job', {"job_id": job, "include_failed_tests": True}).get('data') or {})
        status = d.get('status')
        if status in ('succeeded', 'completed', 'failed'):
            fails = (d.get('progress') or {}).get('failures_so_far') or []
            done = (d.get('progress') or {}).get('completed')
            if status == 'failed' and not fails:
                print('тесты: не запустились —', d.get('error'))
                return None
            print(f'тесты: {done} прогнано, красных {len(fails)}')
            for f in fails:
                print('   ПРОВАЛ:', f['full_name'])
                print('      ', f['message'][:160].replace('\n', ' '))
            return not fails
    print('тесты: не дождался результата')
    return None


def restore_scene():
    """Тест-раннер уводит редактор на свою БЕЗЫМЯННУЮ сцену и не всегда возвращает
    игровую — даже когда прогон дошёл до конца (P309, повтор 12.09). Play на ней
    поднимает только синглтоны: ни уровня, ни HUD, ни персонажа."""
    d = mcp('execute_code', {"action": "execute", "code":
            'var sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene();'
            'if (UnityEngine.Application.isPlaying) return "play|" + sc.path;'
            'if (sc.path == "Assets/Scenes/level1.unity") return "ок|" + sc.path;'
            'if (sc.path != "") return "чужая|" + sc.path;'
            'var back = UnityEditor.SceneManagement.EditorSceneManager.OpenScene('
            '"Assets/Scenes/level1.unity", UnityEditor.SceneManagement.OpenSceneMode.Single);'
            'return "вернул|" + back.path;'})
    res = (d.get('data') or {}).get('result') or '|'
    state, path = (res.split('|') + ['', ''])[:2]
    if state == 'вернул':
        print('сцена: раннер оставил редактор на БЕЗЫМЯННОЙ пустой сцене — вернул', path, '(P309)')
    elif state == 'чужая':
        print('сцена: редактор на', path, '— не игровая, проверь перед play (P309)')
    elif state == 'play':
        print('сцена: редактор в play на', path or 'БЕЗЫМЯННОЙ — это P309, останови play и открой level1.unity')
    else:
        print('сцена: игровая, ок')
    return state in ('ок', 'вернул')


HERO_KIT = """if (!UnityEngine.Application.isPlaying) return "";
Cozy.Character.Equipment eq = null;
foreach (var e in UnityEngine.Object.FindObjectsByType<Cozy.Character.Equipment>(UnityEngine.FindObjectsSortMode.None)) if (e.IsPlayer) eq = e;
if (eq == null) return "";
var sb = new System.Text.StringBuilder("руки:");
foreach (var it in eq.Pockets.Items) sb.Append(" " + it.def.id + "@" + it.anchor.x + "," + it.anchor.y);
sb.Append(" | надето:");
foreach (Cozy.Grid.EquipSlot slot in System.Enum.GetValues(typeof(Cozy.Grid.EquipSlot))) { var d = eq.Get(slot); if (d != null) sb.Append(" " + d.id); }
return sb.ToString();"""
_kit = {'was': None, 'leaks': []}


def hero_kit():
    out = subprocess.run(['python3', str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py'), 'execute_code',
                          json.dumps({'action': 'execute', 'code': HERO_KIT})], capture_output=True, text=True, timeout=120, cwd=PROJECT)
    lines = out.stdout.strip().splitlines()
    try:
        return str(((json.loads(lines[-1]) if lines else {}).get('data') or {}).get('result') or '')
    except Exception:
        return ''


# ⭐ 20.10 (ilya-61): после полного прогона руки героя оказались пустыми, фонарь лежал у ног, газета пропала —
# какая-то проба не вернула героя. Сторож сверяет руки и надетое после каждой пробы и называет первую виноватую.
def watch_hero(name):
    if _kit['was'] is None:
        return
    now = hero_kit()
    if now and now != _kit['was']:
        _kit['leaks'].append(name)
        print('герой: УТЕЧКА после ' + name + ' — было «' + _kit['was'] + '», стало «' + now + '»')
        _kit['was'] = now


def probe(name, *args):
    out = subprocess.run(['python3', REG + '/probes/' + name] + list(args),
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    tail = [l for l in out.stdout.strip().split('\n') if l.strip()]
    line = tail[-1] if tail else 'нет ответа'
    # ⭐ Жалобы живут ПОСЛЕ ' :: ', а счётчики перед ним занимают полтысячи
    # символов — прежний срез на 200 резал ровно то, ради чего проба и нужна.
    # 13.09 замерено: на forest100 счётчики 509 символов, значит check_all НИ
    # РАЗУ не показал ни одной жалобы инвариантов. Счётчики жмём, жалобы — нет.
    head, sep, rest = line.partition(' :: ')
    if sep:
        line = (head[:110] + '…' if len(head) > 110 else head) + ' :: ' + rest
    print(name + ':', line[:1400])
    watch_hero(name)
    return tail


def probe_cs(name, again=False):
    code = open(REG + '/probes/' + name).read()
    out = subprocess.run(['python3', str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py'), 'execute_code',
                          json.dumps({'action': 'execute', 'code': code})], capture_output=True, text=True, timeout=300, cwd=PROJECT)
    lines = out.stdout.strip().splitlines()
    try:
        d = json.loads(lines[-1]) if lines else {}
    except Exception:
        d = {}
    res = str((d.get('data') or {}).get('result') or d.get('message') or 'нет ответа')
    if res.startswith('ПОДГОТОВКА') and not again:
        print(name + ':', res)
        time.sleep(2.5)
        return probe_cs(name, again=True)
    print(name + ':', res[:1400])
    watch_hero(name)


def probe_cs_parts(name, parts=4):
    # ⭐ 19.10: проба по ВСЕМ предметам (inspect_window_probe.cs, 305 предметов) не укладывается в 120 с ответа
    # моста — «нет ответа», а редактор ещё минуты занят ею, и следующая проба тоже без ответа. Гоняем частями:
    # каждый K-й предмет после фильтра pickupItemId, части сводим в одну строку.
    code = open(REG + '/probes/' + name).read()
    key = 'if (def == null || string.IsNullOrEmpty(def.pickupItemId)) continue;'
    if key not in code or '\ntry\n' not in code:
        return probe_cs(name)
    total = 0
    fails = []
    for k in range(parts):
        part = code.replace(key, key + ' if ((_k++ %% %d) != %d) continue;' % (parts, k)).replace('\ntry\n', '\nint _k = 0;\ntry\n', 1)
        out = subprocess.run(['python3', str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py'), 'execute_code',
                              json.dumps({'action': 'execute', 'code': part})], capture_output=True, text=True, timeout=300, cwd=PROJECT)
        lines = out.stdout.strip().splitlines()
        try:
            d = json.loads(lines[-1]) if lines else {}
        except Exception:
            d = {}
        res = str((d.get('data') or {}).get('result') or d.get('message') or 'нет ответа')
        m = re.search(r'из (\d+)', res)
        total += int(m.group(1)) if m else 0
        if not res.startswith('ЗЕЛЁНОЕ'):
            fails.append('часть %d/%d: %s' % (k + 1, parts, res[:600]))
    if fails:
        print(name + ': КРАСНОЕ (частями по %d) — ' % parts + ' || '.join(fails)[:1400])
    else:
        print(name + ': ЗЕЛЁНОЕ из %d (частями по %d)' % (total, parts))
    watch_hero(name)


def main():
    print('=== проверка «всё, что работало, работает» ===')
    ok_lint = lint()
    ok_probes = probes_lint()
    ok_ignored = ignored_sources()
    ok_compile = compile_check()
    probe('export_facing_probe.py')
    play, compiling = editor_state()
    print('редактор: play =', play, ', компилируется =', compiling)
    ok_tests = None
    if not play:
        ok_tests = tests()
        restore_scene()
    else:
        print('тесты: пропущены — редактор в play')
    if play:
        _kit['was'] = hero_kit()
        print('герой до проб:', _kit['was'] or 'не прочитан')
        probe('invariants_play.py')
        probe('transfer_probe.py', '--run')
        probe('level_roundtrip.py')
        probe('posture_probe.py')
        probe('tilt_probe.py')
        probe('paint_strip_probe.py')
        probe('gc_probe.py', 'check')
        probe_cs('slot_wall_probe.cs')
        probe_cs('slot_open_probe.cs')
        probe_cs('build_pick_probe.cs')
        probe_cs('stairwell_view_probe.cs')
        probe_cs('crow_glow_probe.cs')
        probe_cs('box_place_probe.cs')
        probe_cs('wall_hang_probe.cs')
        probe_cs('rug_top_probe.cs')
        probe_cs('dirt_probe.cs')
        probe_cs('roof_snap_pick_probe.cs')
        probe_cs('product_card_probe.cs')
        # ⭐ 18.10 продукты и кухня (PRODUCTS.md, KITCHEN.md): Илья «крит важно, чтобы не ломалось»
        probe_cs('products_probe.cs')
        probe('products_probe.py')  # внутри и parts_motion_probe.cs (ящики, дверцы)
        probe_cs('product_look_probe.cs')
        probe_cs('product_collide_probe.cs')
        probe_cs('product_save_probe.cs')
        probe_cs('product_actions_probe.cs')
        probe_cs('product_wave2_probe.cs')
        # кухня (KITCHEN.md): части, питание и свет, постановка у стены (SKIP без дома), живая гора посуды
        probe_cs('kitchen_parts_probe.cs')
        probe_cs('kitchen_power_probe.cs')
        # свет (LIGHT.md): маски зон, «всегда горит», уличный, щиток, свечи и факелы, слой ламп уровня
        probe_cs('light_probe.cs')
        probe('candle_probe.py')  # свечи и спички (LIGHT.md §8, LI-CA…)
        probe_cs('candle_inside_probe.cs')  # свечи в тумбах и шкафах, подсвечники не внутрь (LI-CI…)
        probe_cs('kitchen_place_probe.cs')
        probe_cs('kitchen_pile_probe.cs')
        # одежда (CLOTHING.md): постановка на пол/стол/кровати/в шкафы/стопкой, надеть-снять-карманы-сейв
        probe_cs('clothes_place_probe.cs')
        probe_cs('clothes_wear_probe.cs')
        # окно «Предмет» (INVENTORY.md): кадр, ближняя плоскость, сетка не двигается и не касается, поворот-подставка, вид по умолчанию, галки — по всем предметам
        probe_cs_parts('inspect_window_probe.cs')
        probe_cs('hands_probe.cs')  # предметы в руках (HELD.md): клетка руки, риг, клетка в инвентаре, сейв рук (HD-…)
        probe_cs('inventory_doll_probe.cs')  # фигура игрока и попап «Предмет»: камера и сетка стоят, своя текстура сетки (INV-D…)
        probe_cs('kitchen_pile_pick_probe.cs')  # взять из горы посуды на голой мойке и на тумбах (P1142)
        probe_cs('place_false_red_probe.cs')  # ложное красное при перемещении на столешницах кухни (P1146)
        # двери, замки, ключи (DOORS.md): эталон замков 18.10 и логика ключей/дверей/дверец
        probe_cs('padlock_hang_probe.cs')
        probe_cs('doors_probe.cs')
        probe_cs('zombie_probe.cs')
        probe_cs('rooms_probe.cs')  # закрытые комнаты (ROOMS.md): флаг, скан HiddenRooms и закрытость независимым обходом, недоступность по AccessCells, крестики
        probe_cs('attack_reach_probe.cs')  # атака только дотянувшись: стена, окно, закрытая дверь, этаж (ZB-A…, P1174)
    else:
        print('живые пробы: пропущены — нужен play')
    print('=== итог ===')
    print('грабли:', 'ок' if ok_lint else 'КРАСНОЕ')
    print('игнор под Assets:', 'ок' if ok_ignored else 'КРАСНОЕ (P1198)')
    print('ссылки проб:', 'ок' if ok_probes else 'КРАСНОЕ — защита умерла, чинить пробу')
    print('компиляция:', 'ок' if ok_compile else 'КРАСНОЕ')
    print('тесты:', 'ок' if ok_tests else ('КРАСНОЕ' if ok_tests is False else 'не прогнаны'))
    print('живые пробы: смотри строки выше')
    if _kit['leaks']:
        print('герой: КРАСНОЕ — пробы не вернули руки/надетое:', ', '.join(_kit['leaks']))
    sys.exit(0 if ok_lint and ok_probes and ok_ignored and ok_compile and ok_tests is not False else 1)


if __name__ == '__main__':
    main()
