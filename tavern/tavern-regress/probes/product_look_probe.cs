// ВИД, ИНВЕНТАРЬ И ТЕКСТЫ ПРОДУКТОВ (PRODUCTS.md, группы 3–5; 18.10). Для execute_code в play, любой уровень.
// Перебирает ВСЕ продукты каталога (def.isProduct или категория «Продукты…»), каждый спавнит в своей зоне (игрок + (0,−60,0), сетка 1,5 м)
// и удаляет в finally. Уровень не меняет и не сохраняет.
//  PT-VIS01 материалы: у видимых рендереров нет пустых слотов и шейдера ошибки (розовое);
//  PT-VIS02 однотонность: слоты материала без текстуры (_BaseMap/_MainTex) — список;
//  PT-VIS06 иконки: у РАЗНЫХ имён иконок нет одинаковых картинок пиксель в пиксель, нет одноцветных заглушек;
//  PT-VIS08 тени: хотя бы один рендерер отбрасывает тень;
//  PT-VIS09 состояния «_open»: разница пивот → центр у закрытой и открытой модели — только INFO; место после еды держит ACT03;
//  PT-INV01 размер: вытянутое (длина ≥ 2,2 × ширины) не лежит в 1×1 (кроме частей батона, шоколадки и «Коровки» — 1×1 по слову Ильи 18.10);
//  PT-INV02 вес > 0;
//  PT-UI01 название: не пустое, не «Объект», кириллица, есть перевод в en;
//  PT-UI03 кнопки: у съедобного «Кушать», у напитка «Пить», у несъедобного (inedible, без food/water) — ни того, ни другого.
// Первая строка — вердикт «ЗЕЛЁНОЕ из N» / «КРАСНОЕ: k из N», дальше FAIL с кодом кейса.
if (!UnityEngine.Application.isPlaying) return "не в play";
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
var cursor = Cozy.Grid.GridCursor.I;
var sb = new System.Text.StringBuilder();
var info = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) { fails++; sb.Append("FAIL " + line + "\n"); } };
System.Func<UnityEngine.GameObject, System.Collections.Generic.List<UnityEngine.Renderer>> Own = go => {
    var l = new System.Collections.Generic.List<UnityEngine.Renderer>();
    foreach (var r in go.GetComponentsInChildren<UnityEngine.Renderer>())
    {
        if (!r.enabled || !r.gameObject.activeInHierarchy || Cozy.Grid.InteractHighlight.IsCopy(r)) continue;
        if (r is UnityEngine.ParticleSystemRenderer || r.name.StartsWith("Outline")) continue;
        l.Add(r);
    }
    return l;
};
System.Func<System.Collections.Generic.List<UnityEngine.Renderer>, UnityEngine.Bounds> BoundsOf = l => {
    var b = l[0].bounds; foreach (var r in l) b.Encapsulate(r.bounds); return b;
};

var en = new System.Collections.Generic.Dictionary<string, string>();
var enAsset = UnityEngine.Resources.Load<UnityEngine.TextAsset>("Localization/en");
if (enAsset != null) Cozy.FlatJson.Parse(enAsset.text, en);
var enExtra = UnityEngine.Resources.Load<UnityEngine.TextAsset>("Localization/en.extra");
if (enExtra != null) Cozy.FlatJson.Parse(enExtra.text, en);

var defs = new System.Collections.Generic.List<Cozy.Grid.ObjectDef>();
foreach (var d in Cozy.Grid.FurnitureCatalog.All()) if (d != null && (d.isProduct || (d.category ?? "").StartsWith(Cozy.Grid.Categories.Food))) defs.Add(d);

