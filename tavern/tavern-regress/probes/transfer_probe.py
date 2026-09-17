"""Крит-сценарий Ильи (13.09): взять → нести → положить на землю → поднять → положить на плоскость → поднять.

python3 transfer_probe.py          проверка привязок: методы и поля на месте, есть кандидаты (без побочных эффектов)
python3 transfer_probe.py --run    полный сценарий ДЕЙСТВИЕМ, ~6 с, только в СВОЁМ play (чужая проба или
                                   сохранение уровня в этот момент испортят сцену, см. SESSIONS.md)

Что меряется (инварианты 3, 80, 104, 149, 154, 156; грабли P079, P300, P369, P384):
1. В руке предмет видим: рендереры включены, хотя бы один в кадре, альфа не нулевая.
2. Положенный на землю лёг НА поверхность: низ модели над `GroundY` в пределах −2…+15 см,
   этаж над рельефом около нуля, объект виден, досягаем (`Interactor.InReach`), наводится
   (`Interactor.Raycast`) и берётся в руку снова.
3. То же на плоскости — верх ближайшей мебели в досягаемости (стол, тумба, полка); если
   такой нет, шаг честно пропускается, это не зелёный.
Кладёт тем же путём, что клик игрока: камера доворачивается так, чтобы луч через настоящий
курсор шёл в цель (мышь подменить нельзя, README), дальше `ComputeObjectPose` → `ReleaseMoving`
→ `ReattachToContainer` → `EndHandMove`. Предмет возвращается на своё место в `finally`.
"""
import json, subprocess, sys, time

MCP = '/home/ilya/.claude/skills/tavern-game/mcp_call.py'
PROJECT = '/media/ilya/T714/Unity/Tavern-fresh'

BIND = r'''
var t = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var sb = new System.Text.StringBuilder();
foreach (var n in new[] { "BeginHandMove", "CancelHandMove", "EndHandMove", "ComputeObjectPose", "ReleaseMoving", "ReattachToContainer", "PlaceFloorY", "SurfaceTopAt" })
    sb.Append(n + "=" + (t.GetMethod(n, bf) != null) + " ");
sb.Append("_movingObj=" + (t.GetField("_movingObj", bf) != null) + " ");
var ti = typeof(Cozy.Grid.Interactor);
sb.Append("InReach=" + (ti.GetMethod("InReach", bf) != null) + " Raycast=" + (ti.GetMethod("Raycast", bf) != null) + " ");
int cand = 0;
if (UnityEngine.Application.isPlaying)
    foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        if (io.Def != null && !io.Def.builtIn && (io.Def.movable || !string.IsNullOrEmpty(io.Def.pickupItemId))
            && io.Container == null && !Cozy.Grid.ContainerSlot.HoldsClosed(io)) cand++;
sb.Append("play=" + UnityEngine.Application.isPlaying + " candidates=" + cand);
return sb.ToString();
'''

PRELUDE = r'''
if (!UnityEngine.Application.isPlaying) return "не в play";
var gc = Cozy.Grid.GridCursor.I;
if (gc == null) return "нет GridCursor";
var tgc = typeof(Cozy.Grid.GridCursor);
var bf = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var fMoving = tgc.GetField("_movingObj", bf);
var cam = UnityEngine.Camera.main;
var mouse = UnityEngine.InputSystem.Mouse.current;
if (cam == null || mouse == null) return "нет камеры или мыши";
var player = Cozy.Grid.PlayerRef.GameObject;
if (player == null) return "нет игрока";
var savedCam = cam.transform.rotation;
System.Action<UnityEngine.Vector3> aim = delegate (UnityEngine.Vector3 target)
{
    var ray = cam.ScreenPointToRay(mouse.position.ReadValue());
    var want = (target - cam.transform.position).normalized;
    cam.transform.rotation = UnityEngine.Quaternion.FromToRotation(ray.direction, want) * cam.transform.rotation;
};
System.Func<int, Cozy.Grid.InteractiveObject> byId = delegate (int id)
{
    foreach (var o in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
        if (o.GetInstanceID() == id) return o;
    return null;
};
'''

