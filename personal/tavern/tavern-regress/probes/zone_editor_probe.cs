// Отпечаток окна «редактор зоны» (HudUI.OpenZoneEditor): дерево UI окна для первой
// зоны существ уровня (нет — любой зоны): имя, компоненты, текст, размер каждого узла.
// Открывает окно отражением, печатает и закрывает. Сверка ДО/ПОСЛЕ посимвольно —
// защита рефакторинга OpenZoneEditor (T-PLAN-0510 №11). Нужна хотя бы одна зона.
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "КРАСНОЕ: нет HudUI";
Cozy.Grid.ZonePiece zone = null;
foreach (var z in Cozy.Grid.ZonePiece.All) { if (z != null && Cozy.Grid.ZonePiece.IsCreatures(z.kind)) { zone = z; break; } }
if (zone == null) foreach (var z in Cozy.Grid.ZonePiece.All) { if (z != null) { zone = z; break; } }
if (zone == null) return "НЕЧЕГО ПРОВЕРЯТЬ: зон на уровне нет";
var t = typeof(Tavern.UI.HudUI);
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var fZone = t.GetField("_selectedZone", bf); var fEditor = t.GetField("_zoneEditor", bf);
var mOpen = t.GetMethod("OpenZoneEditor", bf); var mClose = t.GetMethod("CloseZoneEditor", bf);
if (fZone == null || fEditor == null || mOpen == null || mClose == null) return "КРАСНОЕ: нет полей/методов редактора зоны";
object wasZone = fZone.GetValue(hud);
var sb = new System.Text.StringBuilder();
sb.Append("zone=").Append(zone.DisplaySlug).Append(" kind=").Append(zone.kind).Append('\n');
try
{
    fZone.SetValue(hud, zone);
    mOpen.Invoke(hud, null);
    var editor = fEditor.GetValue(hud) as UnityEngine.GameObject;
    if (editor == null) return "КРАСНОЕ: окно не открылось";
    System.Action<UnityEngine.Transform, int> dump = null;
    dump = (tr, depth) =>
    {
        var rt = tr as UnityEngine.RectTransform;
        var text = tr.GetComponent<TMPro.TMP_Text>();
        var input = tr.GetComponent<TMPro.TMP_InputField>();
        var img = tr.GetComponent<UnityEngine.UI.Image>();
        var kinds = new System.Collections.Generic.List<string>();
        foreach (var c in tr.GetComponents<UnityEngine.Component>()) { if (c != null && !(c is UnityEngine.Transform) && !(c is UnityEngine.CanvasRenderer)) kinds.Add(c.GetType().Name); }
        sb.Append(new string(' ', depth * 2)).Append(tr.name).Append(" [").Append(string.Join(",", kinds.ToArray())).Append("]");
        if (rt != null) sb.Append(" size=").Append(rt.sizeDelta.ToString("0")).Append(" a=").Append(rt.anchorMin.ToString("0.0")).Append(rt.anchorMax.ToString("0.0"));
        if (img != null) sb.Append(" color=").Append(UnityEngine.ColorUtility.ToHtmlStringRGBA(img.color));
        if (text != null) sb.Append(" text=«").Append(text.text.Replace("\n", "⏎")).Append("»");
        if (input != null) sb.Append(" input=«").Append(input.text.Replace("\n", "⏎")).Append("» type=").Append(input.contentType);
        sb.Append(tr.gameObject.activeSelf ? "" : " (off)").Append('\n');
        for (int i = 0; i < tr.childCount; i++) dump(tr.GetChild(i), depth + 1);
    };
    dump(editor.transform, 0);
}
finally
{
    mClose.Invoke(hud, null);
    fZone.SetValue(hud, wasZone);
}
return sb.ToString();
