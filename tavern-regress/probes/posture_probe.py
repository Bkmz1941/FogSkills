"""Характеризующий замер ПОЗ игрока: «Спрятаться», «Сесть», «Лечь».

Прогоняет по каждому объекту с позой (hideable / chair / bed) полный цикл
«свободно → вошёл → чужие кнопки → вышел» и печатает НАБЛЮДАЕМОЕ поведение:
подписи и доступность кнопок, бейджи, флаги поз, клип, позу игрока, число
включённых рендереров (укрытие гасит фигуру). Вход и выход идут через РЕАЛЬНУЮ
кнопку карточки с HudUI в роли IFeatureContext — то есть тем же путём, что у
игрока, а не в обход.

Зачем: рефакторинг трёх поз в одну базу обязан сохранить поведение. Протокол —
`README.md`: замер «ДО» в файл, правка, замер «ПОСЛЕ» в другой файл, дифф
построчно; между прогонами сцену не трогать.

    python3 posture_probe.py > /tmp/posture_before.txt
    ... правка, перекомпиляция, play ...
    python3 posture_probe.py > /tmp/posture_after.txt
    diff /tmp/posture_before.txt /tmp/posture_after.txt

Задвинутый в стол стул сесть не даёт, поэтому проба временно выдвигает его на
0.6 от стола (как `sit_probe.cs`) и возвращает на место — иначе ветка «Сесть»
не измеряется вовсе.

Поза игрока, позиция выдвинутого стула, состояние створок укрытия и активная
поза возвращаются в finally.
"""
import json, subprocess, sys

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var player = Cozy.Grid.PlayerRef.GameObject;
if (hud == null) return "КРАСНОЕ: нет HudUI";
if (player == null) return "КРАСНОЕ: нет игрока";
var cc = player.GetComponent<UnityEngine.CharacterController>();
var sb = new System.Text.StringBuilder();

System.Func<Cozy.Grid.ObjectFeature, string> kind = f =>
    f is Cozy.Grid.HideFeature ? "hide" : (f is Cozy.Grid.SitFeature ? "sit" : (f is Cozy.Grid.SleepFeature ? "sleep" : ""));

var hosts = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io == null || io.Def == null) continue;
    foreach (var f in io.Features) if (kind(f) != "") { hosts.Add(io); break; }
}
System.Func<Cozy.Grid.InteractiveObject, string> key = io => io.Def.id + "@" + io.transform.position.ToString("0.00");
hosts.Sort(delegate (Cozy.Grid.InteractiveObject a, Cozy.Grid.InteractiveObject b) { return string.CompareOrdinal(key(a), key(b)); });

System.Func<Cozy.Grid.ObjectFeature, string> btns = f =>
{
    var s = new System.Text.StringBuilder();
    foreach (var b in f.Buttons(hud)) { if (s.Length > 0) s.Append(","); s.Append(b.Label); s.Append(b.Enabled ? "+" : "-"); }
    if (f.Disabled) s.Append("[выкл]");
    return s.Length == 0 ? "нет" : s.ToString();
};
System.Func<Cozy.Grid.InteractiveObject, string> badges = io =>
{
    var list = new System.Collections.Generic.List<Cozy.Grid.StateBadge>();
    io.CollectBadges(list);
    var s = new System.Text.StringBuilder();
    foreach (var b in list) { if (s.Length > 0) s.Append(","); s.Append(b.icon); s.Append(":"); s.Append(b.label); }
    return s.Length == 0 ? "нет" : s.ToString();
};
System.Func<int> vis = () =>
{
    int n = 0;
    foreach (var r in player.GetComponentsInChildren<UnityEngine.Renderer>()) if (r.enabled) n++;
    return n;
};
System.Func<string> gstate = () =>
{
    string clip = Cozy.Grid.SitFeature.Clip;
    if (clip == null) clip = Cozy.Grid.SleepFeature.Clip;
    if (clip == null) clip = "-";
    return "спрятан=" + Cozy.Grid.HideFeature.PlayerHidden + " сидит=" + Cozy.Grid.SitFeature.PlayerSeated
        + " лежит=" + Cozy.Grid.SleepFeature.PlayerLying + " клип=" + clip
        + " рукиНаСтоле=" + Cozy.Grid.SitFeature.HandsOnTable
        + " корень=" + player.transform.position.ToString("0.00")
        + " курс=" + player.transform.eulerAngles.y.ToString("0.0")
        + " контроллер=" + (cc != null && cc.enabled) + " рендереров=" + vis();
};
System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3> awayFromTable = ch =>
{
    Cozy.Grid.InteractiveObject best = null;
    float bd = 1e9f;
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || io.Def == null || ReferenceEquals(io, ch) || io.Def.seatCount <= 0) continue;
        float d = UnityEngine.Vector3.Distance(io.WorldBounds.center, ch.transform.position);
        if (d < bd) { bd = d; best = io; }
    }
    if (best == null) return UnityEngine.Vector3.zero;
    var dir = ch.transform.position - best.WorldBounds.center;
    dir.y = 0f;
    return dir.sqrMagnitude < 1e-4f ? UnityEngine.Vector3.zero : dir.normalized;
};
System.Action toStart = null;

