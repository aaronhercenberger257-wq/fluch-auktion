"""Anime-Figuren für die Domain-Animationen.

Modelliert statt zusammengesteckt:
  * Körper: Skelett-Graph + Skin-Modifier + Subdivision → ein durchgehender, organischer Körper
  * Rig: echtes Armature, Gewichte automatisch nach Nähe zu den Knochen (weiche Gelenke)
  * Kopf: verformte Kugel mit Anime-Kinn, große Augen (Sklera, Iris, Pupille, Glanzlicht), Brauen, Mund
  * Haare: gebogene, spitz zulaufende Strähnen (eigene Röhren-Meshes), pro Figur eigene Frisur
  * Kleidung: Mantel-/Kimono-Saum, Kragen, Gürtel, Krawatte, Fell usw. als eigene Teile
Alles in Cel-Shading mit schwarzen Umrissen (animelib).
"""
import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

import animelib as A

# ───────────────────────── Skelett ─────────────────────────
# Knochen: name → (kopf, schwanz, eltern). Figur schaut nach −Y, Füße bei z=0, ca. 1,85 m groß.
BONES = {
    'root':    ((0, 0, 0), (0, 0, 0.2), None),
    'pelvis':  ((0, 0, 0.95), (0, 0, 1.12), 'root'),
    'spine':   ((0, 0, 1.12), (0, 0, 1.32), 'pelvis'),
    'chest':   ((0, 0, 1.32), (0, 0, 1.52), 'spine'),
    'neck':    ((0, 0, 1.52), (0, 0, 1.62), 'chest'),
    'head':    ((0, 0, 1.62), (0, 0, 1.92), 'neck'),
    'upper.L': ((0.19, 0, 1.47), (0.23, 0.02, 1.18), 'chest'),
    'fore.L':  ((0.23, 0.02, 1.18), (0.26, 0.0, 0.92), 'upper.L'),
    'hand.L':  ((0.26, 0.0, 0.92), (0.27, -0.01, 0.8), 'fore.L'),
    'upper.R': ((-0.19, 0, 1.47), (-0.23, 0.02, 1.18), 'chest'),
    'fore.R':  ((-0.23, 0.02, 1.18), (-0.26, 0.0, 0.92), 'upper.R'),
    'hand.R':  ((-0.26, 0.0, 0.92), (-0.27, -0.01, 0.8), 'fore.R'),
    'thigh.L': ((0.095, 0, 0.93), (0.1, 0.0, 0.5), 'pelvis'),
    'shin.L':  ((0.1, 0.0, 0.5), (0.1, 0.02, 0.09), 'thigh.L'),
    'foot.L':  ((0.1, 0.02, 0.09), (0.1, -0.14, 0.03), 'shin.L'),
    'thigh.R': ((-0.095, 0, 0.93), (-0.1, 0.0, 0.5), 'pelvis'),
    'shin.R':  ((-0.1, 0.0, 0.5), (-0.1, 0.02, 0.09), 'thigh.R'),
    'foot.R':  ((-0.1, 0.02, 0.09), (-0.1, -0.14, 0.03), 'shin.R'),
}

# Skin-Graph des Körpers: Punkte mit Radius (x, y) – Schultern breit, Taille schmal (Anime-Proportionen)
SKIN_PTS = {
    'pelvis': ((0, 0, 0.95), (0.15, 0.1)),
    'waist':  ((0, 0, 1.1), (0.125, 0.085)),
    'chest':  ((0, 0, 1.32), (0.165, 0.105)),
    'upchest': ((0, 0, 1.45), (0.17, 0.1)),
    'neck':   ((0, 0, 1.58), (0.052, 0.05)),
    'neckTop': ((0, 0, 1.66), (0.048, 0.046)),
    'sh.L':   ((0.19, 0, 1.47), (0.072, 0.07)),
    'el.L':   ((0.23, 0.02, 1.18), (0.052, 0.05)),
    'wr.L':   ((0.26, 0.0, 0.93), (0.038, 0.034)),
    'ha.L':   ((0.27, -0.01, 0.84), (0.044, 0.026)),
    'hi.L':   ((0.095, 0, 0.92), (0.09, 0.09)),
    'kn.L':   ((0.1, 0.0, 0.5), (0.066, 0.066)),
    'an.L':   ((0.1, 0.02, 0.1), (0.048, 0.048)),
    'to.L':   ((0.1, -0.12, 0.035), (0.045, 0.035)),
}
for k in list(SKIN_PTS):
    if k.endswith('.L'):
        (x, y, z), r = SKIN_PTS[k]
        SKIN_PTS[k[:-2] + '.R'] = ((-x, y, z), r)
