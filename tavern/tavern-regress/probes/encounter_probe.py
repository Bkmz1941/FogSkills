"""Характеризующий замер стычки: правила сцен, треки из Blender, исход сцен в живой игре.

Всё, что здесь печатается, обязано быть ДЕТЕРМИНИРОВАННЫМ: замер снимается до
правки и после, строки сверяются посимвольно (`diff`). Числа, которые плывут
сами (энергия восстанавливается, жизнь подтекает от среды, мировые координаты
зависят от разворота игрока), либо не печатаются, либо огрублены.

    python3 encounter_probe.py rules    таблица сцен: урон, проверка, варианты, гейт по энергии, смерть, камера
    python3 encounter_probe.py track    треки птицы и камеры из crowEncounter.json по кадрам
    python3 encounter_probe.py scenes   каждая развязка в живой игре: цепочка сцен, жизнь, ошеломление
    python3 encounter_probe.py scenes --moves   то же плюс сдвиг игрока в его осях и разворот — НЕ детерминирован
                                        (ворона заходит откуда была, опрос раз в 0.4 с): смотреть глазами, не diff
    python3 encounter_probe.py fps      кадр и мусор в РЕДАКТОРЕ: покой против удержания решения сцены 1 спереди и сзади
                                        (сцена на паузе, камера стычки). Сборка этот кадр не видит — меряет спавн
    python3 encounter_probe.py all      rules, track, scenes

Переписана 16.09 под таблицу `CrowEncounter.Scenes` (прежняя звала снятые
`BraceEffect`/`GuardEffect` и ползунки крыльев и молча не работала с ночи 15→16.09).
⚠️ Редактор должен быть в play И НЕ НА ПАУЗЕ (P407). Нужна ворона на уровне
(crown_attack): без неё `scenes` честно скажет «не стартовала».
"""
import json, math, subprocess, sys, time, pathlib

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
SCENES = ['brace', 'guard', 'dodge', 'hit', 'fall', 'back', 'backDodge', 'backHit']


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        res = (d.get('data') or {}).get('result')
        return (res if res is not None else d.get('message') or d.get('error') or '').strip()
    except Exception:
        return 'НЕ РАЗОБРАЛОСЬ: ' + line[:300]


IDS = 'new[] { %s }' % ', '.join('"%s"' % s for s in SCENES)

RULES = r'''
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
float keepE = st.Energy, keepH = st.Health;
var inv = System.Globalization.CultureInfo.InvariantCulture;
string s = "";
foreach (var stat in new[] { Cozy.Combat.SceneCheck.Strength, Cozy.Combat.SceneCheck.Agility })
    s += "стат " + stat + "=" + Cozy.Combat.CrowEncounter.StatOf(stat).ToString("0.##", inv) + "\n";
foreach (var id in IDS)
{
    var e = Cozy.Combat.CrowEncounter.EffectOf(id);
    var rec = Cozy.Combat.CrowEncounter.RecoveryOf(id);
    s += id + ": урон hp=" + e.Health.ToString("0.##", inv) + " en=" + e.Energy.ToString("0.##", inv)
       + " оглушает=" + e.Stuns + " на кнопке hp=" + e.ShowHealth + " en=" + e.ShowEnergy
       + " решаем=" + Cozy.Combat.CrowEncounter.Decides(id)
       + " таймаут=" + (Cozy.Combat.CrowEncounter.TimeoutOf(id) ?? "-")
       + " постановка=" + Cozy.Combat.CrowEncounter.StageOf(id)
       + " лёжа=" + Cozy.Combat.CrowEncounter.EndsFallen(id) + " (" + rec.Item1 + "/" + rec.Item2 + ")"
       + " замедление=" + Cozy.Combat.CrowEncounter.SlowOf(id).ToString("0.##", inv) + "\n";
    var check = Cozy.Combat.CrowEncounter.CheckOf(id);
    if (check != null) s += "   проверка " + check.Stat + " сложность=" + check.Difficulty.ToString("0.##", inv) + "\n";
    var cam = Cozy.Combat.CrowEncounter.CamOf(id);
    s += "   камера " + (cam == null ? "общая" : "своя") + "\n";
    foreach (var c in Cozy.Combat.CrowEncounter.ChoicesOf(id))
    {
        s += "   вариант " + c.Id + " слот=" + c.Slot + " «" + c.Label + "» → " + c.Next
           + " шанс=" + Cozy.Combat.CrowEncounter.ChanceOf(c).ToString("0.##", inv) + " по энергии:";
        foreach (var en in new[] { 100f, 25f, 10f })
        {
            st.SetEnergy(en);
            s += " " + en + "=" + Cozy.Combat.CrowEncounter.Affordable(c);
        }
        s += "\n";
    }
    foreach (var hp in new[] { 100f, 25f })
    {
        st.SetHealth(hp);
        s += "   при жизни " + hp + " смерть→" + Cozy.Combat.CrowEncounter.Lethal(id) + "\n";
    }
    st.SetEnergy(100f); st.SetHealth(100f);
    Cozy.Combat.CrowEncounter.Apply(id);
    s += "   Apply: hp=" + st.Health.ToString("0.##", inv) + " en=" + st.Energy.ToString("0.##", inv) + "\n";
}
st.SetEnergy(keepE); st.SetHealth(keepH);
return s;
'''.replace('IDS', IDS)

