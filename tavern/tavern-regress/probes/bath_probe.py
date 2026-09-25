"""Ванна в play: состояние шторки/крана/пробки/воды и этажного гейта — gateHoles (свои рендереры мимо _targets, кроме жидкости) и gateLeak (рисуется при закрытом гейте) (report), переключить кран (tap), пробку (plug), шторку (curtain). Работает на ванне ТЕКУЩЕГО уровня, ничего не спавнит; после tap/plug вернуть как было."""
import json, subprocess, sys, pathlib
MCP = str(pathlib.Path.home() / '.claude/skills/tavern-game/mcp_call.py')
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'
HEAD = '''
if (!UnityEngine.Application.isPlaying) return "not playing";
Cozy.Grid.InteractiveObject io = null;
foreach (var o in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
    if (o.Def != null && o.Def.id == "home_bath") { io = o; break; }
if (io == null) return "no bath";
System.Func<string, UnityEngine.Transform> find = n => { foreach (var c in io.GetComponentsInChildren<UnityEngine.Transform>(true)) if (c.name == n) return c; return null; };
var sb = new System.Text.StringBuilder();
'''
REPORT = '''
var cc = find("CurtainClosed"); var co = find("CurtainOpen"); var lever = find("LeverBar"); var plug = find("PlugKnob");
sb.Append("closedOn=" + (cc != null && cc.gameObject.activeSelf) + " openOn=" + (co != null && co.gameObject.activeSelf));
sb.Append(" closedCol=" + (cc != null && cc.GetComponent<UnityEngine.Collider>() != null) + " openCol=" + (co != null && co.GetComponent<UnityEngine.Collider>() != null));
sb.Append(" partClosed=" + (cc != null && io.IsPart(cc)) + " partLever=" + (lever != null && io.IsPart(lever)));
var liq = io.Liquid; sb.Append(" litres=" + (liq != null ? liq.Litres.ToString("0.00") : "null") + " cap=" + (liq != null ? liq.Capacity.ToString() : "") + " surfY=" + (liq != null ? liq.SurfaceY.ToString("0.000") : ""));
sb.Append(" lever=" + (lever != null ? lever.position.ToString("F3") : "null") + " plug=" + (plug != null ? plug.position.ToString("F3") : "null"));
var ws = io.GetComponent<Cozy.Grid.WaterSource>(); sb.Append(" supplied=" + (ws != null && ws.Supplied) + " running=" + (ws != null && ws.Running));
var st = find("WaterStream"); sb.Append(" stream=" + (st != null && st.gameObject.activeSelf) + (st != null ? " streamPos=" + st.position.ToString("F3") + " streamScale=" + st.localScale.ToString("F3") : ""));
var vx = find("DrainVortex"); sb.Append(" vortex=" + (vx != null && vx.gameObject.activeSelf));
var water = find("Water"); if (water != null) { var r = water.GetComponent<UnityEngine.Renderer>(); sb.Append(" waterRend=" + (r != null && r.enabled) + " waterB=" + (r != null ? r.bounds.min.y.ToString("0.000") + ".." + r.bounds.max.y.ToString("0.000") : "")); }
sb.Append(" objPos=" + io.transform.position.ToString("F2"));
var fv = io.GetComponent<Cozy.Grid.FloorPieceView>();
var tg = fv != null ? (UnityEngine.Renderer[])typeof(Cozy.Grid.FloorPieceView).GetField("_targets", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(fv) : null;
var tset = new System.Collections.Generic.HashSet<UnityEngine.Renderer>(); if (tg != null) foreach (var t in tg) if (t != null) tset.Add(t);
int holes = 0, leaks = 0; var holeNames = new System.Text.StringBuilder();
foreach (var r in io.GetComponentsInChildren<UnityEngine.Renderer>(true))
{
    if (!Cozy.Grid.InteractiveObject.OwnedBy(r, io)) continue;
    if (!Cozy.Grid.LiquidVolume.IsLiquid(r) && !tset.Contains(r)) { holes++; holeNames.Append(r.name + " "); }
    if (fv != null && !fv.Visible && r.enabled && r.gameObject.activeInHierarchy && !r.forceRenderingOff) leaks++;
}
sb.Append(" gateVisible=" + (fv != null && fv.Visible) + " gateHoles=" + holes + (holes > 0 ? "[" + holeNames.ToString().Trim() + "]" : "") + " gateLeak=" + leaks);
return sb.ToString();
'''
ACTIONS = {
    'report': '',
    'tap': 'sb.Append("toggleTap=" + io.ClickDoorPart(find("TapLever")) + " ");',
    'plug': 'sb.Append("togglePlug=" + io.ClickDoorPart(find("Plug")) + " ");',
    'curtain': 'sb.Append("toggleCurtain=" + io.ClickDoorPart(find("CurtainClosed") != null && find("CurtainClosed").gameObject.activeSelf ? find("CurtainClosed") : find("CurtainOpen")) + " ");',
}
code = HEAD + ACTIONS[sys.argv[1] if len(sys.argv) > 1 else 'report'] + REPORT
out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})], capture_output=True, text=True, timeout=120, cwd=PROJECT)
text = out.stdout.strip()
line = text.splitlines()[-1] if text else '{}'
try:
    d = json.loads(line); print((d.get('data') or {}).get('result') or d)
except Exception:
    print(text[-600:], out.stderr[-300:])
