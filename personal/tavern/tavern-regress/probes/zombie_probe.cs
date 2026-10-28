// Зомби (ZOMBIE.md, коды ZB-…): клипы в Resources, фигура, проигрывание клипов (ZombieAnimation), цепочка
// «перелезает в окно → встаёт с живота» — таз на стыках без скачков. Любой уровень (стенд — «Зомби (тест)»,
// zombie_test); свой зомби ставится далеко и удаляется, Zombie.Clip возвращается как был.
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0, skips = 0;
System.Action<bool, string> Check = (ok, line) => { if (!ok) fails++; sb.Append(ok ? "OK " : "FAIL ").Append(line).Append('\n'); };
System.Action<string> Skip = line => { skips++; sb.Append("SKIP ").Append(line).Append('\n'); };
var NP = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var ZA = typeof(Cozy.Creatures.ZombieAnimation);
var wasClip = Cozy.Creatures.Zombie.Clip;
UnityEngine.GameObject made = null;
try
{
    // ---------- ZB-C: клипы ----------
    var clips = new (string name, bool loop)[] {
        ("Zombie_Idle", true), ("Zombie_Walk", true), ("Zombie_Notice", false), ("Zombie_Chase", true),
        ("Zombie_DoorBang", true), ("Zombie_WindowBang", true), ("Zombie_WindowClimb", false), ("Prone_Up", false) };
    foreach (var c in clips)
    {
        var a = UnityEngine.Resources.Load<UnityEngine.AnimationClip>(c.name);
        Check(a != null && a.humanMotion && a.isLooping == c.loop && a.length > 0.5f,
            "ZB-C01 " + c.name + ": " + (a == null ? "НЕТ" : a.length.ToString("0.00") + " с, луп=" + a.isLooping + " (ждём " + c.loop + "), humanoid=" + a.humanMotion));
    }
    var idle = UnityEngine.Resources.Load<UnityEngine.AnimationClip>("Zombie_Idle");
    foreach (var n in new[] { "Zombie_DoorBang", "Zombie_WindowBang" })
    {
        var a = UnityEngine.Resources.Load<UnityEngine.AnimationClip>(n);
        if (a != null && idle != null)
            Check(UnityEngine.Mathf.Abs(a.length - idle.length) < 0.05f, "ZB-C02 " + n + ": длина = цикл стойки (" + a.length.ToString("0.00") + " / " + idle.length.ToString("0.00") + " с) — шов лупа без рывка");
    }
    // ---------- ZB-E: стычка ----------
    Check(Cozy.Combat.ZombieEncounter.Data != null, "ZB-E01 данные стычки зомби (" + Cozy.Combat.ZombieEncounter.Resource + ") грузятся");
    // ---------- ZB-M: фигура ----------
    var spawn = typeof(Cozy.Grid.GridCursor).GetMethod("SpawnObject", NP);
    var def = Cozy.Grid.FurnitureCatalog.ById("zombie");
    Check(def != null, "ZB-M01 деф zombie есть в каталоге");
    if (def == null) return "КРАСНОЕ: нет дефа zombie\n" + sb;
    var io = (Cozy.Grid.InteractiveObject)spawn.Invoke(Cozy.Grid.GridCursor.I, new object[] { def, new UnityEngine.Vector3(600f, 0f, 600f), 0f });
    made = io.gameObject;
    var anim = made.GetComponentInChildren<Cozy.Creatures.ZombieAnimation>();
    var an = made.GetComponentInChildren<UnityEngine.Animator>();
    Check(anim != null && an != null && an.isHuman, "ZB-M02 фигура: ZombieAnimation и аниматор-гуманоид");
    var eq = made.GetComponentInChildren<Cozy.Character.Equipment>();
    Check(eq != null, "ZB-M03 одежда: Equipment на фигуре");
    if (anim == null || an == null) return "КРАСНОЕ\n" + sb;
    an.cullingMode = UnityEngine.AnimatorCullingMode.AlwaysAnimate;   // вне кадра аниматор иначе стоит
    var update = ZA.GetMethod("Update", NP);
    var fGraph = ZA.GetField("_graph", NP);
    var fPlaying = ZA.GetField("_playing", NP);
    System.Func<bool> GraphOn = () => ((UnityEngine.Playables.PlayableGraph)fGraph.GetValue(anim)).IsValid();
    // ---------- ZB-P: проигрывание ----------
    foreach (var c in new[] { Cozy.Creatures.ZombieClip.DoorBang, Cozy.Creatures.ZombieClip.WindowBang })
    {
        Cozy.Creatures.Zombie.Clip = c;
        update.Invoke(anim, null);
        Check(GraphOn() && (Cozy.Creatures.ZombieClip)fPlaying.GetValue(anim) == c, "ZB-P01 " + c + ": играет свой клип поверх аниматора");
    }
    Cozy.Creatures.Zombie.Clip = Cozy.Creatures.ZombieClip.Stand;
    update.Invoke(anim, null);
    Check(!GraphOn(), "ZB-P02 смена на «стоит» снимает клип «ломится»");
    Cozy.Creatures.Zombie.Notice();
    update.Invoke(anim, null);
    Check(GraphOn() && (Cozy.Creatures.ZombieClip)fPlaying.GetValue(anim) == Cozy.Creatures.ZombieClip.Notice, "ZB-P03 «увидел» играет один раз своим клипом");
    // ---------- ZB-W: перелезает → встаёт (время подставляется полями фаз) ----------
    var hips = an.GetBoneTransform(UnityEngine.HumanBodyBones.Hips);
    var fPhase = ZA.GetField("_phase", NP);
    var fEnd = ZA.GetField("_phaseEnd", NP);
    var fBlend = ZA.GetField("_blendStart", NP);
    var fMix = ZA.GetField("_mix", NP);
    var fUp = ZA.GetField("_upPlay", NP);
    var tick = ZA.GetMethod("TickClimb", NP);
    var home = an.transform.position;
    Cozy.Creatures.Zombie.WindowClimb();
    update.Invoke(anim, null);
    Check(fPhase.GetValue(anim).ToString() == "Climb", "ZB-W01 «перелезает» начинается фазой Climb");
    var graph = (UnityEngine.Playables.PlayableGraph)fGraph.GetValue(anim);
    var mix = (UnityEngine.Animations.AnimationMixerPlayable)fMix.GetValue(anim);
    var climbPlay = UnityEngine.Playables.PlayableExtensions.GetInput(mix, 0);
    var climbLen = UnityEngine.Resources.Load<UnityEngine.AnimationClip>("Zombie_WindowClimb").length;
    UnityEngine.Playables.PlayableExtensions.SetTime(climbPlay, 0.0);
    graph.Evaluate(0f);
    var start = hips.position;
    UnityEngine.Playables.PlayableExtensions.SetTime(climbPlay, (double)climbLen);
    graph.Evaluate(0f);
    var climbEnd = hips.position;
    var moved = new UnityEngine.Vector3(climbEnd.x - start.x, 0f, climbEnd.z - start.z).magnitude;
    Check(moved > 1.5f && moved < 3.0f, "ZB-W02 за перелезание таз уходит в комнату на " + moved.ToString("0.00") + " м (смещение запечено в позу)");
    Check(climbEnd.y < start.y * 0.6f, "ZB-W03 в конце перелезания — поза отжимания: таз " + climbEnd.y.ToString("0.00") + " м (стоя " + start.y.ToString("0.00") + ")");
    fEnd.SetValue(anim, UnityEngine.Time.time - 1f);
    tick.Invoke(anim, null);
    Check(fPhase.GetValue(anim).ToString() == "Blend", "ZB-W04 конец перелезания → смешивание с Prone_Up");
    float maxJump = 0f;
    foreach (var share in new[] { 0.0f, 0.25f, 0.5f, 0.75f, 1.01f })
    {
        fBlend.SetValue(anim, UnityEngine.Time.time - Cozy.Creatures.Zombie.ProneUpBlend * share);
        tick.Invoke(anim, null);
        graph.Evaluate(0f);
        var d = hips.position - climbEnd;
        d.y = 0f;
        maxJump = UnityEngine.Mathf.Max(maxJump, d.magnitude);
    }
    Check(maxJump < 0.15f, "ZB-W05 смешивание: таз по полу уходит от конца перелезания не больше " + (maxJump * 100f).ToString("0.0") + " см (порог 15)");
    Check(fPhase.GetValue(anim).ToString() == "Up", "ZB-W06 после смешивания — фаза Up (встаёт)");
    var up = (UnityEngine.Animations.AnimationClipPlayable)fUp.GetValue(anim);
    UnityEngine.Playables.PlayableExtensions.SetTime(up, (double)up.GetAnimationClip().length);
    graph.Evaluate(0f);
    var stoodAt = hips.position;
    fEnd.SetValue(anim, UnityEngine.Time.time - 1f);
    tick.Invoke(anim, null);
    an.Update(0f);
    var standAt = hips.position;
    var dz = new UnityEngine.Vector3(standAt.x - stoodAt.x, 0f, standAt.z - stoodAt.z).magnitude;
    Check(fPhase.GetValue(anim).ToString() == "None" && Cozy.Creatures.Zombie.Clip == Cozy.Creatures.ZombieClip.Stand && !GraphOn(),
        "ZB-W07 встал — обычная стойка аниматора, клип снят");
    Check(dz < 0.05f, "ZB-W08 стойка на том же месте, где встал: по полу " + (dz * 100f).ToString("0.0") + " см");
    Check(UnityEngine.Mathf.Abs(standAt.y - stoodAt.y) < 0.15f, "ZB-W09 переход в стойку по высоте " + ((standAt.y - stoodAt.y) * 100f).ToString("0.0") + " см (порог 15)");
    Cozy.Creatures.Zombie.WindowClimb();
    update.Invoke(anim, null);
    var again = (an.transform.position - home).magnitude;
    Check(again < 0.01f, "ZB-W10 повтор перелезания начинается с того же места у окна (" + (again * 100f).ToString("0.0") + " см)");
}
finally
{
    Cozy.Creatures.Zombie.Clip = wasClip;
    if (made != null) UnityEngine.Object.DestroyImmediate(made);
}
int total = 0;
foreach (var l in sb.ToString().Split('\n')) if (l.StartsWith("OK ") || l.StartsWith("FAIL ")) total++;
return (fails == 0 ? "ЗЕЛЁНОЕ из " + total : "КРАСНОЕ: " + fails + " из " + total) + (skips > 0 ? ", пропущено " + skips : "") + " (свой зомби создан и удалён)\n" + sb;
