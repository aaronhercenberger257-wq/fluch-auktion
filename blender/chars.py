"""Anime-Figuren für die 3D-Animationen (Version 2: „wie im Anime“).

Aufbau einer Figur:
  * Rig: echtes Armature (gleiche Knochennamen wie früher → alle Szenen laufen weiter)
  * Körper: Skelett-Graph + Skin-Modifier + Subdivision (Rumpf, Arme, Beine) – je Figur eigener Körperbau
  * Kleidung: geloftete Röhren (Jackensaum, Kimono, Ärmel, Hakama, Poncho …), Gewichte nach Knochen-Abstand
  * Hände: modellierte Hände mit fünf Fingern (Gelenke gekrümmt je Handhaltung), mehrere Varianten umschaltbar
  * Kopf: geformter Anime-Schädel (schmales Kinn, flache Gesichtsfläche, Nase, Ohren)
  * Gesicht: „Decals“ – 2D-Formen (Wimpernstrich, Iris mit Verlauf, Glanzlichter, Brauen, Mund, Tattoos, Nähte),
    die auf die Kopfoberfläche projiziert werden → saubere, scharfe Anime-Augen
  * Haare: Büschel aus abgeflachten, spitz zulaufenden Strähnen, pro Figur eigene Frisur
  * Tusche: alle Figurenteile liegen in der Sammlung „Ink“ → Freestyle zeichnet Umriss- und Faltenlinien (animelib.ink)
"""
import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

import animelib as A

# ───────────────────────── Skelett ─────────────────────────
# Knochen: name → (kopf, schwanz, eltern). Figur schaut nach −Y, Füße bei z=0, ca. 1,88 m groß.
BONES = {
    'root':    ((0, 0, 0), (0, 0, 0.2), None),
    'pelvis':  ((0, 0, 0.97), (0, 0, 1.13), 'root'),
    'spine':   ((0, 0, 1.13), (0, 0, 1.32), 'pelvis'),
    'chest':   ((0, 0, 1.32), (0, 0, 1.52), 'spine'),
    'neck':    ((0, 0, 1.52), (0, 0, 1.63), 'chest'),
    'head':    ((0, 0, 1.63), (0, 0, 1.93), 'neck'),
    'upper.L': ((0.2, 0.01, 1.47), (0.235, 0.025, 1.19), 'chest'),
    'fore.L':  ((0.235, 0.025, 1.19), (0.255, 0.0, 0.94), 'upper.L'),
    'hand.L':  ((0.255, 0.0, 0.94), (0.262, -0.005, 0.84), 'fore.L'),
    'upper.R': ((-0.2, 0.01, 1.47), (-0.235, 0.025, 1.19), 'chest'),
    'fore.R':  ((-0.235, 0.025, 1.19), (-0.255, 0.0, 0.94), 'upper.R'),
    'hand.R':  ((-0.255, 0.0, 0.94), (-0.262, -0.005, 0.84), 'fore.R'),
    'thigh.L': ((0.098, 0, 0.95), (0.102, 0.0, 0.52), 'pelvis'),
    'shin.L':  ((0.102, 0.0, 0.52), (0.104, 0.025, 0.09), 'thigh.L'),
    'foot.L':  ((0.104, 0.025, 0.09), (0.104, -0.15, 0.03), 'shin.L'),
    'thigh.R': ((-0.098, 0, 0.95), (-0.102, 0.0, 0.52), 'pelvis'),
    'shin.R':  ((-0.102, 0.0, 0.52), (-0.104, 0.025, 0.09), 'thigh.R'),
    'foot.R':  ((-0.104, 0.025, 0.09), (-0.104, -0.15, 0.03), 'shin.R'),
}
HEAD_C = Vector((0, 0, 1.765))      # Kopfmitte (Ruhepose)
HEAD_R = 0.122

# Skin-Graph: Punkt → (Position, (Radius quer, Radius tief))
SKIN_PTS = {
    'pelvis':  ((0, 0.005, 0.96), (0.145, 0.1)),
    'waist':   ((0, 0.0, 1.1), (0.122, 0.085)),
    'chest':   ((0, -0.005, 1.29), (0.158, 0.1)),
    'upchest': ((0, 0.0, 1.42), (0.17, 0.098)),
    'neck':    ((0, 0.012, 1.56), (0.05, 0.05)),
    'neckTop': ((0, 0.016, 1.68), (0.046, 0.046)),
    'sh.L':    ((0.2, 0.01, 1.455), (0.066, 0.066)),
    'el.L':    ((0.235, 0.025, 1.19), (0.046, 0.046)),
    'wr.L':    ((0.255, 0.0, 0.95), (0.031, 0.028)),
    'hi.L':    ((0.098, 0.0, 0.93), (0.088, 0.088)),
    'kn.L':    ((0.102, 0.0, 0.52), (0.058, 0.06)),
    'an.L':    ((0.104, 0.025, 0.1), (0.04, 0.04)),
    'to.L':    ((0.104, -0.13, 0.035), (0.042, 0.033)),
}
for _k in list(SKIN_PTS):
    if _k.endswith('.L'):
        (_x, _y, _z), _r = SKIN_PTS[_k]
        SKIN_PTS[_k[:-2] + '.R'] = ((-_x, _y, _z), _r)
SKIN_EDGES = [('pelvis', 'waist'), ('waist', 'chest'), ('chest', 'upchest'), ('upchest', 'neck'), ('neck', 'neckTop')]
for _s in ('L', 'R'):
    SKIN_EDGES += [('upchest', 'sh.' + _s), ('sh.' + _s, 'el.' + _s), ('el.' + _s, 'wr.' + _s),
                   ('pelvis', 'hi.' + _s), ('hi.' + _s, 'kn.' + _s), ('kn.' + _s, 'an.' + _s), ('an.' + _s, 'to.' + _s)]


# ───────────────────────── Grundlagen ─────────────────────────
def _link(obj):
    A.ink_collection().objects.link(obj)
    return obj


def _select_only(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _mesh_from_bm(name, bm, mats, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = _link(bpy.data.objects.new(name, me))
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    return o


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
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    return arm


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def skin_weights(obj, bones=None, power=4, bone_pts=None):
    """Gewichte nach Abstand zu den Knochen-Segmenten (die zwei nächsten, weich gemischt)."""
    bones = bones or [b for b in BONES if b != 'root']
    src = bone_pts or BONES
    segs = {b: (Vector(src[b][0]), Vector(src[b][1])) for b in bones}
    groups = {b: (obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b)) for b in bones}
    bpy.context.view_layer.update()
    mw = obj.matrix_world
    for v in obj.data.vertices:
        p = mw @ v.co
        ds = sorted(((_seg_dist(p, a, c), b) for b, (a, c) in segs.items()))
        if len(ds) == 1:
            groups[ds[0][1]].add([v.index], 1.0, 'REPLACE')
            continue
        (d0, b0), (d1, b1) = ds[0], ds[1]
        w0 = 1 / max(d0, 1e-4) ** power
        w1 = 1 / max(d1, 1e-4) ** power
        s = w0 + w1
        groups[b0].add([v.index], w0 / s, 'REPLACE')
        if w1 / s > 0.04:
            groups[b1].add([v.index], w1 / s, 'REPLACE')


def bind(obj, arm, bone=None, bones=None):
    """An das Rig hängen: starr an einen Knochen (bone) oder per Gewichtung (Armature-Modifier)."""
    if bone:
        bpy.context.view_layer.update()
        pb = arm.pose.bones[bone]
        world = obj.matrix_world.copy()
        obj.parent = arm
        obj.parent_type = 'BONE'
        obj.parent_bone = bone
        obj.matrix_parent_inverse = (arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))).inverted()
        obj.matrix_world = world
    else:
        if not obj.vertex_groups:
            skin_weights(obj, bones)
        obj.parent = arm
        mod = obj.modifiers.new('Rig', 'ARMATURE')
        mod.object = arm
        obj.modifiers.move(obj.modifiers.find('Rig'), 0)


