// ДЕЙСТВИЯ С ПРОДУКТАМИ И ПОРЧА (PRODUCTS.md, группы 6–7; 18.10). Для execute_code в play, любой уровень.
// Свои продукты в своей зоне (этаж игрока, +400 м по X, +80 по Z), удаляются в finally. Уровень не меняет и не сохраняет.
//  PT-A05  «Кушать» у каждого съедобного: сытость/вода игрока растёт ровно на Nutrition.ValueOf (с учётом потолка 100);
//          кнопку жмём тем же действием, что игрок (FeatureButton с HudUI как контекстом), только если у HUD НЕТ
//          открытой панели и осмотра — иначе SKIP, чужую панель не закрываем. Сытость и вода возвращаются как были.
//  PT-ACT03 съели пачку с обёрткой (`eatenInto`) — обёртка появилась на месте пачки: центр габарита ±1 см, низ ±1 см (VIS09);
//  PT-B03  испорченный: EatDoses > 0 (травит), свежий: только врождённый poisonDose;
//  PT-ACT01 «Порезать/Отрезать» предлагается только ножу: у каждого такого layout productId = kitchen_knife;
//  PT-C02  батон, испорченный и со сроком: «Порезать» → ровно две половины, порча и срок унаследованы;
//  PT-C04  старый хлеб: «Отрезать» ×6 → 6 ломтиков, у хлеба 0 (уходит), порча унаследована.
// Первая строка — вердикт «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом кейса.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var BS = System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var spawn = T.GetMethod("SpawnObject", B);
var putOne = T.GetMethod("PutOneIntoLayout", B);
var freeSlot = T.GetMethod("LayoutFreeSlot", BS);
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0, skips = 0, eaten = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };

