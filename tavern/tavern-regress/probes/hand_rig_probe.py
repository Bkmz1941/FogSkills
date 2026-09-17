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
    print(run(SAVE))
    try:
        for name, items, active in CASES:
            placed = run(PLACE.replace('%ITEMS%', items).replace('%ACTIVE%', str(active)))
            if placed != 'положено=True':
                print(name + ': ' + str(placed))
                continue
            time.sleep(2.5)
            print(run(MEASURE.replace('%NAME%', name)))
    finally:
        print(run(RESTORE))


if __name__ == '__main__':
    main()
