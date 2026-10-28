// ЛОЖНОЕ КРАСНОЕ ПРИ ПЕРЕМЕЩЕНИИ (Илья 18.10: «часто невалидно и красное, хотя место есть»; P1145). Для execute_code в play.
// Своя зона (герой +400 м по X): столешницы кухни (угловая и прямая тумба с мойкой в SinkSlot, тумба, ящики, плита) и стол;
// переносимые — посуда (с ручкой: сковорода, кастрюля, кружка), продукты, нож. Режим переноса рукой, герой у фасада (0,3 м).
// Сетка точек × 4 поворота настоящим ComputeObjectPose с камерой через настоящий курсор; «свободно» = все опорные точки дна
// (BaseSpread + 1 см) над верхом своей столешницы и не над мойкой. Свободно и красное = FAIL с причиной из ValidateTrace.
// Контроль: ручка сковороды над бортом мойки — зелёное; ручка над кружкой и сквозь стену — красное.
// Всё созданное удаляется, камера, герой, поворот и режим курсора возвращаются в finally.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var spawn = T.GetMethod("SpawnObject", B);
var fFreeYaw = T.GetField("_freeYaw", B); var fOrient = T.GetField("_orient", B);
var fHandMove = T.GetField("_handMove", B);
var mSpread = T.GetMethod("BaseSpread", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursorPx = mouse.position.ReadValue();
var savedPos = cam.transform.position; var savedRot = cam.transform.rotation;
var player = Cozy.Grid.PlayerRef.GameObject;
var savedPlayer = player.transform.position;
object savedYaw = fFreeYaw.GetValue(gc); object savedOrient = fOrient.GetValue(gc); object savedHand = fHandMove.GetValue(gc);
bool savedTrace = Cozy.Grid.GridCursor.TracePoses;
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var sb = new System.Text.StringBuilder();
var reasons = new System.Collections.Generic.Dictionary<string, int>();
var examples = new System.Collections.Generic.Dictionary<string, string>();
int total = 0, red = 0, ctlBad = 0;
bool HAND = true;
System.Func<UnityEngine.GameObject, UnityEngine.Bounds> BoundsOf = go => {
    var b = new UnityEngine.Bounds(go.transform.position, UnityEngine.Vector3.zero); bool first = true;
    foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>()) { if (!r.enabled || Cozy.Grid.InteractHighlight.IsCopy(r) || r is UnityEngine.ParticleSystemRenderer) continue; if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
    return b;
};
try {
    Cozy.Grid.GridCursor.TracePoses = true;
    float floorY = Cozy.Grid.GridManager.LevelY(player.transform.position.y + 0.05f, 3f);
    var origin = new UnityEngine.Vector3(savedPlayer.x + 400f, floorY, savedPlayer.z);
    var hosts = new[] { "home_sink_cabinet_corner", "home_sink_cabinet", "home_kitchen_counter", "home_drawer_module", "office_desk", "home_stove" };
    var items = new[] { "frying_pan", "cooking_pot", "plate", "coffee_cup_red", "bread_loaf", "sausage_pack", "milk_carton", "apple", "chocolate_bar", "kitchen_knife", "oil_bottle" };
    float hx = 0f;
    foreach (var hid in hosts) {
        var hdef = Cozy.Grid.FurnitureCatalog.ById(hid); if (hdef == null) { sb.Append("нет хозяина " + hid + "\n"); continue; }
        var hpos = origin + new UnityEngine.Vector3(hx, 0f, 0f); hx += 5f;
        var host = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { hdef, hpos, 0f });
        if (host == null) { sb.Append("не заспавнился " + hid + "\n"); continue; }
        UnityEngine.Physics.SyncTransforms();
        var hb = BoundsOf(host.gameObject);
        var sinkSlot = Cozy.Grid.FurnitureModel.FindNode(host.transform, "SinkSlot");
        bool hasSinkB = false; var sinkB = new UnityEngine.Bounds();
        if (sinkSlot != null) {
            var sink = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { Cozy.Grid.FurnitureCatalog.ById("home_sink"), sinkSlot.position, 0f });
            if (sink != null) sink.transform.SetPositionAndRotation(sinkSlot.position, UnityEngine.Quaternion.Euler(0f, 0f, 0f));
            UnityEngine.Physics.SyncTransforms();
            if (sink != null) { sinkB = BoundsOf(sink.gameObject); hasSinkB = true; }
            sb.Append("мойка на " + hid + "\n");
        }
        float top = hb.max.y;
        foreach (var iid in items) {
            var idef = Cozy.Grid.FurnitureCatalog.ById(iid); if (idef == null) continue;
            var body = new UnityEngine.GameObject("FalseRedProbe"); made.Add(body);
            body.AddComponent<Cozy.Grid.InteractiveObject>().Build(idef);
            UnityEngine.Physics.SyncTransforms();
            var ib = BoundsOf(body);
            float ihalf = UnityEngine.Mathf.Max(ib.extents.x, ib.extents.z);
            for (int yi = 0; yi < 4; yi++) {
                float yaw = yi * 90f;
                fFreeYaw.SetValue(gc, yaw); fOrient.SetValue(gc, yi);
                for (float fx = 0.15f; fx <= 0.851f; fx += 0.14f)
                for (float fz = 0.15f; fz <= 0.851f; fz += 0.14f) {
                    var target = new UnityEngine.Vector3(UnityEngine.Mathf.Lerp(hb.min.x, hb.max.x, fx), top, UnityEngine.Mathf.Lerp(hb.min.z, hb.max.z, fz));
                    if (target.x - ihalf < hb.min.x + 0.01f || target.x + ihalf > hb.max.x - 0.01f || target.z - ihalf < hb.min.z + 0.01f || target.z + ihalf > hb.max.z - 0.01f) continue;
                    UnityEngine.RaycastHit th;
                    if (!UnityEngine.Physics.Raycast(target + UnityEngine.Vector3.up * 0.5f, UnityEngine.Vector3.down, out th, 1f)) continue;
                    var tio = th.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>();
                    if (tio != host) continue;
                    if (UnityEngine.Mathf.Abs(th.point.y - top) > 0.03f) continue;
                    body.transform.SetPositionAndRotation(target, UnityEngine.Quaternion.Euler(0f, yaw, 0f));
                    UnityEngine.Physics.SyncTransforms();
                    var sa = new object[] { body, BoundsOf(body), null };
                    bool hasSpread = (bool)mSpread.Invoke(null, sa);
                    var loc = (UnityEngine.Bounds)sa[2];
                    var wps = new System.Collections.Generic.List<UnityEngine.Vector3>();
                    if (hasSpread)
                        for (int sx = -1; sx <= 1; sx++) for (int sz = -1; sz <= 1; sz++)
                            wps.Add(body.transform.TransformPoint(new UnityEngine.Vector3(loc.center.x + sx * (loc.extents.x + 0.01f), 0f, loc.center.z + sz * (loc.extents.z + 0.01f))));
                    body.transform.position = new UnityEngine.Vector3(0f, -500f, 0f);
                    UnityEngine.Physics.SyncTransforms();
                    bool freeAll = hasSpread;
                    if (hasSinkB) foreach (var wp in wps) if (wp.x > sinkB.min.x - 0.01f && wp.x < sinkB.max.x + 0.01f && wp.z > sinkB.min.z - 0.01f && wp.z < sinkB.max.z + 0.01f) freeAll = false;
                    foreach (var wp in wps) {
                        UnityEngine.RaycastHit bh;
                        if (!UnityEngine.Physics.Raycast(new UnityEngine.Vector3(wp.x, top + 0.3f, wp.z), UnityEngine.Vector3.down, out bh, 0.6f, ~0, UnityEngine.QueryTriggerInteraction.Ignore) || bh.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() != host || UnityEngine.Mathf.Abs(bh.point.y - top) > 0.003f) { freeAll = false; break; }
                    }
                    if (!freeAll) continue;
                    if (HAND) player.transform.position = new UnityEngine.Vector3(target.x, floorY, hb.min.z - 0.3f);
                    var worldDir = (UnityEngine.Vector3.forward + UnityEngine.Vector3.down * 1.2f).normalized;
                    cam.transform.SetPositionAndRotation(target - worldDir * 3f, UnityEngine.Quaternion.identity);
                    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursorPx.x, cursorPx.y, 0f)).direction;
                    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
                    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursorPx.x, cursorPx.y, 0f)).direction * 3f;
                    UnityEngine.Physics.SyncTransforms();
                    fHandMove.SetValue(gc, HAND);
                    Cozy.Grid.GridCursor.ValidateTrace = ""; Cozy.Grid.GridCursor.HeightTrace = "";
                    var args = new object[] { idef, cam, mouse, body, body.transform, floorY, null, null, null };
                    bool ok = (bool)mPose.Invoke(gc, args);
                    fHandMove.SetValue(gc, savedHand);
                    total++;
                    if (!ok) { red++; string k0 = "нет позы"; reasons[k0] = (reasons.ContainsKey(k0) ? reasons[k0] : 0) + 1; continue; }
                    if ((bool)args[8]) {
                        red++;
                        var tr = Cozy.Grid.GridCursor.LastPoseTrace ?? "";
                        string key = hid + " | " + tr.Replace(target.y.ToString("F3"), "");
                        string vt = Cozy.Grid.GridCursor.ValidateTrace.Trim();
                        string k = hid + ": " + (vt.Length > 0 ? vt : "(" + System.Text.RegularExpressions.Regex.Replace(tr, @"y=[-0-9.]+", "") + ")");
                        reasons[k] = (reasons.ContainsKey(k) ? reasons[k] : 0) + 1;
                        if (!examples.ContainsKey(k)) examples[k] = iid + " yaw" + yaw + " @" + fx.ToString("0.00") + "," + fz.ToString("0.00") + " pos=" + ((UnityEngine.Vector3)args[6]).ToString("F3") + " tgt=" + target.ToString("F3") + " tr=" + tr;
                    }
                }
            }
            made.Remove(body); UnityEngine.Object.DestroyImmediate(body);
        }
    }
    {
        var choff = origin + new UnityEngine.Vector3(40f, 0f, 0f);
        var host = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { Cozy.Grid.FurnitureCatalog.ById("home_sink_cabinet_corner"), choff, 0f });
        UnityEngine.Physics.SyncTransforms();
        var slot = Cozy.Grid.FurnitureModel.FindNode(host.transform, "SinkSlot");
        var sink = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { Cozy.Grid.FurnitureCatalog.ById("home_sink"), slot.position, 0f });
        sink.transform.SetPositionAndRotation(slot.position, UnityEngine.Quaternion.identity);
        UnityEngine.Physics.SyncTransforms();
        var sinkB = sink.WorldBounds;
        float chx = choff.x, chz = choff.z;
    var cup = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { Cozy.Grid.FurnitureCatalog.ById("coffee_cup_red"), new UnityEngine.Vector3(chx + 3.6f, 1.15f, chz + 0.25f), 0f });
    var wall = UnityEngine.GameObject.CreatePrimitive(UnityEngine.PrimitiveType.Cube); made.Add(wall);
    wall.transform.position = new UnityEngine.Vector3(chx + 2.6f, 1.6f, chz + 0.6f); wall.transform.localScale = new UnityEngine.Vector3(0.1f, 1f, 1f);
    UnityEngine.Physics.SyncTransforms();
    var idef = Cozy.Grid.FurnitureCatalog.ById("frying_pan");
    var body = new UnityEngine.GameObject("FalseRedSim"); made.Add(body);
    body.AddComponent<Cozy.Grid.InteractiveObject>().Build(idef);
    UnityEngine.Physics.SyncTransforms();
    var cases = new System.Collections.Generic.List<object[]> {
        new object[] { "ручка над бортом мойки", new UnityEngine.Vector3(sinkB.max.x + 0.27f, 1.15f, sinkB.center.z - 0.2f), 0f, true },
        new object[] { "ручка над кружкой", new UnityEngine.Vector3(chx + 3.6f + 0.45f, 1.15f, chz + 0.25f), 0f, false },
        new object[] { "ручка в стене", new UnityEngine.Vector3(chx + 2.6f + 0.47f, 1.15f, chz + 0.6f), 0f, false },
    };
    foreach (var cs in cases) {
        var pos = (UnityEngine.Vector3)cs[1]; float yaw = (float)cs[2];
        body.transform.SetPositionAndRotation(pos, UnityEngine.Quaternion.Euler(0f, yaw, 0f));
        UnityEngine.Physics.SyncTransforms();
        var mOv = T.GetMethod("OverlapsOthers", B, null, new System.Type[] { typeof(Cozy.Grid.ObjectDef), typeof(UnityEngine.GameObject), typeof(UnityEngine.Vector3), typeof(float), typeof(UnityEngine.Transform), typeof(bool), typeof(bool) }, null);
        var mOb = T.GetMethod("ObstacleTopUnder", B);
        var mBowl = T.GetMethod("OnBowlEdge", B);
        bool ov = (bool)mOv.Invoke(gc, new object[] { idef, body, pos, yaw, body.transform, false, false });
        float ob = (float)mOb.Invoke(gc, new object[] { body, pos, yaw, body.transform, false });
        bool bowl = (bool)mBowl.Invoke(gc, new object[] { body, pos.x, pos.y, pos.z, yaw });
        bool cred = ov || ob > pos.y + 0.001f || bowl;
        string line = cs[0] + ": overlaps=" + ov + " lift=" + (ob - pos.y).ToString("F3") + " bowl=" + bowl + " → " + (cred ? "КРАСНОЕ" : "зелёное") + ", ждём " + ((bool)cs[3] ? "зелёное" : "КРАСНОЕ");
        sb.Append(line + "\n"); if (cred != !(bool)cs[3]) ctlBad++;
    }
    }
} finally {
    foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g);
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
    cam.transform.SetPositionAndRotation(savedPos, savedRot);
    player.transform.position = savedPlayer;
    fFreeYaw.SetValue(gc, savedYaw); fOrient.SetValue(gc, savedOrient); fHandMove.SetValue(gc, savedHand);
    Cozy.Grid.GridCursor.TracePoses = savedTrace;
    UnityEngine.Physics.SyncTransforms();
}
sb.Insert(0, (red == 0 && ctlBad == 0 ? "ЗЕЛЁНОЕ" : "КРАСНОЕ: ложных красных " + red + ", контроль не сошёлся " + ctlBad) + " — поз на свободном месте " + total + " (своя зона, созданное удалено)\n");
foreach (var kv in reasons) sb.Append("FAIL " + kv.Value + "  " + kv.Key + "\n    пример: " + (examples.ContainsKey(kv.Key) ? examples[kv.Key] : "") + "\n");
return sb.ToString();
