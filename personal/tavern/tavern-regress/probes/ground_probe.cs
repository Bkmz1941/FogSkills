// Проба посадки растительности на рельеф (P1221, инв. 621): только читает.
// Каждое растение/камень/палка вне полосы дороги должно стоять на земле:
// y − HeightAt = −0,10 (камешки −0,08) ± 0,05. Пишет число нарушений и худшие пять.
if (!UnityEngine.Application.isPlaying) return "ПОДГОТОВКА: нужен play";
var cur = Cozy.Grid.GridCursor.I;
var h = cur != null ? cur.Heights : null;
if (h == null) return "SKIP: у уровня нет рельефа";
int total = 0, bad = 0;
var worst = new System.Collections.Generic.List<System.Tuple<float, string>>();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io == null || !io.isActiveAndEnabled || io.Def == null) continue;
    string id = io.Def.id;
    if (!(id.StartsWith("veg_") || id.StartsWith("deco_stick"))) continue;
    if (io.transform.parent != null && io.transform.parent.GetComponentInParent<Cozy.Grid.InteractiveObject>() != null) continue;
    var p = io.transform.position;
    bool onRoad = false;
    foreach (var c in UnityEngine.Physics.OverlapSphere(p, 0.05f))
        if (c.GetComponentInParent<Cozy.Grid.InteractiveObject>() is Cozy.Grid.InteractiveObject r && r.Def != null && r.Def.id.StartsWith("env_highway")) { onRoad = true; break; }
    if (onRoad) continue;
    total++;
    float target = id.StartsWith("veg_pebble") ? -0.08f : -0.10f;
    float off = p.y - h.HeightAt(p) - target;
    if (UnityEngine.Mathf.Abs(off) <= 0.05f) continue;
    bad++;
    worst.Add(System.Tuple.Create(UnityEngine.Mathf.Abs(off), id + " " + p.ToString("F1") + " " + (off > 0 ? "висит +" : "в земле ") + off.ToString("F2")));
}
worst.Sort((a, b) => b.Item1.CompareTo(a.Item1));
var sb = new System.Text.StringBuilder((bad == 0 ? "OK" : "FAIL") + " ground: растений " + total + ", не на земле " + bad);
for (int i = 0; i < worst.Count && i < 5; i++) sb.Append(" | " + worst[i].Item2);
return sb.ToString();
