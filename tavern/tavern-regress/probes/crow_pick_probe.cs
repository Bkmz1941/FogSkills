// Характеризующий замер выбора места посадки птицы (CrowFlight.PickTarget), 16.09.
// Запуск: python3 measure.py crow_pick_probe.cs /путь/до.txt → правка → то же в после.txt → diff.
// Каждая птица уровня × 6 позиций у игрока × дождь × испуг × «охота»: Random.InitState с
// фиксированным сидом, PickTarget через отражение, печать места и СЛЕДУЮЩЕГО Random.value —
// оно ловит, если правка поменяла порядок вызовов Random. Гнездо печатается номером, а не
// координатой: ветки качает ветер. Все выключенные ветки на время замера включаются, дождь,
// позиция и «охота» птицы возвращаются. Нужен play.
var inv = System.Globalization.CultureInfo.InvariantCulture;
var T = typeof(Cozy.Grid.CrowFlight);
var pick = T.GetMethod("PickTarget", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
if (pick == null) return "нет PickTarget";
var sb = new System.Text.StringBuilder();
var perchWas = new System.Collections.Generic.List<bool>();
foreach (var p in Cozy.Grid.CrowPerch.All) { perchWas.Add(p != null && p.On); if (p != null && !p.On) p.SetOn(true); }
bool rainWas = Cozy.Grid.Weather.Rain;
var birds = new System.Collections.Generic.List<Cozy.Grid.CrowFlight>(Cozy.Grid.CrowFlight.All);
sb.Append("птиц=").Append(birds.Count).Append(" веток=").Append(Cozy.Grid.CrowPerch.All.Count).Append('\n');
var player = Cozy.Grid.PlayerRef.Transform;
var center = player != null ? player.position : Vector3.zero;
try
{
    int b = 0;
    foreach (var bird in birds)
    {
        if (bird == null) continue;
        var keep = bird.transform.position;
        bool nearWas = bird.Near;
        int k = 0;
        foreach (var off in new[] { new Vector3(0, 0, 0), new Vector3(4, 0, 0), new Vector3(-6, 0, 3), new Vector3(2, 0, -8), new Vector3(10, 0, 10), new Vector3(-12, 0, -4) })
        {
            foreach (var rain in new[] { false, true })
            foreach (var flee in new[] { false, true })
            foreach (var near in new[] { false, true })
            {
                Cozy.Grid.Weather.Rain = rain;
                bird.RestoreNear(near);
                bird.transform.position = center + off + Vector3.up * 1.5f;
                UnityEngine.Random.InitState(9173 + k * 31 + b * 7);
                var args = new object[] { flee, null, null };
                bool ok = (bool)pick.Invoke(bird, args);
                var pt = (Vector3)args[1];
                float yaw = (float)args[2];
                string where = pt.ToString("F3") + " " + yaw.ToString("F2", inv);
                int pi = 0;
                foreach (var perch in Cozy.Grid.CrowPerch.All)
                {
                    if (perch != null)
                        for (int m = 0; m < perch.MountCount; m++)
                            if (perch.MountOf(m) != null && (perch.MountOf(m).position - pt).sqrMagnitude < 0.0001f)
                                where = "гнездо " + pi + "/" + m;
                    pi++;
                }
                sb.Append(b).Append(' ').Append(k).Append(" rain=").Append(rain ? 1 : 0).Append(" flee=").Append(flee ? 1 : 0).Append(" near=").Append(near ? 1 : 0)
                  .Append(" -> ").Append(ok ? 1 : 0).Append(' ').Append(where)
                  .Append(" rnd=").Append(UnityEngine.Random.value.ToString("F6", inv)).Append('\n');
            }
            k++;
        }
        bird.transform.position = keep;
        bird.RestoreNear(nearWas);
        b++;
    }
}
finally
{
    Cozy.Grid.Weather.Rain = rainWas;
    int i = 0;
    foreach (var p in Cozy.Grid.CrowPerch.All) { if (p != null && i < perchWas.Count && !perchWas[i]) p.SetOn(false); i++; }
}
System.IO.File.WriteAllText("/tmp/crow_pick.txt", sb.ToString());
return "мест " + sb.ToString().Split('\n').Length;
