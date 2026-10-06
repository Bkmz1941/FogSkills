if (!UnityEngine.Application.isPlaying) return "не в play";
var BF = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static;
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
var pick = typeof(Cozy.Grid.GridCursor).GetMethod("NearestVisiblePiece", BF);
var side = typeof(Cozy.Grid.Interactor).GetMethod("OpeningSide", BF);
var shows = typeof(Cozy.Grid.Interactor).GetMethod("ShowsThroughDoor", BF);
var pendingKey = "build_pick_probe_opened";
var opened = System.AppDomain.CurrentDomain.GetData(pendingKey) as System.Collections.Generic.List<int>;
if (opened == null)
{
    var ids = new System.Collections.Generic.List<int>();
    foreach (var gh in Cozy.Grid.InteractiveObject.All)
    {
        if (gh == null || gh.Def == null || string.IsNullOrEmpty(gh.Def.slotNodes)) continue;
        foreach (var f in gh.Features) if (f is Cozy.Grid.AccessFeature af && !af.Open && !af.Locked) { af.SetOpen(true); if (!ids.Contains(gh.GetInstanceID())) ids.Add(gh.GetInstanceID()); }
    }
    if (ids.Count > 0)
    {
        System.AppDomain.CurrentDomain.SetData(pendingKey, ids);
        return "ПОДГОТОВКА: открыл секций у " + ids.Count + " хозяев — запусти пробу ещё раз через 2 с";
    }
}
System.AppDomain.CurrentDomain.SetData(pendingKey, null);
var forced = new System.Collections.Generic.List<UnityEngine.Renderer>();
foreach (var fh in Cozy.Grid.InteractiveObject.All)
{
    if (fh == null || fh.Def == null || string.IsNullOrEmpty(fh.Def.slotNodes)) continue;
    foreach (var fr in fh.GetComponentsInChildren<UnityEngine.MeshRenderer>())
        if (!fr.enabled && !Cozy.Grid.InteractHighlight.IsCopy(fr) && fr.GetComponentInParent<Cozy.Grid.InteractiveObject>() == fh) { fr.enabled = true; forced.Add(fr); }
}
int wallRays = 0, leaks = 0, openRays = 0, reached = 0, known = 0;
var knownLeak = new System.Collections.Generic.HashSet<string> { "home_coffee_machine/coffee_carafe" };
var knownShut = new System.Collections.Generic.HashSet<string> { "home_wall_cabinet_corner_wide/filter_pack" };
var sb = new System.Text.StringBuilder();
foreach (var host in Cozy.Grid.InteractiveObject.All)
{
    if (host == null || host.Def == null || !(bool)shows.Invoke(null, new object[] { host.Def })) continue;
    var t = host.transform;
    var hb = host.WorldBounds;
    foreach (var it in host.GetComponentsInChildren<Cozy.Grid.InteractiveObject>(false))
    {
        if (it == host || !Cozy.Grid.InteractiveObject.NestedInside(it, host)) continue;
        var col = it.GetComponentInChildren<UnityEngine.Collider>();
        if (col == null) continue;
        var target = col.bounds.center;
        var open = t.TransformDirection((UnityEngine.Vector3)side.Invoke(null, new object[] { host, it }));
        var dirs = new[] { -t.right, t.right, t.forward, -t.forward, UnityEngine.Vector3.up };
        foreach (var d in dirs)
        {
            bool isOpening = UnityEngine.Vector3.Dot(d, open) > 0.9f;
            var from = target + d * (hb.extents.magnitude + 1f);
            var ray = new UnityEngine.Ray(from, (target - from).normalized);
            var args = new object[] { ray, null };
            var got = pick.Invoke(gc, args) as UnityEngine.Collider;
            if (got == null) continue;
            bool gotItem = got.transform.IsChildOf(it.transform);
            bool hostFirst = got.GetComponentInParent<Cozy.Grid.InteractiveObject>() == host || gotItem;
            if (!hostFirst) continue;
            if (isOpening)
            {
                if (!Cozy.Grid.ContainerSlot.InOpenSlot(it, host)) continue;
                openRays++;
                if (gotItem) reached++; else if (knownShut.Contains(host.Def.id + "/" + it.Def.id)) known++; else sb.Append("ПРОЁМ НЕ ПУСТИЛ " + host.Def.id + "/" + it.Def.id + "; ");
            }
            else
            {
                if (host.IsPart(it.transform)) continue;
                wallRays++;
                if (gotItem)
                {
                    UnityEngine.RaycastHit first;
                    bool wallBetween = UnityEngine.Physics.Raycast(ray, out first, 50f) && first.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() == host && !first.collider.transform.IsChildOf(it.transform);
                    if (wallBetween && knownLeak.Contains(host.Def.id + "/" + it.Def.id)) known++;
                    else if (wallBetween) { leaks++; sb.Append("СКВОЗЬ СТЕНКУ " + host.Def.id + "/" + it.Def.id + " с " + d.ToString("F1") + "; "); }
                }
            }
        }
    }
}
foreach (var fr in forced) if (fr != null) fr.enabled = false;
if (opened != null)
    foreach (var gh in Cozy.Grid.InteractiveObject.All)
        if (gh != null && opened.Contains(gh.GetInstanceID()))
            foreach (var f in gh.Features) if (f is Cozy.Grid.AccessFeature af && af.Open) af.SetOpen(false);
if (wallRays + openRays == 0) return "НЕ ПРОВЕРЕНО: выбор в стройке — ни одного луча (вид на другом этаже, герой не у хозяев); запусти, когда герой на 1 этаже дома";
return "выбор в стройке: лучей сбоку/сверху=" + wallRays + " сквозь стенку=" + leaks + " | через проём=" + openRays + " дотянулся=" + reached + " известных (ниша кофемашины, крыло углового за открытой дверцей)=" + known + " :: " + sb;
