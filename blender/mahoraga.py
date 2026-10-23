"""Mahoraga-Beschwörung: zwei Clips (Sieg / Niederlage).

  blender -b --factory-startup -P blender/mahoraga.py -- win|lose preview|full <ordner>

Ablauf (24 fps, 144 Bilder = 6 s):
   1– 60  Beschwörer formt das Zeichen, Mahoraga steigt aus dem Schattenkreis, das Rad dreht sich (Klick, Klick)
  lose:  Mahoraga holt aus, stürmt vor – ein Schlag schleudert den Beschwörer weit weg; Heldenpose Mahoraga
  win:   Der Beschwörer stürmt vor – BLACK FLASH! Mahoraga taumelt und kniet nieder, das Rad glüht golden
"""
import bpy
import sys
import os
import math
import random
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A  # noqa: E402
import chars as C  # noqa: E402
import cast  # noqa: E402
import scenes as S  # noqa: E402  (nur Helfer)

PI = math.pi
FR = 144
rnd = random.Random(5)
SUMX, MAHX = -1.7, 0.7


def build_mahoraga():
    cfg = dict(hair='#f2efe7', hairShade='#b8b3a6', hairStyle='bald', coat='#ece8de', coatShade='#a8a395',
               trim='#4a4a55', outfit='robe', skin='#ece8de', skinShade='#a8a395', closedEyes=True,
               browColor='#ece8de', angryBrows=True, eyes='#ffffff')

    def extra(p, arm):
        parts = []
        bone = A.toon(p + 'Bone', '#f5f2ea', shade='#b2ab9b')
        gold = A.toon(p + 'Gold', '#d9b24a', shade='#8a6a1e')
        # Flügel an den Schläfen (über den Augen)
        for sx in (-1, 1):
            w = A.cone(p + 'Wing%d' % sx, (0.12 * sx, -0.06, 1.8), 0.05, 0.22, bone, rot=(0, sx * 1.25, 0), verts=4, outline=0.005)
            w.scale = (1, 0.35, 1)
            C.bind(w, arm, 'head')
            parts.append(w)
        # Das achtspeichige Rad über dem Kopf (dreht sich unabhängig → eigenes Objekt)
        wheel = A.empty(p + 'Wheel', (0, 0.05, 2.18))
        bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.025, location=(0, 0, 0))
        ring = bpy.context.active_object
        ring.name = p + 'WheelRing'
        A.set_mat(ring, gold)
        A.add_outline(ring, 0.006)
        ring.parent = wheel
        hub = A.sphere(p + 'Hub', (0, 0, 0), 0.06, gold, segments=12, outline=0.006)
        hub.parent = wheel
        for i in range(8):
            a = i / 8 * math.tau
            sp = A.cylinder(p + 'Spoke%d' % i, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0), 0.012, 0.42, gold, rot=(0, PI / 2, a), outline=0.004)
            sp.parent = wheel
            kn = A.sphere(p + 'Knob%d' % i, (math.cos(a) * 0.43, math.sin(a) * 0.43, 0), 0.04, gold, segments=10, outline=0.004)
            kn.parent = wheel
        C.bind(wheel, arm, 'head')
        # Klinge am rechten Unterarm (Schwert der Auslöschung)
        blade = A.cube(p + 'Blade', (-0.3, -0.02, 0.55), (0.03, 0.012, 0.5), A.toon(p + 'Steel', '#e8eef6', shade='#8a96aa', highlight='#ffffff'), outline=0.005)
        C.bind(blade, arm, 'fore.R')
        parts += [wheel, blade]
        return parts
    cfg['extra'] = extra
    fig = C.build('Maho', cfg, loc=(MAHX, 0, 0), facing=-PI / 2)
    fig['arm'].scale = (1.45, 1.45, 1.45)
    return fig


