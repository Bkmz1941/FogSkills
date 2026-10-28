if (!UnityEngine.Application.isPlaying) return "NOT PLAYING";
System.Type hudType = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) { var t = asm.GetType("Tavern.UI.HudUI"); if (t != null) { hudType = t; break; } }
if (hudType == null) foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) foreach (var t in asm.GetTypes()) if (t.Name == "HudUI") { hudType = t; break; }
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Instance;
var hud = UnityEngine.Object.FindFirstObjectByType(hudType);
var mFocus = hudType.GetMethod("ExamineFocus", flags); var mPitch = hudType.GetMethod("ExaminePitchOf", flags);
var mDist = hudType.GetMethod("ExamineDistanceOf", flags); var mFit = hudType.GetMethod("ExamineFitDistance", flags);
var mShift = hudType.GetMethod("ShiftFocusForCard", flags);
var sb = new System.Text.StringBuilder();
var list = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None)) if (io.Def != null && io.Def.examinable) list.Add(io);
list.Sort((a, b) => { int c = string.CompareOrdinal(a.Def.id, b.Def.id); if (c != 0) return c; c = a.transform.position.x.CompareTo(b.transform.position.x); return c != 0 ? c : a.transform.position.z.CompareTo(b.transform.position.z); });
float[] yaws = { 0f, 69f, 135f };
foreach (var io in list)
{
    var ex = (Cozy.Grid.IExaminable)io;
    var focus = (UnityEngine.Vector3)mFocus.Invoke(mFocus.IsStatic ? null : hud, new object[] { io });
    float pitch = (float)mPitch.Invoke(mPitch.IsStatic ? null : hud, new object[] { io });
    foreach (var yaw in yaws)
    {
        float fit = (float)mFit.Invoke(mFit.IsStatic ? null : hud, new object[] { io, focus, yaw, pitch });
        float dist = (float)mDist.Invoke(mDist.IsStatic ? null : hud, new object[] { io, focus, yaw, pitch });
        var shifted = (UnityEngine.Vector3)mShift.Invoke(mShift.IsStatic ? null : hud, new object[] { focus, yaw, pitch, dist });
        sb.Append(io.Def.id + " @" + io.transform.position.ToString("F2") + " yaw=" + yaw + " pitch=" + pitch.ToString("F1") + " fit=" + fit.ToString("F4") + " dist=" + dist.ToString("F4") + " shift=" + shifted.ToString("F4") + "\n");
    }
}
System.IO.File.WriteAllText("/tmp/out.txt", sb.ToString());
return "объектов=" + list.Count + " строк=" + (list.Count * yaws.Length);