TRACK = r'''
var data = Cozy.Combat.EncounterData.Load();
var inv = System.Globalization.CultureInfo.InvariantCulture;
string s = "голова=" + data.headCenter.Local.ToString("F4") + " шов=" + (data.crowSeam != null ? data.crowSeam.Local.ToString("F4") : "-") + "\n";
foreach (var scene in data.scenes)
{
    s += scene.id + " клип=" + scene.clip + " кадров=" + scene.frames + " fps=" + scene.fps + " сек=" + scene.Seconds.ToString("0.000", inv)
       + " смешение камеры=" + scene.cameraBlendFrames + " настраиваемая=" + scene.Tunable + " таз=" + scene.HasHips + "\n";
    int last = System.Math.Max(1, scene.frames);
    foreach (var f in new[] { 1f, last * 0.25f, last * 0.5f, last * 0.75f, (float)last })
    {
        var p = scene.CrowAt(f);
        s += "   к" + f.ToString("0.##", inv) + " pos=" + p.Pos.ToString("F4") + " dive=" + p.Dive.ToString("0.###", inv)
           + " yaw=" + p.Yaw.ToString("0.###", inv) + " roll=" + p.Roll.ToString("0.###", inv)
           + " flap=" + p.Flap.ToString("0.###", inv) + " tail=" + p.Tail.ToString("0.###", inv)
           + " legs=" + p.Legs.ToString("0.###", inv) + " aim=" + p.HeadAim.ToString("0.###", inv)
           + " beak=" + p.Beak.ToString("0.###", inv) + "\n";
        Vector3 cp, cl; float lens;
        if (scene.CameraAt(f, out cp, out cl, out lens))
            s += "      кам=" + cp.ToString("F4") + " смотрит=" + cl.ToString("F4") + " объектив=" + lens.ToString("0.##", inv) + "\n";
    }
}
return s;
'''

START = r'''
if (Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
Cozy.Combat.CrowAttack.CancelCurrent();
var p = Cozy.Grid.PlayerRef.Transform;
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
st.SetEnergy(100f); st.SetHealth(100f);
Cozy.Combat.CrowAttack.StartAt("SCENE");
var inv = System.Globalization.CultureInfo.InvariantCulture;
return p.position.x.ToString("R", inv) + ";" + p.position.z.ToString("R", inv) + ";" + p.eulerAngles.y.ToString("R", inv);
'''

READ = r'''
var p = Cozy.Grid.PlayerRef.Transform;
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
var inv = System.Globalization.CultureInfo.InvariantCulture;
return Cozy.Combat.Encounter.Running + ";" + (Cozy.Combat.Encounter.SceneId ?? "-") + ";"
     + p.position.x.ToString("R", inv) + ";" + p.position.z.ToString("R", inv) + ";" + p.eulerAngles.y.ToString("R", inv) + ";"
     + st.Health.ToString("R", inv) + ";" + Cozy.Effects.PlayerExposure.Stunned + ";" + Cozy.Character.PlayerTarget.Ready;
'''

