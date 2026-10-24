"""Zusatz-Clips fürs Spiel.

  blender -b --factory-startup -P blender/extras.py -- verdict <variante> preview|full|intro|tail <ordner>
  blender -b --factory-startup -P blender/extras.py -- spin preview|full <ordner>

verdict (Deadly Sentencing – die Waage, 216 Bilder = 9 s), Varianten:
  up3 up2 up1 even down1 down2 down3 exec
     1– 96  Gerichtssaal, die goldene Waage erscheint, der Gegner steht auf der linken Schale, das Gesetzbuch fällt auf die rechte
    97–168  Die Waage neigt sich (down = Gegner sinkt, weil er böse ist; up = er steigt, weil er gut ist)
   169–216  Urteil: Schriftzeichen, rote Flammen / goldenes Licht; exec: das Henkersschwert erscheint und richtet hin
  „intro“ rendert nur 1–96 (für alle Varianten gleich), „tail“ nur 97–216.

spin (Hakari zieht den Hebel, 60 Bilder = 2,5 s)
finger <1|2|3> (Sukuna isst Finger, 168 Bilder = 7 s), resonance (Nobaras Resonanz, 216 Bilder = 9 s):
  blender -b --factory-startup -P blender/extras.py -- finger 3 preview|full <ordner>
  blender -b --factory-startup -P blender/extras.py -- resonance preview|full <ordner>
"""
import bpy
import sys
import os
import math
import random
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A  # noqa: E402
import chars as C  # noqa: E402
import cast  # noqa: E402
import scenes as S  # noqa: E402

PI = math.pi
LEVELS = {'up3': -3, 'up2': -2, 'up1': -1, 'even': 0, 'down1': 1, 'down2': 2, 'down3': 3, 'exec': 3}


def hanger_pos(pivot, ang, side):
    """Position des Aufhängepunkts am Balkenende (Balken entlang X, Drehung um Y)."""
    x = 3.0 * side
    return pivot + Vector((x * math.cos(ang), 0, -x * math.sin(ang)))