PICK = PRELUDE + r'''
if (gc.HandPlacing) return "в руке уже что-то есть — не мешаю";
Cozy.Grid.InteractiveObject best = null; float bestD = float.MaxValue;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
{
    if (io.Def == null || io.Def.builtIn || io.Container != null) continue;
    if (io.Def.mount != Cozy.Grid.ObjectMount.Surface) continue;
    if (!(io.Def.movable || !string.IsNullOrEmpty(io.Def.pickupItemId))) continue;
    if (Cozy.Grid.ContainerSlot.HoldsClosed(io)) continue;
    if (io.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io) continue;
    float feetY = Cozy.Character.PlayerTarget.Feet.y;
    if (io.transform.position.y < feetY - 0.5f || io.transform.position.y > feetY + 2.5f) continue;
    var sizeRends = io.GetComponentsInChildren<UnityEngine.Renderer>(false);
    if (sizeRends.Length > 0)
    {
        var sizeBox = Cozy.Grid.FurnitureModel.Combined(sizeRends);
        if (UnityEngine.Mathf.Max(sizeBox.size.x, sizeBox.size.z) > 0.6f) continue;
    }
    float d = UnityEngine.Vector3.Distance(io.transform.position, player.transform.position);
    string id = io.Def.id;
    if (id.Contains("key") || id.Contains("batter") || id.Contains("apple") || id.Contains("cup") || id.Contains("match")) d -= 2f;
    if (d < bestD) { bestD = d; best = io; }
}
if (best == null) return "нет кандидата";
var p = best.transform.position; var r = best.transform.rotation.eulerAngles;
gc.BeginHandMove(best);
var pp = player.transform.position;
return "взят|" + best.GetInstanceID() + "|" + best.Def.id + "|" + p.x.ToString("R") + "|" + p.y.ToString("R") + "|" + p.z.ToString("R") + "|" + r.y.ToString("R") + "|" + best.name + "|" + pp.x.ToString("R") + "|" + pp.y.ToString("R") + "|" + pp.z.ToString("R");
'''

# Уровень без носимых предметов (crown_attack, 16.09) оставлял крит-сценарий без проверки вовсе:
# «шаг 1: нет кандидата». Тогда проба кладёт у ног игрока свой предмет из каталога, гоняет
# сценарий на нём и сносит его в уборке — уровень остаётся как был.
SPAWN = PRELUDE + r'''
if (gc.HandPlacing) return "в руке уже что-то есть — не мешаю";
Cozy.Grid.ObjectDef def = null;
foreach (var id in new[] { "apple", "matches", "cup", "mug", "battery" })
{
    var d = Cozy.Grid.FurnitureCatalog.ById(id);
    if (d != null && !d.builtIn && d.mount == Cozy.Grid.ObjectMount.Surface && (d.movable || !string.IsNullOrEmpty(d.pickupItemId))) { def = d; break; }
}
if (def == null) return "в каталоге нет носимого предмета для пробы";
var fwd = UnityEngine.Vector3.ProjectOnPlane(player.transform.forward, UnityEngine.Vector3.up).normalized;
if (fwd.sqrMagnitude < 0.01f) fwd = UnityEngine.Vector3.forward;
var at = player.transform.position + fwd * 0.9f;
float gy = UnityEngine.Mathf.Max(gc.GroundY(at.x, at.z, 0f), Cozy.Character.PlayerTarget.Feet.y);
var spawned = gc.SpawnWorldObject(def, new UnityEngine.Vector3(at.x, gy, at.z), 0f);
if (spawned == null) return "предмет пробы не заспавнился";
return "заспавнен|" + spawned.GetInstanceID() + "|" + def.id;
'''

DESPAWN = r'''
int gone = 0;
foreach (var io in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
    if (io != null && io.GetInstanceID() == %ID%) { UnityEngine.Object.DestroyImmediate(io.gameObject); gone++; break; }
return "снесён предмет пробы: " + gone;
'''

REPICK = PRELUDE + r'''
if (gc.HandPlacing) return "в руке уже что-то есть — не мешаю";
var pickAgain = byId(%ID%);
if (pickAgain == null) return "нет кандидата";
gc.BeginHandMove(pickAgain);
return "взят|" + pickAgain.GetInstanceID() + "|" + pickAgain.Def.id + "|0|0|0|0|" + pickAgain.name;
'''