CLEAN = r'''
if (Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
Cozy.Combat.CrowAttack.CancelCurrent();
var st = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
st.SetEnergy(st.maxEnergy); st.SetHealth(st.maxHealth);
return "чисто, timeScale=" + Time.timeScale;
'''

OUTCOMES = ['guard', 'dodge', 'hit', 'backDodge', 'backHit']
MOVES = '--moves' in sys.argv


def outcome(scene):
    mark = run(START.replace('SCENE', scene)).split(';')
    if len(mark) != 3:
        return scene + ': НЕ СТАРТОВАЛА ' + str(mark)
    x0, z0, yaw0 = (float(v) for v in mark)
    seen, started, parts = [], False, []
    for _ in range(90):
        parts = run(READ).split(';')
        if len(parts) != 8:
            time.sleep(0.4)
            continue
        running, sid = parts[0].lower().startswith('t'), parts[1]
        if running:
            started = True
            if sid != '-' and (not seen or seen[-1] != sid):
                seen.append(sid)
            time.sleep(0.4)
            continue
        if not started:
            time.sleep(0.4)
            continue
        x, z, yaw, hp = (float(v) for v in parts[2:6])
        dyaw = (yaw - yaw0 + 540.0) % 360.0 - 180.0
        rad = math.radians(yaw0)
        dx, dz = x - x0, z - z0
        side = dx * math.cos(rad) - dz * math.sin(rad)
        ahead = dx * math.sin(rad) + dz * math.cos(rad)
        line = '%s: сцены=%s жизнь≈%d оглушён=%s' % (scene, '→'.join(seen), round(hp / 10.0) * 10, parts[6])
        if MOVES:
            line += ' | вбок=%.1f вперёд=%.1f разворот=%d' % (round(side, 1) + 0.0, round(ahead, 1) + 0.0, int(round(dyaw)))
        return line
    return scene + ': НЕ ДОИГРАЛАСЬ (стартовала=%s) %s' % (started, ';'.join(parts))


def wait_ready():
    for _ in range(60):
        parts = run(READ).split(';')
        if len(parts) == 8 and not parts[0].lower().startswith('t') and parts[7].lower().startswith('t') \
                and not parts[6].lower().startswith('t'):
            return True
        time.sleep(0.5)
    return False


FPS_START = r'''
if (Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
Cozy.Combat.CrowAttack.StartAt("SCENE");
return "go";
'''

FPS_HOLD = r'''
if (!Cozy.Combat.Encounter.Running) return "не идёт";
if (!Cozy.Combat.Encounter.Paused) Cozy.Combat.Encounter.TogglePause();
return Cozy.Combat.Encounter.SceneId;
'''


def fps(frames=120):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import gc_probe
    gc_probe.uncap(True)
    rows = []
    try:
        run(CLEAN)
        time.sleep(1.0)
        avg, mx, ms, p95 = gc_probe.measure(frames)
        print('покой            кадр %.2f мс, p95 %.2f, мусор %d Б' % (ms, p95, avg), flush=True)
        base = ms
        for scene in ('brace', 'back'):
            run(FPS_START.replace('SCENE', scene))
            time.sleep(1.2)
            held = run(FPS_HOLD)
            if held == 'не идёт':
                print('%-16s не стартовала' % scene)
                continue
            avg, mx, ms, p95 = gc_probe.measure(frames)
            print('%-16s кадр %.2f мс (%+.2f), p95 %.2f, мусор %d Б' % (scene + ' (' + held + ')', ms, ms - base, p95, avg), flush=True)
            run(CLEAN)
            wait_ready()
    finally:
        print(run(CLEAN))


def rules():
    print('--- правила сцен ---')
    print(run(RULES))


def track():
    print('--- треки птицы и камеры ---')
    print(run(TRACK))


def scenes():
    print('--- исход сцен ---')
    try:
        for scene in OUTCOMES:
            wait_ready()
            print(outcome(scene), flush=True)
    finally:
        print(run(CLEAN))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('rules', 'all'):
        rules()
    if what in ('track', 'all'):
        track()
    if what in ('scenes', 'all'):
        scenes()
    if what == 'fps':
        fps()
    if what not in ('rules', 'track', 'scenes', 'all', 'fps'):
        print(__doc__)