def outline(obj, t):
    """Dünne Inverted-Hull-Linie (zusätzlich zu Freestyle → kräftigere Außenkontur)."""
    if t:
        A.add_outline(obj, t)


# ───────────────────────── Geometrie-Bausteine ─────────────────────────
def _cr(P, t):
    """Catmull-Rom-Punkt auf der Polylinie P bei t∈[0,1]."""
    n = len(P) - 1
    if n == 0:
        return P[0].copy()
    i = min(int(t * n), n - 1)
    u = t * n - i
    p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def sweep(name, pts, radii, mats, ring_n=16, rings=None, flat=1.0, up_hint=(0, 0, 1), cap0=True, cap1=True,
          shape=None, smooth=True, twist=0.0):
    """Röhre entlang einer Kurve. radii: Liste (gleich lang wie pts) von r oder (rx, ry), wird entlang interpoliert.
    shape(a, t) → Faktor für den Radius am Winkel a (für Falten, Abflachung …)."""
    P = [Vector(p) for p in pts]
    R = [(r, r) if isinstance(r, (int, float)) else tuple(r) for r in radii]
    rings = rings or max(6, len(P) * 4)
    centers = [_cr(P, i / rings) for i in range(rings + 1)]
    bm = bmesh.new()
    prev = None
    first = last = None
    hint = Vector(up_hint)
    for i, c in enumerate(centers):
        t = i / rings
        d = (centers[min(i + 1, rings)] - centers[max(i - 1, 0)]).normalized()
        side = d.cross(hint)
        if side.length < 1e-3:
            side = d.cross(Vector((1, 0, 0)))
        side.normalize()
        up = side.cross(d).normalized()
        k = t * (len(R) - 1)
        j = min(int(k), len(R) - 2) if len(R) > 1 else 0
        u = k - j
        if len(R) > 1:
            rx = R[j][0] * (1 - u) + R[j + 1][0] * u
            ry = R[j][1] * (1 - u) + R[j + 1][1] * u
        else:
            rx, ry = R[0]
        ring = []
        for q in range(ring_n):
            a = q / ring_n * math.tau + twist * t
            f = shape(a, t) if shape else 1.0
            ring.append(bm.verts.new(c + side * math.cos(a) * rx * f + up * math.sin(a) * ry * flat * f))
        if prev:
            for q in range(ring_n):
                bm.faces.new((prev[q], prev[(q + 1) % ring_n], ring[(q + 1) % ring_n], ring[q]))
        else:
            first = ring
        prev = ring
        last = ring
    if cap0:
        bm.faces.new(list(reversed(first)))
    if cap1:
        bm.faces.new(list(last))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mesh_from_bm(name, bm, mats, smooth)


def loft_z(name, rings, mats, n=32, cap0=False, cap1=False):
    """Kleidungsröhre um die Körperachse. rings: [(z, rx, ry, dy, shape_fn|None)], shape_fn(a) → Faktor."""
    bm = bmesh.new()
    prev = None
    first = last = None
    for z, rx, ry, dy, fn in rings:
        ring = []
        for q in range(n):
            a = q / n * math.tau
            f = fn(a) if fn else 1.0
            ring.append(bm.verts.new((math.cos(a) * rx * f, math.sin(a) * ry * f + dy, z)))
        if prev:
            for q in range(n):
                bm.faces.new((prev[q], prev[(q + 1) % n], ring[(q + 1) % n], ring[q]))
        else:
            first = ring
        prev = last = ring
    if cap0:
        bm.faces.new(list(reversed(first)))
    if cap1:
        bm.faces.new(list(last))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mesh_from_bm(name, bm, mats)


def ellipsoid(name, loc, size, mat, seg=24, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = _mesh_from_bm(name, bm, mat)
    o.location = loc
    o.rotation_euler = rot
    return o


# ───────────────────────── Decals (aufprojizierte 2D-Formen) ─────────────────────────
class Surface:
    """BVH einer oder mehrerer Oberflächen (Ruhepose, ohne Modifier) zum Aufprojizieren."""

    def __init__(self, objs):
        bpy.context.view_layer.update()
        verts, polys = [], []
        for o in objs:
            mw = o.matrix_world
            off = len(verts)
            verts += [mw @ v.co for v in o.data.vertices]
            polys += [[off + i for i in p.vertices] for p in o.data.polygons]
        self.bvh = BVHTree.FromPolygons(verts, polys)

    def project(self, p, d, offset):
        hit = self.bvh.ray_cast(p - d * 1.0, d, 3.0)
        if hit[0] is None:
            return None
        return hit[0] - d * offset


def decal(name, poly, mat, surf, plane=('x', 'z'), direction=(0, 1, 0), offset=0.0012, depth=0.0, sub=2,
          origin=(0, 0, 0)):
    """2D-Polygon (Liste von (u, v)) in der Ebene plane aufprojizieren. Rückgabe: Mesh-Objekt (oder None)."""
    if len(poly) < 3:
        return None
    ax = {'x': Vector((1, 0, 0)), 'y': Vector((0, 1, 0)), 'z': Vector((0, 0, 1)), '-x': Vector((-1, 0, 0)), '-y': Vector((0, -1, 0))}
    U, V = ax[plane[0]], ax[plane[1]]
    D = Vector(direction).normalized()
    O = Vector(origin)
    bm = bmesh.new()
    vs = [bm.verts.new(O + U * u + V * v + D * depth) for u, v in poly]
    try:
        f = bm.faces.new(vs)
    except ValueError:
        bm.free()
        return None
    bmesh.ops.triangulate(bm, faces=[f], quad_method='BEAUTY', ngon_method='BEAUTY')
    if sub:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=sub, use_grid_fill=True)
    keep = []
    for v in bm.verts:
        p = surf.project(v.co, D, offset)
        if p is None:
            keep.append(v)
        else:
            v.co = p
    if len(keep) > len(bm.verts) * 0.5:
        bm.free()
        return None
    bm.normal_update()
    o = _mesh_from_bm(name, bm, mat)
    o.visible_shadow = False
    A.no_ink(o)
    return o


