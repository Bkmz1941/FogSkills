// mass_physics_probe.cs — МАССОВАЯ ФИЗИКА МЕЛОЧИ (правило PhysicsProp.Wants, инвариант 658). Только в play, execute_code (codedom, C# 6).
// PHASE 1 — перепись: сколько предметов уровня с PhysicsProp, живых/спящих/кинематических, FallToSupport, запоминает позы в PROBE_mass (пустышка).
// PHASE 2 (через 3–5 с) — смещения с момента PHASE 1: сколько сдвинулось > 2 см и > 10 см, 8 самых больших с id; ошибки консоли смотреть отдельно.
// Ничего не спавнит и не трогает уровень; PHASE 3 убирает пустышку.
int PHASE = 1;
var sb = new System.Text.StringBuilder();
var keeper = GameObject.Find("PROBE_mass");
if (PHASE == 1)
{
    if (!Application.isPlaying) return "не в play";
    if (keeper == null) keeper = new GameObject("PROBE_mass");
    int props = 0, live = 0, asleep = 0, kin = 0, falls = 0, both = 0, nested = 0;
    var lines = new System.Collections.Generic.List<string>();
    foreach (var io in Cozy.Grid.InteractiveObject.All)
    {
        if (io == null) continue;
        var prop = io.GetComponent<Cozy.Grid.PhysicsProp>();
        var fall = io.GetComponent<Cozy.Grid.FallToSupport>();
        if (fall != null) falls++;
        if (prop == null) continue;
        props++;
        if (fall != null) both++;
        if (io.Container != null) nested++;
        var rb = io.GetComponent<Rigidbody>();
        if (rb == null) continue;
        if (rb.isKinematic) kin++; else { live++; if (rb.IsSleeping()) asleep++; }
        lines.Add(io.GetInstanceID() + "|" + io.Def.id + "|" + io.transform.position.x.ToString("F4") + "|" + io.transform.position.y.ToString("F4") + "|" + io.transform.position.z.ToString("F4") + "|" + Vector3.Angle(io.transform.up, Vector3.up).ToString("F1"));
    }
    keeper.name = "PROBE_mass";
    var tm = keeper.GetComponent<TextMesh>(); if (tm == null) tm = keeper.AddComponent<TextMesh>();
    tm.text = string.Join("\n", lines.ToArray());
    var mr = keeper.GetComponent<MeshRenderer>(); if (mr != null) mr.enabled = false;
    sb.AppendLine("уровень " + Cozy.Grid.LevelIO.CurrentSlug + ": PhysicsProp " + props + " (живых " + live + ", из них спят " + asleep + ", кинематических " + kin + ", вложенных " + nested + "), FallToSupport " + falls + ", оба сразу " + both + " (ждём 0)");
    sb.AppendLine("позы запомнены; через 3–5 с звать PHASE = 2");
    return sb.ToString();
}
if (keeper == null) return "нет PROBE_mass — сначала PHASE = 1";
if (PHASE == 2)
{
    var tm = keeper.GetComponent<TextMesh>();
    var byId = new System.Collections.Generic.Dictionary<int, Cozy.Grid.InteractiveObject>();
    foreach (var io in Cozy.Grid.InteractiveObject.All) if (io != null) byId[io.GetInstanceID()] = io;
    int n = 0, moved2 = 0, moved10 = 0, tipped = 0, gone = 0;
    var worst = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<float, string>>();
    foreach (var line in tm.text.Split('\n'))
    {
        if (line.Length == 0) continue;
        var f = line.Split('|');
        n++;
        Cozy.Grid.InteractiveObject io;
        if (!byId.TryGetValue(int.Parse(f[0]), out io) || io == null) { gone++; continue; }
        var was = new Vector3(float.Parse(f[2]), float.Parse(f[3]), float.Parse(f[4]));
        float d = Vector3.Distance(was, io.transform.position);
        float tilt = Vector3.Angle(io.transform.up, Vector3.up) - float.Parse(f[5]);
        if (d > 0.02f) moved2++;
        if (d > 0.10f) moved10++;
        if (tilt > 20f) tipped++;
        if (d > 0.02f || tilt > 20f) worst.Add(new System.Collections.Generic.KeyValuePair<float, string>(d, f[1] + " сдвиг " + d.ToString("F2") + " м, наклон +" + tilt.ToString("F0") + "°, было " + was.ToString("F2")));
    }
    worst.Sort((a, b) => b.Key.CompareTo(a.Key));
    sb.AppendLine("предметов " + n + ": сдвинулись > 2 см — " + moved2 + ", > 10 см — " + moved10 + ", опрокинулись > 20° — " + tipped + ", исчезли — " + gone + " (ждём 0 / 0 / 0 после загрузки уровня)");
    for (int i = 0; i < worst.Count && i < 8; i++) sb.AppendLine("  " + worst[i].Value);
    return sb.ToString();
}
UnityEngine.Object.DestroyImmediate(keeper);
return "PROBE_mass убрана";
