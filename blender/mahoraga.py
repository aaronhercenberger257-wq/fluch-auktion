"""Mahoraga-Beschwörung: zwei Clips (Sieg / Niederlage), je 15,5 s.

  blender -b --factory-startup -P blender/mahoraga.py -- win|lose preview|full <ordner>

Ablauf (24 fps, 372 Bilder):
    1– 34  Megumi formt das Zeichen (Fäuste aufeinander), Schatten breitet sich aus
   35– 70  Mahoraga steigt riesig HINTER Megumi aus dem Schatten
   71–110  Heldenbild wie in der Vorlage: Megumi vorn, Mahoraga grinsend dahinter, das Rad klickt
  111–130  Megumi springt nach vorn weg und dreht sich um
  131–160  Mahoraga stürmt heran, Schwerthieb – Megumi duckt sich und springt zurück
  161–192  Gegenangriff: Faustschlag in den Bauch – das Rad dreht sich (Anpassung)
  193–220  Mahoraga schlägt zurück, Megumi blockt und rutscht weit zurück
  221–250  Megumi springt hoch, Tritt zum Kopf – Mahoraga blockt
  251–270  Kurze Pause: beide in Kampfhaltung
  win  271–372  Megumi taucht unter dem Hieb weg – BLACK FLASH in die Brust, Mahoraga taumelt und sinkt auf die Knie,
                das Rad glüht golden
  lose 271–372  Megumis Schlag prallt ab, das Rad dreht sich – Mahoraga schlägt zu und schleudert Megumi weit weg
                (wie im Anime) in eine Trümmerwand; Heldenpose Mahoraga
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
import fight as FT  # noqa: E402
import scenes as S  # noqa: E402  (nur Helfer)

PI = math.pi
FR = 372
rnd = random.Random(5)
POOL = Vector((0, 1.7, 0))
MS = 1.85          # Mahoraga-Maßstab


def walk(fig, f0, f1, step=4, amp=28):
    """Einfacher Lauf-/Stampfzyklus der Beine zwischen f0 und f1."""
    k = 0
    for f in range(f0, f1 + 1, step):
        s = 1 if k % 2 else -1
        C.pose(fig, f, **{'thigh.L': (-amp * s, 0, 0), 'thigh.R': (amp * s, 0, 0), 'shin.L': (25 + 20 * (s > 0), 0, 0),
                          'shin.R': (25 + 20 * (s < 0), 0, 0)})
        k += 1


def loc(fig, f, x, y, z=0.0, face=None):
    a = fig['arm']
    a.location = (x, y, z)
    a.keyframe_insert('location', frame=f)
    if face is not None:
        a.rotation_euler = (0, 0, face)
        a.keyframe_insert('rotation_euler', frame=f)


def environment():
    S.sky('MahoSky', '#2a3248', '#06080e', cloud='#4a5670', cloud_scale=1.4, strength=1.0)
    ground = A.toon('MG', '#2c303a', shade='#14161c', highlight='#3c404c')
    A.cube('Ground', (0, -6, -0.05), (50, 50, 0.05), ground)
    rubble = A.toon('Rubble', '#4a4e5a', shade='#1c1e26', highlight='#6a6e7c')
    concrete = A.toon('Concrete', '#3a3e4a', shade='#16181e', highlight='#555a68')
    # Trümmerbrocken
    for i in range(46):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(4, 20)
        p = Vector((math.cos(a) * r, math.sin(a) * r - 6, 0))
        if abs(p.x) < 2.5 and -9 < p.y < 3:
            continue
        b = S.blob('Rub%d' % i, 1.0, rubble, 50 + i, outline=0)
        b.location = p
        b.scale = (rnd.uniform(0.3, 1.2), rnd.uniform(0.3, 1.0), rnd.uniform(0.2, 0.7))
        A.add_outline(b, 0.02)
    # zerstörte Gebäude im Hintergrund (Silhouetten mit Fensterlichtern)
    win = A.glow('Windows', '#ffd9a0', 1.5)
    for i in range(14):
        a = PI * 0.05 + i / 13 * PI * 0.9
        p = Vector((math.cos(a) * 30, math.sin(a) * 26 - 4, 0))
        h = rnd.uniform(6, 18)
        w = rnd.uniform(3, 6)
        A.cube('Bld%d' % i, p + Vector((0, 0, h / 2)), (w / 2, 2.5, h / 2), concrete, rot=(0, rnd.uniform(-0.08, 0.08), a), outline=0.04)
        for k in range(int(h // 2)):
            if rnd.random() < 0.35:
                A.cube('Win%d_%d' % (i, k), p + Vector((rnd.uniform(-w / 3, w / 3), 0, 1 + k * 2)), (0.3, 2.55, 0.4), win, rot=(0, 0, a))
    # Trümmerwand, in die Megumi bei der Niederlage kracht
    for i in range(10):
        b = S.blob('Wall%d' % i, 1.0, concrete, 80 + i, outline=0)
        b.location = (rnd.uniform(-3, 3), -24 + rnd.uniform(-0.5, 0.5), rnd.uniform(0.5, 3.5))
        b.scale = (rnd.uniform(1.0, 2.2), rnd.uniform(0.6, 1.0), rnd.uniform(0.8, 1.6))
        A.add_outline(b, 0.03)
    # Staub-/Ascheflocken
    S.sparks_rise('Ash', (0, -4, 0), '#9aa4b8', 60, 1, FR + 40, radius=12, height=6, size=0.012)


def shadow_pool(f0, f1):
    pool = A.cylinder('Pool', tuple(POOL + Vector((0, 0, 0.004))), 1.0, 0.01, A.flat('PoolM', '#020206'), verts=64, outline=0)
    import bpy as _b
    _b.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.02, location=tuple(POOL + Vector((0, 0, 0.02))))
    rim = _b.context.active_object
    A.set_mat(rim, A.glow('PoolRim', '#7f8fff', 5))
    for o in (pool, rim):
        A.key(o, 1, scale=0.001)
        A.key(o, f0, scale=0.001)
        A.key(o, f1, scale=(2.6, 2.6, 1))
        A.key(o, 140, scale=(2.6, 2.6, 1))
        A.key(o, 150, scale=0.001)
    # Schattenfäden, die hochsteigen
    m = A.flat('ShadowStrand', '#05050a')
    for i in range(16):
        a = i / 16 * math.tau
        p = POOL + Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, 0))
        st = C.sweep('ShStrand%d' % i, [p, p + Vector((0, 0, 1.2)), p + Vector((math.cos(a) * -0.5, math.sin(a) * -0.5, 2.8))], [0.08, 0.05, 0.003], m,
                     ring_n=8, rings=8)
        A.no_ink(st)
        A.key(st, 1, scale=(1, 1, 0.001))
        A.key(st, 30 + i, scale=(1, 1, 0.001))
        A.key(st, 52 + i, scale=(1, 1, 1.0))
        A.key(st, 75, scale=(1, 1, 0.001))


def run(mode):
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=7, threshold=0.8, mix=0.45)
    A.sun(2.2, rot=(math.radians(55), math.radians(10), math.radians(-30)))
    A.ink()
    environment()
    shadow_pool(10, 34)
    Su = cast.build_char('megumi', 'Sum', loc=(0, 0, 0), facing=0.0)
    M = cast.build_char('mahoraga', 'Maho', loc=(POOL.x, POOL.y, -7.0), facing=0.0)
    wheel = bpy.data.objects['MahoWheel']
    wheel.rotation_mode = 'ZXY'
    tilt = wheel.rotation_euler.x
    clicks = [96, 186] + ([292] if mode == 'win' else [290])
    r = 0.0
    A.key(wheel, 1, rot=(tilt, 0, 0))
    for f in clicks:
        A.key(wheel, f - 1, rot=(tilt, 0, r))
        r += PI / 4
        A.key(wheel, f + 2, rot=(tilt, 0, r))
    S.sparks_rise('SumAura', (0, 0, 0), '#8fa4ff', 18, 1, FR + 40, parent=Su['arm'])
    rim = bpy.data.lights.new('MahoRim', 'POINT')
    rim.energy = 900
    rim.color = A._lin('#a8b8ff')
    ro = bpy.data.objects.new('MahoRim', rim)
    bpy.context.collection.objects.link(ro)
    ro.parent = M['arm']
    ro.location = (0, 1.4, 4.2)

    # Grundhaltungen / Atmen
    FT.apply(Su, 1, 'rest')
    FT.apply(M, 1, 'rest')
    for f in range(1, FR, 24):
        C.pose(Su, f, chest=(2 + (f // 24) % 2 * 2, 0, 0))
    # ── A: Beschwörung ──
    FT.apply(Su, 6, 'rest')
    FT.apply(Su, 14, 'summon')
    C.hand_switch(Su, 1, 'R', 'relaxed')
    C.hand_switch(Su, 1, 'L', 'relaxed')
    C.hand_switch(Su, 12, 'R', 'fist')
    C.hand_switch(Su, 12, 'L', 'fist')
    FT.apply(Su, 108, 'summon')
    # Mahoraga steigt hinter Megumi auf
    loc(M, 34, POOL.x, POOL.y, -7.0)
    loc(M, 66, POOL.x, POOL.y, 0.0)
    FT.apply(M, 34, 'roar', head=(-10, 0, 0))
    FT.apply(M, 66, 'rest', head=(15, 0, 0))
    FT.apply(M, 104, 'rest', head=(22, 0, 0))
    S.speedlines  # (Speedlines setzt finish() unten)
    # Megumi springt nach vorn weg und dreht sich um
    loc(Su, 110, 0, 0, 0, 0.0)
    loc(Su, 118, 0, -2.6, 1.3, PI * 0.5)
    loc(Su, 126, 0, -5.0, 0.0, PI)
    FT.apply(Su, 112, 'crouch')
    FT.apply(Su, 118, 'fly')
    FT.apply(Su, 126, 'crouch')
    FT.apply(Su, 132, 'guard')
    loc(M, 112, POOL.x, POOL.y, 0.0)
    loc(M, 128, 0, 0.6, 0.0)
    walk(M, 112, 128, step=8, amp=18)
    FT.apply(M, 130, 'guard')
    # ── B: Kampf ──
    # Mahoraga stürmt heran, Schwerthieb, Megumi duckt sich und springt zurück
    loc(M, 131, 0, 0.6, 0)
    loc(M, 146, 0, -2.9, 0)
    walk(M, 131, 144, step=5, amp=30)
    FT.apply(M, 140, 'slash_wind')
    FT.apply(M, 149, 'slash')
    FT.apply(M, 160, 'guard')
    loc(Su, 140, 0, -5.0, 0)
    FT.apply(Su, 144, 'guard')
    FT.apply(Su, 148, 'crouch')
    loc(Su, 150, 0, -5.0, 0)
    loc(Su, 156, 0, -5.9, 0.7)
    loc(Su, 161, 0, -6.4, 0)
    FT.apply(Su, 156, 'fly')
    FT.apply(Su, 161, 'guard')
    S.slash_line('MSlash1', 149, (0, -4.6, 1.3), 0.12, length=4.5, color='#ffffff', tilt=0.0, life=6)
    S.slash_line('MSlash1b', 150, (0, -4.6, 1.25), 0.1, length=3.8, color='#c8d4ff', tilt=0.0, life=5)
    # Gegenangriff: Faust in den Bauch
    loc(Su, 166, 0, -6.4, 0)
    loc(Su, 175, 0, -3.95, 0)
    walk(Su, 166, 174, step=3, amp=40)
    FT.apply(Su, 172, 'punch_wind')
    FT.apply(Su, 176, 'punch', **{'upper.R': (-115, 0, 5)})
    FT.apply(Su, 184, 'punch', **{'upper.R': (-115, 0, 5)})
    FT.apply(M, 176, 'guard')
    FT.apply(M, 179, 'hurt', spine=(-8, 0, 0), chest=(-5, 0, 0), head=(-5, 0, 0))
    FT.apply(M, 190, 'guard')
    S.shockwave((0, -3.4, 1.9), 176, '#ffffff', life=10, size=2.5)
    hit_flash = [176]
    # Mahoraga schlägt zurück, Megumi blockt, rutscht zurück
    FT.apply(M, 196, 'slash_wind')
    FT.apply(M, 203, 'slash')
    FT.apply(Su, 196, 'guard')
    FT.apply(Su, 203, 'guard', spine=(-10, 0, 0))
    loc(Su, 203, 0, -3.95, 0)
    loc(Su, 216, 0, -7.2, 0)
    FT.apply(Su, 216, 'crouch')
    FT.apply(Su, 222, 'guard')
    S.slash_line('MSlash2', 203, (0, -4.0, 1.5), -0.5, length=4.0, color='#ffffff', tilt=0.3, life=6)
    S.shards('Dust1', (0, -5.5, 0), ['#5a5e6a', '#8a8e9a'], 205, n=24, spread=1.2, up=0.8, size=0.06, seed=4)
    hit_flash.append(203)
    # Sprung, Tritt zum Kopf – Mahoraga blockt mit dem Arm
    loc(Su, 224, 0, -7.2, 0)
    loc(Su, 233, 0, -5.2, 2.0)
    loc(Su, 240, 0, -3.7, 2.6)
    FT.apply(Su, 228, 'crouch')
    FT.apply(Su, 234, 'fly')
    FT.apply(Su, 239, 'kick')
    FT.apply(M, 232, 'guard')
    FT.apply(M, 239, 'guard', **{'upper.L': (-100, 0, -20), 'fore.L': (-100, 0, 0)})
    loc(Su, 242, 0, -3.8, 2.6)
    loc(Su, 252, 0, -5.6, 0.0)
    FT.apply(Su, 246, 'fly')
    FT.apply(Su, 252, 'crouch')
    FT.apply(Su, 260, 'guard')
    FT.apply(M, 252, 'guard')
    S.shockwave((0, -3.4, 3.5), 240, '#ffffff', life=12, size=3)
    hit_flash.append(240)
    loc(M, 252, 0, -2.9, 0)
    loc(M, 270, 0, -2.9, 0)

    cam, tgt = A.camera(lens=30)
    K = [
        (1, (0.55, -2.7, 0.95), (0, 0, 1.5), 34), (34, (0.45, -2.25, 1.0), (0, 0, 1.55), 36),
        (35, (2.8, -5.8, 0.35), (0, 1.0, 2.2), 22), (70, (2.3, -5.2, 0.45), (0, 1.0, 2.8), 22),
        (71, (0.25, -3.6, 1.55), (0, 0.8, 2.45), 38), (110, (0.15, -3.1, 1.6), (0, 0.8, 2.55), 42),
        (111, (7.5, -2.4, 1.7), (0, -2.2, 1.6), 26), (130, (7.2, -2.6, 1.7), (0, -2.4, 1.6), 26),
        (131, (6.0, -1.0, 1.3), (0, -2.0, 1.8), 28), (147, (5.4, -3.0, 1.2), (0, -4.0, 1.4), 30),
        (148, (1.4, -6.6, 0.3), (0, -3.8, 1.8), 20), (161, (1.8, -7.2, 0.4), (0, -4.0, 1.8), 20),
        (162, (5.2, -4.4, 1.2), (0, -4.6, 1.4), 30), (181, (4.6, -4.0, 1.4), (0, -3.6, 1.7), 34),
        (182, (1.2, -4.8, 2.9), (0, -2.9, 3.6), 45), (192, (1.0, -4.6, 2.8), (0, -2.9, 3.7), 48),
        (193, (5.6, -6.0, 1.3), (0, -5.0, 1.3), 28), (220, (6.0, -6.8, 1.5), (0, -5.6, 1.4), 28),
        (221, (3.2, -8.4, 0.4), (0, -4.0, 2.4), 22), (250, (3.6, -7.8, 0.5), (0, -4.2, 2.6), 22),
        (251, (0.9, -7.4, 1.25), (0, -2.9, 2.8), 32), (270, (0.8, -7.0, 1.25), (0, -2.9, 2.9), 34),
    ]
    cuts = {34, 70, 110, 130, 147, 161, 181, 192, 220, 250, 270}

    if mode == 'win':
        # Megumi stürmt heran, taucht unter dem Hieb weg – BLACK FLASH in die Brust
        loc(Su, 271, 0, -5.6, 0)
        loc(Su, 282, 0, -3.95, 0)
        walk(Su, 271, 280, step=3, amp=40)
        FT.apply(M, 274, 'slash_wind')
        FT.apply(M, 284, 'slash')
        FT.apply(Su, 281, 'crouch')
        FT.apply(Su, 286, 'crouch')
        S.slash_line('MSlash3', 284, (0, -4.0, 2.1), 0.05, length=4.5, color='#ffffff', life=6)
        FT.apply(Su, 288, 'punch_wind')
        FT.apply(Su, 292, 'punch', **{'upper.R': (-140, 0, 5), 'fore.R': (-5, 0, 0)})
        FT.apply(Su, 304, 'punch', **{'upper.R': (-140, 0, 5), 'fore.R': (-5, 0, 0)})
        hit_flash.append(292)
        bf = []
        for i in range(22):
            col = '#ff1a1a' if i % 2 else '#0a0000'
            bf.append(S.slash_line('BF%d' % i, 292 + i // 5, (0, -3.35, 2.4 + rnd.uniform(-0.6, 0.6)), rnd.uniform(-1.4, 1.4),
                                   length=rnd.uniform(1.2, 3.2), color=col, tilt=rnd.uniform(-0.8, 0.8), life=6))
        S.shockwave((0, -3.3, 2.4), 292, '#ff2a2a', life=14, size=5)
        S.shockwave((0, -3.3, 2.4), 294, '#000000', life=14, size=4)
        # Mahoraga taumelt zurück und sinkt auf die Knie
        FT.apply(M, 292, 'guard')
        FT.apply(M, 298, 'hurt')
        loc(M, 292, 0, -2.9, 0)
        loc(M, 312, 0, -1.4, 0)
        FT.apply(M, 316, 'hurt')
        FT.apply(M, 330, 'kneel')
        loc(M, 316, 0, -1.4, 0)
        loc(M, 330, 0, -1.4, -0.55 * MS)
        S.shards('Dust2', (0, -1.6, 0), ['#5a5e6a', '#8a8e9a'], 330, n=30, spread=2.0, up=0.6, size=0.07, seed=8)
        gold = bpy.data.materials['MahoGold']
        em = None
        for n in gold.node_tree.nodes:
            if n.type == 'EMISSION':
                em = n
        if em:
            for f, v in ((1, 1.0), (330, 1.0), (342, 5.0), (FR, 3.5)):
                em.inputs['Strength'].default_value = v
                em.inputs['Strength'].keyframe_insert('default_value', frame=f)
        FT.apply(Su, 316, 'punch', **{'upper.R': (-140, 0, 5), 'fore.R': (-5, 0, 0)})
        FT.apply(Su, 334, 'rest')
        C.hand_switch(Su, 336, 'L', 'relaxed')
        K += [
            (271, (5.0, -5.2, 0.8), (0, -4.4, 1.4), 26), (285, (4.6, -4.6, 0.8), (0, -3.9, 1.6), 30),
            (286, (1.0, -5.0, 0.4), (0, -3.3, 2.4), 22), (291, (0.9, -4.9, 0.45), (0, -3.3, 2.5), 22),
            (292, (2.6, -4.6, 2.0), (0, -3.3, 2.3), 28), (312, (3.4, -5.6, 2.2), (0, -2.5, 2.4), 28),
            (313, (-2.6, -7.2, 0.6), (0, -2.0, 1.8), 24), (340, (-2.2, -6.8, 0.8), (0, -2.0, 1.8), 26),
            (341, (4.2, -7.2, 0.9), (0, -2.6, 1.6), 28), (FR, (3.2, -7.6, 1.0), (0, -2.6, 1.7), 30),
        ]
        cuts |= {285, 291, 312, 340}
        title_frames = []
    else:
        # Megumis Schlag prallt ab – das Rad dreht sich – Mahoraga schleudert ihn weg
        loc(Su, 271, 0, -5.6, 0)
        loc(Su, 284, 0, -3.95, 0)
        walk(Su, 271, 282, step=3, amp=40)
        FT.apply(Su, 282, 'punch_wind')
        FT.apply(Su, 286, 'punch', **{'upper.R': (-115, 0, 5)})
        FT.apply(Su, 298, 'punch', **{'upper.R': (-112, 0, 5)})
        hit_flash.append(286)
        S.shockwave((0, -3.4, 1.9), 286, '#ffffff', life=8, size=1.6)
        FT.apply(M, 286, 'guard')
        FT.apply(M, 300, 'punch_wind')
        FT.apply(M, 306, 'punch', **{'upper.R': (-80, 0, 0), 'fore.R': (-5, 0, 0)})
        FT.apply(M, 320, 'punch', **{'upper.R': (-80, 0, 0), 'fore.R': (-5, 0, 0)})
        C.hand_switch(M, 299, 'L', 'fist')
        hit_flash.append(306)
        S.shockwave((0, -3.8, 1.5), 306, '#ffffff', life=14, size=6)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.4, minor_radius=0.04, location=(0, -4.6, 1.4), rotation=(PI / 2, 0, 0))
        cone = bpy.context.active_object
        A.set_mat(cone, A.glow('ShockCone', '#ffffff', 6))
        A.key(cone, 1, scale=0.01)
        A.key(cone, 306, scale=0.2)
        A.key(cone, 318, scale=6)
        S.show_from([cone], 306, 319)
        # Megumi fliegt weit weg und kracht in die Trümmerwand
        loc(Su, 306, 0, -3.95, 0, PI)
        Su['arm'].rotation_euler = (0, 0, PI)
        Su['arm'].keyframe_insert('rotation_euler', frame=306)
        loc(Su, 316, 0, -11.0, 2.6)
        loc(Su, 328, 0, -22.6, 1.2)
        Su['arm'].rotation_euler = (-1.2, 0, PI)
        Su['arm'].keyframe_insert('rotation_euler', frame=328)
        FT.apply(Su, 307, 'fly')
        FT.apply(Su, 328, 'fly')
        loc(Su, 336, 0, -22.2, 0.0)
        FT.apply(Su, 340, 'kneel', head=(40, 0, 0))
        hit_flash.append(328)
        S.shards('Crash', (0, -23, 1.2), ['#5a5e6a', '#8a8e9a', '#3a3e4a'], 328, n=60, spread=3.2, up=2.2, size=0.12, seed=9)
        S.shockwave((0, -23.0, 0.2), 328, '#c8ccd8', life=18, size=8)
        speed_trail = [S.slash_line('Trail%d' % i, 308 + i * 2, (0, -6 - i * 2.4, 1.8 + math.sin(i * 0.5) * 0.6), PI / 2, length=3.0,
                                    color='#e8ecff', tilt=0, life=5) for i in range(8)]
        # Heldenpose Mahoraga
        FT.apply(M, 334, 'rest')
        FT.apply(M, 346, 'roar')
        K += [
            (271, (5.0, -5.2, 0.8), (0, -4.4, 1.4), 26), (287, (4.6, -4.6, 0.9), (0, -3.9, 1.6), 30),
            (288, (1.0, -4.4, 3.1), (0, -2.9, 3.6), 45), (298, (0.9, -4.3, 3.0), (0, -2.9, 3.7), 48),
            (299, (3.0, -6.4, 1.3), (0, -3.6, 1.6), 26), (307, (3.2, -6.6, 1.3), (0, -3.8, 1.6), 26),
            (308, (6.0, -4.5, 2.0), (0, -6.0, 2.0), 30), (312, (6.0, -7.0, 2.3), (0, -8.5, 2.4), 30), (316, (6.0, -9.6, 2.5), (0, -11.0, 2.6), 30),
            (321, (6.0, -14.6, 2.1), (0, -16.5, 2.0), 30), (326, (6.0, -19.4, 1.6), (0, -21.0, 1.5), 30),
            (327, (5.0, -14.0, 1.2), (0, -22.5, 1.4), 26), (344, (4.5, -15.0, 1.4), (0, -22.5, 1.0), 26),
            (345, (2.4, -6.6, 0.3), (0, -2.9, 3.0), 20), (FR, (1.6, -6.0, 0.35), (0, -2.9, 3.3), 20),
        ]
        cuts |= {287, 298, 307, 326, 344}
    for f, pos, look, lens in K:
        A.cam_key(cam, tgt, f, pos, look, lens)
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) in cuts else 'BEZIER'
    # Effekte: Blitze, Impact-Frames, Wackeln, Speedlines
    flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 2.5), outline=0)
    flash.parent = cam
    A.visible(flash, 1, False)
    for f in hit_flash:
        A.visible(flash, f, True)
        A.visible(flash, f + 2, False)
    ctx = {'cam': cam}
    S.black_frames(ctx, [f + 2 for f in hit_flash])
    S.shake(cam, [36] + hit_flash, strength=0.05, length=12)
    S.speedlines(cam, [(111, 126), (131, 146), (166, 176), (271, 284)] + ([(306, 330)] if mode == 'lose' else [(292, 300)]))
    bpy.context.scene.frame_end = FR


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    mode, render, out = argv[0], argv[1], argv[2]
    os.makedirs(out, exist_ok=True)
    run(mode)
    if render == 'preview':
        A.render_frames(out, [20, 60, 95, 120, 145, 152, 176, 187, 205, 240, 262, 284, 293, 310, 330, 360])
    else:
        A.render_frames(out)
    print('FERTIG', mode)
