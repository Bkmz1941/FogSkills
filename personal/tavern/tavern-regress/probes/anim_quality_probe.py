#!/usr/bin/env python3
"""Качество клипов персонажа — то, что в игре читается как «дёргается», «скользит»,
«тонет в пол», «луп щёлкает», но глазами ловится поздно.

  python3 anim_quality_probe.py                       # все FBX-клипы Resources
  python3 anim_quality_probe.py Walk_Calm Jog_Calm    # только эти
  python3 anim_quality_probe.py --json out.json ...   # подробности в json
  python3 anim_quality_probe.py --diff A.fbx B.fbx    # разница двух клипов по кадрам (синхронизация)
  python3 anim_quality_probe.py --file X.blend#Armature_Run  # клип из .blend (арматура по имени)

Меряет по кадрам (Blender headless, тот же FBX, что грузит Unity):
  step   — худший шаг локального поворота сустава за кадр (°/кадр) и у кого;
  wrap   — шаг на стыке последнего и первого кадра лупа против худшего внутри;
  floor  — низ стоп ПО МЕШУ относительно пола покоя (bind-поза), м; минус = под полом;
  slide  — скорость стопы в фазе опоры (м/с): среднее и разброс; у клипа «на месте»
           опорная стопа едет назад ровно, разброс = проскальзывание;
  L/R    — асимметрия опорных скоростей и длины опоры между ногами;
  knee   — переразгиб колена: колено позади линии бедро–лодыжка, см;
  drift  — уход таза по горизонтали за клип (корень должен стоять), м.
Вердикт — строка на клип, флаги в конце строки.
"""
import json, os, subprocess, sys, tempfile

BLENDER = '/media/ilya/T714/Tools/blender-5.2.2-linux-x64/blender'
RES = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources'
SKIP = ('Monster_',)

