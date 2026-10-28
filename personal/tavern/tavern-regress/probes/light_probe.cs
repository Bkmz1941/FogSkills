// СВЕТ (LIGHT.md: LI-GL01, LI-ZN02, LI-ZN04, LI-PW04, LI-PW05, LI-FI01, LI-FI03, LI-VIS05; инфо LI-VIS01; 18.10).
// Дополняет kitchen_power_probe.cs (там LT05/06/08/09 по всем lightRange > 0), здесь — чего там нет.
// Для execute_code в play, на ЛЮБОМ уровне. Перебор по признакам дефа, не по списку:
//   lightRange > 0 — лампа; candle — свеча; torch — факел.
// Лампы спавнит в своей зоне (игрок + (40, −90, 30), шаг 6 м) — там нет щитка, то есть
// «без электричества»; свет считает LateUpdate своих LampDaylight (рефлексией). Уровень проверяется
// только чтением: потолочные лампы уровня при включённом слое ламп не призраки (P1143).
// LampsLit и ShowLamps возвращаются, созданное удаляется в finally.
// Вывод: «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом и числами; INFO и SKIP — что не судим.
if (!UnityEngine.Application.isPlaying) return "не в play";
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var cursor = Cozy.Grid.GridCursor.I;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var late = typeof(Cozy.Grid.LampDaylight).GetMethod("LateUpdate", NP);
var recheck = typeof(Cozy.Grid.LampDaylight).GetField("_recheckAt", NP);
var FPV = typeof(Cozy.Grid.FloorPieceView);
var fpvTick = FPV.GetMethod("Tick", NP);
var fGhost = FPV.GetField("_ghost", NP);
var fLast = FPV.GetField("_last", NP);
var fLampGate = FPV.GetField("_lampGate", NP);
var haloLate = typeof(Cozy.Grid.GlowHalo).GetMethod("LateUpdate", NP);
var fHaloHost = typeof(Cozy.Grid.GlowHalo).GetField("_host", NP);
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
var skips = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 60) sb.Append("FAIL " + line + "\n"); } };
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
var basePos = Cozy.Grid.PlayerRef.Transform.position + new UnityEngine.Vector3(40f, -90f, 30f);
bool keepLit = Cozy.Grid.LampDaylight.LampsLit;
bool keepLamps = Cozy.View.ViewState.ShowLamps;
int slot = 0;
// Огонь (свеча, факел) светит, только если сам виден и стоит на этаже обзора в комнате игрока
// (CandleFire.LightAllowed) — его ставим в 0,6 м от героя на его этаже; всё удаляется в том же вызове,
// кадра с ним не бывает.
var nearPos = Cozy.Grid.PlayerRef.Transform.position + new UnityEngine.Vector3(0.6f, 0f, 0.6f);
nearPos.y = Cozy.View.ViewState.CurrentFloorY;
System.Func<Cozy.Grid.ObjectDef, Cozy.Grid.InteractiveObject> Spawn = def => {
    var p = def.candle || def.torch ? nearPos : basePos + new UnityEngine.Vector3((slot % 8) * 6f, 0f, (slot / 8) * 6f); slot++;
    var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { def, p, 0f });
    if (io != null) made.Add(io.gameObject);
    UnityEngine.Physics.SyncTransforms();
    return io;
};
// Маска зон (LightZones.SetLight) живёт в UniversalAdditionalLightData.renderingLayers; без вызова там значение
// URP по умолчанию (1 = только Indoor без бита этажа), SetLight такого не даёт никогда (к Indoor добавляет этаж).
System.Func<UnityEngine.Light, bool> Zoned = l => {
    if (l.type == UnityEngine.LightType.Directional) return true;
    var data = l.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalLightData>();
    return data != null && data.renderingLayers != 1u && data.renderingLayers != 0u;
};
System.Action<UnityEngine.MonoBehaviour> Frame = mb => { var u = mb.GetType().GetMethod("Update", NP); if (u != null) u.Invoke(mb, null); };
System.Action<Cozy.Grid.LampDaylight> Eval = ld => { recheck.SetValue(ld, 0f); late.Invoke(ld, null); };
int lamps = 0, candles = 0, torches = 0, levelLamps = 0;
var noShadow = new System.Collections.Generic.List<string>();
try {
    // ── 1. Уровень (только чтение): потолочная лампа при включённом слое — не призрак (LI-VIS05, P1143)
    Cozy.View.ViewState.ShowLamps = true;
    foreach (var io in Cozy.Grid.InteractiveObject.All) {
        if (io == null || io.Def == null) continue;
        var v = io.GetComponent<Cozy.Grid.FloorPieceView>();
        if (v == null || !(bool)fLampGate.GetValue(v)) continue;
        fpvTick.Invoke(v, null);
        levelLamps++;
        Check(!(bool)fGhost.GetValue(v), "LI-VIS05 " + io.Def.id + " @" + io.transform.position.ToString("0.0") + ": слой ламп включён, а лампа призраком (накрыта плитой потолка)");
    }
    Cozy.View.ViewState.ShowLamps = keepLamps;
    foreach (var io in Cozy.Grid.InteractiveObject.All) { var v = io != null ? io.GetComponent<Cozy.Grid.FloorPieceView>() : null; if (v != null && (bool)fLampGate.GetValue(v)) fpvTick.Invoke(v, null); }
    if (levelLamps == 0) skips.Append("LI-VIS05: на уровне нет потолочных ламп; ");

    foreach (var def in Cozy.Grid.FurnitureCatalog.All()) {
        if (def == null) continue;
        bool lamp = def.lightRange > 0f, candle = def.candle, torch = def.torch;
        if (!lamp && !candle && !torch) continue;
        Cozy.Grid.InteractiveObject io = null;
        try { io = Spawn(def); } catch (System.Exception e) { Check(false, "спавн " + def.id + ": " + (e.InnerException ?? e).Message); continue; }
        if (io == null) { Check(false, "спавн " + def.id + ": SpawnObject вернул null"); continue; }

        // ── 2. Лампы
        if (lamp) {
            lamps++;
            if (def.lightShadows == false && def.resourceFolder == "Lighting" && !def.outdoorOnly && def.id != "lamp_street_modern") noShadow.Add(def.id);
            var pw = Cozy.Grid.FeatureHost.Get<Cozy.Grid.PowerFeature>(io);
            bool keepOn = pw != null && pw.On;
            var lds = io.GetComponentsInChildren<Cozy.Grid.LampDaylight>(true);
            Check(lds.Length > 0, "LI-ON01 " + def.id + ": lightRange > 0, а LampDaylight нет");
            foreach (var ld in lds) {
                var l = ld.GetComponent<UnityEngine.Light>();
                if (l == null) { Check(false, "LI-ON01 " + def.id + ": у LampDaylight нет Light"); continue; }
                // маска зоны (инв. 135, 221): у созданного кодом источника не «всё»
                Check(Zoned(l), "LI-ZN02 " + def.id + "/" + l.name + ": нет маски зон (renderingLayers по умолчанию) — LightZones не вызван");
                if (ld.owner != null && ld.owner.Far) { skips.Append(def.id + ": за радиусом прорисовки; "); continue; }
                if (pw != null) pw.SetOn(true);
                if (ld.alwaysOn) {
                    // LI-PW05: «всегда» не зависит ни от дня, ни от щитка (в своей зоне щитка нет)
                    Cozy.Grid.LampDaylight.LampsLit = false; Eval(ld);
                    Check(l.enabled, "LI-PW05 " + def.id + ": «всегда горит», а днём без щитка погасла");
                    if (pw != null) { pw.SetOn(false); Eval(ld); Check(!l.enabled, "LI-PW05 " + def.id + ": свой тумблер выключен, а свет горит"); pw.SetOn(true); }
                } else if (!ld.storeyGated && !ld.roomSwitched && pw == null) {
                    // LI-PW04: уличный — городская сеть: ночью горит без щитка, днём нет
                    Cozy.Grid.LampDaylight.LampsLit = true; Eval(ld);
                    Check(l.enabled, "LI-PW04 " + def.id + ": ночью без щитка (городская сеть) не горит");
                    Cozy.Grid.LampDaylight.LampsLit = false; Eval(ld);
                    Check(!l.enabled, "LI-PW04 " + def.id + ": днём горит");
                } else if (ld.storeyGated) {
                    // интерьерная без щитка не горит ни ночью, ни со своим тумблером (LI-PW03)
                    Cozy.Grid.LampDaylight.LampsLit = true; Eval(ld);
                    Check(!l.enabled, "LI-PW03 " + def.id + ": интерьерная лампа без щитка горит");
                }
                // LI-GL01 ореол лампочки горит ровно вместе со своим светом (GlowHalo, 18.10)
                var halo = l.GetComponentInChildren<Cozy.Grid.GlowHalo>(true);
                bool wantHalo = !def.lightForward && string.IsNullOrEmpty(def.haloNodes) && def.resourceFolder != "Special";
                Check(wantHalo == (halo != null), "LI-GL01 " + def.id + ": ореол " + (halo != null ? "есть" : "нет") + ", а ждали " + (wantHalo ? "есть" : "нет"));
                if (halo != null) {
                    var hr = halo.GetComponent<UnityEngine.MeshRenderer>();
                    foreach (bool lit in new[] { true, false }) {
                        Cozy.Grid.LampDaylight.LampsLit = lit; if (pw != null) pw.SetOn(lit); Eval(ld); haloLate.Invoke(halo, null);
                        bool hostSeen = true; var host = fHaloHost.GetValue(halo) as UnityEngine.Renderer; if (host != null) hostSeen = host.enabled && host.gameObject.activeInHierarchy;
                        Check(hr.enabled == (l.enabled && hostSeen), "LI-GL01 " + def.id + ": свет " + l.enabled + ", плафон виден " + hostSeen + ", а ореол " + hr.enabled);
                    }
                    if (pw != null) pw.SetOn(true);
                }
                Cozy.Grid.LampDaylight.LampsLit = keepLit;
            }
            if (pw != null) pw.SetOn(keepOn);
        }

        // ── 3. Свечи: зажечь — свет горит, маска зон; потушить — нет; без воска не зажечь (LI-FI01, LI-ZN04)
        if (candle) {
            candles++;
            Cozy.Grid.CandleFire.SetWax(io, Cozy.Grid.CandleFire.Full);
            bool lit = Cozy.Grid.CandleFire.Ignite(io);
            Check(lit && Cozy.Grid.CandleFire.Burning(io), "LI-FI01 " + def.id + ": полная свеча не зажглась");
            if (io.GetComponent<Cozy.Grid.CandleFire>() is Cozy.Grid.CandleFire cf0) Frame(cf0);
            // пламя у объекта — свой корень сцены (CandleFire.Show), не дочерний: свет берём из поля огня
            var cfl = io.GetComponent<Cozy.Grid.CandleFire>() is Cozy.Grid.CandleFire cf1 ? typeof(Cozy.Grid.CandleFire).GetField("_light", NP).GetValue(cf1) as UnityEngine.Light : null;
            bool any = cfl != null && cfl.enabled && cfl.intensity > 0f;
            if (any) Check(Zoned(cfl), "LI-ZN04 " + def.id + ": у пламени свечи нет маски зон");
            Check(any, "LI-FI01 " + def.id + ": горит, а включённого Light с яркостью > 0 нет");
            var fire = io.GetComponent<Cozy.Grid.CandleFire>();
            if (fire != null) UnityEngine.Object.DestroyImmediate(fire);
            bool after = cfl != null && cfl.enabled && cfl.intensity > 0f;
            Check(!after, "LI-FI01 " + def.id + ": потушили, а свет остался");
            Cozy.Grid.CandleFire.SetWax(io, 0f);
            Check(!Cozy.Grid.CandleFire.Ignite(io), "LI-FI01 " + def.id + ": догоревшая (воск 0) зажглась");
        }

        // ── 4. Факелы: зажечь — свет и пламя, маска зон (LI-FI03, LI-ZN04)
        if (torch) {
            torches++;
            bool lit = Cozy.Grid.TorchFire.Ignite(io);
            Check(lit && Cozy.Grid.TorchFire.Burning(io), "LI-FI03 " + def.id + ": факел не зажёгся");
            if (io.GetComponent<Cozy.Grid.TorchFire>() is Cozy.Grid.TorchFire tf0) Frame(tf0);
            var tfl = io.GetComponent<Cozy.Grid.TorchFire>() is Cozy.Grid.TorchFire tf1 ? typeof(Cozy.Grid.TorchFire).GetField("_light", NP).GetValue(tf1) as UnityEngine.Light : null;
            bool any = tfl != null && tfl.enabled && tfl.intensity > 0f;
            if (any) Check(Zoned(tfl), "LI-ZN04 " + def.id + ": у пламени факела нет маски зон");
            Check(any, "LI-FI03 " + def.id + ": горит, а включённого Light с яркостью > 0 нет");
            var tf = io.GetComponent<Cozy.Grid.TorchFire>();
            if (tf != null) Check(tf.Left > Cozy.Grid.TorchFire.BurnSeconds * 0.9f, "LI-FI03 " + def.id + ": только зажгли, а осталось " + tf.Left.ToString("0") + " с из " + Cozy.Grid.TorchFire.BurnSeconds.ToString("0"));
        }

        made.Remove(io.gameObject); UnityEngine.Object.DestroyImmediate(io.gameObject);
    }
    if (noShadow.Count > 0) info.Append("INFO LI-VIS01: внутренние светильники Lighting без теней (инв. 405, ждёт решения Ильи): " + string.Join(", ", noShadow) + "\n");
} finally {
    Cozy.Grid.LampDaylight.LampsLit = keepLit;
    Cozy.View.ViewState.ShowLamps = keepLamps;
    foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g);
    UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — ламп " + lamps + ", свечей " + candles + ", факелов " + torches + ", потолочных ламп уровня " + levelLamps + " (созданное удалено)\n" + sb + info + (skips.Length > 0 ? "SKIP " + skips : "") + "\nSKIP LI-ON03 (несколько выключателей — нужен дом), LI-FI02/SAVE02 (сейв горящих — нет пробы), LI-HD* (носимый — fog_lamp_probe.py частично).";
