// window_plinth_probe.cs — свой плинтус окна и двери там, где по линии нет стен (витрины ларька, 02.11, P1288, инв. 664).
// Play, уровень «Котедж 104» (ларёк 1 × 2 клетки: восточная сторона — две витрины, южная — дверь во всю клетку).
// Что меряет:
//  1) у витрин соседей-стен по линии нет и кусков плинтуса под ними нет (зеркалить нечего — старое поведение);
//  2) свой флаг внутрь (витрина !spansX → B = −X, face 1; дверь spansX → A = +Z, face 2) → RefreshPlinth → под каждой
//     пьесой есть куски PlinthPiece с owner = пьеса и этой гранью, span = true, низ у пола;
//  3) полоса инструмента от пьесы (GridCursor.CollectPlinthStrip) — сама пьеса и только она;
//  4) флаг снят → куски исчезли. Побочных эффектов нет: флаги возвращаются как были.
// Запуск: execute_code (codedom) — комментарии срезать: grep -v '^//' window_plinth_probe.cs.
var sb = new System.Text.StringBuilder();
int bad = 0;
System.Type wpType = null, dpType = null, ppType = null, gcType = null;
foreach (var a in System.AppDomain.CurrentDomain.GetAssemblies())
{
    if (wpType == null) wpType = a.GetType("Cozy.Grid.WindowPiece");
    if (dpType == null) dpType = a.GetType("Cozy.Grid.DoorPiece");
    if (ppType == null) ppType = a.GetType("Cozy.Grid.PlinthPiece");
    if (gcType == null) gcType = a.GetType("Cozy.Grid.GridCursor");
}
if (!Application.isPlaying || wpType == null) return "НЕЧЕГО ПРОВЕРЯТЬ: play=" + Application.isPlaying;
var ppAll = (System.Collections.IList)ppType.GetField("All").GetValue(null);
var ownerF = ppType.GetField("owner"); var faceF = ppType.GetField("face"); var spanF = ppType.GetField("span");
System.Func<Component, int, int> count = (o, f) => { int n = 0; foreach (var p in ppAll) { if (p == null) continue; if ((Component)ownerF.GetValue(p) == o && (int)faceF.GetValue(p) == f && (bool)spanF.GetValue(p)) n++; } return n; };
var cursor = UnityEngine.Object.FindFirstObjectByType(gcType) as Component;
var strip = gcType.GetMethod("CollectPlinthStrip", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
var listType = typeof(System.Collections.Generic.List<>).MakeGenericType(typeof(System.ValueTuple<Component, int>));
var plinthF_w = wpType.GetField("plinth"); var plinthF_d = dpType.GetField("plinth");
var refresh_w = wpType.GetMethod("RefreshPlinth"); var refresh_d = dpType.GetMethod("RefreshPlinth");
var styleF = wpType.GetField("style");
var pieces = new System.Collections.Generic.List<Component>();
var faces = new System.Collections.Generic.List<int>();
var sideA = new System.Collections.Generic.List<bool>();
foreach (var o in UnityEngine.Object.FindObjectsByType(wpType, FindObjectsSortMode.None))
{
    var c = (Component)o;
    if (!styleF.GetValue(c).ToString().StartsWith("KioskShowcase")) continue;
    pieces.Add(c); faces.Add(1); sideA.Add(false);     // витрина !spansX: внутрь ларька −X = B = face 1
}
foreach (var o in UnityEngine.Object.FindObjectsByType(dpType, FindObjectsSortMode.None))
{
    var c = (Component)o;
    if (Mathf.Abs(c.transform.position.x - 135f) > 0.3f || Mathf.Abs(c.transform.position.z - 49.5f) > 0.3f) continue;
    pieces.Add(c); faces.Add(2); sideA.Add(true);      // дверь spansX: внутрь +Z = A = face 2
}
if (pieces.Count < 3) return "НЕЧЕГО ПРОВЕРЯТЬ: пьес ларька " + pieces.Count + " (нужны 2 витрины + дверь на «Котедж 104»)";
for (int i = 0; i < pieces.Count; i++)
{
    var c = pieces[i]; int face = faces[i]; bool isWin = c.GetType() == wpType;
    var pf = isWin ? plinthF_w : plinthF_d; var rf = isWin ? refresh_w : refresh_d;
    object saved = pf.GetValue(c);
    int before = count(c, face);
    if (before != 0) { bad++; sb.Append("ПЛОХО: у " + c.name + " уже " + before + " своих кусков до флага\n"); }
    // 2) свой флаг
    object pl = pf.GetValue(c);
    pl.GetType().GetField(sideA[i] ? "a" : "b").SetValue(pl, true);
    pf.SetValue(c, pl);
    rf.Invoke(c, null);
    int made = count(c, face);
    float lowest = 99f;
    foreach (var p in ppAll) { if (p == null) continue; if ((Component)ownerF.GetValue(p) == c && (int)faceF.GetValue(p) == face) lowest = Mathf.Min(lowest, ((Component)p).GetComponent<Renderer>().bounds.min.y); }
    bool ok = made > 0 && Mathf.Abs(lowest - c.transform.position.y) < 0.05f;
    if (!ok) bad++;
    sb.Append((ok ? "ок" : "ПЛОХО") + ": " + c.name + " " + c.transform.position.ToString("F1") + " face " + face + " → кусков " + made + ", низ " + lowest.ToString("F3") + "\n");
    // 3) полоса инструмента — сама пьеса
    if (cursor != null && strip != null)
    {
        var into = System.Activator.CreateInstance(listType);
        var args = new object[] { c, face, into, false, false, false, 0f, 0f, 0f, 0f, 0f };
        bool got = (bool)strip.Invoke(cursor, args);
        int n = (int)listType.GetProperty("Count").GetValue(into, null);
        float aMin = (float)args[8], aMax = (float)args[9];
        bool okStrip = got && n == 1 && Mathf.Abs(aMax - aMin) < 0.01f;
        if (!okStrip) bad++;
        sb.Append((okStrip ? "ок" : "ПЛОХО") + ": полоса от " + c.name + " — " + n + " носитель, длина " + (aMax - aMin + 3f).ToString("F1") + "\n");
    }
    // 4) снять. Destroy кусков отложен до конца кадра (PlinthPiece.All их ещё держит) — смотрим списки пьесы,
    //    они чистятся сразу: _sillPlinths[сторона] у окна, _stubPlinths[i] у двери (i чётный = сторона A).
    pf.SetValue(c, saved);
    rf.Invoke(c, null);
    var listF = c.GetType().GetField(isWin ? "_sillPlinths" : "_stubPlinths", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
    var lists = (System.Array)listF.GetValue(c);
    int after = 0;
    for (int k = 0; k < lists.Length; k++) { bool la = isWin ? k == 0 : (k & 1) == 0; if (la == sideA[i]) after += ((System.Collections.ICollection)lists.GetValue(k)).Count; }
    if (after != 0) { bad++; sb.Append("ПЛОХО: после снятия флага у " + c.name + " в списке осталось " + after + "\n"); }
}
int mirrored = 0;
foreach (var p in ppAll) { if (p == null) continue; var ow = ownerF.GetValue(p) as Component; if (ow != null && (bool)spanF.GetValue(p) && ow.GetType() != wpType && ow.GetType() != dpType) mirrored++; }
sb.Append("справочно: кусков под проёмами с зеркалом стены-соседа на уровне " + mirrored + "\n");
sb.Append(bad == 0 ? "PASS" : "FAIL " + bad);
return sb.ToString();
