"""Кнопка «Пить» у мойки: есть в ОБЕИХ карточках и не зависит от рычага (P182).

Гасит кран и осушает чашу мойки, потом строит план рядов карточки обоими
способами: обычная карточка (examineOnly = true) и осмотр. В обоих должна быть
«Пить». Заодно проверяет, что при воде в чаше кнопка тоже есть. Рычаг и вода
возвращаются как были.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
Cozy.Grid.InteractiveObject sink = null;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
    if (io.Def != null && io.Def.id == "home_sink") sink = io;
if (sink == null) return "КРАСНОЕ: мойки нет в уровне";
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "КРАСНОЕ: нет HudUI";
var ws = sink.GetComponent<Cozy.Grid.WaterSource>();
if (ws == null) return "КРАСНОЕ: у мойки нет крана";
var vol = sink.Liquid;
string kind0 = vol.Kind; float l0 = vol.Litres;
bool tap0 = sink.SwitchOn("TapLever");
var t = typeof(Tavern.UI.HudUI);
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var hostField = t.GetField("_activeHost", bf);
var plan = t.GetMethod("PlanRows", bf);
var rowPlan = t.GetField("_rowPlan", bf);
var was = hostField.GetValue(hud);
var bad = new System.Text.StringBuilder();
try
{
    hostField.SetValue(hud, sink);
    sink.SetSwitch("TapLever", false);
    vol.Set("", 0f);
    if (!ws.Supplied) bad.Append("в дом не идёт вода, проба бессмысленна; ");
    if (ws.Running) bad.Append("кран считается открытым при опущенном рычаге; ");
    foreach (var only in new[] { true, false })
    {
        plan.Invoke(hud, new object[] { null, only, false, sink as Cozy.Grid.IExaminable });
        var list = (System.Collections.IEnumerable)rowPlan.GetValue(hud);
        bool found = false;
        foreach (var item in list)
        {
            var b = item.GetType().GetField("button").GetValue(item);
            if ((b.GetType().GetField("Label").GetValue(b) as string) == "Пить") found = true;
        }
        if (!found) bad.Append(only ? "в обычной карточке нет «Пить» при закрытом кране; " : "в осмотре нет «Пить» при закрытом кране; ");
    }
    vol.Set(Cozy.Grid.LiquidVolume.Water, 2f);
    plan.Invoke(hud, new object[] { null, true, false, sink as Cozy.Grid.IExaminable });
    var withWater = (System.Collections.IEnumerable)rowPlan.GetValue(hud);
    bool ok = false;
    foreach (var item in withWater)
    {
        var b = item.GetType().GetField("button").GetValue(item);
        if ((b.GetType().GetField("Label").GetValue(b) as string) == "Пить") ok = true;
    }
    if (!ok) bad.Append("с водой в чаше «Пить» пропала; ");
    return bad.Length == 0 ? "«Пить» у мойки: есть в обычной карточке и в осмотре, рычаг не при чём :: держится" : "КРАСНОЕ: " + bad.ToString();
}
finally
{
    sink.SetSwitch("TapLever", tap0);
    vol.Set(kind0, l0);
    hostField.SetValue(hud, was);
}
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True)
    try:
        data = json.loads(out.stdout.strip().splitlines()[-1])
        result = data.get('data', {}).get('result') if isinstance(data.get('data'), dict) else None
        if not data.get('success'):
            result = "КРАСНОЕ: " + json.dumps(data.get('data'), ensure_ascii=False)[:300]
    except Exception:
        result = "КРАСНОЕ: мост не ответил: " + out.stdout[-200:]
    print(result)
    return 0 if result and "КРАСНОЕ" not in result else 1


if __name__ == '__main__':
    raise SystemExit(main())
