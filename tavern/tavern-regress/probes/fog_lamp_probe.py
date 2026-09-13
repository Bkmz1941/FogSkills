"""Луч фонаря раздвигает туман (инвариант 177): под конусом света клуб прозрачнее, вне луча — как был.

python3 fog_lamp_probe.py     только в СВОЁМ play: ставит игрока в 3 м от ближайшей клетки тумана лицом к ней,
                              выбирает фонарь в хотбаре (через _activeQuick + SyncHand, иначе хотбар вернёт руку
                              за четверть секунды), ждёт кадр, читает глобали конуса и рендерит кадр дважды —
                              «Растворяет туман днём/ночью» 100 % и 0 %; считает пиксели, которые потемнели (туман ушёл).
                              Возвращает хотбар и игрока. Второй замер — игрок ВНУТРИ клетки тумана, где поверх работает пелена «Ничего не видно»
                              (`DarknessVeil`): та же A/B, пелена обязана открыться под лучом. Красное: конус в шейдере
                              нулевой при горящем фонаре или ни один пиксель не изменился снаружи либо изнутри.
Замер 13.09 на Test #1: конус начало у линзы, дальность 15, tan 0.52; изменилось 19 594 пикселя из 518 400, все потемнели.
"""
import json, re, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
def call(code):
    code = '\n'.join(l for l in code.splitlines() if l.strip() and not l.strip().startswith('//'))
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})], capture_output=True, text=True, timeout=180, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line); return (d.get('data') or {}).get('result') or line[:800]
    except Exception: return line[:800]