CARRY = PRELUDE + r'''
var mv = fMoving.GetValue(gc);
if (mv == null) return "КРАСНОЕ: в руке ничего нет (перенос сорвался)";
var anchor = mv.GetType().GetProperty("Anchor").GetValue(mv, null) as UnityEngine.Transform;
var io = anchor == null ? null : anchor.GetComponentInParent<Cozy.Grid.InteractiveObject>();
if (io == null) return "КРАСНОЕ: у носимого нет InteractiveObject";
int total = 0, off = 0, visible = 0, ghostAlpha = 0;
foreach (var rd in io.GetComponentsInChildren<UnityEngine.Renderer>(true))
{
    if (rd.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io) continue;
    if (rd.name.StartsWith("Outline")) continue;
    total++;
    if (!rd.enabled || !rd.gameObject.activeInHierarchy) { off++; continue; }
    if (rd.isVisible) visible++;
    var m = rd.sharedMaterial;
    if (m != null)
    {
        float a = 1f;
        if (m.HasProperty("_BaseColor")) a = m.GetColor("_BaseColor").a;
        else if (m.HasProperty("_Color")) a = m.GetColor("_Color").a;
        if (a < 0.05f) ghostAlpha++;
    }
}
string s = "в руке " + io.Def.id + ": рендереров " + total + ", выключено " + off + ", видно камерой " + visible + ", альфа<0.05 " + ghostAlpha;
if (total == 0 || off > 0 || visible == 0 || ghostAlpha == total) return "КРАСНОЕ: " + s;
return "ок: " + s;
'''

