// Проба «зона кистью» (ZoneShape, 05.10): в play ставит зону 1 клетку в стороне (-61.5;-61.5),
// мажет кистью r=2 м через GridCursor.StampZone — круг, а не квадрат; стирает — центр остаётся;
// квадратики на рельефе; меш строится; зона удаляется. Сейв зоны — level_roundtrip / zone_shape в BUILD.md.
if (!Application.isPlaying) return "NOT PLAYING";
var cur = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var fEdit = T.GetField("_zoneEdit", BF); var fBrush = T.GetField("_zoneBrush", BF);
var mStamp = T.GetMethod("StampZone", BF);
var oldEdit = fEdit.GetValue(cur); var oldBrush = fBrush.GetValue(cur);
var sb = new System.Text.StringBuilder();
var relief = Cozy.Grid.ZoneShape.Relief();
var c0 = new Vector3(-61.5f, 0f, -61.5f);
float gy = relief != null ? relief.HeightAt(c0.x, c0.z) : 0f;
c0.y = gy + 0.05f;
var z = Cozy.Grid.ZonePiece.Spawn(null, new[] { c0 }, 3f, 0.1f, Cozy.Grid.ZoneKind.Technical, Color.white, "PROBE_BRUSH", "probe_brush");
bool ok = true;
try {
  int n0 = z.Shape.Count;
  fEdit.SetValue(cur, z); fBrush.SetValue(cur, 2f);
  var at = c0 + new Vector3(3f, 0f, 0f);
  bool ch = (bool)mStamp.Invoke(cur, new object[] { at, 0f, false });
  z.ShapeEdited(new System.Collections.Generic.List<Vector3>());
  int n1 = z.Shape.Count;
  bool inNear = z.Shape.Contains(at + new Vector3(1.6f, 0, 0), false);
  bool inFar = z.Shape.Contains(at + new Vector3(2.4f, 0, 0), false);
  bool inDiag = z.Shape.Contains(at + new Vector3(1.6f, 0, 1.6f), false); // 2.26 > r → вне круга
  sb.Append("paint changed=" + ch + " sq " + n0 + "→" + n1 + " near=" + inNear + " far=" + inFar + " diag=" + inDiag + " cells=" + z.Cells.Count + "\n");
  ok &= ch && n1 > n0 && inNear && !inFar && !inDiag;
  // отдельный остров не должен рисоваться в черновике, но у правки зоны — рисуется (joins); проверим стирание
  bool er = (bool)mStamp.Invoke(cur, new object[] { at, 0f, true });
  var lost = new System.Collections.Generic.List<Vector3>();
  z.ShapeEdited(lost);
  int n2 = z.Shape.Count;
  sb.Append("erase changed=" + er + " sq→" + n2 + " lost=" + lost.Count + " cells=" + z.Cells.Count + " stillCenter=" + z.Shape.Contains(c0, false) + "\n");
  ok &= er && n2 < n1 && z.Shape.Contains(c0, false);
  // рельеф: квадратики лежат на земле
  float maxDy = 0f; foreach (var s in z.Shape.Squares) if (s.ground && relief != null) { var p = z.Shape.Center(s); maxDy = Mathf.Max(maxDy, Mathf.Abs(p.y - relief.HeightAt(p.x, p.z) - 0.05f)); }
  sb.Append("ground maxDy=" + maxDy.ToString("0.000") + "\n");
  ok &= maxDy < 0.01f;
  // отрисовка
  typeof(Cozy.Grid.ZonePiece).GetMethod("BuildShown", BF).Invoke(z, null);
  var vis = z.transform.Find("Visual");
  int verts = 0; if (vis != null) foreach (var mf in vis.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh != null) verts += mf.sharedMesh.vertexCount;
  sb.Append("visual=" + (vis != null) + " verts=" + verts + "\n");
  ok &= vis != null && verts > 0;
} catch (System.Exception e) { sb.Append("EXC " + (e.InnerException ?? e).ToString().Substring(0, 400) + "\n"); ok = false; }
finally { fEdit.SetValue(cur, oldEdit); fBrush.SetValue(cur, oldBrush); cur.RemoveZone(z); }
sb.Append("left=" + Cozy.Grid.ZonePiece.All.Count + (ok ? " :: ОК" : " :: ПРОВАЛ"));
return sb.ToString();
