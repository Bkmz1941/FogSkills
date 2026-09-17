"""Отпечаток панели дебага (F1): каждая вкладка со ВСЕМИ раскрытыми блоками — строка на элемент.

Защита для правок `HudUI.Debug*.cs`: перенос вкладок по файлам, вынос блоков в методы, общие
помощники. Снимок до правки и после сверяется `diff`: порядок строк, подписи, диапазоны и
значения ползунков, цвета вариантов кнопок, размеры из LayoutElement.

    python3 debug_panel_probe.py snap <метка>     снять отпечаток в play → ~/.cache/tavern-probes/debug_panel_<метка>.txt
    python3 debug_panel_probe.py diff <a> <b>     сравнить два снимка (код 1 при расхождении)
    python3 debug_panel_probe.py fps [кадров]     кадр и мусор с ОТКРЫТОЙ панелью на каждой вкладке против закрытой;
                                                  живые строки тикают каждый кадр — так 16.09 проехало падение
                                                  до 30 FPS (P437), которое замер в сборке не видит

Живые строки и `live`-кнопки (список `_debugLines`) печатаются как <live>: их текст меняется
сам. Вкладку, раскрытые блоки и выбранную вкладку проба возвращает как было; DebugTune не трогает.
⚠️ В play и не на паузе (P407). Счётчик «щелчков» — сколько блоков пришлось раскрыть: ноль на
вкладке с блоками значит, что проба ничего не раскрыла.
"""
import difflib, hashlib, json, pathlib, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gc_probe

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
OUT = pathlib.Path.home() / '.cache/tavern-probes'
# Запасной список — на случай, если игра не ответила. Живой список проба берёт
# из самой игры (`HudUI.DebugTabs`): зашитый уже отставал на три вкладки
# (zones, sudden, ranged — ночь 17→18.09), и их правки шли мимо отпечатка.
FALLBACK_TABS = ['general', 'view', 'zones', 'seethrough', 'weather', 'player', 'character', 'objects', 'effects', 'sudden', 'ranged', 'monsters', 'census', 'system', 'ui']

TABS_CODE = r'''
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "";
var prop = typeof(Tavern.UI.HudUI).GetProperty("DebugTabs", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
var tabs = prop != null ? prop.GetValue(hud, null) as System.Array : null;
if (tabs == null) return "";
var ids = new System.Collections.Generic.List<string>();
foreach (var tab in tabs) ids.Add((string)tab.GetType().GetField("Item1").GetValue(tab));
return string.Join(",", ids.ToArray());
'''


def live_tabs():
    res = run(TABS_CODE)
    ids = [t for t in str(res or '').split(',') if t and ' ' not in t]
    if not ids:
        print('⚠️ список вкладок из игры не получен — беру запасной, он мог отстать', flush=True)
        return list(FALLBACK_TABS)
    missing = [t for t in ids if t not in FALLBACK_TABS]
    if missing:
        print('новые вкладки, которых нет в запасном списке: ' + ', '.join(missing), flush=True)
    return ids


class _Tabs(list):
    """Ленивый список: первое обращение спрашивает игру."""
    def _load(self):
        if not self:
            self.extend(live_tabs())
        return self

    def __iter__(self):
        return list.__iter__(self._load())


TABS = _Tabs()