DROP = PRELUDE + r'''
string mode = "%MODE%";
var mv = fMoving.GetValue(gc);
if (mv == null) return "КРАСНОЕ: в руке ничего нет";
var anchor = mv.GetType().GetProperty("Anchor").GetValue(mv, null) as UnityEngine.Transform;
var io = anchor == null ? null : anchor.GetComponentInParent<Cozy.Grid.InteractiveObject>();
if (io == null) return "КРАСНОЕ: у носимого нет InteractiveObject";
var mCompute = tgc.GetMethod("ComputeObjectPose", bf);
var mRelease = tgc.GetMethod("ReleaseMoving", bf);
var mEnd = tgc.GetMethod("EndHandMove", bf);
var mFloorY = tgc.GetMethod("PlaceFloorY", bf);
var mTopAt = tgc.GetMethod("SurfaceTopAt", bf);
if (mCompute == null || mRelease == null || mEnd == null || mFloorY == null || mTopAt == null) return "КРАСНОЕ: нет методов постановки";
float floorY = (float)mFloorY.Invoke(gc, null);
var targets = new System.Collections.Generic.List<UnityEngine.Vector3>();
var names = new System.Collections.Generic.List<string>();
var hits = new UnityEngine.RaycastHit[32];
if (mode == "ground")
{
    for (int k = 0; k < 8; k++)
    {
        float ang = k * 45f * UnityEngine.Mathf.Deg2Rad;
        var pt = player.transform.position + new UnityEngine.Vector3(UnityEngine.Mathf.Cos(ang), 0f, UnityEngine.Mathf.Sin(ang)) * 1.3f;
        int n = UnityEngine.Physics.RaycastNonAlloc(new UnityEngine.Vector3(pt.x, floorY + 6f, pt.z), UnityEngine.Vector3.down, hits, 12f, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
        bool ground = false, slab = false; float top = float.NegativeInfinity;
        for (int i = 0; i < n; i++)
        {
            var gb = hits[i].collider.GetComponent<Cozy.Grid.GridBlock>();
            if (gb == null) continue;
            if (gb.role == Cozy.Grid.GridRole.Ground) ground = true; else slab = true;
            if (hits[i].point.y > top) top = hits[i].point.y;
        }
        if (!ground && !slab) continue;
        targets.Add(new UnityEngine.Vector3(pt.x, top, pt.z));
        names.Add(slab ? "плита пола" : "земля");
    }
    for (int i = 0; i < names.Count; i++) if (names[i] == "земля" && i > 0) { var tp = targets[i]; targets.RemoveAt(i); targets.Insert(0, tp); names.RemoveAt(i); names.Insert(0, "земля"); break; }
}
else
{
    foreach (var host in UnityEngine.Object.FindObjectsByType<Cozy.Grid.InteractiveObject>(UnityEngine.FindObjectsSortMode.None))
    {
        if (host == io || host.Def == null || host.Def.builtIn || host.Container != null) continue;
        if (host.Def.mount != Cozy.Grid.ObjectMount.Floor || host.Def.movable) continue;
        var rends = host.GetComponentsInChildren<UnityEngine.Renderer>(false);
        if (rends.Length == 0) continue;
        var b = Cozy.Grid.FurnitureModel.Combined(rends);
        float h = b.max.y - floorY;
        if (h < 0.4f || h > 1.5f) continue;
        float topAt = (float)mTopAt.Invoke(gc, new object[] { b.center.x, b.center.z, floorY, io.transform, b.max.y });
        if (UnityEngine.Mathf.Abs(topAt - b.max.y) > 0.06f) continue;
        targets.Add(new UnityEngine.Vector3(b.center.x, b.max.y + 0.03f, b.center.z));
        names.Add(host.Def.id + "@" + b.center.x.ToString("F1") + "," + b.center.z.ToString("F1"));
    }
    for (int i = 1; i < targets.Count; i++)
        for (int j = i; j > 0 && UnityEngine.Vector3.Distance(targets[j], player.transform.position) < UnityEngine.Vector3.Distance(targets[j - 1], player.transform.position); j--)
        { var tt = targets[j]; targets[j] = targets[j - 1]; targets[j - 1] = tt; var nn = names[j]; names[j] = names[j - 1]; names[j - 1] = nn; }
    if (targets.Count > 3) { targets.RemoveRange(3, targets.Count - 3); names.RemoveRange(3, names.Count - 3); }
}
if (targets.Count == 0) return mode == "ground" ? "ПРОПУСК: рядом с игроком нет земли и пола" : "ПРОПУСК: в досягаемости нет плоскости (стол, тумба, полка)";
var tried = new System.Text.StringBuilder();
try
{
    for (int k = 0; k < targets.Count; k++)
    {
        if (mode == "surface")
        {
            var flat = new UnityEngine.Vector3(targets[k].x - player.transform.position.x, 0f, targets[k].z - player.transform.position.z);
            if (flat.magnitude > 2.2f)
            {
                var stand = targets[k] - flat.normalized * 1.4f;
                gc.TeleportPlayerTo(new UnityEngine.Vector3(stand.x, floorY, stand.z));
                UnityEngine.Physics.SyncTransforms();
            }
        }
        aim(targets[k]);
        var args = new object[] { io.Def, cam, mouse, anchor.gameObject, anchor, floorY, null, null, null };
        bool okPose = (bool)mCompute.Invoke(gc, args);
        cam.transform.rotation = savedCam;
        if (!okPose) { tried.Append(names[k] + ": курсор мимо; "); continue; }
        var pos = (UnityEngine.Vector3)args[6]; float yaw = (float)args[7]; bool blocked = (bool)args[8];
        if (blocked) { tried.Append(names[k] + ": красный; "); continue; }
        if (mode == "surface" && pos.y < floorY + 0.3f) { tried.Append(names[k] + ": поза ушла на пол; "); continue; }
        anchor.SetPositionAndRotation(pos, UnityEngine.Quaternion.Euler(0f, yaw, 0f));
        mRelease.Invoke(gc, null);
        gc.ReattachToContainer(io);
        fMoving.SetValue(gc, null);
        mEnd.Invoke(gc, null);
        return "положен|" + names[k] + "|" + pos.x.ToString("R") + "|" + pos.y.ToString("R") + "|" + pos.z.ToString("R") + "|" + floorY.ToString("R");
    }
}
finally { cam.transform.rotation = savedCam; }
return "КРАСНОЕ: некуда положить (" + tried + ")";
'''