def stroke_poly(pts, w0, w1=None, wmid=None, n=24, taper=(0.0, 0.0)):
    """Pinselstrich: Mittellinie pts (2D), Breite w0 → w1 (wmid optional), Enden spitz (taper=(Anteil Anfang, Ende))."""
    P = [Vector((p[0], p[1], 0)) for p in pts]
    w1 = w0 if w1 is None else w1
    C = [_cr(P, i / n) for i in range(n + 1)]
    left, right = [], []
    for i, c in enumerate(C):
        t = i / n
        d = (C[min(i + 1, n)] - C[max(i - 1, 0)])
        d = Vector((d.x, d.y, 0)).normalized()
        nrm = Vector((-d.y, d.x, 0))
        w = w0 + (w1 - w0) * t
        if wmid is not None:
            w = (w0 * (1 - t) + w1 * t) * 0.5 + wmid * math.sin(math.pi * t) * 0.5 + (w0 * (1 - t) + w1 * t) * 0.5 * (1 - math.sin(math.pi * t))
        if taper[0] and t < taper[0]:
            w *= (t / taper[0]) ** 0.7
        if taper[1] and t > 1 - taper[1]:
            w *= ((1 - t) / taper[1]) ** 0.7
        w = max(w, 0.00015)
        left.append(c + nrm * w * 0.5)
        right.append(c - nrm * w * 0.5)
    out = left + list(reversed(right))
    return [(p.x, p.y) for p in out]


def ellipse_poly(cx, cy, rx, ry, n=28, rot=0.0):
    out = []
    for i in range(n):
        a = i / n * math.tau
        x, y = math.cos(a) * rx, math.sin(a) * ry
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def clamp_poly(poly, lo, hi):
    """Polygonpunkte senkrecht zwischen zwei Kurven lo(u) ≤ v ≤ hi(u) einklemmen (Iris im Auge)."""
    return [(u, min(max(v, lo(u)), hi(u))) for u, v in poly]


# ───────────────────────── Körper ─────────────────────────
def body_mesh(prefix, cfg):
    """Skin-Modifier-Körper → angewendet → Materialien je Körperteil."""
    me = bpy.data.meshes.new(prefix + 'BodyMesh')
    bm = bmesh.new()
    idx = {}
    pts = dict(SKIN_PTS)
    for k, (dx, dy, dz) in cfg.get('ptOffset', {}).items():
        for kk in ([k] if k in pts else [k + '.L', k + '.R']):
            (x, y, z), r = pts[kk]
            sx = -1 if kk.endswith('.R') else 1
            pts[kk] = ((x + dx * sx, y + dy, z + dz), r)
    for k, (co, r) in pts.items():
        idx[k] = bm.verts.new(co)
    for a, b in SKIN_EDGES:
        bm.edges.new((idx[a], idx[b]))
    bm.to_mesh(me)
    bm.free()
    obj = _link(bpy.data.objects.new(prefix + 'Body', me))
    _select_only(obj)
    skin = obj.modifiers.new('Skin', 'SKIN')
    skin.use_smooth_shade = True
    radii = cfg.get('radii', {})
    for i, (k, (co, r)) in enumerate(pts.items()):
        sv = me.skin_vertices[0].data[i]
        f = radii.get(k, radii.get(k.split('.')[0], 1.0))
        if isinstance(f, (int, float)):
            f = (f, f)
        sv.radius = (r[0] * f[0], r[1] * f[1])
    me.skin_vertices[0].data[0].use_root = True
    sub = obj.modifiers.new('Sub', 'SUBSURF')
    sub.levels = 2
    sub.render_levels = 2
    bpy.ops.object.modifier_apply(modifier='Skin')
    bpy.ops.object.modifier_apply(modifier='Sub')
    bpy.ops.object.shade_smooth()
    # Materialien: 0 Oberteil, 1 Haut, 2 Schuhe, 3 Hose
    M = cfg['_mats']
    for m in (M['top'], M['skin'], M['shoe'], M['pants']):
        me.materials.append(m)
    bare_arms = cfg.get('bareArms', 0)        # 0 = Ärmel, sonst Höhe, ab der die Arme frei sind
    bare_torso = cfg.get('bareTorso', False)
    shoe_z = cfg.get('shoeZ', 0.14)
    pants_z = cfg.get('pantsZ', 0.93)
    for poly in me.polygons:
        c = poly.center
        if c.z > 1.585 and abs(c.x) < 0.09:
            poly.material_index = 1 if not cfg.get('neckCovered') else 0
        elif bare_arms and abs(c.x) > 0.17 and c.z < bare_arms and c.z > 0.9:
            poly.material_index = 1
        elif bare_torso and c.z > pants_z and abs(c.x) < 0.25:
            poly.material_index = 1
        elif c.z < shoe_z:
            poly.material_index = 2
        elif c.z < pants_z:
            poly.material_index = 3
    skin_weights(obj)
    return obj


# ───────────────────────── Hände ─────────────────────────
# Fingerhaltungen: Krümmung je Glied (Grad) + Spreizung (Grad). Reihenfolge: Zeige, Mittel, Ring, Klein
HAND_POSES = {
    'relaxed': dict(curl=[(12, 22, 12), (16, 26, 14), (20, 30, 16), (24, 34, 18)], spread=[-4, 0, 3, 7], thumb='side'),
    'fist':    dict(curl=[(88, 100, 60)] * 4, spread=[0, 0, 0, 0], thumb='wrap'),
    'point':   dict(curl=[(0, 0, 0), (88, 100, 60), (88, 100, 60), (88, 100, 60)], spread=[0, 0, 0, 0], thumb='wrap'),
    'two':     dict(curl=[(0, 0, 0), (0, 0, 0), (88, 100, 60), (88, 100, 60)], spread=[-4, 4, 0, 0], thumb='wrap'),
    'cross':   dict(curl=[(0, 0, 0), (0, 0, 0), (88, 100, 60), (88, 100, 60)], spread=[6, -12, 0, 0], thumb='wrap', cross=True),
    'open':    dict(curl=[(4, 4, 2)] * 4, spread=[-10, -3, 4, 12], thumb='open'),
    'claw':    dict(curl=[(18, 40, 35), (14, 42, 38), (18, 44, 38), (22, 46, 40)], spread=[-14, -4, 6, 16], thumb='open'),
    'flat':    dict(curl=[(0, 0, 0)] * 4, spread=[0, 0, 0, 0], thumb='flat'),
    'grip':    dict(curl=[(70, 80, 50)] * 4, spread=[0, 0, 0, 0], thumb='wrap'),
}
FINGERS = [  # (Knöchel-y, Längen der drei Glieder, Radius)
    (-0.026, (0.041, 0.025, 0.02), 0.0088),
    (-0.009, (0.046, 0.028, 0.022), 0.009),
    (0.008, (0.043, 0.026, 0.02), 0.0086),
    (0.024, (0.034, 0.021, 0.017), 0.0075),
]


