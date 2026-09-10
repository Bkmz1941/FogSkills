"""Мусор и ВРЕМЯ кадра: базовый замер и A/B-скан по «тикающим» типам (в play, редактор свой).

python3 gc_probe.py                 базовый замер: мусор (среднее, пик) и кадр (мс среднее, p95, пик) за 120 кадров
python3 gc_probe.py scan [кадров]   выключать типы с Update/LateUpdate/FixedUpdate по одному и мерить дельту мусора и мс
python3 gc_probe.py profile [кадров] профайлер редактора: self-мс и мусор ПО МАРКЕРАМ (методам) за N кадров — точнее скана,
                                     у того дельты тонут в шуме ±2 мс; печатает 40 самых дорогих маркеров и все с мусором
Потолка кадров в игре с 10.09 нет (FrameRateConfig: targetFrameRate = -1, Илья: «давай снимем»),
замер это подтверждает явно: при потолке «Main Thread» мерил бы ожидание, а не работу.
Пробник живёт в игре: Assets/Modules/Grid/GcProbe.cs (Begin/Result/ListTicking/SetEnabled).
Между выключением и замером ждётся окно кадров; каждый тип включается обратно в finally.
"""
import json, subprocess, sys, time, pathlib

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line); return (d.get('data') or {}).get('result') or d.get('message')
    except Exception:
        return out.stdout[-200:]


def measure(frames):
    run('Cozy.Grid.GcProbe.Begin(%d); return "ok";' % frames)
    time.sleep(frames / 60.0 + 1.0)
    for _ in range(20):
        res = run('return Cozy.Grid.GcProbe.Result;')
        if res and str(res).startswith('avg='):
            parts = dict(p.split('=') for p in str(res).split())
            return int(parts['avg']), int(parts['max']), float(parts.get('ms', 0)), float(parts.get('p95', 0))
        time.sleep(1)
    return None, None, None, None


def uncap(on):
    run('UnityEngine.Application.targetFrameRate = -1; return "ok";')


PROFILE_CODE = r"""
var sb = new System.Text.StringBuilder();
int last = UnityEditorInternal.ProfilerDriver.lastFrameIndex;
int first = UnityEditorInternal.ProfilerDriver.firstFrameIndex;
if (last < 0) return "no frames";
var agg = new System.Collections.Generic.Dictionary<string, double[]>();
int frames = 0;
double totalMs = 0;
var ids = new System.Collections.Generic.List<int>();
for (int f = System.Math.Max(first, last - FRAMES); f <= last; f++)
{
    using (var view = UnityEditorInternal.ProfilerDriver.GetHierarchyFrameDataView(f, 0, UnityEditor.Profiling.HierarchyFrameDataView.ViewModes.Default, UnityEditor.Profiling.HierarchyFrameDataView.columnSelfTime, false))
    {
        if (view == null || !view.valid) continue;
        frames++;
        totalMs += view.frameTimeMs;
        int root = view.GetRootItemID();
        var stack = new System.Collections.Generic.Stack<int>(); stack.Push(root);
        while (stack.Count > 0)
        {
            int id = stack.Pop();
            view.GetItemChildren(id, ids);
            var kids = ids.ToArray();
            foreach (var c in kids) stack.Push(c);
            if (id == root) continue;
            string name = view.GetItemName(id);
            double self = view.GetItemColumnDataAsSingle(id, UnityEditor.Profiling.HierarchyFrameDataView.columnSelfTime);
            double gc = view.GetItemColumnDataAsSingle(id, UnityEditor.Profiling.HierarchyFrameDataView.columnGcMemory);
            double calls = view.GetItemColumnDataAsSingle(id, UnityEditor.Profiling.HierarchyFrameDataView.columnCalls);
            double[] a; if (!agg.TryGetValue(name, out a)) agg[name] = a = new double[3];
            a[0] += self; a[1] += gc; a[2] += calls;
        }
    }
}
if (frames == 0) return "no valid frames";
sb.Append("frames=").Append(frames).Append(" avgFrameMs=").Append((totalMs / frames).ToString("0.00")).Append('\n');
var list = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, double[]>>(agg);
list.Sort((x, y) => y.Value[0].CompareTo(x.Value[0]));
sb.Append("--- self ms/frame ---\n");
for (int i = 0; i < System.Math.Min(40, list.Count); i++)
    sb.Append((list[i].Value[0] / frames).ToString("0.000")).Append(" ms  calls=").Append((list[i].Value[2] / frames).ToString("0")).Append("  ").Append(list[i].Key).Append('\n');
list.Sort((x, y) => y.Value[1].CompareTo(x.Value[1]));
sb.Append("--- GC bytes/frame ---\n");
for (int i = 0; i < System.Math.Min(30, list.Count); i++)
    if (list[i].Value[1] > 0) sb.Append((list[i].Value[1] / frames).ToString("0")).Append(" B  calls=").Append((list[i].Value[2] / frames).ToString("0")).Append("  ").Append(list[i].Key).Append('\n');
return sb.ToString();
"""


def profile(frames):
    run('UnityEditorInternal.ProfilerDriver.profileEditor = false; UnityEditorInternal.ProfilerDriver.deepProfiling = false; UnityEditorInternal.ProfilerDriver.enabled = true; return "on";')
    time.sleep(frames / 60.0 + 1.5)
    try:
        print(run(PROFILE_CODE.replace('FRAMES', str(frames))))
    finally:
        run('UnityEditorInternal.ProfilerDriver.enabled = false; return "off";')


def main():
    if not str(run('return UnityEngine.Application.isPlaying;')).lower().startswith('true'):
        print('не в play'); sys.exit(1)
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    if len(sys.argv) > 1 and sys.argv[1] == 'profile':
        profile(min(frames, 250))
        return
    uncap(True)
    try:
        if len(sys.argv) < 2 or sys.argv[1] != 'scan':
            avg, mx, ms, p95 = measure(frames)
            print(f'мусор на кадр: среднее {avg} Б, пик {mx} Б; кадр: {ms:.2f} мс среднее, p95 {p95:.2f} мс ({frames} кадров, без потолка)')
            return
        types = [t for t in str(run('return Cozy.Grid.GcProbe.ListTicking();')).split(';') if t]
        print(f'тикающих типов: {len(types)}')
        base, _, bms, _ = measure(frames)
        base2, _, bms2, _ = measure(frames)
        print(f'база: {base} Б/кадр, {bms:.2f} мс (повтор {base2} Б, {bms2:.2f} мс)')
        bms = (bms + bms2) / 2
        rows = []
        for t in types:
            name, cnt = t.split(':')
            try:
                run('return Cozy.Grid.GcProbe.SetEnabled("%s", false);' % name)
                time.sleep(0.5)
                avg, mx, ms, p95 = measure(frames)
            finally:
                run('return Cozy.Grid.GcProbe.SetEnabled("%s", true);' % name)
            if avg is None:
                continue
            rows.append((bms - ms, base - avg, name, cnt, avg, ms))
            print(f'  {name} ×{cnt}: без него {ms:.2f} мс (дельта {bms - ms:+.2f} мс), {avg} Б/кадр (дельта {base - avg:+d})')
        rows.sort(reverse=True)
        print('=== главные источники (дельта к базе, мс за кадр) ===')
        for dms, d, name, cnt, avg, ms in rows[:15]:
            print(f'{dms:+7.2f} мс {d:+8d} Б  {name} ×{cnt}')
    finally:
        uncap(False)


if __name__ == '__main__':
    main()
