"""Лес вокруг дома на текущем уровне (после посадки СРАЗУ сохраняет уровень): деревья с разрежением у двора, кусты,
трава, цветы куртинами, камни и валежник. Спавнит в play через мост — пока
Илья не сохранил уровень, всё откатывается выходом из play.
python3 forest_gen.py [--seed N] [--dry]

--yard — ДВОР вместо леса (Илья 2026-09-22: «рядом с домом прям нет
растительности»). Лесной проход двор намеренно обходит (`inYard`), поэтому у
самых стен пусто. Дворовый проход сажает ТОЛЬКО низкое — траву, цветы куртинами,
редкие кустики и палки, — держит чистой полосу у стен (`WALLGAP`) и круги перед
дверями, деревьев не ставит вовсе.
python3 forest_gen.py --yard [--seed N] [--dry]

--near — деревья и кусты ВПЛОТНУЮ к дому (Илья 2026-10-04: «вокруг дома прям
рядом добавь растительность, деревья и тд, только со стороны входа не надо»).
Кольцо 0,9–6 м от стен с трёх сторон; сторона входа — та стена, у которой
наружная дверь первого этажа, её полоса пропускается целиком (с углами).
Деревья в 2,2 м от стен и в 2,6 м друг от друга, кусты, камни и палки. НЕ
сохраняет уровень сам (`--save` — сохранить): Илья смотрит и сохраняет.
python3 forest_gen.py --near [--seed N] [--dry] [--save]"""
import json, subprocess, sys, pathlib
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
seed = 20260920
if '--seed' in sys.argv: seed = int(sys.argv[sys.argv.index('--seed') + 1])
dry = 'true' if '--dry' in sys.argv else 'false'
yard_mode = '--yard' in sys.argv
near_mode = '--near' in sys.argv
save = 'true' if '--save' in sys.argv else 'false'

