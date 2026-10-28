// Проба «зона уносит свои объёмы» (P: удалил зону — огонь остался, 2026-09-05;
// ветер добавлен 2026-09-06; с 10.09 тип зоны = её функция: три зоны вместо трёх свитчей).
// Запуск в play через execute_code: ставит зоны огня, тумана и ветра 2×1 в стороне
// от уровня (туман в 9 м от огня — костёр рассеивает туман вокруг себя), заливает
// их объёмами, удаляет через GridCursor.RemoveZone и считает объёмы в клетках.
if (!Application.isPlaying) return "NOT PLAYING";
var cursor = Cozy.Grid.GridCursor.I;
var fireAt = new Vector3(-60f, 0f, -60f);
var fogAt = new Vector3(-60f, 0f, -51f);
var fireCells = new[] { fireAt, fireAt + new Vector3(3f, 0f, 0f) };
var fogCells = new[] { fogAt, fogAt + new Vector3(3f, 0f, 0f) };
var fire = Cozy.Grid.ZonePiece.Spawn(null, fireCells, 3f, 0.1f, Cozy.Grid.ZoneKind.Fire, Color.red, "PROBE_FIRE", "probe_fire");
var fog = Cozy.Grid.ZonePiece.Spawn(null, fogCells, 3f, 0.1f, Cozy.Grid.ZoneKind.Fog, Color.gray, "PROBE_FOG", "probe_fog");
var wind = Cozy.Grid.ZonePiece.Spawn(null, fireCells, 3f, 0.1f, Cozy.Grid.ZoneKind.Wind, Color.cyan, "PROBE_WIND", "probe_wind");
Cozy.Grid.GridCursor.FillZoneVolumes(fire, true);
Cozy.Grid.GridCursor.FillZoneVolumes(fog, true);
Cozy.Grid.GridCursor.FillZoneVolumes(wind, true);
int fogBefore = 0, fireBefore = 0, windBefore = 0;
foreach (var c in fogCells) if (Cozy.Grid.FogView.Covers(c)) fogBefore++;
foreach (var c in fireCells) { if (Cozy.Grid.FireView.Occupied(Cozy.Grid.FireView.CellOf(c))) fireBefore++; if (Cozy.Grid.WindView.Occupied(Cozy.Grid.WindView.CellOf(c))) windBefore++; }
cursor.RemoveZone(fire);
cursor.RemoveZone(fog);
cursor.RemoveZone(wind);
int fogAfter = 0, fireAfter = 0, windAfter = 0;
foreach (var c in fogCells) if (Cozy.Grid.FogView.Covers(c)) fogAfter++;
foreach (var c in fireCells) { if (Cozy.Grid.FireView.Occupied(Cozy.Grid.FireView.CellOf(c))) fireAfter++; if (Cozy.Grid.WindView.Occupied(Cozy.Grid.WindView.CellOf(c))) windAfter++; }
return "fog " + fogBefore + "→" + fogAfter + " fire " + fireBefore + "→" + fireAfter + " wind " + windBefore + "→" + windAfter
     + (fogAfter == 0 && fireAfter == 0 && windAfter == 0 && fogBefore == 2 && fireBefore == 2 && windBefore == 2 ? " :: ОК" : " :: ПРОВАЛ");
