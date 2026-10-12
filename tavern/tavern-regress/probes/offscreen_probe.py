"""Проба маркера перехода и жизни за кадром (в play на level1).

1. Маркер: в level1 ставится travel_marker со слагом «travel_probe» под ногами, в заглушке —
   парный маркер со слагом «level1» (повёрнут на восток); переход туда и обратно по маркерам,
   прибытие на маркер лицом по его носику.
2. За кадром: у level1 строки [за кадром] — сектант появляется через 10 игровых минут после ухода,
   идёт к маркеру 2, выключает счётчик; часы переводятся вперёд, пока герой в заглушке; по
   возвращении сектант стоит у маркера 2, счётчик выключен, журнал применён.
3. «Прожить часы здесь»: Simulate на level1 c 24 ч → те же записи применяются на месте.
В конце: сектант убран, строки стёрты, память чистая, level1 из файла.
"""
import json, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
REG = '/home/ilya/.claude/skills/tavern-regress/probes'

def mcp(tool, payload):
    out = subprocess.run(['python3', MCP, tool, json.dumps(payload)], capture_output=True, text=True, timeout=300)
    text = out.stdout.strip(); line = text.splitlines()[-1] if text else '{}'
    try: return json.loads(line)
    except Exception: return {'raw': text[-500:]}

def run(code):
    d = mcp('execute_code', {"action": "execute", "code": code})
    if not d.get('success', True): return 'ОШИБКА: ' + json.dumps(d, ensure_ascii=False)[:600]
    return (d.get('data') or {}).get('result')

def console(kinds=("error",), count=30, text=None):
    payload = {"action": "get", "types": list(kinds), "count": count}
    if text: payload["filter_text"] = text
    d = mcp('read_console', payload); data = d.get('data') if isinstance(d, dict) else None
    items = data if isinstance(data, list) else ((data or {}).get('items') or (data or {}).get('messages') or [])
    return [json.dumps(m, ensure_ascii=False) for m in items]

def report(step, ok, info=''):
    print(('✅' if ok else '❌'), step, ('— ' + str(info)) if info != '' else '')

STATE = ('return Tavern.UI.SceneLoader.Traveling + "|" + Cozy.Grid.LevelIO.CurrentSlug + "|" + Cozy.Grid.PlayerRef.Transform.position.ToString("0.00")'
         ' + "|" + (Tavern.UI.SceneLoader.ArrivedAt != null ? Tavern.UI.SceneLoader.ArrivedAt.name : "-")'
         ' + "|" + Cozy.Grid.PlayerRef.Transform.rotation.eulerAngles.y.ToString("0") + "|" + Cozy.Grid.Weather.Clock(Cozy.Grid.Weather.Hour);')

def state():
    s = str(run(STATE)); p = s.split('|')
    return dict(zip(['traveling','slug','pos','arrived','yaw','clock'], p)) if len(p) >= 6 else {'raw': s}

def teleport(x, y, z):
    return run(f'Cozy.Grid.GridCursor.I.TeleportPlayerTo(new UnityEngine.Vector3({x}f,{y}f,{z}f)); return Cozy.Grid.PlayerRef.Transform.position.ToString("0.00");')

def wait_travel(seconds=90):
    t0 = time.time(); seen = False; last = None
    while time.time() - t0 < seconds:
        st = state(); last = st
        if st.get('traveling') == 'True': seen = True
        if seen and st.get('traveling') == 'False': return True, round(time.time() - t0, 1), st
        time.sleep(0.4)
    return False, round(time.time() - t0, 1), last

