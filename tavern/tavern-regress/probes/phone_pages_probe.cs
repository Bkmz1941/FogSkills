// Отпечаток экранов телефона (PhoneUI.Rebuild) по всем страницам: дерево UI блока —
// имя, компоненты, размер, якоря, цвет картинки, текст (часы и секунды нормализованы).
// Страница подставляется отражением в _page, Rebuild зовётся напрямую, в конце страница
// возвращается и телефон пересобирается. Сверка ДО/ПОСЛЕ посимвольно — защита
// рефакторинга PhoneUI.Rebuild. Анимации и тряска на отпечаток не влияют: снимается
// сразу после Rebuild, до следующего кадра. Destroy в Rebuild отложенный, поэтому перед
// каждой страницей блок чистится DestroyImmediate — иначе в дереве висят дети прошлой.
// Разряженный телефон на всех страницах рисует «Нет заряда» — на время пробы заряд 1.
var t = typeof(Tavern.UI.PhoneUI);
var bfs = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var bfi = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var phone = t.GetField("_inst", bfs).GetValue(null) as Tavern.UI.PhoneUI;
if (phone == null) phone = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.PhoneUI>();
if (phone == null) return "КРАСНОЕ: нет PhoneUI";
var fPage = t.GetField("_page", bfi); var fBlock = t.GetField("_block", bfi); var mRebuild = t.GetMethod("Rebuild", bfi);
if (fPage == null || fBlock == null || mRebuild == null) return "КРАСНОЕ: нет _page/_block/Rebuild";
var block = fBlock.GetValue(phone) as UnityEngine.UI.Image;
if (block == null) return "КРАСНОЕ: блок телефона не построен";
object was = fPage.GetValue(phone);
float charge = Cozy.Character.PhoneState.Charge;
Cozy.Character.PhoneState.Charge = 1f;
var clock = new System.Text.RegularExpressions.Regex(@"\d{1,2}:\d\d|\d+ ?(с|мин|%)");
var sb = new System.Text.StringBuilder();
System.Action<UnityEngine.Transform, int> dump = null;
dump = (tr, depth) =>
{
    var rt = tr as UnityEngine.RectTransform;
    var img = tr.GetComponent<UnityEngine.UI.Image>();
    var text = tr.GetComponent<TMPro.TMP_Text>();
    var kinds = new System.Collections.Generic.List<string>();
    foreach (var c in tr.GetComponents<UnityEngine.Component>()) if (c != null && !(c is UnityEngine.Transform) && !(c is UnityEngine.CanvasRenderer)) kinds.Add(c.GetType().Name);
    sb.Append(new string(' ', depth)).Append(tr.name).Append('[').Append(string.Join(",", kinds.ToArray())).Append(']');
    if (rt != null) sb.Append(' ').Append(rt.sizeDelta.ToString("0")).Append(rt.anchoredPosition.ToString("0")).Append(rt.anchorMin.ToString("0.0")).Append(rt.anchorMax.ToString("0.0"));
    if (img != null) sb.Append(" c=").Append(UnityEngine.ColorUtility.ToHtmlStringRGBA(img.color));
    if (text != null) sb.Append(" «").Append(clock.Replace(text.text, "#").Replace("\n", "⏎")).Append('»');
    if (!tr.gameObject.activeSelf) sb.Append(" off");
    sb.Append('\n');
    for (int i = 0; i < tr.childCount; i++) dump(tr.GetChild(i), depth + 1);
};
try
{
    foreach (var page in System.Enum.GetValues(fPage.FieldType))
    {
        fPage.SetValue(phone, page);
        for (int i = block.transform.childCount - 1; i >= 0; i--) UnityEngine.Object.DestroyImmediate(block.transform.GetChild(i).gameObject);
        try { mRebuild.Invoke(phone, null); }
        catch (System.Exception e) { sb.Append("== ").Append(page).Append(": ИСКЛЮЧЕНИЕ ").Append((e.InnerException ?? e).GetType().Name).Append('\n'); continue; }
        sb.Append("== ").Append(page).Append('\n');
        dump(block.transform, 0);
    }
}
finally
{
    Cozy.Character.PhoneState.Charge = charge;
    fPage.SetValue(phone, was);
    for (int i = block.transform.childCount - 1; i >= 0; i--) UnityEngine.Object.DestroyImmediate(block.transform.GetChild(i).gameObject);
    mRebuild.Invoke(phone, null);
}
return sb.ToString();