yard_code = '''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var BFI = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var spawn = T.GetMethod("SpawnObject", BFI);
var groundOk = T.GetMethod("GrassGroundOk", BFI);
var groundY = T.GetMethod("GroundY", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
if (spawn == null || groundOk == null || groundY == null) return "нет методов";
bool DRY = DRYFLAG;
var rnd = new System.Random(SEEDVAL);

// ── габарит постройки
float hx0 = 1e9f, hx1 = -1e9f, hz0 = 1e9f, hz1 = -1e9f;
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.Rend == null) continue;
    if (gb.role != Cozy.Grid.GridRole.Wall && gb.role != Cozy.Grid.GridRole.Floor) continue;
    var b = gb.Rend.bounds;
    if (b.min.x < hx0) hx0 = b.min.x; if (b.max.x > hx1) hx1 = b.max.x;
    if (b.min.z < hz0) hz0 = b.min.z; if (b.max.z > hz1) hz1 = b.max.z;
}
float yard = 7f, wall = 0.9f;
float cx0 = hx0 - yard, cx1 = hx1 + yard, cz0 = hz0 - yard, cz1 = hz1 + yard;

// Двор — кольцо: внутри пояса, но НЕ на постройке и не впритык к стене.
System.Func<float, float, bool> inBand = (x, z) =>
    x > cx0 && x < cx1 && z > cz0 && z < cz1
    && !(x > hx0 - wall && x < hx1 + wall && z > hz0 - wall && z < hz1 + wall);

// ── что уже стоит во дворе: двери с запасом на проход, прочее — впритык
var doors = new System.Collections.Generic.List<UnityEngine.Vector3>();
var stuff = new System.Collections.Generic.List<UnityEngine.Vector3>();
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null) continue;
    var p = io.transform.position;
    if (p.x < cx0 - 3f || p.x > cx1 + 3f || p.z < cz0 - 3f || p.z > cz1 + 3f) continue;
    if (io.GetComponent<Cozy.Grid.DoorPiece>() != null) { doors.Add(p); continue; }
    // ⚠️ Двери в доме — это НЕ объекты, а куски стройки (`DoorPiece` на
    // PlacedBlocks), поэтому перебор объектов их не находил: первый сухой
    // прогон обошёл 0 дверей.
    if (io.Def.id != null && (io.Def.id.StartsWith("veg_") || io.Def.id.StartsWith("deco_"))) continue;
    stuff.Add(p);
}
foreach (var dp in UnityEngine.Object.FindObjectsByType<Cozy.Grid.DoorPiece>(UnityEngine.FindObjectsSortMode.None))
    if (dp != null) doors.Add(dp.transform.position);
System.Func<float, float, bool> clear = (x, z) =>
{
    foreach (var d in doors)
    {
        float dx = d.x - x, dz = d.z - z;
        if (dx * dx + dz * dz < 2.4f * 2.4f) return false;
    }
    foreach (var o in stuff)
    {
        float dx = o.x - x, dz = o.z - z;
        if (dx * dx + dz * dz < 1.0f * 1.0f) return false;
    }
    return true;
};

var planted = new System.Collections.Generic.List<UnityEngine.Vector2>();
System.Func<float, float, float, bool> far = (x, z, r) =>
{
    foreach (var q in planted) if ((q.x - x) * (q.x - x) + (q.y - z) * (q.y - z) < r * r) return false;
    return true;
};
var defs = new System.Collections.Generic.Dictionary<string, Cozy.Grid.ObjectDef>();
System.Func<string, Cozy.Grid.ObjectDef> def = id =>
{
    if (!defs.ContainsKey(id)) defs[id] = Cozy.Grid.FurnitureCatalog.ById(id);
    return defs[id];
};
int made = 0, tried = 0;
System.Func<string, float, float, float, bool> put = (id, x, z, r) =>
{
    tried++;
    if (!inBand(x, z) || !clear(x, z) || !far(x, z, r)) return false;
    var d = def(id);
    if (d == null) return false;
    float y = (float)groundY.Invoke(gc, new object[]{ x, z, 0f });
    var pos = new UnityEngine.Vector3(x, y, z);
    if (!(bool)groundOk.Invoke(gc, new object[]{ pos, 0f })) return false;
    planted.Add(new UnityEngine.Vector2(x, z));
    if (!DRY) spawn.Invoke(gc, new object[]{ d, pos, (float)(rnd.NextDouble() * 360.0) });
    made++;
    return true;
};
System.Func<float> rx = () => cx0 + (float)rnd.NextDouble() * (cx1 - cx0);
System.Func<float> rz = () => cz0 + (float)rnd.NextDouble() * (cz1 - cz0);

// ── редкие кустики и палки: объём, но не заросли
int bush = 0, stick = 0;
for (int a = 0; a < 5000 && bush < 24; a++)
{
    float x = rx(), z = rz();
    if (put("veg_bush" + (rnd.Next(5) == 0 ? "" : "_" + (rnd.Next(4) + 2)), x, z, 2.0f)) bush++;
}
for (int a = 0; a < 4000 && stick < 14; a++)
{
    float x = rx(), z = rz();
    int v = rnd.Next(5);
    if (put("deco_stick" + (v == 0 ? "" : "_" + (v + 1)), x, z, 1.2f)) stick++;
}
// ── цветы куртинами: у дома они уместнее, чем в чаще
int flow = 0;
for (int c = 0; c < 40 && flow < 150; c++)
{
    float cxp = rx(), czp = rz();
    int kind = rnd.Next(5) + 1;
    string fid = "veg_flower" + (kind == 1 ? "" : "_" + kind);
    float rad = 1.0f + (float)rnd.NextDouble() * 0.7f;
    for (int k = 0; k < 40 && flow < 150; k++)
    {
        double ang = rnd.NextDouble() * 6.2832; double rr = rnd.NextDouble() * rad;
        if (put(fid, cxp + (float)(System.Math.Cos(ang) * rr), czp + (float)(System.Math.Sin(ang) * rr), 0.35f)) flow++;
    }
}
// ── трава: основа двора, гуще к кромке пояса
int grass = 0;
for (int a = 0; a < 26000 && grass < 420; a++)
{
    float x = rx(), z = rz();
    bool tuft = rnd.Next(3) != 0;
    string gid = tuft ? "veg_grass_tuft" : "veg_grass_bush";
    int v = rnd.Next(tuft ? 4 : 3);
    if (v > 0) gid += "_" + (v + 1);
    if (put(gid, x, z, 0.5f)) grass++;
}
string saved = "";
if (!DRY)
{
    string lvl = Cozy.Grid.LevelIO.CurrentLevelName;
    Cozy.Grid.LevelIO.Save(lvl);
    saved = " || сохранён уровень " + lvl;
}
return "двор x " + cx0.ToString("F1") + ".." + cx1.ToString("F1") + " z " + cz0.ToString("F1") + ".." + cz1.ToString("F1")
  + " | дом x " + hx0.ToString("F1") + ".." + hx1.ToString("F1") + " z " + hz0.ToString("F1") + ".." + hz1.ToString("F1")
  + " | дверей обойдено " + doors.Count + ", вещей обойдено " + stuff.Count
  + " || трава " + grass + ", цветы " + flow + ", кусты " + bush + ", палки " + stick
  + " || всего " + made + " из " + tried + " попыток" + (DRY ? " (СУХОЙ ПРОГОН)" : saved);
'''.replace('SEEDVAL', str(seed)).replace('DRYFLAG', dry)

