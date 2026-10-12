"""Карта кадра в редакторе одной командой: куда уходят мс (главный поток, поток рендера, GPU),
счётчики отрисовки и перепись рендереров. Скил tavern-fps.

python3 fps_probe.py frame [кадров] [метка]   профайлер N кадров (≤250): фазы PlayerLoop (total-мс), поток рендера
                                              без ожиданий, GPU, батчи/сетпассы/треугольники/тени, мусор; дописывает
                                              строку в ~/.cache/tavern-probes/fps_<метка>.txt
python3 fps_probe.py scripts [кадров]         скрипты по TOTAL-мс (Update/LateUpdate/FixedUpdate каждого типа)
python3 fps_probe.py census                   перепись рендереров: всего, рисуемых, с forceRenderingOff, выключенных,
                                              по видам тени; по корням-именам (топ-15 по числу)
python3 fps_probe.py cost [N] 'метка::C#' …     цена куска кода ВНУТРИ кадра игры: мс и мусор (Б) на вызов. Код гоняется
                                              N раз (по умолчанию 100) в Application.onBeforeRender под своим маркером
                                              профайлера, три кадра подряд. Нужен, потому что GC.GetAllocatedBytes… в
                                              Mono редактора всегда 0, Profiler.BeginSample из execute_code вырезан
                                              (Conditional ENABLE_PROFILER), а секундомер не видит мусор.
                                              Код с побочными эффектами (таймеры, deltaTime) сюда не давать.
python3 fps_probe.py ab <C#-вкл> <C#-выкл> [кадров]   A/B: кадр с выражением «выкл» против «вкл» (оба — код
                                              execute_code; «вкл» обязан вернуть как было) — по 2 замера на сторону
python3 fps_probe.py spikes [кадров] [маркер ...]  РЫВКИ по кадрам: сред/медиана/p95/макс кадра, 8 самых медленных кадров
                                              с их маркерами (self ≥ 0,25 мс) и для маркеров по подстроке — сред/макс self
                                              и мусор ПО КАДРАМ. Профиль-среднее прячет рывок: 4 мс раз в 0,5 с выглядят
                                              как 0,07 мс/кадр (11.10: PowerLines.Signature, косяки дверей и окон разом)

⚠️ Редактор врёт втрое против сборки: числа здесь — ОТНОСИТЕЛЬНЫЕ (до/после правки, сценарий против сценария).
⚠️ Game view должен быть в фокусе, иначе редактор троттлит кадр (P687); мерить дважды, первый замер после play скачет.
⚠️ Deep Profile на level1 не включать (P699).
"""
import json, pathlib, subprocess, sys, time, datetime

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
OUT = pathlib.Path.home() / '.cache/tavern-probes'


def run(code, timeout=180):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=timeout, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        return (d.get('data') or {}).get('result') or d.get('message') or d.get('error')
    except Exception:
        return out.stdout[-400:]


def playing():
    return str(run('return UnityEngine.Application.isPlaying;')).lower().startswith('true')


