"""Плинтус и цоколь на открытом уровне: есть, не утоплен в обшивке, не лезет в мебель, ровен у дверей.

python3 plinth_probe.py        замер в play, без побочных эффектов (~2 с)

Что меряется (грабли P478, P492, P499, P501–P505, P536, P538):
1. Куски есть и разложены по этажам: `PlinthPiece.All` непустой, счёт по этажам и граням.
   Пусто — «НЕЧЕГО ПРОВЕРЯТЬ», это не зелёное. Куски на лестницах и под проёмами
   носителя-стены не имеют и в проверки не идут — их счёт печатается справочно.
   Куски ПОД ПРОЁМАМИ (`PlinthPiece.span`, строит `PlinthView.BuildSpan`) вырезов
   мебели не знают по устройству — считаются отдельно и красным не делают,
   починка этого лежит в `tavern-refactor/TARGETS.md`.
2. Не утоплен: вынос куска от грани носителя не меньше замеренного выноса досок
   обшивки той же грани (`PlankSide*`). Утопленный кусок Илья не видит за текстурами.
3. Этаж куска считается так же, как гейт видимости считает свой якорь
   (`floor((y + 0.12) / 3)`): подоконные куски сидят у полутора метров, и
   округление к ближайшему этажу давало то 68/40, то 70/38 на одном и том же доме.
4. Не внутри мебели: габарит куска не пересекает корпус напольной мебели, СТОЯЩЕЙ
   с этой стороны грани (ближний край ближе 0.25 м, центр по внешнюю сторону) —
   иначе открытый ящик тумбы показывает полосу плинтуса внутри себя. Условие
   отбора то же, что у `PlinthView.FreeSpans`, проверяется результат.
5. Ровно у проёмов: у одной двери куски по обе стороны и подпороговый лежат на
   одной глубине (разброс до 5 мм), иначе на стыке ступенька.
6. Вплотную к обшивке (P536): у куска на обшитой грани спинка меша не дальше 3 мм
   от грани носителя — тело плинтуса дотянуто до стены, доски под ним спрятаны
   внутри. Иначе между спинкой и рельефом щель, которую видно сверху.
7. Углы цоколя с митрой (P538): два куска цоколя ОДНОГО стиля, сходящиеся в углу
   (перпендикулярны, концы ближе 0,6 м), оба кончаются косым торцом — у торца меша
   `x` зависит от глубины профиля. Прямой торец хотя бы у одного = стык не
   опознан (`PlinthView.Joins` смотрит не ту грань соседа), в углу выемка или
   наложение. Куски под проёмами не считаются — у них торцы прямые по устройству.
8. Прогон без дыр (P541, инвариант 233): куски цоколя одной линии (одна плоскость,
   один этаж) сортируются вдоль; щель > 5 см между соседями допустима, только если
   в ней стоит дверь (`DoorPiece` в 0,8 м от середины щели) или у грани стоит
   корпус напольной мебели высотой ≥ 0,10 м, накрывающий щель. Иначе «дыра в
   цоколе»: так маркер респавна за стеной (высота 0,05) вырезал метр цоколя —
   плоское на полу линию рвать не должно (`PlinthView.FlatOnFloor`).
10. Без устаревших дыр (P559, инвариант 241): щель > 5 см между соседними кусками ОДНОЙ
   линии плинтуса (любой высоты) обязана объясняться сейчас: дверью, корпусом напольной
   мебели (≥ 0,10 м) в щели, вырезом обшивки на этой грани, отсутствием опоры
   (`PlinthView.SupportedAt`), поперечной стеной в щели (Т-стык) или тем, что у
   несущей стены под щелью флага плинтуса на этой грани нет. Иначе «дыра без причины»: так горшок, стоявший в углу при
   постановке плинтуса, уехал, а вырез под него остался — перенос мебели пересборку не
   поднимал.
11. Опора по отрезкам (P560, инвариант 242): у грани с флагом без единого куска не должно
   быть точки, где опора есть (`PlinthView.SupportedAt` в точке), а мебели, выреза обшивки
   и поперечной стены нет. Раньше опора мерилась по центру блока: стена у верха лестницы
   на 2 этаже оставалась без плинтуса целиком, хотя половина её стояла на проступях.
12. Без огрызков (P560): кусок стены короче 12 см, центр которого лежит в теле стены
   (`BuildQuery.BlockAt` роли Wall), — вырожденный: свободный отрезок у Т-стыка оказался
   короче митры внутреннего угла (вырез под мебель кончился в 9 см от стены), и меш
   строился с отрицательной длиной. Он же торчал «внутри ванны».
9. Без сирот (P553, инвариант 240): у куска стены или куба (`span == false`) владелец
   жив (`PlinthPiece.owner != null`). Снос бетонного блока не поднимал `_wallsDirty`
   (только стена), и его плинтус оставался лежать буквой Г на полу.
"""
import json, subprocess, sys

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var all = Cozy.Grid.PlinthPiece.All;
if (all == null || all.Count == 0) return "НЕЧЕГО ПРОВЕРЯТЬ: на уровне нет кусков плинтуса";
System.Func<int, UnityEngine.Vector3> dirOf = delegate (int f)
{
    if (f == 0) return UnityEngine.Vector3.right;
    if (f == 1) return UnityEngine.Vector3.left;
    if (f == 2) return UnityEngine.Vector3.forward;
    return UnityEngine.Vector3.back;
};
var perFloor = new System.Collections.Generic.Dictionary<int, int>();
var fronts = new System.Collections.Generic.List<float>();
int sunk = 0; float worstSunk = 0f; string worstWhere = "";
int inFurn = 0; string furnWhere = "";
int gaps = 0; float worstGap = 0f; string gapWhere = "";
int noOwner = 0; int spans = 0; int spanInFurn = 0;
var byPiece = new System.Collections.Generic.Dictionary<Cozy.Grid.PlinthPiece, float>();
var furn = new System.Collections.Generic.List<UnityEngine.Bounds>();
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null || io.Def.movable) continue;
    if (io.Def.mount != Cozy.Grid.ObjectMount.Floor) continue;
    furn.Add(io.WorldBounds);
}
foreach (var pc in all)
{
    if (pc == null || pc.Rend == null) continue;
    var gb = pc.owner as Cozy.Grid.GridBlock;
    if (gb == null) { noOwner++; continue; }
    if (pc.span) spans++;
    var outward = dirOf(pc.face);
    bool thinX = UnityEngine.Mathf.Abs(outward.x) > 0.5f;
    float sign = thinX ? UnityEngine.Mathf.Sign(outward.x) : UnityEngine.Mathf.Sign(outward.z);
    var sc = gb.transform.localScale;
    float thick = thinX ? sc.x : sc.z;
    var c = gb.transform.position;
    float facePlane = (thinX ? c.x : c.z) + sign * thick * 0.5f;
    float pcOut = thinX ? pc.transform.position.x : pc.transform.position.z;
    float front = (pcOut - facePlane) * sign;
    byPiece[pc] = front;
    fronts.Add(front);
    int fl = UnityEngine.Mathf.FloorToInt((pc.transform.position.y + 0.12f) / 3f);
    perFloor[fl] = perFloor.ContainsKey(fl) ? perFloor[fl] + 1 : 1;
    float clad = 0f;
    foreach (var t in gb.GetComponentsInChildren<UnityEngine.Transform>(true))
    {
        if (!t.name.StartsWith("PlankSide", System.StringComparison.Ordinal)) continue;
        var rr = t.GetComponent<UnityEngine.Renderer>();
        if (rr == null) continue;
        var bb = rr.bounds;
        float outer = thinX ? (sign > 0f ? bb.max.x : bb.min.x) : (sign > 0f ? bb.max.z : bb.min.z);
        float ahead = (outer - facePlane) * sign;
        if (ahead > clad) clad = ahead;
    }
    if (front < clad - 0.001f)
    {
        sunk++;
        float d = clad - front;
        if (d > worstSunk) { worstSunk = d; worstWhere = "y=" + pc.transform.position.y.ToString("F2") + " грань " + pc.face; }
    }
    var pb = pc.Rend.bounds;
    if (clad > 0.001f)
    {
        float backEdge = thinX ? (sign > 0f ? pb.min.x : pb.max.x) : (sign > 0f ? pb.min.z : pb.max.z);
        float backGap = (backEdge - facePlane) * sign;
        if (backGap > 0.003f)
        {
            gaps++;
            if (backGap > worstGap) { worstGap = backGap; gapWhere = "y=" + pc.transform.position.y.ToString("F2") + " грань " + pc.face; }
        }
    }
    pb.Expand(-0.02f);
    foreach (var fb in furn)
    {
        if (!fb.Intersects(pb)) continue;
        float near = thinX ? (sign > 0f ? fb.min.x : fb.max.x) : (sign > 0f ? fb.min.z : fb.max.z);
        if (UnityEngine.Mathf.Abs(near - facePlane) > 0.25f) continue;
        float side = ((thinX ? fb.center.x : fb.center.z) - facePlane) * sign;
        if (side < 0f) continue;
        if (pc.span) spanInFurn++;
        else
        {
            inFurn++;
            if (furnWhere == "") furnWhere = "y=" + pc.transform.position.y.ToString("F2");
        }
        break;
    }
}
int corners = 0; int cornersStraight = 0; string cornerWhere = "";
var socles = new System.Collections.Generic.List<Cozy.Grid.PlinthPiece>();
var socleKey = new System.Collections.Generic.Dictionary<Cozy.Grid.PlinthPiece, string>();
var ends = new System.Collections.Generic.Dictionary<Cozy.Grid.PlinthPiece, UnityEngine.Vector3>();
foreach (var kv in byPiece)
{
    var pc = kv.Key;
    var gb = pc.owner as Cozy.Grid.GridBlock;
    if (gb == null) continue;
    var sc = gb.transform.localScale;
    int faceA = sc.x < sc.z ? 0 : 2;
    var st = pc.face == faceA ? gb.plinthStyleA : gb.plinthStyleB;
    if (!st.IsSocle) continue;
    var mf = pc.GetComponent<UnityEngine.MeshFilter>();
    if (mf == null || mf.sharedMesh == null) continue;
    float half = 0f, pLo = float.PositiveInfinity, pHi = float.NegativeInfinity, nLo = float.PositiveInfinity, nHi = float.NegativeInfinity;
    foreach (var v in mf.sharedMesh.vertices)
    {
        if (UnityEngine.Mathf.Abs(v.x) > half) half = UnityEngine.Mathf.Abs(v.x);
        if (v.x > 0.001f) { if (v.x < pLo) pLo = v.x; if (v.x > pHi) pHi = v.x; }
        else if (v.x < -0.001f) { if (v.x < nLo) nLo = v.x; if (v.x > nHi) nHi = v.x; }
    }
    socles.Add(pc);
    socleKey[pc] = st.Key.ToString();
    ends[pc] = new UnityEngine.Vector3(half, pHi - pLo > 0.002f ? 1f : 0f, nHi - nLo > 0.002f ? 1f : 0f);
}
for (int i = 0; i < socles.Count; i++)
    for (int j = i + 1; j < socles.Count; j++)
    {
        var a = socles[i]; var b = socles[j];
        if (socleKey[a] != socleKey[b]) continue;
        if (UnityEngine.Mathf.Abs(UnityEngine.Vector3.Dot(a.transform.right, b.transform.right)) > 0.5f) continue;
        if (UnityEngine.Mathf.Abs(a.transform.position.y - b.transform.position.y) > 0.5f) continue;
        var ea = ends[a]; var eb = ends[b];
        var aPos = a.transform.position + a.transform.right * ea.x; var aNeg = a.transform.position - a.transform.right * ea.x;
        var bPos = b.transform.position + b.transform.right * eb.x; var bNeg = b.transform.position - b.transform.right * eb.x;
        var ac = a.Rend.bounds.center; var bc = b.Rend.bounds.center;
        bool aUsesPos = (aPos - bc).sqrMagnitude < (aNeg - bc).sqrMagnitude;
        bool bUsesPos = (bPos - ac).sqrMagnitude < (bNeg - ac).sqrMagnitude;
        var tipA = aUsesPos ? aPos : aNeg; var tipB = bUsesPos ? bPos : bNeg;
        if ((tipA - tipB).magnitude > 0.6f) continue;
        corners++;
        bool aM = (aUsesPos ? ea.y : ea.z) > 0.5f, bM = (bUsesPos ? eb.y : eb.z) > 0.5f;
        if (aM && bM) continue;
        cornersStraight++;
        if (cornerWhere == "") cornerWhere = "(" + tipA.x.ToString("F1") + ", " + tipA.z.ToString("F1") + ")";
    }