INNER = r'''
import bpy, math, json, sys
from mathutils import Vector, Quaternion, Matrix
TASK = json.load(open(%(task)r))
OUT = %(out)r
KEY = ['B-hips', 'B-spine', 'B-chest', 'B-neck', 'B-head',
       'B-shoulder.L', 'B-shoulder.R', 'B-upperArm.L', 'B-upperArm.R',
       'B-forearm.L', 'B-forearm.R', 'B-hand.L', 'B-hand.R',
       'B-thigh.L', 'B-thigh.R', 'B-shin.L', 'B-shin.R', 'B-foot.L', 'B-foot.R', 'B-toe.L', 'B-toe.R']


def foot_verts(mesh):
    groups = {g.index: g.name for g in mesh.vertex_groups}
    out = {'L': [], 'R': []}
    for v in mesh.data.vertices:
        top = max(v.groups, key=lambda g: g.weight, default=None)
        if top is None:
            continue
        name = groups.get(top.group, '')
        if name[:-2] in ('B-foot', 'B-toe'):
            out[name[-1]].append(v.index)
    return out


def load(spec):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path, _, arm_name = spec.partition('#')
    arm_name, _, act_name = arm_name.partition('@')
    if path.endswith('.blend'):
        bpy.ops.wm.open_mainfile(filepath=path)
        arms = [o for o in bpy.data.objects if o.type == 'ARMATURE' and (o.animation_data and o.animation_data.action or act_name)]
        arm = next((o for o in arms if o.name == arm_name), None) if arm_name else (arms[0] if arms else None)
        if arm is not None and act_name:
            if arm.animation_data is None:
                arm.animation_data_create()
            arm.animation_data.action = bpy.data.actions[act_name]
    else:
        bpy.ops.import_scene.fbx(filepath=path)
        arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.animation_data and o.animation_data.action), None)
    if arm is None:
        return None, None
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm and o.vertex_groups]
    mesh = max(meshes, key=lambda o: sum(len(v) for v in foot_verts(o).values()), default=None)
    if mesh is not None and not any(foot_verts(mesh).values()):
        mesh = None
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm, mesh


def rest_floor(mesh, fv):
    mw = mesh.matrix_world
    zs = [(mw @ mesh.data.vertices[i].co).z for side in fv for i in fv[side]]
    return min(zs) if zs else None


def ang(q0, q1):
    d = q0.rotation_difference(q1)
    return math.degrees(2.0 * math.acos(max(-1.0, min(1.0, abs(d.w)))))


def rest_wq(arm, name):
    return (arm.matrix_world @ arm.data.bones[name].matrix_local).to_quaternion().normalized()


def sample(arm, mesh):
    action = arm.animation_data.action
    scene = bpy.context.scene
    start, end = int(round(action.frame_range[0])), int(round(action.frame_range[1]))
    fv = foot_verts(mesh) if mesh else None
    floor = rest_floor(mesh, fv) if mesh else None
    frames = []
    dg = bpy.context.evaluated_depsgraph_get()
    for f in range(start, end + 1):
        scene.frame_set(f)
        fr = {'f': f, 'pos': {}, 'wq': {}, 'lq': {}, 'foot_low': {}, 'foot_xy': {}}
        for pb in arm.pose.bones:
            W = arm.matrix_world @ pb.matrix
            fr['pos'][pb.name] = W.to_translation()
            fr['wq'][pb.name] = W.to_quaternion().normalized()
            fr['lq'][pb.name] = pb.matrix_basis.to_quaternion().normalized()
            if pb.name.startswith('B-toe.'):
                fr['pos'][pb.name + '_tail'] = (arm.matrix_world @ pb.tail)
        if mesh:
            ev = mesh.evaluated_get(dg)
            mw = ev.matrix_world
            for side in ('L', 'R'):
                pts = [mw @ ev.data.vertices[i].co for i in fv[side]]
                if pts:
                    lowest = min(pts, key=lambda p: p.z)
                    fr['foot_low'][side] = lowest.z
                    fr['foot_xy'][side] = lowest.copy()
        frames.append(fr)
    return start, end, floor, frames


def analyse(name, arm, mesh, loop_hint):
    start, end, floor, frames = sample(arm, mesh)
    n = len(frames)
    bones = [b for b in KEY if b in arm.pose.bones]
    # шаг локального поворота за кадр
    step = {b: 0.0 for b in bones}
    step_at = {b: start for b in bones}
    for i in range(1, n):
        for b in bones:
            a = ang(frames[i - 1]['lq'][b], frames[i]['lq'][b])
            if a > step[b]:
                step[b], step_at[b] = a, frames[i]['f']
    worst = max(bones, key=lambda b: step[b])
    wstep = {b: 0.0 for b in bones}
    for i in range(1, n):
        for b in bones:
            wstep[b] = max(wstep[b], ang(frames[i - 1]['wq'][b], frames[i]['wq'][b]))
    # стык лупа
    wrap = {b: ang(frames[-1]['lq'][b], frames[0]['lq'][b]) for b in bones}
    wrap_worst = max(bones, key=lambda b: wrap[b])
    hips0, hips1 = frames[0]['pos']['B-hips'], frames[-1]['pos']['B-hips']
    # таз
    hz = [fr['pos']['B-hips'].z for fr in frames]
    drift = max(((fr['pos']['B-hips'] - frames[0]['pos']['B-hips']).xy.length) for fr in frames)
    # стопы
    feet = {}
    fps = 24.0
    for side in ('L', 'R'):
        ankle = [fr['pos']['B-foot.' + side] for fr in frames]
        toe = [fr['pos'].get('B-toe.' + side + '_tail', fr['pos']['B-foot.' + side]) for fr in frames]
        ball = [fr['pos'].get('B-toe.' + side, fr['pos']['B-foot.' + side]) for fr in frames]
        contact_pt = ball
        low = [fr['foot_low'].get(side) for fr in frames] if mesh else [min(a.z, t.z) for a, t in zip(ankle, toe)]
        ref = floor if (mesh and floor is not None) else min(low)
        under = min(l - ref for l in low)
        lowest = min(low)
        ground = min(b.z for b in ball)
        contact = [i for i, b in enumerate(ball) if b.z - ground < 0.03]
        runs, cur = [], []
        for i in contact:
            if cur and i != cur[-1] + 1:
                runs.append(cur)
                cur = []
            cur.append(i)
        if cur:
            runs.append(cur)
        if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == n - 1:
            runs[0] = runs.pop() + runs[0]
        speeds = []
        for run in runs:
            k = len(run)
            mid = run[int(k * 0.2):max(int(k * 0.2) + 1, int(k * 0.8))]
            for i in mid:
                j = (i + 1) %% n
                speeds.append((contact_pt[j] - contact_pt[i]).xy.length * fps)
        mean = sum(speeds) / len(speeds) if speeds else 0.0
        sd = (sum((v - mean) ** 2 for v in speeds) / len(speeds)) ** 0.5 if speeds else 0.0
        feet[side] = dict(under=under, contact_frames=len(contact), speed=mean, speed_sd=sd,
                          amp_z=max(low) - min(low))
    # колено: позади линии бедро–лодыжка по «вперёд» таза
    knee_back = {'L': 0.0, 'R': 0.0}
    knee_at = {'L': start, 'R': start}
    knee_ang = {'L': [999.0, 0.0], 'R': [999.0, 0.0]}
    hips_rest = rest_wq(arm, 'B-hips')
    series = []
    for fr in frames:
        fwd = (fr['wq']['B-hips'] @ hips_rest.inverted()) @ Vector((0.0, -1.0, 0.0))
        fwd.z = 0.0
        if fwd.length < 1e-4:
            continue
        fwd.normalize()
        for side in ('L', 'R'):
            hip, knee, ankle = fr['pos']['B-thigh.' + side], fr['pos']['B-shin.' + side], fr['pos']['B-foot.' + side]
            u = (ankle - hip).normalized()
            v = knee - hip
            off = v - u * v.dot(u)
            back = -off.dot(fwd)
            if back > knee_back[side]:
                knee_back[side], knee_at[side] = back, fr['f']
            a = math.degrees(math.acos(max(-1.0, min(1.0, (knee - hip).normalized().dot((ankle - knee).normalized())))))
            knee_ang[side][0] = min(knee_ang[side][0], a)
            knee_ang[side][1] = max(knee_ang[side][1], a)
            fr.setdefault('knee', {})[side] = (a, back)
    # локоть и запястье
    elbow = {'L': [999.0, 0.0], 'R': [999.0, 0.0]}
    wrist = {'L': 0.0, 'R': 0.0}
    for fr in frames:
        for side in ('L', 'R'):
            s, e, w = fr['pos']['B-upperArm.' + side], fr['pos']['B-forearm.' + side], fr['pos']['B-hand.' + side]
            a = math.degrees(math.acos(max(-1.0, min(1.0, (e - s).normalized().dot((w - e).normalized())))))
            elbow[side][0] = min(elbow[side][0], a)
            elbow[side][1] = max(elbow[side][1], a)
            hq = fr['wq']['B-hand.' + side]
            fq = fr['wq']['B-forearm.' + side]
            fy = fq @ Vector((0.0, 1.0, 0.0))
            hy = hq @ Vector((0.0, 1.0, 0.0))
            wrist[side] = max(wrist[side], math.degrees(math.acos(max(-1.0, min(1.0, fy.dot(hy))))))
    for i, fr in enumerate(frames):
        prev = frames[i - 1] if i > 0 else None
        series.append(dict(f=fr['f'],
                           knee={s: fr.get('knee', {}).get(s, (0.0, 0.0)) for s in ('L', 'R')},
                           low={s: (fr['foot_low'].get(s, 0.0) - (floor or 0.0)) if mesh else 0.0 for s in ('L', 'R')},
                           hips_z=fr['pos']['B-hips'].z, hips_y=fr['pos']['B-hips'].y,
                           lstep={b: (ang(prev['lq'][b], fr['lq'][b]) if prev else 0.0) for b in bones},
                           wstep={b: (ang(prev['wq'][b], fr['wq'][b]) if prev else 0.0) for b in bones},
                           ankle={s: list(fr['pos']['B-foot.' + s]) for s in ('L', 'R')},
                           leg_d={s: (fr['pos']['B-foot.' + s] - fr['pos']['B-thigh.' + s]).length for s in ('L', 'R')}))
    return dict(name=name, frames=n, start=start, end=end, mesh=bool(mesh), floor=floor,
                step=step, step_at=step_at, worst=worst, wstep=wstep, wrap=wrap, wrap_worst=wrap_worst, series=series,
                hips_wrap=(hips1 - hips0).length, hips_z=(min(hz), max(hz)), drift=drift,
                feet=feet, knee_back=knee_back, knee_at=knee_at, knee_ang=knee_ang, elbow=elbow, wrist=wrist)


def diff(a_spec, b_spec):
    arm, mesh = load(a_spec)
    sa = sample(arm, mesh)
    arm, mesh = load(b_spec)
    sb = sample(arm, mesh)
    fa, fb = sa[3], sb[3]
    n = min(len(fa), len(fb))
    bones = [b for b in KEY if b in fa[0]['wq'] and b in fb[0]['wq']]
    per = {b: 0.0 for b in bones}
    per_at = {b: 0 for b in bones}
    pos = 0.0
    for i in range(n):
        for b in bones:
            d = ang(fa[i]['wq'][b], fb[i]['wq'][b])
            if d > per[b]:
                per[b], per_at[b] = d, fa[i]['f']
            p = (fa[i]['pos'][b] - fb[i]['pos'][b]).length
            pos = max(pos, p)
    return dict(frames_a=len(fa), frames_b=len(fb), per=per, per_at=per_at, pos=pos)


results = []
if TASK.get('diff'):
    results.append(diff(*TASK['diff']))
else:
    for spec in TASK['clips']:
        name = spec.split('/')[-1].split('.')[0] + (('#' + spec.split('#')[1]) if '#' in spec else '')
        try:
            arm, mesh = load(spec)
            if arm is None:
                results.append(dict(name=name, error='нет арматуры с действием'))
                continue
            results.append(analyse(name, arm, mesh, TASK.get('loop', {}).get(name)))
        except Exception as e:
            import traceback
            results.append(dict(name=name, error=traceback.format_exc()[-800:]))
json.dump(results, open(OUT, 'w'), default=lambda o: list(o) if hasattr(o, '__iter__') else str(o), indent=1)
print('PROBE DONE', len(results))
'''


