// Проба дверец угловых шкафов (P163): ставит оба угловых навесных шкафа в
// угол, открывает все дверцы через AccessFeature и через 3–4 с (второй файл
// corner_doors_probe_end.cs) меряет угол каждой: ожидание 95° у всех.
if (!Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
System.Reflection.MethodInfo mSpawn = null;
foreach (var m in T.GetMethods(B)) if (m.Name == "SpawnObject") { mSpawn = m; break; }
var specs = new object[][] { new object[] { "home_wall_cabinet_corner_wide", new Vector3(-11.44f, 2.05f, -12.14f) }, new object[] { "home_wall_cabinet_corner", new Vector3(-11.44f, 2.05f, -8.0f) } };
var lines = new System.Collections.Generic.List<string>();
foreach (var spec in specs)
{
    var def = Cozy.Grid.FurnitureCatalog.ById((string)spec[0]);
    var io = mSpawn.Invoke(gc, new object[] { def, (Vector3)spec[1], 90f }) as Cozy.Grid.InteractiveObject;
    io.name = "DoorProbe_" + def.id;
    Physics.SyncTransforms();
    int opened = 0;
    foreach (var f in io.Features)
    {
        var acc = f as Cozy.Grid.AccessFeature;
        if (acc == null) continue;
        acc.SetOpen(true); opened++;
    }
    foreach (var t in io.GetComponentsInChildren<Transform>(true))
        if (t.name.StartsWith("Door")) lines.Add(io.name + "|" + t.name + "|" + t.localRotation.eulerAngles.ToString("F1"));
    sb.Append(def.id + ": дверей-фич открыто " + opened + "\n");
}
System.IO.File.WriteAllLines("/tmp/doors_before.txt", lines.ToArray());
return sb.ToString();