def verdict(variant):
    rnd = random.Random(3)
    level = LEVELS[variant]
    FR = 216
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=7, threshold=0.8, mix=0.45)
    A.sun(1.6, rot=(math.radians(55), math.radians(10), math.radians(-30)))
    A.ink()
    S.sky('CourtSky', '#1a140a', '#020101', cloud='#3a2a10', cloud_scale=1.6, strength=0.9)
    wood = A.toon('CourtWood', '#5a3416', shade='#2a1709', highlight='#8a5a2a')
    floor = A.toon('CourtFloor', '#2a1c10', shade='#120c06')
    gold = A.toon('Gold', '#e6b84a', shade='#8a6a1e', highlight='#fff0a8')
    A.cube('Floor', (0, 0, -0.05), (40, 40, 0.05), floor)
    for i in range(10):   # Säulenhalle
        x = -13 + i * 2.9
        A.cylinder('Col%d' % i, (x, 11, 5), 0.42, 10, A.toon('ColM', '#3a3020', shade='#17130c'), outline=0.02)
    A.cube('Wall', (0, 12.5, 5), (16, 0.3, 5), A.toon('WallM', '#1e160c', shade='#0c0805'))
    # Richterbank + Judgeman (verhüllte Gestalt) hinten
    A.cube('Bench', (0, 8.2, 1.2), (3.0, 0.6, 1.2), wood, outline=0.02)
    A.cube('BenchTrim', (0, 7.58, 2.35), (3.05, 0.05, 0.07), gold)
    A.cone('JudgeBody', (0, 8.8, 3.2), 1.1, 2.2, A.toon('JudgeRobe', '#0e0d12'), r2=0.35, outline=0.02)
    A.sphere('JudgeHead', (0, 8.7, 4.6), (0.55, 0.5, 0.6), A.toon('JudgeCloth', '#e8e3d6', shade='#9e978a'), outline=0.015)
    for sx in (-1, 1):
        A.cube('JudgeBand%d' % sx, (0, 8.18, 4.6 + sx * 0.15), (0.56, 0.05, 0.035), A.toon('Band', '#2a2730'))
    # Die Waage
    pivot = Vector((0, 3.0, 6.2))
    A.cylinder('ScalePole', (0, 3.0, 3.1), 0.16, 6.2, gold, outline=0.015)
    A.cone('ScaleBase', (0, 3.0, 0.25), 1.1, 0.5, gold, r2=0.6, verts=24, outline=0.02)
    A.sphere('ScaleTop', tuple(pivot + Vector((0, 0, 0.35))), 0.32, gold, outline=0.012)
    beam = A.empty('Beam', tuple(pivot))
    bm = A.cube('BeamBar', (0, 0, 0), (3.2, 0.1, 0.1), gold, outline=0.015)
    bm.parent = beam
    for sx in (-1, 1):
        o = A.sphere('BeamEnd%d' % sx, (3.2 * sx, 0, 0), 0.16, gold, outline=0.01)
        o.parent = beam
    hangers = {}
    for side, name in ((-1, 'Foe'), (1, 'Book')):
        h = A.empty('Hang' + name, tuple(hanger_pos(pivot, 0, side)))
        pan = A.cylinder('Pan' + name, (0, 0, -3.0), 1.2, 0.12, gold, r2=1.35, verts=36, outline=0.015)
        pan.parent = h
        for k in range(3):
            a = k / 3 * math.tau + 0.4
            rim = Vector((math.cos(a) * 1.15, math.sin(a) * 1.15, -2.95))
            mid = rim * 0.5
            d = rim.normalized()
            ch = A.cylinder('Chain%s%d' % (name, k), tuple(mid), 0.025, rim.length, gold, outline=0)
            ch.rotation_mode = 'QUATERNION'
            ch.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
            ch.parent = h
        hangers[side] = h
    # Gegner auf der linken Schale
    F = cast.build_char('foe', 'Foe', loc=(0, 0, 0), facing=0.0, sign=False)
    F['arm'].parent = hangers[-1]
    F['arm'].location = (0, 0, -2.94)
    C.pose(F, 1, **{'upper.L': (-20, 0, -15), 'upper.R': (-20, 0, 15), 'fore.L': (-40, 0, 0), 'fore.R': (-40, 0, 0)})
    C.hand_switch(F, 1, 'R', 'fist')
    C.hand_switch(F, 1, 'L', 'fist')
    A.key(F['arm'], 1, scale=0.001)
    A.key(F['arm'], 30, scale=0.001)
    A.key(F['arm'], 38, scale=1.08)
    A.key(F['arm'], 42, scale=1.0)
    # Gesetzbuch auf der rechten Schale (fällt herab)
    book = A.empty('Book', (0, 0, 6.0))
    book.parent = hangers[1]
    cover = A.toon('BookCover', '#7a1a14', shade='#3a0806', highlight='#b03020')
    pages = A.toon('BookPages', '#f4ecd8', shade='#b8ab8c')
    for o in (A.cube('BookBody', (0, 0, 0.45), (0.85, 0.6, 0.45), cover, outline=0.02, bevel=0.05),
              A.cube('BookPg', (0.05, -0.02, 0.45), (0.82, 0.62, 0.36), pages, outline=0.0),
              A.cube('BookTrim', (0, -0.61, 0.45), (0.86, 0.02, 0.4), gold)):
        o.parent = book
    t = S.text_obj('BookKanji', '法', 0.55, A.glow('KanjiG', '#ffd24a', 3), extrude=0.02)
    t.parent = book
    t.location = (0, -0.64, 0.45)
    t.rotation_euler = (PI / 2, 0, 0)
    A.key(book, 1, loc=(0, 0, 9.0))
    A.key(book, 52, loc=(0, 0, 9.0))
    A.key(book, 62, loc=(0, 0, -2.94))
    # Neigung: erst ruhig, beim Aufprall des Buches leichtes Wippen, dann das Urteil
    target = -level * math.radians(9)
    keys = [(1, 0.0), (62, 0.0), (66, math.radians(-4)), (72, math.radians(2.5)), (80, math.radians(-1)), (96, 0.0)]
    keys += [(112, target * 0.25), (128, target * 1.12), (138, target * 0.94), (146, target * 1.02), (FR, target)]
    for f, ang in keys:
        A.key(beam, f, rot=(0, ang, 0))
    # Aufhängungen folgen dem Balken (bleiben senkrecht): Positionen aus dem Balkenwinkel
    fc_beam = None
    for fc in A._fcurves(beam.animation_data.action):
        if fc.data_path == 'rotation_euler' and fc.array_index == 1:
            fc_beam = fc
    for f in range(1, FR + 1, 2):
        ang = fc_beam.evaluate(f)
        for side, h in hangers.items():
            A.key(h, f, loc=tuple(hanger_pos(pivot, ang, side)))
    # Higuruma vorn rechts mit Hammer
    H = cast.build_char('higuruma', 'Hig', loc=(4.6, -1.2, 0), facing=-PI / 2 - 0.4, sign=False)
    C.pose(H, 1, **{'upper.R': (-40, 0, 20), 'fore.R': (-70, 0, 0), 'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0)})
    C.hand_switch(H, 1, 'R', 'fist')
    C.pose(H, 160, **{'upper.R': (-40, 0, 20), 'fore.R': (-70, 0, 0)})
    C.pose(H, 166, **{'upper.R': (-150, 0, 15), 'fore.R': (-30, 0, 0)})
    C.pose(H, 172, **{'upper.R': (-70, 0, 15), 'fore.R': (-20, 0, 0)})
    # Glühen der Schale: rot bei böse, golden-grün bei gut
    evil = level > 0
    if level != 0:
        col = '#ff2a2a' if evil else '#9dffb0'
        aura = A.sphere('Aura', (0, 0, -1.8), (1.3, 1.3, 1.7), A.glow('AuraM', col, 3, alpha=0.25), outline=0)
        aura.parent = hangers[-1]
        A.key(aura, 1, scale=0.001)
        A.key(aura, 140, scale=0.001)
        A.key(aura, 150, scale=1.0 * (0.6 + 0.2 * abs(level)))
        S.sparks_rise('VerdSpark', (0, 0, -2.9), col, 20 + 10 * abs(level), 140, FR + 40, radius=1.1, height=3.0, size=0.02, parent=hangers[-1])
        S.show_from([o for o in bpy.data.objects if o.name.startswith('VerdSpark')], 140)
        if not evil:   # Lichtstrahl von oben
            beam_l = A.cylinder('HolyBeam', (0, 0, 4.0), 1.0, 14, A.glow('HolyM', '#fff6c8', 2.5, alpha=0.3), outline=0)
            beam_l.parent = hangers[-1]
            A.key(beam_l, 1, scale=0.001)
            A.key(beam_l, 150, scale=(0.001, 0.001, 1))
            A.key(beam_l, 160, scale=(0.4 + 0.25 * abs(level), 0.4 + 0.25 * abs(level), 1))
    # Urteil als Schriftzeichen
    word = {3: '死刑', 2: '有罪', 1: '有罪', 0: '無罪', -1: '無罪', -2: '無罪', -3: '潔白'}[level]
    wcol = '#ff2a2a' if level > 0 else '#ffd24a' if level == 0 else '#b8ffcc'
    wt = S.text_obj('VerdictWord', word, 1.6, A.glow('WordM', wcol, 6), extrude=0.06)
    wt.location = (0, 1.0, 8.8)
    wt.rotation_euler = (PI / 2, 0, 0)
    A.key(wt, 1, scale=0.001)
    A.key(wt, 168, scale=0.001)
    A.key(wt, 172, scale=1.5)
    A.key(wt, 177, scale=1.0)
    cam, tgt = A.camera(lens=28)
    flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 2.5), outline=0)
    flash.parent = cam
    A.visible(flash, 1, False)
    flashes = [62, 167]
    K = [(1, (0.0, -15.0, 3.0), (0, 3.0, 4.0), 26), (52, (0.0, -12.5, 3.4), (0, 3.0, 4.2), 28),
         (53, (-5.8, -4.6, 3.4), (-3.0, 3.0, 4.4), 32), (96, (-5.2, -4.0, 3.6), (-3.0, 3.0, 4.5), 34),
         (97, (0.0, -11.0, 4.6), (0, 3.0, 4.0), 28), (160, (0.0, -10.0, 5.0), (0, 3.0, 4.2), 30),
         (161, (2.3, -3.4, 1.7), (4.6, -1.2, 1.65), 34), (166, (2.5, -3.2, 1.7), (4.6, -1.2, 1.7), 38),
         (167, (0.0, -9.0, 5.5), (0, 2.0, 6.5), 26), (FR, (0.0, -10.5, 5.0), (0, 2.0, 6.0), 26)]
    cuts = {52, 96, 160, 166}
    if variant == 'exec':
        # Henkersschwert erscheint über dem Gegner und schlägt zu
        sw = A.empty('ExecSword', (0, 0, 0))
        sw.parent = hangers[-1]
        blade = A.cube('ExecBlade', (0, 0, 1.6), (0.13, 0.03, 1.8), A.glow('ExecM', '#fff1b0', 5), outline=0.012)
        guard = A.cube('ExecGuard', (0, 0, -0.25), (0.5, 0.08, 0.08), gold, outline=0.01)
        grip = A.cylinder('ExecGrip', (0, 0, -0.7), 0.07, 0.8, A.toon('GripM', '#2a1d10'), outline=0.01)
        for o in (blade, guard, grip):
            o.parent = sw
        A.key(sw, 1, loc=(0.4, -0.6, 3.5), rot=(0, 0, 0), scale=0.001)
        A.key(sw, 176, loc=(0.4, -0.6, 3.5), rot=(0, 0, 0), scale=0.001)
        A.key(sw, 184, loc=(0.4, -0.6, 3.0), rot=(0, 0.3, 0), scale=1.0)
        A.key(sw, 190, loc=(1.6, -0.6, 2.4), rot=(0, 1.0, 0), scale=1.0)
        A.key(sw, 194, loc=(-1.0, -0.6, -1.4), rot=(0, -1.9, 0), scale=1.0)
        A.key(sw, 206, loc=(-1.0, -0.6, -1.4), rot=(0, -1.9, 0), scale=0.001)
        S.slash_line('ExecCut', 193, (-3.0, 2.4, 3.0), -0.9, length=4.5, color='#fff3b0', life=7)
        flashes.append(193)
        for o in [o for o in bpy.data.objects if o.name.startswith('Foe') and o.type in ('MESH', 'ARMATURE')]:
            A.visible(o, 1, True)
            A.visible(o, 195, False)
        S.shards('FoeBits', (-3.0, 3.0, 0.3), ['#2a1236', '#120b16', '#a898b4', '#fff1b0'], 195, n=60, spread=2.2)
        K = K[:-2] + [(167, (2.6, -6.0, 4.4), (-3.0, 3.0, 4.2), 30), (192, (2.2, -5.4, 4.2), (-3.0, 3.0, 4.0), 32),
                      (193, (0.0, -9.0, 5.5), (0, 2.0, 6.5), 26), (FR, (0.0, -10.5, 5.0), (0, 2.0, 6.0), 26)]
        cuts |= {192}
    elif level > 0:
        fl = A.glow('Flame', '#ff4a1a', 6)
        for i in range(10 * level):   # rote Flammen um die Schale
            a = i / (10 * level) * math.tau
            c = A.cone('Flame%d' % i, (math.cos(a) * 1.15, math.sin(a) * 1.15, -2.6), 0.18, 0.9, fl, verts=6, outline=0)
            c.parent = hangers[-1]
            A.key(c, 1, scale=0.001)
            A.key(c, 140 + i % 5, scale=0.001)
            for f in range(148 + i % 5, FR + 1, 6):
                A.key(c, f, scale=(1, 1, 0.7 + 0.5 * rnd.random()))
    for f in flashes:
        A.visible(flash, f, True)
        A.visible(flash, f + 2, False)
    for f, pos, look, lens in K:
        A.cam_key(cam, tgt, f, pos, look, lens)
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) in cuts else 'BEZIER'
    S.shake(cam, flashes, strength=0.05, length=10)
    bpy.context.scene.frame_end = FR
    return FR


