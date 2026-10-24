"""Besetzung: Aussehen aller Domain-Besitzer, Megumi, Mahoraga und des Gegners.

Nach den Vorlagen des Nutzers (nur als Referenz nachmodelliert, keine Bilder übernommen):
  Gojo     – weiße, nach oben stehende Haare, schwarze Augenbinde, hochgeschlossene schwarze Uniform mit violetten Glanzlichtern
  Sukuna   – rosa Stachelhaare mit dunklem Undercut, Gesichtszeichen, weißer Kimono mit riesigen Ärmeln, dunkler Schal,
             gemusterter Obi, lange schwarze Krallen, Tabi + Zori
  Jogo     – Vulkankopf mit einem Auge, Pelzkragen, gelber Umhang mit schwarzen Flecken, weite dunkle Hose, Stiefel mit roter Sohle
  Mahito   – lange graublaue Haare mit Zopf, Nähte im Gesicht, schwarzer Patchwork-Umhang, nackte Arme mit Nähten, weiße Schuhe
  Megumi   – schwarze Stachelhaare, dunkle Uniform
  Mahoraga – riesig, muskulös, weiß; Kopf mit vier Flügeln und Grinsen, Rad mit acht Griffen, Halskette, Schärpe,
             dunkelgrüner Hakama, Armreifen, bandagierter rechter Unterarm, Schwert der Auslöschung
"""
import bpy
import bmesh
import math
import random
from mathutils import Vector

import animelib as A
import chars as C

HZ = C.HEAD_C.z
V = Vector

