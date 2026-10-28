if (!UnityEngine.Application.isPlaying) return "не в play";
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var ti = typeof(Cozy.Grid.CrowIdle);
Cozy.Grid.CrowIdle c = null;
foreach (var x in UnityEngine.Object.FindObjectsByType<Cozy.Grid.CrowIdle>(UnityEngine.FindObjectsSortMode.None))
    if (x.GetComponent<Cozy.Grid.CrowFlight>() != null && ti.GetField("_eyeRend", BF).GetValue(x) != null) { c = x; break; }
if (c == null) return "НЕ ПРОВЕРЕНО: в уровне нет вороны с глазами";
var er = ti.GetField("_eyeRend", BF).GetValue(c) as UnityEngine.Renderer;
var glow = ti.GetField("_glowEyes", BF).GetValue(c) as System.Collections.Generic.List<UnityEngine.Renderer>;
var key = "crow_glow_probe_state";
var state = System.AppDomain.CurrentDomain.GetData(key) as object[];
if (state == null)
{
    bool wasRed = (bool)ti.GetField("_forceRed", BF).GetValue(c);
    c.ForceRedEyes(true);
    bool lit = glow.Count > 0 && glow[0].enabled;
    System.AppDomain.CurrentDomain.SetData(key, new object[] { wasRed, er.shadowCastingMode, c.enabled, lit });
    c.enabled = false;
    er.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly;
    return "ПОДГОТОВКА: красные глаза включены, покой выключен как в полёте, голова спрятана гейтом — запусти ещё раз";
}
System.AppDomain.CurrentDomain.SetData(key, null);
bool litBefore = (bool)state[3];
bool stillLit = false;
foreach (var g in glow) if (g != null && g.enabled) stillLit = true;
er.shadowCastingMode = (UnityEngine.Rendering.ShadowCastingMode)state[1];
c.enabled = (bool)state[2];
c.ForceRedEyes((bool)state[0]);
if (!litBefore) return "КРАСНОЕ: красные глаза не зажглись на видимой вороне";
return stillLit ? "КРАСНОЕ: глаза вороны светятся, когда голова спрятана в полёте (P849)" : "глаза вороны (P849): голова спрятана в полёте — свечение погасло, ок";
