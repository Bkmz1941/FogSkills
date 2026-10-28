if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var lu = typeof(Cozy.Grid.PadlockView).GetMethod("LateUpdate", NP);
var contactOf = typeof(Cozy.Grid.PadlockView).GetMethod("Contact", NP);
System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Vector3> ContactAt = o =>
    o.transform.TransformPoint((UnityEngine.Vector3)contactOf.Invoke(o.GetComponent<Cozy.Grid.PadlockView>(), new object[] { Cozy.Grid.Padlocks.Shut(o) ? 0f : 1f }));
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var shutGate = typeof(Cozy.Grid.GridCursor).GetMethod("ShutLock", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
Cozy.Grid.InteractiveObject host = null, table = null;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null) continue;
    if (io.TakesPadlock && io.PadlockPoint != null && host == null) host = io;
    if (io.Def.id == "office_desk" && table == null) table = io;
}
var stand = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
System.Func<string, UnityEngine.Vector3, Cozy.Grid.InteractiveObject> Stand = (id, at) =>
{
    var o = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { Cozy.Grid.FurnitureCatalog.ById(id), at, 0f });
    stand.Add(o);
    return o;
};
if (host == null) { host = Stand("meter_outdoor", new UnityEngine.Vector3(520f, 0f, 500f)); sb.Append("стенд: свой meter_outdoor\n"); }
if (table == null) { table = Stand("office_desk", new UnityEngine.Vector3(530f, 0f, 500f)); sb.Append("стенд: свой office_desk\n"); }
if (host == null || host.PadlockPoint == null || table == null) { foreach (var o in stand) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject); return "НЕЧЕГО ПРОВЕРЯТЬ: не собрать стенд"; }
var def = Cozy.Grid.FurnitureCatalog.ById("padlock_4");
float top = float.MinValue;
foreach (var c in table.GetComponentsInChildren<UnityEngine.Collider>()) top = UnityEngine.Mathf.Max(top, c.bounds.max.y);
var made = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
System.Func<UnityEngine.Vector3, Cozy.Grid.InteractiveObject> Make = at =>
{
    var o = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { def, at, 0f });
    made.Add(o);
    return o;
};
System.Action<Cozy.Grid.InteractiveObject, bool> SetShut = (o, shut) =>
{
    foreach (var f in o.Features)
        if (f is Cozy.Grid.AccessFeature a) { if (shut) { a.SetOpen(false); a.Lock(o.Def.lockKeyCode); } else { a.Unlock(); a.SetOpen(true); } }
};
System.Action<Cozy.Grid.InteractiveObject> Settle = o => { var v = o.GetComponent<Cozy.Grid.PadlockView>(); for (int i = 0; i < 40; i++) lu.Invoke(v, null); };
System.Func<Cozy.Grid.InteractiveObject, UnityEngine.Bounds[]> Parts = o =>
{
    UnityEngine.Transform sh = null;
    foreach (var t in o.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == "Shackle") sh = t;
    var body = new UnityEngine.Bounds(); var shk = new UnityEngine.Bounds(); bool fb = true, fs = true;
    foreach (var r in o.GetComponentsInChildren<UnityEngine.MeshRenderer>())
    {
        if (Cozy.Grid.InteractHighlight.IsCopy(r)) continue;
        if (r.transform.IsChildOf(sh)) { if (fs) { shk = r.bounds; fs = false; } else shk.Encapsulate(r.bounds); }
        else { if (fb) { body = r.bounds; fb = false; } else body.Encapsulate(r.bounds); }
    }
    return new[] { body, shk };
};
System.Func<Cozy.Grid.InteractiveObject, float> LegDepth = o =>
{
    UnityEngine.Transform sh = null;
    foreach (var t in o.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == "Shackle") sh = t;
    float bodyTop = float.MinValue, legLow = float.MaxValue;
    foreach (var mf in o.GetComponentsInChildren<UnityEngine.MeshFilter>())
    {
        if (mf.sharedMesh == null || Cozy.Grid.InteractHighlight.IsCopy(mf.GetComponent<UnityEngine.Renderer>())) continue;
        var mb = mf.sharedMesh.bounds;
        bool onShackle = sh != null && mf.transform.IsChildOf(sh);
        for (int i = 0; i < 8; i++)
        {
            var c = mb.center + UnityEngine.Vector3.Scale(mb.extents, new UnityEngine.Vector3((i & 1) == 0 ? -1f : 1f, (i & 2) == 0 ? -1f : 1f, (i & 4) == 0 ? -1f : 1f));
            float y = o.transform.InverseTransformPoint(mf.transform.TransformPoint(c)).y;
            if (onShackle) legLow = UnityEngine.Mathf.Min(legLow, y); else bodyTop = UnityEngine.Mathf.Max(bodyTop, y);
        }
    }
    return bodyTop - legLow;
};
int fails = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || !Cozy.Grid.Padlocks.Hung(io)) continue;
    var at = io.transform.parent;
    float d = (ContactAt(io) - at.position).magnitude;
    bool okHung = d < 0.02f;
    if (!okHung) fails++;
    sb.Append((okHung ? "OK " : "FAIL ") + "уже висит на уровне (" + at.name + "): дужка от точки " + (d * 100f).ToString("0.0") + " см\n");
}
var basePos = table.transform.position;
basePos.y = top;
try
{
    foreach (bool shut in new[] { false, true })
    {
        var lk = Make(basePos + new UnityEngine.Vector3(shut ? 0.3f : -0.3f, 0f, 0f));
        SetShut(lk, shut);
        Settle(lk);
        var pb = Parts(lk);
        float above = pb[1].max.y - pb[0].max.y, sink = pb[1].min.y - top;
        float gap = UnityEngine.Mathf.Max(0f, UnityEngine.Mathf.Max(pb[0].min.x - pb[1].max.x, pb[1].min.x - pb[0].max.x, pb[0].min.z - pb[1].max.z, pb[1].min.z - pb[0].max.z));
        bool ok = above <= 0.01f && sink >= -0.005f && gap < 0.005f;
        if (!ok) fails++;
        sb.Append((ok ? "OK " : "FAIL ") + "лежит " + (shut ? "закрытый" : "открытый") + ": дужка выше корпуса " + (above * 100f).ToString("0.0") + " см, в столе " + (-sink * 100f).ToString("0.0") + " см, зазор с корпусом " + (gap * 100f).ToString("0.0") + " см\n");

        if (shutGate != null)
        {
            bool gate = (bool)shutGate.Invoke(null, new object[] { lk.transform });
            bool okGate = gate == shut;
            if (!okGate) fails++;
            sb.Append((okGate ? "OK " : "FAIL ") + "запрет вешать " + (shut ? "закрытый" : "открытый") + ": " + gate + "\n");
        }
      foreach (bool load in new[] { false, true })
      {
        var point = host.PadlockPoint;
        if (load) { lk = Make(basePos + new UnityEngine.Vector3(0f, 0f, shut ? 0.3f : -0.3f)); SetShut(lk, shut); Settle(lk); }
        var tr = lk.transform;
        if (load)
        {
            var keep = new System.Collections.Generic.List<UnityEngine.Transform>();
            for (int i = 0; i < point.childCount; i++) keep.Add(point.GetChild(i));
            foreach (var k in keep) k.SetParent(null, true);
            host.HangPadlock(lk);
            Settle(lk);
            foreach (var k in keep) k.SetParent(point, true);
        }
        else
        {
            tr.rotation = UnityEngine.Quaternion.LookRotation(-host.PadlockOut, UnityEngine.Vector3.up);
            tr.position += point.position - Cozy.Grid.DoorPiece.PadlockAnchor(tr).position;
            tr.SetParent(point, true);
            lk.GetComponent<Cozy.Grid.PadlockView>().HangNow();
            Settle(lk);
        }
        var hb = Parts(lk);
        float off = (ContactAt(lk) - point.position).magnitude;
        bool through = hb[1].Contains(new UnityEngine.Vector3(point.position.x, hb[1].center.y, point.position.z));
        bool below = hb[0].center.y < point.position.y;
        float bodyOut = UnityEngine.Mathf.Abs(UnityEngine.Vector3.Dot(hb[0].center - point.position, host.PadlockOut));
        float shkOut = UnityEngine.Mathf.Abs(UnityEngine.Vector3.Dot(hb[1].center - point.position, host.PadlockOut));
        Cozy.Grid.AccessFeature hostAccess = null;
        foreach (var f in host.Features) if (f is Cozy.Grid.AccessFeature haf) hostAccess = haf;
        bool barred = hostAccess == null || hostAccess.Barred;
        if (!barred) fails++;
        sb.Append((barred ? "OK " : "FAIL ") + "дверца не открывается, пока висит " + (shut ? "закрытый" : "открытый") + "\n");
        var along = UnityEngine.Vector3.Cross(UnityEngine.Vector3.up, host.PadlockOut).normalized;
        float lean = UnityEngine.Vector3.Dot(hb[0].center - point.position, along);
        bool plumb = UnityEngine.Mathf.Abs(lean) < 0.01f;
        if (!plumb) fails++;
        sb.Append((plumb ? "OK " : "FAIL ") + "корпус под точкой подвеса (" + (shut ? "закрытый" : "открытый") + "): вбок " + (lean * 100f).ToString("0.0") + " см\n");
        float depth = LegDepth(lk);
        float refDepth = shut ? 0.036f : 0.014f, refWall = shut ? 0.016f : 0.044f;
        bool asRef = UnityEngine.Mathf.Abs(depth - refDepth) < 0.003f && UnityEngine.Mathf.Abs(bodyOut - refWall) < 0.005f;
        if (!asRef) fails++;
        sb.Append((asRef ? "OK " : "FAIL ") + "ЭТАЛОН 18.10 (" + (shut ? "закрытый" : "открытый") + "): ножка " + (depth * 100f).ToString("0.0") + " см (эталон " + (refDepth * 100f).ToString("0.0") + " ±0,3), от стены " + (bodyOut * 100f).ToString("0.0") + " см (эталон " + (refWall * 100f).ToString("0.0") + " ±0,5)\n");
        bool legIn = depth > 0.003f;
        if (!legIn) fails++;
        sb.Append((legIn ? "OK " : "FAIL ") + "длинная ножка в корпусе (" + (shut ? "закрытый" : "открытый") + "): заходит на " + (depth * 100f).ToString("0.0") + " см\n");
        bool hok = off < 0.02f && through && below && bodyOut < (shut ? 0.06f : 0.12f) && shkOut < (shut ? 0.06f : 0.12f);
        if (!hok) fails++;
        sb.Append((hok ? "OK " : "FAIL ") + "висит " + (shut ? "закрытый" : "открытый") + (load ? " (загрузка уровня)" : " (постановка рукой)") + " на " + host.Def.id + ": дужка от точки " + (off * 100f).ToString("0.0") + " см, дужка через пробой=" + through + ", корпус ниже=" + below + ", от стены корпус " + (bodyOut * 100f).ToString("0.0") + " см, дужка " + (shkOut * 100f).ToString("0.0") + " см\n");
      }
    }
}
finally
{
    foreach (var o in made) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject);
    foreach (var o in stand) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject);
}
int total = 0;
foreach (var l in sb.ToString().Split('\n')) if (l.StartsWith("OK ") || l.StartsWith("FAIL ")) total++;
return (fails == 0 ? "ЗЕЛЁНОЕ из " + total : "КРАСНОЕ: " + fails + " из " + total) + " (свои замки, созданы и удалены)\n" + sb;
