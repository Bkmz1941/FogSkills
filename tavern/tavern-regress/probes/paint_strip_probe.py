"""Полоса покраски и Т-стык с проёмом в play (инвариант 226, P533): для каждой двери/окна уровня, чья клетка
примыкает к линии стены с блоками по обе стороны стыка, CollectPaintStrip с красимой стороны пьесы не выходит за
ребро стыка — в любой фазе створки. Часть «косяки» (P537): у двери/окна без своей покраски сторона косяка
равна покраске ближайшего соседа по линии БЕЗ стыка между ними, а если такого нет — не несёт покраску соседа
за стыком; заглушка плинтуса под проёмом взята у соседа без стыка на её стороне (P542). Ничего не меняет. Вердикт: PAINTSTRIP ok | PAINTSTRIP FAIL: …
Часть «юбка лестницы» (инвариант 241, P554): луч кисти по правилам PaintRaycast (игрок, noPick,
passThrough, объекты, выключенные рендереры, ЛЕСТНИЦЫ — пропуск) с любой грани каждой лестницы
(бока, у площадки и торец) не отдаёт первым коллайдер лестницы — иначе клик по юбке уходил в ничью
по дистанции с RaycastStairSide и бок не красился (20.09–23.09). Бок, закрытый СТЕНОЙ (лестница вплотную к наружной
стене, луч пробы идёт снаружи дома), считается «загорожено», а не провалом (26.09, night_build). Вердикт: STAIRSIDE ok | STAIRSIDE FAIL: …
python3 paint_strip_probe.py"""
import json, subprocess, sys, pathlib
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'

STAIR_CODE = """
if (!UnityEngine.Application.isPlaying) return "STAIRSIDE FAIL: not playing";
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
float cs = (float)typeof(Cozy.Grid.GridCursor).GetField("_cell", bf).GetValue(gc);
var paintM = typeof(Cozy.Grid.GridCursor).GetMethod("PaintRaycast", bf, null, new System.Type[] { typeof(UnityEngine.Ray), typeof(UnityEngine.RaycastHit).MakeByRefType() }, null);
var sideM = typeof(Cozy.Grid.GridCursor).GetMethod("RaycastStairSide", bf, null, new System.Type[] { typeof(UnityEngine.Ray), typeof(UnityEngine.RaycastHit).MakeByRefType(), typeof(Cozy.Grid.StairPiece).MakeByRefType() }, null);
if (paintM == null || sideM == null) return "STAIRSIDE FAIL: нет перегрузок PaintRaycast(Ray)/RaycastStairSide(Ray) (переименовали?)";
int faces = 0, occluded = 0; var bad = new System.Text.StringBuilder();
foreach (var sp in Cozy.Grid.StairPiece.All)
{
    if (sp == null || sp.IsGhost) continue;
    var tf = sp.transform;
    float rise = sp.riseCells * cs;
    var targets = new System.Collections.Generic.List<UnityEngine.Vector3>();
    var dirs = new System.Collections.Generic.List<UnityEngine.Vector3>();
    for (int s = -1; s <= 1; s += 2)
    {
        targets.Add(tf.TransformPoint(new UnityEngine.Vector3(s * cs * 0.5f, rise * 0.25f, -sp.FootRun(cs) * 0.5f + cs * 0.5f)));
        dirs.Add(tf.right * s);
        if (sp.landing) { targets.Add(tf.TransformPoint(new UnityEngine.Vector3(s * cs * 0.5f, rise * 0.5f, sp.LandingEnd(cs) - cs * 0.25f))); dirs.Add(tf.right * s); }
    }
    if (sp.landing) { targets.Add(tf.TransformPoint(new UnityEngine.Vector3(0f, rise * 0.5f, sp.LandingEnd(cs)))); dirs.Add(tf.forward); }
    for (int k = 0; k < targets.Count; k++)
    {
        var from = targets[k] + dirs[k] * 2.5f + UnityEngine.Vector3.up * 1.2f;
        var ray = new UnityEngine.Ray(from, (targets[k] - from).normalized);
        var pa = new object[] { ray, null };
        bool hasHit = (bool)paintM.Invoke(gc, pa);
        var hit = (UnityEngine.RaycastHit)pa[1];
        var sa = new object[] { ray, null, null };
        bool hasSide = (bool)sideM.Invoke(gc, sa);
        var side = (UnityEngine.RaycastHit)sa[1];
        var sideSp = sa[2] as Cozy.Grid.StairPiece;
        faces++;
        string where = "лестница " + tf.position.ToString("0.0") + " грань " + k;
        if ((!hasSide || sideSp != sp) && hasHit && hit.collider.GetComponentInParent<Cozy.Grid.GridBlock>() != null && hit.collider.GetComponentInParent<Cozy.Grid.GridBlock>().role == Cozy.Grid.GridRole.Wall) { occluded++; continue; }
        if (!hasSide || sideSp != sp) { bad.Append(" " + where + ": RaycastStairSide не видит грань;"); continue; }
        if (hasHit && hit.collider.GetComponentInParent<Cozy.Grid.StairPiece>() != null) { bad.Append(" " + where + ": общий луч кисти отдал коллайдер лестницы " + hit.collider.name + " — бок проиграет ничью;"); continue; }
        if (hasHit && hit.distance < side.distance) occluded++;
    }
}
return bad.Length == 0 ? "STAIRSIDE ok: граней " + faces + ", загорожено " + occluded : "STAIRSIDE FAIL:" + bad.ToString();
"""

