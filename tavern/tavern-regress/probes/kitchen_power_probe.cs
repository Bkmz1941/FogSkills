// ПИТАНИЕ, НАГРЕВ, ХОЛОД И СВЕТ КУХНИ (KITCHEN.md: KT-ST02–05, FR02, FR04, LT05, LT06, LT08, LT09, AP07; 18.10).
// FR04 с 18.10: холод снят пока (TemperatureSim.ColdOn = false) — ждём, что камера НЕ холодит.
// Для execute_code в play, на ЛЮБОМ уровне. Перебор по признакам дефа, не по списку:
//   tempSources со switchNode — плита; tempSources без тумблера с needsPower — холодильник;
//   FridgeLight в модели — свет камеры; lightRange > 0 — лампы; switches с led — индикаторы.
// Спавнит СВОИ экземпляры в своей зоне (игрок + (0, −90, 0) + 40 м вбок, шаг 6 м). Питание даёт СВОЙ
// временный контур щитка в PowerGrid._circuits (клетки только под своими объектами) и снимает его в finally —
// за один вызов пересчёт контуров (раз в секунду) не успевает. Время гонит НАСТОЯЩИЙ Tick объекта
// (рефлексией, тысячи шагов), свет — LateUpdate своих LampDaylight/FridgeLight. LampsLit возвращается.
// Вывод: «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом и числами; SKIP — что не проверить и почему.
if (!UnityEngine.Application.isPlaying) return "не в play";
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var NS = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var IO = typeof(Cozy.Grid.InteractiveObject);
var cursor = Cozy.Grid.GridCursor.I;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var tick = IO.GetMethod("Tick", NP);
var fTemp = IO.GetField("_tempSrc", NP);
var fSw = IO.GetField("_switches", NP);
var PG = typeof(Cozy.Grid.PowerGrid);
var circuits = PG.GetField("_circuits", NS).GetValue(null) as System.Collections.IList;
var grid = PG.GetField("_grid", NS).GetValue(null) as Cozy.Grid.GridManager;
var keyM = PG.GetMethod("Key", NS);
var zcType = PG.GetNestedType("ZoneCircuit", System.Reflection.BindingFlags.NonPublic);
var sb = new System.Text.StringBuilder();
var skips = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 60) sb.Append("FAIL " + line + "\n"); } };
System.Func<object, string, object> F = (o, n) => o.GetType().GetField(n).GetValue(o);
if (grid == null) return "SKIP: на уровне нет PowerGrid/сетки — питание не проверить";
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
var basePos = Cozy.Grid.PlayerRef.Transform.position + new UnityEngine.Vector3(40f, -90f, 0f);
var circuit = System.Activator.CreateInstance(zcType, true);
var feed = new Cozy.Grid.PowerFeature(true);
zcType.GetField("feature").SetValue(circuit, feed);
zcType.GetField("kind").SetValue(circuit, Cozy.Grid.Utility.Power);
var cells = zcType.GetField("cells").GetValue(circuit) as System.Collections.Generic.HashSet<UnityEngine.Vector3Int>;
bool keepLit = Cozy.Grid.LampDaylight.LampsLit;
float amb = Cozy.View.ViewState.RoomTemperature;
System.Action<UnityEngine.Vector3> Feed = p => { float cs = grid.CellSize; for (int dx = -3; dx <= 3; dx++) for (int dz = -3; dz <= 3; dz++) for (int dy = -1; dy <= 2; dy++) cells.Add((UnityEngine.Vector3Int)keyM.Invoke(null, new object[] { p + new UnityEngine.Vector3(dx * cs, dy * cs, dz * cs), cs })); };
System.Action<Cozy.Grid.InteractiveObject, int> Run = (io, n) => { for (int k = 0; k < n; k++) tick.Invoke(io, null); };
int slot = 0;
System.Func<Cozy.Grid.ObjectDef, Cozy.Grid.InteractiveObject> Spawn = def => {
    var p = basePos + new UnityEngine.Vector3((slot % 8) * 6f, 0f, (slot / 8) * 6f); slot++;
    var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { def, p, 0f });
    if (io != null) { made.Add(io.gameObject); Feed(p); }
    UnityEngine.Physics.SyncTransforms();
    return io;
};
// сколько шагов Tick нужно на ~99 % пути к цели при скорости rate
float dt = UnityEngine.Mathf.Max(UnityEngine.Time.deltaTime, 0.0005f);
System.Func<float, int> StepsFor = rate => UnityEngine.Mathf.Clamp((int)(6.9f / (UnityEngine.Mathf.Max(rate, 0.04f) * 1.6f * dt)) + 10, 50, 200000);
int stoves = 0, fridges = 0, fridgeLights = 0, lamps = 0, leds = 0;
try {
    circuits.Add(circuit);
    foreach (var def in Cozy.Grid.FurnitureCatalog.All()) {
        if (def == null) continue;
        bool hasTemp = def.tempSources != null && def.tempSources.Count > 0;
        bool hasLed = false; if (def.switches != null) foreach (var s in def.switches) if (!string.IsNullOrEmpty(s.led)) hasLed = true;
        bool lamp = def.lightRange > 0f;
        if (!hasTemp && !hasLed && !lamp) continue;
        Cozy.Grid.InteractiveObject io = null;
        try { io = Spawn(def); } catch (System.Exception e) { Check(false, "спавн " + def.id + ": " + (e.InnerException ?? e).Message); continue; }
        if (io == null) continue;
        var srcs = fTemp.GetValue(io) as System.Collections.IList;
        var sws = fSw.GetValue(io) as System.Collections.IList;
        // ── плита: каждая ручка — своя конфорка (ST02), индикатор (ST03), остывание (ST04), без питания (ST05)
        var switched = new System.Collections.Generic.List<object>();
        foreach (var src in srcs) if (F(src, "sw") != null) switched.Add(src);
        if (switched.Count > 0) {
            stoves++;
            foreach (var sw in sws) io.SetSwitch(((UnityEngine.Transform)F(sw, "node")).name, false, true);
            foreach (var src in switched) {
                var sw = F(src, "sw"); var node = ((UnityEngine.Transform)F(sw, "node")).name;
                var sd = F(src, "def"); float target = (float)F(sd, "target"), rate = (float)F(sd, "rate");
                io.SetSwitch(node, true, true);
                Run(io, StepsFor(rate));
                float live = (float)F(src, "live");
                Check(UnityEngine.Mathf.Abs(live - target) <= UnityEngine.Mathf.Max(3f, 0.05f * UnityEngine.Mathf.Abs(target - amb)), "ST02 " + def.id + "/" + node + ": включена, а нагрев " + live.ToString("0") + "° при цели " + target.ToString("0") + "°");
                foreach (var other in switched) if (other != src) {
                    float ol = (float)F(other, "live");
                    Check(UnityEngine.Mathf.Abs(ol - amb) <= 2f, "ST02 " + def.id + "/" + node + ": включили её, а греется и " + ((UnityEngine.Transform)F(F(other, "sw"), "node")).name + " (" + ol.ToString("0") + "°)");
                }
                if (F(sw, "ledMat") != null) Check(F(sw, "ledShown") is bool b1 && b1, "ST03 " + def.id + "/" + node + ": включена, индикатор не горит");
                io.SetSwitch(node, false, true);
                Run(io, StepsFor(rate));
                live = (float)F(src, "live");
                Check(UnityEngine.Mathf.Abs(live - amb) <= 3f, "ST04 " + def.id + "/" + node + ": выключили, а осталось " + live.ToString("0") + "° (комната " + amb.ToString("0") + "°)");
                if (F(sw, "ledMat") != null) Check(F(sw, "ledShown") is bool b2 && !b2, "ST03 " + def.id + "/" + node + ": выключена, индикатор горит");
                if (def.needsPower) {
                    circuits.Remove(circuit);
                    io.SetSwitch(node, true, true);
                    Run(io, StepsFor(rate));
                    live = (float)F(src, "live");
                    Check(UnityEngine.Mathf.Abs(live - amb) <= 3f, "ST05 " + def.id + "/" + node + ": без электричества греет до " + live.ToString("0") + "°");
                    if (F(sw, "ledMat") != null) Check(F(sw, "ledShown") is bool b3 && !b3, "ST05 " + def.id + "/" + node + ": без электричества индикатор горит");
                    io.SetSwitch(node, false, true);
                    circuits.Add(circuit);
                    Run(io, StepsFor(rate));
                }
            }
        }
        // ── холодильник: камера холодит только при питании (FR04)
        var chambers = new System.Collections.Generic.List<object>();
        foreach (var src in srcs) { var sd = F(src, "def"); if (F(src, "sw") == null && !(bool)F(sd, "byFire") && (bool)F(sd, "needsPower") && (float)F(sd, "target") < amb - 5f) chambers.Add(src); }
        bool defCold = false; foreach (var ts in def.tempSources) if (ts.target < amb - 5f) defCold = true;
        { var coldField = typeof(Cozy.Grid.TemperatureSim).GetField("ColdOn"); bool coldOn = coldField == null || (bool)coldField.GetValue(null);
          if (defCold && !coldOn) { fridges++; Check(chambers.Count == 0, "FR04 " + def.id + ": холод снят пока (Илья 18.10), а камера холодит"); } }
        if (chambers.Count > 0) {
            fridges++;
            int steps = 0; foreach (var src in chambers) steps = UnityEngine.Mathf.Max(steps, StepsFor((float)F(F(src, "def"), "rate")));
            Run(io, steps);
            foreach (var src in chambers) { float t = (float)F(F(src, "def"), "target"), live = (float)F(src, "live"); Check(UnityEngine.Mathf.Abs(live - t) <= 2f, "FR04 " + def.id + ": при питании камера " + live.ToString("0.0") + "°, цель " + t.ToString("0.0") + "°"); }
            circuits.Remove(circuit);
            Run(io, steps);
            foreach (var src in chambers) { float live = (float)F(src, "live"); Check(UnityEngine.Mathf.Abs(live - amb) <= 2f, "FR04 " + def.id + ": без питания камера " + live.ToString("0.0") + "°, а комната " + amb.ToString("0.0") + "°"); }
            circuits.Add(circuit);
        }
        // ── свет камеры холодильника (FR02)
        foreach (var fl in io.GetComponentsInChildren<Cozy.Grid.FridgeLight>(true)) {
            fridgeLights++;
            var light = fl.GetComponentInChildren<UnityEngine.Light>(true);
            if (light == null) { Check(false, "FR02 " + def.id + ": у FridgeLight нет Light"); continue; }
            var late = typeof(Cozy.Grid.FridgeLight).GetMethod("LateUpdate", NP);
            Cozy.Grid.AccessFeature sec = null; foreach (var f in io.Features) if (f is Cozy.Grid.AccessFeature a && a.Title == fl.SectionTitle) sec = a;
            if (sec == null) { Check(false, "FR02 " + def.id + ": нет секции «" + fl.SectionTitle + "»"); continue; }
            sec.SetOpen(true); Run(io, 400); late.Invoke(fl, null);
            Check(light.enabled, "FR02 " + def.id + ": дверца открыта, питание есть — свет в камере не горит");
            circuits.Remove(circuit); late.Invoke(fl, null);
            Check(!light.enabled, "FR02 " + def.id + ": без питания свет в камере горит");
            circuits.Add(circuit);
            sec.SetOpen(false); Run(io, 400); late.Invoke(fl, null);
            Check(!light.enabled, "FR02 " + def.id + ": дверца закрыта — свет в камере горит");
        }
        // ── лампы: направление подсветки (LT05), свет = свечение (LT06), днём свой тумблер (LT08), без питания (LT09)
        if (lamp) {
            lamps++;
            var pw = Cozy.Grid.FeatureHost.Get<Cozy.Grid.PowerFeature>(io);
            bool keepOn = pw != null && pw.On;
            var late = typeof(Cozy.Grid.LampDaylight).GetMethod("LateUpdate", NP);
            var fGlow = IO.GetField("_glowShown", NP);
            var lds = io.GetComponentsInChildren<Cozy.Grid.LampDaylight>(true);
            if (lds.Length == 0) { Check(false, "LT06 " + def.id + ": lightRange > 0, а LampDaylight нет"); }
            foreach (var ld in lds) {
                var l = ld.GetComponent<UnityEngine.Light>();
                if (def.lightSpotAngle > 0f && !def.lightForward) Check(ld.transform.forward.y < -0.9f, "LT05 " + def.id + ": прожектор смотрит не вниз, forward " + ld.transform.forward.ToString("0.00"));
                if (ld.owner != null && ld.owner.Far) { skips.Append(def.id + ": за радиусом прорисовки; "); continue; }
                if (pw != null) pw.SetOn(true);
                Cozy.Grid.LampDaylight.LampsLit = true;
                late.Invoke(ld, null);
                if (!ld.roomSwitched) {
                    Check(l.enabled, "LT06 " + def.id + ": включена и с питанием — свет не горит");
                    Check((bool)fGlow.GetValue(io) == l.enabled, "LT06 " + def.id + ": свет " + l.enabled + ", а свечение лампы " + fGlow.GetValue(io));
                    if (pw != null) {
                        Cozy.Grid.LampDaylight.LampsLit = false; late.Invoke(ld, null);
                        Check(l.enabled, "LT08 " + def.id + ": днём лампа со своим тумблером (вкл) погасла");
                        pw.SetOn(false); late.Invoke(ld, null);
                        Check(!l.enabled && !(bool)fGlow.GetValue(io), "LT06 " + def.id + ": тумблер выключен — свет " + l.enabled + ", свечение " + fGlow.GetValue(io));
                        pw.SetOn(true); Cozy.Grid.LampDaylight.LampsLit = true;
                    }
                    if (ld.storeyGated && !ld.alwaysOn) {
                        circuits.Remove(circuit);
                        typeof(Cozy.Grid.LampDaylight).GetField("_recheckAt", NP).SetValue(ld, 0f);
                        late.Invoke(ld, null);
                        Check(!l.enabled && !(bool)fGlow.GetValue(io), "LT09 " + def.id + ": без электричества свет " + l.enabled + ", свечение " + fGlow.GetValue(io));
                        circuits.Add(circuit);
                        typeof(Cozy.Grid.LampDaylight).GetField("_recheckAt", NP).SetValue(ld, 0f);
                        late.Invoke(ld, null);
                        Check(l.enabled, "LT09 " + def.id + ": питание вернули — свет не вернулся");
                    }
                } else skips.Append(def.id + ": потолочная, питание через комнату с выключателем — LT07/09 не здесь; ");
            }
            if (pw != null) pw.SetOn(keepOn);
        }
        // ── индикаторы приборов: цвет свечения свой, не белый (AP07)
        foreach (var sw in sws) {
            var mat = F(sw, "ledMat") as UnityEngine.Material;
            if (mat == null) continue;
            leds++;
            var node = ((UnityEngine.Transform)F(sw, "node")).name;
            bool keep = io.SwitchOn(node);
            io.SetSwitch(node, true, true); Run(io, 3);
            UnityEngine.Color c = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor") : mat.color;
            float h, s, v; UnityEngine.Color.RGBToHSV(c, out h, out s, out v);
            bool shown = F(sw, "ledShown") is bool bs && bs;
            if (shown) Check(s > 0.25f, "AP07 " + def.id + "/" + node + ": индикатор светит почти белым (насыщенность " + s.ToString("0.00") + ", цвет " + c + ")");
            io.SetSwitch(node, keep, true);
        }
        made.Remove(io.gameObject); UnityEngine.Object.DestroyImmediate(io.gameObject);
    }
} finally {
    circuits.Remove(circuit);
    Cozy.Grid.LampDaylight.LampsLit = keepLit;
    foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g);
    UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — плит " + stoves + ", холодильных камер " + fridges + ", света камер " + fridgeLights + ", ламп " + lamps + ", индикаторов " + leds + ", dt " + dt.ToString("0.000") + " (созданное и контур удалены)\n" + sb + (skips.Length > 0 ? "SKIP " + skips : "") + "\nSKIP ST07 (посуда мимо конфорки/в руке — PT-R01/products_probe.py), LT07 (несколько выключателей комнаты — нужен дом с комнатами).";
