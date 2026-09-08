// Проба «туман не проходит сквозь стены и плиты» (Илья 08.09: «туман никогда
// не должен проходить сквозь стены 1 2 3 4 и тд этажей, и плиты пола потолка»).
// Запуск в play через execute_code. Берёт КАЖДЫЙ клуб тумана в сцене, режет его
// габарит коробкой обрезки из property block (то, что реально видит шейдер) и
// проверяет, что от клуба ничего не осталось внутри помещения — на любом этаже.
if (!Application.isPlaying) return "NOT PLAYING";
var block = new MaterialPropertyBlock();
int lo = Shader.PropertyToID("_ClipMin"), hi = Shader.PropertyToID("_ClipMax");
int puffs = 0, cut = 0, bad = 0;
float deepest = 0f;
string worst = "";
foreach (var view in Object.FindObjectsByType<Cozy.Grid.FogView>(FindObjectsSortMode.None))
{
    foreach (var mr in view.GetComponentsInChildren<MeshRenderer>())
    {
        puffs++;
        mr.GetPropertyBlock(block);
        Vector3 mn = block.GetVector(lo), mx = block.GetVector(hi);
        if (mx.x - mn.x < 0.0001f && mx.y - mn.y < 0.0001f) { mn = new Vector3(-1e5f, -1e5f, -1e5f); mx = -mn; }
        var b = mr.bounds;
        var a0 = Vector3.Max(b.min, mn);
        var a1 = Vector3.Min(b.max, mx);
        if (a0.x >= a1.x || a0.y >= a1.y || a0.z >= a1.z) { cut++; continue; }
        for (int ix = 0; ix <= 2; ix++)
        for (int iy = 0; iy <= 2; iy++)
        for (int iz = 0; iz <= 2; iz++)
        {
            var p = new Vector3(Mathf.Lerp(a0.x, a1.x, ix * 0.5f),
                                Mathf.Lerp(a0.y, a1.y, iy * 0.5f),
                                Mathf.Lerp(a0.z, a1.z, iz * 0.5f));
            if (Cozy.Grid.LightZones.ZoneAt(p) != Cozy.Grid.LightZones.Indoor) continue;
            float depth = Mathf.Min(Mathf.Min(p.x - a0.x, a1.x - p.x), Mathf.Min(p.z - a0.z, a1.z - p.z));
            bad++;
            if (depth > deepest)
            {
                deepest = depth;
                worst = mr.transform.parent.parent.name + "/" + mr.name + " @ " + p.ToString("F2");
            }
            ix = iy = iz = 9;
        }
    }
}
return "клубов " + puffs + ", срезано целиком " + cut + ", в помещении " + bad
     + (bad > 0 ? " (худший " + worst + ", вглубь " + deepest.ToString("F2") + " м) :: ПРОВАЛ" : " :: ОК");
