// Проба «Сесть» (INVARIANTS 33). execute_code в play на уровне со стулом
// (`chair`) у стола (`seatCount>0`). Стул временно выдвигается в «За стол»
// (+0.6 от утопленного), мелкий предмет временно ставится в зону рук; всё
// возвращается. Ожидание: seated=True clip=Sit_Idle blocksZone=True
// blocksAside=False; с предметом clip=Sit_Idle_Lap; после Leave seated=False.
var sb = new System.Text.StringBuilder();
var player = Cozy.Grid.PlayerRef.GameObject;
Cozy.Grid.InteractiveObject table = null, small = null, chair = null;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null) continue;
    if (table == null && io.Def.seatCount > 0) table = io;
    if (small == null && !io.Def.chair && io.Def.seatCount == 0 && io.transform.parent != null && io.WorldBounds.size.magnitude < 0.6f && io.WorldBounds.size.magnitude > 0.1f) small = io;
}
if (table == null) return "нет стола с seatCount";
float bestD = 3f;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || !io.Def.chair) continue;
    float d = UnityEngine.Vector3.Distance(io.transform.position, table.WorldBounds.center);
    if (d < bestD) { bestD = d; chair = io; }
}
if (chair == null) return "нет стула у стола";
var dir = chair.transform.position - table.WorldBounds.center; dir.y = 0f; dir.Normalize();
var chairPos = chair.transform.position;
var playerPos = player.transform.position;
if (Cozy.Grid.SitFeature.PushedIn(chair)) chair.transform.position += dir * 0.6f;
UnityEngine.Physics.SyncTransforms();
sb.Append("стул " + chair.transform.position.ToString("0.00") + " pushed=" + Cozy.Grid.SitFeature.PushedIn(chair) + "\n");
Cozy.Grid.SitFeature.SitOn(chair);
float top = table.WorldBounds.max.y;
var zone = new UnityEngine.Bounds(player.transform.position + player.transform.forward * 0.6f + UnityEngine.Vector3.up * (top + 0.1f - player.transform.position.y), new UnityEngine.Vector3(0.2f, 0.2f, 0.2f));
var aside = new UnityEngine.Bounds(zone.center + player.transform.right * 1.5f, zone.size);
sb.Append("seated=" + Cozy.Grid.SitFeature.PlayerSeated + " clip=" + Cozy.Grid.SitFeature.Clip + " blocksZone=" + Cozy.Grid.SitFeature.BlocksPlacement(zone) + " blocksAside=" + Cozy.Grid.SitFeature.BlocksPlacement(aside) + "\n");
Cozy.Grid.SitFeature.Leave();
if (small != null)
{
    var objPos = small.transform.position;
    var front = -chair.transform.forward; front.y = 0f; front.Normalize();
    small.transform.position = new UnityEngine.Vector3(chair.transform.position.x, top + 0.05f, chair.transform.position.z) + front * 0.55f;
    UnityEngine.Physics.SyncTransforms();
    Cozy.Grid.SitFeature.SitOn(chair);
    sb.Append("с предметом в зоне: clip=" + Cozy.Grid.SitFeature.Clip + "\n");
    Cozy.Grid.SitFeature.Leave();
    small.transform.position = objPos;
}
chair.transform.position = chairPos;
UnityEngine.Physics.SyncTransforms();
sb.Append("после: seated=" + Cozy.Grid.SitFeature.PlayerSeated + " игрок вернулся=" + (UnityEngine.Vector3.Distance(player.transform.position, playerPos) < 0.01f) + " cc=" + player.GetComponent<UnityEngine.CharacterController>().enabled + "\n");
return sb.ToString();