def run_blender(task):
    fd, out = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    fd, tpath = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    json.dump(task, open(tpath, 'w'))
    fd, spath = tempfile.mkstemp(suffix='.py')
    os.close(fd)
    open(spath, 'w').write(INNER % dict(task=tpath, out=out))
    proc = subprocess.run([BLENDER, '-b', '--python', spath], capture_output=True, text=True)
    if 'PROBE DONE' not in proc.stdout:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:])
        sys.exit(1)
    return json.load(open(out))


def loop_meta(name):
    meta = os.path.join(RES, name + '.fbx.meta')
    if not os.path.exists(meta):
        return None
    for line in open(meta):
        if 'loopTime:' in line:
            return line.strip().endswith('1')
    return None


def report(r, loop):
    if 'error' in r:
        return '%-16s ОШИБКА %s' % (r['name'], r['error'].strip().splitlines()[-1])
    flags = []
    st = r['step'][r['worst']]
    wr = r['wrap'][r['wrap_worst']]
    fl = r['feet']['L']
    fr = r['feet']['R']
    under = min(fl['under'], fr['under'])
    if st > 10.0:
        flags.append('РЫВОК %s %.0f°@%d' % (r['worst'].replace('B-', ''), st, r['step_at'][r['worst']]))
    if loop and wr > max(3.0, 1.5 * st):
        flags.append('ЛУП %s %.1f°' % (r['wrap_worst'].replace('B-', ''), wr))
    if loop and r['hips_wrap'] > 0.02:
        flags.append('ЛУП таз %.2fм' % r['hips_wrap'])
    if r['mesh'] and under < -0.012:
        flags.append('ПОД ПОЛОМ %.1fсм' % (under * 100.0))
    if fl['speed'] > 0.2 and fr['speed'] > 0.2:
        asym = abs(fl['speed'] - fr['speed']) / max(fl['speed'], fr['speed'])
        if asym > 0.12:
            flags.append('L/R скорость %.0f%%' % (asym * 100.0))
        sd = max(fl['speed_sd'] / max(fl['speed'], 1e-6), fr['speed_sd'] / max(fr['speed'], 1e-6))
        if sd > 0.35:
            flags.append('СКОЛЬЖЕНИЕ разброс %.0f%%' % (sd * 100.0))
    kb = max(r['knee_back']['L'], r['knee_back']['R'])
    if kb > 0.012:
        side = 'L' if r['knee_back']['L'] >= r['knee_back']['R'] else 'R'
        flags.append('КОЛЕНО назад %.1fсм@%d' % (kb * 100.0, r['knee_at'][side]))
    line = ('%-16s %3d к  шаг %5.1f°/к (%s@%d, мир %.0f°)  стык %4.1f° (%s)  пол %+5.1fсм  опора L %.2f±%.2f R %.2f±%.2f м/с  колено %s/%s'
            % (r['name'], r['frames'], st, r['worst'].replace('B-', ''), r['step_at'][r['worst']], r['wstep'][r['worst']], wr,
               r['wrap_worst'].replace('B-', ''), under * 100.0 if r['mesh'] else float('nan'),
               fl['speed'], fl['speed_sd'], fr['speed'], fr['speed_sd'],
               '%.0f-%.0f' % tuple(r['knee_ang']['L']), '%.0f-%.0f' % tuple(r['knee_ang']['R'])))
    return line + ('   ⚠ ' + '; '.join(flags) if flags else '   ok')


