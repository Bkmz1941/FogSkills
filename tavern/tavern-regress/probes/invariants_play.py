"""Проверка ЖИВЫХ инвариантов в play: то, что тестами EditMode не поймать.

Каждая проверка — уже пойманный когда-то баг. Список правил: INVARIANTS.md (tavern-regress).
Запускать после любой правки взаимодействия, наведения или контейнеров.

⭐ У ЗЕЛЁНОГО ДВА СМЫСЛА: «проверил и сошлось» и «не проверял ничего». Поэтому
проба отвечает тремя частями: счётчики :: жалобы :: что НЕ проверялось. Правило,
чей счётчик упал в ноль, на этом уровне не видело ни одного подходящего объекта —
зелёный по нему не значит ничего (13.09 на forest100 так молчали 16 правил из 42).
А пропавшая цель рефлексии даёт ЖАЛОБУ «ЗАЩИТА МЕРТВА, правило N не выполняется»:
треть правил спрятана за `if (… != null)`, и раньше такое правило умирало беззвучно
(P381 — правило 24 красило зелёным сутки после переезда ветра на GPU).

⚠️ А НЕНУЛЕВОЙ счётчик вердиктом не считать. Счётчики — это
«сколько чего осмотрено», и половина из них считается ОТ ПОЛОЖЕНИЯ ИГРОКА:
«скрытых» (этажный гейт и радиус рендера), «с преградой у фокуса», «в кадре».
Сравнивать их с прошлым прогоном можно, только если игрок стоит там же —
11.09 две сессии чуть не начали чинить несуществующий регресс, потому что
замер сделали сразу после входа в play, когда игрок стоял на втором этаже и
гейт прятал нижний (316 → 318 объектов, 10 → 69 скрытых). Расхождение в
счётчиках — повод переспросить соседа, а не чинить код. И прогон, попавший на
чужой stop, врёт целиком: `level_roundtrip` отвечает «ИНВЕНТАРЬ ПОТЕРЯН» на
пустой редактор.
"""
import json, re, subprocess, sys

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE_A = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bad = new System.Text.StringBuilder();
// ⭐⭐ СТОРОЖА САМОЙ ПРОБЫ. Треть правил спрятана за `if (… != null)`: пропала
// цель рефлексии — правило МОЛЧА не выполняется, и проба отвечает зелёным,
// проверив ноль. 13.09 так умерло правило 24 (ветер уехал на GPU, полей
// `_stem`/`_parts` не стало), и ни один ночной прогон этого не заметил.
// Поэтому пропавший член кода — ЖАЛОБА, наравне со сломанным инвариантом.
// Сюда вносится ТОЛЬКО то, что спрятано за тихим guard-ом: члены, на которых
// правило упало бы с NullReference, кричат сами.
var BFq = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var BFqs = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var BFqa = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static;
var BFqp = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
var qGc = typeof(Cozy.Grid.GridCursor); var qHud = typeof(Tavern.UI.HudUI); var qCam = typeof(Cozy.Character.CameraFollow);
System.Action<string, bool, string> Need = (rule, ok, what) => { if (!ok) bad.Append("ЗАЩИТА МЕРТВА, правило " + rule + " не выполняется: " + what + "; "); };
Need("1", typeof(Cozy.Grid.Interactor).GetMethod("SkipHit", BFqs) != null, "нет Interactor.SkipHit");
Need("1", qGc.GetMethod("PieceOnRay", BFq) != null, "нет GridCursor.PieceOnRay");
Need("5", qGc.GetMethod("MountTaken", BFq) != null, "нет GridCursor.MountTaken");
Need("6", qCam.GetMethod("ClearDistance", BFqs) != null, "нет CameraFollow.ClearDistance");
Need("6", typeof(Cozy.Grid.Interactor).GetProperty("ExamineHost") != null, "нет Interactor.ExamineHost");
Need("7", qCam.GetMethod("HostFloor", BFqs) != null, "нет CameraFollow.HostFloor");
Need("7", qCam.GetField("ExamineCamRadius", BFqs) != null, "нет CameraFollow.ExamineCamRadius");
Need("8", qGc.GetMethod("SurfaceSupported", BFq) != null, "нет GridCursor.SurfaceSupported");
Need("10", qGc.GetMethod("WallDeepInside", BFqs) != null, "нет GridCursor.WallDeepInside");
Need("10", qGc.GetMethod("LocalBox", BFqs) != null, "нет GridCursor.LocalBox");
Need("12", typeof(Cozy.Grid.WallCutaway).GetField("_yMin", BFq) != null, "нет WallCutaway._yMin");
Need("13", typeof(Tavern.UI.ItemPreview3D).GetField("_model", BFq) != null, "нет ItemPreview3D._model");
Need("15", qHud.GetMethod("ExamineDistanceOf", BFqs) != null, "нет HudUI.ExamineDistanceOf");
Need("15", qHud.GetProperty("ExamineCardColumn", BFqs) != null, "нет HudUI.ExamineCardColumn");
Need("15", qCam.GetField("ExamineZoomMin", BFqs) != null, "нет CameraFollow.ExamineZoomMin");
Need("17", qGc.GetNestedType("PoseWork", BFqa) != null, "нет вложенного типа GridCursor.PoseWork");
Need("17", qGc.GetField("_movingObj", BFqa) != null, "нет GridCursor._movingObj");
Need("17", qGc.GetField("_handMove", BFqa) != null, "нет GridCursor._handMove");
Need("20", Cozy.Grid.FurnitureCatalog.ById(Cozy.Grid.SpawnPoint.ObjectId) != null, "нет дефа метки спавна");
Need("20", qGc.GetMethod("FurniturePlaceBlocked", BFq) != null, "нет GridCursor.FurniturePlaceBlocked");
Need("24", typeof(Cozy.Grid.TreeWind).GetMethod("TickAll", BFqp) != null, "нет TreeWind.TickAll");
Need("24", typeof(Cozy.Grid.TreeWind).GetField("_kind", BFq) != null, "нет TreeWind._kind");
Need("27", System.Type.GetType("Cozy.Effects.PlayerExposure, Cozy.Effects") != null, "нет типа PlayerExposure");
Need("27", System.Type.GetType("Cozy.Effects.PlayerExposure, Cozy.Effects")?.GetField("FogScreen") != null, "нет поля FogScreen (покрытие экрана)");
Need("29", qCam.GetMethod("ShiftOutsideSolids", BFqp) != null, "нет CameraFollow.ShiftOutsideSolids");
Need("29", qCam.GetMethod("Transparent", BFqs) != null, "нет CameraFollow.Transparent");
Need("30", Cozy.Grid.FurnitureCatalog.ById("hallway_rack") != null, "нет дефа hallway_rack");
Need("33", qHud.GetField("_activeQuick", BFq) != null, "нет HudUI._activeQuick");
Need("33", qHud.GetMethod("PocketPlacedAt", BFq) != null, "нет HudUI.PocketPlacedAt");
Need("21b", typeof(Cozy.Grid.RainDrops).GetMethod("OpenSky", BFqs) != null, "нет RainDrops.OpenSky");
Need("21b", typeof(Cozy.Grid.RainDrops).GetField("_rends", BFq) != null, "нет RainDrops._rends");
Need("39", typeof(Cozy.Grid.GameSfx).GetMethod("MuffleAt", BFqs | System.Reflection.BindingFlags.Public) != null, "нет GameSfx.MuffleAt");
var cam = UnityEngine.Camera.main;
var t = typeof(Cozy.Grid.Interactor);
var skip = t.GetMethod("SkipHit", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var pieceOnRay = qGc.GetMethod("PieceOnRay", BFq);
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
            // Стройка разбирает луч СВОИМ путём (GridCursor.PieceOnRay → NearestVisiblePiece):
            // 25.09 сквозь закрытую дверцу холодильника выделялись яйца на полке (P569).
            if (pieceOnRay != null && Cozy.Grid.GridCursor.I != null
                && ReferenceEquals(pieceOnRay.Invoke(Cozy.Grid.GridCursor.I, new object[] { ray, null }), io))
                bad.Append("стройка выбирает сквозь закрытую секцию: " + io.Def.id + "; ");
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
            if (r != null && (!r.enabled || r.shadowCastingMode == UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly)) continue;
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
        // Вещь В ВЫКЛАДКЕ (горка в мойке, стопки в шкафу) опирается на своего
        // хозяина, а не на мир: у шкафа один коллайдер-коробка на весь корпус,
        // луч опоры стартует внутри него и дна не видит — каждая вещь на дне
        // читалась как «висит над пустотой» (18.09).
        if (Cozy.Grid.Piles.HolderOf(io) != null) continue;
        // Вещь в ВЫКЛАДКЕ контейнера (фрукты в миске, поленья ярусом в камине)
        // живёт В ИЕРАРХИИ хозяина и опирается на него, а не на мир: луч опоры
        // стартует внутри коробки хозяина и дна не видит — каждая такая вещь
        // читалась как «висит над пустотой» (18.09, та же причина, что у горки).
        var under = io.transform.parent != null ? io.transform.parent.GetComponentInParent<Cozy.Grid.InteractiveObject>() : null;
        if (under != null && under != io) continue;
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
    // Вырез под встроенную мойку: центр тумбы — дыра в столешнице, её закрывает
    // посаженный на тумбу предмет (28.09, night_build_c: home_sink_cabinet +1.03).
    bool filled = false;
    foreach (var guest in Cozy.Grid.InteractiveObject.All)
    {
        if (guest == null || guest == io || !Cozy.Grid.InteractiveObject.Same(guest.HostObject, io)) continue;
        var gb2 = guest.WorldBounds;
        if (mid.x >= gb2.min.x && mid.x <= gb2.max.x && mid.z >= gb2.min.z && mid.z <= gb2.max.z && gb2.max.y >= colTop - 0.10f) { filled = true; break; }
    }
    if (filled) continue;
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
                    var obsArgs = new object[mObsP.GetParameters().Length];
                    obsArgs[0] = col; obsArgs[1] = io.gameObject; obsArgs[2] = io.transform; obsArgs[3] = null;
                    obsArgs[4] = wallOk; obsArgs[5] = c; obsArgs[6] = half;
                    for (int oi = 7; oi < obsArgs.Length; oi++) obsArgs[oi] = false;
                    if ((bool)mObsP.Invoke(gc, obsArgs))
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
        float cs18 = UnityEngine.Mathf.Max(1f, Cozy.View.ViewState.CellSize);
        if (UnityEngine.Mathf.Min(bw0.size.x, bw0.size.z) > cs18 * 0.5f) continue;
        // 18b (24.09, P562): стена, у которой плита есть с ОБЕИХ сторон, целиком
        // под перекрытием — её верх обязан быть НИЖЕ плиты, иначе на полу и на
        // крыше читается план стен светлыми полосами.
        float edge0 = UnityEngine.Mathf.Round(bw0.max.y / cs18) * cs18;
        UnityEngine.Vector3 across0 = (bw0.size.z < bw0.size.x ? UnityEngine.Vector3.forward : UnityEngine.Vector3.right) * (cs18 * 0.5f);
        UnityEngine.Vector3 pa0 = bw0.center + across0, pb0 = bw0.center - across0;
        bool buried0 = Cozy.Grid.BuildQuery.HasFloorAt(pa0.x, pa0.z, edge0 + 0.1f, cs18)
            && Cozy.Grid.BuildQuery.HasFloorAt(pb0.x, pb0.z, edge0 + 0.1f, cs18);
        foreach (var sb0 in blocksAll)
        {
            if (sb0 == wb0 || sb0.role != Cozy.Grid.GridRole.Floor) continue;
            var rs0 = sb0.Rend; if (rs0 == null) continue;
            var bs0 = rs0.bounds;
            float up = bs0.max.y - bw0.max.y;
            if (UnityEngine.Mathf.Abs(up) > 0.05f) continue;
            if (bs0.min.x > bw0.max.x - 0.01f || bs0.max.x < bw0.min.x + 0.01f) continue;
            if (bs0.min.z > bw0.max.z - 0.01f || bs0.max.z < bw0.min.z + 0.01f) continue;
            if (buried0 && up < 0.0005f)
            {
                bad.Append("стена торчит сквозь плиту: стена " + bw0.center.ToString("F1")
                    + " верх " + bw0.max.y.ToString("F3") + " выше плиты " + bs0.max.y.ToString("F3") + "; ");
                break;
            }
            if (!buried0 && up > 0.0005f)
            {
                bad.Append("плита накрывает верх стены: стена " + bw0.center.ToString("F1")
                    + " верх " + bw0.max.y.ToString("F3") + " ниже плиты " + bs0.max.y.ToString("F3") + "; ");
                break;
            }
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
            // поперёк ветра при любом угле). Доворот ±14° и петли пути дают 0.66…0.97, порог 0.5.
            var galong = gtail - ghead; galong.y = 0f;
            if (galong.sqrMagnitude > 0.01f && UnityEngine.Vector3.Dot(galong.normalized, Cozy.Grid.Weather.Dir) < 0.5f)
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

// 21b. СНАРУЖИ ДОЖДЬ ЗАКРЫВАЕТ ВЕСЬ КАДР, включая низ (Илья 13.09: «внизу
// будто дождь не идёт»; P383). Правило пишется БЕЗ копии игровой логики: под
// открытым небом гасить столб нечем — гейт крыши требует игрока под крышей,
// гейт стены тоже, — значит выключенных столбов не должно быть ни одного.
// Дождь проба включает сама и возвращает в том же вызове, кадр между этим не
// рисуется, поэтому Илья ничего не увидит.
int rainOutside = 0;
{
    var qT = typeof(Cozy.Grid.RainDrops);
    var qbf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
    var qbfs = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
    var qRig = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.RainDrops>();
    var qLate = qT.GetMethod("LateUpdate", qbf);
    var qSky = qT.GetMethod("OpenSky", qbfs);
    var qCell = qT.GetMethod("CellSize", qbfs);
    var qOrg = qT.GetMethod("GridOrigin", qbfs);
    var qRends = qT.GetField("_rends", qbf);
    if (qRig != null && qLate != null && qSky != null && qCell != null && qOrg != null && qRends != null)
    {
        bool qKeep = Cozy.Grid.Weather.Rain;
        Cozy.Grid.Weather.Rain = true;
        qLate.Invoke(qRig, new object[0]);
        float qcs = (float)qCell.Invoke(null, new object[0]);
        var qorg = (UnityEngine.Vector3)qOrg.Invoke(null, new object[] { qcs });
        var qp = Cozy.View.ViewState.PlayerPos;
        float qfloor = Cozy.View.ViewState.CurrentFloorY;
        int qcx = UnityEngine.Mathf.RoundToInt((qp.x - qorg.x) / qcs);
        int qcz = UnityEngine.Mathf.RoundToInt((qp.z - qorg.z) / qcs);
        var qcell = new UnityEngine.Vector3(qorg.x + qcx * qcs, qfloor, qorg.z + qcz * qcs);
        bool qRoofed = (float)qSky.Invoke(null, new object[] { qcell, qcs, qcx, qcz }) > qfloor + 0.01f;
        var qlist = qRends.GetValue(qRig) as System.Collections.Generic.List<UnityEngine.MeshRenderer>;
        if (!qRoofed && qlist != null && qlist.Count > 0)
        {
            rainOutside = 1;
            int qoff = 0;
            foreach (var qr in qlist) if (qr != null && !qr.enabled) qoff++;
            if (qoff > 0)
                bad.Append("снаружи дождь не рисуется в " + qoff + " клетках из " + qlist.Count
                    + ": под открытым небом столб гасить нечем, кроме отсечки переднего плана, а она работает только в доме (P383); ");
        }
        Cozy.Grid.Weather.Rain = qKeep;
        qLate.Invoke(qRig, new object[0]);
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
    if (fanim != null && fanim.isHuman && flight != null && frig.Held)
    {
        bool fleft = frig.HeldSide == Cozy.Character.FlashlightRig.Side.Left;
        var fhand = fanim.GetBoneTransform(fleft ? UnityEngine.HumanBodyBones.LeftHand : UnityEngine.HumanBodyBones.RightHand);
        var ffore = fanim.GetBoneTransform(fleft ? UnityEngine.HumanBodyBones.LeftLowerArm : UnityEngine.HumanBodyBones.RightLowerArm);
        if (fhand != null && ffore != null)
        {
            var faxis = (fhand.position - ffore.position).normalized;
            float ftip = 0f;
            var fbones = fleft
                ? new UnityEngine.HumanBodyBones[] {
                    UnityEngine.HumanBodyBones.LeftIndexDistal,
                    UnityEngine.HumanBodyBones.LeftMiddleDistal,
                    UnityEngine.HumanBodyBones.LeftRingDistal,
                    UnityEngine.HumanBodyBones.LeftLittleDistal }
                : new UnityEngine.HumanBodyBones[] {
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

// 32. Радиус рендера (VIEW.md «Радиус рендера и сон дальних»): объект в кадре
// главной камеры никогда не скрыт радиусом, объект дальше HideBeyond от игрока
// всегда скрыт и спит (TreeWind/Burnable выключены). Уровень «forest100»: 5550
// объектов, в кадре ~110, скрыто ~4200–4970 — кадр 40 → 18 мс (10.09).
int farHidden = 0, farInView = 0;
{
    var fcam = UnityEngine.Camera.main;
    var fplanes = fcam != null ? UnityEngine.GeometryUtility.CalculateFrustumPlanes(fcam) : null;
    var fp = Cozy.View.ViewState.PlayerPos;
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null) continue;
        bool fh = Cozy.Grid.FarRadius.IsHidden(io);
        if (fh) farHidden++;
        var fr = io.GetComponentInChildren<UnityEngine.Renderer>();
        if (fr != null && fplanes != null && UnityEngine.GeometryUtility.TestPlanesAABB(fplanes, fr.bounds))
        {
            farInView++;
            if (fh) bad.Append("скрыт радиусом, но в кадре: " + io.Def.id + " @ " + io.transform.position.ToString("F1") + "; ");
        }
        var fd = io.transform.position - fp; fd.y = 0f;
        if (Cozy.Grid.FarRadius.Enabled && fd.magnitude > Cozy.Grid.FarRadius.HideBeyond + 3f && !fh && UnityEngine.Time.frameCount > 30)
            bad.Append("дальше радиуса, но не скрыт: " + io.Def.id + " @ " + io.transform.position.ToString("F1") + "; ");
        var ftw = io.GetComponent<Cozy.Grid.TreeWind>();
        if (fh && ftw != null && ftw.enabled) bad.Append("скрыт радиусом, но ветер не спит: " + io.Def.id + "; ");
    }
}

// Дебаг-слои, которые ПРЯЧУТ мир, вне дебаг-режима подняты быть не должны:
// они сохраняются в DebugTune и переживают перезаход, а дом изнутри становится
// чёрным (P457).
int viewLayers = 0;
if (!Cozy.View.ViewState.Debug)
{
    if (Cozy.View.ViewState.ShowCeiling) { bad.Append("поднят дебаг-слой «Показать потолок» вне дебага; "); viewLayers++; }
    if (Cozy.View.ViewState.HiddenRooms) { bad.Append("поднят дебаг-слой «Скрытые комнаты» вне дебага; "); viewLayers++; }
}

// «Ввод отобран» (PlayerPosture.Veiled) держат только сцена стычки, подъём после
// неё, сцена броска, гибель и сон. Поднят без них — игрок стоит столбом и не
// открывает экраны (17.09: флаг завис после чьей-то оборванной сцены).
int veilStuck = 0;
if (Cozy.Grid.PlayerPosture.Veiled && !Cozy.Combat.Encounter.Running && !Cozy.Combat.RangedAttack.SceneRunning
    && Cozy.Character.PlayerTarget.Alive)
{
    var recField = typeof(Cozy.Combat.Encounter).GetField("_recovery", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
    bool recovering = recField != null && recField.GetValue(null) != null;
    var sleepHud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
    var sleepField = typeof(Tavern.UI.HudUI).GetField("_sleepRun", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    bool sleeping = sleepHud != null && sleepField != null && sleepField.GetValue(sleepHud) != null;
    if (!recovering && !sleeping) { bad.Append("«ввод отобран» (Veiled) поднят без сцены, гибели и сна; "); veilStuck = 1; }
}

return " занавес завис=" + veilStuck + " слоёв вида поднято=" + viewLayers + " объектов=" + checkedObjects + " на своих местах=" + posed + " поверхностей=" + surfaces + " хостов осмотра=" + hosts + " рядов слотов=" + slotRows + " кукол=" + dolls + " у стен=" + nearWall + " в закрытых секциях=" + closed + " подвесов=" + mounts + " вложенных=" + nested + " с преградой у фокуса=" + touching + " на открытых поверхностях=" + onSurface + " порожков=" + thresholds + " скрытых=" + hiddenObjs + " настенных=" + wallMounted + " стен=" + wallTops + " порывов ветра=" + gusts + " клеток дождя=" + rainCells + " дождь снаружи=" + rainOutside + " фонарь в руке=" + handLamp + " гейт спавна=" + spawnGate + " молния=" + lightning + " скрыто радиусом=" + farHidden + " в кадре=" + farInView + " :: " + bad.ToString();
'''

CODE_B = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bad = new System.Text.StringBuilder();
var cam = UnityEngine.Camera.main;
var mDistOf = typeof(Tavern.UI.HudUI).GetMethod("ExamineDistanceOf", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var pColumn = typeof(Tavern.UI.HudUI).GetProperty("ExamineCardColumn", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
// 24. Растение на ветру ДЕЙСТВИТЕЛЬНО гнётся: ветер уехал на GPU (13.09,
// FoliageWind.hlsl), и вершины на процессор больше не возвращаются — прежняя
// проверка «корни не ушли под землю по самой нижней вершине» теперь физически
// невозможна. Само это правило шейдер держит ПО ПОСТРОЕНИЮ: `if (y <= 0.001)
// return 0` не двигает вершину у основания, а профиль (y/h)^2 гнёт каждую
// вершину отдельно, так что жёсткого поворота пучка целиком (баг 09.09) быть
// не может. Стережёт это тест EditMode по тексту .hlsl.
// Здесь остаётся то, что ломается ЖИВЬЁМ и молча:
//   1) глобали не подаются — `TickAll` выпал из тикера, ветер замер;
//   2) высота породы нулевая — шейдер выходит по `if (height <= 0.001)`,
//      растение стоит колом;
//   3) растению не подменили материал — оно осталось на шейдере без ветра.
int stemsBent = 0;
{
    var kindNames = new string[] { "None", "Tree", "Bush", "Stem" };
    var kindIds = new string[] { "", "_WindTreeHeight", "_WindBushHeight", "_WindStemHeight" };
    float windOn = UnityEngine.Shader.GetGlobalFloat("_WindOn");
    bool wantWind = Cozy.Grid.Weather.Wind;
    if ((windOn > 0.5f) != wantWind)
        bad.Append("глобали ветра не подаются (TreeWind.TickAll не зовут?): _WindOn=" + windOn.ToString("F0") + " при Weather.Wind=" + wantWind + "; ");
    var wKind = typeof(Cozy.Grid.TreeWind).GetField("_kind", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    var seenKind = new int[4];
    int stiff = 0; string stiffAt = "";
    foreach (var rig in UnityEngine.Object.FindObjectsByType<Cozy.Grid.TreeWind>(UnityEngine.FindObjectsSortMode.None))
    {
        if (rig == null || wKind == null) continue;
        int k = (int)wKind.GetValue(rig);
        if (k <= 0 || k > 3) continue;
        seenKind[k]++;
        stemsBent++;
        // Ключ нужен КАЖДОМУ материалу растения, а не одному из них: у стебля
        // их три, и потеря одного оставляет треть куста стоять колом (укус
        // 13.09 показал, что проверка «хоть один ветреный» этого не ловит).
        int windy = 0, plain = 0;
        foreach (var rend in rig.GetComponentsInChildren<UnityEngine.Renderer>(true))
            foreach (var m in rend.sharedMaterials)
            {
                if (m == null || m.shader == null || m.shader.name != "Tavern/CrownCut") continue;
                bool keyed = k == 3 ? m.IsKeywordEnabled("_WIND_STEM") : k == 2 ? m.IsKeywordEnabled("_WIND_BUSH") : true;
                if (keyed) windy++; else plain++;
            }
        if (windy == 0 || plain > 0)
        {
            stiff++;
            if (stiffAt.Length == 0) stiffAt = rig.name + " @ " + rig.transform.position.ToString("F1")
                + " (ветреных " + windy + ", без ключа " + plain + ")";
        }
    }
    if (stiff > 0) bad.Append("растений с ветром, но без ветреного материала: " + stiff + " (первое " + stiffAt + "); ");
    for (int k = 1; k < 4; k++)
        if (seenKind[k] > 0 && UnityEngine.Shader.GetGlobalFloat(kindIds[k]) <= 0.001f)
            bad.Append("порода " + kindNames[k] + " не гнётся: " + kindIds[k] + " нулевая при " + seenKind[k] + " растениях; ");
}

// 27. Статусы среды согласованы с источниками и ручками (EFFECTS.md): озноб = WetChill при мокром,
// иначе 0; в огне — горит; значки ряда идут через PlayerEffects.Sources и совпадают с флагами
// (с 13.09 один статус «Ничего не видно» ⇔ Blind || Dark, туман и темнота — два его источника); покрытие экрана: при доле тумана или
// темноты > 0 пелена меряет по экрану ровно тогда, когда так стоит ручка FogScreen / DarkScreen.
// Туман на игрока ВЕРНУЛСЯ 11.09 (инвариант 115): статус «не видно» по клетке, визуал по доле
// BlindAmount — перехваты держатся, пока доля > 0, и сняты все разом на нуле.
int exposure = 0;
{
    var xT = System.Type.GetType("Cozy.Effects.PlayerExposure, Cozy.Effects");
    var xPlayer = Cozy.Grid.PlayerRef.GameObject;
    if (xT != null && xPlayer != null)
    {
        exposure = 1;
        System.Func<string, bool> flag = n => (bool)xT.GetProperty(n).GetValue(null);
        bool wet = flag("Wet"), burning = flag("Burning"), inFire = flag("InFire");
        float lim = Cozy.Character.VisionArea.Limit;
        float amt = (float)xT.GetProperty("BlindAmount").GetValue(null);
        bool fogCell = (bool)xT.GetField("FogBlinds").GetValue(null) && Cozy.Grid.FogView.Covers(xPlayer.transform.position);
        if (flag("Blind") != fogCell) bad.Append("статус «не видно» при клетке тумана " + fogCell + "; ");
        float darkAmt = (float)xT.GetProperty("DarkAmount").GetValue(null);
        if (amt <= 0f && darkAmt <= 0f && (lim > 0f || Cozy.Character.DarknessVeil.ForcedDarkness >= 0f)) bad.Append("доли тумана и темноты 0, а перехват не снят; ");
        if (amt > 0f && (lim < (float)xT.GetField("FogSight").GetValue(null) - 0.01f || lim > Cozy.Character.VisionArea.BaseRadius + 0.01f)) bad.Append("обзор " + lim + " вне лерпа FogSight…BaseRadius; ");
        float wantChill = wet ? (float)xT.GetField("WetChill").GetValue(null) : 0f;
        if (UnityEngine.Mathf.Abs(Cozy.Character.BodyTemperature.Chill - wantChill) > 0.001f) bad.Append("озноб " + Cozy.Character.BodyTemperature.Chill + " при wet=" + wet + "; ");
        if (inFire && !burning) bad.Append("в огне, но не горит; ");
        if (Cozy.Character.PlayerEffects.Sources.Count < 1) bad.Append("ряд значков без поставщика статусов среды; ");
        var xStats = xPlayer.GetComponent<Cozy.Character.CharacterStats>();
        var xList = new System.Collections.Generic.List<Cozy.Character.PlayerEffect>();
        Cozy.Character.PlayerEffects.Collect(xStats, xList);
        bool hasBurn = false, hasBlind = false, hasWet = false;
        foreach (var xe in xList) { if (xe.Title == "Ожог") hasBurn = true; if (xe.Title == "Ничего не видно") hasBlind = true; if (xe.Title == "Мокрый") hasWet = true; }
        bool wantScreen = amt > 0f ? (bool)xT.GetField("FogScreen").GetValue(null) : (bool)xT.GetField("DarkScreen").GetValue(null);
        if ((amt > 0f || darkAmt > 0f) && (Cozy.Character.DarknessVeil.ForcedScreen > 0.5f) != wantScreen) bad.Append("покрытие экрана: пелена по экрану " + (Cozy.Character.DarknessVeil.ForcedScreen > 0.5f) + " при ручке " + wantScreen + "; ");
        if (hasBurn != burning || hasBlind != (flag("Blind") || flag("Dark")) || hasWet != wet) bad.Append("значки статусов расходятся с флагами: ожог " + hasBurn + "/" + burning + ", не видно " + hasBlind + " (снят 10.09), мокрый " + hasWet + "/" + wet + "; ");
    }
}

// ⚠️ ПОТОЛОК 50000 СИМВОЛОВ: execute_code длиннее не принимает, а комментарии и пустые
// строки перед отправкой вырезаются. 11.09 правило 27 упёрлось в потолок — новую проверку
// добавлять только вместе с сокращением старой; замерить: len кода после вырезания.
// 28. Просвет кроны (VIEW.md §10a): окно туманом НЕ закрывается (закон Ильи 11.09) — у каждого
// дерева с crownWindow вся листва на Tavern/CrownCut, а материалы ствола — нет (кора не режется);
// у каждой кроны копия-кайма (10.09: тот же меш, _CROWN_BAND, БЕЗ записи глубины, очередь BandQueue
// до дождя и тумана, без теней, кора невидима), включённая кайма ⇒ окно открыто, открытое окно ⇒
// ⭐ КОРА ПРОВЕРЯЕТСЯ ПО КЛЮЧУ РЕЗА, А НЕ ПО ШЕЙДЕРУ (13.09): с переносом ветра на GPU
// (windKind) изгиб коры считает FoliageWind внутри Tavern/CrownCut, и кора ЗАКОННО живёт
// на этом шейдере — материал «… (wind)». Правило же защищает от другого: чтобы окно кроны
// не вырезало ствол. Режет ключ _CROWN_CUT, его и спрашиваем. Проверка по имени шейдера
// давала 709 ложных жалоб на forest100 — ровно по одной на дерево.
// кайма шире 1 px; маска каймы _CrownBandTex рисуется ровно тогда, когда включена хоть одна кайма (_CrownBandOn).
// СГОРЕВШАЯ листва из счёта выброшена: FireView меняет её на CrownWindow.Invisible(), и это не брак, а зола.
int crowns = 0;
{
    var cPlayer = Cozy.Grid.PlayerRef.GameObject;
    if (cPlayer != null)
    {
        bool fogHere = Cozy.Grid.FogView.Covers(cPlayer.transform.position);
        float cOn = UnityEngine.Shader.GetGlobalFloat("_CrownWindowOn");
        if (cOn > 0.5f && UnityEngine.Shader.GetGlobalFloat("_CrownFeatherPx") < 1f) bad.Append("окно кроны открыто без каймы (_CrownFeatherPx < 1); ");
        int bandsLit = 0; foreach (var br in UnityEngine.Object.FindObjectsByType<UnityEngine.MeshRenderer>(UnityEngine.FindObjectsSortMode.None)) if (br.enabled && br.name == Cozy.Grid.SeeThroughView.GhostName) bandsLit++;
        if (cOn > 0.5f && bandsLit > 0 && UnityEngine.Shader.GetGlobalFloat("_CrownBandOn") < 0.5f) bad.Append("кайма включена, а маска каймы (_CrownBandOn) не рисуется; ");
        if (bandsLit == 0 && UnityEngine.Shader.GetGlobalFloat("_CrownBandOn") > 0.5f) bad.Append("маска каймы рисуется без единой включённой каймы (лишняя очистка текстуры каждый кадр); ");
        if (Cozy.Grid.CrownWindow.BandQueue <= 3400 || Cozy.Grid.CrownWindow.BandQueue >= 3550) bad.Append("кайма кроны в очереди " + Cozy.Grid.CrownWindow.BandQueue + " — должна быть после напольных (3400) и огня, но до дождя (3550) и тумана (3600), иначе трава поверх листвы или окружность в тумане (P298); ");
        if (Cozy.Grid.CrownWindow.Enabled && fogHere && cOn <= 0.5f) bad.Append("окно кроны закрылось в тумане, а его не убирают никогда (закон Ильи 11.09); ");
        foreach (var cio in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        {
            if (cio.Def == null || !cio.Def.crownWindow) continue;
            crowns++;
            UnityEngine.Transform crown = null, trunk = null;
            foreach (var tr in cio.GetComponentsInChildren<UnityEngine.Transform>(true)) { if (tr.name == cio.Def.crownNode) crown = tr; if (tr.name == cio.Def.heightNode) trunk = tr; }
            if (crown == null) continue;
            var bark = new System.Collections.Generic.HashSet<UnityEngine.Material>();
            if (trunk != null) foreach (var cr in trunk.GetComponentsInChildren<UnityEngine.MeshRenderer>(true)) foreach (var cm in cr.sharedMaterials) if (cm != null) bark.Add(cm);
            foreach (var cm in bark) if (cm.IsKeywordEnabled(Cozy.Grid.CrownWindow.CutKeyword)) { bad.Append("кору режет окно кроны: " + cio.name + "; "); break; }
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
                foreach (var cm in cr.sharedMaterials) { if (cm == null || bark.Contains(cm) || cm == Cozy.Grid.CrownWindow.Invisible()) continue; leaf++; if (cm.shader.name == "Tavern/CrownCut") cut++; }
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

// 29. Фокус осмотра, сдвинутый под колонку карточки, не лежит внутри ЧУЖОГО
//     непрозрачного коллайдера ни при каком угле подхода (P286: стена за
//     настенным счётчиком и стояком накрывала сдвинутый фокус, зазор ноль во
//     все стороны — камера не крутится и садится внутрь). Проверяем то, что
//     реально пойдёт в BeginExamine: CardShift → ShiftOutsideSolids.
int focusShifts = 0;
var mShiftOut = typeof(Cozy.Character.CameraFollow).GetMethod("ShiftOutsideSolids", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
var mTransp = typeof(Cozy.Character.CameraFollow).GetMethod("Transparent", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
if (cam != null && mDistOf != null && pColumn != null && mShiftOut != null && mTransp != null)
{
    float columnF = (float)pColumn.GetValue(null, null);
    var hostBefore29 = Cozy.Grid.Interactor.ExamineHost;
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        // Только ОСМАТРИВАЕМЫЕ: правило про камеру осмотра, а её нельзя открыть
        // на объекте без `examinable`. На forest100 таких объектов ноль из 7760,
        // и правило давало 106 жалоб на камеру, которой там не бывает (13.09).
        if (io == null || io.Def == null || io.Container != null || !io.Def.examinable) continue;
        var center = io.WorldBounds.center;
        focusShifts++;
        Cozy.Grid.Interactor.ExamineHost = io;
        foreach (float yaw in new float[] { 0f, 22.5f, 45f, 67.5f, 90f, 112.5f, 135f, 157.5f, 180f, 202.5f, 225f, 247.5f, 270f, 292.5f, 315f, 337.5f })
        {
            float baseDist = (float)mDistOf.Invoke(null, new object[] { io, center, yaw, 15f });
            var raw = Tavern.UI.ExamineFraming.CardShift(center, yaw, 15f, baseDist, cam.fieldOfView, cam.aspect, columnF);
            var focus = (UnityEngine.Vector3)mShiftOut.Invoke(null, new object[] { io, center, raw });
            bool buried = false;
            foreach (var col in UnityEngine.Physics.OverlapSphere(focus, 0.02f, UnityEngine.Physics.DefaultRaycastLayers, UnityEngine.QueryTriggerInteraction.Ignore))
            {
                if ((bool)mTransp.Invoke(null, new object[] { col, io })) continue;
                if (!col.bounds.Contains(focus)) continue;
                bad.Append((col.bounds.Contains(center) ? "фокус осмотра ещё ДО сдвига внутри чужого коллайдера: " : "сдвинутый фокус осмотра в чужом коллайдере: ") + io.Def.id + " (" + col.name + ", подход " + yaw + "°); ");
                buried = true; break;
            }
            if (buried) break;
        }
    }
    Cozy.Grid.Interactor.ExamineHost = hostBefore29;
}

// 33. Выбранный фонарь ВСЕГДА в руке, батарейки решают только свет (Илья
// 2026-09-10): у фонаря в активной ячейке хотбара Held всегда true, Lit ровно
// при заряде > 0, модель совпадает с рукой, спот — со светом. Проверка
// пассивная: карманы и заряд не трогаются.
int torchHand = 0;
{
    var qrig = UnityEngine.Object.FindFirstObjectByType<Cozy.Character.FlashlightRig>();
    var qhud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
    var qflags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
    if (qrig != null && qhud != null)
    {
        var qfield = typeof(Tavern.UI.HudUI).GetField("_activeQuick", qflags);
        var qat = typeof(Tavern.UI.HudUI).GetMethod("PocketPlacedAt", qflags);
        if (qfield != null && qat != null)
        {
            int qi = (int)qfield.GetValue(qhud);
            var qplaced = qi >= 0 ? (Cozy.Grid.PlacedItem)qat.Invoke(qhud, new object[] { qi }) : null;
            if (qplaced != null && Cozy.Grid.Items.IsFlashlight(qplaced.def))
            {
                torchHand = 1;
                float qcharge = Cozy.Grid.PowerCells.Charge(qplaced);
                if (!qrig.Held) bad.Append("выбранный фонарь не в руке (заряд " + qcharge.ToString("F0") + "); ");
                if (qrig.Lit != (qcharge > 0f)) bad.Append("свет фонаря не по заряду: светит=" + qrig.Lit + " при заряде " + qcharge.ToString("F0") + "; ");
            }
        }
        var qlamp = qrig.transform.Find("Flashlight");
        if (qlamp != null)
        {
            var qlight = qlamp.GetComponentInChildren<UnityEngine.Light>(true);
            if (qlamp.gameObject.activeSelf != qrig.Held) bad.Append("модель фонаря живёт отдельно от руки: активна=" + qlamp.gameObject.activeSelf + ", в руке=" + qrig.Held + "; ");
            if (qlight != null && qlight.enabled != qrig.Lit) bad.Append("спот фонаря живёт отдельно от света: включён=" + qlight.enabled + ", светит=" + qrig.Lit + "; ");
        }
        if (qrig.Lit && !qrig.Held) bad.Append("фонарь светит, не будучи в руке; ");
    }
}

// 34. Надетая вещь держится на костях НЫНЕШНЕГО тела (P317): вещь, надетая
// следом за другой в том же кадре, садилась на арматуру соседней вещи и через
// кадр теряла все кости — рисовать её было нечем, а герой оказывался голым.
int garmentBones = 0;
{
    var gplayer = Cozy.Grid.PlayerRef.GameObject;
    var gvisual = gplayer != null ? gplayer.transform.Find("Visual") : null;
    if (gvisual != null)
        foreach (UnityEngine.Transform gnode in gvisual)
        {
            if (!gnode.name.StartsWith("Wear_") && gnode.name != "Underwear") continue;
            foreach (var gsmr in gnode.GetComponentsInChildren<UnityEngine.SkinnedMeshRenderer>(true))
                foreach (var gbone in gsmr.bones)
                {
                    garmentBones++;
                    if (gbone == null || !gbone.IsChildOf(gvisual))
                    { bad.Append("вещь на чужих костях: " + gnode.name + "/" + gsmr.name + "; "); break; }
                }
        }
}

// 35. Ветка под ворон живёт по своим мерам (P322, инвариант 120): выключенная
// держит ПУСТОЙ меш и не имеет гнёзд (иначе ворона липнет к дереву без ветки),
// включённая даёт ровно два гнезда, разнесённых так, чтобы влезли две птицы.
int perches = 0;
foreach (var pio in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    var pperch = Cozy.Grid.CrowPerch.Of(pio);
    if (pperch == null) continue;
    perches++;
    UnityEngine.Transform pbranch = null;
    foreach (var pt in pio.GetComponentsInChildren<UnityEngine.Transform>(true))
        if (pt.name == Cozy.Grid.CrowPerch.NodeName) { pbranch = pt; break; }
    if (pbranch == null) { bad.Append("у дерева нет узла ветки: " + pio.Def.id + "; "); continue; }
    var pmounts = new System.Collections.Generic.List<UnityEngine.Transform>();
    foreach (var pt in pbranch.GetComponentsInChildren<UnityEngine.Transform>(true))
        if (pt.name.StartsWith(Cozy.Grid.CrowPerch.MountPrefix)) pmounts.Add(pt);
    var pfilter = pbranch.GetComponent<UnityEngine.MeshFilter>();
    int pverts = pfilter != null && pfilter.sharedMesh != null ? pfilter.sharedMesh.vertexCount : 0;
    if (!pperch.On)
    {
        if (pverts != 0) bad.Append("выключенная ветка рисуется: " + pio.Def.id + "; ");
        if (pmounts.Count != 0) bad.Append("у выключенной ветки остались гнёзда: " + pio.Def.id + "; ");
        continue;
    }
    if (pverts == 0) bad.Append("включённая ветка без меша: " + pio.Def.id + "; ");
    int pcached = 0;
    for (int pi = 0; pi < pperch.MountCount; pi++) if (pperch.MountOf(pi) != null) pcached++;
    if (pcached != pmounts.Count) bad.Append("кэш гнёзд ветки " + pcached + " против " + pmounts.Count + ": " + pio.Def.id + "; ");
    if (pmounts.Count != 2) bad.Append("гнёзд на ветке " + pmounts.Count + " вместо двух: " + pio.Def.id + "; ");
    else if ((pmounts[0].position - pmounts[1].position).magnitude < 0.5f)
        bad.Append("гнёзда на ветке ближе полуметра: " + pio.Def.id + "; ");

    // Корень сука обязан сидеть ВНУТРИ коры на своей высоте (P359): ствол
    // кривой, и посадка в центр коробки промахивалась мимо ствола. Позиция
    // узла в play уже унесена ветром, поэтому снос вычитается через ту же
    // TreeWind.BendAt, что его и добавила.
    UnityEngine.Transform ptrunk = null;
    foreach (var pt in pio.GetComponentsInChildren<UnityEngine.Transform>(true))
        if (pt.name == pio.Def.heightNode) { ptrunk = pt; break; }
    if (ptrunk == null) continue;
    var pgeo = Cozy.Grid.FurnitureModel.Geometry(ptrunk.GetComponentsInChildren<UnityEngine.Renderer>(true));
    float plow = pgeo.min.y + 0.25f;
    float phigh = UnityEngine.Mathf.Max(plow, pgeo.max.y - 0.25f);
    float pworldY = UnityEngine.Mathf.Clamp(pio.transform.position.y + pperch.Height, plow, phigh);
    var pbark = new System.Collections.Generic.List<UnityEngine.Vector3>();
    foreach (var pmf in ptrunk.GetComponentsInChildren<UnityEngine.MeshFilter>(true))
    {
        if (pmf.sharedMesh == null) continue;
        var pv = pmf.sharedMesh.vertices;
        for (int i = 0; i < pv.Length; i++) pbark.Add(pmf.transform.TransformPoint(pv[i]));
    }
    var pslice = new System.Collections.Generic.List<UnityEngine.Vector3>();
    for (float pband = 0.22f; pband <= 1.76f; pband *= 2f)
    {
        pslice.Clear();
        foreach (var pp in pbark) if (UnityEngine.Mathf.Abs(pp.y - pworldY) <= pband) pslice.Add(pp);
        if (pslice.Count >= 6) break;
    }
    if (pslice.Count < 6) continue;
    var paxis = UnityEngine.Vector3.zero;
    foreach (var pp in pslice) paxis += pp;
    paxis /= pslice.Count;
    float prad = 0f;
    foreach (var pp in pslice) prad += new UnityEngine.Vector2(pp.x - paxis.x, pp.z - paxis.z).magnitude;
    prad /= pslice.Count;
    var pwind = Cozy.Grid.TreeWind.On(pio.gameObject);
    var pbend = pwind != null ? pwind.BendAt(pworldY - pio.transform.position.y) : UnityEngine.Vector3.zero;
    float poff = new UnityEngine.Vector2(pbranch.position.x - pbend.x - paxis.x, pbranch.position.z - pbend.z - paxis.z).magnitude;
    if (poff > prad * 0.6f)
        bad.Append("корень ветки вне коры: " + pio.Def.id + " мимо оси на " + poff.ToString("F2") + " м при радиусе ствола " + prad.ToString("F2") + "; ");
}

// 36. СВЕТ СВЕТИТ В ТУ ЗОНУ, ГДЕ СТОИТ (P340): у каждого источника, кроме направленного,
// маска слоёв света обязана пересекаться с маской его места — костёр под небом с Outdoor,
// лампа в комнате с Indoor. Разошлись — источник горит, а вокруг темно, и в инспекторе
// это не видно. Маска Light и маска URP-данных источника обязаны совпадать: URP берёт вторую.
int zoneLights = 0;
foreach (var zl in UnityEngine.Object.FindObjectsByType<UnityEngine.Light>(UnityEngine.FindObjectsSortMode.None))
{
    if (zl.type == UnityEngine.LightType.Directional) continue;
    var zio = zl.GetComponentInParent<Cozy.Grid.InteractiveObject>();
    if (zio == null || zio.Def == null) continue;
    zoneLights++;
    uint zwant = zio.Def.outdoorOnly ? Cozy.Grid.LightZones.Outdoor : Cozy.Grid.LightZones.ZoneAt(zio.transform.position);
    uint zhas = unchecked((uint)zl.renderingLayerMask);
    if ((zhas & zwant) == 0) bad.Append("источник не светит в своё место: " + zio.Def.id + " маска " + zhas + " место " + zwant + "; ");
    var zdata = zl.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalLightData>();
    if (zdata != null && zdata.renderingLayers != zhas) bad.Append("у источника разошлись маски Light и URP: " + zio.Def.id + "; ");
}

// 37. ПРИЦЕЛ ФОНАРЯ ПОДНИМАЕТСЯ ТОЛЬКО ВВЕРХ (tavern-hands, 12.09): точка AimFocus под
// курсором едет вверх по видимой сплошной поверхности, но НИКОГДА не опускается ниже
// плоскости пола игрока — иначе свет прижмётся к ногам сильнее, чем было до правки.
int aimPts = 0;
{
    var aPlayer = Cozy.Grid.PlayerRef.GameObject;
    var aFocus = aPlayer != null ? aPlayer.GetComponent<Cozy.Character.AimFocus>() : null;
    var aCam = UnityEngine.Camera.main;
    if (aFocus != null && aCam != null)
    {
        var aMi = typeof(Cozy.Character.AimFocus).GetMethod("ResolveAimPoint", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        float aFloor = aPlayer.transform.position.y;
        for (int ax = 1; ax <= 5; ax++)
        for (int ay = 1; ay <= 3; ay++)
        {
            var aRay = aCam.ScreenPointToRay(new UnityEngine.Vector3(UnityEngine.Screen.width * ax / 6f, UnityEngine.Screen.height * ay / 4f, 0f));
            var aPt = (UnityEngine.Vector3)aMi.Invoke(aFocus, new object[] { aRay });
            aimPts++;
            if (aPt.y < aFloor - 0.01f) bad.Append("прицел фонаря ниже пола игрока: " + aPt.y.ToString("F2") + " < " + aFloor.ToString("F2") + "; ");
        }
    }
}

// 38. ПЕРЕПИСИ СОВПАДАЮТ С ПЕРЕБОРОМ (13.09): покадровые системы спрашивают
// список, а не перебирают уровень. Списки ведутся вручную, и пропущенный крючок
// делает подмножество неполным МОЛЧА: тепло не считается, ветка выпадает из поиска.
int cens1 = Cozy.Grid.InteractiveObject.Conducting.Count, cens2 = Cozy.Grid.InteractiveObject.Clad.Count;
int cens3 = Cozy.Grid.CrowPerch.All.Count, cens4 = Cozy.Grid.CrowFlight.All.Count;
{
var mSeat = typeof(Cozy.Grid.CladCuts).GetMethod("Seated", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
int w1 = 0, w2 = 0, w4 = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
if (io == null || io.Def == null) continue;
if (io.Conducts) w1++;
if (mSeat != null && (bool)mSeat.Invoke(null, new object[] { io })) w2++;
if (io.Def.birdIdle) w4++;
}
if (cens1 != w1) bad.Append("перепись проводящих " + cens1 + " против " + w1 + "; ");
if (cens2 != w2) bad.Append("перепись врезки обшивки " + cens2 + " против " + w2 + "; ");
if (cens4 != w4) bad.Append("перепись птиц " + cens4 + " против " + w4 + "; ");
}
// 39. ЗВУК ГЛУШИТСЯ ПО ЭТАЖАМ ОТ ИГРОКА, А НЕ ОТ ЭТАЖА ОБЗОРА (P368: сову не было
//     слышно — на улице этаж обзора уезжает к основанию грида, и `MuffleAt` резал
//     ВСЁ: звук с земли ×0.35, птицу на ветке ×0.12, собственный крик боли ×0.35).
//     Два требования разом: у самого уха приглушения этажами нет, и этаж считается
//     ОТБРАСЫВАНИЕМ — ветка под потолком ещё не «этажом выше», а полный этаж уже да.
int muffle = 0;
var mMuffle = typeof(Cozy.Grid.GameSfx).GetMethod("MuffleAt", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var earTf = Cozy.Grid.PlayerRef.Transform;
if (mMuffle != null && earTf != null)
{
muffle = 1;
float cs = UnityEngine.Mathf.Max(1f, Cozy.View.ViewState.CellSize);
var ear = earTf.position;
float atEar = (float)mMuffle.Invoke(null, new object[] { ear });
float nearTop = (float)mMuffle.Invoke(null, new object[] { ear + UnityEngine.Vector3.up * (cs * 0.9f) });
float overFloor = (float)mMuffle.Invoke(null, new object[] { ear + UnityEngine.Vector3.up * (cs * 1.1f) });
if (atEar < 0.4f) bad.Append("звук у самого уха приглушён этажами: " + atEar.ToString("F3") + "; ");
if (nearTop < atEar - 0.001f) bad.Append("звук под потолком своего этажа уже приглушён: " + nearTop.ToString("F3") + " против " + atEar.ToString("F3") + "; ");
if (overFloor > atEar * 0.5f) bad.Append("звук этажом выше не приглушён: " + overFloor.ToString("F3") + " против " + atEar.ToString("F3") + "; ");
}
// 40. ИГРОК ВСТАЁТ НА ЗЕМЛЮ НОГАМИ, А НЕ ЗАКАПЫВАЕТСЯ НАЧАЛОМ ОБЪЕКТА (P378):
//     метка спавна, центр сетки и `FreeSpotNear` говорят о точке ПОДОШВ, а
//     начало игрока лежит на метр выше — телепорт обязан эту разницу добавить.
//     Проверяется действием: прыжок на метку и возврат на прежнее место.
var gcp = Cozy.Grid.GridCursor.I;
var plr = Cozy.Grid.PlayerRef.GameObject;
var spawnPt = Cozy.Grid.SpawnPoint.Instance;
int teleport = 0;
if (gcp != null && plr != null && spawnPt != null)
{
teleport = 1;
var ccp = plr.GetComponent<UnityEngine.CharacterController>();
var savedAt = plr.transform.position;
gcp.TeleportPlayerTo(spawnPt.transform.position);
float feetY = plr.transform.position.y + (ccp != null ? ccp.center.y - ccp.height * 0.5f : 0f);
float soilY = gcp.GroundY(plr.transform.position.x, plr.transform.position.z, 0f);
var castFrom = new UnityEngine.Vector3(plr.transform.position.x, feetY + 0.5f, plr.transform.position.z);
foreach (var fh in UnityEngine.Physics.RaycastAll(castFrom, UnityEngine.Vector3.down, 4f, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
    if (!fh.collider.transform.IsChildOf(plr.transform) && fh.point.y > soilY) soilY = fh.point.y;
if (feetY < soilY - 0.01f) bad.Append("телепорт закопал игрока на " + (soilY - feetY).ToString("F2") + " м; ");
if (feetY > soilY + 0.6f) bad.Append("телепорт поднял игрока на " + (feetY - soilY).ToString("F2") + " м над землёй; ");
if (ccp != null) ccp.enabled = false;
plr.transform.position = savedAt;
if (ccp != null) ccp.enabled = true;
}
// 41. ПЕРЕПИСЬ ТИКАЮЩИХ НЕ ТЕРЯЕТ НИКОГО (13.09): покадровый обход идёт по
//     `InteractiveObject.Ticking`, а не по уровню, поэтому объект, у которого
//     есть что тикать, ОБЯЗАН в этой переписи быть. Признак `Idle` считается
//     живьём тем же кодом, что и в обходе, — сверяем список с ним.
var tIo = typeof(Cozy.Grid.InteractiveObject);
var bfIo = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var pIdle = tIo.GetProperty("Idle", bfIo);
var fInTick = tIo.GetField("_inTicking", bfIo);
if (pIdle != null && fInTick != null)
{
int lostTick = 0, busyTick = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
if (io == null) continue;
if ((bool)pIdle.GetValue(io, null)) continue;
busyTick++;
if (!(bool)fInTick.GetValue(io)) { lostTick++; if (lostTick <= 3) bad.Append("тикающий мимо переписи: " + (io.Def != null ? io.Def.id : io.name) + "; "); }
}
if (busyTick > Cozy.Grid.InteractiveObject.Ticking.Count)
bad.Append("перепись тикающих " + Cozy.Grid.InteractiveObject.Ticking.Count + " против " + busyTick + "; ");
}
// 42. КЭШИ ПОКАДРОВЫХ СИСТЕМ НЕ РАСХОДЯТСЯ С ПРАВДОЙ (13.09). Чтобы не трогать
//     тысячи объектов каждый кадр, две системы держат копию их состояния рядом
//     с собой: полоса каймы помнит «включена ли» (`Band.on`), а гейт этажа
//     держит в реестре только бодрствующие виды. Копия дешёвая, но врущая копия
//     хуже отсутствующей: полоса не нарисуется в маску, вид не пересчитает
//     видимость. Сверяем обе с первоисточником.
var tCw = typeof(Cozy.Grid.CrownWindow);
var fBands = tCw.GetField("_bands", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
if (fBands != null)
{
var bandList = fBands.GetValue(null) as System.Collections.IList;
if (bandList != null && bandList.Count > 0)
{
var bfB = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
var tB = bandList[0].GetType();
var fRend = tB.GetField("rend", bfB); var fOn = tB.GetField("on", bfB);
int bandSplit = 0;
if (fRend != null && fOn != null)
for (int bi = 0; bi < bandList.Count; bi++)
{
var br = fRend.GetValue(bandList[bi]) as UnityEngine.MeshRenderer;
if (br == null) continue;
if (br.enabled != (bool)fOn.GetValue(bandList[bi])) bandSplit++;
}
if (bandSplit > 0) bad.Append("полос каймы с враньём в флаге: " + bandSplit + "; ");
}
}
var tFv = typeof(Cozy.Grid.FloorPieceView);
var fAwake = tFv.GetField("Awake", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var fSlot = tFv.GetField("_slot", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
if (fAwake != null && fSlot != null)
{
var awake = fAwake.GetValue(null) as System.Collections.IList;
int slotBad = 0, farAwake = 0, nearAsleep = 0;
for (int ai = 0; ai < awake.Count; ai++)
{
var v = awake[ai] as Cozy.Grid.FloorPieceView;
if (v == null) continue;
if ((int)fSlot.GetValue(v) != ai) slotBad++;
}
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
if (io == null) continue;
var v = io.GetComponent<Cozy.Grid.FloorPieceView>();
if (v == null || !v.isActiveAndEnabled) continue;
bool inList = (int)fSlot.GetValue(v) >= 0;
if (io.Far && inList) farAwake++;
if (!io.Far && !inList) nearAsleep++;
}
if (slotBad > 0) bad.Append("видов этажа с неверным местом в реестре: " + slotBad + "; ");
if (nearAsleep > 0) bad.Append("близкий вид этажа спит: " + nearAsleep + "; ");
if (farAwake > 0) bad.Append("дальний вид этажа не уснул: " + farAwake + "; ");
}
// 43. КОЛЛАЙДЕР ЗЕМЛИ СОВПАДАЕТ С ПОЛЕМ ВЫСОТ (P360, P384; инвариант 148): рельеф
//     живёт дважды — полем `TerrainHeights` (по нему `GroundY` и постановка) и
//     коллайдерами клеток (по ним ходит игрок и бьёт луч опоры). Разошлись —
//     игрок по колено в земле, призрак не находит пол. Четыре точки в каждой
//     клетке земли без плиты сверху; расхождение > 1 см — жалоба.
int soilPts = 0, soilOff = 0; float soilMax = 0f;
var soilGrid = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
if (gcp != null && soilGrid != null)
{
var soilHits = new UnityEngine.RaycastHit[64];
float soilCs = soilGrid.CellSize;
for (int sx = 0; sx < soilGrid.Width; sx++)
for (int sz = 0; sz < soilGrid.Height; sz++)
{
if (!soilGrid.IsPresent(sx, sz)) continue;
var sc = soilGrid.CellToWorld(sx, sz);
for (int k = 0; k < 4; k++)
{
float px = sc.x + (k % 2 == 0 ? -0.3f : 0.3f) * soilCs;
float pz = sc.z + (k < 2 ? -0.3f : 0.3f) * soilCs;
int nh = UnityEngine.Physics.RaycastNonAlloc(new UnityEngine.Vector3(px, 30f, pz), UnityEngine.Vector3.down, soilHits, 60f, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
float soilHitY = float.NaN; bool slabAbove = false;
for (int i = 0; i < nh; i++)
{
var gb = soilHits[i].collider.GetComponent<Cozy.Grid.GridBlock>();
if (gb == null) continue;
if (gb.role != Cozy.Grid.GridRole.Ground) { slabAbove = true; break; }
if (float.IsNaN(soilHitY) || soilHits[i].point.y > soilHitY) soilHitY = soilHits[i].point.y;
}
if (slabAbove || float.IsNaN(soilHitY)) continue;
soilPts++;
float soilOffNow = UnityEngine.Mathf.Abs(soilHitY - gcp.GroundY(px, pz, 0f));
if (soilOffNow > 0.01f) { soilOff++; if (soilOffNow > soilMax) soilMax = soilOffNow; }
}
}
if (soilOff > 0) bad.Append("коллайдер земли расходится с полем высот: " + soilOff + " из " + soilPts + " точек, до " + soilMax.ToString("F3") + " м — ходят и ставят не по той земле, что нарисована (P360, P384); ");
}
// 203. Ярус зоны в стопке — по типам, которые ЕСТЬ на уровне (P477): одинокая
// техническая зона висела на 1.6 м, потому что ярус брался из номера типа в
// `Kinds`. Стопку включаем на время одного вызова — кадр не проходит, визуал
// не двигается — и сверяем ярус каждой зоны с числом типов, у которых есть
// клетки.
int zonesRanked = 0;
{
bool zpWasAll = Cozy.Grid.ZonePiece.AllLayers;
var zpKinds = new System.Collections.Generic.HashSet<Cozy.Grid.ZoneKind>();
foreach (var zp in Cozy.Grid.ZonePiece.All) if (zp != null && zp.Cells.Count > 0) zpKinds.Add(zp.kind);
Cozy.Grid.ZonePiece.AllLayers = true;
foreach (var zp in Cozy.Grid.ZonePiece.All)
{
if (zp == null || zp.Cells.Count == 0) continue;
zonesRanked++;
float zpThick = 2f * (zp.TopY - zp.VisualLift - zp.Cells[0].y);
int zpStep = zpThick > 0.001f ? UnityEngine.Mathf.RoundToInt(zp.VisualLift / (zpThick * 1.6f)) : 0;
if (zpStep >= zpKinds.Count) bad.Append("зона выше стопки: " + zp.DisplayName + " ярус " + zpStep + " при " + zpKinds.Count + " типах; ");
}
Cozy.Grid.ZonePiece.AllLayers = zpWasAll;
}
// 44. СТОЛБИК УГЛА НЕ ВЫСТУПАЕТ ИЗ ПЛОСКОСТИ СТЕН (P478; инвариант 204): WallCorner
//     на Г-углу с дверью/окном утоплен в обе стены на 2 мм. Выступ +1 см давал
//     пунктирную линию по фасаду в 26 см от угла и засечку сверху; вровень — z-fight.
int cornerPosts = 0;
{
float postT = gcp != null ? gcp.placeThickness : 0.25f;
foreach (var wc in Cozy.Grid.WallCorner.All)
{
if (wc == null) continue;
cornerPosts++;
var ps = wc.transform.localScale;
if (ps.x > postT - 0.001f || ps.z > postT - 0.001f) bad.Append("столбик угла выступает из стены: " + ps.x.ToString("F3") + "×" + ps.z.ToString("F3") + " при толщине " + postT.ToString("F3") + " @ " + wc.transform.position.ToString("F1") + "; ");
}
}
// 45. ПРИ ЗАКРЫТОМ ЭТАЖНОМ ГЕЙТЕ ОБЪЕКТ НЕ РИСУЕТ НИЧЕГО СВОЕГО (P548; инвариант 237):
//     у объекта с FloorPieceView.Visible == false ни один свой рендерер (OwnedBy,
//     включая выключенные при постройке узлы, воду, струю, воронку) не активен с
//     enabled. Шторка ванны (Swap-узел CurtainOpen) торчала с 2 этажа на 1-й.
int gateHidden = 0, gateLeaks = 0;
{
var leakNames = new System.Text.StringBuilder(); int leakObjs = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
if (io == null) continue;
var fv = io.GetComponent<Cozy.Grid.FloorPieceView>();
if (fv == null || fv.Visible) continue;
gateHidden++;
bool leaked = false;
foreach (var r in io.GetComponentsInChildren<UnityEngine.Renderer>(true))
{
if (!Cozy.Grid.InteractiveObject.OwnedBy(r, io)) continue;
if (!r.enabled || !r.gameObject.activeInHierarchy || r.forceRenderingOff) continue;
gateLeaks++; leaked = true;
if (leakNames.Length < 300) leakNames.Append(io.Def.id + "/" + r.name + " ");
}
if (leaked) leakObjs++;
}
if (gateLeaks > 0) bad.Append("рисуется при закрытом этажном гейте: " + gateLeaks + " рендереров у " + leakObjs + " объектов (" + leakNames.ToString().Trim() + "); ");
}
// 46. У КУСКА ПЛИНТУСА СТЕНЫ ИЛИ КУБА ЖИВОЙ ВЛАДЕЛЕЦ (P553; инвариант 240): снос
//     любого блока поднимает _wallsDirty, и плинтус снесённого куба уходит в
//     пересборке. Куски под проёмами и на лестницах (span) владельца могут не иметь.
int plinthPieces = 0, plinthOrphans = 0;
{
string orphanAt = "";
foreach (var pp in Cozy.Grid.PlinthPiece.All)
{
if (pp == null) continue;
plinthPieces++;
if (pp.span || pp.owner != null) continue;
plinthOrphans++;
var prr = pp.GetComponent<UnityEngine.Renderer>();
if (orphanAt == "" && prr != null) orphanAt = prr.bounds.center.ToString("F1");
}
if (plinthOrphans > 0) bad.Append("плинтус без носителя: " + plinthOrphans + " кусков (первый @ " + orphanAt + "); ");
int colorless = 0; var colorlessIds = new System.Text.StringBuilder();
foreach (var pio in Cozy.Grid.InteractiveObject.All)
{
    if (pio == null || pio.Def == null || string.IsNullOrEmpty(pio.Def.primaryMat) || pio.HasPrimaryColor) continue;
    colorless++;
    if (colorless <= 6) colorlessIds.Append(pio.Def.id + " ");
}
if (colorless > 0) bad.Append("правило 46: объект с primaryMat без слота цвета (кнопки «Основной цвет» нет): " + colorless + " (" + colorlessIds.ToString().Trim() + "); ");
}
// 47. НАСТЕННЫЙ НЕ ТОНЕТ В ОБШИВКЕ (P579; инвариант 250): спина объекта с mount Wall
//     не глубже 5 см от реального выноса досок стены за ним (CladOutFor с пустой
//     краской = замер по мешам PlankSide). Ловит отделку по умолчанию, которую
//     FacePaint не видит, и перекраску стены после развески.
int wallSeated = 0, wallSunk = 0; var sunkIds = new System.Text.StringBuilder();
{
var wallCols = new UnityEngine.Collider[64];
foreach (var wio in Cozy.Grid.InteractiveObject.All)
{
    if (wio == null || wio.Def == null || wio.Def.mount != Cozy.Grid.ObjectMount.Wall) continue;
    var wt = wio.transform; var wback = wt.forward; var wc = wt.position;
    float backExt = float.MinValue;
    foreach (var wr in wio.GetComponentsInChildren<UnityEngine.Renderer>())
    {
        if (!wr.enabled) continue; var wb = wr.bounds;
        for (int k = 0; k < 8; k++) { var v = new UnityEngine.Vector3((k & 1) == 0 ? wb.min.x : wb.max.x, (k & 2) == 0 ? wb.min.y : wb.max.y, (k & 4) == 0 ? wb.min.z : wb.max.z); backExt = UnityEngine.Mathf.Max(backExt, UnityEngine.Vector3.Dot(v - wc, wback)); }
    }
    if (backExt == float.MinValue) continue;
    int wn = UnityEngine.Physics.OverlapBoxNonAlloc(wc + wback * (backExt + 0.2f), new UnityEngine.Vector3(0.12f, 0.2f, 0.12f) + new UnityEngine.Vector3(UnityEngine.Mathf.Abs(wback.z), 0f, UnityEngine.Mathf.Abs(wback.x)) * 0.1f, wallCols, UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
    Cozy.Grid.GridBlock wgb = null; float bodyDist = float.MaxValue;
    for (int k = 0; k < wn; k++)
    {
        var col = wallCols[k]; if (col.transform.IsChildOf(wt)) continue;
        var g = col.GetComponentInParent<Cozy.Grid.GridBlock>();
        if (g == null || !Cozy.Grid.BuildQuery.WallLike(col) || Cozy.Grid.BuildQuery.CubeBlock(g)) continue;
        var cb = col.bounds; float near = float.MaxValue;
        for (int q = 0; q < 8; q++) { var v = new UnityEngine.Vector3((q & 1) == 0 ? cb.min.x : cb.max.x, (q & 2) == 0 ? cb.min.y : cb.max.y, (q & 4) == 0 ? cb.min.z : cb.max.z); near = UnityEngine.Mathf.Min(near, UnityEngine.Vector3.Dot(v - wc, wback)); }
        float d = near - backExt;
        if (d < -0.05f || d >= bodyDist) continue;
        bodyDist = d; wgb = g;
    }
    if (wgb == null) continue;
    wallSeated++;
    float planks = Cozy.Grid.PlinthView.CladOutFor(wgb, -wback, "");
    float sunk = planks - bodyDist;
    if (sunk > 0.05f) { wallSunk++; if (wallSunk <= 6) sunkIds.Append(wio.Def.id + "@" + wc.ToString("F1") + " на " + (sunk * 100f).ToString("0") + " см; "); }
}
}
if (wallSunk > 0) bad.Append("правило 47: настенный тонет в обшивке: " + wallSunk + " (" + sunkIds + "); ");
// 48. НАД СТУПЕНЯМИ МАРША НЕТ ПЛИТЫ НА ВЫСОТЕ ГОЛОВЫ (28.09, night_build_c): марш, чей верх
//     уходит под перекрытие без дыры, игрок проходит, упираясь головой. Точки — на 25..85 %
//     длины марша (у самого верха плита по краю дыры законна), запас 1,9 м от ступени до низа плиты.
int stairsChecked = 0, stairsHead = 0; var headWhere = new System.Text.StringBuilder();
foreach (var sp in Cozy.Grid.StairPiece.All)
{
    if (sp == null || sp.IsGhost || sp.riseCells <= 0) continue;
    stairsChecked++;
    var stf = sp.transform; float srun = UnityEngine.Mathf.Max(1, sp.lengthCells) * 3f; float srise = sp.riseCells * 3f;
    for (float fa = 0.25f; fa <= 0.851f; fa += 0.2f)
    {
        var tp = stf.TransformPoint(new UnityEngine.Vector3(0f, srise * fa, -srun * 0.5f + srun * fa));
        var slab = Cozy.Grid.BuildQuery.BlockAt(new UnityEngine.Vector3(tp.x, tp.y + 1.0f, tp.z), new UnityEngine.Vector3(0.1f, 0.9f, 0.1f), Cozy.Grid.GridRole.Floor);
        if (slab == null) continue;
        stairsHead++;
        if (headWhere.Length < 200) headWhere.Append("(" + tp.x.ToString("F1") + ", " + tp.y.ToString("F1") + ", " + tp.z.ToString("F1") + ") ");
        break;
    }
}
if (stairsHead > 0) bad.Append("правило 48: над ступенями марша плита на высоте головы: " + stairsHead + " (" + headWhere.ToString().Trim() + "); ");
int clocksChecked = 0, clocksWrong = 0; var clockIds = new System.Text.StringBuilder();
foreach (var cio in Cozy.Grid.InteractiveObject.All)
{
    if (cio == null || cio.Def == null || !cio.Def.clockFace) continue;
    UnityEngine.Transform handMin = null, handHour = null;
    foreach (var ht in cio.GetComponentsInChildren<UnityEngine.Transform>(true)) { if (ht.name == "HandMinute") handMin = ht; else if (ht.name == "HandHour") handHour = ht; }
    var minRend = handMin != null ? handMin.GetComponentInChildren<UnityEngine.Renderer>() : null;
    var hourRend = handHour != null ? handHour.GetComponentInChildren<UnityEngine.Renderer>() : null;
    if (minRend == null || hourRend == null) continue;
    clocksChecked++;
    float clockHour = UnityEngine.Mathf.Repeat(Cozy.Grid.Weather.Hour, 24f);
    var tipMin = cio.transform.InverseTransformDirection(minRend.bounds.center - handMin.position);
    var tipHour = cio.transform.InverseTransformDirection(hourRend.bounds.center - handHour.position);
    float shownMin = UnityEngine.Mathf.Atan2(tipMin.x, tipMin.y) * UnityEngine.Mathf.Rad2Deg;
    float shownHour = UnityEngine.Mathf.Atan2(tipHour.x, tipHour.y) * UnityEngine.Mathf.Rad2Deg;
    float expectedMin = clockHour * 60f % 60f * 6f;
    float expectedHour = clockHour % 12f / 12f * 360f;
    float offMin = UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(shownMin, expectedMin));
    float offHour = UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(shownHour, expectedHour));
    if (offMin > 2f || offHour > 2f) { clocksWrong++; if (clocksWrong <= 6) clockIds.Append(cio.Def.id + " мин показ=" + shownMin.ToString("0") + "° ожид=" + expectedMin.ToString("0") + "°, час показ=" + shownHour.ToString("0") + "° ожид=" + expectedHour.ToString("0") + "°; "); }
}
if (clocksWrong > 0) bad.Append("правило 48: стрелки часов не по часовой/не по времени: " + clocksWrong + " из " + clocksChecked + " (" + clockIds + "); ");
// 49 (P727): дополнительные лампы по пикселям. В YAML 1 = PerPixel, 2 = PerVertex;
// по вершинам у ламп нет теней, свет холодильника выходит сквозь корпус.
int lampMode = 0;
var urp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline as UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset;
if (urp == null) bad.Append("ЗАЩИТА МЕРТВА, правило 49 не выполняется: нет UniversalRenderPipelineAsset; ");
if (urp != null) { lampMode = 1; if (urp.additionalLightsRenderingMode != UnityEngine.Rendering.Universal.LightRenderingMode.PerPixel) bad.Append("правило 49: лампы считаются " + urp.additionalLightsRenderingMode + ", нужно PerPixel (в PC_RPAsset m_AdditionalLightsRenderingMode: 1); "); }
// 50 (P728): «Годен до:» и дата одним шрифтом и размером. Дата — Inter (WorldLabel),
// надпись — меш Inter из Blender; высота меша с хвостом «д» / высота цифр даты = 1,184.
int expiryChecked = 0, expiryWrong = 0; var expiryIds = new System.Text.StringBuilder();
foreach (var eio in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (eio == null || eio.Def == null) continue;
    UnityEngine.Transform eLab = null, eNode = null, eUp = null; TMPro.TextMeshPro eDate = null;
    foreach (var et in eio.GetComponentsInChildren<UnityEngine.Transform>(true))
    {
        if (et.name == "LabelExpiry" || et.name == "CartonExpiry") eLab = et;
        else if (et.name == "Expiry") eNode = et;
        else if (et.name == "ExpiryUp") eUp = et;
        else if (et.name == "ExpiryLabel") eDate = et.GetComponent<TMPro.TextMeshPro>();
    }
    var eMesh = eLab != null ? eLab.GetComponentInChildren<UnityEngine.MeshFilter>() : null;
    if (eMesh == null || eMesh.sharedMesh == null || eNode == null || eUp == null || eDate == null || string.IsNullOrEmpty(eDate.text)) continue;
    expiryChecked++;
    var eDir = (eUp.position - eNode.position).normalized;
    float eLo = float.MaxValue, eHi = float.MinValue;
    foreach (var ev in eMesh.sharedMesh.vertices) { float ed = UnityEngine.Vector3.Dot(eMesh.transform.TransformPoint(ev) - eNode.position, eDir); if (ed < eLo) eLo = ed; if (ed > eHi) eHi = ed; }
    eDate.ForceMeshUpdate(true, true);
    float eDateH = eDate.textBounds.size.y * eDate.transform.lossyScale.y;
    float eRatio = eDateH > 0f ? (eHi - eLo) / eDateH : 0f;
    bool eFont = eDate.font != null && eDate.font.name.StartsWith("Inter");
    if (!eFont || eRatio < 1.12f || eRatio > 1.25f) { expiryWrong++; if (expiryWrong <= 6) expiryIds.Append(eio.Def.id + " надпись/дата=" + eRatio.ToString("0.00") + (eFont ? "" : " шрифт даты " + (eDate.font != null ? eDate.font.name : "нет")) + "; "); }
}
if (expiryWrong > 0) bad.Append("правило 50: «Годен до:» и дата разного размера или шрифта (норма 1,18): " + expiryWrong + " из " + expiryChecked + " (" + expiryIds + "); ");
return " настенных у обшивки=" + wallSeated + " кусков плинтуса=" + plinthPieces + " скрытых гейтом=" + gateHidden + " растений на ветру=" + stemsBent + " статусы=" + exposure + " крон=" + crowns + " низких слотов=" + floorSlots + " фокусов осмотра=" + focusShifts + " фонарь в кармане=" + torchHand + " костей одежды=" + garmentBones + " веток=" + perches + " источников=" + zoneLights + " точек прицела=" + aimPts + " звук по этажам=" + muffle + " телепорт на метку=" + teleport + " земля=" + soilPts + " переписи=" + cens1 + "/" + cens2 + "/" + cens3 + "/" + cens4 + " ярусов зон=" + zonesRanked + " столбиков угла=" + cornerPosts + " часов=" + clocksChecked + " режим ламп=" + lampMode + " сроков=" + expiryChecked + " :: " + bad.ToString();
'''



def half(code, strike):
    # Мост режет код на 50 000 символов, а отступы занимают шесть с половиной
    # тысяч: снимаем их вместе с комментариями. Многострочных литералов (@"…")
    # в правилах нет, поэтому отступ ничего не значит.
    code = '\n'.join(l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith('//'))
    code = code.replace('STRIKE_ALLOWED', 'true' if strike else 'false')
    if len(code) > 50000:
        return None, 'ПРОБА НЕ ОТПРАВЛЕНА: код %d символов при лимите моста 50 000 — правила надо ужать или резать прогон натрое' % len(code)
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    data = json.loads(line)
    body = data.get("data") if isinstance(data, dict) else None
    if not isinstance(body, dict) or not body.get("result"):
        return None, 'ПРОБА НЕ ОТВЕТИЛА: ' + json.dumps(data, ensure_ascii=False)[:400]
    return body["result"], None


# ⭐ Счётчик → правило, которое им МЕРЯЕТСЯ. Нужен ради одного: счётчик,
# упавший в НОЛЬ, означает «правило не нашло на уровне ни одного подходящего
# объекта», то есть зелёный по нему не значит ничего. В плоской строке из
# тридцати чисел этого не видно, и 13.09 на forest100 так молчали ВОСЕМНАДЦАТЬ
# правил разом — дом проверялся, лес нет. Теперь они называются вслух.
RULE_OF = {
    'объектов': '1–4', 'на своих местах': '17', 'поверхностей': '16',
    'хостов осмотра': '15', 'рядов слотов': '14', 'кукол': '13', 'у стен': '10',
    'в закрытых секциях': '1', 'подвесов': '5', 'вложенных': '6',
    'с преградой у фокуса': '7', 'на открытых поверхностях': '8', 'порожков': '9',
    'скрытых': '11', 'настенных': '12', 'стен': '18', 'порывов ветра': '19',
    'клеток дождя': '21', 'дождь снаружи': '21b', 'фонарь в руке': '22', 'гейт спавна': '20',
    'молния': '23', 'скрыто радиусом': '32', 'в кадре': '32',
    'растений на ветру': '24', 'статусы': '27', 'крон': '28', 'низких слотов': '30',
    'фокусов осмотра': '29', 'фонарь в кармане': '33', 'костей одежды': '34',
    'веток': '35', 'источников': '36', 'точек прицела': '37',
    'настенных у обшивки': '47',
    'звук по этажам': '39', 'телепорт на метку': '40', 'переписи': '38/41/42', 'земля': '43', 'столбиков угла': '44', 'режим ламп': '49', 'сроков': '50',
}


def idle_rules(counters, strike):
    """Правила, чьи счётчики на нуле: они ничего не проверили на этом уровне."""
    seen = {}
    for name, value in re.findall(r'([А-Яа-яёA-Za-z ]+?)=([\d/]+)', counters):
        name = name.strip()
        rule = RULE_OF.get(name)
        if rule is None:
            continue
        alive = any(part not in ('', '0') for part in value.split('/'))
        # У правила 32 два счётчика, и хватает любого живого.
        seen[rule] = seen.get(rule, False) or alive
    idle = sorted((r for r, alive in seen.items() if not alive), key=lambda r: int(re.match(r'\d+', r).group()))
    if not strike and '23' in idle:
        idle.remove('23')
    return idle


def main():
    # Правила уехали за потолок моста, поэтому прогон идёт ДВУМЯ вызовами:
    # у каждой половины свой пролог, свои счётчики и свои жалобы, а склейка
    # здесь — чтобы читателю по-прежнему приходила ОДНА строка (13.09).
    strike = '--strike' in sys.argv
    counters, complaints = [], []
    for code in (CODE_A, CODE_B):
        res, err = half(code, strike)
        if err:
            print(err)
            return
        if res == 'не в play':
            print('не в play')
            return
        left, _, right = res.partition(' :: ')
        counters.append(left.strip())
        complaints.append(right.strip())
    # Жалобы сортируются: порядок FindObjectsByType гуляет между заходами в play,
    # и verify ночи краснел на переставленных «гнёзда на ветке» (18.09, ilya-77).
    items = [x.strip() for c in complaints if c for x in c.split(';') if x.strip()]
    tail = '; '.join(sorted(items))
    counters = ' '.join(counters)
    idle = idle_rules(counters, strike)
    quiet = ''
    if idle:
        quiet = ' :: НЕЧЕГО БЫЛО ПРОВЕРЯТЬ (на уровне нет таких объектов), правила ' + ', '.join(idle)
    if not strike:
        quiet += ' :: правило 23 (молния) пропущено намеренно, нужен --strike'
    print(counters + ' :: ' + (tail if tail else 'инварианты держатся') + quiet)


if __name__ == '__main__':
    main()
