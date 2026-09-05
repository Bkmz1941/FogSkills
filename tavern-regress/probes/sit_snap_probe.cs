// Проба «За стол → Сесть» (INVARIANTS 33). execute_code в play. Берёт стул
// (`chair`) и стол (`seatCount>0`), считает позу НАСТОЯЩИМ снапом
// GridCursor.ComputeObjectPose с курсором у места «За стол» (кромка + 0.5
// наружу), временно ставит стул в эту позу, проверяет PushedIn=false,
// садится (ожидание clip=Sit_Idle при пустом столе), меряет кисть над
// столешницей, встаёт, возвращает стул. Ничего не сохраняет.
if (!Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var player = Cozy.Grid.PlayerRef.GameObject;
var cam = Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
Cozy.Grid.InteractiveObject table = null, chair = null;
foreach (var io in Cozy.Grid.InteractiveObject.All) { if (io == null) continue; if (table == null && io.Def.seatCount > 0) table = io; }
if (table == null) return "нет стола";
float bestD = 4f;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || !io.Def.chair) continue;
    float d = Vector3.Distance(io.transform.position, table.transform.position);
    if (d < bestD) { bestD = d; chair = io; }
}
if (chair == null) return "нет стула у стола";
var tb = table.WorldBounds;
sb.Append("стол " + table.Def.id + " верх=" + tb.max.y.ToString("0.00") + " ext=" + tb.extents.ToString("0.00") + "\n");
var savedChair = chair.transform.position; var savedYaw = chair.transform.rotation;
var savedPlayer = player.transform.position; var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
try
{
    // место «За стол» с той стороны, где сейчас стул: кромка + 0.5 наружу
    var outward = chair.transform.position - tb.center; outward.y = 0f; outward.Normalize();
    var target = new Vector3(tb.center.x, chair.transform.position.y, tb.center.z) + outward * (tb.extents.x + 0.5f);
    player.transform.position = target + outward * 1.5f;
    Physics.SyncTransforms();
    // телом и исключением служит САМ стул, как при переносе (иначе его же
    // коллайдер помечает место «Задвинуть» занятым и снап молчит)
    var worldDir = new Vector3(0.45f, -1f, 0.35f).normalized;
    cam.transform.SetPositionAndRotation(target - worldDir * 3f, Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new Vector3(cursor.x, cursor.y, 0f)).direction;
    cam.transform.rotation = Quaternion.FromToRotation(localDir, worldDir);
    cam.transform.position = target - cam.ScreenPointToRay(new Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
    var args = new object[] { chair.Def, cam, mouse, chair.gameObject, chair.transform, 0f, null, null, null };
    bool ok = (bool)mPose.Invoke(gc, args);
    var pos = (Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
    var fLabel = T.GetField("_seatLabel", B); var fHost = T.GetField("_seatHost", B);
    sb.Append("снап: ok=" + ok + " поза=" + pos.ToString("0.00") + " yaw=" + yaw.ToString("0") + " blocked=" + blocked
        + " метка=" + (fLabel != null ? (fLabel.GetValue(gc) as string) : "?") + " хозяин=" + (fHost != null && fHost.GetValue(gc) != null) + "\n");
    chair.transform.SetPositionAndRotation(new Vector3(pos.x, savedChair.y, pos.z), Quaternion.Euler(0f, yaw, 0f));
    Physics.SyncTransforms();
    player.transform.position = savedPlayer;
    sb.Append(Cozy.Grid.SitFeature.Explain(chair) + "\n");
    Cozy.Grid.FeatureHost.Get<Cozy.Grid.SitFeature>(chair).Enter();
    sb.Append("seated=" + Cozy.Grid.SitFeature.PlayerSeated + " clip=" + Cozy.Grid.SitFeature.Clip + "\n");
}
finally
{
    cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
}
System.IO.File.WriteAllText("/tmp/sit_snap_state.txt", savedChair.x + " " + savedChair.y + " " + savedChair.z + " " + savedYaw.eulerAngles.y);
return sb.ToString();
