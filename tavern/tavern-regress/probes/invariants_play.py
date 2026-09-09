"""Проверка ЖИВЫХ инвариантов в play: то, что тестами EditMode не поймать.

Каждая проверка — уже пойманный когда-то баг. Список правил: INVARIANTS.md (tavern-regress).
Запускать после любой правки взаимодействия, наведения или контейнеров.
"""
import json, subprocess, sys

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bad = new System.Text.StringBuilder();
var cam = UnityEngine.Camera.main;
var t = typeof(Cozy.Grid.Interactor);
var skip = t.GetMethod("SkipHit", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var hits = new UnityEngine.RaycastHit[24];
int closed = 0, checkedObjects = 0;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null) continue;
    checkedObjects++;
    // 1. Предмет в ЗАКРЫТОЙ секции не наводится и не выделяется.
    if (Cozy.Grid.ContainerSlot.HoldsClosed(io))
    {
        closed++;
        var rend = io.GetComponentInChildren<UnityEngine.Renderer>();
        if (rend != null && cam != null && skip != null)
        {
            var ray = new UnityEngine.Ray(cam.transform.position, (rend.bounds.center - cam.transform.position).normalized);
            int n = Cozy.Grid.RayPick.Sorted(ray, 25f, hits);
            for (int i = 0; i < n; i++)
            {
                var col = hits[i].collider;
                if (col.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io) continue;
                var cand = col.GetComponentInParent<Cozy.Grid.IInteractable>();
                if (!(bool)skip.Invoke(null, new object[] { col, cand }))
                    bad.Append("наводится сквозь закрытую секцию: " + io.Def.id + "; ");
                break;
            }
        }
    }
    // 2. Жидкости не больше ёмкости.
    if (io.Liquid != null && io.Liquid.Litres > io.Liquid.Capacity + 0.001f)
        bad.Append("перелив: " + io.Def.id + "; ");
    // 3. Ни одного объекта без видимых мешей — кроме погашенных этажным или
    //    комнатным гейтом (FloorPieceView.Visible == false): с 1 этажа спальня
    //    и должна быть скрыта, её ловят правила 11–12, а не это.
    int visible = 0;
    foreach (var r in io.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
        if (r.enabled && r.gameObject.activeInHierarchy && !r.name.StartsWith("Outline")) visible++;
    //    Метки спавна (игрока и монстров) — не поломка: их модель включена
    //    только при SpawnPoint.ShowVisual (дебаг), вне дебага они и должны
    //    быть без мешей (разбор ilya-44, 06.09).
    var gate = io.GetComponent<Cozy.Grid.FloorPieceView>();
    bool marker = io.Def.id == Cozy.Grid.SpawnPoint.ObjectId || io.Def.id == Cozy.Grid.MonsterSpawnPoint.ObjectId;
    if (visible == 0 && (gate == null || gate.Visible) && !(marker && !Cozy.Grid.SpawnPoint.ShowVisual)) bad.Append("невидимый объект: " + io.Def.id + "; ");
    // 4. Вложенный предмет знает своего хозяина: без Container правило
    //    «в закрытой секции не трогают» слепнет.
    if (io.transform.parent != null && io.Container == null
        && io.transform.parent.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null
        && io.transform.parent.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io)
        bad.Append("вложен, но без Container: " + io.Def.id + "; ");
}
// 5. Подвес шкафа свободен ровно тогда, когда под ним нет лампы того же
//    семейства: занятость считают только родственные по snapToNode объекты
//    (P117: мойка «занимала» подвес раздутым габаритом).
var gc = Cozy.Grid.GridCursor.I;
var mountTaken = gc != null ? gc.GetType().GetMethod("MountTaken", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance) : null;
int mounts = 0;
if (mountTaken != null)
    foreach (var host in Cozy.Grid.InteractiveObject.All)
    {
        if (host == null || host.Def == null || !host.Def.id.StartsWith("home_wall_cabinet")) continue;
        foreach (var node in host.GetComponentsInChildren<UnityEngine.Transform>(true))
        {
            if (!node.name.StartsWith("Mount_Light")) continue;
            mounts++;
            bool lampThere = false;
            foreach (var lamp in Cozy.Grid.InteractiveObject.All)
            {
                if (lamp == null || lamp.Def == null || !lamp.Def.id.StartsWith("home_under_light")) continue;
                var lb = lamp.WorldBounds; lb.Expand(0.2f);
                if (lb.Contains(node.position) || (lamp.transform.position - node.position).sqrMagnitude < 0.04f) { lampThere = true; break; }
            }
            bool taken = (bool)mountTaken.Invoke(gc, new object[] { node.position, "Mount_Light", null });
            if (taken != lampThere) bad.Append("подвес " + node.name + " у " + host.Def.id + ": занят=" + taken + ", лампа=" + lampThere + "; ");
        }
    }
