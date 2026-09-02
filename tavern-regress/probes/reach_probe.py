"""Досягаемость: одна мера у выделения и руки, до ближайшей точки предмета (инвариант 34, P158).

Ставит игрока в дальний угол: ни один объект не в зоне; потом в 3.1 и 3.5 м от грани
холодильника: выделение и рука отвечают одинаково. Игрок возвращается на место.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var player = Cozy.Grid.PlayerRef.GameObject;
if (player == null) return "КРАСНОЕ: нет игрока";
var cc = player.GetComponent<UnityEngine.CharacterController>();
var keep = player.transform.position;
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var inter = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.Interactor>();
var mIn = typeof(Cozy.Grid.Interactor).GetMethod("InReach", flags);
var gc = Cozy.Grid.GridCursor.I;
var mHand = typeof(Cozy.Grid.GridCursor).GetMethod("HandReach", flags, null, new System.Type[] { typeof(UnityEngine.Transform) }, null);
if (inter == null || mIn == null || mHand == null) return "КРАСНОЕ: нет InReach/HandReach";
var all = UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None);
float reach = Cozy.Grid.Interactor.ReachCells * 3f;
var bad = new System.Text.StringBuilder();
if (cc != null) cc.enabled = false;
try
{
    float minX = float.MaxValue, minZ = float.MaxValue;
    foreach (var io in all) { minX = UnityEngine.Mathf.Min(minX, io.transform.position.x); minZ = UnityEngine.Mathf.Min(minZ, io.transform.position.z); }
    player.transform.position = new UnityEngine.Vector3(minX - 12f, 0f, minZ - 12f);
    UnityEngine.Physics.SyncTransforms();
    int near = 0;
    foreach (var io in all)
    {
        if (io.Def == null) continue;
        bool sel = (bool)mIn.Invoke(inter, new object[] { io, null });
        bool hand = (bool)mHand.Invoke(gc, new object[] { io.transform });
        if (sel || hand) { near++; bad.Append("из угла в зоне: " + io.Def.id + " выделение=" + sel + " рука=" + hand + "; "); }
    }
    Cozy.Grid.InteractiveObject fridge = null;
    foreach (var io in all) if (io.Def != null && io.Def.id == "home_fridge") fridge = io;
    string edgeReport = "холодильника нет, шаг у грани пропущен";
    if (fridge != null)
    {
        UnityEngine.Bounds b = new UnityEngine.Bounds(fridge.transform.position, UnityEngine.Vector3.zero); bool first = true;
        foreach (var c in fridge.GetComponentsInChildren<UnityEngine.Collider>()) { if (!c.enabled || c.isTrigger) continue; if (first) { b = c.bounds; first = false; } else b.Encapsulate(c.bounds); }
        float[] gaps = { reach - 0.2f, reach + 0.2f };
        edgeReport = "";
        foreach (var gap in gaps)
        {
            player.transform.position = new UnityEngine.Vector3(b.center.x, 0f, b.max.z + gap);
            UnityEngine.Physics.SyncTransforms();
            bool sel = (bool)mIn.Invoke(inter, new object[] { fridge, null });
            bool hand = (bool)mHand.Invoke(gc, new object[] { fridge.transform });
            bool want = gap < reach;
            edgeReport += "грань+" + gap.ToString("F1") + ": выделение=" + sel + " рука=" + hand + "; ";
            if (sel != want || hand != want) bad.Append("у грани холодильника на " + gap.ToString("F1") + " м ожидалось " + want + ", выделение=" + sel + " рука=" + hand + "; ");
        }
    }
    string head = "объектов=" + all.Length + " из угла в зоне=" + near + " " + edgeReport;
    return bad.Length == 0 ? head + ":: досягаемость держится" : "КРАСНОЕ: " + bad.ToString() + " | " + head;
}
finally
{
    player.transform.position = keep;
    if (cc != null) cc.enabled = true;
}
'''

r = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})], capture_output=True, text=True, timeout=300)
line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '{}'
try:
    d = json.loads(line); print((d.get('data') or {}).get('result') or d.get('message'))
except Exception:
    print('КРАСНОЕ: мост не ответил', r.stdout[-300:])
