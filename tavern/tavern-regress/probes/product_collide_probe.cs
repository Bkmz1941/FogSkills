// ПОСТАНОВКА И ПЕРЕСЕЧЕНИЯ ПРОДУКТОВ (PRODUCTS.md, группы 1–2; 18.10). Для execute_code в play, любой уровень.
// Настоящий конвейер: `GridCursor.ComputeObjectPose` со СВОЕЙ камерой, повёрнутой так, чтобы луч через
// настоящий курсор шёл в цель (главную камеру и игрока не трогаем). Стенд — свой стол `office_desk` в своей
// зоне (этаж игрока, +400 м по X — за краем уровня); всё созданное удаляется в finally. Уровень не меняет и не сохраняет.
//  PT-POS02 у каждого продукта на столе при повороте 0/90/180/270° низ на столешнице ±5 мм;
//  PT-COL02 стоящий продукт не входит в стол (проникновение коллайдеров ≤ 6 мм);
//  PT-POS01 у края стола: красный ИЛИ центр продукта над столешницей;
//  PT-COL04/POS05 продукт на продукт: красный ИЛИ не пересекаются (≤ 6 мм), а если сверху — низ на верхе ±5 мм;
//  PT-COL01 продукты УРОВНЯ (только чтение), стоящие не в контейнере: попарно проникновение ≤ 6 мм.
// Первая строка — вердикт «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом кейса.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
if (gc == null) return "нет GridCursor";
var mouse = UnityEngine.InputSystem.Mouse.current;
if (mouse == null) return "нет мыши";
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var spawn = T.GetMethod("SpawnObject", B);
var mCompute = T.GetMethod("ComputeObjectPose", B);
var fYaw = T.GetField("_freeYaw", B);
var fOrient = T.GetField("_orient", B);
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0, skips = 0, edgeRed = 0, edgeOk = 0, stackRed = 0, stackTop = 0, stackSide = 0; float worstGap = 0f;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };

System.Func<UnityEngine.GameObject, UnityEngine.Bounds?> BoundsOf = go => {
    UnityEngine.Bounds b = default(UnityEngine.Bounds); bool any = false;
    foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>())
    {
        if (!r.enabled || !r.gameObject.activeInHierarchy || Cozy.Grid.InteractHighlight.IsCopy(r) || r is UnityEngine.ParticleSystemRenderer) continue;
        if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
    }
    return any ? b : (UnityEngine.Bounds?)null;
};
// наибольшее проникновение коллайдеров a в коллайдеры b (м); −1 — у кого-то нет коллайдеров
System.Func<UnityEngine.GameObject, UnityEngine.GameObject, float> Pen = (a, b) => {
    var ca = a.GetComponentsInChildren<UnityEngine.Collider>(); var cb = b.GetComponentsInChildren<UnityEngine.Collider>();
    if (ca.Length == 0 || cb.Length == 0) return -1f;
    float worst = 0f;
    foreach (var x in ca) foreach (var y in cb)
    {
        if (!x.enabled || !y.enabled || x.isTrigger || y.isTrigger) continue;
        if (UnityEngine.Physics.ComputePenetration(x, x.transform.position, x.transform.rotation, y, y.transform.position, y.transform.rotation, out var dir, out var dist))
            if (dist > worst) worst = dist;
    }
    return worst;
};

var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);

// PT-COL01: продукты уровня — только чтение
var levelProducts = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.Def != null && io.Container == null && (io.Def.isProduct || (io.Def.category ?? "").StartsWith(Cozy.Grid.Categories.Food))
        && io.GetComponentInParent<Cozy.Grid.InteractiveObject>() == io) levelProducts.Add(io);