// 6. Камера осмотра ВЛОЖЕННОГО предмета не заходит в его контейнер (P147:
//    зум в осмотре бака уводил камеру в корпус кофемашины). Минимум
//    дистанции с 16 ракурсов ставит камеру снаружи внешнего контейнера.
var mClear = typeof(Cozy.Character.CameraFollow).GetMethod("ClearDistance", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var examineProp = typeof(Cozy.Grid.Interactor).GetProperty("ExamineHost");
var savedHost = examineProp.GetValue(null, null);
int nested = 0;
try
{
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null || io.Container == null) continue;
        var outer = io; while (outer.Container != null) outer = outer.Container;
        var ob = outer.WorldBounds; ob.Expand(-0.02f);
        var focus = io.WorldBounds.center;
        nested++;
        examineProp.SetValue(null, io, null);
        bool inside = false;
        foreach (float pitch in new float[] { 10f, 35f })
        foreach (float yaw in new float[] { 0f, 45f, 90f, 135f, 180f, 225f, 270f, 315f })
        {
            float d = (float)mClear.Invoke(null, new object[] { focus, yaw, pitch, 0.05f, 0.15f });
            var pos = focus + UnityEngine.Quaternion.Euler(pitch, yaw, 0f) * new UnityEngine.Vector3(0f, 0f, -d);
            if (ob.Contains(pos)) inside = true;
        }
        if (inside) bad.Append("камера осмотра внутри контейнера: " + io.Def.id + " в " + outer.Def.id + "; ");
    }
}
finally { examineProp.SetValue(null, savedHost, null); }
// 7. Коллайдер, который стартовая сфера луча осмотра уже задевает, не
//    прозрачен (P161: кастрюля на плите вплотную к столешнице тумбы — тумба
//    исчезала для каста, камера уезжала внутрь). Для каждого объекта с такой
//    чужой преградой чистая дистанция в направлениях, входящих в её коробку,
//    не больше входа в коробку (или пола хозяина).
var mHostFloor = typeof(Cozy.Character.CameraFollow).GetMethod("HostFloor", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
float camR = (float)typeof(Cozy.Character.CameraFollow).GetField("ExamineCamRadius", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).GetRawConstantValue();
var ovl = new UnityEngine.Collider[32];
int touching = 0;
try
{
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null) continue;
        var focus = io.WorldBounds.center;
        int n = UnityEngine.Physics.OverlapSphereNonAlloc(focus, camR, ovl, UnityEngine.Physics.DefaultRaycastLayers, UnityEngine.QueryTriggerInteraction.Ignore);
        var foreign = new System.Collections.Generic.List<UnityEngine.Bounds>();
        for (int k = 0; k < n; k++)
        {
            var col = ovl[k];
            if (Cozy.Grid.RayPick.IsPlayer(col) || col.transform.IsChildOf(io.transform) || io.transform.IsChildOf(col.transform)) continue;
            var part = col.GetComponentInParent<Cozy.Grid.InteractiveObject>();
            if (part != null && (Cozy.Grid.InteractiveObject.InContainer(part, io) || Cozy.Grid.InteractiveObject.Same(part.HostObject, io))) continue;
            var r = col.GetComponent<UnityEngine.Renderer>(); if (r == null) r = col.GetComponentInChildren<UnityEngine.Renderer>();
            if (r != null && !r.enabled) continue;
            if (col.bounds.Contains(focus)) continue;
            foreign.Add(col.bounds);
        }
        if (foreign.Count == 0) continue;
        touching++;
        examineProp.SetValue(null, io, null);
        bool leak = false;
        foreach (float pitch in new float[] { -25f, 10f, 35f })
        foreach (float yaw in new float[] { 0f, 45f, 90f, 135f, 180f, 225f, 270f, 315f })
        {
            var dir = UnityEngine.Quaternion.Euler(pitch, yaw, 0f) * UnityEngine.Vector3.back;
            float entry = float.MaxValue;
            foreach (var b in foreign) { float e; if (b.IntersectRay(new UnityEngine.Ray(focus, dir), out e) && e < entry) entry = e; }
            if (entry == float.MaxValue) continue;
            float d = (float)mClear.Invoke(null, new object[] { focus, yaw, pitch, 3.0f, 0.15f });
            float floorD = (float)mHostFloor.Invoke(null, new object[] { io, focus, dir });
            if (d > UnityEngine.Mathf.Max(entry, floorD) + 0.01f) leak = true;
        }
        if (leak) bad.Append("стартовая преграда прозрачна для осмотра: " + io.Def.id + "; ");
    }
}
finally { examineProp.SetValue(null, savedHost, null); }
// 8. Предмет на ОТКРЫТОЙ поверхности опирается на неё КОРПУСОМ, а не только
//    пивотом (P177: сковорода на угловой тумбе висела диском и ручкой над
//    внутренним углом и выглядела утонувшей в стенке тумбы).
var mSurfSup = gc != null ? gc.GetType().GetMethod("SurfaceSupported", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance) : null;
int onSurface = 0;
if (mSurfSup != null)
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null || io.Def.mount != Cozy.Grid.ObjectMount.Surface || io.HostObject != null) continue;
        var p = io.transform.position; var rot = io.transform.rotation;
        if (Cozy.Grid.ContainerSlot.Under(p) != null) continue;
        onSurface++;
        bool held = (bool)mSurfSup.Invoke(gc, new object[] { io.gameObject, p.x, p.y, p.z, rot.eulerAngles.y, null });
        io.transform.SetPositionAndRotation(p, rot);
        if (!held) bad.Append("корпус висит над пустотой: " + io.Def.id + " @ " + p.ToString("F2") + "; ");
    }
// 9. Порожек двери не делит верхнюю плоскость ни с чем (P181: светлый
//    порожек и тёмная плита пола с верхом ровно 0.000 дрожали полосами).
int thresholds = 0;
foreach (var door in UnityEngine.Object.FindObjectsByType<Cozy.Grid.DoorPiece>(UnityEngine.FindObjectsSortMode.None))
{
    foreach (var tr in door.GetComponentsInChildren<UnityEngine.Renderer>(true))
    {
        if (!tr.enabled || tr.transform.name != "Threshold") continue;
        thresholds++;
        var tb = tr.bounds;
        foreach (var other in UnityEngine.Object.FindObjectsByType<UnityEngine.Renderer>(UnityEngine.FindObjectsSortMode.None))
        {
            if (other == tr || !other.enabled || other.transform.IsChildOf(door.transform)) continue;
            var ob = other.bounds;
            if (UnityEngine.Mathf.Abs(ob.max.y - tb.max.y) > 0.0002f) continue;
            if (!(tb.min.x < ob.max.x - 0.001f && ob.min.x < tb.max.x - 0.001f)) continue;
            if (!(tb.min.z < ob.max.z - 0.001f && ob.min.z < tb.max.z - 0.001f)) continue;
            bad.Append("порожек делит плоскость с " + other.transform.name + " на " + tb.max.y.ToString("F4") + "; ");
        }
    }
}
// 10. Стена не проходит сквозь корпус объекта у стены (P220: шкаф-купе и
//     кровать ставились поперёк стены и торцом в боковую). Допуск есть только
//     со спины — обшивка, ≤ 12 см; с боков и спереди стена в коробке = брак.
var mDeep = gc != null ? gc.GetType().GetMethod("WallDeepInside", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static) : null;
var mBox = gc != null ? gc.GetType().GetMethod("LocalBox", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static) : null;
int nearWall = 0;
if (mDeep != null && mBox != null)
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null) continue;
        var d = io.Def;
        if (!(d.seatToWall || d.anchor == Cozy.Grid.ObjectAnchor.Back || d.mount == Cozy.Grid.ObjectMount.Wall)) continue;
        object[] boxArgs = new object[] { io.gameObject, null, null };
        if (!(bool)mBox.Invoke(null, boxArgs)) continue;
        var c0 = (UnityEngine.Vector3)boxArgs[1]; var half = (UnityEngine.Vector3)boxArgs[2];
        var wb = io.WorldBounds;
        var cols = UnityEngine.Physics.OverlapBox(wb.center, wb.extents, UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
        bool any = false;
        foreach (var col in cols)
        {
            if (col.transform.IsChildOf(io.transform) || !Cozy.Grid.BuildQuery.WallLike(col)) continue;
            any = true;
            if ((bool)mDeep.Invoke(null, new object[] { col, io.gameObject, c0, half }))
            { bad.Append("стена в корпусе: " + d.id + " @ " + io.transform.position.ToString("F1") + "; "); break; }
        }
        if (any) nearWall++;
    }
