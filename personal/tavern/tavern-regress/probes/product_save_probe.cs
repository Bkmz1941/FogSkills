// СОХРАНЕНИЕ, ИНВЕНТАРЬ И СЧЁТЧИКИ ПРОДУКТОВ (PRODUCTS.md, группы 4, 8, 9; 18.10). Для execute_code в play, любой уровень.
// Файл уровня НЕ пишется: свои продукты снимаются той же записью, что сейв (`LevelIO.Snapshot` + `CollectFeatures`
// + `CollectCarrier`), уничтожаются и поднимаются тем же `GridCursor.RestoreObjects`, что загрузка уровня.
// Инвентарь — тем же путём данных, что «Подобрать» / «Выложить» (`LiquidState.Of/Apply` + `TakePieces/DropPieces`).
// Зона — этаж игрока, +400 м по X и +40 по Z (за краем уровня), всё созданное удаляется в finally.
//  PT-SAVE01 позиция ±1 мм, поворот ±0,5°;  PT-SAVE02 число продуктов до = после, дублей нет;
//  PT-SAVE03 счётчик, испорченность, срок, жидкость, состояние — прежние;
//  PT-QTY01 пачка на N: −3 → N−3, и столько же после сейва;
//  PT-A03/INV03 «подобрать → выложить» ×5: счётчик, испорченность, срок, жидкость не меняются.
// Первая строка — вердикт «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом кейса.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var BS = System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var spawn = T.GetMethod("SpawnObject", B);
var restore = T.GetMethod("RestoreObjects", B);
var tIO = typeof(Cozy.Grid.LevelIO);
var mSnap = tIO.GetMethod("Snapshot", BS);
var mFeat = tIO.GetMethod("CollectFeatures", BS);
var mCarrier = tIO.GetMethod("CollectCarrier", BS);
if (restore == null || mSnap == null || mFeat == null) return "КРАСНОЕ: нет методов сейва (RestoreObjects/Snapshot/CollectFeatures) — проба умерла";
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };
System.Func<Cozy.Grid.InteractiveObject, string> StateOf = io =>
    "count=" + (io.HasCount ? io.Count.ToString() : "-") + " spoiled=" + io.Spoiled + " expiry=" + io.ExpiryDay
    + " liquid=" + (io.Liquid != null ? io.Liquid.Kind + ":" + io.Liquid.Litres.ToString("0.000") : "-") + " state=" + (io.ProductState ?? "-");

