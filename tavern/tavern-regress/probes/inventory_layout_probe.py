"""Вёрстка экрана инвентаря — отпечаток дерева UI (ночь 17→18.09, цель: `InventoryScreenUI.Build.cs`).

python3 inventory_layout_probe.py [метка]    только в СВОЁМ play, на любом уровне.

Свои вещи вынимаются, кладётся набор пробы (фонарь в левую руку, палка в правую,
батарейки и ключ в самую большую сетку), экран открывается, дерево модалки
печатается в ~/.cache/tavern-probes/inventory_layout_<метка>.txt: узел, вкл/выкл,
якоря, позиция, размер, масштаб, текст и кегль, цвет и спрайт картинки. Сверка
ДО/ПОСЛЕ — diff двух файлов. В конце экран закрывается, свои вещи возвращаются.
"""
import json, pathlib, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
OUT = pathlib.Path.home() / '.cache/tavern-probes'


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=180)
    try:
        d = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return 'нет ответа: ' + out.stdout[-300:]
    if not d.get('success'):
        return 'ОШИБКА: ' + json.dumps(d.get('data') or d, ensure_ascii=False)[:600]
    return (d.get('data') or {}).get('result')


HEAD = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var player = Cozy.Grid.PlayerRef.GameObject;
var eq = player != null ? player.GetComponent<Cozy.Character.Equipment>() : null;
var inv = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.InventoryScreenUI>(UnityEngine.FindObjectsInactive.Include);
if (eq == null || inv == null) return "нет игрока или экрана инвентаря";
Cozy.Grid.GridInventory bag = null;
foreach (var c in eq.Containers)
    if (c.grid != eq.Pockets && (bag == null || c.grid.Columns * c.grid.Rows > bag.Columns * bag.Rows)) bag = c.grid;
'''

SETUP = HEAD + r'''
if (bag == null) return "ПРОПУСК: у игрока нет сетки, кроме рук";
if (System.AppDomain.CurrentDomain.GetData("probe.lay.saved") != null) return "прошлый прогон не убран";
inv.Open();
inv.Close();
var saved = new System.Collections.Generic.List<object[]>();
foreach (var c in eq.Containers)
    foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(c.grid.Items))
    {
        saved.Add(new object[] { c.grid, it, it.anchor, it.rotation });
        c.grid.Remove(it);
    }
System.AppDomain.CurrentDomain.SetData("probe.lay.saved", saved);
bool ok = eq.Pockets.TryPlace(Cozy.Grid.Items.Flashlight, new UnityEngine.Vector2Int(0, 0), 0);
ok &= eq.TryHold(new Cozy.Grid.PlacedItem { def = Cozy.Grid.Items.Stick }, 1, 0);
ok &= bag.TryAdd(Cozy.Grid.Items.Batteries);
ok &= bag.TryAdd(Cozy.Grid.Items.Key);
inv.Open();
return "набор пробы положен=" + ok;
'''

# Карточка вещи (клик по плитке) в отпечаток входит: у неё свой набор кнопок на
# каждый предмет, и её вёрстку иначе ничто не проверяет.
MENU = HEAD + r'''
Tavern.UI.InventoryItemView view = null;
foreach (var v in UnityEngine.Object.FindObjectsByType<Tavern.UI.InventoryItemView>(UnityEngine.FindObjectsSortMode.None))
    if (v.placed != null && v.placed.def.id == "%ITEM%" && v.gameObject.activeInHierarchy) view = v;
