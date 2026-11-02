if (!UnityEngine.Application.isPlaying) return "не в play";
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var fFloor = T.GetField("_floor", BF); var fOrient = T.GetField("_orient", BF); var fManual = T.GetField("_orientManual", BF); var fCell = T.GetField("_cell", BF);
var m = T.GetMethod("ComputeGhostAt", BF);
var floor = fFloor.GetValue(gc) as Cozy.Grid.GridManager;
if (floor == null || m == null) return "нет _floor или ComputeGhostAt";
float cs = (float)fCell.GetValue(gc);
int orient0 = (int)fOrient.GetValue(gc); bool manual0 = (bool)fManual.GetValue(gc);
fManual.SetValue(gc, false);
var walls = new System.Collections.Generic.List<UnityEngine.Vector3>();
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.role != Cozy.Grid.GridRole.Wall || gb.Rend == null || !gb.Rend.enabled) continue;
    var c = gb.Rend.bounds.center;
    if (UnityEngine.Mathf.Abs(c.y - cs * 0.5f) > cs * 0.4f) continue;
    bool near = false;
    foreach (var w in walls) if (UnityEngine.Vector3.Distance(w, c) < 6f) { near = true; break; }
    if (!near) walls.Add(c);
    if (walls.Count >= 6) break;
}
int total = 0, bad = 0; float maxD = 0f; string worst = "";
var hist = new int[8];
float pitch = 50f * UnityEngine.Mathf.Deg2Rad;
var args = new object[5];
foreach (var w in walls)
{
    for (int ix = -9; ix <= 9; ix++) for (int iz = -9; iz <= 9; iz++)
    {
        var p = new UnityEngine.Vector3(w.x + ix * 0.5f, 0f, w.z + iz * 0.5f);
        for (int yaw = 0; yaw < 360; yaw += 30)
        {
            float a = yaw * UnityEngine.Mathf.Deg2Rad;
            var dir = new UnityEngine.Vector3(UnityEngine.Mathf.Cos(pitch) * UnityEngine.Mathf.Cos(a), -UnityEngine.Mathf.Sin(pitch), UnityEngine.Mathf.Cos(pitch) * UnityEngine.Mathf.Sin(a));
            var ray = new UnityEngine.Ray(p - dir * 25f, dir);
            fOrient.SetValue(gc, 0);
            args[0] = p; args[1] = ray; args[2] = 0; args[3] = UnityEngine.Vector3.zero; args[4] = UnityEngine.Vector3.one;
            bool ok = (bool)m.Invoke(gc, args);
            if (!ok) continue;
            var pos = (UnityEngine.Vector3)args[3];
            float d = UnityEngine.Mathf.Sqrt((pos.x - p.x) * (pos.x - p.x) + (pos.z - p.z) * (pos.z - p.z));
            total++;
            int bin = UnityEngine.Mathf.Min(7, (int)(d / 1.5f)); hist[bin]++;
            if (d > 3.4f) bad++;
            if (d > maxD) { maxD = d; worst = "p=" + p.ToString("F2") + " yaw=" + yaw + " → pos=" + pos.ToString("F2"); }
        }
    }
}
fOrient.SetValue(gc, orient0); fManual.SetValue(gc, manual0);
if (walls.Count == 0) return "ПРОПУСК: на уровне нет стен уровня 0 для замера";
var sb = new System.Text.StringBuilder();
sb.Append((bad == 0 && maxD <= 3.4f ? "ok" : "КРАСНОЕ") + " BD-G03 стена у курсора: ");
sb.Append("стен-центров " + walls.Count + " лучей " + total + " улетело(>3.4 м) " + bad + " max " + maxD.ToString("F2") + " м\n");
sb.Append("гистограмма по 1.5 м: ");
for (int i = 0; i < 8; i++) sb.Append(hist[i] + (i < 7 ? " | " : ""));
sb.Append("\nхудший: " + worst);
return sb.ToString();
