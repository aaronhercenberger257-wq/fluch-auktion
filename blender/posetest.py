"""Posen-Test: eine Figur in mehreren Posen (Bild je Pose, Vorder- und Seitenansicht).
  blender -b --factory-startup -P blender/posetest.py -- <ordner> <figur>"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A
import chars as C
import cast
import fight as FT

argv = sys.argv[sys.argv.index('--') + 1:]
out, who = argv[0], argv[1]
names = argv[2].split(',') if len(argv) > 2 else list(FT.POSES)
A.reset_scene()
A.setup_render(len(names), res=(640, 640), samples=8, motion_blur=False)
A.set_world_color((0.55, 0.58, 0.64), 1.0)
A.sun(3.0)
A.ink()
f = cast.build_char(who, 'T', loc=(0, 0, 0), facing=0)
sc = f['arm'].scale.z
for i, n in enumerate(names):
    FT.apply(f, i + 1, n)
cam, tgt = A.camera(lens=35)
s = bpy.context.scene
for i, n in enumerate(names):
    for tag, pos in (('front', (0.6 * sc, -4.6 * sc, 1.2 * sc)), ('side', (4.6 * sc, -0.4 * sc, 1.2 * sc))):
        A.cam_key(cam, tgt, 1, pos, (0, 0, 0.95 * sc), 35)
        s.frame_set(i + 1)
        s.render.filepath = os.path.join(out, 'frame_%02d_%s_%s.png' % (i, n, tag))
        bpy.ops.render.render(write_still=True)
print('FERTIG')
