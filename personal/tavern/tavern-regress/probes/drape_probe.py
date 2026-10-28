"""Натяжка порций на внутреннюю поверхность хозяина (P740, инвариант 320).

Спавнит сковороду с четырьмя яичницами и тарелку с тремя сосисками и яичницей
рядом с героем, раскладывает их RebuildLayout и для каждой вершины порции
сравнивает её высоту с высотой меша хозяина под ней: ни одна вершина не ниже
поверхности (допуск 1,5 мм). Печатает, сколько вершин легло на борт. Пробные
объекты удаляет. Нужен play.
"""
import sys
sys.path.insert(0,'/home/ilya/.claude/skills/tavern-regress/probes')
from cycle import mcp
code=r'''
var sb = new System.Text.StringBuilder();
var gc = Cozy.Grid.GridCursor.I;
var player = Cozy.Grid.PlayerRef.Transform;
var spawned = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
var hostDefs = new string[]{ "frying_pan", "plate" };
var fills = new string[][]{ new string[]{ "fried_egg", "fried_egg", "fried_egg", "fried_egg" }, new string[]{ "sausage", "sausage", "sausage", "fried_egg" } };
for (int h = 0; h < hostDefs.Length; h++)
{
    var hostDef = Cozy.Grid.FurnitureCatalog.ById(hostDefs[h]);
    var host = gc.SpawnWorldObject(hostDef, player.position + player.forward * 2f + player.right * (h - 0.5f) * 1.2f + UnityEngine.Vector3.up * 0.5f, 0f);
    if (host == null) { sb.Append(hostDefs[h]).Append(": нет хозяина\n"); continue; }
    spawned.Add(host);
    foreach (var pid in fills[h])
    {
        var pdef = Cozy.Grid.FurnitureCatalog.ById(pid);
        var p = gc.SpawnWorldObject(pdef, host.transform.position + UnityEngine.Vector3.up * 0.3f, 0f);
        if (p == null) continue;
        p.transform.SetParent(host.transform, true);
        p.Container = host;
    }
    Cozy.Grid.GridCursor.RebuildLayout(host);
    var shell = host.GetComponentInChildren<UnityEngine.MeshFilter>();
    UnityEngine.MeshFilter best = null;
    foreach (var f in host.GetComponentsInChildren<UnityEngine.MeshFilter>()) if (f.GetComponentInParent<Cozy.Grid.InteractiveObject>() == host && (best == null || f.sharedMesh.vertexCount > best.sharedMesh.vertexCount)) best = f;
    var sv = best.sharedMesh.vertices; var st = best.sharedMesh.triangles;
    for (int i = 0; i < sv.Length; i++) sv[i] = best.transform.TransformPoint(sv[i]);
    float rim = float.MinValue; foreach (var v in sv) if (v.y > rim) rim = v.y;
    sb.Append("== ").Append(hostDefs[h]).Append(" rim=").Append((rim - host.transform.position.y).ToString("0.000")).Append("\n");
    foreach (var c in host.GetComponentsInChildren<Cozy.Grid.InteractiveObject>())
    {
        if (c == host || c.Container != host) continue;
        var draped = c.GetComponent<Cozy.Grid.DrapedMesh>();
        int below = 0, total = 0, raised = 0; float worst = 0f;
        foreach (var mf in c.GetComponentsInChildren<UnityEngine.MeshFilter>())
        {
            if (mf.GetComponentInParent<Cozy.Grid.InteractiveObject>() != c) continue;
            var verts = mf.sharedMesh.vertices;
            foreach (var v in verts)
            {
                var w = mf.transform.TransformPoint(v);
                float surf = float.MinValue; bool hit = false;
                for (int t = 0; t + 2 < st.Length; t += 3)
                {
                    var a = sv[st[t]]; var b = sv[st[t + 1]]; var cc = sv[st[t + 2]];
                    if (w.x < UnityEngine.Mathf.Min(a.x, UnityEngine.Mathf.Min(b.x, cc.x)) || w.x > UnityEngine.Mathf.Max(a.x, UnityEngine.Mathf.Max(b.x, cc.x))) continue;
                    if (w.z < UnityEngine.Mathf.Min(a.z, UnityEngine.Mathf.Min(b.z, cc.z)) || w.z > UnityEngine.Mathf.Max(a.z, UnityEngine.Mathf.Max(b.z, cc.z))) continue;
                    float d = (b.z - cc.z) * (a.x - cc.x) + (cc.x - b.x) * (a.z - cc.z);
                    if (UnityEngine.Mathf.Abs(d) < 1e-9f) continue;
                    float u = ((b.z - cc.z) * (w.x - cc.x) + (cc.x - b.x) * (w.z - cc.z)) / d;
                    float vv = ((cc.z - a.z) * (w.x - cc.x) + (a.x - cc.x) * (w.z - cc.z)) / d;
                    float ww = 1f - u - vv;
                    if (u < -1e-4f || vv < -1e-4f || ww < -1e-4f) continue;
                    float hy = u * a.y + vv * b.y + ww * cc.y;
                    if (hy > rim - 0.002f) continue;
                    if (hy > surf) { surf = hy; hit = true; }
                }
                total++;
                if (!hit) continue;
                if (w.y < surf - 0.0015f) { below++; worst = UnityEngine.Mathf.Max(worst, surf - w.y); }
                if (surf > host.transform.position.y + 0.02f) raised++;
            }
        }
        sb.Append("  ").Append(c.Def.id).Append(" draped=").Append(draped != null).Append(" mesh=").Append(c.GetComponentInChildren<UnityEngine.MeshFilter>().sharedMesh.name).Append(" verts=").Append(total).Append(" под поверхностью=").Append(below).Append(" (худшее ").Append((worst * 1000f).ToString("0.0")).Append(" мм) на борту=").Append(raised).Append(" pos=").Append((c.transform.position - host.transform.position).ToString("0.00")).Append("\n");
    }
}
foreach (var s in spawned) { s.gameObject.SetActive(false); UnityEngine.Object.Destroy(s.gameObject); }
return sb.ToString();
'''
d=mcp('execute_code', {"action":"execute","code":code})
res = d.get('data',{}).get('result') if d.get('success') else None
if not res:
    print('ПРОБА НЕ ОТВЕТИЛА: ' + str(d)[:300]); raise SystemExit(1)
bad = [l for l in res.split('\n') if 'под поверхностью=' in l and 'под поверхностью=0 ' not in l]
hosts = res.count('== ')
print(res.strip())
print('натяжка: хозяев=%d порций=%d :: %s' % (hosts, res.count('draped='), 'КРАСНОЕ: порция под поверхностью хозяина' if bad else 'инварианты держатся'))
