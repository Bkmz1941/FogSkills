"""Перетаскивание в инвентаре — характеризующий замер (ночь 17→18.09, цель: `InventoryScreenUI.ResolveDrop`/`UpdateGhost`).

python3 inventory_drop_probe.py    только в СВОЁМ play, на любом уровне.

Свои вещи игрока на время прогона вынимаются из всех сеток (ссылки хранятся в
AppDomain), вместо них кладётся набор пробы: фонарь в левую руку, батарейки,
палка и ключ — в самую большую сетку. Каждый сценарий — один вызов: взять вещь
за центр, довести до цели, снять пометки цели, отпустить, прочитать, где легла.
В конце сетки очищаются и свои вещи возвращаются на прежние клетки. Перед набором
инвентарь открывается вхолостую: первое открытие после входа в play подкладывает стартовый ключ.

Строка на сценарий: «имя: пометка цели → где вещь». Сверка ДО/ПОСЛЕ — посимвольно.
"""
import json, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=120)
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
if (bag == null) return "ПРОПУСК: у игрока нет ни одной сетки, кроме рук";
System.Func<Cozy.Grid.GridInventory, string> dump = null;
dump = delegate (Cozy.Grid.GridInventory g)
{
    var parts = new System.Collections.Generic.List<string>();
    foreach (var it in g.Items)
        parts.Add(it.def.id + "@" + it.anchor.x + "," + it.anchor.y + "r" + it.rotation
            + (it.contents != null && it.contents.Items.Count > 0 ? "[" + dump(it.contents) + "]" : ""));
    parts.Sort(System.StringComparer.Ordinal);
    return string.Join(" ", parts.ToArray());
};
'''

SETUP = HEAD + r'''
if (System.AppDomain.CurrentDomain.GetData("probe.inv.saved") != null) return "прошлый прогон не убран — сначала restore";
inv.Open();
inv.Close();
var saved = new System.Collections.Generic.List<object[]>();
foreach (var c in eq.Containers)
    foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(c.grid.Items))
    {
        saved.Add(new object[] { c.grid, it, it.anchor, it.rotation });
        c.grid.Remove(it);
    }
System.AppDomain.CurrentDomain.SetData("probe.inv.saved", saved);
bool ok = eq.Pockets.TryPlace(Cozy.Grid.Items.Flashlight, new UnityEngine.Vector2Int(0, 0), 0);
ok &= bag.TryAdd(Cozy.Grid.Items.Batteries);
ok &= bag.TryAdd(Cozy.Grid.Items.Key);
ok &= bag.TryAdd(Cozy.Grid.Items.Stick);
inv.Open();
return "набор пробы: сетка " + bag.Columns + "x" + bag.Rows + ", положено=" + ok
    + " | руки: " + dump(eq.Pockets) + " | сетка: " + dump(bag);
'''

# цель: hand0 / hand1 / cell:c,r / slot:<EquipSlot> / miss
DRAG = HEAD + r'''
string itemId = "%ITEM%"; string target = "%TARGET%";
Tavern.UI.InventoryItemView view = null;
foreach (var v in UnityEngine.Object.FindObjectsByType<Tavern.UI.InventoryItemView>(UnityEngine.FindObjectsSortMode.None))
    if (v.placed != null && v.placed.def.id == itemId && v.gameObject.activeInHierarchy) view = v;
