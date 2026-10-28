"""Тарелка у мойки не входит в текстуры (P239, инвариант 70).

Ведёт тарелку призраком (ComputeObjectPose) по 10 точкам: борт → край чаши →
чаша, вдоль и поперёк. Сначала при чаше как есть, потом со спавном сковороды
и кастрюли в горку (сценарий «нет места» со скрина Ильи 05.09). В каждой
точке меряет заход коробки тарелки в любые коллайдеры мира, кроме корпуса
тумбы под мойкой (его сплошной бокс накрывает вырез чаши по построению):
ждём 0 мм. При пустой чаше внутри неё тарелка обязана лечь на дно.
Спавн и позы игрока с камерой возвращаются как были.
"""
import json, subprocess

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'

CODE = r'''
if (!UnityEngine.Application.isPlaying || Cozy.Grid.GridCursor.I == null) return "не в play";
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var gc = Cozy.Grid.GridCursor.I;
var mPose = T.GetMethod("ComputeObjectPose", B);
if (mPose == null) return "КРАСНОЕ: нет ComputeObjectPose";
Cozy.Grid.SinkPile pile = null;
foreach (var p in UnityEngine.Object.FindObjectsByType<Cozy.Grid.SinkPile>(UnityEngine.FindObjectsSortMode.None)) pile = p;
if (pile == null) return "КРАСНОЕ: мойки нет в уровне";
var sinkIo = pile.Owner; var st = sinkIo.transform;
UnityEngine.Bounds bowl;
if (!pile.BowlBounds(out bowl)) return "КРАСНОЕ: чаша мойки не готова";
var host = sinkIo.HostObject;
var bad = new System.Text.StringBuilder();
var members = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
pile.Collect(members, null);
int startMembers = members.Count;
var player = Cozy.Grid.PlayerRef.GameObject; var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPlayer = player.transform.position; var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var spawned = new System.Collections.Generic.List<UnityEngine.GameObject>();
UnityEngine.GameObject body = null;
int points = 0, blockedN = 0;
try {
  var def = Cozy.Grid.FurnitureCatalog.ById("plate");
  body = new UnityEngine.GameObject("RimProbe");
  var io = body.AddComponent<Cozy.Grid.InteractiveObject>(); io.Build(def);
  var plateCols = body.GetComponentsInChildren<UnityEngine.Collider>();
  float floorY = UnityEngine.Mathf.Floor((st.position.y + 0.01f) / 3f) * 3f;
  player.transform.position = st.position + st.forward * -1.2f; UnityEngine.Physics.SyncTransforms();
  float[] xs = new float[]{ 0f, 0f, 0f, 0.55f, 0.45f, 0.35f, 0.25f, 0.15f, -0.15f, -0.35f };
  float[] zs = new float[]{ -0.35f, -0.25f, -0.05f, -0.05f, -0.05f, -0.05f, -0.05f, -0.05f, -0.05f, -0.05f };
  for (int stage = 0; stage < 2; stage++)
  {
    if (stage == 1)
      foreach (var id in new string[]{ "frying_pan", "cooking_pot" })
      {
        var go = new UnityEngine.GameObject("RimProbe_" + id); spawned.Add(go);
        var o = go.AddComponent<Cozy.Grid.InteractiveObject>(); o.Build(Cozy.Grid.FurnitureCatalog.ById(id));
        go.transform.position = st.position + UnityEngine.Vector3.up * 5f; UnityEngine.Physics.SyncTransforms();
        UnityEngine.Vector3 pp; UnityEngine.Quaternion pr;
        if (pile.NextPose(o, null, out pp, out pr)) { go.transform.SetPositionAndRotation(pp, pr); UnityEngine.Physics.SyncTransforms(); }
      }
    for (int k = 0; k < xs.Length; k++)
    {
      float dx = xs[k], dz = zs[k];
      var target = st.TransformPoint(new UnityEngine.Vector3(dx, 0f, dz)); target.y = st.position.y;
      var worldDir = new UnityEngine.Vector3(0.0f, -1f, 0.35f).normalized;
      cam.transform.SetPositionAndRotation(target - worldDir * 3f, UnityEngine.Quaternion.identity);
      var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
      cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
      cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 3f;
      var args = new object[]{ def, cam, mouse, body, body.transform, floorY, null, null, null };
      if (!(bool)mPose.Invoke(gc, args)) { bad.Append("нет позы в точке " + k + "; "); continue; }
      var pos = (UnityEngine.Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
      points++; if (blocked) blockedN++;
      body.transform.SetPositionAndRotation(pos, UnityEngine.Quaternion.Euler(0f, yaw, 0f)); UnityEngine.Physics.SyncTransforms();
      var wb = io.WorldBounds;
      var near = UnityEngine.Physics.OverlapBox(wb.center, wb.extents + UnityEngine.Vector3.one * 0.05f, UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
      foreach (var sc in near)
      {
        if (sc.isTrigger || sc.transform.IsChildOf(body.transform)) continue;
        var oio = sc.GetComponentInParent<Cozy.Grid.InteractiveObject>();
        if (host != null && oio == host) continue;
        foreach (var pc in plateCols)
        {
          if (pc.isTrigger) continue;
          UnityEngine.Vector3 dir; float dist;
          if (UnityEngine.Physics.ComputePenetration(pc, pc.transform.position, pc.transform.rotation, sc, sc.transform.position, sc.transform.rotation, out dir, out dist) && dist > 0.001f)
            bad.Append("заход " + (dist * 1000f).ToString("F0") + " мм в " + (oio != null ? oio.Def.id : sc.name) + " (этап " + stage + ", точка " + k + ", " + (blocked ? "красная" : "валидная") + "); ");
        }
      }
      bool inside = wb.min.x >= bowl.min.x - 0.005f && wb.max.x <= bowl.max.x + 0.005f && wb.min.z >= bowl.min.z - 0.005f && wb.max.z <= bowl.max.z + 0.005f;
      if (stage == 0 && startMembers == 0 && inside && UnityEngine.Mathf.Abs(wb.min.y - bowl.min.y) > 0.005f)
        bad.Append("в пустой чаше тарелка не на дне: " + ((wb.min.y - bowl.min.y) * 1000f).ToString("F0") + " мм над дном (точка " + k + "); ");
    }
  }
} finally {
  if (body != null) UnityEngine.Object.DestroyImmediate(body);
  foreach (var go in spawned) if (go != null) UnityEngine.Object.DestroyImmediate(go);
  player.transform.position = savedPlayer; cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot); UnityEngine.Physics.SyncTransforms();
}
int left = 0;
foreach (var x in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None)) if (x.name.StartsWith("RimProbe")) left++;
if (left > 0) bad.Append("утечка проб: " + left + "; ");
return "точек=" + points + " красных=" + blockedN + " в горке было=" + startMembers + " :: " + (bad.Length == 0 ? "тарелка у мойки чисто" : "КРАСНОЕ: " + bad.ToString());
'''


def main():
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": CODE})],
                         capture_output=True, text=True, timeout=280)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    data = json.loads(line)
    print(data.get("data", {}).get("result") or json.dumps(data, ensure_ascii=False)[:400])


if __name__ == '__main__':
    main()
