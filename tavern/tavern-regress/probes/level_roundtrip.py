"""Сохранить уровень, загрузить его обратно и сверить мир до и после.

Ловит потери и расхождения, которых не видно глазами: пропавшие вложенные
предметы, сброшенные тумблеры, забытые уровни жидкости. Запускать в play.
Нашло 2026-09-01: из 42 объектов доезжало 36-37 (Destroy отложен, привязка
находила приговорённого хозяина).
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
     .Append('|').Append(io.ProductState ?? "-")
     .Append(';');
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
