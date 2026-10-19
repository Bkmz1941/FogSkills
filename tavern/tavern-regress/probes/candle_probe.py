#!/usr/bin/env python3
"""Свечи и спички (LIGHT.md §8, коды LI-CA…; Илья 18.10: «добавил свечи и спички, придумай тесты для работы со свечками, вариации»).

python3 candle_probe.py        только в play, на ЛЮБОМ уровне; уровень не меняет и не сохраняет.

Перебор по признаку `ObjectDef.candle` (все свечи каталога) и `matches`, свои экземпляры в 0,6–2 м от героя на его
этаже (свет свечи разрешён только видимому огню на этаже обзора — CandleFire.LightAllowed). Имена своих объектов
начинаются с `probe_candle_`, удаляются во второй фазе (и при сбое — тоже).

Фаза 1 (один вызов): зажечь, пламя на фитиле, повторно не зажечь, воск тает только горя и с верной скоростью
(церковная — своей), форма воска, пламя едет за свечой, свет гаснет вне этажа обзора, сейв (Snapshot), взять/положить
горящую (Taken/Dropped), коробок: кнопка «Зажечь» по остатку, одна попытка — одна спичка (мир и инвентарь).
Фаза 2 (через 1,5 с живых кадров — Destroy в Unity отложенный): «Потушить» погасило и кнопка пропала, воск прежний,
сейв после тушения, огарок догорел и исчез, ни одного осиротевшего пламени.
Вердикт первой строкой: «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N».
"""
import json, os, subprocess, sys, time

