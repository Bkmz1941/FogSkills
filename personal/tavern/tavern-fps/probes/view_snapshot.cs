// Отпечаток гейта видимости: у каждого FloorPieceView из реестра бодрствующих — Visible
// и (enabled, shadowCastingMode) каждого его рендерера. Сверка ДО/ПОСЛЕ правки
// FloorPieceView/PieceViewTicker: при неподвижном игроке строки обязаны совпасть.
var T = typeof(Cozy.Grid.FloorPieceView);
var aw = (System.Collections.IList)T.GetField("Awake", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Static).GetValue(null);
var all = UnityEngine.Object.FindObjectsByType<Cozy.Grid.FloorPieceView>(UnityEngine.FindObjectsInactive.Include, UnityEngine.FindObjectsSortMode.None);
var rows = new System.Collections.Generic.List<string>();
int vis = 0, on = 0, ghost = 0;
foreach (var v in all)
{
    var sb = new System.Text.StringBuilder();
    var p = v.transform.position;
    sb.Append(v.name).Append(' ').Append(p.x.ToString("F2")).Append(',').Append(p.y.ToString("F2")).Append(',').Append(p.z.ToString("F2"));
    sb.Append(v.Visible ? " V" : " h");
    if (v.Visible) vis++;
    if (v.Targets != null)
        foreach (var r in v.Targets)
        {
            if (r == null) { sb.Append(" -"); continue; }
            sb.Append(r.enabled ? " 1" : " 0").Append((int)r.shadowCastingMode);
            if (r.enabled) on++;
            if (r.enabled && r.shadowCastingMode == UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly) ghost++;
        }
    rows.Add(sb.ToString());
}
rows.Sort(System.StringComparer.Ordinal);
int h = 17; foreach (var s in rows) h = h * 31 + s.GetHashCode();
System.IO.File.WriteAllLines(System.IO.Path.Combine(System.Environment.GetEnvironmentVariable("HOME"), ".cache/tavern-probes/view_snapshot_LABEL.txt"), rows.ToArray());
return "видов=" + all.Length + " бодрых=" + aw.Count + " видимых=" + vis + " рендеров вкл=" + on + " призраков=" + ghost + " хеш=" + h;
