"""Одетый герой в ДВИЖЕНИИ, как в игре: кожа не выходит сквозь штаны (INVARIANTS 57, P205).

Headless Blender: берутся ИГРОВЫЕ файлы — тело `HumanCharacterDummy_M_Skin.fbx`
и штаны `Clothes/JeansM.fbx` (упрощённые сетки и жёсткие веса, ровно то, что
скинит Unity), оба сажаются на арматуры ходьбы и стойки из файла одежды (те же
клипы, что в игре), коже между подолом и поясом даётся красный материал,
кадры рендерятся с трёх сторон и считаются красные пиксели. Замер по плотным
сеткам файла одежды врал: в игре другие сетки и веса (P205, P208).

Запуск: python3 ~/.claude/skills/tavern-regress/probes/worn_jeans_pose_probe.py [JeansM|HomePantsM|TShirtM]
Для TShirtM красная кожа — торс под футболкой (|x|<0.21, z 0.98..1.47) и плечи под рукавами (|x| 0.21..0.30, z 1.36..1.55), камера на z 1.2.
"""
import glob, os, subprocess, sys, tempfile

BLENDER = '/media/ilya/T714/Tools/blender-4.2.3-linux-x64/blender'
CLOTHES = '/media/ilya/T714/Unity/Tavern-fresh/BlenderWork/Library/humanClothes.blend'
RES = '/media/ilya/T714/Unity/Tavern-fresh/Assets/Game/Resources/'
LIMIT = 40
GARMENT = sys.argv[1] if len(sys.argv) > 1 else 'JeansM'
INNER = r'''
import bpy, math
from mathutils import Vector
OUT = %r
RES = %r
GARMENT = %r
def import_fbx(path):
    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o.name not in before]
red = bpy.data.materials.new('_poke_red'); red.diffuse_color = (1.0, 0.0, 0.0, 1.0)
tan = bpy.data.materials.new('_poke_tan'); tan.diffuse_color = (0.85, 0.62, 0.48, 1.0)
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type in ('MESH', 'FONT'):
        o.hide_render = True
def bind(objs, arm):
    from mathutils import Matrix
    for o in objs:
        if o.type != 'MESH':
            continue
        local = o.matrix_local.copy()
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = local
        for m in list(o.modifiers):
            if m.type == 'ARMATURE':
                o.modifiers.remove(m)
        am = o.modifiers.new('Armature', 'ARMATURE'); am.object = arm
        o.hide_render = False
figs = []
for suffix, x, tag in (('_Walk_Cut', 4.8, 'walk'), ('_Idle_Cut', 2.4, 'idle')):
    arm = bpy.data.objects['Armature' + suffix]
    body_all = import_fbx(RES + 'Models/HumanCharacterDummy_M_Skin.fbx')
    jeans_all = import_fbx(RES + 'Clothes/' + GARMENT + '.fbx')
    body = [o for o in body_all if o.type == 'MESH']; jeans = [o for o in jeans_all if o.type == 'MESH']
    bind(body, arm); bind(jeans, arm)
    for o in [o for o in body_all + jeans_all if o.type == 'ARMATURE']:
        bpy.data.objects.remove(o, do_unlink=True)
    skin = max(body, key=lambda o: len(o.data.vertices))
    me = skin.data; me.materials.clear(); me.materials.append(tan); me.materials.append(red)
    mw = arm.matrix_world
    for p in me.polygons:
        c = skin.matrix_world @ p.center
        zz = c.z; xx = abs(c.x - arm.location.x)
        if GARMENT.startswith('TShirt'):
            red_face = (0.98 < zz < 1.47 and xx < 0.21) or (1.36 < zz < 1.55 and 0.21 <= xx < 0.30)
        else:
            red_face = 0.19 < zz < 1.06
        p.material_index = 1 if red_face else 0
    figs.append((tag, x))
bpy.context.view_layer.update()
cd = bpy.data.cameras.new('_PokeCam'); cam = bpy.data.objects.new('_PokeCam', cd); sc.collection.objects.link(cam); cd.lens = 50
sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x, sc.render.resolution_y = 600, 800; sc.render.resolution_percentage = 100
sh = sc.display.shading; sh.light = 'FLAT'; sh.color_type = 'MATERIAL'; sh.show_shadows = False; sh.show_cavity = False
def look(target, dist, yaw, pitch):
    d = Vector((math.cos(pitch)*math.sin(yaw), -math.cos(pitch)*math.cos(yaw), math.sin(pitch)))*dist
    cam.location = Vector(target) + d
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
shots = [('walk', 4.8, f, yaw, pitch) for f in (8, 20, 32, 44, 56, 68) for yaw, pitch in ((-20, 50), (90, 10), (200, 30))]
shots += [('idle', 2.4, 40, yaw, pitch) for yaw, pitch in ((-25, 6), (90, 10), (200, 30))]
for tag, x, f, yaw, pitch in shots:
    sc.frame_set(f)
    look((x, 0.0, 1.2 if GARMENT.startswith('TShirt') else 0.7), 2.0, math.radians(yaw), math.radians(pitch))
    sc.render.filepath = '%%s/%%s_%%d_%%d.png' %% (OUT, tag, f, yaw)
    bpy.ops.render.render(write_still=True)
print('RENDERED', len(shots))
''' 

def main():
    out = tempfile.mkdtemp(prefix='poke_')
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(INNER % (out, RES, GARMENT))
        path = f.name
    try:
        run = subprocess.run(['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=8G',
                              BLENDER, '-b', CLOTHES, '-P', path], capture_output=True, text=True, timeout=900)
    finally:
        os.unlink(path)
    if 'RENDERED' not in run.stdout:
        print(run.stdout[-1500:], run.stderr[-1500:])
        return 1
    from PIL import Image
    worst = 0
    for png in sorted(glob.glob(out + '/*.png')):
        im = Image.open(png).convert('RGB')
        n = sum(1 for r, g, b in im.getdata() if r > 180 and g < 70 and b < 70)
        worst = max(worst, n)
        print('SHOT %s red=%d' % (os.path.basename(png), n))
    print('VERDICT', 'GREEN' if worst <= LIMIT else 'RED worst=%d' % worst, 'renders:', out)
    return 0 if worst <= LIMIT else 1

if __name__ == '__main__':
    sys.exit(main())
