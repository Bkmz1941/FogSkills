// ПРОДУКТЫ, ВОЛНА 2 (PRODUCTS.md, раздел 11 и остатки групп 4–7; 18.10). Для execute_code в play, любой уровень.
// Свои объекты — этаж игрока, +400 м по X и −40 по Z (за краем уровня), всё созданное удаляется в finally.
// Инвентарь игрока НЕ трогаем: «Подобрать» жмём настоящей кнопкой, но GiveToPlayer/StackIntoPlayer на время
// подменены своей сеткой; счётчики отравления FoodSpoil._eaten возвращаются как были.
//  PT-SPN01 спавн каждого продукта: ровно один, свежий, пачка полная, жидкость не больше ёмкости;
//  PT-DRP01 выложили «в воздух» над полом и над столом — FallToSupport кладёт низ на опору ±5 мм;
//  PT-INV04 «Подобрать» при полном инвентаре — продукт остаётся в мире на месте, панель «Инвентарь полон» снята;
//  PT-DUP01 «Подобрать» при свободном — в сетке ровно один предмет, в мире продукт уходит (уничтожается);
//  PT-INV05 иконка: пропорции картинки как у клеток предмета (±35 %), проверка — Илья 18.10 «широкие иконки нужны»;
//  PT-C05  куски батона: «подобрать → выложить» — размер 1×1, габарит модели тот же ±2 %;
//  PT-INV06 вес пачки со счётчиком в мире = вес её предмета в инвентаре (Carry.KgOf) при 3 оставшихся;
//  PT-CNT01 положили продукт в контейнер (миска, тарелка, сковорода, кофемашина) — сдвинули контейнер — продукт едет с ним;
//  PT-CNT02 батон на полке холодильника — «Порезать» — половины на той же полке (Container тот же);
//  PT-SPL01 стандарт времени 2880 с/сутки ×1, день порчи = день часов, срок «сегодня» не испорчен, «вчера» — испорчен;
//  PT-SPL02 испорченное за полный порог таблицы — ровно max(1, poisonDose) доз, не больше (P764);
//  PT-SPL03 у КАЖДОГО продукта с ножевой резкой части наследуют порчу и срок;
//  PT-LIQ01 вылили всё — вес (Carry.KgOf) падает ровно на массу жидкости; в инвентаре вес как в мире;
//  PT-TXT01 описаний у продуктов НЕТ (Илья 18.10: «описания все убираем», BUILD.md 10.09);
//  PT-SAVE04 продукт в контейнере: снимок → загрузка — снова в том же контейнере, не задвоился;
//  PT-B01/B02 продукт на полке каждого холодильника при питании: с 18.10 холод снят пока (TemperatureSim.ColdOn = false) — поле у продукта НЕ холодное; при ColdOn — тянет к холоду камеры.
// Первая строка — вердикт «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL/SKIP/INFO с кодом кейса.
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
var notes = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 150) sb.Append("FAIL " + line + "\n"); } };
System.Func<UnityEngine.GameObject, UnityEngine.Bounds> Box = go => Cozy.Grid.FurnitureModel.Combined(go.GetComponentsInChildren<UnityEngine.Renderer>());

var defs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && (d.isProduct || (d.category ?? "").StartsWith(Cozy.Grid.Categories.Food))) defs.Add(d);
var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var player = Cozy.Grid.PlayerRef.Transform;
float placeFloor = (float)T.GetMethod("PlaceFloorY", B).Invoke(gc, null);
var origin = new UnityEngine.Vector3((player != null ? player.position.x : 0f) + 400f, placeFloor, (player != null ? player.position.z : 0f) - 40f);
int cell = 0;
System.Func<UnityEngine.Vector3> Next = () => { var p = origin + new UnityEngine.Vector3((cell % 12) * 1.6f, 0f, (cell / 12) * 1.6f); cell++; return p; };
System.Func<Cozy.Grid.ObjectDef, UnityEngine.Vector3, Cozy.Grid.InteractiveObject> Make = (def, p) => {
    try { var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, p, 0f }); UnityEngine.Physics.SyncTransforms(); return io; } catch { return null; }
};
var deskDef = Cozy.Grid.FurnitureCatalog.ById("office_desk");
System.Func<UnityEngine.Vector3, float> DeskTop = at => {
    var desk = Make(deskDef, at);
    float top = float.NegativeInfinity;
    if (desk != null) foreach (var h in UnityEngine.Physics.RaycastAll(at + UnityEngine.Vector3.up * 3f, UnityEngine.Vector3.down, 4f))
        if (h.collider.transform.IsChildOf(desk.transform) && h.point.y > top) top = h.point.y;
    return top;
};
System.Func<Cozy.Grid.InteractiveObject, float> SupportGap = io => {
    var b = Box(io.gameObject);
    float support = float.NegativeInfinity;
    foreach (var h in UnityEngine.Physics.RaycastAll(new UnityEngine.Vector3(b.center.x, b.max.y + 0.5f, b.center.z), UnityEngine.Vector3.down, 4f))
    {
        if (h.collider.transform.IsChildOf(io.transform) || h.collider.isTrigger) continue;
        if (h.point.y <= b.min.y + 0.05f && h.point.y > support) support = h.point.y;
    }
    return float.IsInfinity(support) ? float.NaN : b.min.y - support;
};

