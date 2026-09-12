#!/usr/bin/env python3
"""Замеры роликов стычки с вороной — то, что глазами не ловится.

  blender -b <клип>.blend --python crow_fight_probe.py -- arms      # руки по кадрам
  blender -b <клип>.blend --python crow_fight_probe.py -- palm      # разворот ладони
  blender -b <клип>.blend --python crow_fight_probe.py -- len       # длина в секундах
  blender -b <клип>.blend --python crow_fight_probe.py -- seam N f  # выгрузить стык в f

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
