"""Testbild: Figuren nebeneinander + Nahaufnahmen (zum Prüfen des Modellings).
  blender -b --factory-startup -P blender/lineup.py -- <out.png> [figur,figur,...]"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A
import chars as C
import cast

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = argv[0] if argv else 'lineup.png'
keys = argv[1].split(',') if len(argv) > 1 else ['gojo', 'sukuna', 'megumi', 'mahito', 'jogo']
A.reset_scene()
A.setup_render(1, res=(1920, 1080), samples=16, motion_blur=False)
A.set_world_color((0.55, 0.58, 0.64), 1.0)
A.sun(3.0, rot=(math.radians(50), math.radians(10), math.radians(-25)))
A.ink()
gap = 0.9
figs = []
for i, k in enumerate(keys):
    x = (i - (len(keys) - 1) / 2) * gap
    f = cast.build_char(k, k.capitalize(), loc=(x, 0, 0), facing=0)
    C.pose(f, 1, **{'upper.L': (0, -6, 6), 'upper.R': (0, 6, -6), 'fore.L': (-10, 0, 0), 'fore.R': (-10, 0, 0)})
    figs.append((k, x, f))
cam, tgt = A.camera(lens=28)
s = bpy.context.scene
w = max(1, len(keys)) * gap
A.cam_key(cam, tgt, 1, (0, -2.2 - w * 1.3, 1.2), (0, 0, 1.0), 35)
s.frame_set(1)
s.render.filepath = out
bpy.ops.render.render(write_still=True)
s.render.resolution_x, s.render.resolution_y = 960, 960
for k, x, f in figs:
    z = 1.76 * (f['arm'].scale.z)
    for tag, pos, lens in (('face', (x + 0.2, -1.25, z + 0.06), 62), ('body', (x + 0.5, -3.0, 1.1 * f['arm'].scale.z), 45)):
        A.cam_key(cam, tgt, 1, pos, (x, 0, z + 0.05 if tag == 'face' else 1.0 * f['arm'].scale.z), lens)
        s.frame_set(1)
        s.render.filepath = out.replace('.png', '_%s_%s.png' % (k, tag))
        bpy.ops.render.render(write_still=True)
print('FERTIG')
