"""Unlimited Void – Siegesanimation (Gojo).

Aufruf:
  blender -b --factory-startup -P blender/void.py -- preview <ordner>   (nur Testbilder)
  blender -b --factory-startup -P blender/void.py -- full <ordner>      (alle Bilder)
"""
import bpy
import sys
import os
import math
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['preview', os.path.abspath('render_void')]
MODE, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)

FRAMES = 288
A.reset_scene()
S = A.setup_render(FRAMES, samples=12)
A.add_bloom(size=7, threshold=0.8, mix=0.5)
A.sun(2.5, rot=(math.radians(55), math.radians(15), math.radians(-35)))
rnd = random.Random(7)
PI = math.pi

# ───────── Figuren ─────────
GOJO = {'hair': '#f4f7fb', 'hairShade': '#a9b8d4', 'hairStyle': 'spiky', 'coat': '#141a2b', 'coatShade': '#070a12',
        'trim': '#2b4a8a', 'eyes': '#5ec8ff', 'eyeGlow': 4.0}


def gojo_fingers(prefix, J):
    # Zeige- und Mittelfinger gekreuzt (Gojos Zeichen) an der rechten Hand
    skin = A.toon(prefix + 'Skin', '#f3d6c4', shade='#c99a86')
    f1 = A.cylinder(prefix + 'F1', (0.01, -0.01, -0.45), 0.014, 0.11, skin, rot=(0, 0.35, 0), outline=0.005)
    f2 = A.cylinder(prefix + 'F2', (-0.01, -0.025, -0.45), 0.014, 0.11, skin, rot=(0, -0.35, 0), outline=0.005)
    f1.parent = J['el_r']
    f2.parent = J['el_r']


GOJO['extra'] = gojo_fingers

FOE = {'skin': '#8a7c9c', 'hair': '#140a1e', 'hairStyle': 'short', 'coat': '#2a1238', 'coatShade': '#12061a',
       'trim': '#7a1f3a', 'eyes': '#ff3355', 'eyeGlow': 5.0}


def foe_horns(prefix, J):
    horn = A.toon(prefix + 'Horn', '#e8dccb', shade='#9c8f7d')
    for sx in (-1, 1):
        h = A.cone(prefix + 'Horn%d' % sx, (0.09 * sx, 0, 0.3), 0.035, 0.2, horn, rot=(0, 0.45 * sx, 0), outline=0.008)
        h.parent = J['head']


FOE['extra'] = foe_horns

G = A.build_figure('Gojo', GOJO, loc=(-2.2, 0, 0), facing=PI / 2)
F = A.build_figure('Foe', FOE, loc=(2.2, 0, 0), facing=-PI / 2)

# Grundpose: Arme leicht vom Körper weg
for J, s in ((G, 1), (F, 1)):
    A.key(J['sh_l'], 1, rot=(0, 0.12, 0))
    A.key(J['sh_r'], 1, rot=(0, -0.12, 0))

# ───────── Boden & Clash ─────────
ground_mat = A.toon('Ground', '#10162a', shade='#05070d')
ground = A.cube('Ground', (0, 0, -0.05), (40, 40, 0.05), ground_mat)
blue = A.glow('ClashBlue', '#3b82f6', 4, alpha=0.35)
red = A.glow('ClashRed', '#ef4444', 4, alpha=0.35)
white = A.glow('White', '#ffffff', 12)
cb = A.sphere('ClashB', (-0.7, 0, 1.3), 0.6, blue, outline=0)
cr = A.sphere('ClashR', (0.7, 0, 1.3), 0.6, red, outline=0)
core = A.sphere('Core', (0, 0, 1.3), (0.12, 0.6, 1.1), white, outline=0)
for f in range(1, 140, 4):
    k = 1 + 0.12 * math.sin(f * 0.9)
    A.key(cb, f, loc=(-0.7 + 0.08 * math.sin(f * 0.7), 0, 1.3), scale=k)
    A.key(cr, f, loc=(0.7 - 0.08 * math.sin(f * 0.7), 0, 1.3), scale=2 - k)
    A.key(core, f, scale=(0.12 * (1 + 0.5 * math.sin(f * 1.3)), 0.6, 1.1))
