"""Кухонные правила постановки и раскладки (P159, P166, P171, тарелка 03.09).

Спавнит в стороне от уровня кастрюлю и сковороду: сковорода над кастрюлей и
краем дна на её борту — запрет «на посуду» по площади дна (P183), а в стороне
от кастрюли постановка обязана остаться зелёной. Считает раскладку тарелки чистой функцией:
четыре круглых кольцом, пять брёвен в три ленты и два сверху. Поливает пустую
тарелку кетчупом: лужица внутри плоского дна. Всё спавненное удаляется.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var bad = new System.Text.StringBuilder();
var gc = Cozy.Grid.GridCursor.I;
var t = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var potDef = Cozy.Grid.FurnitureCatalog.ById("cooking_pot");
var panDef = Cozy.Grid.FurnitureCatalog.ById("frying_pan");
var plateDef = Cozy.Grid.FurnitureCatalog.ById("plate");
if (potDef == null || panDef == null || plateDef == null) return "КРАСНОЕ: нет дефов посуды";
var origin = new UnityEngine.Vector3(-60f, 0f, -70f);
var pot = gc.SpawnWorldObject(potDef, origin, 0f);
var pan = gc.SpawnWorldObject(panDef, origin + new UnityEngine.Vector3(1.5f, 0f, 0f), 0f);
var plate = gc.SpawnWorldObject(plateDef, origin + new UnityEngine.Vector3(-1.5f, 0f, 0f), 0f);
try
{
    if (pot == null || pan == null || plate == null) return "КРАСНОЕ: посуда не заспавнилась";
    UnityEngine.Physics.SyncTransforms();
    float top = pot.WorldBounds.max.y;
    var onVessel = t.GetMethod("OnVessel", bf);
    bool blocked = (bool)onVessel.Invoke(gc, new object[] { pan.gameObject, origin.x, top, origin.z, 0f, pan.transform });
    if (!blocked) bad.Append("сковорода над кастрюлей не считается «на посуде»; ");
    // Край дна на борту кастрюли: пивот ВНЕ её габарита, точечные пробы туда
    // не попадали и постановка была зелёной (P183).
    float edge = pot.WorldBounds.extents.x + 0.07f;
    bool edgeBlocked = (bool)onVessel.Invoke(gc, new object[] { pan.gameObject, origin.x - edge, top, origin.z, 0f, pan.transform });
    if (!edgeBlocked) bad.Append("сковорода краем дна на борту кастрюли не считается «на посуде»; ");
    // Рядом на столе, дно мимо кастрюли — постановка обязана остаться зелёной.
    float clear = pot.WorldBounds.extents.x + 0.6f;
    bool asideBlocked = (bool)onVessel.Invoke(gc, new object[] { pan.gameObject, origin.x - clear, top, origin.z, 0f, pan.transform });
    if (asideBlocked) bad.Append("сковорода в стороне от кастрюли зря считается «на посуде»; ");
    pan.transform.position = origin + new UnityEngine.Vector3(1.5f, 0f, 0f);

    var fried = Cozy.Grid.CookArrange.FromSize(new UnityEngine.Vector3(0.123f, 0.025f, 0.125f));
    var saus = Cozy.Grid.CookArrange.FromSize(new UnityEngine.Vector3(0.23f, 0.052f, 0.052f));
    var spots = new System.Collections.Generic.List<UnityEngine.Vector2>();
    var yaws = new System.Collections.Generic.List<float>();
    var lifts = new System.Collections.Generic.List<float>();
    Cozy.Grid.CookLayout lay = null;
    foreach (var l in plateDef.cookLayouts) if (l.arrange) { lay = l; break; }
    if (lay == null) return "КРАСНОЕ: у тарелки нет раскладки";
    bool fits;
    Cozy.Grid.CookArrange.Places(lay.floorR, new System.Collections.Generic.List<Cozy.Grid.CookArrange.Piece> { fried, fried, fried, fried }, spots, yaws, lifts, out fits, lay.maxLanes, lay.ringFrom);
    float r0 = spots[0].magnitude; bool ring = fits;
    foreach (var p in spots) if (UnityEngine.Mathf.Abs(p.magnitude - r0) > 0.002f) ring = false;
    if (!ring) bad.Append("четыре яичницы не кольцом; ");
    Cozy.Grid.CookArrange.Places(lay.floorR, new System.Collections.Generic.List<Cozy.Grid.CookArrange.Piece> { saus, saus, saus, saus, saus }, spots, yaws, lifts, out fits, lay.maxLanes, lay.ringFrom);
    int lifted = 0; foreach (var l in lifts) if (l > 0.01f) lifted++;
    if (!fits || lifted != 0) bad.Append("пять сосисок не пятью лентами без яруса (fits=" + fits + ", сверху " + lifted + "); ");
    if (lay.limit != 4 || lay.mixCap != 3) bad.Append("лимиты тарелки не 4 яичницы / смесь 3; ");

    var sauce = Cozy.Grid.Sauced.On(plate);
    if (sauce != null)
    {
        sauce.Set(true);
        UnityEngine.Transform pool = null;
        foreach (var tr in plate.GetComponentsInChildren<UnityEngine.Transform>(true)) if (tr.name == "SaucePool") pool = tr;
        if (pool == null) bad.Append("лужица кетчупа не появилась; ");
        else
        {
            var lp = plate.transform.InverseTransformPoint(pool.position);
            float r = new UnityEngine.Vector2(lp.x, lp.z).magnitude;
            float floor = UnityEngine.Mathf.Min(plate.WorldBounds.size.x, plate.WorldBounds.size.z) * 0.5f * 0.75f;
            if (r > floor) bad.Append("лужица кетчупа за плоским дном r=" + r.ToString("F3") + " > " + floor.ToString("F3") + "; ");
        }
    }
    return bad.Length == 0 ? "сковорода на кастрюлю и краем на борт красная, в стороне зелёная, тарелка кольцом и лентами, кетчуп внутри дна :: держится" : "КРАСНОЕ: " + bad.ToString();
}
finally
{
    if (pot != null) UnityEngine.Object.DestroyImmediate(pot.gameObject);
    if (pan != null) UnityEngine.Object.DestroyImmediate(pan.gameObject);
    if (plate != null) UnityEngine.Object.DestroyImmediate(plate.gameObject);
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