int pairs = 0;
for (int i = 0; i < levelProducts.Count; i++)
    for (int j = i + 1; j < levelProducts.Count; j++)
    {
        var a = levelProducts[i]; var c = levelProducts[j];
        var ba = BoundsOf(a.gameObject); var bc = BoundsOf(c.gameObject);
        if (ba == null || bc == null || !ba.Value.Intersects(bc.Value)) continue;
        if (a.transform.IsChildOf(c.transform) || c.transform.IsChildOf(a.transform)) continue;
        pairs++;
        float p = Pen(a.gameObject, c.gameObject);
        if (p < 0f) { var x = ba.Value; var y = bc.Value; x.Expand(-0.012f); y.Expand(-0.012f); Check(!x.Intersects(y), "PT-COL01 " + a.Def.id + " и " + c.Def.id + " у " + a.transform.position.ToString("F2") + ": коробки пересекаются (коллайдеров нет)"); }
        else Check(p <= 0.006f, "PT-COL01 " + a.Def.id + " и " + c.Def.id + " у " + a.transform.position.ToString("F2") + ": входят друг в друга на " + (p * 1000f).ToString("0") + " мм");
    }
sb.Append("PT-COL01 продуктов уровня " + levelProducts.Count + ", соседних пар " + pairs + "\n");

var defs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && (d.isProduct || (d.category ?? "").StartsWith(Cozy.Grid.Categories.Food)) && d.mount == Cozy.Grid.ObjectMount.Surface) defs.Add(d);

