if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
var furn = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All) { if (io == null || io.Def == null) continue; if (io.Def.mount != Cozy.Grid.ObjectMount.Floor || io.Def.walkOver) continue; furn.Add(io); }
int inside = 0;
foreach (var p in Cozy.Grid.PlinthPiece.All) {
  if (p == null || p.Rend == null) continue;
  var b = p.Rend.bounds;
  foreach (var io in furn) {
    var ob = io.WorldBounds; ob.Expand(-0.01f);
    if (!b.Intersects(ob)) continue;
    inside++;
    sb.Append((p.span ? "ПОД ПРОЁМОМ " : "") + "кусок " + b.center.ToString("F2") + " размер " + b.size.ToString("F2") + " в " + io.Def.id + " " + ob.min.ToString("F2") + ".." + ob.max.ToString("F2") + "\n");
  }
}
sb.Insert(0, "кусков в мебели: " + inside + "\n");
// выключатели: где они и что за спиной
foreach (var io in Cozy.Grid.InteractiveObject.All) {
  if (io == null || io.Def == null) continue;
  if (io.Def.id != "wall_switch" && io.Def.id != "wall_switch_toggle" && io.Def.id != "home_hall_mirror" && io.Def.id != "meter_electric" && io.Def.id != "shelf_plank") continue;
  var back = io.transform.rotation * UnityEngine.Vector3.forward;
  var origin = io.WorldBounds.center;
  UnityEngine.RaycastHit hit; string beh = "ничего";
  if (UnityEngine.Physics.Raycast(origin, back, out hit, 1.0f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) beh = hit.collider.name + " на " + hit.distance.ToString("F3") + " (" + (Cozy.Grid.BuildQuery.WallLike(hit.collider) ? "стена" : "не стена") + ")";
  sb.Append(io.Def.id + " @ " + io.transform.position.ToString("F2") + " yaw " + io.transform.eulerAngles.y.ToString("0") + " за спиной: " + beh + "\n");
}
return sb.ToString();
