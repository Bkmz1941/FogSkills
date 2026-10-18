if (!UnityEngine.Application.isPlaying) return "не в play";
// стенд — только products_test: на боевых уровнях продукты в шкафах и на полках, A01 там красный не по делу (PRODUCTS.md)
if (Cozy.Grid.LevelIO.CurrentSlug != "products_test") return "SKIP: уровень «" + Cozy.Grid.LevelIO.CurrentSlug + "», проба гоняется на products_test";
var sb = new System.Text.StringBuilder();
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var NS = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var GC = typeof(Cozy.Grid.GridCursor);
var spawn = GC.GetMethod("SpawnObject", NP);
var putOne = GC.GetMethod("PutOneIntoLayout", NP);
var freeSlot = GC.GetMethod("LayoutFreeSlot", NS);
var cursor = Cozy.Grid.GridCursor.I;
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };

var products = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.Def != null && io.Def.isProduct && io.Container == null) products.Add(io);
var ids = new System.Collections.Generic.HashSet<string>();
foreach (var io in products)
{
    ids.Add(io.Def.id);
    var b = new UnityEngine.Bounds(); bool first = true;
    foreach (var r in io.GetComponentsInChildren<UnityEngine.Renderer>())
    {
        if (!r.enabled || Cozy.Grid.InteractHighlight.IsCopy(r)) continue;
        if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
    }
    if (first) continue;
    float support = float.NegativeInfinity;
    foreach (var h in UnityEngine.Physics.RaycastAll(new UnityEngine.Vector3(b.center.x, b.max.y + 0.5f, b.center.z), UnityEngine.Vector3.down, 3f))
    {
        if (h.collider.transform.IsChildOf(io.transform)) continue;
        if (h.point.y <= b.min.y + 0.05f && h.point.y > support) support = h.point.y;
    }
    float gap = b.min.y - support;
    Check(!float.IsInfinity(support) && UnityEngine.Mathf.Abs(gap) <= 0.005f, "PT-A01 " + io.Def.id + " у " + io.transform.position.ToString("F2") + ": низ от опоры " + (gap * 100f).ToString("0.0") + " см");
}
sb.Append("PT-A01 продуктов на стенде: " + products.Count + "\n");
var structureClear = typeof(Cozy.Character.CameraFollow).GetMethod("StructureClear", NS);
int stuck = 0;
foreach (var io in products)
{
    var f = io.transform.position + UnityEngine.Vector3.up * 0.05f;
    for (int yaw = 0; yaw < 360; yaw += 30)
        if ((float)structureClear.Invoke(null, new object[] { f, (float)yaw, 15f, 1.0f }) < 0.995f) { stuck++; break; }
}
Check(stuck == 0, "PT-A04 осмотр: поворот упирается у продуктов " + stuck);
sb.Append("PT-A04 осмотр крутится 360° у " + (products.Count - stuck) + " из " + products.Count + "\n");

foreach (var extra in new[] { "bread_loaf", "bread_part_4", "bread_part_2", "bread_part_1" }) ids.Add(extra);
foreach (var id in ids)
{
    var def = Cozy.Grid.FurnitureCatalog.ById(id);
    var item = Cozy.Grid.Items.ById(def != null && !string.IsNullOrEmpty(def.pickupItemId) ? def.pickupItemId : id);
    if (item == null) { Check(false, "PT-A02 " + id + ": нет предмета инвентаря"); continue; }
    bool icon = UnityEngine.Resources.Load<UnityEngine.Sprite>("Icons/" + item.icon) != null;
    Check(icon, "PT-A02 " + id + ": иконка «" + item.icon + "» не найдена в Resources/Icons");
    if (id == "bread_loaf") Check(item.size == new UnityEngine.Vector2Int(2, 1), "PT-A02 bread_loaf: размер " + item.size + ", ждали 2×1");
    if (id.StartsWith("bread_part_")) Check(item.size == new UnityEngine.Vector2Int(1, 1), "PT-A02 " + id + ": размер " + item.size + ", ждали 1×1");
}
sb.Append("PT-A02 предметов проверено: " + ids.Count + "\n");

