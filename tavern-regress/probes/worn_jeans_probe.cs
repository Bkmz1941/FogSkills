// ОДЕТЫЙ ГЕРОЙ. Для Unity MCP execute_code (в play). INVARIANTS 54–56, P202/P203.
// Если джинсы не надеты — надевает через Equipment (настоящий путь WardrobeVisuals)
// и в конце снимает; если надеты — только смотрит. Проверяет: узел Wear_Legs с
// пятью рендерерами (Pants/Belt/Loops/Buckle/Pockets), бельё Underwear неактивно
// при надетых штанах и активно без них, цвета материалов = sRGB из json.
if (!UnityEngine.Application.isPlaying) return "NOT PLAYING";
System.Func<string, System.Type> T = n => { foreach (var a in System.AppDomain.CurrentDomain.GetAssemblies()) { System.Type[] ts; try { ts = a.GetTypes(); } catch { continue; } foreach (var t in ts) if (t.Name == n) return t; } return null; };
var eqType = T("Equipment"); var itemsType = T("Items"); var slotType = T("EquipSlot");
if (eqType == null || itemsType == null || slotType == null) return "RED: нет типов Equipment/Items/EquipSlot";
var player = UnityEngine.GameObject.Find("Player"); if (player == null) return "RED: нет Player";
var eq = player.GetComponent(eqType); if (eq == null) return "RED: у Player нет Equipment";
var legs = System.Enum.Parse(slotType, "Legs");
var get = eqType.GetMethod("Get"); var equip = eqType.GetMethod("Equip"); var uneq = eqType.GetMethod("Unequip");
var jeansMember = itemsType.GetField("Jeans") != null ? (object)itemsType.GetField("Jeans") : itemsType.GetProperty("Jeans");
object jeans = jeansMember is System.Reflection.FieldInfo ? ((System.Reflection.FieldInfo)jeansMember).GetValue(null) : ((System.Reflection.PropertyInfo)jeansMember).GetValue(null);
var visual = player.transform.Find("Visual");
var sb = new System.Text.StringBuilder();
System.Func<string, UnityEngine.Transform> find = n => { foreach (var t in visual.GetComponentsInChildren<UnityEngine.Transform>(true)) if (t.name == n) return t; return null; };
var wornBefore = get.Invoke(eq, new object[] { legs });
bool temp = wornBefore == null;
var wardrobe = player.GetComponent(T("WardrobeVisuals"));
var sync = wardrobe != null ? wardrobe.GetType().GetMethod("Sync", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance) : null;
try
{
    if (temp) { equip.Invoke(eq, new object[] { legs, jeans }); if (sync != null) sync.Invoke(wardrobe, null); }
    var wear = find("Wear_Legs"); var under = find("Underwear");
    if (wear == null) return "RED: после надевания нет узла Wear_Legs";
    var names = new System.Collections.Generic.List<string>();
    foreach (var r in wear.GetComponentsInChildren<UnityEngine.Renderer>(true)) names.Add(r.name);
    names.Sort();
    string want = "Belt,Buckle,Loops,Pants,Pockets";
    sb.Append((string.Join(",", names) == want ? "OK " : "RED ") + "части: " + string.Join(",", names) + "\n");
    sb.Append((under != null && !under.gameObject.activeSelf ? "OK " : "RED ") + "бельё скрыто под штанами: " + (under == null ? "узла нет" : under.gameObject.activeSelf.ToString()) + "\n");
    var json = UnityEngine.Resources.Load<UnityEngine.TextAsset>("Clothes/JeansM-materials");
    foreach (var r in wear.GetComponentsInChildren<UnityEngine.Renderer>(true))
    {
        var m = r.sharedMaterial; var c = m.color;
        string slot = r.name == "Pockets" ? "stitch" : r.name == "Belt" ? "belt_leather" : r.name == "Buckle" ? "buckle_metal" : "denim";
        int i = json.text.IndexOf("\"name\": \"" + slot + "\""); var rr = json.text.Substring(i);
        System.Func<string, float> num = k => { int j = rr.IndexOf("\"" + k + "\": ") + k.Length + 4; int e = rr.IndexOfAny(new[] { ',', '\n', '}' }, j); return float.Parse(rr.Substring(j, e - j), System.Globalization.CultureInfo.InvariantCulture); };
        bool ok = UnityEngine.Mathf.Abs(c.r - num("r")) < 0.01f && UnityEngine.Mathf.Abs(c.g - num("g")) < 0.01f && UnityEngine.Mathf.Abs(c.b - num("b")) < 0.01f;
        sb.Append((ok ? "OK " : "RED ") + r.name + " цвет " + c.ToString("F3") + " json " + slot + "\n");
    }
}
finally
{
    if (temp) { uneq.Invoke(eq, new object[] { legs }); if (sync != null) sync.Invoke(wardrobe, null); var u = find("Underwear"); sb.Append((u != null && u.gameObject.activeSelf ? "OK " : "RED ") + "бельё вернулось после снятия\n"); }
}
return sb.ToString();
