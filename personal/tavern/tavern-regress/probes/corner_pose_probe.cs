if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var player = Cozy.Grid.PlayerRef.GameObject;
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPlayer = player.transform.position;
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var sb = new System.Text.StringBuilder();
UnityEngine.GameObject body = null;
var hidden = new System.Collections.Generic.List<UnityEngine.GameObject>();
try {
  foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.Def != null && (io.Def.id == "home_wall_cabinet_corner" || io.Def.id == "home_under_light_corner")) hidden.Add(io.gameObject);
  foreach (var go in hidden) go.SetActive(false);
  UnityEngine.Physics.SyncTransforms();
  var def = Cozy.Grid.FurnitureCatalog.ById("home_wall_cabinet_corner");
  body = new UnityEngine.GameObject("PoseProbe");
  body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
  player.transform.position = new UnityEngine.Vector3(-12.3f, 0f, -12.3f);
  UnityEngine.Physics.SyncTransforms();
  var cases = new object[][] {
    new object[] { "east wall near corner", new UnityEngine.Vector3(-10.66f, 2.4f, -11.6f), new UnityEngine.Vector3(1f, -0.35f, 0.1f) },
    new object[] { "east wall far", new UnityEngine.Vector3(-10.66f, 2.4f, -12.4f), new UnityEngine.Vector3(1f, -0.35f, 0.1f) },
    new object[] { "north wall near corner", new UnityEngine.Vector3(-11.6f, 2.4f, -10.66f), new UnityEngine.Vector3(0.1f, -0.35f, 1f) },
    new object[] { "north wall far", new UnityEngine.Vector3(-12.4f, 2.4f, -10.66f), new UnityEngine.Vector3(0.1f, -0.35f, 1f) },
  };
  foreach (var c in cases) {
    var target = (UnityEngine.Vector3)c[1];
    var worldDir = ((UnityEngine.Vector3)c[2]).normalized;
    cam.transform.SetPositionAndRotation(target - worldDir * 3f, UnityEngine.Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
    var args = new object[]{ def, cam, mouse, body, body.transform, 0f, null, null, null };
    bool ok = (bool)mPose.Invoke(gc, args);
    var pos = (UnityEngine.Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
    var wb = body.GetComponentInChildren<UnityEngine.Renderer>().bounds;
    foreach (var r in body.GetComponentsInChildren<UnityEngine.Renderer>()) wb.Encapsulate(r.bounds);
    sb.Append((string)c[0] + ": ok=" + ok + " pos=" + pos.ToString("F2") + " yaw=" + yaw.ToString("F0") + " " + (blocked ? "блок" : "ок") + " bounds=" + wb.min.ToString("F2") + ".." + wb.max.ToString("F2") + "\n");
  }
} finally {
  if (body != null) UnityEngine.Object.Destroy(body);
  foreach (var go in hidden) go.SetActive(true);
  player.transform.position = savedPlayer;
  cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
  UnityEngine.Physics.SyncTransforms();
}
return sb.ToString();
