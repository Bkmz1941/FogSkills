if (!UnityEngine.Application.isPlaying) return "NOT PLAYING";
var ui = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.CharacterScreenUI>();
if (ui == null) return "no CharacterScreenUI";
var look = Tavern.UI.CharacterScreenUI.Look.Vitals;
float corner0 = look.Corner;
var sb = new System.Text.StringBuilder();
try
{
    foreach (float corner in new[] { 0f, 20f })
    {
        look.Corner = corner;
        ui.Close();
        ui.Open();
        UnityEngine.Canvas.ForceUpdateCanvases();
        var left = (UnityEngine.RectTransform)UnityEngine.GameObject.Find("Block_Основное").transform;
        var right = (UnityEngine.RectTransform)UnityEngine.GameObject.Find("Block_Состояния").transform;
        float diff = left.rect.width - right.rect.width;
        sb.Append("corner=").Append(corner).Append(" left=").Append(left.rect.width.ToString("0.0"))
          .Append(" right=").Append(right.rect.width.ToString("0.0")).Append(" diff=").Append(diff.ToString("0.0"))
          .Append(System.Math.Abs(diff) < 0.5f ? " OK; " : " FAIL: скругление изменило ширину; ");
    }
}
finally
{
    look.Corner = corner0;
    ui.Close();
}
return sb.ToString();
