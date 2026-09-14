"""Характеризующий замер стычки: числа сцен, гейт по энергии, плашки цены, треки птицы и камеры, исход развязок.

Всё, что здесь печатается, обязано быть ДЕТЕРМИНИРОВАННЫМ: замер снимается до
правки и после, строки сверяются посимвольно (`diff`). Числа, которые плывут
сами (энергия восстанавливается, жизнь подтекает от среды, мировые координаты
зависят от разворота игрока), либо не печатаются, либо огрублены — см. ниже.

    python3 encounter_probe.py effects   эффекты сцен, гейт, плашки под кнопками
    python3 encounter_probe.py core      треки птицы и камеры, крылья, исход трёх развязок
    python3 encounter_probe.py all       и то и другое

⚠️ Редактор должен быть в play И НЕ НА ПАУЗЕ (P407): в паузе мост отвечает, а
мир стоит, и замер разойдётся по всем строкам сразу. Проверить —
`python3 cycle.py status`.
"""
import json, math, subprocess, sys, time, pathlib

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
SETTLE = 2.0


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        return ((json.loads(line).get('data') or {}).get('result') or '').strip()
    except Exception:
        return 'НЕ РАЗОБРАЛОСЬ: ' + line[:200]


NUMBERS = r'''
string s = "";
s += "brace: hp=" + Cozy.Combat.BraceEffect.Health + " en=" + Cozy.Combat.BraceEffect.Energy
   + " showHp=" + Cozy.Combat.BraceEffect.ShowHealth + " showEn=" + Cozy.Combat.BraceEffect.ShowEnergy + "\n";
s += "guard: hp=" + Cozy.Combat.GuardEffect.Health + " en=" + Cozy.Combat.GuardEffect.Energy
   + " showHp=" + Cozy.Combat.GuardEffect.ShowHealth + " showEn=" + Cozy.Combat.GuardEffect.ShowEnergy + "\n";
s += "dodge: hp=" + Cozy.Combat.DodgeEffect.Health + " en=" + Cozy.Combat.DodgeEffect.Energy
   + " showHp=" + Cozy.Combat.DodgeEffect.ShowHealth + " showEn=" + Cozy.Combat.DodgeEffect.ShowEnergy + "\n";
s += "hit: hp=" + Cozy.Combat.HitEffect.Health + " en=" + Cozy.Combat.HitEffect.Energy
   + " showHp=" + Cozy.Combat.HitEffect.ShowHealth + " showEn=" + Cozy.Combat.HitEffect.ShowEnergy + "\n";
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
float keepE = st.Energy, keepH = st.Health;
foreach (var e in new[] { 100f, 25f, 10f })
{
    st.SetEnergy(e);
    s += "энергия " + e + ":";
    foreach (var c in Cozy.Combat.CrowEncounter.ChoicesOf("brace"))
        s += " " + c.Id + "=" + Cozy.Combat.CrowEncounter.Affordable(c);
    s += "\n";
}
st.SetEnergy(keepE); st.SetHealth(keepH);
s += "decides: brace=" + Cozy.Combat.CrowEncounter.Decides("brace")
   + " guard=" + Cozy.Combat.CrowEncounter.Decides("guard")
   + " dodge=" + Cozy.Combat.CrowEncounter.Decides("dodge")
   + " hit=" + Cozy.Combat.CrowEncounter.Decides("hit") + "\n";
s += "таймаут brace=" + Cozy.Combat.CrowEncounter.TimeoutOf("brace")
   + " guard=" + (Cozy.Combat.CrowEncounter.TimeoutOf("guard") ?? "нет") + "\n";
foreach (var id in new[] { "guard", "dodge", "hit" })
{
    st.SetEnergy(100f); st.SetHealth(100f);
    Cozy.Combat.CrowEncounter.Apply(id);
    s += "Apply(" + id + "): hp=" + st.Health + " en=" + st.Energy + "\n";
}
st.SetEnergy(keepE); st.SetHealth(keepH);
return s;
'''

START = r'''
Cozy.Combat.CrowAttack.CancelCurrent();
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
st.SetEnergy(100f); st.SetHealth(100f);
Cozy.Combat.CrowAttack.StartScene1();
return "go";
'''

CHIPS = r'''
if (Cozy.Combat.Encounter.Running && !Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
var canvas = GameObject.Find("EncounterChoicesCanvas");
string s = "сцена=" + Cozy.Combat.Encounter.SceneId + " решаем=" + Cozy.Combat.Encounter.Deciding + "\n";
foreach (var rt in canvas.GetComponentsInChildren<RectTransform>(true))
{
    if (rt.name != "Cost") continue;
    var text = rt.GetComponentsInChildren<TMPro.TMP_Text>(true);
    string value = text.Length > 1 ? text[1].text : "?";
    s += rt.parent.name + " плашка: видна=" + rt.gameObject.activeSelf
       + " число=" + value
       + " w=" + rt.sizeDelta.x.ToString("0.00")
       + " x=" + rt.anchoredPosition.x.ToString("0.00")
       + " y=" + rt.anchoredPosition.y.ToString("0.00")
       + " alpha=" + (text.Length > 0 ? text[0].color.a.ToString("0.00") : "?") + "\n";
}
return s;
'''

CLEAN = r'''
if (Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
Cozy.Combat.CrowAttack.CancelCurrent();
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
st.SetEnergy(st.maxEnergy); st.SetHealth(st.maxHealth);
return "чисто, timeScale=" + Time.timeScale;
'''

