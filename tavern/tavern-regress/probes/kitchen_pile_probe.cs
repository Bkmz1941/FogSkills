// ГОРА ПОСУДЫ В МОЙКЕ — живая игра, а не порт (KITCHEN.md: KT-PL07, PL10 + живые PL02/PL03/PL04; 18.10).
// Для execute_code в play, на ЛЮБОМ уровне. Строит СВОЮ мойку home_sink и свою посуду в своей зоне
// (игрок + (0, −90, 40)), как live_probe.cs из BlenderWork/sink_game_check: посуда «в чаше» = стоит в её коробке,
// раскладку делает настоящий SinkPile.Update.
//  PL07 лимиты дефа мойки (ObjectDef.pile): до лимита HasRoom = да, сверх лимита — нет (кружки 8, тарелки 5, сковорода 1, кастрюля 1);
//  PL10/PL02 после каждого ДОБАВЛЕНИЯ раскладка = свежей раскладке того же состава (память посадок стёрта) ±0,5 мм;
//  PL10/PL03 после СНЯТИЯ кружки или тарелки остальные только оседают: то же пятно (xz ±1 мм), y не выше;
//  PL04 «загрузка»: стёртая память посадок не перекладывает горку (±0,5 мм).
// История — 40 шагов детерминированного случайного «добавить/снять» (System.Random(18)). Всё удаляется в finally.
if (!UnityEngine.Application.isPlaying) return "не в play";
var T = typeof(Cozy.Grid.SinkPile);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var upd = T.GetMethod("Update", B);
var mem = T.GetField("_seatOf", B);
if (upd == null || mem == null) return "SKIP: SinkPile без Update/_seatOf — проба устарела";
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 50) sb.Append("FAIL " + line + "\n"); } };
var made = new System.Collections.Generic.List<UnityEngine.GameObject>();
var origin = Cozy.Grid.PlayerRef.Transform.position + new UnityEngine.Vector3(0f, -90f, 40f);
var sinkDef = Cozy.Grid.FurnitureCatalog.ById("home_sink");
if (sinkDef == null) return "SKIP: нет home_sink в каталоге";
try {
    var sinkGo = new UnityEngine.GameObject("KitchenPileProbeSink"); made.Add(sinkGo);
    sinkGo.transform.position = origin;
    var sink = sinkGo.AddComponent<Cozy.Grid.InteractiveObject>();
    sink.Build(sinkDef);
    var pile = sink.GetComponent<Cozy.Grid.SinkPile>();
    if (pile == null) return "SKIP: у home_sink нет SinkPile";
    var inside = origin + new UnityEngine.Vector3(0f, -0.1f, 0f);
    int n = 0;
    System.Func<string, Cozy.Grid.InteractiveObject> Make = id => {
        var go = new UnityEngine.GameObject("KitchenPileProbe_" + id); made.Add(go);
        go.transform.position = origin + new UnityEngine.Vector3(5f + (n++) * 1.2f, 0f, 0f);
        var io = go.AddComponent<Cozy.Grid.InteractiveObject>(); io.Build(Cozy.Grid.FurnitureCatalog.ById(id)); return io;
    };
    System.Action<Cozy.Grid.InteractiveObject> Out = io => { io.transform.position = origin + new UnityEngine.Vector3(5f + (n++) * 1.2f, 0f, 3f); };
    System.Action Lay = () => { upd.Invoke(pile, null); UnityEngine.Physics.SyncTransforms(); };
    System.Func<System.Collections.Generic.Dictionary<Cozy.Grid.InteractiveObject, UnityEngine.Vector3>> Snap = () => {
        var list = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(); pile.Collect(list);
        var d = new System.Collections.Generic.Dictionary<Cozy.Grid.InteractiveObject, UnityEngine.Vector3>();
        foreach (var io in list) d[io] = sinkGo.transform.InverseTransformPoint(io.transform.position);
        return d;
    };
    // ── PL07 лимиты
    var limits = new System.Collections.Generic.Dictionary<string, int> { { "coffee_cup_red", 8 }, { "plate", 5 }, { "frying_pan", 1 }, { "cooking_pot", 1 } };
    foreach (var kv in limits) {
        var put = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
        for (int i = 0; i < kv.Value + 1; i++) {
            var io = Make(kv.Key);
            bool room = pile.HasRoom(io);
            if (i < kv.Value) { Check(room, "PL07 " + kv.Key + ": " + (i + 1) + "-я не помещается, лимит " + kv.Value); if (room) { io.transform.position = inside; Lay(); put.Add(io); } }
            else Check(!room, "PL07 " + kv.Key + ": " + (i + 1) + "-я помещается сверх лимита " + kv.Value);
        }
        var laid = Snap();
        Check(laid.Count == put.Count, "PL07 " + kv.Key + ": в горке " + laid.Count + " из положенных " + put.Count);
        foreach (var io in put) Out(io);
        Lay(); ((System.Collections.IDictionary)mem.GetValue(pile)).Clear();
    }
    // ── PL10 живая история
    var pool = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    foreach (var id in new[] { "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue", "coffee_cup_red", "plate", "plate", "plate", "frying_pan", "cooking_pot" }) pool.Add(Make(id));
    var inPile = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>();
    var rnd = new System.Random(18);
    int adds = 0, removes = 0;
    for (int step = 0; step < 40; step++) {
        bool add = inPile.Count == 0 || (inPile.Count < pool.Count && rnd.Next(3) > 0);
        if (add) {
            var cand = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
            foreach (var io in pool) if (!inPile.Contains(io) && pile.HasRoom(io)) cand.Add(io);
            if (cand.Count == 0) continue;
            var pick = cand[rnd.Next(cand.Count)];
            pick.transform.position = inside; Lay(); inPile.Add(pick); adds++;
            var after = Snap();
            Check(after.Count == inPile.Count, "PL10 шаг " + step + " +" + pick.Def.id + ": в горке " + after.Count + ", положено " + inPile.Count);
            ((System.Collections.IDictionary)mem.GetValue(pile)).Clear(); Lay();
            var fresh = Snap();
            foreach (var kv in after) {
                UnityEngine.Vector3 f; if (!fresh.TryGetValue(kv.Key, out f)) { Check(false, "PL04 шаг " + step + ": после сброса памяти " + kv.Key.Def.id + " выпала из горки"); continue; }
                float d = (f - kv.Value).magnitude;
                Check(d <= 0.0005f, "PL02/PL04 шаг " + step + " +" + pick.Def.id + ": " + kv.Key.Def.id + " после добавления не как в свежей раскладке, разница " + (d * 1000f).ToString("0.0") + " мм");
            }
        } else {
            var cand = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
            foreach (var io in inPile) if (io.Def.id.StartsWith("coffee_cup") || io.Def.id == "plate") cand.Add(io);
            if (cand.Count == 0) continue;
            var pick = cand[rnd.Next(cand.Count)];
            var before = Snap();
            Out(pick); Lay(); inPile.Remove(pick); removes++;
            var after = Snap();
            foreach (var kv in after) {
                UnityEngine.Vector3 b; if (!before.TryGetValue(kv.Key, out b)) continue;
                var dxz = new UnityEngine.Vector2(kv.Value.x - b.x, kv.Value.z - b.z).magnitude;
                Check(dxz <= 0.001f && kv.Value.y <= b.y + 0.0005f, "PL03 шаг " + step + " −" + pick.Def.id + ": " + kv.Key.Def.id + " сдвинулась не оседанием (xz " + (dxz * 1000f).ToString("0.0") + " мм, y " + ((kv.Value.y - b.y) * 1000f).ToString("+0.0;-0.0") + " мм)");
            }
        }
    }
    sb.Insert(0, "история: добавлений " + adds + ", снятий " + removes + "\n");
} finally {
    foreach (var g in made) if (g != null) UnityEngine.Object.DestroyImmediate(g);
    UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " (своя мойка и посуда, удалены)\n" + sb + "SKIP PL08 (тарелка с едой — глазами), пересечения по мешам — game_pile_check.py (Blender).";
