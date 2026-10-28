#!/usr/bin/env python3
"""Сценарии поведения зомби в play (ZOMBIE.md, ZB-S…): каждый ставит сцену кодом, ждёт, раз в полсекунды снимает
состояние и проверяет ожидание. Стенд — «Зомби (тест)» (zombie_test): комната x −49,5…−40,5, z −55,5…−46,5, дверь
door_1 в северной стене (−45; −46,5), окна запад (−49,5; −51), восток (−40,5; −51), юг (−45; −55,5); madman_1 появляется
правилом уровня. Правила подменяются В ПАМЯТИ (файл уровня не трогается), в конце — LevelIO.JoinScripts().

  python3 zombie_scenarios.py            # все
  python3 zombie_scenarios.py door_latched window_open   # выбранные
Нужен play на zombie_test (cycle.py play).
"""
import json, os, subprocess, sys, time

EX = os.path.expanduser('~/.claude/skills/tavern-night/ex.py')
TMP = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'zombie_scenarios')
os.makedirs(TMP, exist_ok=True)


def cs(code):
    path = os.path.join(TMP, 'run.cs')
    open(path, 'w').write(code)
    out = subprocess.run(['python3', EX, path], capture_output=True, text=True, timeout=120).stdout.strip()
    if out.startswith('{"success": false'):
        raise RuntimeError(out[:600])
    return out


DOOR_TREE = """
- [sees door]:
  - [unlocked]:
    - [unlatched]:
      [open]
    - [latched]:
      [knock]
  - [locked]:
    - [has key]:
      - [unlatched]:
        [open]
      - [latched]:
        [knock]
    - [no key]:
      [knock]"""
WINDOW_TREE = """
- [sees window]:
  - [closed]:
    [knock]
  - [open]:
    [climb]
  - [broken]:
    [climb]"""
BASE = "[madman_1]:\n1. [go][monster_zone_1][walk]\n\n[madman_1]"
CHASE = "\n- [while sees player priority 3]:\n  [track player]\n  [go][player]"

PRE = r'''
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var pl = Cozy.Grid.PlayerRef.Transform;
var cc = pl.GetComponent<UnityEngine.CharacterController>();
float feet = pl.position.y - Cozy.Character.PlayerTarget.Feet.y;
float ground = Cozy.Grid.GridCursor.I.GroundY(0f, 0f, 0f);
System.Action<float, float> Hero = (x, z) => { if (cc != null) cc.enabled = false; pl.position = new UnityEngine.Vector3(x, ground + feet, z); UnityEngine.Physics.SyncTransforms(); if (cc != null) cc.enabled = true; };
var door = Cozy.Grid.DoorPiece.All[0];
var acc = (Cozy.Grid.AccessFeature)typeof(Cozy.Grid.DoorPiece).GetField("_access", NP).GetValue(door);
System.Func<float, float, Cozy.Grid.WindowPiece> Win = (x, z) => { foreach (var wp in Cozy.Grid.WindowPiece.All) if (wp != null && System.Math.Abs(wp.transform.position.x - x) < 0.1f && System.Math.Abs(wp.transform.position.z - z) < 0.1f) return wp; return null; };
var io = Cozy.Grid.InteractiveObject.BySlug("madman_1");
'''

SETUP = PRE + r'''
Cozy.Combat.ZombieAttack.CancelCurrent();
foreach (var other in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
    if (other != null && other.SystemSlug == "zombie_probe_2") UnityEngine.Object.Destroy(other.gameObject);
var za = io.GetComponentInChildren<Cozy.Creatures.ZombieAnimation>();
za.Show = null;
// дверь: закрыта, отперта, без щеколды — потом сценарий своё
door.latched = false;
acc.Unlock();
acc.SetOpen(false);
typeof(Cozy.Grid.DoorPiece).GetField("_t", NP).SetValue(door, 0f);
typeof(Cozy.Grid.DoorPiece).GetMethod("Update", NP).Invoke(door, null);
foreach (var wp in Cozy.Grid.WindowPiece.All) if (wp != null) wp.SetOpen(false);
var eq = io.GetComponentInChildren<Cozy.Character.Equipment>();
foreach (var c in eq.Containers) { var k = c.grid.Find(it => it.def != null && it.def.keyCode != null && it.def.keyCode.Length > 0, 3); if (k != null) c.grid.Remove(k); }
Cozy.Character.PlayerTarget.AttacksOff = true;
%(scene)s
Cozy.Grid.LevelIO.AiRules = %(rules)s;
Cozy.Life.CreaturePlan.RestartAll();
Cozy.Life.LifeRules.RestartSchedule();   // тот же текст правил, что у прошлого сценария, — расписание групп заново
Cozy.Life.LifeRules.RunNow("сценарий");
%(after)s
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var jl = (System.Collections.IList)typeof(Cozy.Life.AiConsole).GetField("_journal", flags).GetValue(null);
var check = Cozy.Life.LifeRules.Check(Cozy.Grid.LevelIO.AiRules);
return jl.Count + "\n" + check;
'''

