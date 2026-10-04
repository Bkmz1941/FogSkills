if (!UnityEngine.Application.isPlaying) return "не в play";
var T = typeof(Cozy.Grid.Interactor);
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var through = T.GetMethod("ThroughOpening", BF);
var shows = T.GetMethod("ShowsThroughDoor", BF);
var side = T.GetMethod("OpeningSide", BF);
var hits = new UnityEngine.RaycastHit[64];
var sb = new System.Text.StringBuilder();
int rays = 0, ok = 0, blocked = 0, open = 0;
var openedGates = new System.Collections.Generic.List<Cozy.Grid.AccessFeature>();
var pendingKey = "slot_open_probe_opened";
var alreadyOpened = System.AppDomain.CurrentDomain.GetData(pendingKey) as System.Collections.Generic.List<int>;
if (alreadyOpened == null)
{
    var ids = new System.Collections.Generic.List<int>();
    foreach (var gh in Cozy.Grid.InteractiveObject.All)
    {
        if (gh == null || gh.Def == null || string.IsNullOrEmpty(gh.Def.slotNodes)) continue;
        bool hasGuest = false;
        foreach (var gi in gh.GetComponentsInChildren<Cozy.Grid.InteractiveObject>(false)) if (gi != gh && Cozy.Grid.InteractiveObject.NestedInside(gi, gh)) { hasGuest = true; break; }
        if (!hasGuest) continue;
        foreach (var f in gh.Features) if (f is Cozy.Grid.AccessFeature af && !af.Open && !af.Locked) { af.SetOpen(true); ids.Add(gh.GetInstanceID()); }
    }
    if (ids.Count > 0)
    {
        System.AppDomain.CurrentDomain.SetData(pendingKey, ids);
        return "ПОДГОТОВКА: открыл секций " + ids.Count + " — створки доезжают, запусти пробу ещё раз через 2 с (она замерит и закроет их сама)";
    }
}
else
{
    System.AppDomain.CurrentDomain.SetData(pendingKey, null);
    foreach (var gh in Cozy.Grid.InteractiveObject.All)
        if (gh != null && alreadyOpened.Contains(gh.GetInstanceID()))
            foreach (var f in gh.Features) if (f is Cozy.Grid.AccessFeature af && af.Open) openedGates.Add(af);
}
var forcedOn = new System.Collections.Generic.List<UnityEngine.Renderer>();
foreach (var fh in Cozy.Grid.InteractiveObject.All)
{
    if (fh == null || fh.Def == null || string.IsNullOrEmpty(fh.Def.slotNodes)) continue;
    foreach (var fr in fh.GetComponentsInChildren<UnityEngine.MeshRenderer>())
        if (!fr.enabled && !Cozy.Grid.InteractHighlight.IsCopy(fr) && fr.GetComponentInParent<Cozy.Grid.InteractiveObject>() == fh) { fr.enabled = true; forcedOn.Add(fr); }
}
foreach (var host in Cozy.Grid.InteractiveObject.All)
{
    if (host == null || host.Def == null || !(bool)shows.Invoke(null, new object[] { host.Def })) continue;
    foreach (var it in host.GetComponentsInChildren<Cozy.Grid.InteractiveObject>(false))
    {
        if (it == host || !Cozy.Grid.InteractiveObject.NestedInside(it, host)) continue;
        var col = it.GetComponentInChildren<UnityEngine.Collider>();
        if (col == null) continue;
        var dirLocal = (UnityEngine.Vector3)side.Invoke(null, new object[] { host, it });
        var dir = host.transform.TransformDirection(dirLocal);
        var target = col.bounds.center;
        var from = target + dir * (host.WorldBounds.extents.magnitude + 1f);
        int n = UnityEngine.Physics.RaycastNonAlloc(from, (target - from).normalized, hits, 10f, ~0, UnityEngine.QueryTriggerInteraction.Collide);
        UnityEngine.RaycastHit hostHit = new UnityEngine.RaycastHit(); bool gotHost = false, gotItem = false; float hd = 1e9f, idist = 1e9f;
        for (int i = 0; i < n; i++)
        {
            var h = hits[i];
            if (h.collider.transform.IsChildOf(it.transform)) { gotItem = true; idist = UnityEngine.Mathf.Min(idist, h.distance); continue; }
            var owner = h.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>();
            if (owner == host && h.distance < hd) { hd = h.distance; hostHit = h; gotHost = true; }
        }
        if (!gotItem) continue;
        rays++;
        if (!gotHost || idist < hd) { open++; continue; }
        bool lets = (bool)through.Invoke(null, new object[] { hostHit, col, host, from + (target - from).normalized * idist });
        if (lets) ok++; else { blocked++; bool part = host.IsPart(hostHit.collider.transform); sb.Append(host.Def.id + "/" + it.Def.id + " side=" + dirLocal + " hit=" + hostHit.collider.name + (part ? "(часть)" : "") + " секция открыта=" + Cozy.Grid.ContainerSlot.InOpenSlot(it, host) + "; "); }
    }
}
var doorFace = T.GetMethod("DoorFace", BF);
var expect = new System.Collections.Generic.Dictionary<string, UnityEngine.Vector3>
{
    { "home_fridge/Slot_Shelf1", UnityEngine.Vector3.back }, { "home_fridge/Slot_Shelf2", UnityEngine.Vector3.back },
    { "home_fridge/Slot_Floor", UnityEngine.Vector3.back }, { "home_fridge/Slot_Bin", UnityEngine.Vector3.back },
    { "home_fridge/Slot_DoorT", UnityEngine.Vector3.back }, { "home_fridge/Slot_DoorB", UnityEngine.Vector3.back },
    { "home_bathroom_cabinet/Slot_FloorL", UnityEngine.Vector3.back }, { "home_bathroom_cabinet/Slot_FloorR", UnityEngine.Vector3.back },
    { "home_bathroom_cabinet/Slot_Shelf1L", UnityEngine.Vector3.back }, { "home_bathroom_cabinet/Slot_Shelf1R", UnityEngine.Vector3.back },
    { "home_wall_cabinet_corner_wide/Slot_FloorMain0", UnityEngine.Vector3.back }, { "home_wall_cabinet_corner_wide/Slot_ShelfMain0", UnityEngine.Vector3.back },
    { "home_wall_cabinet_corner_wide/Slot_FloorMain1", UnityEngine.Vector3.back }, { "home_wall_cabinet_corner_wide/Slot_ShelfMain2", UnityEngine.Vector3.back },
    { "home_wall_cabinet_corner_wide/Slot_FloorWing", UnityEngine.Vector3.right }, { "home_wall_cabinet_corner_wide/Slot_ShelfWing", UnityEngine.Vector3.right },
    { "home_coffee_machine/Slot_Filter", UnityEngine.Vector3.up }, { "home_bedside_table/Slot_Drawer", UnityEngine.Vector3.up },
    { "home_fireplace/Slot_Fire", UnityEngine.Vector3.back }, { "home_stove/Slot_Oven", UnityEngine.Vector3.back },
    { "hallway_rack/Slot_FloorL", UnityEngine.Vector3.back }, { "hallway_rack/Slot_FloorR", UnityEngine.Vector3.back },
};
int checkedSides = 0, wrongSides = 0;
var sideSb = new System.Text.StringBuilder();
var sideSeen = new System.Collections.Generic.HashSet<string>();
foreach (var host in Cozy.Grid.InteractiveObject.All)
{
    if (host == null || host.Def == null) continue;
    foreach (var slot in host.GetComponentsInChildren<Cozy.Grid.ContainerSlot>(true))
    {
        string key = host.Def.id + "/" + slot.name;
        if (!expect.ContainsKey(key) || !sideSeen.Add(key) || string.IsNullOrEmpty(slot.gateNode)) continue;
        UnityEngine.Transform door = null;
        foreach (var tr in host.GetComponentsInChildren<UnityEngine.Transform>(true)) if (tr.name == slot.gateNode) { door = tr; break; }
        UnityEngine.Vector3 c, n;
        if (door == null || !host.ClosedPanel(door, out c, out n)) { wrongSides++; sideSb.Append(key + " нет створки; "); continue; }
        var t = host.transform;
        var got = (UnityEngine.Vector3)doorFace.Invoke(null, new object[] { t.InverseTransformDirection(n), t.InverseTransformPoint(c) - t.InverseTransformPoint(host.ClosedPoint(slot.transform, slot.transform.position)) });
        checkedSides++;
        if (got != expect[key]) { wrongSides++; sideSb.Append("СТОРОНА НЕВЕРНА " + key + " ждали " + expect[key] + " вышло " + got + "; "); }
    }
}
int partRays = 0, partLeaks = 0, partMiss = 0;
var partSb = new System.Text.StringBuilder();
var partHits = new UnityEngine.RaycastHit[64];
foreach (var host in Cozy.Grid.InteractiveObject.All)
{
    if (host == null || host.Def == null || host.Def.parts == null || host.Def.parts.Count == 0) continue;
    foreach (var it in host.GetComponentsInChildren<Cozy.Grid.InteractiveObject>(false))
    {
        if (it == host) continue;
        var col = it.GetComponentInChildren<UnityEngine.Collider>();
        if (col == null) continue;
        var dirs = new[] { host.transform.forward, -host.transform.forward, host.transform.right, -host.transform.right, UnityEngine.Vector3.down };
        foreach (var d in dirs)
        {
            var target = col.bounds.center;
            int n = UnityEngine.Physics.RaycastNonAlloc(target - d * 3f, d, partHits, 4f, ~0, UnityEngine.QueryTriggerInteraction.Collide);
            UnityEngine.RaycastHit hh = new UnityEngine.RaycastHit(); float hd = 1e9f, idist = 1e9f; bool gh = false;
            for (int i = 0; i < n; i++)
            {
                var h = partHits[i];
                if (h.collider.transform.IsChildOf(it.transform)) { idist = UnityEngine.Mathf.Min(idist, h.distance); continue; }
                if (h.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() == host && h.distance < hd) { hd = h.distance; hh = h; gh = true; }
            }
            if (!gh || idist < hd || !host.IsPart(hh.collider.transform) || !col.transform.IsChildOf(hh.collider.transform)) continue;
            partRays++;
            bool outer = host.HitsOuterFace(hh.collider.transform, hh.normal);
            bool front = UnityEngine.Vector3.Dot(hh.normal, target - hh.point) > 0f;
            bool lets = (bool)through.Invoke(null, new object[] { hh, col, host, target - d * 3f + d * idist });
            if (outer && !front && lets) { partLeaks++; partSb.Append("УТЕЧКА " + host.Def.id + "/" + it.Def.id + " сквозь наружную " + hh.collider.name + "; "); }
            if (!outer && !lets && Cozy.Grid.ContainerSlot.InOpenSlot(it, host)) { partMiss++; partSb.Append("НЕДОСТУПНО " + host.Def.id + "/" + it.Def.id + " с внутренней " + hh.collider.name + "; "); }
        }
    }
}
foreach (var fr in forcedOn) if (fr != null) fr.enabled = false;
foreach (var af in openedGates) af.SetOpen(false);
return "секций открыто пробой и закрыто обратно=" + openedGates.Count + " | на деталях: лучей=" + partRays + " утечек=" + partLeaks + " недоступно=" + partMiss + " :: " + partSb + " || через проём: лучей=" + rays + " видно напрямую=" + open + " пропущено=" + ok + " ЗАКРЫТО=" + blocked + " стороны: сверено=" + checkedSides + " неверных=" + wrongSides + " :: " + sideSb + sb;
