"""Проба переноса (COVERAGE, дыра № 1): предмет в руке никогда не исчезает.

python3 transfer_probe.py          проверка привязок: методы и поля на месте, есть кандидаты (без побочных эффектов)
python3 transfer_probe.py --run    взять предмет в руку, через полсекунды замерить, вернуть (только в СВОЁМ play:
                                   чужая проба или сохранение уровня в этот момент испортят сцену, см. SESSIONS.md)
Инвариант 3: у носимого все собственные рендереры включены, хотя бы один виден камерой,
альфа материала не нулевая. Матч с приёмником эта проба не проверяет.
"""
import json, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'

BIND = r'''
var t = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var sb = new System.Text.StringBuilder();
foreach (var n in new[] { "BeginHandMove", "CancelHandMove", "EndHandMove", "Carried" })
    sb.Append(n + "=" + (t.GetMethod(n, bf) != null) + " ");
foreach (var n in new[] { "_movingObj", "_handMove" })
    sb.Append(n + "=" + (t.GetField(n, bf) != null) + " ");
int cand = 0;
if (UnityEngine.Application.isPlaying)
    foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        if (io.Def != null && !io.Def.builtIn && (io.Def.movable || !string.IsNullOrEmpty(io.Def.pickupItemId))
            && io.Container == null && !Cozy.Grid.ContainerSlot.HoldsClosed(io)) cand++;
sb.Append("play=" + UnityEngine.Application.isPlaying + " candidates=" + cand);
return sb.ToString();
'''

PICK = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
if (gc == null) return "нет GridCursor";
if (gc.HandPlacing) return "уже что-то в руке";
Cozy.Grid.InteractiveObject best = null;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null || io.Def.builtIn || io.Container != null) continue;
    if (!(io.Def.movable || !string.IsNullOrEmpty(io.Def.pickupItemId))) continue;
    if (Cozy.Grid.ContainerSlot.HoldsClosed(io)) continue;
    if (best == null || io.Def.id.Contains("plate") || io.Def.id.Contains("cup")) best = io;
}
if (best == null) return "нет кандидата";
gc.BeginHandMove(best);
return "взят " + best.Def.id + " " + best.name;
'''

MEASURE = r'''
var gc = Cozy.Grid.GridCursor.I;
var t = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var sb = new System.Text.StringBuilder();
try
{
    if (!UnityEngine.Application.isPlaying) return "не в play";
    var mv = t.GetField("_movingObj", bf).GetValue(gc);
    if (mv == null) return "КРАСНОЕ: в руке ничего нет (перенос сорвался)";
    var anchor = mv.GetType().GetProperty("Anchor").GetValue(mv, null) as UnityEngine.Transform;
    var io = anchor == null ? null : anchor.GetComponentInParent<Cozy.Grid.InteractiveObject>();
    if (io == null) return "КРАСНОЕ: у носимого нет InteractiveObject";
    int total = 0, off = 0, visible = 0, ghostAlpha = 0;
    foreach (var r in io.GetComponentsInChildren<UnityEngine.Renderer>(true))
    {
        if (r.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io) continue;
        if (r.name.StartsWith("Outline")) continue;
        total++;
        if (!r.enabled || !r.gameObject.activeInHierarchy) { off++; continue; }
        if (r.isVisible) visible++;
        var m = r.sharedMaterial;
        if (m != null)
        {
            float a = 1f;
            if (m.HasProperty("_BaseColor")) a = m.GetColor("_BaseColor").a;
            else if (m.HasProperty("_Color")) a = m.GetColor("_Color").a;
            if (a < 0.05f) ghostAlpha++;
        }
    }
    sb.Append("предмет=" + io.Def.id + " рендереров=" + total + " выключено=" + off + " видно_камерой=" + visible + " альфа<0.05=" + ghostAlpha + " HandPlacing=" + gc.HandPlacing);
    if (total == 0 || off > 0 || visible == 0 || ghostAlpha == total) sb.Insert(0, "КРАСНОЕ: ");
    else sb.Insert(0, "ок: ");
}
finally
{
    var cancel = t.GetMethod("CancelHandMove", bf);
    if (cancel != null) cancel.Invoke(gc, null);
}
return sb.ToString();
'''


def call(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        return (d.get('data') or {}).get('result') or d.get('message') or line
    except Exception:
        return out.stdout[-300:]


def main():
    print('привязки:', call(BIND))
    if '--run' not in sys.argv:
        print('полный прогон: transfer_probe.py --run (только в своём play)')
        return
    picked = call(PICK)
    print('шаг 1:', picked)
    if not str(picked).startswith('взят'):
        sys.exit(1)
    time.sleep(0.7)
    res = call(MEASURE)
    print('шаг 2:', res)
    sys.exit(1 if 'КРАСНОЕ' in str(res) else 0)


if __name__ == '__main__':
    main()