var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var fGive = typeof(Cozy.Grid.PickupFeature).GetField("GiveToPlayer", BS);
var fStack = typeof(Cozy.Grid.PickupFeature).GetField("StackIntoPlayer", BS);
var oldGive = fGive.GetValue(null);
var oldStack = fStack.GetValue(null);
var fEaten = typeof(Cozy.Grid.FoodSpoil).GetField("_eaten", BS);
var eaten = fEaten.GetValue(null) as System.Collections.Generic.Dictionary<string, int>;
var eatenKeep = new System.Collections.Generic.Dictionary<string, int>(eaten);
UnityEngine.Transform hudRoot = null;
var hudKids = new System.Collections.Generic.HashSet<UnityEngine.Transform>();
if (hud != null)
{
    var fr = hud.GetType().GetField("_root", B);
    hudRoot = fr != null ? fr.GetValue(hud) as UnityEngine.Transform : null;
    if (hudRoot == null && fr != null && fr.GetValue(hud) is UnityEngine.Component rc) hudRoot = rc.transform;
    if (hudRoot != null) foreach (UnityEngine.Transform c in hudRoot) hudKids.Add(c);
}
var circuitsF = typeof(Cozy.Grid.PowerGrid).GetField("_circuits", BS);
var circuits = circuitsF != null ? circuitsF.GetValue(null) as System.Collections.IList : null;
object circuit = null;
int spawned = 0, picked = 0, cut = 0, containers = 0, fridges = 0;
string stage = "старт";
try
{
    stage = "SPN01";
    // PT-SPN01 + PT-TXT01 + PT-INV05 — по каталогу
    var en = new System.Collections.Generic.Dictionary<string, string>();
    var enAsset = UnityEngine.Resources.Load<UnityEngine.TextAsset>("Localization/en");
    if (enAsset != null) Cozy.FlatJson.Parse(enAsset.text, en);
    var withDesc = new System.Collections.Generic.List<string>();
    foreach (var def in defs)
    {
        var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
        var io = Make(def, Next());
        if (io == null) { Check(false, "PT-SPN01 " + def.id + ": не спавнится"); continue; }
        spawned++;
        int same = 0;
        foreach (var o in Cozy.Grid.InteractiveObject.All) if (o != null && !known.Contains(o) && o.Def == def) same++;
        Check(same == 1, "PT-SPN01 " + def.id + ": после одного спавна таких объектов " + same);
        if (io.HasCount) Check(io.Count == def.countMax, "PT-SPN01 " + def.id + ": новая пачка " + io.Count + " из " + def.countMax);
        if (Cozy.Grid.FoodSpoil.Perishable(def)) Check(!io.Expired, "PT-SPN01 " + def.id + ": только что поставлен, а испорчен (spoiled=" + io.Spoiled + ", срок " + io.ExpiryDay + ", сегодня " + Cozy.Grid.FoodSpoil.Today + ")");
        var item0 = Cozy.Grid.Items.ById(!string.IsNullOrEmpty(def.pickupItemId) ? def.pickupItemId : def.id);
        if (item0 != null)
        {
            var rw = new System.Collections.Generic.List<Cozy.Grid.ItemEffect>();
            var ri = new System.Collections.Generic.List<Cozy.Grid.ItemEffect>();
            Cozy.Grid.ItemEffects.Collect(io, rw);
            var pl0 = new Cozy.Grid.PlacedItem { def = item0, charge = item0.FullCharge, state = Cozy.Grid.LiquidState.Of(io) };
            Cozy.Grid.InteractiveObject.TakePieces(io, pl0);
            Cozy.Grid.ItemEffects.Collect(item0, pl0, ri);
            string sw = "", si = "";
            foreach (var e in rw) sw += e.Icon + ":" + e.Text + " ";
            foreach (var e in ri) si += e.Icon + ":" + e.Text + " ";
            Check(sw == si, "PT-A04 " + def.id + ": карточка в мире [" + sw.Trim() + "], в инвентаре [" + si.Trim() + "]");
            if (!def.inedible && (def.food > 0f || def.water > 0f)) Check(rw.Count > 0, "PT-A04 " + def.id + ": съедобный (сытость " + def.food + ", вода " + def.water + "), а строк пользы в карточке нет");
        }
        if (io.Liquid != null) Check(io.Liquid.Litres <= def.capacityL + 0.001f, "PT-SPN01 " + def.id + ": жидкости " + io.Liquid.Litres.ToString("0.00") + " л при ёмкости " + def.capacityL.ToString("0.00"));

        string desc = (def.description ?? "").Trim();
        if (desc.Length > 0) withDesc.Add(def.id);
        Check(desc.Length == 0, "PT-TXT01 " + def.id + ": у продукта описание «" + desc + "», а описаний быть не должно (Илья 18.10: «описания все убираем»)");

        var item = Cozy.Grid.Items.ById(!string.IsNullOrEmpty(def.pickupItemId) ? def.pickupItemId : def.id);
        if (item != null && !string.IsNullOrEmpty(item.icon))
        {
            var spr = UnityEngine.Resources.Load<UnityEngine.Sprite>("Icons/" + item.icon);
            if (spr != null)
            {
                var r = spr.textureRect;
                float pic = r.width / UnityEngine.Mathf.Max(1f, r.height), cells = (float)item.size.x / UnityEngine.Mathf.Max(1, item.size.y);
                float k = pic / cells;
                Check(k > 0.65f && k < 1.54f, "PT-INV05 " + def.id + ": картинка " + r.width.ToString("0") + "×" + r.height.ToString("0") + ", клетки " + item.size.x + "×" + item.size.y + " — иконка не по форме клеток (Илья 18.10: «широкие иконки нужны»)");
            }
        }
    }

    stage = "DRP01";
    // PT-DRP01: над полом и над столом — FallToSupport
    float top = DeskTop(origin + new UnityEngine.Vector3(-8f, 0f, 0f));
    int drops = 0;
    var fallUpd = typeof(Cozy.Grid.FallToSupport).GetMethod("Update", B);
    var fTarget = typeof(Cozy.Grid.FallToSupport).GetField("_targetY", B);
    UnityEngine.Vector3? floorSpot = null;
    if (player != null)
        for (int ring = 2; ring < 10 && floorSpot == null; ring++)
            for (int a = 0; a < 12 && floorSpot == null; a++)
            {
                var p0 = player.position + UnityEngine.Quaternion.Euler(0f, a * 30f, 0f) * UnityEngine.Vector3.forward * ring;
                if (!UnityEngine.Physics.Raycast(p0 + UnityEngine.Vector3.up * 1.5f, UnityEngine.Vector3.down, out var fh, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) continue;
                if (fh.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null) continue;
                if (UnityEngine.Physics.OverlapBox(fh.point + UnityEngine.Vector3.up * 0.45f, new UnityEngine.Vector3(0.5f, 0.4f, 0.5f), UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore).Length > 0) continue;
                floorSpot = fh.point;
            }
    if (floorSpot == null) notes.Append("SKIP PT-DRP01/POS03 над полом: рядом с героем нет свободного пола\n");
    foreach (var def in defs)
    {
        if (def.mount != Cozy.Grid.ObjectMount.Surface) continue;
        foreach (var onDesk in new[] { false, true })
        {
            if (onDesk && float.IsInfinity(top)) continue;
            if (!onDesk && floorSpot == null) continue;
            var at = onDesk ? new UnityEngine.Vector3(origin.x - 8f + (drops % 5) * 0.12f - 0.25f, top + 0.6f, origin.z + (drops % 3) * 0.1f - 0.1f) : floorSpot.Value + UnityEngine.Vector3.up * 0.6f;
            var io = Make(def, at);
            if (io == null) continue;
            io.transform.position = at;
            UnityEngine.Physics.SyncTransforms();
            var fall = io.GetComponent<Cozy.Grid.FallToSupport>();
            if (fall == null) { Check(false, "PT-DRP01 " + def.id + ": нет FallToSupport — в воздухе так и останется"); continue; }
            fall.Wake();
            for (int i = 0; i < 20000; i++) { fallUpd.Invoke(fall, null); UnityEngine.Physics.SyncTransforms(); if (i > 2 && float.IsNaN((float)fTarget.GetValue(fall))) break; }
            float gap = SupportGap(io);
            Check(!float.IsNaN(gap) && UnityEngine.Mathf.Abs(gap) <= 0.005f, "PT-DRP01 " + def.id + (onDesk ? " над столом" : " над полом") + ": низ от опоры " + (float.IsNaN(gap) ? "опоры нет" : (gap * 100f).ToString("0.0") + " см"));
            drops++;
            UnityEngine.Object.DestroyImmediate(io.gameObject);
        }
    }

    stage = "INV04";
    // PT-INV04 / PT-DUP01 — настоящая кнопка «Подобрать», своя сетка вместо инвентаря игрока
    var grid = new Cozy.Grid.GridInventory();
    grid.Resize(5, 6);
    bool full = false;
    System.Func<Cozy.Grid.ItemDef, string, Cozy.Grid.GridInventory, bool> give = (d, s, c) => !full && grid.TryAdd(d, s, c);
    fGive.SetValue(null, give);
    fStack.SetValue(null, null);
    if (hud == null) { notes.Append("SKIP PT-INV04/DUP01: нет HudUI (контекст кнопки)\n"); }
    else
        foreach (var def in defs)
        {
            var io = Make(def, Next());
            if (io == null) continue;
            System.Action pick = null;
            foreach (var f in io.Features)
                try { if (f.Available) foreach (var b in f.Buttons(hud)) if (b.Label == "Подобрать" && b.Enabled) pick = b.OnClick; } catch { }
            if (pick == null) { UnityEngine.Object.DestroyImmediate(io.gameObject); continue; }
            picked++;
            var at = io.transform.position;
            full = true;
            int had = grid.Items.Count;
            try { pick(); } catch (System.Exception e) { Check(false, "PT-INV04 " + def.id + ": «Подобрать» упало — " + e.Message); }
            Check(io != null && grid.Items.Count == had && (io.transform.position - at).magnitude < 0.001f, "PT-INV04 " + def.id + ": при полном инвентаре продукт " + (io == null ? "исчез" : "сдвинулся на " + ((io.transform.position - at).magnitude * 100f).ToString("0.0") + " см") + ", в сетке " + grid.Items.Count);
            if (hudRoot != null) foreach (UnityEngine.Transform c in new System.Collections.Generic.List<UnityEngine.Transform>(System.Linq.Enumerable.Cast<UnityEngine.Transform>(hudRoot))) if (!hudKids.Contains(c)) UnityEngine.Object.DestroyImmediate(c.gameObject);
            full = false;
            grid.Resize(5, 6);
            foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(grid.Items)) grid.Remove(it);
            try { pick(); } catch (System.Exception e) { Check(false, "PT-DUP01 " + def.id + ": «Подобрать» упало — " + e.Message); continue; }
            int got = 0; foreach (var it in grid.Items) if (it.def != null) got++;
            Check(got == 1, "PT-DUP01 " + def.id + ": после «Подобрать» в сетке предметов " + got + ", ждали 1");
            if (io != null) UnityEngine.Object.DestroyImmediate(io.gameObject);
            foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(grid.Items)) grid.Remove(it);
        }
    fGive.SetValue(null, oldGive);
    fStack.SetValue(null, oldStack);

    stage = "C05";
    // PT-C05: куски батона туда-обратно ×3; PT-INV06: вес пачки в мире = в инвентаре
    foreach (var def in defs)
    {
        var item = Cozy.Grid.Items.ById(!string.IsNullOrEmpty(def.pickupItemId) ? def.pickupItemId : def.id);
        if (item == null) continue;
        bool part = def.id.StartsWith("bread_part_") || def.id == "bread_slice";
        if (!part && !(def.countMax > 1)) continue;
        var io = Make(def, Next());
        if (io == null) continue;
        if (io.HasCount && def.countMax >= 4) io.SetCount(3);
        var size0 = Box(io.gameObject).size;
        float kgWorld = Cozy.Character.Carry.KgOf(io);
        var placed = new Cozy.Grid.PlacedItem { def = item, charge = item.FullCharge };
        placed.state = Cozy.Grid.LiquidState.Of(io);
        Cozy.Grid.InteractiveObject.TakePieces(io, placed);
        if (io.HasCount && def.countMax >= 4)
            Check(UnityEngine.Mathf.Abs(Cozy.Character.Carry.KgOf(placed) - kgWorld) <= 0.005f, "PT-INV06 " + def.id + ": 3 из " + def.countMax + " в мире " + kgWorld.ToString("0.000") + " кг, в инвентаре " + Cozy.Character.Carry.KgOf(placed).ToString("0.000") + " кг");
        if (part)
        {
            Check(item.size == new UnityEngine.Vector2Int(1, 1), "PT-C05 " + def.id + ": в инвентаре " + item.size.x + "×" + item.size.y + ", ждали 1×1");
            var cur = io;
            for (int round = 0; round < 3; round++)
            {
                var pl = new Cozy.Grid.PlacedItem { def = item, charge = item.FullCharge };
                pl.state = Cozy.Grid.LiquidState.Of(cur);
                Cozy.Grid.InteractiveObject.TakePieces(cur, pl);
                var at = cur.transform.position;
                UnityEngine.Object.DestroyImmediate(cur.gameObject);
                cur = Make(def, at);
                if (!string.IsNullOrEmpty(pl.state)) Cozy.Grid.LiquidState.Apply(cur, pl.state);
                Cozy.Grid.InteractiveObject.DropPieces(cur, pl);
            }
            var size1 = Box(cur.gameObject).size;
            float grow = UnityEngine.Mathf.Max(size1.x / UnityEngine.Mathf.Max(size0.x, 1e-4f), size1.y / UnityEngine.Mathf.Max(size0.y, 1e-4f), size1.z / UnityEngine.Mathf.Max(size0.z, 1e-4f));
            float shrink = UnityEngine.Mathf.Min(size1.x / UnityEngine.Mathf.Max(size0.x, 1e-4f), size1.y / UnityEngine.Mathf.Max(size0.y, 1e-4f), size1.z / UnityEngine.Mathf.Max(size0.z, 1e-4f));
            Check(grow <= 1.02f && shrink >= 0.98f, "PT-C05 " + def.id + ": после 3 кругов габарит " + size0.ToString("F3") + " → " + size1.ToString("F3"));
        }
    }

    stage = "LIQ01";
    // PT-LIQ01: вылить всё
    foreach (var def in defs)
    {
        var io = Make(def, Next());
        if (io == null || io.Liquid == null || io.Liquid.Litres <= 0.01f) { if (io != null) UnityEngine.Object.DestroyImmediate(io.gameObject); continue; }
        string kind = io.Liquid.Kind; float litres = io.Liquid.Litres;
        float kg0 = Cozy.Character.Carry.KgOf(io);
        var item = Cozy.Grid.Items.ById(!string.IsNullOrEmpty(def.pickupItemId) ? def.pickupItemId : def.id);
        if (item != null)
        {
            var pl = new Cozy.Grid.PlacedItem { def = item, charge = item.FullCharge, state = Cozy.Grid.LiquidState.Of(io) };
            Check(UnityEngine.Mathf.Abs(Cozy.Character.Carry.KgOf(pl) - kg0) <= 0.005f, "PT-LIQ01 " + def.id + ": полный в мире " + kg0.ToString("0.000") + " кг, в инвентаре " + Cozy.Character.Carry.KgOf(pl).ToString("0.000") + " кг");
        }
        io.Liquid.Set(kind, 0f);
        float kg1 = Cozy.Character.Carry.KgOf(io);
        float want = Cozy.Character.Carry.LiquidKg(kind, litres);
        Check(UnityEngine.Mathf.Abs((kg0 - kg1) - want) <= 0.005f, "PT-LIQ01 " + def.id + ": вылили " + litres.ToString("0.00") + " л " + kind + ", вес упал на " + (kg0 - kg1).ToString("0.000") + " кг, ждали " + want.ToString("0.000"));
        Check(kg1 > 0f, "PT-LIQ01 " + def.id + ": пустая ёмкость весит " + kg1.ToString("0.000") + " кг");
    }

    stage = "SPL01";
    // PT-SPL01: стандарт времени и дата порчи
    var clock = Tavern.Core.GameClock.I;
    Check(UnityEngine.Mathf.Approximately(Tavern.Core.GameClock.DaySeconds, 2880f), "PT-SPL01 сутки на 1x = " + Tavern.Core.GameClock.DaySeconds + " с, стандарт 2880 (1 мин = 30 игровых)");
    Check(UnityEngine.Mathf.Approximately(Tavern.Core.GameClock.TimeFactor, 1f), "PT-SPL01 множитель времени " + Tavern.Core.GameClock.TimeFactor + ", стандарт 1");
    if (clock != null) Check(Cozy.Grid.FoodSpoil.Today == clock.Day, "PT-SPL01 день порчи " + Cozy.Grid.FoodSpoil.Today + ", день часов " + clock.Day);
    {
        var probeDef = defs.Find(d => Cozy.Grid.FoodSpoil.Perishable(d));
        var io = probeDef != null ? Make(probeDef, Next()) : null;
        if (io != null)
        {
            int today = Cozy.Grid.FoodSpoil.Today;
            io.SetFood(false, today);
            Check(!io.Expired, "PT-SPL01 " + probeDef.id + ": срок «сегодня» уже испорчен");
            var keepDay = Cozy.Grid.FoodSpoil.CurrentDay;
            try
            {
                Cozy.Grid.FoodSpoil.CurrentDay = () => today + 1;
                Check(io.Expired, "PT-SPL01 " + probeDef.id + ": наступил день после срока, а продукт не испорчен");
            }
            finally { Cozy.Grid.FoodSpoil.CurrentDay = keepDay; }
        }
    }

    stage = "SPL02";
    // PT-SPL02: полный порог таблицы — ровно max(1, poisonDose) доз
    foreach (var def in Cozy.Grid.FoodSpoil.Edibles())
    {
        string key = string.IsNullOrEmpty(def.poisonAs) ? def.id : def.poisonAs;
        eaten.Remove(key);
        int need = UnityEngine.Mathf.Max(1, Cozy.Grid.FoodSpoil.EatsPerStage(def));
        int sum = 0, worst = 0;
        for (int i = 0; i < need; i++) { int d = Cozy.Grid.FoodSpoil.EatDoses(def, true); sum += d; if (d > worst) worst = d; }
        int want = UnityEngine.Mathf.Max(1, def.poisonDose);
        Check(sum == want && worst <= want, "PT-SPL02 " + def.id + ": " + need + " шт. испорченного дали " + sum + " доз (за раз до " + worst + "), ждали " + want);
    }
    eaten.Clear(); foreach (var kv in eatenKeep) eaten[kv.Key] = kv.Value;

    stage = "SPL03";
    // PT-SPL03: части наследуют порчу и срок — у всех продуктов с ножевой резкой
    var knifeDef = Cozy.Grid.FurnitureCatalog.ById("kitchen_knife");
    int row = 0;
    foreach (var def in defs)
    {
        if (knifeDef == null || def.cookLayouts == null) continue;
        Cozy.Grid.CookLayout lay = null;
        foreach (var l in def.cookLayouts) if (l.productId == "kitchen_knife") lay = l;
        if (lay == null) continue;
        var at = origin + new UnityEngine.Vector3(-20f - row * 4f, 0f, 10f); row++;
        float t2 = DeskTop(at);
        var knife = Make(knifeDef, at + UnityEngine.Vector3.right * 2.5f);
        var src = Make(def, new UnityEngine.Vector3(at.x, float.IsInfinity(t2) ? at.y : t2, at.z));
        if (src == null) continue;
        int exp = Cozy.Grid.FoodSpoil.Today + 2;
        src.SetFood(true, exp);
        var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
        int s = (int)freeSlot.Invoke(null, new object[] { lay, src, null });
        if (s < 0) { Check(false, "PT-SPL03 " + def.id + ": нет места под часть на своём столе"); continue; }
        putOne.Invoke(gc, new object[] { lay, src, s, knife });
        UnityEngine.Physics.SyncTransforms();
        cut++;
        int parts = 0;
        foreach (var o in Cozy.Grid.InteractiveObject.All)
            if (o != null && !known.Contains(o) && o.Def != null && o.Def != knifeDef)
            {
                parts++;
                Check(o.Spoiled && o.ExpiryDay == exp, "PT-SPL03 " + def.id + " → " + o.Def.id + ": испорчена=" + o.Spoiled + ", срок " + o.ExpiryDay + " (у целого true, " + exp + ")");
            }
        Check(parts > 0, "PT-SPL03 " + def.id + ": «" + lay.actionLabel + "» не дал ни одной части");
    }

    stage = "CNT01";
    // PT-CNT01 / PT-SAVE04: продукт в контейнере (выкладка «Положить»)
    var tIO = typeof(Cozy.Grid.LevelIO);
    var mSnap = tIO.GetMethod("Snapshot", BS);
    var mFeat = tIO.GetMethod("CollectFeatures", BS);
    var mCarrier = tIO.GetMethod("CollectCarrier", BS);
    var restore = T.GetMethod("RestoreObjects", B);
    foreach (var cdef in Cozy.Grid.FurnitureCatalog.All())
    {
        if (cdef == null || cdef.isProduct || cdef.cookLayouts == null) continue;
        Cozy.Grid.CookLayout lay = null; Cozy.Grid.ObjectDef pdef = null;
        foreach (var l in cdef.cookLayouts)
        {
            var p = Cozy.Grid.FurnitureCatalog.ById(l.productId);
            if (p != null && defs.Contains(p) && l.actionLabel == "Положить") { lay = l; pdef = p; break; }
        }
        if (lay == null) continue;
        var at = origin + new UnityEngine.Vector3(-20f - containers * 4f, 0f, 30f);
        float t3 = DeskTop(at);
        var host = Make(cdef, new UnityEngine.Vector3(at.x, float.IsInfinity(t3) ? at.y : t3, at.z));
        var prod = Make(pdef, at + new UnityEngine.Vector3(0f, 0f, 2.5f));
        if (host == null || prod == null) continue;
        var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
        int s = (int)freeSlot.Invoke(null, new object[] { lay, host, null });
        if (s < 0) { notes.Append("SKIP PT-CNT01 " + cdef.id + ": нет свободного места выкладки\n"); continue; }
        try { putOne.Invoke(gc, new object[] { lay, host, s, prod }); } catch (System.Exception e) { Check(false, "PT-CNT01 " + cdef.id + " ← " + pdef.id + ": выкладка упала — " + (e.InnerException ?? e).Message); continue; }
        UnityEngine.Physics.SyncTransforms();
        containers++;
        var inside = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
        foreach (var o in Cozy.Grid.InteractiveObject.All) if (o != null && o != host && o.Container == host && defs.Contains(o.Def) && o.transform.IsChildOf(host.transform.root)) inside.Add(o);
        Check(inside.Count > 0, "PT-CNT01 " + cdef.id + " ← " + pdef.id + ": после «Положить» внутри ничего нет");
        if (inside.Count == 0) continue;
        var rel = new System.Collections.Generic.List<UnityEngine.Vector3>();
        foreach (var o in inside) rel.Add(o.transform.position - host.transform.position);
        host.transform.position += new UnityEngine.Vector3(1.3f, 0f, 0.7f);
        UnityEngine.Physics.SyncTransforms();
        for (int i = 0; i < inside.Count; i++)
        {
            float drift = ((inside[i].transform.position - host.transform.position) - rel[i]).magnitude;
            Check(drift <= 0.001f, "PT-CNT01 " + cdef.id + " ← " + inside[i].Def.id + ": сдвинули контейнер — содержимое отстало на " + (drift * 100f).ToString("0.0") + " см");
        }
        // PT-SAVE04: снимок контейнера с содержимым → загрузка
        if (mSnap != null && restore != null)
        {
            var group = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject> { host };
            group.AddRange(inside);
            var recs = new System.Collections.Generic.List<Cozy.Grid.LevelIO.ObjectData>();
            foreach (var o in group)
            {
                var od = (Cozy.Grid.LevelIO.ObjectData)mSnap.Invoke(null, new object[] { o });
                mFeat.Invoke(null, new object[] { o, od });
                if (mCarrier != null) mCarrier.Invoke(null, new object[] { o, od });
                recs.Add(od);
            }
            var keep = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
            foreach (var o in group) keep.Remove(o);
            foreach (var o in group) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject);
            UnityEngine.Physics.SyncTransforms();
            restore.Invoke(gc, new object[] { recs, false });
            UnityEngine.Physics.SyncTransforms();
            Cozy.Grid.InteractiveObject newHost = null; int contents = 0, loose = 0;
            foreach (var o in Cozy.Grid.InteractiveObject.All) if (o != null && !keep.Contains(o) && !before.Contains(o) && o.Def == cdef) newHost = o;
            var wantDefs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
            foreach (var o in inside) wantDefs.Add(o.Def);
            foreach (var o in Cozy.Grid.InteractiveObject.All)
                if (o != null && !keep.Contains(o) && !before.Contains(o) && o != newHost && defs.Contains(o.Def)) { if (newHost != null && o.Container == newHost && wantDefs.Remove(o.Def)) contents++; else loose++; }
            Check(newHost != null && contents == inside.Count && loose == 0, "PT-SAVE04 " + cdef.id + ": продуктов внутри до сейва " + inside.Count + ", после загрузки на своих местах " + contents + ", лишних/вне контейнера " + loose);
        }
    }

    stage = "CNT02";
    // PT-CNT02 + PT-B01/B02: холодильники — батон на полке, резка; поле холода у продукта при питании
    var loafDef = Cozy.Grid.FurnitureCatalog.ById("bread_loaf");
    var PG = typeof(Cozy.Grid.PowerGrid);
    var zcType = PG.GetNestedType("ZoneCircuit", System.Reflection.BindingFlags.NonPublic);
    var gridM = PG.GetField("_grid", BS).GetValue(null) as Cozy.Grid.GridManager;
    var keyM = PG.GetMethod("Key", BS);
    var tick = typeof(Cozy.Grid.InteractiveObject).GetMethod("Tick", B);
    System.Collections.Generic.HashSet<UnityEngine.Vector3Int> powerCells = null;
    if (zcType != null && gridM != null && circuits != null)
    {
        circuit = System.Activator.CreateInstance(zcType, true);
        zcType.GetField("feature").SetValue(circuit, new Cozy.Grid.PowerFeature(true));
        zcType.GetField("kind").SetValue(circuit, Cozy.Grid.Utility.Power);
        powerCells = zcType.GetField("cells").GetValue(circuit) as System.Collections.Generic.HashSet<UnityEngine.Vector3Int>;
        circuits.Add(circuit);
    }
    float amb = Cozy.View.ViewState.RoomTemperature;
    var mSample = typeof(Cozy.Grid.TemperatureField).GetMethod("Sample", new[] { typeof(UnityEngine.Bounds), typeof(float), typeof(float).MakeByRefType(), typeof(float).MakeByRefType() });
    var mHeatBox = typeof(Cozy.Grid.TemperatureSim).GetMethod("HeatBox", BS);
    foreach (var fdef in Cozy.Grid.FurnitureCatalog.All())
    {
        if (fdef == null || string.IsNullOrEmpty(fdef.slotNodes) || fdef.tempSources == null) continue;
        bool cold = false; foreach (var ts in fdef.tempSources) if (ts.needsPower && ts.target < amb - 5f) cold = true;
        if (!cold || fdef.slotNodes.IndexOf("Slot_Shelf1", System.StringComparison.Ordinal) < 0) continue;
        fridges++;
        var at = origin + new UnityEngine.Vector3(-20f - fridges * 6f, 0f, 50f);
        var fr = Make(fdef, at);
        if (fr == null) continue;
        if (powerCells != null) { float cs = gridM.CellSize; for (int dx = -2; dx <= 2; dx++) for (int dz = -2; dz <= 2; dz++) for (int dy = -1; dy <= 2; dy++) powerCells.Add((UnityEngine.Vector3Int)keyM.Invoke(null, new object[] { at + new UnityEngine.Vector3(dx * cs, dy * cs, dz * cs), cs })); }
        foreach (var f in fr.Features) if (f is Cozy.Grid.AccessFeature a) a.SetOpen(true);
        var shelf = Cozy.Grid.FurnitureModel.FindNode(fr.transform, "Slot_Shelf1");
        if (shelf == null) { notes.Append("SKIP PT-CNT02/B01 " + fdef.id + ": в модели нет Slot_Shelf1\n"); continue; }
        UnityEngine.Physics.SyncTransforms();
        var loaf = Make(loafDef, shelf.position + UnityEngine.Vector3.up * 0.02f);
        if (loaf == null) continue;
        loaf.transform.position = shelf.position + UnityEngine.Vector3.up * 0.02f;
        UnityEngine.Physics.SyncTransforms();
        gc.ReattachToContainer(loaf);
        if (loaf.Container != fr) { Check(false, "PT-CNT02 " + fdef.id + ": батон на Slot_Shelf1 не стал содержимым холодильника (Container=" + (loaf.Container != null ? loaf.Container.Def.id : "-") + ")"); continue; }
        // B01/B02: холод камеры у продукта
        int steps = 0;
        foreach (var ts in fdef.tempSources) if (ts.needsPower) steps = UnityEngine.Mathf.Max(steps, UnityEngine.Mathf.Clamp((int)(6.9f / (UnityEngine.Mathf.Max(ts.rate, 0.04f) * 1.6f * UnityEngine.Mathf.Max(UnityEngine.Time.deltaTime, 0.0005f))) + 10, 50, 200000));
        for (int i = 0; i < steps; i++) tick.Invoke(fr, null);
        if (mSample != null && mHeatBox != null)
        {
            var hb = (UnityEngine.Bounds)mHeatBox.Invoke(null, new object[] { loaf });
            var args = new object[] { hb, amb, 0f, 0f };
            bool near = (bool)mSample.Invoke(null, args);
            float tgt = (float)args[2];
            var coldField = typeof(Cozy.Grid.TemperatureSim).GetField("ColdOn"); bool coldOn = coldField == null || (bool)coldField.GetValue(null);
            if (coldOn) Check(near && tgt < amb - 5f, "PT-B01 " + fdef.id + ": при питании у батона на полке поле " + (near ? tgt.ToString("0.0") + "°" : "не найдено") + ", комната " + amb.ToString("0.0") + "°");
            else Check(!(near && tgt < amb - 5f), "PT-B01 " + fdef.id + ": холод снят пока (Илья 18.10), а у батона на полке поле " + tgt.ToString("0.0") + "° при комнате " + amb.ToString("0.0") + "°");
        }
        notes.Append("INFO PT-B01 " + fdef.id + ": продукт сам " + (loaf.Conducts ? "проводит тепло" : "НЕ в списке проводящих (TemperatureSim его не греет/не холодит)") + ", порча — по календарной дате (FoodSpoil.PastDate), от холода не зависит\n");
        // PT-B04: холодильник с продуктом — снимок → загрузка
        if (mSnap != null && restore != null)
        {
            loaf.SetFood(true, Cozy.Grid.FoodSpoil.Today + 4);
            var grp = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject> { fr, loaf };
            var recs = new System.Collections.Generic.List<Cozy.Grid.LevelIO.ObjectData>();
            foreach (var o in grp)
            {
                var od = (Cozy.Grid.LevelIO.ObjectData)mSnap.Invoke(null, new object[] { o });
                mFeat.Invoke(null, new object[] { o, od });
                if (mCarrier != null) mCarrier.Invoke(null, new object[] { o, od });
                recs.Add(od);
            }
            var lp = loaf.transform.position;
            var keep2 = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
            foreach (var o in grp) keep2.Remove(o);
            foreach (var o in grp) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject);
            UnityEngine.Physics.SyncTransforms();
            restore.Invoke(gc, new object[] { recs, false });
            UnityEngine.Physics.SyncTransforms();
            fr = null; loaf = null; int loaves = 0;
            foreach (var o in Cozy.Grid.InteractiveObject.All) if (o != null && !keep2.Contains(o) && !before.Contains(o)) { if (o.Def == fdef) fr = o; if (o.Def == loafDef) { loaf = o; loaves++; } }
            Check(fr != null && loaves == 1 && loaf != null && loaf.Container == fr, "PT-B04 " + fdef.id + ": после загрузки батонов " + loaves + ", в холодильнике " + (loaf != null && loaf.Container == fr));
            if (loaf != null)
            {
                Check(loaf.Spoiled && loaf.ExpiryDay == Cozy.Grid.FoodSpoil.Today + 4, "PT-B04 " + fdef.id + ": порча/срок после загрузки " + loaf.Spoiled + "/" + loaf.ExpiryDay + ", было true/" + (Cozy.Grid.FoodSpoil.Today + 4));
                Check((loaf.transform.position - lp).magnitude <= 0.001f, "PT-B04 " + fdef.id + ": батон сдвинулся на " + ((loaf.transform.position - lp).magnitude * 1000f).ToString("0") + " мм");
            }
            if (fr == null || loaf == null) continue;
            foreach (var f in fr.Features) if (f is Cozy.Grid.AccessFeature a2) a2.SetOpen(true);
        }
        // CNT02: резка на полке
        var lay = loafDef.cookLayouts.Find(l => l.productId == "kitchen_knife");
        var knife = Make(knifeDef, at + new UnityEngine.Vector3(0f, 0f, 3f));
        var known = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
        int s = lay != null ? (int)freeSlot.Invoke(null, new object[] { lay, loaf, null }) : -1;
        if (s < 0) { notes.Append("INFO PT-CNT02 " + fdef.id + ": на полке нет места под половину — «Порезать» не предлагается\n"); continue; }
        putOne.Invoke(gc, new object[] { lay, loaf, s, knife });
        UnityEngine.Physics.SyncTransforms();
        foreach (var o in Cozy.Grid.InteractiveObject.All)
            if (o != null && !known.Contains(o) && o.Def != null && o.Def.id.StartsWith("bread_part_"))
                Check(o.Container == fr, "PT-CNT02 " + fdef.id + ": половина после резки " + (o.Container != null ? "в " + o.Container.Def.id : "вне холодильника") + " у " + o.transform.position.ToString("F2"));
    }
}
catch (System.Exception e) { fails++; sb.Append("ОШИБКА ПРОБЫ на этапе " + stage + ": " + (e.InnerException ?? e).GetType().Name + " " + (e.InnerException ?? e).Message + "\n"); }
finally
{
    fGive.SetValue(null, oldGive);
    fStack.SetValue(null, oldStack);
    eaten.Clear(); foreach (var kv in eatenKeep) eaten[kv.Key] = kv.Value;
    if (circuit != null && circuits != null) circuits.Remove(circuit);
    if (hudRoot != null) foreach (UnityEngine.Transform c in new System.Collections.Generic.List<UnityEngine.Transform>(System.Linq.Enumerable.Cast<UnityEngine.Transform>(hudRoot))) if (!hudKids.Contains(c)) UnityEngine.Object.DestroyImmediate(c.gameObject);
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — продуктов " + defs.Count + ", спавнено " + spawned + ", подобрано кнопкой " + picked + ", резок " + cut + ", контейнеров " + containers + ", холодильников " + fridges + " (инвентарь игрока не трогали, созданное удалено)\n" + sb + notes;
