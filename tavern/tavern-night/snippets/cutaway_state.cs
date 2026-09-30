if (!UnityEngine.Application.isPlaying) return "не в play";
var lines = new System.Collections.Generic.List<string>();
var T = typeof(Cozy.Grid.WallCutaway); var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public;
var fCols = T.GetField("_cols", B); var fAbove = T.GetField("_lastAbove", B); var fApplied = T.GetField("_applied", B); var fCov = T.GetField("_covered", B);
foreach (var wc in Cozy.Grid.WallCutaway.All) {
  if (wc == null) continue;
  var sb = new System.Text.StringBuilder();
  sb.Append("RUN " + wc.transform.position.ToString("F2") + " above=" + fAbove.GetValue(wc) + " applied=" + fApplied.GetValue(wc) + " covered=" + fCov.GetValue(wc));
  var cols = fCols.GetValue(wc) as System.Collections.IEnumerable;
  int ci = 0;
  foreach (var col in cols) {
    var ct = col.GetType();
    sb.Append(" | col" + ci++ + " along=" + ((float)ct.GetField("along", B).GetValue(col)).ToString("F2") + " fulls=" + ct.GetField("lastFulls", B).GetValue(col) + " cut=" + ct.GetField("lastCut", B).GetValue(col) + " hidden=" + ct.GetField("lastHidden", B).GetValue(col));
    var fulls = ct.GetField("fulls", B).GetValue(col) as System.Collections.Generic.List<UnityEngine.Renderer>;
    var names = new System.Collections.Generic.List<string>();
    foreach (var r in fulls) if (r != null) names.Add(r.name + "@" + r.bounds.center.ToString("F2") + ":" + (r.enabled ? "on" : "off") + "/" + r.shadowCastingMode);
    names.Sort(string.CompareOrdinal); sb.Append(" [" + string.Join(";", names) + "]");
  }
  lines.Add(sb.ToString());
}
lines.Sort(string.CompareOrdinal);
string all = string.Join("\n", lines);
var md5 = System.Security.Cryptography.MD5.Create(); var h = md5.ComputeHash(System.Text.Encoding.UTF8.GetBytes(all));
System.IO.File.WriteAllText("/tmp/claude-1000/-home-ilya/b45c2962-6da6-4790-b188-fe92bc03303c/scratchpad/cutaway_LABEL.txt", all);
return "run'ов " + lines.Count + " md5 " + System.BitConverter.ToString(h).Replace("-", "").Substring(0, 12) + " игрок " + Cozy.Grid.PlayerRef.GameObject.transform.position.ToString("F2") + " этаж " + Cozy.View.ViewState.CurrentFloorY;
