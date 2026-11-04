// Бокс существа и точка появления (P1294, инв. 666, ZOMBIE.md ZB-X…): бокс Валеры не обводит его зоны чувств
// (SightCone, HearZone*) после смены одежды (RefitModel), зоны не входят в OwnRenderers; точка появления
// CrowZoneSpawn не ложится на капсулу героя и не ближе PlayerClearance. Любой уровень; свой Валера ставится
// в 40 м от героя и удаляется.
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0;
System.Action<bool, string> Check = (ok, line) => { if (!ok) fails++; sb.Append(ok ? "OK " : "FAIL ").Append(line).Append('\n'); };
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var NS = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var pm = UnityEngine.Object.FindFirstObjectByType<Cozy.Character.PlayerMovement>();
if (pm == null) return "нет героя";
var hero = pm.transform;
Cozy.Grid.InteractiveObject io = null;
try
{
    // ---------- ZB-X01…X03: бокс по телу ----------
    var def = Cozy.Grid.FurnitureCatalog.ById(Cozy.Grid.FurnitureCatalog.ValeraId);
    io = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, hero.position + new UnityEngine.Vector3(40f, 0f, 0f), 0f);
    io.Slug = "regress_box_valera";
    var box = io.GetComponent<UnityEngine.BoxCollider>();
    var senses = io.GetComponentInChildren<Cozy.Creatures.CreatureSenses>();
    Check(senses != null, "ZB-X00 у Валеры есть CreatureSenses");
    if (senses != null)
    {
        typeof(Cozy.Creatures.CreatureSenses).GetMethod("BuildZones", NP).Invoke(senses, null);
        foreach (var r in io.GetComponentsInChildren<UnityEngine.MeshRenderer>(true))
            if (r.name.StartsWith("HearZone") || r.name == "SightCone")
            {
                r.gameObject.SetActive(true);
                var m = r.GetComponent<UnityEngine.MeshFilter>().sharedMesh;
                m.vertices = new[] { new UnityEngine.Vector3(-12, 0, -12), new UnityEngine.Vector3(12, 0, -12), new UnityEngine.Vector3(12, 0, 12), new UnityEngine.Vector3(-12, 0, 12) };
                m.triangles = new[] { 0, 2, 1, 0, 3, 2 };
                m.RecalculateBounds();
            }
    }
    var eq = io.GetComponentInChildren<Cozy.Character.Equipment>();
    eq.Put(Cozy.Grid.Items.KnitHat.slot, null, null);
    eq.Put(Cozy.Grid.Items.KnitHat.slot, Cozy.Grid.Items.KnitHat, null);
    var s = box.bounds.size;
    Check(s.x < 4f && s.z < 4f && s.y < 4f, "ZB-X01 бокс Валеры после смены одежды при зонах 24 м — по телу: " + s);
    int zonesOwn = 0;
    foreach (var r in io.OwnRenderers()) if (r.name.StartsWith("HearZone") || r.name == "SightCone") zonesOwn++;
    Check(zonesOwn == 0, "ZB-X02 зоны чувств не входят в OwnRenderers: " + zonesOwn);
    int marked = 0, zones = 0;
    foreach (var r in io.GetComponentsInChildren<UnityEngine.Renderer>(true))
        if (r.name.StartsWith("HearZone") || r.name == "SightCone") { zones++; if (r.GetComponent<Cozy.Grid.ModelOverlay>() != null) marked++; }
    Check(zones > 0 && marked == zones, "ZB-X03 все зоны помечены ModelOverlay: " + marked + " из " + zones);

    // ---------- ZB-X04…X05: точка появления не на герое ----------
    var clear = typeof(Cozy.Life.CrowZoneSpawn).GetMethod("ClearOfPeople", NS);
    Check(clear != null, "ZB-X04 есть CrowZoneSpawn.ClearOfPeople");
    if (clear != null)
    {
        bool onHero = UnityEngine.Physics.Raycast(hero.position + UnityEngine.Vector3.up * 6f, UnityEngine.Vector3.down, out var hHero, 12f, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
        bool heroHit = onHero && (hHero.collider is UnityEngine.CharacterController || hHero.collider.CompareTag("Player"));
        Check(heroHit && !(bool)clear.Invoke(null, new object[] { hHero }), "ZB-X04 луч в капсулу героя — не земля (попал в " + (onHero ? hHero.collider.name : "ничто") + ")");
        float need = (float)typeof(Cozy.Life.CrowZoneSpawn).GetField("PlayerClearance", NS).GetValue(null);
        bool near = UnityEngine.Physics.Raycast(hero.position + new UnityEngine.Vector3(need * 0.6f, 6f, 0f), UnityEngine.Vector3.down, out var hNear, 12f, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
        bool far = UnityEngine.Physics.Raycast(hero.position + new UnityEngine.Vector3(need + 1.5f, 6f, 0f), UnityEngine.Vector3.down, out var hFar, 12f, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
        Check(near && !(bool)clear.Invoke(null, new object[] { hNear }), "ZB-X05 ближе " + need + " м к герою не появляется");
        Check(far && (bool)clear.Invoke(null, new object[] { hFar }) || !far, "ZB-X05 дальше " + need + " м — можно (" + (far ? hFar.collider.name : "нет земли") + ")");
    }
}
finally
{
    if (io != null) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
int total = 0;
foreach (var l in sb.ToString().Split('\n')) if (l.StartsWith("OK ") || l.StartsWith("FAIL ")) total++;
return (fails == 0 ? "ЗЕЛЁНОЕ из " + total : "КРАСНОЕ: " + fails + " из " + total) + " (свой Валера создан и удалён)\n" + sb;
