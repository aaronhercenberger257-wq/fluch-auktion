"""Testbild: alle Figuren nebeneinander (zum Prüfen des Modellings)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A
import chars as C
import cast

out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'lineup.png'
A.reset_scene()
A.setup_render(1, res=(1920, 720), samples=16, motion_blur=False)
A.set_world_color((0.06, 0.07, 0.1), 1.0)
A.sun(3.0, rot=(math.radians(50), math.radians(10), math.radians(-25)))
keys = ['gojo', 'sukuna', 'megumi', 'mahito', 'jogo', 'higuruma', 'hakari', 'yuta', 'dagon', 'naoya', 'foe']
for i, k in enumerate(keys):
    f = cast.build_char(k, k.capitalize(), loc=((i - 5) * 0.75, 0, 0), facing=0)
    C.pose(f, 1, **{'upper.L': (0, -10, 8), 'upper.R': (0, 10, -8)})
cam, tgt = A.camera(lens=28)
A.cam_key(cam, tgt, 1, (0, -8.5, 1.3), (0, 0, 1.05), 26)
bpy.context.scene.frame_set(1)
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
# Nahaufnahme Köpfe
A.cam_key(cam, tgt, 1, (-3.0, -2.6, 1.8), (-3.0, 0, 1.78), 50)
bpy.context.scene.frame_set(1)
bpy.context.scene.render.filepath = out.replace('.png', '_close.png')
bpy.ops.render.render(write_still=True)
print('FERTIG')
