"""Эталон закрытых комнат на новом здании стенда «Комнаты (тест)» (RM-H, заведён 28.10).

Здание: большой дом с лестницей на крышу (зал 17 клеток + две западные комнаты на 1 этаже,
четыре комнаты из стен на крыше), клетки x −81…−69, z −75…−60. Илья 28.10: «покрой новое
здание тестами, сейчас ок все» — то, что сейчас, принято за эталон.

Герой встаёт в семь точек (улица, у открытой двери, в зале, в закрытой западной комнате,
в двух комнатах на крыше, далеко). В каждой: проявление снимается мгновенно, по каждой
комнате здания пишется доступ (`Reach`), темнота (`Dark`), крышка, маска, накрытость,
домик; плюс `rooms_probe.cs` обязан быть зелёным. Комнаты сравниваются по (уровень, центр),
не по индексу. Если изменилось само здание (комнаты, двери) — «ЗДАНИЕ ИЗМЕНИЛОСЬ», эталон
переснять: `record`.

python3 rooms_house_probe.py           # сверка с эталоном (в play на rooms_test)
python3 rooms_house_probe.py record    # переснять эталон
"""
import json, pathlib, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
REG = pathlib.Path('/home/ilya/.claude/skills/tavern-regress/probes')
GOLDEN = REG / 'rooms_house_golden.json'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
SLUG = 'rooms_test'
BOX = (-82.5, -67.5, -76.5, -58.5)
POINTS = [
    ('улица юг', -64.0, 0.98, -82.0),
    ('у открытой двери', -65.0, 0.98, -63.0),
    ('зал', -71.0, 0.98, -64.0),
    ('западная закрытая', -79.5, 0.98, -63.0),
    ('крыша юг', -73.34, 4.08, -70.69),
    ('крыша север', -72.0, 4.08, -61.5),
    ('далеко', -49.66, 0.98, -56.24),
]


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    text = out.stdout.strip()
    try:
        d = json.loads(text.splitlines()[-1])
    except Exception:
        return 'ОШИБКА: ' + text[-400:]
    if not d.get('success', True):
        return 'ОШИБКА: ' + json.dumps(d, ensure_ascii=False)[:400]
    return (d.get('data') or {}).get('result')


SNAP = r'''
var t = typeof(Cozy.Grid.HiddenRooms);
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
var o = (UnityEngine.Vector3)t.GetField("_o", bf).GetValue(null);
float cs = (float)t.GetField("_cs", bf).GetValue(null);
var lids = (System.Collections.IList)t.GetField("_lids", bf).GetValue(null);
var mReach = t.GetMethod("Reach", bf);
var mDark = t.GetMethod("Dark", bf);
float floor = Cozy.View.ViewState.CurrentFloorY;
var sb = new System.Text.StringBuilder();
sb.Append("{\"slug\":\"" + Cozy.Grid.LevelIO.CurrentSlug + "\",\"floor\":" + floor.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture)
    + ",\"build\":" + (Cozy.View.ViewState.BuildValid ? "true" : "false") + ",\"room\":" + (Cozy.View.ViewState.RoomValid ? "true" : "false") + ",\"rooms\":[");
var rooms = Cozy.Grid.HiddenRooms.Rooms;
bool first = true;
for (int i = 0; i < rooms.Count && i < lids.Count; i++)
{
    var r = rooms[i];
    if (r.Center.x < BX0 || r.Center.x > BX1 || r.Center.z < BZ0 || r.Center.z > BZ1) continue;
    var lv = lids[i]; var lt = lv.GetType();
    var go = (UnityEngine.GameObject)lt.GetField("Go").GetValue(lv);
    bool on = go != null && go.activeSelf;
    var ops = new System.Text.StringBuilder();
    foreach (var op in r.Openings) ops.Append(Cozy.Grid.ViewSensor.OpeningKindBetween(op.A, op.B, o, cs, r.Level));
    if (!first) sb.Append(",");
    first = false;
    sb.Append("{\"key\":\"" + r.Level.ToString("0.#", System.Globalization.CultureInfo.InvariantCulture) + "@" + r.Center.x.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + "," + r.Center.z.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + "/" + r.Area.Count + "\"");
    sb.Append(",\"doors\":\"" + ops + "\"");
    sb.Append(",\"reach\":" + (int)mReach.Invoke(null, new object[] { i, floor }));
    sb.Append(",\"dark\":" + ((bool)mDark.Invoke(null, new object[] { i, floor }) ? "true" : "false"));
    sb.Append(",\"lid\":" + (on ? "true" : "false"));
    sb.Append(",\"masked\":" + (on && (bool)lt.GetField("Masked").GetValue(lv) ? "true" : "false"));
    sb.Append(",\"topped\":" + ((bool)lt.GetField("Topped").GetValue(lv) ? "true" : "false"));
    sb.Append(",\"dollhouse\":" + ((bool)lt.GetField("Dollhouse").GetValue(lv) ? "true" : "false"));
    sb.Append(",\"fade\":" + ((float)lt.GetField("Fade").GetValue(lv)).ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + "}");
}
sb.Append("]}");
return sb.ToString();
'''.replace('BX0', f'{BOX[0]}f').replace('BX1', f'{BOX[1]}f').replace('BZ0', f'{BOX[2]}f').replace('BZ1', f'{BOX[3]}f')