def spin():
    """Hakari zieht den Hebel – die Walzen beginnen zu rasen (2,5 s)."""
    FR = 60
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=7, threshold=0.8, mix=0.45)
    A.sun(1.8)
    A.ink()
    S.sky('SpinSky', '#3a0a2a', '#0a0208', cloud='#5a1040', cloud_scale=3)
    A.cube('Floor', (0, 0, -0.05), (30, 30, 0.05), A.toon('GF', '#1a0b18', shade='#0a0408'))
    body = A.toon('SlotBody', '#c0186a', shade='#5c0a32', highlight='#ff5fb0')
    gold = A.toon('SlotGold', '#ffd24a', shade='#9a7010', highlight='#fff3b0')
    A.cube('Slot', (0, 1.6, 1.6), (1.3, 0.5, 1.6), body, outline=0.02)
    A.cube('SlotTop', (0, 1.5, 3.4), (1.0, 0.4, 0.25), A.glow('SlotTopM', '#ffe27a', 3), outline=0.015)
    reel_body = A.toon('Reel', '#fbf6ee', shade='#c9bfae', highlight='#ffffff')
    sym_mats = [A.glow('Seven', '#ff1a2e', 3.5), A.flat('SymB', '#1a1a2e'), A.flat('SymG', '#1a8a3a'), A.flat('SymP', '#c0186a')]
    for i, x in enumerate((-0.75, 0, 0.75)):
        keys = [(1, 0.3 * i), (20, 0.3 * i), (FR, 0.3 * i + 9 * math.tau)]
        pv, parts = S.slot_reel('Reel%d' % i, (x, 1.0, 1.9), 0.42, 0.55, ['7', '3', '5', '1', '9', '2', '6', '4'], reel_body, sym_mats, keys)
        for fc in A._fcurves(pv.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    # Hebel in Griffhöhe neben dem Automaten (Hakari steht direkt daneben und kann ihn greifen)
    lever_root = A.empty('LeverRoot', (1.42, 1.45, 1.3))
    lever = A.cylinder('Lever', (1.42, 1.45, 1.72), 0.035, 0.84, gold, outline=0.008)
    knob = A.sphere('LeverKnob', (1.42, 1.45, 2.16), 0.1, A.glow('KnobM', '#ff2a3a', 3), outline=0.008)
    bpy.context.view_layer.update()
    for o in (lever, knob):
        A.parent_keep(o, lever_root)
    bulbs = [A.glow('B%d' % i, c, 6) for i, c in enumerate(('#ffe27a', '#ff6fb8', '#6ff0ff'))]
    for k in range(30):
        a = k / 30 * PI
        A.sphere('Bulb%d' % k, (math.cos(a) * 1.5, 1.05, 1.9 + math.sin(a) * 1.7), 0.05, bulbs[k % 3], segments=8, outline=0)
    H = cast.build_char('hakari', 'Hak', loc=(1.98, 1.22, 0), facing=-PI / 2, sign=False)
    C.hand_switch(H, 1, 'R', 'fist')
    # Hand am Knauf (oben) → kräftig nach unten ziehen
    C.pose(H, 1, **{'upper.R': (-112, 0, -6), 'fore.R': (-28, 0, 0), 'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0), 'head': (-6, 0, 0)})
    C.pose(H, 12, **{'upper.R': (-122, 0, -6), 'fore.R': (-22, 0, 0), 'spine': (-6, 0, 0)})
    C.pose(H, 18, **{'upper.R': (-58, 0, -6), 'fore.R': (-20, 0, 0), 'spine': (22, 0, 0), 'head': (10, 0, 0)})
    # Der Hebel zeigt immer zu Hakaris rechter Hand → er hält ihn wirklich fest (bis Bild 22, dann federt er zurück)
    tr = lever_root.constraints.new('DAMPED_TRACK')
    tr.target = H['arm']
    tr.subtarget = 'hand.R'
    tr.track_axis = 'TRACK_Z'
    tr.influence = 1.0
    tr.keyframe_insert('influence', frame=20)
    tr.influence = 0.0
    tr.keyframe_insert('influence', frame=26)
    C.pose(H, 30, **{'upper.R': (-90, 0, 20), 'fore.R': (-90, 0, 0), 'upper.L': (-90, 0, -20), 'fore.L': (-90, 0, 0), 'spine': (0, 0, 0),
                     'head': (-15, 0, 0)})
    cam, tgt = A.camera(lens=30)
    A.cam_key(cam, tgt, 1, (4.1, -1.9, 2.0), (1.6, 1.3, 1.75), 30)
    A.cam_key(cam, tgt, 24, (3.8, -1.6, 2.0), (1.6, 1.3, 1.8), 32)
    A.cam_key(cam, tgt, 25, (0.3, -1.6, 1.9), (0, 1.0, 1.9), 34)
    A.cam_key(cam, tgt, FR, (0.2, -1.3, 1.95), (0, 1.0, 1.9), 38)
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) == 24 else 'BEZIER'
    S.speedlines(cam, [(25, FR)])
    bpy.context.scene.frame_end = FR
    return FR


def domain_backdrop(center, with_water=True):
    """Kulisse von Malevolent Shrine (für kurze Clips): roter Himmel, dunkles Wasser, Schrein-Silhouette mit Zahn-Maul."""
    c = Vector(center)
    sk = S.sky('ShrSky', '#7a1410', '#150202', cloud='#c0281a', cloud_scale=1.6, strength=1.1)
    sk.location = c
    if with_water:
        w = A.cube('DarkWater', tuple(c + Vector((0, 0, -0.02))), (40, 40, 0.02), A.toon('DW', '#0a0608', shade='#040203', highlight='#2a0a0a'))
    dark = A.toon('ShrSil', '#1a0606', shade='#0a0202', highlight='#3a0a0a')
    roof = A.toon('ShrSilRoof', '#140808', shade='#060202')
    horn = A.toon('ShrSilHorn', '#d8ccb4', shade='#7a6a54')
    b = c + Vector((0, 26, 0))
    A.cube('SilHall', tuple(b + Vector((0, 0, 7))), (7, 4, 7), dark, outline=0.05)
    for lvl, (z, w_) in enumerate(((15, 11), (20, 8), (24.5, 5.5))):
        r = A.cone('SilRoof%d' % lvl, tuple(b + Vector((0, 0, z))), w_, 3.2, roof, r2=w_ * 0.25, verts=4, outline=0.05)
        r.rotation_euler = (0, 0, PI / 4)
        r.scale = (1.0, 0.6, 1.0)
    for sx in (-1, 1):
        C.sweep('SilHorn%d' % sx, [b + Vector((0, 0, 26)), b + Vector((sx * 2.5, 0, 27.5)), b + Vector((sx * 4.0, 0, 31)), b + Vector((sx * 3.2, 0, 33.5))],
                [0.7, 0.5, 0.25, 0.02], horn, ring_n=10, rings=14)
    maw = A.cylinder('SilMaw', tuple(b + Vector((0, -4.05, 6.5))), 4.2, 0.1, A.glow('SilMawM', '#3ad7ff', 2.2), rot=(PI / 2, 0, 0), verts=40, outline=0.05)
    maw.scale = (1, 0.8, 1)
    teeth = A.toon('SilTeeth', '#f0e6d0', shade='#a8987c')
    for i in range(11):
        t = -1 + 2 * i / 10
        A.cone('SilTU%d' % i, tuple(b + Vector((t * 3.6, -4.2, 6.5 + 3.0 * math.sqrt(max(0, 1 - t * t)) - 0.6))), 0.35, 1.4, teeth, rot=(PI, 0, 0), verts=8, outline=0.02)
        A.cone('SilTD%d' % i, tuple(b + Vector((t * 3.4, -4.2, 6.5 - 2.8 * math.sqrt(max(0, 1 - t * t)) + 0.6))), 0.32, 1.2, teeth, verts=8, outline=0.02)
    bone = A.toon('BoneB', '#ece2cc', shade='#9a8d74')
    hornd = A.toon('HornB', '#3a2a22')
    rr = random.Random(9)
    for i in range(40):
        a = rr.uniform(0, math.tau)
        rad = rr.uniform(4, 16)
        S.cow_skull('BSkull%d' % i, tuple(c + Vector((math.cos(a) * rad, abs(math.sin(a)) * rad + 6, rr.uniform(0.1, 0.5)))), bone, hornd,
                    s=rr.uniform(0.25, 0.5), rot=rr.uniform(0, 6))


def bake_follow(objs_offsets, arm, bone, f0, f1, step=1):
    """Objekte folgen einem Knochen (Weltposition gebacken) – z. B. Finger in Sukunas Hand."""
    sc = bpy.context.scene
    pb = arm.pose.bones[bone]
    for f in range(f0, f1 + 1, step):
        sc.frame_set(f)
        M = arm.matrix_world @ pb.matrix
        for o, off in objs_offsets:
            A.key(o, f, loc=tuple(M @ Vector(off)))


def bone_world(arm, bone, frame, off=(0, 0, 0)):
    sc = bpy.context.scene
    sc.frame_set(frame)
    return arm.matrix_world @ arm.pose.bones[bone].matrix @ Vector(off)


def flame_blade(name, root, height, width, lean, mat, twist=0.0):
    """Eine Flammenzacke der Aura: flach, unten breit, oben messerscharf, leicht geschwungen."""
    r = Vector(root)
    d = Vector((lean[0], lean[1], 1.0)).normalized()
    side = Vector((-d.y, d.x, 0)).normalized() if abs(d.z) < 0.99 else Vector((1, 0, 0))
    pts = [r, r + d * height * 0.4 + side * width * 0.3, r + d * height * 0.75 - side * width * 0.2, r + d * height]
    o = C.sweep(name, pts, [(width, width * 0.18), (width * 0.8, width * 0.15), (width * 0.4, width * 0.1), (0.002, 0.002)], mat,
                ring_n=8, rings=14, up_hint=(lean[1], -lean[0], 0.0001) if (lean[0] or lean[1]) else (0, 1, 0), twist=twist)
    A.no_ink(o)
    return o


def red_aura(center, f0, f1, power=1.0, seed=1):
    """Super-Aura wie in Anime-Kampfspielen – nur in Rot: Flammenzacken (außen rot, innen gelb-weiß), Energie-Bänder,
    graue Windschlieren, Brocken, Risse im Boden. Flackert, wächst ab f0."""
    rr = random.Random(seed)
    c = Vector(center)
    outer = A.glow('AuraOuter', '#ff2a14', 4, alpha=0.45)
    mid = A.glow('AuraMid', '#ff7a1a', 5, alpha=0.4)
    core = A.glow('AuraCore', '#fff0c8', 6, alpha=0.3)
    objs = []
    for layer, (mat, n, hmin, hmax, rad) in enumerate(((outer, 26, 2.4, 4.6, 0.85), (mid, 18, 1.6, 3.2, 0.62), (core, 8, 1.0, 2.0, 0.55))):
        for i in range(int(n * power)):
            a = rr.uniform(-0.25 * PI, 1.25 * PI)     # nur hinter und neben ihm (vorne bleibt frei, er ist klar zu sehen)
            rad_i = rad * rr.uniform(0.85, 1.2)
            root = c + Vector((math.cos(a) * rad_i, math.sin(a) * rad_i, rr.uniform(-0.1, 0.5)))
            lean = (math.cos(a) * rr.uniform(0.15, 0.45), math.sin(a) * rr.uniform(0.15, 0.45))
            h = rr.uniform(hmin, hmax) * (0.8 + 0.2 * power)
            o = flame_blade('Flame%d_%d' % (layer, i), root, h, rr.uniform(0.16, 0.32), lean, mat, twist=rr.uniform(-0.6, 0.6))
            o.data.transform(Matrix.Translation(-root))
            o.location = root
            A.key(o, 1, scale=0.001)
            start = f0 + rr.randint(0, 6)
            A.key(o, start, scale=0.001)
            for f in range(start + 3, f1 + 1, 2):
                A.key(o, f, scale=(1.0, 1.0, rr.uniform(0.75, 1.25)))
            objs.append(o)
    # Energie-Bänder, die um ihn herum peitschen
    band_m = A.glow('AuraBand', '#ff5a1a', 9)
    for i in range(int(12 * power)):
        a0 = rr.uniform(0, math.tau)
        rad = rr.uniform(1.4, 4.0)
        z0 = rr.uniform(0.2, 3.5)
        pts = [c + Vector((math.cos(a0 + t) * rad, math.sin(a0 + t) * rad, z0 + t * rr.uniform(-0.6, 0.9))) for t in (0, 0.5, 1.0, 1.4)]
        o = C.sweep('AuraBand%d' % i, pts, [0.004, 0.05, 0.035, 0.002], band_m, ring_n=6, rings=16, flat=0.3)
        A.no_ink(o)
        piv = A.empty('BandPiv%d' % i, tuple(c))
        o.parent = piv
        A.key(piv, 1, rot=(0, 0, 0), scale=0.001)
        A.key(piv, f0 + 4, rot=(0, 0, 0), scale=0.001)
        A.key(piv, f0 + 8, rot=(0, 0, 1.0), scale=1.0)
        A.key(piv, f1, rot=(0, 0, 1.0 + (f1 - f0) * 0.18 * (1 if i % 2 else -1)), scale=1.0)
        objs.append(o)
    # graue Windschlieren (wie Druckwellen im Himmel)
    wind = A.glow('AuraWind', '#d8d8e0', 1.4, alpha=0.35)
    for i in range(int(16 * power)):
        a = rr.uniform(0, math.tau)
        z = rr.uniform(1.0, 9.0)
        d = Vector((math.cos(a), math.sin(a), rr.uniform(-0.1, 0.25))).normalized()
        st = c + d * 2.5 + Vector((0, 0, z))
        o = A.cube('Wind%d' % i, tuple(st), (rr.uniform(2.0, 5.0), 0.02, rr.uniform(0.08, 0.3)), wind, rot=(0, rr.uniform(-0.3, 0.3), a))
        A.key(o, 1, loc=tuple(st), scale=(0.001, 0.001, 0.001))
        A.key(o, f0 + 2, loc=tuple(st), scale=(0.001, 0.001, 0.001))
        A.key(o, f0 + 6, loc=tuple(st + d * 3), scale=(rr.uniform(2.0, 5.0), 0.02, rr.uniform(0.08, 0.3)))
        A.key(o, f1, loc=tuple(st + d * 16), scale=(rr.uniform(4.0, 9.0), 0.02, rr.uniform(0.05, 0.2)))
        objs.append(o)
    # Brocken steigen auf und kreisen
    rock = A.toon('AuraRock', '#2a2024', shade='#120c0e', highlight='#4a3a3e')
    for i in range(int(40 * power)):
        a = rr.uniform(0, math.tau)
        rad = rr.uniform(1.0, 5.0)
        p0 = c + Vector((math.cos(a) * rad, math.sin(a) * rad, 0.05))
        b = S.blob('Debris%d' % i, rr.uniform(0.04, 0.16), rock, 900 + i, outline=0.004)
        b.location = p0
        A.key(b, 1, loc=tuple(p0))
        A.key(b, f0, loc=tuple(p0))
        p1 = c + Vector((math.cos(a + 1.5) * rad * 1.2, math.sin(a + 1.5) * rad * 1.2, rr.uniform(1.5, 7.0)))
        A.key(b, f1, loc=tuple(p1), rot=(rr.uniform(0, 9), rr.uniform(0, 9), rr.uniform(0, 9)))
        objs.append(b)
    # rote Blitze
    bolt = A.glow('AuraBolt', '#ff3a3a', 12)
    for i in range(int(10 * power)):
        a = rr.uniform(0, math.tau)
        pts = [c + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, rr.uniform(0.5, 2.0)))]
        for k in range(4):
            pts.append(pts[-1] + Vector((math.cos(a) * 0.5 + rr.uniform(-0.3, 0.3), math.sin(a) * 0.5 + rr.uniform(-0.3, 0.3), rr.uniform(-0.2, 0.5))))
        o = C.sweep('Bolt%d' % i, pts, [0.02] * 5, bolt, ring_n=4, rings=12)
        A.no_ink(o)
        fon = f0 + 6 + rr.randint(0, max(1, f1 - f0 - 12))
        A.visible(o, 1, False)
        for k in range(3):
            A.visible(o, fon + k * 9, True)
            A.visible(o, fon + k * 9 + 2, False)
        objs.append(o)
    crater = A.cylinder('Crater', tuple(c + Vector((0, 0, 0.01))), 2.4, 0.02, A.glow('CraterM', '#ff2a14', 2.5, alpha=0.6), verts=48, outline=0)
    A.key(crater, 1, scale=0.001)
    A.key(crater, f0, scale=0.001)
    A.key(crater, f0 + 6, scale=1.0)
    objs.append(crater)
    for o in objs:
        A.no_ink(o)
    return objs


