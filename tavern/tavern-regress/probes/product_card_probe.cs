if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0, checks = 0;
System.Action<bool, string> Ok = (ok, what) => { checks++; if (!ok) fails++; sb.Append((ok ? "OK " : "FAIL ") + what + "\n"); };
var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
Cozy.Grid.InteractiveObject table = null;
foreach (var io in Cozy.Grid.InteractiveObject.All)
    if (io != null && io.Def != null && io.Def.id == "office_desk") { table = io; break; }
UnityEngine.Vector3 at;
if (table != null)
{
    float top = float.MinValue;
    foreach (var c in table.GetComponentsInChildren<UnityEngine.Collider>()) top = UnityEngine.Mathf.Max(top, c.bounds.max.y);
    at = new UnityEngine.Vector3(table.transform.position.x, top, table.transform.position.z);
}
else at = Cozy.Grid.GridCursor.I.transform.position;
var made = new System.Collections.Generic.List<Cozy.Grid.InteractiveObject>();
var rows = new System.Collections.Generic.List<Cozy.Grid.ItemEffect>();
System.Func<string, float, Cozy.Grid.InteractiveObject> Make = (id, dx) =>
{
    var o = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { Cozy.Grid.FurnitureCatalog.ById(id), at + new UnityEngine.Vector3(dx, 0f, 0f), 0f });
    made.Add(o);
    return o;
};
System.Func<System.Collections.Generic.List<Cozy.Grid.ItemEffect>, string> Show = list =>
{
    var s = new System.Text.StringBuilder();
    foreach (var e in list) s.Append("[" + e.Icon + " «" + e.Text + "» подсказка=" + (e.Hint ?? "нет") + " тон=" + (e.Tone ?? "нет") + "] ");
    return s.ToString();
};
System.Func<Cozy.Grid.InteractiveObject, System.Collections.Generic.List<Cozy.Grid.ItemEffect>> InHand = o =>
{
    var list = new System.Collections.Generic.List<Cozy.Grid.ItemEffect>();
    var item = Cozy.Grid.Items.ById(o.Def.pickupItemId);
    var placed = new Cozy.Grid.PlacedItem { def = item, state = Cozy.Grid.LiquidState.Of(o) };
    Cozy.Grid.ItemEffects.Collect(item, placed, list);
    return list;
};
try
{
    // PT-P01/P02: масло и кетчуп — одна строка «осталось Nед», без жажды и без подсказки, свой тон.
    foreach (var id in new[] { "oil_bottle", "ketchup" })
    {
        var o = Make(id, made.Count * 0.3f - 0.45f);
        int units = Cozy.Grid.LiquidVolume.Units(o.Liquid.Litres);
        for (int pass = 0; pass < 2; pass++)
        {
            string where = pass == 0 ? "в мире" : "в инвентаре";
            if (pass == 0) Cozy.Grid.ItemEffects.Collect(o, rows); else rows = InHand(o);
            bool one = rows.Count == 1;
            var r = one ? rows[0] : default(Cozy.Grid.ItemEffect);
            Ok(one && r.Icon == "effect-water" && r.Text == units + "ед" && string.IsNullOrEmpty(r.Hint)
                && r.Tone == Cozy.Grid.ItemEffects.LiquidLeftTone && Tavern.UI.HudLook.ToneOf(r.Tone) != null,
                "PT-P01 " + id + " " + where + ": одна строка «" + units + "ед», без подсказки, свой тон — " + Show(rows));
        }
        Ok(units == 25, "PT-P01 " + id + ": полная бутылка = 25ед (0,5 л × 50) — " + units);
        o.Liquid.Take(0.02f);
        Cozy.Grid.ItemEffects.Collect(o, rows);
        int left = Cozy.Grid.LiquidVolume.Units(o.Liquid.Litres);
        Ok(left == 24 && rows.Count == 1 && rows[0].Text == "24ед", "PT-P02 " + id + ": после порции 0,02 л строка «24ед» — " + Show(rows));
    }
    // PT-P03/P04: газировка как бутылка воды — «Пить», «+35ед», вес 1,3 кг полная, выпитая «0ед».
    foreach (var id in new[] { "water_soda", "water_bottle" })
    {
        var o = Make(id, made.Count * 0.3f - 0.45f);
        Ok(o.Liquid != null && o.Liquid.Litres > 0.99f && o.Liquid.Kind == Cozy.Grid.LiquidVolume.Water,
            "PT-P03 " + id + ": налит литр воды — " + (o.Liquid == null ? "жидкости нет" : o.Liquid.Kind + " " + o.Liquid.Litres.ToString("0.00") + " л"));
        bool drink = false;
        foreach (var f in o.Features) if (f.GetType().Name == "DrinkFeature") drink = true;
        Ok(drink && Cozy.Cooking.Nutrition.Drinkable(o.Liquid), "PT-P03 " + id + ": есть «Пить»");
        float perLitre = Cozy.Cooking.Nutrition.LiquidValue(Cozy.Grid.LiquidVolume.Water).Water;
        for (int pass = 0; pass < 3; pass++)
        {
            if (pass == 2) o.Liquid.Take(0.3f);
            string want = "+" + UnityEngine.Mathf.RoundToInt(perLitre * o.Liquid.Litres) + "ед";
            if (pass == 1) rows = InHand(o); else Cozy.Grid.ItemEffects.Collect(o, rows);
            bool plus = false;
            foreach (var r in rows) if (r.Icon == "effect-water" && r.Text == want && r.Hint == "Утоление жажды") plus = true;
            Ok(plus, "PT-P03 " + id + (pass == 0 ? " полная в мире" : pass == 1 ? " полная в инвентаре" : " отпита до 0,7 л") + ": «" + want + "» как у воды, подсказка «Утоление жажды» — " + Show(rows));
        }
        if (id == "water_soda")
        {
            float kg = Cozy.Character.Carry.KgOf(o);
            Ok(UnityEngine.Mathf.Abs(kg - 1.0f) < 0.06f, "PT-P03 water_soda: 0,3 кг бутылка + 0,7 л воды = 1,0 кг — " + kg.ToString("0.00"));
        }
        o.Liquid.Take(o.Liquid.Litres);
        Cozy.Grid.ItemEffects.Collect(o, rows);
        bool zero = false;
        foreach (var r in rows) if (r.Icon == "effect-water" && r.Text == "0ед") zero = true;
        Ok(zero, "PT-P04 " + id + ": выпитая показывает «0ед» — " + Show(rows));
    }
}
finally
{
    foreach (var o in made) if (o != null) UnityEngine.Object.DestroyImmediate(o.gameObject);
}
return (fails == 0 ? "ЗЕЛЁНОЕ" : "КРАСНОЕ: " + fails) + " из " + checks + " (свои бутылки, созданы и удалены" + (table == null ? ", стола нет — у курсора" : "") + ")\n" + sb;