FRAME_CODE = r"""
int last = UnityEditorInternal.ProfilerDriver.lastFrameIndex;
int first = UnityEditorInternal.ProfilerDriver.firstFrameIndex;
if (last < 0) return "no frames";
var V = UnityEditor.Profiling.HierarchyFrameDataView.ViewModes.Default;
int TT = UnityEditor.Profiling.HierarchyFrameDataView.columnTotalTime;
int ST = UnityEditor.Profiling.HierarchyFrameDataView.columnSelfTime;
int GCc = UnityEditor.Profiling.HierarchyFrameDataView.columnGcMemory;
var phase = new System.Collections.Generic.Dictionary<string, double>();
var named = new System.Collections.Generic.Dictionary<string, double>();
string[] watch = { "EditorLoop", "BehaviourUpdate", "LateBehaviourUpdate", "FixedBehaviourUpdate", "Physics.Simulate", "Physics.Processing",
  "Inl_UniversalRenderPipeline.RenderSingleCameraInternal: Main Camera", "CullScriptable", "Inl_Cull", "RenderLoop.ScheduleDraw",
  "Shadows.PrepareShadowmap", "Inl_MainLightShadowCasterPass", "Inl_AdditionalLightsShadowCasterPass", "Inl_DrawOpaqueObjects",
  "Inl_DrawTransparentObjects", "Inl_UberPostProcessPass", "PostLateUpdate.UpdateAllRenderers", "PostLateUpdate.UpdateAllSkinnedMeshes",
  "Gfx.WaitForPresentOnGfxThread", "Gfx.WaitForRenderThread", "GC.Collect", "Camera.Render", "DrawRenderers", "SRPBatcher.Flush",
  "TransformChangeSystem", "UGUI.Rendering.UpdateBatches", "Canvas.SendWillRenderCanvases", "PreLateUpdate.DirectorUpdateAnimationBegin",
  "PreLateUpdate.ParticleSystemBeginUpdateAll", "Profiler.FlushMemoryCounters", "Profiler.CollectGlobalStats", "Culling", "SceneCulling",
  "CullAllVisibleLights", "ShadowCulling", "CullSendEvents", "Gfx.PresentFrame", "FinishFrameRendering" };
var watchSet = new System.Collections.Generic.HashSet<string>(watch);
double renderBusy = 0, gc = 0, mainMs = 0; int frames = 0;
var ids = new System.Collections.Generic.List<int>();
string[] cnames = { "Batches Count", "SetPass Calls Count", "Draw Calls Count", "Triangles Count", "Shadow Casters Count",
  "Visible Skinned Meshes Count", "GC Allocated In Frame", "CPU Main Thread Frame Time", "CPU Render Thread Frame Time", "GPU Frame Time", "CPU Total Frame Time" };
var csum = new double[cnames.Length]; var cn = new int[cnames.Length];
for (int f = System.Math.Max(first, last - SKIP - FRAMES); f <= last - SKIP; f++)
{
    using (var view = UnityEditorInternal.ProfilerDriver.GetHierarchyFrameDataView(f, 0, V, TT, false))
    {
        if (view == null || !view.valid) continue;
        frames++; mainMs += view.frameTimeMs;
        var stack = new System.Collections.Generic.Stack<int[]>();
        stack.Push(new int[] { view.GetRootItemID(), 0, 0 });
        while (stack.Count > 0)
        {
            var it = stack.Pop(); int id = it[0], depth = it[1], inWatch = it[2];
            string name = id == view.GetRootItemID() ? "" : view.GetItemName(id);
            double tot = id == view.GetRootItemID() ? 0 : view.GetItemColumnDataAsSingle(id, TT);
            if (name == "GC.Alloc") gc += view.GetItemColumnDataAsSingle(id, GCc) ;
            int nextWatch = inWatch;
            if (depth == 2 || depth == 1) { double a; phase.TryGetValue((depth == 2 ? "  " : "") + name, out a); phase[(depth == 2 ? "  " : "") + name] = a + tot; }
            if (inWatch == 0 && watchSet.Contains(name)) { double a; named.TryGetValue(name, out a); named[name] = a + tot; }
            view.GetItemChildren(id, ids);
            foreach (var c in ids.ToArray()) stack.Push(new int[] { c, depth + 1, nextWatch });
        }
    }
    using (var rv = UnityEditorInternal.ProfilerDriver.GetHierarchyFrameDataView(f, 1, V, ST, false))
    {
        if (rv != null && rv.valid)
        {
            var st = new System.Collections.Generic.Stack<int>(); st.Push(rv.GetRootItemID());
            while (st.Count > 0)
            {
                int id = st.Pop();
                rv.GetItemChildren(id, ids);
                foreach (var c in ids.ToArray()) st.Push(c);
                if (id == rv.GetRootItemID()) continue;
                string n = rv.GetItemName(id);
                if (n.Contains("Wait") || n.Contains("Semaphore") || n.Contains("Idle")) continue;
                renderBusy += rv.GetItemColumnDataAsSingle(id, ST);
            }
        }
    }
    using (var raw = UnityEditorInternal.ProfilerDriver.GetRawFrameDataView(f, 0))
    {
        if (raw != null && raw.valid)
            for (int i = 0; i < cnames.Length; i++)
            {
                int mid = raw.GetMarkerId(cnames[i]);
                if (mid < 0) continue;
                csum[i] += raw.GetCounterValueAsLong(mid); cn[i]++;
            }
    }
}
if (frames == 0) return "no valid frames";
var sb = new System.Text.StringBuilder();
sb.Append("frames=").Append(frames).Append(" main=").Append((mainMs / frames).ToString("0.00"));
sb.Append(" renderBusy=").Append((renderBusy / frames).ToString("0.00")).Append(" gcB=").Append((gc / frames).ToString("0"));
for (int i = 0; i < cnames.Length; i++)
{
    if (cn[i] == 0) continue;
    double v = csum[i] / cn[i];
    if (cnames[i].Contains("Time")) v /= 1e6;
    sb.Append(" |").Append(cnames[i].Replace(" Count", "").Replace(" ", "")).Append('=').Append(v.ToString(cnames[i].Contains("Time") ? "0.00" : "0"));
}
sb.Append('\n');
var pl = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, double>>(phase);
pl.Sort((x, y) => y.Value.CompareTo(x.Value));
sb.Append("--- фазы (total мс/кадр) ---\n");
foreach (var kv in pl) if (kv.Value / frames >= 0.03) sb.Append((kv.Value / frames).ToString("0.000")).Append("  ").Append(kv.Key).Append('\n');
var nl = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, double>>(named);
nl.Sort((x, y) => y.Value.CompareTo(x.Value));
sb.Append("--- маркеры (total мс/кадр) ---\n");
foreach (var kv in nl) if (kv.Value / frames >= 0.01) sb.Append((kv.Value / frames).ToString("0.000")).Append("  ").Append(kv.Key).Append('\n');
return sb.ToString();
"""

