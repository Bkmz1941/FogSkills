// Камин: дрова в топке и в поленнице (инвариант 118). Строит камин ВНЕ уровня
// (y = -50), раскладывает поленья по всем местам обеих раскладок, проверяет,
// что ничто не вылезает из топки и ниши и не пересекается глубже 12 мм, затем
// проверяет сам механизм: выбор раскладки по ближнему узлу, занятость места
// разными видами полена и гейт топки по створке. Всё построенное удаляется.
if (!Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
var def = Cozy.Grid.FurnitureCatalog.ById("home_fireplace");
var logDef = Cozy.Grid.FurnitureCatalog.ById("firewood_log");
var splitDef = Cozy.Grid.FurnitureCatalog.ById("firewood_split");
if (def == null || logDef == null || splitDef == null) return "нет дефов камина или дров";
var body = new GameObject("PROBE_FIREPLACE");
body.transform.SetPositionAndRotation(new Vector3(0f, -50f, 0f), Quaternion.identity);
var io = body.AddComponent<Cozy.Grid.InteractiveObject>();
io.Build(def);
System.Func<string, Transform> find = name => { foreach (var t in body.GetComponentsInChildren<Transform>(true)) if (t.name == name) return t; return null; };
System.Func<string, Bounds> nodeBox = name => {
    var t = find(name); var b = new Bounds(); bool f = true;
    if (t != null) foreach (var r in t.GetComponentsInChildren<Renderer>(true)) { if (f) { b = r.bounds; f = false; } else b.Encapsulate(r.bounds); }
    return b;
};
var floor = nodeBox("LinFloor"); var ceil = nodeBox("LinTop"); var sideL = nodeBox("LinSideL"); var sideR = nodeBox("LinSideR"); var back = nodeBox("LinBack"); var glass = nodeBox("Glass");
var nFloor = nodeBox("NicheFloor"); var nL = nodeBox("NicheSideL"); var nR = nodeBox("NicheSideR"); var nBack = nodeBox("NicheBack"); var hearth = nodeBox("Hearth");
var made = new System.Collections.Generic.List<GameObject>();
var boxes = new System.Collections.Generic.List<Bounds>();
var tags = new System.Collections.Generic.List<string>();
foreach (var layout in def.cookLayouts)
{
    if (layout.resultId != "firewood_log") continue;
    var node = find(layout.slotNode);
    string tag = layout.slotNode == "Slot_Fire" ? "Т" : "П";
    for (int s = 0; s < layout.slots.Count; s++)
    {
        var d = s % 3 == 0 ? splitDef : logDef;
        var g = new GameObject("PROBE_LOG" + tag + s);
        g.AddComponent<Cozy.Grid.InteractiveObject>().Build(d);
        g.transform.SetPositionAndRotation(node.position + body.transform.rotation * layout.slots[s],
            Quaternion.Euler(0f, body.transform.eulerAngles.y + layout.yaws[s], 0f));
        var b = new Bounds(); bool f = true;
        foreach (var r in g.GetComponentsInChildren<Renderer>(true)) { if (f) { b = r.bounds; f = false; } else b.Encapsulate(r.bounds); }
        made.Add(g); boxes.Add(b); tags.Add(tag + s + (d == splitDef ? "к" : "ц"));
    }
}
int brak = 0;
for (int i = 0; i < boxes.Count; i++)
{
    var b = boxes[i];
    bool inFire = tags[i].StartsWith("Т");
    float loY = inFire ? floor.max.y : nFloor.max.y, hiY = inFire ? ceil.min.y : hearth.min.y;
    float loX = inFire ? sideL.max.x : nL.max.x, hiX = inFire ? sideR.min.x : nR.min.x;
    float loZ = inFire ? glass.max.z : hearth.min.z, hiZ = inFire ? back.min.z : nBack.min.z;
    string bad = "";
    if (b.min.y < loY - 0.002f) bad += " ниже пола " + (loY - b.min.y).ToString("F3");
    if (b.max.y > hiY + 0.002f) bad += " выше потолка " + (b.max.y - hiY).ToString("F3");
    if (b.min.x < loX - 0.002f) bad += " в левую стенку " + (loX - b.min.x).ToString("F3");
    if (b.max.x > hiX + 0.002f) bad += " в правую стенку " + (b.max.x - hiX).ToString("F3");
    if (b.min.z < loZ - 0.002f) bad += " наружу " + (loZ - b.min.z).ToString("F3");
    if (b.max.z > hiZ + 0.002f) bad += " в заднюю стенку " + (b.max.z - hiZ).ToString("F3");
    if (bad != "") { sb.Append("  БРАК " + tags[i] + ":" + bad + "\n"); brak++; }
}
// Перекрытие КОРОБОК у лежащих в развилке — норма, коробка повёрнутого
// полена вдвое больше его самого. Врезание меряется по ОСЯМ: у двух
// брёвен расстояние между осями не должно быть меньше суммы радиусов.
// Радиус берём как половину МЕНЬШЕЙ стороны коробки.
int sink = 0; float worst = 0f; string worstPair = "";
for (int i = 0; i < boxes.Count; i++)
    for (int j = i + 1; j < boxes.Count; j++)
    {
        if (!boxes[i].Intersects(boxes[j])) continue;
        var a = boxes[i]; var b = boxes[j];
        float ra = Mathf.Min(a.size.x, Mathf.Min(a.size.y, a.size.z)) * 0.5f;
        float rb = Mathf.Min(b.size.x, Mathf.Min(b.size.y, b.size.z)) * 0.5f;
        float need = ra + rb;
        var d = a.center - b.center;
        // Вдоль полена они лежат внахлёст по построению, поэтому меряем в
        // плоскости «поперёк + высота» той пары, что шире вдоль x.
        float dist = new Vector2(Mathf.Abs(d.y), Mathf.Abs(a.size.x > a.size.z ? d.z : d.x)).magnitude;
        float deep = need - dist;
        if (deep <= 0.003f) continue;
        sink++;
        if (deep > worst) { worst = deep; worstPair = tags[i] + "/" + tags[j]; }
    }
sb.Append("мест " + boxes.Count + ", вне объёма " + brak + ", врезаний по осям " + sink
    + (sink > 0 ? " (худшее " + worst.ToString("F3") + " " + worstPair + ")" : "") + "\n");
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
System.Reflection.MethodInfo mFor = null, mFree = null;
foreach (var m in T.GetMethods(B))
{
    var ps = m.GetParameters();
    if (m.Name == "LayoutFor" && ps.Length == 3 && ps[0].ParameterType == typeof(Cozy.Grid.InteractiveObject)) mFor = m;
    if (m.Name == "LayoutFreeSlot") mFree = m;
}
foreach (var g in made) UnityEngine.Object.DestroyImmediate(g);
System.Func<string, Vector3, string> where = (id, point) => {
    var l = mFor.Invoke(null, new object[] { io, id, point }) as Cozy.Grid.CookLayout;
    return l == null ? "нет" : l.slotNode + "#" + (int)mFree.Invoke(null, new object[] { l, io, null });
};
var fireP = find("Slot_Fire").position;
var woodP = find("Slot_Wood").position;
sb.Append("выбор места: целое у топки " + where("firewood_log", fireP) + ", у поленницы " + where("firewood_log", woodP)
    + "; колотое у топки " + where("firewood_split", fireP) + ", у поленницы " + where("firewood_split", woodP) + "\n");
int acc = 0;
foreach (var f in io.Features) { var a = f as Cozy.Grid.AccessFeature; if (a == null) continue; acc++; a.SetOpen(true); }
var slots = body.GetComponentsInChildren<Cozy.Grid.ContainerSlot>(true);
sb.Append("створок " + acc + "; открыта:");
foreach (var s in slots) sb.Append(" " + s.name + "=" + s.Open);
foreach (var f in io.Features) { var a = f as Cozy.Grid.AccessFeature; if (a != null) a.SetOpen(false); }
sb.Append("; закрыта:");
foreach (var s in slots) sb.Append(" " + s.name + "=" + s.Open);
sb.Append("\n");
UnityEngine.Object.DestroyImmediate(body);
sb.Append("осталось проб=" + System.Array.FindAll(UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsSortMode.None), t => t.name.StartsWith("PROBE_")).Length + "\n");
return sb.ToString();
