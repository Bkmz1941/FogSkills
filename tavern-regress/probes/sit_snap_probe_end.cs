// Вторая половина sit_snap_probe.cs: через 1–2 с после посадки меряет кисти
// относительно столешницы, встаёт и возвращает стул на место.
var sb = new System.Text.StringBuilder();
var player = Cozy.Grid.PlayerRef.GameObject;
var chair = Cozy.Grid.SitFeature.Seat;
if (chair == null) return "не сидит";
float top = 0f;
foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null && io.Def.seatCount > 0) { top = io.WorldBounds.max.y; break; }
var anim = player.GetComponentInChildren<Animator>();
foreach (var b in new HumanBodyBones[] { HumanBodyBones.Hips, HumanBodyBones.LeftHand, HumanBodyBones.LeftLowerArm, HumanBodyBones.RightHand })
{
    var t = anim.GetBoneTransform(b);
    sb.Append(b + ": y=" + t.position.y.ToString("0.00") + " от столешницы " + (t.position.y - top).ToString("+0.00;-0.00") + "\n");
}
if (Cozy.Grid.PlayerPosture.Current != null) Cozy.Grid.PlayerPosture.Current.Leave();
var parts = System.IO.File.ReadAllText("/tmp/sit_snap_state.txt").Split(' ');
chair.transform.SetPositionAndRotation(new Vector3(float.Parse(parts[0]), float.Parse(parts[1]), float.Parse(parts[2])), Quaternion.Euler(0f, float.Parse(parts[3]), 0f));
Physics.SyncTransforms();
sb.Append("после: seated=" + Cozy.Grid.SitFeature.PlayerSeated + " стул " + chair.transform.position.ToString("0.00") + "\n");
return sb.ToString();
