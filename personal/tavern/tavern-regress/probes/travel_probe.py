"""Проба перехода между уровнями (зона to_<слаг> → карточка места → другой уровень → обратно).

Круг: level1 → уровень-заглушка travel_probe из памяти (LevelIO.Visited) → назад в level1 из
памяти → отказ (цели нет) → снова заглушка → назад в level1 из ФАЙЛА. В конце память чистится,
часы возвращаются, живой уровень = файл (unsaved_check). Запускать в play на level1.
"""
import json, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
REG = '/home/ilya/.claude/skills/tavern-regress/probes'

def mcp(tool, payload):
    out = subprocess.run(['python3', MCP, tool, json.dumps(payload)], capture_output=True, text=True, timeout=300)
    text = out.stdout.strip()
    line = text.splitlines()[-1] if text else '{}'
    try: return json.loads(line)
    except Exception: return {'raw': text[-500:]}

def run(code):
    d = mcp('execute_code', {"action": "execute", "code": code})
    if not d.get('success', True): return 'ОШИБКА: ' + json.dumps(d, ensure_ascii=False)[:400]
    return (d.get('data') or {}).get('result')

def console(kinds=("error",), count=30, text=None):
    payload = {"action": "get", "types": list(kinds), "count": count}
    if text: payload["filter_text"] = text
    d = mcp('read_console', payload)
    data = d.get('data') if isinstance(d, dict) else None
    items = data if isinstance(data, list) else ((data or {}).get('items') or (data or {}).get('messages') or [])
    return [json.dumps(m, ensure_ascii=False) for m in items]

STATE = ('return Tavern.UI.SceneLoader.Traveling + "|" + Cozy.Grid.LevelIO.CurrentSlug + "|" + Cozy.Grid.LevelIO.CurrentLevelName'
         ' + "|" + Cozy.Grid.PlayerRef.Transform.position.ToString("0.00") + "|" + (Tavern.UI.SceneLoader.ArrivedAt is Cozy.Grid.ZonePiece az ? az.slug : Tavern.UI.SceneLoader.ArrivedAt != null ? Tavern.UI.SceneLoader.ArrivedAt.name : "-")'
         ' + "|" + UnityEngine.Time.timeScale + "|" + Cozy.Grid.PlayerRef.Transform.rotation.eulerAngles.y.ToString("0")'
         ' + "|" + (UnityEngine.Camera.main != null ? UnityEngine.Vector3.Distance(UnityEngine.Camera.main.transform.position, Cozy.Grid.PlayerRef.Transform.position).ToString("0.0") : "-")'
         ' + "|" + Cozy.Grid.ZonePiece.All.Count + "|" + (Tavern.Core.GameClock.I != null ? Tavern.Core.GameClock.I.Day + " " + Tavern.Core.GameClock.Now : "-");')
INV = 'return UnityEngine.JsonUtility.ToJson(Cozy.Grid.LevelIO.CollectPlayer());'
SEED = '''
var d = new Cozy.Grid.LevelIO.LevelData{ sceneName="travel_probe", slug="travel_probe", gridWidth=12, gridHeight=12, gridAnchored=true, baseWidth=12, baseHeight=12, gridOriginX=0f, gridOriginZ=0f, baseOriginX=0f, baseOriginZ=0f, cellSize=3f };
var z = new Cozy.Grid.LevelIO.ZoneData{ name="Назад в «Сосны»", slug="to_level1", kind=1, note="Тропа к коттеджу" };
z.cells.Add(new Cozy.Grid.LevelIO.Vec3{ x=3f, y=0.1f, z=3f });
d.zones.Add(z);
Cozy.Grid.LevelIO.Visited["travel_probe"] = d;
return "seeded " + Cozy.Grid.LevelIO.Visited.Count;
'''
GATE = '''
var g = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground);
var p = Cozy.Grid.PlayerRef.Transform.position;
float cs = g.CellSize; var o = g.Origin;
float cx = o.x + UnityEngine.Mathf.Round((p.x - o.x)/cs)*cs; float cz = o.z + UnityEngine.Mathf.Round((p.z - o.z)/cs)*cs;
var z = new Cozy.Grid.LevelIO.ZoneData{ name="Шоссе на Лихово", slug="to_travel_probe", kind=1, note="1,5 км по грунтовке" };
z.cells.Add(new Cozy.Grid.LevelIO.Vec3{ x=cx, y=0.1f, z=cz });
Cozy.Grid.GridCursor.I.SpawnZone(z);
var zone = Cozy.Grid.ZonePiece.BySlug("to_travel_probe");
return cx + "|" + cz + "|" + (zone != null ? zone.Bounds.center.ToString("0.00") + " contains=" + zone.ContainsAt(p) : "нет зоны");
'''

def state():
    s = str(run(STATE))
    parts = s.split('|')
    return dict(zip(['traveling','slug','name','pos','arrived','scale','yaw','camdist','zones','clock'], parts)) if len(parts) >= 10 else {'raw': s}

def teleport(x, y, z):
    return run(f'Cozy.Grid.GridCursor.I.TeleportPlayerTo(new UnityEngine.Vector3({x}f,{y}f,{z}f)); return Cozy.Grid.PlayerRef.Transform.position.ToString("0.00");')