SKIN_EDGES = [('pelvis', 'waist'), ('waist', 'chest'), ('chest', 'upchest'), ('upchest', 'neck'), ('neck', 'neckTop')]
for s in ('L', 'R'):
    SKIN_EDGES += [('upchest', 'sh.' + s), ('sh.' + s, 'el.' + s), ('el.' + s, 'wr.' + s), ('wr.' + s, 'ha.' + s),
                   ('pelvis', 'hi.' + s), ('hi.' + s, 'kn.' + s), ('kn.' + s, 'an.' + s), ('an.' + s, 'to.' + s)]


def _link(obj):
    bpy.context.collection.objects.link(obj)
    return obj


def _select_only(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def make_armature(prefix):
    arm_data = bpy.data.armatures.new(prefix + 'Rig')
    arm = _link(bpy.data.objects.new(prefix + 'Rig', arm_data))
    _select_only(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    for name, (h, t, par) in BONES.items():
        b = eb.new(name)
        b.head, b.tail = Vector(h), Vector(t)
    for name, (h, t, par) in BONES.items():
        if par:
            eb[name].parent = eb[par]
            eb[name].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.show_in_front = False
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    return arm


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def skin_weights(obj, bones=None):
    """Gewichte nach Abstand zu den Knochen-Segmenten (die zwei nächsten, weich gemischt)."""
    bones = bones or [b for b in BONES if b != 'root']
    segs = {b: (Vector(BONES[b][0]), Vector(BONES[b][1])) for b in bones}
    groups = {b: obj.vertex_groups.new(name=b) for b in bones}
    for v in obj.data.vertices:
        p = v.co
        ds = sorted(((_seg_dist(p, a, c), b) for b, (a, c) in segs.items()))
        (d0, b0), (d1, b1) = ds[0], ds[1]
        w0 = 1 / max(d0, 1e-4) ** 4
        w1 = 1 / max(d1, 1e-4) ** 4
        s = w0 + w1
        groups[b0].add([v.index], w0 / s, 'REPLACE')
        if w1 / s > 0.05:
            groups[b1].add([v.index], w1 / s, 'REPLACE')


def bind(obj, arm, bone=None):
    """An das Rig hängen: ganz an einen Knochen (bone) oder per Gewichtung (Armature-Modifier)."""
    if bone:
        # Bone-Parenting: Ursprung ist das Knochenende → Ruhepose-Matrix herausrechnen,
        # damit das Teil genau dort bleibt, wo es modelliert wurde.
        bpy.context.view_layer.update()
        pb = arm.pose.bones[bone]
        world = obj.matrix_world.copy()
        obj.parent = arm
        obj.parent_type = 'BONE'
        obj.parent_bone = bone
        obj.matrix_parent_inverse = (arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))).inverted()
        obj.matrix_world = world
    else:
        obj.parent = arm
        mod = obj.modifiers.new('Rig', 'ARMATURE')
        mod.object = arm
        obj.modifiers.move(obj.modifiers.find('Rig'), 0)  # Rig vor dem Umriss auswerten


