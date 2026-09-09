// Проба статусов среды (EFFECTS.md): печатает InFire/Burning/Wet/Blind, обзор, Chill, HP,
// скорость урона и значки. Игрока в зону ставят заранее (центр клетки = origin + cell·cs;
// клетки — FireView.Occupied / FogView.Occupied), дождь — setup из rain_house_probe.
// После — вернуть позицию и здоровье (SetHealth(maxHealth)): ожог жжёт по-настоящему.
var stats = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
var list = new System.Collections.Generic.List<Cozy.Character.PlayerEffect>();
Cozy.Character.PlayerEffects.Collect(stats, list);
var titles = new System.Text.StringBuilder(); foreach (var e in list) titles.Append(e.Title + "(" + e.Icon + ") ");
return "pos=" + Cozy.Grid.PlayerRef.GameObject.transform.position.ToString("0.0") + " inFire=" + Cozy.Character.PlayerExposure.InFire + " burning=" + Cozy.Character.PlayerExposure.Burning + " wet=" + Cozy.Character.PlayerExposure.Wet + " blind=" + Cozy.Character.PlayerExposure.Blind + " | vision=" + Cozy.Character.VisionArea.Radius.ToString("0.0") + " chill=" + Cozy.Character.BodyTemperature.Chill + " hp=" + stats.Health.ToString("0.0") + " drain/s=" + Cozy.Character.PlayerEffects.HealthDrainPerSecond(stats).ToString("0.00") + " | effects: " + titles;
