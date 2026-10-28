if (!UnityEngine.Application.isPlaying) return "СОХРАНЕНО: не в play";
var io = typeof(Cozy.Grid.LevelIO);
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
string name = Cozy.Grid.LevelIO.CurrentLevelName;
if (string.IsNullOrEmpty(name)) return "СОХРАНЕНО: уровень без имени";
string path = Cozy.Grid.LevelIO.PathFor(name);
if (!System.IO.File.Exists(path)) return "НЕ СОХРАНЕНО: файла уровня нет — " + path;
var saved = UnityEngine.JsonUtility.FromJson<Cozy.Grid.LevelIO.LevelData>(System.IO.File.ReadAllText(path));
var live = new Cozy.Grid.LevelIO.LevelData();
foreach (var step in new[] { "CollectBlocks", "CollectDoors", "CollectWindows", "CollectStairs", "CollectObjects", "CollectZones", "CollectRoofs", "CollectWater" })
    io.GetMethod(step, BF).Invoke(null, new object[] { live });
var gc = Cozy.Grid.GridCursor.I;
string liveHeights = gc != null && gc.Heights != null ? gc.Heights.Pack() : "";
var diff = new System.Collections.Generic.List<string>();
System.Action<string, int, int> count = (what, a, b) => { if (a != b) diff.Add(what + " " + b + "→" + a); };
count("стены", live.walls.Count, saved.walls.Count);
count("полы", live.floors.Count, saved.floors.Count);
count("двери", live.doors.Count, saved.doors.Count);
count("окна", live.windows.Count, saved.windows.Count);
count("лестницы", live.stairs.Count, saved.stairs.Count);
count("зоны", live.zones.Count, saved.zones.Count);
count("крыши", live.roofs.Count, saved.roofs.Count);
count("вода", live.water.Count, saved.water.Count);
if (liveHeights != (saved.heights ?? "")) diff.Add("рельеф изменён");
System.Func<Cozy.Grid.LevelIO.ObjectData, bool> roams = o => { var d = Cozy.Grid.FurnitureCatalog.ById(o.id); return d != null && d.birdIdle; };
System.Func<Cozy.Grid.LevelIO.ObjectData, string> key = o => roams(o) ? o.id + "@летает" : o.id + "@" + UnityEngine.Mathf.RoundToInt(o.pos.x * 100f) + "," + UnityEngine.Mathf.RoundToInt(o.pos.y * 100f) + "," + UnityEngine.Mathf.RoundToInt(o.pos.z * 100f);
var bag = new System.Collections.Generic.Dictionary<string, int>();
foreach (var o in saved.objects) { var k = key(o); bag[k] = (bag.ContainsKey(k) ? bag[k] : 0) + 1; }
var added = new System.Collections.Generic.List<string>();
foreach (var o in live.objects) { var k = key(o); if (bag.ContainsKey(k) && bag[k] > 0) bag[k]--; else added.Add(k); }
var gone = new System.Collections.Generic.List<string>();
foreach (var kv in bag) for (int i = 0; i < kv.Value; i++) gone.Add(kv.Key);
if (added.Count > 0) diff.Add("объектов новых/сдвинутых " + added.Count + " (" + string.Join(" ", added.GetRange(0, System.Math.Min(4, added.Count))) + ")");
if (gone.Count > 0) diff.Add("объектов пропало/сдвинуто " + gone.Count + " (" + string.Join(" ", gone.GetRange(0, System.Math.Min(4, gone.Count))) + ")");
return diff.Count == 0 ? "СОХРАНЕНО: живой уровень совпадает с " + System.IO.Path.GetFileName(path) : "НЕ СОХРАНЕНО: " + string.Join("; ", diff);