SCRIPTS_CODE = r"""
int last = UnityEditorInternal.ProfilerDriver.lastFrameIndex;
int first = UnityEditorInternal.ProfilerDriver.firstFrameIndex;
var V = UnityEditor.Profiling.HierarchyFrameDataView.ViewModes.Default;
int TT = UnityEditor.Profiling.HierarchyFrameDataView.columnTotalTime;
int CA = UnityEditor.Profiling.HierarchyFrameDataView.columnCalls;
int GCc = UnityEditor.Profiling.HierarchyFrameDataView.columnGcMemory;
var agg = new System.Collections.Generic.Dictionary<string, double[]>();
int frames = 0; var ids = new System.Collections.Generic.List<int>();
for (int f = System.Math.Max(first, last - SKIP - FRAMES); f <= last - SKIP; f++)
using (var view = UnityEditorInternal.ProfilerDriver.GetHierarchyFrameDataView(f, 0, V, TT, false))
{
    if (view == null || !view.valid) continue;
    frames++;
    var st = new System.Collections.Generic.Stack<int>(); st.Push(view.GetRootItemID());
    while (st.Count > 0)
    {
        int id = st.Pop(); string n = id == view.GetRootItemID() ? "" : view.GetItemName(id);
        if (n.EndsWith("[Invoke]") || n.EndsWith("[Coroutine]"))
        {
            double[] a; if (!agg.TryGetValue(n, out a)) agg[n] = a = new double[3];
            a[0] += view.GetItemColumnDataAsSingle(id, TT); a[1] += view.GetItemColumnDataAsSingle(id, CA); a[2] += view.GetItemColumnDataAsSingle(id, GCc);
            continue;
        }
        view.GetItemChildren(id, ids); foreach (var c in ids.ToArray()) st.Push(c);
    }
}
if (frames == 0) return "no frames";
var list = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, double[]>>(agg);
list.Sort((x, y) => y.Value[0].CompareTo(x.Value[0]));
double sum = 0; foreach (var kv in list) sum += kv.Value[0];
var sb = new System.Text.StringBuilder();
sb.Append("frames=").Append(frames).Append(" скрипты всего=").Append((sum / frames).ToString("0.00")).Append(" мс\n");
for (int i = 0; i < System.Math.Min(45, list.Count); i++)
{
    var v = list[i].Value; string n = list[i].Key.Replace(".dll!", " ").Replace(" [Invoke]", "");
    sb.Append((v[0] / frames).ToString("0.000")).Append(" мс  ×").Append((v[1] / frames).ToString("0")).Append("  ").Append((v[2] / frames).ToString("0")).Append(" Б  ").Append(n).Append('\n');
}
return sb.ToString();
"""