TRACK = r'''
var data = Cozy.Combat.EncounterData.Load();
string s = "";
foreach (var id in new[] { "brace", "guard", "dodge", "hit" })
{
    var scene = data.Scene(id);
    if (scene == null) { s += id + ": нет сцены\n"; continue; }
    s += id + " кадров=" + scene.frames + " fps=" + scene.fps + " сек=" + scene.Seconds.ToString("0.000")
       + " настраиваемая=" + scene.Tunable + "\n";
    foreach (var f in new[] { 1f, 12f, 24f, 60f, 132f })
    {
        var p = scene.CrowAt(f);
        s += "   к" + f + " pos=" + p.Pos.ToString("F4") + " dive=" + p.Dive.ToString("0.###")
           + " yaw=" + p.Yaw.ToString("0.###") + " roll=" + p.Roll.ToString("0.###")
           + " flap=" + p.Flap.ToString("0.###") + " twist=" + p.Twist.ToString("0.###")
           + " sweep=" + p.Sweep.ToString("0.###") + " tail=" + p.Tail.ToString("0.###")
           + " legs=" + p.Legs.ToString("0.###") + " aim=" + p.HeadAim.ToString("0.###")
           + " beak=" + p.Beak.ToString("0.###") + "\n";
        if (scene.CameraAt(f, out Vector3 cp, out Vector3 cl, out float lens))
            s += "      кам=" + cp.ToString("F4") + " смотрит=" + cl.ToString("F4") + " объектив=" + lens.ToString("0.##") + "\n";
    }
}
return s;
'''

WINGS_START = r'''
Cozy.Combat.CrowAttack.CancelCurrent();
Cozy.Combat.CrowAttack.DiveFlapHz = 0f;
Cozy.Combat.CrowAttack.StartScene1();
return "go";
'''

WINGS_READ = r'''
if (Cozy.Combat.Encounter.Running && !Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
string s = "мах выключен, сцена=" + Cozy.Combat.Encounter.SceneId + "\n";
var wings = new System.Collections.Generic.List<string>();
foreach (var t in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsSortMode.None))
{
    if (t.name != "WingLFly" && t.name != "WingRFly") continue;
    wings.Add(t.name + " local=" + t.localEulerAngles.ToString("F2"));
}
wings.Sort(System.StringComparer.Ordinal);
foreach (var w in wings) s += w + "\n";
s += "ползунки: lift=" + Cozy.Combat.CrowAttack.WingLift + " twist=" + Cozy.Combat.CrowAttack.WingTwist
   + " sweep=" + Cozy.Combat.CrowAttack.WingSweep + "\n";
return s;
'''

OUTCOME_START = r'''
if (Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
Cozy.Combat.CrowAttack.CancelCurrent();
var p = Cozy.Grid.PlayerRef.Transform;
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
st.SetEnergy(100f); st.SetHealth(100f);
string mark = p.position.x + ";" + p.position.z + ";" + p.eulerAngles.y;
Cozy.Combat.CrowAttack.StartAt("SCENE");
return mark;
'''

OUTCOME_READ = r'''
var p = Cozy.Grid.PlayerRef.Transform;
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
return Cozy.Combat.Encounter.Running + ";" + p.position.x + ";" + p.position.z + ";" + p.eulerAngles.y + ";" + st.Health;
'''

def outcome(scene):
    mark = run(OUTCOME_START.replace('SCENE', scene)).split(';')
    if len(mark) != 3:
        return scene + ': НЕ СТАРТОВАЛА ' + str(mark)
    x0, z0, yaw0 = (float(v) for v in mark)
    started = False
    line = ''
    for _ in range(60):
        line = run(OUTCOME_READ)
        parts = line.split(';')
        if len(parts) != 5:
            time.sleep(0.4)
            continue
        running = parts[0].lower().startswith('t')
        if running:
            started = True
            time.sleep(0.4)
            continue
        if not started:
            time.sleep(0.4)
            continue
        x, z, yaw, hp = (float(v) for v in parts[1:])
        dyaw = (yaw - yaw0 + 540.0) % 360.0 - 180.0
        rad = math.radians(yaw0)
        dx, dz = x - x0, z - z0
        side = dx * math.cos(rad) - dz * math.sin(rad)
        ahead = dx * math.sin(rad) + dz * math.cos(rad)
        return '%s: вбок=%.2f вперёд=%.2f разворот=%.0f жизнь≈%d' % (
            scene, side + 0.0, ahead + 0.0, dyaw + 0.0, round(hp / 10.0) * 10)
    return scene + ': НЕ ДОИГРАЛАСЬ (стартовала=%s) %s' % (started, line)


def effects():
    print('--- числа и гейт ---')
    print(run(NUMBERS))
    run(START)
    time.sleep(SETTLE)
    print('--- плашки под кнопками ---')
    print(run(CHIPS))
    print('--- уборка ---')
    print(run(CLEAN))


def core():
    print('--- треки птицы и камеры по кадрам ---')
    print(run(TRACK))
    print('--- крылья сцены 1 без маха ---')
    run(WINGS_START)
    time.sleep(SETTLE)
    print(run(WINGS_READ))
    print('--- исход развязок ---')
    for scene in ('guard', 'dodge', 'hit'):
        print(outcome(scene))
    print('--- уборка ---')
    print(run(CORE_CLEAN))


CORE_CLEAN = r'''
if (Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
Cozy.Combat.CrowAttack.CancelCurrent();
Cozy.Combat.CrowAttack.DiveFlapHz = 8f;
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
st.SetEnergy(st.maxEnergy); st.SetHealth(st.maxHealth);
return "чисто, мах=" + Cozy.Combat.CrowAttack.DiveFlapHz + " timeScale=" + Time.timeScale;
'''


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('effects', 'all'):
        effects()
    if what in ('core', 'all'):
        core()
