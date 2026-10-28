"""Кнопка «Пить» у мойки (P182, инвариант 46; правило Ильи 19.09: «пить можно
только если вода вкл», отменяет 03.09 «пьют и при закрытом рычаге»).

Строит план рядов карточки обоими способами — обычная карточка (examineOnly =
true) и осмотр: кран открыт → «Пить» в обоих; кран закрыт и чаша пуста → «Пить»
нет; кран закрыт, в чаше 2 л воды → «Пить» есть. Рычаг и вода возвращаются как были.
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
    System.Func<bool, bool> hasDrink = only =>
    {
        plan.Invoke(hud, new object[] { null, only, false, sink as Cozy.Grid.IExaminable });
        foreach (var item in (System.Collections.IEnumerable)rowPlan.GetValue(hud))
        {
            var b = item.GetType().GetField("button").GetValue(item);
            if ((b.GetType().GetField("Label").GetValue(b) as string) == "Пить") return true;
        }
        return false;
    };
    vol.Set("", 0f);
    sink.SetSwitch("TapLever", true);
    if (!ws.Supplied) bad.Append("в дом не идёт вода, проба бессмысленна; ");
    else
    {
        if (!ws.Running) bad.Append("кран не открылся рычагом; ");
        if (!hasDrink(true)) bad.Append("кран открыт, а в обычной карточке нет «Пить»; ");
        if (!hasDrink(false)) bad.Append("кран открыт, а в осмотре нет «Пить»; ");
    }
    sink.SetSwitch("TapLever", false);
    if (ws.Running) bad.Append("кран считается открытым при опущенном рычаге; ");
    if (hasDrink(true) || hasDrink(false)) bad.Append("кран закрыт, чаша пуста, а «Пить» есть; ");
    vol.Set(Cozy.Grid.LiquidVolume.Water, 2f);
    if (!hasDrink(true)) bad.Append("кран закрыт, в чаше 2 л воды, а «Пить» нет; ");
    return bad.Length == 0 ? "«Пить» у мойки: открытый кран — в обеих карточках, закрытый и пустая чаша — нет, вода в чаше — есть :: держится" : "КРАСНОЕ: " + bad.ToString();
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
