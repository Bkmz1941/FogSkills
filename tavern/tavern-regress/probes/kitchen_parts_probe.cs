// ЯЩИКИ И ДВЕРЦЫ КУХНИ (KITCHEN.md, KT-PRT05–08; 18.10). Для execute_code в play, на ЛЮБОМ уровне.
// По каждому дефу с подвижными частями (`parts`, по признаку, не по списку) спавнит СВОЙ экземпляр
// в своей зоне (игрок + (0, −90, 0), шаг 6 м) и гоняет НАСТОЯЩИЙ Tick объекта (рефлексией, до остановки):
//  PRT05 дверца духовки (узел *Oven*) откидывается ВНИЗ на горизонтальной оси;
//  PRT06 стена вплотную сзади и соседи вплотную по бокам (боксы-примитивы, зазор 3 мм): открытая часть
//        входит в них не глубже 5 мм (OpenLimit обязан остановить створку);
//  PRT07 открыть→закрыть ×3: закрытая часть ровно в исходной позе (±1 мм, ±0,5°);
//  PRT08 сейв открытого в памяти (Snapshot + CollectFeatures → JSON → RestoreOne, путь загрузки): после
//        восстановления секции открыты так же и части доехали до открытой позы (±1 мм, ±0,5°).
// Всё созданное удаляется в finally. Вывод: «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом.
if (!UnityEngine.Application.isPlaying) return "не в play";
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var NPS = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public;
var IO = typeof(Cozy.Grid.InteractiveObject);
var GC = typeof(Cozy.Grid.GridCursor);
var cursor = Cozy.Grid.GridCursor.I;
var spawn = GC.GetMethod("SpawnObject", NP);
var restoreOne = GC.GetMethod("RestoreOne", NP);
var tick = IO.GetMethod("Tick", NP);
var fMoving = IO.GetField("_moving", NP);
var openLimitM = IO.GetMethod("OpenLimit", NP);
var setPose = IO.GetMethod("SetPartPose", NP);
var snapshot = typeof(Cozy.Grid.LevelIO).GetMethod("Snapshot", NPS);
var collectF = typeof(Cozy.Grid.LevelIO).GetMethod("CollectFeatures", NPS);
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0, skipped = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 60) sb.Append("FAIL " + line + "\n"); } };
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
var basePos = Cozy.Grid.PlayerRef.Transform.position + new UnityEngine.Vector3(-700f, -90f, 0f);

System.Func<object, string, object> F = (o, n) => o.GetType().GetField(n).GetValue(o);
System.Action<Cozy.Grid.InteractiveObject> Settle = io => {
    var list = fMoving.GetValue(io) as System.Collections.IList;
    for (int k = 0; k < 2000; k++) {
        tick.Invoke(io, null);
        bool moving = false;
        foreach (var m in list) {
            if ((bool)F(m, "swap") || (bool)F(m, "manual")) continue;
            var acc = F(m, "access") as Cozy.Grid.AccessFeature; var pw = F(m, "power") as Cozy.Grid.PowerFeature;
            bool on = pw != null ? pw.On : acc != null && acc.Open;
            float target = on ? (float)F(m, "limit") : 0f;
            if (!UnityEngine.Mathf.Approximately((float)F(m, "t"), target)) { moving = true; break; }
        }
        if (!moving) break;
    }
    UnityEngine.Physics.SyncTransforms();
};
System.Func<UnityEngine.GameObject, UnityEngine.Bounds> BoundsOf = go => {
    var b = new UnityEngine.Bounds(go.transform.position, UnityEngine.Vector3.zero); bool first = true;
    foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>()) {
        if (!r.enabled || Cozy.Grid.InteractHighlight.IsCopy(r)) continue;
        if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
    }
    return b;
};
System.Func<UnityEngine.Vector3, UnityEngine.Vector3, UnityEngine.GameObject> Box = (center, size) => {
    var g = UnityEngine.GameObject.CreatePrimitive(UnityEngine.PrimitiveType.Cube);
    g.name = "kitchen_parts_probe_block"; g.transform.position = center; g.transform.localScale = size;
    made.Add(g); return g;
};

