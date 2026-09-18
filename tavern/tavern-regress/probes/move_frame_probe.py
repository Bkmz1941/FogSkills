"""Характеризующий замер UpdateMoveObject (GridCursor.ObjectMove.cs): что делает перенос В РУКАХ кадр за кадром при неподвижной мыши.

python3 move_frame_probe.py --save <имя>   в СВОЁМ play: берёт ближайший носимый предмет (BeginHandMove), 90 кадров пишет
                                           состояние переноса (поза якоря, тинт/призрак, хосты снапов, подписи, колесо),
                                           возвращает предмет (CancelHandMove); трасса в .move_frames/<имя>.txt
python3 move_frame_probe.py --diff <а> <б> посимвольная сверка двух трасс: первое расхождение и число кадров
Мышь трогать нельзя: трасса зависит от курсора, поэтому сверка честна только в одной сессии без Ильи за мышью.
"""
import json, os, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '.move_frames')
TRACE = '/tmp/move_frame_trace.txt'
FRAMES = 90

def call(code):
    code = '\n'.join(l for l in code.splitlines() if l.strip() and not l.strip().startswith('//'))
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=180, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        r = (d.get('data') or {}).get('result')
        return r if r is not None else line[:800]
    except Exception:
        return line[:800]

PICK = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; if (gc == null) return "нет GridCursor";
if (gc.HandPlacing) return "в руке уже что-то есть — не мешаю";
var player = Cozy.Grid.PlayerRef.GameObject; if (player == null) return "нет игрока";
Cozy.Grid.InteractiveObject best = null; float bestD = float.MaxValue;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null || io.Def.builtIn || io.Container != null || Cozy.Grid.ContainerSlot.HoldsClosed(io)) continue;
    if (!(io.Def.movable || !string.IsNullOrEmpty(io.Def.pickupItemId))) continue;
    float d = UnityEngine.Vector3.Distance(io.transform.position, player.transform.position);
    var id = io.Def.id;
    if (id.Contains("apple") || id.Contains("cup") || id.Contains("key")) d -= 2f;
    if (d < bestD) { bestD = d; best = io; }
}
if (best == null) return "носимого нет";
var p = best.transform.position; var r = best.transform.eulerAngles;
gc.BeginHandMove(best);
return "взят " + best.Def.id + " id=" + best.GetInstanceID() + " @" + p.ToString("F3") + " rot " + r.ToString("F1") + " hand=" + gc.HandPlacing;
'''

SAMPLE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; var t = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
System.Func<string, object> F = n => { var f = t.GetField(n, bf); return f != null ? f.GetValue(gc) : "?"; };
System.Func<string, object> S = n => { var p = t.GetProperty(n, bf); return p != null ? p.GetValue(gc) : "?"; };
System.Func<object, string> N = o => o == null ? "-" : (o is UnityEngine.Component c ? c.name : o.ToString());
string path = "%TRACE%"; System.IO.File.WriteAllText(path, "");
int left = %FRAMES%;
UnityEditor.EditorApplication.CallbackFunction tick = null;
tick = () =>
{
    var mv = F("_movingObj");
    var sb = new System.Text.StringBuilder();
    var ap = mv != null && !(mv is string) ? mv.GetType().GetProperty("Anchor") : null;
    var anchor = ap != null ? ap.GetValue(mv) as UnityEngine.Transform : null;
    sb.Append(anchor != null ? anchor.position.ToString("F3") + " " + anchor.eulerAngles.ToString("F1") : "anchor=-");
    sb.Append(" blocked=" + F("_moveBlocked") + " ghost=" + F("_moveGhosted") + " seeThroughOff=" + F("_seeThroughOff"));
    sb.Append(" hover=" + N(F("_hoverHost")) + " seat=" + N(F("_seatHost")) + " dish=" + N(F("_dishHost")) + " hostSnap=" + F("_hostSnapped"));
    sb.Append(" pileGuest=" + N(S("PileGuest")) + " chip=" + (S("CursorChipText") ?? "-") + "/" + S("CursorChipDenied"));
    sb.Append(" label=" + (S("ActionLabelText") ?? "-") + "/" + S("ActionLabelDenied") + "@" + N(S("ActionLabelTarget")));
    sb.Append(" wheel=" + Cozy.View.ViewState.WheelCaptured);
    System.IO.File.AppendAllText(path, sb.ToString() + "\n");
    if (--left <= 0) UnityEditor.EditorApplication.update -= tick;
};
UnityEditor.EditorApplication.update += tick;
return "sampling " + left;
'''

CANCEL = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; if (gc == null) return "нет GridCursor";
var t = typeof(Cozy.Grid.GridCursor);
var m = t.GetMethod("CancelHandMove", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public);
if (m == null) return "нет CancelHandMove";
m.Invoke(gc, null);
return "возвращён, hand=" + gc.HandPlacing;
'''

def run(name):
    os.makedirs(OUT, exist_ok=True)
    picked = call(PICK)
    print(picked)
    if not str(picked).startswith('взят'):
        return 1
    try:
        time.sleep(0.5)
        print(call(SAMPLE.replace('%TRACE%', TRACE).replace('%FRAMES%', str(FRAMES))))
        time.sleep(FRAMES / 30.0 + 1.5)
    finally:
        print(call(CANCEL))
    rows = open(TRACE, encoding='utf-8').read().splitlines() if os.path.exists(TRACE) else []
    dst = os.path.join(OUT, name + '.txt')
    open(dst, 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    distinct = len(set(rows))
    print('кадров %d, различных состояний %d, файл %s' % (len(rows), distinct, dst))
    print('первый кадр:', rows[0] if rows else '-')
    return 0

def diff(a, b):
    ra = open(os.path.join(OUT, a + '.txt'), encoding='utf-8').read().splitlines()
    rb = open(os.path.join(OUT, b + '.txt'), encoding='utf-8').read().splitlines()
    n = min(len(ra), len(rb))
    for i in range(n):
        if ra[i] != rb[i]:
            print('РАСХОЖДЕНИЕ на кадре %d:\n  %s: %s\n  %s: %s' % (i, a, ra[i], b, rb[i]))
            return 1
    if len(ra) != len(rb):
        print('кадров %d против %d' % (len(ra), len(rb)))
        return 1
    print('совпало посимвольно: %d кадров' % n)
    return 0

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == '--save': sys.exit(run(args[1]))
    if len(args) == 3 and args[0] == '--diff': sys.exit(diff(args[1], args[2]))
    print(__doc__)