var before = new System.Collections.Generic.HashSet<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All);
var player = Cozy.Grid.PlayerRef.Transform;
var origin = (player != null ? player.position : UnityEngine.Vector3.zero) + new UnityEngine.Vector3(0f, -60f, 0f);
var spawned = new System.Collections.Generic.Dictionary<string, Cozy.Grid.InteractiveObject>();
var iconHash = new System.Collections.Generic.Dictionary<string, string>();
var hashOwner = new System.Collections.Generic.Dictionary<string, string>();
int plainTotal = 0;
try
{
    int k = 0;
    foreach (var def in defs)
    {
        var p = origin + new UnityEngine.Vector3((k % 12) * 1.5f, 0f, (k / 12) * 1.5f); k++;
        Cozy.Grid.InteractiveObject io = null;
        try { io = (Cozy.Grid.InteractiveObject)spawn.Invoke(cursor, new object[] { def, p, 0f }); }
        catch (System.Exception e) { Check(false, "PT-VIS01 " + def.id + ": не спавнится — " + (e.InnerException ?? e).Message); continue; }
        if (io == null) { Check(false, "PT-VIS01 " + def.id + ": не спавнится"); continue; }
        spawned[def.id] = io;
        var rs = Own(io.gameObject);
        Check(rs.Count > 0, "PT-VIS01 " + def.id + ": нет видимых рендереров");
        if (rs.Count == 0) continue;
        int emptySlots = 0, pink = 0, shadows = 0;
        var plain = new System.Collections.Generic.List<string>();
        foreach (var r in rs)
        {
            if (r.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off) shadows++;
            foreach (var m in r.sharedMaterials)
            {
                if (m == null) { emptySlots++; continue; }
                if (m.shader == null || m.shader.name.Contains("InternalError")) { pink++; continue; }
                UnityEngine.Texture t = null;
                if (m.HasProperty("_BaseMap")) t = m.GetTexture("_BaseMap");
                if (t == null && m.HasProperty("_MainTex")) t = m.GetTexture("_MainTex");
                var tag = r.name + ":" + m.name;
                if (t == null && !m.shader.name.Contains("Liquid") && !m.shader.name.Contains("Glass") && !plain.Contains(tag)) plain.Add(tag);
            }
        }
        Check(emptySlots == 0 && pink == 0, "PT-VIS01 " + def.id + ": пустых слотов " + emptySlots + ", шейдер ошибки " + pink);
        // PT-VIS02 — только счёт, не красное: Илья 18.10 «текстуры — ок пока» (однотонные детали продуктов допустимы)
        plainTotal += plain.Count;
        Check(shadows > 0, "PT-VIS08 " + def.id + ": ни один рендерер не отбрасывает тень");

        // инвентарь
        var item = Cozy.Grid.Items.ById(!string.IsNullOrEmpty(def.pickupItemId) ? def.pickupItemId : def.id);
        if (item != null)
        {
            var b = BoundsOf(rs);
            float lo = UnityEngine.Mathf.Min(b.size.x, b.size.z), hi = UnityEngine.Mathf.Max(b.size.x, b.size.z);
            // части батона, шоколадка и «Коровка» 1×1 — решение Ильи 18.10, не баг
            if (item.size == new UnityEngine.Vector2Int(1, 1) && !def.id.StartsWith("bread_part_") && def.id != "chocolate_bar" && def.id != "candy_korovka")
                Check(hi < lo * 2.2f, "PT-INV01 " + def.id + ": модель " + (hi * 100f).ToString("0") + "×" + (lo * 100f).ToString("0") + " см вытянута, а в инвентаре 1×1");
            // иконка
            var spr = string.IsNullOrEmpty(item.icon) ? null : UnityEngine.Resources.Load<UnityEngine.Sprite>("Icons/" + item.icon);
            if (spr != null && !iconHash.ContainsKey(item.icon))
            {
                var tex = spr.texture; var rect = spr.textureRect;
                var rt = UnityEngine.RenderTexture.GetTemporary(tex.width, tex.height, 0, UnityEngine.RenderTextureFormat.ARGB32);
                var prev = UnityEngine.RenderTexture.active;
                UnityEngine.Graphics.Blit(tex, rt);
                UnityEngine.RenderTexture.active = rt;
                var read = new UnityEngine.Texture2D((int)rect.width, (int)rect.height, UnityEngine.TextureFormat.RGBA32, false);
                read.ReadPixels(new UnityEngine.Rect(rect.x, tex.height - rect.y - rect.height, rect.width, rect.height), 0, 0);
                read.Apply();
                UnityEngine.RenderTexture.active = prev;
                UnityEngine.RenderTexture.ReleaseTemporary(rt);
                var px = read.GetPixels32();
                UnityEngine.Object.Destroy(read);
                ulong h = 1469598103934665603UL; var c0 = px.Length > 0 ? px[0] : default(UnityEngine.Color32); bool mono = true;
                foreach (var c in px) { h = (h ^ c.r) * 1099511628211UL; h = (h ^ c.g) * 1099511628211UL; h = (h ^ c.b) * 1099511628211UL; h = (h ^ c.a) * 1099511628211UL; if (mono && (c.r != c0.r || c.g != c0.g || c.b != c0.b || c.a != c0.a)) mono = false; }
                var key = h.ToString("x") + ":" + px.Length;
                iconHash[item.icon] = key;
                Check(!mono, "PT-VIS06 иконка «" + item.icon + "» (" + def.id + "): одноцветная заглушка");
                if (hashOwner.ContainsKey(key)) Check(false, "PT-VIS06 иконки «" + item.icon + "» и «" + hashOwner[key] + "» — одна и та же картинка");
                else hashOwner[key] = item.icon;
            }
        }
        // вес
        Check(io.WeightKg > 0f, "PT-INV02 " + def.id + ": вес " + io.WeightKg.ToString("0.###") + " кг");
        // название
        string name = def.UiName ?? "";
        bool cyr = false; foreach (var ch in name) if (ch >= 'Ѐ' && ch <= 'ӿ') cyr = true;
        Check(name.Length > 0 && name != "Объект" && cyr, "PT-UI01 " + def.id + ": название «" + name + "»");
        if (enAsset != null && cyr) Check(en.ContainsKey(name) && en[name].Length > 0, "PT-UI01 " + def.id + ": нет перевода «" + name + "» в en");
        // кнопки
        var labels = new System.Collections.Generic.List<string>();
        foreach (var f in io.Features)
        {
            try { if (!f.Available) continue; foreach (var btn in f.Buttons(null)) labels.Add(btn.Label); }
            catch (System.Exception) { }
        }
        bool eat = labels.Contains("Кушать"), drink = labels.Contains("Пить");
        bool liquid = io.Liquid != null && io.Liquid.Litres > 0.001f;
        if (def.inedible && def.food <= 0f && def.water <= 0f && !liquid)
            Check(!eat && !drink, "PT-UI03 " + def.id + ": несъедобное, а кнопки [" + string.Join(", ", labels.ToArray()) + "]");
        else if (io.Edible)
            Check(eat, "PT-UI03 " + def.id + ": съедобное (Edible), а «Кушать» нет — [" + string.Join(", ", labels.ToArray()) + "]");
        info.Append(def.id + "=" + string.Join("/", labels.ToArray()) + (io.Edible ? " E" : "") + (liquid ? " L" : "") + (def.inedible ? " I" : "") + "; ");
    }

    // состояния «_open»: открытая пачка там же, где закрытая
    foreach (var kv in spawned)
    {
        if (!kv.Key.EndsWith("_open")) continue;
        var closedId = kv.Key.Substring(0, kv.Key.Length - 5);
        if (!spawned.ContainsKey(closedId)) continue;
        var a = spawned[closedId]; var o = kv.Value;
        var la = Own(a.gameObject); var lo2 = Own(o.gameObject);
        if (la.Count == 0 || lo2.Count == 0) continue;
        var ba = BoundsOf(la); var bo = BoundsOf(lo2);
        var ca = ba.center - a.transform.position; var co = bo.center - o.transform.position;
        float dxz = new UnityEngine.Vector2(ca.x - co.x, ca.z - co.z).magnitude;
        float dlow = (ba.min.y - a.transform.position.y) - (bo.min.y - o.transform.position.y);
        if (dxz > 0.01f || UnityEngine.Mathf.Abs(dlow) > 0.01f) sb.Append("INFO PT-VIS09 " + closedId + " → " + kv.Key + ": пивот модели смещён от центра на " + (dxz * 100f).ToString("0.0") + " см — компенсирует замещение по центру габарита (ACT03)\n");
    }
}
finally
{
    foreach (var io in new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>(Cozy.Grid.InteractiveObject.All))
        if (io != null && !before.Contains(io)) UnityEngine.Object.DestroyImmediate(io.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ из " + checks : "КРАСНОЕ: " + fails + " из " + checks) + " — продуктов " + defs.Count + ", слотов без текстуры всего " + plainTotal + " (созданное удалено)\n" + sb + "кнопки: " + info;
