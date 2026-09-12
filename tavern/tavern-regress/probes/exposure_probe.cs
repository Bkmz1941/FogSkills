// Проба статусов среды (EFFECTS.md): печатает InFire/Burning/Wet, Chill, HP,
// скорость урона и значки. Игрока в зону ставят заранее (центр клетки = origin + cell·cs;
// клетки — FireView.Occupied), дождь — setup из rain_house_probe, туман — клетка FogView.Occupied.
// После — вернуть позицию и здоровье (SetHealth(maxHealth)): ожог жжёт по-настоящему.
// amount — доля эффекта тумана (BlindAmount): сразу после входа/выхода она между 0 и 1,
// поэтому sight и veil в этот момент промежуточные. Мерить установившееся значение —
// после FogFadeIn/FogFadeOut секунд, либо поставить их в 0 для мгновенного переключения.
var stats = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
var list = new System.Collections.Generic.List<Cozy.Character.PlayerEffect>();
Cozy.Character.PlayerEffects.Collect(stats, list);
var titles = new System.Text.StringBuilder(); foreach (var e in list) titles.Append(e.Title + "(" + e.Icon + ") ");
return "pos=" + Cozy.Grid.PlayerRef.GameObject.transform.position.ToString("0.0") + " inFire=" + Cozy.Effects.PlayerExposure.InFire + " burning=" + Cozy.Effects.PlayerExposure.Burning + " wet=" + Cozy.Effects.PlayerExposure.Wet + " blind=" + Cozy.Effects.PlayerExposure.Blind + " amount=" + Cozy.Effects.PlayerExposure.BlindAmount.ToString("0.00") + " dark=" + Cozy.Effects.PlayerExposure.Dark + " darkAmount=" + Cozy.Effects.PlayerExposure.DarkAmount.ToString("0.00") + " lightNear=" + Cozy.Effects.PlayerExposure.LightNear + " | sight=" + Cozy.Character.VisionArea.Radius.ToString("0.0") + " veil=" + Cozy.Character.DarknessVeil.ForcedDarkness.ToString("0.00") + " | chill=" + Cozy.Character.BodyTemperature.Chill + " hp=" + stats.Health.ToString("0.0") + " drain/s=" + Cozy.Character.PlayerEffects.HealthDrainPerSecond(stats).ToString("0.00") + " | effects: " + titles;
