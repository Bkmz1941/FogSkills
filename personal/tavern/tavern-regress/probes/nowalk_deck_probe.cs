// Проба «настил в зоне запрета хода» (инв. 631, P1286): в play через execute_code (codedom, C# 6),
// тело вставлять без этих строк-комментариев. Для каждого объекта со stepOffNode (причал Т/Г, мостки)
// ищет точки настила (сетка 1 м по локальным осям, луч вниз), берёт самую дальнюю от центра точку,
// лежащую в зоне NoWalk, и проверяет: на настиле не заблокировано; по четырём направлениям идёт до
// кромки настила (DeckUnder ложь) и за кромкой гонит шаг через оба стража (EdgeGuard.FilterMove +
// ZonePiece.WalkGuard): за кромкой зона → «стоп» обязателен; за кромкой берег без зоны (сторона схода)
// → «идёт» допустим. Ожидание 02.11 на «Котедж 104» (причал Г): к воде — стоп (гасят и кромка, и зона),
// к берегу — идёт, по настилу — свободно. Мостки `env_pier` там в зону не попадают (мелко) — пропуск.
var sb = new System.Text.StringBuilder();
var asms = System.AppDomain.CurrentDomain.GetAssemblies();
System.Type ioT = null, zpT = null, egT = null;
var all = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Instance;
foreach (var a in asms) { System.Type[] ts; try { ts = a.GetTypes(); } catch (System.Exception) { continue; } foreach (var t in ts) { if (t.FullName == "Cozy.Grid.InteractiveObject") ioT = t; if (t.FullName == "Cozy.Grid.ZonePiece") zpT = t; if (t.FullName == "Cozy.Grid.EdgeGuard") egT = t; } }
if (ioT == null || zpT == null || egT == null) return "FAIL types";
var walkBlocked = zpT.GetMethod("WalkBlocked", all);
var walkGuard = zpT.GetMethod("WalkGuard", all);
var filterMove = egT.GetMethod("FilterMove", all);
var deckUnder = egT.GetMethod("DeckUnder", all);
var containsAt = zpT.GetMethod("ContainsAt", all);
if (deckUnder == null) return "FAIL no EdgeGuard.DeckUnder";
var zones = new System.Collections.Generic.List<Component>();
foreach (var z in (System.Collections.IEnumerable)zpT.GetField("All", all).GetValue(null)) { var zc = z as Component; if (zc != null && (int)zpT.GetField("kind", all).GetValue(zc) == 23) zones.Add(zc); }
System.Func<Vector3, bool> inZone = p => { foreach (var zc in zones) if ((bool)containsAt.Invoke(zc, new object[] { p })) return true; return false; };
System.Func<Vector3, bool> deck = p => (bool)deckUnder.Invoke(null, new object[] { p });
int checkedDecks = 0;
foreach (var o in (System.Collections.IEnumerable)ioT.GetField("All", all).GetValue(null))
{
    var c = o as Component; if (c == null) continue;
    var def = ioT.GetProperty("Def", all).GetValue(c, null); if (def == null) continue;
    if (string.IsNullOrEmpty((string)def.GetType().GetField("stepOffNode").GetValue(def))) continue;
    string id = (string)def.GetType().GetField("id").GetValue(def);
    Vector3 best = Vector3.zero; float bestD = -1f; int deckPts = 0, zonePts = 0;
    for (int dz = -9; dz <= 9; dz++) for (int dx = -5; dx <= 5; dx++)
    {
        var top = c.transform.TransformPoint(new Vector3(dx, 0f, dz)) + Vector3.up * 3f;
        Vector3 pt = Vector3.zero; bool found = false;
        foreach (var h in Physics.RaycastAll(top, Vector3.down, 6f, ~0, QueryTriggerInteraction.Ignore))
            if (h.collider.transform.IsChildOf(c.transform) && (!found || h.point.y > pt.y)) { pt = h.point; found = true; }
        if (!found) continue;
        deckPts++;
        var feet = pt + Vector3.up * 0.1f;
        if (!inZone(feet)) continue;
        zonePts++;
        float d = Vector3.Distance(pt, c.transform.position);
        if (d > bestD) { bestD = d; best = feet; }
    }
    if (zonePts == 0) { sb.Append(id + ": точек настила " + deckPts + ", в зоне 0 — пропуск; "); continue; }
    checkedDecks++;
    sb.Append(id + " (" + zonePts + " из " + deckPts + " точек в зоне) проба @" + best.ToString("0.0") + ": на настиле " + ((bool)walkBlocked.Invoke(null, new object[] { best }) ? "FAIL заблокирован" : "PASS свободно") + "; ");
    foreach (var dirRaw in new Vector3[] { c.transform.right, -c.transform.right, c.transform.forward, -c.transform.forward })
    {
        var dir = dirRaw; dir.y = 0f; dir.Normalize();
        Vector3 edge = best; int steps = 0;
        while (steps < 80 && deck(edge + dir * 0.1f)) { edge += dir * 0.1f; steps++; }
        if (steps >= 80) continue;
        var beyond = edge + dir * 0.5f;
        bool beyondZone = inZone(beyond);
        var v1 = (Vector3)filterMove.Invoke(null, new object[] { dir * 2f, edge, 0.55f, 0.02f });
        var v2 = (Vector3)walkGuard.Invoke(null, new object[] { v1, edge, 0.4f, 0.02f });
        bool stop = v2.magnitude < 0.01f;
        sb.Append("кромка " + dir.ToString("0.0") + " @" + edge.ToString("0.0") + " за ней " + (beyondZone ? "вода-зона" : "без зоны") + ": " + (beyondZone ? (stop ? "PASS стоп" : "FAIL идёт") : (stop ? "стоп (кромка)" : "идёт (сход)")) + "; ");
    }
}
if (checkedDecks == 0) sb.Append("FAIL: ни одного настила в зоне NoWalk");
return sb.ToString();
