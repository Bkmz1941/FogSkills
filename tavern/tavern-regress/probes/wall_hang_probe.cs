// ПОДВЕС НА СТЕНУ (P1051, инв. 549; верх под плитой перекрытия). Для execute_code (в play).
// Ищет свободную нарисованную стену своего этажа рядом с игроком, настоящим ComputeObjectPose
// вешает полотно церкви (пивот наверху, keepModelPivot+keepModelHeight) и икону (пивот внизу):
// оба зелёные, полотно целиком между полом + 5 см и плитой перекрытия (3 − 0,2 − 0,05).
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPos = cam.transform.position; var savedRot = cam.transform.rotation;
var player = Cozy.Grid.PlayerRef.GameObject;
float cell = 3f;
float floorY = Cozy.Grid.GridManager.LevelY(player.transform.position.y + 0.05f, cell);
Cozy.Grid.GridBlock wall = null; var back = UnityEngine.Vector3.zero; bool wallThinX = false;
var cols = new UnityEngine.Collider[32];
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.role != Cozy.Grid.GridRole.Wall || gb.railing || !Cozy.Grid.FloorPieceView.Drawn(gb.Rend)) continue;
    var p = gb.transform.position; var s = gb.transform.lossyScale;
    if (UnityEngine.Mathf.Abs(p.y - s.y * 0.5f - floorY) > 0.3f) continue;
    if ((p - player.transform.position).sqrMagnitude > 400f) continue;
    bool thinX = s.x < s.z;
    var toP = player.transform.position - p;
    var n = thinX ? new UnityEngine.Vector3(UnityEngine.Mathf.Sign(toP.x), 0f, 0f) : new UnityEngine.Vector3(0f, 0f, UnityEngine.Mathf.Sign(toP.z));
    var probe = new UnityEngine.Vector3(p.x, floorY + 1.5f, p.z) + n * 0.9f;
    int hits = UnityEngine.Physics.OverlapBoxNonAlloc(probe, new UnityEngine.Vector3(thinX ? 0.75f : 1.4f, 1.4f, thinX ? 1.4f : 0.75f), cols, UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
    bool busy = false;
    for (int i = 0; i < hits; i++)
        if (cols[i].GetComponentInParent<Cozy.Grid.InteractiveObject>() != null || cols[i].GetComponentInParent<Cozy.Grid.StairPiece>() != null || cols[i].GetComponentInParent<Cozy.Grid.DoorPiece>() != null) { busy = true; break; }
    if (busy) continue;
    wall = gb; back = -n; wallThinX = thinX; break;
}
if (wall == null) return "ПРОПУСК: нет свободной нарисованной стены своего этажа в 20 м от игрока";
var sb = new System.Text.StringBuilder();
var bad = new System.Collections.Generic.List<string>();
UnityEngine.GameObject body = null;
try
{
    var wp = wall.transform.position; var ws = wall.transform.lossyScale;
    float half = (wallThinX ? ws.x : ws.z) * 0.5f;
    var face = new UnityEngine.Vector3(wp.x, floorY + 1.6f, wp.z) - back * (half + 0.02f);
    foreach (var id in new[] { "church_sheet_1", "church_icon_1" })
    {
        var def = Cozy.Grid.FurnitureCatalog.ById(id);
        if (def == null) { bad.Add(id + ": нет в каталоге"); continue; }
        body = new UnityEngine.GameObject("WallHangProbe");
        body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
        var worldDir = (back + UnityEngine.Vector3.down * 0.6f).normalized;
        cam.transform.SetPositionAndRotation(face - worldDir * 3f, UnityEngine.Quaternion.identity);
        var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
        cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
        cam.transform.position = face - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
        var args = new object[] { def, cam, mouse, body, body.transform, floorY, null, null, null };
        bool ok = (bool)mPose.Invoke(gc, args);
        var pos = (UnityEngine.Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
        body.transform.SetPositionAndRotation(pos, UnityEngine.Quaternion.Euler(0f, yaw, 0f));
        var rends = body.GetComponentsInChildren<UnityEngine.Renderer>();
        var bb = rends.Length > 0 ? rends[0].bounds : new UnityEngine.Bounds();
        foreach (var r in rends) bb.Encapsulate(r.bounds);
        sb.Append(id + ": " + (ok ? (blocked ? "КРАСНОЕ" : "зелёное") : "нет позы") + " y " + (bb.min.y - floorY).ToString("0.00") + ".." + (bb.max.y - floorY).ToString("0.00") + "; ");
        if (!ok || blocked) bad.Add(id + " у свободной стены " + (ok ? "красное" : "без позы") + " (P1051)");
        if (bb.min.y < floorY + 0.04f) bad.Add(id + ": низ под полом (" + (bb.min.y - floorY).ToString("0.00") + ") — пивот наверху не учтён (P1051)");
        if (bb.max.y > floorY + cell - 0.2f + 0.01f) bad.Add(id + ": верх в плите перекрытия (" + (bb.max.y - floorY).ToString("0.00") + " > 2,80)");
        UnityEngine.Object.DestroyImmediate(body); body = null;
    }
}
finally
{
    if (body != null) UnityEngine.Object.DestroyImmediate(body);
    cam.transform.SetPositionAndRotation(savedPos, savedRot);
    UnityEngine.Physics.SyncTransforms();
}
return (bad.Count == 0 ? "ОК" : "ПРОВАЛ: " + string.Join("; ", bad.ToArray())) + " | стена " + wall.transform.position.ToString("0.0") + " | " + sb;
