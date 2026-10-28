// СНИМОК ПАНЕЛИ ВЫБОРА. Для Unity MCP execute_code (в play), C# 6 (codedom).
// Строит GridCursor.BuildObjectSelection для КАЖДОГО IInteractable уровня и
// выписывает все поля Selection: значения как есть, у делегатов — есть/нет.
// Сверка до/после — посимвольно. Пишет в файл OUT, возвращает число строк.
// Поменяй OUT под метку шага.
string OUT = "/media/ilya/T714/Unity/Tavern-fresh/.git/night/probe/selection_LABEL.txt";
if (!Application.isPlaying) return "не в play";
var cursor = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
if (cursor == null) return "нет GridCursor";
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var build = typeof(Cozy.Grid.GridCursor).GetMethod("BuildObjectSelection", B);
if (build == null) return "нет BuildObjectSelection";
var selType = typeof(Cozy.Grid.GridCursor.Selection);
var fields = selType.GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
System.Array.Sort(fields, (a, b) => string.CompareOrdinal(a.Name, b.Name));
var items = new System.Collections.Generic.List<MonoBehaviour>();
foreach (var m in UnityEngine.Object.FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
    if (m is Cozy.Grid.IInteractable && m.isActiveAndEnabled) items.Add(m);
System.Func<MonoBehaviour, string> key = m => m.GetType().Name + "|" + m.name + "|" + m.transform.position.ToString("0.000");
items.Sort((a, b) => string.CompareOrdinal(key(a), key(b)));
System.Func<object, string> show = null;
show = v =>
{
    if (v == null) return "null";
    if (v is System.Delegate) return "fn";
    if (v is string) return "\"" + v + "\"";
    if (v is float) return ((float)v).ToString("R", System.Globalization.CultureInfo.InvariantCulture);
    if (v is Color) { var c = (Color)v; return "rgba(" + c.r.ToString("R") + "," + c.g.ToString("R") + "," + c.b.ToString("R") + "," + c.a.ToString("R") + ")"; }
    if (v is UnityEngine.Object) { var o = (UnityEngine.Object)v; return o == null ? "destroyed" : o.GetType().Name + ":" + o.name; }
    var arr = v as System.Array;
    if (arr != null)
    {
        var parts = new System.Collections.Generic.List<string>();
        foreach (var e in arr) parts.Add(show(e));
        return "[" + string.Join(";", parts.ToArray()) + "]";
    }
    return v.ToString();
};
var lines = new System.Collections.Generic.List<string>();
foreach (var m in items)
{
    var boxed = build.Invoke(cursor, new object[] { m });
    var row = new System.Text.StringBuilder(key(m));
    foreach (var f in fields)
    {
        var v = f.GetValue(boxed);
        if (v == null) continue;
        if (f.FieldType.IsValueType && !(v is System.Delegate) && v.Equals(System.Activator.CreateInstance(f.FieldType))) continue;
        row.Append(" ").Append(f.Name).Append("=").Append(show(v));
    }
    lines.Add(row.ToString());
}
System.IO.File.WriteAllLines(OUT, lines.ToArray());
return "объектов=" + items.Count + " полей=" + fields.Length + " -> " + OUT;