// 11. Скрытый этажным/комнатным гейтом объект НЕ глотает луч (P231: с 1 этажа
//     выключенные коробки спальни были первым хитом на пути к холодильнику).
int hiddenObjs = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null || skip == null) continue;
    var fv = io.GetComponent<Cozy.Grid.FloorPieceView>();
    if (fv == null || fv.Visible) continue;
    var col = io.GetComponent<UnityEngine.Collider>();
    if (col == null) continue;
    hiddenObjs++;
    if (!(bool)skip.Invoke(null, new object[] { col, (Cozy.Grid.IInteractable)io }))
        bad.Append("скрытый объект глотает луч: " + io.Def.id + "; ");
}
// 12. Настенный объект гаснет ТОЛЬКО со стеной своего этажа (P232: шкафчик на
//     2.05 м матчил стену 2 этажа и пропадал при взгляде с 1 этажа).
int wallMounted = 0;
var fYMin = typeof(Cozy.Grid.WallCutaway).GetField("_yMin", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
float cellSz = Cozy.Grid.FurnitureModel.CellSize();
foreach (var wm in UnityEngine.Object.FindObjectsByType<Cozy.Grid.WallMountedCut>(UnityEngine.FindObjectsSortMode.None))
{
    wallMounted++;
    var fv = wm.GetComponent<Cozy.Grid.FloorPieceView>();
    if (fv == null || !fv.WallCut || fYMin == null) continue;
    var back = wm.transform.forward; var p = wm.transform.position;
    bool axisX = UnityEngine.Mathf.Abs(back.x) > UnityEngine.Mathf.Abs(back.z);
    float plane = axisX ? p.x + UnityEngine.Mathf.Sign(back.x) * cellSz * 0.5f : p.z + UnityEngine.Mathf.Sign(back.z) * cellSz * 0.5f;
    float along = axisX ? p.z : p.x;
    float floorY = UnityEngine.Mathf.Floor((p.y + cellSz * 0.1f) / cellSz) * cellSz;
    bool ownFloor = false;
    foreach (var wc in Cozy.Grid.WallCutaway.All)
        if (wc != null && wc.MatchesAdjacent(axisX, plane, along, floorY, cellSz)
            && (wc.CutShownNear(along, cellSz * 0.6f) || wc.HiddenAbove)
            && UnityEngine.Mathf.Abs((float)fYMin.GetValue(wc) - floorY) < cellSz * 0.5f) { ownFloor = true; break; }
    if (!ownFloor)
    {
        var owner = wm.GetComponent<Cozy.Grid.InteractiveObject>();
        bad.Append("настенный объект погашен чужой стеной: " + (owner != null && owner.Def != null ? owner.Def.id : wm.name) + " @ " + p.ToString("F1") + "; ");
    }
}
// 13. Фигура в инвентаре видна и из режима осмотра (P240: PlayerGhost гасил
//     рендереры игрока, копия Visual для куклы наследовала выключенные).
int dolls = 0;
var fModel = typeof(Tavern.UI.ItemPreview3D).GetField("_model", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
foreach (var pv in UnityEngine.Object.FindObjectsByType<Tavern.UI.ItemPreview3D>(UnityEngine.FindObjectsSortMode.None))
{
    if (pv.name != "ModelPreview3D" || fModel == null) continue;
    var model = fModel.GetValue(pv) as UnityEngine.Transform;
    if (model == null) continue;
    dolls++;
    int on = 0;
    foreach (var r in model.GetComponentsInChildren<UnityEngine.Renderer>()) if (r.enabled) on++;
    if (on == 0) bad.Append("фигура в инвентаре без включённых рендереров (призрак осмотра); ");
}
// 14. Ряд слота экипировки не ниже своей заявленной высоты (P241: стек с
//     childControlHeight=false глушил preferredHeight, плитки 130 в рядах 100).
int slotRows = 0;
foreach (var le in UnityEngine.Object.FindObjectsByType<UnityEngine.UI.LayoutElement>(UnityEngine.FindObjectsSortMode.None))
{
    if (!le.name.StartsWith("Slot_") || le.transform.parent == null || le.transform.parent.name != "Slots") continue;
    slotRows++;
    var rrt = (UnityEngine.RectTransform)le.transform;
    if (rrt.rect.height < le.preferredHeight - 0.5f)
        bad.Append("ряд слота ниже preferredHeight: " + le.name + " " + rrt.rect.height.ToString("F0") + "<" + le.preferredHeight.ToString("F0") + "; ");
}
// 15. Камера осмотра не заходит в СОБСТВЕННЫЙ корпус объекта (P242: шкаф-купе,
//     минимум зума меньше половины ширины, круг от сдвинутого под карточку
//     фокуса не защищал). Для каждого объекта: фокус со сдвигом под карточку,
//     минимум зума с 16 ракурсов и 4 тангажей, камера снаружи коробки.
int hosts = 0;
var mDistOf = typeof(Tavern.UI.HudUI).GetMethod("ExamineDistanceOf", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var pColumn = typeof(Tavern.UI.HudUI).GetProperty("ExamineCardColumn", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
float zoomMin = (float)typeof(Cozy.Character.CameraFollow).GetField("ExamineZoomMin", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).GetRawConstantValue();
if (cam != null && mDistOf != null && pColumn != null)
{
    float column = (float)pColumn.GetValue(null, null);
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null || io.Container != null) continue;
        var box = io.WorldBounds; box.Expand(-0.02f);
        if (box.size.x <= 0f || box.size.y <= 0f || box.size.z <= 0f) continue;
        hosts++;
        var center = io.WorldBounds.center;
        float baseDist = (float)mDistOf.Invoke(null, new object[] { io, center, 0f, 15f });
        var focus = Tavern.UI.ExamineFraming.CardShift(center, 0f, 15f, baseDist, cam.fieldOfView, cam.aspect, column);
        bool inside = false;
        foreach (float pitch in new float[] { -25f, 15f, 60f, 89f })
        foreach (float yaw in new float[] { 0f, 22.5f, 45f, 67.5f, 90f, 112.5f, 135f, 157.5f, 180f, 202.5f, 225f, 247.5f, 270f, 292.5f, 315f, 337.5f })
        {
            float want = UnityEngine.Mathf.Max(baseDist * zoomMin, Cozy.Character.CameraFollow.ExamineFloor(io, focus, yaw, pitch));
            float d = Cozy.Character.CameraFollow.ExamineOutside(io, focus, yaw, pitch, want);
            var pos = focus + UnityEngine.Quaternion.Euler(pitch, yaw, 0f) * new UnityEngine.Vector3(0f, 0f, -d);
            if (box.Contains(pos)) inside = true;
            if (d < baseDist * zoomMin - 0.01f) inside = true;
        }
        if (inside) bad.Append("камера осмотра в корпусе или ближе предельного зума: " + io.Def.id + "; ");
    }
}
// 16. Коллайдер не поднимает опору выше видимой поверхности (P250: у кровати
//     один бокс на весь объект имел верх по изголовью, и вещи, положенные на
//     постель, повисали на полметра выше одеяла). В центре следа берём самый
//     высокий СВОЙ нетриггерный коллайдер и самый высокий СВОЙ рендерер:
//     первый не должен торчать над вторым. Триггеры не в счёт — постановка их
//     игнорирует; допуск 10 см на кромки и скруглённые боксы.
int surfaces = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null || io.Container != null) continue;
    if (io.Def.mount == Cozy.Grid.ObjectMount.Ceiling) continue;
    var ownRends = new System.Collections.Generic.List<UnityEngine.Renderer>();
    foreach (var r in io.GetComponentsInChildren<UnityEngine.Renderer>())
        if (r.enabled && !r.name.StartsWith("Outline") && r.GetComponentInParent<Cozy.Grid.InteractiveObject>() == io)
            ownRends.Add(r);
    if (ownRends.Count == 0) continue;
    // Щупаем ЦЕНТР следа, а не сетку. Сетка 3x3 пробовалась 06.09 и дала две
    // ложные тревоги: у углового кухонного блока коллайдер столешницы честно
    // накрывает ВЫРЕЗ под раковину (видимого меша там нет, но класть туда и
    // правда некуда), у плиты в выборку попадали коллайдеры СТОЯЩЕЙ НА НЕЙ
    // посуды. Центр ловит тот случай, ради которого правило заведено (высокая
    // часть вроде изголовья поднимает опору на всей площади), и молчит там,
    // где всё честно.
    var mid = io.WorldBounds.center;
    float colTop = float.NegativeInfinity, rendTop = float.NegativeInfinity;
    foreach (var col in io.GetComponentsInChildren<UnityEngine.Collider>())
    {
        if (col.isTrigger) continue;
        // Только СВОИ коллайдеры: у плиты дети — сковорода и кастрюля, их
        // верх к её поверхности отношения не имеет.
        if (col.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io) continue;
        var cb = col.bounds;
        if (mid.x < cb.min.x || mid.x > cb.max.x || mid.z < cb.min.z || mid.z > cb.max.z) continue;
        if (cb.max.y > colTop) colTop = cb.max.y;
    }
    foreach (var r in ownRends)
    {
        var rb = r.bounds;
        if (mid.x < rb.min.x || mid.x > rb.max.x || mid.z < rb.min.z || mid.z > rb.max.z) continue;
        if (rb.max.y > rendTop) rendTop = rb.max.y;
    }
    if (float.IsNegativeInfinity(colTop) || float.IsNegativeInfinity(rendTop)) continue;
    surfaces++;
    if (colTop > rendTop + 0.10f)
        bad.Append("коллайдер выше видимой поверхности: " + io.Def.id + " (+"
            + (colTop - rendTop).ToString("0.00") + " м); ");
}