MEASURE = PRELUDE + r'''
var io = byId(%ID%);
if (io == null) return "КРАСНОЕ: предмет исчез после постановки";
if (gc.Carried(io.transform)) return "КРАСНОЕ: предмет всё ещё в руке";
var rends = io.GetComponentsInChildren<UnityEngine.Renderer>(false);
var own = new System.Collections.Generic.List<UnityEngine.Renderer>();
int off = 0, seen = 0;
foreach (var rd in rends)
{
    if (rd.GetComponentInParent<Cozy.Grid.InteractiveObject>() != io || rd.name.StartsWith("Outline")) continue;
    own.Add(rd);
    if (!rd.enabled) off++; else if (rd.isVisible) seen++;
}
if (own.Count == 0) return "КРАСНОЕ: у предмета нет рендереров";
var b = Cozy.Grid.FurnitureModel.Combined(own);
var p = io.transform.position;
float support;
string mode = "%MODE%";
float floorLift = UnityEngine.Mathf.Max(0f, %FLOORY%f - gc.GroundY(p.x, p.z, 0f));
if (mode == "ground") support = gc.GroundY(p.x, p.z, 0f) + floorLift;
else
{
    var mTop = tgc.GetMethod("SurfaceTopAt", bf);
    support = (float)mTop.Invoke(gc, new object[] { p.x, p.z, %FLOORY%f, io.transform, p.y });
}
float gap = b.min.y - support;
float above = Cozy.Grid.GridManager.AboveRelief(p);
var fv = io.GetComponent<Cozy.Grid.FloorPieceView>();
bool shown = fv == null || fv.Visible;
var inter = UnityEngine.Object.FindFirstObjectByType<Cozy.Grid.Interactor>();
var ti = typeof(Cozy.Grid.Interactor);
bool reach = false, hovered = false, clearRay = false; string obstacle = "";
if (inter != null)
{
    var mReach = ti.GetMethod("InReach", bf);
    if (mReach != null) reach = (bool)mReach.Invoke(inter, new object[] { io, null });
    var mRay = ti.GetMethod("Raycast", bf);
    if (mRay != null)
    {
        try
        {
            aim(b.center);
            var hoverRay = cam.ScreenPointToRay(mouse.position.ReadValue());
            var hits = UnityEngine.Physics.RaycastAll(hoverRay, 80f, ~0, UnityEngine.QueryTriggerInteraction.Ignore);
            float mine = float.MaxValue; float other = float.MaxValue; string otherName = "";
            foreach (var h in hits)
            {
                bool isMine = h.collider.GetComponentInParent<Cozy.Grid.InteractiveObject>() == io;
                if (isMine) { if (h.distance < mine) mine = h.distance; }
                else if (h.distance < other && !h.collider.transform.IsChildOf(player.transform)) { other = h.distance; otherName = h.collider.name; }
            }
            clearRay = mine < other;
            obstacle = otherName;
            var hit = mRay.Invoke(inter, new object[] { mouse }) as UnityEngine.Component;
            hovered = hit != null && hit.GetComponentInParent<Cozy.Grid.InteractiveObject>() == io;
        }
        finally { cam.transform.rotation = savedCam; }
    }
}
gc.BeginHandMove(io);
bool taken = gc.HandPlacing && gc.Carried(io.transform);
var mCancel = tgc.GetMethod("CancelHandMove", bf);
if (taken && mCancel != null) mCancel.Invoke(gc, null);
var bad = new System.Text.StringBuilder();
if (gap < -0.02f) bad.Append("утонул в опоре на " + (-gap).ToString("F3") + " м; ");
if (gap > 0.15f) bad.Append("висит над опорой на " + gap.ToString("F3") + " м; ");
if (mode == "ground" && (above - floorLift < -0.2f || above - floorLift > 0.4f)) bad.Append("этаж над рельефом " + above.ToString("F2") + "; ");
if (!shown) bad.Append("скрыт гейтом этажа; ");
if (off > 0 || seen == 0) bad.Append("не виден (выключено " + off + ", в кадре " + seen + "); ");
if (!reach) bad.Append("недосягаем; ");
if (!hovered && clearRay) bad.Append("не наводится при чистом луче; ");
if (!taken) bad.Append("не берётся снова; ");
string s = "низ−опора " + gap.ToString("+0.000;-0.000") + " м, над рельефом " + above.ToString("F2") + ", виден " + (shown && off == 0 && seen > 0) + ", досягаем " + reach + ", наводится " + (hovered ? "True" : clearRay ? "False" : "не проверено, луч через " + obstacle) + ", взят снова " + taken;
return (bad.Length == 0 ? "ок: " : "КРАСНОЕ: " + bad + "| ") + s;
'''