SEED = '''
var d = new Cozy.Grid.LevelIO.LevelData{ sceneName="travel_probe", slug="travel_probe", gridWidth=12, gridHeight=12, gridAnchored=true, baseWidth=12, baseHeight=12, gridOriginX=0f, gridOriginZ=0f, baseOriginX=0f, baseOriginZ=0f, cellSize=3f };
var o = new Cozy.Grid.LevelIO.ObjectData{ id="travel_marker", pos=new Cozy.Grid.LevelIO.Vec3{x=3f,y=0f,z=3f}, rotY=90f, slug="level1", title="Назад в «Сосны»" };
d.objects.Add(o);
Cozy.Grid.LevelIO.Visited["travel_probe"] = d;
return "seeded";
'''
MARKER = '''
var def = Cozy.Grid.FurnitureCatalog.ById("travel_marker");
if (def == null) return "нет дефа travel_marker";
var p = Cozy.Grid.PlayerRef.Transform.position;
var io = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, new UnityEngine.Vector3(p.x, 0f, p.z), 0f);
if (io == null) return "не поставился";
io.Slug = "travel_probe"; io.Title = "Шоссе на Лихово";
var tp = io.GetComponent<Cozy.Grid.TravelPoint>();
return "marker " + io.SystemSlug + " at " + io.transform.position.ToString("0.00") + " tp=" + (tp != null) + " target=" + (tp != null ? tp.Target : "-") + " all=" + Cozy.Grid.TravelPoint.All.Count;
'''