CENSUS_CODE = r"""
var all = UnityEngine.Object.FindObjectsByType<UnityEngine.Renderer>(UnityEngine.FindObjectsInactive.Include, UnityEngine.FindObjectsSortMode.None);
int total = all.Length, inactive = 0, disabled = 0, forced = 0, live = 0, shadowsOnly = 0, castOn = 0, visible = 0, liveForcedGo = 0;
var byRoot = new System.Collections.Generic.Dictionary<string, int[]>();
foreach (var r in all)
{
    bool act = r.gameObject.activeInHierarchy;
    string root = r.transform.root.name;
    int cut = root.IndexOf('('); if (cut > 0) root = root.Substring(0, cut);
    var p = r.transform; string key = root;
    var io = r.GetComponentInParent<Cozy.Grid.InteractiveObject>();
    if (io != null && io.Def != null) key = "io:" + io.Def.id;
    int[] a; if (!byRoot.TryGetValue(key, out a)) byRoot[key] = a = new int[4];
    a[0]++;
    if (!act) { inactive++; continue; }
    if (!r.enabled) { disabled++; a[1]++; continue; }
    if (r.forceRenderingOff) { forced++; a[2]++; continue; }
    live++; a[3]++;
    if (r.shadowCastingMode == UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly) shadowsOnly++;
    else if (r.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off) castOn++;
    if (r.isVisible) visible++;
}
var sb = new System.Text.StringBuilder();
sb.Append("рендереров=").Append(total).Append(" неактивных GO=").Append(inactive).Append(" enabled=false: ").Append(disabled)
  .Append(" forceRenderingOff: ").Append(forced).Append(" рисуемых: ").Append(live).Append(" (из них ShadowsOnly ").Append(shadowsOnly)
  .Append(", с тенью ").Append(castOn).Append(", isVisible ").Append(visible).Append(")\n");
var list = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, int[]>>(byRoot);
list.Sort((x, y) => y.Value[0].CompareTo(x.Value[0]));
sb.Append("--- по объектам (всего / enabled=false / forceOff / рисуемых) ---\n");
for (int i = 0; i < System.Math.Min(20, list.Count); i++)
    sb.Append(list[i].Value[0]).Append(" / ").Append(list[i].Value[1]).Append(" / ").Append(list[i].Value[2]).Append(" / ").Append(list[i].Value[3]).Append("  ").Append(list[i].Key).Append('\n');
return sb.ToString();
"""