LEGS = ['pelvis', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R']
TORSO = ['pelvis', 'spine', 'chest', 'neck', 'upper.L', 'upper.R']


def ink(o):
    C.to_ink(o) if hasattr(C, 'to_ink') else A.to_ink(o)
    return o


def body_surface(prefix):
    return C.Surface([bpy.data.objects[prefix + 'Body']])


def front_decals(prefix, items, surf, mat, direction=(0, 1, 0), plane=('x', 'z'), offset=0.0015):
    """Mehrere Pinselstriche aufs Gewand projizieren (gewichtet an den Körper)."""
    out = []
    for i, it in enumerate(items):
        pts, w0, w1 = it[0], it[1], it[2] if len(it) > 2 else it[1]
        o = C.decal(prefix + 'Fold%d_%d' % (len(bpy.data.objects), i), C.stroke_poly(pts, w0, w1, taper=(0.3, 0.4)), mat, surf,
                    plane=plane, direction=direction, offset=offset, sub=2)
        if o:
            out.append((o, TORSO + LEGS + ['fore.L', 'fore.R']))
    return out


# ═════════════════════════ Kleidungsteile ═════════════════════════
def high_collar(prefix, cfg, arm, top=1.71, color=None):
    mat = cfg['_mats']['top'] if not color else A.toon(prefix + 'CollarM', color)
    rings = [(1.5, 0.11, 0.085, 0.01, None), (1.56, 0.075, 0.07, 0.012, None), (top - 0.02, 0.074, 0.072, 0.016, None),
             (top, 0.078, 0.076, 0.018, None)]
    o = C.loft_z(prefix + 'Collar', rings, mat, n=32)
    sol = o.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.006
    C.outline(o, 0.003)
    return [(o, ['chest', 'neck'])]


def jacket_skirt(prefix, cfg, arm, low=0.8, flare=1.0):
    """Saum der Uniformjacke von der Taille bis über die Oberschenkel."""
    mat = cfg['_mats']['top']
    rings = [(1.12, 0.128, 0.09, 0.0, None), (1.0, 0.152, 0.106, 0.004, None), (0.9, 0.16 * flare, 0.112, 0.006, None),
             (low, 0.166 * flare, 0.118, 0.008, None)]
    o = C.loft_z(prefix + 'JacketSkirt', rings, mat, n=36)
    sol = o.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.006
    C.outline(o, 0.003)
    return [(o, ['spine', 'pelvis', 'thigh.L', 'thigh.R'])]


def seam(prefix, cfg, arm, color='#05060a', z0=1.66, z1=0.8, w=0.0028):
    surf = C.Surface([o for o in bpy.data.objects if o.name in (prefix + 'Body', prefix + 'JacketSkirt', prefix + 'Collar')])
    m = A.flat(prefix + 'SeamM', color)
    o = C.decal(prefix + 'Seam', C.stroke_poly([(0, z0), (0.002, (z0 + z1) / 2), (0, z1)], w, w), m, surf, sub=3)
    return [(o, TORSO + LEGS)] if o else []


def fold_lines(prefix, cfg, arm, color, items):
    surf = C.Surface([o for o in bpy.data.objects if o.name.startswith(prefix) and o.name.split(prefix)[1] in ('Body', 'JacketSkirt', 'Robe', 'Poncho')])
    return front_decals(prefix, items, surf, A.flat(prefix + 'FoldM', color))


def kimono_robe(prefix, cfg, arm, low=0.06, color=None):
    mat = cfg['_mats']['top']

    def wav(a):
        return 1.0 + 0.04 * math.sin(a * 7)
    rings = [(1.18, 0.13, 0.092, 0.0, None), (1.05, 0.158, 0.11, 0.0, None), (0.8, 0.19, 0.13, 0.01, wav), (0.45, 0.205, 0.14, 0.015, wav),
             (low, 0.225, 0.155, 0.02, wav)]
    o = C.loft_z(prefix + 'Robe', rings, mat, n=40)
    sol = o.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.008
    C.outline(o, 0.003)
    return [(o, ['spine', 'pelvis', 'thigh.L', 'thigh.R'])]


def wide_sleeves(prefix, cfg, arm, end_r=0.16, length=0.08):
    mat = cfg['_mats']['top']
    out = []
    for s, sx in (('L', 1), ('R', -1)):
        sh = V(C.BONES['upper.' + s][0])
        el = V(C.BONES['fore.' + s][0])
        wr = V(C.BONES['hand.' + s][0])
        d = (wr - el).normalized()
        end = wr + d * length + V((sx * 0.03, 0.02, 0))
        pts = [sh + V((-sx * 0.02, 0, 0.02)), (sh + el) / 2, el, (el + end) / 2, end]
        o = C.sweep(prefix + 'Sleeve' + s, pts, [(0.075, 0.07), (0.085, 0.085), (0.11, 0.12), (0.15, 0.17), (end_r * 0.8, end_r)], mat,
                    ring_n=20, rings=20, up_hint=(0, -1, 0), cap0=False, cap1=False)
        sol = o.modifiers.new('Th', 'SOLIDIFY')
        sol.thickness = 0.008
        C.outline(o, 0.003)
        bones = ['chest', 'upper.' + s, 'fore.' + s]
        out.append((o, bones))
    return out


def obi(prefix, cfg, arm, color, pattern=None, z=1.08, h=0.085):
    m = A.toon(prefix + 'ObiM', color, shade=cfg.get('obiShade'))
    rings = [(z - h / 2, 0.165, 0.118, 0.0, None), (z + h / 2, 0.16, 0.114, 0.0, None)]
    o = C.loft_z(prefix + 'Obi', rings, m, n=40, cap0=True, cap1=True)
    C.outline(o, 0.003)
    out = [(o, ['spine', 'pelvis'])]
    if pattern:
        surf = C.Surface([o])
        pm = A.flat(prefix + 'ObiPat', pattern)
        for i in range(-4, 5):
            x = i * 0.034
            pts = [(x - 0.017, z), (x, z + h * 0.36), (x + 0.017, z), (x, z - h * 0.36)]
            pts.append(pts[0])
            dd = C.decal(prefix + 'ObiP%d' % i, C.stroke_poly(pts, 0.0024, 0.0024), pm, surf, offset=0.001, sub=1)
            if dd:
                out.append((dd, ['spine', 'pelvis']))
    return out


def scarf(prefix, cfg, arm, color, shade=None):
    m = A.toon(prefix + 'ScarfM', color, shade=shade)

    def bump(a):
        return 1.0 + 0.05 * math.sin(a * 5)
    rings = [(1.47, 0.12, 0.1, 0.0, bump), (1.53, 0.115, 0.1, 0.004, bump), (1.6, 0.095, 0.088, 0.012, bump), (1.66, 0.085, 0.082, 0.016, bump),
             (1.69, 0.078, 0.075, 0.018, None)]
    o = C.loft_z(prefix + 'Scarf', rings, m, n=32, cap0=False)
    sol = o.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.01
    C.outline(o, 0.003)
    return [(o, ['chest', 'neck'])]


def lapel_band(prefix, cfg, arm, color, hanging=True):
    """Dunkler Kragenrand (V) und herabhängendes Band (Sukuna)."""
    surf = C.Surface([o for o in bpy.data.objects if o.name in (prefix + 'Body', prefix + 'Robe', prefix + 'Obi')])
    m = A.flat(prefix + 'LapelM', color)
    out = []
    o = C.decal(prefix + 'Lapel', C.stroke_poly([(-0.07, 1.5), (-0.02, 1.36), (0.03, 1.2), (0.05, 1.12)], 0.03, 0.03), m, surf, sub=2, offset=0.002)
    if o:
        out.append((o, TORSO))
    o = C.decal(prefix + 'Lapel2', C.stroke_poly([(0.07, 1.5), (0.035, 1.42), (0.0, 1.34)], 0.02, 0.012), m, surf, sub=2, offset=0.0018)
    if o:
        out.append((o, TORSO))
    if hanging:
        # Band vom Obi bis fast zum Boden (eigenes Stück Stoff, schwingt mit dem Becken)
        pts = [V((0.04, -0.125, 1.04)), V((0.05, -0.16, 0.7)), V((0.055, -0.175, 0.35)), V((0.06, -0.18, 0.1))]
        b = C.sweep(prefix + 'Hang', pts, [(0.03, 0.006), (0.032, 0.006), (0.033, 0.006), (0.034, 0.006)], A.toon(prefix + 'HangM', color),
                    ring_n=8, rings=12, up_hint=(0, -1, 0))
        C.outline(b, 0.002)
        out.append((b, ['pelvis']))
    return out


def sandals(prefix, cfg, arm, sole='#4a3528', strap='#9a9aa6'):
    out = []
    sm = A.toon(prefix + 'SoleM', sole)
    st = A.toon(prefix + 'StrapM', strap)
    for s, sx in (('L', 1), ('R', -1)):
        x = 0.104 * sx
        o = C.ellipsoid(prefix + 'Sole' + s, (x, -0.06, 0.012), (0.05, 0.13, 0.012), sm, seg=20)
        C.outline(o, 0.002)
        out.append((o, 'foot.' + s))
        for k, (yy, zz) in enumerate(((-0.1, 0.05), (-0.06, 0.07))):
            t = C.sweep(prefix + 'Strap%s%d' % (s, k), [(x - 0.04, yy + 0.04, 0.03), (x, yy, zz), (x + 0.04, yy + 0.04, 0.03)], [0.007] * 3, st, ring_n=8, rings=8)
            out.append((t, 'foot.' + s))
    return out


def boots_sole(prefix, cfg, arm, color='#c42a2a'):
    out = []
    m = A.toon(prefix + 'RedSole', color)
    for s, sx in (('L', 1), ('R', -1)):
        o = C.ellipsoid(prefix + 'RSole' + s, (0.104 * sx, -0.06, 0.008), (0.05, 0.12, 0.01), m, seg=20)
        C.outline(o, 0.002)
        out.append((o, 'foot.' + s))
    return out


def blindfold(prefix, cfg, arm):
    m = A.toon(prefix + 'BlindM', '#16161c', shade='#08080b', highlight='#3a3a48')
    c = C.HEAD_C
    rings = []
    o = C.loft_z(prefix + 'Blindfold', [(c.z - 0.028, C.HEAD_R * 0.98, C.HEAD_R * 1.0, 0.004, None), (c.z + 0.018, C.HEAD_R * 1.0, C.HEAD_R * 1.04, 0.006, None)],
                 m, n=40)
    # Gesichtsseite flacher anpassen (Kopf vorne flach)
    for v in o.data.vertices:
        if v.co.y < -C.HEAD_R * 0.55:
            v.co.y = -C.HEAD_R * 0.55 - (-(v.co.y) - C.HEAD_R * 0.55) * 0.6 - 0.004
    sol = o.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.005
    C.outline(o, 0.002)
    return [(o, 'head')]


def jogo_head(prefix, cfg):
    """Jogo: Vulkankopf – helles, rundes Gesicht mit einem Auge, oben brauner Vulkan mit Krater, seitliche Steine."""
    M = cfg['_mats']
    face_m = M['skin']
    rock = A.toon(prefix + 'VolcRock', '#8a5a3c', shade='#4a2c1c', highlight='#a8744e')
    dark = A.toon(prefix + 'VolcDark', '#3a2218', shade='#1a0e08')
    c = C.HEAD_C + V((0, 0, -0.01))
    parts = []
    # Gesicht/Kopf: breiter, runder Kegelstumpf
    rings = [(c.z - 0.13, 0.07, 0.065, 0.0, None), (c.z - 0.1, 0.115, 0.11, 0.0, None), (c.z - 0.03, 0.135, 0.13, 0.0, None),
             (c.z + 0.04, 0.13, 0.125, 0.0, None), (c.z + 0.08, 0.118, 0.112, 0.0, None)]
    hd = C.loft_z(prefix + 'Head', rings, face_m, n=40, cap0=True, cap1=False)
    C.outline(hd, 0.003)
    parts.append(hd)
    # Vulkan-Oberteil (braun), oben schmal mit Krater
    vr = [(c.z + 0.055, 0.136, 0.131, 0.0, None), (c.z + 0.1, 0.124, 0.118, 0.003, None), (c.z + 0.16, 0.095, 0.09, 0.008, None),
          (c.z + 0.215, 0.066, 0.063, 0.012, None), (c.z + 0.235, 0.072, 0.069, 0.012, None)]
    vt = C.loft_z(prefix + 'VolcTop', vr, rock, n=40)
    sol = vt.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.012
    C.outline(vt, 0.003)
    parts.append(vt)
    lava = A.glow(prefix + 'Crater', '#ff8a2a', 3.5)
    parts.append(C.loft_z(prefix + 'CraterIn', [(c.z + 0.215, 0.058, 0.055, 0.012, None), (c.z + 0.216, 0.0, 0.0, 0.012, None)], lava, n=24, cap0=True))
    # gezackte Lavaflecken am Rand des Vulkans
    surf = C.Surface([vt])
    for i in range(10):
        a = i / 10 * math.tau
        p = V((math.sin(a) * 0.13, -math.cos(a) * 0.13, 0))
        pts = [(math.sin(a) * 0.4 * k, 0) for k in range(1)]
    for sx in (-1, 1):   # Steine an den Seiten
        st = C.ellipsoid(prefix + 'Stone%d' % sx, c + V((sx * 0.13, 0.0, 0.03)), (0.03, 0.035, 0.045), dark, seg=12)
        C.outline(st, 0.002)
        parts.append(st)
    # Gesicht: ein großes Auge in der Mitte + breiter Mund
    fs = C.Surface([hd])
    white = A.flat(prefix + 'EyeW', '#fbfbf6')
    blk = A.flat(prefix + 'EyeB', '#141012')
    iris = A.glow(prefix + 'Iris', '#2a1a12', 1.0)
    ez = c.z + 0.025
    up = [(-0.04 + 0.08 * i / 20, ez + 0.022 * math.sin(math.pi * i / 20) ** 0.7) for i in range(21)]
    lo = [(-0.04 + 0.08 * i / 20, ez - 0.02 * math.sin(math.pi * i / 20) ** 0.8) for i in range(21)]
    parts.append(C.decal(prefix + 'EyeWhite', up + list(reversed(lo)), white, fs))
    parts.append(C.decal(prefix + 'EyeIris', C.ellipse_poly(0.0, ez, 0.009, 0.012), iris, fs, offset=0.0016))
    parts.append(C.decal(prefix + 'EyeLid', C.stroke_poly(up, 0.004, 0.004), blk, fs, offset=0.002))
    parts.append(C.decal(prefix + 'EyeLow', C.stroke_poly(lo, 0.002, 0.002), blk, fs, offset=0.002))
    mz = c.z - 0.06
    top = [(-0.055 + 0.11 * i / 20, mz + 0.006 * abs(-1 + 2 * i / 20) ** 2) for i in range(21)]
    bot = [(-0.045 + 0.09 * i / 20, mz - 0.016 * math.sin(math.pi * i / 20)) for i in range(21)]
    parts.append(C.decal(prefix + 'MouthIn', top + list(reversed(bot)), A.flat(prefix + 'MouthD', '#2a1014'), fs, offset=0.0012))
    tb = [(u, v - 0.004) for u, v in top]
    parts.append(C.decal(prefix + 'TeethJ', top + list(reversed(tb)), A.flat(prefix + 'TeethM', '#f4efe2'), fs, offset=0.0015))
    parts.append(C.decal(prefix + 'Lips', C.stroke_poly(top, 0.0025, 0.0025), A.flat(prefix + 'LipM', '#3a2a3a'), fs, offset=0.0019))
    parts.append(C.decal(prefix + 'LipsB', C.stroke_poly(bot, 0.002, 0.002), A.flat(prefix + 'LipM', '#3a2a3a'), fs, offset=0.0019))
    # Lava-/Felstropfen vom Vulkanrand über die Stirn
    dm = A.flat(prefix + 'DripM', '#6a4028')
    for i, (x, ln) in enumerate(((-0.1, 0.03), (-0.06, 0.018), (-0.02, 0.026), (0.03, 0.02), (0.075, 0.032), (0.11, 0.02))):
        top_z = c.z + 0.062
        parts.append(C.decal(prefix + 'Drip%d' % i, [(x - 0.016, top_z), (x + 0.016, top_z), (x + 0.008, top_z - ln * 0.6), (x, top_z - ln), (x - 0.007, top_z - ln * 0.6)], dm, fs, offset=0.0012, sub=1))
    # Wangenfalten
    for sx in (-1, 1):
        parts.append(C.decal(prefix + 'Cheek%d' % sx, C.stroke_poly([(sx * 0.06, mz + 0.02), (sx * 0.068, mz - 0.005), (sx * 0.055, mz - 0.025)], 0.0015, 0.0008),
                             blk, fs, offset=0.0016))
    return [p for p in parts if p]


def fur_collar(prefix, cfg, arm, color='#f0e6d2', shade='#bfae90', z=1.55):
    m = A.toon(prefix + 'FurM', color, shade=shade)
    bm = bmesh.new()
    R, r = 0.14, 0.065
    n, k = 48, 14
    rnd = random.Random(3)
    grid = []
    for i in range(n):
        a = i / n * math.tau
        ring = []
        for j in range(k):
            b = j / k * math.tau
            fluff = 1.0 + 0.22 * max(0, math.sin(a * 9 + j)) * (0.5 + 0.5 * math.cos(b))
            rr = r * fluff
            p = V((math.cos(a) * (R + math.cos(b) * rr), math.sin(a) * (R * 0.85 + math.cos(b) * rr), z + math.sin(b) * rr * 0.9))
            ring.append(bm.verts.new(p))
        grid.append(ring)
    for i in range(n):
        for j in range(k):
            bm.faces.new((grid[i][j], grid[(i + 1) % n][j], grid[(i + 1) % n][(j + 1) % k], grid[i][(j + 1) % k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = C._mesh_from_bm(prefix + 'Fur', bm, m)
    C.outline(o, 0.003)
    return [(o, ['chest', 'neck'])]


def poncho(prefix, cfg, arm, color, shade, hem=1.04, spots=None, rx=0.31, ry=0.22, ragged=0.0):
    """Umhang/Poncho über die Schultern (Jogo: Flecken, Mahito: Patchwork)."""
    m = A.toon(prefix + 'PonchoM', color, shade=shade, highlight=cfg.get('ponchoHi'))
    rnd = random.Random(7)

    def rag(a):
        return 1.0 + ragged * (0.5 + 0.5 * math.sin(a * 5 + 1.3))
    rings = [(1.6, 0.085, 0.08, 0.012, None), (1.55, 0.16, 0.12, 0.008, None), (1.47, 0.255, 0.15, 0.005, None),
             (1.35, rx * 0.95, ry * 0.85, 0.0, None), ((1.35 + hem) / 2, rx, ry, 0.0, None), (hem, rx * 1.02, ry * 1.02, 0.0, rag)]
    o = C.loft_z(prefix + 'Poncho', rings, m, n=48)
    sol = o.modifiers.new('Th', 'SOLIDIFY')
    sol.thickness = 0.008
    C.outline(o, 0.003)
    out = [(o, ['chest', 'spine', 'neck', 'upper.L', 'upper.R'])]
    if spots:
        surf = C.Surface([o])
        sm = A.flat(prefix + 'Spot', spots)
        k = 0
        for direction, plane, sign in (((0, 1, 0), ('x', 'z'), 1), ((0, -1, 0), ('x', 'z'), -1), ((-1, 0, 0), ('y', 'z'), 1), ((1, 0, 0), ('y', 'z'), -1)):
            for i in range(9):
                u = rnd.uniform(-0.22, 0.22)
                v = rnd.uniform(hem + 0.04, 1.48)
                rr = rnd.uniform(0.014, 0.03)
                poly = [(u + math.cos(a) * rr * rnd.uniform(0.75, 1.25), v + math.sin(a) * rr * rnd.uniform(0.7, 1.2)) for a in [q / 10 * math.tau for q in range(10)]]
                d = C.decal(prefix + 'Spot%d' % k, poly, sm, surf, plane=plane, direction=direction, offset=0.002, sub=1)
                k += 1
                if d:
                    out.append((d, ['chest', 'spine', 'neck', 'upper.L', 'upper.R']))
    return out


# ═════════════════════════ Besetzung ═════════════════════════
def _gojo():
    folds = [  # violette Glanzlichter auf der schwarzen Uniform (wie in der Vorlage)
        ([(-0.12, 1.42), (-0.06, 1.36), (-0.02, 1.3)], 0.012, 0.004), ([(0.13, 1.4), (0.08, 1.33)], 0.01, 0.003),
        ([(-0.1, 1.2), (-0.04, 1.15)], 0.008, 0.002), ([(0.06, 1.12), (0.12, 1.05)], 0.008, 0.003),
        ([(-0.14, 0.95), (-0.1, 0.88)], 0.008, 0.002), ([(0.13, 0.93), (0.1, 0.85)], 0.006, 0.002),
        ([(-0.1, 0.62), (-0.09, 0.5), (-0.1, 0.42)], 0.007, 0.002), ([(0.08, 0.7), (0.1, 0.6)], 0.006, 0.002),
        ([(0.11, 0.33), (0.1, 0.22)], 0.005, 0.002), ([(-0.11, 0.3), (-0.095, 0.2)], 0.005, 0.002),
        ([(0.24, 1.36), (0.245, 1.25)], 0.008, 0.002), ([(-0.24, 1.34), (-0.245, 1.26)], 0.008, 0.002),
        ([(0.25, 1.08), (0.255, 0.99)], 0.006, 0.002), ([(-0.25, 1.1), (-0.255, 1.0)], 0.006, 0.002),
    ]
    return dict(
        radii={'sh': 0.95, 'el': 0.92, 'wr': 0.95, 'hi': 0.93, 'kn': 0.95, 'an': 0.95, 'waist': 0.95, 'chest': 1.0, 'upchest': 1.02},
        hair='#f4f6fb', hairShade='#b6bfd6', hairHi='#ffffff', hairStyle='gojo', capFront=0.35,
        coat='#1a1828', coatShade='#0c0b14', coatHi='#3a3058', coatSteps=(0.42, 0.93), shoe='#101014', shoeHi='#55556a',
        eye={'iris': '#5fd8ff', 'irisLo': '#e0fbff', 'irisDark': '#1b4a7a', 'lash': '#e8ecf6', 'w': 0.033, 'h': 0.0145, 'slant': 0.002,
             'irisW': 0.0125, 'irisH': 0.0155},
        eyeGlow=2.6, browColor='#e8ecf6', browAngle=0.05, mouth='line', neckCovered=True,
        hands={'R': ['relaxed', 'cross'], 'L': ['relaxed', 'fist']},
        builders=[high_collar, jacket_skirt, blindfold, seam,
                  lambda p, c, a: fold_lines(p, c, a, '#4a3a78', folds)],
        sign='cross', blindfold=True, signHands={'R': 'cross'})


def _sukuna():
    marks = []
    for sx in (-1, 1):
        marks += [
            dict(pts=[(sx * 0.024, HZ - 0.021), (sx * 0.05, HZ - 0.024), (sx * 0.074, HZ - 0.016)], w=0.0032, w1=0.0018, taper=(0.1, 0.4)),   # unter dem Auge
            dict(pts=[(sx * 0.082, HZ - 0.03), (sx * 0.07, HZ - 0.05), (sx * 0.074, HZ - 0.07)], w=0.0034, w1=0.002),                       # Wange
            dict(pts=[(sx * 0.06, HZ - 0.085), (sx * 0.042, HZ - 0.092), (sx * 0.03, HZ - 0.1)], w=0.0028, w1=0.0016),                       # Kinn
        ]
    marks += [dict(pts=[(-0.012, HZ + 0.06), (0.0, HZ + 0.052), (0.012, HZ + 0.06)], w=0.0035, w1=0.0035),
              dict(pts=[(-0.016, HZ + 0.072), (0.0, HZ + 0.066), (0.016, HZ + 0.072)], w=0.0028, w1=0.0028)]
    folds = [([(-0.1, 0.9), (-0.12, 0.6), (-0.13, 0.3)], 0.004, 0.001), ([(0.12, 0.85), (0.15, 0.5), (0.16, 0.2)], 0.004, 0.001),
             ([(0.02, 0.85), (0.04, 0.5), (0.05, 0.15)], 0.003, 0.001)]
    return dict(
        radii={'sh': 1.02, 'chest': 1.05, 'upchest': 1.08, 'waist': 1.0, 'hi': 1.0, 'kn': 1.1, 'an': 1.05},
        hair='#f2a0b8', hairShade='#c2627e', hairHi='#ffd0dd', hairStyle='sukuna', undercut='#3a2228', capFront=0.6, capLow=0.2,
        coat='#f2f1ee', coatShade='#b4b6c0', coatHi='#ffffff', pants='#f2f1ee', shoe='#2e3038', shoeZ=0.12,
        skin='#f6d9c4', skinShade='#d9a58e',
        eye={'iris': '#ff2e3a', 'irisLo': '#ffb0a0', 'irisDark': '#5a0a10', 'lash': '#1a1013', 'w': 0.031, 'h': 0.011, 'slant': 0.006,
             'irisW': 0.0085, 'irisH': 0.0105},
        eyeGlow=2.2, browColor='#c46d86', browAngle=0.25, mouth='grin', marks=marks, markColor='#1c1214', nails='#141016',
        neckCovered=True, hands={'R': ['claw', 'flat', 'fist', 'open'], 'L': ['claw', 'flat', 'fist']},
        builders=[kimono_robe, wide_sleeves, scarf_dark, obi_sukuna, sukuna_lapel, sandals, sukuna_open_mouth,
                  lambda p, c, a: fold_lines(p, c, a, '#a9acb8', folds)],
        sign='enma', signHands={'R': 'flat', 'L': 'flat'})


def sukuna_open_mouth(p, c, a):
    """Weit geöffnetes Maul (für die Nahaufnahme, wenn Sukuna den Finger fängt) – Zähne oben/unten, Zunge.
    Standardmäßig ausgeblendet (build_char), die Szene blendet es ein."""
    head = bpy.data.objects[p + 'Head']
    fs = C.Surface([head])
    out = []
    cz = HZ - 0.07
    rx, rz = 0.028, 0.03
    rim = [(math.cos(t) * rx, cz + math.sin(t) * rz * (1.0 if math.sin(t) > 0 else 1.15)) for t in [k / 32 * math.tau for k in range(32)]]
    k = [0]

    def put(poly, mat, off, sub=1):
        o = C.decal(p + 'BigMouth%d' % k[0], poly, mat, fs, offset=off, sub=sub)
        k[0] += 1
        if o:
            out.append(o)
    put(rim, A.flat(p + 'BigMouthIn', '#2a0608'), 0.0012, sub=2)
    put(C.ellipse_poly(0, cz - rz * 0.6, rx * 0.6, rz * 0.35), A.flat(p + 'BigMouthTongue', '#b0303a'), 0.0016)
    teeth = A.flat(p + 'BigMouthTeeth', '#fbf8f2')
    for i in range(8):
        u = -0.022 + i * 0.0063
        top = cz + rz * math.sqrt(max(0.0, 1 - (u / rx) ** 2)) - 0.001
        bot = cz - rz * 1.15 * math.sqrt(max(0.0, 1 - (u / rx) ** 2)) + 0.001
        put([(u - 0.003, top), (u + 0.003, top), (u, top - (0.009 if i in (1, 6) else 0.006))], teeth, 0.0019)
        put([(u - 0.003, bot), (u + 0.003, bot), (u, bot + 0.006)], teeth, 0.0019)
    put(C.stroke_poly(rim + [rim[0]], 0.0018, 0.0018), A.flat(p + 'BigMouthLine', '#1a0a0c'), 0.0022)
    return [(o, 'head') for o in out if o]


def scarf_dark(p, c, a):
    return scarf(p, c, a, '#3a3e48', shade='#1e2028')


def obi_sukuna(p, c, a):
    return obi(p, c, a, '#2a2c3c', pattern='#c8ccd8')


def sukuna_lapel(p, c, a):
    return lapel_band(p, c, a, '#2a2c3c')


def _megumi():
    return dict(
        radii={'sh': 0.93, 'el': 0.9, 'wr': 0.92, 'hi': 0.92, 'kn': 0.92, 'an': 0.95, 'waist': 0.92, 'chest': 0.96, 'upchest': 0.97},
        hair='#14161f', hairShade='#05060a', hairHi='#3c4258', hairStyle='megumi', capFront=0.42,
        coat='#1b2030', coatShade='#0a0c14', coatHi='#3a4460', shoe='#0e0f14',
        eye={'iris': '#5a6f96', 'irisLo': '#b8c8e8', 'irisDark': '#141c30', 'w': 0.031, 'h': 0.0115, 'slant': 0.003, 'irisW': 0.0105},
        eyeGlow=1.1, browColor='#14161f', browAngle=0.18, mouth='line', neckCovered=True,
        hands={'R': ['relaxed', 'fist'], 'L': ['relaxed', 'fist']},
        builders=[high_collar, jacket_skirt, lambda p, c, a: seam(p, c, a, color='#9aa3b8', w=0.002)],
        sign='dog', signHands={'R': 'fist', 'L': 'fist'})


def _mahito():
    stitches = [
        [(0.07, HZ + 0.045), (0.035, HZ + 0.012), (0.0, HZ - 0.02), (-0.04, HZ - 0.045), (-0.075, HZ - 0.06)],   # quer übers Gesicht
        [(-0.07, HZ + 0.03), (-0.072, HZ - 0.0)],
    ]
    return dict(
        radii={'sh': 0.98, 'el': 0.9, 'wr': 0.92, 'hi': 0.95, 'kn': 0.92, 'an': 0.95, 'waist': 0.92},
        hair='#b9cdd6', hairShade='#7f99aa', hairHi='#e2eef2', hairStyle='mahito', capFront=0.5,
        coat='#24242c', coatShade='#101016', coatHi='#5c6a8a', pants='#1e1e26', pantsHi='#5c6a8a', shoe='#eeeef2', shoeShade='#a9aab8', shoeHi='#ffffff',
        skin='#f3e3d6', skinShade='#d4b2a2', bareArms=1.44,
        eye={'iris': '#9db4d0', 'irisLo': '#e6f0ff', 'irisDark': '#3a4a66', 'w': 0.032, 'h': 0.0135, 'slant': -0.001, 'irisW': 0.0105},
        eyeGlow=1.4, browColor='#9fb4c0', browAngle=-0.05, mouth='smile', stitches=stitches, markColor='#3a2a30',
        hands={'R': ['claw', 'open'], 'L': ['claw', 'open']},
        builders=[mahito_poncho, mahito_straps, mahito_arm_stitches, mahito_shoes, mahito_mouth],
        sign='hands', signHands={'R': 'open', 'L': 'open'})


def mahito_mouth(p, c, a):
    """Weit aufgerissener Mund (von der Nase bis zum Kinn) – darin füllt das Fingerzeichen fast den ganzen Mund:
    zwei helle Handflächen, die Finger kreuzweise ineinander verschränkt, Daumen in der Mitte nach oben (nach Anime-Vorlage).
    Wird in der Domain nur für die Gesichts-Nahaufnahme eingeblendet."""
    head = bpy.data.objects[p + 'Head']
    fs = C.Surface([head])
    out = []
    cz = HZ - 0.074
    rx, rz = 0.031, 0.04
    n = 32
    rim = [(math.cos(t) * rx * (1 - 0.12 * max(0, -math.sin(t))), cz + math.sin(t) * rz) for t in [k / n * math.tau for k in range(n)]]
    k = [0]

    def put(poly, mat, off, sub=1):
        o = C.decal(p + 'BigMouth%d' % k[0], poly, mat, fs, offset=off, sub=sub)
        k[0] += 1
        if o:
            out.append(o)
    dark = A.flat(p + 'BigMouthIn', '#100818')
    put(rim, dark, 0.0012, sub=2)
    teeth = A.flat(p + 'BigMouthTeeth', '#f6f2ff')
    for i in range(8):
        u = -0.024 + i * 0.0069
        top = cz + rz * math.sqrt(max(0.0, 1 - (u / rx) ** 2)) - 0.001
        bot = cz - rz * math.sqrt(max(0.0, 1 - (u / rx) ** 2)) * 0.88 + 0.001
        put([(u - 0.0032, top), (u + 0.0032, top), (u, top - 0.011)], teeth, 0.0016)
        put([(u - 0.0032, bot), (u + 0.0032, bot), (u, bot + 0.01)], teeth, 0.0016)
    ink = A.flat(p + 'MouthSignInk', '#22142c')
    skin = A.flat(p + 'MouthSignSkin', '#f4e8f2')
    shade = A.flat(p + 'MouthSignShade', '#c4aed8')
    put(C.stroke_poly(rim + [rim[0]], 0.0022, 0.0022), A.flat(p + 'BigMouthLine', '#2a1a2e'), 0.0021)
    # Fingerzeichen
    pz = cz - 0.012          # Handflächen-Mitte
    for sx in (-1, 1):
        palm = [(sx * 0.0012, pz - 0.019), (sx * 0.016, pz - 0.016), (sx * 0.019, pz + 0.002), (sx * 0.0012, pz + 0.006)]
        put(palm, skin, 0.0024)
        put([(sx * 0.0012, pz - 0.019), (sx * 0.006, pz - 0.018), (sx * 0.005, pz + 0.004), (sx * 0.0012, pz + 0.006)], shade, 0.0025)
        put(C.stroke_poly(palm + [palm[0]], 0.0013, 0.0013), ink, 0.0031)
    # verschränkte Finger: abwechselnd von links und rechts, schräg nach oben über die Mitte
    for f in range(4):
        for sx in ((-1, 1) if f % 2 == 0 else (1, -1)):
            z0 = pz + 0.004 + f * 0.0058
            b = (sx * 0.018, z0)
            t = (-sx * 0.012, z0 + 0.011)
            mid = ((b[0] + t[0]) / 2, (b[1] + t[1]) / 2 + 0.0015)
            off = 0.0026 + f * 0.0002 + (0.0001 if sx > 0 else 0)
            put(C.stroke_poly([b, mid, t], 0.0052, 0.0036, taper=(0.0, 0.25)), skin, off)
            put(C.stroke_poly([(b[0], b[1] - 0.0012), (mid[0], mid[1] - 0.0012), (t[0], t[1] - 0.0012)], 0.0016, 0.001, taper=(0.0, 0.3)), shade, off + 0.0001)
            put(C.stroke_poly([b, mid, t], 0.0009, 0.0007), ink, off + 0.0004)
    # Daumen in der Mitte, nebeneinander nach oben
    for sx in (-1, 1):
        th = [(sx * 0.0035, pz - 0.012), (sx * 0.003, pz + 0.002), (sx * 0.0022, pz + 0.012)]
        put(C.stroke_poly(th, 0.0048, 0.0036, taper=(0.0, 0.2)), skin, 0.0036)
        put(C.stroke_poly(th, 0.0009, 0.0008), ink, 0.004)
    return [(o, 'head') for o in out if o]


def mahito_poncho(p, c, a):
    out = poncho(p, c, a, '#24242c', '#0e0e14', hem=1.08, rx=0.3, ry=0.2, ragged=0.08)
    # Gitter-Nähte (Patchwork)
    surf = C.Surface([bpy.data.objects[p + 'Poncho']])
    m = A.flat(p + 'GridM', '#55586a')
    k = 0
    for direction in ((0, 1, 0), (0, -1, 0)):
        for i in range(-4, 5):
            o = C.decal(p + 'GridV%d' % k, C.stroke_poly([(i * 0.055, 1.5), (i * 0.06, 1.1)], 0.002, 0.002), m, surf, direction=direction, offset=0.002, sub=2)
            k += 1
            if o:
                out.append((o, ['chest', 'spine', 'upper.L', 'upper.R']))
        for j in range(5):
            z = 1.45 - j * 0.075
            o = C.decal(p + 'GridH%d' % k, C.stroke_poly([(-0.32, z), (0.32, z)], 0.002, 0.002), m, surf, direction=direction, offset=0.002, sub=3)
            k += 1
            if o:
                out.append((o, ['chest', 'spine', 'upper.L', 'upper.R']))
    # blaugraue Glanzstreifen
    hm = A.flat(p + 'PonchoHi', '#4f5a78')
    for i, pts in enumerate(([(-0.2, 1.38), (-0.26, 1.15)], [(0.18, 1.4), (0.24, 1.18)], [(0.02, 1.3), (0.05, 1.12)])):
        o = C.decal(p + 'PHi%d' % i, C.stroke_poly(pts, 0.03, 0.006, taper=(0.1, 0.5)), hm, surf, offset=0.0015, sub=2)
        if o:
            out.append((o, ['chest', 'spine', 'upper.L', 'upper.R']))
    return out


def mahito_straps(p, c, a):
    """Stoffbänder um den rechten Oberarm (wie in der Vorlage)."""
    m = A.toon(p + 'StrapM', '#2a2c38', shade='#12121a', highlight='#5c6a8a')
    out = []
    sh = V(C.BONES['upper.R'][0])
    el = V(C.BONES['fore.R'][0])
    for k, t in enumerate((0.35, 0.62)):
        cc = sh.lerp(el, t)
        rings = []
        o = C.sweep(p + 'ArmBand%d' % k, [cc + V((0, 0, 0.022)), cc + V((0, 0, -0.022))], [0.064, 0.06], m, ring_n=20, rings=3)
        C.outline(o, 0.002)
        out.append((o, ['upper.R']))
    return out


def mahito_arm_stitches(p, c, a):
    surf = C.Surface([bpy.data.objects[p + 'Body']])
    m = A.flat(p + 'ArmSt', '#4a3036')
    out = []
    for s, sx in (('L', 1), ('R', -1)):
        for k, z in enumerate((1.12, 0.99)):
            x = (0.24 + (1.19 - z) * 0.08) * sx
            o = C.decal(p + 'AS%s%d' % (s, k), C.stroke_poly([(x - 0.04, z + 0.008), (x + 0.04, z - 0.006)], 0.0014, 0.0014), m, surf, offset=0.0012, sub=2)
            if o:
                out.append((o, ['upper.' + s, 'fore.' + s]))
            for q in range(5):
                xx = x - 0.03 + q * 0.015
                zz = z + 0.006 - q * 0.0035
                o = C.decal(p + 'ASt%s%d%d' % (s, k, q), C.stroke_poly([(xx, zz + 0.006), (xx, zz - 0.006)], 0.0011, 0.0011), m, surf, offset=0.0014, sub=1)
                if o:
                    out.append((o, ['upper.' + s, 'fore.' + s]))
    return out


def mahito_shoes(p, c, a):
    surf = C.Surface([bpy.data.objects[p + 'Body']])
    m = A.flat(p + 'ShoeLine', '#1a1a22')
    out = []
    for sx in (-1, 1):
        o = C.decal(p + 'ShoeStripe%d' % sx, C.stroke_poly([(0.104 * sx - 0.02, 0.1), (0.104 * sx + 0.02, 0.05)], 0.006, 0.006), m, surf,
                    plane=('y', 'z'), direction=(-sx, 0, 0), origin=(0, 0, 0), offset=0.0015, sub=1)
        out += []
    return out


def _jogo():
    return dict(
        radii={'sh': 0.85, 'el': 0.75, 'wr': 0.8, 'chest': 0.95, 'upchest': 0.95, 'waist': 1.05, 'pelvis': 1.25, 'hi': (1.55, 1.5),
               'kn': (1.85, 1.75), 'an': (0.95, 0.95), 'to': 1.1},
        ptOffset={'kn': (0.07, 0.0, 0.0), 'an': (0.03, 0.0, 0.0), 'to': (0.03, 0.0, 0.0)},
        hairStyle='none', hair='#8a5a3c', coat='#1d2236', coatShade='#0b0d18', coatHi='#3a4466', pants='#1d2236',
        skin='#c8d0d8', skinShade='#8e9aa8', skinHi='#e2e8ee', shoe='#5a3a26', shoeShade='#2e1c12', shoeHi='#8a5e40', shoeZ=0.3,
        bareArms=1.42, headBuilder=jogo_head, handScale=0.95,
        hands={'R': ['relaxed', 'open'], 'L': ['relaxed', 'fist']},
        builders=[lambda p, c, a: fur_collar(p, c, a), jogo_haori, boots_sole],
        sign='fist', scale=0.86, signHands={'R': 'open'})


def jogo_haori(p, c, a):
    return poncho(p, c, a, '#cbbf4a', '#8a7f20', hem=1.14, spots='#1a1610', rx=0.3, ry=0.21)


def _mahoraga_parts(p, c, arm):
    """Halskette, Schärpe, Hakama, Armreifen, Bandage, Schwert, Muskel-Linien."""
    out = []
    white = c['_mats']['skin']
    blk = A.toon(p + 'Ring', '#2a2c30', shade='#111214', highlight='#55585e')
    cloth = A.toon(p + 'Cloth', '#ecebe6', shade='#a9abb2')
    green = A.toon(p + 'Hakama', '#3d4a44', shade='#1f2723', highlight='#56665e')
    # Hakama (weit, bis über die Knöchel)

    def pleat(a):
        return 1.0 + 0.045 * math.sin(a * 9)
    rings = [(1.1, 0.16, 0.115, 0.0, None), (0.95, 0.19, 0.135, 0.0, pleat), (0.6, 0.22, 0.155, 0.01, pleat), (0.22, 0.24, 0.17, 0.015, pleat)]
    hk = C.loft_z(p + 'HakamaSkirt', rings, green, n=48)
    hk.modifiers.new('Th', 'SOLIDIFY').thickness = 0.01
    C.outline(hk, 0.003)
    out.append((hk, ['spine', 'pelvis', 'thigh.L', 'thigh.R']))
    # Schärpe (weiß, Knoten vorne, Enden hängen) + dunkler Bund
    band = C.loft_z(p + 'Waistband', [(1.04, 0.165, 0.12, 0.0, None), (1.1, 0.162, 0.118, 0.0, None)], blk, n=40, cap0=True, cap1=True)
    C.outline(band, 0.002)
    out.append((band, ['spine', 'pelvis']))

    def twist(a):
        return 1.0 + 0.08 * math.sin(a * 3)
    sash = C.loft_z(p + 'Sash', [(1.0, 0.178, 0.132, -0.004, twist), (1.04, 0.176, 0.13, -0.004, twist)], cloth, n=40, cap0=True, cap1=True)
    C.outline(sash, 0.002)
    out.append((sash, ['spine', 'pelvis']))
    knot = C.ellipsoid(p + 'Knot', (0.0, -0.14, 1.02), (0.04, 0.03, 0.035), cloth, seg=14)
    C.outline(knot, 0.002)
    out.append((knot, 'pelvis'))
    for k, sx in enumerate((-1, 1)):
        tail = C.sweep(p + 'SashEnd%d' % k, [(sx * 0.015, -0.15, 1.0), (sx * 0.04, -0.175, 0.85), (sx * 0.05, -0.185, 0.66)],
                       [(0.03, 0.008), (0.038, 0.008), (0.035, 0.008)], cloth, ring_n=8, rings=10, up_hint=(0, -1, 0))
        C.outline(tail, 0.002)
        out.append((tail, ['pelvis']))
    # Halskette: Seil + Quasten
    neck_r = 0.15
    pts = [V((math.sin(a) * neck_r, -math.cos(a) * neck_r * 0.82 + 0.01, 1.47 - 0.07 * math.cos(a) ** 2)) for a in [math.radians(x) for x in range(-110, 111, 20)]]
    rope = C.sweep(p + 'Necklace', pts, [0.008] * len(pts), blk, ring_n=8, rings=30)
    out.append((rope, ['chest']))
    for i, ang in enumerate((-60, -30, 0, 30, 60)):
        a = math.radians(ang)
        base = V((math.sin(a) * neck_r, -math.cos(a) * neck_r * 0.82 + 0.005, 1.47 - 0.07 * math.cos(a) ** 2))
        bead = C.ellipsoid(p + 'Bead%d' % i, base + V((0, -0.008, -0.012)), (0.014, 0.012, 0.016), blk, seg=10)
        tas = C.sweep(p + 'Tassel%d' % i, [base + V((0, -0.01, -0.02)), base + V((0, -0.012, -0.07))], [0.006, 0.014], blk, ring_n=8, rings=4)
        out += [(bead, ['chest']), (tas, ['chest'])]
    # Armreifen (Handgelenke, Oberarme) + Fußreifen
    for s in ('L', 'R'):
        wr = V(C.BONES['hand.' + s][0])
        el = V(C.BONES['fore.' + s][0])
        d = (wr - el).normalized()
        rg = C.sweep(p + 'WristRing' + s, [wr - d * 0.06, wr - d * 0.03], [0.045, 0.045], blk, ring_n=18, rings=3)
        C.outline(rg, 0.002)
        out.append((rg, 'fore.' + s))
        an = V(C.BONES['foot.' + s][0])
        fr = C.sweep(p + 'AnkleRing' + s, [an + V((0, 0, 0.04)), an + V((0, 0, 0.065))], [0.05, 0.05], blk, ring_n=18, rings=3)
        C.outline(fr, 0.002)
        out.append((fr, 'shin.' + s))
    # Bandage am rechten Unterarm
    el, wr = V(C.BONES['fore.R'][0]), V(C.BONES['hand.R'][0])
    for k in range(7):
        t0 = 0.12 + k * 0.1
        a0, a1 = el.lerp(wr, t0), el.lerp(wr, t0 + 0.09)
        b = C.sweep(p + 'Band%d' % k, [a0, a1], [0.047 - k * 0.0015, 0.046 - k * 0.0015], cloth, ring_n=16, rings=3, cap0=False, cap1=False)
        b.rotation_euler = (0.08 * (k % 2), 0, 0)
        C.outline(b, 0.0015)
        out.append((b, 'fore.R'))
    # Schwert der Auslöschung: lange schmale Klinge aus der rechten Faust nach unten
    steel = A.toon(p + 'Steel', '#e6ebf2', shade='#9aa4b6', highlight='#ffffff')
    hb = V(C.BONES['hand.R'][0])
    bm = bmesh.new()
    L = 0.95
    prof = [(-0.016, 0.0), (0.016, 0.0), (0.012, -L * 0.9), (0.0, -L)]
    vs = [bm.verts.new((hb.x - 0.0 + 0, hb.y - 0.045 + x, hb.z - 0.06 + z)) for x, z in prof]
    vs2 = [bm.verts.new((hb.x + 0.004, hb.y - 0.045 + x, hb.z - 0.06 + z)) for x, z in prof]
    bm.faces.new(vs)
    bm.faces.new(list(reversed(vs2)))
    for i in range(4):
        bm.faces.new((vs[i], vs[(i + 1) % 4], vs2[(i + 1) % 4], vs2[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    blade = C._mesh_from_bm(p + 'Blade', bm, steel, smooth=False)
    C.outline(blade, 0.002)
    out.append((blade, 'hand.R'))
    guard = C.ellipsoid(p + 'Guard', (hb.x, hb.y - 0.045, hb.z - 0.06), (0.012, 0.03, 0.012), blk, seg=10)
    out.append((guard, 'hand.R'))
    # Muskel-Linien (Tusche) auf Brust, Bauch, Armen
    surf = C.Surface([bpy.data.objects[p + 'Body']])
    lm = A.flat(p + 'Muscle', '#6e7078')
    strokes = [
        [(-0.14, 1.36), (-0.08, 1.31), (-0.02, 1.32)], [(0.14, 1.36), (0.08, 1.31), (0.02, 1.32)],        # Brust unten
        [(-0.0, 1.43), (0.0, 1.32)],                                                                      # Brustbein
        [(-0.17, 1.44), (-0.14, 1.38)], [(0.17, 1.44), (0.14, 1.38)],                                       # Achsel
        [(0.0, 1.29), (0.0, 1.06)],                                                                       # Bauchlinie
        [(-0.06, 1.25), (0.06, 1.25)], [(-0.065, 1.18), (0.065, 1.18)], [(-0.06, 1.11), (0.06, 1.11)],      # Bauch
        [(-0.1, 1.28), (-0.09, 1.1), (-0.06, 1.0)], [(0.1, 1.28), (0.09, 1.1), (0.06, 1.0)],                # Seiten
        [(-0.135, 1.27), (-0.12, 1.24)], [(-0.135, 1.22), (-0.12, 1.19)], [(0.135, 1.27), (0.12, 1.24)], [(0.135, 1.22), (0.12, 1.19)],
        [(0.21, 1.4), (0.225, 1.3)], [(-0.21, 1.4), (-0.225, 1.3)], [(0.235, 1.15), (0.25, 1.05)], [(-0.235, 1.15), (-0.25, 1.05)],
    ]
    for i, st in enumerate(strokes):
        o = C.decal(p + 'Mus%d' % i, C.stroke_poly(st, 0.0045, 0.0018, taper=(0.2, 0.5)), lm, surf, offset=0.0016, sub=2)
        if o:
            out.append((o, TORSO + ['fore.L', 'fore.R']))
    return out


def mahoraga_head(prefix, cfg):
    """Kopf: helmartig, vier Flügel (zwei nach oben, zwei zur Seite, über den Augen), breites Grinsen, Rad darüber,
    Fortsatz nach hinten."""
    M = cfg['_mats']
    white = M['skin']
    wing = A.toon(prefix + 'WingM', '#f2f1ec', shade='#b4b6bc', highlight='#ffffff')
    gold = A.toon(prefix + 'Gold', '#d8b04a', shade='#8c6a1e', highlight='#fff0a8')
    c = C.HEAD_C
    parts = []
    hd = C.ellipsoid(prefix + 'Head', c + V((0, 0.005, -0.005)), (0.105, 0.11, 0.13), white, seg=32)
    for v in hd.data.vertices:          # Kiefer nach vorn, breites Maul
        if v.co.z < -0.02:
            t = (-0.02 - v.co.z) / 0.11
            v.co.y -= 0.03 * t
            v.co.x *= 1 + 0.12 * t
    C.outline(hd, 0.003)
    parts.append(hd)
    fs = C.Surface([hd])
    # Grinsen mit großen Zähnen
    mz = c.z - 0.055
    top = [(-0.07 + 0.14 * i / 24, mz + 0.022 * abs(-1 + 2 * i / 24) ** 1.5) for i in range(25)]
    bot = [(-0.062 + 0.124 * i / 24, mz - 0.022 * (1 - abs(-1 + 2 * i / 24) ** 2)) for i in range(25)]
    parts.append(C.decal(prefix + 'Maw', top + list(reversed(bot)), A.flat(prefix + 'MawM', '#1a1418'), fs, offset=0.0012))
    tm = A.flat(prefix + 'ToothM', '#fbfaf4')
    for i in range(10):
        u0 = -0.06 + i * 0.012
        v0 = mz + 0.022 * abs((u0 + 0.006) / 0.07) ** 1.5
        parts.append(C.decal(prefix + 'TU%d' % i, [(u0 + 0.001, v0), (u0 + 0.011, v0), (u0 + 0.0095, v0 - 0.016), (u0 + 0.0025, v0 - 0.016)], tm, fs, offset=0.0016, sub=1))
        parts.append(C.decal(prefix + 'TD%d' % i, [(u0 + 0.002, mz - 0.018 * (1 - ((u0 + 0.006) / 0.065) ** 2) + 0.001),
                                                    (u0 + 0.0105, mz - 0.018 * (1 - ((u0 + 0.006) / 0.065) ** 2) + 0.001),
                                                    (u0 + 0.009, mz - 0.003), (u0 + 0.003, mz - 0.003)], tm, fs, offset=0.0016, sub=1))
    parts.append(C.decal(prefix + 'MawL', C.stroke_poly(top, 0.0028, 0.0028), A.flat(prefix + 'MawLine', '#121014'), fs, offset=0.002))
    # Flügel: obere (nach oben-außen), untere (zur Seite, decken die Augen)
    for sx in (-1, 1):
        for k, (root, mid, tip, w) in enumerate((
                ((sx * 0.045, -0.07, 0.06), (sx * 0.09, -0.05, 0.12), (sx * 0.13, -0.01, 0.2), 0.03),
                ((sx * 0.025, -0.1, 0.015), (sx * 0.09, -0.085, 0.025), (sx * 0.17, -0.04, 0.05), 0.026))):
            pts = [c + V(root), c + V(mid), c + V(tip)]
            o = C.sweep(prefix + 'Wing%d%d' % (sx, k), pts, [(w, w * 0.5), (w * 0.9, w * 0.45), (0.003, 0.002)], wing, ring_n=12, rings=14,
                        up_hint=(0, -1, 0.3))
            C.outline(o, 0.002)
            parts.append(o)
            # Federlinien
            for q in range(3):
                f0 = c + V(root).lerp(V(mid), 0.3 + q * 0.2)
                f = C.sweep(prefix + 'Feather%d%d%d' % (sx, k, q), [f0 + V((0, -0.03, 0)), f0 + V((sx * 0.03, -0.035, -0.02 + 0.01 * k))],
                            [0.003, 0.0008], A.flat(prefix + 'FeatherL', '#6e7078'), ring_n=6, rings=4)
                parts.append(f)
    # Fortsatz vom Hinterkopf (nach hinten, Ende eingerollt)
    tail = [c + V((0, 0.08, 0.06)), c + V((0.0, 0.2, 0.08)), c + V((0.02, 0.35, 0.02)), c + V((0.03, 0.45, -0.06)), c + V((0.035, 0.43, -0.14)),
            c + V((0.03, 0.38, -0.12))]
    tl = C.sweep(prefix + 'HeadTail', tail, [0.045, 0.04, 0.035, 0.028, 0.02, 0.012], white, ring_n=14, rings=24)
    C.outline(tl, 0.002)
    parts.append(tl)
    # Rad mit acht Griffen (leicht geneigt über dem Kopf)
    wheel = A.empty(prefix + 'Wheel', c + V((0, 0.03, 0.24)))
    rim_pts = [V((math.cos(a) * 0.26, math.sin(a) * 0.26, 0)) for a in [i / 32 * math.tau for i in range(33)]]
    ring = C.sweep(prefix + 'WheelRing', rim_pts, [0.016] * 33, gold, ring_n=10, rings=64, cap0=False, cap1=False)
    hub = C.ellipsoid(prefix + 'Hub', (0, 0, 0), (0.04, 0.04, 0.03), gold, seg=14)
    wparts = [ring, hub]
    for i in range(8):
        a = i / 8 * math.tau
        d = V((math.cos(a), math.sin(a), 0))
        wparts.append(C.sweep(prefix + 'Spoke%d' % i, [d * 0.03, d * 0.26], [0.008, 0.008], gold, ring_n=8, rings=3))
        wparts.append(C.sweep(prefix + 'Handle%d' % i, [d * 0.26, d * 0.33, d * 0.37], [0.012, 0.012, 0.01], gold, ring_n=8, rings=6))
        wparts.append(C.ellipsoid(prefix + 'Knob%d' % i, tuple(d * 0.385), (0.022, 0.022, 0.022), gold, seg=12))
    for o in wparts:
        C.outline(o, 0.0018)
        o.parent = wheel
    wheel.rotation_euler = (math.radians(-18), 0, 0)
    parts.append(wheel)
    return [p for p in parts if p]


def _mahoraga():
    return dict(
        radii={'pelvis': (1.25, 1.3), 'waist': (1.1, 1.18), 'chest': (1.55, 1.42), 'upchest': (1.72, 1.5), 'neck': 1.9, 'neckTop': 1.7,
               'sh': 1.75, 'el': 1.45, 'wr': 1.35, 'hi': 1.4, 'kn': 1.35, 'an': 1.25, 'to': 1.2},
        ptOffset={'sh': (0.035, 0.0, 0.0), 'el': (0.04, 0.0, 0.0), 'wr': (0.035, 0.0, 0.0)},
        hairStyle='none', hair='#efeeea', coat='#efeeea', coatShade='#b2b5bc', skin='#efeeea', skinShade='#b2b5bc', skinHi='#ffffff',
        pants='#3d4a44', pantsShade='#1f2723', shoe='#efeeea', shoeShade='#b2b5bc', shoeZ=0.0, bareTorso=True, bareArms=1.6, pantsZ=0.0,
        headBuilder=mahoraga_head, handScale=1.15,
        hands={'R': ['grip'], 'L': ['relaxed', 'fist']},
        builders=[_mahoraga_parts], outline=0.004, sign=None, scale=1.85)


def _generic(**kw):
    base = dict(hands={'R': ['relaxed', 'point', 'fist'], 'L': ['relaxed', 'fist']})
    base.update(kw)
    return base


def _yuta():
    return _generic(hair='#1c1b2c', hairShade='#08080f', hairHi='#3c3a5a', hairStyle='messy', coat='#f1f2f6', coatShade='#a6aabb', coatHi='#ffffff',
                    eye={'iris': '#2a2a48', 'irisLo': '#9a8ac8', 'irisDark': '#0e0e1a', 'w': 0.032, 'h': 0.014, 'slant': -0.002},
                    eyeGlow=1.0, browColor='#1c1b2c', browAngle=-0.08, mouth='line', neckCovered=True, shoe='#2a2a34',
                    builders=[high_collar, jacket_skirt, lambda p, c, a: seam(p, c, a, color='#2b2d3a'), yuta_katana], sign='cross',
                    hands={'R': ['relaxed', 'cross', 'grip'], 'L': ['relaxed', 'fist']})


def yuta_katana(p, c, a):
    sm = A.toon(p + 'SheathM', '#1c1720')
    hm = A.toon(p + 'KHiltM', '#3b2a4a')
    s = C.sweep(p + 'Sheath', [(0.2, 0.15, 0.8), (-0.12, 0.15, 1.5)], [0.022, 0.022], sm, ring_n=10, rings=4)
    h = C.sweep(p + 'KHilt', [(-0.12, 0.15, 1.5), (-0.2, 0.15, 1.68)], [0.018, 0.018], hm, ring_n=10, rings=4)
    for o in (s, h):
        C.outline(o, 0.002)
    return [(s, 'chest'), (h, 'chest')]


def _higuruma():
    return _generic(hair='#18161c', hairShade='#050407', hairHi='#3a3640', hairStyle='slick', coat='#1e1e26', coatShade='#0b0b10', coatHi='#3e3e50',
                    eye={'iris': '#d8b84a', 'irisLo': '#fff0b0', 'irisDark': '#3a2a10', 'w': 0.031, 'h': 0.011, 'slant': 0.001},
                    eyeGlow=1.3, browColor='#18161c', browAngle=0.12, mouth='line', builders=[jacket_skirt, suit_parts], sign='point')


def suit_parts(p, c, a):
    surf = C.Surface([o for o in bpy.data.objects if o.name in (p + 'Body', p + 'JacketSkirt')])
    out = []
    shirt = C.decal(p + 'Shirt', [(-0.045, 1.55), (0.045, 1.55), (0.0, 1.3)], A.flat(p + 'ShirtM', '#f0f0f2'), surf, sub=2)
    tie = C.decal(p + 'Tie', [(-0.012, 1.53), (0.012, 1.53), (0.016, 1.3), (0.0, 1.27), (-0.016, 1.3)], A.flat(p + 'TieM', '#8a1d1d'), surf, offset=0.0025, sub=2)
    badge = C.decal(p + 'Badge', C.ellipse_poly(0.085, 1.43, 0.013, 0.013), A.glow(p + 'BadgeM', '#ffd24a', 2.5), surf, offset=0.0025, sub=1)
    for o in (shirt, tie, badge):
        if o:
            out.append((o, TORSO))
    return out


def _hakari():
    return _generic(hair='#2e2e36', hairShade='#111116', hairHi='#55556a', hairStyle='pompadour', capFront=0.62, coat='#202634', coatShade='#0b0e15', coatHi='#3e4a66',
                    eye={'iris': '#ff6fb0', 'irisLo': '#ffd0e6', 'irisDark': '#4a0a2a', 'w': 0.031, 'h': 0.0125, 'slant': 0.004},
                    eyeGlow=1.8, browColor='#2e2e36', browAngle=0.18, mouth='grin', neckCovered=True,
                    builders=[high_collar, jacket_skirt, lambda p, c, a: fur_collar(p, c, a, z=1.52)], sign='fist')


def _naoya():
    return _generic(hair='#f2d35c', hairShade='#b38b20', hairHi='#fff3b0', hairStyle='undercut', coat='#22204a', coatShade='#0d0c21', coatHi='#4a46a0',
                    pants='#22204a', eye={'iris': '#c7d2fe', 'irisLo': '#ffffff', 'irisDark': '#3a3a6a', 'w': 0.031, 'h': 0.011, 'slant': 0.005},
                    eyeGlow=1.6, browColor='#d8b84a', browAngle=0.15, mouth='smile', neckCovered=False,
                    builders=[kimono_robe, lambda p, c, a: obi(p, c, a, '#a5b4fc'), sandals], sign='point')


def _dagon():
    return _generic(hair='#d83a3a', hairStyle='none', coat='#8a1c1c', coatShade='#3d0909', coatHi='#c04040', skin='#e05a4a', skinShade='#a02a20',
                    headBuilder=dagon_head, builders=[kimono_robe], sign='hands')


def dagon_head(prefix, cfg):
    red = A.toon(prefix + 'Octo', '#d83a3a', shade='#7a1414', highlight='#ff8080')
    c = C.HEAD_C
    parts = [C.ellipsoid(prefix + 'Dome', c + V((0, 0.02, 0.1)), (0.2, 0.18, 0.22), red, seg=32)]
    for i in range(6):
        a = math.pi * 1.1 + i / 5 * math.pi * 0.8
        x, y = math.cos(a) * 0.1, math.sin(a) * 0.08
        parts.append(C.sweep(prefix + 'Tent%d' % i, [c + V((x, y - 0.02, -0.04)), c + V((x * 1.3, y - 0.05, -0.16)), c + V((x * 1.6, y - 0.02, -0.28))],
                             [0.035, 0.025, 0.004], red, ring_n=10, rings=10))
    eye = A.glow(prefix + 'Iris', '#fde68a', 2.5)
    fs = C.Surface([parts[0]])
    for sx in (-1, 1):
        parts.append(C.decal(prefix + 'OEye%d' % sx, C.ellipse_poly(sx * 0.07, c.z + 0.12, 0.025, 0.02), eye, fs))
    for o in parts:
        if o and o.type == 'MESH' and 'Eye' not in o.name:
            C.outline(o, 0.003)
    return [p for p in parts if p]


def _foe():
    return _generic(hair='#130c18', hairShade='#000000', hairHi='#3a2a48', hairStyle='messy', coat='#2a1236', coatShade='#0f0514', coatHi='#5a2a78',
                    skin='#a898b4', skinShade='#6a5878',
                    eye={'iris': '#ff2d55', 'irisLo': '#ffb0c0', 'irisDark': '#4a0010', 'w': 0.031, 'h': 0.011, 'slant': 0.006},
                    eyeGlow=2.4, browColor='#130c18', browAngle=0.3, mouth='grin',
                    builders=[kimono_robe, lambda p, c, a: obi(p, c, a, '#7a1f3a'), foe_horns], sign='fist',
                    hands={'R': ['claw', 'fist'], 'L': ['claw', 'fist']})


def foe_horns(p, c, a):
    horn = A.toon(p + 'Horn', '#efe3cf', shade='#9c8f7d')
    out = []
    for sx in (-1, 1):
        h = C.sweep(p + 'Horn%d' % sx, [C.HEAD_C + V((0.06 * sx, 0.0, 0.1)), C.HEAD_C + V((0.11 * sx, 0.02, 0.18)), C.HEAD_C + V((0.12 * sx, 0.06, 0.27))],
                    [0.026, 0.016, 0.002], horn, ring_n=10, rings=10)
        C.outline(h, 0.002)
        out.append((h, 'head'))
    return out


def _nobara():
    """Nobara Kugisaki: rotbrauner Bob, dunkle Uniformjacke, schwarzer Rock, Strumpfhose, braune Stiefel, Hammer."""
    return dict(
        radii={'sh': 0.84, 'el': 0.8, 'wr': 0.82, 'chest': 0.9, 'upchest': 0.88, 'waist': 0.86, 'pelvis': 1.0, 'hi': 0.88, 'kn': 0.82,
               'an': 0.82, 'neck': 0.9},
        hair='#c46a32', hairShade='#7a3a16', hairHi='#ee9a5a', hairStyle='bob', capFront=0.5,
        coat='#1d2234', coatShade='#0b0d16', coatHi='#3a4466', pants='#18161c', pantsShade='#08070a', pantsHi='#2a2832', shoe='#5a3a26', shoeShade='#2a1a10',
        shoeHi='#8a5e40', shoeZ=0.3, skin='#f8e0d0', skinShade='#e2b8a4',
        eye={'iris': '#b0602a', 'irisLo': '#ffc28a', 'irisDark': '#3a1a08', 'lash': '#1a1012', 'w': 0.031, 'h': 0.0145, 'slant': 0.003,
             'irisW': 0.012, 'irisH': 0.015, 'lashW': 0.005},
        eyeGlow=1.2, browColor='#8a4a20', browAngle=0.08, mouth='smile',
        hands={'R': ['grip'], 'L': ['relaxed', 'open', 'point']},
        builders=[nobara_skirt, nobara_hammer], scale=0.92, sign=None)


def nobara_skirt(p, c, a):
    m = A.toon(p + 'SkirtM', '#16141c', shade='#060508', highlight='#3a3646')

    def pleat(t):
        return 1.0 + 0.05 * math.sin(t * 14)
    o = C.loft_z(p + 'Skirt', [(1.06, 0.13, 0.094, 0.0, None), (0.95, 0.16, 0.115, 0.0, pleat), (0.72, 0.2, 0.15, 0.01, pleat)], m, n=48)
    o.modifiers.new('Th', 'SOLIDIFY').thickness = 0.006
    C.outline(o, 0.003)
    return [(o, ['spine', 'pelvis', 'thigh.L', 'thigh.R'])]


def nobara_hammer(p, c, a):
    wood = A.toon(p + 'HammerWood', '#8a5a32', shade='#4a2a12', highlight='#c08a5a')
    steel = A.toon(p + 'HammerHead', '#9aa4b2', shade='#4a5260', highlight='#ffffff')
    hb = Vector(C.BONES['hand.R'][0])
    grip = C.sweep(p + 'HammerGrip', [hb + Vector((0.01, -0.03, 0.02)), hb + Vector((0.01, -0.03, -0.3))], [0.014, 0.014], wood, ring_n=10, rings=4)
    head = C.sweep(p + 'HammerHeadM', [hb + Vector((0.01, -0.09, -0.3)), hb + Vector((0.01, 0.05, -0.3))], [0.03, 0.03], steel, ring_n=12, rings=4)
    for o in (grip, head):
        C.outline(o, 0.002)
    return [(grip, 'hand.R'), (head, 'hand.R')]


def sukuna_finger(name, mat=None, nail=None, length=0.11):
    """Sukunas Finger (nach Vorlage): vertrocknet, rötlich-lila, knorrig mit kleinen Löchern, grauer Nagel,
    wurzelartige Fasern am unteren Ende. Länge entlang +Z, Ursprung in der Mitte."""
    rnd = random.Random(sum(map(ord, name)))
    mat = mat or A.toon('FingerM', '#86465a', shade='#4a1e2e', highlight='#b07888')
    nail = nail or A.toon('FingerNail', '#d4d8e2', shade='#6a6e7c', highlight='#ffffff', steps=(0.3, 0.8))
    hole = A.flat('FingerHole', '#2a0a14')
    L = length
    pts = [Vector((0, 0, -L / 2)), Vector((0.003, 0.002, -L * 0.15)), Vector((0.0, -0.002, L * 0.2)), Vector((-0.002, 0.0, L / 2))]

    def knot(ang, t):
        return 1.0 + 0.12 * math.sin(ang * 3 + t * 20) * math.sin(t * 9) + 0.06 * math.sin(ang * 7 + t * 31)
    body = C.sweep(name, pts, [0.013, 0.012, 0.0105, 0.009], mat, ring_n=16, rings=24, shape=knot)
    parts = [body]
    # großer, gut sichtbarer Nagel auf der Oberseite der Spitze (wie in der Vorlage)
    nb = C.sweep(name + 'Nail', [pts[-1] + Vector((0, -0.007, -0.028)), pts[-1] + Vector((0, -0.0085, -0.01)), pts[-1] + Vector((0, -0.008, 0.007))],
                 [(0.0115, 0.0042), (0.0115, 0.004), (0.0095, 0.003)], nail, ring_n=12, rings=8)
    parts.append(nb)
    for k, (z, a0) in enumerate(((0.02, 0.4), (0.0, 2.2), (-0.015, 4.1))):
        parts.append(C.ellipsoid(name + 'Hole%d' % k, (math.cos(a0) * 0.0115, math.sin(a0) * 0.0115, z), (0.0022, 0.0022, 0.0022), hole, seg=8))
    for k in range(7):   # Fasern / Wurzeln
        a0 = k / 7 * math.tau + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a0), math.sin(a0), -0.6)).normalized()
        b = pts[0] + Vector((math.cos(a0) * 0.009, math.sin(a0) * 0.009, 0.004))
        parts.append(C.sweep(name + 'Root%d' % k, [b, b + d * 0.012 + Vector((0, 0, -0.004)), b + d * 0.026 + Vector((0, 0, 0.004))], [0.0035, 0.0022, 0.0004],
                             mat, ring_n=6, rings=6))
    C._select_only(parts[0])
    for o in parts[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    f = bpy.context.active_object
    f.name = name
    C.outline(f, 0.0012)
    return f


CAST = {'gojo': _gojo, 'sukuna': _sukuna, 'megumi': _megumi, 'mahito': _mahito, 'jogo': _jogo, 'higuruma': _higuruma,
        'hakari': _hakari, 'yuta': _yuta, 'dagon': _dagon, 'naoya': _naoya, 'foe': _foe, 'mahoraga': _mahoraga, 'nobara': _nobara}

AURA_EYES = {}


def build_char(key, prefix, loc=(0, 0, 0), facing=0.0, sign=True):
    cfg = CAST[key]()
    fig = C.build(prefix, cfg, loc, facing)
    hb = fig['arm'].pose.bones['head']
    hb.scale = (cfg.get('headScale', 1.0),) * 3
    hb.keyframe_insert('scale', frame=1)
    if cfg.get('scale'):
        s = cfg['scale']
        fig['arm'].scale = (s, s, s)
    # Mahitos aufgerissener Mund ist nur für die Nahaufnahme seiner Domain gedacht
    for o in bpy.data.objects:
        if o.name.startswith((prefix + 'BigMouth', prefix + 'MouthHand')):
            A.visible(o, 1, False)
    return fig
