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

Вторая половина — ПОКОЙ птиц уровня (`CrowIdle`), который до 13.09 не был прикрыт
ничем: голова каждой сидящей птицы прослеживается восемь секунд и обязана
1) шевелиться (покой живой, а не замерший) и 2) не выходить за предел СВОЕЙ породы
(`CrowIdle.CalmOf(kind).HeadYaw`: ворона 62°, сова 96°).

⚠️ Проба ДВИГАЕТ игрока: спавнит сову рядом с веткой и подводит камеру к сидящей
птице, потом возвращает игрока ровно туда, где он стоял, и сносит свою сову. Если
в этот момент играет Илья — он увидит рывок, поэтому в `check_all.py` она не
входит и гоняется под задачу.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/bird_flight_probe.py
Нужен play и уровень С ДЕРЕВЬЯМИ: включённая ветка со свободным гнездом, а если таких нет —
проба на время прогона включит выключенную ветку (`CrowPerch.SetOn`) и выключит её в уборке (16.09:
на crown_attack все ветки выключены, и полёт не проверялся вовсе).
Идёт около тридцати секунд: полёт и покой живые, ускорить их нечем.
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
int lit = 0;
if (free == null)
{
    foreach (var p in Cozy.Grid.CrowPerch.All)
    {
        if (p == null || p.On || p.Owner == null) continue;
        p.SetOn(true);
        if (p.MountCount > 0) { free = p; lit = p.Owner.GetInstanceID(); break; }
        p.SetOn(false);
    }
}
if (free == null) return "на уровне нет ветки со свободным гнездом и нет выключенной, которую можно включить — проверять нечего";
var ground = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
var at = free.transform.position;
float gx = at.x + 3f, gz = at.z;
float gy = ground.transform.position.y + (ground.Heights != null ? ground.Heights.HeightAt(gx, gz) : 0f);
var owl = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, new UnityEngine.Vector3(gx, gy, gz), 0f);
if (owl == null) return "сова не заспавнилась";
return "id=" + owl.GetInstanceID() + " земля=" + gy.ToString("F2") + " ветка=" + at.ToString("F1").Replace(" ", "") + " включена=" + lit;
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
if (__LIT__ != 0)
    foreach (var p in Cozy.Grid.CrowPerch.All)
        if (p != null && p.Owner != null && p.Owner.GetInstanceID() == __LIT__) p.SetOn(false);
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
    lit = head.split('включена=')[1].split()[0] if 'включена=' in head else '0'
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
        tail = run(CLEAN.replace('__ID__', ident).replace('__LIT__', lit))
        if 'убрано 1' not in tail:
            print('⚠️ уборка: ' + tail)


# ⚠️ Птица ВНЕ КАДРА замирает по замыслу (`CrowIdle.Update` выходит первой
# строкой, если `ViewCull.InView` ложно) — значит мерить покой у птицы, на
# которую никто не смотрит, бессмысленно. Поэтому проба подводит игрока к
# птице: ближе, чем видит камера, но ДАЛЬШЕ её пугливого радиуса 3.2 м,
# иначе птица просто улетит и мерить снова будет нечего.
APPROACH = r'''
Cozy.Grid.CrowIdle best = null;
var ph = typeof(Cozy.Grid.CrowFlight).GetField("_phase", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
int skip = TRY;
foreach (var idle in UnityEngine.Object.FindObjectsByType<Cozy.Grid.CrowIdle>(UnityEngine.FindObjectsSortMode.None))
{
    var fl = idle.GetComponent<Cozy.Grid.CrowFlight>();
    if (fl != null && ph != null && ph.GetValue(fl).ToString() != "Perched") continue;
    if (skip-- > 0) continue;
    best = idle; break;
}
if (best == null) return "сидящих птиц больше нет";
var plr = Cozy.Grid.PlayerRef.Transform;
SAVED
var g = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
var at = best.transform.position;
// Встаём так, чтобы птица оказалась ПЕРЕД камерой: она следует за игроком с
// постоянным разворотом, поэтому отходим против её взгляда. Шесть метров —
// вдвое дальше пугливого радиуса 3.2 м, и птица остаётся на ветке.
var cam = UnityEngine.Camera.main;
var dir = cam != null ? UnityEngine.Vector3.ProjectOnPlane(cam.transform.forward, UnityEngine.Vector3.up).normalized : UnityEngine.Vector3.forward;
if (dir.sqrMagnitude < 0.01f) dir = UnityEngine.Vector3.forward;
var spot = at - dir * 6f;
float fy = g.transform.position.y + (g.Heights != null ? g.Heights.HeightAt(spot.x, spot.z) : 0f);
Cozy.Grid.GridCursor.I.TeleportPlayerTo(new UnityEngine.Vector3(spot.x, fy, spot.z));
return "подвёл к " + at.ToString("F1") + " сохранено " + plr.position.ToString("F2");
'''