SPIKES_CODE = r"""
int last = UnityEditorInternal.ProfilerDriver.lastFrameIndex, first = UnityEditorInternal.ProfilerDriver.firstFrameIndex;
var V = UnityEditor.Profiling.HierarchyFrameDataView.ViewModes.Default;
int ST = UnityEditor.Profiling.HierarchyFrameDataView.columnSelfTime;
int GCc = UnityEditor.Profiling.HierarchyFrameDataView.columnGcMemory;
string[] pats = new string[] { PATS };
var sb = new System.Text.StringBuilder();
var frames = new System.Collections.Generic.List<double>();
var perFrame = new System.Collections.Generic.List<string>();
var patSum = new double[pats.Length]; var patMax = new double[pats.Length]; var patGcSum = new double[pats.Length]; var patGcMax = new double[pats.Length]; int n = 0;
var ids = new System.Collections.Generic.List<int>();
for (int f = System.Math.Max(first, last - FRAMES); f <= last; f++)
using (var v = UnityEditorInternal.ProfilerDriver.GetHierarchyFrameDataView(f, 0, V, ST, false))
{
    if (v == null || !v.valid) continue;
    n++;
    frames.Add(v.frameTimeMs);
    var top = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, double>>();
    var pv = new double[pats.Length]; var pg = new double[pats.Length];
    var st = new System.Collections.Generic.Stack<int>(); st.Push(v.GetRootItemID());
    while (st.Count > 0)
    {
        int id = st.Pop(); v.GetItemChildren(id, ids); foreach (var c in ids.ToArray()) st.Push(c);
        if (id == v.GetRootItemID()) continue;
        string name = v.GetItemName(id);
        double self = v.GetItemColumnDataAsSingle(id, ST);
        double gc = v.GetItemColumnDataAsSingle(id, GCc);
        if (self >= 0.25) top.Add(new System.Collections.Generic.KeyValuePair<string, double>(name, self));
        for (int p = 0; p < pats.Length; p++) if (name.Contains(pats[p])) { pv[p] += self; pg[p] += gc; }
    }
    for (int p = 0; p < pats.Length; p++) { patSum[p] += pv[p]; patGcSum[p] += pg[p]; if (pv[p] > patMax[p]) patMax[p] = pv[p]; if (pg[p] > patGcMax[p]) patGcMax[p] = pg[p]; }
    top.Sort((a, b) => b.Value.CompareTo(a.Value));
    var line = new System.Text.StringBuilder();
    line.Append(v.frameTimeMs.ToString("0.00")).Append(" мс:");
    for (int i = 0; i < System.Math.Min(6, top.Count); i++) line.Append("  ").Append(top[i].Key).Append('=').Append(top[i].Value.ToString("0.00"));
    perFrame.Add(line.ToString());
}
if (n == 0) return "no frames";
var sorted = new System.Collections.Generic.List<double>(frames); sorted.Sort();
double avg = 0; foreach (var x in frames) avg += x; avg /= n;
sb.Append("кадров=").Append(n).Append(" сред=").Append(avg.ToString("0.00")).Append(" медиана=").Append(sorted[n / 2].ToString("0.00"))
  .Append(" p95=").Append(sorted[(int)(n * 0.95)].ToString("0.00")).Append(" макс=").Append(sorted[n - 1].ToString("0.00")).Append('\n');
var order = new System.Collections.Generic.List<int>(); for (int i = 0; i < n; i++) order.Add(i);
order.Sort((a, b) => frames[b].CompareTo(frames[a]));
sb.Append("--- самые медленные кадры (self ≥ 0,25 мс) ---\n");
for (int i = 0; i < System.Math.Min(8, n); i++) sb.Append('#').Append(order[i]).Append("  ").Append(perFrame[order[i]]).Append('\n');
sb.Append("--- маркеры по шаблону: сред / макс self мс; сред / макс мусор Б ---\n");
for (int p = 0; p < pats.Length; p++) sb.Append(pats[p]).Append(": ").Append((patSum[p] / n).ToString("0.000")).Append(" / ").Append(patMax[p].ToString("0.00"))
  .Append(" мс; ").Append((patGcSum[p] / n).ToString("0")).Append(" / ").Append(patGcMax[p].ToString("0")).Append(" Б\n");
return sb.ToString();
"""