def wait_travel(expect_slug, seconds=60):
    t0 = time.time(); seen = False; last = None
    while time.time() - t0 < seconds:
        st = state(); last = st
        if st.get('traveling') == 'True': seen = True
        if seen and st.get('traveling') == 'False':
            return True, round(time.time() - t0, 1), st
        time.sleep(0.4)
    return False, round(time.time() - t0, 1), last

def report(step, ok, info):
    print(('✅' if ok else '❌'), step, '—', info)

def main():
    if not str(run('return UnityEngine.Application.isPlaying;')).lower().startswith('t'):
        print('не в play'); sys.exit(1)
    st0 = state()
    if st0.get('slug') != 'level1':
        print('ожидался level1, а в редакторе', st0); sys.exit(1)
    errors_before = len(console())
    inv0 = run(INV)
    clock0 = st0['clock']
    print('старт:', st0)

    # ставим игрока на землю у дома и ворота под ноги
    print('телепорт на землю:', teleport(23.5, 0, 16.4))
    time.sleep(0.5)
    print(run(SEED))
    print('ворота в level1:', run(GATE))

    ok, dt, st = wait_travel('travel_probe', 40)
    report('1. level1 → travel_probe (память)', ok and st.get('slug') == 'travel_probe', f'{dt} с, {st}')
    inv1 = run(INV)
    report('   инвентарь доехал', inv1 == inv0, f'{len(str(inv0))} символов')
    report('   прибыл в ворота to_level1', st.get('arrived') == 'to_level1' and st.get('pos','').startswith('(3.'), st.get('pos'))
    report('   камера рядом', st.get('camdist') not in ('-', '') and float(st['camdist']) < 25, st.get('camdist'))

    # шаг наружу и назад — переход обратно из памяти
    print('выход из ворот:', teleport(9, 0, 9)); time.sleep(0.6)
    print('назад в ворота:', teleport(3, 0, 3))
    ok, dt, st = wait_travel('level1', 90)
    report('2. travel_probe → level1 (память)', ok and st.get('slug') == 'level1', f'{dt} с, {st}')
    inv2 = run(INV)
    report('   инвентарь доехал', inv2 == inv0, '')
    gate = run('var z = Cozy.Grid.ZonePiece.BySlug("to_travel_probe"); return z != null ? z.Bounds.center.ToString("0.00") : "нет";')
    report('   память уровня: ворота to_travel_probe на месте', gate != 'нет', gate)
    report('   прибыл в них', st.get('arrived') == 'to_travel_probe', st.get('pos'))

    # отказ: цели нет
    run('Cozy.Grid.LevelIO.Visited.Clear(); return "cleared";')
    print('выход из ворот:', teleport(23.5 + 6, 0, 16.4 + 6)); time.sleep(0.6)
    print('назад в ворота:', teleport(23.5, 0, 16.4))
    ok, dt, st = wait_travel('level1', 30)
    report('3. цели нет → остаёмся', ok and st.get('slug') == 'level1' and st.get('scale') == '1', f'{dt} с, {st}')

    # снова на заглушку и назад уже из файла
    run(SEED)
    print('выход из ворот:', teleport(23.5 + 6, 0, 16.4 + 6)); time.sleep(0.6)
    print('назад в ворота:', teleport(23.5, 0, 16.4))
    ok, dt, st = wait_travel('travel_probe', 60)
    report('4. level1 → travel_probe (повтор)', ok and st.get('slug') == 'travel_probe', f'{dt} с')
    run('Cozy.Grid.LevelIO.Visited.Remove("level1"); return "forgot level1";')
    print('выход из ворот:', teleport(9, 0, 9)); time.sleep(0.6)
    print('назад в ворота:', teleport(3, 0, 3))
    ok, dt, st = wait_travel('level1', 120)
    report('5. travel_probe → level1 (ФАЙЛ)', ok and st.get('slug') == 'level1', f'{dt} с, {st}')
    inv5 = run(INV)
    report('   инвентарь доехал', inv5 == inv0, '')
    gate = run('var z = Cozy.Grid.ZonePiece.BySlug("to_travel_probe"); return z != null ? "есть" : "нет";')
    report('   уровень из файла: пробных ворот нет', gate == 'нет', gate)

    # уборка
    run('Cozy.Grid.LevelIO.Visited.Clear(); return "cleared";')
    h = clock0.split(' ')
    if len(h) == 2 and st.get('clock','').split(' ')[0] == h[0]:
        hh, mm = h[1].split(':')
        run(f'Tavern.Core.GameClock.I.SetHours({int(hh)}f + {int(mm)}f/60f); return "clock back";')
    print('часы:', state().get('clock'), '(было', clock0 + ')')
    logs = console(("log",), 60, text='Переход')
    for m in logs[-6:]: print('   лог:', m[:300])
    errs = console()
    report('консоль без новых ошибок', len(errs) <= errors_before, f'{len(errs)} (было {errors_before})')
    for m in errs[:5]: print('   ', m[:300])
    unsaved = run(open(REG + '/unsaved_check.cs', encoding='utf-8').read())
    report('живой уровень = файл', str(unsaved).startswith('СОХРАНЕНО'), str(unsaved)[:200])

if __name__ == '__main__':
    main()
