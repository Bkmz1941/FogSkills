if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0, skips = 0;
System.Action<bool, string> Check = (ok, line) => { if (!ok) fails++; sb.Append(ok ? "OK " : "FAIL ").Append(line).Append('\n'); };
System.Action<string> Skip = line => { skips++; sb.Append("SKIP ").Append(line).Append('\n'); };
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var lu = typeof(Cozy.Grid.PadlockView).GetMethod("LateUpdate", NP);
var contactOf = typeof(Cozy.Grid.PadlockView).GetMethod("Contact", NP);
var doorAccess = typeof(Cozy.Grid.DoorPiece).GetField("_access", NP);
var shutGate = typeof(Cozy.Grid.GridCursor).GetMethod("ShutLock", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var made = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
var far = new UnityEngine.Vector3(500f, 0f, 500f);
System.Func<string, Cozy.Grid.InteractiveObject> Make = id =>
{
    var o = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { Cozy.Grid.FurnitureCatalog.ById(id), far + UnityEngine.Vector3.right * made.Count, 0f });
    made.Add(o);
    return o;
};
System.Action<Cozy.Grid.InteractiveObject> Settle = o => { var v = o.GetComponent<Cozy.Grid.PadlockView>(); for (int i = 0; i < 40; i++) lu.Invoke(v, null); };
System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3> ContactAt = o =>
    o.transform.TransformPoint((UnityEngine.Vector3)contactOf.Invoke(o.GetComponent<Cozy.Grid.PadlockView>(), new object[] { Cozy.Grid.Padlocks.Shut(o) ? 0f : 1f }));
System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Bounds> Body = o =>
{
    UnityEngine.Transform sh = null;
    foreach (var t in o.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == "Shackle") sh = t;
    var b = new UnityEngine.Bounds(); bool first = true;
    foreach (var r in o.GetComponentsInChildren<UnityEngine.MeshRenderer>())
    {
        if (Cozy.Grid.InteractHighlight.IsCopy(r) || sh != null && r.transform.IsChildOf(sh)) continue;
        if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
    }
    return b;
};

var keys = Cozy.Grid.Items.Keys;
var codes = new System.Collections.Generic.HashSet<string>();
foreach (var k in keys)
{
    Check(codes.Add(k.keyCode), "DR-I02 код " + k.keyCode + " у " + k.id + " не повторяется");
    Check(Cozy.Grid.Items.KeyByCode(k.keyCode) == k, "DR-I02 KeyByCode(" + k.keyCode + ") = " + k.id);
    var def = Cozy.Grid.FurnitureCatalog.ById(k.id);
    bool icon = UnityEngine.Resources.Load<UnityEngine.Sprite>("Icons/" + k.icon) != null;
    Check(k.size == UnityEngine.Vector2Int.one && UnityEngine.Mathf.Approximately(k.weight, 0.1f) && icon && def != null && def.pickupItemId == k.id,
        "DR-I01 " + k.id + ": 1×1=" + (k.size == UnityEngine.Vector2Int.one) + ", вес " + k.weight + ", иконка=" + icon + ", деф=" + (def != null) + ", подбор=" + (def != null ? def.pickupItemId : "-"));
    Check(def != null && def.examinePopup, "DR-I04 " + k.id + ": осмотр попапом");
    if (def != null && k.id.StartsWith("old_key_")) Check(UnityEngine.Mathf.Approximately(def.modelScale, 0.7f), "DR-I06 " + k.id + ": масштаб " + def.modelScale + " (ждём 0,7)");
}

var padlockIds = new System.Collections.Generic.List<string>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All())
    if (d != null && d.onDoor && !padlockIds.Contains(d.id)) padlockIds.Add(d.id);
Check(padlockIds.Count >= 4, "дефов замков (onDoor): " + padlockIds.Count);