if (view == null) return "нет плитки " + itemId;
string from = view.sourceGrid == eq.Pockets ? "руки" : view.sourceGrid == bag ? "сетка" : "внутри";
var rt = view.itemRoot;
var e = new UnityEngine.EventSystems.PointerEventData(UnityEngine.EventSystems.EventSystem.current);
e.position = UnityEngine.RectTransformUtility.WorldToScreenPoint(null, rt.TransformPoint(rt.rect.center));
view.OnBeginDrag(e);
UnityEngine.RectTransform goal = null;
UnityEngine.Vector2 point = new UnityEngine.Vector2(5f, 5f);
var handRects = (System.Collections.Generic.List<UnityEngine.RectTransform>)typeof(Tavern.UI.InventoryScreenUI).GetField("_handRects", bf).GetValue(inv);
if (target.StartsWith("hand"))
{
    goal = handRects[int.Parse(target.Substring(4))];
    point = UnityEngine.RectTransformUtility.WorldToScreenPoint(null, goal.TransformPoint(goal.rect.center));
}
else if (target.StartsWith("cell:"))
{
    var cr = target.Substring(5).Split(',');
    var grids = (System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<Cozy.Grid.GridInventory, UnityEngine.RectTransform>>)typeof(Tavern.UI.InventoryScreenUI).GetField("_grids", bf).GetValue(inv);
    foreach (var g in grids) if (g.Key == bag) goal = g.Value;
    if (goal == null) return "сетки нет на экране";
    float step = (float)typeof(Tavern.UI.InventoryScreenUI).GetField("Step", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).GetValue(null);
    float gap = (float)typeof(Tavern.UI.InventoryScreenUI).GetField("Gap", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).GetValue(null);
    var corner = goal.TransformPoint(new UnityEngine.Vector3(goal.rect.xMin + gap + int.Parse(cr[0]) * step, goal.rect.yMax - gap - int.Parse(cr[1]) * step, 0f));
    var half = rt.TransformVector(new UnityEngine.Vector3(rt.rect.width * 0.5f, -rt.rect.height * 0.5f, 0f));
    point = UnityEngine.RectTransformUtility.WorldToScreenPoint(null, corner + half);
}
else if (target.StartsWith("slot:"))
{
    var slots = (System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<Cozy.Grid.EquipSlot, UnityEngine.RectTransform>>)typeof(Tavern.UI.InventoryScreenUI).GetField("_slotRects", bf).GetValue(inv);
    foreach (var s in slots) if (s.Key.ToString() == target.Substring(5)) goal = s.Value;
    if (goal == null) return "слота нет: " + target;
    point = UnityEngine.RectTransformUtility.WorldToScreenPoint(null, goal.TransformPoint(goal.rect.center));
}
inv.OnDragMove(point);
string mark = "—";
var hover = goal != null ? goal.GetComponent<Tavern.UI.InventoryCellHover>() : null;
if (hover != null)
{
    var frame = hover.markFrame != null && hover.markFrame.enabled ? hover.markFrame : hover.frame;
    var col = frame != null ? frame.color : UnityEngine.Color.clear;
    string tone = col.r > 0.9f && col.g < 0.5f ? "красная" : col.b > 0.7f && col.r < 0.5f ? "синяя" : col.r > 0.9f && col.g > 0.9f && col.a > 0.5f ? "белая" : "покой";
    mark = "рамка " + tone + (hover.fill != null && hover.fill.enabled ? "+заливка" : "");
}
var ghost = typeof(Tavern.UI.InventoryScreenUI).GetField("_ghost", bf).GetValue(inv) as UnityEngine.GameObject;
if (ghost != null)
{
    var img = ghost.GetComponentInChildren<UnityEngine.UI.Image>();
    mark += " призрак" + (img != null && img.color.r > 0.9f && img.color.g < 0.5f ? " красный" : " белый");
}
var host = typeof(Tavern.UI.InventoryScreenUI).GetField("_dropHost", bf).GetValue(inv) as Tavern.UI.InventoryItemView;
if (host != null) mark += " хозяин=" + host.placed.def.id;
e.position = point;
view.OnEndDrag(e);
return itemId + " (" + from + ") → " + target + ": " + mark + " ⇒ руки: " + dump(eq.Pockets) + " | сетка: " + dump(bag);
'''

RESTORE = HEAD + r'''
var saved = System.AppDomain.CurrentDomain.GetData("probe.inv.saved") as System.Collections.Generic.List<object[]>;
if (saved == null) return "нечего возвращать";
inv.Close();
foreach (var c in eq.Containers)
    foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(c.grid.Items)) c.grid.Remove(it);
int back = 0;
foreach (var row in saved)
    if (((Cozy.Grid.GridInventory)row[0]).TryPlace((Cozy.Grid.PlacedItem)row[1], (UnityEngine.Vector2Int)row[2], (int)row[3])) back++;
System.AppDomain.CurrentDomain.SetData("probe.inv.saved", null);
return "свои вещи возвращены: " + (back == saved.Count ? "все" : back + " из " + saved.Count);
'''

SCENARIOS = [
    ('batteries', 'hand1'),        # из сетки в пустую руку
    ('batteries', 'hand0'),        # из руки в гнездо фонаря в другой руке
    ('deco_stick', 'hand1'),       # длинная вещь в руку — встаёт стоя
    ('key', 'hand1'),              # занятая рука не принимает
    ('key', 'hand0'),              # ключ на фонарь: гнездо его не берёт
    ('deco_stick', 'cell:0,0'),    # стоячая палка в сетку в одну строку не лезет
    ('key', 'cell:4,0'),           # перекладка внутри сетки
    ('key', 'miss'),               # мимо всего — возвращается на место
    ('flashlight', 'slot:Head'),   # не одежда — слот не берёт
    ('flashlight', 'cell:0,0'),    # из руки в сетку вместе с батарейкой внутри
]


def main():
    first = run(SETUP)
    print(first)
    # «не в play» — не результат: два пустых прогона совпадают и выглядят
    # доказательством (поймано 18.09).
    if isinstance(first, str) and 'не в play' in first:
        raise SystemExit('редактор не в play — замер не снят')
    time.sleep(0.8)
    try:
        for item, target in SCENARIOS:
            print(run(DRAG.replace('%ITEM%', item).replace('%TARGET%', target)))
            time.sleep(0.6)
    finally:
        print(run(RESTORE))


if __name__ == '__main__':
    main()