def run(mode):
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=7, threshold=0.8, mix=0.45)
    A.sun(2.0, rot=(math.radians(55), math.radians(10), math.radians(-30)))
    S.sky('MahoSky', '#141a2a', '#020306', cloud='#25304a', cloud_scale=1.6, strength=1.3)
    A.cube('Ground', (0, 0, -0.05), (40, 40, 0.05), A.toon('MG', '#0d111b', shade='#05070c'))
    # Schattenkreis
    pool = A.cylinder('Pool', (MAHX, 0, 0.005), 1.6, 0.01, A.toon('PoolM', '#000000'), verts=48, outline=0)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.02, location=(MAHX, 0, 0.02))
    rim = bpy.context.active_object
    A.set_mat(rim, A.glow('PoolRim', '#8fa4ff', 4))
    for f in range(1, FR, 12):
        A.key(rim, f, scale=1.0 + 0.05 * math.sin(f))
    # Figuren
    Su = cast.build_char('megumi', 'Sum', loc=(SUMX, 0, 0), facing=PI / 2, sign=False)
    M = build_mahoraga()
    wheel = bpy.data.objects['MahoWheel']
    for fig in (Su, M):
        for f in range(1, FR + 1, 24):
            C.pose(fig, f, chest=(2 + (f // 24) % 2 * 2, 0, 0), **{'upper.L': (0, 0, -10), 'upper.R': (0, 0, 10), 'fore.L': (-12, 0, 0), 'fore.R': (-12, 0, 0)})
    # Zeichen (Hund mit beiden Händen)
    sign = {'upper.R': (-70, 0, 25), 'fore.R': (-115, 0, 0), 'upper.L': (-70, 0, -25), 'fore.L': (-115, 0, 0)}
    C.pose(Su, 4, **{'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0), 'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0)})
    C.pose(Su, 12, **sign)
    C.pose(Su, 56, **sign)
    S.sparks_rise('SumAura', (0, 0, 0), '#8fa4ff', 18, 1, FR + 40, parent=Su['arm'])
    # Mahoraga steigt auf
    M['arm'].location = (MAHX, 0, -4.8)
    M['arm'].keyframe_insert('location', frame=1)
    M['arm'].keyframe_insert('location', frame=18)
    M['arm'].location = (MAHX, 0, 0)
    M['arm'].keyframe_insert('location', frame=54)
    C.pose(M, 18, spine=(30, 0, 0), head=(30, 0, 0))
    C.pose(M, 54, spine=(0, 0, 0), head=(-8, 0, 0))
    # Rad dreht sich in Klicks (Anpassung)
    for f, r in ((1, 0), (58, 0), (59, PI / 4), (66, PI / 4), (67, PI / 2), (120, PI / 2), (121, 3 * PI / 4)):
        A.key(wheel, f, rot=(PI / 2, 0, r))
    A.set_interp(wheel, 'CONSTANT')
    shadow_mat = A.toon('ShadowDrip', '#000000')
    for i in range(10):   # Schatten tropfen von Mahoraga ab, während er aufsteigt
        a = rnd.uniform(0, math.tau)
        d = A.sphere('Drip%d' % i, (MAHX + math.cos(a) * 0.5, math.sin(a) * 0.5, 1.0), 0.07, shadow_mat, segments=10, outline=0)
        A.key(d, 18, loc=(MAHX + math.cos(a) * 0.5, math.sin(a) * 0.5, 2.6), scale=0.07)
        A.key(d, 54, loc=(MAHX + math.cos(a) * 0.7, math.sin(a) * 0.7, 0.0), scale=0.01)
        S.show_from([d], 18, 56)

    cam, tgt = A.camera(lens=28)
    flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 2.5), outline=0)
    flash.parent = cam
    A.visible(flash, 1, False)

    def flash_at(f):
        A.visible(flash, f, True)
        A.visible(flash, f + 2, False)

    K = [(1, (SUMX + 1.6, -2.4, 1.5), (SUMX, 0, 1.6), 34), (17, (SUMX + 1.4, -2.1, 1.55), (SUMX, 0, 1.65), 38),
         (18, (2.4, -3.0, 0.35), (MAHX, 0, 2.2), 22), (56, (2.0, -3.4, 0.5), (MAHX, 0, 2.9), 22),
         (57, (MAHX - 0.2, -1.6, 3.0), (MAHX, 0.05, 3.15), 45), (70, (MAHX - 0.1, -1.4, 3.1), (MAHX, 0.05, 3.2), 50)]
    cuts = {17, 56, 70}

    if mode == 'lose':
        # Ausholen, Vorstürmen, Schlag
        C.pose(M, 71, **{'upper.R': (40, 0, 30), 'fore.R': (-60, 0, 0), 'spine': (0, -25, 0)})
        C.pose(M, 76, **{'upper.R': (-95, 0, 5), 'fore.R': (0, 0, 0), 'spine': (15, 20, 0)})
        M['arm'].location = (MAHX, 0, 0)
        M['arm'].keyframe_insert('location', frame=73)
        M['arm'].location = (SUMX + 1.15, 0, 0)
        M['arm'].keyframe_insert('location', frame=76)
        flash_at(77)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.03, location=(SUMX + 0.1, 0, 1.5), rotation=(0, PI / 2, 0))
        shock = bpy.context.active_object
        A.set_mat(shock, A.glow('Shock', '#ffffff', 6))
        A.key(shock, 77, scale=0.1)
        A.key(shock, 86, scale=7)
        S.show_from([shock], 77, 87)
        # Beschwörer fliegt weit weg
        C.place(Su, 1, (SUMX, 0, 0))
        C.place(Su, 77, (SUMX, 0, 0))
        Su['arm'].rotation_euler = (0, 0, PI / 2)
        Su['arm'].keyframe_insert('rotation_euler', frame=77)
        C.place(Su, 88, (SUMX - 5, 0, 2.2))
        C.place(Su, 100, (SUMX - 10, 0, 0.2))
        Su['arm'].rotation_euler = (0, -4.5, PI / 2)
        Su['arm'].keyframe_insert('rotation_euler', frame=100)
        C.pose(Su, 77, **{'upper.L': (-170, 0, -20), 'upper.R': (-170, 0, 20), 'spine': (-30, 0, 0)})
        S.shards('Dust', (SUMX - 10, 0, 0), ['#3a3f52', '#5c6377'], 100, n=30, spread=1.5, up=2, size=0.08)
        C.pose(M, 100, **{'upper.R': (-95, 0, 5), 'fore.R': (0, 0, 0), 'spine': (15, 20, 0)})
        C.pose(M, 112, **{'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0), 'spine': (0, 0, 0)})
        mx = SUMX + 1.15
        K += [(71, (MAHX + 1.2, -3.2, 1.8), (MAHX - 0.6, 0, 1.9), 32), (78, (SUMX + 0.2, -3.6, 1.6), (SUMX, 0, 1.4), 30),
              (100, (SUMX - 2.5, -5.5, 2.4), (SUMX - 6, 0, 1.0), 26),
              (101, (mx + 1.8, -2.6, 0.5), (mx, 0, 2.8), 24), (144, (mx + 0.8, 2.4, 0.7), (mx, 0, 2.9), 24)]
        cuts |= {100}
    else:
        # Beschwörer stürmt vor – BLACK FLASH
        C.place(Su, 1, (SUMX, 0, 0))
        C.place(Su, 64, (SUMX, 0, 0))
        C.place(Su, 74, (MAHX - 0.95, 0, 0))
        C.pose(Su, 64, **{'upper.R': (40, 0, 20), 'fore.R': (-90, 0, 0), 'spine': (10, 0, 0)})
        C.pose(Su, 74, **{'upper.R': (-95, 0, 5), 'fore.R': (0, 0, 0), 'spine': (25, 0, 0)})
        flash_at(75)
        bf = []
        for i in range(14):   # schwarze Blitze mit rotem Rand
            col = '#ff2a2a' if i % 2 else '#1a0000'
            bf.append(S.slash_line('BF%d' % i, 75 + i // 4, (MAHX - 0.35, -0.1, 1.9 + rnd.uniform(-0.4, 0.4)),
                                   rnd.uniform(-1.2, 1.2), length=rnd.uniform(1.0, 2.4), color=col, tilt=rnd.uniform(-0.6, 0.6), life=5))
        # Mahoraga taumelt und kniet nieder
        C.pose(M, 75, spine=(0, 0, 0), head=(-8, 0, 0))
        C.pose(M, 80, spine=(-25, 0, 0), head=(-20, 0, 0))
        C.pose(M, 96, spine=(25, 0, 0), head=(30, 0, 0), **{'thigh.L': (-80, 0, 0), 'shin.L': (95, 0, 0), 'thigh.R': (-10, 0, 0), 'shin.R': (100, 0, 0)})
        C.move(M, 80, 'pelvis', (0, 0, 0))
        C.move(M, 96, 'pelvis', (0, -0.1, -0.42))
        gold = bpy.data.materials['MahoGold']
        em = gold.node_tree.nodes.get('Emission')
        for f, v in ((1, 1.0), (96, 1.0), (106, 4.0), (144, 3.0)):
            em.inputs['Strength'].default_value = v
            em.inputs['Strength'].keyframe_insert('default_value', frame=f)
        C.pose(Su, 100, **{'upper.R': (-95, 0, 5), 'fore.R': (0, 0, 0), 'spine': (25, 0, 0)})
        C.pose(Su, 114, **{'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0), 'spine': (0, 0, 0)})
        sx = MAHX - 0.95
        K += [(71, (sx - 1.2, -2.6, 1.6), (MAHX, 0, 1.9), 30), (76, (MAHX - 0.2, -2.0, 1.9), (MAHX, 0, 2.2), 38),
              (96, (MAHX + 0.5, -3.4, 1.4), (MAHX, 0, 1.6), 32),
              (97, (sx - 2.2, -2.8, 0.6), (sx + 0.4, 0, 1.9), 24), (144, (sx - 1.6, 2.4, 0.9), (sx + 0.4, 0, 2.0), 24)]
        cuts |= {96}
    for f, pos, look, lens in K:
        A.cam_key(cam, tgt, f, pos, look, lens)
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) in cuts else 'BEZIER'


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    mode, render, out = argv[0], argv[1], argv[2]
    os.makedirs(out, exist_ok=True)
    run(mode)
    if render == 'preview':
        A.render_frames(out, [10, 40, 62, 74, 78, 90, 100, 130])
    else:
        A.render_frames(out)
    print('FERTIG', mode)
