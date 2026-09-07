if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public;
var mPose = T.GetMethod("ComputeObjectPose", B);
System.Reflection.MethodInfo mSpawn = null;
foreach (var m in T.GetMethods(B)) if (m.Name == "SpawnObject") { mSpawn = m; break; }
var player = Cozy.Grid.PlayerRef.GameObject;
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPlayer = player.transform.position;
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var sb = new System.Text.StringBuilder();
UnityEngine.GameObject body = null;
UnityEngine.GameObject spawned = null;
Cozy.Grid.InteractiveObject bodyIo = null;
try {
  player.transform.position = new UnityEngine.Vector3(-13.0f, 0f, -12.3f);
  UnityEngine.Physics.SyncTransforms();
  var cab = Cozy.Grid.FurnitureCatalog.ById("home_wall_cabinet");
  var io = mSpawn.Invoke(gc, new object[] { cab, new UnityEngine.Vector3(-13.15f, 2.05f, -10.98f), 0f }) as Cozy.Grid.InteractiveObject;
  spawned = io.gameObject;
  UnityEngine.Physics.SyncTransforms();
  var lamp = Cozy.Grid.FurnitureCatalog.ById("home_under_light");
  body = new UnityEngine.GameObject("PoseProbe");
  bodyIo = body.AddComponent<Cozy.Grid.InteractiveObject>();
  bodyIo.Build(lamp);
  Cozy.Grid.InteractiveObject.All.Remove(bodyIo);
  var worldDir = new UnityEngine.Vector3(0.1f, -0.35f, 1f).normalized;
  foreach (var target in new UnityEngine.Vector3[] { new UnityEngine.Vector3(-13.1f, 2.0f, -10.75f), new UnityEngine.Vector3(-12.5f, 2.0f, -10.75f), new UnityEngine.Vector3(-13.9f, 2.0f, -10.75f) }) {
    cam.transform.SetPositionAndRotation(target - worldDir * 3f, UnityEngine.Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
    var args = new object[]{ lamp, cam, mouse, body, body.transform, 0f, null, null, null };
    bool ok = (bool)mPose.Invoke(gc, args);
    var pos = (UnityEngine.Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
    sb.Append("lamp target=" + target.ToString("F2") + " ok=" + ok + " pos=" + pos.ToString("F3") + " yaw=" + yaw.ToString("F0") + " " + (blocked ? "блок" : "ок") + "\n");
  }
} finally {
  if (body != null) UnityEngine.Object.Destroy(body);
  if (spawned != null) UnityEngine.Object.Destroy(spawned);
  player.transform.position = savedPlayer;
  cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
  UnityEngine.Physics.SyncTransforms();
}
return sb.ToString();
