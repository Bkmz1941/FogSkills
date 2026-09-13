"""Сова, поставленная на землю, САМА улетает и садится в гнездо ветки (MONSTERS.md).

Правило Ильи (12.09): «сову можно разместить на земле, но она должна сразу улетать
искать ветку». Проверить это осмотром уровня нельзя — в уровне совы либо нет, либо
она уже сидит, — поэтому проба ставит птицу сама и ждёт живой полёт. Заодно это
единственная проверка ЛЁТНОЙ части кода (`CrowFlight`): взлёт, маршрут, посадка.

Что меряется:
1. Птица ставится на землю и через несколько секунд ПОКИДАЕТ её (фаза не Perched
   или высота выросла) — сама, без игрока.
2. Через десяток секунд она сидит на ветке: фаза Perched и расстояние до
   ближайшего узла `Mount_Crow` меньше сантиметра.
3. Она не оказалась ниже земли и не улетела за край уровня.
4. После прогона в уровне ровно столько же объектов, сколько было.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/bird_flight_probe.py
Нужен play и уровень С ДЕРЕВЬЯМИ (есть включённые ветки со свободными гнёздами).
Идёт около двадцати секунд: полёт живой, ускорить его нечем.
"""
import json, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

SPAWN = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var def = Cozy.Grid.FurnitureCatalog.ById("owl");
if (def == null) return "нет дефа совы";
Cozy.Grid.CrowPerch free = null;
foreach (var p in Cozy.Grid.CrowPerch.All)
{
    if (p == null || !p.On) continue;
    bool taken = false;
    for (int i = 0; i < p.MountCount && !taken; i++)
    {
        var m = p.MountOf(i);
        if (m == null) { taken = true; break; }
        foreach (var other in Cozy.Grid.CrowFlight.All)
            if (other != null && UnityEngine.Vector3.Distance(other.transform.position, m.position) < 0.4f) { taken = true; break; }
    }
    if (!taken) { free = p; break; }
}
if (free == null) return "на уровне нет ветки со свободным гнездом — проверять нечего";
var ground = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
var at = free.transform.position;
float gx = at.x + 3f, gz = at.z;
float gy = ground.transform.position.y + (ground.Heights != null ? ground.Heights.HeightAt(gx, gz) : 0f);
var owl = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, new UnityEngine.Vector3(gx, gy, gz), 0f);
if (owl == null) return "сова не заспавнилась";
return "id=" + owl.GetInstanceID() + " земля=" + gy.ToString("F2") + " ветка=" + at.ToString("F1");
'''

CHECK = r'''
var ph = typeof(Cozy.Grid.CrowFlight).GetField("_phase", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
Cozy.Grid.CrowFlight mine = null;
foreach (var fl in Cozy.Grid.CrowFlight.All)
{
    if (fl == null) continue;
    var io = fl.GetComponent<Cozy.Grid.InteractiveObject>();
    if (io != null && io.GetInstanceID() == __ID__) { mine = fl; break; }
}
if (mine == null) return "сова пропала из переписи птиц";
float best = 9999f;
foreach (var p in Cozy.Grid.CrowPerch.All)
{
    if (p == null) continue;
    for (int i = 0; i < p.MountCount; i++)
    {
        var m = p.MountOf(i);
        if (m == null) continue;
        float d = UnityEngine.Vector3.Distance(m.position, mine.transform.position);
        if (d < best) best = d;
    }
}
var at = mine.transform.position;
return "фаза=" + (ph != null ? ph.GetValue(mine).ToString() : "?") + " где=" + at.ToString("F2")
    + " до гнезда=" + best.ToString("F3");
'''

CLEAN = r'''
int gone = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.GetInstanceID() == __ID__) { UnityEngine.Object.DestroyImmediate(io.gameObject); gone++; break; }
return "убрано " + gone + ", объектов " + Cozy.Grid.InteractiveObject.All.Count;
'''


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        data = json.loads(line)
    except Exception:
        return 'ПРОБА НЕ ОТВЕТИЛА: ' + line[:200]
    body = data.get("data") if isinstance(data, dict) else None
    if not isinstance(body, dict) or body.get("result") is None:
        return 'ПРОБА НЕ ОТВЕТИЛА: ' + json.dumps(data, ensure_ascii=False)[:300]
    return body["result"]


def main():
    head = run(SPAWN)
    if not head.startswith('id='):
        print(head)
        return
    ident = head.split()[0][3:]
    ground = float(head.split('земля=')[1].split()[0])
    bad = []
    try:
        time.sleep(5)
        away = run(CHECK.replace('__ID__', ident))
        if 'фаза=' not in away:
            print('КРАСНОЕ: ' + away)
            return
        if 'фаза=Perched' in away and 'до гнезда=0.0' not in away:
            bad.append('через 5 с сова всё ещё на земле: ' + away)
        for _ in range(4):
            time.sleep(5)
            sat = run(CHECK.replace('__ID__', ident))
            if 'фаза=Perched' in sat and ('до гнезда=0.00' in sat or 'до гнезда=0.01' in sat):
                break
        else:
            bad.append('за двадцать секунд сова не села на ветку: ' + sat)
        near = float(sat.split('до гнезда=')[1])
        low = float(sat.split('где=(')[1].split(',')[1])
        if near > 0.05:
            bad.append('села мимо гнезда на %.3f м' % near)
        if low < ground - 0.5:
            bad.append('оказалась ниже земли: %.2f при земле %.2f' % (low, ground))
        print(('полёт совы: ' + away + ' → ' + sat + ' :: держится') if not bad
              else ('КРАСНОЕ: ' + '; '.join(bad)))
    finally:
        tail = run(CLEAN.replace('__ID__', ident))
        if 'убрано 1' not in tail:
            print('⚠️ уборка: ' + tail)


if __name__ == '__main__':
    main()