RESTORE = PRELUDE + r'''
var io = byId(%ID%);
if (io == null) return "предмет не найден";
if (gc.Carried(io.transform)) { var mCancel = tgc.GetMethod("CancelHandMove", bf); if (mCancel != null) mCancel.Invoke(gc, null); }
io.transform.SetParent(null, true);
io.transform.SetPositionAndRotation(new UnityEngine.Vector3(%X%f, %Y%f, %Z%f), UnityEngine.Quaternion.Euler(0f, %YAW%f, 0f));
gc.ReattachToContainer(io);
var back = new UnityEngine.Vector3(%PX%f, %PY%f, %PZ%f);
string moved = "";
if (UnityEngine.Vector3.Distance(player.transform.position, back) > 0.5f)
{
    var cc = player.GetComponent<UnityEngine.CharacterController>();
    float rise = cc != null ? cc.height * 0.5f - cc.center.y : 0f;
    gc.TeleportPlayerTo(back - UnityEngine.Vector3.up * rise);
    moved = ", игрок возвращён в " + player.transform.position.ToString("F2");
}
UnityEngine.Physics.SyncTransforms();
return "возвращён " + io.Def.id + " в " + io.transform.position.ToString("F2") + moved;
'''


def call(code):
    code = '\n'.join(l for l in code.splitlines() if l.strip() and not l.strip().startswith('//'))
    out = subprocess.run(['python3', MCP, 'execute_code', json.dumps({"action": "execute", "code": code})],
                         capture_output=True, text=True, timeout=120, cwd=PROJECT)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else '{}'
    try:
        d = json.loads(line)
        return (d.get('data') or {}).get('result') or d.get('message') or line
    except Exception:
        return out.stdout[-300:]


def fill(code, **kw):
    for k, v in kw.items():
        code = code.replace('%' + k + '%', str(v))
    return code


def main():
    print('привязки:', call(BIND))
    if '--run' not in sys.argv:
        print('полный прогон: transfer_probe.py --run (только в своём play)')
        return
    picked = str(call(PICK))
    spawned = None
    if picked == 'нет кандидата':
        made = str(call(SPAWN))
        if not made.startswith('заспавнен|'):
            print('шаг 1: нет кандидата, и свой предмет не положить —', made)
            sys.exit(1)
        spawned = made.split('|')[1]
        print('шаг 0: на уровне нет носимых — положен свой', made.split('|')[2])
        time.sleep(1.0)
        picked = str(call(PICK))
    if not picked.startswith('взят|'):
        print('шаг 1:', picked)
        if spawned:
            print('уборка:', call(fill(DESPAWN, ID=spawned)))
        sys.exit(1)
    _, oid, did, ox, oy, oz, oyaw, oname, ppx, ppy, ppz = picked.split('|')
    print('шаг 1: взят', did, oname)
    red = False
    notes = []
    try:
        time.sleep(0.7)
        res = str(call(CARRY)); print('шаг 2:', res); red |= not res.startswith('ок')
        notes.append(res.replace('ок: ', ''))
        step = 3
        for mode, title in (('ground', 'на землю'), ('surface', 'на плоскость')):
            if mode == 'surface':
                pick2 = str(call(fill(REPICK, ID=oid)))
                if not pick2.startswith('взят|'):
                    print('шаг %d: повторно не взят — %s' % (step, pick2)); red = True; break
                time.sleep(0.5)
            drop = str(call(fill(DROP, MODE=mode)))
            if drop.startswith('ПРОПУСК'):
                print('шаг %d: %s — %s' % (step, title, drop)); notes.append(title + ': ' + drop); step += 2; continue
            if not drop.startswith('положен|'):
                print('шаг %d: %s — %s' % (step, title, drop)); notes.append(title + ': ' + drop); red = True; break
            _, where, px, py, pz, fy = drop.split('|')
            print('шаг %d: положен %s (%s) в (%.2f, %.2f, %.2f)' % (step, title, where, float(px), float(py), float(pz)))
            time.sleep(1.0)
            res = str(call(fill(MEASURE, ID=oid, MODE=mode, FLOORY=fy)))
            print('шаг %d: %s' % (step + 1, res)); red |= not res.startswith('ок')
            notes.append(title + ' (' + where + '): ' + res.replace('ок: ', ''))
            time.sleep(0.6)
            step += 2
    finally:
        print('возврат:', call(fill(RESTORE, ID=oid, X=ox, Y=oy, Z=oz, YAW=oyaw, PX=ppx, PY=ppy, PZ=ppz)))
        if spawned:
            print('уборка:', call(fill(DESPAWN, ID=spawned)))
    print(('перенос: КРАСНОЕ' if red else 'перенос: ок') + ' :: ' + '; '.join(notes))
    sys.exit(1 if red else 0)


if __name__ == '__main__':
    main()