COST_RUN = r"""
int left = 3;
var marks = new System.IntPtr[COUNT];
for (int i = 0; i < COUNT; i++) marks[i] = Unity.Profiling.LowLevel.Unsafe.ProfilerUnsafeUtility.CreateMarker("ZZcost_" + i, 1, Unity.Profiling.LowLevel.MarkerFlags.Default, 0);
UnityEngine.Events.UnityAction cb = null;
cb = () => {
    if (left-- <= 0) { UnityEngine.Application.onBeforeRender -= cb; return; }
BODY
};
UnityEngine.Application.onBeforeRender += cb;
return "ok";
"""

COST_READ = r"""
int last = UnityEditorInternal.ProfilerDriver.lastFrameIndex, first = UnityEditorInternal.ProfilerDriver.firstFrameIndex;
var sum = new System.Collections.Generic.Dictionary<string, double[]>(); var ids = new System.Collections.Generic.List<int>();
for (int f = first; f <= last; f++)
using (var v = UnityEditorInternal.ProfilerDriver.GetHierarchyFrameDataView(f, 0, UnityEditor.Profiling.HierarchyFrameDataView.ViewModes.Default, UnityEditor.Profiling.HierarchyFrameDataView.columnTotalTime, false))
{
    if (v == null || !v.valid) continue;
    var st = new System.Collections.Generic.Stack<int>(); st.Push(v.GetRootItemID());
    while (st.Count > 0)
    {
        int id = st.Pop(); v.GetItemChildren(id, ids); foreach (var c in ids.ToArray()) st.Push(c);
        if (id == v.GetRootItemID()) continue; string n = v.GetItemName(id);
        if (!n.StartsWith("ZZcost_")) continue;
        double[] a; if (!sum.TryGetValue(n, out a)) sum[n] = a = new double[3];
        a[0] += v.GetItemColumnDataAsSingle(id, UnityEditor.Profiling.HierarchyFrameDataView.columnTotalTime);
        a[1] += v.GetItemColumnDataAsSingle(id, UnityEditor.Profiling.HierarchyFrameDataView.columnGcMemory); a[2]++;
    }
}
var sb = new System.Text.StringBuilder();
foreach (var kv in sum) sb.Append(kv.Key).Append(' ').Append((kv.Value[0] / kv.Value[2]).ToString("0.0000")).Append(' ').Append((kv.Value[1] / kv.Value[2]).ToString("0")).Append(' ').Append(kv.Value[2]).Append('\n');
return sb.ToString();
"""


def cost(n, pieces):
    body = []
    for i, (label, code) in enumerate(pieces):
        body.append('    Unity.Profiling.LowLevel.Unsafe.ProfilerUnsafeUtility.BeginSample(marks[%d]);' % i)
        body.append('    for (int it = 0; it < %d; it++) { %s; }' % (n, code))
        body.append('    Unity.Profiling.LowLevel.Unsafe.ProfilerUnsafeUtility.EndSample(marks[%d]);' % i)
    run('UnityEditorInternal.ProfilerDriver.ClearAllFrames(); UnityEditorInternal.ProfilerDriver.profileEditor = false; '
        'UnityEditorInternal.ProfilerDriver.deepProfiling = false; UnityEditorInternal.ProfilerDriver.enabled = true; return "on";')
    try:
        time.sleep(1.0)
        res = run(COST_RUN.replace('COUNT', str(len(pieces))).replace('BODY', '\n'.join(body)))
        if res != 'ok':
            print('код не скомпилировался:', res); return 1
        time.sleep(2.0)
        out = str(run(COST_READ))
    finally:
        run('UnityEditorInternal.ProfilerDriver.enabled = false; return "off";')
    got = {}
    for line in out.splitlines():
        p = line.split()
        if len(p) == 4:
            got[int(p[0].split('_')[1])] = (float(p[1]), float(p[2]), p[3])
    for i, (label, code) in enumerate(pieces):
        if i not in got:
            print('%-30s нет замера' % label); continue
        ms, gc, frames = got[i]
        print('%-30s %8.4f мс/вызов  %7.0f Б/вызов  (×%d, кадров %s)' % (label, ms / n, gc / n, n, frames))
    return 0


