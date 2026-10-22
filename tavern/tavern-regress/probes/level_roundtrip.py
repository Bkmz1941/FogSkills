"""Сохранить уровень, загрузить его обратно и сверить мир до и после.

Шаг «инвентарь» (2026-09-10, инвариант 111): подобранное обязано пережить не
загрузку уровня, а ВЫХОД ИЗ ИГРЫ — инвентарь игрока живёт на игроке и загрузку
переживает сам, поэтому проверяем именно круг «сохранить → вычистить карманы →
поднять из сейва».

Ловит потери и расхождения, которых не видно глазами: пропавшие вложенные
предметы, сброшенные тумблеры, забытые уровни жидкости. Запускать в play.
Нашло 2026-09-01: из 42 объектов доезжало 36-37 (Destroy отложен, привязка
находила приговорённого хозяина).

Руки героя (2026-10-22, ilya-de): до шага «инвентарь» карманы, надетое и их
содержимое снимаются `LevelIO.CollectPlayer()` в файл, а в конце возвращаются
`RestorePlayer` — раньше проба оставляла в руке СВОЙ фонарь, и после каждого
`check_all` у героя прибавлялся фонарь (потом он уезжал в мир через
`transfer_probe`, и `cycle.py stop` отказывал по P843 — «утечка фонарика»).

Выключатели (2026-09-28, P631, инвариант 286): у каждого сверяются ПОЗИЦИИ
ламп, на которые он указывает. Имена целей `деф#N` до и после круга совпадали
и при баге — путались лампы за этими именами.
"""
import json, subprocess, collections, sys

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

SNAPSHOT = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var s = new System.Text.StringBuilder();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null) continue;
    s.Append(io.Def.id)
     .Append('|').Append(io.transform.position.ToString("0.0"))
     .Append('|').Append(io.Liquid != null ? io.Liquid.Kind + ":" + io.Liquid.Litres.ToString("0.##") : "-")
     .Append('|').Append(io.HasCount ? io.Count.ToString() : "-")
     .Append('|').Append(io.ProductState ?? "-");
    var ws = Cozy.Grid.FeatureHost.Get<Cozy.Grid.WallSwitchFeature>(io);
    if (ws != null)
    {
        var lamps = new System.Collections.Generic.List<string>();
        foreach (var lamp in Cozy.Grid.InteractiveObject.All)
            if (lamp != null && lamp.Def != null && ws.Controls(lamp.SystemName)) lamps.Add(lamp.transform.position.ToString("0.0"));
        lamps.Sort(string.CompareOrdinal);
        s.Append("|лампы:").Append(ws.On ? "вкл " : "выкл ").Append(string.Join(",", lamps.ToArray()));
    }
    s.Append(';');
}
return s.ToString();
'''

RELOAD = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var cursor = Cozy.Grid.GridCursor.I;
var keepName = Cozy.Grid.LevelIO.CurrentLevelName;
var keepSlug = Cozy.Grid.LevelIO.CurrentSlug;
const string scratch = "_roundtrip";
Cozy.Grid.LevelIO.Save(scratch);
var data = Cozy.Grid.LevelIO.Load(scratch, false);
if (data == null) return "сейв не читается";
cursor.RestoreLevel(data);
Cozy.Grid.LevelIO.CurrentLevelName = keepName;
Cozy.Grid.LevelIO.CurrentSlug = keepSlug;
Cozy.Grid.LevelIO.Delete(scratch);
return "объектов в файле=" + data.objects.Count + " уровень=" + Cozy.Grid.LevelIO.CurrentLevelName;
'''


def call(code):
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    return json.loads(line).get("data", {}).get("result") or ""


def parse(dump):
    return collections.Counter(x for x in dump.split(';') if x)


before = parse(call(SNAPSHOT))
print("до:", sum(before.values()), "объектов")
print(call(RELOAD))
import time
time.sleep(4)
after = parse(call(SNAPSHOT))
print("после:", sum(after.values()), "объектов")
lost, gained = before - after, after - before
if not lost and not gained:
    print("СОВПАЛО полностью")
