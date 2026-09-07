// Проба «зона уносит свои объёмы» (P: удалил зону — огонь остался, 2026-09-05;
// ветер добавлен 2026-09-06).
// Запуск в play через execute_code: строит зону 2×1 с огнём и туманом в стороне
// от уровня, удаляет её через GridCursor.RemoveZone и считает объёмы в её клетках.
if (!Application.isPlaying) return "NOT PLAYING";
var cursor = Cozy.Grid.GridCursor.I;
var origin = new Vector3(-60f, 0f, -60f);
var cells = new[] { origin, origin + new Vector3(3f, 0f, 0f) };
var zone = Cozy.Grid.ZonePiece.Spawn(null, cells, 3f, 0.1f, Color.red, "PROBE_ZONE", "probe_zone");
zone.fog = true; zone.fire = true; zone.wind = true;
Cozy.Grid.FogView.FillZone(zone, true);
Cozy.Grid.FireView.FillZone(zone, true);
Cozy.Grid.WindView.FillZone(zone, true);
int fogBefore = 0, fireBefore = 0, windBefore = 0;
foreach (var c in cells) { if (Cozy.Grid.FogView.Covers(c)) fogBefore++; if (Cozy.Grid.FireView.Occupied(Cozy.Grid.FireView.CellOf(c))) fireBefore++; if (Cozy.Grid.WindView.Occupied(Cozy.Grid.WindView.CellOf(c))) windBefore++; }
cursor.RemoveZone(zone);
int fogAfter = 0, fireAfter = 0, windAfter = 0;
foreach (var c in cells) { if (Cozy.Grid.FogView.Covers(c)) fogAfter++; if (Cozy.Grid.FireView.Occupied(Cozy.Grid.FireView.CellOf(c))) fireAfter++; if (Cozy.Grid.WindView.Occupied(Cozy.Grid.WindView.CellOf(c))) windAfter++; }
return "fog " + fogBefore + "→" + fogAfter + " fire " + fireBefore + "→" + fireAfter + " wind " + windBefore + "→" + windAfter
     + (fogAfter == 0 && fireAfter == 0 && windAfter == 0 && fogBefore == 2 && fireBefore == 2 && windBefore == 2 ? " :: ОК" : " :: ПРОВАЛ");