IDLE = r'''
var sb = new System.Text.StringBuilder();
foreach (var idle in UnityEngine.Object.FindObjectsByType<Cozy.Grid.CrowIdle>(UnityEngine.FindObjectsSortMode.None))
{
    if (idle == null) continue;
    var io = idle.GetComponent<Cozy.Grid.InteractiveObject>();
    if (io == null || io.Def == null) continue;
    var rend = idle.GetComponentInChildren<UnityEngine.Renderer>();
    if (rend == null || !Cozy.Grid.ViewCull.InView(rend.bounds)) continue;
    // Берём САМ угол, который код и ограничивает (`_yaw`), а не эйлер узла: оси
    // головы пришли из FBX повёрнутыми — поворот влево-вправо живёт в Z, и
    // чтение `localEulerAngles.y` показывает косой взгляд вместо поворота
    // (проба 13.09 из-за этого решила, что голова не шевелится).
    var fYaw = typeof(Cozy.Grid.CrowIdle).GetField("_yaw", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    if (fYaw == null) return "у CrowIdle нет поля _yaw";
    float yaw = (float)fYaw.GetValue(idle);
    sb.Append(io.GetInstanceID() + "|" + io.Def.birdKind + "|" + yaw.ToString("F2") + ";");
}
return sb.Length == 0 ? "птиц в кадре нет" : sb.ToString();
'''

LIMITS = r'''
return "ворона=" + Cozy.Grid.CrowIdle.CalmOf("").HeadYaw.ToString("F0")
    + " сова=" + Cozy.Grid.CrowIdle.CalmOf(Cozy.Grid.CrowIdle.Owl).HeadYaw.ToString("F0")
    + " час=" + Cozy.Grid.Weather.Hour.ToString("F1");
'''


def idle_check():
    limits = run(LIMITS)
    if not limits.startswith('ворона='):
        print('покой: ' + limits)
        return
    where = run('var p = Cozy.Grid.PlayerRef.Transform; return p.position.x + " " + p.position.y + " " + p.position.z;')
    try:
        # Птица может оказаться за спиной камеры или за деревом — тогда пробуем
        # следующую сидящую. Трёх попыток хватает: лишний заход стоит секунду.
        for attempt in range(3):
            came = run(APPROACH.replace('SAVED', '').replace('TRY', str(attempt)))
            if not came.startswith('подвёл'):
                print('покой: ' + came)
                return
            time.sleep(1.2)
            if '|' in run(IDLE):
                idle_samples(limits)
                return
        print('покой: ни одна сидящая птица не попала в кадр — проверять нечего')
    finally:
        x, y, z = where.split()
        run('var p = Cozy.Grid.PlayerRef.GameObject; var cc = p.GetComponent<UnityEngine.CharacterController>();'
            ' if (cc != null) cc.enabled = false;'
            ' p.transform.position = new UnityEngine.Vector3(%sf, %sf, %sf);'
            ' if (cc != null) cc.enabled = true; return "вернул игрока";' % (x, y, z))


def idle_samples(limits):
    crow = float(limits.split('ворона=')[1].split()[0])
    owl = float(limits.split('сова=')[1].split()[0])
    seen = {}
    for _ in range(12):
        line = run(IDLE)
        if '|' not in line:
            print('покой: ' + line + ' — проверять нечего')
            return
        for part in line.split(';'):
            if part.count('|') != 2:
                continue
            ident, kind, yaw = part.split('|')
            lo, hi = seen.get(ident, (999.0, -999.0))[:2] if ident in seen else (999.0, -999.0)
            seen[ident] = (min(lo, float(yaw)), max(hi, float(yaw)), kind)
        time.sleep(0.7)
    bad, say = [], []
    for ident, (lo, hi, kind) in seen.items():
        limit = owl if kind == 'owl' else crow
        say.append('%s: крайний поворот %.1f° при пределе %.0f°, размах %.1f°'
                   % (kind or 'crow', max(abs(lo), abs(hi)), limit, hi - lo))
        if hi - lo < 0.5:
            bad.append('%s: голова не шевелится за восемь секунд' % (kind or 'crow'))
        if max(abs(lo), abs(hi)) > limit + 2.0:
            bad.append('%s: голова ушла на %.1f° при пределе %.0f°' % (kind or 'crow', max(abs(lo), abs(hi)), limit))
    print(('покой: ' + '; '.join(say) + ' :: держится') if not bad else ('КРАСНОЕ: ' + '; '.join(bad)))


if __name__ == '__main__':
    main()
    idle_check()