def profiled(code, frames):
    run('UnityEngine.Application.targetFrameRate = -1; UnityEditorInternal.ProfilerDriver.profileEditor = false; '
        'UnityEditorInternal.ProfilerDriver.deepProfiling = false; UnityEditorInternal.ProfilerDriver.ClearAllFrames(); '
        'UnityEditorInternal.ProfilerDriver.enabled = true; return "on";')
    time.sleep(frames / 50.0 + 2.0)
    try:
        return run(code.replace('FRAMES', str(frames)).replace('SKIP', '0'), timeout=300)
    finally:
        run('UnityEditorInternal.ProfilerDriver.enabled = false; return "off";')


def where():
    return run('var p = Cozy.Grid.PlayerRef.Transform; return (p != null ? p.position.ToString("F1") : "нет игрока") + " этаж=" + '
               'Cozy.View.ViewState.CurrentFloorY.ToString("F1") + " внутри=" + Cozy.View.ViewState.BuildValid + " уровень=" + Cozy.Grid.LevelIO.CurrentLevelName;')


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 0
    if not playing():
        print('не в play'); return 1
    cmd = a[0]
    if cmd == 'frame':
        frames = min(int(a[1]) if len(a) > 1 else 200, 250)
        label = a[2] if len(a) > 2 else None
        w = where()
        res = profiled(FRAME_CODE, frames)
        print(w); print(res)
        if label:
            OUT.mkdir(parents=True, exist_ok=True)
            with open(OUT / ('fps_%s.txt' % label), 'a') as f:
                f.write('%s  %s\n%s\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), w, res))
        return 0
    if cmd == 'scripts':
        frames = min(int(a[1]) if len(a) > 1 else 200, 250)
        print(where()); print(profiled(SCRIPTS_CODE, frames)); return 0
    if cmd == 'spikes':
        frames = min(int(a[1]) if len(a) > 1 and a[1].isdigit() else 300, 300)
        pats = [x for x in a[1:] if not x.isdigit()] or ['PieceViewTicker', 'PowerLines.Update', 'DoorPiece.Update', 'WindowPiece.Update', 'GC.Collect']
        code = SPIKES_CODE.replace('PATS', ', '.join('"%s"' % x for x in pats)).replace('FRAMES', str(frames))
        print(where()); print(profiled(code, frames)); return 0
    if cmd == 'census':
        print(where()); print(run(CENSUS_CODE, timeout=300)); return 0
    if cmd == 'cost':
        rest = a[1:]
        n = 100
        if rest and rest[0].isdigit():
            n = int(rest[0]); rest = rest[1:]
        pieces = [(r.split('::', 1)[0], r.split('::', 1)[1]) if '::' in r else (r[:30], r) for r in rest]
        return cost(n, pieces)
    if cmd == 'ab':
        on, off = a[1], a[2]
        frames = int(a[3]) if len(a) > 3 else 120
        sys.path.insert(0, str(pathlib.Path.home() / '.claude/skills/tavern-regress/probes'))
        import gc_probe
        res = []
        try:
            for side, code in (('вкл', on), ('выкл', off), ('вкл', on), ('выкл', off)):
                run(code); time.sleep(1.0)
                avg, mx, ms, p95 = gc_probe.measure(frames)
                res.append((side, ms, avg))
                print('%-5s кадр %.2f мс, мусор %s Б' % (side, ms or 0, avg), flush=True)
        finally:
            run(on)
        for side in ('вкл', 'выкл'):
            v = [r[1] for r in res if r[0] == side and r[1]]
            print('%s: среднее %.2f мс' % (side, sum(v) / max(1, len(v))))
        return 0
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main())