def main():
    if not str(run('return UnityEngine.Application.isPlaying;')).lower().startswith('t'): print('не в play'); sys.exit(1)
    st0 = state()
    if st0.get('slug') != 'level1': print('ожидался level1:', st0); sys.exit(1)
    errors_before = len(console())
    print('старт:', st0)
    print('телепорт на землю:', teleport(23.5, 0, 16.4)); time.sleep(0.4)
    print(run(SEED))
    spawn_api = run('return typeof(Cozy.Grid.GridCursor).GetMethod("SpawnWorldObject") != null;')
    print('SpawnPlaced есть:', spawn_api)
    print('маркер:', run(MARKER))

    # 1. маркер → заглушка
    ok, dt, st = wait_travel(40)
    report('1. level1 → travel_probe по маркеру', ok and st.get('slug') == 'travel_probe', f'{dt} с, {st}')
    report('   прибыл на парный маркер (3,0,3)', st.get('pos', '').startswith('(3.') and st.get('arrived', '-') != '-', st.get('pos'))
    report('   лицом по носику маркера (восток, yaw≈90)', st.get('yaw') in ('89', '90', '91'), st.get('yaw'))

    # 2. за кадром: строки для level1 — время через 10 минут от текущих часов
    hour = float(run('return Cozy.Grid.Weather.Hour.ToString(System.Globalization.CultureInfo.InvariantCulture);'))
    t1 = (hour + 10/60) % 24; t2 = (hour + 20/60) % 24; t3 = (hour + 30/60) % 24
    clk = lambda h: f'{int(h):02d}:{int(round((h - int(h))*60)) % 60:02d}'
    lines = f'[{clk(t1)}][sectant sectant_off][appear][monster_zone_2/marker_1]\\n[{clk(t2)}][sectant_off][go][monster_zone_2/marker_2]\\n[{clk(t3)}][sectant_off][off][meter_outdoor_1]'
    r = run(f'Cozy.Grid.LevelIO.Visited["level1"].aiOffscreen = "{lines}"; return Cozy.Life.Offscreen.Parse("{lines}").Count + " строк, ошибок " + Cozy.Life.Offscreen.Parse("{lines}").FindAll(l => !l.Ok).Count;')
    print('строки за кадром для level1:', r)
    # часы вперёд на 40 минут, пока герой в заглушке (тик за кадром ловит переход через отметки)
    for step in range(4):
        run('Tavern.Core.GameClock.I.Advance(10f/60f); return "+10";'); time.sleep(0.6)
    facts = run('return Cozy.Life.Offscreen.Levels.ContainsKey("level1") ? Cozy.Life.Offscreen.Levels["level1"].Facts.Count.ToString() : "нет";')
    report('2a. журнал level1 накопил 3 записи, пока героя не было', facts == '3', facts)

    # назад по маркеру → применение
    print('выход из маркера:', teleport(9, 0, 9)); time.sleep(0.6)
    print('назад на маркер:', teleport(3, 0, 3))
    ok, dt, st = wait_travel(90)
    report('2b. travel_probe → level1 по маркеру', ok and st.get('slug') == 'level1', f'{dt} с, {st}')
    sect = run('var io = Cozy.Grid.InteractiveObject.BySlug("sectant_off"); if (io == null) return "нет"; var z = Cozy.Grid.ZonePiece.BySlug("monster_zone_2"); UnityEngine.Vector3 m = UnityEngine.Vector3.zero; bool has = false; if (z != null) has = z.MarkCell(2, out m); if (!has) return io.transform.position.ToString("0.0") + " marker2=- dist=-"; return io.transform.position.ToString("0.0") + " marker2=" + m.ToString("0.0") + " dist=" + UnityEngine.Vector3.Distance(io.transform.position, m).ToString("0.0");')
    report('   сектант sectant_off стоит у маркера 2', sect != 'нет' and 'dist=' in str(sect) and float(str(sect).split('dist=')[1]) < 3.5, sect)
    meter = run('var io = Cozy.Life.CreaturePlan.FindObject("meter_outdoor_1"); if (io == null) return "нет объекта"; var p = Cozy.Grid.FeatureHost.Get<Cozy.Grid.PowerFeature>(io); var sw = Cozy.Grid.FeatureHost.Get<Cozy.Grid.WallSwitchFeature>(io); if (p != null) return "power.On=" + p.On; if (sw != null) return "switch.On=" + sw.On; return "не включается";')
    report('   счётчик meter_outdoor_1 выключен', str(meter).endswith('=False'), meter)
    ledger = run('var a = Cozy.Life.Offscreen.Levels["level1"]; int ap = a.Facts.FindAll(f => f.Applied).Count; var bad = a.Facts.FindAll(f => f.Result.Length > 0); return ap + " применено, с ошибкой " + bad.Count + (bad.Count > 0 ? ": " + bad[0].Result : "");')
    report('   журнал: все записи применены без ошибок', str(ledger).startswith('3 применено, с ошибкой 0'), ledger)

    # 3. прожить часы здесь: убрать сектанта, включить счётчик, Simulate 24 ч на level1
    run('var io = Cozy.Grid.InteractiveObject.BySlug("sectant_off"); if (io != null) Cozy.Life.CrowZoneSpawn.RemoveCreature(io); var m = Cozy.Life.CreaturePlan.FindObject("meter_outdoor_1"); var p = m != null ? Cozy.Grid.FeatureHost.Get<Cozy.Grid.PowerFeature>(m) : null; if (p != null && !p.On) p.TryToggle(); Cozy.Grid.LevelIO.AiOffscreen = "' + lines + '"; return "reset";')
    n = run('return Cozy.Life.Offscreen.Simulate(Cozy.Grid.LevelIO.CurrentSlug, 24f, Cozy.Grid.LevelIO.AiOffscreen).ToString();')
    sect2 = run('var io = Cozy.Grid.InteractiveObject.BySlug("sectant_off"); return io != null ? io.transform.position.ToString("0.0") : "нет";')
    report('3. Simulate(24 ч) на месте: применено 3, сектант есть', n == '3' and sect2 != 'нет', f'n={n} sectant={sect2}')

    # уборка
    run('var io = Cozy.Grid.InteractiveObject.BySlug("sectant_off"); if (io != null) Cozy.Life.CrowZoneSpawn.RemoveCreature(io); Cozy.Grid.LevelIO.AiOffscreen = ""; Cozy.Life.Offscreen.Levels.Clear(); return "clean";')
    logs = console(("log",), 40, text='За кадром')
    for m in logs[-8:]: print('   лог:', m[:220])
    errs = console()
    report('консоль без новых ошибок', len(errs) <= errors_before, f'{len(errs)} (было {errors_before})')
    for m in errs[:5]: print('   ', m[:300])

if __name__ == '__main__':
    main()