OBSERVE = PRE + r'''
var za = io.GetComponentInChildren<Cozy.Creatures.ZombieAnimation>();
var p = io.transform.position;
bool inRoom = p.x > -49.5f && p.x < -40.5f && p.z > -55.5f && p.z < -46.5f;
var d = new System.Collections.Generic.Dictionary<string, object> {
  {"t", UnityEngine.Time.time}, {"x", p.x}, {"z", p.z}, {"yaw", io.transform.eulerAngles.y},
  {"show", za.Show.HasValue ? za.Show.Value.ToString() : ""}, {"busy", za.Busy}, {"inRoom", inRoom},
  {"door_open", door.IsOpen}, {"door_latched", door.LatchShut}, {"door_locked", door.Locked},
  {"door_dist", UnityEngine.Vector3.Distance(new UnityEngine.Vector3(p.x, 0, p.z), new UnityEngine.Vector3(door.transform.position.x, 0, door.transform.position.z))},
  {"enc", Cozy.Combat.Encounter.Running}, {"attacker", Cozy.Combat.AttackTurn.Attacker != null ? Cozy.Combat.AttackTurn.Attacker.SystemSlug : ""},
  {"hero_dist", UnityEngine.Vector3.Distance(new UnityEngine.Vector3(p.x, 0, p.z), new UnityEngine.Vector3(pl.position.x, 0, pl.position.z))},
  {"plan", Cozy.Life.CreaturePlan.Describe(io)},
};
var win = Win(%(wx)sf, %(wz)sf);
if (win != null) d["win_open"] = win.IsOpen;
var z2 = Cozy.Grid.InteractiveObject.BySlug("zombie_probe_2");
if (z2 != null) { var a2 = z2.GetComponentInChildren<Cozy.Creatures.ZombieAnimation>(); d["z2_drive"] = a2.Drive.HasValue ? a2.Drive.Value.ToString() : ""; }
var sb = new System.Text.StringBuilder("{");
foreach (var kv in d) { if (sb.Length > 1) sb.Append(","); sb.Append("\"").Append(kv.Key).Append("\":"); var v = kv.Value; if (v is bool b) sb.Append(b ? "true" : "false"); else if (v is float f) sb.Append(f.ToString(System.Globalization.CultureInfo.InvariantCulture)); else sb.Append("\"").Append(v.ToString().Replace("\"", "'")).Append("\""); }
return sb.Append("}").ToString();
'''

JOURNAL = r'''
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var jl = (System.Collections.IList)typeof(Cozy.Life.AiConsole).GetField("_journal", flags).GetValue(null);
var sb = new System.Text.StringBuilder();
for (int i = %(from)d; i < jl.Count; i++) { var e = jl[i]; sb.Append(e.GetType().GetField("Item2").GetValue(e)).Append('\n'); }
var ev = Cozy.View.GameEvents.All;
for (int i = System.Math.Max(0, ev.Count - 6); i < ev.Count; i++) if (ev[i].Text.Contains("ИИ-план")) sb.Append("событие: ").Append(ev[i].Text).Append('\n');
return sb.ToString();
'''

END = r'''
Cozy.Combat.ZombieAttack.CancelCurrent();
foreach (var other in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
    if (other != null && other.SystemSlug == "zombie_probe_2") UnityEngine.Object.Destroy(other.gameObject);
Cozy.Character.PlayerTarget.AttacksOff = false;
Cozy.Grid.LevelIO.JoinScripts();
Cozy.Life.CreaturePlan.RestartAll();
return "правила уровня возвращены";
'''

# сцена: код C# после общего сброса; zombie — (x, z, yaw)
OUT_DOOR = 'io.transform.SetPositionAndRotation(door.transform.position + door.Normal * 4f + UnityEngine.Vector3.up * (ground - door.transform.position.y), UnityEngine.Quaternion.LookRotation(-door.Normal));'
HERO_IN = 'Hero(-45f, -52f);'
EAST = (-40.5, -51.0)
OUT_EAST = 'io.transform.SetPositionAndRotation(new UnityEngine.Vector3(-37.2f, ground, -51f), UnityEngine.Quaternion.LookRotation(UnityEngine.Vector3.left));'


