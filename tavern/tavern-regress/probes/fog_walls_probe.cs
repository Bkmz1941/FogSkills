// Проба «туман не проходит сквозь стены и плиты» (Илья 08.09: «туман никогда не
// должен проходить сквозь стены 1 2 3 4 и тд этажей, и плиты пола потолка»).
// Запуск в play через execute_code (компилятор codedom, C# 6 — без out var).
//
// Меряет ИМЕННО ЖАЛОБУ: берёт коробку обрезки из property block — то, что
// реально видит шейдер, — режет ею габарит клуба и проверяет, пересекает ли
// ОСТАТОК объём комнаты. Комната — это промежуток между плитой и плитой над
// ней (иначе крыша считалась бы комнатой и туман над домом шёл бы в брак).
// Клуб считается эллипсоидом, вписанным в габарит: по коробке габарита углы
// торчат на 40 % и дают ложные срабатывания.
if (!Application.isPlaying) return "NOT PLAYING";
var rooms = new System.Collections.Generic.List<Bounds>();
foreach (var gb in UnityEngine.Object.FindObjectsByType<Cozy.Grid.GridBlock>(FindObjectsSortMode.None))
{
    if (gb.role != Cozy.Grid.GridRole.Floor) continue;
    var col = gb.GetComponentInChildren<Collider>();
    if (col == null) continue;
    var slab = col.bounds;
    float top = slab.max.y;
    var centre = new Vector3(slab.center.x, top + 3.05f, slab.center.z);
    bool lid = false;
    var hits = Physics.OverlapBox(centre, new Vector3(1.2f, 0.15f, 1.2f), Quaternion.identity);
    foreach (var h in hits)
    {
        var over = h.GetComponentInParent<Cozy.Grid.GridBlock>();
        if (over != null && over != gb && over.role == Cozy.Grid.GridRole.Floor) lid = true;
    }
    if (!lid) continue;
    var room = new Bounds();
    room.SetMinMax(new Vector3(slab.center.x - 1.4f, top + 0.05f, slab.center.z - 1.4f),
                   new Vector3(slab.center.x + 1.4f, top + 2.95f, slab.center.z + 1.4f));
    rooms.Add(room);
}
var block = new MaterialPropertyBlock();
int lo = Shader.PropertyToID("_ClipMin"), hi = Shader.PropertyToID("_ClipMax");
int puffs = 0, bad = 0;
float deepest = 0f;
string worst = "";
foreach (var view in UnityEngine.Object.FindObjectsByType<Cozy.Grid.FogView>(FindObjectsSortMode.None))
{
    foreach (var mr in view.GetComponentsInChildren<MeshRenderer>(true))
    {
        puffs++;
        mr.GetPropertyBlock(block);
        Vector3 cmin = block.GetVector(lo), cmax = block.GetVector(hi);
        if (cmax.x - cmin.x < 0.0001f) { cmin = new Vector3(-1e5f, -1e5f, -1e5f); cmax = -cmin; }
        var b = mr.bounds;
        var a0 = Vector3.Max(b.min, cmin);
        var a1 = Vector3.Min(b.max, cmax);
        if (a0.x >= a1.x || a0.y >= a1.y || a0.z >= a1.z) continue;
        var c = b.center;
        var e = b.extents;
        if (e.x < 0.0001f || e.y < 0.0001f || e.z < 0.0001f) continue;
        foreach (var room in rooms)
        {
            var r0 = Vector3.Max(room.min, a0);
            var r1 = Vector3.Min(room.max, a1);
            if (r0.x >= r1.x || r0.y >= r1.y || r0.z >= r1.z) continue;
            float nx = Mathf.Max(0f, Mathf.Max((r0.x - c.x) / e.x, (c.x - r1.x) / e.x));
            float ny = Mathf.Max(0f, Mathf.Max((r0.y - c.y) / e.y, (c.y - r1.y) / e.y));
            float nz = Mathf.Max(0f, Mathf.Max((r0.z - c.z) / e.z, (c.z - r1.z) / e.z));
            if (nx * nx + ny * ny + nz * nz > 1f) continue;
            bad++;
            float depth = Mathf.Min(r1.x - r0.x, r1.z - r0.z);
            if (depth > deepest)
            {
                deepest = depth;
                worst = view.name + "/" + mr.name + " комната " + room.center.ToString("F1");
            }
            break;
        }
    }
}
// Вторая половина правила — видимость: клетки не гасятся целиком, а срезаются
// крышкой, и только те, что стоят НИЖЕ пола игрока. Гонять НА ОБОИХ ЭТАЖАХ:
// на втором крышка есть, на первом её быть не должно, и замер на одном этаже
// держит половину правила.
int shown = 0, dark = 0, lidded = 0;
float lowest = 1e9f;
foreach (var view in UnityEngine.Object.FindObjectsByType<Cozy.Grid.FogView>(FindObjectsSortMode.None))
{
    var body = view.transform.Find("Fog");
    if (body == null) continue;
    if (!body.gameObject.activeSelf) { dark++; continue; }
    shown++;
    var mrs = body.GetComponentsInChildren<MeshRenderer>(true);
    if (mrs.Length == 0) continue;
    mrs[0].GetPropertyBlock(block);
    Vector3 top = block.GetVector(hi);
    if (top.y < 1000f) { lidded++; if (top.y < lowest) lowest = top.y; }
}
var who = Cozy.Grid.PlayerRef.GameObject;
float floorY = who == null ? 0f : Cozy.Grid.GridManager.LevelY(who.transform.position.y, 3f);
return "клубов " + puffs + ", комнат " + rooms.Count + ", в помещении " + bad
     + (bad > 0 ? " (худший " + worst + ", вглубь " + deepest.ToString("F2") + " м) :: ПРОВАЛ" : " :: ОК")
     + "\nвидимость (игрок на полу y=" + floorY.ToString("F1") + "): показано " + shown
     + ", погашено " + dark + ", с крышкой " + lidded + (lidded > 0 ? " на y=" + lowest.ToString("F2") : "")
     + (dark > 0 ? " :: ПРОВАЛ, клетки гасятся целиком" : " :: ОК");