CODE = r'''
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "нет HudUI";
var T = typeof(Tavern.UI.HudUI);
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var row = (UnityEngine.Transform)T.GetField("_debugActionsRow", F).GetValue(hud);
var head = (UnityEngine.Transform)T.GetField("_debugHeadRow", F).GetValue(hud);
if (row == null) return "панель дебага не построена";
var tabField = T.GetField("_debugTab", F);
var open = (System.Collections.Generic.HashSet<string>)T.GetField("_skinOpen", F).GetValue(hud);
var linesField = T.GetField("_debugLines", F);
var rebuild = T.GetMethod("RebuildDebugActions", F);
string keepTab = (string)tabField.GetValue(hud);
var keepOpen = new System.Collections.Generic.List<string>(open);
var sb = new System.Text.StringBuilder();
var inv = System.Globalization.CultureInfo.InvariantCulture;
string[] tabs = TABS;
System.Func<UnityEngine.UI.Button> findClosed = () =>
{
    var stack = new System.Collections.Generic.Stack<UnityEngine.Transform>();
    stack.Push(row);
    while (stack.Count > 0)
    {
        var t = stack.Pop();
        for (int i = t.childCount - 1; i >= 0; i--) stack.Push(t.GetChild(i));
        if (t.name != "SkinSubHead" && t.name != "SkinBlockHead") continue;
        if (t.Find("Icon_plus") == null) continue;
        var b = t.GetComponent<UnityEngine.UI.Button>();
        if (b != null) return b;
    }
    return null;
};
try
{
    foreach (var tab in tabs)
    {
        tabField.SetValue(hud, tab);
        open.Clear();
        rebuild.Invoke(hud, null);
        int clicks = 0;
        for (; clicks < 3000; clicks++)
        {
            var closed = findClosed();
            if (closed == null) break;
            closed.onClick.Invoke();
        }
        var live = new System.Collections.Generic.HashSet<int>();
        var lines = (System.Collections.IList)linesField.GetValue(hud);
        foreach (var kv in lines)
        {
            var key = kv.GetType().GetProperty("Key").GetValue(kv, null) as UnityEngine.Object;
            if (key != null) live.Add(key.GetInstanceID());
        }
        sb.Append("=== ").Append(tab).Append(" раскрыто=").Append(clicks).Append(" живых=").Append(lines.Count).Append('\n');
        foreach (var root in new[] { head, row })
        {
            var stack = new System.Collections.Generic.Stack<System.Collections.Generic.KeyValuePair<UnityEngine.Transform, int>>();
            stack.Push(new System.Collections.Generic.KeyValuePair<UnityEngine.Transform, int>(root, 0));
            while (stack.Count > 0)
            {
                var top = stack.Pop();
                var t = top.Key;
                for (int i = t.childCount - 1; i >= 0; i--)
                    stack.Push(new System.Collections.Generic.KeyValuePair<UnityEngine.Transform, int>(t.GetChild(i), top.Value + 1));
                sb.Append(new string(' ', top.Value)).Append(t.name);
                if (!t.gameObject.activeSelf) sb.Append(" [off]");
                var text = t.GetComponent<TMPro.TMP_Text>();
                if (text != null)
                    sb.Append(" text=").Append(live.Contains(text.GetInstanceID()) ? "<live>" : "\"" + text.text + "\"")
                      .Append(" size=").Append(text.fontSize.ToString("0.##", inv));
                var slider = t.GetComponent<UnityEngine.UI.Slider>();
                if (slider != null)
                    sb.Append(" slider=[").Append(slider.minValue.ToString("R", inv)).Append(',')
                      .Append(slider.maxValue.ToString("R", inv)).Append("]=").Append(slider.value.ToString("R", inv));
                var input = t.GetComponent<TMPro.TMP_InputField>();
                if (input != null) sb.Append(" input=\"").Append(input.text).Append('"');
                var img = t.GetComponent<UnityEngine.UI.Image>();
                if (img != null) sb.Append(" img=#").Append(UnityEngine.ColorUtility.ToHtmlStringRGBA(img.color))
                    .Append(img.sprite != null ? " " + img.sprite.name : "");
                var le = t.GetComponent<UnityEngine.UI.LayoutElement>();
                if (le != null) sb.Append(" le=").Append(le.preferredWidth.ToString("0.##", inv)).Append('x')
                    .Append(le.preferredHeight.ToString("0.##", inv)).Append(" flex=").Append(le.flexibleWidth.ToString("0.##", inv))
                    .Append(le.ignoreLayout ? " ignore" : "");
                if (t.GetComponent<UnityEngine.UI.Button>() != null) sb.Append(" btn");
                sb.Append('\n');
            }
        }
    }
}
finally
{
    tabField.SetValue(hud, keepTab);
    open.Clear();
    foreach (var k in keepOpen) open.Add(k);
    rebuild.Invoke(hud, null);
}
System.IO.File.WriteAllText(PATH, sb.ToString());
return "ok " + sb.Length;
'''


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=600, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        return str((d.get('data') or {}).get('result') or d.get('message') or d.get('error') or line[:400])
    except Exception:
        return 'НЕ РАЗОБРАЛОСЬ: ' + out.stdout[-600:]


