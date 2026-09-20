"""Плинтус и цоколь на открытом уровне: есть, не утоплен в обшивке, не лезет в мебель, ровен у дверей.

python3 plinth_probe.py        замер в play, без побочных эффектов (~2 с)

Что меряется (грабли P478, P492, P499, P501–P505):
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
var floors = new System.Text.StringBuilder();
foreach (var kv in perFloor) floors.Append("этаж " + kv.Key + ": " + kv.Value + "; ");
float minF = float.PositiveInfinity, maxF = float.NegativeInfinity;
foreach (var v in fronts) { if (v < minF) minF = v; if (v > maxF) maxF = v; }
var bad = new System.Text.StringBuilder();
if (sunk > 0) bad.Append("утоплено в обшивке " + sunk + " (худший на " + (worstSunk * 100f).ToString("F1") + " см, " + worstWhere + "); ");
if (inFurn > 0) bad.Append("внутри мебели " + inFurn + " (" + furnWhere + "); ");
if (steps > 0) bad.Append("ступенька у проёмов " + steps + " (до " + (worstStep * 1000f).ToString("F0") + " мм); ");
string s = "кусков " + all.Count + " (под проёмами " + spans + ", из них в мебели " + spanInFurn + "; на лестницах " + noOwner + "), " + floors.ToString() + "дверей " + doors
    + ", вынос " + minF.ToString("F3") + ".." + maxF.ToString("F3") + " м";
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
