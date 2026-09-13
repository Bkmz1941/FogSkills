"""Характеризующий замер ПОЗ игрока: «Спрятаться», «Сесть», «Лечь».

Прогоняет по каждому объекту с позой (hideable / chair / bed) полный цикл
«свободно → вошёл → чужие кнопки → вышел» и печатает НАБЛЮДАЕМОЕ поведение:
подписи и доступность кнопок, бейджи, флаги поз, клип, позу игрока, число
включённых рендереров (укрытие гасит фигуру). Вход и выход идут через РЕАЛЬНУЮ
кнопку карточки с HudUI в роли IFeatureContext — то есть тем же путём, что у
игрока, а не в обход.

Печатает вердикт: инвариант 73 (игрок в ОДНОЙ позе за раз — пока занят, кнопки
входа всех прочих поз недоступны) плюс чистота выхода (поза снята, контроллер
включён, бейдж занятости убран, фигура видима). Нарушение — строка «КРАСНОЕ» и
ненулевой код возврата, поэтому пробу можно звать из check_all.py.

Зачем ещё: рефакторинг трёх поз в одну базу обязан сохранить поведение. Протокол —
`README.md`: замер «ДО» в файл, правка, замер «ПОСЛЕ» в другой файл, дифф
построчно; между прогонами сцену не трогать.

    python3 posture_probe.py > /tmp/posture_before.txt
    ... правка, перекомпиляция, play ...
    python3 posture_probe.py > /tmp/posture_after.txt
    diff /tmp/posture_before.txt /tmp/posture_after.txt

Задвинутый в стол стул сесть не даёт, поэтому проба временно выдвигает его на
0.6 от стола (как `sit_probe.cs`) и возвращает на место — иначе ветка «Сесть»
не измеряется вовсе.

Отдельной парой вызовов проверяется правило осмотра: пока игрок ЗАНЯЛ
осматриваемый объект (лёг на осматриваемую кровать), фигура не прячется —
иначе «Лечь» из осмотра выглядит как «ничего не произошло». Два вызова нужны
потому, что призрак осмотра снимается в следующем кадре.

Поза игрока, позиция выдвинутого стула, состояние створок укрытия и активная
поза возвращаются в finally. Правило осмотра — инвариант 75.
"""
import json, subprocess, sys, time

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
    string clip = Cozy.Grid.PlayerPosture.Clip;
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
var bad = new System.Collections.Generic.List<string>();
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
                    string line = btns(g);
                    sb.Append("  чужой " + key(o) + " [" + k2 + "]: " + line + "\n");
                    if (line.Contains("+")) bad.Add("занят " + key(h) + ", а у " + key(o) + " [" + k2 + "] кнопка доступна: " + line);
                    shown++;
                }
                if (shown >= 8) break;
            }
            bool left = false;
            foreach (var b in f.Buttons(hud)) { if (b.Enabled) { b.OnClick(); left = true; } break; }
            UnityEngine.Physics.SyncTransforms();
            sb.Append("  вышел(" + left + "): " + gstate() + "\n");
            string afterBadges = badges(h);
            sb.Append("  вышел: кнопки=" + btns(f) + " бейджи=" + afterBadges + "\n");
            if (Cozy.Grid.HideFeature.PlayerHidden || Cozy.Grid.SitFeature.PlayerSeated || Cozy.Grid.SleepFeature.PlayerLying)
                bad.Add("после выхода из " + key(h) + " игрок всё ещё в позе");
            if (cc != null && !cc.enabled) bad.Add("после выхода из " + key(h) + " контроллер выключен");
            if (afterBadges.Contains("занят")) bad.Add("после выхода из " + key(h) + " остался бейдж занятости");
            if (vis() == 0) bad.Add("после выхода из " + key(h) + " фигура осталась невидимой");
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
foreach (var b in bad) sb.Append("   нарушение: " + b + "\n");
sb.Append(bad.Count == 0
    ? ":: инвариант 73 держится, выход из позы чист\n"
    : ":: КРАСНОЕ: нарушений " + bad.Count + ", подробности строками выше\n");
return sb.ToString();
'''


EXAMINE_SETUP = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
if (Cozy.Grid.PlayerPosture.Current != null) Cozy.Grid.PlayerPosture.Current.Leave();
Cozy.Grid.InteractiveObject bed = null;
foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.Def != null && io.Def.bed) bed = io;
if (bed == null) return "кровати в уровне нет";
var pl = Cozy.Grid.PlayerRef.GameObject;
var cc = pl.GetComponent<UnityEngine.CharacterController>();
var spot = bed.WorldBounds.center + bed.transform.right * 2.2f;
cc.enabled = false;
pl.transform.SetPositionAndRotation(new UnityEngine.Vector3(spot.x, bed.transform.position.y + 1.0f, spot.z),
    UnityEngine.Quaternion.LookRotation(-bed.transform.right, UnityEngine.Vector3.up));
cc.enabled = true;
UnityEngine.Physics.SyncTransforms();
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
typeof(Tavern.UI.HudUI).GetMethod("OpenExamine", bf).Invoke(hud, new object[] { bed as Cozy.Grid.IExaminable });
bool laid = Cozy.Grid.FeatureHost.Get<Cozy.Grid.SleepFeature>(bed).Enter();
return "осмотр открыт, лёг=" + laid;
'''

