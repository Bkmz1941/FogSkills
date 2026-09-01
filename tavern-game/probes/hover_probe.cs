// ЗАМЕР НАВЕДЕНИЯ. Для Unity MCP execute_code (в play).
// Гоняет настоящий Interactor.Raycast по каждому объекту сцены с четырёх
// ракурсов, в осмотре и вне его. Пишет строки «id|угол|режим|что навелось».
// Путь файла поменяй под свою сессию.
if (!Application.isPlaying) return "не в play";
var t = typeof(Cozy.Grid.Interactor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var rayM = t.GetMethod("Raycast", B);
var inter = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.Interactor>();
// ExamineHost с 30.08 — свойство; запасной путь на случай отката к полю.
var hostP = t.GetProperty("ExamineHost", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
var hostF = hostP == null ? t.GetField("ExamineHost") : null;
var muteF = t.GetField("MuteObjectHighlight");
System.Action<object> setHost = v => { if (hostP != null) hostP.SetValue(null, v); else hostF.SetValue(null, v); };
object savedHost = hostP != null ? hostP.GetValue(null) : hostF.GetValue(null);
var player = Cozy.Grid.PlayerRef.GameObject;
var cam = Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();          // мышь НЕ двигаем — двигаем камеру
var savedMute = muteF.GetValue(null);
var savedPlayer = player.transform.position;
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var lines = new System.Collections.Generic.List<string>();
try {
  var targets = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
  foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def != null) targets.Add(io);
  targets.Sort((a, b2) => string.CompareOrdinal(a.Def.id + a.transform.position.ToString("0.00"),
                                                b2.Def.id + b2.transform.position.ToString("0.00")));
  var dirs = new Vector3[]{ new Vector3(0.6f,-1f,-0.2f), new Vector3(-0.55f,-1f,0.45f),
                            new Vector3(0f,-1f,0.9f), new Vector3(0.4f,-1.4f,0.4f) };
  foreach (var io in targets) {
    var rends = io.GetComponentsInChildren<Renderer>();
    if (rends.Length == 0) continue;
    var bb = rends[0].bounds; foreach (var r in rends) bb.Encapsulate(r.bounds);
    player.transform.position = new Vector3(bb.center.x, savedPlayer.y, bb.center.z) + new Vector3(0f, 0f, -1.0f);
    Physics.SyncTransforms();
    for (int d = 0; d < dirs.Length; d++) {
      var worldDir = dirs[d].normalized;
      // Разворот камеры так, чтобы луч ЧЕРЕЗ РЕАЛЬНЫЙ КУРСОР шёл в цель.
      cam.transform.SetPositionAndRotation(bb.center - worldDir * 2.5f, Quaternion.identity);
      var localDir = cam.ScreenPointToRay(new Vector3(cursor.x, cursor.y, 0f)).direction;
      cam.transform.rotation = Quaternion.FromToRotation(localDir, worldDir);
      cam.transform.position = bb.center - cam.ScreenPointToRay(new Vector3(cursor.x, cursor.y, 0f)).direction * 2.5f;
      foreach (var mode in new int[]{ 0, 1 }) {
        setHost(mode == 1 ? io : null);
        muteF.SetValue(null, mode == 1);
        var hit = rayM.Invoke(inter, new object[]{ mouse }) as Cozy.Grid.IInteractable;
        var hio = hit as Cozy.Grid.InteractiveObject;
        lines.Add(io.Def.id + "|угол" + d + "|осмотр" + mode + "|"
          + (hit == null ? "-" : (hio != null && hio.Def != null ? hio.Def.id : hit.GetType().Name)));
      }
    }
  }
} finally {
  setHost(savedHost); muteF.SetValue(null, savedMute);
  player.transform.position = savedPlayer;
  cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot);
  Physics.SyncTransforms();
}
System.IO.File.WriteAllLines("/tmp/hover_before.txt", lines.ToArray());
return "проб: " + lines.Count;
