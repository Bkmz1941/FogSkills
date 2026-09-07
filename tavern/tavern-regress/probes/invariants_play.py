"""Проверка ЖИВЫХ инвариантов в play: то, что тестами EditMode не поймать.

Каждая проверка — уже пойманный когда-то баг. Список правил: INVARIANTS.md (tavern-regress).
Запускать после любой правки взаимодействия, наведения или контейнеров.
"""
import json, subprocess

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
// видимый порыв не стоит в клетке, где есть пол здания (Илья 2026-09-06:
// «если глобально, внутри зданий не должно быть»).
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
            var gp = gr.transform.position;
            var gg = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground) ?? Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Floor);
            float gcs = gg != null ? gg.CellSize : 3f;
            var go2 = gg != null ? gg.Origin : UnityEngine.Vector3.zero;
            var gcell = Cozy.Grid.GridSnap.Cell(gp, go2, gcs);
            var gmid = new UnityEngine.Vector3(go2.x + gcell.x * gcs, gp.y, go2.z + gcell.y * gcs);
            if (Cozy.Grid.LightZones.ZoneAt(gmid) == Cozy.Grid.LightZones.Indoor)
                bad.Append("ветер в помещении: " + gp.ToString("F1") + "; ");
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

return "объектов=" + checkedObjects + " на своих местах=" + posed + " поверхностей=" + surfaces + " хостов осмотра=" + hosts + " рядов слотов=" + slotRows + " кукол=" + dolls + " у стен=" + nearWall + " в закрытых секциях=" + closed + " подвесов=" + mounts + " вложенных=" + nested + " с преградой у фокуса=" + touching + " на открытых поверхностях=" + onSurface + " порожков=" + thresholds + " скрытых=" + hiddenObjs + " настенных=" + wallMounted + " стен=" + wallTops + " порывов ветра=" + gusts + " гейт спавна=" + spawnGate + " :: "
     + (bad.Length == 0 ? "инварианты держатся" : bad.ToString());
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    data = json.loads(line)
    print(data.get("data", {}).get("result") or json.dumps(data, ensure_ascii=False)[:400])


if __name__ == '__main__':
    main()
