// ПРОБА ПОСТАНОВКИ В КОРОБКУ (04.10, P778/P779): настоящий перенос листа на лист внутри открытого
// контейнера с loadsFromTop тем же конвейером, что клик игрока: BeginHandMove → камера над коробкой,
// довёрнутая через настоящий курсор → ComputeObjectPose → ReleaseMoving → ReattachToContainer →
// EndHandMove. Ожидание: blocked=False, низ верхнего = верх нижнего (зазор < 6 мм). Героя телепортирует
// к коробке и возвращает, буклет возвращает на место, коробки над целью поднимает и возвращает.
// Двухфазная: если коробка закрыта — открывает её и просит запустить ещё раз через 2 с (створки едут).
// Для Unity MCP execute_code, только в play. Пропуск честный, если на уровне нет пары буклетов в коробке.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var tgc = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var fMoving = tgc.GetField("_movingObj", bf);
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var player = Cozy.Grid.PlayerRef.GameObject;
if (gc.HandPlacing) return "в руке уже что-то есть — не мешаю";
System.Action<Vector3> aim = delegate (Vector3 target) {
    var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
    var want = (target - cam.transform.position).normalized;
    cam.transform.rotation = Quaternion.FromToRotation(ray.direction, want) * cam.transform.rotation; };
Cozy.Grid.InteractiveObject lower=null, upper=null, box=null;
foreach (var h in Cozy.Grid.InteractiveObject.All) { if (h==null||h.Def==null||h.Container==null||h.Container.Def==null||!h.Container.Def.loadsFromTop||!h.Def.sheet) continue; if (lower==null) lower=h; else if (upper==null && h.Container==lower.Container) upper=h; }
if (lower==null||upper==null) return "ПРОПУСК: на уровне нет двух листов (sheet) в одной коробке loadsFromTop — положи два буклета в картонную коробку";
var lifted = new System.Collections.Generic.List<Transform>();
foreach (var h in Cozy.Grid.InteractiveObject.All) { if (h==null||h.Def==null||h.Def.id!="cardboard_box") continue;
  var wb = h.WorldBounds; var lp = lower.transform.position;
  if (lp.x < wb.min.x || lp.x > wb.max.x || lp.z < wb.min.z || lp.z > wb.max.z) continue;
  if (h.transform.position.y < 0.3f) box = h; else lifted.Add(h.transform); }