var made = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
try
{
    UnityEngine.Vector3 spot = UnityEngine.Vector3.zero; bool found = false;
    UnityEngine.Transform spawnMark = null;
    foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def != null && io.Def.id == "spawn_marker") spawnMark = io.transform;
    var origin = spawnMark != null ? spawnMark.position : UnityEngine.Vector3.zero;
    for (int ring = 2; ring < 12 && !found; ring++)
        for (int k = 0; k < 8 && !found; k++)
        {
            var p = origin + UnityEngine.Quaternion.Euler(0f, k * 45f, 0f) * UnityEngine.Vector3.forward * ring;
            if (!UnityEngine.Physics.Raycast(p + UnityEngine.Vector3.up * 3f, UnityEngine.Vector3.down, out var hit, 6f)) continue;
            if (hit.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null) continue;
            if (UnityEngine.Physics.OverlapBox(hit.point + UnityEngine.Vector3.up * 0.3f, new UnityEngine.Vector3(1.2f, 0.25f, 1.2f)).Length > 0) continue;
            spot = hit.point; found = true;
        }
    if (!found) { Check(false, "PT-C: нет свободного пола под резку"); }
    else
    {
        var loaf = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { Cozy.Grid.FurnitureCatalog.ById("bread_loaf"), spot, 0f });
        var knife = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { Cozy.Grid.FurnitureCatalog.ById("kitchen_knife"), spot + UnityEngine.Vector3.right * 2.5f, 0f });
        UnityEngine.Physics.SyncTransforms();
        var pieces = new System.Collections.Generic.Dictionary<string, int> { { "bread_loaf", 8 }, { "bread_part_4", 4 }, { "bread_part_2", 2 }, { "bread_part_1", 1 } };
        int cuts = 0;
        for (int guard = 0; guard < 20; guard++)
        {
            Cozy.Grid.InteractiveObject target = null;
            foreach (var io in Cozy.Grid.InteractiveObject.All)
                if (io != null && io.Def != null && !before.Contains(io) && pieces.ContainsKey(io.Def.id) && io.Def.id != "bread_part_1") { target = io; break; }
            if (target == null) break;
            Cozy.Grid.CookLayout layout = null;
            foreach (var l in target.Def.cookLayouts) if (l.productId == "kitchen_knife") layout = l;
            if (layout == null) { Check(false, "PT-C01 " + target.Def.id + ": нет «Порезать»"); break; }
            Check(layout.actionLabel == "Порезать", "PT-C01 " + target.Def.id + ": подпись «" + layout.actionLabel + "»");
            int slot = (int)freeSlot.Invoke(null, new object[] { layout, target, null });
            if (slot < 0) { Check(false, "PT-C06 " + target.Def.id + ": на открытом полу не нашлось места для половины"); break; }
            putOne.Invoke(cursor, new object[] { layout, target, slot, knife });
            UnityEngine.Object.DestroyImmediate(target.gameObject);
            UnityEngine.Physics.SyncTransforms();
            cuts++;
        }
        int total = 0, partOne = 0;
        var halves = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
        foreach (var io in Cozy.Grid.InteractiveObject.All)
            if (io != null && io.Def != null && !before.Contains(io) && pieces.ContainsKey(io.Def.id)) { total += pieces[io.Def.id]; halves.Add(io); if (io.Def.id == "bread_part_1") partOne++; }
        Check(cuts == 7, "PT-C03 резов " + cuts + ", ждали 7");
        Check(total == 8 && partOne == 8, "PT-C03 кусков всего " + total + ", кусков батона " + partOne + ", ждали 8 и 8");
        int overlaps = 0;
        for (int i = 0; i < halves.Count; i++)
            for (int j = i + 1; j < halves.Count; j++)
            {
                var a = halves[i].GetComponentInChildren<UnityEngine.Renderer>().bounds; var c = halves[j].GetComponentInChildren<UnityEngine.Renderer>().bounds;
                a.Expand(-0.006f); c.Expand(-0.006f);
                if (a.Intersects(c)) overlaps++;
            }
        Check(overlaps == 0, "PT-C06 куски входят друг в друга: пар " + overlaps);
        sb.Append("PT-C резка батона: резов " + cuts + ", кусков " + total + "\n");
        Check(Cozy.Grid.FurnitureCatalog.ById("bread_part_1").cookLayouts.Count == 0, "PT-C03 у куска есть «Порезать»");
    }
}
finally
{
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ" : "КРАСНОЕ: " + fails) + " — проверок " + checks + " (созданное удалено)\n" + sb;
