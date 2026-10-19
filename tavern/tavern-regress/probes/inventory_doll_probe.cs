// ИНВЕНТАРЬ: ФИГУРА ИГРОКА И ПОПАП «ПРЕДМЕТ» (крит-тема Ильи 18.10, подгруппа «инвентарь», P1153–P1154).
// Для execute_code в play, любой уровень. Стенды свои: копия фигуры игрока (`ItemPreview3D.AttachModel`, как в окне
// инвентаря) и попап предмета (`Attach`) на временном холсте; всё удаляется в finally, уровень не меняется.
//  INV-D01 у фигуры есть сетка пола после SetGrid;
//  INV-D02 камера и сетка фигуры НЕ двигаются: поворот стрелкой, перетаскивание, колесо, подъём средней кнопкой
//          (Илья: «вверх вниз двигаю и двигается сетка»); двигается сама фигура;
//  INV-D03 поворот крутит фигуру вокруг вертикали (без наклона); без увеличения средняя кнопка фигуру НЕ двигает
//          (Илья 19.10: «если я не приближал, то вверх-вниз нельзя двигать»);
//  INV-D04 ноги не уходят под сетку на старте и при колесе;
//  INV-D05 сетка фигуры переживает попап предмета с другой толщиной линий (Илья: «открыл попап объекта, закрыл —
//          пропала сетка у игрока»): у каждого стенда СВОЯ текстура сетки, чужой стенд её не трогает;
//  INV-D06 фон попапа предмета = фон фигуры игрока (Илья: «фон сетки и фон игрока сделай одинаковым»).
//  (19.10: при увеличении фигура опускается ВМЕСТЕ с сеткой — иначе голову не увидеть, не нарушив «ноги не под сеткой»)
//  INV-D07 фигуру нельзя уменьшить колесом (Илья 19.10: «вообще не давай уменьшить»); при максимальном увеличении
//          её можно опустить так, что макушка в кадре (Илья: «ноги могу посмотреть, а голову нет»);
//  INV-D08 сетка не гаснет никогда, ноги не заходят под неё ни при каком опускании (Илья 19.10: «сетка никогда не
//          должна исчезать, игрок её не должен пересекать — добавь отступ»).
if (!UnityEngine.Application.isPlaying) return "не в play";
var F = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance;
var T = typeof(Tavern.UI.ItemPreview3D);
var sb = new System.Text.StringBuilder();
int bad = 0, checks = 0;
System.Action<bool, string> Ok = (ok, code) => { checks++; if (!ok) { bad++; sb.Append("FAIL " + code + "\n"); } };
System.Func<object, string, object> Get = (o, f) => { var fi = T.GetField(f, F); return fi == null ? null : fi.GetValue(o); };
var player = Cozy.Grid.PlayerRef.GameObject;
var visual = player != null ? player.transform.Find("Visual") : null;
if (visual == null) return "нет фигуры игрока (Visual)";
var holder = new UnityEngine.GameObject("InvDollProbeHolder", typeof(UnityEngine.RectTransform));
((UnityEngine.RectTransform)holder.transform).sizeDelta = new UnityEngine.Vector2(360f, 560f);
var itemHolder = new UnityEngine.GameObject("InvDollProbeItem", typeof(UnityEngine.RectTransform));
((UnityEngine.RectTransform)itemHolder.transform).sizeDelta = new UnityEngine.Vector2(640f, 480f);
try
{
    var IS = typeof(Tavern.UI.InventoryScreenUI);
    System.Func<string, float> K = n => System.Convert.ToSingle(IS.GetField(n, System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).GetRawConstantValue());
    var doll = Tavern.UI.ItemPreview3D.AttachModel((UnityEngine.RectTransform)holder.transform, visual, K("DollYaw"), Tavern.UI.InventoryScreenUI.PanelLook.DollCamPitch,
        K("DollPitchLimit"), K("DollZoom"), K("DollZoomMin"), K("DollZoomMax"), K("DollLight"));
    if (doll == null) return "КРАСНОЕ: фигура не собралась";
    doll.SetGrid(0.35f, 1.25f, 1.6f);
    var cam = (UnityEngine.Camera)Get(doll, "_cam");
    UnityEngine.Transform grid = null;
    foreach (var t in cam.transform.parent.GetComponentsInChildren<UnityEngine.Transform>()) if (t.name == "ItemPreviewGrid") grid = t;
    Ok(grid != null, "INV-D01 нет сетки");
    if (grid == null) return "КРАСНОЕ: 1\n" + sb;
    var gridRend = grid.GetComponent<UnityEngine.Renderer>();
    var camPos = cam.transform.position; var camRot = cam.transform.rotation;
    var gridView = cam.WorldToViewportPoint(grid.position);
    System.Func<float> Feet = () =>
    {
        float low = float.MaxValue;
        foreach (var r in doll.Model.GetComponentsInChildren<UnityEngine.Renderer>())
            if (r != null && r.enabled && r.gameObject.activeInHierarchy) low = UnityEngine.Mathf.Min(low, r.bounds.min.y);
        return low;
    };
    System.Action<string> Still = stage =>
    {
        bool camStill = (cam.transform.position - camPos).sqrMagnitude < 1e-10f && UnityEngine.Quaternion.Angle(cam.transform.rotation, camRot) < 0.01f;
        bool gridStill = (cam.WorldToViewportPoint(grid.position) - gridView).sqrMagnitude < 1e-8f;
        Ok(camStill && gridStill, "INV-D02 " + stage + (camStill ? "" : " камера поехала") + (gridStill ? "" : " сетка поехала на экране"));
        Ok(Feet() > grid.position.y - 0.01f, "INV-D04 " + stage + " ноги под сеткой");
    };
    Still("старт");
    var model = doll.Model;
    var fwd0 = model.forward; var pos0 = model.position;
    doll.Turn(30f);
    Still("стрелка");
    Ok(UnityEngine.Vector3.Angle(model.forward, fwd0) > 20f, "INV-D03 стрелка не повернула фигуру");
    Ok(UnityEngine.Vector3.Angle(model.up, UnityEngine.Vector3.up) < 0.5f, "INV-D03 фигура наклонилась");
    var es = UnityEngine.EventSystems.EventSystem.current;
    var drag = new UnityEngine.EventSystems.PointerEventData(es) { button = UnityEngine.EventSystems.PointerEventData.InputButton.Left, delta = new UnityEngine.Vector2(60f, 40f) };
    doll.OnDrag(drag);
    Still("перетаскивание");
    Ok(UnityEngine.Vector3.Angle(model.up, UnityEngine.Vector3.up) < 0.5f, "INV-D03 перетаскивание наклонило фигуру");
    var y0 = model.position.y;
    var lift = new UnityEngine.EventSystems.PointerEventData(es) { button = UnityEngine.EventSystems.PointerEventData.InputButton.Middle, delta = new UnityEngine.Vector2(0f, 80f) };
    doll.OnDrag(lift);
    Still("подъём средней кнопкой");
    Ok(UnityEngine.Mathf.Abs(model.position.y - y0) < 1e-5f, "INV-D03 без увеличения средняя кнопка сдвинула фигуру");
    doll.OnDrag(new UnityEngine.EventSystems.PointerEventData(es) { button = UnityEngine.EventSystems.PointerEventData.InputButton.Middle, delta = new UnityEngine.Vector2(0f, -80f) });
    Ok(UnityEngine.Mathf.Abs(model.position.y - y0) < 1e-5f, "INV-D03 без увеличения средняя кнопка опустила фигуру");
    foreach (var dir in new[] { 1f, -1f, -1f, -1f })
    {
        var wheel = new UnityEngine.EventSystems.PointerEventData(es) { scrollDelta = new UnityEngine.Vector2(0f, dir) };
        doll.OnScroll(wheel);
        Still(dir > 0 ? "колесо ближе" : "колесо дальше");
    }
    doll.ResetView();
    Still("вид по умолчанию");

    var grid0 = gridRend.sharedMaterial.GetColor("_BaseColor").a;
    float h0 = 0f;
    { var b0 = doll.Model.GetComponentsInChildren<UnityEngine.Renderer>(); float lo = float.MaxValue, hi = float.MinValue; foreach (var r in b0) if (r.enabled) { lo = UnityEngine.Mathf.Min(lo, r.bounds.min.y); hi = UnityEngine.Mathf.Max(hi, r.bounds.max.y); } h0 = hi - lo; }
    for (int i = 0; i < 10; i++) doll.OnScroll(new UnityEngine.EventSystems.PointerEventData(es) { scrollDelta = new UnityEngine.Vector2(0f, -1f) });
    { var b1 = doll.Model.GetComponentsInChildren<UnityEngine.Renderer>(); float lo = float.MaxValue, hi = float.MinValue; foreach (var r in b1) if (r.enabled) { lo = UnityEngine.Mathf.Min(lo, r.bounds.min.y); hi = UnityEngine.Mathf.Max(hi, r.bounds.max.y); }
      Ok(hi - lo >= h0 - 1e-3f, "INV-D07 колесо уменьшило фигуру: " + (hi - lo).ToString("0.000") + " < " + h0.ToString("0.000")); }
    for (int i = 0; i < 10; i++) doll.OnScroll(new UnityEngine.EventSystems.PointerEventData(es) { scrollDelta = new UnityEngine.Vector2(0f, 1f) });
    var yZoomed = model.position.y;
    float gapZoomed = Feet() - grid.position.y;
    for (int i = 0; i < 40; i++) doll.OnDrag(new UnityEngine.EventSystems.PointerEventData(es) { button = UnityEngine.EventSystems.PointerEventData.InputButton.Middle, delta = new UnityEngine.Vector2(0f, -120f) });
    float top = float.MinValue;
    foreach (var r in doll.Model.GetComponentsInChildren<UnityEngine.Renderer>()) if (r.enabled) top = UnityEngine.Mathf.Max(top, r.bounds.max.y);
    var topCenter = doll.Model.position; topCenter.y = top;
    sb.Append("инфо: при максимальном увеличении и полном опускании макушка на y=" + cam.WorldToViewportPoint(topCenter).y.ToString("0.00") + " кадра\n");
    Ok(model.position.y < yZoomed - 1e-4f, "INV-D07 увеличенную фигуру не опустить средней кнопкой");
    Ok((cam.transform.position - camPos).sqrMagnitude < 1e-10f, "INV-D02 опускание увеличенной фигуры сдвинуло камеру");
    Ok(UnityEngine.Mathf.Abs((Feet() - grid.position.y) - gapZoomed) < 1e-3f, "INV-D08 увеличенная фигура опускается без своей сетки (ноги и сетка разошлись)");
    Ok(cam.WorldToViewportPoint(topCenter).y <= 1.001f, "INV-D07 при максимальном увеличении макушку не опустить в кадр");
    Ok(Feet() > grid.position.y + 1e-4f, "INV-D08 опущенная фигура зашла ногами под сетку");
    Ok(gridRend.enabled && UnityEngine.Mathf.Abs(gridRend.sharedMaterial.GetColor("_BaseColor").a - grid0) < 1e-4f, "INV-D08 сетка погасла");
    doll.ResetView();

    var dollTex = gridRend.sharedMaterial.GetTexture("_BaseMap");
    UnityEngine.Texture itemTex = null;
    var milk = Cozy.Grid.FurnitureCatalog.ById("milk_carton");
    Cozy.Grid.ObjectDef itemDef = milk;
    if (itemDef == null)
        foreach (var d in Cozy.Grid.FurnitureCatalog.All()) if (d != null && !string.IsNullOrEmpty(d.pickupItemId)) { itemDef = d; break; }
    var item = Tavern.UI.ItemPreview3D.Attach((UnityEngine.RectTransform)itemHolder.transform, itemDef);
    if (item != null)
    {
        item.SetGrid(0.35f, 1.05f, 3.3f);
        var ig = (UnityEngine.Renderer)Get(item, "_grid");
        if (ig != null) itemTex = ig.sharedMaterial.GetTexture("_BaseMap");
        UnityEngine.Object.DestroyImmediate(item.gameObject);
    }
    var ownTex = Get(doll, "_gridTex") as UnityEngine.Texture;
    Ok(T.GetField("_gridTex", F) != null && !T.GetField("_gridTex", F).IsStatic, "INV-D05 текстура сетки общая на все стенды (static)");
    Ok(dollTex != null && ownTex == dollTex && itemTex != null && !ReferenceEquals(itemTex, dollTex), "INV-D05 попап предмета подменил/удалил текстуру сетки фигуры");
    Ok(gridRend.sharedMaterial.GetTexture("_BaseMap") == dollTex, "INV-D05 после закрытия попапа у фигуры другая текстура");

    var inspectBack = Tavern.UI.InventoryScreenUI.InspectLook.BackColor;
    var figureBack = Tavern.UI.InventoryScreenUI.PanelLook.FigureBack;
    Ok(inspectBack == figureBack, "INV-D06 фон попапа " + UnityEngine.ColorUtility.ToHtmlStringRGBA(inspectBack) + " ≠ фон фигуры " + UnityEngine.ColorUtility.ToHtmlStringRGBA(figureBack));
}
finally
{
    UnityEngine.Object.DestroyImmediate(holder);
    UnityEngine.Object.DestroyImmediate(itemHolder);
}
return (bad == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + bad + " из " + checks) + "\n" + sb;
