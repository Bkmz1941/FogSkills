if (!UnityEngine.Application.isPlaying) return "не в play";
var T = typeof(Cozy.Grid.Interactor);
var through = T.GetMethod("ThroughOpening", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var shows = T.GetMethod("ShowsThroughDoor", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
var sb = new System.Text.StringBuilder();
var byDef = new System.Collections.Generic.Dictionary<string, int[]>();
var hits = new UnityEngine.RaycastHit[64];
int hosts = 0, rays = 0, leaks = 0;
foreach (var host in Cozy.Grid.InteractiveObject.All)
{
    if (host == null || host.Def == null || !(bool)shows.Invoke(null, new object[] { host.Def })) continue;
    var items = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
    foreach (var it in host.GetComponentsInChildren<Cozy.Grid.InteractiveObject>(false))
        if (it != host && Cozy.Grid.InteractiveObject.NestedInside(it, host)) items.Add(it);
    if (items.Count == 0) continue;
    hosts++;
    var hb = host.WorldBounds; var t = host.transform;
    string[] sides = { "лево", "право", "зад", "верх" };
    UnityEngine.Vector3[] dirs = { -t.right, t.right, t.forward, UnityEngine.Vector3.up };
    if (!byDef.ContainsKey(host.Def.id)) byDef[host.Def.id] = new int[8];
    foreach (var it in items)
    {
        var col = it.GetComponentInChildren<UnityEngine.Collider>();
        if (col == null) continue;
        var target = col.bounds.center;
        for (int s = 0; s < 4; s++)
        {
            var from = target + dirs[s] * (hb.extents.magnitude + 1f);
            var dir = (target - from).normalized;
            int n = UnityEngine.Physics.RaycastNonAlloc(from, dir, hits, 10f, ~0, UnityEngine.QueryTriggerInteraction.Collide);
            UnityEngine.RaycastHit hostHit = new UnityEngine.RaycastHit(); bool gotHost = false, gotItem = false; float hd = 1e9f;
            for (int i = 0; i < n; i++)
            {
                var h = hits[i];
                var owner = h.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>();
                if (owner == host && !h.collider.transform.IsChildOf(it.transform) && h.distance < hd) { hd = h.distance; hostHit = h; gotHost = true; }
                if (h.collider.transform.IsChildOf(it.transform)) gotItem = true;
            }
            if (!gotHost || !gotItem) continue;
            rays++;
            bool lets = (bool)through.Invoke(null, new object[] { hostHit, col, host });
            byDef[host.Def.id][s * 2] += 1;
            if (lets) { byDef[host.Def.id][s * 2 + 1] += 1; leaks++; }
        }
    }
}
foreach (var kv in byDef)
{
    sb.Append(kv.Key + ": ");
    string[] sides = { "лево", "право", "зад", "верх" };
    for (int s = 0; s < 4; s++) sb.Append(sides[s] + " " + kv.Value[s * 2 + 1] + "/" + kv.Value[s * 2] + " ");
    sb.Append("; ");
}
return "хозяев с содержимым=" + hosts + " лучей=" + rays + " сквозь стенку=" + leaks + " :: " + sb;
