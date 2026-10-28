if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mDoor = T.GetMethod("DoorSlotValid", B); var mWin = T.GetMethod("WindowSlotValid", B);
var sb = new System.Text.StringBuilder(); float cs = 3f;
int okD = 0, okW = 0, total = 0;
for (int f = 0; f < 5; f++) {
  float L = f * cs; float yc = L + (cs - 0.2f) * 0.5f;
  for (int i = 0; i < 4; i++) for (int j = 0; j < 3; j++) {
    float cx = -6f + i * cs, cz = -6f + j * cs;
    var edges = new[] { new object[]{ new UnityEngine.Vector3(cx, yc, cz + cs * 0.5f), true, "N" }, new object[]{ new UnityEngine.Vector3(cx + cs * 0.5f, yc, cz), false, "E" } };
    if (j == 0) edges = new[] { edges[0], edges[1], new object[]{ new UnityEngine.Vector3(cx, yc, cz - cs * 0.5f), true, "S" } };
    if (i == 0) { var l = new System.Collections.Generic.List<object[]>(edges); l.Add(new object[]{ new UnityEngine.Vector3(cx - cs * 0.5f, yc, cz), false, "W" }); edges = l.ToArray(); }
    foreach (var e in edges) {
      var pos = (UnityEngine.Vector3)e[0]; bool sx = (bool)e[1];
      bool d = (bool)mDoor.Invoke(gc, new object[]{ pos, sx, cs }); bool w = (bool)mWin.Invoke(gc, new object[]{ pos, cs });
      total++; if (d) okD++; if (w) okW++;
      var wall = Cozy.Grid.BuildQuery.BlockAt(pos, new UnityEngine.Vector3(0.75f, 0.9f, 0.75f), Cozy.Grid.GridRole.Wall);
      bool door = Cozy.Grid.BuildQuery.DoorAt(pos, new UnityEngine.Vector3(0.75f, 0.9f, 0.75f)); bool win = Cozy.Grid.BuildQuery.WindowAt(pos, new UnityEngine.Vector3(0.75f, 0.9f, 0.75f));
      sb.Append("э" + f + " (" + i + "," + j + ") " + e[2] + " " + (wall != null ? "стена" : door ? "дверь" : win ? "окно" : "пусто") + " дверь=" + (d ? "да" : "нет") + " окно=" + (w ? "да" : "нет") + "\n");
    }
  }
}
sb.Insert(0, "рёбер " + total + ": дверь можно " + okD + ", окно можно " + okW + "\n");
return sb.ToString();
