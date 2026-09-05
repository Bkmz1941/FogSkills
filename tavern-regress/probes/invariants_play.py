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
    // 3. Ни одного объекта без видимых мешей.
    int visible = 0;
    foreach (var r in io.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
        if (r.enabled && r.gameObject.activeInHierarchy && !r.name.StartsWith("Outline")) visible++;
    if (visible == 0) bad.Append("невидимый объект: " + io.Def.id + "; ");
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
var mHostClear = typeof(Cozy.Character.CameraFollow).GetMethod("HostClear", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var mEnclosing = typeof(Cozy.Character.CameraFollow).GetMethod("EnclosingClear", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
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
        float floorD = (float)mHostClear.Invoke(null, new object[] { io });
        bool leak = false;
        foreach (float pitch in new float[] { -25f, 10f, 35f })
        foreach (float yaw in new float[] { 0f, 45f, 90f, 135f, 180f, 225f, 270f, 315f })
        {
            var dir = UnityEngine.Quaternion.Euler(pitch, yaw, 0f) * UnityEngine.Vector3.back;
            float entry = float.MaxValue;
            foreach (var b in foreign) { float e; if (b.IntersectRay(new UnityEngine.Ray(focus, dir), out e) && e < entry) entry = e; }
            if (entry == float.MaxValue) continue;
            float d = (float)mClear.Invoke(null, new object[] { focus, yaw, pitch, 3.0f, 0.15f });
            float enclosing = (float)mEnclosing.Invoke(null, new object[] { io, focus, dir });
            if (d > UnityEngine.Mathf.Max(entry, UnityEngine.Mathf.Max(floorD, enclosing)) + 0.01f) leak = true;
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
return "объектов=" + checkedObjects + " у стен=" + nearWall + " в закрытых секциях=" + closed + " подвесов=" + mounts + " вложенных=" + nested + " с преградой у фокуса=" + touching + " на открытых поверхностях=" + onSurface + " порожков=" + thresholds + " :: "
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
