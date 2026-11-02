var gc = Cozy.Grid.GridCursor.I;
var t = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
var cam = Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var fPend = t.GetField("_pendingObject", bf); var fGhost = t.GetField("_furnGhost", bf);
if (fPend.GetValue(gc) != null) return "что-то уже ставится";
var fTrace = t.GetField("TracePoses", bf | System.Reflection.BindingFlags.Static);
fTrace.SetValue(null, true);
var sb = new System.Text.StringBuilder();
var p = Cozy.Grid.PlayerRef.Transform.position;
var savedRot = cam.transform.rotation;
var ground = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
foreach (var id in new[]{"cardboard_box","photo_print","flashlight"})
{
  var def = Cozy.Grid.FurnitureCatalog.ById(id);
  if (def == null) { sb.Append(id + ": нет дефа\n"); continue; }
  fPend.SetValue(gc, def);
  t.GetMethod("EnsureFurnGhost", bf).Invoke(gc, null);
  var body = (GameObject)fGhost.GetValue(gc);
  foreach (var off in new[]{ new Vector3(1.5f,0,1.5f), new Vector3(-1.5f,0,1f) })
  {
    var target = new Vector3(p.x + off.x, -0.4f, p.z + off.z);
    var subs = new System.Collections.Generic.Dictionary<Vector2Int,int>();
    target.y = ground.transform.position.y + Cozy.Grid.GridView.SurfaceAt(ground.Heights, ground.Origin, ground.CellSize, target.x, target.z, subs);
    var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
    cam.transform.rotation = Quaternion.FromToRotation(ray.direction, (target - cam.transform.position).normalized) * cam.transform.rotation;
    var args = new object[]{ def, cam, mouse, body, null, 0f, null, null, null };
    bool ok = (bool)t.GetMethod("ComputeObjectPose", bf).Invoke(gc, args);
    var pos = (Vector3)args[6];
    body.transform.position = pos; Physics.SyncTransforms();
    float minY = float.MaxValue; foreach (var r in body.GetComponentsInChildren<Renderer>()) minY = Mathf.Min(minY, r.bounds.min.y);
    sb.AppendFormat("{0} target={1} ok={2} pos={3} blocked={4} bottom={5:F3} groundAt={6:F3}\n  trace={7}\n", id, target.ToString("F2"), ok, pos.ToString("F3"), args[8], minY, target.y, t.GetField("LastPoseTrace", bf | System.Reflection.BindingFlags.Static).GetValue(null));
    cam.transform.rotation = savedRot;
  }
  t.GetMethod("ClearFurnGhost", bf).Invoke(gc, null);
  fPend.SetValue(gc, null);
}
fTrace.SetValue(null, false);
return sb.ToString();