else:
    for k in list(lost)[:12]: print("  потеряно:", k)
    for k in list(gained)[:12]: print("  появилось:", k)

CELLS_FILL = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var eq = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.Equipment>();
if (eq == null) return "нет Equipment";
var keepPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "_roundtrip_keep.json");
System.IO.File.WriteAllText(keepPath, UnityEngine.JsonUtility.ToJson(Cozy.Grid.LevelIO.CollectPlayer()));
foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(eq.Pockets.Items)) eq.Pockets.Remove(it);
eq.Pockets.TryAdd(Cozy.Grid.Items.Flashlight);
eq.Pockets.TryAdd(Cozy.Grid.Items.Batteries);
Cozy.Grid.PlacedItem flash = null, loose = null;
foreach (var it in eq.Pockets.Items)
{
    if (it.def == Cozy.Grid.Items.Flashlight) flash = it;
    if (it.def == Cozy.Grid.Items.Batteries) loose = it;
}
if (flash == null || loose == null) return "не легло в карманы";
loose.charge = 77f;
var slots = Cozy.Grid.PowerCells.SlotsOf(flash);
if (slots == null || !slots.TryAdd(new Cozy.Grid.PlacedItem { def = Cozy.Grid.Items.Batteries, charge = 42f })) return "гнездо не приняло батарейку";
return "положено: фонарь(гнездо 42%) + батарейки(77%)";
'''

CELLS_ROUND = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var keepName = Cozy.Grid.LevelIO.CurrentLevelName;
var keepSlug = Cozy.Grid.LevelIO.CurrentSlug;
Cozy.Grid.LevelIO.Save("_roundtrip_cells");
Cozy.Grid.LevelIO.CurrentLevelName = keepName;
Cozy.Grid.LevelIO.CurrentSlug = keepSlug;
var eq = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.Equipment>();
foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(eq.Pockets.Items)) eq.Pockets.Remove(it);
Cozy.Grid.LevelIO.PlayerSnapshot = null;
var data = Cozy.Grid.LevelIO.Load("_roundtrip_cells", false);
Cozy.Grid.LevelIO.Delete("_roundtrip_cells");
if (data == null) return "сейв не читается";
if (data.player == null || !data.player.saved) return "в сейве НЕТ инвентаря игрока";
Cozy.Grid.LevelIO.RestorePlayer(data.player);
var s = new System.Text.StringBuilder();
foreach (var it in eq.Pockets.Items)
{
    s.Append(it.def.id).Append('=').Append(it.charge.ToString("0"));
    if (it.contents != null) foreach (var c in it.contents.Items) s.Append("[").Append(c.def.id).Append('=').Append(c.charge.ToString("0")).Append("]");
    s.Append(' ');
}
foreach (var it in new System.Collections.Generic.List<Cozy.Grid.PlacedItem>(eq.Pockets.Items)) eq.Pockets.Remove(it);
var keepPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "_roundtrip_keep.json");
var keepJson = System.IO.File.Exists(keepPath) ? System.IO.File.ReadAllText(keepPath) : "";
if (keepJson.Length == 0) return s.ToString().Trim() + " | ГЕРОЙ НЕ ВОЗВРАЩЁН: нет снимка карманов";
var keep = UnityEngine.JsonUtility.FromJson<Cozy.Grid.LevelIO.PlayerData>(keepJson);
System.IO.File.WriteAllText(keepPath, "");
Cozy.Grid.LevelIO.RestorePlayer(keep);
return s.ToString().Trim();
'''

print(call(CELLS_FILL))
got = call(CELLS_ROUND)
print("инвентарь после круга:", got)
print("ИНВЕНТАРЬ ЦЕЛ" if "flashlight=100[batteries=42]" in str(got) and "batteries=77" in str(got)
      else "ИНВЕНТАРЬ ПОТЕРЯН — инвариант 111")
