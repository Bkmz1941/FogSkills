#!/usr/bin/env python3
"""Замеры роликов стычки с вороной — то, что глазами не ловится.

  blender -b <клип>.blend --python crow_fight_probe.py -- arms      # руки по кадрам
  blender -b <клип>.blend --python crow_fight_probe.py -- palm      # разворот ладони
  blender -b <клип>.blend --python crow_fight_probe.py -- len       # длина в секундах
  blender -b <клип>.blend --python crow_fight_probe.py -- seam N f  # выгрузить стык в f
  blender -b <клип>.blend --python crow_fight_probe.py -- path 80 96 1  # путь кисти к голове
  blender -b <клип>.blend --python crow_fight_probe.py -- body      # габариты тела в осях головы
  blender -b <клип>.blend --python crow_fight_probe.py -- loop      # длина и смыкание лупа
  blender -b <клип>.blend --python crow_fight_probe.py -- hand R 1 24 1  # ладонь, излом, крен одной кисти по кадрам

Стык сверяется двумя выгрузками: последний кадр Crow_Brace и первый кадр
развязки, затем `seamdiff a.json b.json`.
"""
import bpy, sys, math, json, os
from mathutils import Vector

HERE = '/media/ilya/T714/Unity/Tavern-fresh/BlenderWork'
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import anim_common as A

K = 1.82 / 2.55
BODY = ('B-hips', 'B-spine', 'B-chest', 'B-thigh.L', 'B-thigh.R')


def parts():
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
    return arm, mesh


def limb(n, side):
    return n.endswith('.' + side) and any(
        w in n for w in ('forearm', 'hand', 'Finger', 'thumb', 'pinky'))


def verts(mesh, pred):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    groups = {g.index: g.name for g in mesh.vertex_groups}
    m = mesh.matrix_world
    out = []
    for v in ev.data.vertices:
        top = max(v.groups, key=lambda g: g.weight, default=None)
        if top is None or top.weight <= 0.5:
            continue
        if pred(groups.get(top.group, '')):
            out.append(m @ v.co)
    return out


def elbow(arm, side):
    m3 = arm.matrix_world.to_3x3()
    u = arm.pose.bones['B-upperArm.' + side]
    f = arm.pose.bones['B-forearm.' + side]
    a = (m3 @ (u.tail - u.head)).normalized()
    b = (m3 @ (f.tail - f.head)).normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


def head_centre(mesh):
    lo = Vector((A.extent_of(mesh, lambda n: n == 'B-head', i, lo=True) for i in range(3)))
    hi = Vector((A.extent_of(mesh, lambda n: n == 'B-head', i, lo=False) for i in range(3)))
    return (lo + hi) * 0.5


def run_arms(step=6):
    """Зазор руки до КОРПУСА и угол в локте. ⚠️ Мерить надо оба: зазор без угла
    не ловит прямую руку-палку, угол без зазора не ловит прижатие к телу."""
    arm, mesh = parts()
    sc = bpy.context.scene
    print('кадр  правая↔корпус  левая↔корпус  локоть L  локоть R')
    for fr in range(sc.frame_start, sc.frame_end + 1, step):
        sc.frame_set(fr)
        body = verts(mesh, lambda n: n in BODY)
        row = []
        for sd in 'RL':
            lm = verts(mesh, lambda n, s=sd: limb(n, s))
            d = min((a - b).length for a in lm for b in body) / K * 100.0 if lm and body else 99.0
            row.append(d)
        print('%4d   %+9.1f см %+9.1f см   %6.1f°  %6.1f°'
              % (fr, row[0], row[1], elbow(arm, 'L'), elbow(arm, 'R')))


