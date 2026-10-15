// ОБЪЕКТ-КРЫША ВЫДЕЛЯЕТСЯ С ЭТАЖА ПОД НИМ (P1062). Для execute_code (в play).
// Купол и звонница (roofSnap) стоят ровно на верхней плоскости этажа; с этажа, который они
// накрывают, CursorHidden обязан отдавать false (иначе их нельзя выделить и удалить).
// Проверяет все roofSnap-объекты уровня относительно этажа ИГРОКА: те, что лежат на его
// крыше, не спрятаны; те, что на два и больше этажей выше, — спрятаны.
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var mHidden = T.GetMethod("CursorHidden", B);
var player = Cozy.Grid.PlayerRef.GameObject;
float cell = 3f;
float floorY = Cozy.Grid.GridManager.FloorOf(player.transform.position, cell);
var sb = new System.Text.StringBuilder();
var bad = new System.Collections.Generic.List<string>();
int onRoof = 0, higher = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null || !io.Def.roofSnap) continue;
    var p = io.transform.position;
    bool hidden = (bool)mHidden.Invoke(gc, new object[] { io });
    bool roofOfMine = Cozy.Grid.GridManager.OnFloor(p - UnityEngine.Vector3.up * cell, floorY, cell) || Cozy.Grid.GridManager.OnFloor(p, floorY, cell);
    float above = Cozy.Grid.GridManager.AboveRelief(p) - floorY;
    sb.Append(io.Def.id + " y+" + above.ToString("0.0") + (hidden ? " спрятан" : " виден") + "; ");
    if (roofOfMine) { onRoof++; if (hidden) bad.Add(io.Def.id + " на крыше этажа игрока, но CursorHidden = true (P1062)"); }
    else if (above >= cell * 2f) { higher++; if (!hidden) bad.Add(io.Def.id + " на " + above.ToString("0.0") + " м выше этажа игрока, но виден курсору"); }
}
if (onRoof + higher == 0) return "ПРОПУСК: на уровне нет roofSnap-объектов (купол, звонница) — встань в башню под купол";
return (bad.Count == 0 ? "ОК" : "ПРОВАЛ: " + string.Join("; ", bad.ToArray())) + " | этаж игрока " + floorY + ", на его крыше " + onRoof + ", выше " + higher + " | " + sb;
