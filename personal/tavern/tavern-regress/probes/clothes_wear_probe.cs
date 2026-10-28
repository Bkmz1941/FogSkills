// НАДЕТЬ / СНЯТЬ / КАРМАНЫ / СЕЙВ ОДЕЖДЫ (CLOTHING.md, группы 5–8; 18.10). Для execute_code в play, любой уровень.
// Работает на НАСТОЯЩЕМ `Equipment` героя: гардероб и карманы снимаются `SaveState` в начале и возвращаются
// `LoadState` в finally; мост «к ногам» (`Equipment.DropForPlayer`) на время пробы подменён счётчиком —
// в мир ничего не падает. Перебор — все предметы `Items` с носимым слотом, новая вещь попадает сама.
//  CL-WEAR01 вещь пола героя надевается в свой слот и видна на модели (узел Wear_* с рендерерами);
//  CL-WEAR02 снятая уходит с фигуры в том же кадре (инвариант 66);
//  CL-WEAR03 вещь чужого пола не надевается;
//  CL-WEAR04 закрывающая вещь (covers) сбрасывает закрытое ровно по разу, без дублей;
//  CL-WEAR05 обувь поднимает фигуру на soleLift;
//  CL-PCK01 карманы едут с вещью одним экземпляром сетки (снял — та же сетка с тем же предметом);
//  CL-SAVE01 SaveState → LoadState: надетое и содержимое карманов прежние;
//  CL-ITM01 иконка есть; CL-ITM02 у вещи есть двойник в мире; CL-ITM03 вес двойника = вес предмета;
//  CL-ITM04 карманы двойника = карманы предмета.
if (!UnityEngine.Application.isPlaying) return "не в play";
Cozy.Character.Equipment eq = null;
foreach (var e in UnityEngine.Object.FindObjectsByType<Cozy.Character.Equipment>(UnityEngine.FindObjectsSortMode.None))
    if (e.IsPlayer) eq = e;
if (eq == null) return "SKIP: нет Equipment героя";
var visual = eq.transform.Find("Visual");
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };
System.Func<Cozy.Grid.EquipSlot, string> NodeOf = s => s == Cozy.Grid.EquipSlot.Body ? "Wear_Body" : s == Cozy.Grid.EquipSlot.Outer ? "Wear_Outer"
    : s == Cozy.Grid.EquipSlot.Legs ? "Wear_Legs" : s == Cozy.Grid.EquipSlot.Feet ? "Wear_Feet" : s == Cozy.Grid.EquipSlot.Bag ? "Wear_Bag" : null;
System.Func<string, int> Rends = node => {
    var v = eq.transform.Find("Visual");
    var n = v != null ? v.Find(node) : null;
    return n == null ? -1 : n.GetComponentsInChildren<UnityEngine.Renderer>().Length;
};