code = '''
if (!UnityEngine.Application.isPlaying) return "PAINTSTRIP FAIL: not playing";
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
if (gc == null) return "PAINTSTRIP FAIL: нет GridCursor";
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var m = typeof(Cozy.Grid.GridCursor).GetMethod("CollectPaintStrip", bf);
var cf = typeof(Cozy.Grid.GridCursor).GetField("_cell", bf);
if (m == null || cf == null) return "PAINTSTRIP FAIL: нет CollectPaintStrip или _cell (переименовали?)";
float cs = (float)cf.GetValue(gc);
var wallHalf = new UnityEngine.Vector3(cs * 0.25f, cs * 0.3f, cs * 0.25f);
var roots = new System.Collections.Generic.List<UnityEngine.Vector3>();
var spans = new System.Collections.Generic.List<bool>();
var names = new System.Collections.Generic.List<string>();
foreach (var d in Cozy.Grid.DoorPiece.All) if (d != null) { roots.Add(d.transform.position); spans.Add(d.SpansX); names.Add("дверь" + (d.IsOpen ? "(откр)" : "(закр)")); }
foreach (var w in Cozy.Grid.WindowPiece.All) if (w != null) { roots.Add(w.transform.position); spans.Add(w.SpansX); names.Add("окно"); }
int junctions = 0; var bad = new System.Text.StringBuilder(); var seen = new System.Text.StringBuilder();
for (int i = 0; i < roots.Count; i++)
{
    var r = roots[i]; bool thinX = spans[i]; float y = r.y + cs * 0.5f;
    for (int sgn = -1; sgn <= 1; sgn += 2)
    {
        float plane = (thinX ? r.x : r.z) + sgn * cs * 0.5f;
        float edge = thinX ? r.z : r.x;
        bool sidePos = sgn < 0;
        float before = edge - cs * 0.5f, after = edge + cs * 0.5f;
        var pb = thinX ? new UnityEngine.Vector3(plane, y, before) : new UnityEngine.Vector3(before, y, plane);
        var pa = thinX ? new UnityEngine.Vector3(plane, y, after) : new UnityEngine.Vector3(after, y, plane);
        if (Cozy.Grid.BuildQuery.BlockAt(pb, wallHalf, Cozy.Grid.GridRole.Wall) == null) continue;
        if (Cozy.Grid.BuildQuery.BlockAt(pa, wallHalf, Cozy.Grid.GridRole.Wall) == null) continue;
        junctions++;
        string tag = names[i] + " (" + r.x.ToString("0.#") + "; " + r.z.ToString("0.#") + ") линия " + (thinX ? "x=" : "z=") + plane.ToString("0.#");
        var a1 = new object[] { thinX, plane, y, sidePos, before, new System.Collections.Generic.List<Cozy.Grid.GridBlock>(), new System.Collections.Generic.List<Cozy.Grid.GridBlock>(), new System.Collections.Generic.List<Cozy.Grid.StairPiece>(), 0f, 0f };
        m.Invoke(gc, a1); float hi = (float)a1[9];
        var a2 = new object[] { thinX, plane, y, sidePos, after, new System.Collections.Generic.List<Cozy.Grid.GridBlock>(), new System.Collections.Generic.List<Cozy.Grid.GridBlock>(), new System.Collections.Generic.List<Cozy.Grid.StairPiece>(), 0f, 0f };
        m.Invoke(gc, a2); float lo = (float)a2[8];
        bool leak = hi > before + 0.01f || lo < after - 0.01f;
        if (leak) bad.Append(tag + ": полоса прошла стык, достигла " + (hi > before + 0.01f ? hi.ToString("0.#") : lo.ToString("0.#")) + "; ");
        else seen.Append(tag + " ok; ");
    }
}
int jambChecks = 0; var jambBad = new System.Text.StringBuilder();
var pieces = new System.Collections.Generic.List<UnityEngine.Component>();
foreach (var d in Cozy.Grid.DoorPiece.All) if (d != null) pieces.Add(d);
foreach (var w in Cozy.Grid.WindowPiece.All) if (w != null) pieces.Add(w);
var pbf = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
foreach (var pc in pieces)
{
    var t = pc.GetType();
    bool spansX = (bool)t.GetProperty("SpansX").GetValue(pc, null);
    var parts = t.GetProperty("WallPartRenderers").GetValue(pc, null) as UnityEngine.Renderer[];
    if (parts == null) continue;
    var fa = t.GetField("paintA", pbf); var fb = t.GetField("paintB", pbf);
    string ownA = fa != null ? (string)fa.GetValue(pc) : "", ownB = fb != null ? (string)fb.GetValue(pc) : "";
    var r = pc.transform.position;
    UnityEngine.Vector3 along = spansX ? UnityEngine.Vector3.right : UnityEngine.Vector3.forward;
    var half = new UnityEngine.Vector3(cs * 0.25f, cs * 0.3f, cs * 0.25f);
    var nbP = Cozy.Grid.BuildQuery.BlockAt(r + along * cs, half, Cozy.Grid.GridRole.Wall);
    var nbM = Cozy.Grid.BuildQuery.BlockAt(r - along * cs, half, Cozy.Grid.GridRole.Wall);
    bool thinX = !spansX; float plane = spansX ? r.z : r.x; float along0 = spansX ? r.x : r.z; float y = r.y + cs * 0.5f;
    for (int sub = 1; sub <= 2; sub++)
    {
        bool sideA = sub == 1;
        if (!string.IsNullOrEmpty(sideA ? ownA : ownB)) continue;
        bool cutP = Cozy.Grid.BuildQuery.PerpBarrierAt(thinX, plane, y, sideA, along0 + cs * 0.5f, cs);
        bool cutM = Cozy.Grid.BuildQuery.PerpBarrierAt(thinX, plane, y, sideA, along0 - cs * 0.5f, cs);
        string expect = "";
        if (!cutP && nbP != null) expect = sideA ? nbP.paintA : nbP.paintB;
        if (string.IsNullOrEmpty(expect) && !cutM && nbM != null) expect = sideA ? nbM.paintA : nbM.paintB;
        var forbidden = new System.Collections.Generic.List<string>();
        if (cutP && nbP != null) forbidden.Add(sideA ? nbP.paintA : nbP.paintB);
        if (cutM && nbM != null) forbidden.Add(sideA ? nbM.paintA : nbM.paintB);
        string tag = (pc is Cozy.Grid.DoorPiece ? "дверь" : "окно") + " (" + r.x.ToString("0.#") + "; " + r.z.ToString("0.#") + ") сторона " + (sideA ? "A" : "B");
        foreach (var part in parts)
        {
            if (part == null) continue;
            var ms = part.sharedMaterials; if (ms.Length <= sub) continue;
            jambChecks++;
            var mat = ms[sub];
            if (!string.IsNullOrEmpty(expect))
            {
                var em = Cozy.Grid.PlankRelief.CladBand(expect) ? Cozy.Grid.PlankRelief.CoreMaterial : Cozy.Grid.PaintLibrary.Get(expect);
                if (em != null && mat != em) { jambBad.Append(tag + " " + part.name + ": ожидалась " + expect + "; "); break; }
            }
            else
            {
                bool leaked = false;
                foreach (var f in forbidden)
                {
                    if (string.IsNullOrEmpty(f) || Cozy.Grid.PlankRelief.CladBand(f)) continue;
                    if (mat == Cozy.Grid.PaintLibrary.Get(f)) { jambBad.Append(tag + " " + part.name + ": за стыком несёт " + f + "; "); leaked = true; break; }
                }
                if (leaked) break;
            }
        }
    }
    foreach (var stub in pc.GetComponentsInChildren<Cozy.Grid.PlinthPiece>(true))
    {
        if (stub == null || !stub.span) continue;
        var owner = stub.owner as Cozy.Grid.GridBlock; if (owner == null) continue;
        bool stubA = stub.face == 0 || stub.face == 2;
        bool cut;
        if (owner == nbP) cut = Cozy.Grid.BuildQuery.PerpBarrierAt(thinX, plane, y, stubA, along0 + cs * 0.5f, cs);
        else if (owner == nbM) cut = Cozy.Grid.BuildQuery.PerpBarrierAt(thinX, plane, y, stubA, along0 - cs * 0.5f, cs);
        else continue;
        jambChecks++;
        if (cut) { jambBad.Append((pc is Cozy.Grid.DoorPiece ? "дверь" : "окно") + " (" + r.x.ToString("0.#") + "; " + r.z.ToString("0.#") + "): заглушка плинтуса грань " + stub.face + " взята у соседа за стыком; "); break; }
    }
}
if (jambBad.Length > 0) bad.Append("КОСЯКИ: " + jambBad);
if (junctions == 0 && jambChecks == 0) return "PAINTSTRIP ok: Т-стыков и проёмов на уровне нет (нечего проверять)";
if (bad.Length > 0) return "PAINTSTRIP FAIL: " + bad + " :: " + seen;
return "PAINTSTRIP ok: стыков " + junctions + ", сторон косяков " + jambChecks + " :: " + seen;
'''
out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})], capture_output=True, text=True, timeout=120, cwd=PROJECT)
text = out.stdout.strip(); line = text.splitlines()[-1] if text else '{}'
try:
    d = json.loads(line); res = (d.get('data') or {}).get('result') or str(d)
except Exception:
    res = 'PAINTSTRIP FAIL: мост ' + text[-300:]
print(res)
out2 = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": STAIR_CODE})], capture_output=True, text=True, timeout=120, cwd=PROJECT)
text2 = out2.stdout.strip(); line2 = text2.splitlines()[-1] if text2 else '{}'
try:
    d2 = json.loads(line2); res2 = (d2.get('data') or {}).get('result') or str(d2)
except Exception:
    res2 = 'STAIRSIDE FAIL: мост ' + text2[-300:]
print(res2)
sys.exit(0 if res.startswith('PAINTSTRIP ok') and res2.startswith('STAIRSIDE ok') else 1)