code = '''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var BFI = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var spawn = T.GetMethod("SpawnObject", BFI);
var groundOk = T.GetMethod("GrassGroundOk", BFI);
var groundY = T.GetMethod("GroundY", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
if (spawn == null || groundOk == null || groundY == null) return "нет методов: spawn=" + (spawn != null) + " ok=" + (groundOk != null) + " y=" + (groundY != null);
bool DRY = DRYFLAG;
var rnd = new System.Random(SEEDVAL);

// ── двор: габарит постройки плюс запас
float hx0 = 1e9f, hx1 = -1e9f, hz0 = 1e9f, hz1 = -1e9f;
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.Rend == null) continue;
    if (gb.role != Cozy.Grid.GridRole.Wall && gb.role != Cozy.Grid.GridRole.Floor) continue;
    var b = gb.Rend.bounds;
    if (b.min.x < hx0) hx0 = b.min.x; if (b.max.x > hx1) hx1 = b.max.x;
    if (b.min.z < hz0) hz0 = b.min.z; if (b.max.z > hz1) hz1 = b.max.z;
}
float yard = 7f, belt = 30f;
float cx0 = hx0 - yard, cx1 = hx1 + yard, cz0 = hz0 - yard, cz1 = hz1 + yard;
float fx0 = cx0 - belt, fx1 = cx1 + belt, fz0 = cz0 - belt, fz1 = cz1 + belt;

System.Func<float, float, bool> inYard = (x, z) => x > cx0 && x < cx1 && z > cz0 && z < cz1;
// Плотность растёт от двора к чаще: у кромки редко, дальше 12 м — полная.
System.Func<float, float, float> thick = (x, z) =>
{
    float dx = UnityEngine.Mathf.Max(0f, UnityEngine.Mathf.Max(cx0 - x, x - cx1));
    float dz = UnityEngine.Mathf.Max(0f, UnityEngine.Mathf.Max(cz0 - z, z - cz1));
    float d = UnityEngine.Mathf.Sqrt(dx * dx + dz * dz);
    return UnityEngine.Mathf.Clamp01(d / 12f);
};

var defs = new System.Collections.Generic.Dictionary<string, Cozy.Grid.ObjectDef>();
System.Func<string, Cozy.Grid.ObjectDef> def = id =>
{
    if (!defs.ContainsKey(id)) defs[id] = Cozy.Grid.FurnitureCatalog.ById(id);
    return defs[id];
};

// ── сетка занятости: разрежение без перебора всех точек
int GS = 128; float GC_ = (fx1 - fx0) / GS;
var buckets = new System.Collections.Generic.List<UnityEngine.Vector2>[GS * GS];
System.Func<float, float, int> cellOf = (x, z) =>
{
    int i = UnityEngine.Mathf.Clamp((int)((x - fx0) / GC_), 0, GS - 1);
    int j = UnityEngine.Mathf.Clamp((int)((z - fz0) / ((fz1 - fz0) / GS)), 0, GS - 1);
    return j * GS + i;
};
System.Func<float, float, float, bool> far = (x, z, r) =>
{
    int i0 = UnityEngine.Mathf.Clamp((int)((x - r - fx0) / GC_), 0, GS - 1);
    int i1 = UnityEngine.Mathf.Clamp((int)((x + r - fx0) / GC_), 0, GS - 1);
    int j0 = UnityEngine.Mathf.Clamp((int)((z - r - fz0) / ((fz1 - fz0) / GS)), 0, GS - 1);
    int j1 = UnityEngine.Mathf.Clamp((int)((z + r - fz0) / ((fz1 - fz0) / GS)), 0, GS - 1);
    for (int j = j0; j <= j1; j++)
      for (int i = i0; i <= i1; i++)
      {
          var lst = buckets[j * GS + i];
          if (lst == null) continue;
          foreach (var p in lst) if ((p.x - x) * (p.x - x) + (p.y - z) * (p.y - z) < r * r) return false;
      }
    return true;
};
System.Action<float, float> mark = (x, z) =>
{
    int k = cellOf(x, z);
    if (buckets[k] == null) buckets[k] = new System.Collections.Generic.List<UnityEngine.Vector2>();
    buckets[k].Add(new UnityEngine.Vector2(x, z));
};

int made = 0, tried = 0;
System.Func<string, float, float, float, bool> put = (id, x, z, r) =>
{
    tried++;
    var d = def(id);
    if (d == null) return false;
    float y = (float)groundY.Invoke(gc, new object[]{ x, z, 0f });
    var pos = new UnityEngine.Vector3(x, y, z);
    if (!(bool)groundOk.Invoke(gc, new object[]{ pos, 0f })) return false;
    if (!far(x, z, r)) return false;
    mark(x, z);
    if (!DRY) spawn.Invoke(gc, new object[]{ d, pos, (float)(rnd.NextDouble() * 360.0) });
    made++;
    return true;
};
System.Func<float> rx = () => fx0 + (float)rnd.NextDouble() * (fx1 - fx0);
System.Func<float> rz = () => fz0 + (float)rnd.NextDouble() * (fz1 - fz0);

// ── деревья: 5 видов, шаг 2.4–3.4 м, у двора реже
int trees = 0;
for (int a = 0; a < 26000 && trees < 430; a++)
{
    float x = rx(), z = rz();
    if (inYard(x, z)) continue;
    float th = thick(x, z);
    if (rnd.NextDouble() > 0.25 + 0.75 * th) continue;
    if (put("veg_tree" + (rnd.Next(5) == 0 ? "" : "_" + (rnd.Next(4) + 2)), x, z, 2.4f + (float)rnd.NextDouble() * 1.0f)) trees++;
}
// ── кусты подлеском, ближе к прогалинам
int bush = 0;
for (int a = 0; a < 9000 && bush < 190; a++)
{
    float x = rx(), z = rz();
    if (inYard(x, z)) continue;
    if (put("veg_bush" + (rnd.Next(5) == 0 ? "" : "_" + (rnd.Next(4) + 2)), x, z, 1.5f)) bush++;
}
// ── валежник и камни: редко, для разнообразия
int rock = 0, fallen = 0, log = 0, stick = 0;
for (int a = 0; a < 6000 && rock < 46; a++) { float x = rx(), z = rz(); int v = rnd.Next(12); if (!inYard(x, z) && put("veg_rock" + (v == 0 ? "" : "_" + (v + 1)), x, z, 1.1f)) rock++; }
for (int a = 0; a < 4000 && fallen < 13; a++) { float x = rx(), z = rz(); int v = rnd.Next(3); if (!inYard(x, z) && put("veg_fallen_tree" + (v == 0 ? "" : "_" + (v + 1)), x, z, 2.2f)) fallen++; }
for (int a = 0; a < 4000 && log < 16; a++) { float x = rx(), z = rz(); if (!inYard(x, z) && put("veg_log", x, z, 1.6f)) log++; }
for (int a = 0; a < 6000 && stick < 55; a++) { float x = rx(), z = rz(); int v = rnd.Next(5); if (!inYard(x, z) && put("deco_stick" + (v == 0 ? "" : "_" + (v + 1)), x, z, 0.8f)) stick++; }
// ── цветы куртинами в просветах
int flow = 0;
for (int c = 0; c < 70 && flow < 260; c++)
{
    float cxp = rx(), czp = rz();
    if (inYard(cxp, czp)) continue;
    int kind = rnd.Next(5) + 1;
    string fid = "veg_flower" + (kind == 1 ? "" : "_" + kind);
    float rad = 1.2f + (float)rnd.NextDouble() * 0.8f;
    int want = 6 + rnd.Next(14);
    for (int k = 0; k < want * 4 && flow < 260; k++)
    {
        double ang = rnd.NextDouble() * 6.2832; double rr = rnd.NextDouble() * rad;
        if (put(fid, cxp + (float)(System.Math.Cos(ang) * rr), czp + (float)(System.Math.Sin(ang) * rr), 0.4f)) flow++;
    }
}
// ── трава: гуще у двора, где игрок ходит
int grass = 0;
for (int a = 0; a < 30000 && grass < 1300; a++)
{
    float x = rx(), z = rz();
    if (inYard(x, z)) continue;
    bool tuft = rnd.Next(3) != 0;
    string gid = tuft ? "veg_grass_tuft" : "veg_grass_bush";
    int v = rnd.Next(tuft ? 4 : 3);
    if (v > 0) gid += "_" + (v + 1);
    if (put(gid, x, z, 0.55f)) grass++;
}
string saved = "";
if (!DRY)
{
    string lvl = Cozy.Grid.LevelIO.CurrentLevelName;
    // Сохраняем ТЕМ ЖЕ вызовом: перезапуск play или доменная перезагрузка от
    // компиляции стирают всё, что не на диске (поймано 20.09 — первый лес
    // пропал целиком).
    Cozy.Grid.LevelIO.Save(lvl);
    saved = " || сохранён уровень " + lvl;
}
return "двор x " + cx0.ToString("F1") + ".." + cx1.ToString("F1") + " z " + cz0.ToString("F1") + ".." + cz1.ToString("F1")
  + " | лес x " + fx0.ToString("F1") + ".." + fx1.ToString("F1") + " z " + fz0.ToString("F1") + ".." + fz1.ToString("F1")
  + " || деревья " + trees + ", кусты " + bush + ", цветы " + flow + ", трава " + grass
  + ", камни " + rock + ", валежник " + fallen + ", брёвна " + log + ", палки " + stick
  + " || всего " + made + " из " + tried + " попыток" + (DRY ? " (СУХОЙ ПРОГОН)" : saved);
'''.replace('SEEDVAL', str(seed)).replace('DRYFLAG', dry)

