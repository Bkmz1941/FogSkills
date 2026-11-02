// physics_bin_probe.cs — ФИЗИЧЕСКИЙ БАК (инварианты 655, 656). Только в play, через execute_code (codedom, C# 6).
// BIN — id бака: dumpster_skip (без крышки) или trash_bin_1100 (крышка-гейт: закрыт → Bin.Open false, проба открывает сама).
// Спавнит бак перед игроком, бросает в него 8 предметов с рима, ждать 3–5 с, звать
// ВТОРОЙ РАЗ с PHASE = 2 (проверка: все внутри полости, спят, кружка с водой опрокинута → 0 л), затем PHASE = 3 (уборка).
// Уровень не сохраняется; все пробные объекты названы PROBE_ и удаляются фазой 3.
// Наклон кружки — через Rigidbody.rotation/position: у спящего тела с интерполяцией правка одного transform откатывается к позе физики (01.11, ilya-0b).
int PHASE = 1;
string BIN = "dumpster_skip";
var cur = Cozy.Grid.GridCursor.I;
var sb = new System.Text.StringBuilder();
Cozy.Grid.InteractiveObject bin = null, cup = null;
foreach (var o in Cozy.Grid.InteractiveObject.All) { if (o == null) continue; if (o.name == "PROBE_bin") bin = o; if (o.name == "PROBE_item_coffee_cup_red") cup = o; }
if (PHASE == 1)
{
    if (!Application.isPlaying) return "не в play";
    var player = Cozy.Grid.PlayerRef.GameObject.transform;
    Vector3 at = player.position + player.forward * 7f;
    RaycastHit gh;
    if (Physics.Raycast(at + Vector3.up * 30f, Vector3.down, out gh, 80f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)) at.y = gh.point.y;
    bin = cur.SpawnWorldObject(Cozy.Grid.FurnitureCatalog.ById(BIN), at, 30f);
    bin.gameObject.name = "PROBE_bin";
    Bounds cav;
    if (!Cozy.Grid.PhysicsProp.Bin.Cavity(bin, out cav)) return "FAIL: у бака нет полости (нет площадки Slot_Floor?)";
    bool wasOpen = Cozy.Grid.PhysicsProp.Bin.Open(bin);
    foreach (var f in bin.Features) { var af = f as Cozy.Grid.AccessFeature; if (af != null && !af.Open) af.SetOpen(true); }
    sb.AppendLine("бак " + BIN + " " + at.ToString("F1") + " yaw 30 полость " + cav.size.ToString("F2") + " меш=" + (bin.GetComponentInChildren<MeshCollider>() != null) + " гейт до=" + wasOpen + " после=" + Cozy.Grid.PhysicsProp.Bin.Open(bin));
    if (!Cozy.Grid.PhysicsProp.Bin.Open(bin)) return sb.ToString() + "FAIL: бак не открылся";
    string[] ids = { "old_book_1", "trash_can_1", "coffee_cup_red", "water_bottle", "old_book_3", "trash_bottle_1", "apple", "old_cup_1" };
    int k = 0;
    foreach (var id in ids)
    {
        var def = Cozy.Grid.FurnitureCatalog.ById(id);
        if (def == null) { sb.AppendLine(id + ": нет дефа"); continue; }
        Vector3 pos;
        if (!Cozy.Grid.PhysicsProp.Bin.Clamp(bin, new Vector3(cav.center.x + ((k % 3) - 1) * 0.45f, cav.center.y, cav.center.z + ((k / 3) - 1) * 0.35f), 0.12f, 0.12f, out pos)) { sb.AppendLine("FAIL " + id + ": не влезает в полость"); continue; }
        pos.y += 0.02f;
        var io = cur.SpawnWorldObject(def, pos, k * 37f);
        io.gameObject.name = "PROBE_item_" + id;
        cur.ReattachToContainer(io);
        Cozy.Grid.PhysicsProp.Drop(io);
        var rb = io.GetComponent<Rigidbody>();
        if (io.Container != bin || rb == null || rb.isKinematic) sb.AppendLine("FAIL " + id + ": container=" + (io.Container != null ? io.Container.name : "null") + " rb=" + (rb != null) + (rb != null ? " kin=" + rb.isKinematic : ""));
        if (id == "coffee_cup_red" && io.Liquid != null) io.Liquid.Fill(Cozy.Grid.LiquidVolume.Water, 0.2f);
        k++;
    }
    sb.AppendLine("брошено " + k + "; через 3–5 с звать PHASE = 2");
    return sb.ToString();
}
if (bin == null) return "нет PROBE_bin — сначала PHASE = 1";
if (PHASE == 2)
{
    Bounds cav; Cozy.Grid.PhysicsProp.Bin.Cavity(bin, out cav);
    int inside = 0, total = 0, asleep = 0, nested = 0;
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null || !io.name.StartsWith("PROBE_item_")) continue;
        total++;
        var b = io.WorldBounds;
        bool inXZ = b.min.x >= cav.min.x - 0.05f && b.max.x <= cav.max.x + 0.05f && b.min.z >= cav.min.z - 0.05f && b.max.z <= cav.max.z + 0.05f;
        bool inY = b.min.y >= cav.min.y - 0.05f && b.max.y <= cav.max.y + 0.3f;
        if (inXZ && inY) inside++; else sb.AppendLine("FAIL снаружи: " + io.name + " " + b.min.ToString("F2"));
        var rb = io.GetComponent<Rigidbody>();
        if (rb != null && rb.IsSleeping()) asleep++;
        if (io.Container == bin) nested++;
    }
    sb.AppendLine("внутри " + inside + "/" + total + ", спят " + asleep + ", привязаны к баку " + nested);
    if (cup != null && cup.Liquid != null)
    {
        if (cup.HasLiquid)
        {
            var crb = cup.GetComponent<Rigidbody>();
            if (crb != null) { crb.WakeUp(); crb.rotation = Quaternion.Euler(100f, 0f, 0f) * crb.rotation; crb.position = crb.position + Vector3.up * 0.3f; }
            cup.transform.rotation = Quaternion.Euler(100f, 0f, 0f) * cup.transform.rotation;
            cup.transform.position += Vector3.up * 0.3f;
            Physics.SyncTransforms();
            sb.AppendLine("кружка " + cup.Liquid.Litres.ToString("F2") + " л наклонена на 100° — через секунду PHASE = 2 ещё раз: ждём 0 л");
        }
        else sb.AppendLine("кружка после наклона: " + cup.Liquid.Litres.ToString("F3") + " л (ждём 0) — " + (cup.Liquid.Litres < 0.001f ? "OK" : "FAIL"));
    }
    return sb.ToString();
}
var list = new System.Collections.Generic.List<GameObject>();
foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.name.StartsWith("PROBE_")) list.Add(io.gameObject);
foreach (var go in list) UnityEngine.Object.Destroy(go);
return "убрано " + list.Count + " пробных объектов";
