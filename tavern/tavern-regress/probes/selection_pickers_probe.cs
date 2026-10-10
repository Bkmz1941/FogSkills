// Отпечаток четырёх всплывающих панелей выбора в карточке выделения (рисунок, вид,
// расцветка, цвет): геометрия панели и сетки, число ячеек. Панели строятся лениво,
// поэтому проба подставляет синтетический набор (три рисунка, три расцветки, семь
// видов), зовёт Build*Picker отражением, печатает отпечаток и всё сносит, вернув
// поля как были. Сверка ДО/ПОСЛЕ посимвольно — защита рефакторинга HudUI.Selection
// (T-UI-ДУБЛИ: PickerPanel ×4). Уровень любой: карточка выделения не нужна.
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "КРАСНОЕ: нет HudUI";
var t = typeof(Tavern.UI.HudUI);
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var fTex = t.GetField("_patternTex", bf); var fSw = t.GetField("_paletteSwatches", bf); var fLook = t.GetField("_lookCount", bf);
var fP = t.GetField("_patternPicker", bf); var fL = t.GetField("_lookPicker", bf); var fPa = t.GetField("_palettePicker", bf); var fC = t.GetField("_colorPicker", bf);
if (fTex == null || fSw == null || fLook == null || fP == null || fL == null || fPa == null || fC == null) return "КРАСНОЕ: поля панелей выбора не найдены";
var builders = new string[] { "BuildPatternPicker", "BuildLookPicker", "BuildPalettePicker", "BuildColorPicker" };
var fields = new System.Reflection.FieldInfo[] { fP, fL, fPa, fC };
object wasTex = fTex.GetValue(hud); object wasSw = fSw.GetValue(hud); object wasLook = fLook.GetValue(hud);
var wasPanels = new object[4];
for (int i = 0; i < 4; i++) wasPanels[i] = fields[i].GetValue(hud);
var sb = new System.Text.StringBuilder();
try
{
    fTex.SetValue(hud, new string[] { "Probe/a", "Probe/b", "Probe/c" });
    fSw.SetValue(hud, new UnityEngine.Color[] { UnityEngine.Color.red, UnityEngine.Color.green, UnityEngine.Color.blue });
    fLook.SetValue(hud, 7);
    for (int i = 0; i < 4; i++)
    {
        fields[i].SetValue(hud, null);
        var m = t.GetMethod(builders[i], bf);
        if (m == null) { sb.Append(builders[i]).Append(": нет метода\n"); continue; }
        m.Invoke(hud, null);
        var go = fields[i].GetValue(hud) as UnityEngine.GameObject;
        if (go == null) { sb.Append(builders[i]).Append(": панель не построена\n"); continue; }
        var rt = go.GetComponent<UnityEngine.RectTransform>();
        var grid = go.GetComponent<UnityEngine.UI.GridLayoutGroup>();
        var img = go.GetComponent<UnityEngine.UI.Image>();
        sb.Append(go.name).Append(" active=").Append(go.activeSelf)
          .Append(" anchors=").Append(rt.anchorMin.ToString("0.00")).Append(rt.anchorMax.ToString("0.00")).Append(" pivot=").Append(rt.pivot.ToString("0.00"))
          .Append(" pos=").Append(rt.anchoredPosition.ToString("0.0")).Append(" size=").Append(rt.sizeDelta.ToString("0.0"))
          .Append(" color=").Append(img != null ? UnityEngine.ColorUtility.ToHtmlStringRGBA(img.color) : "-");
        if (grid != null) sb.Append(" cell=").Append(grid.cellSize.ToString("0.0")).Append(" gap=").Append(grid.spacing.ToString("0.0"))
          .Append(" pad=").Append(grid.padding.left).Append("/").Append(grid.padding.right).Append("/").Append(grid.padding.top).Append("/").Append(grid.padding.bottom)
          .Append(" cols=").Append(grid.constraint).Append(":").Append(grid.constraintCount);
        sb.Append(" cells=").Append(go.transform.childCount);
        for (int c = 0; c < go.transform.childCount; c++)
        {
            var ch = go.transform.GetChild(c);
            var crt = ch as UnityEngine.RectTransform;
            var cimg = ch.GetComponent<UnityEngine.UI.Image>();
            var ctext = ch.GetComponentInChildren<TMPro.TMP_Text>(true);
            sb.Append(" [").Append(ch.name).Append(" ").Append(crt != null ? crt.sizeDelta.ToString("0") : "-").Append(" ").Append(cimg != null ? UnityEngine.ColorUtility.ToHtmlStringRGBA(cimg.color) : "-").Append(" ").Append(ctext != null ? ctext.text : "").Append("]");
        }
        sb.Append('\n');
    }
}
finally
{
    for (int i = 0; i < 4; i++)
    {
        var built = fields[i].GetValue(hud) as UnityEngine.GameObject;
        if (built != null && !ReferenceEquals(built, wasPanels[i])) UnityEngine.Object.Destroy(built);
        fields[i].SetValue(hud, wasPanels[i]);
    }
    fTex.SetValue(hud, wasTex); fSw.SetValue(hud, wasSw); fLook.SetValue(hud, wasLook);
}
return sb.ToString();