def finger_feast(n):
    """Sukuna isst n Finger (1–3), 8 s:
         1– 40  Nahaufnahme: offene Hand (Handfläche nach OBEN), die Finger liegen darauf
        41– 52  Sukuna wirft die Finger hoch
        53– 68  Die Finger wirbeln vor dem roten Himmel
        69–108  Nahaufnahme Gesicht: Maul weit offen, die Finger fallen hinein – Maul zu, „ゴクッ“ (geschluckt)
       109–192  Super-Aura in Rot: Flammenzacken, Energie-Bänder, Windschlieren, Brocken, Blitze – Heldenpose"""
    FR = 192
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=8, threshold=0.75, mix=0.6)
    A.sun(2.0, rot=(math.radians(50), math.radians(10), math.radians(-30)))
    A.ink()
    domain_backdrop((0, 0, 0))
    Su = cast.build_char('sukuna', 'Suk', loc=(0, 0, 0), facing=0.0, sign=False)
    C.hand_switch(Su, 1, 'R', 'open')
    C.hand_switch(Su, 1, 'L', 'claw')
    rest = {'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0), 'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0), 'head': (0, 0, 0), 'chest': (0, 0, 0)}
    C.pose(Su, 1, **dict(rest, **{'upper.R': (-50, 0, 15), 'fore.R': (-60, 0, 0)}))
    C.pose(Su, 42, **{'upper.R': (-50, 0, 15), 'fore.R': (-60, 0, 0)})
    C.pose(Su, 45, **{'upper.R': (-80, 0, 15), 'fore.R': (-100, 0, 0)})
    C.pose(Su, 49, **{'upper.R': (-165, 0, 12), 'fore.R': (-15, 0, 0)})
    C.pose(Su, 62, **{'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0)})
    tilt = {'head': (-32, 0, 0), 'chest': (-8, 0, 0)}
    C.pose(Su, 68, **tilt)
    C.pose(Su, 100, **tilt)
    C.pose(Su, 106, head=(10, 0, 0), chest=(0, 0, 0))
    # ── Nahaufnahme-Requisit: Hand mit Handfläche nach oben (eigenes Modell, damit nichts durch die Hand geht) ──
    sk_m = bpy.data.materials['SukSkin']
    nail_m = bpy.data.materials.get('SukNail')
    prop = A.empty('PropHand', (30, 0, 1.2))
    ph = C.hand_mesh('PropHandM', 'R', 'open', sk_m, nail=nail_m, scale=1.0)
    S.orient_hand(ph, (30, 0, 1.2), (1, 0.25, -0.05), (0, 0, 1))   # Finger nach rechts, Handfläche nach OBEN
    A.add_outline(ph, 0.0025)
    sleeve = C.sweep('PropSleeve', [(29.58, -0.1, 1.24), (29.78, -0.05, 1.22), (29.97, 0, 1.2)], [(0.13, 0.15), (0.1, 0.1), (0.05, 0.045)],
                     bpy.data.materials['SukCoat'], ring_n=20, rings=10, up_hint=(0, 0, 1), cap0=False)
    A.add_outline(sleeve, 0.003)
    for o in (ph, sleeve):
        A.parent_keep(o, prop)
    fingers = []
    palm = Vector((30.07, 0.02, 1.225))
    for i in range(n):
        f = cast.sukuna_finger('Finger%d' % i)
        fingers.append(f)
        lay = palm + Vector((0.0, -0.022 + i * 0.022, 0.012 + 0.004 * i))
        A.key(f, 1, loc=tuple(lay), rot=(0, math.radians(90), math.radians(10 - 12 * i)))
        A.key(f, 40, loc=tuple(lay + Vector((0, 0, 0.002))), rot=(0, math.radians(90), math.radians(12 - 12 * i)))
    # ── Wurf: Finger starten über Sukunas echter Hand (nicht in ihr) ──
    sc = bpy.context.scene
    catches = [80, 88, 96][:n]
    face_pts = []
    for cf in catches:
        face_pts.append(bone_world(Su['arm'], 'head', cf, (0, 0.065, 0.11)))   # Mund: lokal Y = oben, +Z = vorne
    for i, f in enumerate(fingers):
        p0 = bone_world(Su['arm'], 'hand.R', 41, (0, 0.06, 0)) + Vector((0, 0, 0.08 + 0.02 * i))
        A.key(f, 41, loc=tuple(p0), rot=(0, math.radians(90), 0))
        A.key(f, 44, loc=tuple(p0), rot=(0, math.radians(90), 0))
        peak = p0 + Vector((0.12 * (i - 1), -0.15, 2.4 + 0.25 * i))
        A.key(f, 58, loc=tuple(peak), rot=(5 + i, 7, 2))
        above = face_pts[i] + Vector((0, -0.2, 0.5))
        A.key(f, catches[i] - 6, loc=tuple(above), rot=(0.3, 0.1, 0))
        A.key(f, catches[i], loc=tuple(face_pts[i]), rot=(0.15, 0, 0))
        S.show_from([f], 1, catches[i] + 1)
    # Maul auf → zu nach dem letzten Finger
    big = [o for o in bpy.data.objects if o.name.startswith(('SukBigMouth',))]
    small = [o for o in bpy.data.objects if o.name in ('SukMouthO', 'SukMouthL', 'SukTeethU', 'SukTeethD')]
    last = catches[-1]
    for o in big:
        A.visible(o, 1, False)
        A.visible(o, 66, True)
        A.visible(o, last + 2, False)
    for o in small:
        A.visible(o, 1, True)
        A.visible(o, 66, False)
        A.visible(o, last + 2, True)
    gulp = S.text_obj('Gulp', 'ゴクッ', 0.16, A.glow('GulpM', '#ffffff', 3), extrude=0.01)
    gulp.location = tuple(bone_world(Su['arm'], 'neck', last + 4, (0.18, 0.0, -0.08)) + Vector((0, -0.25, 0)))
    gulp.rotation_euler = (PI / 2, 0, 0.15)
    A.key(gulp, 1, scale=0.001)
    A.key(gulp, last + 3, scale=0.001)
    A.key(gulp, last + 6, scale=1.3)
    A.key(gulp, last + 10, scale=1.0)
    A.key(gulp, last + 14, scale=0.001)
    C.pose(Su, last + 3, head=(-32, 0, 0))
    C.pose(Su, last + 6, head=(-10, 0, 0))   # Schlucken: Kopf nickt
    # ── Super-Aura ──
    A0 = 112
    C.hand_switch(Su, A0 - 4, 'R', 'fist')
    C.hand_switch(Su, A0 - 4, 'L', 'fist')
    power = {'upper.R': (-6, 0, 32), 'fore.R': (-35, 0, 0), 'upper.L': (-6, 0, -32), 'fore.L': (-35, 0, 0), 'spine': (-6, 0, 0),
             'chest': (-6, 0, 0), 'head': (-6, 0, 0), 'thigh.L': (0, 0, -8), 'thigh.R': (0, 0, 8)}
    C.pose(Su, A0 - 4, **power)
    C.pose(Su, FR, **power)
    red_aura((0, 0, 0), A0, FR + 8, power=0.75 + 0.25 * n, seed=n)
    iris = bpy.data.materials.get('SukIris')
    if iris:
        em = iris.node_tree.nodes.get('Emission')
        for f, v in ((1, 2.2), (A0 - 6, 2.2), (A0, 16 + 4 * n), (FR, 10)):
            em.inputs['Strength'].default_value = v
            em.inputs['Strength'].keyframe_insert('default_value', frame=f)
    for k in range(n + 1):
        S.shockwave((0, 0, 0.05), A0 + k * 6, '#ff3030', life=22, size=7 + 3 * k)
    cam, tgt = A.camera(lens=40)
    flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 2.5), outline=0)
    flash.parent = cam
    A.visible(flash, 1, False)
    flashes = [A0]
    for f in flashes:
        A.visible(flash, f, True)
        A.visible(flash, f + 2, False)
    face = bone_world(Su['arm'], 'head', 84, (0, 0.08, 0.1))
    K = [(1, (30.1, -0.5, 1.36), (30.05, 0.0, 1.23), 50), (40, (30.08, -0.43, 1.34), (30.05, 0.0, 1.23), 56),
         (41, (0.9, -2.6, 1.4), (0, 0, 1.6), 32), (52, (0.8, -2.4, 1.4), (0, 0, 1.9), 32),
         (53, (0.6, -1.5, 2.6), (0, -0.1, 3.8), 45), (68, (0.5, -1.4, 2.6), (0, -0.1, 3.4), 45),
         (69, tuple(face + Vector((0.08, -0.42, 0.42))), tuple(face), 42),
         (last + 2, tuple(face + Vector((0.07, -0.36, 0.36))), tuple(face), 46),
         (last + 3, tuple(face + Vector((0.3, -0.75, -0.05))), tuple(face + Vector((0, 0, -0.1))), 42),
         (A0 - 1, tuple(face + Vector((0.26, -0.68, -0.05))), tuple(face + Vector((0, 0, -0.1))), 45),
         (A0, (1.6, -4.4, 0.35), (0, 0, 1.6), 22), (FR - 34, (1.9, -5.0, 0.45), (0, 0, 1.8), 22),
         (FR - 33, (0.5, -1.4, 1.65), (0, 0, 1.7), 40), (FR, (0.45, -1.15, 1.7), (0, 0, 1.72), 46)]
    cuts = {40, 52, 68, last + 2, A0 - 1, FR - 34}
    for f, pos, look, lens in K:
        A.cam_key(cam, tgt, f, pos, look, lens)
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) in cuts else 'BEZIER'
    S.shake(cam, [A0, A0 + 20, A0 + 40], strength=0.05, length=14)
    S.speedlines(cam, [(53, 68), (A0, A0 + 14)])
    bpy.context.scene.frame_end = FR
    return FR


