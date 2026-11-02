// Закрытые комнаты (ROOMS.md, коды RM-…): флаг HiddenRooms, скан комнат (топология, закрытость по
// независимому обходу рёбер), правило недоступности по AccessCells, крестики, крышки не выше этажа обзора
// (Илья 22.10: «чернота этажей выше никогда не рисуется»; «если я на 2 этаже — темнота с закрытых комнат
// не должна исчезать, если потолка нет — сверху смотрю»; 28.10: «я поднялся на крышу и по идее должен
// видеть всё что внутри 1 этажа сверху, но вижу чёрное»), закрытая комната = внутри здания.
// Любой уровень (стенд — «Комнаты (тест)», rooms_test); флаг, список комнат, маркеры и этаж возвращаются как были.
if (!UnityEngine.Application.isPlaying) return "не в play";
var sb = new System.Text.StringBuilder();
int fails = 0, skips = 0, checks = 0;
System.Action<bool, string> Check = (ok, line) => { checks++; if (!ok) fails++; sb.Append(ok ? "OK " : "FAIL ").Append(line).Append('\n'); };
System.Action<string> Skip = line => { skips++; sb.Append("SKIP ").Append(line).Append('\n'); };
var NPI = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var NPS = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var HR = typeof(Cozy.Grid.HiddenRooms);
var hr = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.HiddenRooms>(UnityEngine.FindObjectsInactive.Include);
if (hr == null) return "КРАСНОЕ: HiddenRooms не поднят в сцене (SceneSingleton)";
var mLate = HR.GetMethod("LateUpdate", NPI);
var mScan = HR.GetMethod("Scan", NPI);
var mSync = HR.GetMethod("SyncMarks", NPI);
var mBuild = HR.GetMethod("BuildLids", NPI);
var mReach = HR.GetMethod("Reachable", NPS);
var mReachKind = HR.GetMethod("Reach", NPS);
var mOnFloor = HR.GetMethod("OnFloor", NPS);
var mAbove = HR.GetMethod("AboveFloor", NPS);
var mUnder = HR.GetMethod("UnderDollhouse", NPS);
var mInterior = HR.GetMethod("Interior", NPS);
var mSolid = HR.GetMethod("Solid", NPS);
var fMarks = HR.GetField("_marks", NPI);
var fLids = HR.GetField("_lids", NPS);
var fScanned = HR.GetField("_scanned", NPI);
if (mLate == null || mScan == null || mSync == null || mBuild == null || mReach == null || mOnFloor == null || mAbove == null || mUnder == null || mInterior == null || mSolid == null || fMarks == null || fLids == null || fScanned == null)
    return "ЗАЩИТА МЕРТВА: в HiddenRooms нет LateUpdate/Scan/SyncMarks/BuildLids/Reachable/OnFloor/AboveFloor/UnderDollhouse/Interior/Solid/_marks/_lids/_scanned";
