import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A, chars as C, cast
out = sys.argv[sys.argv.index('--') + 1]
A.reset_scene(); A.setup_render(1, res=(1600, 600), samples=8, motion_blur=False)
A.set_world_color((0.06, 0.07, 0.1), 1.0); A.sun(3.0)
tests = [
  ('rest', {}),
  ('ux-60', {'upper.R': (-60, 0, 0)}),
  ('ux+60', {'upper.R': (60, 0, 0)}),
  ('uz-60', {'upper.R': (0, 0, -60)}),
  ('uz+60', {'upper.R': (0, 0, 60)}),
  ('sign', {'upper.R': (-70, 0, 25), 'fore.R': (-110, 0, 0)}),
  ('fx-90', {'fore.R': (-90, 0, 0)}),
  ('spine', {'spine': (20, 0, 0), 'head': (20, 0, 0)}),
]
for i, (n, p) in enumerate(tests):
    f = cast.build_char('gojo', 'T%d' % i, loc=((i - 3.5) * 0.9, 0, 0), facing=math.radians(-35))
    C.pose(f, 1, **p)
cam, tgt = A.camera(lens=30)
A.cam_key(cam, tgt, 1, (0, -8, 1.2), (0, 0, 1.1), 30)
bpy.context.scene.frame_set(1); bpy.context.scene.render.filepath = out; bpy.ops.render.render(write_still=True)