int steps = 0; int doors = 0; float worstStep = 0f;
foreach (var dp in UnityEngine.Object.FindObjectsByType<Cozy.Grid.DoorPiece>(UnityEngine.FindObjectsSortMode.None))
{
    if (dp == null) continue;
    doors++;
    for (int f = 0; f < 4; f++)
    {
        float lo = float.PositiveInfinity, hi = float.NegativeInfinity; int n = 0;
        foreach (var kv in byPiece)
        {
            var pc = kv.Key;
            if (pc == null || pc.face != f) continue;
            var d = pc.transform.position - dp.transform.position;
            if (UnityEngine.Mathf.Abs(d.y) > 0.5f) continue;
            if (new UnityEngine.Vector2(d.x, d.z).magnitude > 2.0f) continue;
            n++;
            if (kv.Value < lo) lo = kv.Value;
            if (kv.Value > hi) hi = kv.Value;
        }
        if (n < 2) continue;
        if (hi - lo > 0.005f) { steps++; if (hi - lo > worstStep) worstStep = hi - lo; }
    }
}
int holes = 0; string holeWhere = "";
var lineOf = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<Cozy.Grid.PlinthPiece>>();
foreach (var pc in all)
{
    if (pc == null || pc.Rend == null) continue;
    var rb = pc.Rend.bounds;
    if (rb.size.y < 0.25f) continue;
    bool ax = rb.size.x > rb.size.z;
    string key = (ax ? "z" + rb.center.z.ToString("F1") : "x" + rb.center.x.ToString("F1")) + "|" + UnityEngine.Mathf.FloorToInt((rb.min.y + 0.12f) / 3f) + "|" + (ax ? "x" : "z");
    if (!lineOf.ContainsKey(key)) lineOf[key] = new System.Collections.Generic.List<Cozy.Grid.PlinthPiece>();
    lineOf[key].Add(pc);
}
var doorList = UnityEngine.Object.FindObjectsByType<Cozy.Grid.DoorPiece>(UnityEngine.FindObjectsSortMode.None);
foreach (var kv in lineOf)
{
    bool ax = kv.Key.EndsWith("x");
    kv.Value.Sort((a, b) => (ax ? a.Rend.bounds.min.x : a.Rend.bounds.min.z).CompareTo(ax ? b.Rend.bounds.min.x : b.Rend.bounds.min.z));
    for (int i = 1; i < kv.Value.Count; i++)
    {
        var pb0 = kv.Value[i - 1].Rend.bounds; var pb1 = kv.Value[i].Rend.bounds;
        float g0 = ax ? pb0.max.x : pb0.max.z, g1 = ax ? pb1.min.x : pb1.min.z;
        if (g1 - g0 < 0.05f) continue;
        var mid = ax ? new UnityEngine.Vector3((g0 + g1) * 0.5f, pb0.center.y, pb0.center.z) : new UnityEngine.Vector3(pb0.center.x, pb0.center.y, (g0 + g1) * 0.5f);
        bool doorway = false;
        foreach (var dp in doorList)
        {
            if (dp == null) continue;
            var d = dp.transform.position - mid;
            if (UnityEngine.Mathf.Abs(d.y) < 1.6f && (ax ? UnityEngine.Mathf.Abs(d.x) : UnityEngine.Mathf.Abs(d.z)) < (g1 - g0) * 0.5f + 0.3f && (ax ? UnityEngine.Mathf.Abs(d.z) : UnityEngine.Mathf.Abs(d.x)) < 0.8f) { doorway = true; break; }
        }
        if (doorway) continue;
        var gapBox = new UnityEngine.Bounds(mid, ax ? new UnityEngine.Vector3(g1 - g0, 0.5f, 0.8f) : new UnityEngine.Vector3(0.8f, 0.5f, g1 - g0));
        bool body = false;
        foreach (var io in Cozy.Grid.InteractiveObject.All)
        {
            if (io == null || io.Def == null || io.Def.mount != Cozy.Grid.ObjectMount.Floor) continue;
            var ib = io.WorldBounds;
            if (ib.size.y < 0.1f || !ib.Intersects(gapBox)) continue;
            body = true; break;
        }
        if (body) continue;
        holes++;
        if (holeWhere == "") holeWhere = "(" + mid.x.ToString("F1") + ", " + mid.z.ToString("F1") + ") " + (g1 - g0).ToString("F2") + " м";
    }
}
int stale = 0; string staleWhere = "";
{
var lines2 = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<Cozy.Grid.PlinthPiece>>();
foreach (var pc in all)
{
    if (pc == null || pc.Rend == null || pc.owner == null || pc.span) continue;
    var rb = pc.Rend.bounds;
    bool ax = rb.size.x > rb.size.z;
    string key = (ax ? "z" + rb.center.z.ToString("F1") : "x" + rb.center.x.ToString("F1")) + "|" + UnityEngine.Mathf.FloorToInt((rb.min.y + 0.12f) / 3f) + "|" + pc.face + "|" + (ax ? "x" : "z");
    if (!lines2.ContainsKey(key)) lines2[key] = new System.Collections.Generic.List<Cozy.Grid.PlinthPiece>();
    lines2[key].Add(pc);
}
var doorList2 = UnityEngine.Object.FindObjectsByType<Cozy.Grid.DoorPiece>(UnityEngine.FindObjectsSortMode.None);
foreach (var kv in lines2)
{
    bool ax = kv.Key.EndsWith("x");
    kv.Value.Sort((a, b) => (ax ? a.Rend.bounds.min.x : a.Rend.bounds.min.z).CompareTo(ax ? b.Rend.bounds.min.x : b.Rend.bounds.min.z));
    for (int i = 1; i < kv.Value.Count; i++)
    {
        var pb0 = kv.Value[i - 1].Rend.bounds; var pb1 = kv.Value[i].Rend.bounds;
        float g0 = ax ? pb0.max.x : pb0.max.z, g1 = ax ? pb1.min.x : pb1.min.z;
        if (g1 - g0 < 0.05f) continue;
        var mid = ax ? new UnityEngine.Vector3((g0 + g1) * 0.5f, pb0.center.y, pb0.center.z) : new UnityEngine.Vector3(pb0.center.x, pb0.center.y, (g0 + g1) * 0.5f);
        bool explained = false;
        foreach (var dp in doorList2)
        {
            if (dp == null) continue;
            var d = dp.transform.position - mid;
            if (UnityEngine.Mathf.Abs(d.y) < 1.6f && (ax ? UnityEngine.Mathf.Abs(d.x) : UnityEngine.Mathf.Abs(d.z)) < (g1 - g0) * 0.5f + 0.3f && (ax ? UnityEngine.Mathf.Abs(d.z) : UnityEngine.Mathf.Abs(d.x)) < 0.8f) { explained = true; break; }
        }
        var outward = Cozy.Grid.PlinthView.Outward(kv.Value[i].face);
        if (!explained && !Cozy.Grid.PlinthView.SupportedAt(mid - outward * 0.05f, outward, 3f)) explained = true;
        if (!explained && Cozy.Grid.BuildQuery.BlockAt(mid + UnityEngine.Vector3.up, new UnityEngine.Vector3(0.05f, 0.5f, 0.05f), Cozy.Grid.GridRole.Wall) != null) explained = true;
        if (!explained)
        {
            var carrier = Cozy.Grid.BuildQuery.BlockAt(mid - outward * 0.25f + UnityEngine.Vector3.up, new UnityEngine.Vector3(0.15f, 0.5f, 0.15f), Cozy.Grid.GridRole.Wall);
            if (carrier == null || !Cozy.Grid.PlinthView.Has(carrier, kv.Value[i].face, 3f)) explained = true;
        }
        if (!explained)
        {
            var gapBox = new UnityEngine.Bounds(mid, ax ? new UnityEngine.Vector3(g1 - g0, 0.5f, 0.8f) : new UnityEngine.Vector3(0.8f, 0.5f, g1 - g0));
            foreach (var io in Cozy.Grid.InteractiveObject.All)
            {
                if (io == null || io.Def == null || io.Def.mount != Cozy.Grid.ObjectMount.Floor || io.Def.id.StartsWith("veg_")) continue;
                var ib = io.WorldBounds;
                if (ib.size.y < 0.1f || !ib.Intersects(gapBox)) continue;
                explained = true; break;
            }
        }
        if (!explained)
        {
            float plane = ax ? pb0.center.z : pb0.center.x;
            foreach (var cut in Cozy.Grid.PlankRelief.Cuts)
            {
                if (cut.thinX == ax || UnityEngine.Mathf.Abs(cut.plane - plane) > 0.3f) continue;
                if (cut.y0 > pb0.max.y || cut.y1 < pb0.min.y) continue;
                if (UnityEngine.Mathf.Max(cut.a0, g0) < UnityEngine.Mathf.Min(cut.a1, g1)) { explained = true; break; }
            }
        }
        if (explained) continue;
        stale++;
        if (staleWhere == "") staleWhere = "(" + mid.x.ToString("F1") + ", " + mid.z.ToString("F1") + ") " + (g1 - g0).ToString("F2") + " м";
    }
}
}
int bareFaces = 0; string bareWhere = ""; int stubs = 0; string stubWhere = "";
{
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.role != Cozy.Grid.GridRole.Wall || gb.railing || gb.fence || gb.ceiling || gb.Rend == null || gb.Col == null || gb.Col.isTrigger) continue;
    if (Cozy.Grid.PlinthView.IsCube(gb, 3f)) continue;
    var wb = gb.Rend.bounds; bool thinX = wb.size.x < wb.size.z;
    for (int side = 0; side < 2; side++)
    {
        int face = Cozy.Grid.PlinthView.FaceForSide(gb, side == 0);
        if (!Cozy.Grid.PlinthView.Has(gb, face, 3f)) continue;
        bool anyPiece = false; foreach (var pc in all) if (pc != null && !pc.span && pc.owner == gb && pc.face == face) { anyPiece = true; break; }
        if (anyPiece) continue;
        var outward = Cozy.Grid.PlinthView.Outward(face);
        bool sidePos = (thinX ? outward.x : outward.z) > 0f;
        float plane = (thinX ? wb.center.x : wb.center.z) + (sidePos ? 1f : -1f) * (thinX ? wb.size.x : wb.size.z) * 0.5f;
        float a0 = thinX ? wb.min.z : wb.min.x, a1 = thinX ? wb.max.z : wb.max.x;
        bool bare = false;
        for (float sa = a0 + 0.125f; sa < a1 && !bare; sa += 0.25f)
        {
            var basePt = thinX ? new UnityEngine.Vector3(plane, wb.min.y, sa) : new UnityEngine.Vector3(sa, wb.min.y, plane);
            if (!Cozy.Grid.PlinthView.SupportedAt(basePt, outward, 3f)) continue;
            var samplePt = basePt + outward * 0.06f + UnityEngine.Vector3.up * 0.9f;
            if (Cozy.Grid.BuildQuery.BlockAt(samplePt, new UnityEngine.Vector3(0.04f, 0.5f, 0.04f), Cozy.Grid.GridRole.Wall) != null) continue;
            bool blocked = false;
            foreach (var c in Cozy.Grid.PlankRelief.Cuts)
            {
                if (c.thinX != thinX || c.sidePos != sidePos || UnityEngine.Mathf.Abs(c.plane - plane) > 0.2f) continue;
                if (c.y0 > wb.min.y + 0.14f || c.y1 < wb.min.y + 0.01f) continue;
                if (sa >= c.a0 - 0.01f && sa <= c.a1 + 0.01f) { blocked = true; break; }
            }
            if (!blocked)
                foreach (var io in Cozy.Grid.InteractiveObject.All)
                {
                    if (io == null || io.Def == null || io.Def.mount != Cozy.Grid.ObjectMount.Floor || io.Def.id.StartsWith("veg_")) continue;
                    var ib = io.WorldBounds; if (ib.size.y < 0.1f) continue;
                    if (ib.max.y < wb.min.y + 0.02f || ib.min.y > wb.min.y + 0.13f) continue;
                    float near = thinX ? (sidePos ? ib.min.x : ib.max.x) : (sidePos ? ib.min.z : ib.max.z);
                    if (UnityEngine.Mathf.Abs(near - plane) > 0.25f) continue;
                    float e0 = thinX ? ib.min.z : ib.min.x, e1 = thinX ? ib.max.z : ib.max.x;
                    if (sa >= e0 - 0.03f && sa <= e1 + 0.03f) { blocked = true; break; }
                }
            if (!blocked) bare = true;
        }
        if (bare) { bareFaces++; if (bareWhere == "") bareWhere = gb.transform.position.ToString("F1") + " грань " + face; }
    }
}
foreach (var pc in all)
{
    if (pc == null || pc.span || pc.owner == null || pc.Rend == null) continue;
    var pb = pc.Rend.bounds;
    float along = UnityEngine.Mathf.Max(pb.size.x, pb.size.z);
    if (along > 0.12f) continue;
    if (Cozy.Grid.BuildQuery.BlockAt(pb.center + UnityEngine.Vector3.up * 0.9f, new UnityEngine.Vector3(0.03f, 0.5f, 0.03f), Cozy.Grid.GridRole.Wall) == null) continue;
    stubs++; if (stubWhere == "") stubWhere = pb.center.ToString("F1") + " " + along.ToString("F2") + " м";
}
}
var floors = new System.Text.StringBuilder();
foreach (var kv in perFloor) floors.Append("этаж " + kv.Key + ": " + kv.Value + "; ");
float minF = float.PositiveInfinity, maxF = float.NegativeInfinity;
foreach (var v in fronts) { if (v < minF) minF = v; if (v > maxF) maxF = v; }
var bad = new System.Text.StringBuilder();
if (sunk > 0) bad.Append("утоплено в обшивке " + sunk + " (худший на " + (worstSunk * 100f).ToString("F1") + " см, " + worstWhere + "); ");
if (inFurn > 0) bad.Append("внутри мебели " + inFurn + " (" + furnWhere + "); ");
if (gaps > 0) bad.Append("щель за плинтусом " + gaps + " (худшая " + (worstGap * 1000f).ToString("F0") + " мм, " + gapWhere + "); ");
if (steps > 0) bad.Append("ступенька у проёмов " + steps + " (до " + (worstStep * 1000f).ToString("F0") + " мм); ");
if (cornersStraight > 0) bad.Append("угол цоколя без митры " + cornersStraight + " из " + corners + " (" + cornerWhere + "); ");
if (holes > 0) bad.Append("дыра в цоколе " + holes + " (" + holeWhere + "); ");
int orphans = 0; string orphanWhere = "";
foreach (var op in all)
{
    if (op == null || op.span || op.owner != null) continue;
    orphans++;
    var orr = op.GetComponent<UnityEngine.Renderer>();
    if (orphanWhere == "" && orr != null) orphanWhere = orr.bounds.center.ToString("F1");
}
if (orphans > 0) bad.Append("сирота без носителя " + orphans + " (" + orphanWhere + "); ");
if (stale > 0) bad.Append("дыра без причины " + stale + " (" + staleWhere + "); ");
if (bareFaces > 0) bad.Append("грань с флагом без куска при опоре " + bareFaces + " (" + bareWhere + "); ");
if (stubs > 0) bad.Append("огрызок внутри стены " + stubs + " (" + stubWhere + "); ");
string s = "кусков " + all.Count + " (под проёмами " + spans + ", из них в мебели " + spanInFurn + "; на лестницах " + noOwner + "), " + floors.ToString() + "дверей " + doors
    + ", вынос " + minF.ToString("F3") + ".." + maxF.ToString("F3") + " м, углов цоколя " + corners;
return (bad.Length == 0 ? "плинтус: ок — " : "плинтус: КРАСНОЕ: " + bad + "| ") + s;
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    text = out.stdout.strip()
    line = text.splitlines()[-1] if text else ''
    try:
        d = json.loads(line)
        res = (d.get('data') or {}).get('result')
    except Exception:
        res = None
    if not res:
        print('плинтус: мост не ответил —', (line or out.stderr)[:300]); sys.exit(1)
    print(res)
    sys.exit(1 if 'КРАСНОЕ' in str(res) else 0)


if __name__ == '__main__':
    main()
