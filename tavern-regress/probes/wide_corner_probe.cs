if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
var mPose = T.GetMethod("ComputeObjectPose", B);
var mVariant = T.GetMethod("HostVariant", B);
System.Reflection.MethodInfo mSpawn = null;
foreach (var m in T.GetMethods(B)) if (m.Name == "SpawnObject") { mSpawn = m; break; }
var player = Cozy.Grid.PlayerRef.GameObject;
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPlayer = player.transform.position;
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var sb = new System.Text.StringBuilder();
UnityEngine.GameObject body = null; UnityEngine.GameObject spawned = null;
var hidden = new System.Collections.Generic.List<UnityEngine.GameObject>();
try {
  foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.Def != null && (io.Def.id.StartsWith("home_wall_cabinet") || io.Def.id.StartsWith("home_under_light"))) hidden.Add(io.gameObject);
  foreach (var go in hidden) go.SetActive(false);
  player.transform.position = new UnityEngine.Vector3(-13.0f, 0f, -13.0f);
  UnityEngine.Physics.SyncTransforms();
  System.Func<Cozy.Grid.ObjectDef, UnityEngine.Vector3, UnityEngine.Vector3, string> probe = (def, target, dir) => {
    var worldDir = dir.normalized;
    cam.transform.SetPositionAndRotation(target - worldDir * 3f, UnityEngine.Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
    var args = new object[]{ def, cam, mouse, body, body.transform, 0f, null, null, null };
    bool ok = (bool)mPose.Invoke(gc, args);
    var pos = (UnityEngine.Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
    var wb = body.GetComponentInChildren<UnityEngine.Renderer>().bounds;
    foreach (var r in body.GetComponentsInChildren<UnityEngine.Renderer>()) wb.Encapsulate(r.bounds);
    return def.id + " ok=" + ok + " pos=" + pos.ToString("F2") + " yaw=" + yaw.ToString("F0") + " " + (blocked ? "блок" : "ок") + " bounds=" + wb.min.ToString("F2") + ".." + wb.max.ToString("F2");
  };
  var wide = Cozy.Grid.FurnitureCatalog.ById("home_wall_cabinet_corner_wide");
  body = new UnityEngine.GameObject("PoseProbe"); body.AddComponent<Cozy.Grid.InteractiveObject>().Build(wide);
  Cozy.Grid.InteractiveObject.All.Remove(body.GetComponent<Cozy.Grid.InteractiveObject>());
  sb.Append("east: " + probe(wide, new UnityEngine.Vector3(-10.66f, 2.4f, -12.0f), new UnityEngine.Vector3(1f, -0.35f, 0.1f)) + "\n");
  sb.Append("north: " + probe(wide, new UnityEngine.Vector3(-12.0f, 2.4f, -10.66f), new UnityEngine.Vector3(0.1f, -0.35f, 1f)) + "\n");
  UnityEngine.Object.Destroy(body); body = null;
  var io2 = mSpawn.Invoke(gc, new object[] { wide, new UnityEngine.Vector3(-11.93f, 2.05f, -12.63f), 90f }) as Cozy.Grid.InteractiveObject;
  spawned = io2.gameObject;
  UnityEngine.Physics.SyncTransforms();
  var wbs = io2.WorldBounds;
  sb.Append("spawned wide bounds=" + wbs.min.ToString("F2") + ".." + wbs.max.ToString("F2") + " cols=" + io2.GetComponents<UnityEngine.Collider>().Length + " feats=" + io2.Features.Count + "\n");
  foreach (var t in io2.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == "Mount_LightCorner") sb.Append("Mount_LightCorner@" + t.position.ToString("F2") + "\n");
  var straight = Cozy.Grid.FurnitureCatalog.ById("home_under_light");
  var variant = mVariant.Invoke(null, new object[] { straight, "home_wall_cabinet_corner_wide" }) as Cozy.Grid.ObjectDef;
  sb.Append("variant for wide host: " + (variant != null ? variant.id : "null") + "\n");
  var wlamp = Cozy.Grid.FurnitureCatalog.ById("home_under_light_corner_wide");
  body = new UnityEngine.GameObject("PoseProbe"); body.AddComponent<Cozy.Grid.InteractiveObject>().Build(wlamp);
  Cozy.Grid.InteractiveObject.All.Remove(body.GetComponent<Cozy.Grid.InteractiveObject>());
  sb.Append("lamp: " + probe(wlamp, new UnityEngine.Vector3(-10.75f, 2.0f, -12.5f), new UnityEngine.Vector3(1f, -0.35f, 0.1f)) + "\n");
  sb.Append("lamp2: " + probe(wlamp, new UnityEngine.Vector3(-12.5f, 2.0f, -10.75f), new UnityEngine.Vector3(0.1f, -0.35f, 1f)) + "\n");
} finally {
  if (body != null) UnityEngine.Object.Destroy(body);
  if (spawned != null) UnityEngine.Object.Destroy(spawned);
  foreach (var go in hidden) go.SetActive(true);
  player.transform.position = savedPlayer;
  cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
  UnityEngine.Physics.SyncTransforms();
}
return sb.ToString();