def path_of(label):
    return OUT / ('debug_panel_%s.txt' % label)


def snap(label):
    OUT.mkdir(parents=True, exist_ok=True)
    target = path_of(label)
    code = CODE.replace('TABS', 'new[] { %s }' % ', '.join('"%s"' % t for t in TABS)) \
               .replace('PATH', json.dumps(str(target)))
    res = run(code)
    if not res.startswith('ok'):
        print('проба не прошла:', res)
        return 1
    text = target.read_text(encoding='utf-8')
    heads = [l for l in text.splitlines() if l.startswith('=== ')]
    print('снимок %s: %d строк, md5 %s' % (target, text.count('\n'), hashlib.md5(text.encode()).hexdigest()[:12]))
    for h in heads:
        print('  ' + h[4:])
    return 0


def diff(a, b):
    left = path_of(a).read_text(encoding='utf-8').splitlines()
    right = path_of(b).read_text(encoding='utf-8').splitlines()
    delta = list(difflib.unified_diff(left, right, a, b, lineterm='', n=1))
    if not delta:
        print('СОВПАЛО: %d строк' % len(left))
        return 0
    print('\n'.join(delta[:120]))
    print('... расхождений в строках: %d' % sum(1 for d in delta if d[:1] in '+-' and d[:3] not in ('+++', '---')))
    return 1


PANEL = r'''
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "нет HudUI";
var T = typeof(Tavern.UI.HudUI);
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
T.GetMethod("SetDebugMode", F).Invoke(hud, new object[] { MODE });
if (TAB != null) { T.GetField("_debugTab", F).SetValue(hud, TAB); T.GetMethod("RebuildDebugActions", F).Invoke(hud, null); }
return "ok";
'''

STATE = r'''
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var T = typeof(Tavern.UI.HudUI);
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
return T.GetField("_debugMode", F).GetValue(hud) + "|" + T.GetField("_debugTab", F).GetValue(hud);
'''

SPIKE_MS = 1.0


def panel(mode, tab):
    code = PANEL.replace('MODE', 'true' if mode else 'false').replace('TAB', json.dumps(tab) if tab else 'null')
    return run(code)


def fps(frames):
    state = run(STATE)
    if '|' not in state:
        print('проба не прошла:', state)
        return 1
    was_mode, was_tab = state.split('|', 1)
    gc_probe.uncap(True)
    rows, bad = [], []
    try:
        panel(False, None)
        time.sleep(1.0)
        base = gc_probe.measure(frames)
        print('%-10s кадр %.2f мс, p95 %.2f, мусор %d Б' % ('закрыта', base[2], base[3], base[0]), flush=True)
        for tab in TABS:
            panel(True, tab)
            time.sleep(1.0)
            avg, mx, ms, p95 = gc_probe.measure(frames)
            delta = ms - base[2]
            mark = '  ⚠️ дороже закрытой на %.2f мс' % delta if delta > SPIKE_MS else ''
            if mark:
                bad.append(tab)
            print('%-10s кадр %.2f мс (%+.2f), p95 %.2f, мусор %d Б (%+d)%s'
                  % (tab, ms, delta, p95, avg, avg - base[0], mark), flush=True)
    finally:
        panel(was_mode.lower().startswith('t'), was_tab)
    if bad:
        print('КРАСНОЕ: вкладки дороже закрытой панели больше чем на %.1f мс: %s — смотреть живые строки, '
              '`gc_probe.py profile`' % (SPIKE_MS, ', '.join(bad)))
        return 1
    print('панель на всех вкладках в пределах %.1f мс от закрытой' % SPIKE_MS)
    return 0


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == 'snap':
        return snap(sys.argv[2])
    if len(sys.argv) >= 4 and sys.argv[1] == 'diff':
        return diff(sys.argv[2], sys.argv[3])
    if len(sys.argv) >= 2 and sys.argv[1] == 'fps':
        return fps(int(sys.argv[2]) if len(sys.argv) >= 3 else 240)
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