var camGo = new UnityEngine.GameObject("product_collide_probe_cam");
var cam = camGo.AddComponent<UnityEngine.Camera>();
cam.enabled = false;
if (UnityEngine.Camera.main != null) cam.fieldOfView = UnityEngine.Camera.main.fieldOfView;
float oldYaw = (float)fYaw.GetValue(gc);
object oldOrient = fOrient != null ? fOrient.GetValue(gc) : null;
var player = Cozy.Grid.PlayerRef.Transform;
// пол зоны — на сетке этажей: поверхность ищется только ниже floorY + клетка, и пол «не на сетке» прятал стол
float placeFloor = (float)T.GetMethod("PlaceFloorY", B).Invoke(gc, null);
// ⚠️ зона НЕ под уровнем, а на этаже игрока за краем уровня (+400 м по X): ниже текущего этажа луч опоры
// (`SurfaceTopAt` → `Ignored`) стол не видит, и каждая поза красная — замер 18.10
var origin = new UnityEngine.Vector3((player != null ? player.position.x : 0f) + 400f, placeFloor, player != null ? player.position.z : 0f);
string verdictTail = "";
try
{
    var deskDef = Cozy.Grid.FurnitureCatalog.ById("office_desk");
    if (deskDef == null) return "SKIP: нет office_desk в каталоге";
    var desk = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { deskDef, origin, 0f });
    UnityEngine.Physics.SyncTransforms();
    var db = BoundsOf(desk.gameObject).Value;
    float top = float.NegativeInfinity;
    foreach (var h in UnityEngine.Physics.RaycastAll(new UnityEngine.Vector3(db.center.x, db.max.y + 1f, db.center.z), UnityEngine.Vector3.down, 3f))
        if (h.collider.transform.IsChildOf(desk.transform) && h.point.y > top) top = h.point.y;
    if (float.IsInfinity(top)) return "SKIP: у стола пробы нет коллайдера сверху";
    float floorY = origin.y;
    var parking = origin + new UnityEngine.Vector3(0f, -30f, 6f);

    // поставить body настоящим конвейером в точку target; вернуть (ok, blocked, pos, yaw)
    System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3, object[]> Pose = (io, target) => {
        cam.transform.position = target + new UnityEngine.Vector3(0.05f, 1.1f, -0.7f);
        cam.transform.rotation = UnityEngine.Quaternion.identity;
        var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
        cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(ray.direction, (target - cam.transform.position).normalized);
        var args = new object[] { io.Def, cam, mouse, io.gameObject, io.transform, floorY, null, null, null };
        bool ok = (bool)mCompute.Invoke(gc, args);
        return new object[] { ok, args[8], args[6], args[7] };
    };
    System.Action<Cozy.Grid.InteractiveObject, object[]> Apply = (io, r) => {
        io.transform.SetPositionAndRotation((UnityEngine.Vector3)r[2], UnityEngine.Quaternion.Euler(0f, (float)r[3], 0f));
        UnityEngine.Physics.SyncTransforms();
    };
    var mid = new UnityEngine.Vector3(db.center.x, top, db.center.z);
    int tested = 0;
    // PT-POS03: свободный пол уровня рядом с героем (только чтение: продукт ставится и сразу уходит)
    UnityEngine.Vector3? floorSpot = null;
    if (player != null)
        for (int ring = 2; ring < 10 && floorSpot == null; ring++)
            for (int a = 0; a < 12 && floorSpot == null; a++)
            {
                var p0 = player.position + UnityEngine.Quaternion.Euler(0f, a * 30f, 0f) * UnityEngine.Vector3.forward * ring;
                if (!UnityEngine.Physics.Raycast(p0 + UnityEngine.Vector3.up * 1.5f, UnityEngine.Vector3.down, out var fh, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) continue;
                if (fh.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null) continue;
                if (UnityEngine.Mathf.Abs(fh.point.y - placeFloor) > 0.3f) continue;
                if (UnityEngine.Physics.OverlapBox(fh.point + UnityEngine.Vector3.up * 0.45f, new UnityEngine.Vector3(0.6f, 0.4f, 0.6f), UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore).Length > 0) continue;
                floorSpot = fh.point;
            }
    if (floorSpot == null) sb.Append("SKIP PT-POS03: рядом с героем нет свободного пола своего этажа\n");
    int floorOk = 0, floorRed = 0, shelfOk = 0, shelfRed = 0;
    // PT-POS04: полки холодильников — свои экземпляры, дверцы открыты
    var shelves = new System.Collections.Generic.List<object[]>();
    int fi = 0;
    foreach (var fdef in Cozy.Grid.FurnitureCatalog.All())
    {
        if (fdef == null || string.IsNullOrEmpty(fdef.slotNodes) || fdef.slotNodes.IndexOf("Slot_Shelf1", System.StringComparison.Ordinal) < 0) continue;
        bool cold = false; if (fdef.tempSources != null) foreach (var ts in fdef.tempSources) if (ts.needsPower && ts.target < 5f) cold = true;
        if (!cold) continue;
        var fr = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { fdef, origin + new UnityEngine.Vector3(-6f - fi * 4f, 0f, 8f), 180f });
        fi++;
        if (fr == null) continue;
        foreach (var f in fr.Features) if (f is Cozy.Grid.AccessFeature acc) acc.SetOpen(true);
        var tickM = typeof(Cozy.Grid.InteractiveObject).GetMethod("Tick", B);
        if (tickM != null) for (int t = 0; t < 3000; t++) tickM.Invoke(fr, null);
        UnityEngine.Physics.SyncTransforms();
        foreach (var node in new[] { "Slot_Shelf1", "Slot_Shelf2", "Slot_Floor" })
        {
            var n = Cozy.Grid.FurnitureModel.FindNode(fr.transform, node);
            if (n != null) shelves.Add(new object[] { fr, node, n.position });
        }
    }
    foreach (var def in defs)
    {
        Cozy.Grid.InteractiveObject io = null;
        try { io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, parking + new UnityEngine.Vector3(tested * 1.2f, 0f, 0f), 0f }); } catch { }
        if (io == null) { skips++; sb.Append("SKIP " + def.id + ": не спавнится\n"); continue; }
        tested++;
        UnityEngine.Physics.SyncTransforms();
        // PT-POS02 + PT-COL02: четыре поворота в центре стола
        foreach (var yaw in new[] { 0f, 90f, 180f, 270f })
        {
            fYaw.SetValue(gc, yaw);
            if (fOrient != null) fOrient.SetValue(gc, System.Convert.ChangeType((int)(yaw / 90f), fOrient.FieldType));
            var r = Pose(io, mid);
            if (!(bool)r[0]) { Check(false, "PT-POS02 " + def.id + " " + yaw + "°: курсор мимо стола"); continue; }
            if ((bool)r[1]) { Check(false, "PT-POS02 " + def.id + " " + yaw + "°: красный на пустом столе"); continue; }
            Apply(io, r);
            var b = BoundsOf(io.gameObject);
            if (b == null) continue;
            float gap = b.Value.min.y - top;
            if (UnityEngine.Mathf.Abs(gap) > UnityEngine.Mathf.Abs(worstGap)) worstGap = gap;
            Check(UnityEngine.Mathf.Abs(gap) <= 0.005f, "PT-POS02 " + def.id + " " + yaw + "°: низ от столешницы " + (gap * 1000f).ToString("0") + " мм");
            float pen = Pen(io.gameObject, desk.gameObject);
            if (pen >= 0f) Check(pen <= 0.006f, "PT-COL02 " + def.id + " " + yaw + "°: входит в стол на " + (pen * 1000f).ToString("0") + " мм");
        }
        fYaw.SetValue(gc, 0f);
        if (fOrient != null) fOrient.SetValue(gc, System.Convert.ChangeType(0, fOrient.FieldType));
        // PT-POS01: у края стола (2 см от кромки по X)
        var edge = new UnityEngine.Vector3(db.max.x - 0.02f, top, db.center.z);
        var re = Pose(io, edge);
        if ((bool)re[0] && (bool)re[1]) edgeRed++;
        if ((bool)re[0] && !(bool)re[1])
        {
            edgeOk++;
            Apply(io, re);
            var b = BoundsOf(io.gameObject);
            if (b != null) Check(b.Value.center.x <= db.max.x + 0.001f, "PT-POS01 " + def.id + ": у края центр за кромкой на " + ((b.Value.center.x - db.max.x) * 100f).ToString("0.0") + " см, не красный");
        }
        // PT-COL04 / PT-POS05: тот же продукт на продукт
        Cozy.Grid.InteractiveObject other = null;
        try { other = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, parking + new UnityEngine.Vector3(tested * 1.2f, 0f, 1.5f), 0f }); } catch { }
        if (other != null)
        {
            UnityEngine.Physics.SyncTransforms();
            var r0 = Pose(io, mid);
            if ((bool)r0[0] && !(bool)r0[1])
            {
                Apply(io, r0);
                var bi = BoundsOf(io.gameObject).Value;
                var r1 = Pose(other, new UnityEngine.Vector3(bi.center.x, bi.max.y, bi.center.z));
                if ((bool)r1[0] && (bool)r1[1]) stackRed++;
                if ((bool)r1[0] && !(bool)r1[1])
                {
                    Apply(other, r1);
                    var bo = BoundsOf(other.gameObject).Value;
                    float pen = Pen(io.gameObject, other.gameObject);
                    if (pen >= 0f) Check(pen <= 0.006f, "PT-COL04 " + def.id + " на " + def.id + ": входят друг в друга на " + (pen * 1000f).ToString("0") + " мм, не красный");
                    else { var x = bi; var y = bo; x.Expand(-0.012f); y.Expand(-0.012f); Check(!x.Intersects(y), "PT-COL04 " + def.id + " на " + def.id + ": коробки пересекаются, не красный"); }
                    bool onTop = bo.min.y > bi.min.y + 0.01f;
                    if (onTop) stackTop++; else stackSide++;
                    if (onTop) Check(UnityEngine.Mathf.Abs(bo.min.y - bi.max.y) <= 0.005f || pen >= 0f && pen <= 0.006f, "PT-POS05 " + def.id + " на " + def.id + ": низ верхнего от верха нижнего " + ((bo.min.y - bi.max.y) * 1000f).ToString("0") + " мм");
                }
            }
            UnityEngine.Object.DestroyImmediate(other.gameObject);
        }
        fYaw.SetValue(gc, 0f);
        if (floorSpot != null)
        {
            var rf = Pose(io, floorSpot.Value);
            if ((bool)rf[0] && (bool)rf[1]) floorRed++;
            if ((bool)rf[0] && !(bool)rf[1])
            {
                floorOk++;
                Apply(io, rf);
                var bf = BoundsOf(io.gameObject);
                if (bf != null) Check(UnityEngine.Mathf.Abs(bf.Value.min.y - floorSpot.Value.y) <= 0.005f, "PT-POS03 " + def.id + ": на полу низ от пола " + ((bf.Value.min.y - floorSpot.Value.y) * 1000f).ToString("0") + " мм");
            }
            io.transform.position = parking + new UnityEngine.Vector3(tested * 1.2f, 0f, 3f);
            UnityEngine.Physics.SyncTransforms();
        }
        foreach (var sh in shelves)
        {
            var fr = (Cozy.Grid.InteractiveObject)sh[0]; var node = (string)sh[1]; var at = (UnityEngine.Vector3)sh[2];
            var rs = Pose(io, at);
            if (!(bool)rs[0]) continue;
            if ((bool)rs[1]) { shelfRed++; continue; }
            shelfOk++;
            Apply(io, rs);
            var bs = BoundsOf(io.gameObject);
            var fb = BoundsOf(fr.gameObject);
            if (bs == null || fb == null) continue;
            float sup = float.NegativeInfinity;
            foreach (var h in UnityEngine.Physics.RaycastAll(new UnityEngine.Vector3(bs.Value.center.x, bs.Value.max.y + 0.3f, bs.Value.center.z), UnityEngine.Vector3.down, 3f, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
                if (h.collider.transform.IsChildOf(fr.transform) && h.point.y <= bs.Value.min.y + 0.03f && h.point.y > sup) sup = h.point.y;
            Check(!float.IsInfinity(sup) && UnityEngine.Mathf.Abs(bs.Value.min.y - sup) <= 0.005f, "PT-POS04 " + fr.Def.id + "/" + node + " " + def.id + ": низ от полки " + (float.IsInfinity(sup) ? "полки под ним нет" : ((bs.Value.min.y - sup) * 1000f).ToString("0") + " мм"));
            Check(bs.Value.center.x > fb.Value.min.x && bs.Value.center.x < fb.Value.max.x && bs.Value.center.z > fb.Value.min.z && bs.Value.center.z < fb.Value.max.z, "PT-POS04 " + fr.Def.id + "/" + node + " " + def.id + ": центр продукта вне холодильника");
            // корпус холодильника — сплошной бокс, проникновение в него по построению; ловим вылет за стенки
            float outX = UnityEngine.Mathf.Max(fb.Value.min.x - bs.Value.min.x, bs.Value.max.x - fb.Value.max.x), outZ = UnityEngine.Mathf.Max(fb.Value.min.z - bs.Value.min.z, bs.Value.max.z - fb.Value.max.z);
            Check(outX <= 0.005f && outZ <= 0.005f, "PT-POS04 " + fr.Def.id + "/" + node + " " + def.id + ": вылезает за стенку холодильника на " + (UnityEngine.Mathf.Max(outX, outZ) * 1000f).ToString("0") + " мм, не красный");
            io.transform.position = parking + new UnityEngine.Vector3(tested * 1.2f, 0f, 3f);
            UnityEngine.Physics.SyncTransforms();
        }
        UnityEngine.Object.DestroyImmediate(io.gameObject);
        UnityEngine.Physics.SyncTransforms();
    }
    verdictTail = "продуктов прогнано " + tested + " из " + defs.Count + "; худший зазор низа " + (worstGap * 1000f).ToString("0.0") + " мм; у края красных " + edgeRed + ", поставлено " + edgeOk + "; продукт на продукт: красных " + stackRed + ", сверху " + stackTop + ", рядом " + stackSide + "; на полу поставлено " + floorOk + ", красных " + floorRed + "; полок холодильников " + shelves.Count + ": поставлено " + shelfOk + ", красных " + shelfRed;
}
finally
{
    fYaw.SetValue(gc, oldYaw);
    if (fOrient != null && oldOrient != null) fOrient.SetValue(gc, oldOrient);
    UnityEngine.Object.DestroyImmediate(camGo);
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — " + verdictTail + ", пропусков " + skips + " (созданное удалено)\n" + sb;