MCP = os.path.expanduser('~/.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=300, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
    except Exception:
        return 'ОШИБКА моста: ' + out.stdout[-300:]
    if not d.get('success'):
        return 'ОШИБКА: ' + json.dumps(d, ensure_ascii=False)[:600]
    return str((d.get('data') or {}).get('result'))


COMMON = r'''
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var CF = typeof(Cozy.Grid.CandleFire);
var fLight = CF.GetField("_light", NP);
var fFlame = CF.GetField("_flame", NP);
var fLeft = CF.GetField("_left", NP);
var mUpd = CF.GetMethod("Update", NP);
var mSnap = typeof(Cozy.Grid.LevelIO).GetMethod("Snapshot", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
System.Func<Cozy.Grid.InteractiveObject, Cozy.Grid.LevelIO.ObjectData> Snap = io => (Cozy.Grid.LevelIO.ObjectData)mSnap.Invoke(null, new object[] { io });
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 60) sb.Append("FAIL " + line + "\n"); } };
System.Func<int> Flames = () => { int n = 0; foreach (var g in UnityEngine.Object.FindObjectsByType<UnityEngine.GameObject>(UnityEngine.FindObjectsSortMode.None)) if (g.name == "CandleFlame") n++; return n; };
System.Func<Cozy.Grid.InteractiveObject, string, System.Nullable<Cozy.Grid.FeatureButton>> Button = (io, label) => {
    foreach (var f in io.Features) foreach (var b in f.Buttons(null)) if (b.Label == label) return b;
    return null;
};
'''

PHASE1 = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
''' + COMMON + r'''
var cursor = Cozy.Grid.GridCursor.I;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var player = Cozy.Grid.PlayerRef.Transform.position;
float floorY = Cozy.View.ViewState.CurrentFloorY;
int slot = 0, candles = 0;
int baseFlames = Flames();
System.Func<Cozy.Grid.ObjectDef, bool, Cozy.Grid.InteractiveObject> Spawn = (def, far) => {
    var p = far ? player + new UnityEngine.Vector3(40f, -90f, 30f + slot * 2f)
                : new UnityEngine.Vector3(player.x + 0.6f + (slot % 6) * 0.3f, floorY, player.z + 0.6f + (slot / 6) * 0.3f);
    slot++;
    var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { def, p, 0f });
    if (io != null) io.gameObject.name = "probe_candle_" + def.id + "_" + slot;
    UnityEngine.Physics.SyncTransforms();
    return io;
};
System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Transform> Wick = io => Cozy.Grid.FurnitureModel.FindNode(io.transform, "WaxWick");
float dt = UnityEngine.Time.deltaTime;
try {
    foreach (var def in Cozy.Grid.FurnitureCatalog.All()) {
        if (def == null || !def.candle) continue;
        candles++;
        var io = Spawn(def, false);
        if (io == null) { Check(false, "спавн " + def.id); continue; }
        Cozy.Grid.CandleFire.SetWax(io, Cozy.Grid.CandleFire.Full);
        // CA01 зажечь: тем же путём, что спичка (Ignition.Can → Light)
        Check(Cozy.Grid.Ignition.Can(io), "LI-CA01 " + def.id + ": полную свечу нельзя поджечь (Ignition.Can = false)");
        Check(Cozy.Grid.Ignition.Light(io) && Cozy.Grid.CandleFire.Burning(io), "LI-CA01 " + def.id + ": не зажглась");
        var fire = io.GetComponent<Cozy.Grid.CandleFire>();
        if (fire == null) continue;
        mUpd.Invoke(fire, null);
        var l = fLight.GetValue(fire) as UnityEngine.Light;
        var flame = fFlame.GetValue(fire) as UnityEngine.GameObject;
        Check(l != null && l.enabled && l.intensity > 0f, "LI-CA01 " + def.id + ": горит, а свет не горит");
        Check(flame != null, "LI-CA01 " + def.id + ": горит, а пламени нет");
        var wick = Wick(io);
        if (flame != null && wick != null) {
            var wr = wick.GetComponent<UnityEngine.Renderer>();
            var top = wr != null ? new UnityEngine.Vector3(wr.bounds.center.x, wr.bounds.max.y, wr.bounds.center.z) : wick.position;
            var fp = flame.transform.position;
            float side = new UnityEngine.Vector2(fp.x - top.x, fp.z - top.z).magnitude;
            Check(side <= 0.03f && fp.y >= top.y - 0.03f && fp.y <= top.y + 0.12f, "LI-CA01 " + def.id + ": пламя не на фитиле — вбок " + (side * 100f).ToString("0.0") + " см, по высоте " + ((fp.y - top.y) * 100f).ToString("0.0") + " см");
        } else if (wick == null) sb.Append("INFO " + def.id + ": нет узла WaxWick — положение пламени не проверено\n");
        // CA03 горящую повторно не поджечь (и спичка не тратится — HUD тратит только при Can)
        Check(!Cozy.Grid.Ignition.Can(io), "LI-CA03 " + def.id + ": горящую можно поджечь ещё раз — спичка уйдёт впустую");
        // CA04 воск тает только горя, со своей скоростью
        float burn = def.churchCandle ? Cozy.Grid.CandleFire.ChurchBurnSeconds : Cozy.Grid.CandleFire.BurnSeconds;
        float w0 = io.Wax; int k = 400;
        for (int i = 0; i < k; i++) mUpd.Invoke(fire, null);
        float want = k * dt / burn * 100f, got = w0 - io.Wax;
        Check(UnityEngine.Mathf.Abs(got - want) <= UnityEngine.Mathf.Max(0.002f, want * 0.1f), "LI-CA04 " + def.id + ": за " + (k * dt).ToString("0.00") + " с горения воск −" + got.ToString("0.000") + "%, ждали −" + want.ToString("0.000") + "% (срок " + burn.ToString("0") + " с)");
        // CA09 пламя едет за свечой
        io.transform.position += new UnityEngine.Vector3(0.4f, 0f, 0f);
        UnityEngine.Physics.SyncTransforms();
        mUpd.Invoke(fire, null);
        if (flame != null && wick != null) {
            var fp = flame.transform.position; var wp = wick.position;
            float side = new UnityEngine.Vector2(fp.x - wp.x, fp.z - wp.z).magnitude;
            Check(side <= 0.03f, "LI-CA09 " + def.id + ": свечу сдвинули на 40 см, пламя отстало на " + (side * 100f).ToString("0.0") + " см");
        }
        // CA10 сейв горящей: Snapshot пишет воск и огонь
        Cozy.Grid.CandleFire.SetWax(io, 37f);
        var od = Snap(io);
        Check(UnityEngine.Mathf.Abs(od.wax - 37f) < 0.01f && od.fireLit, "LI-CA10 " + def.id + ": сейв горящей — wax " + od.wax.ToString("0.0") + ", fireLit " + od.fireLit);
        // CA11 взять горящую в руку и положить: воск и огонь едут с вещью
        var item = Cozy.Grid.Items.ById(def.pickupItemId);
        if (item == null) sb.Append("INFO " + def.id + ": нет предмета " + def.pickupItemId + " — Taken/Dropped не проверены\n");
        else {
            var pi = new Cozy.Grid.PlacedItem { def = item };
            Cozy.Grid.CandleFire.Taken(io, pi);
            Check(UnityEngine.Mathf.Abs(pi.charge - 37f) < 0.01f && Cozy.Grid.TorchFire.BurningItem(pi), "LI-CA11 " + def.id + ": взяли горящую — в вещи воск " + pi.charge.ToString("0.0") + ", горит " + Cozy.Grid.TorchFire.BurningItem(pi));
            var io2 = Spawn(def, false);
            if (io2 != null) {
                Cozy.Grid.CandleFire.Dropped(io2, pi);
                Check(UnityEngine.Mathf.Abs(io2.Wax - 37f) < 0.01f && Cozy.Grid.CandleFire.Burning(io2), "LI-CA11 " + def.id + ": положили горящую — воск " + io2.Wax.ToString("0.0") + ", горит " + Cozy.Grid.CandleFire.Burning(io2));
                Check(!Cozy.Grid.TorchFire.BurningItem(pi), "LI-CA11 " + def.id + ": положили, а вещь в инвентаре всё ещё «горит»");
            }
        }
        // CA02 «Потушить» есть у горящей; жмём — проверка во второй фазе
        var douse = Button(io, "Потушить");
        Check(douse.HasValue && douse.Value.Enabled, "LI-CA02 " + def.id + ": у горящей нет кнопки «Потушить»");
        if (douse.HasValue) { try { douse.Value.OnClick(); } catch (System.NullReferenceException) { } }
        io.gameObject.name = "probe_candle_doused_" + def.id + "_" + io.Wax.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture);
        // CA08 форма воска по остатку; CA07 огарок с воском 0 не зажигается
        var w = Spawn(def, false);
        if (w != null) {
            var waxNode = Cozy.Grid.FurnitureModel.FindNode(w.transform, "Wax");
            Cozy.Grid.CandleFire.SetWax(w, 50f);
            if (waxNode != null) {
                float wantZ = UnityEngine.Mathf.Lerp(UnityEngine.Mathf.Clamp(Cozy.Grid.CandleFire.WaxLeft, 0.02f, 1f), 1f, 0.5f);
                Check(UnityEngine.Mathf.Abs(waxNode.localScale.z - wantZ) < 0.01f, "LI-CA08 " + def.id + ": воск 50 %, а высота воска " + waxNode.localScale.z.ToString("0.00") + " (ждали " + wantZ.ToString("0.00") + ")");
            } else sb.Append("INFO " + def.id + ": нет узла Wax — форма не проверена\n");
            Cozy.Grid.CandleFire.SetWax(w, 0f);
            Check(!Cozy.Grid.CandleFire.Ignite(w), "LI-CA07 " + def.id + ": воск 0, а зажглась");
        }
        // CA06 огарок догорает и исчезает — проверка во второй фазе
        var stub = Spawn(def, false);
        if (stub != null) {
            Cozy.Grid.CandleFire.SetWax(stub, 0.02f);
            Check(Cozy.Grid.CandleFire.Ignite(stub), "LI-CA06 " + def.id + ": огарок 0,02 % не зажёгся");
            stub.gameObject.name = "probe_candle_stub_" + def.id;
        }
        // CA15 вне этажа обзора свет не горит
        var far = Spawn(def, true);
        if (far != null) {
            Cozy.Grid.CandleFire.SetWax(far, 100f); Cozy.Grid.CandleFire.Ignite(far);
            var ff = far.GetComponent<Cozy.Grid.CandleFire>();
            if (ff != null) { mUpd.Invoke(ff, null); var fl = fLight.GetValue(ff) as UnityEngine.Light; Check(fl == null || !fl.enabled, "LI-CA15 " + def.id + ": горит за 90 м под этажом обзора, а свет включён"); }
        }
    }
    // ── CA18 шкаф: свеча на полке за створкой. Закрыли — гаснет (Илья 18.10: «гаснуть»), открытый — горит.
    // Первый по каталогу напольный хозяин со слотом за створкой; свеча кладётся на площадку слота и
    // привязывается настоящим GridCursor.ReattachToContainer (тот же путь, что после постановки).
    var candleDef = Cozy.Grid.FurnitureCatalog.ById("candle_1");
    int cabinets = 0;
    foreach (var cdef in Cozy.Grid.FurnitureCatalog.All()) {
        if (cabinets >= 2 || cdef == null || !cdef.openable || cdef.mount != Cozy.Grid.ObjectMount.Floor || string.IsNullOrEmpty(cdef.slotNodes)) continue;
        var cab = Spawn(cdef, true);
        if (cab == null) continue;
        cab.gameObject.name = "probe_candle_cab_" + cdef.id;
        Cozy.Grid.ContainerSlot gated = null; UnityEngine.Collider pad = null;
        foreach (var sl in cab.GetComponentsInChildren<Cozy.Grid.ContainerSlot>(true)) {
            if (sl.Gate == null) continue;
            sl.Gate.SetOpen(true);
            var c = sl.GetComponent<UnityEngine.Collider>();
            if (c != null && (sl.accepts == null || sl.accepts.Length == 0)) { gated = sl; pad = c; break; }
        }
        if (gated == null) continue;
        var cand = Spawn(candleDef, true);
        if (cand == null) continue;
        var b = pad.bounds;
        cand.transform.position = new UnityEngine.Vector3(b.center.x, b.max.y + 0.002f, b.center.z);
        UnityEngine.Physics.SyncTransforms();
        cursor.ReattachToContainer(cand);
        if (!ReferenceEquals(cand.Container, cab)) { sb.Append("INFO LI-CA18 " + cdef.id + ": свеча на площадке слота не привязалась к шкафу — пропуск\n"); continue; }
        Cozy.Grid.CandleFire.SetWax(cand, 80f);
        Check(Cozy.Grid.Ignition.Light(cand), "LI-CA18 " + cdef.id + ": свеча в открытом шкафу не зажглась");
        cabinets++;
        if (cabinets == 1) {
            gated.Gate.SetOpen(false);
            Check(Cozy.Grid.ContainerSlot.HoldsClosed(cand), "LI-CA18 " + cdef.id + ": створку закрыли, а свеча не считается закрытой (HoldsClosed)");
            cand.gameObject.name = "probe_candle_shut_" + cdef.id;
        } else cand.gameObject.name = "probe_candle_open_" + cdef.id;
    }
    if (cabinets < 2) sb.Append("INFO LI-CA18: шкафов со слотом за створкой нашлось " + cabinets + " из 2\n");

    // ── Спички: коробок в мире
    var box = Spawn(Cozy.Grid.FurnitureCatalog.ById("matches"), false);
    if (box == null) Check(false, "LI-CA13 спавн коробка matches");
    else {
        int n0 = box.HasCount ? box.Count : -1;
        Check(n0 > 0, "LI-CA13 новый коробок: спичек " + n0);
        var ign = Button(box, "Зажечь");
        Check(ign.HasValue && ign.Value.Enabled, "LI-CA13 у полного коробка нет активной «Зажечь»");
        var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
        var H = typeof(Tavern.UI.HudUI);
        if (hud != null) {
            H.GetField("_igniteBox", NP).SetValue(hud, box);
            H.GetMethod("SpendMatch", NP).Invoke(hud, null);
            Check(box.Count == n0 - 1, "LI-CA14 одна попытка из коробка в мире: было " + n0 + ", стало " + box.Count);
            H.GetField("_igniteBox", NP).SetValue(hud, null);
            var mi = Cozy.Grid.Items.Matches;
            var pm = new Cozy.Grid.PlacedItem { def = mi, charge = mi.piecesInside };
            int p0 = mi.PiecesLeft(pm.charge);
            H.GetField("_igniteMatches", NP).SetValue(hud, pm);
            H.GetMethod("SpendMatch", NP).Invoke(hud, null);
            H.GetField("_igniteMatches", NP).SetValue(hud, null);
            Check(mi.PiecesLeft(pm.charge) == p0 - 1, "LI-CA14 одна попытка из коробка в инвентаре: было " + p0 + ", стало " + mi.PiecesLeft(pm.charge));
        } else sb.Append("INFO нет HudUI — трата спичек не проверена\n");
        box.SetCount(0);
        var ign0 = Button(box, "Зажечь");
        Check(!ign0.HasValue || !ign0.Value.Enabled, "LI-CA13 пустой коробок: «Зажечь» активна");
        box.gameObject.name = "probe_candle_box";
    }
} catch (System.Exception e) {
    Check(false, "исключение: " + (e.InnerException ?? e).Message);
}
return "P1|" + fails + "|" + checks + "|" + candles + "|" + baseFlames + "\n" + sb;
'''

PHASE2 = r'''
''' + COMMON + r'''
int baseFlames = BASE;
int doused = 0, stubs = 0;
var mine = new System.Collections.Generic.List<UnityEngine.GameObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All) {
    if (io == null || !io.gameObject.name.StartsWith("probe_candle_")) continue;
    mine.Add(io.gameObject);
    string n = io.gameObject.name;
    if (n.StartsWith("probe_candle_doused_")) {
        doused++;
        string id = n.Substring("probe_candle_doused_".Length); int us = id.LastIndexOf('_');
        float waxThen = float.Parse(id.Substring(us + 1), System.Globalization.CultureInfo.InvariantCulture); id = id.Substring(0, us);
        Check(!Cozy.Grid.CandleFire.Burning(io), "LI-CA02 " + id + ": «Потушить» нажали, а свеча горит");
        Check(!Button(io, "Потушить").HasValue, "LI-CA02 " + id + ": потушенная, а кнопка «Потушить» осталась");
        Check(UnityEngine.Mathf.Abs(io.Wax - waxThen) < 0.05f, "LI-CA02 " + id + ": воск после тушения " + io.Wax.ToString("0.00") + ", был " + waxThen.ToString("0.00") + " — тает потушенная");
        Check(Cozy.Grid.Ignition.Can(io), "LI-CA02 " + id + ": потушенную с воском нельзя зажечь снова");
        var od = Snap(io);
        Check(!od.fireLit, "LI-CA10 " + id + ": сейв потушенной — fireLit = true");
    }
    if (n.StartsWith("probe_candle_shut_")) Check(!Cozy.Grid.CandleFire.Burning(io), "LI-CA18 " + n.Substring(18) + ": створку шкафа закрыли, а свеча внутри горит");
    if (n.StartsWith("probe_candle_open_")) Check(Cozy.Grid.CandleFire.Burning(io), "LI-CA18 " + n.Substring(18) + ": шкаф открыт, а свеча на полке погасла");
    if (n.StartsWith("probe_candle_stub_")) { stubs++; Check(false, "LI-CA06 " + n.Substring(18) + ": огарок 0,02 % за 1,5 с не догорел — объект остался"); }
}
foreach (var g in mine) if (g != null) UnityEngine.Object.DestroyImmediate(g);
UnityEngine.Physics.SyncTransforms();
return "P2|" + fails + "|" + checks + "|" + doused + "|" + mine.Count + "\n" + sb;
'''

COUNT_FLAMES = COMMON + r'''
return "F|" + Flames();
'''

CLEANUP = r'''
var mine = new System.Collections.Generic.List<UnityEngine.GameObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.gameObject.name.StartsWith("probe_candle_")) mine.Add(io.gameObject);
foreach (var g in mine) UnityEngine.Object.DestroyImmediate(g);
return "убрано " + mine.Count;
'''


def main():
    r1 = run(PHASE1)
    if not r1.startswith('P1|'):
        print('КРАСНОЕ: проба не прошла фазу 1 —', r1[:600])
        print(run(CLEANUP))
        sys.exit(1)
    head, _, body1 = r1.partition('\n')
    _, f1, c1, candles, base = head.split('|')
    time.sleep(1.5)
    r2 = run(PHASE2.replace('BASE', base))
    if not r2.startswith('P2|'):
        print('КРАСНОЕ: проба не прошла фазу 2 —', r2[:600])
        print(run(CLEANUP))
        sys.exit(1)
    head2, _, body2 = r2.partition('\n')
    _, f2, c2, doused, removed = head2.split('|')
    time.sleep(0.3)
    flames = run(COUNT_FLAMES)
    left = int(flames.split('|')[1]) if flames.startswith('F|') else -1
    leak_fail = 0 if left == int(base) else 1
    fails = int(f1) + int(f2) + leak_fail
    checks = int(c1) + int(c2) + 1
    verdict = ('ЗЕЛЁНОЕ из %d' % checks) if fails == 0 else ('КРАСНОЕ: %d из %d' % (fails, checks))
    print('%s — свечей %s, потушено кнопкой %s, своих объектов убрано %s' % (verdict, candles, doused, removed))
    sys.stdout.write(body1 + body2)
    if leak_fail:
        print('FAIL LI-CA12: пламени CandleFlame в сцене было %s, после пробы %s — осиротевшее пламя' % (base, left))
    print('SKIP LI-CA05 (свеча в гнездо подсвечника — настоящим конвейером, нет пробы), LI-CA16 (поджиг в руке через HUD), LI-CA17 (сейв → загрузка уровня — level_roundtrip.py)')
    print(verdict)  # check_all.py показывает последнюю строку
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
