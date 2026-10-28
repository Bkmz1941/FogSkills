"""Планарное зеркало в play (инвариант 211, P487): у каждого объекта с mirrorNode — компонент MirrorReflection,
шейдер Cozy/MirrorGlass на стекле, камера-двойник, и её поза = отражение главной камеры относительно плоскости
стекла (по ту сторону, зазор ≤ 3 см); камера-двойник включена ⇔ стекло в кадре ГЛАВНОЙ камеры, на этаже героя и ближе 12 м (инвариант 248, P573; 303, P687). Ничего не меняет. Вердикт: MIRROR ok | MIRROR FAIL: …
python3 mirror_probe.py            вердикт по всем зеркалам уровня
python3 mirror_probe.py --dump     плюс дамп RenderTexture первого зеркала в scratchpad (mirror_rt.png)"""
import json, os, subprocess, sys, pathlib
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
DUMP = os.environ.get('MIRROR_DUMP', '/tmp/mirror_rt.png')
code = '''
if (!UnityEngine.Application.isPlaying) return "MIRROR FAIL: not playing";
var main = UnityEngine.Camera.main;
if (main == null) return "MIRROR FAIL: no main camera";
int n = 0; var bad = new System.Text.StringBuilder(); var seen = new System.Text.StringBuilder();
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null || string.IsNullOrEmpty(io.Def.mirrorNode)) continue;
    n++;
    var mr = io.GetComponent<Cozy.Grid.MirrorReflection>();
    if (mr == null) { bad.Append(io.Def.id + ": нет MirrorReflection; "); continue; }
    UnityEngine.Transform glass = null;
    foreach (var c in io.GetComponentsInChildren<UnityEngine.Transform>(true)) if (c.name == io.Def.mirrorNode) { glass = c; break; }
    var r = glass != null ? glass.GetComponent<UnityEngine.Renderer>() : null;
    if (r == null) { bad.Append(io.Def.id + ": нет узла стекла; "); continue; }
    if (r.sharedMaterial == null || r.sharedMaterial.shader.name != "Cozy/MirrorGlass") bad.Append(io.Def.id + ": шейдер " + (r.sharedMaterial != null ? r.sharedMaterial.shader.name : "null") + "; ");
    var camT = io.transform.Find("MirrorCamera"); var cam = camT != null ? camT.GetComponent<UnityEngine.Camera>() : null;
    var hero = Cozy.Grid.PlayerRef.Transform;
    bool near = false;
    if (hero != null)
    {
        float storey = Cozy.Grid.FurnitureModel.CellSize();
        var feet = hero.position; var gap = r.bounds.ClosestPoint(feet) - feet; gap.y = 0f;
        near = UnityEngine.Mathf.FloorToInt((feet.y + 0.3f) / storey) == UnityEngine.Mathf.FloorToInt((r.bounds.min.y + 0.3f) / storey) && gap.sqrMagnitude < 144f;
    }
    bool inView = near && r.isVisible && UnityEngine.GeometryUtility.TestPlanesAABB(UnityEngine.GeometryUtility.CalculateFrustumPlanes(main), r.bounds);
    if (!inView) { if (cam != null && cam.enabled) bad.Append(io.Def.id + ": стекло вне кадра главной камеры / не на этаже героя / дальше 12 м, а камера-двойник включена (P573, P687); "); else seen.Append(io.Def.id + ": стекло вне кадра, камера выкл; "); continue; }
    if (cam == null || !cam.enabled) { bad.Append(io.Def.id + ": стекло в кадре, а камеры-двойника нет или выключена; "); continue; }
    if (cam.targetTexture == null) bad.Append(io.Def.id + ": нет RenderTexture; ");
    var b = r.bounds; var s = b.size; var axis = s.x <= s.y && s.x <= s.z ? UnityEngine.Vector3.right : (s.y <= s.z ? UnityEngine.Vector3.up : UnityEngine.Vector3.forward);
    float dMain = UnityEngine.Vector3.Dot(axis, main.transform.position - b.center);
    float dCam = UnityEngine.Vector3.Dot(axis, cam.transform.position - b.center);
    var expect = main.transform.position - 2f * dMain * axis;
    float err = UnityEngine.Vector3.Distance(expect, cam.transform.position);
    if (dMain * dCam >= 0f) bad.Append(io.Def.id + ": камера-двойник по ту же сторону стекла (" + dMain.ToString("0.00") + " / " + dCam.ToString("0.00") + "); ");
    else if (err > 0.03f) bad.Append(io.Def.id + ": поза двойника не отражение главной, расходится на " + err.ToString("0.000") + " м; ");
    seen.Append(io.Def.id + ": ok, rt=" + (cam.targetTexture != null ? cam.targetTexture.width + "x" + cam.targetTexture.height : "-") + ", зазор " + err.ToString("0.000") + "; ");
    if (DUMPFLAG && cam.targetTexture != null) {
        var rt = cam.targetTexture; var prev = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt;
        var tex = new UnityEngine.Texture2D(rt.width, rt.height, UnityEngine.TextureFormat.RGBA32, false); tex.ReadPixels(new UnityEngine.Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply(); UnityEngine.RenderTexture.active = prev;
        System.IO.File.WriteAllBytes("DUMPPATH", tex.EncodeToPNG()); UnityEngine.Object.Destroy(tex);
    }
}
if (n == 0) return "MIRROR ok: зеркал на уровне нет (нечего проверять)";
if (bad.Length > 0) return "MIRROR FAIL: " + bad + " :: " + seen;
return "MIRROR ok: зеркал " + n + " :: " + seen;
'''.replace('DUMPFLAG', 'true' if '--dump' in sys.argv else 'false').replace('DUMPPATH', DUMP)
out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})], capture_output=True, text=True, timeout=120, cwd=PROJECT)
text = out.stdout.strip(); line = text.splitlines()[-1] if text else '{}'
try:
    d = json.loads(line); res = (d.get('data') or {}).get('result') or str(d)
except Exception:
    res = 'MIRROR FAIL: мост ' + text[-300:]
print(res)
sys.exit(0 if res.startswith('MIRROR ok') else 1)