def body_mesh(prefix, cfg):
    """Skin-Modifier-Körper → angewendet → Materialien je Körperteil."""
    me = bpy.data.meshes.new(prefix + 'BodyMesh')
    bm = bmesh.new()
    idx = {}
    for k, (co, r) in SKIN_PTS.items():
        idx[k] = bm.verts.new(co)
    for a, b in SKIN_EDGES:
        bm.edges.new((idx[a], idx[b]))
    bm.to_mesh(me)
    bm.free()
    obj = _link(bpy.data.objects.new(prefix + 'Body', me))
    _select_only(obj)
    skin = obj.modifiers.new('Skin', 'SKIN')
    skin.use_smooth_shade = True
    for i, (k, (co, r)) in enumerate(SKIN_PTS.items()):
        sv = me.skin_vertices[0].data[i]
        sv.radius = r
    me.skin_vertices[0].data[0].use_root = True
    sub = obj.modifiers.new('Sub', 'SUBSURF')
    sub.levels = 2
    sub.render_levels = 2
    bpy.ops.object.modifier_apply(modifier='Skin')
    bpy.ops.object.modifier_apply(modifier='Sub')
    bpy.ops.object.shade_smooth()
    # Materialien: Kleidung, Haut (Hände/Hals), Schuhe
    mats = [A.toon(prefix + 'Coat', cfg['coat'], shade=cfg.get('coatShade')),
            A.toon(prefix + 'Skin', cfg.get('skin', '#f6dccb'), shade=cfg.get('skinShade', '#d5a48f')),
            A.toon(prefix + 'Shoe', cfg.get('shoe', '#121212')),
            A.toon(prefix + 'Pants', cfg.get('pants', cfg['coat']), shade=cfg.get('coatShade'))]
    for m in mats:
        me.materials.append(m)
    for poly in me.polygons:
        c = poly.center
        if c.z > 1.6 and abs(c.x) < 0.08:
            poly.material_index = 1          # Hals
        elif abs(c.x) > 0.24 and c.z < 0.95 and c.z > 0.75:
            poly.material_index = 1          # Hände
        elif c.z < 0.14:
            poly.material_index = 2          # Schuhe
        elif c.z < 0.9 and cfg.get('pants'):
            poly.material_index = 3
    skin_weights(obj)
    return obj


