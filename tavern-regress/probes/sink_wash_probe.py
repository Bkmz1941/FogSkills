"""Мойка губкой: порог воды и что именно снимает губка (решения 2026-09-03).

Спавнит сковороду и тарелку, кладёт их в горку мойки уровня, тарелку пачкает,
сковороду смазывает (кружка сверх этих двух в чашу уже не влезает: место
меряется пятнами). Проверяет порог готовности: пустая чаша и порог
минус 0.1 л не готовы, ровно порог воды готов, масло в чаше любым объёмом не
годится. Затем WashAll одним вызовом моет ВСЮ горку, включая смазку сковороды,
и отдельно проверяется пара Soiling.NeedsSponge/Wipe вне мойки. Вода мойки и
спавненная посуда возвращаются как были.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
Cozy.Grid.InteractiveObject sink = null;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
    if (io.Def != null && io.Def.pile != null && io.Def.pile.Count > 0) sink = io;
if (sink == null) return "КРАСНОЕ: мойки нет в уровне";
var pile = Cozy.Grid.SinkPile.On(sink);
if (pile == null || sink.Liquid == null) return "КРАСНОЕ: у мойки нет горки или объёма";
var vol = sink.Liquid;
string kind0 = vol.Kind; float l0 = vol.Litres;
var bad = new System.Text.StringBuilder();
var plateDef = Cozy.Grid.FurnitureCatalog.ById("plate");
var panDef = Cozy.Grid.FurnitureCatalog.ById("frying_pan");
if (plateDef == null || panDef == null) return "КРАСНОЕ: нет дефов посуды";
var far = new UnityEngine.Vector3(-70f, 0f, -80f);
var plate = gc.SpawnWorldObject(plateDef, far, 0f);
var pan = gc.SpawnWorldObject(panDef, far + new UnityEngine.Vector3(1.5f, 0f, 0f), 0f);
var loose = gc.SpawnWorldObject(panDef, far + new UnityEngine.Vector3(3f, 0f, 0f), 0f);
try
{
    if (plate == null || pan == null || loose == null) return "КРАСНОЕ: посуда не заспавнилась";
    foreach (var io in new[] { pan, plate })
    {
        UnityEngine.Vector3 p; UnityEngine.Quaternion r;
        if (!pile.NextPose(io, out p, out r)) { bad.Append("нет позы в горке для " + io.Def.id + "; "); continue; }
        io.transform.SetPositionAndRotation(p, r);
        UnityEngine.Physics.SyncTransforms();
        if (io == pan) continue;
        var soil = Cozy.Grid.Soiling.On(io);
        if (soil == null) bad.Append("посуда не пачкается: " + io.Def.id + "; "); else soil.Set(1f);
    }
    UnityEngine.Physics.SyncTransforms();
    var film = Cozy.Grid.Greased.On(pan);
    if (film == null) bad.Append("сковорода не смазывается; ");
    else { film.Set(true); if (!film.Has) bad.Append("смазка не легла на сковороду; "); }
    if (!pile.Holds(plate) || !pile.Holds(pan)) bad.Append("посуда не попала в горку; ");
    if (!pile.HasUnwashed()) bad.Append("грязь не видна горке; ");

    var looseFilm = Cozy.Grid.Greased.On(loose);
    if (looseFilm != null)
    {
        looseFilm.Set(true);
        if (!Cozy.Grid.Soiling.NeedsSponge(loose)) bad.Append("смазанная сковорода вне мойки не зовёт губку; ");
        Cozy.Grid.Soiling.Wipe(loose);
        if (looseFilm.Has) bad.Append("губка не сняла масло вне мойки; ");
    }
    vol.Set("", 0f);
    if (pile.WaterReady) bad.Append("пустая чаша считается готовой; ");
    vol.Set(Cozy.Grid.LiquidVolume.Water, Cozy.Grid.SinkPile.WashLitres - 0.1f);
    if (pile.WaterReady) bad.Append("воды меньше порога, а чаша готова; ");
    vol.Set(Cozy.Grid.LiquidVolume.Water, Cozy.Grid.SinkPile.WashLitres);
    if (!pile.WaterReady) bad.Append("ровно порог воды не считается готовым; ");
    vol.Set(Cozy.Grid.LiquidVolume.Oil, 3f);
    if (pile.WaterReady) bad.Append("масло считается водой; ");
    vol.Set(Cozy.Grid.LiquidVolume.Water, Cozy.Grid.SinkPile.WashLitres);
    int washed = pile.WashAll();
    if (washed != 2) bad.Append("вымыто " + washed + " предметов вместо 2; ");
    if (pile.HasUnwashed()) bad.Append("после мойки осталась грязь; ");
    if (film != null && film.Has) bad.Append("смазка сковороды пережила мойку; ");
    return bad.Length == 0
        ? "мойка: порог " + Cozy.Grid.SinkPile.WashLitres + " л воды, масло в чаше не годится, губка снимает грязь и смазку разом :: держится"
        : "КРАСНОЕ: " + bad.ToString();
}
finally
{
    if (plate != null) UnityEngine.Object.DestroyImmediate(plate.gameObject);
    if (pan != null) UnityEngine.Object.DestroyImmediate(pan.gameObject);
    if (loose != null) UnityEngine.Object.DestroyImmediate(loose.gameObject);
    vol.Set(kind0, l0);
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