def run_palm(step=6):
    """Угол между нормалью ладони и направлением на голову. ⚠️ `aim` скрутку
    кисти НЕ переносит: если ключи клались направлениями, тут будет уход."""
    arm, mesh = parts()
    sc = bpy.context.scene
    print('кадр  ладонь→голова  локоть L  кисть↔голова')
    for fr in range(sc.frame_start, sc.frame_end + 1, step):
        sc.frame_set(fr)
        m3 = arm.matrix_world.to_3x3()
        pb = arm.pose.bones['B-hand.L']
        wrist = arm.matrix_world @ pb.head
        palm = (m3 @ (pb.matrix.to_3x3() @ Vector((0.0, 0.0, 1.0)))).normalized()
        to_head = head_centre(mesh) - wrist
        ang = math.degrees(math.acos(max(-1.0, min(1.0, palm.dot(to_head.normalized())))))
        print('%4d     %6.0f°     %6.1f°   %6.1f см'
              % (fr, ang, elbow(arm, 'L'), to_head.length / K * 100.0))


def run_len():
    sc = bpy.context.scene
    n = sc.frame_end - sc.frame_start + 1
    print('%s: кадры %d..%d при %d к/с = %.2f с'
          % (os.path.basename(bpy.data.filepath), sc.frame_start, sc.frame_end,
             sc.render.fps, n / float(sc.render.fps)))


