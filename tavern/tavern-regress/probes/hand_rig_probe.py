"""Риг рук — характеризующий замер (ночь 17→18.09): предмет в каждой руке на модели и подъём фонаря.

python3 hand_rig_probe.py    только в СВОЁМ play, на любом уровне.

Свои вещи из клеток рук вынимаются (ссылки — в AppDomain) и возвращаются в конце.
Позы меряются В ОСЯХ КИСТИ, поэтому дыхание стойки и место игрока на числа не влияют:
  hang   фонарь в левой руке опущен, палка в правой — где модель относительно кости кисти и куда смотрит ось
  raiseL фонарь поднят левой (цифра 1) — модель в кисти, кончики пальцев
  raiseR фонарь поднят правой (цифра 2) — то же, зеркально
  knife  нож в левой руке — рукоять в кулаке, лезвие вперёд
Сверка ДО/ПОСЛЕ — посимвольно; правая и левая обязаны быть зеркальны по X.
"""
import json, subprocess, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'


def run(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                         capture_output=True, text=True, timeout=120)
    # ⚠️ «не в play» — НЕ результат: два таких прогона совпадают между собой и
    # выглядят как доказательство (поймано 18.09 на самом себе).
    try:
        d = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return 'нет ответа: ' + out.stdout[-300:]
    if not d.get('success'):
        return 'ОШИБКА: ' + json.dumps(d.get('data') or d, ensure_ascii=False)[:600]
    return (d.get('data') or {}).get('result')


