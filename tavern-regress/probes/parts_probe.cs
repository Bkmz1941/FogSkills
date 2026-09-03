// Части светятся только у осматриваемого хозяина (P162).
if (!Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
Cozy.Grid.InteractiveObject fridge = null, pot = null;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null) continue;
    if (fridge == null && io.Def.id == "home_fridge") fridge = io;
    if (pot == null && io.Def.id == "cooking_pot") pot = io;
}
if (fridge == null || pot == null) return "нет холодильника или кастрюли";
var T = typeof(Cozy.Grid.Interactor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var mLit = T.GetMethod("PartsLit", B);
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var open = typeof(Tavern.UI.HudUI).GetMethod("OpenExamine", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
var close = typeof(Tavern.UI.HudUI).GetMethod("CloseExamine", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
sb.Append("глобально: fridge=" + mLit.Invoke(null, new object[] { fridge }) + "\n");
open.Invoke(hud, new object[] { pot });
sb.Append("осмотр кастрюли: fridge=" + mLit.Invoke(null, new object[] { fridge }) + " pot=" + mLit.Invoke(null, new object[] { pot }) + "\n");
close.Invoke(hud, new object[] { false });
open.Invoke(hud, new object[] { fridge });
sb.Append("осмотр холодильника: fridge=" + mLit.Invoke(null, new object[] { fridge }) + " pot=" + mLit.Invoke(null, new object[] { pot }) + "\n");
close.Invoke(hud, new object[] { false });
sb.Append("после: examine=" + (Cozy.Grid.Interactor.ExamineHost != null) + "\n");
return sb.ToString();
