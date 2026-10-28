// Проба «дождь в доме» (WEATHER.md «Дождь над домом»): два рендера камеры — дождь есть / нет —
// и разность пикселей внутри ТОЧНОГО четырёхугольника каждой крытой клетки в кадре.
// A — как есть; B — старое поведение (срез и гейт выключены); C — только дворовые столбы;
// E — всё срезано (шум пола, норма 0). Под крышей норма A = 0; снаружи A > 0 — дождь поверх
// зданий. ⚠️ Мерить на НЕСКОЛЬКИХ ракурсах: CameraFollow.yaw 70/160/250/340, в ViewState.Debug
// ещё pitch 65/75 и distance 14/18 — на 70°/50° проекции почти нет, на 160°/250° тысячи px.
// Перед запуском: дождь вкл, игрок на месте (под крышей или во дворе), 2–3 с на столбы.
var cam = UnityEngine.Camera.main;
var pp = Cozy.View.ViewState.PlayerPos; float floorY = Cozy.View.ViewState.CurrentFloorY;
var ground = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground) ?? Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Floor);
float cs = ground.CellSize; var origin = ground.Origin;
int cx = UnityEngine.Mathf.RoundToInt((pp.x - origin.x) / cs), cz = UnityEngine.Mathf.RoundToInt((pp.z - origin.z) / cs);
int W = cam.pixelWidth, H = cam.pixelHeight;
var rects = new System.Collections.Generic.List<UnityEngine.RectInt>(); var quads = new System.Collections.Generic.List<UnityEngine.Vector2[]>();
for (int dx = -3; dx <= 3; dx++) for (int dz = -3; dz <= 3; dz++)
{
  var c = new UnityEngine.Vector3(origin.x + (cx + dx) * cs, floorY, origin.z + (cz + dz) * cs);
  if (!Cozy.Grid.WindGusts.Indoors(c + UnityEngine.Vector3.up * 0.1f)) continue;
  float minx = 1e9f, maxx = -1e9f, miny = 1e9f, maxy = -1e9f; bool ok = true; var q = new UnityEngine.Vector2[4]; int[] ox = { -1, 1, 1, -1 }; int[] oz = { -1, -1, 1, 1 };
  for (int k = 0; k < 4; k++) { var corner = c + new UnityEngine.Vector3(ox[k] * cs * 0.35f, 0.05f, oz[k] * cs * 0.35f); var sp = cam.WorldToScreenPoint(corner); if (sp.z <= 0) { ok = false; break; } q[k] = new UnityEngine.Vector2(sp.x, sp.y); minx = UnityEngine.Mathf.Min(minx, sp.x); maxx = UnityEngine.Mathf.Max(maxx, sp.x); miny = UnityEngine.Mathf.Min(miny, sp.y); maxy = UnityEngine.Mathf.Max(maxy, sp.y); }
  if (!ok) continue;
  int x0 = UnityEngine.Mathf.Clamp((int)minx, 0, W - 1), x1 = UnityEngine.Mathf.Clamp((int)maxx, 0, W - 1), y0 = UnityEngine.Mathf.Clamp((int)miny, 0, H - 1), y1 = UnityEngine.Mathf.Clamp((int)maxy, 0, H - 1);
  if (x1 - x0 < 8 || y1 - y0 < 8) continue;
  rects.Add(new UnityEngine.RectInt(x0, y0, x1 - x0, y1 - y0)); quads.Add(q);
}
System.Func<UnityEngine.Color32[]> Shot = () => { var rt = UnityEngine.RenderTexture.GetTemporary(W, H, 24); var prevT = cam.targetTexture; cam.targetTexture = rt; cam.Render(); cam.targetTexture = prevT; var tex = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGB24, false); var prevA = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt; tex.ReadPixels(new UnityEngine.Rect(0, 0, W, H), 0, 0); tex.Apply(); UnityEngine.RenderTexture.active = prevA; UnityEngine.RenderTexture.ReleaseTemporary(rt); var px = tex.GetPixels32(); UnityEngine.Object.Destroy(tex); return px; };
System.Func<UnityEngine.Vector2[], float, float, bool> Inside = (qq, px, py) => { bool pos = false, neg = false; for (int k = 0; k < 4; k++) { var a1 = qq[k]; var b1 = qq[(k + 1) % 4]; float cr = (b1.x - a1.x) * (py - a1.y) - (b1.y - a1.y) * (px - a1.x); if (cr > 0) pos = true; if (cr < 0) neg = true; } return !(pos && neg); };
System.Func<UnityEngine.Color32[], UnityEngine.Color32[], int> DiffIn = (a, b) => { int n = 0; for (int ri = 0; ri < rects.Count; ri++) { var r = rects[ri]; var qq = quads[ri]; for (int y = r.yMin; y < r.yMax; y++) for (int x = r.xMin; x < r.xMax; x++) { if (!Inside(qq, x, y)) continue; int i = y * W + x; if (System.Math.Abs(a[i].r - b[i].r) + System.Math.Abs(a[i].g - b[i].g) + System.Math.Abs(a[i].b - b[i].b) > 12) n++; } } return n; };
var all = new System.Collections.Generic.List<UnityEngine.MeshRenderer>(); var house = new System.Collections.Generic.List<UnityEngine.MeshRenderer>(); var yard = new System.Collections.Generic.List<UnityEngine.MeshRenderer>();
foreach (var rd in UnityEngine.Object.FindObjectsByType<Cozy.Grid.RainDrops>(UnityEngine.FindObjectsSortMode.None)) foreach (var mr in rd.GetComponentsInChildren<UnityEngine.MeshRenderer>(true)) { if (!mr.enabled || mr.name != "RainCell") continue; all.Add(mr); var cell = mr.transform.position - Cozy.Grid.RainDrops.Slide; if (cell.y > floorY + 0.01f) house.Add(mr); else yard.Add(mr); }
foreach (var mr in all) mr.enabled = false; var Z = Shot(); foreach (var mr in all) mr.enabled = true;
var A = Shot();
var winSave = UnityEngine.Shader.GetGlobalVector("_RainWindow"); var roofsSave = UnityEngine.Shader.GetGlobalFloatArray("_RainRoof"); var minus = new float[49]; for (int i = 0; i < 49; i++) minus[i] = -100f;
UnityEngine.Shader.SetGlobalFloatArray("_RainRoof", minus); UnityEngine.Shader.SetGlobalVector("_RainWindow", new UnityEngine.Vector4(winSave.x, winSave.y, winSave.z, 0f));
var B = Shot();
UnityEngine.Shader.SetGlobalFloatArray("_RainRoof", roofsSave); UnityEngine.Shader.SetGlobalVector("_RainWindow", winSave);
foreach (var mr in house) mr.enabled = false; var C = Shot(); foreach (var mr in house) mr.enabled = true;
var plus = new float[49]; for (int i = 0; i < 49; i++) plus[i] = 100f; UnityEngine.Shader.SetGlobalFloatArray("_RainRoof", plus); var E = Shot(); UnityEngine.Shader.SetGlobalFloatArray("_RainRoof", roofsSave);
return "rects=" + rects.Count + " columns: yard=" + yard.Count + " raisedOverHouse=" + house.Count + " underRoofGate=" + winSave.w + " | rain px in house (diff vs no rain): A(new)=" + DiffIn(A, Z) + " B(old: no clip, no gate)=" + DiffIn(B, Z) + " C(only yard, new)=" + DiffIn(C, Z) + " E(all clipped, noise floor)=" + DiffIn(E, Z);