var defs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && (d.isProduct || (d.category ?? "").StartsWith(Cozy.Grid.Categories.Food))) defs.Add(d);
var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var player = Cozy.Grid.PlayerRef.Transform;
float placeFloor = (float)T.GetMethod("PlaceFloorY", B).Invoke(gc, null);
var origin = new UnityEngine.Vector3((player != null ? player.position.x : 0f) + 400f, placeFloor, (player != null ? player.position.z : 0f) + 40f);
int qty = 0, inv = 0, saved = 0;
try
{
    // свои продукты с непустым состоянием
    var mine = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    int k = 0;
    foreach (var def in defs)
    {
        Cozy.Grid.InteractiveObject io = null;
        var p = origin + new UnityEngine.Vector3((k % 10) * 1.3f + 0.137f * (k % 3), 0f, (k / 10) * 1.3f + 0.071f * (k % 5));
        try { io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, p, 37f * k + 11.3f }); } catch { }
        k++;
        if (io == null) continue;
        if (io.HasCount && def.countMax >= 3)
        {
            io.SetCount(def.countMax - 3);
            qty++;
            Check(io.Count == UnityEngine.Mathf.Max(def.countMin, def.countMax - 3), "PT-QTY01 " + def.id + ": из пачки на " + def.countMax + " вынули 3, осталось " + io.Count);
        }
        if (Cozy.Grid.FoodSpoil.Perishable(def)) io.SetFood(k % 2 == 0, Cozy.Grid.FoodSpoil.Today + 3 + k % 4);
        if (io.Liquid != null && io.Liquid.Litres > 0.01f) io.Liquid.Set(io.Liquid.Kind, io.Liquid.Litres * 0.6f);
        mine.Add(io);
    }
    UnityEngine.Physics.SyncTransforms();

    // PT-A03 / PT-INV03: подобрать → выложить ×5 тем же путём данных, что инвентарь
    foreach (var src in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(mine))
    {
        var def = src.Def;
        var item = Cozy.Grid.Items.ById(def.pickupItemId);
        if (item == null) continue;
        inv++;
        string want = StateOf(src);
        var cur = src;
        var probeCopy = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, src.transform.position + UnityEngine.Vector3.up * 30f, 0f });
        // копия состояния, которую гоняем (оригинал остаётся для сейва)
        probeCopy.SetCount(src.Count);
        probeCopy.SetFood(src.Spoiled, src.ExpiryDay);
        if (src.Liquid != null && probeCopy.Liquid != null) probeCopy.Liquid.UnpackParts(src.Liquid.PackParts());
        cur = probeCopy;
        string first = StateOf(cur);
        for (int round = 0; round < 5; round++)
        {
            var placed = new Cozy.Grid.PlacedItem { def = item, charge = item.FullCharge };
            placed.state = Cozy.Grid.LiquidState.Of(cur);
            Cozy.Grid.InteractiveObject.TakePieces(cur, placed);
            var at = cur.transform.position;
            UnityEngine.Object.DestroyImmediate(cur.gameObject);
            cur = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, at, 0f });
            if (!string.IsNullOrEmpty(placed.state)) Cozy.Grid.LiquidState.Apply(cur, placed.state);
            Cozy.Grid.InteractiveObject.DropPieces(cur, placed);
        }
        string got = StateOf(cur);
        Check(got == first, "PT-INV03 " + def.id + ": после 5 кругов «подобрать → выложить» было [" + first + "], стало [" + got + "]");
    }

    // PT-SAVE01–03: снимок → уничтожить → поднять
    var records = new System.Collections.Generic.List<Cozy.Grid.LevelIO.ObjectData>();
    var expect = new System.Collections.Generic.List<string>();
    var poses = new System.Collections.Generic.List<UnityEngine.Vector3>();
    var yaws = new System.Collections.Generic.List<float>();
    foreach (var io in mine)
    {
        var od = (Cozy.Grid.LevelIO.ObjectData)mSnap.Invoke(null, new object[] { io });
        mFeat.Invoke(null, new object[] { io, od });
        if (mCarrier != null) mCarrier.Invoke(null, new object[] { io, od });
        records.Add(od);
        expect.Add(io.Def.id + " " + StateOf(io));
        poses.Add(io.transform.position);
        yaws.Add(io.transform.eulerAngles.y);
    }
    saved = records.Count;
    var keep = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
    foreach (var io in mine) { keep.Remove(io); UnityEngine.Object.DestroyImmediate(io.gameObject); }
    UnityEngine.Physics.SyncTransforms();
    restore.Invoke(gc, new object[] { records, false });
    UnityEngine.Physics.SyncTransforms();
    var back = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    foreach (var io in Cozy.Grid.InteractiveObject.All)
        if (io != null && !keep.Contains(io) && !before.Contains(io) && io.Def != null) back.Add(io);
    int productsBack = 0;
    foreach (var io in back) if (defs.Contains(io.Def)) productsBack++;
    Check(productsBack == records.Count, "PT-SAVE02 продуктов до сейва " + records.Count + ", после загрузки " + productsBack + " (всего поднято объектов " + back.Count + ")");
    for (int i = 0; i < records.Count; i++)
    {
        Cozy.Grid.InteractiveObject best = null; float bestD = float.MaxValue;
        foreach (var io in back)
        {
            if (io.Def.id != records[i].id) continue;
            float d = UnityEngine.Vector3.Distance(io.transform.position, poses[i]);
            if (d < bestD) { bestD = d; best = io; }
        }
        if (best == null) { Check(false, "PT-SAVE02 " + records[i].id + ": не поднялся"); continue; }
        back.Remove(best);
        Check(bestD <= 0.001f, "PT-SAVE01 " + records[i].id + ": позиция ушла на " + (bestD * 1000f).ToString("0.0") + " мм");
        float dy = UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(best.transform.eulerAngles.y, yaws[i]));
        Check(dy <= 0.5f, "PT-SAVE01 " + records[i].id + ": поворот ушёл на " + dy.ToString("0.0") + "°");
        string got = best.Def.id + " " + StateOf(best);
        Check(got == expect[i], "PT-SAVE03 было [" + expect[i] + "], стало [" + got + "]");
    }
}
finally
{
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — продуктов " + defs.Count + ", в сейве " + saved + ", пачек " + qty + ", кругов инвентаря " + inv + " (файл уровня не писался, созданное удалено)\n" + sb;
