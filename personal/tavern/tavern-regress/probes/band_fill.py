"""Добор леса в прямоугольной полосе текущего уровня до плотности существующего леса (Илья 29.10,
«Котедж 104»: «мало растительности вокруг дороги — добавь леса, заполни пробелы все рядом с
дорогой»). Состав как в лесу 104 (трава 30 %, куст травы 15 %, дерево 13 %, цветы 12 %, куст 9 %,
галька 8 %, камень 5 %, папоротник 3 %, ель 2 %, грибы 2 %, бревно и валежник по 0,4 %), по клеткам
~9×10 м добирает до нормы с учётом того, что уже стоит; попарный зазор — меньший из радиусов видов
(дерево от дерева 2,8 м, трава под деревом 0,55), склон и вода — GrassGroundOk. Спавнит в play через
мост, НЕ сохраняет: Илья смотрит и сохраняет сам.
python3 band_fill.py X0 X1 Z0 Z1 [--clear x0 x1 z0 z1] [--density 25] [--seed N] [--dry]
Пример 29.10: band_fill.py -112 -76 -76 134 --clear -84 -74 -9 5   (полоса между кромкой карты и
западной обочиной дороги, двор остановки с мусоркой чистый) → 1 512 растений."""
import json, subprocess, sys, pathlib
CODE = r'''
// Лес вдоль дороги «Котеджа 104» (Илья 29.10: «мало растительности вокруг дороги — добавь леса,
// заполни пробелы все рядом с дорогой»): полоса x −112…−76 между кромкой карты и западной
// обочиной, по всей высоте дороги z −76…134. Состав и плотность — как в существующем лесу
// (25 растений на 100 м²: трава 30 %, куст травы 15 %, дерево 13 %, цветы 12 %, куст 9 %,
// галька 8 %, камень 5 %, папоротник 3 %, ель 2 %, грибы 2 %, бревно/валежник по 0,4 %).
// Добирает по клеткам 10×10 м до нормы с учётом того, что уже стоит; дорога, остановка с
// мусоркой и спавн не трогаются. Спавн в play — Илья смотрит и сохраняет.
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

float X0 = BX0F, X1 = BX1F, Z0 = BZ0F, Z1 = BZ1F;
// Остановка (-78.9..-75.5, -4.6..1.1), расписание, мусорка (-79.5..-77.9, -5.5..-4.7): чистый двор.
System.Func<float, float, bool> clear = (x, z) => CLEARRECT;
System.Func<float, float, bool> inBand = (x, z) => x >= X0 && x <= X1 && z >= Z0 && z <= Z1 && !clear(x, z);

// ── что уже стоит: занятость по сетке 1 м, плюс счёт по клеткам 10×10 и видам
int CW = (int)((X1 - X0) + 16), CH = (int)((Z1 - Z0) + 16); float BX0 = X0 - 8f, BZ0 = Z0 - 8f;
var buckets = new System.Collections.Generic.List<UnityEngine.Vector3>[CW * CH];
System.Action<float, float, float> mark = (x, z, r) =>
{
    int i = UnityEngine.Mathf.Clamp((int)(x - BX0), 0, CW - 1), j = UnityEngine.Mathf.Clamp((int)(z - BZ0), 0, CH - 1);
    if (buckets[j * CW + i] == null) buckets[j * CW + i] = new System.Collections.Generic.List<UnityEngine.Vector3>();
    buckets[j * CW + i].Add(new UnityEngine.Vector3(x, z, r));
};
// Свободно, если до каждого соседа не ближе МЕНЬШЕГО из радиусов: дерево от дерева 2,8 м, трава под деревом — 0,55.
System.Func<float, float, float, bool> far = (x, z, r) =>
{
    int i0 = UnityEngine.Mathf.Clamp((int)(x - r - 4f - BX0), 0, CW - 1), i1 = UnityEngine.Mathf.Clamp((int)(x + r + 4f - BX0), 0, CW - 1);
    int j0 = UnityEngine.Mathf.Clamp((int)(z - r - 4f - BZ0), 0, CH - 1), j1 = UnityEngine.Mathf.Clamp((int)(z + r + 4f - BZ0), 0, CH - 1);
    for (int j = j0; j <= j1; j++)
        for (int i = i0; i <= i1; i++)
        {
            var lst = buckets[j * CW + i];
            if (lst == null) continue;
            foreach (var p in lst) { float d = UnityEngine.Mathf.Min(r, p.z); if ((p.x - x) * (p.x - x) + (p.y - z) * (p.y - z) < d * d) return false; }
        }
    return true;
};
int NX = UnityEngine.Mathf.Max(1, UnityEngine.Mathf.RoundToInt((X1 - X0) / 9f)), NZ = UnityEngine.Mathf.Max(1, UnityEngine.Mathf.RoundToInt((Z1 - Z0) / 10f)); // клетки ~9×10 м
float CX = (X1 - X0) / NX, CZ = (Z1 - Z0) / NZ;
string[] kinds = { "veg_grass_tuft", "veg_grass_bush", "veg_tree", "veg_flower", "veg_bush", "veg_pebble", "veg_rock", "veg_fern", "veg_spruce", "veg_mushroom", "veg_log", "veg_fallen_tree" };
float[] share = { 0.30f, 0.15f, 0.13f, 0.12f, 0.09f, 0.08f, 0.05f, 0.03f, 0.02f, 0.02f, 0.004f, 0.004f };
float[] radius = { 0.55f, 0.6f, 2.8f, 0.4f, 1.5f, 0.5f, 1.1f, 0.8f, 2.8f, 0.5f, 1.6f, 2.2f };
int[] variants = { 4, 3, 5, 5, 5, 6, 12, 3, 3, 4, 1, 3 };
var have = new int[NX * NZ * kinds.Length];
System.Func<string, int> kindOf = id =>
{
    for (int k = kinds.Length - 1; k >= 0; k--) if (id == kinds[k] || id.StartsWith(kinds[k] + "_")) { if (kinds[k] == "veg_tree" && id.StartsWith("veg_tree_")) return 2; return k; }
    return -1;
};
int existing = 0;
foreach (var io in Cozy.Grid.InteractiveObject.All)
{
    if (io == null || io.Def == null) continue;
    var p = io.transform.position;
    if (p.x < X0 - 8f || p.x > X1 + 8f || p.z < Z0 - 8f || p.z > Z1 + 8f) continue;
    string id = io.Def.id;
    int k = id.StartsWith("veg_") ? kindOf(id) : -1;
    float r = k >= 0 ? radius[k] : (id.StartsWith("deco_stick") ? 0.8f : 2.5f);
    if (id.StartsWith("env_highway")) r = 1.2f;
    mark(p.x, p.z, r);
    if (k >= 0 && inBand(p.x, p.z)) { int ci = UnityEngine.Mathf.Clamp((int)((p.x - X0) / CX), 0, NX - 1), cj = UnityEngine.Mathf.Clamp((int)((p.z - Z0) / CZ), 0, NZ - 1); have[(cj * NX + ci) * kinds.Length + k]++; existing++; }
}

var defs = new System.Collections.Generic.Dictionary<string, Cozy.Grid.ObjectDef>();
System.Func<string, Cozy.Grid.ObjectDef> def = id => { if (!defs.ContainsKey(id)) defs[id] = Cozy.Grid.FurnitureCatalog.ById(id); return defs[id]; };
System.Func<int, string> pick = k =>
{
    int v = rnd.Next(variants[k]);
    if (kinds[k] == "veg_tree") return v == 0 ? "veg_tree" : "veg_tree_" + (v + 1);
    return v == 0 ? kinds[k] : kinds[k] + "_" + (v + 1);
};
int made = 0, tried = 0, slope = 0, busy = 0;
var madeBy = new int[kinds.Length];
System.Func<int, float, float, bool> put = (k, x, z) =>
{
    tried++;
    if (!inBand(x, z)) return false;
    var d = def(pick(k));
    if (d == null) return false;
    float y = (float)groundY.Invoke(gc, new object[] { x, z, 0f });
    var pos = new UnityEngine.Vector3(x, y, z);
    if (!(bool)groundOk.Invoke(gc, new object[] { pos, 0f })) { slope++; return false; }
    if (!far(x, z, radius[k])) { busy++; return false; }
    mark(x, z, radius[k]);
    if (!DRY) spawn.Invoke(gc, new object[] { d, pos, (float)(rnd.NextDouble() * 360.0) });
    made++; madeBy[k]++;
    return true;
};
float target = DENSITY * CX * CZ / 100f;
// Сначала крупное (деревья, ели, кусты, валежник), потом мелочь в промежутки; цветы и грибы — куртинами.
int[] order = { 2, 8, 4, 11, 10, 6, 7, 1, 0, 5, 3, 9 };
for (int cj = 0; cj < NZ; cj++)
    for (int ci = 0; ci < NX; ci++)
    {
        float cx0 = X0 + ci * CX, cz0 = Z0 + cj * CZ;
        foreach (int k in order)
        {
            float wantF = target * share[k]; int want = (int)wantF + (rnd.NextDouble() < wantF - (int)wantF ? 1 : 0) - have[(cj * NX + ci) * kinds.Length + k];
                        if (want <= 0) continue;
            if (k == 3 || k == 9)
            {
                // куртины: 1–2 центра на клетку
                int got = 0;
                for (int c = 0; c < 3 && got < want; c++)
                {
                    float cxp = cx0 + (float)rnd.NextDouble() * CX, czp = cz0 + (float)rnd.NextDouble() * CZ;
                    float rad = k == 3 ? 1.2f + (float)rnd.NextDouble() * 0.8f : 0.6f + (float)rnd.NextDouble() * 0.4f;
                    for (int a = 0; a < want * 4 && got < want; a++)
                    {
                        double ang = rnd.NextDouble() * 6.2832, rr = rnd.NextDouble() * rad;
                        if (put(k, cxp + (float)(System.Math.Cos(ang) * rr), czp + (float)(System.Math.Sin(ang) * rr))) got++;
                    }
                }
                continue;
            }
            int got2 = 0;
            for (int a = 0; a < want * 12 && got2 < want; a++)
                if (put(k, cx0 + (float)rnd.NextDouble() * CX, cz0 + (float)rnd.NextDouble() * CZ)) got2++;
        }
    }
var sb = new System.Text.StringBuilder();
sb.Append("полоса x ").Append(X0).Append("..").Append(X1).Append(" z ").Append(Z0).Append("..").Append(Z1).Append(" (").Append((X1 - X0) * (Z1 - Z0) / 100f).Append(" соток), было растений ").Append(existing).Append(", норма ").Append(UnityEngine.Mathf.RoundToInt(target * NX * NZ)).Append(" || посажено ").Append(made).Append(" из ").Append(tried).Append(" попыток (склон/вода ").Append(slope).Append(", занято ").Append(busy).Append("): ");
for (int k = 0; k < kinds.Length; k++) if (madeBy[k] > 0) sb.Append(kinds[k].Substring(4)).Append(' ').Append(madeBy[k]).Append(", ");
sb.Append(DRY ? "(СУХОЙ ПРОГОН)" : "— в мире, не сохранено");
return sb.ToString();
'''

MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
a = [x for x in sys.argv[1:] if not x.startswith('--')]
if len(a) < 4:
    print(__doc__); sys.exit(1)
x0, x1, z0, z1 = [float(v) for v in a[:4]]
clear = 'false'
if '--clear' in sys.argv:
    i = sys.argv.index('--clear'); cx0, cx1, cz0, cz1 = [float(v) for v in sys.argv[i + 1:i + 5]]
    clear = 'x > %sf && x < %sf && z > %sf && z < %sf' % (cx0, cx1, cz0, cz1)
density = float(sys.argv[sys.argv.index('--density') + 1]) if '--density' in sys.argv else 25.0
seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 20261029
dry = 'true' if '--dry' in sys.argv else 'false'
code = CODE.replace('BX0F', '%sf' % x0).replace('BX1F', '%sf' % x1).replace('BZ0F', '%sf' % z0).replace('BZ1F', '%sf' % z1)
code = code.replace('CLEARRECT', clear).replace('SEEDVAL', str(seed)).replace('DENSITY', '%sf' % density).replace('DRYFLAG', dry)
out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({'action': 'execute', 'code': code})],
                     capture_output=True, text=True, timeout=600, cwd=PROJECT)
line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-500:]
try:
    d = json.loads(line); print((d.get('data') or {}).get('result') or d)
except Exception:
    print(line[:1500])
