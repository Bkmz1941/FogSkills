// Характеризующий замер раскладки тумана: исходные данные КАЖДОГО клуба уровня, как их
// посадил FogVolume.SpawnPlan (16.09). Живые позиции клубов дышат и качаются, поэтому
// печатается не transform, а то, что FogAnim запомнил при посадке: позиция, масштаб,
// поворот, меш, плотность, тон, флаги и три фазы из rng клетки. Запуск в play:
// python3 measure.py fog_spawn_probe.cs /путь/до.txt → правка → перезаход в play → после.txt → diff.
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var itemsF = typeof(Cozy.Grid.FogAnim).GetField("_items", F);
var inv = System.Globalization.CultureInfo.InvariantCulture;
var rows = new System.Collections.Generic.List<string>();
int puffs = 0;
foreach (var anim in Cozy.Grid.FogAnim.All)
{
    if (anim == null) continue;
    string path = anim.transform.name;
    for (var t = anim.transform.parent; t != null; t = t.parent) path = t.name + "/" + path;
    var sb = new System.Text.StringBuilder();
    sb.Append(path).Append(" @").Append(anim.transform.position.ToString("F3")).Append('\n');
    foreach (var it in (System.Collections.IList)itemsF.GetValue(anim))
    {
        var ty = it.GetType();
        System.Func<string, object> g = name => ty.GetField(name).GetValue(it);
        var tr = (UnityEngine.Transform)g("T");
        var mf = tr != null ? tr.GetComponent<UnityEngine.MeshFilter>() : null;
        sb.Append("  ").Append(tr != null ? tr.name : "null")
          .Append(" m=").Append(mf != null && mf.sharedMesh != null ? mf.sharedMesh.name : "-")
          .Append(" rot=").Append(tr != null ? tr.localRotation.eulerAngles.ToString("F3") : "-")
          .Append(" pos=").Append(((UnityEngine.Vector3)g("Pos")).ToString("F4"))
          .Append(" scale=").Append(((UnityEngine.Vector3)g("Scale")).ToString("F4"))
          .Append(" a=").Append(((float)g("Alpha")).ToString("F4", inv))
          .Append(" tone=").Append(((float)g("Tone")).ToString("F4", inv))
          .Append(" fade=").Append(g("Fading")).Append(" flare=").Append(g("Flare"))
          .Append(" life=").Append(((float)g("Life")).ToString("F4", inv))
          .Append(" move=").Append(((float)g("Move")).ToString("F4", inv))
          .Append(" puff=").Append(((float)g("Puff")).ToString("F4", inv)).Append('\n');
        puffs++;
    }
    rows.Add(sb.ToString());
}
rows.Sort(System.StringComparer.Ordinal);
System.IO.File.WriteAllText("/tmp/fog_spawn.txt", "клеток " + rows.Count + ", клубов " + puffs + "\n" + string.Join("", rows));
return "клеток " + rows.Count + ", клубов " + puffs;