SETUP = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I; var player = Cozy.Grid.PlayerRef.GameObject;
var fogs = UnityEngine.Object.FindObjectsByType<Cozy.Grid.FogAnim>(UnityEngine.FindObjectsSortMode.None);
if (fogs.Length == 0) return "на уровне нет тумана";
UnityEngine.Vector3 best = UnityEngine.Vector3.zero; float bd = float.MaxValue;
foreach (var f in fogs) { float d = UnityEngine.Vector3.Distance(f.transform.position, player.transform.position); if (d < bd) { bd = d; best = f.transform.position; } }
var pp = player.transform.position;
var away = pp - best; away.y = 0f; if (away.magnitude < 0.1f) away = UnityEngine.Vector3.back; away.Normalize();
var stand = best + away * 3.0f;
gc.TeleportPlayerTo(new UnityEngine.Vector3(stand.x, gc.GroundY(stand.x, stand.z, 0f), stand.z));
player.transform.rotation = UnityEngine.Quaternion.LookRotation(-away, UnityEngine.Vector3.up);
UnityEngine.Physics.SyncTransforms();
var rig = player.GetComponent<Cozy.Character.FlashlightRig>();
if (rig == null) return "нет FlashlightRig";
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var th = typeof(Tavern.UI.HudUI);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
var fQuick = th.GetField("_activeQuick", bf); var mAt = th.GetMethod("PocketPlacedAt", bf); var mSync = th.GetMethod("SyncHand", bf);
if (hud == null || fQuick == null || mAt == null || mSync == null) return "нет доступа к хотбару";
int wasQuick = (int)fQuick.GetValue(hud); int torchSlot = -1;
for (int i = 0; i < 5 && torchSlot < 0; i++) { var placed = mAt.Invoke(hud, new object[] { i }); if (placed == null) continue; var def = placed.GetType().GetField("def").GetValue(placed) as Cozy.Grid.ItemDef; if (def != null && Cozy.Grid.Items.IsFlashlight(def)) torchSlot = i; }
if (torchSlot < 0) return "в карманах нет фонаря";
fQuick.SetValue(hud, torchSlot); mSync.Invoke(hud, null);
return "туман @" + best.ToString("F1") + " клеток " + fogs.Length + " | игрок был " + pp.ToString("F2") + " → стоит " + player.transform.position.ToString("F2") + " | фонарь в ячейке " + torchSlot + " (было " + wasQuick + "): held=" + rig.Held + " lit=" + rig.Lit + "|" + pp.x.ToString("R") + "|" + pp.y.ToString("R") + "|" + pp.z.ToString("R") + "|" + wasQuick;
'''
MEASURE = r'''
var cam = UnityEngine.Camera.main;
var cone = UnityEngine.Shader.GetGlobalVector("_FogLampCone"); var dir = UnityEngine.Shader.GetGlobalVector("_FogLampDir");
float clear = UnityEngine.Shader.GetGlobalFloat("_FogLampClear"), soft = UnityEngine.Shader.GetGlobalFloat("_FogLampSoft"), reach = UnityEngine.Shader.GetGlobalFloat("_FogLampReach");
int W = 960, H = 540;
System.Func<UnityEngine.Color32[]> Shot = () => { var rt = UnityEngine.RenderTexture.GetTemporary(W, H, 24); var prevT = cam.targetTexture; cam.targetTexture = rt; cam.Render(); cam.targetTexture = prevT; var tex = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGB24, false); var prevA = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt; tex.ReadPixels(new UnityEngine.Rect(0, 0, W, H), 0, 0); tex.Apply(); UnityEngine.RenderTexture.active = prevA; UnityEngine.RenderTexture.ReleaseTemporary(rt); var px = tex.GetPixels32(); UnityEngine.Object.Destroy(tex); return px; };
float savedDay = Cozy.Character.FlashlightRig.FogClearDay, savedNight = Cozy.Character.FlashlightRig.FogClearNight;
UnityEngine.Color32[] a, b;
try
{
    Cozy.Character.FlashlightRig.FogClearDay = 1f; Cozy.Character.FlashlightRig.FogClearNight = 1f; UnityEngine.Shader.SetGlobalFloat("_FogLampClear", 1f); a = Shot();
    UnityEngine.Shader.SetGlobalFloat("_FogLampClear", 0f); b = Shot();
}
finally { Cozy.Character.FlashlightRig.FogClearDay = savedDay; Cozy.Character.FlashlightRig.FogClearNight = savedNight; }
int changed = 0, darker = 0; long sumA = 0, sumB = 0; int minX = W, maxX = 0, minY = H, maxY = 0;
for (int i = 0; i < a.Length; i++)
{
    int la = (a[i].r * 3 + a[i].g * 6 + a[i].b) / 10, lb = (b[i].r * 3 + b[i].g * 6 + b[i].b) / 10;
    sumA += la; sumB += lb;
    if (System.Math.Abs(la - lb) > 12) { changed++; if (la < lb) darker++; int x = i % W, y = i / W; if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y; }
}
return "конус: начало " + new UnityEngine.Vector3(cone.x, cone.y, cone.z).ToString("F2") + " дальность " + cone.w.ToString("F1") + " dir " + new UnityEngine.Vector3(dir.x, dir.y, dir.z).ToString("F2") + " tan " + dir.w.ToString("F2") + " | ручки clear=" + clear.ToString("F2") + " soft=" + soft.ToString("F2") + " reach=" + reach.ToString("F2") + " | A/B (луч 100% / 0%): пикселей изменилось " + changed + " из " + a.Length + ", из них стало темнее (туман ушёл) " + darker + ", средняя яркость " + (sumA / (float)a.Length).ToString("F1") + " / " + (sumB / (float)a.Length).ToString("F1") + ", область x " + minX + ".." + maxX + " y " + minY + ".." + maxY;
'''
INSIDE = r'''
var gc = Cozy.Grid.GridCursor.I; var player = Cozy.Grid.PlayerRef.GameObject;
var fogs = UnityEngine.Object.FindObjectsByType<Cozy.Grid.FogAnim>(UnityEngine.FindObjectsSortMode.None);
UnityEngine.Vector3 best = UnityEngine.Vector3.zero; float bd = float.MaxValue;
foreach (var f in fogs) { float d = UnityEngine.Vector3.Distance(f.transform.position, player.transform.position); if (d < bd) { bd = d; best = f.transform.position; } }
var keep = player.transform.rotation;
gc.TeleportPlayerTo(new UnityEngine.Vector3(best.x, gc.GroundY(best.x, best.z, 0f), best.z));
player.transform.rotation = keep;
UnityEngine.Physics.SyncTransforms();
return "игрок в клетке тумана " + player.transform.position.ToString("F2") + " накрыт=" + Cozy.Grid.FogView.Covers(player.transform.position);
'''
RESTORE = r'''
var gc = Cozy.Grid.GridCursor.I; var player = Cozy.Grid.PlayerRef.GameObject;
var rig = player.GetComponent<Cozy.Character.FlashlightRig>();
var hud = UnityEngine.Object.FindFirstObjectByType<Tavern.UI.HudUI>();
var th = typeof(Tavern.UI.HudUI);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
th.GetField("_activeQuick", bf).SetValue(hud, %QUICK%); th.GetMethod("SyncHand", bf).Invoke(hud, null);
var cc = player.GetComponent<UnityEngine.CharacterController>();
float rise = cc != null ? cc.height * 0.5f - cc.center.y : 0f;
gc.TeleportPlayerTo(new UnityEngine.Vector3(%X%f, %Y%f - rise, %Z%f));
return "возврат: игрок " + player.transform.position.ToString("F2") + " фонарь held=" + rig.Held + " lit=" + rig.Lit;
'''
s = str(call(SETUP)); print('setup:', s.split('|')[0] if '|' in s else s)
if '|' not in s: sys.exit(1)
parts = s.split('|'); px, py, pz, quick = parts[-4], parts[-3], parts[-2], parts[-1]
try:
    time.sleep(1.5)
    res = str(call(MEASURE)); print('снаружи:', res)
    m = re.search(r'дальность ([0-9.]+).*?изменилось (\d+)', res)
    red = m is None or float(m.group(1)) <= 0 or int(m.group(2)) == 0
    print('внутрь:', call(INSIDE))
    time.sleep(3.5)
    res2 = str(call(MEASURE)); print('изнутри (с пеленой):', res2)
    m2 = re.search(r'изменилось (\d+)', res2)
    red = red or m2 is None or int(m2.group(1)) == 0
finally:
    print(call(RESTORE.replace('%X%', px).replace('%Y%', py).replace('%Z%', pz).replace('%QUICK%', quick)))
print('луч в тумане: ' + ('КРАСНОЕ' if red else 'ок'))
sys.exit(1 if red else 0)