def spawn2(x, z):
    return ('var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);'
            'var z2io = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { Cozy.Grid.FurnitureCatalog.ById("zombie"), new UnityEngine.Vector3(%sf, ground, %sf), 0f });'
            'z2io.Slug = "zombie_probe_2";' % (x, z))


# «услышал героя»: место звука — герой, событие как от чувств (шаги героя в тесте не подделать)
HEAR = (r'var se = io.GetComponentInChildren<Cozy.Creatures.CreatureSenses>();'
        r'typeof(Cozy.Creatures.CreatureSenses).GetProperty("LastHeard").SetValue(se, pl.position);'
        r'typeof(Cozy.Creatures.CreatureSenses).GetField("_lastHeardAt", NP).SetValue(se, UnityEngine.Time.time);'
        r'Cozy.Life.LifeRules.OnEvent("madman_1", Cozy.Life.LifeRules.HearsPlayer, "");')
HEARS_LOCAL = """
- [hears player priority 2]:
  [look][last heard][1s]
  [go][last heard][walk]
  [look around/wait left1s right1s]
  - [sees door]:
    - [latched]:
      [knock]
    - [unlatched]:
      [open]"""
HEARS_PLAIN = """
- [hears player priority 2]:
  [look][last heard][1s]
  [go][last heard][walk]
  [look around/wait left1s right1s]"""
FACE_AWAY = 'io.transform.SetPositionAndRotation(door.transform.position + door.Normal * 4f + UnityEngine.Vector3.up * (ground - door.transform.position.y), UnityEngine.Quaternion.LookRotation(door.Normal));'

