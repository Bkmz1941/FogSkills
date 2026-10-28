"""Лежачий предмет ложится ПО СКЛОНУ и не тонет в грунте (инвариант 153, P365).

Правило проверяется ДЕЙСТВИЕМ, а не осмотром уровня: у Ильи рельеф есть только в
лесу, а наклоняемые вещи (еда и одежда) лежат в доме, где земля плоская, — пассивный
обход не увидел бы механизм ни на одном уровне. Поэтому проба сама ставит сумку на
самый крутой склон загруженного уровня, меряет и всё за собой убирает.

Что меряется:
1. Модель довёрнута по нормали рельефа на min(склон, 18°) — наклон живёт в МОДЕЛИ.
2. Сам объект остался с чистым yaw: поза, габариты и прижимы считаются одним углом,
   и наклон не имеет права в них просочиться.
3. Низ предмета не ушёл под опору: после доворота вокруг точки опоры нижний угол
   поднимается обратно (у сумки было 1.8 см под землёй).
4. На ровном месте наклона нет вовсе.
5. Объект БЕЗ признака наклона на том же склоне не наклоняется.

Запуск: python3 ~/.claude/skills/tavern-regress/probes/tilt_probe.py
Нужен play и уровень с рельефом (лес). На плоском уровне проба честно говорит, что
проверять нечего, и не считается зелёной.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var ground = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
var heights = ground != null ? ground.Heights : null;
if (heights == null) return "нет поля высот";
if (heights.Flat) return "уровень плоский (" + Cozy.Grid.LevelIO.CurrentLevelName + ") — наклон тут не работает по замыслу, проверять нечего";

var bagDef = Cozy.Grid.FurnitureCatalog.ById("sport_bag");
if (bagDef == null) return "КРАСНОЕ: нет дефа sport_bag";
if (!bagDef.TiltsToGround) return "КРАСНОЕ: sport_bag потерял признак наклона";
Cozy.Grid.ObjectDef plainDef = null;
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && !d.TiltsToGround && d.freePlace && d.mount == Cozy.Grid.ObjectMount.Surface) { plainDef = d; break; }

float baseY = ground.transform.position.y;
var steepAt = UnityEngine.Vector3.zero; float steep = 0f;
var flatAt = UnityEngine.Vector3.zero; bool haveFlat = false;
for (float x = heights.MinX + 3f; x < heights.MinX + heights.NodesX - 3f; x += 2f)
for (float z = heights.MinZ + 3f; z < heights.MinZ + heights.NodesZ - 3f; z += 2f)
{
    float a = UnityEngine.Vector3.Angle(UnityEngine.Vector3.up, heights.Normal(x, z));
    if (a > steep) { steep = a; steepAt = new UnityEngine.Vector3(x, baseY + heights.HeightAt(x, z), z); }
    if (!haveFlat && a < 0.2f) { haveFlat = true; flatAt = new UnityEngine.Vector3(x, baseY + heights.HeightAt(x, z), z); }
}
if (steep < 2f) return "на уровне нет склона круче " + steep.ToString("F1") + "° — проверять нечего";

var before = new System.Collections.Generic.HashSet<int>();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None)) before.Add(io.GetInstanceID());
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var modelField = typeof(Cozy.Grid.InteractiveObject).GetField("_model", bf);
var restFlag = typeof(Cozy.Grid.InteractiveObject).GetField("_tiltRest", bf);
var restRot = typeof(Cozy.Grid.InteractiveObject).GetField("_tiltRestRot", bf);
if (modelField == null || restFlag == null || restRot == null) return "КРАСНОЕ: у InteractiveObject нет полей наклона";
var bad = new System.Text.StringBuilder();
var say = new System.Text.StringBuilder();
try
{
    for (int k = 0; k < 3; k++)
    {
        bool onSlope = k != 1;
        var def = k == 2 ? plainDef : bagDef;
        if (def == null) { say.Append("контрольного дефа без наклона в каталоге нет; "); continue; }
        var at = onSlope ? steepAt : flatAt;
        if (!onSlope && !haveFlat) { say.Append("ровного места на уровне нет, п.4 пропущен; "); continue; }
        var io = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, at, 0f);
        if (io == null) { bad.Append("не заспавнился " + def.id + "; "); continue; }
        var model = modelField.GetValue(io) as UnityEngine.GameObject;
        if (model == null) { bad.Append("нет модели у " + def.id + "; "); continue; }

        // Наклон меряется ДЕЛЬТОЙ от покоящейся позы самой модели: своя ось Y у
        // импортированного FBX смотрит куда угодно, и «up против мирового up»
        // даёт 90° даже на ровном месте.
        float slope = UnityEngine.Vector3.Angle(UnityEngine.Vector3.up, heights.Normal(at.x, at.z));
        bool tilted = (bool)restFlag.GetValue(io);
        float tilt = tilted ? UnityEngine.Quaternion.Angle(model.transform.localRotation, (UnityEngine.Quaternion)restRot.GetValue(io)) : 0f;
        float want = k == 2 ? 0f : UnityEngine.Mathf.Min(slope, 18f);
        if (UnityEngine.Mathf.Abs(tilt - want) > 0.6f)
            bad.Append((k == 2 ? "объект без признака наклонился" : onSlope ? "наклон не по склону" : "на ровном месте наклонён")
                + ": " + def.id + " склон " + slope.ToString("F1") + "° наклон " + tilt.ToString("F1") + "° ждали " + want.ToString("F1") + "°; ");

        var euler = io.transform.rotation.eulerAngles;
        float offYaw = UnityEngine.Mathf.Max(UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(euler.x, 0f)), UnityEngine.Mathf.Abs(UnityEngine.Mathf.DeltaAngle(euler.z, 0f)));
        if (offYaw > 0.1f) bad.Append("наклон просочился в сам объект: " + def.id + " крен " + offYaw.ToString("F2") + "°; ");

        var rends = io.GetComponentsInChildren<UnityEngine.Renderer>(true);
        float surface = ground.transform.position.y + heights.HeightAt(at.x, at.z);
        float under = surface - Cozy.Grid.FurnitureModel.Combined(rends).min.y;
        if (under > 0.002f) bad.Append("низ ушёл под опору: " + def.id + " на " + under.ToString("F3") + " м; ");
        say.Append(def.id + (onSlope ? " на склоне " : " на ровном ") + slope.ToString("F1") + "°: наклон " + tilt.ToString("F1")
            + "°, запас над опорой " + (-under).ToString("F3") + " м; ");
        UnityEngine.Object.DestroyImmediate(io.gameObject);
    }
}
finally
{
    foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        if (!before.Contains(io.GetInstanceID())) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return "уровень=" + Cozy.Grid.LevelIO.CurrentLevelName + " самый крутой склон " + steep.ToString("F1") + "° :: " + say.ToString()
     + (bad.Length == 0 ? ":: наклон по склону держится" : ":: КРАСНОЕ: " + bad.ToString());
'''


def main():
    code = '\n'.join(l.strip() for l in CODE.splitlines() if l.strip() and not l.strip().startswith('//'))
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    data = json.loads(line)
    body = data.get("data") if isinstance(data, dict) else None
    if not isinstance(body, dict) or not body.get("result"):
        print('ПРОБА НЕ ОТВЕТИЛА: ' + json.dumps(data, ensure_ascii=False)[:400])
        return
    print(body["result"])


if __name__ == '__main__':
    main()
