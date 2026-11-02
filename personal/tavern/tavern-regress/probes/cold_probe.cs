// Проба холода и простуды (EFFECTS.md «Замерзание и простуда», инв. 607, 608).
// step 0 — только читает: улица/крыша, ощущаемую, утепление, порог, тело, степень «Замёрз»,
//   простуду с часами, хуки бега/ходьбы/энергии, значки ряда, шум игрока, пар изо рта (CD-P: air/strength/active/period).
// step 1 — включает принудительно «Замёрз 2» и «Простуда 2» (BodyTemperature.ForceCold, PlayerExposure.ForceIll)
//   и ждёт кадра: прогнать шаг 0 следом — ждём RunAllowed=false (ColdRun2 выкл), WalkPace<1, в ряду
//   «Сильно замёрз» и «Сильная простуда», реплика/чих по таймерам.
// step 2 — снимает принудительное и лечит (CureIll), возвращает ForceColdStage/ForceIllStage = 1.
// Погоду и уровень не трогает; после шага 1 ОБЯЗАТЕЛЕН шаг 2.
int step = 0;
var sb = new System.Text.StringBuilder();
if (step == 1)
{
    Cozy.Character.BodyTemperature.ForceColdStage = 2;
    Cozy.Character.BodyTemperature.ForceCold = true;
    Cozy.Effects.PlayerExposure.ForceIllStage = 2;
    Cozy.Effects.PlayerExposure.ForceIll = true;
    return "forced: cold 2 + ill 2; прогнать шаг 0 через кадр, потом шаг 2";
}
if (step == 2)
{
    Cozy.Character.BodyTemperature.ForceCold = false;
    Cozy.Character.BodyTemperature.ForceColdStage = 1;
    Cozy.Effects.PlayerExposure.ForceIll = false;
    Cozy.Effects.PlayerExposure.ForceIllStage = 1;
    Cozy.Effects.PlayerExposure.CureIll();
    return "released";
}
var stats = Cozy.Grid.PlayerRef.GameObject.GetComponent<Cozy.Character.CharacterStats>();
var list = new System.Collections.Generic.List<Cozy.Character.PlayerEffect>();
Cozy.Character.PlayerEffects.Collect(stats, list);
var titles = new System.Text.StringBuilder(); foreach (var e in list) titles.Append(e.Title + "(" + e.Icon + ") ");
sb.Append("weather T=" + Cozy.Grid.Weather.Temperature.ToString("0.0") + "→" + Cozy.Grid.Weather.TemperatureTarget.ToString("0.0") + " rain=" + Cozy.Grid.Weather.Rain + "/" + Cozy.Grid.Weather.RainForce + " wind=" + Cozy.Grid.Weather.Wind + "/" + Cozy.Grid.Weather.Force + " hour=" + Cozy.Grid.Weather.Hour.ToString("0.00"));
sb.Append(" | body=" + Cozy.Character.BodyTemperature.Current.ToString("0.00") + " feels=" + Cozy.Character.BodyTemperature.Feels.ToString("0.0") + " outdoors=" + Cozy.Character.BodyTemperature.Outdoors + " warmth=" + Cozy.Character.BodyTemperature.Warmth + " comfort=" + Cozy.Character.BodyTemperature.ComfortLow + " wet=" + Cozy.Character.BodyTemperature.Wet + " coldStage=" + Cozy.Character.BodyTemperature.ColdStage + " force=" + Cozy.Character.BodyTemperature.ForceCold);
sb.Append(" | ill=" + Cozy.Effects.PlayerExposure.Ill + " stage=" + Cozy.Effects.PlayerExposure.IllStage + " chillH=" + Cozy.Effects.PlayerExposure.ChillHours.ToString("0.00") + " worseH=" + Cozy.Effects.PlayerExposure.WorseHours.ToString("0.00") + " cureH=" + Cozy.Effects.PlayerExposure.CureHours.ToString("0.00") + " treating=" + Cozy.Effects.PlayerExposure.Treating + " suppressed=" + Cozy.Effects.PlayerExposure.Suppressed + " lastSymptom=" + Cozy.Effects.PlayerExposure.LastSymptom);
sb.Append(" | runAllowed=" + Cozy.Character.PlayerEffects.RunAllowed() + " walkPace=" + Cozy.Character.PlayerEffects.WalkPace().ToString("0.00") + " energyCost=" + Cozy.Character.PlayerEffects.EnergyCost().ToString("0.00") + " regenFactor=" + Cozy.Character.PlayerEffects.EnergyRegenFactor(stats).ToString("0.00") + " drain/s=" + Cozy.Character.PlayerEffects.HealthDrainPerSecond(stats).ToString("0.000") + " underRain=" + Cozy.Effects.PlayerExposure.UnderRain);
sb.Append(" | breath: air=" + Cozy.Character.BodyTemperature.Air.ToString("0.0") + " strength=" + Cozy.Effects.BreathSteam.Strength.ToString("0.00") + " active=" + Cozy.Effects.BreathSteam.Active + " period=" + Cozy.Effects.BreathSteam.Period.ToString("0.0") + " on=" + Cozy.Effects.BreathSteam.On);
sb.Append(" | noise=" + Cozy.Creatures.Noise.Player + " | effects: " + titles);
return sb.ToString();