// 17. Свободно стоящий объект уровня не упирается в ОКРУЖЕНИЕ на своём месте:
//     стены, полы, метки в его коробке = правила постановки сломали то, что уже
//     стоит (06.09: шкаф-купе краснел у стены спальни, причина искалась вслепую).
//     Чужая мебель в коробке не в счёт: стулья задвигают под стол позже стола.
int posed = 0;
var gcT = gc != null ? gc.GetType() : null;
var BFp = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static;
var pwT = gcT != null ? gcT.GetNestedType("PoseWork", BFp) : null;
bool moving = gcT != null && (gcT.GetField("_movingObj", BFp).GetValue(gc) != null || (bool)gcT.GetField("_handMove", BFp).GetValue(gc));
if (pwT != null && !moving)
{
    var steps = new[] { "SnapToNeighbours", "SnapToWall", "SnapKitLine", "ResolvePoseHeight" };
    var mBoxP = gcT.GetMethod("LocalBox", BFp); var mObsP = gcT.GetMethod("Obstacle", BFp);
    float liftMax = (float)gcT.GetField("OverlapLift", BFp).GetValue(null); float skinP = (float)gcT.GetField("OverlapSkin", BFp).GetValue(null);
    var player = Cozy.Grid.PlayerRef.GameObject;
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null) continue;
        var d = io.Def;
        if (!d.FreeYaw || d.mount != Cozy.Grid.ObjectMount.Floor || d.hostPart || d.builtIn || d.walkOver || !string.IsNullOrEmpty(d.snapToId) || d.passThrough) continue;
        var wb = io.WorldBounds; wb.Expand(1f);
        if (player != null && wb.Contains(player.transform.position)) continue;
        var p0 = io.transform.position; var r0 = io.transform.rotation; float yaw0 = io.transform.eulerAngles.y;
        float fy = UnityEngine.Mathf.Floor((p0.y + cellSz * 0.1f) / cellSz) * cellSz;
        object w = System.Activator.CreateInstance(pwT);
        System.Action<string, object> S = (n, v) => pwT.GetField(n).SetValue(w, v);
        S("Def", d); S("Body", io.gameObject); S("Exclude", io.transform); S("FloorY", fy); S("Hit", new UnityEngine.Vector3(p0.x, fy, p0.z));
        S("Kit", !string.IsNullOrEmpty(d.kit)); S("Free", true); S("WallMount", false); S("X", p0.x); S("Z", p0.z); S("Yaw", yaw0); S("FreeWall", false);
        object[] args = new object[] { w };
        string env = "";
        try
        {
            foreach (var st in steps) gcT.GetMethod(st, BFp).Invoke(gc, args);
            w = args[0];
            var pos = new UnityEngine.Vector3((float)pwT.GetField("X").GetValue(w), (float)pwT.GetField("Y").GetValue(w), (float)pwT.GetField("Z").GetValue(w));
            object[] bx = new object[] { io.gameObject, null, null };
            if ((bool)mBoxP.Invoke(null, bx))
            {
                var c = (UnityEngine.Vector3)bx[1]; var half = (UnityEngine.Vector3)bx[2];
                var rot = UnityEngine.Quaternion.Euler(0f, yaw0, 0f);
                io.transform.SetPositionAndRotation(pos, rot);
                UnityEngine.Physics.SyncTransforms();
                float lift = UnityEngine.Mathf.Min(liftMax, half.y * 0.5f);
                var centre = io.transform.TransformPoint(c) + UnityEngine.Vector3.up * lift;
                var h = new UnityEngine.Vector3(UnityEngine.Mathf.Max(0.005f, half.x - skinP), UnityEngine.Mathf.Max(0.005f, half.y - lift), UnityEngine.Mathf.Max(0.005f, half.z - skinP));
                bool wallOk = d.mount == Cozy.Grid.ObjectMount.Wall || d.seatToWall || d.SticksToWall;
                foreach (var col in UnityEngine.Physics.OverlapBox(centre, h, rot, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
                {
                    if (col.transform.IsChildOf(io.transform) || col.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null) continue;
                    if (col.GetComponentInParent<Cozy.Grid.DoorPiece>() != null || col.GetComponentInParent<Cozy.Grid.WindowPiece>() != null) continue;
                    if ((bool)mObsP.Invoke(gc, new object[] { col, io.gameObject, io.transform, null, wallOk, c, half, false }))
                        env += col.name + " " + col.bounds.center.ToString("F1") + "/" + col.bounds.size.ToString("F2") + ",";
                }
            }
        }
        finally { io.transform.SetPositionAndRotation(p0, r0); UnityEngine.Physics.SyncTransforms(); }
        posed++;
        if (env.Length > 0) bad.Append("объект упёрся в окружение на своём месте: " + d.id + " @ " + p0.ToString("F1") + " [" + env + "]; ");
    }
}
// 18. Верх стены не ниже верха плиты или куба, который перекрывает её в плане:
// полноклеточная плита идёт ДО линии сетки, а стена стоит по центру линии, и
// стоит верху стены оказаться ниже — плита накрывает половину её толщины, и
// сверху стена читается вдвое тоньше (Илья 2026-09-06).
int wallTops = 0;
{
    var blocksAll = new System.Collections.Generic.List<Cozy.Grid.GridBlock>(Cozy.Grid.GridBlock.All);
    foreach (var wb0 in blocksAll)
    {
        if (wb0.role != Cozy.Grid.GridRole.Wall || wb0.railing || wb0.fence) continue;
        var rw0 = wb0.Rend; if (rw0 == null) continue;
        var bw0 = rw0.bounds; wallTops++;
        foreach (var sb0 in blocksAll)
        {
            if (sb0 == wb0 || sb0.role != Cozy.Grid.GridRole.Floor) continue;
            var rs0 = sb0.Rend; if (rs0 == null) continue;
            var bs0 = rs0.bounds;
            float up = bs0.max.y - bw0.max.y;
            if (up <= 0.0005f || up > 0.05f) continue;
            if (bs0.min.x > bw0.max.x - 0.01f || bs0.max.x < bw0.min.x + 0.01f) continue;
            if (bs0.min.z > bw0.max.z - 0.01f || bs0.max.z < bw0.min.z + 0.01f) continue;
            bad.Append("плита накрывает верх стены: стена " + bw0.center.ToString("F1")
                + " верх " + bw0.max.y.ToString("F3") + " ниже плиты " + bs0.max.y.ToString("F3") + "; ");
            break;
        }
    }
}
// 19. Ветер не рисуется в помещении: пока включён глобальный ветер, ни один
// видимый порыв не стоит в клетке, НАД КОТОРОЙ ЕСТЬ ПЕРЕКРЫТИЕ (Илья 2026-09-06:
// «если глобально, внутри зданий не должно быть», повторено 2026-09-08).
// Вопрос сменён 08.09 с «есть ли пол здания» на «есть ли крыша» (P273, P276):
// на первом этаже полом служит сама земля, плиты там нет, и старая проверка
// пропускала ветер в комнату — замер дал 4 видимых порыва под перекрытием из 9.
int gusts = 0;
if (Cozy.Grid.Weather.Wind)
{
    foreach (var rig in UnityEngine.Object.FindObjectsByType<Cozy.Grid.WindGusts>(UnityEngine.FindObjectsSortMode.None))
    {
        if (!rig.Global) continue;
        foreach (var gr in rig.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
        {
            if (!gr.enabled) continue;
            gusts++;
            // Спрашиваем ТОЙ ЖЕ функцией, что и гейт: своя проба в точке уже
            // дважды соврала, поймав плиту соседней клетки сквозь стену
            // (инвариант 88). Проверяется, что гейт применён, а не переписан.
            // ⚠️ Меряется ЛЕНТА, а не узел (P278): узел — начало пути, лента
            // сидит до path метров ниже по ветру, при сильном ветре до ~18 м.
            // До 09.09 правило смотрело на узел и было зелёным при ленте в комнате.
            var gmf = gr.GetComponent<UnityEngine.MeshFilter>();
            var gv = gmf != null && gmf.sharedMesh != null ? gmf.sharedMesh.vertices : null;
            if (gv == null || gv.Length < 2) continue;
            var ghead = gr.transform.TransformPoint(gv[0]);
            var gmid = gr.transform.TransformPoint(gv[gv.Length / 2]);
            var gtail = gr.transform.TransformPoint(gv[gv.Length - 1]);
            if (Cozy.Grid.WindGusts.Indoors(ghead) || Cozy.Grid.WindGusts.Indoors(gmid) || Cozy.Grid.WindGusts.Indoors(gtail))
                bad.Append("ветер в помещении: лента " + ghead.ToString("F1") + " → " + gtail.ToString("F1") + " (узел " + gr.transform.position.ToString("F1") + "); ");
            // 31. Лента лежит ПО ВЕТРУ: от первой вершины к последней — вдоль Weather.Dir
            // (P293: путь строился вдоль локальной X, а узел смотрит вдоль Z — ленты летели
            // поперёк ветра при любом угле). Доворот ±14° и петли пути дают 0.84…0.97.
            var galong = gtail - ghead; galong.y = 0f;
            if (galong.sqrMagnitude > 0.01f && UnityEngine.Vector3.Dot(galong.normalized, Cozy.Grid.Weather.Dir) < 0.7f)
                bad.Append("лента поперёк ветра: cos=" + UnityEngine.Vector3.Dot(galong.normalized, Cozy.Grid.Weather.Dir).ToString("F2") + " у узла " + gr.transform.position.ToString("F1") + "; ");
        }
    }
}

// 20. Метка спавна ставится всегда: пока в мире живёт маркер, постановка
// нового его ПЕРЕНОСИТ, а не краснеет (P263: гейт «второй не ставится» стал
// вечным запретом, когда метка начала переживать загрузку уровня).
int spawnGate = 0;
if (Cozy.Grid.SpawnPoint.Instance != null && Cozy.Grid.GridCursor.I != null)
{
    var markDef = Cozy.Grid.FurnitureCatalog.ById(Cozy.Grid.SpawnPoint.ObjectId);
    var gate = typeof(Cozy.Grid.GridCursor).GetMethod("FurniturePlaceBlocked",
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    if (markDef != null && gate != null)
    {
        var mp = Cozy.Grid.SpawnPoint.Instance.transform.position;
        spawnGate = 1;
        if ((bool)gate.Invoke(Cozy.Grid.GridCursor.I, new object[] { markDef, mp.x, mp.y, mp.z, null }))
            bad.Append("метку спавна некуда поставить: занято её же клеткой " + mp.ToString("F1") + "; ");
    }
}

// 21. Дождь: внутри дома капель нет, НАД домом идут (Илья 2026-09-07: «над
// зданием не идет дождь, а должен»), и петля падения бесшовна — второй период
// сетки точная копия первого со смещением на шаг («капли будто не долетают»).
int rainCells = 0;
if (Cozy.Grid.Weather.Rain)
{
    var rgd = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground) ?? Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Floor);
    float rcs = rgd != null ? rgd.CellSize : 3f;
    float rfloor = Cozy.View.ViewState.CurrentFloorY;
    var rorg = rgd != null ? rgd.Origin : UnityEngine.Vector3.zero;
    foreach (var rrig in UnityEngine.Object.FindObjectsByType<Cozy.Grid.RainDrops>(UnityEngine.FindObjectsSortMode.None))
    {
        foreach (UnityEngine.Transform rt in rrig.transform)
        {
            if (rt.name != "RainCell") continue;
            var rr = rt.GetComponent<UnityEngine.MeshRenderer>();
            if (rr == null || !rr.enabled) continue;
            rainCells++;
            var rp = rt.position;
            var rcell = rp - Cozy.Grid.RainDrops.Slide;
            var rmid = new UnityEngine.Vector3(rcell.x, rcell.y, rcell.z);
            if (Cozy.Grid.LightZones.ZoneAt(rmid) == Cozy.Grid.LightZones.Indoor)
                bad.Append("столб дождя стоит в клетке-доме: " + rmid.ToString("F1") + "; ");
            var rmf = rt.GetComponent<UnityEngine.MeshFilter>();
            if (rmf == null || rmf.sharedMesh == null) continue;
            var rv = rmf.sharedMesh.vertices;
            if (rv.Length < 8) continue;
            var rstep = rv[4] - rv[0];
            bool torn = false;
            for (int rk = 0; rk + 8 <= rv.Length && !torn; rk += 8)
                for (int rj = 0; rj < 4; rj++)
                    if ((rv[rk + 4 + rj] - rv[rk + rj] - rstep).magnitude > 0.001f) { torn = true; break; }
            if (torn) bad.Append("петля дождя рвётся: второй период не копия первого; ");
        }
    }
}

