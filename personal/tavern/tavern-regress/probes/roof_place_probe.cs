// Проба «светильники и антенна встают на крышу ларька» (P1289/P1290): play, «Котедж 104», codedom. Конвейер без мыши:
// SurfaceCursorPoint (луч сверху-спереди в верх крыши, этаж 0) → ResolveHeight → ValidatePose на настоящем призраке.
// Ожидание: точка на верху крыши (3,12), y = верх крыши, blocked=False — PASS у четырёх дефов.
// P1292: герой ПОД крышей (внутри ларька) — тот же луч сверху НЕ берёт верх крыши: тетрадь проката ложится внутрь (y < низа крыши).
var asms = System.AppDomain.CurrentDomain.GetAssemblies();
System.Type ioT = null, gcT = null, fcT = null;
var all = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Instance;
foreach (var a in asms) { System.Type[] ts; try { ts = a.GetTypes(); } catch (System.Exception) { continue; } foreach (var t in ts) { if (t.FullName == "Cozy.Grid.InteractiveObject") ioT = t; if (t.FullName == "Cozy.Grid.GridCursor") gcT = t; if (t.FullName == "Cozy.Grid.FurnitureCatalog") fcT = t; } }
if (!Application.isPlaying) return "FAIL: не play";
var cursor = UnityEngine.Object.FindObjectsByType(gcT, FindObjectsSortMode.None)[0];
var sb = new System.Text.StringBuilder();
Component roof = null;
foreach (var o in (System.Collections.IEnumerable)ioT.GetField("All", all).GetValue(null))
{
    var c = o as Component; if (c == null) continue;
    var def = ioT.GetProperty("Def", all).GetValue(c, null); if (def == null) continue;
    if ((string)def.GetType().GetField("id").GetValue(def) == "kiosk_roof") roof = c;
}
if (roof == null) return "FAIL: нет крыши ларька";
var byId = fcT.GetMethod("ById", all);
var pwT = gcT.GetNestedType("PoseWork", all);
var validate = gcT.GetMethod("ValidatePose", all);
var resolve = gcT.GetMethod("ResolveHeight", all);
var surfPt = gcT.GetMethod("SurfaceCursorPoint", all);
var pendingF = gcT.GetField("_pendingObject", all);
var ghostF = gcT.GetField("_furnGhost", all);
var ensure = gcT.GetMethod("EnsureFurnGhost", all);
var traceF = gcT.GetField("TracePoses", all);
var vtF = gcT.GetField("ValidateTrace", all);
traceF.SetValue(null, true);
float floorY = 0f;
var top = roof.transform.position + Vector3.up * 8f;
Vector3 pt = Vector3.zero; bool found = false;
foreach (var h in Physics.RaycastAll(top, Vector3.down, 12f, ~0, QueryTriggerInteraction.Ignore))
    if (h.collider.transform.IsChildOf(roof.transform) && (!found || h.point.y > pt.y)) { pt = h.point; found = true; }
if (!found) return "FAIL: луч не попал в крышу";
sb.Append("roof@" + roof.transform.position + " top=" + pt.y.ToString("0.00") + " floorY=" + floorY + "; ");
int fails = 0;
foreach (string id in new string[] { "kiosk_roof_flood", "kiosk_roof_goose", "kiosk_roof_mast", "kiosk_antenna" })
{
    var def = byId.Invoke(null, new object[] { id });
    if (def == null) { sb.Append(id + ": нет дефа; "); fails++; continue; }
    pendingF.SetValue(cursor, def);
    ensure.Invoke(cursor, null);
    var ghost = ghostF.GetValue(cursor) as GameObject;
    if (ghost == null) { sb.Append(id + ": нет призрака; "); fails++; continue; }
    ghost.SetActive(true);
    var ray = new Ray(pt + new Vector3(0f, 9f, -6f), (pt - (pt + new Vector3(0f, 9f, -6f))).normalized);
    var sargs = new object[] { ray, floorY, null, null };
    bool sOk = (bool)surfPt.Invoke(cursor, sargs);
    Vector3 sp = sOk ? (Vector3)sargs[3] : pt;
    var rargs = new object[] { def, sp.x, sp.z, 0f, 0f, sp, null, false, false };
    float y = (float)resolve.Invoke(cursor, rargs);
    object w = System.Activator.CreateInstance(pwT);
    pwT.GetField("Def").SetValue(w, def); pwT.GetField("Body").SetValue(w, ghost);
    pwT.GetField("Hit").SetValue(w, sp); pwT.GetField("Probe").SetValue(w, sp);
    pwT.GetField("FloorY").SetValue(w, floorY); pwT.GetField("X").SetValue(w, sp.x); pwT.GetField("Z").SetValue(w, sp.z); pwT.GetField("Y").SetValue(w, y);
    pwT.GetField("Free").SetValue(w, (bool)def.GetType().GetProperty("FreeYaw").GetValue(def, null));
    pwT.GetField("Blocked").SetValue(w, (bool)rargs[8]);
    var vargs = new object[] { w }; validate.Invoke(cursor, vargs); w = vargs[0];
    bool blocked = (bool)pwT.GetField("Blocked").GetValue(w); float yv = (float)pwT.GetField("Y").GetValue(w);
    bool ok = sOk && !blocked && Mathf.Abs(yv - pt.y) < 0.15f;
    if (!ok) fails++;
    sb.Append(id + ": surf=" + sOk + " sp.y=" + sp.y.ToString("0.00") + " y=" + yv.ToString("0.00") + " blocked=" + blocked + " [" + (string)vtF.GetValue(null) + "] " + (ok ? "PASS" : "FAIL") + "; ");
    ghost.SetActive(false);
}
var viewT = System.Type.GetType("Cozy.View.ViewState, Cozy.View");
foreach (var a2 in asms) { if (viewT != null) break; viewT = a2.GetType("Cozy.View.ViewState"); }
var ppF = viewT.GetField("PlayerPos", all);
var heroWas = (Vector3)ppF.GetValue(null);
var rb = (Bounds)ioT.GetProperty("WorldBounds", all).GetValue(roof, null);
ppF.SetValue(null, new Vector3(rb.center.x, rb.min.y - 2.5f, rb.center.z));
var book = byId.Invoke(null, new object[] { "rental_book" });
pendingF.SetValue(cursor, book);
var inRay = new Ray(pt + new Vector3(0f, 9f, -6f), (pt - (pt + new Vector3(0f, 9f, -6f))).normalized);
var iargs = new object[] { inRay, floorY, null, null };
bool iOk = (bool)surfPt.Invoke(cursor, iargs);
Vector3 ip = iOk ? (Vector3)iargs[3] : Vector3.zero;
ppF.SetValue(null, heroWas);
bool inside = !iOk || ip.y < rb.min.y - 0.05f;
if (!inside) fails++;
sb.Append("rental_book под крышей: surf=" + iOk + " y=" + ip.y.ToString("0.00") + " (низ крыши " + rb.min.y.ToString("0.00") + ") " + (inside ? "PASS" : "FAIL") + "; ");
traceF.SetValue(null, false);
pendingF.SetValue(cursor, null);
return (fails == 0 ? "PASS" : "FAIL " + fails) + " — " + sb.ToString();
