// Проба статусов среды (EFFECTS.md): печатает InFire/Burning/Wet, Chill, HP,
// скорость урона и значки. Игрока в зону ставят заранее (центр клетки = origin + cell·cs;
// клетки — FireView.Occupied), дождь — setup из rain_house_probe. Туман на игрока не действует с 10.09.
// После — вернуть позицию и здоровье (SetHealth(maxHealth)): ожог жжёт по-настоящему.
var stats = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
var list = new System.Collections.Generic.List<Cozy.Character.PlayerEffect>();
Cozy.Character.PlayerEffects.Collect(stats, list);
var titles = new System.Text.StringBuilder(); foreach (var e in list) titles.Append(e.Title + "(" + e.Icon + ") ");
return "pos=" + Cozy.Grid.PlayerRef.GameObject.transform.position.ToString("0.0") + " inFire=" + Cozy.Effects.PlayerExposure.InFire + " burning=" + Cozy.Effects.PlayerExposure.Burning + " wet=" + Cozy.Effects.PlayerExposure.Wet + " | chill=" + Cozy.Character.BodyTemperature.Chill + " hp=" + stats.Health.ToString("0.0") + " drain/s=" + Cozy.Character.PlayerEffects.HealthDrainPerSecond(stats).ToString("0.00") + " | effects: " + titles;
