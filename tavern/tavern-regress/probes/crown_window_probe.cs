// Проба просвета кроны (VIEW.md §10a): два рендера камеры — окно вкл и выкл (_CrownWindowOn),
// разность пикселей внутри экранного круга и снаружи. Норма: снаружи ≈ 0; под кроной внутри — тысячи;
// без крон над персонажем — 0/0. Плюс счёт материалов: листва на Tavern/CrownCut, кора на Lit.
// Персонажа под крону ставят заранее (у ствола, на 0.9 м к камере), после — вернуть позицию.
var cam = UnityEngine.Camera.main; var player = Cozy.Grid.PlayerRef.GameObject;
var sb = new System.Text.StringBuilder();
int cut = 0, lit = 0, other = 0; var shaders = new System.Collections.Generic.HashSet<string>();
foreach (var tw in UnityEngine.Object.FindObjectsByType<Cozy.Grid.TreeWind>(UnityEngine.FindObjectsSortMode.None))
  foreach (var r in tw.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
    foreach (var m in r.sharedMaterials) { if (m == null) continue; shaders.Add(m.shader.name); if (m.shader.name == "Tavern/CrownCut") cut++; else if (m.shader.name.Contains("Lit")) lit++; else other++; }
sb.Append("mats: cut=" + cut + " lit=" + lit + " other=" + other + " shaders=[" + string.Join(",", shaders) + "] | ");
var win = UnityEngine.Shader.GetGlobalVector("_CrownWindow"); float on = UnityEngine.Shader.GetGlobalFloat("_CrownWindowOn");
sb.Append("window on=" + on + " center=(" + win.x.ToString("0") + "," + win.y.ToString("0") + ") rPx=" + win.z.ToString("0") + " depth=" + win.w.ToString("0.0") + " screen=" + cam.pixelWidth + "x" + cam.pixelHeight + " | ");
int W = cam.pixelWidth, H = cam.pixelHeight;
System.Func<UnityEngine.Color32[]> Shot = () => { var rt = UnityEngine.RenderTexture.GetTemporary(W, H, 24); var prevT = cam.targetTexture; cam.targetTexture = rt; cam.Render(); cam.targetTexture = prevT; var tex = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGB24, false); var prevA = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt; tex.ReadPixels(new UnityEngine.Rect(0, 0, W, H), 0, 0); tex.Apply(); UnityEngine.RenderTexture.active = prevA; UnityEngine.RenderTexture.ReleaseTemporary(rt); var px = tex.GetPixels32(); UnityEngine.Object.Destroy(tex); return px; };
var a = Shot();
UnityEngine.Shader.SetGlobalFloat("_CrownWindowOn", 0f); var b = Shot(); UnityEngine.Shader.SetGlobalFloat("_CrownWindowOn", on);
int inDiff = 0, outDiff = 0, inTotal = 0;
for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) { int i = y * W + x; float dx = x - win.x, dy = y - win.y; bool inside = dx * dx + dy * dy < win.z * win.z; if (inside) inTotal++; var p = a[i]; var q = b[i]; bool diff = System.Math.Abs(p.r - q.r) + System.Math.Abs(p.g - q.g) + System.Math.Abs(p.b - q.b) > 24; if (diff) { if (inside) inDiff++; else outDiff++; } }
sb.Append("pixels: inside disk " + inTotal + ", changed by window inside=" + inDiff + " outside=" + outDiff);
return sb.ToString();