bool wasOn = Cozy.View.ViewState.HiddenRooms;
System.Func<int> ActiveMarks = () => { int n = 0; foreach (var go in (System.Collections.Generic.List<UnityEngine.GameObject>)fMarks.GetValue(hr)) if (go != null && go.activeSelf) n++; return n; };
System.Func<int, UnityEngine.GameObject> LidGo = i => { var l = (System.Collections.IList)fLids.GetValue(hr); if (i >= l.Count) return null; return (UnityEngine.GameObject)l[i].GetType().GetField("Go").GetValue(l[i]); };
System.Func<int, float> LidFade = i => { var l = (System.Collections.IList)fLids.GetValue(hr); if (i >= l.Count) return -1f; return (float)l[i].GetType().GetField("Fade").GetValue(l[i]); };
System.Func<Cozy.Grid.HiddenRooms.Room, float, bool> OnFloor = (r, f) => (bool)mOnFloor.Invoke(null, new object[] { r, f });
System.Func<Cozy.Grid.HiddenRooms.Room, float, bool> Above = (r, f) => (bool)mAbove.Invoke(null, new object[] { r, f });
System.Func<Cozy.Grid.HiddenRooms.Room, bool> Under = r => (bool)mUnder.Invoke(null, new object[] { r });
System.Func<int, bool> Drawn = i => { var lg = LidGo(i); return (lg != null && lg.activeSelf) || LidFade(i) > 0f; };
System.Func<int, bool> Active = i => { var lg = LidGo(i); return lg != null && lg.activeSelf; };
try
{
    var coord = Cozy.Grid.GridManager.GroundOrFloor();
    if (coord == null) return "НЕЧЕГО БЫЛО ПРОВЕРЯТЬ: нет GridManager (уровень не поднят)";
    float cs = coord.CellSize;
    var o = coord.Origin;
    var rooms = Cozy.Grid.HiddenRooms.Rooms;

    // ---------- RM-F: флаг ----------
    Cozy.View.ViewState.HiddenRooms = false;
    mLate.Invoke(hr, null);
    Check(rooms.Count == 0 && ActiveMarks() == 0, "RM-F01 флаг выключен: комнат " + rooms.Count + ", активных маркеров " + ActiveMarks());

    // ---------- RM-S: скан ----------
    Cozy.View.ViewState.HiddenRooms = true;
    bool scanned = (bool)mScan.Invoke(hr, null);
    Check(scanned, "RM-S01 скан на поднятом уровне → true");
    if (!scanned) return "КРАСНОЕ\n" + sb;
    mBuild.Invoke(hr, null);
    int[] dx = { 1, -1, 0, 0 }, dz = { 0, 0, 1, -1 };
    var taken = new System.Collections.Generic.HashSet<UnityEngine.Vector3Int>();
    int badShape = 0, badCell = 0, leaks = 0, overlaps = 0, noInterior = 0;
    var table = new System.Text.StringBuilder();
    for (int i = 0; i < rooms.Count; i++)
    {
        var r = rooms[i];
        int li = Cozy.Grid.GridManager.LevelIndex(r.Level, cs);
        bool shape = r.Area != null && r.Cells == r.Area.Count && r.Cells > 0 && r.Cells <= 400
            && UnityEngine.Mathf.Abs(Cozy.Grid.GridManager.LevelY(r.Level, cs) - r.Level) < 1e-3f;
        float minX = float.MaxValue, maxX = float.MinValue, minZ = float.MaxValue, maxZ = float.MinValue;
        int interiorCells = 0;
        foreach (var c in r.Area)
        {
            float wx = o.x + c.x * cs, wz = o.z + c.y * cs;
            minX = UnityEngine.Mathf.Min(minX, wx); maxX = UnityEngine.Mathf.Max(maxX, wx);
            minZ = UnityEngine.Mathf.Min(minZ, wz); maxZ = UnityEngine.Mathf.Max(maxZ, wz);
            bool interior = (bool)mInterior.Invoke(null, new object[] { c, r.Level, o, cs });
            bool solid = (bool)mSolid.Invoke(null, new object[] { c, r.Level, o, cs });
            if (interior) interiorCells++;
            if (solid) badCell++;
            if (!taken.Add(new UnityEngine.Vector3Int(c.x, c.y, li))) overlaps++;
            for (int d = 0; d < 4; d++)
            {
                var nb = new UnityEngine.Vector2Int(c.x + dx[d], c.y + dz[d]);
                if (r.Area.Contains(nb)) continue;
                if (Cozy.Grid.ViewSensor.WallBetween(c, nb, o, cs, r.Level)) continue;
                if (Cozy.Grid.ViewSensor.OpeningKindBetween(c, nb, o, cs, r.Level) != 0) continue;
                if ((bool)mSolid.Invoke(null, new object[] { nb, r.Level, o, cs })) continue;
                leaks++;
            }
        }
        shape = shape && r.Center.x >= minX - cs && r.Center.x <= maxX + cs && r.Center.z >= minZ - cs && r.Center.z <= maxZ + cs
            && UnityEngine.Mathf.Abs(r.Center.y - (r.Level + cs * 0.5f)) < 1e-3f
            && UnityEngine.Mathf.Abs(r.Min.x - minX) < 1e-3f && UnityEngine.Mathf.Abs(r.Max.x - maxX) < 1e-3f && UnityEngine.Mathf.Abs(r.Min.y - minZ) < 1e-3f && UnityEngine.Mathf.Abs(r.Max.y - maxZ) < 1e-3f;
        if (!shape) badShape++;
        if (interiorCells == 0) noInterior++;
        bool reach = (bool)mReach.Invoke(null, new object[] { i, Cozy.View.ViewState.CurrentFloorY });
        table.Append("  #" + i + " уровень " + r.Level.ToString("0.#") + " клеток " + r.Cells + " центр " + r.Center.x.ToString("0.#") + "/" + r.Center.z.ToString("0.#") + (reach ? " доступна" : " КРЕСТИК") + "\n");
    }
    Check(badShape == 0, "RM-S02 форма комнат (клетки, уровень, центр, габарит Min/Max, ≤400): плохих " + badShape + " из " + rooms.Count);
    Check(badCell == 0 && noInterior == 0, "RM-S03 клетка комнаты не куб, хотя бы одна клетка интерьер (проём лестницы в полу — тоже клетка комнаты): кубов " + badCell + ", комнат без интерьера " + noInterior);
    Check(leaks == 0, "RM-S04 закрытость независимым обходом рёбер: утечек " + leaks);
    Check(overlaps == 0, "RM-S05 комнаты одного уровня не пересекаются: пересечений " + overlaps);
    if (rooms.Count == 0) Skip("RM-S02…S05 на уровне нет закрытых комнат — правила не проверены (нужен стенд rooms_test)");

    // ---------- RM-S13: стенки лестницы — стена на ребре (01.11) ----------
    int stairN = 0, stairBackWall = 0, stairTopSide = 0, stairTopSideWall = 0, stairFootOpen = 0, stairFootSealed = 0;
    foreach (var st in Cozy.Grid.StairPiece.All)
    {
        if (st == null || st.IsGhost || !st.landing) continue;
        var t = st.transform;
        float lvl = t.position.y;
        var fwd = new UnityEngine.Vector2Int(UnityEngine.Mathf.RoundToInt(t.forward.x), UnityEngine.Mathf.RoundToInt(t.forward.z));
        var lat = new UnityEngine.Vector2Int(fwd.y, -fwd.x);
        var topCell = Cozy.Grid.GridSnap.Cell(t.position + t.forward * st.TopAhead(cs), o, cs);
        var footCell = Cozy.Grid.GridSnap.Cell(t.position + t.forward * st.BaseCellLocal(cs).z, o, cs);
        stairN++;
        if (Cozy.Grid.ViewSensor.WallBetween(topCell, topCell + fwd, o, cs, lvl)) stairBackWall++;
        foreach (var side in new[] { lat, -lat })
        {
            var tn = topCell + side;
            float tx = o.x + (topCell.x + tn.x) * 0.5f * cs, tz = o.z + (topCell.y + tn.y) * 0.5f * cs;
            if (!Cozy.Grid.BuildQuery.WallAtEdge(tx, tz, lvl, cs)) { stairTopSide++; if (Cozy.Grid.BuildQuery.StairWallAtEdge(tx, tz, lvl, cs)) stairTopSideWall++; }
            var fn = footCell + side;
            float fx = o.x + (footCell.x + fn.x) * 0.5f * cs, fz = o.z + (footCell.y + fn.y) * 0.5f * cs;
            if (!Cozy.Grid.BuildQuery.WallAtEdge(fx, fz, lvl, cs)) { stairFootOpen++; if (Cozy.Grid.BuildQuery.StairWallAtEdge(fx, fz, lvl, cs)) stairFootSealed++; }
        }
    }
    if (stairN > 0) Check(stairBackWall == stairN && stairTopSideWall == stairTopSide && stairFootSealed == 0, "RM-S13 торец (BackWall) и боковины (SideWall) лестницы с площадкой — стена на ребре для заливки комнат и линии взгляда, вход у подножия (боковина начинается с середины клетки подножия) открыт (Илья 01.11 по скриншоту 03-40-16: спальня «Котеджа 104» за закрытой дверью сливалась с холлом под верхом лестницы, P1228): лестниц " + stairN + ", торцов-стен " + stairBackWall + ", боковин у площадки стен " + stairTopSideWall + " из " + stairTopSide + ", подножий запечатано " + stairFootSealed);
    else Skip("RM-S13 лестниц с площадкой на уровне нет");

    // ---------- RM-A27/A28: окно и шторы (01.11) ----------
    int winClear = 0, winClearPass = 0, winCurt = 0, winCurtBarrier = 0;
    foreach (var w in Cozy.Grid.WindowPiece.All)
    {
        if (w == null) continue;
        var wp = w.transform.position;
        int kind = Cozy.Grid.BuildQuery.OpeningKindAt(new UnityEngine.Vector3(wp.x, wp.y + cs * 0.5f, wp.z), cs);
        if (w.Curtained) { winCurt++; if (kind == 2) winCurtBarrier++; }
        else { winClear++; if (kind == 1) winClearPass++; }
    }
    if (winClear > 0) Check(winClearPass == winClear, "RM-A27 окно без штор — проход для взгляда (OpeningKindAt = 1): комната за ним в радиусе и на линии взгляда доступна как за открытой дверью (Reach = 2, крышка под крышей остаётся; Илья 01.11: «как открытая дверь»): окон " + winClear + ", проходимых " + winClearPass);
    else Skip("RM-A27 окон без штор на уровне нет");
    if (winCurt > 0) Check(winCurtBarrier == winCurt, "RM-A28 окно с задёрнутыми шторами / опущенными жалюзи (`WindowPiece.Curtained`) — барьер (OpeningKindAt = 2) в обе стороны: комната за ним тёмная, линия взгляда не проходит, «снаружи тусклое» при всех зашторенных окнах (Илья 01.11: «закрытые на жалюзи или шторы окна — не пропускают зону видимости, как внутрь так и вне»): зашторенных " + winCurt + ", барьеров " + winCurtBarrier);
    else Skip("RM-A28 зашторенных окон на уровне нет");

    // ---------- RM-A: недоступность и крестики ----------
    System.Func<int, bool> Roofed = i =>
    {
        foreach (var c in rooms[i].Area) if (Cozy.Grid.BuildQuery.CeilingUnderside(o.x + c.x * cs, o.z + c.y * cs, rooms[i].Level, cs, out _)) return true;
        return false;
    };
    System.Func<int, float, bool> HiddenRule = (i, f) =>
    {
        if (Above(rooms[i], f) && Under(rooms[i])) return false;
        int kind = mReachKind != null ? (int)mReachKind.Invoke(null, new object[] { i, f }) : ((bool)mReach.Invoke(null, new object[] { i, f }) ? 1 : 0);
        return kind == 0 || (kind == 2 && Roofed(i));
    };
    if (mReachKind == null) Check(false, "RM-A24 ЗАЩИТА МЕРТВА: в HiddenRooms нет Reach(i, floor)");
    System.Func<int, float, bool> CeilingDrawn = (i, f) => !(Cozy.View.ViewState.BuildValid && Cozy.View.ViewState.Mode != Cozy.View.ViewMode.ShowAll
        && rooms[i].Level + cs > f + Cozy.View.ViewState.YEps && Under(rooms[i]));
    System.Func<int, float, bool> Topped = (i, f) =>
    {
        int covered = 0, above = 0, shaded = 0, ceil = 0;
        foreach (var c in rooms[i].Area)
        {
            bool cov = false;
            for (int j = 0; j < rooms.Count; j++) if (rooms[j].Level > rooms[i].Level + 0.01f && rooms[j].Area.Contains(c)) { cov = true; break; }
            if (Cozy.Grid.BuildQuery.CeilingUnderside(o.x + c.x * cs, o.z + c.y * cs, rooms[i].Level, cs, out _)) { cov = true; ceil++; }
            if (cov) covered++;
        }
        for (int j = 0; j < rooms.Count; j++)
        {
            if (rooms[j].Level <= rooms[i].Level + 0.01f) continue;
            bool bare = false; foreach (var c in rooms[j].Area) if (rooms[i].Area.Contains(c) && !Cozy.Grid.BuildQuery.CeilingUnderside(o.x + c.x * cs, o.z + c.y * cs, rooms[i].Level, cs, out _)) { bare = true; break; }
            if (!bare) continue;
            above++; if (HiddenRule(j, f)) shaded++;
        }
        bool coverOn = shaded == above && (ceil == 0 || CeilingDrawn(i, f));
        return covered == rooms[i].Area.Count && covered > 0 && coverOn;
    };
    System.Func<int, float, bool> WantLid = (i, f) => Cozy.Grid.HiddenRooms.Lid && HiddenRule(i, f) && !Topped(i, f);
    mSync.Invoke(hr, null);
    float floor = Cozy.View.ViewState.CurrentFloorY;
    int unreachable = 0, doorRoofed = 0, doorRoofedDark = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (HiddenRule(i, floor)) unreachable++;
        if (mReachKind != null && OnFloor(rooms[i], floor) && (int)mReachKind.Invoke(null, new object[] { i, floor }) == 2 && Roofed(i)) { doorRoofed++; if (HiddenRule(i, floor)) doorRoofedDark++; }
    }
    if (doorRoofed > 0) Check(doorRoofedDark == doorRoofed, "RM-A24 комната под крышей (хоть одна клетка с плитой), доступная ТОЛЬКО через открытую дверь в радиусе — остаётся тёмной: дверь не открывает дыру в крыше сверху (Илья 28.10: «почему я стал видеть лестницу?»): таких " + doorRoofed + ", тёмных " + doorRoofedDark);
    int wantMarks = Cozy.Grid.HiddenRooms.Marks ? unreachable : 0;
    Check(ActiveMarks() == wantMarks, "RM-A01 маркеры ⇔ недоступные, кроме спрятанных кукольным домиком (крестики " + (Cozy.Grid.HiddenRooms.Marks ? "вкл" : "выкл") + "): активных " + ActiveMarks() + ", ждём " + wantMarks);
    int activeLids = 0, wantLids = 0, lidMismatch = 0;
    for (int i = 0; i < rooms.Count; i++) { bool a = Active(i), w = WantLid(i, floor); if (a) activeLids++; if (w) wantLids++; if (a != w) lidMismatch++; }
    Check(lidMismatch == 0, "RM-V10 крышки ⇔ недоступные, кроме спрятанных кукольным домиком и накрытых крышкой верхней комнаты (крышка " + (Cozy.Grid.HiddenRooms.Lid ? "вкл" : "выкл") + "): активных " + activeLids + ", ждём " + wantLids + ", расхождений " + lidMismatch);
    int toppedN = 0, toppedOff = 0;
    for (int i = 0; i < rooms.Count; i++) if (HiddenRule(i, floor) && Topped(i, floor)) { toppedN++; if (!Active(i)) toppedOff++; }
    if (toppedN > 0 && Cozy.Grid.HiddenRooms.Lid) Check(toppedOff == toppedN, "RM-A20 комната целиком под нарисованной крышкой верхней комнаты или под нарисованным потолком → своя крышка не рисуется (темнота только на самом верхнем этаже; «если есть потолок — то потолка»): выключено " + toppedOff + " из " + toppedN);
    int slabN = 0, slabOff = 0, slabLitAbove = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (!CeilingDrawn(i, floor)) continue;
        bool all = true; foreach (var c in rooms[i].Area) if (!Cozy.Grid.BuildQuery.CeilingUnderside(o.x + c.x * cs, o.z + c.y * cs, rooms[i].Level, cs, out _)) { all = false; break; }
        if (!all) continue;
        slabN++; if (!Active(i)) slabOff++;
        for (int j = 0; j < rooms.Count; j++) if (rooms[j].Level > rooms[i].Level + 0.01f && !HiddenRule(j, floor)) { foreach (var c in rooms[j].Area) if (rooms[i].Area.Contains(c)) { slabLitAbove++; goto nextSlab; } }
        nextSlab:;
    }
    if (slabN > 0) Check(slabOff == slabN, "RM-A26 комната целиком под НАРИСОВАННОЙ плитой → крышки нет, даже если над ней светлая комната (герой на крыше, стены на крыше дали комнату уровнем выше) — иначе крышка ложится на плиту, чернота на полу у героя (Илья 28.10: «передо мной темнота рисуется почему-то на полу»): без крышки " + slabOff + " из " + slabN + ", из них со светлой комнатой сверху " + slabLitAbove);
    int roofedN = 0, roofedOff = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (!HiddenRule(i, floor)) continue;
        int ceilCells = 0; foreach (var c in rooms[i].Area) if (Cozy.Grid.BuildQuery.CeilingUnderside(o.x + c.x * cs, o.z + c.y * cs, rooms[i].Level, cs, out _)) ceilCells++;
        if (ceilCells != rooms[i].Area.Count || !CeilingDrawn(i, floor)) continue;
        roofedN++; if (!Active(i)) roofedOff++;
    }
    if (roofedN > 0 && Cozy.Grid.HiddenRooms.Lid) Check(roofedOff == roofedN, "RM-A22 комната под целым нарисованным потолком → крышки нет, темнота = потолок (Илья 22.10: «убери её, если потолок рисуем»): выключено " + roofedOff + " из " + roofedN);
    var feet = Cozy.Character.PlayerTarget.Feet;
    var myCell = Cozy.Grid.GridSnap.Cell(feet, o, cs);
    int mine = -1;
    for (int i = 0; i < rooms.Count; i++)
        if (OnFloor(rooms[i], floor) && rooms[i].Area.Contains(myCell)) { mine = i; break; }
    if (!Cozy.View.ViewState.RoomValid || mine < 0) Skip("RM-A02 герой не в закрытой комнате (RoomValid=" + Cozy.View.ViewState.RoomValid + ") — своя комната не проверена");
    else Check((bool)mReach.Invoke(null, new object[] { mine, floor }), "RM-A02 комната героя #" + mine + " без крестика");
    if (!wasOn || mine < 0) Skip("RM-A15 режим " + (wasOn ? "вкл, герой не в закрытой комнате" : "выкл") + " — «закрытая комната = внутри» не проверено");
    else
    {
        var roomCells = Cozy.View.ViewState.RoomCells;
        var accessCells = Cozy.View.ViewState.AccessCells;
        bool box = Cozy.View.ViewState.BuildValid && Cozy.View.ViewState.RoomValid && roomCells.IsSupersetOf(rooms[mine].Area)
            && accessCells.IsSupersetOf(rooms[mine].Area);
        foreach (var c in rooms[mine].Area)
        {
            float wx = o.x + c.x * cs, wz = o.z + c.y * cs;
            if (!Cozy.View.ViewState.InBuilding(wx, wz, 0.01f)) { box = false; break; }
        }
        Check(box, "RM-A15 герой в закрытой комнате → внутри здания и без крыши: BuildValid=" + Cozy.View.ViewState.BuildValid + ", RoomCells " + Cozy.View.ViewState.RoomCells.Count + ", AccessCells " + Cozy.View.ViewState.AccessCells.Count + ", коробка накрывает комнату #" + mine);
    }
    System.Func<Cozy.Grid.HiddenRooms.Room, bool> StairsUp = room =>
    {
        float vr0 = Cozy.View.ViewState.VisionRadius != null ? Cozy.View.ViewState.VisionRadius() : 12f;
        var pp0 = Cozy.View.ViewState.PlayerPos;
        foreach (var st in Cozy.Grid.StairPiece.All)
        {
            if (st == null || st.IsGhost) continue;
            var t = st.transform;
            if (UnityEngine.Mathf.Abs(t.position.y - room.Level) > Cozy.View.ViewState.YEps || UnityEngine.Mathf.Abs(t.position.y + st.riseCells * cs - floor) > Cozy.View.ViewState.YEps) continue;
            if (!room.Area.Contains(Cozy.Grid.GridSnap.Cell(t.position + t.forward * st.BaseCellLocal(cs).z, o, cs))) continue;
            var top = t.position + t.forward * st.TopAhead(cs);
            var topCell = Cozy.Grid.GridSnap.Cell(top, o, cs);
            if (Cozy.View.ViewState.RoomValid && Cozy.View.ViewState.AccessCells.Contains(topCell)) return true;
            float sx = top.x - pp0.x, sz = top.z - pp0.z;
            if (sx * sx + sz * sz <= vr0 * vr0 && Cozy.Grid.HiddenRooms.SightClear(Cozy.Grid.GridSnap.Cell(pp0, o, cs), topCell, floor)) return true;
        }
        return false;
    };
    System.Func<int, float, bool> SeenAbove = (i, f) =>
    {
        var room = rooms[i];
        if (Above(room, f) || OnFloor(room, f)) return false;
        float vr2 = Cozy.View.ViewState.VisionRadius != null ? Cozy.View.ViewState.VisionRadius() : 12f;
        var pp2 = Cozy.View.ViewState.PlayerPos;
        var hero2 = Cozy.Grid.GridSnap.Cell(pp2, o, cs);
        foreach (var c in room.Area)
        {
            float wx = o.x + c.x * cs, wz = o.z + c.y * cs;
            float ddx = wx - pp2.x, ddz = wz - pp2.z;
            if (ddx * ddx + ddz * ddz > vr2 * vr2) continue;
            bool blocked = false;
            for (float lvl = room.Level; lvl < f - Cozy.View.ViewState.YEps && !blocked; lvl += cs)
                if (Cozy.Grid.BuildQuery.CeilingUnderside(wx, wz, lvl, cs, out _)) blocked = true;
            for (int j = 0; j < rooms.Count && !blocked; j++)
                if (rooms[j].Level > room.Level + 0.01f && rooms[j].Area.Contains(c) && HiddenRule(j, f)) blocked = true;
            if (blocked) continue;
            if (Cozy.Grid.HiddenRooms.SightClear(hero2, c, f)) return true;
        }
        return false;
    };
    int otherFloorBad = 0, otherFloor = 0, aboveDrawn = 0, aboveN = 0, aboveOutN = 0, aboveOutLit = 0, belowDark = 0, belowN = 0, stairRooms = 0, stairLit = 0, seenRooms = 0, seenLit = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (OnFloor(rooms[i], floor)) continue;
        otherFloor++;
        bool reach = (bool)mReach.Invoke(null, new object[] { i, floor });
        bool viaStairs = !Above(rooms[i], floor) && StairsUp(rooms[i]);
        bool seenAbove = SeenAbove(i, floor);
        if (reach != (viaStairs || seenAbove)) otherFloorBad++;
        if (Above(rooms[i], floor)) { if (Under(rooms[i])) { aboveN++; if (Drawn(i)) aboveDrawn++; } else { aboveOutN++; if (!(Active(i) == WantLid(i, floor) && LidFade(i) >= 1f)) aboveOutLit++; } }
        else if (viaStairs) { stairRooms++; if (!Drawn(i)) stairLit++; }
        else if (seenAbove) { seenRooms++; if (!Drawn(i)) seenLit++; }
        else { belowN++; if (Active(i) == WantLid(i, floor) && LidFade(i) >= 1f) belowDark++; }
    }
    if (otherFloor == 0) Skip("RM-A07 закрытых комнат на других этажах нет");
    else Check(otherFloorBad == 0, "RM-A07 другой этаж → недоступна, кроме комнаты ниже с лестницей на этаж героя (RM-A18) и комнаты ниже, видимой сверху (RM-A23): расхождений " + otherFloorBad + " из " + otherFloor);
    if (seenRooms > 0 && Cozy.Grid.HiddenRooms.Lid) Check(seenLit == seenRooms, "RM-A23 комната ниже, клетка без плит над ней в радиусе обзора и на линии взгляда на этаже героя (с крыши смотрю вниз) → без темноты (Илья 28.10: «я поднялся на крышу и по идее должен видеть всё что внутри 1 этажа сверху, но вижу чёрное»): светлых " + seenLit + " из " + seenRooms);
    else if (Cozy.Grid.HiddenRooms.Lid) Skip("RM-A23 комнат ниже, видимых сверху (клетка без плиты в радиусе и на линии взгляда), нет");
    if (aboveN > 0) Check(aboveDrawn == 0, "RM-A11 этаж выше под кукольным домиком → крышка не рисуется (Fade 0, объект выключен): нарисовано " + aboveDrawn + " из " + aboveN);
    if (aboveOutN > 0 && Cozy.Grid.HiddenRooms.Lid) Check(aboveOutLit == 0, "RM-A19 этаж выше, который домик не прячет (герой снаружи / чужое здание) → темнота на самом верхнем этаже: светлых " + aboveOutLit + " из " + aboveOutN);
    if (rooms.Count > 0 && Cozy.Grid.HiddenRooms.Lid)
    {
        bool wasBuild = Cozy.View.ViewState.BuildValid;
        Cozy.View.ViewState.BuildValid = false;
        mSync.Invoke(hr, null);
        int outDark = 0, outN = 0;
        for (int i = 0; i < rooms.Count; i++) { if (!Above(rooms[i], floor)) continue; outN++; if (Active(i) == WantLid(i, floor) && LidFade(i) >= 1f) outDark++; }
        Cozy.View.ViewState.BuildValid = wasBuild;
        mSync.Invoke(hr, null);
        if (outN == 0) Skip("RM-A19b комнат выше этажа обзора нет — «снаружи верх тёмный» не проверено");
        else Check(outDark == outN, "RM-A19b герой снаружи здания (BuildValid выкл) → все комнаты выше тёмные в тот же кадр: " + outDark + " из " + outN);
    }
    if (belowN > 0 && Cozy.Grid.HiddenRooms.Lid) Check(belowDark == belowN, "RM-A16 этаж ниже вне взгляда сверху и без лестницы к герою → темнота стоит (под крышкой верхней — своя не рисуется): верных " + belowDark + " из " + belowN);
    if (stairRooms > 0 && Cozy.Grid.HiddenRooms.Lid) Check(stairLit == stairRooms, "RM-A18 комната ниже с лестницей на этаж героя (верх в доступе или в радиусе) → без темноты, лестница не накрыта: светлых " + stairLit + " из " + stairRooms);
    if (rooms.Count > 0 && Cozy.Grid.HiddenRooms.Lid)
    {
        Cozy.View.ViewState.CurrentFloorY = floor + cs;
        mSync.Invoke(hr, null);
        int darkUp = 0, wantUp = 0;
        for (int i = 0; i < rooms.Count; i++)
        {
            if (!OnFloor(rooms[i], floor)) continue;
            bool reachUp = (bool)mReach.Invoke(null, new object[] { i, floor + cs });
            wantUp++;
            if (reachUp ? !Drawn(i) : (Active(i) == WantLid(i, floor + cs) && LidFade(i) >= 1f)) darkUp++;
        }
        Check(darkUp == wantUp, "RM-A12 герой этажом выше → этаж ниже тёмный в тот же кадр (кроме комнат с лестницей наверх к герою), бывшая комната героя тоже: верных " + darkUp + " из " + wantUp);
        Cozy.View.ViewState.CurrentFloorY = floor - cs;
        mSync.Invoke(hr, null);
        int okDown = 0, wantDown = 0;
        for (int i = 0; i < rooms.Count; i++)
        {
            if (!OnFloor(rooms[i], floor)) continue;
            wantDown++;
            if (Under(rooms[i]) ? !Drawn(i) : (Active(i) == WantLid(i, floor - cs) && LidFade(i) >= 1f)) okDown++;
        }
        Check(okDown == wantDown, "RM-A17 герой этажом ниже → этаж выше под кукольным домиком не рисуется, без домика (снаружи) тёмный в тот же кадр: верных " + okDown + " из " + wantDown);
        Cozy.View.ViewState.CurrentFloorY = floor;
        mSync.Invoke(hr, null);
        int snapped = 0, wantSnap = 0, lit = 0, wantLit = 0;
        for (int i = 0; i < rooms.Count; i++)
        {
            if (!OnFloor(rooms[i], floor)) continue;
            bool reach = !(bool)HR.GetMethod("Dark", NPS).Invoke(null, new object[] { i, floor });
            if (reach) { wantLit++; if (!Drawn(i)) lit++; }
            else { wantSnap++; if (Active(i) == WantLid(i, floor) && LidFade(i) >= 1f) snapped++; }
        }
        Check(snapped == wantSnap && lit == wantLit, "RM-A13 вернулся на этаж → тёмные (недоступные и под крышей только через дверь, RM-A24) стоят целиком (Fade 1), доступные погасли в тот же кадр: " + snapped + " из " + wantSnap + ", светлых " + lit + " из " + wantLit);
    }
    int accessMismatch = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (!OnFloor(rooms[i], floor)) continue;
        bool shares = false;
        if (Cozy.View.ViewState.RoomValid) foreach (var c in Cozy.View.ViewState.AccessCells) if (rooms[i].Area.Contains(c)) { shares = true; break; }
        bool openNear = false;
        float vr = Cozy.View.ViewState.VisionRadius != null ? Cozy.View.ViewState.VisionRadius() : 12f;
        var pp = Cozy.View.ViewState.PlayerPos;
        var heroCell = Cozy.Grid.GridSnap.Cell(pp, o, cs);
        foreach (var op in rooms[i].Openings)
        {
            if (Cozy.Grid.ViewSensor.OpeningKindBetween(op.A, op.B, o, cs, rooms[i].Level) != 1) continue;
            float ddx = op.At.x - pp.x, ddz = op.At.z - pp.z;
            if (ddx * ddx + ddz * ddz <= vr * vr && Cozy.Grid.HiddenRooms.SightClear(heroCell, op.B, rooms[i].Level)) { openNear = true; break; }
        }
        bool inRoom = rooms[i].Area.Contains(Cozy.Grid.GridSnap.Cell(pp, o, cs));
        bool reach = (bool)mReach.Invoke(null, new object[] { i, floor });
        if (reach != (inRoom || shares || openNear)) accessMismatch++;
    }
    int wallBlocked = 0, wallBlockedDark = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (!OnFloor(rooms[i], floor) || rooms[i].Area.Contains(Cozy.Grid.GridSnap.Cell(Cozy.View.ViewState.PlayerPos, o, cs))) continue;
        bool shares = false;
        if (Cozy.View.ViewState.RoomValid) foreach (var c in Cozy.View.ViewState.AccessCells) if (rooms[i].Area.Contains(c)) { shares = true; break; }
        if (shares) continue;
        float vr1 = Cozy.View.ViewState.VisionRadius != null ? Cozy.View.ViewState.VisionRadius() : 12f;
        var pp1 = Cozy.View.ViewState.PlayerPos;
        bool nearButBlocked = false, anySeen = false;
        foreach (var op in rooms[i].Openings)
        {
            if (Cozy.Grid.ViewSensor.OpeningKindBetween(op.A, op.B, o, cs, rooms[i].Level) != 1) continue;
            float ddx = op.At.x - pp1.x, ddz = op.At.z - pp1.z;
            if (ddx * ddx + ddz * ddz > vr1 * vr1) continue;
            if (Cozy.Grid.HiddenRooms.SightClear(Cozy.Grid.GridSnap.Cell(pp1, o, cs), op.B, rooms[i].Level)) anySeen = true; else nearButBlocked = true;
        }
        if (!nearButBlocked || anySeen) continue;
        wallBlocked++;
        if (!(bool)mReach.Invoke(null, new object[] { i, floor })) wallBlockedDark++;
    }
    if (wallBlocked > 0) Check(wallBlockedDark == wallBlocked, "RM-A21 открытая дверь в радиусе, но за стеной от героя (линия взгляда перекрыта) → комната остаётся тёмной (Илья 22.10: «никто не может видеть через стены»): тёмных " + wallBlockedDark + " из " + wallBlocked);
    Check(accessMismatch == 0, "RM-A01b доступность ⇔ герой в комнате ИЛИ общая клетка с AccessCells ИЛИ открытый проём в радиусе обзора и на линии взгляда (клетки без стен и закрытых дверей): расхождений " + accessMismatch);
    var mRound = HR.GetMethod("RoundCorners", NPS);
    var mMerged = HR.GetMethod("MergedArea", NPS);
    if (mRound == null || mMerged == null) Check(false, "RM-V13 ЗАЩИТА МЕРТВА: в HiddenRooms нет RoundCorners/MergedArea");
    else
    {
        int withNear = 0, seamRounded = 0, freeFlat = 0, mergedBad = 0;
        var dirs = new[] { new UnityEngine.Vector2Int(1, 0), new UnityEngine.Vector2Int(-1, 0), new UnityEngine.Vector2Int(0, 1), new UnityEngine.Vector2Int(0, -1) };
        for (int i = 0; i < rooms.Count; i++)
        {
            var area = rooms[i].Area;
            var merged = (System.Collections.Generic.HashSet<UnityEngine.Vector2Int>)mMerged.Invoke(null, new object[] { i });
            if (!merged.IsSupersetOf(area)) mergedBad++;
            bool touches = false;
            foreach (var c in area) foreach (var d in dirs) if (!area.Contains(c + d) && merged.Contains(c + d)) touches = true;
            if (!touches) continue;
            withNear++;
            int minX = int.MaxValue, maxX = int.MinValue, minZ = int.MaxValue, maxZ = int.MinValue;
            foreach (var c in area) { minX = System.Math.Min(minX, c.x); maxX = System.Math.Max(maxX, c.x); minZ = System.Math.Min(minZ, c.y); maxZ = System.Math.Max(maxZ, c.y); }
            float pad = 1.375f * cs, texel = cs / 32f;
            float x0 = o.x + (minX - 0.5f) * cs - pad, x1 = o.x + (maxX + 0.5f) * cs + pad;
            float z0 = o.z + (minZ - 0.5f) * cs - pad, z1 = o.z + (maxZ + 0.5f) * cs + pad;
            int w = UnityEngine.Mathf.CeilToInt((x1 - x0) / texel) + 1, h = UnityEngine.Mathf.CeilToInt((z1 - z0) / texel) + 1;
            var data = new float[w * h];
            mRound.Invoke(null, new object[] { data, w, h, x0, z0, texel, area, merged, o, cs, 1f, null });
            System.Func<int, int, int> Touched = (vx, vz) =>
            {
                float wx = o.x + (vx - 0.5f) * cs, wz = o.z + (vz - 0.5f) * cs;
                int n = 0;
                for (int jj = 0; jj < h; jj++) for (int ii = 0; ii < w; ii++)
                {
                    float px = x0 + ii * texel - wx, pz = z0 + jj * texel - wz;
                    if (px * px + pz * pz <= 0.25f && data[jj * w + ii] != 0f) n++;
                }
                return n;
            };
            var seenV = new System.Collections.Generic.HashSet<UnityEngine.Vector2Int>();
            foreach (var c in area)
                for (int k = 0; k < 4; k++)
                {
                    int vx = c.x + (k & 1), vz = c.y + (k >> 1);
                    if (!seenV.Add(new UnityEngine.Vector2Int(vx, vz))) continue;
                    int nOwn = 0, nAll = 0;
                    for (int q = 0; q < 4; q++)
                    {
                        var cc = new UnityEngine.Vector2Int(vx - 1 + (q & 1), vz - 1 + (q >> 1));
                        if (area.Contains(cc)) nOwn++;
                        if (merged.Contains(cc)) nAll++;
                    }
                    if (nOwn == 1 && nAll == 1) { if (Touched(vx, vz) == 0) freeFlat++; }
                    else if (nAll != nOwn) { if (Touched(vx, vz) > 0) seamRounded++; }
                }
        }
        int lidsN = 0, misaligned = 0;
        var lidList = (System.Collections.IList)fLids.GetValue(hr);
        for (int i = 0; i < lidList.Count && i < rooms.Count; i++)
        {
            var rect = (UnityEngine.Vector4)lidList[i].GetType().GetField("Rect").GetValue(lidList[i]);
            lidsN++;
            foreach (var c in rooms[i].Area)
            {
                float fx = (o.x + (c.x - 0.5f) * cs - rect.x) * rect.z, fz = (o.z + (c.y - 0.5f) * cs - rect.y) * rect.z;
                if (UnityEngine.Mathf.Abs(fx - UnityEngine.Mathf.Round(fx)) > 0.01f || UnityEngine.Mathf.Abs(fz - UnityEngine.Mathf.Round(fz)) > 0.01f) { misaligned++; break; }
            }
        }
        if (lidsN > 0) Check(misaligned == 0, "RM-V14 границы клеток лежат на центрах текселей SDF-текстуры крышки (запас — целое число текселей): иначе угол размазывается на соседнюю крышку и на стыке двух тёмных комнат светлый зубец (Илья 22.10 по скриншоту 15-19-03): крышек " + lidsN + ", смещённых " + misaligned);
        int cornerLids = 0, cornerBad = 0, cornerTotal = 0, slabJunctions = 0, slabRounded = 0;
        var mpbRead = new UnityEngine.MaterialPropertyBlock();
        System.Func<int, UnityEngine.Vector2Int, int, float> ShadeAt = null;
        ShadeAt = (j, c, self) =>
        {
            var lj = lidList[j];
            var TJ = lj.GetType();
            var gj = (UnityEngine.GameObject)TJ.GetField("Go").GetValue(lj);
            bool maskedJ = (bool)TJ.GetField("Masked").GetValue(lj);
            var covJ = (System.Collections.Generic.HashSet<UnityEngine.Vector2Int>)TJ.GetField("Covered").GetValue(lj);
            float v = gj != null && gj.activeSelf && !(maskedJ && covJ.Contains(c)) ? (float)TJ.GetField("Fade").GetValue(lj) : 0f;
            for (int a = 0; a < rooms.Count && a < lidList.Count && v < 1f; a++)
                if (rooms[a].Level > rooms[j].Level + 0.01f && rooms[a].Area.Contains(c)) v = System.Math.Max(v, ShadeAt(a, c, self));
            return v;
        };
        for (int i = 0; i < lidList.Count && i < rooms.Count; i++)
        {
            var lv = lidList[i];
            var go = (UnityEngine.GameObject)lv.GetType().GetField("Go").GetValue(lv);
            if (go == null || !go.activeSelf) continue;
            var rend = (UnityEngine.MeshRenderer)lv.GetType().GetField("Rend").GetValue(lv);
            bool maskedI = (bool)lv.GetType().GetField("Masked").GetValue(lv);
            var cornersL = (System.Collections.Generic.List<UnityEngine.Vector4>)lv.GetType().GetField(maskedI ? "CornersMasked" : "Corners").GetValue(lv);
            var areaUsed = maskedI ? (System.Collections.Generic.HashSet<UnityEngine.Vector2Int>)lv.GetType().GetField("AreaMasked").GetValue(lv) : rooms[i].Area;
            rend.GetPropertyBlock(mpbRead);
            int cnt = (int)mpbRead.GetFloat("_CornerCount");
            var ws = mpbRead.GetFloatArray("_CornerW");
            if (cornersL.Count == 0) continue;
            cornerLids++;
            if (cnt != System.Math.Min(cornersL.Count, 8) || ws == null || ws.Length < cnt) { cornerBad++; continue; }
            for (int k = 0; k < cnt; k++)
            {
                cornerTotal++;
                var cn = cornersL[k];
                int vx = UnityEngine.Mathf.RoundToInt((cn.x - o.x) / cs + 0.5f), vz = UnityEngine.Mathf.RoundToInt((cn.y - o.z) / cs + 0.5f);
                float shade = 0f;
                bool ownCovered = false;
                for (int q = 0; q < 4; q++)
                {
                    var cc = new UnityEngine.Vector2Int(vx - 1 + (q & 1), vz - 1 + (q >> 1));
                    if (areaUsed.Contains(cc)) continue;
                    int j = -1;
                    for (int jj = 0; jj < rooms.Count; jj++) if (System.Math.Abs(rooms[jj].Level - rooms[i].Level) < cs * 0.5f && rooms[jj].Area.Contains(cc)) { j = jj; break; }
                    if (j < 0) continue;
                    if (j == i) ownCovered = true;
                    shade = System.Math.Max(shade, ShadeAt(j, cc, i));
                }
                if (ownCovered) slabJunctions++;
                if (UnityEngine.Mathf.Abs(ws[k] - (1f - shade)) > 0.05f) cornerBad++;
            }
        }
        if (cornerLids > 0) Check(cornerBad == 0, "RM-V15 угол на стыке скругляется обратно, когда соседняя клетка открыта сверху: вес скругления в шейдере = 1 − закрытость соседней клетки (тёмная крышка соседа, нарисованная плита над ней, тёмная комната выше) (Илья 22.10: «если одна из смежных ушла со стороны темноты — другая возвращается в скруглённые»): крышек со стыками " + cornerLids + ", углов " + cornerTotal + ", расхождений " + cornerBad);
        else Skip("RM-V15 нарисованных крышек со стыками нет");
        int maskedLids = 0, maskedFlat = 0, maskedOpen = 0;
        float rad = Cozy.Grid.HiddenRooms.RoundRadius();
        for (int i = 0; i < lidList.Count && i < rooms.Count; i++)
        {
            var lv = lidList[i];
            var sdfM = lv.GetType().GetField("SdfMasked").GetValue(lv);
            var restAll = (System.Collections.Generic.HashSet<UnityEngine.Vector2Int>)lv.GetType().GetField("Rest").GetValue(lv);
            var covered = (System.Collections.Generic.HashSet<UnityEngine.Vector2Int>)lv.GetType().GetField("Covered").GetValue(lv);
            if (sdfM == null || restAll == null || covered == null || covered.Count == 0) continue;
            var area = rooms[i].Area;
            var rest = new System.Collections.Generic.HashSet<UnityEngine.Vector2Int>(restAll); rest.IntersectWith(area);
            if (rest.Count == 0) continue;
            maskedLids++;
            int minX = int.MaxValue, maxX = int.MinValue, minZ = int.MaxValue, maxZ = int.MinValue;
            foreach (var c in area) { minX = System.Math.Min(minX, c.x); maxX = System.Math.Max(maxX, c.x); minZ = System.Math.Min(minZ, c.y); maxZ = System.Math.Max(maxZ, c.y); }
            float pad = 1.375f * cs, texel = cs / 32f;
            float x0 = o.x + (minX - 0.5f) * cs - pad, x1 = o.x + (maxX + 0.5f) * cs + pad;
            float z0 = o.z + (minZ - 0.5f) * cs - pad, z1 = o.z + (maxZ + 0.5f) * cs + pad;
            int w = UnityEngine.Mathf.CeilToInt((x1 - x0) / texel) + 1, h = UnityEngine.Mathf.CeilToInt((z1 - z0) / texel) + 1;
            var hrT = typeof(Cozy.Grid.HiddenRooms);
            var bfS = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
            var segsM = hrT.GetMethod("OverlapSegs", bfS).Invoke(null, new object[] { rest, covered, o, cs });
            var texM = (UnityEngine.Texture2D)hrT.GetMethod("Field", bfS).Invoke(null, new object[] { rest, restAll, o, cs, x0, z0, texel, w, h, 0f, new System.Collections.Generic.List<UnityEngine.Vector4>(), segsM });
            var rtM = UnityEngine.RenderTexture.GetTemporary(w, h, 0, UnityEngine.RenderTextureFormat.RFloat, UnityEngine.RenderTextureReadWrite.Linear);
            UnityEngine.Graphics.Blit(texM, rtM);
            var rdM = new UnityEngine.Texture2D(w, h, UnityEngine.TextureFormat.RFloat, false, true);
            UnityEngine.RenderTexture.active = rtM; rdM.ReadPixels(new UnityEngine.Rect(0, 0, w, h), 0, 0); rdM.Apply(); UnityEngine.RenderTexture.active = null; UnityEngine.RenderTexture.ReleaseTemporary(rtM);
            var data = rdM.GetPixelData<float>(0).ToArray();
            UnityEngine.Object.Destroy(texM); UnityEngine.Object.Destroy(rdM);
            var cmL = (System.Collections.Generic.List<UnityEngine.Vector4>)lv.GetType().GetField("CornersMasked").GetValue(lv);
            float rL = (float)lv.GetType().GetField("R").GetValue(lv);
            var seenV = new System.Collections.Generic.HashSet<UnityEngine.Vector2Int>();
            foreach (var c in rest)
                for (int k = 0; k < 4; k++)
                {
                    int vx = c.x + (k & 1), vz = c.y + (k >> 1);
                    if (!seenV.Add(new UnityEngine.Vector2Int(vx, vz))) continue;
                    int nRest = 0, nCov = 0, nOther = 0;
                    for (int q = 0; q < 4; q++)
                    {
                        var cc = new UnityEngine.Vector2Int(vx - 1 + (q & 1), vz - 1 + (q >> 1));
                        if (rest.Contains(cc)) nRest++; else if (covered.Contains(cc)) nCov++; else if (restAll.Contains(cc)) nOther++;
                    }
                    if (nRest != 1 || nCov == 0 || nOther > 0) continue;
                    float wx = o.x + (vx - 0.5f) * cs, wz = o.z + (vz - 0.5f) * cs;
                    UnityEngine.Vector2Int own = default(UnityEngine.Vector2Int);
                    for (int q = 0; q < 4; q++) { var cc = new UnityEngine.Vector2Int(vx - 1 + (q & 1), vz - 1 + (q >> 1)); if (rest.Contains(cc)) own = cc; }
                    var dir = new UnityEngine.Vector2(wx - (o.x + own.x * cs), wz - (o.z + own.y * cs)).normalized;
                    float lapM = System.Math.Max(0.03f, rad * (UnityEngine.Mathf.Sqrt(2f) - 1f) + 0.01f);
                    System.Func<float, float, float> At = (sx, sz) =>
                    {
                        float fx = (sx - x0) / texel, fz = (sz - z0) / texel;
                        int ix = UnityEngine.Mathf.FloorToInt(fx), iz = UnityEngine.Mathf.FloorToInt(fz);
                        float tx = fx - ix, tz = fz - iz;
                        float dv = UnityEngine.Mathf.Lerp(UnityEngine.Mathf.Lerp(data[iz * w + ix], data[iz * w + ix + 1], tx), UnityEngine.Mathf.Lerp(data[(iz + 1) * w + ix], data[(iz + 1) * w + ix + 1], tx), tz);
                        foreach (var cn in cmL)
                        {
                            float ux = (sx - cn.x) * cn.z, uz = (sz - cn.y) * cn.w;
                            if (ux < 0f || ux > rL || uz < 0f || uz > rL) continue;
                            float ax = sx - (cn.x + cn.z * rL), az = sz - (cn.y + cn.w * rL);
                            dv = rL - UnityEngine.Mathf.Sqrt(ax * ax + az * az);
                        }
                        return dv;
                    };
                    float isx = UnityEngine.Mathf.Sign(o.x + own.x * cs - wx), isz = UnityEngine.Mathf.Sign(o.z + own.y * cs - wz);
                    bool roofX = covered.Contains(new UnityEngine.Vector2Int(own.x - (int)isx, own.y)), roofZ = covered.Contains(new UnityEngine.Vector2Int(own.x, own.y - (int)isz));
                    if (At(wx + (roofX ? 0f : isx * 0.125f), wz + (roofZ ? 0f : isz * 0.125f)) <= 0f) maskedOpen++;
                    if (rad > 0.01f && At(wx + dir.x * lapM, wz + dir.y * lapM) >= 0f) maskedFlat++;
                }
        }
        if (maskedLids > 0) Check(maskedFlat == 0 && maskedOpen == 0, "RM-V19 угол крышки-маски на стыке с накрытой крышей частью своей комнаты СКРУГЛЁН, как любой свободный (Илья 28.10 по скриншоту 19-42-07: «где лестница — углы есть где прямые — так не должно быть — всегда закругляем»; 28.10 21-08-24: нахлёст 3 см у шва с крышей не возвращает острый угол — поле вместе со швами): крышек-масок " + maskedLids + ", прямых углов " + maskedFlat + ", вершин дыры не накрыто " + maskedOpen + " (сторона у наружной стены — точка у внутренней грани стены, 12,5 см от оси) (Илья 28.10 21-38-17: «где лестница — не до конца покрывает»: дуга у крыши заходит на плиту на 0,414·R + 1 см и накрывает угол дыры; 21-51-17: дугу у крыши рисует шейдер по `CornersMasked`, в текстуре только прямой сдвиг — иначе билинейка рвёт дугу)");
        else Skip("RM-V19 крышек-масок (крыша на части клеток) нет");
        if (withNear > 0) Check(seamRounded == 0 && freeFlat == 0 && mergedBad == 0, "RM-V13 смежные комнаты одного этажа сливаются в одну тень: углы на стыке не скругляются, свободные углы скруглены (Илья 22.10: «если смежные, то объединяются»): комнат со смежниками " + withNear + ", скруглений на стыке " + seamRounded + ", плоских свободных углов " + freeFlat + ", объединений без своих клеток " + mergedBad);
        else Skip("RM-V13 смежных комнат одного этажа на уровне нет");
    }
    sb.Append("комнат " + rooms.Count + ", этаж обзора " + floor.ToString("0.#") + ", AccessCells " + Cozy.View.ViewState.AccessCells.Count + ", RoomValid " + Cozy.View.ViewState.RoomValid + "\n" + table);
}
finally
{
    Cozy.View.ViewState.HiddenRooms = wasOn;
    fScanned.SetValue(hr, false);
    mLate.Invoke(hr, null);
}
return (fails == 0 ? "ЗЕЛЁНОЕ" : "КРАСНОЕ") + " RM: проверок " + checks + ", красных " + fails + ", пропусков " + skips + "\n" + sb;
