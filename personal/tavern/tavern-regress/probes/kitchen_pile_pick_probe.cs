// ВЗЯТЬ ИЗ ГОРЫ ПОСУДЫ (KITCHEN.md 6б, KT-PK01…PK04; P1134, Илья 18.10: «не могу в горе посуды выделить сковородку»).
// Для execute_code в play, на ЛЮБОМ уровне. Своя мойка home_sink в своей зоне (игрок + (400, 0, 0)) в трёх постановках:
// голая, на прямой тумбе home_sink_cabinet, на угловой home_sink_cabinet_corner (у неё ниша Slot_Niche с дверцей — P1134).
// Посуда кладётся, только пока горка говорит «есть место» (HasRoom), как в игре. Составы горки — набор характерных (сковорода одна, под тарелкой, под кастрюлей, полная горка, кружки, тарелки стопкой).
// Для каждого предмета горки: СВОБОДНЫЕ точки его поверхности — не накрытые другой посудой сверху и не под
// посудой, которая лежит на нём (край тарелки в середине стопки — это стопка, из неё берут верхнюю; ручка сковороды — свободна); настоящий Interactor.Raycast
// с трёх игровых ракурсов (спереди под 50°, спереди-слева, спереди-справа) через реальный курсор.
//  PK01 предмет, у которого есть открытые точки, наводится хотя бы с одного ракурса (иначе его нельзя выделить вовсе);
//  PK02 доля «навёлся сам» по его открытым точкам ≥ 50 % (тумба/мойка не перехватывают);
//  PK03 тумба под мойкой не забирает наведение на посуду в чаше (не больше 10 % прицелов у каждого предмета);
//  PK04 у наведённого предмета есть «Переместить» или «Подобрать» и он Clickable.
// СНЯТИЕ (Илья 18.10: «опускается на дно — но если есть место», «любое можно взять если выделяешь», «только то что выделил, 1 объект»),
// на голой мойке, каждый предмет каждого состава отдельно, на свежей горке:
//  PK05 в руке ровно выделенный предмет: MovingObject = он, ничего из горки не прицепилось к нему и не уехало с ним;
//  PK06 если SinkPile.TakeDenialOf пусто — после снятия остальные только оседают: XZ ±5 см, не выше +1 см, попарно не входят друг в друга (коробки −12 мм; пары «держит» — сковорода с грузом, тарелка в стопке — не меряются, их судит game_pile_check.py по мешам);
//  PK07 если не пусто — «Переместить» и «Подобрать» неактивны, подсказка = SinkPile.NoRoomBelow; брать нельзя.
// Всё созданное удаляется, камера и герой возвращаются.
if (!UnityEngine.Application.isPlaying) return "не в play";
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var gc = Cozy.Grid.GridCursor.I;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var upd = typeof(Cozy.Grid.SinkPile).GetMethod("Update", NP);
var rayM = typeof(Cozy.Grid.Interactor).GetMethod("Raycast", NP);
var inter = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.Interactor>();
if (gc == null || spawn == null || upd == null || rayM == null || inter == null) return "SKIP: нет GridCursor/SinkPile.Update/Interactor.Raycast — проба устарела";
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var player = Cozy.Grid.PlayerRef.GameObject;
var savedP = player.transform.position; var savedCP = cam.transform.position; var savedCR = cam.transform.rotation;
var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; if (fails <= 40) sb.Append("FAIL " + line + "\n"); } };
var combos = new string[][] {
    new[]{ "frying_pan" },
    new[]{ "frying_pan", "plate" },
    new[]{ "frying_pan", "cooking_pot" },
    new[]{ "frying_pan", "plate", "plate", "plate", "plate", "plate" },
    new[]{ "frying_pan", "cooking_pot", "plate", "plate", "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue" },
    new[]{ "cooking_pot", "coffee_cup_red" },
    new[]{ "plate", "plate", "coffee_cup_red", "coffee_cup_blue" },
    new[]{ "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue", "coffee_cup_red" },
    new[]{ "frying_pan", "cooking_pot", "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue", "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue" },
    new[]{ "frying_pan", "plate", "plate", "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue", "coffee_cup_red", "coffee_cup_yellow", "coffee_cup_blue", "coffee_cup_red", "coffee_cup_yellow" },
};
var setups = new[]{ "", "home_sink_cabinet", "home_sink_cabinet_corner" };
int items = 0, aimsAll = 0, refused = 0;
try {
  var baseO = savedP + new UnityEngine.Vector3(400f, 0f, 0f);
  UnityEngine.RaycastHit g; if (UnityEngine.Physics.Raycast(baseO + UnityEngine.Vector3.up * 50f, UnityEngine.Vector3.down, out g, 200f)) baseO = g.point;
  for (int si = 0; si < setups.Length; si++)
  for (int ci = 0; ci < combos.Length; ci++) {
    var origin = baseO + new UnityEngine.Vector3(si * 8f, 0f, ci * 6f);
    var made = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    try {
      Cozy.Grid.InteractiveObject cab = null, sink;
      float yaw = si == 2 ? 195f : 0f;
      if (setups[si] != "") {
        cab = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById(setups[si]), origin, yaw }); made.Add(cab);
        UnityEngine.Physics.SyncTransforms();
        var slot = Cozy.Grid.FurnitureModel.FindNode(cab.transform, "SinkSlot");
        var at = slot != null ? slot.position : origin + UnityEngine.Vector3.up * cab.WorldBounds.size.y;
        sink = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById("home_sink"), at, yaw });
        sink.transform.SetPositionAndRotation(at, UnityEngine.Quaternion.Euler(0f, yaw, 0f));
      } else sink = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById("home_sink"), origin, yaw });
      made.Add(sink);
      UnityEngine.Physics.SyncTransforms();
      var pile = sink.GetComponent<Cozy.Grid.SinkPile>();
      var liq = sink.GetComponent<Cozy.Grid.LiquidVolume>();
      if (pile == null || liq == null) { Check(false, "мойка без SinkPile/LiquidVolume"); continue; }
      var inside = liq.FullWorldBounds().center;
      var dishes = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
      int k = 0;
      foreach (var id in combos[ci]) {
        var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById(id), origin + new UnityEngine.Vector3(3f + k++, 0f, 3f), 0f });
        made.Add(io);
        if (!pile.HasRoom(io)) { refused++; continue; }
        io.transform.position = inside; UnityEngine.Physics.SyncTransforms();
        upd.Invoke(pile, null); UnityEngine.Physics.SyncTransforms();
        dishes.Add(io);
      }
      upd.Invoke(pile, null); UnityEngine.Physics.SyncTransforms();
      foreach (var io in dishes) gc.ReattachToContainer(io);
      UnityEngine.Physics.SyncTransforms();
      var front = sink.transform.position + sink.transform.rotation * new UnityEngine.Vector3(0f, 0f, -1.2f);
      player.transform.position = new UnityEngine.Vector3(front.x, origin.y, front.z);
      UnityEngine.Physics.SyncTransforms();
      var dirs = new UnityEngine.Vector3[]{ new UnityEngine.Vector3(0f, -1.2f, 1f), new UnityEngine.Vector3(0.5f, -1.2f, 1f), new UnityEngine.Vector3(-0.5f, -1.2f, 1f) };
      string where = (setups[si] == "" ? "голая мойка" : setups[si]) + " [" + string.Join("+", combos[ci]) + "]";
      foreach (var io in dishes) {
        items++;
        var own = io.GetComponentsInChildren<UnityEngine.Collider>();
        var ib = io.WorldBounds;
        var pts = new System.Collections.Generic.List<UnityEngine.Vector3>();
        int stackPts = 0;
        for (int gx = 0; gx < 10; gx++) for (int gz = 0; gz < 10; gz++) {
          var top = new UnityEngine.Vector3(UnityEngine.Mathf.Lerp(ib.min.x, ib.max.x, (gx + 0.5f) / 10f), ib.max.y + 1f, UnityEngine.Mathf.Lerp(ib.min.z, ib.max.z, (gz + 0.5f) / 10f));
          float bestD = 99f; UnityEngine.Vector3 bp = UnityEngine.Vector3.zero;
          foreach (var c in own) { if (c.isTrigger) continue; UnityEngine.RaycastHit h; if (c.Raycast(new UnityEngine.Ray(top, UnityEngine.Vector3.down), out h, 3f) && h.distance < bestD) { bestD = h.distance; bp = h.point; } }
          if (bestD >= 99f) continue;
          bool covered = false;
          foreach (var h in UnityEngine.Physics.RaycastAll(top, UnityEngine.Vector3.down, bestD - 0.002f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) {
            if (Cozy.Grid.RayPick.Classify(h.collider) != Cozy.Grid.RayPick.Kind.Pickable) continue;
            var o = h.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>();
            if (o == null || o == sink || o == cab) continue;
            covered = true; break;
          }
          if (covered) continue;
          bool underStack = false;
          foreach (var up in dishes) {
            if (up == io) continue;
            var ub = up.WorldBounds;
            if (ub.center.y <= ib.center.y + 0.005f) continue;
            if (bp.x >= ub.min.x && bp.x <= ub.max.x && bp.z >= ub.min.z && bp.z <= ub.max.z) { underStack = true; break; }
          }
          if (underStack) { stackPts++; continue; }
          pts.Add(bp);
        }
        int self = 0, total = 0, byCab = 0; var got = new System.Collections.Generic.Dictionary<string, int>();
        foreach (var wd0 in dirs) foreach (var p in pts) {
          var wd = (sink.transform.rotation * wd0).normalized;
          cam.transform.SetPositionAndRotation(p - wd * 6f, UnityEngine.Quaternion.identity);
          var ld = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
          cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(ld, wd);
          cam.transform.position = p - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * 6f;
          var hit = rayM.Invoke(inter, new object[]{ mouse }) as Cozy.Grid.InteractiveObject;
          total++; aimsAll++;
          { string key = hit == null ? "-" : hit == io ? "сам" : hit.Def.id; int cc; got.TryGetValue(key, out cc); got[key] = cc + 1; }
          if (hit == io) self++;
          else if (cab != null && hit == cab) byCab++;
        }
        if (pts.Count == 0) { info.Append(where + " " + io.Def.id + ": свободных точек нет" + (stackPts > 0 ? " (край под стопкой " + stackPts + ")" : "") + "; "); continue; }
        var gs = new System.Text.StringBuilder(); foreach (var kv in got) gs.Append(kv.Key + "=" + kv.Value + " ");
        Check(self > 0, "PK01 " + where + " " + io.Def.id + ": не наводится ни с одного ракурса (открытых точек " + pts.Count + ", тумба забрала " + byCab + " из " + total + ")");
        Check(self * 2 >= total, "PK02 " + where + " " + io.Def.id + ": навёлся сам " + self + " из " + total + " [" + gs + "]");
        if (cab != null) Check(byCab * 10 <= total, "PK03 " + where + " " + io.Def.id + ": тумба забрала " + byCab + " из " + total);
        bool canTake = false;
        foreach (var f in io.Features) if (f.Available) foreach (var b in f.Buttons(null)) if ((b.Label == "Переместить" || b.Label == "Подобрать") && b.Enabled) canTake = true;
        Check(io.Clickable && canTake, "PK04 " + where + " " + io.Def.id + ": Clickable=" + io.Clickable + ", кнопка взять=" + canTake);
      }
    } finally {
      foreach (var io in made) if (io != null) UnityEngine.Object.DestroyImmediate(io.gameObject);
    }
  }

  var denialM = typeof(Cozy.Grid.SinkPile).GetMethod("TakeDenialOf");
  var noRoom = typeof(Cozy.Grid.SinkPile).GetField("NoRoomBelow");
  var cancel = typeof(Cozy.Grid.GridCursor).GetMethod("CancelHandMove", NP | System.Reflection.BindingFlags.Public);
  if (denialM == null) info.Append("⏳ в play старый код: SinkPile.TakeDenialOf нет — PK06/PK07 по правилу «есть куда опустить» не проверены; ");
  int takes = 0, denied = 0;
  for (int ci = 0; ci < combos.Length; ci++)
  for (int t = 0; t < combos[ci].Length; t++) {
    var origin = baseO + new UnityEngine.Vector3(40f, 0f, ci * 6f);
    var made = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    bool moving = false;
    try {
      var sink = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById("home_sink"), origin, 0f });
      made.Add(sink); UnityEngine.Physics.SyncTransforms();
      var pile = sink.GetComponent<Cozy.Grid.SinkPile>();
      var inside = sink.GetComponent<Cozy.Grid.LiquidVolume>().FullWorldBounds().center;
      var dishes = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
      int k = 0;
      foreach (var id in combos[ci]) {
        var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(gc, new object[]{ Cozy.Grid.FurnitureCatalog.ById(id), origin + new UnityEngine.Vector3(3f + k++, 0f, 3f), 0f });
        made.Add(io);
        if (!pile.HasRoom(io)) continue;
        io.transform.position = inside; UnityEngine.Physics.SyncTransforms();
        upd.Invoke(pile, null); UnityEngine.Physics.SyncTransforms();
        dishes.Add(io);
      }
      upd.Invoke(pile, null); UnityEngine.Physics.SyncTransforms();
      if (t >= dishes.Count) continue;
      var target = dishes[t];
      string where = "[" + string.Join("+", combos[ci]) + "] снять " + target.Def.id + "#" + t;
      string why = denialM != null ? (string)denialM.Invoke(null, new object[]{ target }) : null;
      if (why != null) {
        denied++;
        bool anyOn = false; string hint = null;
        foreach (var f in target.Features) if (f.Available) foreach (var b in f.Buttons(null)) if (b.Label == "Переместить" || b.Label == "Подобрать") { if (b.Enabled) anyOn = true; hint = b.Hint; }
        Check(!anyOn && hint == (string)noRoom.GetValue(null), "PK07 " + where + ": отказ «" + why + "», а кнопка активна=" + anyOn + ", подсказка «" + hint + "»");
        continue;
      }
      takes++;
      var was = new System.Collections.Generic.Dictionary<Cozy.Grid.InteractiveObject, UnityEngine.Vector3>();
      foreach (var d in dishes) if (d != target) was[d] = d.transform.position;
      System.Func<Cozy.Grid.InteractiveObject, Cozy.Grid.InteractiveObject, bool> meet = (x, y) => { var bx = x.WorldBounds; var by = y.WorldBounds; bx.Expand(-0.012f); by.Expand(-0.012f); return bx.Intersects(by); };
      var metBefore = new System.Collections.Generic.HashSet<long>();
      foreach (var x in dishes) foreach (var y in dishes) if (x != y && meet(x, y)) metBefore.Add((long)x.GetInstanceID() * 100000L + y.GetInstanceID());
      gc.BeginHandMove(target); moving = true;
      UnityEngine.Physics.SyncTransforms();
      var held = gc.MovingObject as Cozy.Grid.InteractiveObject;
      int riders = 0; foreach (var d in dishes) if (d != target && d.transform.IsChildOf(target.transform)) riders++;
      Check(held == target && riders == 0, "PK05 " + where + ": в руке " + (held == null ? "ничего" : held.Def.id) + ", прицепилось " + riders);
      upd.Invoke(pile, null); UnityEngine.Physics.SyncTransforms();
      foreach (var kv in was) {
        var now = kv.Key.transform.position;
        float dxz = new UnityEngine.Vector2(now.x - kv.Value.x, now.z - kv.Value.z).magnitude;
        Check(dxz <= 0.05f && now.y <= kv.Value.y + 0.01f, "PK06 " + where + ": " + kv.Key.Def.id + " не осел, а сдвинулся на " + (dxz * 100f).ToString("0.0") + " см вбок, по высоте " + ((now.y - kv.Value.y) * 100f).ToString("0.0") + " см");
      }
      var rest = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(was.Keys);
      for (int a = 0; a < rest.Count; a++) for (int b2 = a + 1; b2 < rest.Count; b2++) {
        if (metBefore.Contains((long)rest[a].GetInstanceID() * 100000L + rest[b2].GetInstanceID())) continue;
        bool rests = rest[a].Def.id == "frying_pan" || rest[b2].Def.id == "frying_pan" || rest[a].Def.id == "plate" && rest[b2].Def.id == "plate";
        if (rests) continue;
        Check(!meet(rest[a], rest[b2]), "PK06 " + where + ": после снятия " + rest[a].Def.id + " и " + rest[b2].Def.id + " входят друг в друга (до снятия не входили)");
      }
    } finally {
      if (moving && cancel != null) cancel.Invoke(gc, null);
      foreach (var io in made) if (io != null) UnityEngine.Object.DestroyImmediate(io.gameObject);
    }
  }
  info.Append("снятий " + takes + ", отказов «некуда опустить» " + denied + "; ");
} finally {
  foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All)) if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
  player.transform.position = savedP; cam.transform.SetPositionAndRotation(savedCP, savedCR); UnityEngine.Physics.SyncTransforms();
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — постановок 3, составов " + combos.Length + ", предметов " + items + ", прицелов " + aimsAll + ", не влезло в горку " + refused + " (созданное удалено)\n" + sb + (info.Length > 0 ? "INFO " + info : "");