try
{
    foreach (var id in padlockIds)
    {
        var def = Cozy.Grid.FurnitureCatalog.ById(id);
        var own = Cozy.Grid.Items.KeyByCode(def.lockKeyCode);
        Check(own != null, "DR-I05 " + id + ": свой ключ " + def.lockKeyCode + " = " + (own != null ? own.id : "НЕТ"));
        Check(UnityEngine.Mathf.Approximately(def.modelScale, 0.64f), "DR-P07 " + id + ": масштаб " + def.modelScale + " (ждём 0,64)");
        Check(!def.examinePopup, "DR-P09 " + id + ": осмотр приближением, не попапом");
        var lk = Make(id);
        Settle(lk);
        var a = Cozy.Grid.Padlocks.Access(lk);
        Check(a != null && !a.Locked && a.KeyCode == def.lockKeyCode, "DR-P01 " + id + ": рождается открытым с ключом " + (a != null ? a.KeyCode : "-"));
        if (a == null || own == null) continue;
        Cozy.Grid.ItemDef stranger = null;
        foreach (var k in keys) if (k.keyCode != own.keyCode) { stranger = k; break; }
        a.ApplyKey(stranger);
        Check(!a.Locked, "DR-P03 " + id + ": чужой ключ " + stranger.keyCode + " не закрывает");
        a.ApplyKey(own);
        Check(a.Locked, "DR-P02 " + id + ": свой ключ закрывает");
        a.ApplyKey(stranger);
        Check(a.Locked, "DR-P03 " + id + ": чужой ключ не открывает");
        string state = Cozy.Grid.LiquidState.Of(lk);
        var copy = Make(id);
        Cozy.Grid.LiquidState.Apply(copy, state);
        var ca = Cozy.Grid.Padlocks.Access(copy);
        Check(ca != null && ca.Locked && ca.KeyCode == own.keyCode, "DR-P08 " + id + ": закрытый через метку «" + state + "» остаётся закрытым на " + (ca != null ? ca.KeyCode : "-"));
        a.ApplyKey(own);
        Check(!a.Locked, "DR-P02 " + id + ": свой ключ открывает");
        Settle(lk);
        var hull = new UnityEngine.Bounds(); bool firstBox = true;
        foreach (var c in lk.GetComponents<UnityEngine.BoxCollider>())
            if (!c.isTrigger) { if (firstBox) { hull = c.bounds; firstBox = false; } else hull.Encapsulate(c.bounds); }
        float boxH = hull.size.y;
        float bodyH = Body(lk).size.y;
        Check(UnityEngine.Mathf.Abs(boxH - bodyH) < 0.005f, "DR-P05 " + id + ": коробки лёжа вместе " + (boxH * 100f).ToString("0.0") + " см, корпус " + (bodyH * 100f).ToString("0.0") + " см");
    }

    foreach (var io in Cozy.Grid.InteractiveObject.All)
        if (io != null && io.Def != null && io.Def.id == "meter_outdoor_broken")
            Check(io.TakesPadlock, "DR-H11 сломанный счётчик: точка подвеса есть, замок вешается (Илья 18.10)");

    Cozy.Grid.InteractiveObject meter = null;
    foreach (var io in Cozy.Grid.InteractiveObject.All)
        if (io != null && io.TakesPadlock && !io.PadlockHung && !made.Contains(io)) { meter = io; break; }
    if (meter == null) Skip("DR-M01/M03/M04: нет свободного хозяина с точкой подвеса");
    else
    {
        Cozy.Grid.AccessFeature ma = null;
        foreach (var f in meter.Features) if (f is Cozy.Grid.AccessFeature af) ma = af;
        bool wasOpen = ma.Open;
        ma.SetOpen(true);
        Check(ma.Open, "DR-M01 " + meter.Def.id + ": без замка дверца открывается");
        Check(meter.PadlockBusy, "DR-M03 " + meter.Def.id + ": открытая дверца — точка занята для подвеса");
        ma.SetOpen(false);
        Check(!ma.Open, "DR-M01 " + meter.Def.id + ": закрывается");
        var lk = Make(padlockIds[0]);
        meter.HangPadlock(lk);
        Settle(lk);
        ma.SetOpen(true);
        Check(!ma.Open, "PT-L05 " + meter.Def.id + ": с открытым замком дверца не открывается");
        UnityEngine.Object.DestroyImmediate(lk.gameObject);
        ma.SetOpen(true);
        Check(ma.Open, "DR-M04 " + meter.Def.id + ": замок снят — дверца открывается");
        ma.SetOpen(wasOpen);
    }

    foreach (var door in Cozy.Grid.DoorPiece.All)
    {
        if (door == null) continue;
        bool shouldLock = door.style != Cozy.Grid.DoorStyle.HomeFlat && door.style != Cozy.Grid.DoorStyle.OldPlank;
        Check(door.Lockable == shouldLock, "DR-K01 " + door.style + ": свой замок=" + door.Lockable + " (ждём " + shouldLock + ")");
        var access = (Cozy.Grid.AccessFeature)doorAccess.GetValue(door);
        if (access == null) continue;
        bool wasLocked = door.Locked, wasOpen = door.IsOpen;
        string wasCode = access.KeyCode;
        var borrowed = new System.Collections.Generic.List<(Cozy.Grid.InteractiveObject io, int side, bool locked, string code)>();
        try
        {
            if (door.Lockable)
            {
                if (door.PadlockHung) { Skip("DR-K02..K05 " + door.style + ": на двери висит замок уровня"); continue; }
                access.Unlock();
                access.SetOpen(false);
                access.KeyCode = "";
                var first = keys[0];
                access.ApplyKey(first);
                Check(door.Locked && access.KeyCode == first.keyCode && Cozy.Grid.AccessFeature.ColorsMatch(access.LockColor, first.color),
                    "DR-K02 " + door.style + ": пустая дверь запирается любым ключом и берёт его код (" + access.KeyCode + ")");
                access.ApplyKey(keys[1]);
                Check(door.Locked, "DR-K03 " + door.style + ": чужой ключ " + keys[1].keyCode + " не отпирает");
                access.SetOpen(true);
                Check(!door.IsOpen && door.Barred, "DR-K06 " + door.style + ": запертая не открывается");
                access.ApplyKey(first);
                Check(!door.Locked && access.KeyCode == first.keyCode, "DR-K04 " + door.style + ": свой ключ отпирает, код остаётся");
                access.SetOpen(true);
                Check(door.IsOpen, "DR-D01 " + door.style + ": отпертая открывается");
                access.ApplyKey(first);
                Check(!door.Locked, "DR-K05 " + door.style + ": открытую не запереть");
                access.SetOpen(false);
                Check(!door.IsOpen, "DR-D01 " + door.style + ": закрывается");
            }
            else if (!door.TakesPadlocks)
            {
                access.SetOpen(true);
                Check(door.IsOpen, "DR-D01 " + door.style + ": открывается");
                access.SetOpen(false);
                Check(!door.IsOpen, "DR-D01 " + door.style + ": закрывается");
            }
            if (!door.TakesPadlocks) continue;
            for (int side = 0; side < 2; side++)
            {
                var own = door.PadlockOn(side);
                if (own == null) continue;
                var oa = Cozy.Grid.Padlocks.Access(own);
                borrowed.Add((own, side, oa != null && oa.Locked, oa != null ? oa.KeyCode : ""));
                if (oa != null) oa.Unlock();
                own.transform.SetParent(null, true);
                own.transform.position += far + UnityEngine.Vector3.forward * (10f + side);
            }
            if (borrowed.Count > 0) sb.Append("стенд: замки уровня на старой двери сняты на время пробы: " + borrowed.Count + "\n");
            // С 20.10 у старой двери точка подвеса одна — снаружи (`PadlockA`); изнутри щеколда (P1160).
            Check(door.PadlockPoint(1) == null, "DR-H12 " + door.style + ": изнутри точки подвеса нет (только щеколда)");
            for (int side = 0; side < 1; side++)
            {
                var point = door.PadlockPoint(side);
                if (point == null) { Check(false, "DR-H01 " + door.style + " сторона " + side + ": точки нет"); continue; }
                if (door.PadlockOn(side) != null) { Skip("DR-H01..H07 сторона " + side + ": занята замком уровня"); continue; }
                if (door.PadlockHung) { Skip("DR-H04..H07 сторона " + side + ": на другой стороне замок уровня"); continue; }
                access.SetOpen(false);
                var lk = Make(padlockIds[side % padlockIds.Count]);
                door.HangPadlock(lk, side);
                Settle(lk);
                float off = (ContactAt(lk) - point.position).magnitude;
                bool below = Body(lk).center.y < point.position.y;
                Check(off < 0.02f && below && door.PadlockOn(side) == lk, "DR-H01 " + door.style + " сторона " + side + ": дужка от точки " + (off * 100f).ToString("0.0") + " см, корпус ниже=" + below);
                access.SetOpen(true);
                Check(!door.IsOpen && door.Barred, "DR-H04 сторона " + side + ": с открытым замком дверь не открывается");
                var la = Cozy.Grid.Padlocks.Access(lk);
                la.ApplyKey(Cozy.Grid.Items.KeyByCode(lk.Def.lockKeyCode));
                Check(door.PadlockShut, "DR-H05 сторона " + side + ": замок закрыт ключом, дверь заперта");
                if (shutGate != null) Check((bool)shutGate.Invoke(null, new object[] { lk.transform }), "DR-H06 сторона " + side + ": закрытый замок не перенести");
                la.ApplyKey(Cozy.Grid.Items.KeyByCode(lk.Def.lockKeyCode));
                made.Remove(lk);
                UnityEngine.Object.DestroyImmediate(lk.gameObject);
                access.SetOpen(true);
                Check(door.IsOpen, "DR-H07 сторона " + side + ": замок снят — дверь открывается");
                access.SetOpen(false);
            }
        }
        finally
        {
            access.Unlock();
            access.KeyCode = wasCode;
            if (wasLocked) { access.SetOpen(false); access.Lock(wasCode); }
            else access.SetOpen(wasOpen);
            foreach (var b in borrowed)
            {
                if (b.io == null) continue;
                door.HangPadlock(b.io, b.side);
                var ba = Cozy.Grid.Padlocks.Access(b.io);
                if (b.locked && ba != null) ba.Lock(b.code);
                Settle(b.io);
                Check(door.PadlockOn(b.side) == b.io && (ba == null || ba.Locked == b.locked), "стенд: замок уровня возвращён на сторону " + b.side + (b.locked ? " закрытым" : " открытым"));
            }
        }
    }

    // ---------- щеколда изнутри (Илья 20.10; P1160, P1161, P1162) ----------
    var fBolt = typeof(Cozy.Grid.DoorPiece).GetField("_latchBolt", NP);
    var fSide = typeof(Cozy.Grid.DoorPiece).GetField("_latchSide", NP);
    var fRoot = typeof(Cozy.Grid.DoorPiece).GetField("_latchRoot", NP);
    var upLatch = typeof(Cozy.Grid.DoorPiece).GetMethod("UpdateLatch", NP);
    var fLeafT = typeof(Cozy.Grid.DoorPiece).GetField("_t", NP);
    var doorUpdate = typeof(Cozy.Grid.DoorPiece).GetMethod("Update", NP);
    foreach (var door in Cozy.Grid.DoorPiece.All)
    {
        if (door == null) continue;
        bool kit = door.style == Cozy.Grid.DoorStyle.OldPlank || door.style == Cozy.Grid.DoorStyle.WoodModern || door.style == Cozy.Grid.DoorStyle.SteelModern;
        bool wants = kit || door.style == Cozy.Grid.DoorStyle.Steel || door.style == Cozy.Grid.DoorStyle.WhiteFlat || door.style == Cozy.Grid.DoorStyle.HomeFlat;
        if (door.style == Cozy.Grid.DoorStyle.GlassModern) wants = false;
        if (!wants && !door.HasLatch) continue;
        Check(door.HasLatch == wants, "DR-L01 " + door.style + ": щеколда в модели=" + door.HasLatch + " (ждём " + wants + ")");
        if (!door.HasLatch) continue;
        var access = (Cozy.Grid.AccessFeature)doorAccess.GetValue(door);
        bool wasLatched = door.latched, wasOpen = door.IsOpen, wasLocked = door.Locked;
        string wasCode = access.KeyCode;
        var bolt = (UnityEngine.Transform)fBolt.GetValue(door);
        try
        {
            if (door.PadlockHung) { Skip("DR-L02..L06 " + door.style + ": висит замок уровня"); continue; }
            access.Unlock();
            door.latched = false;
            access.SetOpen(false);
            // створка уровня могла стоять открытой — довести до рамы сразу, иначе щеколда отказывает (ход _t > 0)
            fLeafT.SetValue(door, 0f);
            doorUpdate.Invoke(door, null);
            for (int i = 0; i < 1000; i++) upLatch.Invoke(door, null);  // ход по Time.deltaTime — с запасом до упора
            // Сторона щеколды — по НЕЗАВИСИМОЙ примете: у старой двери снаружи точка навесного (`PadlockA`),
            // у кита изнутри (+Y Blender) — сторона замка `LockB`. Щеколда по центру меша засова (P1160).
            float side = (float)fSide.GetValue(door);
            UnityEngine.Vector3 n = door.Normal, root = door.transform.position;
            UnityEngine.Transform truth = door.style == Cozy.Grid.DoorStyle.OldPlank ? door.PadlockPoint(0) : null;
            if (truth == null)
                foreach (var t in door.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == "LockB") truth = t;
            if (truth != null)
            {
                var tr = truth.GetComponentInChildren<UnityEngine.Renderer>();
                float s = UnityEngine.Mathf.Sign(UnityEngine.Vector3.Dot((tr != null ? tr.bounds.center : truth.position) - root, n));
                bool inside = door.style != Cozy.Grid.DoorStyle.OldPlank;
                Check(inside ? side == s : side == -s, "DR-L02 " + door.style + ": щеколда на внутренней стороне (сторона " + side + ", примета " + s + ")");
            }
            else Skip("DR-L02 " + door.style + ": нет приметы стороны");
            // Закрытая щеколда держит дверь; закрыть открытую нельзя.
            door.SetLatched(true);
            Check(door.latched && door.Barred, "DR-L03 " + door.style + ": щеколда закрыта — дверь заперта (Barred)");
            access.SetOpen(true);
            Check(!door.IsOpen, "DR-L03 " + door.style + ": с закрытой щеколдой не открывается");
            for (int i = 0; i < 1000; i++) upLatch.Invoke(door, null);  // ход по Time.deltaTime — с запасом до упора
            var bShut = bolt.position;
            // Закрытый засов входит в ответную часть на раме/косяке (Илья 20.10, скрин 13-11-15: «нет на стене
            // места, куда щеколда входит»): видимый `LatchKeeper*` пересекается с засовом.
            var boltBox = bolt.GetComponent<UnityEngine.Renderer>().bounds;
            boltBox.Expand(0.01f);
            bool keeperHit = false; int keepers = 0;
            foreach (var r in door.GetComponentsInChildren<UnityEngine.Renderer>())
            {
                bool isKeeper = false;
                for (var p = r.transform; p != null && p != door.transform; p = p.parent) if (p.name.StartsWith("LatchKeeper")) { isKeeper = true; break; }
                if (!isKeeper || Cozy.Grid.InteractHighlight.IsCopy(r)) continue;
                keepers++;
                if (r.bounds.Intersects(boltBox)) keeperHit = true;
            }
            Check(keeperHit, "DR-L13 " + door.style + ": закрытый засов входит в ответную часть (видимых частей " + keepers + ")");
            door.SetLatched(false);
            for (int i = 0; i < 1000; i++) upLatch.Invoke(door, null);  // ход по Time.deltaTime — с запасом до упора
            float travel = (bolt.position - bShut).magnitude;
            Check(travel > 0.05f && travel < 0.2f, "DR-L04 " + door.style + ": засов отъезжает на " + (travel * 100f).ToString("0.0") + " см");
            access.SetOpen(true);
            Check(door.IsOpen, "DR-L03 " + door.style + ": щеколда открыта — дверь открывается");
            door.SetLatched(true);
            Check(!door.latched, "DR-L05 " + door.style + ": открытую дверь щеколдой не закрыть");
            access.SetOpen(false);
            // Материалы засова — слоты кита с картинкой, не «Lit» по умолчанию (P1161).
            var latchRoot = (UnityEngine.Transform)fRoot.GetValue(door);
            bool texOk = true; string bad = "";
            foreach (var r in latchRoot.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
                foreach (var m in r.sharedMaterials)
                    if (m == null || !m.name.StartsWith("doorKit_") || m.mainTexture == null) { texOk = false; bad = r.name + ":" + (m != null ? m.name : "null"); }
            if (kit) Check(texOk, "DR-L06 " + door.style + ": у щеколды материалы кита с картинкой" + (texOk ? "" : " (" + bad + ")"));
            // Глазок — со стороны щеколды (P1166).
            if (Cozy.Grid.DoorPiece.HasPeephole(door.style))
                Check(UnityEngine.Vector3.Dot(door.PeepInsideNormal, n) * side > 0f, "DR-L12 " + door.style + ": глазок изнутри — со стороны щеколды");
        }
        finally
        {
            door.latched = false;
            access.Unlock();
            access.KeyCode = wasCode;
            access.SetOpen(wasOpen);
            if (wasLocked) { access.SetOpen(false); access.Lock(wasCode); }
            door.latched = wasLatched && !door.IsOpen;
            for (int i = 0; i < 1000; i++) upLatch.Invoke(door, null);  // ход по Time.deltaTime — с запасом до упора
        }
    }
    // Фурнитура на одном расстоянии от свободной кромки у всех дверей (Илья 20.10, скрин 13-20-22; P1169): в осях
    // створки `Leaf` кромка на x = −ширина. Щеколда — центр планки 0,28, личинка — 0,22, глазок — по центру ширины.
    var fLeafW = typeof(Cozy.Grid.DoorPiece).GetField("_leafW", NP);
    System.Func<UnityEngine.Transform, UnityEngine.Transform, float> EdgeDist = (leaf, part) =>
    {
        var rs = part.GetComponentsInChildren<UnityEngine.Renderer>(true);
        if (rs.Length == 0) return float.NaN;
        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
        return leaf.InverseTransformPoint(b.center).x;
    };
    foreach (var door in Cozy.Grid.DoorPiece.All)
    {
        if (door == null || door.Leaf == null || door.style == Cozy.Grid.DoorStyle.GlassDouble) continue;
        float lw = (float)fLeafW.GetValue(door);
        UnityEngine.Transform latchBase = null, lockPart = null, peep = null;
        foreach (var t in door.Leaf.GetComponentsInChildren<UnityEngine.Transform>(true))
        {
            if (t.name == "LatchBase" && latchBase == null) latchBase = t;
            else if ((t.name == "LockA" || t.name == "LockRosette") && lockPart == null) lockPart = t;
            else if ((t.name == "PeepholeA" || t.name == "PeepholeRing0") && peep == null) peep = t;
        }
        if (latchBase != null)
        {
            float d = EdgeDist(door.Leaf, latchBase) + lw;
            Check(UnityEngine.Mathf.Abs(d - 0.28f) < 0.03f, "DR-F01 " + door.style + ": щеколда от кромки " + (d * 100f).ToString("0.0") + " см (стандарт 28)");
        }
        if (lockPart != null)
        {
            float d = EdgeDist(door.Leaf, lockPart) + lw;
            Check(UnityEngine.Mathf.Abs(d - 0.22f) < 0.03f, "DR-F02 " + door.style + ": личинка от кромки " + (d * 100f).ToString("0.0") + " см (стандарт 22, под ручкой)");
        }
        if (peep != null)
        {
            float d = EdgeDist(door.Leaf, peep) + lw;
            Check(UnityEngine.Mathf.Abs(d - lw * 0.5f) < 0.05f, "DR-F03 " + door.style + ": глазок от кромки " + (d * 100f).ToString("0.0") + " см (по центру " + (lw * 50f).ToString("0") + ")");
        }
    }
    // Ответная часть на раме: у стекла спрятана, у остальных кита видна.
    foreach (var door in Cozy.Grid.DoorPiece.All)
    {
        if (door == null || door.style != Cozy.Grid.DoorStyle.GlassModern && door.style != Cozy.Grid.DoorStyle.WoodModern) continue;
        foreach (var t in door.GetComponentsInChildren<UnityEngine.Transform>(true))
            if (t.name == "LatchKeeper")
                Check(t.gameObject.activeInHierarchy == (door.style != Cozy.Grid.DoorStyle.GlassModern), "DR-L07 " + door.style + ": ответная часть щеколды " + (t.gameObject.activeInHierarchy ? "видна" : "спрятана"));
    }
}
finally
{
    foreach (var o in made) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject);
}
int total = 0;
foreach (var l in sb.ToString().Split('\n')) if (l.StartsWith("OK ") || l.StartsWith("FAIL ")) total++;
return (fails == 0 ? "ЗЕЛЁНОЕ из " + total : "КРАСНОЕ: " + fails + " из " + total) + (skips > 0 ? ", пропущено " + skips : "") + " (свои замки созданы и удалены, двери уровня возвращены как были)\n" + sb;