// 22. Своя кисть не заслоняет свой фонарь: вылет пальцев за источник по оси
// луча меньше ближней плоскости теней спота (P267, инвариант 90). Снипет
// замера жил в tavern-hands/HANDS.md, автопробы не было.
int handLamp = 0;
{
    var frig = UnityEngine.Object.FindFirstObjectByType<Cozy.Character.FlashlightRig>();
    var fanim = frig != null ? frig.GetComponentInChildren<UnityEngine.Animator>() : null;
    var flamp = frig != null ? frig.transform.Find("Flashlight") : null;
    var flight = flamp != null ? flamp.GetComponentInChildren<UnityEngine.Light>(true) : null;
    if (fanim != null && fanim.isHuman && flight != null)
    {
        var fhand = fanim.GetBoneTransform(UnityEngine.HumanBodyBones.RightHand);
        var ffore = fanim.GetBoneTransform(UnityEngine.HumanBodyBones.RightLowerArm);
        if (fhand != null && ffore != null)
        {
            var faxis = (fhand.position - ffore.position).normalized;
            float ftip = 0f;
            var fbones = new UnityEngine.HumanBodyBones[] {
                UnityEngine.HumanBodyBones.RightIndexDistal,
                UnityEngine.HumanBodyBones.RightMiddleDistal,
                UnityEngine.HumanBodyBones.RightRingDistal,
                UnityEngine.HumanBodyBones.RightLittleDistal };
            foreach (var fb in fbones)
            {
                var ft = fanim.GetBoneTransform(fb);
                if (ft != null) ftip = UnityEngine.Mathf.Max(ftip, UnityEngine.Vector3.Dot(ft.position - fhand.position, faxis));
            }
            float fat = 0.06f + 0.08f;
            handLamp = 1;
            if (ftip - fat >= flight.shadowNearPlane)
                bad.Append("кисть заслоняет свой фонарь: вылет " + (ftip - fat).ToString("F3")
                    + " м при ближней плоскости " + flight.shadowNearPlane.ToString("F2") + "; ");
        }
    }
}

