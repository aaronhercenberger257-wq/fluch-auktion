import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A, chars as C, cast, mahoraga as M
out = sys.argv[sys.argv.index('--') + 1]
A.reset_scene(); A.setup_render(1, res=(1600, 800), samples=12, motion_blur=False)
A.set_world_color((0.07, 0.08, 0.11), 1.0); A.sun(3.0)
M.MAHX = 0.0
m = M.build_mahoraga()
m['arm'].rotation_euler = (0, 0, math.radians(-25))
C.pose(m, 1, **{'upper.L': (0, 0, -14), 'upper.R': (-20, 0, 14), 'fore.R': (-40, 0, 0)})
g = cast.build_char('gojo', 'Ref', loc=(-1.6, 0, 0), facing=math.radians(-20))
cam, tgt = A.camera(lens=35)
A.cam_key(cam, tgt, 1, (0.4, -7.5, 2.0), (-0.4, 0, 1.6), 32)
bpy.context.scene.frame_set(1); bpy.context.scene.render.filepath = out; bpy.ops.render.render(write_still=True)
A.cam_key(cam, tgt, 1, (0.9, -2.6, 3.4), (0, 0, 2.75), 45)
bpy.context.scene.frame_set(1); bpy.context.scene.render.filepath = out.replace('.png', '_head.png'); bpy.ops.render.render(write_still=True)