var defs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && (d.isProduct || (d.category ?? "").StartsWith(Cozy.Grid.Categories.Food))) defs.Add(d);
var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var player = Cozy.Grid.PlayerRef.Transform;
float placeFloor = (float)T.GetMethod("PlaceFloorY", B).Invoke(gc, null);
var origin = new UnityEngine.Vector3((player != null ? player.position.x : 0f) + 400f, placeFloor, (player != null ? player.position.z : 0f) + 80f);
var stats = UnityEngine.Object.FindFirstObjectByType<Cozy.Character.CharacterStats>();
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
float sat0 = stats != null ? stats.Satiety : 0f, wat0 = stats != null ? stats.Water : 0f;
bool hudFree = false;
if (hud != null)
{
    var fPanel = hud.GetType().GetField("_interactPanel", B);
    var pExam = hud.GetType().GetProperty("Examining", B);
    hudFree = fPanel != null && fPanel.GetValue(hud) == null && (pExam == null || !(bool)pExam.GetValue(hud, null));
}
System.Func<Cozy.Grid.ObjectDef, UnityEngine.Vector3, Cozy.Grid.InteractiveObject> Make = (def, p) => {
    try { return (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, p, 0f }); } catch { return null; }
};
try
{
    int k = 0;
    // PT-B03 и PT-ACT01 — по каталогу
    foreach (var def in defs)
    {
        if (Cozy.Grid.FoodSpoil.Perishable(def) && !def.inedible && (def.food > 0f || def.water > 0f))
        {
            Check(Cozy.Grid.FoodSpoil.EatDoses(def, true) > 0, "PT-B03 " + def.id + ": испорченный не травит (доз " + Cozy.Grid.FoodSpoil.EatDoses(def, true) + ")");
            Check(Cozy.Grid.FoodSpoil.EatDoses(def, false) == UnityEngine.Mathf.Max(0, def.poisonDose), "PT-B03 " + def.id + ": свежий травит на " + Cozy.Grid.FoodSpoil.EatDoses(def, false) + " доз, врождённых " + def.poisonDose);
        }
        foreach (var l in def.cookLayouts)
            if (l.actionLabel == "Порезать" || l.actionLabel == "Отрезать")
                Check(l.productId == "kitchen_knife", "PT-ACT01 " + def.id + ": «" + l.actionLabel + "» откликается на «" + l.productId + "», а не на нож");
    }

    // PT-A05 / PT-ACT03 — настоящая кнопка «Кушать»
    if (stats == null || hud == null) { skips++; sb.Append("SKIP PT-A05: нет CharacterStats или HudUI\n"); }
    else if (!hudFree) { skips++; sb.Append("SKIP PT-A05: у HUD открыта панель или осмотр — чужое не закрываю\n"); }
    else
        foreach (var def in defs)
        {
            var io = Make(def, origin + new UnityEngine.Vector3((k % 10) * 1.3f, 0f, (k / 10) * 1.3f)); k++;
            if (io == null) continue;
            if (Cozy.Grid.FoodSpoil.Perishable(def)) io.SetFood(false, Cozy.Grid.FoodSpoil.Today + 5);
            System.Action eat = null;
            foreach (var f in io.Features)
            {
                try { if (!f.Available) continue; foreach (var btn in f.Buttons(hud)) if (btn.Label == "Кушать" && btn.Enabled) eat = btn.OnClick; } catch { }
            }
            if (eat == null) { UnityEngine.Object.DestroyImmediate(io.gameObject); continue; }
            var value = Cozy.Cooking.Nutrition.ValueOf(io);
            stats.SetSatiety(0f); stats.SetWater(0f);
            var wrapDef = string.IsNullOrEmpty(def.eatenInto) ? null : Cozy.Grid.FurnitureCatalog.ById(def.eatenInto);
            var atBox = Cozy.Grid.FurnitureModel.Combined(io.GetComponentsInChildren<UnityEngine.Renderer>());
            var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
            try { eat(); } catch (System.Exception e) { Check(false, "PT-A05 " + def.id + ": «Кушать» упало — " + e.Message); continue; }
            eaten++;
            float wantFood = UnityEngine.Mathf.Min(value.Food, stats.maxSatiety), wantWater = UnityEngine.Mathf.Clamp(value.Water, 0f, stats.maxWater);
            Check(UnityEngine.Mathf.Abs(stats.Satiety - wantFood) <= 0.01f, "PT-A05 " + def.id + ": сытость +" + stats.Satiety.ToString("0.#") + ", ждали +" + wantFood.ToString("0.#"));
            Check(UnityEngine.Mathf.Abs(stats.Water - wantWater) <= 0.01f, "PT-A05 " + def.id + ": вода +" + stats.Water.ToString("0.#") + ", ждали +" + wantWater.ToString("0.#"));
            Check(value.Food > 0f || value.Water > 0f || value.Cheer, "PT-A05 " + def.id + ": «Кушать» есть, а пользы ноль");
            if (wrapDef != null)
            {
                Cozy.Grid.InteractiveObject wrap = null;
                foreach (var o in Cozy.Grid.InteractiveObject.All) if (o != null && !known.Contains(o) && o.Def == wrapDef) wrap = o;
                Check(wrap != null, "PT-ACT03 " + def.id + ": после еды нет обёртки «" + def.eatenInto + "»");
                if (wrap != null)
                {
                    var wb = Cozy.Grid.FurnitureModel.Combined(wrap.GetComponentsInChildren<UnityEngine.Renderer>());
                    float dxz = new UnityEngine.Vector2(wb.center.x - atBox.center.x, wb.center.z - atBox.center.z).magnitude, dlow = wb.min.y - atBox.min.y;
                    Check(dxz <= 0.01f && UnityEngine.Mathf.Abs(dlow) <= 0.01f, "PT-ACT03 " + def.id + ": центр обёртки в " + (dxz * 100f).ToString("0.0") + " см от центра пачки, низ на " + (dlow * 100f).ToString("0.0") + " см");
                }
            }
        }

    // PT-C02: испорченный батон со сроком — «Порезать» один раз
    var knifeDef = Cozy.Grid.FurnitureCatalog.ById("kitchen_knife");
    var loafDef = Cozy.Grid.FurnitureCatalog.ById("bread_loaf");
    // резке нужна опора под ломтиками и половинами — свой стол, хлеб на столешнице
    var cutAt = origin + new UnityEngine.Vector3(0f, 0f, -20f);
    var deskDef = Cozy.Grid.FurnitureCatalog.ById("office_desk");
    System.Func<UnityEngine.Vector3, UnityEngine.Vector3> OnDesk = at => {
        if (deskDef == null) return at;
        var desk = Make(deskDef, at);
        UnityEngine.Physics.SyncTransforms();
        float top = at.y;
        foreach (var h in UnityEngine.Physics.RaycastAll(at + UnityEngine.Vector3.up * 3f, UnityEngine.Vector3.down, 4f))
            if (h.collider.transform.IsChildOf(desk.transform) && h.point.y > top) top = h.point.y;
        return new UnityEngine.Vector3(at.x, top, at.z);
    };
    if (knifeDef == null || loafDef == null) { skips++; sb.Append("SKIP PT-C02: нет ножа или батона в каталоге\n"); }
    else
    {
        var knife = Make(knifeDef, cutAt + UnityEngine.Vector3.right * 3f);
        var loaf = Make(loafDef, OnDesk(cutAt));
        loaf.SetFood(true, Cozy.Grid.FoodSpoil.Today + 2);
        UnityEngine.Physics.SyncTransforms();
        Cozy.Grid.CookLayout cut = null;
        foreach (var l in loafDef.cookLayouts) if (l.productId == "kitchen_knife") cut = l;
        var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
        int slot = cut != null ? (int)freeSlot.Invoke(null, new object[] { cut, loaf, null }) : -1;
        if (slot < 0) Check(false, "PT-C02 у батона нет «Порезать» или места для половины");
        else
        {
            putOne.Invoke(gc, new object[] { cut, loaf, slot, knife });
            var halves = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
            foreach (var o in Cozy.Grid.InteractiveObject.All) if (o != null && !known.Contains(o)) halves.Add(o);
            Check(halves.Count == 2, "PT-C02 после «Порезать» новых объектов " + halves.Count + ", ждали 2 половины");
            foreach (var h in halves)
                Check(h.Def.id == cut.resultId && h.Spoiled && h.ExpiryDay == Cozy.Grid.FoodSpoil.Today + 2, "PT-C02 половина " + h.Def.id + ": испорчена=" + h.Spoiled + ", срок " + h.ExpiryDay + " (у батона true, " + (Cozy.Grid.FoodSpoil.Today + 2) + ")");
        }
    }

    // PT-C04: старый хлеб — «Отрезать» ×6
    var breadDef = Cozy.Grid.FurnitureCatalog.ById("bread");
    if (knifeDef == null || breadDef == null) { skips++; sb.Append("SKIP PT-C04: нет ножа или хлеба\n"); }
    else
    {
        var knife = Make(knifeDef, cutAt + new UnityEngine.Vector3(3f, 0f, 4f));
        var bread = Make(breadDef, OnDesk(cutAt + new UnityEngine.Vector3(0f, 0f, 4f)));
        bread.SetFood(true, Cozy.Grid.FoodSpoil.Today + 1);
        UnityEngine.Physics.SyncTransforms();
        Cozy.Grid.CookLayout slice = null;
        foreach (var l in breadDef.cookLayouts) if (l.productId == "kitchen_knife") slice = l;
        var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
        int start = bread.Count, cuts = 0;
        for (int i = 0; i < 10 && slice != null && bread.Count > 0; i++)
        {
            int s = (int)freeSlot.Invoke(null, new object[] { slice, bread, null });
            if (s < 0) break;
            putOne.Invoke(gc, new object[] { slice, bread, s, knife });
            UnityEngine.Physics.SyncTransforms();
            cuts++;
        }
        int slices = 0, inherited = 0;
        foreach (var o in Cozy.Grid.InteractiveObject.All)
            if (o != null && !known.Contains(o) && o.Def.id == (slice != null ? slice.resultId : "")) { slices++; if (o.Spoiled) inherited++; }
        Check(start == 6, "PT-C04 у нового хлеба ломтиков " + start + ", ждали 6");
        Check(cuts == 6 && slices == 6, "PT-C04 резов " + cuts + ", ломтиков " + slices + ", ждали 6 и 6");
        Check(bread.Count == 0, "PT-C04 после 6 ломтиков у хлеба осталось " + bread.Count + " (должен уйти)");
        Check(inherited == slices, "PT-C04 порчу унаследовали " + inherited + " из " + slices + " ломтиков");
    }
}
finally
{
    if (stats != null) { stats.SetSatiety(sat0); stats.SetWater(wat0); }
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — продуктов " + defs.Count + ", съедено кнопкой " + eaten + ", пропусков " + skips + " (сытость и вода возвращены: " + sat0.ToString("0.#") + "/" + wat0.ToString("0.#") + "; созданное удалено)\n" + sb;
