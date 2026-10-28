var t = typeof(Cozy.Grid.LightZones);
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static;
t.GetMethod("MarkScene", F).Invoke(null, null);
var rends = UnityEngine.Object.FindObjectsByType<UnityEngine.Renderer>(UnityEngine.FindObjectsSortMode.None);
var lines = new System.Collections.Generic.List<string>(rends.Length);
var hist = new System.Collections.Generic.SortedDictionary<uint, int>();
foreach (var r in rends) {
  var sb = new System.Text.StringBuilder(); var x = r.transform;
  while (x != null) { sb.Insert(0, "/" + x.name + "#" + x.GetSiblingIndex()); x = x.parent; }
  uint m = r.renderingLayerMask; lines.Add(sb + " " + m);
  int c; hist.TryGetValue(m, out c); hist[m] = c + 1;
}
lines.Sort(string.CompareOrdinal);
uint h = 2166136261;
foreach (var l in lines) foreach (char ch in l) { h ^= ch; h *= 16777619; }
var hs = new System.Text.StringBuilder();
foreach (var kv in hist) hs.Append(kv.Key + ":" + kv.Value + " ");
var lights = new System.Collections.Generic.List<string>();
foreach (var l in UnityEngine.Object.FindObjectsByType<UnityEngine.Light>(UnityEngine.FindObjectsSortMode.None)) { var d = l.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalLightData>(); lights.Add(l.name + ":" + l.renderingLayerMask + ":" + (d != null ? (uint)d.renderingLayers + "/" + (uint)d.shadowRenderingLayers + "/" + d.customShadowLayers : "-")); }
lights.Sort(string.CompareOrdinal);
return "renderers=" + rends.Length + " hash=" + h + " hist=" + hs + "\nlights=" + string.Join(" ", lights.ToArray());