sparks = []
for i in range(50):
    sp = A.sphere('Spark%d' % i, (0, 0, 1.3), 0.03, white, segments=8, outline=0)
    for f in range(1, 140, 3):
        A.key(sp, f, loc=(rnd.uniform(-0.4, 0.4), rnd.uniform(-1.2, 1.2), 1.3 + rnd.uniform(-1.2, 1.2)))
    sparks.append(sp)
for o in [cb, cr, core] + sparks:
    A.visible(o, 1, True)
    A.visible(o, 43, False)

# ───────── Unendliche Leere (Kugel mit Sternen + Galaxie) ─────────
void_mat = bpy.data.materials.new('VoidSky')
void_mat.use_nodes = True
nt = void_mat.node_tree
nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial')
em = nt.nodes.new('ShaderNodeEmission')
coord = nt.nodes.new('ShaderNodeTexCoord')
stars = nt.nodes.new('ShaderNodeTexVoronoi')
stars.inputs['Scale'].default_value = 140
sramp = nt.nodes.new('ShaderNodeValToRGB')
sramp.color_ramp.interpolation = 'EASE'
sramp.color_ramp.elements[0].position = 0.0
sramp.color_ramp.elements[0].color = (1, 1, 1, 1)
sramp.color_ramp.elements[1].position = 0.045
sramp.color_ramp.elements[1].color = (0, 0, 0, 1)
gal = nt.nodes.new('ShaderNodeTexNoise')
gal.inputs['Scale'].default_value = 1.6
gal.inputs['Detail'].default_value = 8
gramp = nt.nodes.new('ShaderNodeValToRGB')
gramp.color_ramp.elements[0].position = 0.42
gramp.color_ramp.elements[0].color = (0.0, 0.0, 0.01, 1)
gramp.color_ramp.elements[1].position = 0.75
gramp.color_ramp.elements[1].color = (*A._lin('#4a6cff'), 1)
mid = gramp.color_ramp.elements.new(0.6)
mid.color = (*A._lin('#2a145c'), 1)
add = nt.nodes.new('ShaderNodeMix')
add.data_type = 'RGBA'
add.blend_type = 'ADD'
add.inputs['Factor'].default_value = 1.0
nt.links.new(coord.outputs['Object'], stars.inputs['Vector'])
nt.links.new(coord.outputs['Object'], gal.inputs['Vector'])
nt.links.new(stars.outputs['Distance'], sramp.inputs['Fac'])
nt.links.new(gal.outputs['Fac'], gramp.inputs['Fac'])
nt.links.new(gramp.outputs['Color'], add.inputs[6])
nt.links.new(sramp.outputs['Color'], add.inputs[7])
nt.links.new(add.outputs[2], em.inputs['Color'])
em.inputs['Strength'].default_value = 1.6
nt.links.new(em.outputs[0], out.inputs['Surface'])
void_mat.use_backface_culling = False