def hand_mesh(name, side, kind, mat, nail=None, scale=1.0):
    """Modellierte Hand im Knochenraum: Handgelenk im Ursprung, Finger nach −Z, Handfläche zur Körpermitte."""
    P = HAND_POSES[kind]
    sx = 1 if side == 'R' else -1      # rechte Hand: Handfläche zeigt nach +X
    parts = []
    palm = ellipsoid(name + 'Palm', (0, 0, -0.048), (0.017, 0.042, 0.05), mat, seg=20)
    parts.append(palm)
    tips = []
    for fi, (ky, lens, r) in enumerate(FINGERS):
        curl = P['curl'][fi]
        spread = math.radians(P['spread'][fi])
        pts = [Vector((0.002 * sx, ky, -0.088 + abs(ky) * 0.25))]
        ang = 0.0
        p = pts[0]
        for gi, L in enumerate(lens):
            ang += math.radians(curl[gi])
            d = Vector((math.sin(ang) * sx, math.sin(spread) * math.cos(ang), -math.cos(ang) * math.cos(spread)))
            if P.get('cross') and fi == 1:
                d += Vector((0, -0.25, 0)) * (gi + 1) / 3
            p = p + d.normalized() * L
            pts.append(p)
        radii = [r * 1.05, r, r * 0.92, r * 0.8]
        parts.append(sweep(name + 'F%d' % fi, pts, radii, mat, ring_n=10, rings=10))
        tips.append((p, d))
    # Daumen
    th = P['thumb']
    base = Vector((0.012 * sx, -0.036, -0.03))
    if th == 'wrap':
        tp = [base, base + Vector((0.022 * sx, -0.022, -0.035)), base + Vector((0.034 * sx, -0.004, -0.06)), base + Vector((0.036 * sx, 0.016, -0.068))]
    elif th == 'open':
        tp = [base, base + Vector((0.006 * sx, -0.032, -0.028)), base + Vector((0.008 * sx, -0.052, -0.05)), base + Vector((0.01 * sx, -0.062, -0.07))]
    elif th == 'flat':
        tp = [base, base + Vector((0.004 * sx, -0.016, -0.034)), base + Vector((0.004 * sx, -0.022, -0.06)), base + Vector((0.004 * sx, -0.024, -0.082))]
    else:  # side
        tp = [base, base + Vector((0.012 * sx, -0.022, -0.03)), base + Vector((0.02 * sx, -0.03, -0.055)), base + Vector((0.026 * sx, -0.03, -0.075))]
    parts.append(sweep(name + 'Th', tp, [0.012, 0.011, 0.0095, 0.008], mat, ring_n=10, rings=10))
    tips.append((tp[-1], (tp[-1] - tp[-2]).normalized()))
    if nail:
        for i, (p, d) in enumerate(tips):
            parts.append(sweep(name + 'Nail%d' % i, [p - d * 0.006, p + d * 0.016, p + d * 0.03], [0.0065, 0.004, 0.0004], nail, ring_n=8, rings=6))
    # verbinden
    _select_only(parts[0])
    for o in parts[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    h = bpy.context.active_object
    h.name = name
    h.scale = (scale, scale, scale)
    return h


def add_hands(prefix, arm, cfg, kinds):
    """Hände in den gewünschten Haltungen bauen und an die Hand-Knochen hängen.
    kinds: {'R': ['relaxed', 'cross'], 'L': ['relaxed']} → Rückgabe {('R', 'cross'): obj, …}"""
    M = cfg['_mats']
    out = {}
    for side, lst in kinds.items():
        bone = BONES['hand.' + side]
        head, tail = Vector(bone[0]), Vector(bone[1])
        d = (tail - head).normalized()
        rot = Vector((0, 0, -1)).rotation_difference(d).to_matrix().to_4x4()
        for i, kind in enumerate(lst):
            h = hand_mesh(prefix + 'Hand%s_%s' % (side, kind), side, kind, M['hand'], nail=M.get('nail'), scale=cfg.get('handScale', 1.0))
            h.matrix_world = Matrix.Translation(head) @ rot @ h.matrix_world
            outline(h, 0.0025)
            bind(h, arm, 'hand.' + side)
            if i > 0:
                A.visible(h, 1, False)
            out[(side, kind)] = h
    return out


def hand_switch(fig, frame, side, kind):
    """Ab Bild 'frame' die Handhaltung 'kind' zeigen."""
    for (s, k), o in fig['hands'].items():
        if s == side:
            A.visible(o, frame, k == kind)


# ───────────────────────── Kopf & Gesicht ─────────────────────────
def head_mesh(prefix, cfg):
    """Anime-Schädel: runder Oberkopf, flaches Gesicht, schmale Wangen → spitzes Kinn, Hinterkopf voll."""
    R = HEAD_R
    jaw = cfg.get('jaw', 1.0)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=R)
    for v in bm.verts:
        x, y, z = v.co
        nz = z / R
        if nz < 0.05:
            t = (0.05 - nz) / 1.05            # 0 an den Wangenknochen … 1 am Kinn
            front = max(0.0, -y / R)          # vorne stärker verjüngen
            w = 1 - (0.5 * jaw) * t ** 1.25 * (0.55 + 0.45 * front)
            x *= w
            y = y * (1 - 0.18 * t) - 0.018 * t * front
            z = 0.05 * R + (z - 0.05 * R) * 1.32
        if y > 0:
            y *= 1.06                          # Hinterkopf
        if y < -0.55 * R:                      # flache Gesichtsfläche
            y = -0.55 * R + (y + 0.55 * R) * 0.55
        x *= 0.93
        v.co = Vector((x, y, z))
    o = _mesh_from_bm(prefix + 'Head', bm, cfg['_mats']['skin'])
    o.location = HEAD_C
    # Nase: kleiner Keil
    nb = bmesh.new()
    tip = Vector((0, -R * 0.87, -0.032))
    for p in [(-0.009, -R * 0.73, -0.036), (0.009, -R * 0.73, -0.036), (0, -R * 0.72, 0.002)]:
        nb.verts.new(p)
    nb.verts.new(tip)
    vs = list(nb.verts)
    for tri in ((0, 1, 3), (1, 2, 3), (2, 0, 3), (0, 2, 1)):
        nb.faces.new([vs[i] for i in tri])
    bmesh.ops.recalc_face_normals(nb, faces=nb.faces)
    nose = _mesh_from_bm(prefix + 'Nose', nb, cfg['_mats']['skin'], smooth=False)
    nose.location = HEAD_C
    # Ohren
    ears = []
    for sx in (-1, 1):
        e = ellipsoid(prefix + 'Ear%d' % sx, HEAD_C + Vector((sx * R * 0.9, 0.012, -0.008)), (0.012, 0.022, 0.032), cfg['_mats']['skin'], seg=14,
                      rot=(0.15, 0, -sx * 0.25))
        ears.append(e)
    return o, [nose] + ears