SCENARIOS = {
    'hears_door_local': dict(
        what='услышал героя за дверью на щеколде (стоит спиной), «слышит» с местным блоком двери — разворачивается, идёт, ломится',
        scene='Hero(-45f, -48.5f); door.SetLatched(true);' + FACE_AWAY, rules="[madman_1]" + HEARS_LOCAL, after=HEAR, secs=12,
        checks=[('ломится', lambda s: any(x['show'] == 'DoorBang' for x in s)),
                ('дверь закрыта', lambda s: all(not x['door_open'] for x in s)),
                ('пока ломится — на месте', lambda s: spread([x for x in s if x['show'] == 'DoorBang'], 'door_dist') <= 0.1)]),
    'hears_door_global': dict(
        what='то же, «слышит» без местного блока, общее дерево двери (приоритет 0) — упёрся и ломится',
        scene='Hero(-45f, -48.5f); door.SetLatched(true);' + FACE_AWAY, rules="[madman_1]" + HEARS_PLAIN + DOOR_TREE, after=HEAR, secs=12,
        checks=[('ломится', lambda s: any(x['show'] == 'DoorBang' for x in s)),
                ('дверь закрыта', lambda s: all(not x['door_open'] for x in s))]),
    'door_no_rule': dict(
        what='закрытая незапертая дверь, правил двери нет — встаёт у двери, дверь не трогает',
        scene=HERO_IN + OUT_DOOR, rules=BASE + '\n- [hears player]:\n  [wait][1s]', secs=9,
        checks=[('дверь осталась закрытой', lambda s: all(not x['door_open'] for x in s)),
                ('дошёл до двери (≤ 1,4 м)', lambda s: min(x['door_dist'] for x in s) <= 1.4),
                ('в комнату не попал', lambda s: not any(x['inRoom'] for x in s))]),
    'door_open': dict(
        what='незапертая без щеколды + дерево двери — открывает и входит',
        scene=HERO_IN + OUT_DOOR, rules=BASE + DOOR_TREE, secs=14,
        checks=[('дверь открыта', lambda s: any(x['door_open'] for x in s)),
                ('вошёл в комнату', lambda s: any(x['inRoom'] for x in s))]),
    'door_latched': dict(
        what='щеколда + дерево двери — ломится клипом, дверь закрыта, не дёргается туда-сюда',
        scene=HERO_IN + 'door.SetLatched(true);' + OUT_DOOR, rules=BASE + DOOR_TREE, secs=14,
        checks=[('ломится (DoorBang)', lambda s: any(x['show'] == 'DoorBang' for x in s)),
                ('дверь закрыта всё время', lambda s: all(not x['door_open'] for x in s)),
                ('пока ломится — стоит на месте (разброс ≤ 0,1 м)', lambda s: spread([x for x in s if x['show'] == 'DoorBang'], 'door_dist') <= 0.1),
                ('ломится без перерывов-отходов (≥ 70 % замеров после начала)', lambda s: share_after(s, lambda x: x['show'] == 'DoorBang') >= 0.7)]),
    'door_locked_nokey': dict(
        what='заперта на ключ, ключа нет — ломится',
        scene=HERO_IN + 'door.Lock("103");' + OUT_DOOR, rules=BASE + DOOR_TREE, secs=10,
        checks=[('ломится', lambda s: any(x['show'] == 'DoorBang' for x in s)),
                ('дверь закрыта и заперта', lambda s: all(not x['door_open'] and x['door_locked'] for x in s))]),
    'door_locked_key': dict(
        what='заперта, ключ у зомби — отпирает, открывает, входит',
        scene=HERO_IN + 'door.Lock("103"); foreach (var c in eq.Containers) if (c.grid.TryAdd(Cozy.Grid.Items.KeyStar)) break;' + OUT_DOOR,
        rules=BASE + DOOR_TREE, secs=14,
        checks=[('дверь открыта', lambda s: any(x['door_open'] for x in s)),
                ('вошёл', lambda s: any(x['inRoom'] for x in s))]),
    'door_key_latched': dict(
        what='заперта, ключ есть, но щеколда — ломится, не открывает',
        scene=HERO_IN + 'door.Lock("103"); door.SetLatched(true); foreach (var c in eq.Containers) if (c.grid.TryAdd(Cozy.Grid.Items.KeyStar)) break;' + OUT_DOOR,
        rules=BASE + DOOR_TREE, secs=10,
        checks=[('ломится', lambda s: any(x['show'] == 'DoorBang' for x in s)),
                ('дверь закрыта', lambda s: all(not x['door_open'] for x in s))]),
    'window_closed': dict(
        what='закрытое окно перед ним + дерево окна — бьёт в стекло, остаётся снаружи',
        scene=HERO_IN + OUT_EAST, rules="[madman_1]" + WINDOW_TREE, secs=10, win=EAST,
        checks=[('бьёт в окно (WindowBang)', lambda s: any(x['show'] == 'WindowBang' for x in s)),
                ('окно закрыто', lambda s: all(not x.get('win_open', False) for x in s)),
                ('снаружи', lambda s: not any(x['inRoom'] for x in s))]),
    'window_open': dict(
        what='открытое окно + дерево окна, дверь на щеколде (через дверь не пройти) — перелезает и оказывается в комнате',
        scene=HERO_IN + 'door.SetLatched(true); Win(-40.5f, -51f).SetOpen(true);' + OUT_EAST, rules="[madman_1]" + WINDOW_TREE, secs=16, win=EAST,
        checks=[('перелезает (занят цепочкой)', lambda s: any(x['busy'] for x in s)),
                ('в конце в комнате', lambda s: s[-1]['inRoom'])]),
    'window_open_door': dict(
        what='открытое окно + дерево окна, дверь проходима (закрыта, без щеколды) — всё равно перелезает: безумный прямолинеен, маршрут через дверь не ищет (Илья 21.10, P1184 отменён)',
        scene=HERO_IN + 'Win(-40.5f, -51f).SetOpen(true);' + OUT_EAST, rules="[madman_1]" + WINDOW_TREE, secs=16, win=EAST,
        checks=[('перелезает (занят цепочкой)', lambda s: any(x['busy'] for x in s)),
                ('в конце в комнате', lambda s: s[-1]['inRoom'])]),
    'attack_wall': dict(
        what='герой у стены изнутри, зомби снаружи в 2,5 м — атаки нет',
        scene='Hero(-41.5f, -54f); io.transform.SetPositionAndRotation(new UnityEngine.Vector3(-39f, ground, -54f), UnityEngine.Quaternion.LookRotation(UnityEngine.Vector3.left)); Cozy.Character.PlayerTarget.AttacksOff = false;',
        rules="[madman_1]\n- [while sees player priority 3]:\n  [wait][1s]", secs=6,
        checks=[('стычки нет', lambda s: not any(x['enc'] for x in s))]),
    'attack_window': dict(
        what='герой у окна изнутри, зомби снаружи у стекла — атаки нет',
        scene='Hero(-41.5f, -51f);' + OUT_EAST + ' Cozy.Character.PlayerTarget.AttacksOff = false;',
        rules="[madman_1]\n- [while sees player priority 3]:\n  [wait][1s]", secs=6, win=EAST,
        checks=[('стычки нет', lambda s: not any(x['enc'] for x in s))]),
    'attack_field': dict(
        what='поле, зомби в 2 м лицом к герою — нападает',
        scene='Hero(-30f, -30f); io.transform.SetPositionAndRotation(new UnityEngine.Vector3(-30f, ground, -32f), UnityEngine.Quaternion.LookRotation(UnityEngine.Vector3.forward)); Cozy.Character.PlayerTarget.AttacksOff = false;',
        rules="[madman_1]\n- [while sees player priority 3]:\n  [wait][1s]", secs=5,
        checks=[('стычка началась', lambda s: any(x['enc'] for x in s))]),
    'two_zombies': dict(
        what='двое в радиусе — нападает один, второй стоит',
        scene='Hero(-30f, -30f); io.transform.SetPositionAndRotation(new UnityEngine.Vector3(-28f, ground, -30f), UnityEngine.Quaternion.LookRotation(UnityEngine.Vector3.left));' + spawn2(-32, -30) + ' Cozy.Character.PlayerTarget.AttacksOff = false;',
        rules="[madman_1]\n- [while sees player priority 3]:\n  [wait][1s]", secs=5,
        checks=[('стычка одна', lambda s: any(x['enc'] for x in s)),
                ('нападающий — один из двух', lambda s: any(x['attacker'] in ('madman_1', 'zombie_probe_2') for x in s))]),
    'chase': dict(
        what='видит героя в 7 м — идёт к нему',
        scene='Hero(-30f, -23f); io.transform.SetPositionAndRotation(new UnityEngine.Vector3(-30f, ground, -30f), UnityEngine.Quaternion.LookRotation(UnityEngine.Vector3.forward));',
        rules="[madman_1]" + CHASE, secs=6,
        checks=[('сблизился на 2 м и больше', lambda s: s[0]['hero_dist'] - min(x['hero_dist'] for x in s) >= 2.0)]),
}


