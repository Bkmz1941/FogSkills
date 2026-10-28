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

Стадия «тело на хозяине» (инвариант 225, P532): для каждого хоста «Сесть»/
«Лечь» вход ОДНИМ вызовом, замер СЛЕДУЮЩИМ — поза клипа ложится на кости только
после кадра аниматора, в кадре входа таз ещё стоит по-старому. Таз гуманоида
обязан быть внутри `WorldBounds` хозяина по XZ (запас 0.15) и не выше его верха
+ 0.6; иначе «КРАСНОЕ: тело вне хозяина» — так ловится клип, собранный не от
того начала или не тем лицом (диван: тело левитировало перед сиденьем).
Игрок возвращается на место последним вызовом.

Стадия «место вставания» (инвариант 238, P549): после «Встать» капсула игрока
не пересекает ни одного твёрдого коллайдера (стены, мебели), а у хозяина со
СВОИМ клипом (`sitClip`, диван у стены) игрок стоит ПЕРЕД фронтом, а не за
спинкой, как со стула; иначе «КРАСНОЕ: игрок стоит внутри коллайдера …» /
«встал не перед фронтом».

Там же, в стадии «тело на хозяине»: в позе руки ПУСТЫ — ни одного включённого
MeshRenderer под игроком (предмет из хотбара и модель фонаря риг прячет, пока
`PlayerPosture.Current != null`, инвариант 239); иначе «КРАСНОЕ: в позе виден
предмет в руке».
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
System.Func<string> insideSolid = () =>
{
    if (cc == null) return "";
    float half = UnityEngine.Mathf.Max(0f, cc.height * 0.5f - cc.radius);
    var c = player.transform.position + cc.center + UnityEngine.Vector3.up * 0.03f;
    foreach (var col in UnityEngine.Physics.OverlapCapsule(c - UnityEngine.Vector3.up * half, c + UnityEngine.Vector3.up * half, cc.radius, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
    {
        if (col.transform.IsChildOf(player.transform)) continue;
        return col.name + (col.transform.parent != null ? "/" + col.transform.parent.name : "");
    }
    return "";
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
            if (k == "sit")
            {
                string solid = insideSolid();
                bool ownClip = !string.IsNullOrEmpty(h.Def.sitClip);
                bool inFront = UnityEngine.Vector3.Dot(player.transform.position - h.transform.position, -h.transform.forward) > 0f;
                sb.Append("  место: " + (solid == "" ? "свободно" : "внутри " + solid) + (ownClip ? (inFront ? ", перед фронтом" : ", НЕ перед фронтом") : "") + "\n");
                if (solid != "") bad.Add("после выхода из " + key(h) + " игрок стоит внутри коллайдера " + solid);
                var pathFrom = h.transform.position + UnityEngine.Vector3.up * 1f;
                var pathTo = player.transform.position - UnityEngine.Vector3.up * (cc != null ? (cc.height * 0.5f - cc.center.y) : 0f) + UnityEngine.Vector3.up * 1f;
                foreach (var ph in UnityEngine.Physics.RaycastAll(pathFrom, (pathTo - pathFrom).normalized, (pathTo - pathFrom).magnitude, ~0, UnityEngine.QueryTriggerInteraction.Ignore))
                {
                    if (ph.collider.transform.IsChildOf(h.transform) || ph.collider.transform.IsChildOf(player.transform)) continue;
                    bad.Add("после выхода из " + key(h) + " игрок встал за преградой " + ph.collider.name + (ph.collider.transform.parent != null ? "/" + ph.collider.transform.parent.name : "") + " (сквозь стену)");
                    break;
                }
                bool leavesForward = ownClip || (Cozy.Grid.FeatureHost.Get<Cozy.Grid.SitFeature>(h) != null && h.Def != null && !h.Def.chair);
                if (leavesForward && !inFront) bad.Add("после выхода из " + key(h) + " игрок встал не перед фронтом (свой клип или не стул — P921)");
            }
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


BODY_LIST = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io == null || io.Def == null) continue;
    foreach (var f in io.Features)
    {
        string k = f is Cozy.Grid.SitFeature ? "sit" : (f is Cozy.Grid.SleepFeature ? "sleep" : "");
        if (k == "") continue;
        sb.Append(io.Def.id + "@" + io.transform.position.ToString("0.00") + "|" + k + "\n");
    }
}
return sb.Length == 0 ? "хостов нет" : sb.ToString();
'''

BODY_POS = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var player = Cozy.Grid.PlayerRef.GameObject;
if (player == null) return "КРАСНОЕ: нет игрока";
var inv = System.Globalization.CultureInfo.InvariantCulture;
var p = player.transform.position;
return p.x.ToString("R", inv) + "," + p.y.ToString("R", inv) + "," + p.z.ToString("R", inv) + "|" + player.transform.eulerAngles.y.ToString("R", inv);
'''

BODY_ENTER = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "КРАСНОЕ: нет HudUI";
if (Cozy.Grid.PlayerPosture.Current != null) Cozy.Grid.PlayerPosture.Current.Leave();
Cozy.Grid.InteractiveObject host = null;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
    if (io != null && io.Def != null && io.Def.id == "{ID}" && io.transform.position.ToString("0.00") == "{POS}") { host = io; break; }
if (host == null) return "хост не найден";
Cozy.Grid.ObjectFeature f = "{KIND}" == "sit"
    ? (Cozy.Grid.ObjectFeature)Cozy.Grid.FeatureHost.Get<Cozy.Grid.SitFeature>(host)
    : Cozy.Grid.FeatureHost.Get<Cozy.Grid.SleepFeature>(host);
if (f == null) return "фичи нет";
bool entered = false;
foreach (var b in f.Buttons(hud)) { if (b.Enabled) { b.OnClick(); entered = true; } break; }
return entered ? "вошёл" : "войти нельзя";
'''

BODY_CHECK = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var player = Cozy.Grid.PlayerRef.GameObject;
var pc = Cozy.Grid.PlayerPosture.Current;
if (player == null || pc == null) return "КРАСНОЕ: поза не удержалась до следующего кадра";
var host = Cozy.Grid.SitFeature.Seat != null ? Cozy.Grid.SitFeature.Seat : Cozy.Grid.SleepFeature.Bed;
var anim = player.GetComponentInChildren<UnityEngine.Animator>();
var hips = anim != null && anim.isHuman ? anim.GetBoneTransform(UnityEngine.HumanBodyBones.Hips) : null;
string res;
if (hips == null || host == null) res = "таза или хозяина нет";
else
{
    var hb = host.WorldBounds;
    var p = hips.position;
    bool inXZ = p.x >= hb.min.x - 0.15f && p.x <= hb.max.x + 0.15f && p.z >= hb.min.z - 0.15f && p.z <= hb.max.z + 0.15f;
    bool inY = p.y >= hb.min.y && p.y <= hb.max.y + 0.6f;
    res = "тело: таз=" + p.ToString("0.00") + " хозяин=" + hb.min.ToString("0.00") + ".." + hb.max.ToString("0.00")
        + " клип=" + (Cozy.Grid.PlayerPosture.Clip ?? "-")
        + (inXZ && inY ? " :: на хозяине" : " :: КРАСНОЕ: тело вне хозяина");
}
int props = 0;
foreach (var r in player.GetComponentsInChildren<UnityEngine.MeshRenderer>())
    if (r.enabled && r.gameObject.activeInHierarchy && r.transform != player.transform) props++;
res += props == 0 ? "; руки пусты" : " :: КРАСНОЕ: в позе виден предмет в руке (" + props + ")";
pc.Leave();
return res;
'''

BODY_RESTORE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
if (Cozy.Grid.PlayerPosture.Current != null) Cozy.Grid.PlayerPosture.Current.Leave();
var player = Cozy.Grid.PlayerRef.GameObject;
if (player == null) return "КРАСНОЕ: нет игрока";
var inv = System.Globalization.CultureInfo.InvariantCulture;
var parts = "{HOME}".Split('|');
var xyz = parts[0].Split(',');
var pos = new UnityEngine.Vector3(float.Parse(xyz[0], inv), float.Parse(xyz[1], inv), float.Parse(xyz[2], inv));
var rot = UnityEngine.Quaternion.Euler(0f, float.Parse(parts[1], inv), 0f);
var cc = player.GetComponent<UnityEngine.CharacterController>();
bool on = cc != null && cc.enabled;
if (cc != null) cc.enabled = false;
player.transform.SetPositionAndRotation(pos, rot);
if (cc != null) cc.enabled = on;
UnityEngine.Physics.SyncTransforms();
return "игрок на месте";
'''


def body_stage():
    hosts, err = call(BODY_LIST)
    if err:
        return 'КРАСНОЕ (тело, список): ' + err, True
    if 'не в play' in hosts:
        return hosts, False
    if 'хостов нет' in hosts:
        return 'тело на хозяине: хостов поз нет', False
    home, err = call(BODY_POS)
    if err:
        return 'КРАСНОЕ (тело, позиция): ' + err, True
    lines, red = [], False
    try:
        for row in hosts.strip().splitlines():
            key, kind = row.rsplit('|', 1)
            ident, pos = key.split('@', 1)
            code = BODY_ENTER.replace('{ID}', ident).replace('{POS}', pos).replace('{KIND}', kind)
            ent, err = call(code)
            if err:
                lines.append('КРАСНОЕ (тело, вход %s): %s' % (key, err)); red = True; continue
            if ent != 'вошёл':
                lines.append('  %s [%s]: %s' % (key, kind, ent)); continue
            time.sleep(0.5)
            chk, err = call(BODY_CHECK)
            if err:
                lines.append('КРАСНОЕ (тело, замер %s): %s' % (key, err)); red = True; continue
            lines.append('  %s [%s]: %s' % (key, kind, chk))
            red = red or 'КРАСНОЕ' in chk
    finally:
        call(BODY_RESTORE.replace('{HOME}', home))
    return 'тело на хозяине:\n' + '\n'.join(lines), red


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
    body, body_red = body_stage()
    print('\n' + body)
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
        print(':: позы %s; тело %s; осмотр не прогнан — на этом уровне нет кровати'
              % ('КРАСНОЕ' if 'КРАСНОЕ' in res else 'ок', 'КРАСНОЕ' if body_red else 'ок'))
        sys.exit(1 if ('КРАСНОЕ' in res or body_red) else 0)
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
    red = 'КРАСНОЕ' in res or 'КРАСНОЕ' in check or body_red
    print(':: позы %s; тело %s; осмотр %s' % (
        'КРАСНОЕ' if 'КРАСНОЕ' in res else 'ок',
        'КРАСНОЕ' if body_red else 'ок',
        'КРАСНОЕ' if 'КРАСНОЕ' in check else 'ок'))
    if red:
        sys.exit(1)


if __name__ == '__main__':
    main()