EXAMINE_CHECK = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var ep = typeof(Tavern.UI.HudUI).GetField("_examinePanel", bf).GetValue(hud) as UnityEngine.GameObject;
var labels = new System.Collections.Generic.List<string>();
if (ep != null)
    foreach (var one in ep.GetComponentsInChildren<UnityEngine.UI.Button>(true))
    {
        var tmp = one.GetComponentInChildren<TMPro.TMP_Text>(true);
        var lab = tmp != null ? tmp.text : "";
        if (!string.IsNullOrEmpty(lab) && lab != "i") labels.Add(lab);
    }
var pl = Cozy.Grid.PlayerRef.GameObject;
int vis = 0;
foreach (var r in pl.GetComponentsInChildren<UnityEngine.Renderer>()) if (r.enabled) vis++;
bool lying = Cozy.Grid.SleepFeature.PlayerLying;
bool ghost = Cozy.Character.PlayerGhost.Active;
var bad = new System.Text.StringBuilder();
if (ep == null) bad.Append("осмотр закрылся; ");
if (!lying) bad.Append("поза не удержалась в осмотре; ");
if (ghost) bad.Append("фигура спрятана призраком осмотра, хотя лежит на осматриваемой кровати; ");
if (vis == 0) bad.Append("ни одного видимого рендерера у лежащего; ");
if (labels.Count < 2) bad.Append("в карточке осмотра нет пары кнопок «встать» и «спать»; ");
if (Cozy.Grid.PlayerPosture.Current != null) Cozy.Grid.PlayerPosture.Current.Leave();
var m = typeof(Tavern.UI.HudUI).GetMethod("CloseExamine", bf);
if (m != null) m.Invoke(hud, new object[] { false });
return "осмотр: кнопки=[" + string.Join(",", labels.ToArray()) + "] лежит=" + lying
    + " призрак=" + ghost + " видимых=" + vis
    + (bad.Length == 0 ? " :: правило осмотра держится" : " :: КРАСНОЕ: " + bad.ToString());
'''


def call(code):
    out = subprocess.run(['python3', MCP, 'execute_code',
                          json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=300)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ''
    try:
        data = json.loads(line)
    except Exception:
        return None, 'мост не ответил: ' + (out.stdout or out.stderr)[-300:]
    res = (data.get('data') or {}).get('result')
    if not res:
        return None, json.dumps(data, ensure_ascii=False)[:400]
    return res, None


def main():
    res, err = call(CODE)
    if err:
        print('КРАСНОЕ: ' + err)
        sys.exit(1)
    print(res)
    setup, err = call(EXAMINE_SETUP)
    if err:
        print('КРАСНОЕ (осмотр, подготовка): ' + err)
        sys.exit(1)
    print('\n' + setup)
    # На уровне без кровати проверять нечего: правило про карточку осмотра в позе
    # требует кровати, и раньше проба честно писала «кровати в уровне нет», а
    # следом всё равно рапортовала КРАСНОЕ — на лесных уровнях это ложная
    # регрессия в каждом прогоне check_all (13.09).
    if 'кровати в уровне нет' in setup:
        print(':: позы %s; осмотр не прогнан — на этом уровне нет кровати'
              % ('КРАСНОЕ' if 'КРАСНОЕ' in res else 'ок'))
        sys.exit(1 if 'КРАСНОЕ' in res else 0)
    time.sleep(1.0)
    check, err = call(EXAMINE_CHECK)
    if err:
        print('КРАСНОЕ (осмотр, проверка): ' + err)
        sys.exit(1)
    print(check)
    # Редактор не в play — зонду нечего мерить. Раньше EXAMINE_CHECK в edit mode
    # не находил HudUI и рапортовал КРАСНОЕ: ложная регрессия ловилась каждый
    # раз, когда прогон попадал в чужое окно stop → компиляция → play.
    if 'не в play' in res or 'не в play' in setup or 'не в play' in check:
        print(':: не прогнан — редактор не в play')
        return
    red = 'КРАСНОЕ' in res or 'КРАСНОЕ' in check
    print(':: позы %s; осмотр %s' % (
        'КРАСНОЕ' if 'КРАСНОЕ' in res else 'ок',
        'КРАСНОЕ' if 'КРАСНОЕ' in check else 'ок'))
    if red:
        sys.exit(1)


if __name__ == '__main__':
    main()
