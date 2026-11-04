// Общение с персонажами (TALK.md, скил tavern-talk): ответы по фазам, «!» после ответа, предел роста за день,
// просьба текстом, передача, имя «как назвался», тема, дописки только к утверждению, запас, крик, реплики #id.
// Любой уровень: свой Валера ставится в 2 м от героя и удаляется; память настоящего Валеры уровня сохраняется и
// возвращается. Модель выключена, паузы ответа нулевые, разговор ведётся синхронно через Talk.Update().
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0;
System.Action<bool, string> Check = (ok, line) => { if (!ok) fails++; sb.Append(ok ? "OK " : "FAIL ").Append(line).Append('\n'); };
var pm = UnityEngine.Object.FindFirstObjectByType<Cozy.Character.PlayerMovement>();
if (pm == null) return "нет героя";
var T = typeof(Cozy.Life.Talk);
var file = UnityEngine.JsonUtility.FromJson<Cozy.Life.Talk.DialogFile>(UnityEngine.Resources.Load<UnityEngine.TextAsset>("Dialogs/valera").text);
System.Func<string, int, string> Expect = (q, ph) =>
{
    foreach (var p in file.pairs)
        if (p.player.ru.Split('/')[0].Trim() == q && ph >= p.from && ph <= p.to) return p.reply.Get();
    return null;
};
Cozy.Grid.LevelIO.TalkMemoryData keep = null;
bool hadKeep = Cozy.Grid.LevelIO.TalkMemory.TryGetValue("valera", out keep);
string keepJson = hadKeep && keep != null ? UnityEngine.JsonUtility.ToJson(keep) : null;
bool useModel = Cozy.Life.Talk.UseModel;
float rMin = Cozy.Life.Talk.ReplyMin, rMax = Cozy.Life.Talk.ReplyMax, danger = Cozy.Life.Talk.DangerRadius, offer = Cozy.Life.Talk.OfferChance, topic = Cozy.Life.Talk.TopicChance;
int offerAfter = Cozy.Life.Talk.OfferAfterLines, topicAfter = Cozy.Life.Talk.TopicAfterLines;
Cozy.Grid.InteractiveObject io = null;
System.Func<string> Last = () => Cozy.Life.Talk.Lines.Count > 0 ? Cozy.Life.Talk.Lines[Cozy.Life.Talk.Lines.Count - 1].Text : "";
System.Func<string, string> Say = text => { Cozy.Life.Talk.Ask(text); Cozy.Life.Talk.Update(); return Last(); };
try
{
    if (Cozy.Life.Talk.Active) Cozy.Life.Talk.End();
    Cozy.Life.Talk.UseModel = false;
    Cozy.Life.Talk.ReplyMin = Cozy.Life.Talk.ReplyMax = 0f;
    Cozy.Life.Talk.DangerRadius = 0f;
    Cozy.Life.Talk.OfferChance = 0f;
    Cozy.Life.Talk.TopicChance = 0f;
    Cozy.Life.Talk.OfferAfterLines = 0;
    Cozy.Life.Talk.TopicAfterLines = 0;
    Cozy.Grid.LevelIO.TalkMemory.Remove("valera");
    var def = Cozy.Grid.FurnitureCatalog.ById(Cozy.Grid.FurnitureCatalog.ValeraId);
    io = Cozy.Grid.GridCursor.I.SpawnWorldObject(def, pm.transform.position + pm.transform.forward * 2f, 0f);
    io.Slug = "valera_97";
    var m = Cozy.Life.Talk.MemoryOf("valera_97");
    Check(m.score == 0 && m.phase == Cozy.Life.Talk.PhaseStart, "TK-S03 старт: счёт 0, фаза Знакомство (" + m.score + ", " + m.phase + ")");
    Check(Cozy.Life.Talk.IsPeaceful(io), "TK-U01 Валера мирный");
    Check(Cozy.Creatures.CreatureHealth.TitleOf(io) == "Незнакомец", "TK-N02 до знакомства — «Незнакомец» («" + Cozy.Creatures.CreatureHealth.TitleOf(io) + "»)");

    Cozy.Life.Talk.Start(io);
    Cozy.Life.Talk.Update();
    Check(Cozy.Life.Talk.Active && Last() == file.greeting.Get(), "TK-A00 приветствие «" + Last() + "»");
    Check(m.meetings == 1, "TK-M05 встреча №1 (" + m.meetings + ")");

    string got = Say("привет");
    Check(got == Expect("привет", 1), "TK-A01 «привет» в Знакомстве: «" + got + "»");
    Cozy.Life.Talk.SetScore("valera", 12, "проба");
    Check(m.phase == 3, "TK-S02 счёт 12 при шкале 24 — Доверие (" + m.phase + ")");
    got = Say("привет");
    Check(got == Expect("привет", 3), "TK-A02 «привет» в Доверии: «" + got + "»");
    Cozy.Life.Talk.SetScore("valera", -10, "проба");
    got = Say("где лодки?");
    Check(m.phase == 0 && got == Expect("где лодки?", 0), "TK-A03 Неприязнь «где лодки?»: «" + got + "»");
    got = Say("Кто вы?");
    Check(got == Expect("вы кто?", 0), "TK-A05 «Кто вы?» = вариант «вы кто?»: «" + got + "»");

    Cozy.Life.Talk.SetScore("valera", 0, "проба");
    int before = m.score;
    got = Say("Где лодки!");
    Check(got == Expect("где лодки?", 1), "TK-L01 ответ в ПРЕЖНЕЙ фазе: «" + got + "»");
    Check(m.score == before - 2 && m.phases[m.phases.Count - 1].why.Contains("голос"), "TK-L01 «!» → −2 «голос» (" + before + " → " + m.score + ")");
    int afterFirst = m.score;
    Say("Ну где лодки!");
    Check(m.score == afterFirst, "TK-L02 второй «!» за разговор не штрафует (" + m.score + ")");

    m.gained = 0; m.gainDay = Cozy.Grid.FoodSpoil.Today;
    Cozy.Life.Talk.SetScore("valera", 0, "проба");
    Cozy.Life.Talk.AddScore("valera", 4, "проба +4");
    Cozy.Life.Talk.AddScore("valera", 4, "проба +4");
    Check(m.score == 6 && m.phases[m.phases.Count - 1].why.Contains("2 из 4"), "TK-S04 предел дня +6: 4 + 2 (" + m.score + ", «" + m.phases[m.phases.Count - 1].why + "»)");
    Cozy.Life.Talk.AddScore("valera", -8, "проба −8");
    Check(m.score == -2, "TK-S05 минус без предела (" + m.score + ")");
    Cozy.Life.Talk.SetScore("valera", 99, "проба");
    Check(m.score == 24, "TK-S07 край шкалы +24 (" + m.score + ")");

    Cozy.Life.Talk.SetScore("valera", 0, "проба");
    Cozy.Life.Talk.OfferChance = 1f;
    got = Say("как вас зовут?");
    Check(Cozy.Life.Talk.Offer == null, "TK-A13 после ответа-вопроса просьбы нет: «" + got + "»");
    Check(Cozy.Creatures.CreatureHealth.TitleOf(io) == "Валерий" && m.knownName == "Валерий", "TK-N03 назвался — карточка «" + Cozy.Creatures.CreatureHealth.TitleOf(io) + "»");
    got = Say("где лодки?");
    Check(Cozy.Life.Talk.Offer != null && got.StartsWith(Expect("где лодки?", 1)), "TK-R01 просьба дописана к утверждению: «" + got + "»");
    var asked = Cozy.Life.Talk.Offer;
    Cozy.Life.Talk.OfferChance = 0f;
    got = Say("Да, принесу");
    Check(Cozy.Life.Talk.Offer == null && asked != null && m.active.Contains(asked.id) && got == "Договорились.", "TK-R02 «Да, принесу» → обещано «" + (asked != null ? asked.id : "-") + "», ответ «" + got + "»");

    Cozy.Life.Talk.Assign("valera", "water");
    int s0 = m.score;
    bool taken = Cozy.Life.Talk.Give(io, "banana", "Банан");
    Cozy.Life.Talk.Update();
    Check(!taken && file.refuse.Length > 0 && System.Array.Exists(file.refuse, r => r.Get() == Last()), "TK-R08 не нужное — отказ, вещь осталась: «" + Last() + "»");
    m.gained = 0;
    taken = Cozy.Life.Talk.Give(io, "water_bottle", "Бутылка с водой");
    Cozy.Life.Talk.Update();
    Check(taken && m.done.Contains("water") && m.score > s0, "TK-R07 вода по обещанию: взял, +" + (m.score - s0) + ", «" + Last() + "»");
    Check(Cozy.Life.Talk.RequestFor("valera", "mushroom_toadstool") == null, "TK-R10 поганка не еда");

    Cozy.Life.Talk.TopicChance = 1f;
    got = Say("абракадабра");
    Check(Cozy.Life.Talk.Topic == null && System.Array.Exists(file.pool, p => p.Get() == got), "TK-A10 запас без дописок: «" + got + "»");
    got = Say("до скольки работаете?");
    var t = Cozy.Life.Talk.Topic;
    Check(t != null, "TK-T01 тема заведена: «" + got + "»");
    Cozy.Life.Talk.TopicChance = 0f;
    m.gained = 0;
    int s1 = m.score;
    Say("Люблю, на опарыша ловлю");
    Check(t != null && m.topics.Exists(k => k.StartsWith(t.id + "@")) && m.score == s1 + t.points, "TK-T02 ответ по теме +" + (m.score - s1));

    int logBefore = m.log.Count;
    Cozy.Life.Talk.Shout(io, "#till_away", 4f);
    string shout = m.log.Count > logBefore ? m.log[m.log.Count - 1].text : "";
    var till = System.Array.Find(file.lines, l => l.id == "till_away");
    string want = till != null && m.phase < till.byPhase.Length ? till.byPhase[m.phase].Get() : "";
    Check(shout.Contains(want) && shout.Contains("[кричит герою]"), "TK-P18/P19 крик #till_away по фазе: «" + shout + "»");
    Check(Cozy.Life.Talk.LineFor(io, "«Уйди!» | «Go away!»") == (Cozy.Loc.Language == Cozy.Loc.En ? "Go away!" : "Уйди!"), "TK-P17 «ру» | «en» по языку");
    Check(m.log.Count > 0 && m.log[0].day > 0 && m.log[0].at.Length > 0, "TK-M01 журнал с днём и временем (" + m.log.Count + " строк)");

    Cozy.Life.Talk.End();
    Check(!Cozy.Life.Talk.Active, "TK-U06 разговор окончен");
    Cozy.Life.Talk.Forget("valera");
    Check(m.score == 0 && m.log.Count == 0 && !m.knowsName && m.done.Count == 0, "TK-M08 «Стереть» — всё с нуля");
}
catch (System.Exception e) { fails++; sb.Append("FAIL исключение ").Append(e.GetType().Name).Append(": ").Append(e.Message).Append('\n'); }
finally
{
    if (Cozy.Life.Talk.Active) Cozy.Life.Talk.End();
    if (io != null) UnityEngine.Object.Destroy(io.gameObject);
    Cozy.Grid.LevelIO.TalkMemory.Remove("valera");
    if (keepJson != null) Cozy.Grid.LevelIO.TalkMemory["valera"] = UnityEngine.JsonUtility.FromJson<Cozy.Grid.LevelIO.TalkMemoryData>(keepJson);
    Cozy.Life.Talk.UseModel = useModel;
    Cozy.Life.Talk.ReplyMin = rMin; Cozy.Life.Talk.ReplyMax = rMax; Cozy.Life.Talk.DangerRadius = danger;
    Cozy.Life.Talk.OfferChance = offer; Cozy.Life.Talk.TopicChance = topic;
    Cozy.Life.Talk.OfferAfterLines = offerAfter; Cozy.Life.Talk.TopicAfterLines = topicAfter;
}
return (fails == 0 ? "ОК " : "КРАСНОЕ ") + fails + " провалов\n" + sb;