void = A.sphere('Void', (-2.2, 0, 1.0), 30, void_mat, segments=64, outline=0)
A.key(void, 1, scale=0.001)
A.key(void, 139, scale=0.001)
A.key(void, 162, scale=30)
A.visible(void, 1, False)
A.visible(void, 139, True)
A.key(void, 139, rot=(0, 0, 0))
A.key(void, 288, rot=(0.2, 0.1, 1.2))
A.visible(ground, 1, True)
A.visible(ground, 158, False)
# Leuchtende Ringe der Domain
ring_mat = A.glow('Ring', '#9cc8ff', 3.5, alpha=0.8)
rings = []
for i, r in enumerate((3.0, 5.0, 8.0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.02, location=(-2.2, 0, 1.0))
    ring = bpy.context.active_object
    A.set_mat(ring, ring_mat)
    A.key(ring, 139, rot=(PI / 2 - 0.3 * i, 0.2 * i, 0), scale=0.01)
    A.key(ring, 165 + i * 4, scale=1)
    A.key(ring, 288, rot=(PI / 2 - 0.3 * i + 0.8, 0.2 * i + 0.6, 1.5))
    A.visible(ring, 1, False)
    A.visible(ring, 139, True)
    rings.append(ring)

# ───────── Gojo: Fingerzeichen, leuchtende Augen ─────────
A.key(G['sh_r'], 63, rot=(0, -0.12, 0))
A.key(G['sh_r'], 72, rot=(-1.45, -0.25, 0.25))
A.key(G['el_r'], 63, rot=(0, 0, 0))
A.key(G['el_r'], 72, rot=(-1.55, 0, 0))
A.key(G['head'], 63, rot=(0, 0, 0))
A.key(G['head'], 100, rot=(0.12, 0, 0))
eye = bpy.data.materials['GojoEye'].node_tree.nodes['Emission'].inputs['Strength']
for f, v in ((1, 4), (110, 4), (124, 26), (138, 12), (288, 8)):
    eye.default_value = v
    eye.keyframe_insert('default_value', frame=f)
# Aura um Gojo
# Randlicht (blau) von hinten + aufsteigende Energiepartikel statt einer Aura-Kugel
rim = bpy.data.lights.new('Rim', 'POINT')
rim.energy = 400
rim.color = (0.35, 0.6, 1.0)
rim_o = bpy.data.objects.new('Rim', rim)
bpy.context.collection.objects.link(rim_o)
rim_o.parent = G['root']
rim_o.location = (0, 0.9, 2.0)
aura_mat = A.glow('AuraP', '#8cc4ff', 6)
for i in range(22):
    p = A.cube('AuraP%d' % i, (0, 0, 0), (0.005, 0.005, 0.028), aura_mat)
    p.parent = G['root']
    a = rnd.uniform(0, math.tau)
    r = rnd.uniform(0.35, 0.7)
    off = rnd.randint(0, 40)
    for f in range(1 - off, 289, 40):
        A.key(p, max(f, 1), loc=(math.cos(a) * r, math.sin(a) * r, 0.1))
        A.key(p, max(f + 39, 1), loc=(math.cos(a) * r * 0.8, math.sin(a) * r * 0.8, 2.4))
    A.set_interp(p, 'LINEAR')

# ───────── Finisher ─────────
info_mat = A.glow('Info', '#bfe3ff', 8)
head_world = (2.2, 0, 1.92)
infos = []
for i in range(60):
    o = A.cube('Info%d' % i, (0, 0, 0), (0.03, 0.005, 0.05), info_mat)
    a = rnd.uniform(0, math.tau)
    b = rnd.uniform(-0.8, 0.8)
    r = rnd.uniform(3, 6)
    start = (head_world[0] + math.cos(a) * r, math.sin(a) * r, head_world[2] + b * 3)
    f0 = 181 + int(i * 0.5)
    A.key(o, 1, loc=start)
    A.key(o, f0, loc=start, rot=(rnd.random() * 3, rnd.random() * 3, rnd.random() * 3))
    A.key(o, f0 + 12, loc=head_world, rot=(rnd.random() * 9, rnd.random() * 9, rnd.random() * 9))
    A.visible(o, 1, False)
    A.visible(o, f0, True)
    A.visible(o, f0 + 13, False)
    infos.append(o)
# Gegner erstarrt: Zittern
for f in range(185, 228, 2):
    A.key(F['root'], f, loc=(2.2 + rnd.uniform(-0.015, 0.015), rnd.uniform(-0.015, 0.015), 0))
# Der leuchtende Punkt hinter dem Gegner
pt = A.sphere('VoidPoint', (2.75, 0, 1.95), 0.07, A.glow('Point', '#e6f3ff', 6), outline=0)
A.key(pt, 1, scale=0.001)
A.key(pt, 199, scale=0.001)
A.key(pt, 210, scale=0.07)
for f in range(212, 246, 3):
    A.key(pt, f, scale=0.07 * (0.9 + 0.25 * math.sin(f)))
A.key(pt, 247, scale=0.001)
# Gojo teleportiert sich direkt vor den Gegner und greift zu
for f, x in ((1, -2.2), (218, -2.2)):
    A.key(G['root'], f, loc=(x, 0, 0))
A.key(G['root'], 219, loc=(1.42, 0, 0))
A.set_interp(G['root'], 'CONSTANT')
A.key(G['sh_r'], 218, rot=(-1.45, -0.25, 0.25))
A.key(G['sh_r'], 222, rot=(-1.95, -0.1, 0.0))
A.key(G['el_r'], 218, rot=(-1.55, 0, 0))
A.key(G['el_r'], 222, rot=(-0.4, 0, 0))
# Weißer Blitz vor der Kamera
cam, tgt = A.camera(lens=28)
flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 3), outline=0)
flash.parent = cam
A.visible(flash, 1, False)
A.visible(flash, 226, True)
A.visible(flash, 229, False)
# Kopf fliegt (ohne Blut – stilisiert), Körper kippt
A.key(F['head'], 227, loc=(0, 0, 0.14), rot=(0, 0, 0))
A.key(F['head'], 236, loc=(0, 0.3, 1.1), rot=(2.5, 1.0, 3.0))
A.key(F['head'], 246, loc=(0, 0.9, 1.6), rot=(5.5, 2.0, 6.5), scale=0.6)
A.key(F['hips'], 229, rot=(0, 0, 0), loc=(0, 0, 0.98))
A.key(F['hips'], 246, rot=(-1.35, 0, 0), loc=(0, 0.3, 0.4))
A.visible(F['root'], 1, True)
for o in bpy.data.objects:
    if o.name.startswith('Foe'):
        A.visible(o, 1, True)
        A.visible(o, 252, False)

