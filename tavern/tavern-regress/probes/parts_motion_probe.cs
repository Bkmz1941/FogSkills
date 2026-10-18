// ХОД ЧАСТЕЙ В МИРЕ (18.10, P-грабля угловой тумбы). Для execute_code в play, ничего не двигает:
// по каждому объекту уровня с частями (`parts`) берёт closed/open из InteractiveObject._moving и
// переводит ход в мировые оси. Правила:
//  1) ящик (Slide, подпись с «Ящик») едет ГОРИЗОНТАЛЬНО (|dy| ≤ 15 % хода) и НАРУЖУ от центра корпуса, ход ≥ 10 см;
//  2) дверца на петле (Rotate, узел *Door*, кроме духовки *Oven*) вращается вокруг ВЕРТИКАЛИ (|ось·up| ≥ 0,9).
// Вывод: «PARTS ok/FAIL», нарушения, число проверенных частей по видам (по одному экземпляру на деф).
if (!Application.isPlaying) return "не в play";
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public;
var fMoving = typeof(Cozy.Grid.InteractiveObject).GetField("_moving", F);
var bad = new System.Collections.Generic.List<string>();
var seen = new System.Collections.Generic.HashSet<string>();
int drawers = 0, doors = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All) {
  if (io == null || io.Def == null || io.Def.parts == null || io.Def.parts.Count == 0 || !seen.Add(io.Def.id)) continue;
  var list = fMoving.GetValue(io) as System.Collections.IList;
  if (list == null) continue;
  var body = new Bounds(io.transform.position, Vector3.zero); bool first = true;
  foreach (var r in io.GetComponentsInChildren<Renderer>()) { if (first) { body = r.bounds; first = false; } else body.Encapsulate(r.bounds); }
  foreach (var m in list) {
    var t = m.GetType();
    var tf = t.GetField("tf").GetValue(m) as Transform;
    if (tf == null || tf.parent == null) continue;
    bool rotate = (bool)t.GetField("rotate").GetValue(m);
    bool swap = (bool)(t.GetField("swap") != null ? t.GetField("swap").GetValue(m) : false);
    if (swap) continue;
    string label = "";
    foreach (var p in io.Def.parts) if (p.node == tf.name) { label = (p.label ?? "").ToLowerInvariant(); break; }
    string key = io.Def.id + "/" + tf.name;
    if (!rotate) {
      if (!label.Contains("ящик")) continue;
      drawers++;
      var d = tf.parent.TransformVector((Vector3)t.GetField("openPos").GetValue(m) - (Vector3)t.GetField("closedPos").GetValue(m));
      var flat = new Vector3(d.x, 0f, d.z);
      var fromCenter = new Vector3(tf.position.x - body.center.x, 0f, tf.position.z - body.center.z);
      if (d.magnitude < 0.1f) bad.Add(key + ": ход " + d.magnitude.ToString("0.00") + " м");
      else if (Mathf.Abs(d.y) > 0.15f * d.magnitude) bad.Add(key + ": ящик едет по вертикали dy=" + d.y.ToString("0.00") + " при ходе " + d.magnitude.ToString("0.00"));
      else if (fromCenter.sqrMagnitude > 0.01f && Vector3.Dot(flat, fromCenter) < 0f && Vector3.Dot(flat.normalized, io.transform.forward) > -0.5f) bad.Add(key + ": ящик едет внутрь корпуса");
    } else {
      if (!tf.name.Contains("Door") || tf.name.Contains("Oven")) continue;
      doors++;
      var axis = (Vector3)t.GetField("axis").GetValue(m);
      var world = tf.parent.TransformDirection((Quaternion)t.GetField("closedRot").GetValue(m) * axis).normalized;
      if (Mathf.Abs(Vector3.Dot(world, Vector3.up)) < 0.9f) bad.Add(key + ": петля не вертикальна, ось " + world.ToString("0.00"));
    }
  }
}
return (bad.Count == 0 ? "PARTS ok" : "PARTS FAIL") + " :: ящиков " + drawers + ", дверец " + doors + " (по экземпляру на деф)" + (bad.Count > 0 ? " :: " + string.Join("; ", bad.ToArray()) : "");