if (box == null) return "ПРОПУСК: нет коробки под листом";
var boxAcc = Cozy.Grid.FeatureHost.Get<Cozy.Grid.AccessFeature>(box);
var openKey = "box_place_probe_opened";
bool openedByProbe = System.AppDomain.CurrentDomain.GetData(openKey) is bool ob && ob;
if (boxAcc != null && !boxAcc.Open && !boxAcc.Locked)
{
    boxAcc.SetOpen(true);
    System.AppDomain.CurrentDomain.SetData(openKey, true);
    return "ПОДГОТОВКА: коробка была закрыта — открыл, створки едут; запусти пробу ещё раз через 2 с";
}
foreach (var t in lifted) t.position += Vector3.up * 5f;
Physics.SyncTransforms();
var savedCam = cam.transform.rotation; var savedCamPos = cam.transform.position;
var savedPlayer = player.transform.position;
var savedPos = upper.transform.position; var savedRot = upper.transform.rotation; var savedParent = upper.transform.parent;
var forced = new System.Collections.Generic.List<Renderer>();
foreach (var io in new[]{lower,upper,box}) foreach (var r in io.GetComponentsInChildren<Renderer>()) if (!r.enabled && !Cozy.Grid.InteractHighlight.IsCopy(r)) { r.enabled=true; forced.Add(r); }
var sb = new System.Text.StringBuilder(); bool keep = false;
var fTrace = tgc.GetField("TracePoses", bf | System.Reflection.BindingFlags.Static);
bool oldTrace = fTrace != null && (bool)fTrace.GetValue(null); if (fTrace != null) fTrace.SetValue(null, true);
try {
  Vector3 stand = Vector3.zero; bool found = false; var probeHits = new RaycastHit[32];
  for (int k = 0; k < 16 && !found; k++) {
    float ang = k * 22.5f * Mathf.Deg2Rad; float rad = k < 8 ? 1.1f : 1.4f;
    var pt = box.transform.position + new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang)) * rad;
    int n = Physics.RaycastNonAlloc(new Vector3(pt.x, 2.5f, pt.z), Vector3.down, probeHits, 3f, ~0, QueryTriggerInteraction.Ignore);
    float top = -9f; bool obstacle = false;
    for (int i = 0; i < n; i++) { var h = probeHits[i]; if (Cozy.Grid.RayPick.IsPlayer(h.collider)) continue; if (h.point.y > 0.3f) obstacle = true; else top = Mathf.Max(top, h.point.y); }
    if (!obstacle && top > -0.2f && top < 0.1f) { stand = new Vector3(pt.x, 0f, pt.z); found = true; }
  }
  if (!found) return "нет свободной точки у коробки";
  gc.TeleportPlayerTo(stand); Physics.SyncTransforms();
  float floorY = 0f;
  sb.Append("floorY="+floorY+" player="+player.transform.position.ToString("0.00")+"\n");
  gc.BeginHandMove(upper);
  var mv = fMoving.GetValue(gc); if (mv == null) return "перенос не начался";
  var anchor = mv.GetType().GetProperty("Anchor").GetValue(mv, null) as Transform;
  var lb = lower.WorldBounds;
  var mCompute = tgc.GetMethod("ComputeObjectPose", bf);
  var over = new Vector3(savedPos.x, 2.4f, savedPos.z) - box.transform.forward * 0.5f;
  cam.transform.position = over; cam.transform.LookAt(new Vector3(savedPos.x, 0.1f, savedPos.z));
  var downCam = cam.transform.rotation;
  foreach (var yAim in new[]{ lb.max.y + 0.08f, lb.center.y }) {
    var target = new Vector3(savedPos.x, yAim, savedPos.z);
    aim(target);
    var args = new object[] { upper.Def, cam, mouse, anchor.gameObject, anchor, floorY, null, null, null };
    bool ok = (bool)mCompute.Invoke(gc, args);
    string trace = (string)tgc.GetField("LastPoseTrace", bf | System.Reflection.BindingFlags.Static).GetValue(null);
    sb.Append("цель y="+yAim.ToString("0.000")+": ok="+ok);
    if (ok) { var pos=(Vector3)args[6]; sb.Append(" pos="+pos.ToString("0.000")+" yaw="+((float)args[7]).ToString("0")+" blocked="+args[8]); }
    sb.Append(" trace="+trace+"\n");
    cam.transform.rotation = downCam;
  }
  // финальная постановка по первой цели
  aim(new Vector3(savedPos.x, lb.max.y + 0.08f, savedPos.z));
  var a2 = new object[] { upper.Def, cam, mouse, anchor.gameObject, anchor, floorY, null, null, null };
  if ((bool)mCompute.Invoke(gc, a2) && !(bool)a2[8]) {
    anchor.SetPositionAndRotation((Vector3)a2[6], Quaternion.Euler(0f,(float)a2[7],0f));
    tgc.GetMethod("ReleaseMoving", bf).Invoke(gc, null);
    gc.ReattachToContainer(upper);
    fMoving.SetValue(gc, null);
    tgc.GetMethod("EndHandMove", bf).Invoke(gc, null);
    Physics.SyncTransforms();
    var ub = upper.WorldBounds;
    bool good = (ub.min.y - lb.max.y) < 0.006f && (ub.min.y - lb.max.y) > -0.006f;
    sb.Append(good ? "ОК: лист лёг на лист без зазора и без красного\n" : "КРАСНОЕ: зазор или сдвиг — смотри строки выше\n");
    sb.Append("ПОЛОЖЕН: низ="+ub.min.y.ToString("0.000")+" верх нижнего="+lb.max.y.ToString("0.000")+" зазор="+(ub.min.y-lb.max.y).ToString("0.000")+" parent="+upper.transform.parent.name+" container="+(upper.Container!=null?upper.Container.Def.id:"-")+"\n");
  } else {
    var mCancel = tgc.GetMethod("CancelHandMove", bf); if (mCancel != null) mCancel.Invoke(gc, null);
    sb.Append("КРАСНОЕ: лист над листом в открытой коробке не ставится (blocked) или курсор мимо\n");
  }
} finally {
  if (gc.Carried(upper.transform)) { var mCancel = tgc.GetMethod("CancelHandMove", bf); if (mCancel != null) mCancel.Invoke(gc, null); }
  cam.transform.SetPositionAndRotation(savedCamPos, savedCam);
  if (!keep) { upper.transform.SetParent(savedParent, true); upper.transform.SetPositionAndRotation(savedPos, savedRot); } else sb.Append("ОСТАВЛЕН там, где лёг (пос. "+upper.transform.position.ToString("0.000")+")\n");
  gc.TeleportPlayerTo(savedPlayer); Physics.SyncTransforms();
  foreach (var r in forced) if (r != null) r.enabled = false;
  foreach (var t in lifted) t.position -= Vector3.up * 5f;
  if (openedByProbe && boxAcc != null) { boxAcc.SetOpen(false); System.AppDomain.CurrentDomain.SetData(openKey, null); }
  Physics.SyncTransforms();
  sb.Append("верхних коробок поднимал и вернул: "+lifted.Count+"\n");
  if (fTrace != null) fTrace.SetValue(null, oldTrace);
}
return sb.ToString();
