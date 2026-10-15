// ВЕЩЬ НА КОВЁР — СВЕРХУ (P1049): для execute_code (в play). Берёт нарисованный ковёр уровня,
// настоящим ComputeObjectPose кладёт на его середину книгу: поза зелёная, низ книги на верхе
// ковра (не под ним и не на полу).
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPos = cam.transform.position; var savedRot = cam.transform.rotation;
Cozy.Grid.InteractiveObject rug = null;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null || io.Def.mount != Cozy.Grid.ObjectMount.Floor || !io.Def.walkOver || !io.Def.underFurniture) continue;
    if (io.Def.id == null || !io.Def.id.Contains("rug")) continue;
    var r = io.GetComponentInChildren<UnityEngine.Renderer>();
    if (r == null || !Cozy.Grid.FloorPieceView.Drawn(r)) continue;
    var wb = io.WorldBounds;
    if (wb.min.y - Cozy.Grid.GridManager.LevelY(wb.min.y + 0.05f, 3f) > 0.1f) continue;
    rug = io; break;
}
if (rug == null) return "ПРОПУСК: на уровне нет нарисованного напольного ковра (rug в id, walkOver + underFurniture, лежит на полу)";
var def = Cozy.Grid.FurnitureCatalog.ById("book_prayer");
if (def == null) return "ПРОПУСК: нет дефа book_prayer";
var rb = rug.WorldBounds;
float floorY = Cozy.Grid.GridManager.LevelY(rb.min.y + 0.05f, 3f);
UnityEngine.GameObject body = null;
string verdict;
try
{
    body = new UnityEngine.GameObject("RugTopProbe");
    body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
    var target = new UnityEngine.Vector3(rb.center.x, rb.max.y, rb.center.z);
    var worldDir = new UnityEngine.Vector3(0.25f, -1f, 0.2f).normalized;
    cam.transform.SetPositionAndRotation(target - worldDir * 4f, UnityEngine.Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 4f;
    var args = new object[] { def, cam, mouse, body, body.transform, floorY, null, null, null };
    bool ok = (bool)mPose.Invoke(gc, args);
    var pos = (UnityEngine.Vector3)args[6]; bool blocked = (bool)args[8];
    float lift = pos.y - rb.max.y;
    verdict = (ok && !blocked && UnityEngine.Mathf.Abs(lift) <= 0.03f ? "ОК" : "ПРОВАЛ")
        + ": книга на ковре «" + rug.Def.id + "» " + (ok ? (blocked ? "красная" : "зелёная") : "без позы")
        + ", низ книги над ворсом " + lift.ToString("0.000") + " м (ворс " + (rb.max.y - floorY).ToString("0.00") + " над полом; P1049 — под ковёр нельзя)";
}
finally
{
    if (body != null) UnityEngine.Object.DestroyImmediate(body);
    cam.transform.SetPositionAndRotation(savedPos, savedRot);
    UnityEngine.Physics.SyncTransforms();
}
return verdict;
