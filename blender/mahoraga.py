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
    """Mahoraga nach Anime-Vorlage: riesig, muskulös, weiße Haut, kleiner Kopf mit vier Flügeln über den Augen,
    waagerecht schwebendes Rad mit acht Griffen, Klinge am rechten Unterarm, Lendentuch mit dunkler Schärpe."""
    white = '#efece4'
    cfg = dict(hair=white, hairStyle='none', coat=white, coatShade='#a9a498', skin=white, skinShade='#a9a498',
               trim='#2b2b33', outfit='none', closedEyes=True, browColor=white, angryBrows=True, eyes='#ffffff',
               shoe=white,
               radii={'pelvis': (1.25, 1.3), 'waist': (1.05, 1.15), 'chest': (1.55, 1.4), 'upchest': (1.7, 1.5),
                      'neck': 1.7, 'neckTop': 1.55, 'sh': 1.55, 'el': 1.3, 'wr': 1.15, 'ha': 1.2,
                      'hi': 1.35, 'kn': 1.35, 'an': 1.2, 'to': 1.15})

    def extra(p, arm):
        parts = []
        skin = A.toon(p + 'Skin', white, shade='#a9a498')
        wing = A.toon(p + 'WingM', '#f6f3ec', shade='#b6b0a2')
        gold = A.toon(p + 'Gold', '#d9b24a', shade='#8a6a1e')
        sash = A.toon(p + 'Sash', '#2b2b33', shade='#121217')
        cloth = A.toon(p + 'Cloth', '#e4e0d6', shade='#9d978a')
        # Brust- und Bauchmuskeln
        for sx in (-1, 1):
            m = A.sphere(p + 'Pec%d' % sx, (0.085 * sx, -0.125, 1.4), (0.11, 0.05, 0.075), skin, segments=16, outline=0.006)
            C.bind(m, arm, 'chest')
            parts.append(m)
            for row, z in enumerate((1.27, 1.19, 1.11)):
                ab = A.sphere(p + 'Ab%d%d' % (sx, row), (0.042 * sx, -0.108, z), (0.038, 0.022, 0.032), skin, segments=12, outline=0.004)
                C.bind(ab, arm, 'spine')
                parts.append(ab)
        # Vier Flügel am Kopf (je zwei pro Seite, über den Augen, nach hinten-oben)
        for sx in (-1, 1):
            for k, (z, up) in enumerate(((1.79, 0.05), (1.74, -0.02))):
                w = C.strand(p + 'Wing%d%d' % (sx, k), [(0.06 * sx, -0.135, z), (0.15 * sx, -0.06, z + up + 0.02),
                                                         (0.22 * sx, 0.08, z + up + 0.08)], 0.045, wing, flat=0.3)
                C.bind(w, arm, 'head')
                parts.append(w)
        # Das Rad: flach über dem Kopf, acht Speichen, Griffe ragen über den Ring hinaus
        wheel = A.empty(p + 'Wheel', (0, 0.02, 2.0))
        bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.03, location=(0, 0, 0))
        ring = bpy.context.active_object
        ring.name = p + 'WheelRing'
        A.set_mat(ring, gold)
        A.add_outline(ring, 0.006)
        ring.parent = wheel
        bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.025, location=(0, 0, 0))
        inner = bpy.context.active_object
        inner.name = p + 'WheelInner'
        A.set_mat(inner, gold)
        inner.parent = wheel
        hub = A.sphere(p + 'Hub', (0, 0, 0), 0.07, gold, segments=12, outline=0.006)
        hub.parent = wheel
        for i in range(8):
            a = i / 8 * math.tau
            sp = A.cylinder(p + 'Spoke%d' % i, (math.cos(a) * 0.28, math.sin(a) * 0.28, 0), 0.014, 0.56, gold, rot=(0, PI / 2, a), outline=0.004)
            sp.parent = wheel
            hd = A.cylinder(p + 'Handle%d' % i, (math.cos(a) * 0.5, math.sin(a) * 0.5, 0), 0.02, 0.14, gold, rot=(0, PI / 2, a), outline=0.004)
            hd.parent = wheel
            kn = A.sphere(p + 'Knob%d' % i, (math.cos(a) * 0.58, math.sin(a) * 0.58, 0), 0.035, gold, segments=10, outline=0.004)
            kn.parent = wheel
        C.bind(wheel, arm, 'head')
        # Schwert der Auslöschung: breite Klinge am rechten Unterarm, ragt weit über die Hand hinaus
        blade = A.cube(p + 'Blade', (-0.29, -0.05, 0.62), (0.035, 0.008, 0.55),
                       A.toon(p + 'Steel', '#f3f6fb', shade='#9aa6ba', highlight='#ffffff'), outline=0.005)
        C.bind(blade, arm, 'fore.R')
        edge = A.cube(p + 'Edge', (-0.29, -0.065, 0.62), (0.008, 0.004, 0.55), A.glow(p + 'EdgeGlow', '#fff6c8', 3))
        C.bind(edge, arm, 'fore.R')
        # Lendentuch + Schärpe
        loin = A.cylinder(p + 'Loin', (0, 0, 0.78), 0.2, 0.46, cloth, r2=0.27, verts=32, outline=0.008)
        loin.rotation_euler = (PI, 0, 0)
        loin.scale = (1.25, 1.1, 1)
        C.bind(loin, arm, 'pelvis')
        belt = A.cylinder(p + 'Sash', (0, 0, 1.02), 0.2, 0.09, sash, verts=32, outline=0.006)
        belt.scale = (1.25, 1.15, 1)
        C.bind(belt, arm, 'pelvis')
        flap = A.cube(p + 'Flap', (0, -0.21, 0.78), (0.09, 0.012, 0.24), sash, outline=0.005)
        C.bind(flap, arm, 'pelvis')
        parts += [wheel, blade, edge, loin, belt, flap]
        return parts
    cfg['extra'] = extra
    fig = C.build('Maho', cfg, loc=(MAHX, 0, 0), facing=-PI / 2)
    fig['arm'].scale = (1.5, 1.5, 1.5)
    hb = fig['arm'].pose.bones['head']
    hb.scale = (0.8, 0.8, 0.8)   # kleiner Kopf auf riesigem Körper
    hb.keyframe_insert('scale', frame=1)
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
        A.key(wheel, f, rot=(0, 0, r))  # flach über dem Kopf
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
         (57, (MAHX - 0.4, -1.6, 4.2), (MAHX, 0.03, 3.0), 38), (70, (MAHX - 0.2, -1.35, 4.05), (MAHX, 0.03, 3.0), 44)]
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
    S.retime([1, 61, 145], [1, 97, 217], 216)   # länger: Beschwörung 4 s, Kampf 5 s
    if render == 'preview':
        A.render_frames(out, [16, 64, 100, 118, 124, 140, 160, 200])
    else:
        A.render_frames(out)
    print('FERTIG', mode)
