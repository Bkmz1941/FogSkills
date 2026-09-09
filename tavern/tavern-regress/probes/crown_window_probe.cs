// Проба просвета кроны (VIEW.md §10a): три рендера камеры — окно с каймой (ON), окно выкл (OFF)
// и жёсткий выкус до внешнего края каймы (HARD: _CrownWindow.z = rOut, кайма 1 px). Разность
// ON−OFF считается внутри круга rOut и снаружи; ПРОФИЛЬ КРАЯ — по кольцам 4 px отношение
// Σ|ON−OFF| / Σ|HARD−OFF| на пикселях листвы (|HARD−OFF| > 24): 1 в выкусе, плавно к 0 у rOut
// (P257: ступенька = большой перепад между соседними кольцами); ШОВ на rOut — перепад яркости ON
// минус тот же перепад OFF (P261). Норма: снаружи ≈ 0; внутри — тысячи; профиль на +1/4, +1/2,
// +3/4 каймы ≈ 0.84 / 0.50 / 0.16 (1 − smoothstep); maxStep ≤ 0.15; шов < 2. Плюс счёт материалов
// и кайм: листва на Tavern/CrownCut, кора на Lit; у каждой кроны копия-кайма (_CROWN_BAND, ZWrite 1,
// очередь CrownWindow.BandQueue, тот же меш, без теней), включена ⇒ окно открыто.
// Персонажа под крону ставят заранее (у ствола, на 0.9 м к камере, НЕ в тумане), после — вернуть.
var cam = UnityEngine.Camera.main; var player = Cozy.Grid.PlayerRef.GameObject;
var sb = new System.Text.StringBuilder();
int cut = 0, lit = 0, other = 0; var shaders = new System.Collections.Generic.HashSet<string>();
int bands = 0, bandsOn = 0, bandBad = 0; int queue = Cozy.Grid.CrownWindow.BandQueue;
foreach (var tw in UnityEngine.Object.FindObjectsByType<Cozy.Grid.TreeWind>(UnityEngine.FindObjectsSortMode.None))
  foreach (var r in tw.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
  {
    if (r.name == Cozy.Grid.SeeThroughView.GhostName)
    {
      bands++; if (r.enabled) bandsOn++;
      var pf = r.transform.parent.GetComponent<UnityEngine.MeshFilter>(); var bf = r.GetComponent<UnityEngine.MeshFilter>();
      if (pf == null || bf == null || bf.sharedMesh != pf.sharedMesh) bandBad++;
      if (r.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off) bandBad++;
      foreach (var m in r.sharedMaterials)
      {
        if (m == null) { bandBad++; continue; }
        if (m.renderQueue != queue) bandBad++;
        if (m.shader.name == "Tavern/CrownCut") { if (!m.IsKeywordEnabled(Cozy.Grid.CrownWindow.BandKeyword) || m.GetInt("_ZWrite") != 1) bandBad++; }
        else if (m.color.a > 0.001f) bandBad++;
      }
      continue;
    }
    foreach (var m in r.sharedMaterials) { if (m == null) continue; shaders.Add(m.shader.name); if (m.shader.name == "Tavern/CrownCut") cut++; else if (m.shader.name.Contains("Lit")) lit++; else other++; }
  }
sb.Append("mats: cut=" + cut + " lit=" + lit + " other=" + other + " shaders=[" + string.Join(",", shaders) + "] | bands=" + bands + " on=" + bandsOn + " bad=" + bandBad + " | ");
var win = UnityEngine.Shader.GetGlobalVector("_CrownWindow"); float on = UnityEngine.Shader.GetGlobalFloat("_CrownWindowOn"); float feather = UnityEngine.Shader.GetGlobalFloat("_CrownFeatherPx");
float rIn = win.z, rOut = win.z + feather;
sb.Append("window on=" + on + " center=(" + win.x.ToString("0") + "," + win.y.ToString("0") + ") rInPx=" + rIn.ToString("0") + " featherPx=" + feather.ToString("0") + " depth=" + win.w.ToString("0.0") + " screen=" + cam.pixelWidth + "x" + cam.pixelHeight + " | ");
int W = cam.pixelWidth, H = cam.pixelHeight;
System.Func<UnityEngine.Color32[]> Shot = () => { var rt = UnityEngine.RenderTexture.GetTemporary(W, H, 24); var prevT = cam.targetTexture; cam.targetTexture = rt; cam.Render(); cam.targetTexture = prevT; var tex = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGB24, false); var prevA = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt; tex.ReadPixels(new UnityEngine.Rect(0, 0, W, H), 0, 0); tex.Apply(); UnityEngine.RenderTexture.active = prevA; UnityEngine.RenderTexture.ReleaseTemporary(rt); var px = tex.GetPixels32(); UnityEngine.Object.Destroy(tex); return px; };
var a = Shot();
UnityEngine.Shader.SetGlobalFloat("_CrownWindowOn", 0f); var b = Shot();
UnityEngine.Shader.SetGlobalFloat("_CrownWindowOn", on); UnityEngine.Shader.SetGlobalVector("_CrownWindow", new UnityEngine.Vector4(win.x, win.y, rOut, win.w)); UnityEngine.Shader.SetGlobalFloat("_CrownFeatherPx", 1f); var c = Shot();
UnityEngine.Shader.SetGlobalVector("_CrownWindow", win); UnityEngine.Shader.SetGlobalFloat("_CrownFeatherPx", feather);
int inDiff = 0, outDiff = 0, inTotal = 0;
const int ringW = 4; int rings = (int)((rOut + 40f) / ringW) + 1;
var softSum = new double[rings]; var hardSum = new double[rings]; var ringN = new int[rings];
double aIn = 0, aOut = 0, bIn = 0, bOut = 0; int nIn = 0, nOut = 0;
for (int y = 0; y < H; y++) for (int x = 0; x < W; x++)
{
  int i = y * W + x; float dx = x - win.x, dy = y - win.y; float d = UnityEngine.Mathf.Sqrt(dx * dx + dy * dy);
  var p = a[i]; var q = b[i]; var h = c[i];
  int soft = System.Math.Abs(p.r - q.r) + System.Math.Abs(p.g - q.g) + System.Math.Abs(p.b - q.b);
  int hard = System.Math.Abs(h.r - q.r) + System.Math.Abs(h.g - q.g) + System.Math.Abs(h.b - q.b);
  bool inside = d < rOut; if (inside) inTotal++;
  if (soft > 24) { if (inside) inDiff++; else outDiff++; }
  int ring = (int)(d / ringW); if (ring < rings && hard > 24) { softSum[ring] += soft; hardSum[ring] += hard; ringN[ring]++; }
  if (d >= rOut - 3f && d < rOut) { aIn += p.r + p.g + p.b; bIn += q.r + q.g + q.b; nIn++; }
  else if (d >= rOut && d < rOut + 3f) { aOut += p.r + p.g + p.b; bOut += q.r + q.g + q.b; nOut++; }
}
var ratio = new double[rings]; for (int k = 0; k < rings; k++) ratio[k] = hardSum[k] > 0 ? softSum[k] / hardSum[k] : -1;
double maxStep = 0; int stepAt = -1; for (int k = 0; k + 1 < rings; k++) { if (ringN[k] < 50 || ringN[k + 1] < 50) continue; double st = System.Math.Abs(ratio[k] - ratio[k + 1]); if (st > maxStep) { maxStep = st; stepAt = k; } }
System.Func<float, string> At = d => { int k = (int)(d / ringW); return k < rings && ringN[k] >= 50 ? ratio[k].ToString("0.00") : "-"; };
double seam = nIn > 0 && nOut > 0 ? System.Math.Abs((aIn / nIn - aOut / nOut) - (bIn / nIn - bOut / nOut)) / 3.0 : -1;
int leafPx = 0; for (int k = 0; k < rings; k++) leafPx += ringN[k];
sb.Append("pixels: inside " + inTotal + ", changed inside=" + inDiff + " outside=" + outDiff + ", leaf px in rings=" + leafPx + " | ");
sb.Append("profile (soft/hard): 0.5rIn=" + At(rIn * 0.5f) + " rIn=" + At(rIn) + " +1/4=" + At(rIn + feather * 0.25f) + " +1/2=" + At(rIn + feather * 0.5f) + " +3/4=" + At(rIn + feather * 0.75f) + " rOut-4=" + At(rOut - 4f) + " rOut+8=" + At(rOut + 8f));
sb.Append(" | maxStep=" + maxStep.ToString("0.00") + " at d=" + (stepAt * ringW) + "px | seam=" + seam.ToString("0.0"));
return sb.ToString();
