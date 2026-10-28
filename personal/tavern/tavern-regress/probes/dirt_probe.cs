// КИСТЬ ГРЯЗИ (P1052, P1053, P1055, P1056, P1057, P1064, P1065; инв. 550–554, 563). Для execute_code (в play).
// 1) квады грязи над плитами = нарисованные плиты Floor по этажам (включая ceiling, скрытые видом — нет);
// 2) очередь ковровой грязи выше ковра; 3) новый атлас стен обнулён; 4) мазок по свободной стене —
// пятно по кисти в одной плитке, не вся грань; 5) сейв → загрузка атласа стен без потерь;
// 6) у каждой лестницы носители боковин (коллайдеры SideWall), настоящий луч WallFaceOnRay: в бок лестницы —
// грань лестницы, в ступень — полу; верх стены этажа ниже — полу, стены своего этажа — грань (этаж кисти
// переключается через _buildLevel и возвращается);
// 7) крыша (инв. 564): у видимой крыши луч сверху RoofUnderCursor даёт точку на скате, мазок DirtStamp ложится в канал
// этажа крыши у этой XZ, меши крыши собраны в _dirtRoofs, материал крыши с _SlopeUV; маску проба возвращает.
// 8) фронтон (инв. 565): у видимой крыши луч в фронтон GableUnderCursor даёт грань с хозяином-узлом фронтона и
// высотой до конька; мазок WallDirtStamp красит плитку этой грани (атлас проба возвращает вместе со стенами).
// Всё, что проба намазала, она стирает сама; атлас, созданный ею, снимает. Временные файлы сейва лежат в
// temporaryCachePath и перезаписываются каждым прогоном (File.Delete мост не пропускает).
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
var T = typeof(Cozy.Grid.GridCursor);
var B = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var sb = new System.Text.StringBuilder();
var bad = new System.Collections.Generic.List<string>();
float cell = 3f;
var overlays = T.GetField("_dirtOverlays", B).GetValue(gc) as UnityEngine.GameObject[];
if (overlays == null || overlays[0] == null) sb.Append("квады: грязи пола на уровне нет, пропуск; ");
else
{
    var want = new int[overlays.Length];
    foreach (var gb in Cozy.Grid.GridBlock.All)
    {
        if (gb == null || gb.role != Cozy.Grid.GridRole.Floor || gb.railing || !Cozy.Grid.FloorPieceView.Drawn(gb.Rend)) continue;
        int l = Cozy.Grid.GridManager.LevelIndex(gb.transform.position.y + gb.transform.lossyScale.y * 0.5f, cell);
        if (l >= 0 && l < want.Length) want[l]++;
    }
    for (int l = 0; l < overlays.Length; l++)
    {
        var mf = overlays[l] != null ? overlays[l].GetComponent<UnityEngine.MeshFilter>() : null;
        int have = mf != null && mf.sharedMesh != null ? mf.sharedMesh.vertexCount / 4 : 0;
        sb.Append("этаж " + l + " квадов " + have + "/" + want[l] + "; ");
        if (have != want[l]) bad.Add("этаж " + l + ": квадов грязи " + have + ", нарисованных плит " + want[l] + " (P1053/P1055/инв. 552)");
    }
}
var rugMats = T.GetField("_dirtRugMats", B).GetValue(gc) as UnityEngine.Material[,];
if (rugMats != null && rugMats[0, 0] != null)
{
    int q = rugMats[0, 0].renderQueue;
    sb.Append("очередь ковров " + q + "; ");
    if (q <= 3400) bad.Add("очередь ковровой грязи " + q + " не выше ковра 3400 (P1052)");
}
var mCollect = T.GetMethod("CollectWallHosts", B);
var mOnRay = T.GetMethod("WallFaceOnRay", B);
var fByRoot = T.GetField("_wallHostByRoot", B);
var fHosts = T.GetField("_wallHosts", B);
var fBuildLevel = T.GetField("_buildLevel", B);
if (mOnRay == null) sb.Append("WallFaceOnRay нет в домене — бок лестницы и кромка пола не проверены (⏳ после перекомпиляции); ");
else
{
    mCollect.Invoke(gc, null);
    var byRoot = fByRoot.GetValue(gc) as System.Collections.IDictionary;
    int stairsAll = 0, stairsHosted = 0;
    foreach (var sp in Cozy.Grid.StairPiece.All) { if (sp == null) continue; stairsAll++; if (byRoot.Contains(sp.transform)) stairsHosted++; }
    sb.Append("лестниц с боковинами " + stairsHosted + "/" + stairsAll + "; ");
    if (stairsHosted != stairsAll) bad.Add("лестниц без носителей боковин: " + (stairsAll - stairsHosted) + " (P1064)");
    int savedBuild = (int)fBuildLevel.GetValue(gc);
    int playerLevel = (int)T.GetMethod("DirtLevel", B).Invoke(gc, null) - savedBuild;
    try
    {
        string stairSide = "бок лестницы: нет луча без заслона", stairTop = "ступень: нет луча без заслона";
        foreach (var sp in Cozy.Grid.StairPiece.All)
        {
            if (sp == null || !byRoot.Contains(sp.transform)) continue;
            var hosts = byRoot[sp.transform] as System.Collections.IList;
            foreach (var h in hosts)
            {
                var ht = h.GetType();
                bool thinX = (bool)ht.GetField("thinX").GetValue(h);
                float cx = (float)ht.GetField("cx").GetValue(h), cz = (float)ht.GetField("cz").GetValue(h);
                float sx = (float)ht.GetField("sx").GetValue(h), sz = (float)ht.GetField("sz").GetValue(h);
                float fy = (float)ht.GetField("floorY").GetValue(h); int lv = (int)ht.GetField("level").GetValue(h);
                float side = thinX ? UnityEngine.Mathf.Sign(cx - sp.transform.position.x) : UnityEngine.Mathf.Sign(cz - sp.transform.position.z);
                var nrm = thinX ? new UnityEngine.Vector3(side, 0f, 0f) : new UnityEngine.Vector3(0f, 0f, side);
                float plane = (thinX ? cx : cz) + side * (thinX ? sx : sz) * 0.5f;
                var pt = thinX ? new UnityEngine.Vector3(plane, fy + 0.6f, cz) : new UnityEngine.Vector3(cx, fy + 0.6f, plane);
                var ray = default(UnityEngine.Ray); var hit = default(UnityEngine.RaycastHit); bool clear = false;
                float[] dists = { 3f, 1.5f, 0.8f }; float[] ups = { 2.5f, 1.5f, 0.8f };
                for (int di = 0; di < dists.Length && !clear; di++)
                    for (int ui = 0; ui < ups.Length && !clear; ui++)
                    {
                        var org = pt + nrm * dists[di] + UnityEngine.Vector3.up * ups[ui];
                        ray = new UnityEngine.Ray(org, (pt - org).normalized);
                        if (!UnityEngine.Physics.Raycast(ray, out hit, 20f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) continue;
                        if (hit.collider.GetComponentInParent<Cozy.Grid.StairPiece>() != sp) continue;
                        float along = thinX ? hit.normal.x : hit.normal.z;
                        clear = UnityEngine.Mathf.Abs(along) >= 0.5f;
                    }
                if (!clear) continue;
                fBuildLevel.SetValue(gc, lv - playerLevel);
                var args = new object[] { ray, null, null };
                bool got = (bool)mOnRay.Invoke(gc, args);
                var fh = args[2] != null ? args[2].GetType().GetField("host").GetValue(args[2]) as UnityEngine.Transform : null;
                bool ok = got && fh == sp.transform;
                stairSide = "бок лестницы → грань лестницы: " + (ok ? "да" : "НЕТ (got " + got + ", host " + (fh != null ? fh.name : "—") + ")");
                if (!ok) bad.Add("луч в бок лестницы не даёт грань лестницы (P1064)");
                var rampT = sp.transform.Find("RampCollider"); var rampC = rampT != null ? rampT.GetComponent<UnityEngine.Collider>() : null;
                var topOrg = (rampC != null ? rampC.bounds.center : sp.transform.position + UnityEngine.Vector3.up * 1.5f) + UnityEngine.Vector3.up * 1f;
                var topRay = new UnityEngine.Ray(topOrg, UnityEngine.Vector3.down);
                if (UnityEngine.Physics.Raycast(topRay, out hit, 3f, ~0, UnityEngine.QueryTriggerInteraction.Ignore) && hit.collider.GetComponentInParent<Cozy.Grid.StairPiece>() == sp)
                {
                    args = new object[] { topRay, null, null };
                    bool gotTop = (bool)mOnRay.Invoke(gc, args);
                    stairTop = "ступень → полу: " + (gotTop ? "НЕТ, прилипла к боку" : "да");
                    if (gotTop) bad.Add("луч в ступень лестницы прилипает к боку (P1064)");
                }
                break;
            }
            if (stairSide.EndsWith("да") || stairSide.Contains("НЕТ")) break;
        }
        sb.Append(stairSide + "; " + stairTop + "; ");
        string lower = "верх стены этажа ниже: нет луча без заслона", own = "верх стены своего этажа: нет луча без заслона";
        var all = fHosts.GetValue(gc) as System.Collections.IList;
        foreach (var h in all)
        {
            var ht = h.GetType();
            if ((bool)ht.GetField("cube").GetValue(h) || (bool)ht.GetField("stair").GetValue(h)) continue;
            var root = ht.GetField("root").GetValue(h) as UnityEngine.Transform;
            if (root == null || root.GetComponent<Cozy.Grid.GridBlock>() == null) continue;
            bool thinX = (bool)ht.GetField("thinX").GetValue(h);
            float cx = (float)ht.GetField("cx").GetValue(h), cz = (float)ht.GetField("cz").GetValue(h);
            float sx = (float)ht.GetField("sx").GetValue(h), sz = (float)ht.GetField("sz").GetValue(h);
            float fy = (float)ht.GetField("floorY").GetValue(h); int lv = (int)ht.GetField("level").GetValue(h);
            if (lv > 2) continue;
            bool found = false;
            for (int s = -1; s <= 1 && !found; s += 2)
            {
                var nrm = thinX ? new UnityEngine.Vector3(s, 0f, 0f) : new UnityEngine.Vector3(0f, 0f, s);
                var pt = thinX ? new UnityEngine.Vector3(cx + s * sx * 0.3f, fy + cell, cz) : new UnityEngine.Vector3(cx, fy + cell, cz + s * sz * 0.3f);
                var org = pt + nrm * 2f + UnityEngine.Vector3.up * 3f;
                var ray = new UnityEngine.Ray(org, (pt - org).normalized);
                UnityEngine.RaycastHit hit;
                if (!UnityEngine.Physics.Raycast(ray, out hit, 20f, ~0, UnityEngine.QueryTriggerInteraction.Ignore)) continue;
                var gbHit = hit.collider.GetComponentInParent<Cozy.Grid.GridBlock>();
                if (gbHit == null || gbHit.transform != root || hit.normal.y < 0.5f) continue;
                found = true;
                fBuildLevel.SetValue(gc, lv + 1 - playerLevel);
                var args = new object[] { ray, null, null };
                bool gotLower = (bool)mOnRay.Invoke(gc, args);
                lower = "верх стены этажа ниже → полу: " + (gotLower ? "НЕТ, кисть прилипла к стене" : "да");
                if (gotLower) bad.Add("кисть с этажа выше прилипает к верху стены этажа ниже (P1065)");
                fBuildLevel.SetValue(gc, lv - playerLevel);
                args = new object[] { ray, null, null };
                bool gotOwn = (bool)mOnRay.Invoke(gc, args);
                own = "верх стены своего этажа → грань: " + (gotOwn ? "да" : "НЕТ");
                if (!gotOwn) bad.Add("верх стены своего этажа не даёт грань (P1065)");
            }
            if (found) break;
        }
        sb.Append(lower + "; " + own + "; ");
    }
    finally { fBuildLevel.SetValue(gc, savedBuild); }
}
var fErase7 = T.GetField("_dirtErase", B); var fRadius7 = T.GetField("_brushRadius", B); var fVariant7 = T.GetField("_dirtVariant", B);
var mRoof = T.GetMethod("RoofUnderCursor", B);
if (mRoof == null) sb.Append("RoofUnderCursor нет в домене — крыша не проверена (⏳ после перекомпиляции); ");
else
{
    Cozy.Grid.RoofPiece roofSeen = null; var roofRay = default(UnityEngine.Ray); float roofDist = 0f;
    foreach (var r in Cozy.Grid.RoofPiece.All)
    {
        if (r == null) continue;
        var top = r.Bounds.center + UnityEngine.Vector3.up * 12f;
        var ray = new UnityEngine.Ray(top, UnityEngine.Vector3.down);
        float d;
        if (r.RayHit(ray, out d)) { roofSeen = r; roofRay = ray; roofDist = d; break; }
    }
    if (roofSeen == null) sb.Append("крыша: видимых крыш нет, пропуск; ");
    else
    {
        var rargs = new object[] { roofRay, null, null };
        bool gotRoof = (bool)mRoof.Invoke(gc, rargs);
        var rp = rargs[1] as Cozy.Grid.RoofPiece; var rpt = (UnityEngine.Vector3)rargs[2];
        sb.Append("крыша: луч сверху → " + (gotRoof ? "скат " + (rp == roofSeen ? "своей" : "ЧУЖОЙ") + " крыши, y " + rpt.y.ToString("F2") : "НЕТ") + "; ");
        if (!gotRoof || rp != roofSeen) bad.Add("луч сверху в видимую крышу не даёт её скат (инв. 564)");
        var masks = T.GetField("_dirtMasks", B).GetValue(gc) as UnityEngine.Texture2D[];
        var roofMats = T.GetField("_dirtRoofMats", B).GetValue(gc) as UnityEngine.Material[,];
        if (gotRoof && masks != null && masks[0] != null && roofMats != null && roofMats[0, 0] != null)
        {
            int lv = (int)T.GetMethod("RoofDirtLevel", B).Invoke(gc, new object[] { rp });
            int variant = (int)fVariant7.GetValue(gc);
            var mask = masks[variant];
            var before = mask.GetPixels32();
            var used = T.GetField("_dirtLevelUsed", B).GetValue(gc) as bool[,];
            bool usedBefore = used[variant, lv];
            float minX = (float)T.GetField("_freePaintMinX", B).GetValue(gc), minZ = (float)T.GetField("_freePaintMinZ", B).GetValue(gc), ppm = (float)T.GetField("_freePaintPxPerM", B).GetValue(gc);
            bool erase = (bool)fErase7.GetValue(gc);
            try
            {
                fErase7.SetValue(gc, false); fRadius7.SetValue(gc, 0.5f);
                T.GetMethod("DirtStamp", B).Invoke(gc, new object[] { rpt, lv });
                int px = UnityEngine.Mathf.Clamp(UnityEngine.Mathf.RoundToInt((rpt.x - minX) * ppm), 0, mask.width - 1);
                int pz = UnityEngine.Mathf.Clamp(UnityEngine.Mathf.RoundToInt((rpt.z - minZ) * ppm), 0, mask.height - 1);
                var c = mask.GetPixel(px, pz);
                float ch = lv == 0 ? c.r : lv == 1 ? c.g : lv == 2 ? c.b : c.a;
                sb.Append("мазок на крышу: канал " + lv + " = " + ch.ToString("F2") + ", мешей крыш " + (T.GetField("_dirtRoofs", B).GetValue(gc) as System.Collections.IList).Count + ", _SlopeUV " + roofMats[variant, lv].GetFloat("_SlopeUV") + "; ");
                if (ch <= 0.01f) bad.Add("мазок на крышу не попал в маску этажа крыши (инв. 564)");
                if (roofMats[variant, lv].GetFloat("_SlopeUV") < 0.5f) bad.Add("материал грязи крыши без _SlopeUV (инв. 564)");
            }
            finally
            {
                mask.SetPixels32(before); mask.Apply();
                used[variant, lv] = usedBefore;
                fErase7.SetValue(gc, erase);
            }
        }
    }
}
var fAtlas = T.GetField("_wallAtlas", B);
var fFaces = T.GetField("_wallFaces", B);
var fIndex = T.GetField("_wallFaceIndex", B);
var mEnsure = T.GetMethod("EnsureWallDirt", B);
var mRelease = T.GetMethod("ReleaseWallDirt", B);
var mFace = T.GetMethod("WallFaceUnderCursor", B);
var mStamp = T.GetMethod("WallDirtStamp", B);
var mSave = T.GetMethod("SaveWallDirt", B);
var mLoad = T.GetMethod("LoadWallDirt", B);
var fErase = T.GetField("_dirtErase", B); var fRadius = T.GetField("_brushRadius", B); var fVariant = T.GetField("_dirtVariant", B);
bool createdHere = false;
var atlas = fAtlas.GetValue(gc) as UnityEngine.Texture2D;
if (atlas == null)
{
    mEnsure.Invoke(gc, null);
    atlas = fAtlas.GetValue(gc) as UnityEngine.Texture2D;
    createdHere = true;
    int dirty = 0;
    foreach (var c in atlas.GetPixels32()) if (c.r > 0 || c.g > 0 || c.b > 0 || c.a > 0) dirty++;
    sb.Append("новый атлас: мусора " + dirty + "; ");
    if (dirty > 0) bad.Add("новый атлас стен не обнулён: " + dirty + " пикселей (P1056)");
}
var cam = UnityEngine.Camera.main; var mouse = UnityEngine.InputSystem.Mouse.current;
var cursor = mouse.position.ReadValue();
var savedPos = cam.transform.position; var savedRot = cam.transform.rotation;
bool savedErase = (bool)fErase.GetValue(gc); float savedRadius = (float)fRadius.GetValue(gc); int savedVariant = (int)fVariant.GetValue(gc);
var snapshot = atlas.GetPixels32();
var facesBefore = fFaces.GetValue(gc) as System.Collections.IList;
int facesCountBefore = facesBefore.Count;
var player = Cozy.Grid.PlayerRef.GameObject;
float floorY = Cozy.Grid.GridManager.LevelY(player.transform.position.y + 0.05f, cell);
Cozy.Grid.GridBlock wall = null; var back = UnityEngine.Vector3.zero; bool wallThinX = false;
var cols = new UnityEngine.Collider[32];
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.role != Cozy.Grid.GridRole.Wall || gb.railing || !Cozy.Grid.FloorPieceView.Drawn(gb.Rend)) continue;
    var p = gb.transform.position; var s = gb.transform.lossyScale;
    if (UnityEngine.Mathf.Abs(p.y - s.y * 0.5f - floorY) > 0.3f || (p - player.transform.position).sqrMagnitude > 400f) continue;
    bool thinX = s.x < s.z;
    var toP = player.transform.position - p;
    var n = thinX ? new UnityEngine.Vector3(UnityEngine.Mathf.Sign(toP.x), 0f, 0f) : new UnityEngine.Vector3(0f, 0f, UnityEngine.Mathf.Sign(toP.z));
    var probe = new UnityEngine.Vector3(p.x, floorY + 1.5f, p.z) + n * 0.9f;
    int hits = UnityEngine.Physics.OverlapBoxNonAlloc(probe, new UnityEngine.Vector3(thinX ? 0.75f : 1.4f, 1.4f, thinX ? 1.4f : 0.75f), cols, UnityEngine.Quaternion.identity, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
    bool busy = false;
    for (int i = 0; i < hits; i++)
        if (cols[i].GetComponentInParent<Cozy.Grid.InteractiveObject>() != null || cols[i].GetComponentInParent<Cozy.Grid.StairPiece>() != null || cols[i].GetComponentInParent<Cozy.Grid.DoorPiece>() != null) { busy = true; break; }
    if (busy) continue;
    wall = gb; back = -n; wallThinX = thinX; break;
}
string tmp = System.IO.Path.Combine(UnityEngine.Application.temporaryCachePath, "dirt_probe.json");
try
{
    var mGable = T.GetMethod("GableUnderCursor", B);
    if (mGable == null) sb.Append("GableUnderCursor нет в домене — фронтон не проверен (⏳ после перекомпиляции); ");
    else
    {
        string gableRes = "фронтон: видимых нет, пропуск";
        foreach (var r in Cozy.Grid.RoofPiece.All)
        {
            if (r == null) continue;
            bool ridgeX = r.cellsX >= r.cellsZ;
            float width = (ridgeX ? r.cellsX : r.cellsZ) * r.cell, depth = (ridgeX ? r.cellsZ : r.cellsX) * r.cell;
            float apex = Cozy.Grid.RoofMesh.RidgeHeight(depth, r.style) - r.SlabDepth * 0.5f;
            bool done = false;
            for (int sgn = -1; sgn <= 1 && !done; sgn += 2)
            {
                var nrm = r.transform.right * sgn;
                var target = r.transform.position + nrm * (width * 0.5f + Cozy.Grid.RoofMesh.GableT * 0.5f) + UnityEngine.Vector3.up * (apex * 0.3f);
                var org = target + nrm * 4f + UnityEngine.Vector3.up * 2f;
                var gray = new UnityEngine.Ray(org, (target - org).normalized);
                float gd; float gs; UnityEngine.Vector3 gp;
                if (!r.GableRayHit(gray, out gd, out gs, out gp)) continue;
                var gargs = new object[] { gray, null, null };
                bool got = (bool)mGable.Invoke(gc, gargs);
                var gface = gargs[1];
                var node = r.transform.Find(sgn > 0 ? Cozy.Grid.RoofMesh.GablePlusName : Cozy.Grid.RoofMesh.GableMinusName);
                var host = got ? gface.GetType().GetField("host").GetValue(gface) as UnityEngine.Transform : null;
                float height = got ? (float)gface.GetType().GetField("height").GetValue(gface) : 0f;
                gableRes = "фронтон: луч → " + (got ? "грань, хозяин " + (host == node ? "узел фронтона" : "ЧУЖОЙ " + (host != null ? host.name : "—")) + ", высота " + height.ToString("F2") + " (конёк " + apex.ToString("F2") + ")" : "НЕТ");
                if (!got || host != node) { bad.Add("луч в фронтон не даёт грань узла фронтона (инв. 565)"); done = true; break; }
                if (UnityEngine.Mathf.Abs(height - apex) > 0.05f) bad.Add("высота грани фронтона " + height.ToString("F2") + " ≠ конёк " + apex.ToString("F2") + " (инв. 565)");
                var facesNow = fFaces.GetValue(gc) as System.Collections.IList;
                int before = facesNow.Count;
                fErase.SetValue(gc, false); fRadius.SetValue(gc, 0.5f);
                mStamp.Invoke(gc, new object[] { (UnityEngine.Vector3)gargs[2], gface });
                var index = fIndex.GetValue(gc) as System.Collections.Generic.Dictionary<string, int>;
                string gkey = (string)gface.GetType().GetField("key").GetValue(gface);
                int gi; int painted = 0;
                if (index.TryGetValue(gkey, out gi))
                {
                    var cur = fAtlas.GetValue(gc) as UnityEngine.Texture2D;
                    int tx = gi % 32, ty = gi / 32;
                    for (int z = 0; z < 16; z++) for (int x = 0; x < 16; x++) { var c = cur.GetPixel(tx * 16 + x, ty * 16 + z); if (c.r + c.g + c.b + c.a > 0.004f) painted++; }
                }
                gableRes += ", мазок: пикселей в плитке " + painted;
                if (painted == 0) bad.Add("мазок по фронтону не лёг в его плитку (инв. 565)");
                done = true;
            }
            if (done) break;
        }
        sb.Append(gableRes + "; ");
    }
    if (wall == null) sb.Append("стена: нет свободной нарисованной рядом, мазок пропущен; ");
    else
    {
        var wp = wall.transform.position; var ws = wall.transform.lossyScale;
        float half = (wallThinX ? ws.x : ws.z) * 0.5f;
        var target = new UnityEngine.Vector3(wp.x, floorY + 1.5f, wp.z) - back * (half + 0.02f);
        var worldDir = (back + UnityEngine.Vector3.down * 0.5f).normalized;
        // Камера под потолком своего этажа (19.10, «Свет (тест)»): в 4 м от стены она поднималась на 1,8 м над
        // точкой мазка — выше плиты перекрытия, и луч кисти бил в плиту, а не в стену («кисть не видит стену»).
        float camDist = UnityEngine.Mathf.Min(4f, (floorY + 2.75f - target.y) / -worldDir.y);
        cam.transform.SetPositionAndRotation(target - worldDir * camDist, UnityEngine.Quaternion.identity);
        var localDir = cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction;
        cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(localDir, worldDir);
        cam.transform.position = target - cam.ScreenPointToRay(new UnityEngine.Vector3(cursor.x, cursor.y, 0f)).direction * camDist;
        var args = new object[] { cam, mouse, null, null };
        bool found = (bool)mFace.Invoke(gc, args);
        if (!found) bad.Add("кисть не видит свободную стену " + wp.ToString("0.0") + " (режим стены)");
        else
        {
            var face = args[3];
            string key = (string)face.GetType().GetField("key").GetValue(face);
            fErase.SetValue(gc, false); fRadius.SetValue(gc, 0.5f); fVariant.SetValue(gc, 0);
            mStamp.Invoke(gc, new object[] { (UnityEngine.Vector3)args[2], face });
            var after = atlas.GetPixels32();
            var index = fIndex.GetValue(gc) as System.Collections.Generic.Dictionary<string, int>;
            int tile = index[key];
            int tpr = 512 / 16, tx = tile % tpr, ty = tile / tpr;
            int inside = 0, outside = 0;
            for (int i = 0; i < after.Length; i++)
            {
                if (after[i].r == snapshot[i].r && after[i].g == snapshot[i].g && after[i].b == snapshot[i].b && after[i].a == snapshot[i].a) continue;
                int px = i % 512, py = i / 512;
                if (px / 16 == tx && py / 16 == ty) inside++; else outside++;
            }
            sb.Append("мазок r0,5: пикселей в плитке " + inside + ", вне " + outside + "; ");
            if (inside == 0) bad.Add("мазок по стене не лёг в плитку грани");
            if (inside > 60) bad.Add("мазок r0,5 закрасил " + inside + " пикселей плитки — не по кисти, а вся грань (P1056)");
            if (outside > 0) bad.Add("мазок задел " + outside + " пикселей чужих плиток");
            var facesNow = fFaces.GetValue(gc) as System.Collections.IList;
            int facesNow1 = facesNow.Count;
            mSave.Invoke(gc, new object[] { tmp });
            mLoad.Invoke(gc, new object[] { tmp });
            var reloaded = fAtlas.GetValue(gc) as UnityEngine.Texture2D;
            var facesAfter = fFaces.GetValue(gc) as System.Collections.IList;
            int paintedBefore = 0, paintedAfter = 0;
            var rp = reloaded.GetPixels32();
            for (int i = 0; i < after.Length; i++) { if (after[i].r > 0) paintedBefore++; if (rp[i].r > 0) paintedAfter++; }
            sb.Append("сейв→загрузка: граней " + facesNow1 + "→" + facesAfter.Count + ", пикселей " + paintedBefore + "→" + paintedAfter + "; ");
            if (facesAfter.Count != facesNow1 || paintedAfter != paintedBefore) bad.Add("атлас стен после сейва и загрузки не совпал (P1057)");
            atlas = reloaded;
        }
    }
}
finally
{
    fErase.SetValue(gc, savedErase); fRadius.SetValue(gc, savedRadius); fVariant.SetValue(gc, savedVariant);
    cam.transform.SetPositionAndRotation(savedPos, savedRot);
    UnityEngine.Physics.SyncTransforms();
    if (createdHere) mRelease.Invoke(gc, null);
    else
    {
        var cur = fAtlas.GetValue(gc) as UnityEngine.Texture2D;
        if (cur != null) { cur.SetPixels32(snapshot); cur.Apply(); }
        var faces = fFaces.GetValue(gc) as System.Collections.IList;
        var index = fIndex.GetValue(gc) as System.Collections.Generic.Dictionary<string, int>;
        while (faces.Count > facesCountBefore)
        {
            var last = faces[faces.Count - 1];
            index.Remove((string)last.GetType().GetField("key").GetValue(last));
            faces.RemoveAt(faces.Count - 1);
        }
        for (int i = 0; i < faces.Count; i++)
        {
            var used = faces[i].GetType().GetField("used").GetValue(faces[i]) as bool[];
            int tx = i % 32, ty = i / 32;
            for (int v = 0; v < used.Length; v++) used[v] = false;
            for (int z = 0; z < 16; z++) for (int x = 0; x < 16; x++)
            {
                var c = snapshot[(ty * 16 + z) * 512 + tx * 16 + x];
                if (c.r > 0) used[0] = true; if (c.g > 0) used[1] = true; if (c.b > 0) used[2] = true; if (c.a > 0) used[3] = true;
            }
        }
    }
}
return (bad.Count == 0 ? "ОК" : "ПРОВАЛ: " + string.Join("; ", bad.ToArray())) + " | " + sb;