HEAD = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var player = Cozy.Grid.PlayerRef.GameObject;
var eq = player != null ? player.GetComponent<Cozy.Character.Equipment>() : null;
var rig = player != null ? player.GetComponent<Cozy.Character.FlashlightRig>() : null;
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var anim = player != null ? player.GetComponentInChildren<UnityEngine.Animator>() : null;
if (eq == null || rig == null || hud == null || anim == null) return "нет игрока, рига или HUD";
var hands = eq.Pockets;
'''

SAVE = HEAD + r'''
if (System.AppDomain.CurrentDomain.GetData("probe.rig.saved") != null) return "прошлый прогон не убран";
var saved = new System.Collections.Generic.List<object[]>();
foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(hands.Items)) { saved.Add(new object[] { it, it.anchor, it.rotation }); hands.Remove(it); }
System.AppDomain.CurrentDomain.SetData("probe.rig.saved", saved);
typeof(Tavern.UI.HudUI).GetMethod("SetQuickActive", bf).Invoke(hud, new object[] { -1 });
return "руки освобождены";
'''

PLACE = HEAD + r'''
foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(hands.Items)) hands.Remove(it);
bool ok = true;
%ITEMS%
typeof(Tavern.UI.HudUI).GetMethod("SetQuickActive", bf).Invoke(hud, new object[] { %ACTIVE% });
return "положено=" + ok;
'''

MEASURE = HEAD + r'''
var sb = new System.Text.StringBuilder();
sb.Append("%NAME%: поднят=" + rig.Held + (rig.Held ? " рука=" + rig.HeldSide : ""));
var torch = player.transform.Find("Flashlight");
foreach (string side in new[] { "Left", "Right" })
{
    bool left = side == "Left";
    var hand = anim.GetBoneTransform(left ? UnityEngine.HumanBodyBones.LeftHand : UnityEngine.HumanBodyBones.RightHand);
    sb.Append(" | " + (left ? "Л" : "П") + ":");
    if (rig.Held && rig.HeldSide.ToString() == side && torch != null && torch.gameObject.activeSelf)
        sb.Append(" фонарь " + hand.InverseTransformPoint(torch.position).ToString("F3") + " ось " + hand.InverseTransformDirection(torch.forward).ToString("F2"));
    var shown = rig.ShownInHand(left ? Cozy.Character.FlashlightRig.Side.Left : Cozy.Character.FlashlightRig.Side.Right);
    if (shown != null && shown != torch && shown.gameObject.activeSelf)
        sb.Append(" " + rig.HandItem(left ? Cozy.Character.FlashlightRig.Side.Left : Cozy.Character.FlashlightRig.Side.Right)
            + " " + hand.InverseTransformPoint(shown.position).ToString("F3") + " ось " + hand.InverseTransformDirection(shown.forward).ToString("F2"));
    bool busy = (rig.Held && rig.HeldSide.ToString() == side) || (shown != null && shown.gameObject.activeSelf);
    if (!busy) { sb.Append(" свободна"); continue; }
    var tips = left
        ? new[] { UnityEngine.HumanBodyBones.LeftIndexDistal, UnityEngine.HumanBodyBones.LeftLittleDistal, UnityEngine.HumanBodyBones.LeftThumbDistal }
        : new[] { UnityEngine.HumanBodyBones.RightIndexDistal, UnityEngine.HumanBodyBones.RightLittleDistal, UnityEngine.HumanBodyBones.RightThumbDistal };
    foreach (var b in tips) sb.Append(" " + hand.InverseTransformPoint(anim.GetBoneTransform(b).position).ToString("F3"));
}
return sb.ToString();
'''

# Переход «опущена → поднята» снимается НЕ по времени, а по весу подъёма: вес
# ставится в поле рига, вызывается LateUpdate и меряется поза. Иначе числа
# зависят от кадров и сравнивать два прогона нельзя.
RAISE_CURVE = HEAD + r'''
var side = rig.HeldSide;
bool left = side == Cozy.Character.FlashlightRig.Side.Left;
var hand = anim.GetBoneTransform(left ? UnityEngine.HumanBodyBones.LeftHand : UnityEngine.HumanBodyBones.RightHand);
var upper = anim.GetBoneTransform(left ? UnityEngine.HumanBodyBones.LeftUpperArm : UnityEngine.HumanBodyBones.RightUpperArm);
var fore = anim.GetBoneTransform(left ? UnityEngine.HumanBodyBones.LeftLowerArm : UnityEngine.HumanBodyBones.RightLowerArm);
var fRaise = typeof(Cozy.Character.FlashlightRig).GetField("_raise", bf);
var fYaw = typeof(Cozy.Character.FlashlightRig).GetField("_aimYaw", bf);
var fPitch = typeof(Cozy.Character.FlashlightRig).GetField("_aimPitch", bf);
var mLate = typeof(Cozy.Character.FlashlightRig).GetMethod("LateUpdate", bf);
if (fRaise == null || mLate == null) return "подъём: полей рига не видно";
float keep = (float)fRaise.GetValue(rig);
// Базовую позу пришпиливаем к началу текущего состояния аниматора: дыхание
// стойки иначе шевелит доворот на ±0.7° и два прогона не сходятся.
var state = anim.GetCurrentAnimatorStateInfo(0);
float keepTime = state.normalizedTime;
float keepSpeed = anim.speed;
anim.speed = 0f;
var sb = new System.Text.StringBuilder("подъём по весу:");
foreach (float w in new[] { 0f, 0.25f, 0.5f, 0.75f, 1f })
{
    // Аниматор обязан переиграть позу ПЕРЕД каждым вызовом: риг доворачивает
    // кости поверх анимационной позы, и два вызова подряд без Update(0) дают
    // накопленный поворот — числа скакали между двумя состояниями.
    // Меряем ВКЛАД РИГА, а не позу в мире: разворот каждой кости от той, что
    // дал аниматор. Иначе дыхание стойки шевелит числа между прогонами.
    // Наводка фонаря (_aimYaw/_aimPitch) сглаживается ОТ ПРОШЛОГО кадра: без
    // обнуления каждый вызов доводил её чуть дальше, и доворот плеча гулял на
    // градус между прогонами.
    fRaise.SetValue(rig, w);
    if (fYaw != null) fYaw.SetValue(rig, 0f);
    if (fPitch != null) fPitch.SetValue(rig, 0f);
    anim.Play(state.fullPathHash, 0, 0f);
    anim.Update(0f);
    var wasU = upper.rotation; var wasF = fore.rotation; var wasH = hand.rotation;
    mLate.Invoke(rig, null);
    var torch = Cozy.Grid.PlayerRef.GameObject.transform.Find("Flashlight");
    // Десятые доли градуса не печатаем: игрок с раскачкой корпуса даёт ±0.1°,
    // а нам важна ФОРМА подъёма (0 → ~9 → ~26 → ~36 → ~37), а не точность до
    // десятой.
    sb.Append("\n  вес " + w.ToString("0.00") + " | доворот рига: плечо " + UnityEngine.Mathf.Round(UnityEngine.Quaternion.Angle(wasU, upper.rotation))
        + "° предплечье " + UnityEngine.Mathf.Round(UnityEngine.Quaternion.Angle(wasF, fore.rotation))
        + "° кисть " + UnityEngine.Mathf.Round(UnityEngine.Quaternion.Angle(wasH, hand.rotation)) + "°");
    if (torch != null && torch.gameObject.activeSelf)
        sb.Append(" | фонарь в кисти " + hand.InverseTransformPoint(torch.position).ToString("F3") + " ось " + hand.InverseTransformDirection(torch.forward).ToString("F2"));
    sb.Append(" | светит=" + rig.Lit);
}
fRaise.SetValue(rig, keep);
anim.Play(state.fullPathHash, 0, keepTime);
anim.speed = keepSpeed;
anim.Update(0f);
mLate.Invoke(rig, null);
return sb.ToString();
'''

RESTORE = HEAD + r'''
var saved = System.AppDomain.CurrentDomain.GetData("probe.rig.saved") as System.Collections.Generic.List<object[]>;
if (saved == null) return "нечего возвращать";
typeof(Tavern.UI.HudUI).GetMethod("SetQuickActive", bf).Invoke(hud, new object[] { -1 });
foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(hands.Items)) hands.Remove(it);
int back = 0;
foreach (var row in saved) if (hands.TryPlace((Cozy.Grid.PlacedItem)row[0], (UnityEngine.Vector2Int)row[1], (int)row[2])) back++;
System.AppDomain.CurrentDomain.SetData("probe.rig.saved", null);
return "свои вещи возвращены: " + (back == saved.Count ? "все" : back + " из " + saved.Count);
'''


def item(name, cell):
    return 'ok &= hands.TryPlace(Cozy.Grid.Items.%s, new UnityEngine.Vector2Int(%d, 0), 0);\n' % (name, cell)


CASES = [
    ('hang', item('Flashlight', 0) + item('Stick', 1), -1),
    ('raiseL', item('Flashlight', 0) + item('Stick', 1), 0),
    ('raiseR', item('Stick', 0) + item('Flashlight', 1), 1),
    ('knife', item('KitchenKnife', 0), -1),
]


def main():
    first = run(SAVE)
    print(first)
    if isinstance(first, str) and 'не в play' in first:
        raise SystemExit('редактор не в play — замер не снят')
    try:
        for name, items, active in CASES:
            placed = run(PLACE.replace('%ITEMS%', items).replace('%ACTIVE%', str(active)))
            if placed != 'положено=True':
                print(name + ': ' + str(placed))
                continue
            time.sleep(2.5)
            print(run(MEASURE.replace('%NAME%', name)))
            if name.startswith('raise'):
                print(run(RAISE_CURVE))
    finally:
        print(run(RESTORE))


if __name__ == '__main__':
    main()