int defs = 0, parts = 0, ovens = 0, visNote = 0;
var vis = new System.Text.StringBuilder();
try {
    int slot = 0;
    foreach (var def in Cozy.Grid.FurnitureCatalog.All()) {
        if (def == null || def.parts == null || def.parts.Count == 0) continue;
        var pos = basePos + new UnityEngine.Vector3((slot % 8) * 6f, 0f, (slot / 8) * 6f); slot++;
        Cozy.Grid.InteractiveObject io = null;
        try { io = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { def, pos, 0f }); } catch (System.Exception e) { Check(false, "спавн " + def.id + ": " + (e.InnerException ?? e).Message); continue; }
        if (io == null) { skipped++; continue; }
        made.Add(io.gameObject);
        UnityEngine.Physics.SyncTransforms();
        var list = fMoving.GetValue(io) as System.Collections.IList;
        var mine = new System.Collections.Generic.List<object>();
        foreach (var m in list) {
            if ((bool)F(m, "swap") || (bool)F(m, "scaled") || F(m, "access") == null) continue;
            if (!(bool)m.GetType().GetProperty("Travels").GetValue(m)) continue;
            mine.Add(m);
        }
        if (mine.Count == 0) { skipped++; UnityEngine.Object.DestroyImmediate(io.gameObject); continue; }
        defs++; parts += mine.Count;
        // закрытые позы и закрытый корпус
        var closedLP = new System.Collections.Generic.Dictionary<object, UnityEngine.Vector3>();
        var closedLR = new System.Collections.Generic.Dictionary<object, UnityEngine.Quaternion>();
        foreach (var m in mine) { var tf = (UnityEngine.Transform)F(m, "tf"); closedLP[m] = tf.localPosition; closedLR[m] = tf.localRotation; }
        var body = BoundsOf(io.gameObject);
        // PRT05 духовка
        foreach (var m in mine) {
            var tf = (UnityEngine.Transform)F(m, "tf");
            if (!tf.name.Contains("Oven") || !(bool)F(m, "rotate")) continue;
            ovens++;
            var axis = tf.parent.TransformDirection((UnityEngine.Quaternion)F(m, "closedRot") * (UnityEngine.Vector3)F(m, "axis")).normalized;
            var c0 = BoundsOf(tf.gameObject).center;
            tf.localRotation = (UnityEngine.Quaternion)F(m, "openRot");
            var c1 = BoundsOf(tf.gameObject).center;
            tf.localRotation = closedLR[m];
            Check(UnityEngine.Mathf.Abs(UnityEngine.Vector3.Dot(axis, UnityEngine.Vector3.up)) < 0.1f, "PRT05 " + def.id + "/" + tf.name + ": ось духовки не горизонтальна " + axis.ToString("0.00"));
            Check(c1.y < c0.y - 0.02f, "PRT05 " + def.id + "/" + tf.name + ": дверца духовки не идёт вниз (центр " + c0.y.ToString("0.00") + " → " + c1.y.ToString("0.00") + ")");
        }
        // фасад: куда в среднем уходят центры частей при полном открытии
        var front = UnityEngine.Vector3.zero;
        foreach (var m in mine) {
            var tf = (UnityEngine.Transform)F(m, "tf"); var c0 = BoundsOf(tf.gameObject).center;
            if ((bool)F(m, "rotate")) tf.localRotation = (UnityEngine.Quaternion)F(m, "openRot"); else tf.localPosition = (UnityEngine.Vector3)F(m, "openPos");
            front += BoundsOf(tf.gameObject).center - c0;
            tf.localRotation = closedLR[m]; tf.localPosition = closedLP[m];
        }
        front.y = 0f;
        UnityEngine.Physics.SyncTransforms();
        // PRT03 в чистом поле каждая часть открывается до конца (limit 1): мешать ей нечему, кроме своего же корпуса
        io.SetAllDoors(true); Settle(io);
        foreach (var m in mine) {
            var tf = (UnityEngine.Transform)F(m, "tf"); float lim = (float)F(m, "limit");
            Check(lim >= 0.99f, "PRT03 " + def.id + "/" + tf.name + ": в чистом поле открывается только на " + (lim * 100f).ToString("0") + " % (" + ((bool)F(m, "rotate") ? (lim * UnityEngine.Quaternion.Angle((UnityEngine.Quaternion)F(m, "closedRot"), (UnityEngine.Quaternion)F(m, "openRot"))).ToString("0") + "°" : "хода") + ") — упирается в свой корпус или соседнюю створку");
        }
        io.SetAllDoors(false); Settle(io);
        // PRT03s стабильность: предел каждой части один и тот же, на каком бы кадре анимации ни стояли соседи
        io.SetAllDoors(true);
        foreach (var m in mine) {
            var tf = (UnityEngine.Transform)F(m, "tf");
            float first = float.NaN;
            foreach (float mid in new[] { 0f, 0.1f, 0.3f, 0.6f }) {
                foreach (var o in mine) if (o != m) setPose.Invoke(io, new object[] { o, mid });
                float lim = (float)openLimitM.Invoke(io, new object[] { m });
                if (float.IsNaN(first)) first = lim;
                Check(UnityEngine.Mathf.Abs(lim - first) < 0.001f, "PRT03s " + def.id + "/" + tf.name + ": предел зависит от кадра анимации соседей — при соседях на " + mid.ToString("0.0") + " хода " + lim.ToString("0.00") + ", при закрытых " + first.ToString("0.00"));
            }
            foreach (var o in mine) setPose.Invoke(io, new object[] { o, 0f });
        }
        io.SetAllDoors(false); Settle(io);
        // PRT06 стена сзади и соседи по бокам
        var blocks = new System.Collections.Generic.List<UnityEngine.Collider>();
        if (front.sqrMagnitude > 1e-4f) {
            bool alongX = UnityEngine.Mathf.Abs(front.x) > UnityEngine.Mathf.Abs(front.z);
            float sgn = alongX ? UnityEngine.Mathf.Sign(front.x) : UnityEngine.Mathf.Sign(front.z);
            var e = body.extents; var c = body.center; const float gap = 0.003f;
            if (alongX) {
                blocks.Add(Box(new UnityEngine.Vector3(c.x - sgn * (e.x + gap + 0.05f), c.y, c.z), new UnityEngine.Vector3(0.1f, e.y * 2f + 1f, e.z * 2f + 3f)).GetComponent<UnityEngine.Collider>());
                blocks.Add(Box(new UnityEngine.Vector3(c.x, c.y, c.z + e.z + gap + 0.5f), new UnityEngine.Vector3(e.x * 2f, e.y * 2f, 1f)).GetComponent<UnityEngine.Collider>());
                blocks.Add(Box(new UnityEngine.Vector3(c.x, c.y, c.z - e.z - gap - 0.5f), new UnityEngine.Vector3(e.x * 2f, e.y * 2f, 1f)).GetComponent<UnityEngine.Collider>());
            } else {
                blocks.Add(Box(new UnityEngine.Vector3(c.x, c.y, c.z - sgn * (e.z + gap + 0.05f)), new UnityEngine.Vector3(e.x * 2f + 3f, e.y * 2f + 1f, 0.1f)).GetComponent<UnityEngine.Collider>());
                blocks.Add(Box(new UnityEngine.Vector3(c.x + e.x + gap + 0.5f, c.y, c.z), new UnityEngine.Vector3(1f, e.y * 2f, e.z * 2f)).GetComponent<UnityEngine.Collider>());
                blocks.Add(Box(new UnityEngine.Vector3(c.x - e.x - gap - 0.5f, c.y, c.z), new UnityEngine.Vector3(1f, e.y * 2f, e.z * 2f)).GetComponent<UnityEngine.Collider>());
            }
            UnityEngine.Physics.SyncTransforms();
            io.SetAllDoors(true); Settle(io);
            float worst = 0f, worstVis = 0f; string worstAt = "", visAt = "";
            foreach (var m in mine) {
                var tf = (UnityEngine.Transform)F(m, "tf");
                var pc = tf.GetComponent<UnityEngine.BoxCollider>();
                if (pc == null) continue;
                // коробка так, как её видит игра (OpenLimit): петля подрезана на HingeSlack, кожа OpenSkin
                var c0 = pc.center; var s0 = pc.size;
                if ((bool)F(m, "rotate")) { int a = 0; if (UnityEngine.Mathf.Abs(c0.y) > UnityEngine.Mathf.Abs(c0[a])) a = 1; if (UnityEngine.Mathf.Abs(c0.z) > UnityEngine.Mathf.Abs(c0[a])) a = 2; float trim = UnityEngine.Mathf.Min(0.09f, s0[a] * 0.5f); s0[a] -= trim; c0[a] += (c0[a] >= 0f ? 1f : -1f) * trim * 0.5f; }
                var probeGo = new UnityEngine.GameObject("kitchen_parts_probe_box"); made.Add(probeGo);
                probeGo.transform.SetParent(tf, false);
                var gb = probeGo.AddComponent<UnityEngine.BoxCollider>(); gb.isTrigger = true; gb.center = c0;
                var sc = tf.lossyScale; gb.size = UnityEngine.Vector3.Max(s0 - new UnityEngine.Vector3(0.024f / UnityEngine.Mathf.Abs(sc.x), 0.024f / UnityEngine.Mathf.Abs(sc.y), 0.024f / UnityEngine.Mathf.Abs(sc.z)), UnityEngine.Vector3.one * 0.004f);
                UnityEngine.Physics.SyncTransforms();
                foreach (var bc in blocks) {
                    UnityEngine.Vector3 dir; float dist;
                    string where = tf.name + " в " + (bc == blocks[0] ? "стену" : "соседа");
                    if (UnityEngine.Physics.ComputePenetration(gb, gb.transform.position, gb.transform.rotation, bc, bc.transform.position, bc.transform.rotation, out dir, out dist) && dist > worst) { worst = dist; worstAt = where; }
                    if (UnityEngine.Physics.ComputePenetration(pc, pc.transform.position, pc.transform.rotation, bc, bc.transform.position, bc.transform.rotation, out dir, out dist) && dist > worstVis) { worstVis = dist; visAt = where; }
                }
                made.Remove(probeGo); UnityEngine.Object.DestroyImmediate(probeGo);
            }
            Check(worst <= 0.005f, "PRT06 " + def.id + ": открытая часть " + worstAt + " на " + (worst * 1000f).ToString("0") + " мм (коробка игры, без петли и кожи)");
            if (worstVis > 0.02f) { visNote++; if (visNote <= 25) vis.Append(def.id + " " + visAt + " " + (worstVis * 1000f).ToString("0") + " мм; "); }
            io.SetAllDoors(false); Settle(io);
            foreach (var bc in blocks) { made.Remove(bc.gameObject); UnityEngine.Object.DestroyImmediate(bc.gameObject); }
            UnityEngine.Physics.SyncTransforms();
        }
        // PRT07 открыть→закрыть ×3
        for (int round = 0; round < 3; round++) { io.SetAllDoors(true); Settle(io); io.SetAllDoors(false); Settle(io); }
        foreach (var m in mine) {
            var tf = (UnityEngine.Transform)F(m, "tf");
            float dp = (tf.localPosition - closedLP[m]).magnitude * (tf.parent != null ? tf.parent.lossyScale.x : 1f);
            float da = UnityEngine.Quaternion.Angle(tf.localRotation, closedLR[m]);
            Check(dp <= 0.001f && da <= 0.5f, "PRT07 " + def.id + "/" + tf.name + ": после 3 циклов сдвиг " + (dp * 1000f).ToString("0.0") + " мм, " + da.ToString("0.0") + "°");
        }
        // PRT08 сейв открытого: путь загрузки RestoreOne
        io.SetAllDoors(true); Settle(io);
        var openLP = new System.Collections.Generic.Dictionary<string, UnityEngine.Vector3>();
        var openLR = new System.Collections.Generic.Dictionary<string, UnityEngine.Quaternion>();
        var openSec = new System.Collections.Generic.Dictionary<string, bool>();
        foreach (var m in mine) { var tf = (UnityEngine.Transform)F(m, "tf"); openLP[tf.name] = tf.localPosition; openLR[tf.name] = tf.localRotation; }
        int si = 0; foreach (var f in io.Features) if (f is Cozy.Grid.AccessFeature a) openSec[(si++) + ":" + a.Title] = a.Open;
        var rec = snapshot.Invoke(null, new object[] { io });
        collectF.Invoke(null, new object[] { io, rec });
        var json = UnityEngine.JsonUtility.ToJson(rec);
        var rec2 = UnityEngine.JsonUtility.FromJson(json, rec.GetType());
        made.Remove(io.gameObject); UnityEngine.Object.DestroyImmediate(io.gameObject);
        var ps = restoreOne.GetParameters();
        var back = (Cozy.Grid.InteractiveObject)restoreOne.Invoke(cursor, new object[] { rec2, System.Activator.CreateInstance(ps[1].ParameterType), System.Activator.CreateInstance(ps[2].ParameterType) });
        if (back == null) { Check(false, "PRT08 " + def.id + ": RestoreOne вернул null"); continue; }
        made.Add(back.gameObject);
        Settle(back);
        si = 0; foreach (var f in back.Features) if (f is Cozy.Grid.AccessFeature a) { var key = (si++) + ":" + a.Title; bool was; if (openSec.TryGetValue(key, out was)) Check(was == a.Open, "PRT08 " + def.id + ": секция «" + a.Title + "» была " + (was ? "открыта" : "закрыта") + ", после загрузки " + (a.Open ? "открыта" : "закрыта")); }
        foreach (var m in fMoving.GetValue(back) as System.Collections.IList) {
            var tf = (UnityEngine.Transform)F(m, "tf");
            if (tf == null || !openLP.ContainsKey(tf.name)) continue;
            float dp = (tf.localPosition - openLP[tf.name]).magnitude * (tf.parent != null ? tf.parent.lossyScale.x : 1f);
            float da = UnityEngine.Quaternion.Angle(tf.localRotation, openLR[tf.name]);
            Check(dp <= 0.001f && da <= 0.5f, "PRT08 " + def.id + "/" + tf.name + ": после загрузки поза открытой отличается на " + (dp * 1000f).ToString("0.0") + " мм, " + da.ToString("0.0") + "°");
        }
        made.Remove(back.gameObject); UnityEngine.Object.DestroyImmediate(back.gameObject);
    }
} finally {
    foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g);
    UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — дефов с частями " + defs + ", частей " + parts + ", духовок " + ovens + ", без ходящих частей " + skipped + " (созданное удалено)\n" + sb + (visNote > 0 ? "INFO PRT06 у петли (зона HingeSlack 9 см игра не проверяет by design) полный бокс створки заходит в соседа > 20 мм у " + visNote + " дефов: " + vis : "");