def head_mesh(prefix, cfg):
    """Anime-Kopf: Kugel, unten zu einem spitzen Kinn geformt, hinten etwas flacher."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=0.135)
    for v in bm.verts:
        x, y, z = v.co
        if z < 0:
            t = -z / 0.135
            v.co.x = x * (1 - 0.42 * t ** 1.4)
            v.co.y = y * (1 - 0.25 * t) - 0.02 * t  # Kinn leicht nach vorn
            v.co.z = z * 1.18
        if y > 0:
            v.co.y = y * 0.92                       # Hinterkopf flacher
        v.co.z += 0.0
    me = bpy.data.meshes.new(prefix + 'HeadMesh')
    bm.to_mesh(me)
    bm.free()
    obj = _link(bpy.data.objects.new(prefix + 'Head', me))
    obj.location = (0, 0, 1.76)
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(A.toon(prefix + 'Skin', cfg.get('skin', '#f6dccb'), shade=cfg.get('skinShade', '#d5a48f')))
    A.add_outline(obj, 0.007)
    return obj


def _disc(name, center, sx, sz, mat, depth=0.004, rot_z=0.0):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = _link(bpy.data.objects.new(name, me))
    o.location = center
    o.rotation_euler = (math.pi / 2, 0, rot_z)
    o.scale = (sx, sz, 1)
    me.materials.append(mat)
    return o


def face(prefix, cfg, head_obj):
    """Große Anime-Augen, Brauen, Mund – als flache Teile auf der Gesichtsfläche."""
    parts = []
    eye_c = cfg.get('eyes', '#5ec8ff')
    sclera = A.toon(prefix + 'Sclera', '#ffffff', shade='#dfe6f0')
    iris = A.glow(prefix + 'Iris', eye_c, cfg.get('eyeGlow', 2.0))
    pupil = A.toon(prefix + 'Pupil', '#0b1020')
    shine = A.glow(prefix + 'Shine', '#ffffff', 4)
    lash = A.toon(prefix + 'Lash', cfg.get('lash', '#151018'))
    brow = A.toon(prefix + 'Brow', cfg.get('browColor', cfg['hair']), shade=cfg.get('hairShade'))
    hz = 1.76
    for sx in (-1, 1):
        x = 0.05 * sx
        y = -0.128
        z = hz + 0.005
        parts.append(_disc(prefix + 'Sclera%d' % sx, (x, y, z), 0.034, 0.024, sclera, rot_z=0.18 * sx))
        if not cfg.get('closedEyes'):
            parts.append(_disc(prefix + 'Iris%d' % sx, (x * 0.98, y - 0.002, z - 0.002), 0.019, 0.022, iris))
            parts.append(_disc(prefix + 'Pupil%d' % sx, (x * 0.98, y - 0.003, z - 0.002), 0.008, 0.011, pupil))
            parts.append(_disc(prefix + 'Shine%d' % sx, (x * 0.98 - 0.007, y - 0.004, z + 0.007), 0.005, 0.005, shine))
        # Oberes Lid (dicker Anime-Strich)
        lid = A.cube(prefix + 'Lid%d' % sx, (x, y - 0.004, z + 0.021), (0.036, 0.003, 0.0026), lash, rot=(0, -0.2 * sx, 0))
        parts.append(lid)
        # Braue
        b = A.cube(prefix + 'Brow%d' % sx, (x * 1.05, y + 0.004, z + 0.047), (0.028, 0.004, 0.0038), brow, rot=(0, (0.22 if cfg.get('angryBrows', True) else -0.1) * sx, 0))
        parts.append(b)
        if cfg.get('marks'):
            parts.append(A.cube(prefix + 'Mark%d' % sx, (x * 1.25, y + 0.01, z - 0.03), (0.022, 0.003, 0.0035), lash, rot=(0, 0.35 * sx, 0)))
            parts.append(A.cube(prefix + 'Mark2%d' % sx, (x * 1.0, y + 0.004, z - 0.045), (0.02, 0.003, 0.003), lash, rot=(0, -0.25 * sx, 0)))
    mouth = A.toon(prefix + 'MouthC', '#6e2b2b')
    parts.append(A.cube(prefix + 'Mouth', (0, -0.118, hz - 0.075), (0.016, 0.003, 0.0025), mouth))
    nose = A.toon(prefix + 'NoseC', cfg.get('skinShade', '#d5a48f'))
    parts.append(A.cube(prefix + 'Nose', (0, -0.136, hz - 0.035), (0.003, 0.003, 0.006), nose))
    if cfg.get('stitches'):
        st = A.toon(prefix + 'Stitch', '#2a3240')
        parts.append(A.cube(prefix + 'StitchL', (0.0, -0.13, hz + 0.01), (0.06, 0.002, 0.0016), st, rot=(0, 0.6, 0)))
        for i in range(5):
            parts.append(A.cube(prefix + 'St%d' % i, (-0.035 + i * 0.017, -0.131, hz + 0.03 - i * 0.011), (0.0014, 0.002, 0.007), st))
    return parts


def strand(name, pts, r0, mat, flat=0.55, segs=10):
    """Haarsträhne: Röhre entlang einer Catmull-Rom-Kurve, Radius läuft spitz zu, Querschnitt abgeflacht."""
    P = [Vector(p) for p in pts]

    def cr(t):
        n = len(P) - 1
        i = min(int(t * n), n - 1)
        u = t * n - i
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n)]
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

    rings = 12
    ring_n = 8
    bm = bmesh.new()
    prev = None
    centers = [cr(i / rings) for i in range(rings + 1)]
    for i, c in enumerate(centers):
        t = i / rings
        d = (centers[min(i + 1, rings)] - centers[max(i - 1, 0)]).normalized()
        side = d.cross(Vector((0, 0, 1)))
        if side.length < 1e-3:
            side = d.cross(Vector((1, 0, 0)))
        side.normalize()
        up = side.cross(d).normalized()
        r = r0 * (1 - t) ** 0.9 + 0.0008
        ring = []
        for k in range(ring_n):
            a = k / ring_n * math.tau
            ring.append(bm.verts.new(c + side * math.cos(a) * r + up * math.sin(a) * r * flat))
        if prev:
            for k in range(ring_n):
                bm.faces.new((prev[k], prev[(k + 1) % ring_n], ring[(k + 1) % ring_n], ring[k]))
        else:
            bm.faces.new(list(reversed(ring)))
        prev = ring
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = _link(bpy.data.objects.new(name, me))
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    A.add_outline(o, 0.004)
    return o


def hair(prefix, cfg):
    """Frisuren als Sammlung von Strähnen. Kopfmitte bei (0,0,1.76)."""
    mat = A.toon(prefix + 'Hair', cfg['hair'], shade=cfg.get('hairShade'), highlight=cfg.get('hairHi'))
    style = cfg.get('hairStyle', 'spiky')
    rnd = random.Random(sum(map(ord, prefix)))
    H = Vector((0, 0, 1.76))
    parts = []
    # Haarkappe (etwas größer als der Kopf, nur oben)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.146)
    for v in list(bm.verts):
        if v.co.z < -0.02 and v.co.y < 0.06:
            v.co.z = -0.02 + (v.co.z + 0.02) * 0.1
        if v.co.y < -0.08 and v.co.z < 0.05:
            v.co.y = -0.08
    me = bpy.data.meshes.new(prefix + 'CapMesh')
    bm.to_mesh(me)
    bm.free()
    cap = _link(bpy.data.objects.new(prefix + 'HairCap', me))
    cap.location = H + Vector((0, 0.012, 0.02))
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    if style not in ('volcano', 'octo'):
        A.add_outline(cap, 0.005)
        parts.append(cap)
    else:
        bpy.data.objects.remove(cap)

    def add(pts, r):
        parts.append(strand(prefix + 'Str%d' % len(parts), [H + Vector(p) for p in pts], r, mat))

    if style == 'spiky':          # Gojo: weiße, nach oben/außen stehende Stacheln
        for i in range(30):
            a = i / 30 * math.tau + rnd.uniform(-0.1, 0.1)
            el = rnd.uniform(0.35, 1.1)
            base = Vector((math.cos(a) * 0.12, math.sin(a) * 0.12 + 0.01, 0.06 + el * 0.04))
            out = Vector((math.cos(a) * math.cos(el) * 0.26, math.sin(a) * math.cos(el) * 0.26, math.sin(el) * 0.28 + 0.08))
            mid = base * 0.5 + out * 0.5 + Vector((0, 0, 0.04))
            add([base, mid, out], rnd.uniform(0.04, 0.055))
        for x in (-0.085, -0.03, 0.03, 0.085):   # Pony (kurz, Augen frei)
            add([(x, -0.1, 0.11), (x * 1.3, -0.15, 0.06), (x * 1.6, -0.15, 0.03)], 0.03)
    elif style == 'sukuna':       # kurz, nach hinten stachelig, abrasierte Seiten
        for i in range(18):
            a = math.pi * 0.25 + i / 18 * math.pi * 1.5
            base = Vector((math.cos(a) * 0.1, math.sin(a) * 0.1 + 0.03, 0.11))
            out = Vector((math.cos(a) * 0.17, math.sin(a) * 0.17 + 0.12, 0.2 + rnd.uniform(0, 0.05)))
            add([base, (base + out) / 2 + Vector((0, 0, 0.03)), out], 0.045)
        for x in (-0.05, 0.0, 0.05):
            add([(x, -0.08, 0.13), (x, -0.1, 0.2), (x * 1.6, -0.02, 0.27)], 0.035)
    elif style == 'messy':        # Megumi/Yuta: wild, nach außen
        for i in range(34):
            a = i / 34 * math.tau
            el = rnd.uniform(-0.2, 0.9)
            if math.sin(a) < -0.35:          # vorne: Strähnen nach oben, Gesicht frei
                el = max(el, 0.6)
            base = Vector((math.cos(a) * 0.12, math.sin(a) * 0.12 + 0.01, 0.05 + el * 0.05))
            out = Vector((math.cos(a) * 0.24 * rnd.uniform(0.8, 1.2), math.sin(a) * 0.24 + 0.03, 0.06 + el * 0.2))
            add([base, (base + out) / 2 + Vector((0, 0, 0.05)), out], rnd.uniform(0.035, 0.05))
        for x in (-0.08, -0.025, 0.03, 0.085):
            add([(x, -0.11, 0.11), (x * 1.25, -0.155, 0.06), (x * 1.5, -0.15, 0.035)], 0.026)
    elif style == 'long':         # Mahito: lang, über die Schultern, in der Mitte gescheitelt
        for i in range(26):
            a = math.pi * 0.05 + i / 26 * math.pi * 0.9
            for sx in (-1, 1):
                base = Vector((sx * math.sin(a) * 0.13, math.cos(a) * 0.06 + 0.02, 0.12 - abs(math.cos(a)) * 0.02))
                down = Vector((sx * (0.16 + rnd.uniform(0, 0.04)), 0.05 + rnd.uniform(-0.04, 0.06), -0.38 - rnd.uniform(0, 0.12)))
                add([base, base + Vector((sx * 0.06, 0, -0.08)), down], 0.04)
    elif style == 'slick':        # Higuruma: nach hinten gekämmt
        for i in range(16):
            x = -0.11 + i * 0.015
            add([(x, -0.12, 0.07), (x * 1.05, -0.03, 0.15), (x * 0.9, 0.12, 0.06)], 0.028)
    elif style == 'pompadour':    # Hakari: hohe Tolle, Seiten kurz
        for i in range(12):
            x = -0.07 + i * 0.013
            add([(x, -0.06, 0.13), (x, -0.13, 0.21), (x * 0.8, -0.06, 0.25)], 0.03)
    elif style == 'undercut':     # Naoya: blond, nach hinten, Strähnen vorne
        for i in range(14):
            x = -0.09 + i * 0.014
            add([(x, -0.1, 0.1), (x, 0.0, 0.18), (x, 0.13, 0.1)], 0.04)
        for x in (-0.06, 0.06):
            add([(x, -0.12, 0.08), (x * 1.3, -0.15, 0.0), (x * 1.4, -0.14, -0.07)], 0.025)
    return parts


def volcano_head(prefix, cfg):
    """Jogo: vulkanförmiger Kopf mit Krater und Rauch."""
    rock = A.toon(prefix + 'Rock', '#d8cfc2', shade='#8f8578')
    o = A.cone(prefix + 'Volc', (0, 0, 1.8), 0.16, 0.3, rock, r2=0.07, verts=24, outline=0.006)
    lava = A.glow(prefix + 'Lava', '#ff7a1a', 6)
    k = A.cylinder(prefix + 'Crater', (0, 0, 1.955), 0.06, 0.012, lava, outline=0)
    return [o, k]


def octo_head(prefix, cfg):
    """Dagon: großer Oktopus-Kopf mit Tentakeln."""
    red = A.toon(prefix + 'Octo', '#d83a3a', shade='#7a1414')
    parts = [A.sphere(prefix + 'Dome', (0, 0.02, 1.88), (0.2, 0.18, 0.22), red, outline=0.007)]
    for i in range(6):
        a = math.pi * 1.1 + i / 5 * math.pi * 0.8
        x, y = math.cos(a) * 0.1, math.sin(a) * 0.08
        parts.append(strand(prefix + 'Tent%d' % i, [(x, y - 0.02, 1.72), (x * 1.3, y - 0.05, 1.6), (x * 1.6, y - 0.02, 1.48)], 0.035, red, flat=1.0))
    return parts


def clothing(prefix, cfg):
    """Zusätzliche Kleidungsteile je nach Outfit."""
    coat = A.toon(prefix + 'Coat', cfg['coat'], shade=cfg.get('coatShade'))
    trim = A.toon(prefix + 'Trim', cfg.get('trim', '#2b4a8a'))
    parts = []
    outfit = cfg.get('outfit', 'uniform')
    # Mantel-/Kimonosaum: weiter Kegel von der Taille bis zu den Knien
    if outfit in ('uniform', 'robe', 'kimono'):
        low = 0.52 if outfit == 'uniform' else 0.18
        parts.append(A.cylinder(prefix + 'Hem', (0, 0.0, (1.05 + low) / 2), 0.2, 1.05 - low, coat, r2=0.25 if outfit != 'uniform' else 0.22, verts=32, outline=0.008))
        parts[-1].scale = (1.0, 0.85, 1.0)
        parts[-1].rotation_euler = (math.pi, 0, 0)
    if outfit == 'uniform':       # hoher Kragen + Knopfleiste
        parts.append(A.cylinder(prefix + 'Collar', (0, 0, 1.6), 0.075, 0.14, coat, r2=0.085, verts=24, outline=0.006))
        for i in range(4):
            parts.append(A.sphere(prefix + 'Btn%d' % i, (0, -0.108, 1.42 - i * 0.13), 0.011, A.toon(prefix + 'Gold', '#d6b44a'), segments=10, outline=0))
    if outfit in ('kimono', 'robe'):
        parts.append(A.cylinder(prefix + 'Belt', (0, 0, 1.08), 0.135, 0.07, trim, verts=24, outline=0.006))
        parts[-1].scale = (1.0, 0.75, 1)
        # V-Ausschnitt-Kragen
        for sx in (-1, 1):
            parts.append(A.cube(prefix + 'Lapel%d' % sx, (0.04 * sx, -0.1, 1.38), (0.015, 0.008, 0.16), trim, rot=(0, 0.35 * sx, 0), outline=0.004))
    if outfit == 'suit':
        parts.append(A.cube(prefix + 'Shirt', (0, -0.1, 1.42), (0.04, 0.01, 0.1), A.toon(prefix + 'ShirtC', '#f1f1f1'), outline=0.004))
        parts.append(A.cube(prefix + 'Tie', (0, -0.112, 1.36), (0.016, 0.006, 0.12), trim, outline=0.004))
        parts.append(A.sphere(prefix + 'Badge', (0.08, -0.105, 1.42), (0.018, 0.005, 0.018), A.glow(prefix + 'Gold', '#ffd24a', 3), outline=0))
    if cfg.get('fur'):
        for i in range(14):
            a = i / 14 * math.tau
            parts.append(A.sphere(prefix + 'Fur%d' % i, (math.cos(a) * 0.12, math.sin(a) * 0.09, 1.55), 0.045, A.toon(prefix + 'FurC', '#ece6dc', shade='#b6aa98'), segments=12, outline=0.004))
    if cfg.get('scarf'):
        parts.append(A.cylinder(prefix + 'Scarf', (0, 0, 1.58), 0.09, 0.08, A.toon(prefix + 'ScarfC', cfg['scarf']), verts=24, outline=0.006))
    return parts


def build(prefix, cfg, loc=(0, 0, 0), facing=0.0):
    """Komplette Figur bauen. Rückgabe: {'arm', 'body', 'head', 'parts', 'cfg'}"""
    arm = make_armature(prefix)
    body = body_mesh(prefix, cfg)
    A.add_outline(body, 0.009)
    bind(body, arm)
    # Kopf & alles am Kopf → am Kopf-Knochen
    head_parts = []
    style = cfg.get('hairStyle')
    if style == 'volcano':
        head_parts += volcano_head(prefix, cfg)
        eye = A.glow(prefix + 'Iris', cfg.get('eyes', '#ff7a1a'), 4)
        head_parts.append(_disc(prefix + 'Cyclops', (0, -0.142, 1.76), 0.032, 0.032, eye))
    elif style == 'octo':
        head_parts += octo_head(prefix, cfg)
        eye = A.glow(prefix + 'Iris', cfg.get('eyes', '#fde68a'), 3)
        for sx in (-1, 1):
            head_parts.append(_disc(prefix + 'OEye%d' % sx, (0.07 * sx, -0.19, 1.9), 0.025, 0.02, eye))
    else:
        h = head_mesh(prefix, cfg)
        head_parts.append(h)
        head_parts += face(prefix, cfg, h)
        head_parts += hair(prefix, cfg)
        # Ohren
        sk = A.toon(prefix + 'Skin', cfg.get('skin', '#f6dccb'))
        for sx in (-1, 1):
            head_parts.append(A.sphere(prefix + 'Ear%d' % sx, (0.13 * sx, 0.0, 1.75), (0.018, 0.012, 0.03), sk, segments=12, outline=0.004))
    for o in head_parts:
        bind(o, arm, 'head')
    # Kleidung am Oberkörper/Becken
    for o in clothing(prefix, cfg):
        bone = 'pelvis' if o.location.z < 1.15 else 'chest' if o.location.z < 1.55 else 'neck'
        bind(o, arm, bone)
    # Extras (z. B. Finger für Handzeichen) → an die Hände
    extra = []
    if cfg.get('extra'):
        extra = cfg['extra'](prefix, arm) or []
    arm.location = loc
    arm.rotation_euler = (0, 0, facing)
    return {'arm': arm, 'body': body, 'head': head_parts, 'cfg': cfg, 'extra': extra}


# ───────────────────────── Posen ─────────────────────────
def pose(fig, frame, **rots):
    """pose(fig, 10, **{'upper.R': (x, y, z), 'head': (...)}) – Euler in Grad."""
    arm = fig['arm']
    for b, r in rots.items():
        pb = arm.pose.bones[b]
        pb.rotation_euler = tuple(math.radians(v) for v in r)
        pb.keyframe_insert('rotation_euler', frame=frame)


def move(fig, frame, bone, loc):
    pb = fig['arm'].pose.bones[bone]
    pb.location = loc
    pb.keyframe_insert('location', frame=frame)


def idle(fig, f0, f1, seed=0):
    """Leichtes Atmen + Arme locker (Anime-Grundhaltung)."""
    r = random.Random(seed)
    for f in range(f0, f1 + 1, 24):
        ph = r.uniform(0, 1)
        pose(fig, f, chest=(2 + ph, 0, 0), **{'upper.L': (0, -8, 6), 'upper.R': (0, 8, -6), 'fore.L': (8, 0, 0), 'fore.R': (8, 0, 0)})


def place(fig, frame, loc, facing=None):
    a = fig['arm']
    a.location = loc
    a.keyframe_insert('location', frame=frame)
    if facing is not None:
        a.rotation_euler = (0, 0, facing)
        a.keyframe_insert('rotation_euler', frame=frame)


# Hand-Teile: Finger für Zeichen (an den Hand-Knochen gebunden)
def fingers(prefix, arm, side, kind, skin_hex='#f6dccb'):
    sk = A.toon(prefix + 'Skin', skin_hex, shade='#d5a48f')
    bx = 0.27 if side == 'L' else -0.27
    parts = []
    base = Vector((bx, -0.01, 0.8))
    if kind == 'cross':     # Zeige- und Mittelfinger überkreuzt (Gojo)
        parts.append(A.cylinder(prefix + 'FgA' + side, base + Vector((0.006, -0.012, -0.04)), 0.009, 0.075, sk, rot=(0, 0.3, 0), outline=0.003))
        parts.append(A.cylinder(prefix + 'FgB' + side, base + Vector((-0.006, -0.02, -0.04)), 0.009, 0.075, sk, rot=(0, -0.3, 0), outline=0.003))
    elif kind == 'two':      # zwei Finger nach oben
        for dx in (-0.01, 0.01):
            parts.append(A.cylinder(prefix + 'Fg%s%.2f' % (side, dx), base + Vector((dx, -0.015, -0.045)), 0.009, 0.08, sk, outline=0.003))
    elif kind == 'point':
        parts.append(A.cylinder(prefix + 'FgP' + side, base + Vector((0, -0.015, -0.05)), 0.009, 0.09, sk, outline=0.003))
    for p in parts:
        bind(p, arm, 'hand.' + side)
    return parts