def run_seam(frame, out):
    arm, mesh = parts()
    sc = bpy.context.scene
    sc.frame_set(frame)
    crow = next(o for o in bpy.data.objects
                if o.parent is None and o.name.startswith('Crow_'))
    cam = sc.camera
    fwd = (cam.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    json.dump(dict(crow_loc=[v / K for v in crow.location],
                   crow_rot=list(crow.rotation_euler),
                   head=[v / K for v in head_centre(mesh)],
                   cam_loc=list(cam.matrix_world.translation),
                   cam_fwd=list(fwd), lens=cam.data.lens,
                   bones={pb.name: list((arm.matrix_world @ pb.matrix).to_quaternion().normalized())
                          for pb in arm.pose.bones}),
              open(out, 'w'))
    print('выгружено', out)


def head_axes(arm):
    """Оси головы сидящего, как `head_axes` в crow_fight.py: верх — ось кости
    B-head, лицо — от груди без составляющей вдоль верха, бок — up × face со
    знаком по плечам. У откинутого корпуса мировые оси не годятся."""
    mh = (arm.matrix_world @ arm.pose.bones['B-head'].matrix).to_3x3()
    up = (mh @ Vector((0.0, 1.0, 0.0))).normalized()
    rest = (arm.matrix_world @ arm.pose.bones['B-chest'].bone.matrix_local).to_3x3().inverted()
    mc = (arm.matrix_world @ arm.pose.bones['B-chest'].matrix).to_3x3()
    face = (mc @ (rest @ Vector((0.0, -1.0, 0.0)))).normalized()
    face = (face - up * face.dot(up)).normalized()
    side = up.cross(face).normalized()
    sh = arm.matrix_world @ arm.pose.bones['B-upperArm.R'].head
    if (sh - (arm.matrix_world @ arm.pose.bones['B-upperArm.L'].head)).dot(side) < 0.0:
        side = -side
    return side, face, up, sh


def run_path(lo=80, hi=96, step=1, sd='R'):
    """Путь кисти к голове: запястье и ЛОКОТЬ в осях головы, радиус от плеча,
    угол локтя, зазоры ПО ЧАСТЯМ (предплечье и кисть отдельно). ⚠️ Мерить надо
    и локоть: на изломе кусочного пути он разворачивается за два кадра на 110°,
    а на запястье этого не видно (P401). Зазор по частям — потому что пальцы
    висят на 0.25 м ниже запястья и метут по бедру, когда предплечье смотрит
    вниз (P400)."""
    arm, mesh = parts()
    sc = bpy.context.scene
    print('кадр  запястье(бок/лицо/верх)   локоть(бок/лицо/верх)  R пл.  локоть°  предплечье↔тело  кисть↔тело')
    for fr in range(lo, hi + 1, step):
        sc.frame_set(fr)
        side, face, up, sh = head_axes(arm)
        hc = head_centre(mesh)
        wr = arm.matrix_world @ arm.pose.bones['B-forearm.' + sd].tail
        el = arm.matrix_world @ arm.pose.bones['B-forearm.' + sd].head
        body = verts(mesh, lambda n: n in BODY or n.startswith('B-shin'))
        fore = verts(mesh, lambda n: n == 'B-forearm.' + sd)
        hand = verts(mesh, lambda n: n.endswith('.' + sd) and any(
            w in n for w in ('hand', 'Finger', 'thumb', 'pinky')))
        gf = min((p - q).length for p in fore for q in body) / K * 100.0 if fore and body else 99.9
        gh = min((p - q).length for p in hand for q in body) / K * 100.0 if hand and body else 99.9
        dw, de = (wr - hc) / K, (el - hc) / K
        print('%4d  %+5.2f %+5.2f %+5.2f      %+5.2f %+5.2f %+5.2f   %4.2f   %4.0f°   %6.1f см   %6.1f см'
              % (fr, dw.dot(side), dw.dot(face), dw.dot(up), de.dot(side), de.dot(face), de.dot(up),
                 (wr - sh).length / K, elbow(arm, sd), gf, gh))


def run_body(frame=1):
    """Габариты групп тела в осях головы — куда кисти ходить НЕЛЬЗЯ."""
    arm, mesh = parts()
    sc = bpy.context.scene
    sc.frame_set(frame)
    side, face, up, sh = head_axes(arm)
    hc = head_centre(mesh)
    print('в осях головы (бок/лицо/верх), игровые м:')
    for g in ('B-hips', 'B-spine', 'B-chest', 'B-thigh.R', 'B-shin.R', 'B-thigh.L', 'B-shin.L'):
        pts = [(p - hc) / K for p in verts(mesh, lambda n, g=g: n == g)]
        if not pts:
            continue
        print('  %-12s бок %+.2f..%+.2f  лицо %+.2f..%+.2f  верх %+.2f..%+.2f'
              % (g.replace('B-', ''), min(p.dot(side) for p in pts), max(p.dot(side) for p in pts),
                 min(p.dot(face) for p in pts), max(p.dot(face) for p in pts),
                 min(p.dot(up) for p in pts), max(p.dot(up) for p in pts)))
    d = (sh - hc) / K
    print('  плечо R      бок %+.2f  лицо %+.2f  верх %+.2f' % (d.dot(side), d.dot(face), d.dot(up)))


def run_hand(sd='R', lo=None, hi=None, step=1):
    """Ладонь ОДНОЙ кисти по кадрам: нормаль в осях (наружу, вперёд, вверх),
    излом запястья, крен кисти к покою и худшие шаги между соседними кадрами.
    Пороги закона анатомии руки: ладонь ≤ 15°/кадр, излом ≤ 8°/кадр, крен
    (скрутка) ≤ 15°/кадр. Крен к покою — угол между фактической нормалью
    ладони и той, что даёт кисть без своего поворота относительно предплечья
    (`rest_hand_z`); знак — вокруг оси кисти."""
    arm, _ = parts()
    sc = bpy.context.scene
    mw = arm.matrix_world
    lo = lo or sc.frame_start
    hi = hi or sc.frame_end
    sx = 1.0 if sd == 'L' else -1.0
    axes = lambda v: (sx * v.x, -v.y, v.z)
    bf, bh = arm.data.bones['B-forearm.' + sd], arm.data.bones['B-hand.' + sd]
    rest = (bf.matrix_local.to_3x3().inverted() @ (bh.matrix_local.to_3x3() @ Vector((0.0, 0.0, 1.0)))).normalized()
    prev, worst = None, dict(palm=0.0, bend=0.0, roll=0.0)
    print('%s: кадр | ладонь (нар,вп,вв) | излом | крен к покою | шаг ладони | шаг излома' % sd)
    for fr in range(lo, hi + 1, step):
        sc.frame_set(fr)
        fo, ha = arm.pose.bones['B-forearm.' + sd], arm.pose.bones['B-hand.' + sd]
        m3 = mw.to_3x3()
        fdir = (m3 @ (fo.tail - fo.head)).normalized()
        hdir = (m3 @ (ha.tail - ha.head)).normalized()
        palm = ((mw @ ha.matrix).to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
        nat = ((mw @ fo.matrix).to_3x3() @ rest).normalized()
        bend = math.degrees(fdir.angle(hdir))
        n_p = (nat - hdir * nat.dot(hdir)).normalized()
        p_p = (palm - hdir * palm.dot(hdir)).normalized()
        roll = math.degrees(n_p.angle(p_p))
        if hdir.dot(n_p.cross(p_p)) < 0.0:
            roll = -roll
        dp = db = 0.0
        if prev is not None:
            dp, db = math.degrees(prev[0].angle(palm)), abs(prev[1] - bend)
            worst['palm'] = max(worst['palm'], dp)
            worst['bend'] = max(worst['bend'], db)
            worst['roll'] = max(worst['roll'], abs(prev[2] - roll))
        prev = (palm, bend, roll)
        print('%4d | %+.2f %+.2f %+.2f | %4.0f° | %+5.0f° | %5.1f° | %5.1f°'
              % ((fr,) + axes(palm) + (bend, roll, dp, db)))
    print('худший шаг за %d кадр: ладонь %.1f°  излом %.1f°  крен %.1f°'
          % (step, worst['palm'], worst['bend'], worst['roll']))


def run_loop():
    """Длина клипа и смыкание лупа: худшая кость между первым и последним кадром."""
    arm, _ = parts()
    sc = bpy.context.scene
    run_len()
    snap = lambda: {pb.name: (arm.matrix_world @ pb.matrix).to_quaternion().normalized()
                    for pb in arm.pose.bones}
    sc.frame_set(sc.frame_start)
    a = snap()
    sc.frame_set(sc.frame_end)
    b = snap()
    worst = max((math.degrees(a[k].rotation_difference(b[k]).angle), k) for k in a)
    print('луп: худшая кость между первым и последним кадром — %s %.2f°' % (worst[1], worst[0]))


def face_axes(arm):
    """Оси ЛИЦА от кости B-head (бок наружу вправо, лицо, верх): в падении
    голова отвёрнута от груди до 58°, и оси груди для ладоней на лице врут."""
    b = arm.pose.bones['B-head']
    rest = (arm.matrix_world @ b.bone.matrix_local).to_3x3().inverted()
    m = (arm.matrix_world @ b.matrix).to_3x3()
    fwd = (m @ (rest @ Vector((0.0, -1.0, 0.0)))).normalized()
    up = (m @ (rest @ Vector((0.0, 0.0, 1.0)))).normalized()
    side = up.cross(fwd).normalized()
    sh = lambda sd: arm.matrix_world @ arm.pose.bones['B-upperArm.' + sd].head
    if (sh('R') - sh('L')).dot(side) < 0.0:
        side = -side
    return side, fwd, up


def owners(mesh):
    dg = bpy.context.evaluated_depsgraph_get()
    me = mesh.evaluated_get(dg).data
    groups = {g.index: g.name for g in mesh.vertex_groups}
    m = mesh.matrix_world
    verts = [m @ v.co for v in me.vertices]
    owner = []
    for v in me.vertices:
        top = max(v.groups, key=lambda g: g.weight, default=None)
        owner.append(groups.get(top.group, '') if top is not None and top.weight > 0.5 else '')
    return verts, owner, [tuple(p.vertices) for p in me.polygons]


def closed_head(verts, owner, polys):
    """Грани головы + крышка на дыре шеи веером от центра кромки: по открытой
    оболочке чётность луча врёт в обе стороны (P432)."""
    faces = [list(p) for p in polys if all(owner[i] == 'B-head' for i in p)]
    edges = {}
    for p in faces:
        for i in range(len(p)):
            e = tuple(sorted((p[i], p[(i + 1) % len(p)])))
            edges[e] = edges.get(e, 0) + 1
    rim = [e for e, n in edges.items() if n == 1]
    verts = list(verts)
    if rim:
        ids = sorted({i for e in rim for i in e})
        verts.append(sum((verts[i] for i in ids), Vector()) / len(ids))
        faces += [[a, b, len(verts) - 1] for a, b in rim]
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons(verts, faces, all_triangles=False)


def inside(tree, p, d=Vector((0.37, 0.61, 0.70)).normalized()):
    o, hits = p.copy(), 0
    for _ in range(64):
        loc, _, _, _ = tree.ray_cast(o, d, 10.0)
        if loc is None:
            break
        hits += 1
        o = loc + d * 1e-5
    return hits % 2 == 1


def run_face(frames):
    """Ладони на лице (сцена 5): направление и нормаль кисти в осях лица, излом,
    вершины кисти ВНУТРИ головы (по костям, чётность по закрытой оболочке),
    зазор до кожи, угол между кистями и между ладонями, зазор кисть↔кисть."""
    from mathutils.kdtree import KDTree
    arm, mesh = parts()
    sc, mw = bpy.context.scene, arm.matrix_world
    hand = lambda n, sd: n.endswith('.' + sd) and any(w in n for w in ('hand', 'Finger', 'thumb', 'pinky'))
    print('кадр | S | кисть (нар,лиц,вв) | ладонь (нар,лиц,вв) | излом° | внутри головы | до кожи см || кисти° | ладони° | L↔R см')
    for fr in frames:
        sc.frame_set(fr)
        side, fwd, up = face_axes(arm)
        verts, owner, polys = owners(mesh)
        tree = closed_head(verts, owner, polys)
        hv = [verts[i] for i in range(len(verts)) if owner[i] == 'B-head']
        kd = KDTree(len(hv))
        for i, p in enumerate(hv):
            kd.insert(p, i)
        kd.balance()
        c = (Vector((min(p.x for p in hv), min(p.y for p in hv), min(p.z for p in hv)))
             + Vector((max(p.x for p in hv), max(p.y for p in hv), max(p.z for p in hv)))) * 0.5
        rows, dirs, palms, pts = [], {}, {}, {}
        for sd, sgn in (('L', -1.0), ('R', 1.0)):
            fo, ha = arm.pose.bones['B-forearm.' + sd], arm.pose.bones['B-hand.' + sd]
            fdir = (mw.to_3x3() @ (fo.tail - fo.head)).normalized()
            hdir = (mw.to_3x3() @ (ha.tail - ha.head)).normalized()
            palm = ((mw @ ha.matrix).to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
            ax = lambda v: (sgn * v.dot(side), v.dot(fwd), v.dot(up))
            idx = [i for i in range(len(verts)) if hand(owner[i], sd)]
            pts[sd] = [verts[i] for i in idx]
            by = {}
            for i in idx:
                if inside(tree, verts[i]):
                    n = owner[i].replace('B-', '').replace('Finger', 'F')
                    by[n] = by.get(n, 0) + 1
            if by:
                print('      %s внутри головы: %s' % (sd, ' '.join('%s:%d' % kv for kv in sorted(by.items()))))
            gap = min(kd.find(p)[2] for p in pts[sd]) / 0.71 * 100.0
            dirs[sd], palms[sd] = hdir, palm
            rows.append('%4d | %s | %+.2f %+.2f %+.2f | %+.2f %+.2f %+.2f | %4.0f | %4d | %5.1f'
                        % ((fr, sd) + ax(hdir) + ax(palm) + (math.degrees(fdir.angle(hdir)), sum(by.values()), gap)))
        kl = KDTree(len(pts['L']))
        for i, p in enumerate(pts['L']):
            kl.insert(p, i)
        kl.balance()
        lr = min(kl.find(p)[2] for p in pts['R']) / 0.71 * 100.0
        print(rows[0])
        print(rows[1] + ' || %5.1f | %5.1f | %5.1f' % (math.degrees(dirs['L'].angle(dirs['R'])),
                                                        math.degrees(palms['L'].angle(palms['R'])), lr))


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['arms']
    if a[0] == 'arms':
        run_arms(int(a[1]) if len(a) > 1 else 6)
    elif a[0] == 'palm':
        run_palm(int(a[1]) if len(a) > 1 else 6)
    elif a[0] == 'len':
        run_len()
    elif a[0] == 'seam':
        run_seam(int(a[1]), a[2])
    elif a[0] == 'path':
        run_path(*(int(x) for x in a[1:4]))
    elif a[0] == 'body':
        run_body(int(a[1]) if len(a) > 1 else 1)
    elif a[0] == 'loop':
        run_loop()
    elif a[0] == 'hand':
        run_hand(a[1] if len(a) > 1 else 'R', *(int(x) for x in a[2:5]))
    elif a[0] == 'face':
        run_face([int(x) for x in a[1:]] or [47, 49, 58, 68, 110])
