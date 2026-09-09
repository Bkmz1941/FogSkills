// Проба «дождь в доме» (P281): три рендера камеры в одном кадре и разность светлых
// пикселей внутри спроецированных клеток дома: A — как есть, B — срез _RainRoof выключен
// (старое поведение), C — только дворовые столбы, D — только столбы над домом.
// B−A = что снимает срез по крыше клетки (течь сквозь стены); C = дождь ПЕРЕД домом,
// спроецированный наклонной камерой на открытый интерьер, — это не течь.
// Перед запуском: игрок снаружи у наветренной стены (P281: точка -18,0,-21 на Test #1),
// ночь (SetHours 23), Weather.Rain = true, дать 3 с столбам родиться.
// Запуск: python3 ~/.claude/skills/tavern-game/mcp_call.py execute_code "$(python3 -c 'import json,sys;print(json.dumps({"action":"execute","code":open(sys.argv[1]).read()}))' rain_house_probe.cs)"
var cam = UnityEngine.Camera.main;
var pp = Cozy.View.ViewState.PlayerPos; float floorY = Cozy.View.ViewState.CurrentFloorY;
var ground = Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Ground) ?? Cozy.Grid.GridManager.FindByRole(Cozy.Grid.GridRole.Floor);
float cs = ground.CellSize; var origin = ground.Origin;
int cx = UnityEngine.Mathf.RoundToInt((pp.x - origin.x) / cs), cz = UnityEngine.Mathf.RoundToInt((pp.z - origin.z) / cs);
int W = cam.pixelWidth, H = cam.pixelHeight;
var rects = new System.Collections.Generic.List<UnityEngine.RectInt>();
for (int dx = -3; dx <= 3; dx++) for (int dz = -3; dz <= 3; dz++)
{
  var c = new UnityEngine.Vector3(origin.x + (cx + dx) * cs, floorY, origin.z + (cz + dz) * cs);
  if (!Cozy.Grid.WindGusts.Indoors(c + UnityEngine.Vector3.up * 0.1f)) continue;
  float minx = 1e9f, maxx = -1e9f, miny = 1e9f, maxy = -1e9f; bool ok = true;
  for (int k = 0; k < 4; k++) { var corner = c + new UnityEngine.Vector3((k % 2 == 0 ? -1 : 1) * cs * 0.35f, 0.05f, (k < 2 ? -1 : 1) * cs * 0.35f); var sp = cam.WorldToScreenPoint(corner); if (sp.z <= 0) { ok = false; break; } minx = UnityEngine.Mathf.Min(minx, sp.x); maxx = UnityEngine.Mathf.Max(maxx, sp.x); miny = UnityEngine.Mathf.Min(miny, sp.y); maxy = UnityEngine.Mathf.Max(maxy, sp.y); }
  if (!ok) continue;
  int x0 = UnityEngine.Mathf.Clamp((int)minx, 0, W - 1), x1 = UnityEngine.Mathf.Clamp((int)maxx, 0, W - 1), y0 = UnityEngine.Mathf.Clamp((int)miny, 0, H - 1), y1 = UnityEngine.Mathf.Clamp((int)maxy, 0, H - 1);
  if (x1 - x0 < 8 || y1 - y0 < 8) continue;
  rects.Add(new UnityEngine.RectInt(x0, y0, x1 - x0, y1 - y0));
}
System.Func<int> InHouse = () => { var rt = UnityEngine.RenderTexture.GetTemporary(W, H, 24); var prevT = cam.targetTexture; cam.targetTexture = rt; cam.Render(); cam.targetTexture = prevT; var tex = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGB24, false); var prevA = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt; tex.ReadPixels(new UnityEngine.Rect(0, 0, W, H), 0, 0); tex.Apply(); UnityEngine.RenderTexture.active = prevA; UnityEngine.RenderTexture.ReleaseTemporary(rt); var px = tex.GetPixels32(); UnityEngine.Object.Destroy(tex); int n = 0; foreach (var r in rects) for (int y = r.yMin; y < r.yMax; y++) for (int x = r.xMin; x < r.xMax; x++) { var p = px[y * W + x]; if (System.Math.Max(p.r, System.Math.Max(p.g, p.b)) > 90) n++; } return n; };
var roofsF = typeof(Cozy.Grid.RainDrops).GetField("_roofs", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var roofs = (float[])roofsF.GetValue(null);
var all = new System.Collections.Generic.List<UnityEngine.MeshRenderer>(); var house = new System.Collections.Generic.List<UnityEngine.MeshRenderer>(); var yard = new System.Collections.Generic.List<UnityEngine.MeshRenderer>();
foreach (var rd in UnityEngine.Object.FindObjectsByType<Cozy.Grid.RainDrops>(UnityEngine.FindObjectsSortMode.None)) foreach (var mr in rd.GetComponentsInChildren<UnityEngine.MeshRenderer>(true)) { if (!mr.enabled || mr.name != "RainCell") continue; all.Add(mr); var cell = mr.transform.position - Cozy.Grid.RainDrops.Slide; if (cell.y > floorY + 0.01f) house.Add(mr); else yard.Add(mr); }
int A = InHouse();
var minus = new float[49]; for (int i = 0; i < 49; i++) minus[i] = -100f; UnityEngine.Shader.SetGlobalFloatArray("_RainRoof", minus);
int B = InHouse();
UnityEngine.Shader.SetGlobalFloatArray("_RainRoof", roofs);
foreach (var mr in house) mr.enabled = false; int C = InHouse(); foreach (var mr in house) mr.enabled = true;
foreach (var mr in yard) mr.enabled = false; int D = InHouse(); foreach (var mr in yard) mr.enabled = true;
foreach (var mr in all) mr.enabled = false; int Z = InHouse(); foreach (var mr in all) mr.enabled = true;
return "rects=" + rects.Count + " columns: yard=" + yard.Count + " raisedOverHouse=" + house.Count + " | in-house bright px minus no-rain: A(clip on)=" + (A - Z) + " B(clip off, old)=" + (B - Z) + " C(only yard columns, clip on)=" + (C - Z) + " D(only raised columns, clip on)=" + (D - Z) + " | leak removed by clip = " + (B - A);
