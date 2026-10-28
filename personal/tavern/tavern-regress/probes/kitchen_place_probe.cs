// ПОСТАНОВКА КУХОННОЙ МЕБЕЛИ (KITCHEN.md: KT-POS01, 02, 04, 07, IN03–05; 18.10). Для execute_code в play.
// Нужна свободная нарисованная стена своего этажа с нарисованным ПОЛОМ перед ней в 20 м от героя (3 м вдоль неё пусто), иначе SKIP.
// Все позы — НАСТОЯЩИМ ComputeObjectPose с камерой, довёрнутой на точку через настоящий курсор
// (как wall_hang_probe.cs): прицел, призрак, привязка к стене и соседям — как у игрока. Ставит SpawnObject в эту позу.
//  POS01 каждый напольный кухонный деф (Кухня / прибор с tempSources / id *kitchen*, seatToWall) у стены:
//        зелёный, задом к стене (зазор 0…20 мм, в стену не глубже 2 мм); рядом с ним эталонная тумба,
//        прицел на 3 см мимо стыка: не входят друг в друга (≤ 2 мм), зазор стыка — в отчёт;
//  POS02 верх столешниц рядом стоящих тумб одной высоты (±1 мм) — среди дефов с верхом в ±10 см от эталона;
//  POS04 навесные кухонные (mount Wall, seatToWall или Кухня) на высоте 1,7 м: зелёные, к стене ≤ 20 мм,
//        не в стене, низ выше пола, верх ниже плиты перекрытия (3 − 0,2);
//  POS07 холодильник вплотную к тумбе: его дверца открывается (OpenLimit ≥ 0,8) — сосед не мешает;
//  IN03/IN04 кружка в открытый ящик (настоящая поза над ящиком): на дне ±5 мм, едет с ящиком, после закрытия
//        внутри корпуса (не торчит > 5 мм);
//  IN05 кружка на столешницу: низ на верхе ±5 мм.
// Всё созданное удаляется, камера возвращается в finally.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var spawn = T.GetMethod("SpawnObject", B);
var tick = typeof(Cozy.Grid.InteractiveObject).GetMethod("Tick", B);
var fMoving = typeof(Cozy.Grid.InteractiveObject).GetField("_moving", B);
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursorPx = mouse.position.ReadValue();
var savedPos = cam.transform.position; var savedRot = cam.transform.rotation;
var player = Cozy.Grid.PlayerRef.GameObject;
float cell = 3f;
float floorY = Cozy.Grid.GridManager.LevelY(player.transform.position.y + 0.05f, cell);
Cozy.Grid.GridBlock wall = null; var back = UnityEngine.Vector3.zero; bool wallThinX = false;
var cols = new UnityEngine.Collider[64];
foreach (var gb in Cozy.Grid.GridBlock.All) {
    if (gb == null || gb.role != Cozy.Grid.GridRole.Wall || gb.railing || !Cozy.Grid.FloorPieceView.Drawn(gb.Rend)) continue;
    var p = gb.transform.position; var s = gb.transform.lossyScale;
    if (UnityEngine.Mathf.Abs(p.y - s.y * 0.5f - floorY) > 0.3f) continue;
    if ((p - player.transform.position).sqrMagnitude > 400f) continue;
    bool thinX = s.x < s.z;
    if ((thinX ? s.z : s.x) < 2.9f) continue;
    var toP = player.transform.position - p;
    var n = thinX ? new UnityEngine.Vector3(UnityEngine.Mathf.Sign(toP.x), 0f, 0f) : new UnityEngine.Vector3(0f, 0f, UnityEngine.Mathf.Sign(toP.z));
    var probe = new UnityEngine.Vector3(p.x, floorY + 1.4f, p.z) + n * 1.0f;
    int hits = UnityEngine.Physics.OverlapBoxNonAlloc(probe, new UnityEngine.Vector3(thinX ? 0.9f : 1.45f, 1.3f, thinX ? 1.45f : 0.9f), cols, UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
    bool busy = false;
    for (int i = 0; i < hits; i++)
        if (cols[i].GetComponentInParent<Cozy.Grid.InteractiveObject>() != null || cols[i].GetComponentInParent<Cozy.Grid.StairPiece>() != null || cols[i].GetComponentInParent<Cozy.Grid.DoorPiece>() != null || cols[i].GetComponentInParent<Cozy.Grid.GridBlock>() != null && cols[i].GetComponentInParent<Cozy.Grid.GridBlock>() != gb && cols[i].GetComponentInParent<Cozy.Grid.GridBlock>().role == Cozy.Grid.GridRole.Wall) { busy = true; break; }
    if (busy) continue;
    // перед стеной нужен нарисованный ПОЛ дома (на земле уровня тумба к стене не садится — это не кухня)
    UnityEngine.RaycastHit fh;
    if (!UnityEngine.Physics.Raycast(new UnityEngine.Vector3(p.x, floorY + 1f, p.z) + n * 0.6f, UnityEngine.Vector3.down, out fh, 1.5f)) continue;
    var fb = fh.collider.GetComponentInParent<Cozy.Grid.GridBlock>();
    if (fb == null || fb.role != Cozy.Grid.GridRole.Floor || !Cozy.Grid.FloorPieceView.Drawn(fb.Rend)) continue;
    wall = gb; back = -n; wallThinX = thinX; break;
}
if (wall == null) return "SKIP: нет свободной нарисованной стены с нарисованным полом перед ней (3 м, пусто) в 20 м от героя — нужен дом (level1, kitchen_test); POS01, 02, 04, 07, IN03–05 не проверены";
var sb = new System.Text.StringBuilder(); var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 60) sb.Append("FAIL " + line + "\n"); } };
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
var wp = wall.transform.position; var ws = wall.transform.lossyScale;
float halfT = (wallThinX ? ws.x : ws.z) * 0.5f;
var along = wallThinX ? UnityEngine.Vector3.forward : UnityEngine.Vector3.right;
var faceCenter = new UnityEngine.Vector3(wp.x, floorY, wp.z) - back * halfT;   // плоскость стены со стороны героя, на полу
float faceCoord = UnityEngine.Vector3.Dot(faceCenter, -back);                   // координата плоскости по нормали к комнате
System.Func<UnityEngine.GameObject, UnityEngine.Bounds> BoundsOf = go => {
    var b = new UnityEngine.Bounds(go.transform.position, UnityEngine.Vector3.zero); bool first = true;
    foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>()) { if (!r.enabled || Cozy.Grid.InteractHighlight.IsCopy(r) || r is UnityEngine.ParticleSystemRenderer) continue; if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
    return b;
};
// поза настоящим курсором: камера смотрит на точку target под углом сверху со стороны комнаты
System.Func<Cozy.Grid.ObjectDef, UnityEngine.Vector3, float, object[]> Pose = (def, target, pitchDown) => {
    var body = new UnityEngine.GameObject("KitchenPlaceProbe"); made.Add(body);
    body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
    var worldDir = (back + UnityEngine.Vector3.down * pitchDown).normalized;
    cam.transform.SetPositionAndRotation(target - worldDir * 3f, UnityEngine.Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursorPx.x, cursorPx.y, 0f)).direction;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursorPx.x, cursorPx.y, 0f)).direction * 3f;
    UnityEngine.Physics.SyncTransforms();
    var args = new object[] { def, cam, mouse, body, body.transform, floorY, null, null, null };
    bool ok = (bool)mPose.Invoke(gc, args);
    made.Remove(body); UnityEngine.Object.DestroyImmediate(body);
    return new object[] { ok, args[6], args[7], args[8] };
};
System.Func<Cozy.Grid.ObjectDef, object[], Cozy.Grid.InteractiveObject> Put = (def, pose) => {
    var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[] { def, (UnityEngine.Vector3)pose[1], (float)pose[2] });
    if (io != null) made.Add(io.gameObject);
    UnityEngine.Physics.SyncTransforms();
    return io;
};
System.Action<Cozy.Grid.InteractiveObject> Settle = io => { for (int k = 0; k < 3000; k++) tick.Invoke(io, null); UnityEngine.Physics.SyncTransforms(); };
System.Action Clear = () => { foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g); made.Clear(); UnityEngine.Physics.SyncTransforms(); };
// от стены: >0 — зазор, <0 — в стене
System.Func<UnityEngine.Bounds, float> WallGap = b => { var ext = UnityEngine.Vector3.Scale(b.extents, new UnityEngine.Vector3(UnityEngine.Mathf.Abs(back.x), 0f, UnityEngine.Mathf.Abs(back.z))).magnitude; return (UnityEngine.Vector3.Dot(b.center, -back) - ext) - faceCoord; };
System.Func<UnityEngine.Bounds, float> HalfAlong = b => UnityEngine.Vector3.Scale(b.extents, new UnityEngine.Vector3(UnityEngine.Mathf.Abs(along.x), 0f, UnityEngine.Mathf.Abs(along.z))).magnitude;
var refDef = Cozy.Grid.FurnitureCatalog.ById("home_kitchen_counter");
var cupDef = Cozy.Grid.FurnitureCatalog.ById("coffee_cup_red");
var floorDefs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
var wallDefs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All()) {
    if (d == null || d.hostPart) continue;
    bool kitchen = d.category == Cozy.Grid.Categories.Kitchen || d.id.Contains("kitchen") || (d.tempSources != null && d.tempSources.Count > 0 && d.mount == Cozy.Grid.ObjectMount.Floor && !d.id.Contains("fireplace") && !d.id.Contains("stove_wood"));
    if (!kitchen) continue;
    if (d.mount == Cozy.Grid.ObjectMount.Floor && d.seatToWall) floorDefs.Add(d);
    else if (d.mount == Cozy.Grid.ObjectMount.Wall && string.IsNullOrEmpty(d.hostVariants)) wallDefs.Add(d);
}
float refTop = float.NaN;
var slotA = faceCenter + back * 0f - back * 0.5f;   // точка на полу в 0,5 м от стены, у центра стены
// Герой — в досягаемость (правило 2 регресса, 19.10): поза тянется к игроку по досягаемости, и герой в 8 м
// от стены давал призрак в метре от неё и красный — проба краснела по-разному от того, где он стоял.
var savedFeet = Cozy.Character.PlayerTarget.Feet;
gc.TeleportPlayerTo(faceCenter - back * 1.5f); UnityEngine.Physics.SyncTransforms();
// Поворот призрака — состояние курсора (R у игрока), не проба: при 0° мебель вставала боком к стене, и POS01
// краснел или зеленел от того, как курсор крутили до пробы. Спиной к стене — и вернуть как было.
var fFreeYaw = T.GetField("_freeYaw", B); var fOrient = T.GetField("_orient", B);
object savedFreeYaw = fFreeYaw.GetValue(gc), savedOrient = fOrient.GetValue(gc);
float backYaw = UnityEngine.Mathf.Repeat(UnityEngine.Mathf.Atan2(back.x, back.z) * UnityEngine.Mathf.Rad2Deg, 360f);
fFreeYaw.SetValue(gc, backYaw); fOrient.SetValue(gc, UnityEngine.Mathf.RoundToInt(backYaw / 90f) % 4);
try {
    // эталонная высота столешницы
    if (refDef != null) {
        var pr = Pose(refDef, slotA - along * 0.8f, 0.9f);
        if ((bool)pr[0]) { var r = Put(refDef, pr); if (r != null) refTop = BoundsOf(r.gameObject).max.y; }
        Clear();
    }
    foreach (var def in floorDefs) {
        var pa = Pose(def, slotA - along * 0.8f, 0.9f);
        if (!(bool)pa[0]) { Check(false, "POS01 " + def.id + ": у свободной стены нет позы"); continue; }
        Check(!(bool)pa[3], "POS01 " + def.id + ": у свободной стены призрак красный");
        var a = Put(def, pa); if (a == null) { Check(false, "POS01 " + def.id + ": не заспавнился"); continue; }
        var ba = BoundsOf(a.gameObject);
        float g = WallGap(ba);
        Check(g >= -0.002f && g <= 0.02f, "POS01 " + def.id + ": от стены " + (g * 1000f).ToString("0") + " мм (ждём 0…20)");
        // сосед — эталонная тумба справа, прицел на 3 см мимо стыка
        if (refDef != null) {
            float halfA = HalfAlong(ba);
            var tgt = new UnityEngine.Vector3(ba.center.x, floorY, ba.center.z) + along * (halfA + 0.33f + 0.03f);
            tgt = tgt + back * (UnityEngine.Vector3.Dot(tgt, -back) - faceCoord - 0.5f) * 1f;
            var pb = Pose(refDef, tgt, 0.9f);
            if ((bool)pb[0] && !(bool)pb[3]) {
                var b = Put(refDef, pb); var bb = BoundsOf(b.gameObject);
                var ia = ba; ia.Expand(-0.004f);
                float gapAlong = UnityEngine.Vector3.Dot(bb.center - ba.center, along) - HalfAlong(bb) - halfA;
                Check(gapAlong >= -0.002f, "POS01 " + def.id + " + home_kitchen_counter: входят друг в друга на " + (-gapAlong * 1000f).ToString("0") + " мм");
                info.Append(def.id + "|стык " + (gapAlong * 1000f).ToString("0") + " мм; ");
                if (!float.IsNaN(refTop) && UnityEngine.Mathf.Abs(ba.max.y - refTop) <= 0.10f)
                    Check(UnityEngine.Mathf.Abs(ba.max.y - bb.max.y) <= 0.001f, "POS02 " + def.id + ": верх " + (ba.max.y - floorY).ToString("0.000") + " м, у соседней тумбы " + (bb.max.y - floorY).ToString("0.000") + " м");
                // POS07: дверцы соседа открываются целиком (сосед не мешает)
                foreach (var who in new[] { a, b }) {
                    who.SetAllDoors(true); Settle(who);
                    foreach (var m in fMoving.GetValue(who) as System.Collections.IList) {
                        var tf = (UnityEngine.Transform)m.GetType().GetField("tf").GetValue(m);
                        if (m.GetType().GetField("access").GetValue(m) == null || (bool)m.GetType().GetField("swap").GetValue(m)) continue;
                        float lim = (float)m.GetType().GetField("limit").GetValue(m);
                        Check(lim >= 0.8f, "POS07 " + who.Def.id + "/" + tf.name + " рядом с " + (who == a ? refDef.id : def.id) + ": открывается только на " + (lim * 100f).ToString("0") + " %");
                    }
                    who.SetAllDoors(false); Settle(who);
                }
            } else info.Append(def.id + "|сосед справа: " + ((bool)pb[0] ? "красный" : "нет позы") + "; ");
        }
        // IN03/IN04: кружка в открытый ящик
        if (cupDef != null) {
            foreach (var slot in a.GetComponentsInChildren<Cozy.Grid.ContainerSlot>()) {
                if (slot.carrier == null || slot.Gate == null) continue;
                var col = slot.GetComponent<UnityEngine.Collider>(); if (col == null) continue;
                slot.Gate.SetOpen(true); Settle(a);
                var top = col.bounds; var aim = new UnityEngine.Vector3(top.center.x, top.max.y, top.center.z);
                var pc = Pose(cupDef, aim, 2.5f);
                if (!(bool)pc[0] || (bool)pc[3]) { info.Append(def.id + "/" + slot.carrier.name + "|кружка в ящик: " + ((bool)pc[0] ? "красный" : "нет позы") + "; "); slot.Gate.SetOpen(false); Settle(a); continue; }
                var cup = Put(cupDef, pc); gc.ReattachToContainer(cup);
                var cb = BoundsOf(cup.gameObject);
                Check(UnityEngine.Mathf.Abs(cb.min.y - top.max.y) <= 0.005f, "IN03 " + def.id + "/" + slot.carrier.name + ": кружка не на дне ящика, низ " + ((cb.min.y - top.max.y) * 1000f).ToString("0") + " мм от дна");
                Check(cup.transform.IsChildOf(slot.carrier), "IN04 " + def.id + "/" + slot.carrier.name + ": кружка не привязана к ящику (родитель " + (cup.transform.parent != null ? cup.transform.parent.name : "-") + ")");
                var carrier0 = slot.carrier.position; var cup0 = cup.transform.position;
                slot.Gate.SetOpen(false); Settle(a);
                var moved = (slot.carrier.position - carrier0) - (cup.transform.position - cup0);
                Check(moved.magnitude <= 0.001f, "IN04 " + def.id + "/" + slot.carrier.name + ": при закрытии кружка отстала от ящика на " + (moved.magnitude * 1000f).ToString("0") + " мм");
                var shut = BoundsOf(a.gameObject); var cb2 = BoundsOf(cup.gameObject);
                float stick = UnityEngine.Mathf.Max(0f, UnityEngine.Mathf.Max(cb2.max.y - shut.max.y, UnityEngine.Vector3.Dot(cb2.center, -back) + UnityEngine.Vector3.Scale(cb2.extents, new UnityEngine.Vector3(UnityEngine.Mathf.Abs(back.x), 0f, UnityEngine.Mathf.Abs(back.z))).magnitude - (UnityEngine.Vector3.Dot(shut.center, -back) + UnityEngine.Vector3.Scale(shut.extents, new UnityEngine.Vector3(UnityEngine.Mathf.Abs(back.x), 0f, UnityEngine.Mathf.Abs(back.z))).magnitude)));
                Check(stick <= 0.005f, "IN03 " + def.id + "/" + slot.carrier.name + ": ящик закрыт, кружка торчит наружу на " + (stick * 1000f).ToString("0") + " мм");
                made.Remove(cup.gameObject); UnityEngine.Object.DestroyImmediate(cup.gameObject);
            }
        }
        // IN05: кружка на столешницу
        if (cupDef != null && !float.IsNaN(refTop) && UnityEngine.Mathf.Abs(ba.max.y - refTop) <= 0.10f) {
            var aim = new UnityEngine.Vector3(ba.center.x, ba.max.y, ba.center.z);
            var pc = Pose(cupDef, aim, 2.5f);
            if ((bool)pc[0] && !(bool)pc[3]) {
                var cup = Put(cupDef, pc); var cb = BoundsOf(cup.gameObject);
                Check(UnityEngine.Mathf.Abs(cb.min.y - ba.max.y) <= 0.005f, "IN05 " + def.id + ": кружка на столешнице, низ " + ((cb.min.y - ba.max.y) * 1000f).ToString("0") + " мм от верха");
            } else Check(false, "IN05 " + def.id + ": кружка на столешницу — " + ((bool)pc[0] ? "красный" : "нет позы"));
        }
        Clear();
    }
    foreach (var def in wallDefs) {
        var pw = Pose(def, faceCenter + UnityEngine.Vector3.up * 1.7f - back * 0.02f + along * 0.4f, 0.1f);
        if (!(bool)pw[0]) { Check(false, "POS04 " + def.id + ": на свободной стене нет позы"); continue; }
        Check(!(bool)pw[3], "POS04 " + def.id + ": на свободной стене красный");
        var w = Put(def, pw); if (w == null) continue;
        var bw = BoundsOf(w.gameObject);
        float g = WallGap(bw);
        Check(g >= -0.002f && g <= 0.02f, "POS04 " + def.id + ": от стены " + (g * 1000f).ToString("0") + " мм (ждём 0…20)");
        Check(bw.min.y > floorY + 0.5f, "POS04 " + def.id + ": низ навесного на " + (bw.min.y - floorY).ToString("0.00") + " м от пола");
        Check(bw.max.y <= floorY + cell - 0.2f + 0.01f, "POS04 " + def.id + ": верх в плите перекрытия (" + (bw.max.y - floorY).ToString("0.00") + " > 2,80)");
        Clear();
    }
} finally {
    Clear();
    gc.TeleportPlayerTo(savedFeet);
    fFreeYaw.SetValue(gc, savedFreeYaw); fOrient.SetValue(gc, savedOrient);
    cam.transform.SetPositionAndRotation(savedPos, savedRot);
    UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — напольных " + floorDefs.Count + ", навесных " + wallDefs.Count + ", стена " + wp.ToString("0.0") + ", верх эталона " + (refTop - floorY).ToString("0.000") + " (созданное удалено)\n" + sb + (info.Length > 0 ? "INFO " + info : "") + "\nSKIP POS06 (подсветка в гнездо под шкафом — hostVariants, отдельный путь), IN06 (полки навесного).";
