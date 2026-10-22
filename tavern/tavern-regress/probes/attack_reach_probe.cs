// Атака только «дотянувшись» (ZOMBIE.md ZB-A…, P1174): AttackReach.Clear рвут стена, окно (закрытое и открытое), закрытая
// дверь, другой этаж; открытая дверь и чистое поле — не рвут. Любой уровень со стеной, окном и дверью на земле
// (стенд — «Зомби (тест)»). Проба ставит своего зомби и героя по разные стороны преграды и всё возвращает.
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0;
System.Action<bool, string> Check = (ok, line) => { if (!ok) fails++; sb.Append(ok ? "OK " : "FAIL ").Append(line).Append('\n'); };
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var player = Cozy.Grid.PlayerRef.Transform;
if (player == null) return "нет героя";
var cc = player.GetComponent<UnityEngine.CharacterController>();
var wasPos = player.position; var wasRot = player.rotation;
UnityEngine.GameObject made = null;
var doorsWere = new System.Collections.Generic.List<(Cozy.Grid.DoorPiece, bool)>();
var winsWere = new System.Collections.Generic.List<(Cozy.Grid.WindowPiece, bool)>();
foreach (var d in Cozy.Grid.DoorPiece.All) if (d != null) doorsWere.Add((d, d.IsOpen));
foreach (var w in Cozy.Grid.WindowPiece.All) if (w != null) winsWere.Add((w, w.IsOpen));
float feetToRoot = player.position.y - Cozy.Character.PlayerTarget.Feet.y;
System.Action<UnityEngine.Vector3> PutHero = at =>
{
    if (cc != null) cc.enabled = false;
    player.position = new UnityEngine.Vector3(at.x, at.y + feetToRoot, at.z);
    UnityEngine.Physics.SyncTransforms();
    if (cc != null) cc.enabled = true;
};
try
{
    var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
    var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { Cozy.Grid.FurnitureCatalog.ById("zombie"), new UnityEngine.Vector3(600f, 0f, 600f), 0f });
    made = io.gameObject;
    foreach (var col in made.GetComponentsInChildren<UnityEngine.Collider>()) col.enabled = false;   // свой зомби не мешает лучу героя
    float ground = Cozy.Grid.GridCursor.I.GroundY(0f, 0f, 0f);
    System.Func<UnityEngine.Vector3, UnityEngine.Vector3, float, bool> Across = (center, normal, gap) =>
    {
        normal.y = 0f; normal.Normalize();
        var a = center + normal * gap; var b = center - normal * gap;
        a.y = b.y = ground;
        io.transform.position = a;
        PutHero(b);
        return Cozy.Combat.AttackReach.Clear(io, player);
    };
    // чистое поле: далеко от построек
    Check(Across(new UnityEngine.Vector3(10f, 0f, 10f), UnityEngine.Vector3.right, 1.5f), "ZB-A01 чистое поле: атака дотягивается");
    // стена: середина стенового блока земли подальше от проёмов
    Cozy.Grid.GridBlock wall = null;
    foreach (var b in Cozy.Grid.GridBlock.All)
    {
        if (b == null || b.role != Cozy.Grid.GridRole.Wall) continue;
        var c = b.GetComponent<UnityEngine.Collider>(); if (c == null || c.bounds.min.y > 0.5f || c.bounds.max.y < 1.5f) continue;
        bool nearOpening = false;
        foreach (var d in Cozy.Grid.DoorPiece.All) if (d != null && (d.transform.position - c.bounds.center).sqrMagnitude < 4f) nearOpening = true;
        foreach (var w in Cozy.Grid.WindowPiece.All) if (w != null && (w.transform.position - c.bounds.center).sqrMagnitude < 4f) nearOpening = true;
        if (!nearOpening) { wall = b; break; }
    }
    if (wall != null)
    {
        var bb = wall.GetComponent<UnityEngine.Collider>().bounds;
        var n = bb.size.x < bb.size.z ? UnityEngine.Vector3.right : UnityEngine.Vector3.forward;
        Check(!Across(bb.center, n, 1.5f), "ZB-A02 сквозь стену: нет");
    }
    else sb.Append("SKIP ZB-A02 нет стены без проёма\n");
    // окно: закрытое и открытое
    var win = Cozy.Grid.WindowPiece.All.Count > 0 ? Cozy.Grid.WindowPiece.All[0] : null;
    if (win != null)
    {
        win.SetOpen(false);
        Check(!Across(win.transform.position, win.InsideNormal, 1.5f), "ZB-A03 сквозь закрытое окно: нет");
        win.SetOpen(true);
        Check(!Across(win.transform.position, win.InsideNormal, 1.5f), "ZB-A04 сквозь открытое окно: нет (в окно не бьют)");
    }
    else sb.Append("SKIP ZB-A03/A04 нет окна\n");
    // дверь: закрытая — нет, открытая — да
    var door = Cozy.Grid.DoorPiece.All.Count > 0 ? Cozy.Grid.DoorPiece.All[0] : null;
    if (door != null)
    {
        var acc = (Cozy.Grid.AccessFeature)typeof(Cozy.Grid.DoorPiece).GetField("_access", NP).GetValue(door);
        var fT = typeof(Cozy.Grid.DoorPiece).GetField("_t", NP); var upd = typeof(Cozy.Grid.DoorPiece).GetMethod("Update", NP);
        acc.SetOpen(false); fT.SetValue(door, 0f); upd.Invoke(door, null); UnityEngine.Physics.SyncTransforms();
        Check(!Across(door.transform.position, door.Normal, 1.5f), "ZB-A05 сквозь закрытую дверь: нет");
        acc.SetOpen(true); fT.SetValue(door, 1f); upd.Invoke(door, null); UnityEngine.Physics.SyncTransforms();
        Check(Across(door.transform.position, door.Normal, 1.5f), "ZB-A06 в открытую дверь: да");
    }
    else sb.Append("SKIP ZB-A05/A06 нет двери\n");
    // другой этаж: зомби над героем
    Across(new UnityEngine.Vector3(10f, 0f, 10f), UnityEngine.Vector3.right, 0.5f);
    io.transform.position += UnityEngine.Vector3.up * 3f;
    Check(!Cozy.Combat.AttackReach.Clear(io, player), "ZB-A07 с другого этажа: нет");
}
finally
{
    if (made != null) UnityEngine.Object.DestroyImmediate(made);
    foreach (var dw in doorsWere) { var d = dw.Item1; bool open = dw.Item2; if (d == null) continue; var acc = (Cozy.Grid.AccessFeature)typeof(Cozy.Grid.DoorPiece).GetField("_access", NP).GetValue(d); acc.SetOpen(open); }
    foreach (var ww in winsWere) if (ww.Item1 != null) ww.Item1.SetOpen(ww.Item2);
    if (cc != null) cc.enabled = false;
    player.SetPositionAndRotation(wasPos, wasRot);
    UnityEngine.Physics.SyncTransforms();
    if (cc != null) cc.enabled = true;
}
int total = 0;
foreach (var l in sb.ToString().Split('\n')) if (l.StartsWith("OK ") || l.StartsWith("FAIL ")) total++;
return (fails == 0 ? "ЗЕЛЁНОЕ из " + total : "КРАСНОЕ: " + fails + " из " + total) + " (свой зомби, герой и проёмы возвращены)\n" + sb;