def teleport(x, y, z):
    return run(f'Cozy.Grid.GridCursor.I.TeleportPlayerTo(new UnityEngine.Vector3({x}f, {y}f, {z}f)); UnityEngine.Physics.SyncTransforms(); return "ok";')


def capture():
    state = run('var p = Cozy.View.ViewState.PlayerPos; return Cozy.Grid.HiddenRooms.FadeSeconds + "|" + Cozy.Grid.HiddenRooms.FadeOutSeconds + "|" + Cozy.View.ViewState.HiddenRooms + "|" + p.x + "|" + p.y + "|" + p.z;')
    if not state or state.startswith('ОШИБКА'):
        sys.exit(f'нет play: {state}')
    fin, fout, flag, px, py, pz = state.split('|')
    slug = run('return Cozy.Grid.LevelIO.CurrentSlug;')
    if slug != SLUG:
        sys.exit(f'нужен уровень {SLUG}, сейчас {slug}')
    if flag != 'True':
        run('Cozy.View.ViewState.HiddenRooms = true; return "ok";')
    run('Cozy.Grid.HiddenRooms.FadeSeconds = 0.01f; Cozy.Grid.HiddenRooms.FadeOutSeconds = 0.01f; return "ok";')
    shots, probes = {}, {}
    try:
        for name, x, y, z in POINTS:
            teleport(x, y, z)
            time.sleep(1.5)
            raw = run(SNAP)
            try:
                shots[name] = json.loads(raw)
            except Exception:
                sys.exit(f'{name}: снимок не прочитан: {raw}')
            if shots[name]['slug'] != SLUG:
                sys.exit(f'{name}: уровень сменился посреди прогона ({shots[name]["slug"]}) — редактор занят другой сессией? эталон не трогаю')
            res = run((REG / 'rooms_probe.cs').read_text(encoding='utf-8')) or ''
            probes[name] = [l for l in res.splitlines() if l.startswith(('ЗЕЛ', 'КРАС', 'FAIL'))]
    finally:
        run(f'Cozy.Grid.HiddenRooms.FadeSeconds = {fin}f; Cozy.Grid.HiddenRooms.FadeOutSeconds = {fout}f; Cozy.View.ViewState.HiddenRooms = {flag.lower()}; return "ok";')
        teleport(px, py, pz)
    return shots, probes


def layout(shot):
    return sorted((r['key'], r['doors']) for r in shot['rooms'])


def main():
    record = len(sys.argv) > 1 and sys.argv[1] == 'record'
    shots, probes = capture()
    red = [f'{n}: {l}' for n, ls in probes.items() for l in ls if not l.startswith('ЗЕЛ')]
    if record:
        if red:
            print('\n'.join(red))
            sys.exit('rooms_probe красная — эталон не пишу')
        GOLDEN.write_text(json.dumps(shots, ensure_ascii=False, indent=1), encoding='utf-8')
        n = sum(len(s['rooms']) for s in shots.values())
        print(f'эталон записан: {GOLDEN} — точек {len(shots)}, строк комнат {n}')
        return
    gold = json.loads(GOLDEN.read_text(encoding='utf-8'))
    bad = list(red)
    for name, shot in shots.items():
        g = gold.get(name)
        if g is None:
            bad.append(f'{name}: нет в эталоне'); continue
        if shot['slug'] != g['slug']:
            sys.exit(f'не тот уровень: {shot["slug"]} (эталон {g["slug"]})')
        if layout(shot) != layout(g):
            sys.exit(f'ЗДАНИЕ ИЗМЕНИЛОСЬ в точке «{name}»: {layout(shot)} ≠ {layout(g)} — переснять: record')
        for k in ('floor', 'build', 'room'):
            if shot[k] != g[k]: bad.append(f'{name}: {k} {shot[k]} ≠ {g[k]}')
        gr = {r['key']: r for r in g['rooms']}
        for r in shot['rooms']:
            e = gr[r['key']]
            for k in ('reach', 'dark', 'lid', 'masked', 'topped', 'dollhouse', 'fade'):
                if r[k] != e[k]: bad.append(f'{name}: комната {r["key"]} {k} {r[k]} ≠ {e[k]}')
    total = sum(len(s['rooms']) for s in shots.values())
    if bad:
        print(f'КРАСНОЕ RM-H: расхождений {len(bad)}')
        print('\n'.join(bad))
        sys.exit(1)
    print(f'ЗЕЛЁНОЕ RM-H: точек {len(shots)}, строк комнат {total}, rooms_probe зелёная во всех точках')


if __name__ == '__main__':
    main()
