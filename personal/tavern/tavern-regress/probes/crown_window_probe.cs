// Проба просвета кроны (VIEW.md §10a): три рендера камеры — окно с каймой (ON), окно выкл (OFF)
// и жёсткий выкус до внешнего края каймы (HARD: _CrownWindow.z = rOut, кайма 1 px). Разность
// ON−OFF считается внутри круга rOut и снаружи; ПРОФИЛЬ КРАЯ — по кольцам 4 px отношение
// Σ|ON−OFF| / Σ|HARD−OFF| на пикселях листвы (|HARD−OFF| > 24): 1 в выкусе, плавно к 0 у rOut
// (P257: ступенька = большой перепад между соседними кольцами); ШОВ на rOut — перепад яркости ON
// минус тот же перепад OFF (P261). Норма: снаружи ≈ 0; внутри — тысячи; профиль на +1/4, +1/2,
// +3/4 каймы ≈ 0.57 / 0.10 / 0.00 (1 − покрытие, 3 слоя, ядро 0.95), у границы 0; maxStep ≤ 0.15; шов < 2. Плюс счёт материалов
// и кайм: листва на Tavern/CrownCut, кора на Lit; у каждой кроны копия-кайма (_CROWN_BAND, ZWrite 1,
// очередь CrownWindow.BandQueue, тот же меш, без теней, БЕЗ записи глубины), включена ⇒ окно открыто;
// маска каймы _CrownBandTex (R = 1 − альфа, G = глубина; пусто = 1, 1e4; пишется BlendOp Min) рисуется в beginCameraRendering: пиксели маски лежат
// в кольце rIn..rOut вокруг центра окна (центроид ≈ центр, d в [rIn, rOut]), meanZ < глубины груди.
// Персонажа под крону ставят заранее (у ствола, на 0.9 м к камере), после — вернуть.
// С 11.09 туман окно не закрывает, поэтому клетка тумана замеру больше не мешает.
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
        if (m.shader.name == "Tavern/CrownCut") { if (!m.IsKeywordEnabled(Cozy.Grid.CrownWindow.BandKeyword) || m.GetInt("_ZWrite") != 0) bandBad++; }
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
var maskRt = UnityEngine.Shader.GetGlobalTexture("_CrownBandTex") as UnityEngine.RenderTexture; float maskOn = UnityEngine.Shader.GetGlobalFloat("_CrownBandOn");
if (maskRt != null)
{
  var mt = new UnityEngine.Texture2D(maskRt.width, maskRt.height, UnityEngine.TextureFormat.RGBAHalf, false); var prevM = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = maskRt; mt.ReadPixels(new UnityEngine.Rect(0, 0, maskRt.width, maskRt.height), 0, 0); mt.Apply(); UnityEngine.RenderTexture.active = prevM;
  var mp = mt.GetPixels(); UnityEngine.Object.Destroy(mt);
  int mw = maskRt.width, mh = maskRt.height; long n = 0; double cx = 0, cy = 0; float dMin = 1e9f, dMax = 0; double zSum = 0;
  for (int y = 0; y < mh; y++) for (int x = 0; x < mw; x++) { var mc = mp[y * mw + x]; if (mc.r >= 0.999f) continue; n++; cx += x; cy += y; zSum += mc.g; float dx = x - win.x, dy = y - win.y; float d = UnityEngine.Mathf.Sqrt(dx * dx + dy * dy); if (d < dMin) dMin = d; if (d > dMax) dMax = d; }
  sb.Append("mask: on=" + maskOn + " size=" + mw + "x" + mh + " px=" + n + (n > 0 ? " centroid=(" + (cx / n).ToString("0") + "," + (cy / n).ToString("0") + ") d=[" + dMin.ToString("0") + ".." + dMax.ToString("0") + "] meanZ=" + (zSum / n).ToString("0.0") : "") + " flip=" + Cozy.Grid.CrownWindow.MaskFlip + " | ");
}
else sb.Append("mask: none (on=" + maskOn + ") | ");
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
// ОБРЫВКИ ЛИСТВЫ В ОКНЕ (P334): глубина среза — грудь ПЛЮС внешний радиус окна (CrownWindow.Outer),
// а не плоскость груди. Проба обходит каждое дерево с crownWindow и сажает воображаемого игрока по
// кольцам 0.3 м вокруг ствола (24 кольца × 36 направлений, камера — текущий отступ от игрока):
// ни одна ПЕРЕДНЯЯ грань листвы, попавшая в круг окна, не должна быть глубже среза. Норма: 0.
// Вторым числом печатается срез по груди (как было до 11.09) — на нём остаются сотни позиций,
// в каждой обрывок силуэта кроны в 3–5 треугольников, та самая «тонкая линия».
{
  var lo = cam.transform.position - player.transform.position; var lf = cam.transform.forward;
  float lSlack = Cozy.Grid.CrownWindow.Outer, lChest = Cozy.Grid.CrownWindow.ChestHeight;
  int lPos = 0, lFlat = 0, lNow = 0; float lWorst = -999f; string lWhere = "";
  foreach (var lio in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
  {
    if (lio.Def == null || !lio.Def.crownWindow) continue;
    UnityEngine.Transform lc = null; foreach (var tr in lio.GetComponentsInChildren<UnityEngine.Transform>(true)) if (tr.name == lio.Def.crownNode) lc = tr;
    var lmf = lc == null ? null : lc.GetComponent<UnityEngine.MeshFilter>(); var lrend = lc == null ? null : lc.GetComponent<UnityEngine.MeshRenderer>();
    if (lmf == null || lmf.sharedMesh == null || lrend == null) continue;
    var lmesh = lmf.sharedMesh; var lv = lmesh.vertices; var lmats = lrend.sharedMaterials; var ltp = lio.transform.position;
    for (int ring = 1; ring <= 24; ring++) for (int aa = 0; aa < 36; aa++)
    {
      float lrad = ring * 0.3f, lang = aa * UnityEngine.Mathf.PI * 2f / 36f;
      var lpp = new UnityEngine.Vector3(ltp.x + UnityEngine.Mathf.Cos(lang) * lrad, ltp.y, ltp.z + UnityEngine.Mathf.Sin(lang) * lrad);
      var lch = lpp + UnityEngine.Vector3.up * lChest; var lcam = lpp + lo;
      float lDepth = UnityEngine.Vector3.Dot(lch - lcam, lf); float lAng = UnityEngine.Mathf.Atan2(lSlack, lDepth) * UnityEngine.Mathf.Rad2Deg;
      lPos++; float lOver = -999f;
      for (int s = 0; s < lmesh.subMeshCount; s++)
      {
        if (s >= lmats.Length || lmats[s] == null || lmats[s].shader.name != "Tavern/CrownCut") continue;
        var lt = lmesh.GetTriangles(s);
        for (int i = 0; i < lt.Length; i += 3)
        {
          var w0 = lc.TransformPoint(lv[lt[i]]); var w1 = lc.TransformPoint(lv[lt[i + 1]]); var w2 = lc.TransformPoint(lv[lt[i + 2]]);
          var ctr = (w0 + w1 + w2) / 3f;
          if (UnityEngine.Vector3.Dot(UnityEngine.Vector3.Cross(w1 - w0, w2 - w0), ctr - lcam) > 0f) continue;
          if (UnityEngine.Vector3.Angle(ctr - lcam, lch - lcam) > lAng) continue;
          float dm = UnityEngine.Mathf.Max(UnityEngine.Vector3.Dot(w0 - lcam, lf), UnityEngine.Mathf.Max(UnityEngine.Vector3.Dot(w1 - lcam, lf), UnityEngine.Vector3.Dot(w2 - lcam, lf)));
          if (dm - lDepth > lOver) lOver = dm - lDepth;
        }
      }
      if (lOver > 0f) lFlat++;
      if (lOver > lSlack) { lNow++; if (lOver - lSlack > lWorst) { lWorst = lOver - lSlack; lWhere = lio.name + " " + lpp.ToString("F1"); } }
    }
  }
  sb.Append(" | leftovers: позиций " + lPos + ", срез по груди " + lFlat + ", срез +" + lSlack.ToString("0.0") + " м " + lNow + (lNow > 0 ? (" худший +" + lWorst.ToString("0.00") + " м " + lWhere) : ""));
}
return sb.ToString();
