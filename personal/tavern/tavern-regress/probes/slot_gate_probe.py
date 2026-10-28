"""Гейт слота по положению предмета (инварианты 33 и 129, P157, P335).

Две проверки, обе спавнят хозяев в стороне от уровня и всё за собой убирают:
1. Широкий угловой навесной шкаф и чашка за дверцей 3: скрыта только пока закрыта дверца 3,
   соседние дверцы на неё не влияют.
2. КАЖДОЕ объявленное место раскладки находит СВОЙ слот: у любого дефа с гейтом на слоте
   пустышка, поставленная в место `cookLayouts.slots[i]`, обязана вернуть из `OwnSlot` тот
   слот, чей узел раскладка и называет. Крайние места топки камина разнесены до 0.30 м от
   узла — при мерке до точки они не находили свой слот и проходили мимо створки (P335).
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var cabDef = Cozy.Grid.FurnitureCatalog.ById("home_wall_cabinet_corner_wide");
var cupDef = Cozy.Grid.FurnitureCatalog.ById("coffee_cup_blue");
if (cabDef == null || cupDef == null) return "КРАСНОЕ: нет дефов шкафа или чашки";
var before = new System.Collections.Generic.HashSet<int>();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None)) before.Add(io.GetInstanceID());
var cab = Cozy.Grid.GridCursor.I.SpawnWorldObject(cabDef, new UnityEngine.Vector3(-60f, 1.8f, -60f), 0f);
if (cab == null) return "КРАСНОЕ: шкаф не заспавнился";
var bad = new System.Text.StringBuilder();
Cozy.Grid.InteractiveObject cup = null;
try
{
    Cozy.Grid.ContainerSlot slot = null;
    foreach (var s in cab.GetComponentsInChildren<Cozy.Grid.ContainerSlot>(true)) if (s.gameObject.name == "Slot_ShelfMain2") slot = s;
    if (slot == null) return "КРАСНОЕ: нет Slot_ShelfMain2";
    var feats = new System.Collections.Generic.List<Cozy.Grid.AccessFeature>();
    foreach (var f in cab.Features) { var a = f as Cozy.Grid.AccessFeature; if (a != null) feats.Add(a); }
    System.Action<System.Func<Cozy.Grid.AccessFeature, bool>> set = (rule) => { foreach (var a in feats) a.SetOpen(rule(a)); };
    set(a => a.Title == "Дверца 3");
    cup = Cozy.Grid.GridCursor.I.SpawnWorldObject(cupDef, slot.transform.position + UnityEngine.Vector3.up * 0.02f, 0f);
    if (cup == null) return "КРАСНОЕ: чашка не заспавнилась";
    cup.transform.SetParent(slot.carrier, true);
    cup.Container = cab;
    if (Cozy.Grid.Targeting.Hidden(cup)) bad.Append("открыта только своя дверца, а чашка скрыта; ");
    set(a => true);
    if (Cozy.Grid.Targeting.Hidden(cup)) bad.Append("все дверцы открыты, а чашка скрыта; ");
    set(a => a.Title != "Дверца 3");
    if (!Cozy.Grid.Targeting.Hidden(cup)) bad.Append("своя дверца закрыта, соседние открыты, а чашка видна; ");
    set(a => false);
    if (!Cozy.Grid.Targeting.Hidden(cup)) bad.Append("всё закрыто, а чашка видна; ");
    return bad.Length == 0 ? "широкий шкаф, чашка за дверцей 3: гейт по своей дверце :: держится" : "КРАСНОЕ: " + bad.ToString();
}
finally
{
    foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        if (!before.Contains(io.GetInstanceID())) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
'''

SLOTS_CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var before = new System.Collections.Generic.HashSet<int>();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None)) before.Add(io.GetInstanceID());
var probe = new UnityEngine.GameObject("SlotProbe").transform;
var bad = new System.Text.StringBuilder();
int hosts = 0, places = 0;
try
{
    foreach (var def in Cozy.Grid.FurnitureCatalog.All())
    {
        if (def == null || string.IsNullOrEmpty(def.slotNodes) || !def.slotNodes.Contains(":")) continue;
        bool anyLayout = false;
        foreach (var lay in def.cookLayouts) if (!string.IsNullOrEmpty(lay.slotNode)) anyLayout = true;
        if (!anyLayout) continue;
        var host = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, new UnityEngine.Vector3(-60f, 1.8f, -60f), 0f);
        if (host == null) { bad.Append(def.id + " не заспавнился; "); continue; }
        hosts++;
        var slots = new System.Collections.Generic.List<Cozy.Grid.ContainerSlot>();
        host.GetComponentsInChildren(true, slots);
        foreach (var lay in def.cookLayouts)
        {
            if (string.IsNullOrEmpty(lay.slotNode)) continue;
            Cozy.Grid.ContainerSlot mine = null;
            foreach (var s in slots) if (s.gameObject.name == lay.slotNode) mine = s;
            if (mine == null) { bad.Append(def.id + "/" + lay.slotNode + ": нет такого слота; "); continue; }
            for (int i = 0; i < lay.slots.Count; i++)
            {
                probe.position = mine.transform.position + host.transform.rotation * lay.slots[i];
                places++;
                var got = Cozy.Grid.ContainerSlot.OwnSlot(slots, probe);
                if (got != mine) bad.Append(def.id + "/" + lay.slotNode + " место " + i + " (" + lay.slots[i].ToString("F3") + ") нашло " + (got == null ? "НИЧЕГО" : got.gameObject.name) + "; ");
            }
        }
        UnityEngine.Object.DestroyImmediate(host.gameObject);
    }
    return bad.Length == 0
        ? "места раскладок находят свой слот: хозяев " + hosts + ", мест " + places + " :: держится"
        : "КРАСНОЕ (хозяев " + hosts + ", мест " + places + "): " + bad.ToString();
}
finally
{
    if (probe != null) UnityEngine.Object.DestroyImmediate(probe.gameObject);
    foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        if (!before.Contains(io.GetInstanceID())) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
'''


def run(code):
    r = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})], capture_output=True, text=True, timeout=300)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        return (d.get('data') or {}).get('result') or d.get('message')
    except Exception:
        return 'КРАСНОЕ: мост не ответил ' + r.stdout[-300:]


print(run(CODE))
print(run(SLOTS_CODE))
