if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
System.Func<string, int, System.Reflection.MethodInfo> M = (name, n) => { foreach (var m in T.GetMethods(B)) if (m.Name == name && m.GetParameters().Length == n) return m; return null; };
var mBegin = M("BeginPose", 7); var steps = new[] { "SnapToNeighbours", "SnapToWall", "SnapKitLine", "ResolvePoseHeight", "ValidatePose", "ApplyLiftStop" };
var PW = T.GetNestedType("PoseWork", B);
System.Func<object, string> show = w => { var sb2 = new System.Text.StringBuilder(); foreach (var f in new[]{ "X", "Y", "Z", "Yaw", "Blocked", "WallBlocked", "Kit", "Free", "WallMount", "FreeWall", "Hugged" }) { var fi = PW.GetField(f, B); if (fi != null) sb2.Append(f + "=" + fi.GetValue(w) + " "); } return sb2.ToString(); };
var fOrient = T.GetField("_orient", B); var fSide = T.GetField("_sideStop", B); var fLift = T.GetField("_liftStop", B); var fFreeYaw = T.GetField("_freeYaw", B);
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current; var cursor = mouse.position.ReadValue();
var savedCamPos = cam.transform.position; var savedCamRot = cam.transform.rotation;
var sb = new System.Text.StringBuilder();
UnityEngine.GameObject body = null;
try {
  var cases = new object[][] {
    new object[]{ "home_coffee_machine", 3.84f, 1.15f, -1.6f, 345f, "surf" },
    new object[]{ "coffee_cup_blue", 2.64f, 1.15f, 1.09f, 90f, "surf" },
    new object[]{ "sponge", 4.14f, 1.15f, -1.1f, 210f, "surf" },
    new object[]{ "apple", 0f, 1.42f, -3.0f, 0f, "surf" },
    new object[]{ "frying_pan", 3.48f, 1.16f, -4.55f, 270f, "surf" },
    new object[]{ "home_wall_cabinet_corner_wide", 4.48f, 1.8f, -0.2f, 90f, "wall" },
  };
  foreach (var c in cases) {
    string id = (string)c[0]; float tx = (float)c[1]; float ty = (float)c[2]; float tz = (float)c[3]; float yaw = (float)c[4]; string kind = (string)c[5];
    var def = Cozy.Grid.FurnitureCatalog.ById(id);
    fSide.SetValue(gc, 0); fLift.SetValue(gc, 0); fOrient.SetValue(gc, ((int)UnityEngine.Mathf.Round(yaw / 90f)) & 3); fFreeYaw.SetValue(gc, yaw);
    UnityEngine.Vector3 target, dir; float dist;
    if (kind == "wall") { var back = new UnityEngine.Vector3(UnityEngine.Mathf.Sin(yaw * UnityEngine.Mathf.Deg2Rad), 0f, UnityEngine.Mathf.Cos(yaw * UnityEngine.Mathf.Deg2Rad)); target = new UnityEngine.Vector3(tx, ty, tz) - back * 0.02f; dir = (back + UnityEngine.Vector3.down * 0.35f).normalized; dist = 1.6f; }
    else { target = new UnityEngine.Vector3(tx, ty, tz); dir = new UnityEngine.Vector3(0.12f, -1f, 0.08f).normalized; dist = 1.4f; }
    cam.transform.SetPositionAndRotation(target - dir * dist, UnityEngine.Quaternion.identity);
    var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, dir);
    cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * dist;
    body = new UnityEngine.GameObject("NightProbe"); body.transform.position = new UnityEngine.Vector3(tx, -50f, tz);
    body.AddComponent<Cozy.Grid.InteractiveObject>().Build(def);
    var a = new object[] { def, cam, mouse, body, body.transform, 0f, null };
    bool ok = (bool)mBegin.Invoke(gc, a);
    sb.Append("== " + id + " цель " + target.ToString("F2") + " begin=" + ok + "\n");
    if (!ok) { UnityEngine.Object.DestroyImmediate(body); body = null; continue; }
    object w = a[6];
    sb.Append("   begin: " + show(w) + "\n");
    foreach (var s in steps) {
      var m = M(s, 1); var sa = new object[] { w }; m.Invoke(gc, sa); w = sa[0];
      sb.Append("   " + s + ": " + show(w) + "\n");
      if (s == "ResolvePoseHeight" && kind == "surf") {
        float X = (float)PW.GetField("X", B).GetValue(w), Y = (float)PW.GetField("Y", B).GetValue(w), Z = (float)PW.GetField("Z", B).GetValue(w), YW = (float)PW.GetField("Yaw", B).GetValue(w);
        var pos = new UnityEngine.Vector3(X, Y, Z);
        try { sb.Append("      RaiseToBaseSupport=" + M("RaiseToBaseSupport", 7).Invoke(gc, new object[]{ body, X, Y, Z, YW, 0f, body.transform }) + "\n"); } catch (System.Exception e) { sb.Append("      RaiseToBaseSupport ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      VesselTopUnder=" + M("VesselTopUnder", 6).Invoke(gc, new object[]{ body, X, Y, Z, YW, body.transform }) + "\n"); } catch (System.Exception e) { sb.Append("      VesselTopUnder ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      BasinFloorUnder=" + M("BasinFloorUnder", 6).Invoke(gc, new object[]{ body, X, Y, Z, YW, body.transform }) + "\n"); } catch (System.Exception e) { sb.Append("      BasinFloorUnder ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      ObstacleTopUnder=" + M("ObstacleTopUnder", 5).Invoke(gc, new object[]{ body, pos, YW, body.transform, false }) + "\n"); } catch (System.Exception e) { sb.Append("      ObstacleTopUnder ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      SlotFits=" + M("SlotFits", 5).Invoke(gc, new object[]{ body, X, Y, Z, YW }) + "\n"); } catch (System.Exception e) { sb.Append("      SlotFits ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      SlotUnder=" + (Cozy.Grid.ContainerSlot.Under(pos) != null) + "\n"); } catch (System.Exception e) { sb.Append("      SlotUnder ошибка " + e.Message + "\n"); }
        try { sb.Append("      SurfaceSupported=" + M("SurfaceSupported", 6).Invoke(gc, new object[]{ body, X, Y, Z, YW, body.transform }) + "\n"); } catch (System.Exception e) { sb.Append("      SurfaceSupported ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      OnVessel=" + M("OnVessel", 6).Invoke(gc, new object[]{ body, X, Y, Z, YW, body.transform }) + "\n"); } catch (System.Exception e) { sb.Append("      OnVessel ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      OnStep=" + M("OnStep", 7).Invoke(gc, new object[]{ body, X, Y, Z, YW, 0f, body.transform }) + "\n"); } catch (System.Exception e) { sb.Append("      OnStep ошибка " + e.InnerException?.Message + "\n"); }
        try { sb.Append("      OnBowlEdge=" + M("OnBowlEdge", 5).Invoke(gc, new object[]{ body, X, Y, Z, YW }) + "\n"); } catch (System.Exception e) { sb.Append("      OnBowlEdge ошибка " + e.InnerException?.Message + "\n"); }
      }
    }
    UnityEngine.Object.DestroyImmediate(body); body = null;
  }
} finally { if (body != null) UnityEngine.Object.DestroyImmediate(body); cam.transform.SetPositionAndRotation(savedCamPos, savedCamRot); }
return sb.ToString();