if (view == null) return "нет плитки %ITEM%";
typeof(Tavern.UI.InventoryScreenUI).GetMethod("ShowItemMenu", bf).Invoke(inv, new object[] { view, null });
return "карточка %ITEM% открыта";
'''

DUMP = HEAD + r'''
UnityEngine.Canvas.ForceUpdateCanvases();
var modal = typeof(Tavern.UI.ModalScreenUI).GetField("_modal", bf).GetValue(inv) as UnityEngine.GameObject;
if (modal == null) return "экран не открыт";
var ci = System.Globalization.CultureInfo.InvariantCulture;
var sb = new System.Text.StringBuilder();
var stack = new System.Collections.Generic.Stack<System.Collections.Generic.KeyValuePair<UnityEngine.Transform, int>>();
stack.Push(new System.Collections.Generic.KeyValuePair<UnityEngine.Transform, int>(modal.transform, 0));
int nodes = 0;
while (stack.Count > 0)
{
    var top = stack.Pop();
    var t = top.Key;
    for (int i = t.childCount - 1; i >= 0; i--)
        stack.Push(new System.Collections.Generic.KeyValuePair<UnityEngine.Transform, int>(t.GetChild(i), top.Value + 1));
    nodes++;
    sb.Append(new string(' ', top.Value)).Append(t.name);
    if (!t.gameObject.activeSelf) sb.Append(" [off]");
    var rt = t as UnityEngine.RectTransform;
    // Позицию карточки на экране не печатаем: ScreenClampUI отталкивает её от
    // нижней полосы HUD, а полоса бывает скрыта — число прыгало между прогонами
    // на её высоту. Размер и всё содержимое (координаты внутри карточки) целы.
    if (rt != null && t.GetComponent<Tavern.UI.ScreenClampUI>() != null)
        sb.Append(" p=подвижно s=").Append(rt.rect.width.ToString("0.#", ci)).Append('x').Append(rt.rect.height.ToString("0.#", ci));
    else if (rt != null)
        sb.Append(" a=").Append(rt.anchorMin.x.ToString("0.##", ci)).Append(',').Append(rt.anchorMin.y.ToString("0.##", ci)).Append('-')
          .Append(rt.anchorMax.x.ToString("0.##", ci)).Append(',').Append(rt.anchorMax.y.ToString("0.##", ci))
          .Append(" p=").Append(rt.anchoredPosition.x.ToString("0.#", ci)).Append(',').Append(rt.anchoredPosition.y.ToString("0.#", ci))
          .Append(" s=").Append(rt.rect.width.ToString("0.#", ci)).Append('x').Append(rt.rect.height.ToString("0.#", ci));
    if (UnityEngine.Mathf.Abs(t.localScale.x - 1f) > 0.001f) sb.Append(" k=").Append(t.localScale.x.ToString("0.###", ci));
    var text = t.GetComponent<TMPro.TMP_Text>();
    if (text != null) sb.Append(" text=\"").Append(text.text).Append("\" size=").Append(text.fontSize.ToString("0.##", ci));
    var img = t.GetComponent<UnityEngine.UI.Image>();
    if (img != null) sb.Append(" img=#").Append(UnityEngine.ColorUtility.ToHtmlStringRGBA(img.color))
        .Append(img.enabled ? "" : " скрыта").Append(img.sprite != null ? " " + img.sprite.name : "");
    sb.Append('\n');
}
System.IO.Directory.CreateDirectory("%DIR%");
System.IO.File.WriteAllText("%FILE%", sb.ToString());
return "узлов " + nodes + ", файл %FILE%";
'''

RESTORE = HEAD + r'''
var saved = System.AppDomain.CurrentDomain.GetData("probe.lay.saved") as System.Collections.Generic.List<object[]>;
if (saved == null) return "нечего возвращать";
inv.Close();
foreach (var c in eq.Containers)
    foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(c.grid.Items)) c.grid.Remove(it);
int back = 0;
foreach (var row in saved)
    if (((Cozy.Grid.GridInventory)row[0]).TryPlace((Cozy.Grid.PlacedItem)row[1], (UnityEngine.Vector2Int)row[2], (int)row[3])) back++;
System.AppDomain.CurrentDomain.SetData("probe.lay.saved", null);
return "свои вещи возвращены: " + (back == saved.Count ? "все" : back + " из " + saved.Count);
'''


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'now'
    path = OUT / ('inventory_layout_%s.txt' % label)
    first = run(SETUP)
    print(first)
    # «не в play» — не результат: два пустых прогона совпадают и выглядят
    # доказательством (поймано 18.09).
    if isinstance(first, str) and 'не в play' in first:
        raise SystemExit('редактор не в play — замер не снят')
    try:
        time.sleep(1.0)
        print(run(DUMP.replace('%DIR%', str(OUT)).replace('%FILE%', str(path))))
        for item in ('flashlight', 'batteries', 'key'):
            print(run(MENU.replace('%ITEM%', item)))
            time.sleep(0.6)
            card = OUT / ('inventory_menu_%s_%s.txt' % (item, label))
            print(run(DUMP.replace('%DIR%', str(OUT)).replace('%FILE%', str(card))))
    finally:
        print(run(RESTORE))


if __name__ == '__main__':
    main()