def spread(rows, key):
    vals = [r[key] for r in rows]
    return max(vals) - min(vals) if vals else 0.0


def share_after(rows, pred):
    idx = next((i for i, r in enumerate(rows) if pred(r)), None)
    if idx is None:
        return 0.0
    rest = rows[idx:]
    return sum(1 for r in rest if pred(r)) / len(rest)


def run(name, sc):
    rules = json.dumps(sc['rules'], ensure_ascii=False)
    head = cs(SETUP % {'scene': sc['scene'], 'rules': rules, 'after': sc.get('after', '')})
    first, _, check = head.partition('\n')
    wx, wz = sc.get('win', EAST)
    samples = []
    end = time.time() + sc['secs']
    while time.time() < end:
        samples.append(json.loads(cs(OBSERVE % {'wx': wx, 'wz': wz})))
        time.sleep(0.4)
    journal = cs(JOURNAL % {'from': int(first)})
    ok_all = True
    lines = []
    for title, fn in sc['checks']:
        try:
            ok = bool(fn(samples))
        except Exception as e:
            ok, title = False, title + ' (ошибка проверки: %s)' % e
        ok_all &= ok
        lines.append(('OK   ' if ok else 'FAIL ') + title)
    print('\n=== %s — %s: %s' % (name, sc['what'], 'ЗЕЛЁНОЕ' if ok_all else 'КРАСНОЕ'))
    for l in lines:
        print('  ' + l)
    if 'непонятых 0' not in check:
        print('  ⚠ правила:', check.strip().splitlines()[-1])
    trail = []
    for x in samples:
        tag = '%.1f d=%.2f show=%s%s%s %s' % (x['t'], x['door_dist'], x['show'] or '-', ' ВНУТРИ' if x['inRoom'] else '',
                                              ' СТЫЧКА' if x['enc'] else '', x['plan'][:70])
        if not trail or trail[-1][1] != tag.split(' ', 1)[1]:
            trail.append((x['t'], tag.split(' ', 1)[1], tag))
    for _, _, tag in trail[:14]:
        print('    ' + tag)
    for l in journal.strip().splitlines()[-8:]:
        print('    · ' + l)
    return ok_all


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    results = {}
    try:
        for n in names:
            results[n] = run(n, SCENARIOS[n])
    finally:
        print('\n' + cs(END))
    bad = [n for n, ok in results.items() if not ok]
    print('ИТОГ: %d из %d зелёные%s' % (len(results) - len(bad), len(results), '; красные: ' + ', '.join(bad) if bad else ''))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
