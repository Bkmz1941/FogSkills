// Проба «мелочь кладётся на настил причала» (P1287): в play через execute_code (codedom, C# 6), тело без
// строк-комментариев. Для первого причала/мостков (stepOffNode) берёт точки настила по оси рукава и гонит
// конвейер постановки без мыши: ResolveHeight → FloatOnWater → ValidatePose на настоящем призраке
// (_pendingObject + EnsureFurnGhost) для фотоаппарата, молотка (Surface) и фото (плавучее, floatDraft).
// Ожидание: y = верх настила (не уровень воды), blocked=False, trace пустой (ни «step», ни «water»).
var asms = System.AppDomain.CurrentDomain.GetAssemblies();
System.Type ioT = null, gcT = null, fcT = null;
var all = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Instance;
foreach (var a in asms) { System.Type[] ts; try { ts = a.GetTypes(); } catch (System.Exception) { continue; } foreach (var t in ts) { if (t.FullName == "Cozy.Grid.InteractiveObject") ioT = t; if (t.FullName == "Cozy.Grid.GridCursor") gcT = t; if (t.FullName == "Cozy.Grid.FurnitureCatalog") fcT = t; } }
var cursor = UnityEngine.Object.FindObjectsByType(gcT, FindObjectsSortMode.None)[0];
var sb = new System.Text.StringBuilder();
Component deckObj = null; string deckId = "";
foreach (var o in (System.Collections.IEnumerable)ioT.GetField("All", all).GetValue(null))
{
    var c = o as Component; if (c == null) continue;
    var def = ioT.GetProperty("Def", all).GetValue(c, null); if (def == null) continue;
    if (string.IsNullOrEmpty((string)def.GetType().GetField("stepOffNode").GetValue(def))) continue;
    string id = (string)def.GetType().GetField("id").GetValue(def);
    if (deckObj == null || id.StartsWith("old_dock")) { deckObj = c; deckId = id; }
}
if (deckObj == null) return "FAIL: нет причала/мостков на уровне";
var byId = fcT.GetMethod("ById", all);
var pwT = gcT.GetNestedType("PoseWork", all);
var validate = gcT.GetMethod("ValidatePose", all);
var floatW = gcT.GetMethod("FloatOnWater", all);
var resolve = gcT.GetMethod("ResolveHeight", all);
var pendingF = gcT.GetField("_pendingObject", all);
var ghostF = gcT.GetField("_furnGhost", all);
var ensure = gcT.GetMethod("EnsureFurnGhost", all);
var traceF = gcT.GetField("TracePoses", all);
var vtF = gcT.GetField("ValidateTrace", all);
traceF.SetValue(null, true);
int fails = 0;
foreach (string id in new string[] { "photo_camera", "old_hammer", "photo_anna_4" })
{
    var def = byId.Invoke(null, new object[] { id });
    if (def == null) { sb.Append(id + ": нет дефа; "); continue; }
    pendingF.SetValue(cursor, def);
    ensure.Invoke(cursor, null);
    var ghost = ghostF.GetValue(cursor) as GameObject;
    if (ghost == null) { sb.Append(id + ": нет призрака; "); continue; }
    ghost.SetActive(true);
    foreach (int dz in new int[] { 2, -7 })
    {
        var top = deckObj.transform.TransformPoint(new Vector3(0f, 0f, dz)) + Vector3.up * 3f;
        Vector3 pt = Vector3.zero; bool found = false;
        foreach (var h in Physics.RaycastAll(top, Vector3.down, 6f, ~0, QueryTriggerInteraction.Ignore))
            if (h.collider.transform.IsChildOf(deckObj.transform) && (!found || h.point.y > pt.y)) { pt = h.point; found = true; }
        if (!found) { sb.Append(id + " dz" + dz + ": нет настила; "); continue; }
        var rargs = new object[] { def, pt.x, pt.z, 0f, 0f, pt, null, false, false };
        float y = (float)resolve.Invoke(cursor, rargs);
        object w = System.Activator.CreateInstance(pwT);
        pwT.GetField("Def").SetValue(w, def); pwT.GetField("Body").SetValue(w, ghost);
        pwT.GetField("Hit").SetValue(w, pt); pwT.GetField("Probe").SetValue(w, pt);
        pwT.GetField("FloorY").SetValue(w, 0f); pwT.GetField("X").SetValue(w, pt.x); pwT.GetField("Z").SetValue(w, pt.z); pwT.GetField("Y").SetValue(w, y);
        pwT.GetField("Free").SetValue(w, (bool)def.GetType().GetProperty("FreeYaw").GetValue(def, null));
        pwT.GetField("Blocked").SetValue(w, (bool)rargs[8]);
        var fargs = new object[] { w }; floatW.Invoke(cursor, fargs); w = fargs[0];
        var vargs = new object[] { w }; validate.Invoke(cursor, vargs); w = vargs[0];
        bool blocked = (bool)pwT.GetField("Blocked").GetValue(w); float yv = (float)pwT.GetField("Y").GetValue(w);
        bool ok = !blocked && Mathf.Abs(yv - pt.y) < 0.08f;
        if (!ok) fails++;
        sb.Append(id + " dz" + dz + ": y=" + yv.ToString("0.00") + " настил=" + pt.y.ToString("0.00") + " blocked=" + blocked + " [" + (string)vtF.GetValue(null) + "] " + (ok ? "PASS" : "FAIL") + "; ");
    }
    ghost.SetActive(false);
}
traceF.SetValue(null, false);
pendingF.SetValue(cursor, null);
return deckId + ": " + (fails == 0 ? "PASS" : "FAIL " + fails) + " — " + sb.ToString();
