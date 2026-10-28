// Отпечаток нижнего меню HUD: по очереди открывает каждую вкладку (строительство,
// объекты, окружение, текстуры, одежда, растительность, ландшафт, анимации, модели,
// монстры, смена уровня, уровни, спавны, зоны, геймплей), снимает активное дерево
// HudCanvas (путь, размер, позиция, текст, цвет картинки) и закрывает вкладку тем же
// тумблером. Полный отпечаток — в файл /tmp/hud_menu_<метка>.txt, ответ — число
// строк и хеш. Защита рефакторинга построителей меню (PaletteRoom, PaletteUsables,
// BuildLevelsManager, BuildSelectionPanel). Верхняя панель (часы, FPS) не снимается — шум.
// Только в play; уровень не меняет.
// Метка — первая строка кода: var label = "...";
var label = "probe";
if (!UnityEngine.Application.isPlaying) return "не в play";
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
if (hud == null) return "КРАСНОЕ: нет HudUI";
var t = typeof(Tavern.UI.HudUI);
var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var canvas = UnityEngine.GameObject.Find("HudCanvas");
if (canvas == null) return "КРАСНОЕ: нет HudCanvas";
var tabs = new string[] { "ToggleBuild", "ToggleObjects", "ToggleEnvironment", "ToggleTextures", "ToggleClothes", "ToggleVegetation",
    "ToggleTerrain", "ToggleAnimations", "ToggleModels", "ToggleMonsters", "ToggleLevelSelect", "ToggleLevelsManager",
    "ToggleSpecial", "ToggleZones", "ToggleGameplay" };
var inv = System.Globalization.CultureInfo.InvariantCulture;
var sb = new System.Text.StringBuilder();
System.Action<UnityEngine.Transform, string> dump = null;
dump = (tr, path) =>
{
    if (!tr.gameObject.activeInHierarchy) return;
    if (tr.name == "TopBar") return;
    string p = path + "/" + tr.name;
    var rt = tr as UnityEngine.RectTransform;
    sb.Append(p);
    if (rt != null) sb.Append(" s=").Append(rt.rect.width.ToString("0.#", inv)).Append("x").Append(rt.rect.height.ToString("0.#", inv))
        .Append(" p=").Append(rt.anchoredPosition.x.ToString("0.#", inv)).Append(",").Append(rt.anchoredPosition.y.ToString("0.#", inv));
    var text = tr.GetComponent<TMPro.TMP_Text>();
    if (text != null) sb.Append(" t=").Append(text.text.Replace("\n", "\\n"));
    var img = tr.GetComponent<UnityEngine.UI.Image>();
    if (img != null) sb.Append(" c=").Append(UnityEngine.ColorUtility.ToHtmlStringRGBA(img.color));
    sb.Append('\n');
    for (int i = 0; i < tr.childCount; i++) dump(tr.GetChild(i), p);
};
var missing = new System.Collections.Generic.List<string>();
foreach (var name in tabs)
{
    var m = t.GetMethod(name, bf);
    if (m == null) { missing.Add(name); continue; }
    sb.Append("=== ").Append(name).Append('\n');
    m.Invoke(hud, null);
    UnityEngine.Canvas.ForceUpdateCanvases();
    dump(canvas.transform, "");
    m.Invoke(hud, null);
    UnityEngine.Canvas.ForceUpdateCanvases();
}
var all = sb.ToString();
System.IO.File.WriteAllText("/tmp/hud_menu_" + label + ".txt", all);
int lines = all.Split('\n').Length;
int hash = 17;
foreach (char ch in all) hash = unchecked(hash * 31 + ch);
return "hud_menu " + label + ": строк " + lines + ", хеш " + hash.ToString("X8") + (missing.Count > 0 ? ", нет методов: " + string.Join(",", missing) : "");
