var sb = new System.Text.StringBuilder();
var before = new System.Collections.Generic.Dictionary<string, Vector3>();
foreach (var l in System.IO.File.ReadAllLines("/tmp/doors_before.txt"))
{
    var p = l.Split('|'); var v = p[2].Trim('(', ')').Split(',');
    before[p[0] + "|" + p[1]] = new Vector3(float.Parse(v[0]), float.Parse(v[1]), float.Parse(v[2]));
}
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || !io.name.StartsWith("DoorProbe_")) continue;
    foreach (var t in io.GetComponentsInChildren<Transform>(true))
    {
        if (!t.name.StartsWith("Door")) continue;
        Vector3 b0; before.TryGetValue(io.name + "|" + t.name, out b0);
        float ang = Quaternion.Angle(Quaternion.Euler(b0), t.localRotation);
        sb.Append(io.Def.id + " " + t.name + ": открыта на " + ang.ToString("0") + "°" + (ang < 90f ? "  <-- НЕ ДО КОНЦА" : "") + "\n");
    }
}
foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
    if (io != null && io.name.StartsWith("DoorProbe_")) UnityEngine.Object.Destroy(io.gameObject);
return sb.ToString();