def face(prefix, cfg, head):
    """Augen, Brauen, Mund, Male – als Decals auf dem Kopf."""
    surf = Surface([head])
    E = cfg.get('eye', {})
    M = cfg['_mats']
    hz = HEAD_C.z
    parts = []
    lash = A.flat(prefix + 'LashM', E.get('lash', '#17121a'))
    sclera = A.flat(prefix + 'ScleraM', '#fbfbff')
    iris_dark = A.flat(prefix + 'IrisDark', E.get('irisDark', '#1a2236'))
    iris = A.glow(prefix + 'Iris', E.get('iris', '#4fd2ff'), cfg.get('eyeGlow', 1.6))
    iris_lo = A.glow(prefix + 'IrisLo', E.get('irisLo', '#d8f6ff'), cfg.get('eyeGlow', 1.6) * 0.9)
    pupil = A.flat(prefix + 'Pupil', E.get('pupil', '#0a0d16'))
    shine = A.glow(prefix + 'Shine', '#ffffff', 3)
    brow = A.flat(prefix + 'BrowM', cfg.get('browColor', cfg.get('hair', '#222222')))
    skin_line = A.flat(prefix + 'SkinLine', cfg.get('skinLine', '#b07a6a'))
    ew = E.get('w', 0.032)                 # halbe Augenbreite
    eh = E.get('h', 0.0135)                # Augenhöhe (Öffnung)
    slant = E.get('slant', 0.004)          # Außenwinkel höher (scharfer Blick)
    ey = E.get('z', -0.004)
    ex = E.get('x', 0.046)
    for sx in (-1, 1):
        cx = ex * sx

        def U(u, sx=sx, cx=cx):     # Oberlid (Höhe über u)
            t = (u - cx) / ew * sx  # −1 innen … +1 außen
            t = max(-1.0, min(1.0, t))
            return hz + ey + eh * (1 - t * t) ** 0.6 * 0.9 + slant * t - 0.002

        def L(u, sx=sx, cx=cx):     # Unterlid
            t = (u - cx) / ew * sx
            t = max(-1.0, min(1.0, t))
            return hz + ey - eh * 0.55 * (1 - t * t) ** 0.8 + slant * 0.4 * t
        n = 26
        us = [cx + sx * ew * (-1 + 2 * i / n) for i in range(n + 1)]
        if not cfg.get('closedEyes'):
            scl = [(u, U(u)) for u in us] + [(u, L(u)) for u in reversed(us)]
            parts.append(decal(prefix + 'Sclera%d' % sx, scl, sclera, surf, offset=0.0008))
            ir_x = cx + sx * E.get('look', 0.0)
            irx, irz = E.get('irisW', 0.0115), E.get('irisH', 0.0145)
            izc = hz + ey + E.get('irisZ', 0.0015)
            parts.append(decal(prefix + 'IrisD%d' % sx, clamp_poly(ellipse_poly(ir_x, izc, irx, irz), L, U), iris_dark, surf, offset=0.0011))
            parts.append(decal(prefix + 'IrisC%d' % sx, clamp_poly(ellipse_poly(ir_x, izc - 0.0008, irx * 0.82, irz * 0.82), L, U), iris, surf, offset=0.0014))
            parts.append(decal(prefix + 'IrisL%d' % sx, clamp_poly(ellipse_poly(ir_x, izc - irz * 0.45, irx * 0.62, irz * 0.38), L, U), iris_lo, surf, offset=0.0017))
            if E.get('pupil', True) is not False:
                parts.append(decal(prefix + 'Pupil%d' % sx, clamp_poly(ellipse_poly(ir_x, izc + 0.001, irx * 0.36, irz * 0.42), L, U), pupil, surf, offset=0.002))
            parts.append(decal(prefix + 'Shine%d' % sx, ellipse_poly(ir_x - 0.004 * sx, izc + irz * 0.45, 0.0028, 0.0024), shine, surf, offset=0.0024))
            parts.append(decal(prefix + 'Shine2%d' % sx, ellipse_poly(ir_x + 0.004 * sx, izc - irz * 0.35, 0.0013, 0.0013), shine, surf, offset=0.0024))
        # Wimpernstrich oben (dick, außen mit Haken)
        top = [(u, U(u) + 0.0012) for u in us]
        top.append((cx + sx * (ew + 0.004), U(cx + sx * ew) - 0.003))
        if cfg.get('closedEyes'):
            top = [(u, (U(u) + L(u)) / 2) for u in us]
        parts.append(decal(prefix + 'Lash%d' % sx, stroke_poly(top, E.get('lashW', 0.0042) * 0.6, E.get('lashW', 0.0042) * 1.25,
                                                              taper=(0.15, 0.05)), lash, surf, offset=0.0026))
        # Unterlid (dünn, nur außen)
        lo = [(u, L(u) - 0.0006) for u in us[n // 3:]]
        parts.append(decal(prefix + 'LowLid%d' % sx, stroke_poly(lo, 0.0006, 0.0014, taper=(0.4, 0.1)), lash, surf, offset=0.0026))
        # Lidfalte
        if E.get('crease', True):
            cr = [(u, U(u) + 0.0055 + 0.001 * abs((u - cx) / ew)) for u in us[n // 4: n - 2]]
            parts.append(decal(prefix + 'Crease%d' % sx, stroke_poly(cr, 0.0005, 0.0009, taper=(0.3, 0.3)), skin_line, surf, offset=0.0016))
        # Braue
        bz = hz + ey + cfg.get('browZ', 0.026)
        ang = cfg.get('browAngle', 0.12)   # >0: innen tiefer (grimmig)
        bp = [(cx - sx * ew * 0.95, bz - ang * 0.03), (cx, bz + 0.002), (cx + sx * ew * 1.05, bz + ang * 0.02 + 0.001)]
        parts.append(decal(prefix + 'Brow%d' % sx, stroke_poly(bp, cfg.get('browW', 0.0042), 0.0012, taper=(0.05, 0.4)), brow, surf, offset=0.0016))
    # Mund
    mz = hz + cfg.get('mouthZ', -0.068)
    mt = cfg.get('mouth', 'line')
    mouth_c = A.flat(prefix + 'MouthLine', '#3a1c1c')
    if mt == 'line':
        parts.append(decal(prefix + 'Mouth', stroke_poly([(-0.014, mz + 0.0005), (0, mz), (0.012, mz + 0.0012)], 0.0013, 0.0008, taper=(0.3, 0.3)), mouth_c, surf, offset=0.0016))
    elif mt in ('grin', 'smile'):
        wide = 0.03 if mt == 'grin' else 0.022
        up = 0.009 if mt == 'grin' else 0.006
        inner = A.flat(prefix + 'MouthIn', '#4a1418')
        teeth = A.flat(prefix + 'Teeth', '#fbf8f2')
        n = 16
        top_c = [(-wide + 2 * wide * i / n, mz + up * abs(-1 + 2 * i / n) ** 1.6 + 0.001) for i in range(n + 1)]
        bot_c = [(-wide * 0.8 + 1.6 * wide * i / n, mz - (0.012 if mt == 'grin' else 0.007) * (1 - abs(-1 + 2 * i / n) ** 2)) for i in range(n + 1)]
        parts.append(decal(prefix + 'MouthO', top_c + list(reversed(bot_c)), inner, surf, offset=0.0012))
        if mt == 'grin':
            tb = [(u, v - 0.0042) for u, v in top_c]
            parts.append(decal(prefix + 'TeethU', top_c + list(reversed(tb)), teeth, surf, offset=0.0015))
            bb = [(u * 0.92, v + 0.003) for u, v in bot_c]
            parts.append(decal(prefix + 'TeethD', bb + list(reversed(bot_c)), teeth, surf, offset=0.0015))
        parts.append(decal(prefix + 'MouthL', stroke_poly(top_c, 0.0012, 0.0012, taper=(0.1, 0.1)), mouth_c, surf, offset=0.0019))
    # Nasen-Schatten (kleiner Strich)
    parts.append(decal(prefix + 'NoseLine', stroke_poly([(0.003, hz - 0.03), (0.0055, hz - 0.036), (0.002, hz - 0.04)], 0.0011, 0.0008), skin_line, surf, offset=0.0035))
    # Zeichen (Sukuna), Nähte (Mahito)
    mk = A.flat(prefix + 'MarkM', cfg.get('markColor', '#1a1416'))
    for i, st in enumerate(cfg.get('marks', [])):
        parts.append(decal(prefix + 'Mark%d' % i, stroke_poly(st['pts'], st.get('w', 0.003), st.get('w1', st.get('w', 0.003)), taper=st.get('taper', (0.1, 0.3))),
                           mk, surf, offset=0.0013))
    for i, st in enumerate(cfg.get('stitches', [])):
        parts.append(decal(prefix + 'StL%d' % i, stroke_poly(st, 0.0011, 0.0011), mk, surf, offset=0.0014))
        P = [Vector((p[0], p[1], 0)) for p in st]
        for k in range(1, 12):
            c = _cr(P, k / 12)
            d = (_cr(P, min(1, k / 12 + 0.02)) - _cr(P, max(0, k / 12 - 0.02))).normalized()
            nrm = Vector((-d.y, d.x, 0)) * 0.0055
            parts.append(decal(prefix + 'St%d_%d' % (i, k), stroke_poly([(c - nrm)[:2], (c + nrm)[:2]], 0.001, 0.001), mk, surf, offset=0.0016, sub=1))
    return [p for p in parts if p]


# ───────────────────────── Haare ─────────────────────────
def clump(name, root, tip, width, mat, bend=(0, 0, 0), flat=0.42, thick_base=1.0, ring_n=10, twist=0.0, up_hint=None):
    """Haarbüschel: breite, flache Basis → spitze Spitze, leicht gebogen."""
    root, tip = Vector(root), Vector(tip)
    mid = root * 0.55 + tip * 0.45 + Vector(bend)
    mid2 = root * 0.2 + tip * 0.8 + Vector(bend) * 0.6
    pts = [root, mid, mid2, tip]
    radii = [(width, width * thick_base), (width * 0.72, width * 0.7), (width * 0.3, width * 0.3), (0.0004, 0.0004)]
    hint = up_hint or (root - HEAD_C).normalized()
    return sweep(name, pts, radii, mat, ring_n=ring_n, rings=12, flat=flat, up_hint=hint, cap1=False, twist=twist)


def scalp(az, el, r=None):
    """Punkt auf der Kopfhaut: az 0 = vorne (−Y), positiv = links (+X); el 0 = Äquator, 90° = Scheitel."""
    r = r or HEAD_R * 1.02
    a, e = math.radians(az), math.radians(el)
    return HEAD_C + Vector((math.sin(a) * math.cos(e) * r, -math.cos(a) * math.cos(e) * r, math.sin(e) * r + 0.008))


def hair(prefix, cfg):
    M = cfg['_mats']
    mat = M['hair']
    style = cfg.get('hairStyle', 'spiky')
    rnd = random.Random(sum(map(ord, prefix)) + len(style))
    parts = []
    if style in ('none', 'volcano', 'octo'):
        return parts
    # Haarkappe: etwas größer als der Schädel, Gesicht frei
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=HEAD_R * 1.05)
    cut_front = cfg.get('capFront', 0.25)
    rm = []
    for v in bm.verts:
        x, y, z = v.co
        if z < -HEAD_R * 0.25 and y < HEAD_R * 0.3:
            rm.append(v)
        elif y < -HEAD_R * 0.5 and z < HEAD_R * cut_front:
            rm.append(v)
        elif z < HEAD_R * cfg.get('capLow', -0.62):
            rm.append(v)
    bmesh.ops.delete(bm, geom=rm, context='VERTS')
    for v in bm.verts:
        v.co.y *= 1.08
        if v.co.y > 0:
            v.co.y *= 1.04
    cap = _mesh_from_bm(prefix + 'HairCap', bm, mat)
    cap.location = HEAD_C + Vector((0, 0.006, 0.004))
    sol = cap.modifiers.new('Thick', 'SOLIDIFY')
    sol.thickness = 0.008
    parts.append(cap)

    def add(root, tip, w, bend=(0, 0, 0), flat=0.42, twist=0.0):
        parts.append(clump(prefix + 'Cl%d' % len(parts), root, tip, w, mat, bend=bend, flat=flat, twist=twist))

    def spikes(rings, up, back, out_w, front_cut=None, bend_up=0.03, flat=0.62, sink=0.9, jitter=10, lens=(0.85, 1.2)):
        """Stachel-Frisur: rings = [(Höhe°, Anzahl, Länge, Breite)], Richtung = außen·out_w + oben·up + hinten·back."""
        for ring, (el, n, L, w) in enumerate(rings):
            n = int(round(n * 1.15))
            w = w * 0.78
            for i in range(n):
                az = i / n * 360 + rnd.uniform(-jitter, jitter) + ring * 13
                if front_cut and math.cos(math.radians(az)) > front_cut[0] and el < front_cut[1]:
                    continue
                root = scalp(az, el, HEAD_R * sink)
                out = (root - HEAD_C).normalized()
                d = (out * out_w + Vector((0, back, up))).normalized()
                tip = root + d * L * rnd.uniform(*lens) + out * 0.02
                add(root, tip, w * rnd.uniform(0.85, 1.15), bend=out * 0.025 + Vector((0, 0, bend_up)), flat=flat, twist=rnd.uniform(-0.7, 0.7))

    def bangs(xs, length, w, fwd=0.045, spread=0.6):
        for k, x in enumerate(xs):
            root = HEAD_C + Vector((x * 0.85, -HEAD_R * 0.62, HEAD_R * 0.86))
            ln = length * (1.0 - 0.25 * abs(x) / 0.09) * rnd.uniform(0.9, 1.1)
            add(root, root + Vector((x * spread, -fwd, -ln)), w * 0.75, bend=(0, -fwd * 0.6, 0.015), flat=0.55)

    vol = {'gojo': ((0, 0.01, 0.075), (1.22, 1.22, 1.05)), 'megumi': ((0, 0.025, 0.07), (1.22, 1.2, 0.95)), 'sukuna': ((0, 0.02, 0.06), (0.95, 1.05, 0.85)),
           'gojo_down': ((0, 0.01, 0.05), (1.12, 1.15, 0.95))}.get(style)
    if vol:
        vb = ellipsoid(prefix + 'HairVol', HEAD_C + Vector(vol[0]), tuple(HEAD_R * k for k in vol[1]), mat, seg=24)
        vbm = bmesh.new()
        vbm.from_mesh(vb.data)
        sz = Vector(vol[1]) * HEAD_R
        bmesh.ops.delete(vbm, geom=[v for v in vbm.verts if (v.co.y < -0.3 * sz.y and v.co.z + vol[0][2] < HEAD_R * 0.42) or v.co.z + vol[0][2] < -HEAD_R * 0.3], context='VERTS')
        vbm.to_mesh(vb.data)
        vbm.free()
        parts.append(vb)
    if style == 'gojo':
        # Gojo mit Augenbinde (Vorlage): weiße Haare stehen in vielen Spitzen nach oben, leicht nach hinten
        spikes([(84, 7, 0.17, 0.026), (66, 14, 0.19, 0.028), (48, 18, 0.19, 0.028), (30, 20, 0.16, 0.026), (12, 18, 0.12, 0.024)],
               up=0.85, back=0.15, out_w=0.9, bend_up=0.035)
        for x in (-0.07, -0.035, 0.0, 0.035, 0.07):   # Stirn: Strähnen über der Binde nach oben
            root = HEAD_C + Vector((x, -HEAD_R * 0.8, HEAD_R * 0.45))
            add(root, root + Vector((x * 1.2, -0.05, 0.12)), 0.02, bend=(0, -0.03, 0.0), flat=0.6)
    elif style == 'gojo_down':
        spikes([(80, 8, 0.15, 0.032), (58, 14, 0.16, 0.034), (36, 16, 0.14, 0.032)], up=0.35, back=0.1, out_w=1.0, front_cut=(0.5, 60))
        bangs((-0.07, -0.04, -0.01, 0.02, 0.05, 0.075), 0.12, 0.024)
    elif style == 'sukuna':
        # Sukuna (Vorlage): kurze rosa Stacheln nach oben/hinten gekämmt, dunkler Undercut an den Seiten
        spikes([(84, 5, 0.085, 0.03), (66, 11, 0.095, 0.032), (50, 13, 0.09, 0.03), (36, 12, 0.07, 0.028)],
               up=0.7, back=0.9, out_w=0.55, bend_up=0.02, sink=0.92)
        for x in (-0.05, -0.017, 0.017, 0.05):          # vorne hochgestellt
            root = HEAD_C + Vector((x, -HEAD_R * 0.72, HEAD_R * 0.62))
            add(root, root + Vector((x * 0.6, 0.01, 0.1)), 0.02, bend=(0, -0.025, 0), flat=0.6)
        under = A.toon(prefix + 'Undercut', cfg.get('undercut', '#2a1a20'), shade='#120a0d')
        ub = bmesh.new()
        bmesh.ops.create_uvsphere(ub, u_segments=32, v_segments=20, radius=HEAD_R * 1.01)
        bmesh.ops.delete(ub, geom=[v for v in ub.verts if v.co.y < -HEAD_R * 0.35 or v.co.z < -HEAD_R * 0.45 or v.co.z > HEAD_R * 0.5], context='VERTS')
        uc = _mesh_from_bm(prefix + 'UnderC', ub, under)
        uc.location = HEAD_C + Vector((0, 0.008, 0.0))
        parts.append(uc)
    elif style == 'megumi':
        # Megumi: schwarze Stacheln in alle Richtungen (Seeigel), vorne Strähnen in die Stirn
        spikes([(86, 7, 0.16, 0.026), (68, 14, 0.18, 0.028), (50, 18, 0.18, 0.028), (32, 20, 0.17, 0.026), (12, 18, 0.13, 0.024)],
               up=0.3, back=0.12, out_w=1.0, front_cut=(0.62, 40), bend_up=0.04)
        bangs((-0.075, -0.045, -0.015, 0.015, 0.045, 0.075), 0.11, 0.024, spread=0.9)
    elif style == 'mahito':
        # Mahito (Vorlage): lang, glatt, Mittelscheitel, Zopf vorne über der (eigenen) rechten Schulter
        for side in (-1, 1):
            for k in range(12):
                az = side * (8 + k * 13)
                root = scalp(az, 64 - k * 2.5, HEAD_R * 0.95)
                out = (root - HEAD_C).normalized()
                back = 0.02 + k * 0.012
                ex = side * (0.135 + 0.004 * k)
                if side < 0 and k < 6:      # rechte Seite (Figur) → nach vorn zum Zopf
                    end = HEAD_C + Vector((-0.13, -0.045, -0.3))
                else:
                    end = HEAD_C + Vector((ex * 1.08, back + 0.03, -0.3 - rnd.uniform(0, 0.08)))
                pts = [root, root + out * 0.025 + Vector((0, 0, 0.005)), HEAD_C + Vector((ex, back - 0.01, -0.06)), (HEAD_C + Vector((ex, back, -0.06))).lerp(end, 0.5), end]
                parts.append(sweep(prefix + 'Long%d_%d' % (side, k), pts, [(0.026, 0.026), (0.03, 0.026), (0.03, 0.024), (0.024, 0.02), (0.004, 0.004)], mat,
                                   ring_n=10, rings=16, flat=0.5, up_hint=out, cap1=False))
        pt = [HEAD_C + Vector((-0.13, -0.045, -0.28)), HEAD_C + Vector((-0.14, -0.07, -0.4)), HEAD_C + Vector((-0.145, -0.08, -0.56)),
              HEAD_C + Vector((-0.13, -0.075, -0.72))]
        parts.append(sweep(prefix + 'Tail', pt, [0.036, 0.04, 0.03, 0.004], mat, ring_n=12, rings=14, cap1=False))
        band = A.toon(prefix + 'Band', '#1b1d26')
        parts.append(sweep(prefix + 'TailBand', [pt[0] + Vector((0, 0, 0.015)), pt[0] + Vector((-0.003, -0.006, -0.04))], [0.043, 0.043], band, ring_n=12, rings=4))
        bangs((-0.06, -0.025, 0.03, 0.065), 0.14, 0.022, fwd=0.035, spread=1.0)
    elif style == 'bob':
        # Nobara: kurzer, glatter Bob bis zum Kinn, gerader Pony
        for k in range(26):
            az = -165 + k * (330 / 25)
            if abs(az) < 38:
                continue
            root = scalp(az, 58, HEAD_R * 0.96)
            out = (root - HEAD_C).normalized()
            side = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0))
            mid = HEAD_C + side * (HEAD_R * 1.12) + Vector((0, 0, 0.0))
            end = HEAD_C + side * (HEAD_R * 1.08) + Vector((0, 0.0, -0.11))
            tip = HEAD_C + side * (HEAD_R * 0.98) + Vector((0, 0, -0.125))
            parts.append(sweep(prefix + 'Bob%d' % k, [root, mid, end, tip], [(0.032, 0.032), (0.034, 0.03), (0.03, 0.026), (0.006, 0.006)], mat,
                               ring_n=10, rings=14, flat=0.5, up_hint=out, cap1=False))
        for x in (-0.07, -0.042, -0.014, 0.014, 0.042, 0.07):
            root = HEAD_C + Vector((x * 0.85, -HEAD_R * 0.6, HEAD_R * 0.88))
            add(root, root + Vector((x * 0.25, -0.05, -0.085)), 0.018, bend=(0, -0.025, 0.012), flat=0.55)
    elif style == 'messy':
        for i in range(36):
            az = i / 36 * 360
            el = rnd.uniform(10, 80)
            root = scalp(az, el)
            out = (root - HEAD_C).normalized()
            if math.cos(math.radians(az)) > 0.6 and el < 50:
                continue
            add(root, root + (out + Vector((0, 0, 0.35))).normalized() * rnd.uniform(0.11, 0.16), 0.04, bend=Vector((0, 0, 0.02)))
        for x in (-0.06, -0.02, 0.025, 0.065):
            root = HEAD_C + Vector((x * 0.8, -HEAD_R * 0.7, HEAD_R * 0.78))
            add(root, root + Vector((x * 0.6, -0.045, -0.1)), 0.026, bend=(0, -0.02, 0.02))
    elif style == 'slick':
        for i in range(18):
            x = -0.1 + i * 0.012
            root = HEAD_C + Vector((x, -HEAD_R * 0.8, HEAD_R * 0.62))
            add(root, HEAD_C + Vector((x * 1.1, HEAD_R * 1.2, HEAD_R * 0.1)), 0.03, bend=(0, 0, 0.06), flat=0.35)
    elif style == 'pompadour':
        for i in range(12):
            x = -0.07 + i * 0.013
            root = HEAD_C + Vector((x, -HEAD_R * 0.6, HEAD_R * 0.85))
            add(root, root + Vector((0, -0.07, 0.07)), 0.035, bend=(0, -0.02, 0.05))
        for i in range(14):
            az = 100 + i / 14 * 160
            root = scalp(az, 40)
            add(root, root + (root - HEAD_C).normalized() * 0.05 + Vector((0, 0.04, 0.0)), 0.04)
    elif style == 'undercut':
        for i in range(16):
            x = -0.09 + i * 0.012
            root = HEAD_C + Vector((x, -HEAD_R * 0.7, HEAD_R * 0.7))
            add(root, HEAD_C + Vector((x * 1.1, HEAD_R * 1.15, HEAD_R * 0.3)), 0.034, bend=(0, 0, 0.06))
        for sx in (-1, 1):
            root = HEAD_C + Vector((sx * 0.05, -HEAD_R * 0.75, HEAD_R * 0.7))
            add(root, root + Vector((sx * 0.03, -0.03, -0.15)), 0.022, bend=(0, -0.02, 0))
    return parts


# ───────────────────────── Figur zusammensetzen ─────────────────────────
def materials(prefix, cfg):
    M = {}
    M['top'] = A.toon(prefix + 'Coat', cfg['coat'], shade=cfg.get('coatShade'), highlight=cfg.get('coatHi'), steps=cfg.get('coatSteps', (0.4, 0.9)))
    M['pants'] = A.toon(prefix + 'Pants', cfg.get('pants', cfg['coat']), shade=cfg.get('pantsShade', cfg.get('coatShade')),
                        highlight=cfg.get('pantsHi', cfg.get('coatHi')), steps=cfg.get('coatSteps', (0.4, 0.9)))
    M['skin'] = A.toon(prefix + 'Skin', cfg.get('skin', '#f9e2d2'), shade=cfg.get('skinShade', '#e2b4a2'), highlight=cfg.get('skinHi', cfg.get('skin', '#f9e2d2')),
                       steps=cfg.get('skinSteps', (0.14, 0.99)))
    M['hand'] = M['skin']
    M['shoe'] = A.toon(prefix + 'Shoe', cfg.get('shoe', '#121216'), shade=cfg.get('shoeShade'), highlight=cfg.get('shoeHi', '#3a3a48'))
    M['hair'] = A.toon(prefix + 'Hair', cfg['hair'], shade=cfg.get('hairShade'), highlight=cfg.get('hairHi'), steps=(0.42, 0.88))
    M['trim'] = A.toon(prefix + 'Trim', cfg.get('trim', '#2b2b33'), shade=cfg.get('trimShade'))
    if cfg.get('nails'):
        M['nail'] = A.toon(prefix + 'Nail', cfg['nails'])
    cfg['_mats'] = M
    return M


def build(prefix, cfg, loc=(0, 0, 0), facing=0.0):
    """Komplette Figur bauen. Rückgabe: {'arm', 'body', 'head', 'parts', 'hands', 'cfg'}"""
    materials(prefix, cfg)
    arm = make_armature(prefix)
    parts = []
    body = body_mesh(prefix, cfg)
    outline(body, cfg.get('outline', 0.004))
    bind(body, arm)
    parts.append(body)
    # Kopf
    head_parts = []
    if cfg.get('headBuilder'):
        head_parts += cfg['headBuilder'](prefix, cfg)
    else:
        h, extras = head_mesh(prefix, cfg)
        outline(h, 0.003)
        head_parts += [h] + extras
        head_parts += face(prefix, cfg, h)
        for hp in hair(prefix, cfg):
            outline(hp, 0.0022)
            head_parts.append(hp)
    for o in head_parts:
        bind(o, arm, 'head')
    # Kleidung & Extras (eigene Bauteile je Figur)
    for fn in cfg.get('builders', []):
        for o, how in fn(prefix, cfg, arm) or []:
            if isinstance(how, str):
                bind(o, arm, how)
            elif how is None:
                pass
            else:
                bind(o, arm, bones=how)
            parts.append(o)
    hands = add_hands(prefix, arm, cfg, cfg.get('hands', {'R': ['relaxed'], 'L': ['relaxed']}))
    arm.location = loc
    arm.rotation_euler = (0, 0, facing)
    return {'arm': arm, 'body': body, 'head': head_parts, 'parts': parts, 'hands': hands, 'cfg': cfg, 'extra': []}


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


def fingers(prefix, arm, side, kind, skin_hex='#f6dccb'):
    """Kompatibilität: Handhaltungen werden jetzt über cfg['hands'] gebaut."""
    return []


def strand(name, pts, r0, mat, flat=0.55, segs=10):
    """Kompatibilität (Szenen-Deko): spitz zulaufende Röhre ohne Freestyle-Linien, mit dünnem Umriss."""
    o = sweep(name, pts, [r0, r0 * 0.6, 0.001] if len(pts) == 3 else [r0 * (1 - i / max(1, len(pts) - 1)) + 0.001 for i in range(len(pts))],
              mat, ring_n=8, rings=12, flat=flat, cap1=False)
    A.no_ink(o)
    A.add_outline(o, 0.004)
    return o
