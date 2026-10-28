// ПОСТАНОВКА ОДЕЖДЫ (CLOTHING.md, группы 1–3; 18.10). Для execute_code в play, любой уровень.
// Настоящий конвейер: `GridCursor.ComputeObjectPose` со СВОЕЙ камерой, повёрнутой так, чтобы луч через
// настоящий курсор шёл в цель. Стенд свой: стол, все кровати (`bed`), все шкафы (id с «wardrobe») и вешалка —
// в зоне на этаже игрока за краем уровня (+400 м по X); дверцы распахнуты сразу (позы частей доводятся
// рефлексией). Всё созданное удаляется в finally. Уровень не меняет и не сохраняет.
// Вещи — все дефы, которые подбираются в носимый слот или лежат в категории «Одежда» (новая вещь попадает сама).
//  CL-POS01 на полу: не красный, низ на полу ±5 мм;
//  CL-POS02 на столе 0/90/180/270°: не красный, низ на столешнице ±5 мм, в стол не входит (≤ 6 мм);
//  CL-BED01 на каждой кровати: не красный, не висит над постелью (≤ 2 см), в неё не тонет (≤ 3 см);
//  CL-STK01 сложенная на сложенную (та же и джинсы): НЕ красный, сверху, без провала (≤ 3 см) и без зазора (≤ 2 см);
//  CL-STK02 обувь на вещь: красный или сверху;
//  CL-SIDE01 рядом с лежащей вплотную (3 см): не красный, не пересекаются;
//  CL-WRD01 каждая полка/дно каждого шкафа: ставится (сводка по полкам), низ на доске ±5 мм, внутри шкафа,
//           в доски не входит; у шкафа со стопками (`WardrobePile`) вещь внутри числится в горке (видна через проём).
// Первая строка — вердикт, дальше сводка по полкам и FAIL с кодом кейса.
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
var IO = typeof(Cozy.Grid.InteractiveObject);
var fMoving = IO.GetField("_moving", B);
var mSetPartPose = IO.GetMethod("SetPartPose", B);
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };

System.Func<UnityEngine.GameObject, UnityEngine.Bounds?> BoundsOf = go => {
    // видимые рендеры; выключенные (скрытые части модели) — только если видимых нет (вещь в закрытом шкафу)
    UnityEngine.Bounds b = default(UnityEngine.Bounds); bool any = false;
    for (int pass = 0; pass < 2 && !any; pass++)
        foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>(pass == 1))
        {
            if (Cozy.Grid.InteractHighlight.IsCopy(r) || r is UnityEngine.ParticleSystemRenderer || r.name == "OutlineMask" || r.name == "OutlineBand") continue;
            if (pass == 0 && !r.enabled) continue;
            if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
        }
    return any ? b : (UnityEngine.Bounds?)null;
};
System.Func<UnityEngine.GameObject, UnityEngine.GameObject, float> Pen = (a, b) => {
    var ca = a.GetComponentsInChildren<UnityEngine.Collider>(); var cb = b.GetComponentsInChildren<UnityEngine.Collider>();
    if (ca.Length == 0 || cb.Length == 0) return -1f;
    float worst = 0f;
    foreach (var x in ca) foreach (var y in cb)
    {
        if (!x.enabled || !y.enabled || x.isTrigger || y.isTrigger) continue;
        if (x.transform.IsChildOf(b.transform) || y.transform.IsChildOf(a.transform)) continue;
        if (UnityEngine.Physics.ComputePenetration(x, x.transform.position, x.transform.rotation, y, y.transform.position, y.transform.rotation, out var dir, out var dist))
            if (dist > worst) worst = dist;
    }
    return worst;
};
// опора под точкой: верхняя нетриггерная поверхность host не выше `below`
System.Func<UnityEngine.Transform, UnityEngine.Vector3, float, float> SupportY = (host, at, below) => {
    float sup = float.NegativeInfinity;
    foreach (var h in UnityEngine.Physics.RaycastAll(new UnityEngine.Vector3(at.x, below + 0.25f, at.z), UnityEngine.Vector3.down, 2f, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
        if ((host == null || h.collider.transform.IsChildOf(host)) && h.point.y <= below + 0.03f && h.point.y > sup) sup = h.point.y;
    return sup;
};

var defs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
{
    if (d == null || d.mount != Cozy.Grid.ObjectMount.Surface || d.NeedsHost) continue;
    var it = string.IsNullOrEmpty(d.pickupItemId) ? null : Cozy.Grid.Items.ById(d.pickupItemId);
    bool worn = it != null && it.slot != Cozy.Grid.EquipSlot.None;
    if (worn || d.category == Cozy.Grid.Categories.Clothing) defs.Add(d);
}
System.Func<Cozy.Grid.ObjectDef, bool> Folded = d => d.drapes;
System.Func<Cozy.Grid.ObjectDef, bool> Shoes = d => { var it = Cozy.Grid.Items.ById(d.pickupItemId); return it != null && it.slot == Cozy.Grid.EquipSlot.Feet; };

var hostDefs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && d.mount == Cozy.Grid.ObjectMount.Floor && (d.bed || d.id.Contains("wardrobe") || d.id == "hallway_rack")) hostDefs.Add(d);

var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var camGo = new UnityEngine.GameObject("clothes_place_probe_cam");
var cam = camGo.AddComponent<UnityEngine.Camera>();
cam.enabled = false;
if (UnityEngine.Camera.main != null) cam.fieldOfView = UnityEngine.Camera.main.fieldOfView;
float oldYaw = (float)fYaw.GetValue(gc);
object oldOrient = fOrient != null ? fOrient.GetValue(gc) : null;
var player = Cozy.Grid.PlayerRef.Transform;
float placeFloor = (float)T.GetMethod("PlaceFloorY", B).Invoke(gc, null);
var origin = new UnityEngine.Vector3((player != null ? player.position.x : 0f) + 400f, placeFloor, player != null ? player.position.z : 0f);
string tail = "";
bool oldTrace = Cozy.Grid.GridCursor.TracePoses;
Cozy.Grid.GridCursor.TracePoses = true;
try
{
    var parking = origin + new UnityEngine.Vector3(0f, -30f, -10f);
    // Pose: камера в camPos, луч через настоящий курсор — в target
    System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3, UnityEngine.Vector3, object[]> PoseFrom = (io, target, camPos) => {
        cam.transform.position = camPos;
        cam.transform.rotation = UnityEngine.Quaternion.identity;
        var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
        cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(ray.direction, (target - camPos).normalized);
        var args = new object[] { io.Def, cam, mouse, io.gameObject, io.transform, origin.y, null, null, null };
        bool ok = (bool)mCompute.Invoke(gc, args);
        return new object[] { ok, args[8], args[6], args[7] };
    };
    System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3, object[]> Pose = (io, target) => PoseFrom(io, target, target + new UnityEngine.Vector3(0.05f, 1.1f, -0.7f));
    System.Action<Cozy.Grid.InteractiveObject, object[]> Apply = (io, r) => {
        io.transform.SetPositionAndRotation((UnityEngine.Vector3)r[2], UnityEngine.Quaternion.Euler(0f, (float)r[3], 0f));
        UnityEngine.Physics.SyncTransforms();
    };
    System.Action<Cozy.Grid.InteractiveObject, int> Park = (io, k) => { io.transform.position = parking + new UnityEngine.Vector3(k * 1.5f, 0f, 0f); UnityEngine.Physics.SyncTransforms(); };
    System.Action<Cozy.Grid.InteractiveObject> OpenAll = host => {
        foreach (var f in host.Features) if (f is Cozy.Grid.AccessFeature a && !a.Locked) a.SetOpen(true);
        var list = fMoving.GetValue(host) as System.Collections.IList;
        if (list == null) return;
        foreach (var m in list)
        {
            var mt = m.GetType();
            var acc = mt.GetField("access").GetValue(m) as Cozy.Grid.AccessFeature;
            if (acc == null || !acc.Open) continue;
            mt.GetField("t").SetValue(m, 1f);
            mSetPartPose.Invoke(host, new object[] { m, 1f });
        }
        UnityEngine.Physics.SyncTransforms();
    };

    // свой стенд
    var desk = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { Cozy.Grid.FurnitureCatalog.ById("office_desk"), origin, 0f });
    UnityEngine.Physics.SyncTransforms();
    var db = BoundsOf(desk.gameObject).Value;
    float deskTop = SupportY(desk.transform, db.center, db.max.y + 0.01f);
    var hosts = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    for (int i = 0; i < hostDefs.Count; i++)
    {
        Cozy.Grid.InteractiveObject h = null;
        try { h = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { hostDefs[i], origin + new UnityEngine.Vector3(6f + (i % 6) * 6f, 0f, 6f + (i / 6) * 7f), 0f }); } catch { }
        if (h == null) { info.Append("SKIP хозяин " + hostDefs[i].id + ": не спавнится\n"); continue; }
        OpenAll(h);
        hosts.Add(h);
    }
    UnityEngine.Physics.SyncTransforms();

    // видимая поверхность кровати — временные MeshCollider на её мешах (коробки по узлам могут врать, P250)
    var bedMesh = new System.Collections.Generic.Dictionary<Cozy.Grid.InteractiveObject, System.Collections.Generic.List<UnityEngine.MeshCollider>>();
    foreach (var h in hosts)
    {
        if (!h.Def.bed) continue;
        var list = new System.Collections.Generic.List<UnityEngine.MeshCollider>();
        foreach (var mf in h.GetComponentsInChildren<UnityEngine.MeshFilter>())
        {
            if (mf.sharedMesh == null || mf.name == "OutlineMask" || mf.name == "OutlineBand" || mf.name == "OutlineHull") continue;
            var tmp = new UnityEngine.GameObject("clothes_probe_mesh");
            tmp.layer = 2;
            tmp.transform.SetParent(mf.transform, false);
            var mc = tmp.AddComponent<UnityEngine.MeshCollider>(); mc.sharedMesh = mf.sharedMesh; mc.enabled = false;
            list.Add(mc);
        }
        bedMesh[h] = list;
    }
    System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3, float, float> VisibleY = (h, at, from) => {
        float best = float.NegativeInfinity;
        foreach (var mc in bedMesh[h])
        {
            mc.enabled = true;
            if (mc.Raycast(new UnityEngine.Ray(new UnityEngine.Vector3(at.x, from + 0.3f, at.z), UnityEngine.Vector3.down), out var mh, 3f) && mh.point.y > best && mh.point.y <= from + 0.03f) best = mh.point.y;
            mc.enabled = false;
        }
        return best;
    };
    // поверхности хозяина: все горизонтальные доски его коллайдеров по сетке 5×5, кластер по высоте 3 см,
    // в кластере — точка ближе к центру; к каждой ищется камера, которой цель видна (спереди/сзади/сбоку/сверху)
    var spots = new System.Collections.Generic.List<object[]>(); // host, target, camPos, name
    foreach (var h in hosts)
    {
        // габарит хозяина — по его нетриггерным коллайдерам: распахнутые створки (триггеры) раздували бы его вперёд
        var hb = BoundsOf(h.gameObject).Value; bool firstCol = true;
        foreach (var cc in h.GetComponentsInChildren<UnityEngine.Collider>())
        {
            if (cc.isTrigger || !cc.enabled) continue;
            if (firstCol) { hb = cc.bounds; firstCol = false; } else hb.Encapsulate(cc.bounds);
        }
        // все горизонтальные доски по сетке 7×5, кластер по высоте 3 см; в кластере держим все точки
        var levels = new System.Collections.Generic.List<UnityEngine.Vector3>();
        var members = new System.Collections.Generic.List<System.Collections.Generic.List<UnityEngine.Vector3>>();
        for (int ix = 0; ix < 7; ix++) for (int iz = 0; iz < 5; iz++)
        {
            var p = new UnityEngine.Vector3(UnityEngine.Mathf.Lerp(hb.min.x + 0.12f, hb.max.x - 0.12f, ix / 6f), hb.max.y + 0.5f, UnityEngine.Mathf.Lerp(hb.min.z + 0.12f, hb.max.z - 0.12f, iz / 4f));
            foreach (var hit in UnityEngine.Physics.RaycastAll(p, UnityEngine.Vector3.down, hb.size.y + 1f, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
            {
                if (!hit.collider.transform.IsChildOf(h.transform) || hit.normal.y < 0.85f || hit.point.y < hb.min.y + 0.05f) continue;
                int k = levels.FindIndex(v => UnityEngine.Mathf.Abs(v.y - hit.point.y) < 0.03f);
                if (k < 0) { levels.Add(hit.point); members.Add(new System.Collections.Generic.List<UnityEngine.Vector3> { hit.point }); }
                else members[k].Add(hit.point);
            }
        }
        // представитель уровня — точка с наибольшим запасом до чужих досок вокруг (не на перегородке и не у боковины)
        for (int k = 0; k < levels.Count && !h.Def.bed; k++)
        {
            float best = -1f;
            foreach (var m in members[k])
            {
                float room = 0f;
                for (float r = 0.05f; r <= 0.6f; r += 0.05f)
                {
                    bool clear = true;
                    foreach (var c in UnityEngine.Physics.OverlapBox(m + UnityEngine.Vector3.up * 0.06f, new UnityEngine.Vector3(r, 0.04f, r), h.transform.rotation, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
                        if (c.transform.IsChildOf(h.transform)) { clear = false; break; }
                    if (!clear) break;
                    room = r;
                }
                float edge = UnityEngine.Mathf.Min(UnityEngine.Mathf.Min(hb.max.x - m.x, m.x - hb.min.x), UnityEngine.Mathf.Min(hb.max.z - m.z, m.z - hb.min.z)) - 0.05f;
                room = UnityEngine.Mathf.Min(room, edge);
                if (room > best) { best = room; levels[k] = m; }
            }
        }
        levels.Sort((a, c) => a.y.CompareTo(c.y));
        // кровать — только спальное место: верхняя доска над центром (не изголовье и не рама);
        // шкаф — все доски ниже крыши (крыша — не место для одежды)
        if (h.Def.bed)
        {
            float bedTop = SupportY(h.transform, hb.center, hb.max.y);
            levels.Clear();
            levels.Add(new UnityEngine.Vector3(hb.center.x, bedTop, hb.center.z));
        }
        else levels.RemoveAll(v => v.y > hb.max.y - 0.12f);
        var dirs = new[] { -h.transform.forward, h.transform.forward, h.transform.right, -h.transform.right };
        foreach (var lv in levels)
        {
            UnityEngine.Vector3? camPos = null, target = null;
            foreach (var dir in dirs)
            {
                foreach (var shift in new[] { 0f, 0.12f, 0.25f })
                {
                    var t = lv + dir * shift;
                    if (shift > 0f && UnityEngine.Mathf.Abs(SupportY(h.transform, t, lv.y + 0.01f) - lv.y) > 0.01f) continue;
                    foreach (var dist in new[] { 0.9f, 1.4f })
                        foreach (var up in new[] { 0.15f, 0.3f, 0.5f, 0.8f })
                        {
                            var cp = t + dir * dist + UnityEngine.Vector3.up * up;
                            if (UnityEngine.Physics.Raycast(cp, (t - cp).normalized, out var first, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)
                                && (first.point - t).magnitude < 0.04f && first.collider.transform.IsChildOf(h.transform)) { camPos = cp; target = t; break; }
                        }
                    if (camPos != null) break;
                }
                if (camPos != null) break;
            }
            var lt = target != null ? h.transform.InverseTransformPoint(target.Value) : UnityEngine.Vector3.zero;
            string name = h.Def.id + " y=" + (lv.y - origin.y).ToString("0.00") + " x=" + lt.x.ToString("0.00") + " z=" + lt.z.ToString("0.00");
            if (camPos == null) { info.Append("INFO " + name + ": доска не видна снаружи ни одной камерой — не прогнана\n"); continue; }
            spots.Add(new object[] { h, target.Value, camPos.Value, name });
        }
    }

    // опорная лежащая вещь для «на другую» — джинсы
    var jeansDef = Cozy.Grid.FurnitureCatalog.ById("jeans_folded");
    var refJeans = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { jeansDef, parking + new UnityEngine.Vector3(0f, 0f, -5f), 0f });
    var spotOk = new System.Collections.Generic.Dictionary<string, int>();
    var traces = new System.Collections.Generic.Dictionary<string, string>();
    var spotOut = new System.Collections.Generic.Dictionary<string, int>();
    var spotRed = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>>();
    foreach (var s in spots) { spotOk[(string)s[3]] = 0; spotRed[(string)s[3]] = new System.Collections.Generic.List<string>(); }
    // пол — свободный пол своего этажа у героя (за краем уровня пола нет)
    UnityEngine.Vector3 floorSpot = UnityEngine.Vector3.zero; bool floorFound = false;
    if (player != null)
        for (int ring = 2; ring < 12 && !floorFound; ring++)
            for (int a = 0; a < 12 && !floorFound; a++)
            {
                var p0 = player.position + UnityEngine.Quaternion.Euler(0f, a * 30f, 0f) * UnityEngine.Vector3.forward * ring;
                if (!UnityEngine.Physics.Raycast(p0 + UnityEngine.Vector3.up * 1.5f, UnityEngine.Vector3.down, out var fh, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) continue;
                if (fh.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null || UnityEngine.Mathf.Abs(fh.point.y - placeFloor) > 0.3f) continue;
                if (UnityEngine.Physics.OverlapBox(fh.point + UnityEngine.Vector3.up * 0.45f, new UnityEngine.Vector3(0.7f, 0.4f, 0.7f), UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore).Length > 0) continue;
                floorSpot = fh.point; floorFound = true;
            }
    if (!floorFound) info.Append("SKIP CL-POS01: у героя нет свободного пола своего этажа\n");
    int tested = 0;
    foreach (var def in defs)
    {
        Cozy.Grid.InteractiveObject io = null;
        try { io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, parking + new UnityEngine.Vector3(tested * 1.5f, 0f, 0f), 0f }); } catch { }
        if (io == null) { info.Append("SKIP " + def.id + ": не спавнится\n"); continue; }
        tested++;
        UnityEngine.Physics.SyncTransforms();
        // CL-POS01 пол
        var rf = floorFound ? Pose(io, floorSpot) : new object[] { true, false, null, 0f };
        if (!floorFound) { }
        else if (!(bool)rf[0]) Check(false, "CL-POS01 " + def.id + ": курсор мимо пола");
        else if ((bool)rf[1]) Check(false, "CL-POS01 " + def.id + ": красный на пустом полу");
        else
        {
            Apply(io, rf);
            var b = BoundsOf(io.gameObject).Value;
            Check(UnityEngine.Mathf.Abs(b.min.y - floorSpot.y) <= 0.005f, "CL-POS01 " + def.id + ": низ от пола " + ((b.min.y - floorSpot.y) * 1000f).ToString("0") + " мм");
        }
        // CL-POS02 стол, четыре поворота
        var mid = new UnityEngine.Vector3(db.center.x, deskTop, db.center.z);
        foreach (var yaw in new[] { 0f, 90f, 180f, 270f })
        {
            fYaw.SetValue(gc, yaw);
            if (fOrient != null) fOrient.SetValue(gc, System.Convert.ChangeType((int)(yaw / 90f), fOrient.FieldType));
            var r = Pose(io, mid);
            if (!(bool)r[0]) { Check(false, "CL-POS02 " + def.id + " " + yaw + "°: курсор мимо стола"); continue; }
            if ((bool)r[1]) { Check(false, "CL-POS02 " + def.id + " " + yaw + "°: красный на пустом столе"); continue; }
            Apply(io, r);
            var b = BoundsOf(io.gameObject).Value;
            Check(UnityEngine.Mathf.Abs(b.min.y - deskTop) <= 0.005f, "CL-POS02 " + def.id + " " + yaw + "°: низ от столешницы " + ((b.min.y - deskTop) * 1000f).ToString("0") + " мм");
            float pen = Pen(io.gameObject, desk.gameObject);
            if (pen >= 0f) Check(pen <= 0.006f, "CL-POS02 " + def.id + " " + yaw + "°: входит в стол на " + (pen * 1000f).ToString("0") + " мм");
        }
        fYaw.SetValue(gc, 0f);
        if (fOrient != null) fOrient.SetValue(gc, System.Convert.ChangeType(0, fOrient.FieldType));
        // CL-STK01/02 на другую вещь (та же и джинсы) и CL-SIDE01 рядом — на столе
        foreach (var underDef in new[] { def, jeansDef })
        {
            Cozy.Grid.InteractiveObject under = underDef == jeansDef && def != jeansDef ? refJeans : null;
            bool own = under == null;
            if (own) under = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { underDef, parking + new UnityEngine.Vector3(tested * 1.5f, 0f, 2f), 0f });
            if (under == null) continue;
            UnityEngine.Physics.SyncTransforms();
            var r0 = Pose(under, mid);
            if ((bool)r0[0] && !(bool)r0[1])
            {
                Apply(under, r0);
                var bu = BoundsOf(under.gameObject).Value;
                var r1 = Pose(io, new UnityEngine.Vector3(bu.center.x, bu.max.y, bu.center.z));
                string pair = def.id + " на " + underDef.id;
                bool mustStack = Folded(def) && Folded(underDef);
                if (!(bool)r1[0]) Check(false, "CL-STK " + pair + ": курсор мимо");
                else if ((bool)r1[1]) Check(!mustStack, "CL-STK01 " + pair + ": красный — сложенную на сложенную не положить");
                else
                {
                    Apply(io, r1);
                    var bo = BoundsOf(io.gameObject).Value;
                    bool onTop = bo.min.y > bu.min.y + 0.01f;
                    if (mustStack || Shoes(def)) Check(onTop, (mustStack ? "CL-STK01 " : "CL-STK02 ") + pair + ": не сверху, а рядом (низ " + ((bo.min.y - bu.min.y) * 100f).ToString("0.0") + " см от низа нижней)");
                    if (onTop)
                    {
                        float gap = bo.min.y - bu.max.y;
                        Check(gap <= 0.02f, "CL-STK " + pair + ": висит над нижней на " + (gap * 100f).ToString("0.0") + " см");
                        Check(gap >= -0.03f, "CL-STK " + pair + ": провалилась в нижнюю на " + (-gap * 100f).ToString("0.0") + " см");
                    }
                }
                // CL-SIDE01 рядом вплотную
                var bi = BoundsOf(io.gameObject).Value;
                var side = new UnityEngine.Vector3(bu.max.x + bi.extents.x + 0.03f, deskTop, bu.center.z);
                if (side.x + bi.extents.x < db.max.x - 0.01f)
                {
                    var rs = Pose(io, side);
                    if ((bool)rs[0])
                    {
                        Check(!(bool)rs[1], "CL-SIDE01 " + def.id + " рядом с " + underDef.id + ": красный при зазоре 3 см");
                        if (!(bool)rs[1])
                        {
                            Apply(io, rs);
                            var bs = BoundsOf(io.gameObject).Value;
                            float pen = Pen(io.gameObject, under.gameObject);
                            if (pen >= 0f) Check(pen <= 0.006f, "CL-SIDE01 " + def.id + " рядом с " + underDef.id + ": входят друг в друга на " + (pen * 1000f).ToString("0") + " мм");
                            Check(UnityEngine.Mathf.Abs(bs.min.y - deskTop) <= 0.005f, "CL-SIDE01 " + def.id + " рядом с " + underDef.id + ": забралась на соседку, низ " + ((bs.min.y - deskTop) * 1000f).ToString("0") + " мм от стола");
                        }
                    }
                }
            }
            if (own) UnityEngine.Object.DestroyImmediate(under.gameObject);
            else Park(under, -4);
            Park(io, tested);
        }
        // CL-BED01 и CL-WRD01 — все поверхности хозяев
        foreach (var s in spots)
        {
            var h = (Cozy.Grid.InteractiveObject)s[0]; var t = (UnityEngine.Vector3)s[1]; var cp = (UnityEngine.Vector3)s[2]; var name = (string)s[3];
            var r = PoseFrom(io, t, cp);
            if (!(bool)r[0]) { spotRed[name].Add(def.id + "(мимо)"); continue; }
            if ((bool)r[1]) { if (spotRed[name].Count == 0) traces[name] = Cozy.Grid.GridCursor.LastPoseTrace; spotRed[name].Add(def.id); if (h.Def.bed) Check(false, "CL-BED01 " + name + " " + def.id + ": красный на пустой кровати"); continue; }
            spotOk[name]++;
            Apply(io, r);
            var b = BoundsOf(io.gameObject).Value;
            var hb = BoundsOf(h.gameObject).Value;
            float sup = SupportY(h.transform, b.center, b.min.y);
            float pen = Pen(io.gameObject, h.gameObject);
            if (h.Def.bed)
            {
                // висит — над САМОЙ ВЫСОКОЙ видимой точкой постели под вещью (центр и 8 точек на 60 % габарита):
                // вещь на гребне сложенного одеяла лежит на гребне, а под её центром одеяла может не быть
                float top = float.NegativeInfinity;
                for (int k = 0; k < 9; k++)
                {
                    float ang = k * UnityEngine.Mathf.PI * 0.25f;
                    var at = k < 8 ? b.center + new UnityEngine.Vector3(UnityEngine.Mathf.Cos(ang) * b.extents.x * 0.6f, 0f, UnityEngine.Mathf.Sin(ang) * b.extents.z * 0.6f) : b.center;
                    top = UnityEngine.Mathf.Max(top, VisibleY(h, at, b.min.y + 0.1f));
                }
                float vis = VisibleY(h, b.center, b.min.y + 0.1f);
                Check(!float.IsInfinity(top) && b.min.y - top <= 0.03f, "CL-BED01 " + name + " " + def.id + ": висит над видимой постелью на " + (float.IsInfinity(top) ? "∞" : ((b.min.y - top) * 100f).ToString("0.0")) + " см");
                if (!float.IsInfinity(vis)) Check(vis - b.min.y <= 0.08f, "CL-BED01 " + name + " " + def.id + ": утонула в постели на " + ((vis - b.min.y) * 100f).ToString("0.0") + " см");
            }
            else if (!string.IsNullOrEmpty(h.Def.slotNodes))
            {
                // шкаф со слотами: корпус — сплошной бокс, опора — узел Slot_* под вещью
                float slotY = float.NegativeInfinity; string slotName = "";
                foreach (var t2 in h.GetComponentsInChildren<UnityEngine.Transform>(true))
                    if (t2.name.StartsWith("Slot_") && t2.position.y <= b.min.y + 0.02f && t2.position.y > slotY) { slotY = t2.position.y; slotName = t2.name; }
                // не над слотом (скамья вешалки, крыша шкафа) — опора по доскам, как у шкафа без слотов
                if (float.IsInfinity(slotY) || b.min.y - slotY > 0.05f)
                    Check(!float.IsInfinity(sup) && UnityEngine.Mathf.Abs(b.min.y - sup) <= 0.005f, "CL-WRD01 " + name + " " + def.id + ": низ от доски " + (float.IsInfinity(sup) ? "доски под ним нет" : ((b.min.y - sup) * 1000f).ToString("0") + " мм"));
                else Check(UnityEngine.Mathf.Abs(b.min.y - slotY) <= 0.005f, "CL-WRD01 " + name + " " + def.id + ": низ от " + slotName + " " + ((b.min.y - slotY) * 1000f).ToString("0") + " мм");
                bool sticks = !(b.min.x >= hb.min.x - 0.005f && b.max.x <= hb.max.x + 0.005f && b.min.z >= hb.min.z - 0.005f && b.max.z <= hb.max.z + 0.005f && b.max.y <= hb.max.y + 0.005f);
                bool gated = (h.Def.slotNodes ?? "").Contains(slotName + ":");
                if (gated) Check(!sticks, "CL-WRD01 " + name + " " + def.id + ": вылезает из шкафа за дверцей — дверцу не закрыть");
                else if (sticks) spotOut[name] = (spotOut.ContainsKey(name) ? spotOut[name] : 0) + 1;
            }
            else
            {
                Check(!float.IsInfinity(sup) && UnityEngine.Mathf.Abs(b.min.y - sup) <= 0.005f, "CL-WRD01 " + name + " " + def.id + ": низ от доски " + (float.IsInfinity(sup) ? "доски под ним нет" : ((b.min.y - sup) * 1000f).ToString("0") + " мм"));
                bool inside = b.center.x > hb.min.x && b.center.x < hb.max.x && b.center.z > hb.min.z && b.center.z < hb.max.z;
                Check(inside, "CL-WRD01 " + name + " " + def.id + ": центр вне шкафа");
                if (pen >= 0f) Check(pen <= 0.006f, "CL-WRD01 " + name + " " + def.id + ": входит в доски на " + (pen * 1000f).ToString("0") + " мм");
                var pile = Cozy.Grid.Piles.On(h);
                if (pile != null && def.category == Cozy.Grid.Categories.Clothing) Check(pile.Holds(io), "CL-WRD02 " + name + " " + def.id + ": лежит в шкафу, но горка его не числит — не видно и не взять через проём");
            }
            Park(io, tested);
        }
        UnityEngine.Object.DestroyImmediate(io.gameObject);
        UnityEngine.Physics.SyncTransforms();
    }
    foreach (var s in spots)
    {
        var name = (string)s[3];
        var red = spotRed[name];
        info.Append("ПОВЕРХНОСТЬ " + name + ": встало " + spotOk[name] + " из " + tested + (spotOut.ContainsKey(name) ? " (свисают с открытой полки " + spotOut[name] + ")" : "") + (red.Count > 0 ? ", красных " + red.Count + ": " + string.Join(" ", red) + (traces.ContainsKey(name) ? "\n   трасса первого красного: " + traces[name] : "") : "") + "\n");
    }
    tail = "вещей " + tested + " из " + defs.Count + ", хозяев " + hosts.Count + ", поверхностей " + spots.Count;
}
finally
{
    Cozy.Grid.GridCursor.TracePoses = oldTrace;
    fYaw.SetValue(gc, oldYaw);
    if (fOrient != null && oldOrient != null) fOrient.SetValue(gc, oldOrient);
    UnityEngine.Object.DestroyImmediate(camGo);
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — " + tail + " (созданное удалено)\n" + info + sb;