// 23. Молнии под крышей нет: гейт вспышки спрашивает ТОЙ ЖЕ функцией, что
// ветер и деревья (WindGusts.Indoors по игроку, P276), и вспышка начинается с
// пика. Проверка синхронная: Strike + ApplyLight, свет сравнивается с прежним,
// потом вспышка снимается через _flashLeft и свет возвращается.
int lightning = 0;
// ⚠️ Молния бьётся ТОЛЬКО с флагом --strike (Илья 10.09: «почему иногда бьёт
// молния? я не вызываю и не кликал — надо убрать»; P284): в общей play-сессии
// удар слышит и видит Илья. Без флага правило пропускается, «молния=0».
if (STRIKE_ALLOWED)
{
    var lclock = Tavern.Core.GameClock.I;
    var lsunF = typeof(Tavern.Core.GameClock).GetField("_sun",
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    var lleftF = typeof(Tavern.Core.GameClock).GetField("_flashLeft",
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    var lsun = lclock != null && lsunF != null ? lsunF.GetValue(lclock) as UnityEngine.Light : null;
    if (lclock != null && lsun != null && lleftF != null)
    {
        lightning = 1;
        bool roofed = Cozy.Grid.WindGusts.Indoors(Cozy.View.ViewState.PlayerPos + UnityEngine.Vector3.up * 0.1f);
        float before = lsun.intensity;
        var ambBefore = UnityEngine.RenderSettings.ambientLight;
        lclock.Strike();
        lclock.ApplyLight();
        float peak = lclock.Flash;
        float lit = lsun.intensity;
        var ambLit = UnityEngine.RenderSettings.ambientLight;
        lleftF.SetValue(lclock, 0f);
        lclock.ApplyLight();
        float after = lsun.intensity;
        var ambAfter = UnityEngine.RenderSettings.ambientLight;
        System.Func<UnityEngine.Color, UnityEngine.Color, float> gap = (a, b) =>
            UnityEngine.Mathf.Abs(a.r - b.r) + UnityEngine.Mathf.Abs(a.g - b.g) + UnityEngine.Mathf.Abs(a.b - b.b);
        // Направленный свет бьёт с пика ВСЕГДА — под крышей он входит через окна
        // (Илья 09.09: «чтобы в окнах было видно грозу»); ambient и небо — только снаружи.
        if (peak < 0.999f || lit - before < 0.5f)
            bad.Append("молния не бьёт с пика: flash " + peak.ToString("F2") + ", свет " + before.ToString("F2") + " → " + lit.ToString("F2") + "; ");
        if (roofed && gap(ambLit, ambBefore) > 0.001f)
            bad.Append("молния под крышей засветила ambient: " + ambBefore.ToString("F3") + " → " + ambLit.ToString("F3") + "; ");
        if (!roofed && gap(ambLit, ambBefore) < 0.05f)
            bad.Append("молния снаружи не засветила ambient: " + ambBefore.ToString("F3") + " → " + ambLit.ToString("F3") + "; ");
        if (UnityEngine.Mathf.Abs(after - before) > 0.001f || gap(ambAfter, ambBefore) > 0.001f)
            bad.Append("свет после молнии не вернулся: " + before.ToString("F2") + " → " + after.ToString("F2") + ", ambient " + ambBefore.ToString("F3") + " → " + ambAfter.ToString("F3") + "; ");
    }
}

// 24. Трава кланяется на ветру, но корни остаются в земле: у стебля профиль
// изгиба (y/h)^2 не двигает вершины у основания. Жёсткий поворот пучка целиком
// (первая попытка 09.09) хоронил наветренную половину блейдов в земле на 14 см
// — отсюда проверка по САМОЙ НИЖНЕЙ вершине, а не по наклону. Ветер включается
// самой пробой и возвращается, чтобы правило не зависело от тумблера.
int stemsBent = 0;
{
    var sF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
    var sT = typeof(Cozy.Grid.TreeWind);
    var sLate = sT.GetMethod("LateUpdate", sF);
    var sStem = sT.GetField("_stem", sF);
    var sParts = sT.GetField("_parts", sF);
    var sIn = sT.GetField("_indoors", sF);
    if (sLate != null && sStem != null && sParts != null)
    {
        bool wasWind = Cozy.Grid.Weather.Wind;
        var wasForce = Cozy.Grid.Weather.Force;
        Cozy.Grid.Weather.Wind = true;
        Cozy.Grid.Weather.Force = Cozy.Grid.WindForce.Strong;
        var noArgs = new object[0];
        float worst = 0f;
        string worstAt = "";
        foreach (var rig in UnityEngine.Object.FindObjectsByType<Cozy.Grid.TreeWind>(UnityEngine.FindObjectsSortMode.None))
        {
            if (!(bool)sStem.GetValue(rig) || (bool)sIn.GetValue(rig)) continue;
            sLate.Invoke(rig, noArgs);
            var plist = sParts.GetValue(rig) as System.Collections.IList;
            if (plist == null || plist.Count == 0) continue;
            var pt = plist[0];
            var ptT = pt.GetType();
            var work = (UnityEngine.Vector3[])ptT.GetField("work").GetValue(pt);
            var node = (UnityEngine.Transform)ptT.GetField("node").GetValue(pt);
            float ground = rig.transform.position.y;
            float sunk = 0f;
            for (int i = 0; i < work.Length; i++)
                sunk = UnityEngine.Mathf.Max(sunk, ground - node.TransformPoint(work[i]).y);
            stemsBent++;
            if (sunk > worst) { worst = sunk; worstAt = rig.transform.position.ToString("F1"); }
        }
        if (worst > 0.01f)
            bad.Append("трава ушла под землю на " + worst.ToString("F3") + " м у " + worstAt + "; ");
        Cozy.Grid.Weather.Wind = wasWind;
        Cozy.Grid.Weather.Force = wasForce;
        foreach (var rig in UnityEngine.Object.FindObjectsByType<Cozy.Grid.TreeWind>(UnityEngine.FindObjectsSortMode.None))
            if ((bool)sStem.GetValue(rig)) sLate.Invoke(rig, noArgs);
    }
}

// 27. Статусы среды согласованы с источниками и ручками (EFFECTS.md): озноб = WetChill при мокром,
// иначе 0; в огне — горит; значки ряда идут через PlayerEffects.Sources и совпадают с флагами.
// Статус «не видно» и обзор × FogSight сняты 10.09 (туман на игрока не действует).
int exposure = 0;
{
    var xT = System.Type.GetType("Cozy.Effects.PlayerExposure, Cozy.Effects");
    var xPlayer = Cozy.Grid.PlayerRef.GameObject;
    if (xT != null && xPlayer != null)
    {
        exposure = 1;
        System.Func<string, bool> flag = n => (bool)xT.GetProperty(n).GetValue(null);
        bool wet = flag("Wet"), burning = flag("Burning"), inFire = flag("InFire");
        if (xT.GetProperty("Blind") != null) bad.Append("статус «не видно» вернулся в PlayerExposure, а туман на игрока снят 10.09; ");
        float wantChill = wet ? (float)xT.GetField("WetChill").GetValue(null) : 0f;
        if (UnityEngine.Mathf.Abs(Cozy.Character.BodyTemperature.Chill - wantChill) > 0.001f) bad.Append("озноб " + Cozy.Character.BodyTemperature.Chill + " при wet=" + wet + "; ");
        if (inFire && !burning) bad.Append("в огне, но не горит; ");
        if (Cozy.Character.PlayerEffects.Sources.Count < 1) bad.Append("ряд значков без поставщика статусов среды; ");
        var xStats = xPlayer.GetComponent<Cozy.Character.CharacterStats>();
        var xList = new System.Collections.Generic.List<Cozy.Character.PlayerEffect>();
        Cozy.Character.PlayerEffects.Collect(xStats, xList);
        bool hasBurn = false, hasBlind = false, hasWet = false;
        foreach (var xe in xList) { if (xe.Title == "Ожог") hasBurn = true; if (xe.Title == "Ничего не видно") hasBlind = true; if (xe.Title == "Мокрый") hasWet = true; }
        if (hasBurn != burning || hasBlind || hasWet != wet) bad.Append("значки статусов расходятся с флагами: ожог " + hasBurn + "/" + burning + ", не видно " + hasBlind + " (снят 10.09), мокрый " + hasWet + "/" + wet + "; ");
    }
}

// 28. Просвет кроны (VIEW.md §10a): окно закрыто ровно тогда, когда игрок в тумане; у каждого
// дерева с crownWindow вся листва на Tavern/CrownCut, а материалы ствола — нет (кора не режется);
// у каждой кроны копия-кайма (10.09: тот же меш, _CROWN_BAND, БЕЗ записи глубины, очередь BandQueue
// до дождя и тумана, без теней, кора невидима), включённая кайма ⇒ окно открыто, открытое окно ⇒
// кайма шире 1 px и маска каймы _CrownBandTex рисуется (_CrownBandOn).
int crowns = 0;
{
    var cPlayer = Cozy.Grid.PlayerRef.GameObject;
    if (cPlayer != null)
    {
        bool fogHere = Cozy.Grid.FogView.Covers(cPlayer.transform.position);
        float cOn = UnityEngine.Shader.GetGlobalFloat("_CrownWindowOn");
        if (cOn > 0.5f && UnityEngine.Shader.GetGlobalFloat("_CrownFeatherPx") < 1f) bad.Append("окно кроны открыто без каймы (_CrownFeatherPx < 1); ");
        if (cOn > 0.5f && UnityEngine.Shader.GetGlobalFloat("_CrownBandOn") < 0.5f) bad.Append("окно кроны открыто, а маска каймы (_CrownBandOn) не рисуется; ");
        if (Cozy.Grid.CrownWindow.BandQueue >= 3000) bad.Append("кайма кроны в очереди " + Cozy.Grid.CrownWindow.BandQueue + " — после дождя и тумана, окружность на краю тумана (P298); ");
        if (Cozy.Grid.CrownWindow.Enabled && (cOn > 0.5f) == fogHere) bad.Append("окно кроны " + (cOn > 0.5f ? "открыто" : "закрыто") + " при тумане под игроком " + fogHere + "; ");
        foreach (var cio in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        {
            if (cio.Def == null || !cio.Def.crownWindow) continue;
            crowns++;
            UnityEngine.Transform crown = null, trunk = null;
            foreach (var tr in cio.GetComponentsInChildren<UnityEngine.Transform>(true)) { if (tr.name == cio.Def.crownNode) crown = tr; if (tr.name == cio.Def.heightNode) trunk = tr; }
            if (crown == null) continue;
            var bark = new System.Collections.Generic.HashSet<UnityEngine.Material>();
            if (trunk != null) foreach (var cr in trunk.GetComponentsInChildren<UnityEngine.MeshRenderer>(true)) foreach (var cm in cr.sharedMaterials) if (cm != null) bark.Add(cm);
            foreach (var cm in bark) if (cm.shader.name == "Tavern/CrownCut") { bad.Append("кора на CrownCut: " + cio.name + "; "); break; }
            int leaf = 0, cut = 0, bandsHere = 0;
            foreach (var cr in crown.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
            {
                if (cr.name == Cozy.Grid.SeeThroughView.GhostName)
                {
                    bandsHere++;
                    var pf = cr.transform.parent.GetComponent<UnityEngine.MeshFilter>(); var bf = cr.GetComponent<UnityEngine.MeshFilter>();
                    if (pf == null || bf == null || bf.sharedMesh != pf.sharedMesh) bad.Append("кайма кроны не на меше кроны: " + cio.name + "; ");
                    if (cr.enabled && cOn < 0.5f) bad.Append("кайма кроны включена при закрытом окне: " + cio.name + "; ");
                    if (cr.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off) bad.Append("кайма кроны бросает тень: " + cio.name + "; ");
                    foreach (var bm in cr.sharedMaterials)
                    {
                        if (bm == null) { bad.Append("пустой слот каймы: " + cio.name + "; "); continue; }
                        bool leafBand = bm.shader.name == "Tavern/CrownCut";
                        if (leafBand && (!bm.IsKeywordEnabled(Cozy.Grid.CrownWindow.BandKeyword) || bm.GetInt("_ZWrite") != 0)) bad.Append("кайма без _CROWN_BAND или пишет глубину (туман за листвой пропадёт): " + cio.name + "; ");
                        if (!leafBand && bm.color.a > 0.001f) bad.Append("кора в кайме видима: " + cio.name + "; ");
                        if (bm.renderQueue != Cozy.Grid.CrownWindow.BandQueue) bad.Append("кайма не в очереди " + Cozy.Grid.CrownWindow.BandQueue + ": " + cio.name + "; ");
                    }
                    continue;
                }
                foreach (var cm in cr.sharedMaterials) { if (cm == null || bark.Contains(cm)) continue; leaf++; if (cm.shader.name == "Tavern/CrownCut") cut++; }
            }
            if (leaf > 0 && cut != leaf) bad.Append("листва без CrownCut: " + cio.name + " " + cut + "/" + leaf + "; ");
            if (leaf > 0 && bandsHere == 0) bad.Append("крона без каймы: " + cio.name + "; ");
        }
    }
}

// 30. Площадка слота — опора на ЛЮБОЙ высоте (P288): у тумбы-скамьи дно короба на
// полу, площадка Slot_FloorL на 3 см — ниже «мёртвой зоны пола» FloorSkin. Через
// открытую дверцу точка курсора и SurfaceTopAt ложатся на площадку; за закрытой — нет (P067).
int floorSlots = 0;
{
    var fsDef = Cozy.Grid.FurnitureCatalog.ById("hallway_rack");
    var fsGc = Cozy.Grid.GridCursor.I;
    if (fsDef != null && fsGc != null)
    {
        var fsRack = fsGc.SpawnWorldObject(fsDef, new UnityEngine.Vector3(-70f, 0f, -90f), 0f);
        if (fsRack != null)
        {
            try
            {
                UnityEngine.Physics.SyncTransforms();
                var fsF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
                var fsCursor = typeof(Cozy.Grid.GridCursor).GetMethod("SurfaceCursorPoint", fsF);
                var fsTop = typeof(Cozy.Grid.GridCursor).GetMethod("SurfaceTopAt", fsF);
                Cozy.Grid.ContainerSlot fsSlot = null; UnityEngine.Transform fsDoor = null;
                foreach (var fsS in fsRack.GetComponentsInChildren<Cozy.Grid.ContainerSlot>(true)) if (fsS.name == "Slot_FloorL") fsSlot = fsS;
                foreach (var fsT in fsRack.GetComponentsInChildren<UnityEngine.Transform>(true)) if (fsT.name == "DoorL") fsDoor = fsT;
                Cozy.Grid.AccessFeature fsGate = null;
                foreach (var fsFeat in fsRack.Features) { var fsA = fsFeat as Cozy.Grid.AccessFeature; if (fsA != null && fsA.Title == "Дверца левая") fsGate = fsA; }
                if (fsSlot == null || fsDoor == null || fsGate == null) bad.Append("у вешалки нет Slot_FloorL, DoorL или фичи «Дверца левая»; ");
                else
                {
                    var fsPad = fsSlot.GetComponent<UnityEngine.Collider>().bounds;
                    var fsDoorCol = fsDoor.GetComponent<UnityEngine.Collider>();
                    var fsFront = fsDoor.position - fsRack.transform.position; fsFront.y = 0f; fsFront.Normalize();
                    var fsTarget = fsPad.center + fsFront * 0.10f; fsTarget.y = fsPad.max.y;
                    var fsOrigin = fsTarget + fsFront * 1.6f + UnityEngine.Vector3.up * 1.9f;
                    var fsRay = new UnityEngine.Ray(fsOrigin, (fsTarget - fsOrigin).normalized);
                    if (fsPad.max.y > 0.05f) bad.Append("площадка дна вешалки выше мёртвой зоны пола (" + fsPad.max.y.ToString("F3") + "), правило 30 не проверяется; ");
                    foreach (var fsOpen in new[] { true, false })
                    {
                        fsGate.SetOpen(fsOpen);
                        fsDoorCol.enabled = !fsOpen;
                        UnityEngine.Physics.SyncTransforms();
                        var fsArgs = new object[] { fsRay, 0f, null, null };
                        bool fsFound = (bool)fsCursor.Invoke(fsGc, fsArgs);
                        var fsPt = (UnityEngine.Vector3)fsArgs[3];
                        float fsTopY = fsFound ? (float)fsTop.Invoke(fsGc, new object[] { fsPt.x, fsPt.z, 0f, null, fsPt.y }) : -1f;
                        bool fsOnPad = fsFound && UnityEngine.Mathf.Abs(fsPt.y - fsPad.max.y) < 0.01f && UnityEngine.Mathf.Abs(fsTopY - fsPad.max.y) < 0.01f;
                        if (fsOpen && !fsOnPad) bad.Append("дверца открыта, а дно тумбы не опора: курсор " + (fsFound ? fsPt.y.ToString("F3") : "нет") + ", верх " + fsTopY.ToString("F3") + "; ");
                        if (!fsOpen && fsOnPad) bad.Append("дверца закрыта, а курсор ложится на дно тумбы; ");
                        floorSlots++;
                    }
                    fsGate.SetOpen(false);
                    fsDoorCol.enabled = true;
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(fsRack.gameObject); }
        }
    }
}

return "объектов=" + checkedObjects + " на своих местах=" + posed + " поверхностей=" + surfaces + " хостов осмотра=" + hosts + " рядов слотов=" + slotRows + " кукол=" + dolls + " у стен=" + nearWall + " в закрытых секциях=" + closed + " подвесов=" + mounts + " вложенных=" + nested + " с преградой у фокуса=" + touching + " на открытых поверхностях=" + onSurface + " порожков=" + thresholds + " скрытых=" + hiddenObjs + " настенных=" + wallMounted + " стен=" + wallTops + " порывов ветра=" + gusts + " клеток дождя=" + rainCells + " фонарь в руке=" + handLamp + " гейт спавна=" + spawnGate + " молния=" + lightning + " травы на ветру=" + stemsBent + " статусы=" + exposure + " крон=" + crowns + " низких слотов=" + floorSlots + " :: "
     + (bad.Length == 0 ? "инварианты держатся" : bad.ToString());
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE.replace('STRIKE_ALLOWED', 'true' if '--strike' in sys.argv else 'false')})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    data = json.loads(line)
    print(data.get("data", {}).get("result") or json.dumps(data, ensure_ascii=False)[:400])


if __name__ == '__main__':
    main()
