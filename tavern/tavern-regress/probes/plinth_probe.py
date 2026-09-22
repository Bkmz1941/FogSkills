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
    if (gb == null || pc.span) continue;
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
