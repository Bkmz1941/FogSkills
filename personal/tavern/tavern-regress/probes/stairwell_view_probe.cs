if (!UnityEngine.Application.isPlaying) return "не в play";
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var t = typeof(Cozy.Grid.FloorPieceView);
var fBase = t.GetField("_basePos", BF);
var fRoofed = t.GetField("_roofed", BF);
var fHide = t.GetField("_hideBelow", BF);
float cs = Cozy.View.ViewState.CellSize;
int checkedHigh = 0, wrong = 0;
var sb = new System.Text.StringBuilder();
foreach (var v in UnityEngine.Object.FindObjectsByType<Cozy.Grid.FloorPieceView>(UnityEngine.FindObjectsSortMode.None))
{
    if (!(bool)fHide.GetValue(v)) continue;
    var b = (UnityEngine.Vector3)fBase.GetValue(v);
    bool holeUnderHigherSlab = false;
    for (int i = 0; i < 5 && !holeUnderHigherSlab; i++)
    {
        float ox = i == 1 ? cs : i == 2 ? -cs : 0f;
        float oz = i == 3 ? cs : i == 4 ? -cs : 0f;
        bool cov; float above;
        Cozy.Grid.BuildQuery.ColumnScan(b.x + ox, b.z + oz, b.y, cs, out cov, out above);
        if (above < 1e9f && above > b.y + cs + Cozy.View.ViewState.YEps) holeUnderHigherSlab = true;
    }
    if (!holeUnderHigherSlab) continue;
    checkedHigh++;
    if ((bool)fRoofed.GetValue(v)) { wrong++; if (wrong <= 6) sb.Append(v.name + " " + b.ToString("F1") + "; "); }
}
if (checkedHigh == 0) return "НЕ ПРОВЕРЕНО: у проёма под высоким перекрытием предметов нет (нужен дом с лестницей и этажом выше проёма)";
return "вид в проём сверху (P848): предметов у проёма под высоким перекрытием=" + checkedHigh + " спрятаны как накрытые=" + wrong + (wrong > 0 ? " КРАСНОЕ: " + sb : "");