def resonance():
    """Nobaras Resonanz: Nagel + Finger in die Luft, Hammerschlag, der Nagel nagelt den Finger an eine Mauer –
    Schnitt: Sukuna in seiner Domain, Impact-Frame, er geht in die Knie und hält sich die Brust."""
    FR = 216
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=7, threshold=0.8, mix=0.45)
    A.sun(2.0, rot=(math.radians(55), math.radians(10), math.radians(-30)))
    A.ink()
    import mahoraga as MH
    MH.environment()
    wallm = A.toon('WallC', '#5a5e6a', shade='#2a2c34', highlight='#7a7e8a')
    A.cube('ConcreteWall', (4.2, 0.0, 2.0), (0.25, 3.5, 2.5), wallm, outline=0.03)
    N = cast.build_char('nobara', 'Nob', loc=(0, 0, 0), facing=PI / 2 - 0.9, sign=False)
    C.hand_switch(N, 1, 'L', 'relaxed')
    C.pose(N, 1, **{'upper.L': (-40, 0, -10), 'fore.L': (-70, 0, 0), 'upper.R': (0, 0, 10), 'fore.R': (-20, 0, 0), 'head': (5, 0, 0)})
    C.pose(N, 26, **{'upper.L': (-40, 0, -10), 'fore.L': (-70, 0, 0)})
    C.pose(N, 32, **{'upper.L': (-150, 0, -10), 'fore.L': (-10, 0, 0)})
    C.hand_switch(N, 32, 'L', 'open')
    C.pose(N, 40, **{'upper.R': (20, 0, 60), 'fore.R': (-60, 0, 0), 'spine': (0, 30, 0), 'upper.L': (-100, 0, -10)})   # Ausholen
    C.pose(N, 50, **{'upper.R': (30, 0, 70), 'fore.R': (-80, 0, 0), 'spine': (0, 40, 0)})
    C.pose(N, 55, **{'upper.R': (-95, 0, -20), 'fore.R': (-5, 0, 0), 'spine': (10, -30, 0), 'upper.L': (-30, 0, -20)})  # Schlag
    C.pose(N, 80, **{'upper.R': (-80, 0, -15), 'fore.R': (-10, 0, 0), 'spine': (5, -20, 0)})
    # Nagel + Finger
    steel = A.toon('NailSteel', '#b8c0cc', shade='#5a626e', highlight='#ffffff')
    nail = C.sweep('Nail', [(0, 0, 0.05), (0, 0, -0.06)], [0.006, 0.0008], steel, ring_n=8, rings=4)
    nhead = C.ellipsoid('NailHead', (0, 0, 0.055), (0.014, 0.014, 0.004), steel, seg=10)
    nroot = A.empty('NailRoot', (0, 0, 0))
    for o in (nail, nhead):
        o.parent = nroot
        C.outline(o, 0.0008)
    finger = cast.sukuna_finger('NobFinger')
    hand_p = bone_world(N['arm'], 'hand.L', 26, (0, 0.08, 0))
    air = hand_p + Vector((0.15, 0, 0.9))
    hit = air + Vector((0.12, 0, -0.1))
    wall = Vector((4.0, hit.y, hit.z))
    A.key(finger, 1, loc=tuple(hand_p), rot=(0.5, 0, 0))
    A.key(finger, 30, loc=tuple(hand_p), rot=(0.5, 0, 0))
    A.key(finger, 40, loc=tuple(air), rot=(2.0, 0.6, 0))
    A.key(finger, 55, loc=tuple(air + Vector((0.05, 0, 0.02))), rot=(2.3, 0.9, 0.2))
    A.key(finger, 63, loc=tuple(wall + Vector((-0.06, 0, 0))), rot=(PI / 2, 0, PI / 2))
    A.key(nroot, 1, loc=tuple(hand_p + Vector((0, 0, 0.03))), rot=(0, PI / 2, 0))
    A.key(nroot, 30, loc=tuple(hand_p + Vector((0, 0, 0.03))), rot=(0, PI / 2, 0))
    A.key(nroot, 40, loc=tuple(air + Vector((-0.12, 0, 0))), rot=(0.4, PI / 2 + 1.2, 0))
    A.key(nroot, 54, loc=tuple(air + Vector((-0.1, 0, -0.03))), rot=(0, PI / 2, 0))
    A.key(nroot, 55, loc=tuple(air + Vector((-0.08, 0, -0.03))), rot=(0, PI / 2, 0))
    A.key(nroot, 63, loc=tuple(wall + Vector((-0.02, 0, 0))), rot=(0, PI / 2, 0))
    for o in (finger, nroot):
        A.set_interp(o, 'BEZIER')
    # Resonanz: Wellen am Finger, Risse in der Mauer
    for k in range(4):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.008, location=tuple(wall + Vector((-0.08, 0, 0))), rotation=(0, PI / 2, 0))
        t = bpy.context.active_object
        A.set_mat(t, A.glow('ResRing', '#7ab8ff', 6))
        A.key(t, 1, scale=0.01)
        A.key(t, 63 + k * 8, scale=0.01)
        A.key(t, 75 + k * 8, scale=9)
        S.show_from([t], 63 + k * 8, 76 + k * 8)
    S.shards('WallChips', tuple(wall + Vector((-0.1, 0, -1.0))), ['#5a5e6a', '#8a8e9a'], 63, n=26, spread=1.2, up=1.2, size=0.05, seed=31)
    crack = A.flat('Crack', '#141418')
    rr = random.Random(4)
    for k in range(10):
        a = k / 10 * math.tau
        ln = rr.uniform(0.3, 0.9)
        c = A.cube('Crack%d' % k, tuple(wall + Vector((0.01, math.cos(a) * ln / 2, math.sin(a) * ln / 2))), (0.005, ln / 2, 0.008), crack, rot=(a, 0, 0))
        S.show_from([c], 63)
    kanji = S.text_obj('ResKanji', '共鳴', 0.5, A.glow('ResKM', '#7ab8ff', 5), extrude=0.03)
    kanji.location = tuple(wall + Vector((-0.3, -0.6, 0.6)))
    kanji.rotation_euler = (PI / 2, 0, -PI / 2 + 0.3)
    A.key(kanji, 1, scale=0.001)
    A.key(kanji, 66, scale=0.001)
    A.key(kanji, 70, scale=1.3)
    A.key(kanji, 74, scale=1.0)
    # ── Szene B: Sukuna in seiner Domain – Resonanz trifft ihn, Impact-Frame mit leuchtendem Herz ──
    B = Vector((300, 0, 0))
    domain_backdrop(B)
    Su = cast.build_char('sukuna', 'Suk', loc=tuple(B), facing=0.0, sign=False)
    SX = cast.build_char('sukuna', 'SukX', loc=tuple(B), facing=0.0, sign=False)   # schwarze Silhouette für den Impact-Frame
    black = A.flat('SilhouetteBlack', '#050505')
    for o in bpy.data.objects:
        if o.name.startswith('SukX') and o.type == 'MESH':
            for slot in o.material_slots:
                slot.material = black
    for fig in (Su, SX):
        C.hand_switch(fig, 1, 'R', 'claw')
        C.hand_switch(fig, 1, 'L', 'claw')

    def both(f, **rots):
        C.pose(Su, f, **rots)
        C.pose(SX, f, **rots)
    stand = {'upper.R': (0, 0, 10), 'upper.L': (0, 0, -10), 'fore.R': (-12, 0, 0), 'fore.L': (-12, 0, 0), 'head': (0, 0, 0), 'spine': (0, 0, 0),
             'chest': (0, 0, 0), 'thigh.L': (0, 0, 0), 'shin.L': (0, 0, 0), 'thigh.R': (0, 0, 0), 'shin.R': (0, 0, 0)}
    both(1, **stand)
    both(119, **dict(stand, head=(-5, 0, 0)))
    both(121, **dict(stand, spine=(-18, 0, 0), head=(-32, 0, 0), **{'upper.R': (-45, 0, -35), 'fore.R': (-115, 0, 0)}))   # Schock
    clutch = {'thigh.L': (-85, 0, 0), 'shin.L': (90, 0, 0), 'thigh.R': (-5, 0, 0), 'shin.R': (100, 0, 0), 'spine': (30, 0, 0), 'chest': (10, 0, 0),
              'head': (22, 0, 0), 'upper.R': (-55, 0, -38), 'fore.R': (-110, 0, 0), 'upper.L': (-25, 0, -25), 'fore.L': (-35, 0, 0)}
    both(125, **clutch)
    both(FR, **clutch)
    for fig in (Su, SX):
        A.key(fig['arm'], 1, loc=tuple(B))
        A.key(fig['arm'], 121, loc=tuple(B))
        A.key(fig['arm'], 125, loc=tuple(B + Vector((0, 0.05, -0.5))))
    # Herz + Adern (gehören zur Silhouette, liegen knapp vor der Brust)
    red = A.glow('HeartGlow', '#ff1a1a', 9)
    # Herz + Adern: im Ruhe-Koordinatensystem der Figur gebaut (Ursprung), dann an das Rig gehängt
    heart_c = Vector((0.045, -0.165, 1.37))
    heart = []
    for sx in (-1, 1):
        heart.append(C.ellipsoid('SukXHeartLobe%d' % sx, tuple(heart_c + Vector((sx * 0.018, 0, 0.012))), (0.024, 0.012, 0.022), red, seg=14))
    heart.append(C.sweep('SukXHeartTip', [heart_c + Vector((0, 0, 0.01)), heart_c + Vector((0, 0, -0.035))], [0.03, 0.002], red, ring_n=10, rings=4,
                         flat=0.4))
    rr = random.Random(12)
    vein = A.glow('VeinGlow', '#ff2020', 6)
    for i in range(14):
        a = i / 14 * math.tau + rr.uniform(-0.2, 0.2)
        pts = [heart_c]
        d = Vector((math.cos(a) * 1.0, 0, math.sin(a) * 1.25))
        for k in range(5):
            last = pts[-1]
            step = d * rr.uniform(0.035, 0.06) + Vector((rr.uniform(-0.02, 0.02), 0, rr.uniform(-0.02, 0.02)))
            nxt = last + step
            nxt.y = -0.17 + 0.03 * (nxt.x ** 2) * 6
            pts.append(nxt)
        heart.append(C.sweep('SukXVein%d' % i, pts, [0.006, 0.005, 0.004, 0.003, 0.002, 0.001], vein, ring_n=6, rings=14))
        if i % 2 == 0:   # Verzweigung
            mid = pts[2]
            br = [mid, mid + Vector((rr.uniform(-0.05, 0.05), 0, rr.uniform(-0.05, 0.05))), mid + Vector((rr.uniform(-0.09, 0.09), 0, rr.uniform(-0.09, 0.09)))]
            heart.append(C.sweep('SukXVeinB%d' % i, br, [0.0035, 0.002, 0.0008], vein, ring_n=6, rings=8))
    for o in heart:
        A.no_ink(o)
        C.bind(o, SX['arm'], bones=['chest', 'spine', 'neck', 'upper.L', 'upper.R'])
    # grauer Raum für den Impact-Frame
    gray = A.flat('ImpactGray', '#8c8c94')
    dome = A.sphere('ImpactDome', tuple(B), 4.0, gray, segments=32, outline=0)
    for p in dome.data.polygons:
        p.flip()
    floor = A.cube('ImpactFloor', tuple(B + Vector((0, 0, 0.004))), (4, 4, 0.004), A.flat('ImpactFloorM', '#6e6e76'))
    impact_on = [(126, 134), (138, 143)]
    sil = [o for o in bpy.data.objects if o.name.startswith('SukX') and o.type in ('MESH', 'ARMATURE')] + [dome, floor]
    norm = [o for o in bpy.data.objects if o.name.startswith('Suk') and not o.name.startswith('SukX') and o.type in ('MESH', 'ARMATURE')]
    for o in sil:
        A.visible(o, 1, False)
        for a0, a1 in impact_on:
            A.visible(o, a0, True)
            A.visible(o, a1, False)
    for o in norm:
        A.visible(o, 1, True)
        for a0, a1 in impact_on:
            A.visible(o, a0, False)
            A.visible(o, a1, True)
    S.shockwave(tuple(B + Vector((0, 0, 0.05))), 143, '#7ab8ff', life=18, size=7)
    S.sparks_rise('PainSpark', tuple(B), '#7ab8ff', 30, 121, FR + 40, radius=0.8, height=2.5, size=0.01)
    S.show_from([o for o in bpy.data.objects if o.name.startswith('PainSpark')], 143)
    cam, tgt = A.camera(lens=35)
    flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 2.5), outline=0)
    flash.parent = cam
    A.visible(flash, 1, False)
    hits = [55, 63, 120]
    for f in hits:
        A.visible(flash, f, True)
        A.visible(flash, f + 1, False)
    ctx = {'cam': cam}
    S.black_frames(ctx, [56])
    redf = A.cube('ImpactRed', (0, 0, -0.58), (2, 2, 0.01), A.glow('ImpRedM', '#ff1a1a', 2.5), outline=0)
    redf.parent = cam
    A.visible(redf, 1, False)
    A.visible(redf, 125, True)
    A.visible(redf, 126, False)
    K = [(1, (1.4, -2.9, 1.5), (0.2, 0, 1.4), 34), (28, (1.2, -2.6, 1.5), (0.2, 0, 1.45), 36),
         (29, tuple(air + Vector((0.6, -1.4, -0.2))), tuple(air), 45), (54, tuple(air + Vector((0.45, -1.1, -0.15))), tuple(air), 52),
         (55, (2.0, -3.6, 1.9), (2.0, 0, 1.9), 26), (62, (2.6, -3.4, 1.9), (3.2, 0, 1.9), 26),
         (63, tuple(wall + Vector((-0.9, -0.9, 0.1))), tuple(wall), 40), (110, tuple(wall + Vector((-0.6, -0.6, 0.05))), tuple(wall), 48),
         (111, tuple(B + Vector((0.4, -3.4, 1.4))), tuple(B + Vector((0, 0, 1.6))), 32), (120, tuple(B + Vector((0.35, -3.0, 1.45))), tuple(B + Vector((0, 0, 1.6))), 34),
         (121, tuple(B + Vector((0.2, -1.6, 1.6))), tuple(B + Vector((0, 0, 1.45))), 38), (125, tuple(B + Vector((0.2, -1.8, 1.3))), tuple(B + Vector((0, 0, 1.1))), 38),
         (126, tuple(B + Vector((0.05, -2.3, 1.05))), tuple(B + Vector((0, 0, 0.95))), 36), (143, tuple(B + Vector((0.05, -2.0, 1.05))), tuple(B + Vector((0, 0, 0.95))), 38),
         (144, tuple(B + Vector((2.2, -3.4, 0.4))), tuple(B + Vector((0, 0, 0.9))), 26), (FR, tuple(B + Vector((1.6, -2.6, 0.5))), tuple(B + Vector((0, 0, 0.95))), 28)]
    cuts = {28, 54, 62, 110, 120, 125, 143}
    for f, pos, look, lens in K:
        A.cam_key(cam, tgt, f, pos, look, lens)
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) in cuts else 'BEZIER'
    S.shake(cam, hits + [126, 138], strength=0.05, length=10)
    S.speedlines(cam, [(55, 63), (121, 126)])
    bpy.context.scene.frame_end = FR
    return FR


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    if argv[0] in ('finger', 'resonance'):
        if argv[0] == 'finger':
            n, mode, out = int(argv[1]), argv[2], argv[3]
            FR = finger_feast(n)
        else:
            mode, out = argv[1], argv[2]
            FR = resonance()
        os.makedirs(out, exist_ok=True)
        if mode == 'preview':
            A.render_frames(out, [int(x) for x in argv[-1].split(',')] if ',' in argv[-1] else [10, 40, 52, 66, 80, 100, 122, 125, 140, 160])
        else:
            A.render_frames(out)
    elif argv[0] == 'verdict':
        variant, mode, out = argv[1], argv[2], argv[3]
        os.makedirs(out, exist_ok=True)
        FR = verdict(variant)
        if mode == 'preview':
            A.render_frames(out, [20, 60, 90, 120, 150, 165, 175, 190, 200, 214])
        elif mode == 'intro':
            A.render_frames(out, list(range(1, 97)))
        elif mode == 'tail':
            A.render_frames(out, list(range(97, FR + 1)))
        else:
            A.render_frames(out)
    else:
        mode, out = argv[1], argv[2]
        os.makedirs(out, exist_ok=True)
        FR = spin()
        if mode == 'preview':
            A.render_frames(out, [5, 15, 20, 30, 45, 58])
        else:
            A.render_frames(out)
    print('FERTIG')