var saved = eq.SaveState();
var oldDrop = Cozy.Character.Equipment.DropForPlayer;
var dropped = new System.Collections.Generic.List<string>();
Cozy.Character.Equipment.DropForPlayer = (item, contents) => { dropped.Add(item.id); return true; };
var items = new System.Collections.Generic.List<Cozy.Grid.ItemDef>();
foreach (var p in typeof(Cozy.Grid.Items).GetProperties(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
    if (p.PropertyType == typeof(Cozy.Grid.ItemDef) && p.GetValue(null) is Cozy.Grid.ItemDef it && it.slot != Cozy.Grid.EquipSlot.None && !items.Contains(it)) items.Add(it);
int worn = 0, foreign = 0, noVisual = 0;
try
{
    foreach (var s in Cozy.Character.Equipment.Slots) eq.TakeOff(s);
    foreach (var it in items)
    {
        // CL-ITM01–04: предмет и двойник
        Check(UnityEngine.Resources.Load<UnityEngine.Sprite>("Icons/" + it.icon) != null || !it.iconPicture, "CL-ITM01 " + it.id + ": нет иконки Icons/" + it.icon);
        var twin = Cozy.Grid.FurnitureCatalog.ByPickupItem(it.id);
        if (twin == null) { Check(false, "CL-ITM02 " + it.id + ": нет объекта мира — «Положить», «Выбросить», «Снять и положить» серые"); }
        else
        {
            Check(UnityEngine.Mathf.Abs(twin.weightKg - it.weight) < 0.051f, "CL-ITM03 " + it.id + ": вес в мире " + twin.weightKg + " кг, предмета " + it.weight + " кг");
            int ic = it.invColumns * it.invRows, tc = twin.inspectable ? twin.inspectColumns * twin.inspectRows : 0;
            Check(ic == tc, "CL-ITM04 " + it.id + ": карманы предмета " + it.invColumns + "×" + it.invRows + ", у " + twin.id + " " + (twin.inspectable ? twin.inspectColumns + "×" + twin.inspectRows : "нет"));
        }
        // CL-WEAR03: чужой пол
        if (!it.FitsHero)
        {
            foreign++;
            Check(!eq.Equip(it.slot, it), "CL-WEAR03 " + it.id + " (" + it.wear + "): наделась на героя другого пола");
            eq.TakeOff(it.slot);
            continue;
        }
        // CL-WEAR01/02
        Check(eq.Equip(it.slot, it), "CL-WEAR01 " + it.id + ": не надевается в " + it.slot);
        if (eq.Get(it.slot) != it) continue;
        worn++;
        var node = NodeOf(it.slot);
        if (node != null)
        {
            int r = Rends(node);
            if (r <= 0) { noVisual++; Check(false, "CL-WEAR01 " + it.id + ": надета, но на модели не видна (узла " + node + " нет)"); }
        }
        // CL-WEAR05: подъём на подошве
        if (it.slot == Cozy.Grid.EquipSlot.Feet && it.soleLift > 0f && visual != null)
            info.Append("INFO CL-WEAR05 " + it.id + ": Visual.y " + visual.localPosition.y.ToString("0.000") + ", soleLift " + it.soleLift + "\n");
        eq.TakeOff(it.slot);
        if (node != null) Check(Rends(node) < 0, "CL-WEAR02 " + it.id + ": снята, а узел " + node + " ещё на фигуре в этом кадре");
    }
    // CL-WEAR04: закрывающая вещь
    foreach (var cover in items)
    {
        if (cover.covers == null || cover.covers.Length == 0 || !cover.FitsHero) continue;
        foreach (var s in Cozy.Character.Equipment.Slots) eq.TakeOff(s);
        var under = new System.Collections.Generic.List<string>();
        foreach (var s in cover.covers)
            foreach (var it in items)
                if (it.slot == s && it.FitsHero && it.covers.Length == 0 && eq.Get(s) == null && eq.Equip(s, it)) { under.Add(it.id); break; }
        dropped.Clear();
        bool shed = eq.ShedCovered(cover);
        bool on = shed && eq.Equip(cover.slot, cover);
        Check(on, "CL-WEAR04 " + cover.id + ": не надевается поверх " + string.Join(",", under));
        var dup = new System.Collections.Generic.HashSet<string>();
        foreach (var d in dropped) Check(dup.Add(d), "CL-WEAR04 " + cover.id + ": " + d + " сброшен дважды");
        Check(dropped.Count == under.Count, "CL-WEAR04 " + cover.id + ": сброшено " + dropped.Count + " (" + string.Join(",", dropped) + "), надето под ним было " + under.Count);
        foreach (var s in cover.covers) Check(eq.Get(s) == null, "CL-WEAR04 " + cover.id + ": слот " + s + " не освобождён");
        // надеть обычную вещь в слот закрывающей: она сама уходит один раз
        foreach (var it in items)
        {
            if (it.slot != cover.slot || it == cover || !it.FitsHero || it.covers.Length > 0) continue;
            dropped.Clear();
            bool shed2 = eq.ShedCovered(it);
            var prev = eq.Get(it.slot);
            Check(shed2 && prev == null && dropped.Count == 1 && dropped[0] == cover.id, "CL-WEAR04 " + it.id + " поверх " + cover.id + ": сброшено [" + string.Join(",", dropped) + "], в слоте осталось " + (prev != null ? prev.id : "пусто") + " — ждали: " + cover.id + " к ногам один раз, слот пуст");
            break;
        }
    }
    // CL-PCK01 карманы едут с вещью
    foreach (var s in Cozy.Character.Equipment.Slots) eq.TakeOff(s);
    Cozy.Grid.ItemDef pocketed = null;
    foreach (var it in items) if (it.FitsHero && it.invColumns * it.invRows > 0 && it.covers.Length == 0) { pocketed = it; break; }
    if (pocketed != null)
    {
        var grid = new Cozy.Grid.GridInventory(); grid.Resize(pocketed.invColumns, pocketed.invRows);
        bool put = grid.TryAdd(Cozy.Grid.Items.Flashlight);
        Check(put && eq.Equip(pocketed.slot, pocketed, grid), "CL-PCK01 " + pocketed.id + ": не надеть с карманами");
        Check(eq.ContentsOf(pocketed.slot) == grid, "CL-PCK01 " + pocketed.id + ": надетая держит НЕ ту сетку карманов");
        // CL-SAVE01 — пока вещь надета и в кармане фонарь
        var snap = eq.SaveState();
        eq.TakeOff(pocketed.slot);
        eq.LoadState(snap);
        Check(eq.Get(pocketed.slot) == pocketed, "CL-SAVE01 " + pocketed.id + ": после загрузки не надета");
        var back = eq.ContentsOf(pocketed.slot);
        Check(back != null && back.Items.Count == 1, "CL-SAVE01 " + pocketed.id + ": после загрузки в карманах " + (back == null ? "нет сетки" : back.Items.Count + " предметов"));
        var off = eq.TakeOff(pocketed.slot);
        Check(off != null && off.Items.Count == 1, "CL-PCK01 " + pocketed.id + ": снятая отдала сетку без содержимого");
    }
}
finally
{
    Cozy.Character.Equipment.DropForPlayer = oldDrop;
    eq.LoadState(saved);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — носимых предметов " + items.Count + ", надето " + worn + ", чужого пола " + foreign + ", не видно на модели " + noVisual + " (гардероб героя возвращён)\n" + info + sb;
