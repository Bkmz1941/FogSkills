// ЗАМЕР ПОСТАНОВКИ. Для Unity MCP execute_code (в play).
// Гоняет настоящую GridCursor.ComputeObjectPose по сетке точек для набора
// объектов и пишет «id|точка|нашлось|поза|поворот|вердикт».
if (!Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mPose = T.GetMethod("ComputeObjectPose", B);
var player = Cozy.Grid.PlayerRef.GameObject;
var cam = Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPlayer = player.transform.position;
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var lines = new System.Collections.Generic.List<string>();
var ids = new string[]{ "plate", "coffee_cup_red", "frying_pan", "home_kitchen_chair", "home_wall_cabinet", "home_stove" };
GameObject body = null;
try {
  var anchor = new Vector3(-11.3f, 0f, -14.5f);          // центр области замера
  player.transform.position = anchor + new Vector3(1.2f, 0f, 1.2f);
  Physics.SyncTransforms();
  foreach (var id in ids) {
    var def = Cozy.Grid.FurnitureCatalog.ById(id);
    if (def == null) { lines.Add(id + "|НЕТ В КАТАЛОГЕ"); continue; }
    body = new GameObject("PoseProbe");
    body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
    for (int ix = 0; ix < 7; ix++) for (int iz = 0; iz < 7; iz++) for (int iy = 0; iy < 3; iy++) {
      var target = anchor + new Vector3(-1.2f + ix * 0.4f, iy * 0.9f, -1.2f + iz * 0.4f);
      var worldDir = new Vector3(0.45f, -1f, 0.35f).normalized;
      cam.transform.SetPositionAndRotation(target - worldDir * 3f, Quaternion.identity);
      var localDir = cam.ScreenPointToRay(new Vector3(cursor.x, cursor.y, 0f)).direction;
      cam.transform.rotation = Quaternion.FromToRotation(localDir, worldDir);
      cam.transform.position = target - cam.ScreenPointToRay(new Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
      var args = new object[]{ def, cam, mouse, body, body.transform, 0f, null, null, null };
      bool ok = (bool)mPose.Invoke(gc, args);
      var pos = (Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
      lines.Add(id + "|" + ix + "," + iy + "," + iz + "|" + (ok ? "1" : "0") + "|"
        + pos.x.ToString("0.000") + "," + pos.y.ToString("0.000") + "," + pos.z.ToString("0.000")
        + "|" + yaw.ToString("0.0") + "|" + (blocked ? "блок" : "ок"));
    }
    UnityEngine.Object.DestroyImmediate(body); body = null;
  }
} finally {
  if (body != null) UnityEngine.Object.DestroyImmediate(body);
  player.transform.position = savedPlayer;
  cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
  Physics.SyncTransforms();
}
System.IO.File.WriteAllLines("/tmp/pose_before.txt", lines.ToArray());
return "проб: " + lines.Count;