var pos0 = player.transform.position;
var rot0 = player.transform.rotation;
bool ccOn0 = cc != null && cc.enabled;
toStart = () =>
{
    if (cc != null) cc.enabled = false;
    player.transform.SetPositionAndRotation(pos0, rot0);
    if (cc != null) cc.enabled = ccOn0;
    UnityEngine.Physics.SyncTransforms();
};

sb.Append("хостов поз: " + hosts.Count + "\n");
Cozy.Grid.InteractiveObject pulled = null;
UnityEngine.Vector3 pulledHome = UnityEngine.Vector3.zero;
try
{
    foreach (var h in hosts)
    {
        foreach (var f in h.Features)
        {
            string k = kind(f);
            if (k == "") continue;
            sb.Append("\n== " + key(h) + " [" + k + "]\n");
            toStart();
            sb.Append("  свободно: кнопки=" + btns(f) + " бейджи=" + badges(h) + "\n");
            var hostPos0 = h.transform.position;
            if (k == "sit")
            {
                sb.Append("  геометрия: задвинут=" + Cozy.Grid.SitFeature.PushedIn(h) + " " + Cozy.Grid.SitFeature.Explain(h) + "\n");
                if (Cozy.Grid.SitFeature.PushedIn(h))
                {
                    var away = awayFromTable(h);
                    if (away != UnityEngine.Vector3.zero)
                    {
                        h.transform.position = hostPos0 + away * 0.6f;
                        UnityEngine.Physics.SyncTransforms();
                        pulled = h; pulledHome = hostPos0;
                        sb.Append("  выдвинут на 0.6: задвинут=" + Cozy.Grid.SitFeature.PushedIn(h)
                            + " кнопки=" + btns(f) + "\n");
                    }
                }
            }
            var acc = Cozy.Grid.FeatureHost.Get<Cozy.Grid.AccessFeature>(h);
            bool accOpen0 = acc != null && acc.Open;
            bool entered = false;
            foreach (var b in f.Buttons(hud)) { if (b.Enabled) { b.OnClick(); entered = true; } break; }
            if (!entered) { sb.Append("  войти нельзя\n"); continue; }
            UnityEngine.Physics.SyncTransforms();
            sb.Append("  вошёл: " + gstate() + "\n");
            sb.Append("  вошёл: кнопки=" + btns(f) + " бейджи=" + badges(h) + "\n");
            if (k == "sit")
            {
                var front = player.transform.position + player.transform.forward * 0.6f + UnityEngine.Vector3.up * 0.9f;
                var side = player.transform.position + player.transform.right * 1.5f + UnityEngine.Vector3.up * 0.9f;
                var box = new UnityEngine.Vector3(0.2f, 0.2f, 0.2f);
                sb.Append("  зона рук: перед=" + Cozy.Grid.SitFeature.BlocksPlacement(new UnityEngine.Bounds(front, box))
                    + " сбоку=" + Cozy.Grid.SitFeature.BlocksPlacement(new UnityEngine.Bounds(side, box)) + "\n");
            }
            int shown = 0;
            foreach (var o in hosts)
            {
                if (ReferenceEquals(o, h)) continue;
                foreach (var g in o.Features)
                {
                    string k2 = kind(g);
                    if (k2 == "") continue;
                    sb.Append("  чужой " + key(o) + " [" + k2 + "]: " + btns(g) + "\n");
                    shown++;
                }
                if (shown >= 8) break;
            }
            bool left = false;
            foreach (var b in f.Buttons(hud)) { if (b.Enabled) { b.OnClick(); left = true; } break; }
            UnityEngine.Physics.SyncTransforms();
            sb.Append("  вышел(" + left + "): " + gstate() + "\n");
            sb.Append("  вышел: кнопки=" + btns(f) + " бейджи=" + badges(h) + "\n");
            if (acc != null && acc.Open != accOpen0) acc.SetOpen(accOpen0);
            if (pulled != null) { pulled.transform.position = hostPos0; UnityEngine.Physics.SyncTransforms(); pulled = null; }
        }
    }
}
finally
{
    if (pulled != null) { pulled.transform.position = pulledHome; UnityEngine.Physics.SyncTransforms(); }
    foreach (var h in hosts)
        foreach (var f in h.Features)
        {
            string k = kind(f);
            if (k == "") continue;
            bool active = (k == "hide" && ReferenceEquals(Cozy.Grid.HideFeature.Spot, h))
                || (k == "sit" && ReferenceEquals(Cozy.Grid.SitFeature.Seat, h))
                || (k == "sleep" && ReferenceEquals(Cozy.Grid.SleepFeature.Bed, h));
            if (!active) continue;
            foreach (var b in f.Buttons(hud)) { if (b.Enabled) b.OnClick(); break; }
        }
    toStart();
}
sb.Append("\nитог: " + gstate() + "\n");
return sb.ToString();
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code',
                          json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True, timeout=300)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ''
    try:
        data = json.loads(line)
    except Exception:
        print('КРАСНОЕ: мост не ответил\n' + (out.stdout or out.stderr)[-500:])
        sys.exit(1)
    res = (data.get('data') or {}).get('result')
    if not res:
        print('КРАСНОЕ: ' + json.dumps(data, ensure_ascii=False)[:500])
        sys.exit(1)
    print(res)


if __name__ == '__main__':
    main()
