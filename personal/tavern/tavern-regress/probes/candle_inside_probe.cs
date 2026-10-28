// СВЕЧИ ВНУТРИ ТУМБ И ШКАФОВ (LIGHT.md §8, LI-CI…; Илья 18.10: «посмотри, как свечи кладутся внутрь тумбочки —
// как одежда с вещами делает, то же самое сделай, только подсвечники не клади внутрь»).
// Для execute_code в play, любой уровень. Образец — clothes_place_probe.cs: НАСТОЯЩИЙ конвейер
// `GridCursor.ComputeObjectPose` со своей камерой, луч через настоящий курсор в цель.
// Стенд свой: вся напольная открываемая МЕБЕЛЬ (технику и топки — холодильник, плиту, камин, мойку, колодец,
// мусорный бак — пропускаем), у которой после спавна есть площадка ContainerSlot СО СТВОРКОЙ; ставится в зону на
// этаже игрока за краем уровня (+400 м по X), створки распахнуты сразу. Свечи — все дефы `candle` и все
// поверхностные `notInside` (подсвечники). Всё созданное удаляется в finally; уровень не меняется.
//  LI-CI01 свеча (не notInside) на каждой площадке за створкой: не красная, если по высоте влезает (просвет над
//          площадкой ≥ высоты свечи); низ на площадке ±5 мм, внутри корпуса, в доски не входит (≤ 6 мм);
//  LI-CI02 привязалась к хозяину (ReattachToContainer → Container = хозяин);
//  LI-CI03 закрыли створку — свеча спрятана (Targeting.Hidden), открыли — снова видна;
//  LI-CI04 подсвечник (notInside) на площадку за створкой — КРАСНЫЙ (Илья: «подсвечники не клади внутрь»);
//  LI-CI05 подсвечник на верх той же мебели — не красный (на верх можно).
// Первая строка — вердикт, дальше сводка по площадкам и FAIL с кодом.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
if (gc == null) return "нет GridCursor";
var mouse = UnityEngine.InputSystem.Mouse.current;
if (mouse == null) return "нет мыши";
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var spawn = T.GetMethod("SpawnObject", B);
var mCompute = T.GetMethod("ComputeObjectPose", B);
var IO = typeof(Cozy.Grid.InteractiveObject);
var fMoving = IO.GetField("_moving", B);
var mSetPartPose = IO.GetMethod("SetPartPose", B);
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 80) sb.Append("FAIL " + line + "\n"); } };

System.Func<UnityEngine.GameObject, UnityEngine.Bounds?> BoundsOf = go => {
    UnityEngine.Bounds b = default(UnityEngine.Bounds); bool any = false;
    for (int pass = 0; pass < 2 && !any; pass++)
        foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>(pass == 1))
        {
            if (Cozy.Grid.InteractHighlight.IsCopy(r) || r is UnityEngine.ParticleSystemRenderer || r.name == "OutlineMask" || r.name == "OutlineBand" || r.name == "GlowHalo") continue;
            if (pass == 0 && !r.enabled) continue;
            if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
        }
    return any ? b : (UnityEngine.Bounds?)null;
};
System.Func<UnityEngine.GameObject, UnityEngine.GameObject, float> Pen = (a, b) => {
    var ca = a.GetComponentsInChildren<UnityEngine.Collider>(); var cb = b.GetComponentsInChildren<UnityEngine.Collider>();
    float worst = 0f;
    foreach (var x in ca) foreach (var y in cb)
    {
        if (!x.enabled || !y.enabled || x.isTrigger || y.isTrigger) continue;
        if (y.GetComponent<Cozy.Grid.ContainerSlot>() != null) continue; // площадка слота — опора, не стенка
        if (UnityEngine.Physics.ComputePenetration(x, x.transform.position, x.transform.rotation, y, y.transform.position, y.transform.rotation, out var dir, out var dist))
            if (dist > worst) worst = dist;
    }
    return worst;
};

var appliance = new[] { "fridge", "stove", "oven", "fireplace", "sink", "well", "dumpster", "microwave", "washer" };
var hostDefs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
{
    if (d == null || d.mount != Cozy.Grid.ObjectMount.Floor || !d.openable) continue;
    bool skip = false; foreach (var a in appliance) if (d.id.Contains(a)) skip = true;
    if (!skip) hostDefs.Add(d);
}
// флаг notInside рефлексией: на коде до 18.10 его нет — тогда подсвечники по id (замер «до»)
var fNotInside = typeof(Cozy.Grid.ObjectDef).GetField("notInside");
System.Func<Cozy.Grid.ObjectDef, bool> Holder = d => fNotInside != null ? (bool)fNotInside.GetValue(d) : d.id == "old_candle_1" || d.id.StartsWith("church_candle_s") || d.id.StartsWith("church_kanun");
var candleDefs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && d.mount == Cozy.Grid.ObjectMount.Surface && (d.candle || Holder(d))) candleDefs.Add(d);
if (fNotInside == null) info.Append("INFO код без ObjectDef.notInside — подсвечники по id (old_candle_1, church_candle_small)\n");