# Sieger-Pose: Arm runter, Kopf leicht gehoben
A.key(G['sh_r'], 250, rot=(-1.95, -0.1, 0.0))
A.key(G['sh_r'], 262, rot=(0, -0.12, 0))
A.key(G['el_r'], 250, rot=(-0.4, 0, 0))
A.key(G['el_r'], 262, rot=(0, 0, 0))
A.key(G['head'], 250, rot=(0.12, 0, 0))
A.key(G['head'], 270, rot=(-0.1, 0, 0))

# ───────── Kamera ─────────
CK = [
    # Totale, langsamer Dolly
    (1, (0, -9.5, 2.3), (0, 0, 1.3), 28), (42, (0, -7.8, 2.0), (0, 0, 1.3), 28),
    # Reißschwenk auf Gojo
    (48, (-1.35, -2.1, 1.8), (-2.2, 0, 1.7), 50), (62, (-1.45, -1.9, 1.75), (-2.2, 0, 1.72), 52),
    # Fingerzeichen, Untersicht
    (63, (-1.1, -0.95, 1.55), (-1.95, 0, 1.88), 40), (110, (-1.2, -0.8, 1.6), (-1.95, 0, 1.9), 46),
    # Augen extrem nah
    (111, (-1.05, -0.05, 1.93), (-2.07, 0, 1.92), 80), (138, (-1.4, -0.02, 1.92), (-2.07, 0, 1.92), 95),
    # Domain entfaltet sich, Kamera fährt zurück und kreist
    (139, (0.5, -5.5, 3.2), (-1.2, 0, 1.3), 22), (180, (4.0, -6.0, 3.8), (0, 0, 1.3), 24),
    # Gegner erstarrt, Informationsflut
    (181, (0.7, -2.7, 1.95), (2.2, 0, 1.75), 40), (217, (1.0, -2.3, 1.95), (2.2, 0, 1.8), 44),
    # Gojo erscheint – seitliche Einstellung, Kopf fliegt
    (218, (1.8, -3.4, 1.6), (1.85, 0, 1.6), 32), (246, (2.4, -3.9, 2.4), (2.2, 0.5, 2.6), 30),
    # Siegerfahrt um Gojo
    (247, (3.6, -2.2, 1.75), (1.42, 0, 1.6), 40), (288, (3.0, 2.0, 2.1), (1.42, 0, 1.65), 40),
]
for f, pos, look, lens in CK:
    A.cam_key(cam, tgt, f, pos, look, lens)
# Schnitte: zwischen den Einstellungen hart springen (CONSTANT), innerhalb weich
cuts = {42, 62, 110, 138, 180, 217, 246}
for o in (cam, tgt):
    for fc in A._fcurves(o.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if int(kp.co.x) in cuts else 'BEZIER'
# Kamera: der Reißschwenk (42→48) soll schnell und verwischt sein
for o in (cam, tgt):
    for fc in A._fcurves(o.animation_data.action):
        for kp in fc.keyframe_points:
            if int(kp.co.x) == 42:
                kp.interpolation = 'LINEAR'

if MODE == 'preview':
    A.render_frames(OUT, [20, 46, 85, 125, 150, 175, 200, 215, 222, 232, 260, 285])
else:
    A.render_frames(OUT)
print('FERTIG', OUT)
