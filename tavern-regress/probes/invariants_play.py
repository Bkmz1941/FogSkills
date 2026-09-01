"""Проверка ЖИВЫХ инвариантов в play: то, что тестами EditMode не поймать.

Каждая проверка — уже пойманный когда-то баг. Список правил: INVARIANTS.md (tavern-regress).
Запускать после любой правки взаимодействия, наведения или контейнеров.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bad = new System.Text.StringBuilder();
var cam = UnityEngine.Camera.main;
var t = typeof(Cozy.Grid.Interactor);
var skip = t.GetMethod("SkipHit", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var hits = new UnityEngine.RaycastHit[24];
int closed = 0, checkedObjects = 0;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null) continue;
    checkedObjects++;
    // 1. Предмет в ЗАКРЫТОЙ секции не наводится и не выделяется.
    if (Cozy.Grid.ContainerSlot.HoldsClosed(io))
    {
        closed++;
        var rend = io.GetComponentInChildren<UnityEngine.Renderer>();
        if (rend != null && cam != null && skip != null)
        {
            var ray = new UnityEngine.Ray(cam.transform.position, (rend.bounds.center - cam.transform.position).normalized);
            int n = Cozy.Grid.RayPick.Sorted(ray, 25f, hits);
            for (int i = 0; i < n; i++)
            {
                var col = hits[i].collider;
                if (col.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io) continue;
                var cand = col.GetComponentInParent<Cozy.Grid.IInteractable>();
                if (!(bool)skip.Invoke(null, new object[] { col, cand }))
                    bad.Append("наводится сквозь закрытую секцию: " + io.Def.id + "; ");
                break;
            }
        }
    }
    // 2. Жидкости не больше ёмкости.
    if (io.Liquid != null && io.Liquid.Litres > io.Liquid.Capacity + 0.001f)
        bad.Append("перелив: " + io.Def.id + "; ");
    // 3. Ни одного объекта без видимых мешей.
    int visible = 0;
    foreach (var r in io.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
        if (r.enabled && r.gameObject.activeInHierarchy && !r.name.StartsWith("Outline")) visible++;
    if (visible == 0) bad.Append("невидимый объект: " + io.Def.id + "; ");
    // 4. Вложенный предмет знает своего хозяина: без Container правило
    //    «в закрытой секции не трогают» слепнет.
    if (io.transform.parent != null && io.Container == null
        && io.transform.parent.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null
        && io.transform.parent.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io)
        bad.Append("вложен, но без Container: " + io.Def.id + "; ");
}
// 5. Подвес шкафа свободен ровно тогда, когда под ним нет лампы того же
//    семейства: занятость считают только родственные по snapToNode объекты
//    (P117: мойка «занимала» подвес раздутым габаритом).
var gc = Cozy.Grid.GridCursor.I;
var mountTaken = gc != null ? gc.GetType().GetMethod("MountTaken", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance) : null;
int mounts = 0;
if (mountTaken != null)
    foreach (var host in Cozy.Grid.InteractiveObject.All)
    {
        if (host == null || host.Def == null || !host.Def.id.StartsWith("home_wall_cabinet")) continue;
        foreach (var node in host.GetComponentsInChildren<UnityEngine.Transform>(true))
        {
            if (!node.name.StartsWith("Mount_Light")) continue;
            mounts++;
            bool lampThere = false;
            foreach (var lamp in Cozy.Grid.InteractiveObject.All)
            {
                if (lamp == null || lamp.Def == null || !lamp.Def.id.StartsWith("home_under_light")) continue;
                var lb = lamp.WorldBounds; lb.Expand(0.2f);
                if (lb.Contains(node.position) || (lamp.transform.position - node.position).sqrMagnitude < 0.04f) { lampThere = true; break; }
            }
            bool taken = (bool)mountTaken.Invoke(gc, new object[] { node.position, "Mount_Light", null });
            if (taken != lampThere) bad.Append("подвес " + node.name + " у " + host.Def.id + ": занят=" + taken + ", лампа=" + lampThere + "; ");
        }
    }
return "объектов=" + checkedObjects + " в закрытых секциях=" + closed + " подвесов=" + mounts + " :: "
     + (bad.Length == 0 ? "инварианты держатся" : bad.ToString());
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    data = json.loads(line)
    print(data.get("data", {}).get("result") or json.dumps(data, ensure_ascii=False)[:400])


if __name__ == '__main__':
    main()
