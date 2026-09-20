"""Лес вокруг дома на текущем уровне (после посадки СРАЗУ сохраняет уровень): деревья с разрежением у двора, кусты,
трава, цветы куртинами, камни и валежник. Спавнит в play через мост — пока
Илья не сохранил уровень, всё откатывается выходом из play.
python3 forest_gen.py [--seed N] [--dry]"""
import json, subprocess, sys, pathlib
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
seed = 20260920
if '--seed' in sys.argv: seed = int(sys.argv[sys.argv.index('--seed') + 1])
dry = 'true' if '--dry' in sys.argv else 'false'

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

out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                     capture_output=True, text=True, timeout=900, cwd=PROJECT)
text = out.stdout.strip(); line = text.splitlines()[-1] if text else '{}'
try:
    d = json.loads(line); print((d.get('data') or {}).get('result') or d)
except Exception:
    print(text[-700:], out.stderr[-300:])
