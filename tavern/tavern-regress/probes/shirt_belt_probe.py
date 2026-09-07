# Футболка накрывает ремень/шлёвки/пряжку джинс и резинку/шнурки домашних штанов (INVARIANTS 60, P219). Запуск: мостом (exec) или
#   blender -b Library/humanClothes.blend -P shirt_belt_probe.py  — печатает виды с красными пикселями, ждём {}.
import bpy, math, os
import numpy as np
from mathutils import Vector
OUT = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'shirt_belt_probe/')
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; cam = bpy.data.objects['_VarCam']
shd = sc.display.shading
saved = dict(cam=sc.camera, engine=sc.render.engine, frame=sc.frame_current, rx=sc.render.resolution_x, ry=sc.render.resolution_y,
             ctype=shd.color_type, light=shd.light, shadows=shd.show_shadows, cavity=shd.show_cavity, bg=shd.background_type,
             hide={o.name: o.hide_render for o in bpy.data.objects}, colors={o.name: tuple(o.color) for o in bpy.data.objects})
sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x, sc.render.resolution_y = 480, 600
shd.color_type = 'OBJECT'; shd.light = 'FLAT'; shd.show_shadows = False; shd.show_cavity = False
FIG = {'': (bpy.data.objects['Armature_Cut'].location.x, [0]),
       '_Idle': (bpy.data.objects['Armature_Idle_Cut'].location.x, [1, 20, 40]),
       '_Home': (bpy.data.objects['Armature_Home_Cut'].location.x, [1, 20, 40]),
       '_Walk': (bpy.data.objects['Armature_Walk_Cut'].location.x, [1, 8, 15, 22, 29, 36])}
RED = ('Belt', 'Loops', 'Buckle', 'Waistband', 'Cord0', 'Cord1')
WHITE = ('Shirt', 'ShirtCollar', 'Pants', 'Pockets', 'Cuffs')
def look(target, dist, yaw, pitch):
    d = Vector((math.cos(pitch)*math.sin(yaw), -math.cos(pitch)*math.cos(yaw), math.sin(pitch)))*dist
    cam.location = Vector(target) + d
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
report = {}
for suf, (fx, frames) in FIG.items():
    for o in bpy.data.objects:
        o.hide_render = True
    for base in RED + WHITE:
        ob = bpy.data.objects.get(base + suf + '_Cut')
        if ob is None:
            continue
        ob.hide_render = False
        ob.color = (1, 0, 0, 1) if base in RED else (1, 1, 1, 1)
    for fr in frames:
        sc.frame_set(fr)
        for yaw in (0, 90, 180, 270, 45, 225):
            for pitch in (30, 5):
                look((fx, 0.0, 1.05), 2.0, math.radians(yaw), math.radians(pitch))
                path = OUT + 'p%s_f%d_y%d_p%d.png' % (suf or '_Rest', fr, yaw, pitch)
                sc.render.filepath = path
                bpy.ops.render.render(write_still=True)
                img = bpy.data.images.load(path)
                px = np.array(img.pixels[:]).reshape(-1, 4)
                bpy.data.images.remove(img)
                red = int(np.sum((px[:, 0] > 0.6) & (px[:, 1] < 0.3) & (px[:, 2] < 0.3)))
                report['%s f%d y%d p%d' % (suf or 'Rest', fr, yaw, pitch)] = red
                if red == 0:
                    os.remove(path)
for o in bpy.data.objects:
    o.hide_render = saved['hide'][o.name]
    o.color = saved['colors'][o.name]
sc.camera = saved['cam']; sc.render.engine = saved['engine']; sc.frame_set(saved['frame'])
sc.render.resolution_x, sc.render.resolution_y = saved['rx'], saved['ry']
shd.color_type = saved['ctype']; shd.light = saved['light']; shd.show_shadows = saved['shadows']; shd.show_cavity = saved['cavity']
RESULT = {k: v for k, v in report.items() if v > 0}
RESULT['_renders'] = len(report)
print('[shirt_belt_probe]', RESULT)