near_code = '''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.GridCursor>();
if (gc == null) return "нет GridCursor";
var T = typeof(Cozy.Grid.GridCursor);
var BFI = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var spawn = T.GetMethod("SpawnObject", BFI);
var groundOk = T.GetMethod("GrassGroundOk", BFI);
var groundY = T.GetMethod("GroundY", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
if (spawn == null || groundOk == null || groundY == null) return "нет методов";
bool DRY = DRYFLAG, SAVE = SAVEFLAG;
var rnd = new System.Random(SEEDVAL);

float hx0 = 1e9f, hx1 = -1e9f, hz0 = 1e9f, hz1 = -1e9f;
foreach (var gb in Cozy.Grid.GridBlock.All)
{
    if (gb == null || gb.Rend == null) continue;
    if (gb.role != Cozy.Grid.GridRole.Wall && gb.role != Cozy.Grid.GridRole.Floor) continue;
    var b = gb.Rend.bounds;
    if (b.min.x < hx0) hx0 = b.min.x; if (b.max.x > hx1) hx1 = b.max.x;
    if (b.min.z < hz0) hz0 = b.min.z; if (b.max.z > hz1) hz1 = b.max.z;
}
float ring = 6f, wall = 0.9f, treeWall = 2.2f;

// ── сторона входа: наружная дверь первого этажа у края габарита
var doors = new System.Collections.Generic.List<UnityEngine.Vector3>();
foreach (var dp in UnityEngine.Object.FindObjectsByType<Cozy.Grid.DoorPiece>(UnityEngine.FindObjectsSortMode.None))
    if (dp != null) doors.Add(dp.transform.position);
string entrance = "";
foreach (var d in doors)
{
    if (d.y > 1f) continue;
    if (UnityEngine.Mathf.Abs(d.x - hx0) < 0.7f) entrance += "W";
    else if (UnityEngine.Mathf.Abs(d.x - hx1) < 0.7f) entrance += "E";
    else if (UnityEngine.Mathf.Abs(d.z - hz0) < 0.7f) entrance += "S";
    else if (UnityEngine.Mathf.Abs(d.z - hz1) < 0.7f) entrance += "N";
}
System.Func<float, float, bool> entranceSide = (x, z) =>
    entrance.Contains("W") && x < hx0 || entrance.Contains("E") && x > hx1
    || entrance.Contains("S") && z < hz0 || entrance.Contains("N") && z > hz1;
System.Func<float, float, float> wallGap = (x, z) =>
{
    float dx = UnityEngine.Mathf.Max(0f, UnityEngine.Mathf.Max(hx0 - x, x - hx1));
    float dz = UnityEngine.Mathf.Max(0f, UnityEngine.Mathf.Max(hz0 - z, z - hz1));
    return UnityEngine.Mathf.Sqrt(dx * dx + dz * dz);
};

var stuff = new System.Collections.Generic.List<UnityEngine.Vector2>();
var planted = new System.Collections.Generic.List<UnityEngine.Vector3>();
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null) continue;
    var p = io.transform.position;
    if (wallGap(p.x, p.z) > ring + 3f) continue;
    if (io.Def.id != null && (io.Def.id.StartsWith("veg_grass") || io.Def.id.StartsWith("veg_flower") || io.Def.id.StartsWith("veg_pebble"))) continue;
    if (io.Def.id != null && (io.Def.id.StartsWith("veg_tree") || io.Def.id.StartsWith("veg_bush")))
        planted.Add(new UnityEngine.Vector3(p.x, p.z, io.Def.id.StartsWith("veg_tree") ? 2.6f : 1.4f));
    else stuff.Add(new UnityEngine.Vector2(p.x, p.z));
}
int before = planted.Count;
System.Func<float, float, float, bool> free = (x, z, r) =>
{
    foreach (var d in doors) if ((d.x - x) * (d.x - x) + (d.z - z) * (d.z - z) < 2.4f * 2.4f) return false;
    foreach (var o in stuff) if ((o.x - x) * (o.x - x) + (o.y - z) * (o.y - z) < 1.2f * 1.2f) return false;
    foreach (var q in planted)
    {
        float rr = UnityEngine.Mathf.Max(r, q.z);
        if ((q.x - x) * (q.x - x) + (q.y - z) * (q.y - z) < rr * rr) return false;
    }
    return true;
};
var defs = new System.Collections.Generic.Dictionary<string, Cozy.Grid.ObjectDef>();
var log = new System.Text.StringBuilder();
int made = 0;
System.Func<string, float, float, float, float, bool> put = (id, x, z, r, minWall) =>
{
    float g = wallGap(x, z);
    if (g < minWall || g > ring || entranceSide(x, z) || !free(x, z, r)) return false;
    if (!defs.ContainsKey(id)) defs[id] = Cozy.Grid.FurnitureCatalog.ById(id);
    var d = defs[id];
    if (d == null) return false;
    float y = (float)groundY.Invoke(gc, new object[]{ x, z, 0f });
    var pos = new UnityEngine.Vector3(x, y, z);
    if (!(bool)groundOk.Invoke(gc, new object[]{ pos, 0f })) return false;
    planted.Add(new UnityEngine.Vector3(x, z, r));
    if (!DRY) spawn.Invoke(gc, new object[]{ d, pos, (float)(rnd.NextDouble() * 360.0) });
    log.Append(id + "@" + x.ToString("F2") + "," + z.ToString("F2") + ";");
    made++;
    return true;
};
System.Func<float> rx = () => hx0 - ring + (float)rnd.NextDouble() * (hx1 - hx0 + ring * 2f);
System.Func<float> rz = () => hz0 - ring + (float)rnd.NextDouble() * (hz1 - hz0 + ring * 2f);

int trees = 0, bush = 0, rock = 0, stick = 0;
for (int a = 0; a < 20000 && trees < 16; a++)
    if (put("veg_tree" + (rnd.Next(5) == 0 ? "" : "_" + (rnd.Next(4) + 2)), rx(), rz(), 2.6f + (float)rnd.NextDouble() * 0.6f, treeWall)) trees++;
for (int a = 0; a < 20000 && bush < 26; a++)
    if (put("veg_bush" + (rnd.Next(5) == 0 ? "" : "_" + (rnd.Next(4) + 2)), rx(), rz(), 1.3f, wall)) bush++;
for (int a = 0; a < 8000 && rock < 6; a++) { int v = rnd.Next(12); if (put("veg_rock" + (v == 0 ? "" : "_" + (v + 1)), rx(), rz(), 1.0f, wall)) rock++; }
for (int a = 0; a < 8000 && stick < 8; a++) { int v = rnd.Next(5); if (put("deco_stick" + (v == 0 ? "" : "_" + (v + 1)), rx(), rz(), 0.8f, wall)) stick++; }

string saved = "";
if (!DRY && SAVE)
{
    string lvl = Cozy.Grid.LevelIO.CurrentLevelName;
    Cozy.Grid.LevelIO.Save(lvl);
    saved = " || сохранён уровень " + lvl;
}
return "дом x " + hx0.ToString("F1") + ".." + hx1.ToString("F1") + " z " + hz0.ToString("F1") + ".." + hz1.ToString("F1")
  + " | вход: " + (entrance == "" ? "не найден" : entrance) + " | было рядом деревьев и кустов " + before
  + " || деревья " + trees + ", кусты " + bush + ", камни " + rock + ", палки " + stick + " — всего " + made
  + (DRY ? " (СУХОЙ ПРОГОН)" : SAVE ? saved : " (НЕ сохранено)") + " || " + log;
'''.replace('SEEDVAL', str(seed)).replace('DRYFLAG', dry).replace('SAVEFLAG', save)

out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": near_code if near_mode else yard_code if yard_mode else code})],
                     capture_output=True, text=True, timeout=900, cwd=PROJECT)
text = out.stdout.strip(); line = text.splitlines()[-1] if text else '{}'
try:
    d = json.loads(line); print((d.get('data') or {}).get('result') or d)
except Exception:
    print(text[-700:], out.stderr[-300:])