def main(argv):
    if '--diff' in argv:
        i = argv.index('--diff')
        a, b = argv[i + 1], argv[i + 2]
        d = run_blender({'diff': [a, b]})[0]
        print('кадров %d / %d, позиция до %.1f мм' % (d['frames_a'], d['frames_b'], d['pos'] * 1000.0))
        for bone, v in sorted(d['per'].items(), key=lambda kv: -kv[1])[:8]:
            print('  %-14s %6.2f° @%d' % (bone, v, d['per_at'][bone]))
        return
    trace = None
    if '--trace' in argv:
        i = argv.index('--trace')
        trace = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    out_json = None
    if '--json' in argv:
        i = argv.index('--json')
        out_json = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    files = []
    if '--file' in argv:
        i = argv.index('--file')
        files.append(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    names = [a for a in argv if not a.startswith('--')]
    if not names and not files:
        names = sorted(f[:-4] for f in os.listdir(RES) if f.endswith('.fbx') and not f.startswith(SKIP))
    clips = [os.path.join(RES, n + '.fbx') for n in names] + files
    loops = {n: loop_meta(n) for n in names}
    results = run_blender({'clips': clips, 'loop': loops})
    for r in results:
        print(report(r, loops.get(r['name'].split('#')[0])))
        if trace and 'series' in r:
            b = 'B-' + trace
            print('  кадр  колено L(°,назад см)  R        низ L/R см   таз y/z        лодыжка L x,y        R x,y      бедро-лодыжка L/R   шаг %s лок/мир' % trace)
            for e in r['series']:
                print('  %4d  %5.1f %5.1f   %5.1f %5.1f   %5.1f %5.1f   %+.3f %.3f   %+.3f %+.3f   %+.3f %+.3f   %.2f %.2f   %5.1f %5.1f'
                      % (e['f'], e['knee']['L'][0], e['knee']['L'][1] * 100, e['knee']['R'][0], e['knee']['R'][1] * 100,
                         e['low']['L'] * 100, e['low']['R'] * 100, e['hips_y'], e['hips_z'],
                         e['ankle']['L'][0], e['ankle']['L'][1], e['ankle']['R'][0], e['ankle']['R'][1],
                         e.get('leg_d', {}).get('L', 0.0), e.get('leg_d', {}).get('R', 0.0),
                         e['lstep'].get(b, 0.0), e['wstep'].get(b, 0.0)))
    if out_json:
        json.dump(results, open(out_json, 'w'), indent=1, ensure_ascii=False)
        print('json:', out_json)


if __name__ == '__main__':
    main(sys.argv[1:])
