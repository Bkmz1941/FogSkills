// ПРЕДМЕТЫ В РУКАХ (HELD.md; 20.10). Для execute_code в play, любой уровень; стенд — «Предметы в руках (тест)».
// Работает на НАСТОЯЩЕМ `Equipment` героя: руки и сумки снимаются `SaveState` в начале и возвращаются `LoadState`
// в finally. Перебор — все предметы `Items`, новая вещь попадает сама.
//  HD-LIVE01 то, что сейчас в руках, лежит по правилу руки: клетка (рука, 0), ширина 1 (P1156);
//  HD-LIVE02 риг держит в каждой руке ровно то, что лежит в её клетке;
//  HD-LIVE03 инвентарь открыт — в клетке руки виден предмет, который в ней лежит (P1156);
//  HD-CELL01 любой предмет, который держится в руке, общим TryAdd в руки при занятой левой ложится в правую по правилу;
//  HD-CELL02 обе руки заняты — TryAdd в руки отказывает, ничего не кладёт поперёк;
//  HD-CELL03 предмет, который в руку не влезает (HoldRotation < 0), в руки не ложится;
//  HD-SAVE01 старый сейв с вещью поперёк рук (newspaper в (0,1)) поднимается в клетку руки, вещь не теряется;
//  HD-SAVE02 SaveState → LoadState: в руках то же, в тех же клетках и с тем же поворотом.
if (!UnityEngine.Application.isPlaying) return "не в play";
Cozy.Character.Equipment eq = null;
foreach (var e in UnityEngine.Object.FindObjectsByType<Cozy.Character.Equipment>(UnityEngine.FindObjectsSortMode.None))
    if (e.IsPlayer) eq = e;
if (eq == null) return "SKIP: нет Equipment героя";
var rig = eq.GetComponent<Cozy.Character.FlashlightRig>();
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };
var hands = eq.Pockets;
System.Func<Cozy.Grid.PlacedItem, bool> ByHandRule = it =>
    it.anchor.y == 0 && Cozy.Grid.Shapes.Bounds(Cozy.Grid.Shapes.Rotate(it.def.Footprint(), it.rotation)).x == 1;
System.Func<Cozy.Grid.PlacedItem, string> Tell = it => it.def.id + " в (" + it.anchor.x + "," + it.anchor.y + ") пов " + it.rotation;

foreach (var it in hands.Items)
    Check(ByHandRule(it), "HD-LIVE01 сейчас в руках поперёк правила: " + Tell(it));
var sides = new[] { Cozy.Character.FlashlightRig.Side.Left, Cozy.Character.FlashlightRig.Side.Right };
for (int h = 0; h < 2 && rig != null; h++)
{
    var held = eq.HandItem(h);
    string want = held != null ? held.def.id : null;
    string has = rig.HandItem(sides[h]);
    Check((want ?? "") == (has ?? ""), "HD-LIVE02 рука " + h + ": в клетке «" + want + "», риг держит «" + has + "»");
}
UnityEngine.RectTransform plate = null;
foreach (var t in UnityEngine.Object.FindObjectsByType<UnityEngine.RectTransform>(UnityEngine.FindObjectsSortMode.None))
    if (t.name == "Hands" && t.parent != null && t.parent.name == "Doll" && t.gameObject.activeInHierarchy) plate = t;
if (plate == null) info.Append("HD-LIVE03 пропущен: инвентарь закрыт\n");
else for (int h = 0; h < 2; h++)
{
    var tile = plate.Find("Hand" + h);
    var held = eq.HandItem(h);
    bool shown = false;
    if (tile != null) foreach (UnityEngine.Transform c in tile) if (c.name != "Overlay" && c.name != "Border" && c.name != "MutedHand") shown = true;
    if (held != null) Check(shown, "HD-LIVE03 рука " + h + ": лежит " + Tell(held) + ", а клетка в инвентаре пустая");
}

var saved = eq.SaveState();
var items = new System.Collections.Generic.List<Cozy.Grid.ItemDef>();
foreach (var p in typeof(Cozy.Grid.Items).GetProperties(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
    if (p.PropertyType == typeof(Cozy.Grid.ItemDef) && p.GetValue(null) is Cozy.Grid.ItemDef it && !items.Contains(it)) items.Add(it);
System.Action Empty = () => { foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(hands.Items)) hands.Remove(it); };
var flash = Cozy.Grid.Items.Flashlight;
int holdable = 0, wide = 0, refused = 0;
try
{
    foreach (var def in items)
    {
        if (def == flash) continue;
        bool fitsHand = Cozy.Character.Equipment.HoldRotation(def, 0) >= 0;
        Empty();
        hands.TryPlace(flash, new UnityEngine.Vector2Int(0, 0), 0);
        bool added = hands.TryAdd(def);
        var put = added ? Cozy.Grid.GridInventory.LastPlaced : null;
        if (!fitsHand)
        {
            refused++;
            Check(!added, "HD-CELL03 " + def.id + " в руку не влезает, а лёг: " + (put != null ? Tell(put) : "?"));
            continue;
        }
        holdable++;
        if (Cozy.Grid.Shapes.Bounds(def.Footprint()).x > 1) wide++;
        Check(added && put != null && put.anchor.x == 1 && ByHandRule(put), "HD-CELL01 " + def.id + ": " + (added ? Tell(put) : "не лёг в свободную правую"));
        if (!added) continue;
        Check(!hands.TryAdd(Cozy.Grid.Items.Newspaper2Folded), "HD-CELL02 обе руки заняты (" + flash.id + ", " + def.id + "), а газета легла");
    }

    var bad = eq.SaveState();
    foreach (var c in bad.containers)
        if (c.slot == 0)
        {
            c.items.Clear();
            c.items.Add(new Cozy.Grid.LevelIO.ItemData { id = flash.id, x = 0, y = 0, rot = 0, state = "", charge = 100f, host = -1 });
            c.items.Add(new Cozy.Grid.LevelIO.ItemData { id = Cozy.Grid.Items.Newspaper2Folded.id, x = 0, y = 1, rot = 0, state = "", charge = 100f, host = -1 });
        }
    eq.LoadState(bad);
    Cozy.Grid.PlacedItem paper = null;
    foreach (var it in hands.Items) if (it.def == Cozy.Grid.Items.Newspaper2Folded) paper = it;
    Check(paper != null, "HD-SAVE01 газета из старого сейва потерялась");
    if (paper != null) Check(ByHandRule(paper), "HD-SAVE01 газета из старого сейва осталась поперёк: " + Tell(paper));

    eq.LoadState(saved);
    var again = eq.SaveState();
    System.Func<Cozy.Grid.LevelIO.PlayerData, string> Hands = d =>
    {
        var s = new System.Text.StringBuilder();
        foreach (var c in d.containers) if (c.slot == 0) foreach (var i in c.items) s.Append(i.id + "@" + i.x + "," + i.y + "r" + i.rot + " ");
        return s.ToString();
    };
    Check(Hands(again) == Hands(saved), "HD-SAVE02 руки до «" + Hands(saved) + "», после «" + Hands(again) + "»");
}
finally
{
    eq.LoadState(saved);
}
info.Append("перебрано: держится в руке " + holdable + " (шире клетки " + wide + "), не влезает " + refused + "\n");
return (fails == 0 ? "OK" : "FAIL") + " руки: проверок " + checks + ", красных " + fails + "\n" + sb + info;