var camGo = new UnityEngine.GameObject("candle_inside_probe_cam");
var cam = camGo.AddComponent<UnityEngine.Camera>();
cam.enabled = false;
if (UnityEngine.Camera.main != null) cam.fieldOfView = UnityEngine.Camera.main.fieldOfView;
var player = Cozy.Grid.PlayerRef.Transform;
float placeFloor = (float)T.GetMethod("PlaceFloorY", B).Invoke(gc, null);
var origin = new UnityEngine.Vector3((player != null ? player.position.x : 0f) + 400f, placeFloor, player != null ? player.position.z : 0f);
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
bool oldTrace = Cozy.Grid.GridCursor.TracePoses;
Cozy.Grid.GridCursor.TracePoses = true;
int hostsUsed = 0, pads = 0;
try
{
    var parking = origin + new UnityEngine.Vector3(0f, -30f, -10f);
    System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3, UnityEngine.Vector3, object[]> PoseFrom = (io, target, camPos) => {
        cam.transform.position = camPos;
        cam.transform.rotation = UnityEngine.Quaternion.identity;
        var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
        cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(ray.direction, (target - camPos).normalized);
        var args = new object[] { io.Def, cam, mouse, io.gameObject, io.transform, origin.y, null, null, null };
        bool ok = (bool)mCompute.Invoke(gc, args);
        return new object[] { ok, args[8], args[6], args[7] };
    };
    System.Action<Cozy.Grid.InteractiveObject, object[]> Apply = (io, r) => {
        io.transform.SetPositionAndRotation((UnityEngine.Vector3)r[2], UnityEngine.Quaternion.Euler(0f, (float)r[3], 0f));
        UnityEngine.Physics.SyncTransforms();
    };
    System.Action<Cozy.Grid.InteractiveObject, int> Park = (io, k) => { io.transform.SetParent(null, true); io.Container = null; io.transform.position = parking + new UnityEngine.Vector3(k * 1.5f, 0f, 0f); UnityEngine.Physics.SyncTransforms(); };
    // открыта только нужная створка (only = null — все): открытые соседние ящики нависают друг над другом,
    // и свеча «в нижний» вставала в средний — игрок так не открывает
    System.Action<Cozy.Grid.InteractiveObject, bool, Cozy.Grid.AccessFeature> SetOnly = (host, open, only) => {
        foreach (var f in host.Features) if (f is Cozy.Grid.AccessFeature a && !a.Locked) a.SetOpen(open && (only == null || ReferenceEquals(a, only)));
        var list = fMoving.GetValue(host) as System.Collections.IList;
        if (list != null)
            foreach (var m in list)
            {
                var mt = m.GetType();
                var acc = mt.GetField("access").GetValue(m) as Cozy.Grid.AccessFeature;
                if (acc == null) continue;
                float t = acc.Open ? 1f : 0f;
                mt.GetField("t").SetValue(m, t);
                mSetPartPose.Invoke(host, new object[] { m, t });
            }
        UnityEngine.Physics.SyncTransforms();
    };
    System.Action<Cozy.Grid.InteractiveObject, bool> SetAll = (host, open) => SetOnly(host, open, null);

    // свечи — в парковку
    var candles = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    for (int i = 0; i < candleDefs.Count; i++)
    {
        var c = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { candleDefs[i], parking + new UnityEngine.Vector3(i * 1.5f, 0f, 0f), 0f });
        if (c == null) { info.Append("SKIP " + candleDefs[i].id + ": не спавнится\n"); continue; }
        made.Add(c.gameObject); candles.Add(c);
    }
    UnityEngine.Physics.SyncTransforms();

    int hi = 0;
    foreach (var hd in hostDefs)
    {
        Cozy.Grid.InteractiveObject h = null;
        var hp = origin + new UnityEngine.Vector3(6f + (hi % 6) * 6f, 0f, 6f + (hi / 6) * 7f);
        try { h = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { hd, hp, 0f }); } catch { }
        if (h == null) continue;
        hi++;
        made.Add(h.gameObject);
        SetAll(h, true);
        var gated = new System.Collections.Generic.List<Cozy.Grid.ContainerSlot>();
        foreach (var s in h.GetComponentsInChildren<Cozy.Grid.ContainerSlot>(true))
            if (s.Gate != null && s.GetComponent<UnityEngine.Collider>() != null) gated.Add(s);
        if (gated.Count == 0) { made.Remove(h.gameObject); UnityEngine.Object.DestroyImmediate(h.gameObject); hi--; continue; }
        hostsUsed++;
        var hb = BoundsOf(h.gameObject).Value;
        foreach (var slot in gated)
        {
            // просвет — при ЗАКРЫТЫХ створках, как его меряет игра (у выдвинутого ящика над дном пусто)
            SetAll(h, false);
            var closedPad = slot.GetComponent<UnityEngine.Collider>().bounds;
            var closedTop = new UnityEngine.Vector3(closedPad.center.x, closedPad.max.y, closedPad.center.z);
            // просвет над площадкой — по ВИДИМЫМ мешам хозяина (корпус мебели со слотами — сплошной бокс-коллайдер,
            // по нему просвет нулевой): временные MeshCollider на слое 2, луч вверх от площадки
            float clear = 9f;
            var tmp = new System.Collections.Generic.List<UnityEngine.GameObject>();
            foreach (var mf in h.GetComponentsInChildren<UnityEngine.MeshFilter>())
            {
                if (mf.sharedMesh == null || mf.name == "OutlineMask" || mf.name == "OutlineBand" || mf.name == "OutlineHull") continue;
                var mr = mf.GetComponent<UnityEngine.MeshRenderer>(); if (mr == null || !mr.enabled) continue;
                var g = new UnityEngine.GameObject("ci_probe_mesh"); g.layer = 2; g.transform.SetParent(mf.transform, false);
                var mc = g.AddComponent<UnityEngine.MeshCollider>(); mc.sharedMesh = mf.sharedMesh; tmp.Add(g);
            }
            UnityEngine.Physics.SyncTransforms();
            foreach (var g in tmp)
            {
                var mc = g.GetComponent<UnityEngine.MeshCollider>();
                if (mc.Raycast(new UnityEngine.Ray(closedTop + UnityEngine.Vector3.up * 0.02f, UnityEngine.Vector3.up), out var uh, 3f)) clear = UnityEngine.Mathf.Min(clear, uh.distance + 0.02f);
            }
            foreach (var g in tmp) UnityEngine.Object.DestroyImmediate(g);
            UnityEngine.Physics.SyncTransforms();
            SetOnly(h, true, slot.Gate);
            var pad = slot.GetComponent<UnityEngine.Collider>().bounds;
            // цель — ВИДИМАЯ точка площадки: у ящика под крышкой середина дна спрятана под коробкой корпуса,
            // игрок целится в ту часть, что видна; из видимых — ближе к середине площадки
            var padCol = slot.GetComponent<UnityEngine.Collider>();
            UnityEngine.Vector3 target = new UnityEngine.Vector3(pad.center.x, pad.max.y, pad.center.z);
            UnityEngine.Vector3? camPos = null; float bestMiss = float.MaxValue;
            for (int gx = 0; gx < 5; gx++) for (int gz = 0; gz < 5; gz++)
            {
                var t = new UnityEngine.Vector3(UnityEngine.Mathf.Lerp(pad.min.x + 0.03f, pad.max.x - 0.03f, gx / 4f), pad.max.y, UnityEngine.Mathf.Lerp(pad.min.z + 0.03f, pad.max.z - 0.03f, gz / 4f));
                float miss = new UnityEngine.Vector2(t.x - pad.center.x, t.z - pad.center.z).sqrMagnitude;
                if (miss >= bestMiss) continue;
                foreach (var dir in new[] { -h.transform.forward, h.transform.forward, h.transform.right, -h.transform.right })
                {
                    bool seen = false;
                    foreach (var dist in new[] { 0.9f, 1.4f })
                        foreach (var up in new[] { 0.15f, 0.3f, 0.5f, 0.8f })
                        {
                            var cp = t + dir * dist + UnityEngine.Vector3.up * up;
                            if (UnityEngine.Physics.Raycast(cp, (t - cp).normalized, out var first, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)
                                && first.collider == padCol && (first.point - t).magnitude < 0.02f) { camPos = cp; target = t; bestMiss = miss; seen = true; break; }
                        }
                    if (seen) break;
                }
            }
            string name = hd.id + "/" + slot.name;
            if (camPos == null) { info.Append("INFO " + name + ": площадка не видна снаружи — не прогнана\n"); continue; }
            pads++;
            int ok = 0; var red = new System.Collections.Generic.List<string>();
            for (int ci = 0; ci < candleDefs.Count; ci++)
            {
                var cd = candleDefs[ci];
                Cozy.Grid.InteractiveObject c = null;
                try { c = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { cd, parking + new UnityEngine.Vector3(ci * 1.5f, 0f, 0f), 0f }); } catch { }
                if (c == null) continue;
                made.Add(c.gameObject);
                UnityEngine.Physics.SyncTransforms();
                float hgt = BoundsOf(c.gameObject).Value.size.y;
                var r = PoseFrom(c, target, camPos.Value);
                bool blocked = (bool)r[1];
                if (!(bool)r[0]) red.Add(cd.id + "(мимо)");
                else if (Holder(cd)) Check(blocked, "LI-CI04 " + name + " " + cd.id + ": подсвечник ставится внутрь (за створку)");
                else if (blocked)
                {
                    red.Add(cd.id);
                    Check(hgt > clear - 0.01f, "LI-CI01 " + name + " " + cd.id + ": красный, хотя влезает (свеча " + (hgt * 100f).ToString("0") + " см, просвет " + (clear * 100f).ToString("0") + " см) — " + Cozy.Grid.GridCursor.LastPoseTrace);
                }
                else
                {
                    ok++;
                    Apply(c, r);
                    var b = BoundsOf(c.gameObject).Value;
                    bool inPad = b.center.x >= pad.min.x && b.center.x <= pad.max.x && b.center.z >= pad.min.z && b.center.z <= pad.max.z;
                    Check(inPad && UnityEngine.Mathf.Abs(b.min.y - pad.max.y) <= 0.005f, "LI-CI01 " + name + " " + cd.id + ": встала не на площадку — низ " + ((b.min.y - pad.max.y) * 1000f).ToString("0") + " мм от неё, центр " + (inPad ? "над ней" : "мимо"));
                    Check(hgt <= clear + 0.005f, "LI-CI01 " + name + " " + cd.id + ": встала, но выше просвета (свеча " + (hgt * 100f).ToString("0") + " см, просвет " + (clear * 100f).ToString("0") + " см) — створку не закрыть");
                    gc.ReattachToContainer(c);
                    Check(ReferenceEquals(c.Container, h), "LI-CI02 " + name + " " + cd.id + ": не привязалась к хозяину (Container = " + (c.Container != null ? c.Container.Def.id : "null") + ")");
                    if (ReferenceEquals(c.Container, h))
                    {
                        slot.Gate.SetOpen(false);
                        Check(Cozy.Grid.Targeting.Hidden(c), "LI-CI03 " + name + " " + cd.id + ": створку закрыли, а свеча не спрятана");
                        slot.Gate.SetOpen(true);
                        Check(!Cozy.Grid.Targeting.Hidden(c), "LI-CI03 " + name + " " + cd.id + ": открыли, а свеча всё ещё спрятана");
                    }
                }
                made.Remove(c.gameObject);
                c.Container = null;
                UnityEngine.Object.DestroyImmediate(c.gameObject);
                UnityEngine.Physics.SyncTransforms();
            }
            sb.Append("  " + name + ": просвет " + (clear > 8f ? "∞" : (clear * 100f).ToString("0") + " см") + ", встало " + ok + (red.Count > 0 ? ", красные: " + string.Join(", ", red) : "") + "\n");
        }
        // LI-CI05 подсвечник на верх той же мебели — можно (створки закрыты: открытая дверца не мешает)
        SetAll(h, false);
        hb = BoundsOf(h.gameObject).Value; // габарит при закрытых створках: открытые сдвигали «середину верха» на дверцу
        var top = new UnityEngine.Vector3(hb.center.x, hb.max.y, hb.center.z);
        foreach (var c in candles)
        {
            if (!Holder(c.Def)) continue;
            var cp = top + (-h.transform.forward) * 1.2f + UnityEngine.Vector3.up * 1.2f;
            if (!UnityEngine.Physics.Raycast(cp, (top - cp).normalized, out var fh, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore) || !fh.collider.transform.IsChildOf(h.transform) || fh.normal.y < 0.85f) continue;
            var r = PoseFrom(c, fh.point, cp);
            if ((bool)r[0]) Check(!(bool)r[1], "LI-CI05 " + hd.id + " " + c.Def.id + ": подсвечник не ставится и на верх мебели");
        }
        SetAll(h, false);
    }
}
catch (System.Exception e) { Check(false, "исключение: " + (e.InnerException ?? e).Message); }
finally
{
    Cozy.Grid.GridCursor.TracePoses = oldTrace;
    foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g);
    if (camGo != null) UnityEngine.Object.DestroyImmediate(camGo);
    UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — мебели со створкой " + hostsUsed + ", площадок " + pads + ", свечей и подсвечников " + candleDefs.Count + " (созданное удалено)\n" + sb + info;
