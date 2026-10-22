// Закрытые комнаты (ROOMS.md, коды RM-…): флаг HiddenRooms, скан комнат (топология, закрытость по
// независимому обходу рёбер), правило недоступности по AccessCells, крестики, крышки не выше этажа обзора
// (Илья 22.10: «чернота этажей выше никогда не рисуется»; «если я на 2 этаже — темнота с закрытых комнат
// не должна исчезать, если потолка нет — сверху смотрю»), закрытая комната = внутри здания.
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
var mOnFloor = HR.GetMethod("OnFloor", NPS);
var mAbove = HR.GetMethod("AboveFloor", NPS);
var mUnder = HR.GetMethod("UnderDollhouse", NPS);
var mInterior = HR.GetMethod("Interior", NPS);
var mSolid = HR.GetMethod("Solid", NPS);
var fMarks = HR.GetField("_marks", NPI);
var fLids = HR.GetField("_lids", NPI);
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
        bool reach = (bool)mReach.Invoke(null, new object[] { r, Cozy.View.ViewState.CurrentFloorY });
        table.Append("  #" + i + " уровень " + r.Level.ToString("0.#") + " клеток " + r.Cells + " центр " + r.Center.x.ToString("0.#") + "/" + r.Center.z.ToString("0.#") + (reach ? " доступна" : " КРЕСТИК") + "\n");
    }
    Check(badShape == 0, "RM-S02 форма комнат (клетки, уровень, центр, габарит Min/Max, ≤400): плохих " + badShape + " из " + rooms.Count);
    Check(badCell == 0 && noInterior == 0, "RM-S03 клетка комнаты не куб, хотя бы одна клетка интерьер (проём лестницы в полу — тоже клетка комнаты): кубов " + badCell + ", комнат без интерьера " + noInterior);
    Check(leaks == 0, "RM-S04 закрытость независимым обходом рёбер: утечек " + leaks);
    Check(overlaps == 0, "RM-S05 комнаты одного уровня не пересекаются: пересечений " + overlaps);
    if (rooms.Count == 0) Skip("RM-S02…S05 на уровне нет закрытых комнат — правила не проверены (нужен стенд rooms_test)");

    // ---------- RM-A: недоступность и крестики ----------
    System.Func<int, float, bool> HiddenRule = (i, f) => !(Above(rooms[i], f) && Under(rooms[i])) && !(bool)mReach.Invoke(null, new object[] { rooms[i], f });
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
            bool overlap = false; foreach (var c in rooms[j].Area) if (rooms[i].Area.Contains(c)) { overlap = true; break; }
            if (!overlap) continue;
            above++; if (HiddenRule(j, f)) shaded++;
        }
        bool coverOn = shaded == above && (ceil == 0 || CeilingDrawn(i, f));
        return covered == rooms[i].Area.Count && covered > 0 && coverOn;
    };
    System.Func<int, float, bool> WantLid = (i, f) => Cozy.Grid.HiddenRooms.Lid && HiddenRule(i, f) && !Topped(i, f);
    mSync.Invoke(hr, null);
    float floor = Cozy.View.ViewState.CurrentFloorY;
    int unreachable = 0;
    for (int i = 0; i < rooms.Count; i++)
        if (!(Above(rooms[i], floor) && Under(rooms[i])) && !(bool)mReach.Invoke(null, new object[] { rooms[i], floor })) unreachable++;
    int wantMarks = Cozy.Grid.HiddenRooms.Marks ? unreachable : 0;
    Check(ActiveMarks() == wantMarks, "RM-A01 маркеры ⇔ недоступные, кроме спрятанных кукольным домиком (крестики " + (Cozy.Grid.HiddenRooms.Marks ? "вкл" : "выкл") + "): активных " + ActiveMarks() + ", ждём " + wantMarks);
    int activeLids = 0, wantLids = 0, lidMismatch = 0;
    for (int i = 0; i < rooms.Count; i++) { bool a = Active(i), w = WantLid(i, floor); if (a) activeLids++; if (w) wantLids++; if (a != w) lidMismatch++; }
    Check(lidMismatch == 0, "RM-V10 крышки ⇔ недоступные, кроме спрятанных кукольным домиком и накрытых крышкой верхней комнаты (крышка " + (Cozy.Grid.HiddenRooms.Lid ? "вкл" : "выкл") + "): активных " + activeLids + ", ждём " + wantLids + ", расхождений " + lidMismatch);
    int toppedN = 0, toppedOff = 0;
    for (int i = 0; i < rooms.Count; i++) if (HiddenRule(i, floor) && Topped(i, floor)) { toppedN++; if (!Active(i)) toppedOff++; }
    if (toppedN > 0 && Cozy.Grid.HiddenRooms.Lid) Check(toppedOff == toppedN, "RM-A20 комната целиком под нарисованной крышкой верхней комнаты или под нарисованным потолком → своя крышка не рисуется (темнота только на самом верхнем этаже; «если есть потолок — то потолка»): выключено " + toppedOff + " из " + toppedN);
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
    else Check((bool)mReach.Invoke(null, new object[] { rooms[mine], floor }), "RM-A02 комната героя #" + mine + " без крестика");
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
    int otherFloorBad = 0, otherFloor = 0, aboveDrawn = 0, aboveN = 0, aboveOutN = 0, aboveOutLit = 0, belowDark = 0, belowN = 0, stairRooms = 0, stairLit = 0;
    for (int i = 0; i < rooms.Count; i++)
    {
        if (OnFloor(rooms[i], floor)) continue;
        otherFloor++;
        bool reach = (bool)mReach.Invoke(null, new object[] { rooms[i], floor });
        bool viaStairs = !Above(rooms[i], floor) && StairsUp(rooms[i]);
        if (reach != viaStairs) otherFloorBad++;
        if (Above(rooms[i], floor)) { if (Under(rooms[i])) { aboveN++; if (Drawn(i)) aboveDrawn++; } else { aboveOutN++; if (!(Active(i) == WantLid(i, floor) && LidFade(i) >= 1f)) aboveOutLit++; } }
        else if (viaStairs) { stairRooms++; if (!Drawn(i)) stairLit++; }
        else { belowN++; if (Active(i) == WantLid(i, floor) && LidFade(i) >= 1f) belowDark++; }
    }
    if (otherFloor == 0) Skip("RM-A07 закрытых комнат на других этажах нет");
    else Check(otherFloorBad == 0, "RM-A07 другой этаж → недоступна, кроме комнаты ниже с лестницей на этаж героя (RM-A18): расхождений " + otherFloorBad + " из " + otherFloor);
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
    if (belowN > 0 && Cozy.Grid.HiddenRooms.Lid) Check(belowDark == belowN, "RM-A16 этаж ниже → темнота стоит (сверху в комнату без потолка смотрим, а она закрыта; под крышкой верхней — своя не рисуется): верных " + belowDark + " из " + belowN);
    if (stairRooms > 0 && Cozy.Grid.HiddenRooms.Lid) Check(stairLit == stairRooms, "RM-A18 комната ниже с лестницей на этаж героя (верх в доступе или в радиусе) → без темноты, лестница не накрыта: светлых " + stairLit + " из " + stairRooms);
    if (rooms.Count > 0 && Cozy.Grid.HiddenRooms.Lid)
    {
        Cozy.View.ViewState.CurrentFloorY = floor + cs;
        mSync.Invoke(hr, null);
        int darkUp = 0, wantUp = 0;
        for (int i = 0; i < rooms.Count; i++)
        {
            if (!OnFloor(rooms[i], floor)) continue;
            bool reachUp = (bool)mReach.Invoke(null, new object[] { rooms[i], floor + cs });
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
            bool reach = (bool)mReach.Invoke(null, new object[] { rooms[i], floor });
            if (reach) { wantLit++; if (!Drawn(i)) lit++; }
            else { wantSnap++; if (Active(i) == WantLid(i, floor) && LidFade(i) >= 1f) snapped++; }
        }
        Check(snapped == wantSnap && lit == wantLit, "RM-A13 вернулся на этаж → недоступные стоят целиком (Fade 1), доступные погасли в тот же кадр: " + snapped + " из " + wantSnap + ", светлых " + lit + " из " + wantLit);
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
        bool reach = (bool)mReach.Invoke(null, new object[] { rooms[i], floor });
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
        if (!(bool)mReach.Invoke(null, new object[] { rooms[i], floor })) wallBlockedDark++;
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
            float pad = 1.375f * cs, texel = cs / 8f;
            float x0 = o.x + (minX - 0.5f) * cs - pad, x1 = o.x + (maxX + 0.5f) * cs + pad;
            float z0 = o.z + (minZ - 0.5f) * cs - pad, z1 = o.z + (maxZ + 0.5f) * cs + pad;
            int w = UnityEngine.Mathf.CeilToInt((x1 - x0) / texel) + 1, h = UnityEngine.Mathf.CeilToInt((z1 - z0) / texel) + 1;
            var data = new float[w * h];
            mRound.Invoke(null, new object[] { data, w, h, x0, z0, texel, area, merged, o, cs, 1f, 0f, null });
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
        int cornerLids = 0, cornerBad = 0, cornerTotal = 0;
        var mpbRead = new UnityEngine.MaterialPropertyBlock();
        for (int i = 0; i < lidList.Count && i < rooms.Count; i++)
        {
            var lv = lidList[i];
            var go = (UnityEngine.GameObject)lv.GetType().GetField("Go").GetValue(lv);
            if (go == null || !go.activeSelf) continue;
            var rend = (UnityEngine.MeshRenderer)lv.GetType().GetField("Rend").GetValue(lv);
            var cornersL = (System.Collections.Generic.List<UnityEngine.Vector4>)lv.GetType().GetField("Corners").GetValue(lv);
            var ownersL = (System.Collections.Generic.List<UnityEngine.Vector3Int>)lv.GetType().GetField("CornerRooms").GetValue(lv);
            var maskedTex = lv.GetType().GetField("SdfMasked").GetValue(lv);
            rend.GetPropertyBlock(mpbRead);
            int cnt = (int)mpbRead.GetFloat("_CornerCount");
            var ws = mpbRead.GetFloatArray("_CornerW");
            if (cornersL.Count == 0) continue;
            cornerLids++;
            var usedTex = mpbRead.GetTexture("_Sdf");
            if (maskedTex != null && ReferenceEquals(usedTex, maskedTex)) continue;
            if (cnt != System.Math.Min(cornersL.Count, 8) || ws == null || ws.Length < cnt) { cornerBad++; continue; }
            for (int k = 0; k < cnt; k++)
            {
                cornerTotal++;
                float shade = 0f;
                var ow = ownersL[k];
                foreach (int j in new[] { ow.x, ow.y, ow.z })
                {
                    if (j < 0 || j >= lidList.Count) continue;
                    var og = (UnityEngine.GameObject)lidList[j].GetType().GetField("Go").GetValue(lidList[j]);
                    float f = (float)lidList[j].GetType().GetField("Fade").GetValue(lidList[j]);
                    if (og != null && og.activeSelf) shade = System.Math.Max(shade, f);
                }
                if (UnityEngine.Mathf.Abs(ws[k] - (1f - shade)) > 0.05f) cornerBad++;
            }
        }
        if (cornerLids > 0) Check(cornerBad == 0, "RM-V15 угол на стыке скругляется обратно, когда соседняя комната не тёмная: вес скругления в шейдере = 1 − рисуемость соседней крышки (Илья 22.10: «если одна из смежных ушла со стороны темноты — другая возвращается в скруглённые»): крышек со стыками " + cornerLids + ", углов " + cornerTotal + ", расхождений " + cornerBad);
        else Skip("RM-V15 нарисованных крышек со стыками нет");
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
