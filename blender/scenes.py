"""Domain-Siegesanimationen (alle 10 Domains) – gemeinsame Dramaturgie + eigene Welt & Finisher.

Aufruf:
  blender -b --factory-startup -P blender/scenes.py -- <domain> preview|full <ordner>
Domains: void shrine shadow hands volcano court gamble swords beach frames

Zeitplan (24 fps, 288 Bilder = 12 s):
  S1   1– 42  Totale: die Energie beider Kämpfer prallt aufeinander
  S2  43– 62  Reißschwenk auf den Sieger
  S3  63–110  Fingerzeichen (Untersicht)            → Schrift „領域展開“ (HTML)
  S4 111–138  Augen extrem nah, Augen glühen auf    → Titelkarte (HTML)
  S5 139–180  Domain entfaltet sich, Kamera kreist
  S6 181–246  Finisher (je Domain)
  S7 247–288  Sieger-Kamerafahrt                    → „SIEG!“ (HTML)
"""
import bpy
import bmesh
import sys
import os
import math
import random
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animelib as A  # noqa: E402
import chars as C  # noqa: E402
import cast  # noqa: E402

PI = math.pi
FR = 288
WX, FX = -2.0, 2.0          # Positionen Sieger / Gegner
HEAD_Z = 1.76
rnd = random.Random(11)


# ═════════════════════════ Helfer ═════════════════════════
def objs_of(prefix):
    return [o for o in bpy.data.objects if o.name.startswith(prefix)]


def show_from(objs, f_on, f_off=None):
    for o in objs:
        A.visible(o, 1, False)
        A.visible(o, f_on, True)
        if f_off:
            A.visible(o, f_off, False)


def hide_fig(prefix, frame):
    for o in objs_of(prefix):
        if o.type in ('MESH', 'ARMATURE', 'CURVE', 'FONT'):
            A.visible(o, 1, True)
            A.visible(o, frame, False)


def mesh_obj(name, bm, mat, outline=0.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    if outline:
        A.add_outline(o, outline)
    return o


def blob(name, size, mat, seed, outline=0.0):
    """Unregelmäßiger, flacher Klecks (wie gemalte Farbflecken)."""
    r = random.Random(seed)
    bm = bmesh.new()
    n = 48
    ph = [r.uniform(0, 6.28) for _ in range(4)]
    amp = [r.uniform(0.08, 0.25) for _ in range(4)]
    verts = []
    for i in range(n):
        a = i / n * math.tau
        k = 1 + sum(amp[j] * math.sin((j + 2) * a + ph[j]) for j in range(4))
        verts.append(bm.verts.new((math.cos(a) * size * k, math.sin(a) * size * k * r.uniform(0.6, 0.9), 0)))
    bm.faces.new(verts)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    o = mesh_obj(name, bm, mat, outline)
    return o


def text_obj(name, body, size, mat, extrude=0.05):
    cu = bpy.data.curves.new(name, 'FONT')
    for fp in ('C:/Windows/Fonts/YuGothB.ttc', 'C:/Windows/Fonts/msgothic.ttc', 'C:/Windows/Fonts/meiryob.ttc'):
        if os.path.exists(fp):
            cu.font = bpy.data.fonts.load(fp, check_existing=True)
            break
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    cu.materials.append(mat)
    return o


def sky(name, top, bottom, cloud=None, cloud_scale=2.0, strength=1.0, radius=60):
    """Himmelskugel (von innen sichtbar): Verlauf + optionale Wolken."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*A._lin(bottom), 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*A._lin(top), 1)
    mapr = nt.nodes.new('ShaderNodeMapRange')
    mapr.inputs['From Min'].default_value = -1
    mapr.inputs['From Max'].default_value = 1
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
    nt.links.new(mapr.outputs['Result'], ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if cloud:
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = cloud_scale
        noise.inputs['Detail'].default_value = 8
        cr = nt.nodes.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].position = 0.5
        cr.color_ramp.elements[0].color = (0, 0, 0, 1)
        cr.color_ramp.elements[1].position = 0.78
        cr.color_ramp.elements[1].color = (*A._lin(cloud), 1)
        add = nt.nodes.new('ShaderNodeMix')
        add.data_type = 'RGBA'
        add.blend_type = 'ADD'
        add.inputs['Factor'].default_value = 1
        nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
        nt.links.new(noise.outputs['Fac'], cr.inputs['Fac'])
        nt.links.new(col, add.inputs[6])
        nt.links.new(cr.outputs['Color'], add.inputs[7])
        col = add.outputs[2]
    nt.links.new(col, em.inputs['Color'])
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    s = A.sphere(name, (0, 0, 0), radius, m, segments=64, outline=0)
    return s


def flat_light(name, color, strength=1.0):
    return A.glow(name, color, strength)


def shards(prefix, center, colors, f0, n=40, spread=2.5, up=1.0, size=0.08, seed=3):
    """Gegner zerfällt in Splitter (stilisiert, kein Blut)."""
    r = random.Random(seed)
    mats = [A.toon(prefix + 'Sh%d' % i, c) for i, c in enumerate(colors)]
    out = []
    for i in range(n):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1)
        for v in bm.verts:
            v.co *= r.uniform(0.6, 1.3)
        o = mesh_obj(prefix + 'Shard%d' % i, bm, mats[i % len(mats)], outline=0.01)
        s = size * r.uniform(0.6, 1.6)
        p0 = Vector(center) + Vector((r.uniform(-0.2, 0.2), r.uniform(-0.15, 0.15), r.uniform(0.1, 1.8)))
        d = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.2, 1) * up)).normalized() * r.uniform(0.5, spread)
        A.key(o, 1, loc=p0, scale=s)
        A.key(o, f0, loc=p0, scale=s, rot=(0, 0, 0))
        A.key(o, f0 + 26, loc=p0 + d + Vector((0, 0, -0.4)), scale=s * 0.2, rot=(r.uniform(-6, 6), r.uniform(-6, 6), r.uniform(-6, 6)))
        show_from([o], f0, f0 + 27)
        out.append(o)
    return out


def slash_line(name, f, center, angle, length=3.0, color='#ffffff', tilt=0.0, life=4):
    """Ein Schnitt: dünne leuchtende Fläche, die in 'life' Bildern aufblitzt."""
    o = A.cube(name, center, (length / 2, 0.006, 0.012), A.glow('SlashMat_' + color, color, 14), rot=(tilt, angle, 0))
    A.key(o, 1, scale=(0.001, 0.006, 0.012))
    A.key(o, f, scale=(0.001, 0.006, 0.012))
    A.key(o, f + 1, scale=(length / 2, 0.006, 0.02))
    A.key(o, f + life, scale=(length / 2, 0.006, 0.001))
    show_from([o], f, f + life + 1)
    return o


def sparks_rise(name, center, color, n, f0, f1, radius=0.6, height=2.6, size=0.006, parent=None):
    mat = A.glow(name + 'M', color, 6)
    for i in range(n):
        p = A.cube(name + '%d' % i, (0, 0, 0), (size, size, size * 5), mat)
        if parent:
            p.parent = parent
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(radius * 0.5, radius)
        c = Vector(center)
        off = rnd.randint(0, 40)
        for f in range(f0 - off, f1, 40):
            A.key(p, max(f, 1), loc=c + Vector((math.cos(a) * r, math.sin(a) * r, 0.05)))
            A.key(p, max(f + 39, 1), loc=c + Vector((math.cos(a) * r * 0.8, math.sin(a) * r * 0.8, height)))
        A.set_interp(p, 'LINEAR')


def eye_glow(prefix, keys):
    m = bpy.data.materials.get(prefix + 'Iris')
    if not m:
        return
    em = m.node_tree.nodes.get('Emission')
    for f, v in keys:
        em.inputs['Strength'].default_value = v
        em.inputs['Strength'].keyframe_insert('default_value', frame=f)


# ═════════════════════════ Gemeinsamer Ablauf ═════════════════════════
def common(dom):
    """Arena, Figuren, Clash, Sieger-Posen, Kamera, Domain-Ausbreitung."""
    A.reset_scene()
    A.setup_render(FR, samples=12)
    A.add_bloom(size=7, threshold=0.8, mix=0.45)
    A.sun(2.2, rot=(math.radians(52), math.radians(12), math.radians(-38)))
    ctx = {'dom': dom}
    W = cast.build_char(dom['char'], 'Win', loc=(WX, 0, 0), facing=PI / 2)
    Fo = cast.build_char('foe', 'Foe', loc=(FX, 0, 0), facing=-PI / 2, sign=False)
    ctx['W'], ctx['F'] = W, Fo
    # Grundhaltung + leichtes Atmen
    for fig, seed in ((W, 1), (Fo, 2)):
        for f in range(1, FR + 1, 24):
            C.pose(fig, f, chest=(2 + (f // 24) % 2 * 2, 0, 0), **{'upper.L': (0, 0, -10), 'upper.R': (0, 0, 10),
                                                                     'fore.L': (-12, 0, 0), 'fore.R': (-12, 0, 0)})
    # Kampfhaltung des Gegners
    C.pose(Fo, 1, **{'upper.L': (-30, 0, -18), 'upper.R': (-30, 0, 18), 'fore.L': (-70, 0, 0), 'fore.R': (-70, 0, 0), 'spine': (8, 0, 0)})
    # Arena
    ground = A.cube('ArenaGround', (0, 0, -0.05), (30, 30, 0.05), A.toon('ArenaG', dom.get('arena', '#141a28'), shade='#06080f'))
    ctx['ground'] = ground
    # Clash (S1)
    ca = A.glow('ClashW', dom['aura'], 4, alpha=0.4)
    cf = A.glow('ClashF', '#ff2d55', 4, alpha=0.4)
    white = A.glow('ClashCore', '#ffffff', 10)
    cw = A.sphere('ClashWs', (-0.55, 0, 1.3), 0.55, ca, outline=0)
    cfo = A.sphere('ClashFs', (0.55, 0, 1.3), 0.55, cf, outline=0)
    core = A.sphere('ClashCoreS', (0, 0, 1.3), (0.1, 0.55, 1.0), white, outline=0)
    for f in range(1, 46, 3):
        k = 1 + 0.15 * math.sin(f * 0.9)
        A.key(cw, f, loc=(-0.55 + 0.07 * math.sin(f * 0.7), 0, 1.3), scale=0.55 * k)
        A.key(cfo, f, loc=(0.55 - 0.07 * math.sin(f * 0.7), 0, 1.3), scale=0.55 * (2 - k))
        A.key(core, f, scale=(0.1 * (1 + 0.6 * math.sin(f * 1.4)), 0.55, 1.0))
    clash = [cw, cfo, core]
    for i in range(40):
        sp = A.sphere('ClSpark%d' % i, (0, 0, 1.3), 0.022, white, segments=8, outline=0)
        for f in range(1, 46, 3):
            A.key(sp, f, loc=(rnd.uniform(-0.3, 0.3), rnd.uniform(-1.0, 1.0), 1.3 + rnd.uniform(-1.0, 1.0)))
        clash.append(sp)
    show_from(clash, 1, 43)
    # Aura des Siegers (aufsteigende Funken) + Randlicht
    sparks_rise('WinAura', (0, 0, 0), dom['aura'], 26, 1, FR + 40, parent=W['arm'])
    rim = bpy.data.lights.new('WinRim', 'POINT')
    rim.energy = 350
    rim.color = tuple(A._lin(dom['aura']))
    ro = bpy.data.objects.new('WinRim', rim)
    bpy.context.collection.objects.link(ro)
    ro.parent = W['arm']
    ro.location = (0, 0.9, 2.1)
    # Fingerzeichen (S3) und zurück
    sign = dom.get('signPose', {'upper.R': (-72, 0, 28), 'fore.R': (-112, 0, 0), 'head': (6, 0, 0)})
    rest = {'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0), 'head': (0, 0, 0)}
    C.pose(W, 62, **rest)
    C.pose(W, 70, **sign)
    C.pose(W, 176, **sign)
    if dom.get('twoHands'):
        C.pose(W, 62, **{'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0)})
        C.pose(W, 70, **{'upper.L': (-72, 0, -28), 'fore.L': (-112, 0, 0)})
    eye_glow('Win', [(1, 2.0), (112, 2.0), (124, 22), (138, 10), (FR, 6)])
    # Domain breitet sich aus (S5): Himmelskugel wächst vom Sieger aus
    ctx['domain_sky'] = None
    # Kamera
    cam, tgt = A.camera(lens=28)
    ctx['cam'], ctx['tgt'] = cam, tgt
    flash = A.cube('Flash', (0, 0, -0.6), (2, 2, 0.01), A.glow('FlashMat', '#ffffff', 2.5), outline=0)
    flash.parent = cam
    ctx['flash'] = flash
    A.visible(flash, 1, False)
    return ctx


def flash_at(ctx, frames):
    for f in frames:
        A.visible(ctx['flash'], f, True)
        A.visible(ctx['flash'], f + 2, False)


def expand(ctx, sky_obj, radius=60, f0=139, f1=158, env=()):
    """Domain-Welt ausbreiten: Himmelskugel wächst vom Sieger, Welt erscheint, Arena verschwindet."""
    sky_obj.location = (WX, 0, 1.0)
    A.key(sky_obj, 1, scale=0.001)
    A.key(sky_obj, f0, scale=0.001)
    A.key(sky_obj, f1, scale=radius)
    A.key(sky_obj, f1 + 1, loc=(0, 0, 0))
    A.key(sky_obj, f1, loc=(WX, 0, 1.0))
    show_from([sky_obj], f0)
    show_from(list(env), 151)
    A.visible(ctx['ground'], 1, True)
    A.visible(ctx['ground'], 151, False)
    flash_at(ctx, [151])


def camera_track(ctx, fin_shots=None):
    """Kamerafahrten aller Einstellungen. fin_shots ersetzt die Finisher-Kamera (181–246)."""
    cam, tgt = ctx['cam'], ctx['tgt']
    ex = WX + ctx['dom'].get('eyeFront', 0.13)  # Augen (der Sieger schaut nach +X)
    ez = ctx['dom'].get('eyeZ', HEAD_Z)
    K = [
        (1, (0, -9.5, 2.2), (0, 0, 1.3), 28), (42, (0, -7.6, 1.9), (0, 0, 1.3), 28),
        (48, (WX + 0.85, -2.0, 1.75), (WX, 0, 1.65), 50), (62, (WX + 0.75, -1.85, 1.72), (WX, 0, 1.68), 52),
        (63, (WX + 0.9, -0.95, 1.4), (WX + 0.15, 0, 1.75), 38), (110, (WX + 0.8, -0.8, 1.48), (WX + 0.15, 0, 1.78), 44),
        (111, (ex + 0.9, -0.05, ez + 0.02), (ex, 0, ez + 0.01), 85), (138, (ex + 0.62, -0.03, ez + 0.02), (ex, 0, ez + 0.01), 100),
        (139, (1.2, -6.0, 3.0), (WX + 0.5, 0, 1.4), 22), (180, (4.5, -6.3, 3.6), (0, 0, 1.3), 24),
    ]
    K += fin_shots or [
        (181, (FX - 1.2, -2.6, 1.9), (FX, 0, 1.6), 38), (217, (FX - 1.0, -2.3, 1.95), (FX, 0, 1.65), 42),
        (218, (0.2, -4.2, 1.7), (0.6, 0, 1.4), 30), (246, (0.6, -4.6, 2.1), (0.8, 0, 1.5), 30),
    ]
    wx = ctx.get('win_end_x', WX)
    K += [(247, (wx + 1.6, -2.2, 1.75), (wx, 0, 1.6), 40), (288, (wx + 1.0, 2.0, 2.1), (wx, 0, 1.65), 40)]
    for f, pos, look, lens in K:
        A.cam_key(cam, tgt, f, pos, look, lens)
    cuts = {42, 62, 110, 138, 180, 217, 246} | set(ctx.get('extra_cuts', ()))
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                fr = int(round(kp.co.x))
                kp.interpolation = 'LINEAR' if fr == 42 else ('CONSTANT' if fr in cuts else 'BEZIER')


# ═════════════════════════ Domains ═════════════════════════
def d_void():
    dom = {'char': 'gojo', 'aura': '#7fc4ff', 'arena': '#121829'}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    # Himmel: dunkelblauer Nebel
    s = sky('VoidSky', '#0e1a3a', '#03050c', cloud='#3a5a9a', cloud_scale=1.4, strength=1.0)
    # Schwarzes Loch mit ausfransender, weiß-blauer Korona (hinter den Kämpfern)
    bh_c = Vector((0, 11, 3.2))
    hole = A.sphere('BlackHole', bh_c, 2.6, A.glow('Hole', '#000000', 0.0), segments=48, outline=0)
    cor = bpy.data.materials.new('Corona')
    cor.use_nodes = True
    nt = cor.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    fres = nt.nodes.new('ShaderNodeLayerWeight')
    fres.inputs['Blend'].default_value = 0.35
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 9
    noise.inputs['Detail'].default_value = 10
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.12
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (*A._lin('#e8f2ff'), 1)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 3.0
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fres.outputs['Facing'], mul.inputs[0])
    nt.links.new(noise.outputs['Fac'], mul.inputs[1])
    nt.links.new(mul.outputs[0], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(ramp.outputs['Color'], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    cor.surface_render_method = 'BLENDED'
    corona = A.sphere('Corona', bh_c, 3.3, cor, segments=48, outline=0)
    A.key(corona, 139, rot=(0, 0, 0))
    A.key(corona, FR, rot=(0.3, 0.2, 1.2))
    # Weiße Klecks-Wolken überall im Raum
    wmat = A.glow('Blob', '#c9d1e2', 0.85)
    blobs = []
    for i in range(70):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-0.2, 1), rnd.uniform(-0.4, 0.8))).normalized() * rnd.uniform(7, 18)
        b = blob('Blob%d' % i, rnd.uniform(0.3, 1.5), wmat, i)
        b.location = Vector((0, 2, 2)) + d
        r0 = (rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6))
        A.key(b, 139, rot=r0)
        A.key(b, FR, rot=(r0[0] + rnd.uniform(-0.4, 0.4), r0[1] + rnd.uniform(-0.4, 0.4), r0[2] + rnd.uniform(-0.6, 0.6)))
        blobs.append(b)
    expand(ctx, s, env=[hole, corona] + blobs)
    # ── Finisher: Informationsflut, leuchtender Punkt, Teleport, Kopf fliegt ──
    info_mat = A.glow('Info', '#cfe8ff', 7)
    head = Vector((FX, 0, HEAD_Z))
    infos = []
    for i in range(70):
        o = A.cube('Info%d' % i, (0, 0, 0), (0.025, 0.004, 0.04), info_mat)
        a, b = rnd.uniform(0, math.tau), rnd.uniform(-0.8, 0.8)
        r = rnd.uniform(2.5, 5.5)
        st = head + Vector((math.cos(a) * r, math.sin(a) * r, b * 2.5))
        f0 = 181 + int(i * 0.45)
        A.key(o, 1, loc=st)
        A.key(o, f0, loc=st, rot=(rnd.random() * 3, rnd.random() * 3, rnd.random() * 3))
        A.key(o, f0 + 12, loc=head, rot=(rnd.random() * 9, rnd.random() * 9, rnd.random() * 9))
        show_from([o], f0, f0 + 13)
        infos.append(o)
    for f in range(185, 228, 2):   # Gegner erstarrt (zittert)
        A.key(Fo['arm'], f, loc=(FX + rnd.uniform(-0.012, 0.012), rnd.uniform(-0.012, 0.012), 0))
    pt = A.sphere('VoidPoint', (FX + 0.55, 0, HEAD_Z + 0.15), 0.06, A.glow('Pt', '#ffffff', 7), outline=0)
    A.key(pt, 1, scale=0.0001)
    A.key(pt, 199, scale=0.0001)
    A.key(pt, 208, scale=0.06)
    for f in range(210, 246, 3):
        A.key(pt, f, scale=0.06 * (0.9 + 0.25 * math.sin(f)))
    A.key(pt, 247, scale=0.0001)
    # Teleport vor den Gegner, Griff zum Kopf
    C.place(W, 1, (WX, 0, 0))
    C.place(W, 218, (WX, 0, 0))
    W['arm'].location = (FX - 0.62, 0, 0)
    W['arm'].keyframe_insert('location', frame=219)
    A.set_interp(W['arm'], 'CONSTANT')
    C.pose(W, 218, **{'upper.R': (-72, 0, 28), 'fore.R': (-112, 0, 0)})
    C.pose(W, 223, **{'upper.R': (-95, 0, 8), 'fore.R': (-20, 0, 0)})
    flash_at(ctx, [226])
    # Kopf fliegt (stilisiert, ohne Blut), Körper kippt
    C.move(Fo, 227, 'head', (0, 0, 0))
    C.pose(Fo, 227, head=(0, 0, 0))
    C.move(Fo, 236, 'head', (0, 0.9, 0.35))
    C.pose(Fo, 236, head=(140, 60, 90))
    C.move(Fo, 246, 'head', (0, 1.6, 0.9))
    C.pose(Fo, 246, head=(320, 150, 200))
    C.pose(Fo, 229, spine=(8, 0, 0), pelvis=(0, 0, 0))
    C.pose(Fo, 246, spine=(-25, 0, 0), pelvis=(-60, 0, 0))
    hide_fig('Foe', 252)
    C.pose(W, 250, **{'upper.R': (-95, 0, 8), 'fore.R': (-20, 0, 0)})
    C.pose(W, 262, **{'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0)})
    ctx['win_end_x'] = FX - 0.62
    camera_track(ctx, [
        (181, (FX - 1.0, -2.5, 1.9), (FX, 0, 1.65), 40), (217, (FX - 0.85, -2.2, 1.95), (FX, 0, 1.7), 44),
        (218, (FX - 0.2, -3.2, 1.6), (FX - 0.3, 0, 1.6), 32), (246, (FX + 0.3, -3.6, 2.3), (FX, 0.5, 2.3), 30),
    ])
    return ctx


def skull(name, loc, mat, horn, scale=0.3, rot=0.0):
    parts = [A.sphere(name, loc, (scale, scale * 0.9, scale * 0.8), mat, segments=16, outline=0.01)]
    L = Vector(loc)
    for sx in (-1, 1):
        parts.append(A.cone(name + 'H%d' % sx, L + Vector((sx * scale * 1.0, 0, scale * 0.5)), scale * 0.25, scale * 1.6, horn,
                            rot=(0, sx * 1.1, 0), outline=0.008))
        parts.append(A.sphere(name + 'E%d' % sx, L + Vector((sx * scale * 0.35, -scale * 0.8, scale * 0.1)), scale * 0.2, A.toon('SkullHole', '#120404'), segments=10, outline=0))
    for p in parts:
        p.rotation_euler.z += rot
    return parts


def d_shrine():
    dom = {'char': 'sukuna', 'aura': '#ff4b4b', 'arena': '#1a0d0d',
           'signPose': {'upper.R': (-70, 0, 30), 'fore.R': (-110, 0, 0), 'upper.L': (-70, 0, -30), 'fore.L': (-110, 0, 0), 'head': (8, 0, 0)},
           'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('ShrineSky', '#3b0606', '#0a0101', cloud='#5a0f0f', cloud_scale=2.2, strength=1.0)
    env = []
    water = A.cube('BloodWater', (0, 0, -0.03), (40, 40, 0.02), A.toon('BloodW', '#2a0707', shade='#120202'))
    env.append(water)
    moon = A.sphere('RedMoon', (14, 30, 16), 3.5, A.glow('MoonR', '#ff5a3a', 3), outline=0)
    env.append(moon)
    # Der Schrein (hinter Sukuna): Schädelberg, Plattform, Säulen, geschwungene Dächer, Maul mit Zähnen
    base = Vector((-4.5, 7.0, 0))
    bone = A.toon('Bone', '#e9e0cf', shade='#9a8f7c')
    horn = A.toon('HornS', '#2a1f1a')
    for i in range(46):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(0, 3.6)
        z = max(0.1, 1.6 - r * 0.45) * rnd.uniform(0.3, 1.0)
        env += skull('Skull%d' % i, base + Vector((math.cos(a) * r, math.sin(a) * r * 0.7, z)), bone, horn, scale=rnd.uniform(0.18, 0.32), rot=rnd.uniform(-0.6, 0.6))
    wood = A.toon('ShrineWood', '#3a0d0d', shade='#170404')
    dark = A.toon('ShrineDark', '#160606')
    env.append(A.cube('Platform', base + Vector((0, 0, 1.7)), (2.2, 1.6, 0.12), wood, outline=0.02))
    for x in (-1.7, 1.7):
        for y in (-1.2, 1.2):
            env.append(A.cube('Pillar', base + Vector((x, y, 3.0)), (0.12, 0.12, 1.2), wood, outline=0.015))
    env.append(A.cube('Walls', base + Vector((0, 0.2, 3.0)), (1.5, 1.0, 1.15), dark, outline=0.015))
    # Maul in der Front: Kiefer mit Zähnen
    mouth = A.cube('Mouth', base + Vector((0, -0.85, 2.7)), (1.1, 0.05, 0.42), A.glow('MouthIn', '#7a0b0b', 1.5))
    env.append(mouth)
    teeth = A.toon('Teeth', '#f4ecdc')
    for i in range(10):
        x = -1.0 + i * 0.22
        env.append(A.cone('ToothU%d' % i, base + Vector((x, -0.9, 3.05)), 0.07, 0.3, teeth, rot=(PI, 0, 0), outline=0.006))
        env.append(A.cone('ToothD%d' % i, base + Vector((x + 0.1, -0.9, 2.35)), 0.07, 0.3, teeth, outline=0.006))
    # Zwei geschwungene Dächer (Pagode)
    roof = A.toon('Roof', '#1c0707', shade='#0a0202')
    for lvl, (z, w) in enumerate(((4.35, 2.6), (5.3, 1.9))):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=w, radius2=0.25, depth=0.8)
        for v in bm.verts:   # Ecken nach oben schwingen
            if v.co.z < 0:
                d = math.hypot(v.co.x, v.co.y)
                v.co.z += 0.25 * (d / w) ** 3
        r = mesh_obj('Roof%d' % lvl, bm, roof, outline=0.02)
        r.location = base + Vector((0, 0, z))
        r.rotation_euler = (0, 0, PI / 4)
        r.scale = (1.0, 0.75, 1.0)
        env.append(r)
    env.append(A.cone('Spire', base + Vector((0, 0, 6.0)), 0.12, 0.8, A.toon('Spire', '#c9a24a'), outline=0.006))
    # roter Nebel unten
    for i in range(18):
        b = blob('Mist%d' % i, rnd.uniform(1.5, 3.5), A.glow('MistR', '#5c0a0a', 0.6, alpha=0.5), 100 + i)
        b.location = (rnd.uniform(-12, 12), rnd.uniform(-2, 14), rnd.uniform(0.1, 0.6))
        env.append(b)
    expand(ctx, s, env=env)
    # ── Finisher: Schnitt-Gewitter (Dismantle & Cleave), Gegner zerfällt in Splitter ──
    hc = Vector((FX, 0, 1.2))
    for i in range(60):
        f = 184 + int(i * 0.55)
        slash_line('Cut%d' % i, f, hc + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.6, 0.2), rnd.uniform(-0.8, 0.9))),
                   rnd.uniform(-1.4, 1.4), length=rnd.uniform(1.4, 3.2), color='#ffffff' if i % 3 else '#ff6b6b', tilt=rnd.uniform(-0.5, 0.5))
    for f in range(184, 220, 2):  # Gegner zuckt unter den Treffern
        C.pose(Fo, f, spine=(rnd.uniform(-10, 14), rnd.uniform(-8, 8), 0), head=(rnd.uniform(-15, 15), 0, rnd.uniform(-15, 15)))
    flash_at(ctx, [218])
    hide_fig('Foe', 219)
    shards('FoeBits', (FX, 0, 0), ['#2a1236', '#120b16', '#9a8aa8', '#7a1f3a'], 219, n=70, spread=2.8)
    # zwei große Kreuz-Schnitte zum Schluss
    slash_line('BigCut1', 216, hc + Vector((0, -0.4, 0.3)), 0.8, length=5.0, color='#ffffff', life=8)
    slash_line('BigCut2', 217, hc + Vector((0, -0.4, 0.3)), -0.8, length=5.0, color='#ff8080', life=8)
    # Sukuna: Hand nach vorn (Schnitte auslösen), dann gelassen
    C.pose(W, 180, **{'upper.R': (-80, 0, 20), 'fore.R': (-30, 0, 0), 'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0)})
    C.pose(W, 240, **{'upper.R': (-80, 0, 20), 'fore.R': (-30, 0, 0)})
    C.pose(W, 256, **{'upper.R': (0, 0, 10), 'fore.R': (-12, 0, 0)})
    camera_track(ctx)
    return ctx


def dog(name, loc, rot_z, mat, eye):
    parts = [A.sphere(name + 'B', (0, 0, 0.45), (0.22, 0.45, 0.22), mat, outline=0.01),
             A.sphere(name + 'H', (0, -0.48, 0.65), (0.15, 0.2, 0.14), mat, outline=0.01),
             A.cone(name + 'Sn', (0, -0.7, 0.62), 0.07, 0.2, mat, rot=(PI / 2, 0, 0), outline=0.008)]
    for sx in (-1, 1):
        parts.append(A.cone(name + 'E%d' % sx, (0.08 * sx, -0.45, 0.82), 0.05, 0.16, mat, outline=0.006))
        parts.append(A.sphere(name + 'Y%d' % sx, (0.07 * sx, -0.62, 0.7), 0.025, eye, segments=10, outline=0))
        for fy in (-0.3, 0.3):
            parts.append(A.cylinder(name + 'L%d%.1f' % (sx, fy), (0.12 * sx, fy, 0.18), 0.05, 0.36, mat, outline=0.008))
    root = A.empty(name, loc)
    root.rotation_euler = (0, 0, rot_z)
    for p in parts:
        p.parent = root
    return root, parts


def d_shadow():
    dom = {'char': 'megumi', 'aura': '#8a9ac0', 'arena': '#0e121c',
           'signPose': {'upper.R': (-70, 0, 25), 'fore.R': (-115, 0, 0), 'upper.L': (-70, 0, -25), 'fore.L': (-115, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('ShadowSky', '#2a3a5e', '#05070d', cloud='#3a4d78', cloud_scale=1.8, strength=1.6)
    moon = A.sphere('ShadowMoon', (8, 30, 14), 3.0, A.glow('ShMoon', '#dfe8ff', 3), outline=0)
    env = [moon, A.cube('ShadowSea', (0, 0, -0.02), (40, 40, 0.02), A.toon('SeaB', '#0a0e18', shade='#020306'))]
    fill = bpy.data.lights.new('ShFill', 'SUN')
    fill.energy = 2.0
    fill.color = (0.6, 0.7, 1.0)
    fill.use_shadow = False
    fo = bpy.data.objects.new('ShFill', fill)
    bpy.context.collection.objects.link(fo)
    fo.rotation_euler = (0.9, 0.0, 2.6)
    ring = A.glow('Ripple', '#3b4a6b', 2.0)
    for i in range(10):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.012, location=(rnd.uniform(-8, 8), rnd.uniform(-4, 10), 0.01))
        t = bpy.context.active_object
        A.set_mat(t, ring)
        st = 139 + rnd.randint(0, 40)
        for f in range(st, FR, 40):
            A.key(t, f, scale=0.1)
            A.key(t, f + 39, scale=3.0)
        env.append(t)
    # Schattenhunde tauchen auf
    dmat = A.toon('DogM', '#06070b', shade='#000000')
    deye = A.glow('DogEye', '#ffffff', 6)
    dogs = []
    for i, (x, y) in enumerate(((WX - 1.2, 1.2), (WX - 0.4, 2.0))):
        root, parts = dog('Dog%d' % i, (x, y, -1.2), -PI / 2 + 0.3, dmat, deye)
        A.key(root, 150, loc=(x, y, -1.2))
        A.key(root, 170, loc=(x, y, 0))
        dogs.append(root)
        env += parts
    # Schatten-Ranken
    tendrils = []
    tm = A.toon('Tendril', '#030408')
    for i in range(14):
        a = i / 14 * math.tau
        x, y = FX + math.cos(a) * 0.9, math.sin(a) * 0.9
        o = C.strand('Tendril%d' % i, [(x, y, 0), (x - math.cos(a) * 0.3, y - math.sin(a) * 0.3, 1.0), (FX + math.cos(a) * 0.15, math.sin(a) * 0.15, 1.7)], 0.09, tm)
        A.key(o, 1, scale=(1, 1, 0.001))
        A.key(o, 186 + i, scale=(1, 1, 0.001))
        A.key(o, 200 + i, scale=(1, 1, 1))
        tendrils.append(o)
    expand(ctx, s, env=env + tendrils)
    # Hunde springen auf den Gegner
    for i, root in enumerate(dogs):
        x, y = root.location.x, root.location.y
        A.key(root, 205 + i * 4, loc=(x, y, 0))
        A.key(root, 214 + i * 4, loc=(FX - 0.6, 0.3 - i * 0.6, 1.2))
        A.key(root, 222 + i * 4, loc=(FX - 0.2, 0.2 - i * 0.4, 0.4))
    # Gegner versinkt im Schatten
    C.place(Fo, 1, (FX, 0, 0))
    C.place(Fo, 214, (FX, 0, 0))
    C.place(Fo, 244, (FX, 0, -2.2))
    C.pose(Fo, 214, **{'upper.L': (-30, 0, -18), 'upper.R': (-30, 0, 18)})
    C.pose(Fo, 230, **{'upper.L': (-170, 0, -20), 'upper.R': (-170, 0, 20)})
    hide_fig('Foe', 246)
    camera_track(ctx)
    return ctx


def big_hand(name, loc, rot, mat, s=1.0):
    root = A.empty(name, loc)
    root.rotation_euler = rot
    parts = [A.sphere(name + 'P', (0, 0, 0), (0.45 * s, 0.14 * s, 0.5 * s), mat, outline=0.015)]
    for i in range(4):
        x = (-0.3 + i * 0.2) * s
        parts.append(A.cylinder(name + 'F%d' % i, (x, 0, 0.75 * s), 0.08 * s, 0.6 * s, mat, outline=0.012))
    parts.append(A.cylinder(name + 'T', (0.45 * s, 0, 0.15 * s), 0.09 * s, 0.45 * s, mat, rot=(0, 0.9, 0), outline=0.012))
    parts.append(A.cylinder(name + 'W', (0, 0, -0.9 * s), 0.25 * s, 1.2 * s, mat, outline=0.015))
    for p in parts:
        p.parent = root
    return root, parts


def d_hands():
    dom = {'char': 'mahito', 'aura': '#5eead4', 'arena': '#0c1a18',
           'signPose': {'upper.R': (-70, 0, 20), 'fore.R': (-100, 0, 0), 'upper.L': (-70, 0, -20), 'fore.L': (-100, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('HandsSky', '#0e2a26', '#020807', cloud='#1d4a44', cloud_scale=2.5)
    env = [A.cube('HandsFloor', (0, 0, -0.02), (40, 40, 0.02), A.toon('HF', '#0a1614'))]
    hm = A.toon('BigHandM', '#cfd8d2', shade='#7e918a')
    for i in range(34):
        a = i / 34 * math.tau
        el = rnd.uniform(-0.1, 0.9)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        p = Vector((0, 2, 0)) + d * 9
        root, parts = big_hand('BH%d' % i, p, (0, 0, 0), hm, s=rnd.uniform(1.6, 2.6))
        root.rotation_mode = 'QUATERNION'
        root.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(-d)
        env += parts
    expand(ctx, s, env=env)
    # Mahito tritt heran und berührt die Seele
    C.place(W, 1, (WX, 0, 0))
    C.place(W, 190, (WX, 0, 0))
    C.place(W, 202, (FX - 0.7, 0, 0))
    C.pose(W, 200, **{'upper.R': (-72, 0, 28), 'fore.R': (-112, 0, 0)})
    C.pose(W, 206, **{'upper.R': (-90, 0, 5), 'fore.R': (-10, 0, 0)})
    # Seelen-Verformung: Knochen wild skalieren und verdrehen, dann schrumpfen
    arm = Fo['arm']

    def sc(f, bone, v):
        pb = arm.pose.bones[bone]
        pb.scale = v
        pb.keyframe_insert('scale', frame=f)
    for b in ('chest', 'head', 'upper.L', 'upper.R', 'thigh.L'):
        sc(206, b, (1, 1, 1))
    sc(216, 'head', (1.8, 0.7, 1.5))
    sc(216, 'upper.L', (1, 2.2, 1))
    sc(216, 'chest', (1.5, 0.8, 1.3))
    sc(226, 'upper.R', (1, 2.6, 1))
    sc(226, 'head', (0.6, 1.9, 0.7))
    C.pose(Fo, 216, spine=(30, 20, 40), head=(40, -30, 60))
    C.pose(Fo, 226, spine=(-20, -30, -50), head=(-60, 40, -30))
    A.key(arm, 228, scale=1.0)
    A.key(arm, 244, scale=0.05)
    hide_fig('Foe', 245)
    ctx['win_end_x'] = FX - 0.7
    camera_track(ctx)
    return ctx


def d_volcano():
    dom = {'char': 'jogo', 'aura': '#ff8a2a', 'arena': '#1c0d06',
           'signPose': {'upper.R': (-80, 0, 15), 'fore.R': (-60, 0, 0), 'head': (0, 0, 0)}}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('VolcSky', '#3a1206', '#0a0301', cloud='#6a2508', cloud_scale=2.0)
    env = []
    lava = bpy.data.materials.new('LavaSea')
    lava.use_nodes = True
    nt = lava.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 1.5
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*A._lin('#ffd27a'), 1)
    ramp.color_ramp.elements[1].position = 0.08
    ramp.color_ramp.elements[1].color = (*A._lin('#2a0c04'), 1)
    nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    em.inputs['Strength'].default_value = 3
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    env.append(A.cube('Lava', (0, 0, -0.03), (40, 40, 0.02), lava))
    rock = A.toon('VolcRock', '#2a1a12', shade='#100804')
    for i in range(16):   # Kraterwände
        a = i / 16 * math.tau
        env.append(A.cone('Wall%d' % i, (math.cos(a) * 16, math.sin(a) * 16 + 2, 4), rnd.uniform(3, 5), 12, rock, verts=6, outline=0.03))
    for i in range(6):    # Felsinseln
        env.append(A.cone('Isle%d' % i, (rnd.uniform(-10, 10), rnd.uniform(3, 12), 0.3), rnd.uniform(0.8, 1.6), 1.0, rock, r2=0.4, verts=7, outline=0.02))
    sparks_rise('Ember', (0, 3, 0), '#ffb35c', 50, 139, FR + 40, radius=10, height=8, size=0.02)
    expand(ctx, s, env=env)
    # Eruptionen unter dem Gegner, Gegner glüht und zerfällt zu Asche
    em_mat = A.glow('Erupt', '#ffb347', 8)
    for i in range(7):
        a = i / 7 * math.tau
        p = (FX + math.cos(a) * 0.5, math.sin(a) * 0.5, 0)
        c = A.cylinder('Erupt%d' % i, p, 0.22, 1.0, em_mat, outline=0)
        A.key(c, 1, scale=(1, 1, 0.001), loc=p)
        A.key(c, 196 + i * 2, scale=(1, 1, 0.001), loc=p)
        A.key(c, 206 + i * 2, scale=(1, 1, 4.0), loc=(p[0], p[1], 2.0))
        A.key(c, 228, scale=(0.3, 0.3, 4.0), loc=(p[0], p[1], 2.0))
        show_from([c], 196 + i * 2, 230)
    pillar = A.cylinder('BigErupt', (FX, 0, 0), 0.8, 1.0, A.glow('BigE', '#fff1c4', 10), outline=0)
    A.key(pillar, 1, scale=(1, 1, 0.001), loc=(FX, 0, 0))
    A.key(pillar, 210, scale=(1, 1, 0.001), loc=(FX, 0, 0))
    A.key(pillar, 214, scale=(1, 1, 6.0), loc=(FX, 0, 3.0))
    A.key(pillar, 226, scale=(0.05, 0.05, 6.0), loc=(FX, 0, 3.0))
    show_from([pillar], 210, 228)
    C.pose(Fo, 200, **{'upper.L': (-30, 0, -18), 'upper.R': (-30, 0, 18)})
    C.pose(Fo, 210, **{'upper.L': (-160, 0, -30), 'upper.R': (-160, 0, 30)}, spine=(-20, 0, 0))
    hide_fig('Foe', 214)
    shards('Ash', (FX, 0, 0), ['#3a3a3a', '#6b6b6b', '#ff7a1a'], 214, n=60, spread=1.6, up=3.0, size=0.06)
    C.pose(W, 190, **{'upper.R': (-80, 0, 15), 'fore.R': (-60, 0, 0)})
    C.pose(W, 200, **{'upper.R': (-100, 0, 10), 'fore.R': (-5, 0, 0)})
    camera_track(ctx)
    return ctx


def d_court():
    dom = {'char': 'higuruma', 'aura': '#ffd24a', 'arena': '#14110a',
           'signPose': {'upper.R': (-80, 0, 15), 'fore.R': (-40, 0, 0), 'head': (0, 0, 0)}}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('CourtSky', '#14100a', '#000000', strength=1.0)
    env = [A.cube('CourtFloor', (0, 0, -0.02), (40, 40, 0.02), A.toon('CF', '#1a140c', shade='#0a0805'))]
    wood = A.toon('CourtWood', '#5a3416', shade='#2a1709')
    gold = A.toon('CourtGold', '#e6b84a', shade='#8a6a1e')
    # Richterbank + Judgeman (verhüllte Gestalt)
    env.append(A.cube('Bench', (0, 4.2, 1.1), (2.2, 0.5, 1.1), wood, outline=0.02))
    env.append(A.cube('BenchTrim', (0, 3.68, 2.15), (2.25, 0.05, 0.06), gold, outline=0))
    cloth = A.toon('JudgeCloth', '#e8e3d6', shade='#9e978a')
    env.append(A.cone('JudgeBody', (0, 4.6, 2.9), 0.9, 1.8, A.toon('JudgeRobe', '#0e0d12'), r2=0.3, outline=0.02))
    env.append(A.sphere('JudgeHead', (0, 4.55, 4.05), (0.45, 0.42, 0.5), cloth, outline=0.015))
    for sx in (-1, 1):
        env.append(A.cube('JudgeBand%d' % sx, (0, 4.1, 4.05 + sx * 0.12), (0.46, 0.05, 0.03), A.toon('Band', '#2a2730')))
    # Zeugenstände für beide
    for x in (WX + 0.55, FX - 0.55):
        env.append(A.cube('Stand%.1f' % x, (x, 0, 0.55), (0.3, 0.45, 0.55), wood, outline=0.015))
    # Säulen + Waage
    for i in range(8):
        x = -9 + i * 2.6
        env.append(A.cylinder('Col%d' % i, (x, 8, 4), 0.35, 8, A.toon('ColM', '#3a3020', shade='#17130c'), outline=0.02))
    env.append(A.cylinder('ScaleRod', (0, 6.5, 6.0), 0.05, 2.0, gold, outline=0.01))
    env.append(A.cube('ScaleBeam', (0, 6.5, 7.0), (1.5, 0.05, 0.05), gold, outline=0.01))
    spot = bpy.data.lights.new('Spot', 'SPOT')
    spot.energy = 1500
    spot.spot_size = 0.7
    so = bpy.data.objects.new('Spot', spot)
    bpy.context.collection.objects.link(so)
    so.location = (0, 0, 9)
    expand(ctx, s, env=env)
    # Hammerschlag
    gavel_root = A.empty('Gavel', (0.9, 3.8, 2.4))
    gh = A.cylinder('GavelHead', (0, 0, 0.6), 0.16, 0.5, wood, rot=(0, PI / 2, 0), outline=0.01)
    gs = A.cylinder('GavelStick', (0, 0, 0.3), 0.04, 0.6, wood, outline=0.008)
    gh.parent = gavel_root
    gs.parent = gavel_root
    A.key(gavel_root, 184, rot=(0, -1.2, 0))
    A.key(gavel_root, 192, rot=(0, 0.3, 0))
    A.key(gavel_root, 194, rot=(0, 0.1, 0))
    show_from([gh, gs], 151)
    verdict = text_obj('Verdict', '死刑', 0.9, A.glow('VerdictM', '#ff2a2a', 6), extrude=0.04)
    verdict.location = (FX, -0.2, 2.9)
    verdict.rotation_euler = (PI / 2, 0, 0)
    A.key(verdict, 1, scale=0.001)
    A.key(verdict, 194, scale=0.001)
    A.key(verdict, 198, scale=1.4)
    A.key(verdict, 202, scale=1.0)
    show_from([verdict], 194, 230)
    # Henkersschwert erscheint in Higurumas Hand, Schlag
    sw = A.cube('ExecSword', (0, 0, 0), (0.05, 0.02, 0.9), A.glow('SwordM', '#fff1b0', 4), outline=0.01)
    sw.parent = W['arm']
    sw.parent_type = 'BONE'
    sw.parent_bone = 'hand.R'
    sw.location = (0, 0.85, 0)
    sw.rotation_euler = (PI / 2, 0, 0)
    show_from([sw], 204)
    C.place(W, 1, (WX, 0, 0))
    C.place(W, 212, (WX, 0, 0))
    C.place(W, 216, (FX - 0.9, 0, 0))
    C.pose(W, 204, **{'upper.R': (-160, 0, 20), 'fore.R': (-20, 0, 0)})
    C.pose(W, 216, **{'upper.R': (-160, 0, 20), 'fore.R': (-20, 0, 0)})
    C.pose(W, 221, **{'upper.R': (-30, 0, 40), 'fore.R': (-10, 0, 0)})
    slash_line('ExecCut', 220, (FX, -0.3, 1.3), -0.9, length=3.5, color='#fff3b0', life=7)
    flash_at(ctx, [221])
    C.pose(Fo, 222, spine=(0, 0, 0), pelvis=(0, 0, 0))
    C.pose(Fo, 236, spine=(40, 0, 0), pelvis=(70, 0, 0), head=(20, 0, 0))
    C.move(Fo, 222, 'pelvis', (0, 0, 0))
    C.move(Fo, 236, 'pelvis', (0, -0.3, -0.75))
    shards('Light', (FX, 0, 0), ['#fff1b0', '#ffd24a'], 238, n=40, spread=1.2, up=2.5, size=0.04)
    hide_fig('Foe', 239)
    ctx['win_end_x'] = FX - 0.9
    camera_track(ctx)
    return ctx


def d_gamble():
    dom = {'char': 'hakari', 'aura': '#ff5fb0', 'arena': '#1a0a14',
           'signPose': {'upper.R': (-90, 0, 10), 'fore.R': (-80, 0, 0), 'upper.L': (-90, 0, -10), 'fore.L': (-80, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('GambleSky', '#3a0a2a', '#0a0208', cloud='#5a1040', cloud_scale=3)
    env = [A.cube('GFloor', (0, 0, -0.02), (40, 40, 0.02), A.toon('GF', '#1a0b18'))]
    bulbs = [A.glow('BulbY', '#ffe27a', 6), A.glow('BulbP', '#ff6fb8', 6), A.glow('BulbC', '#6ff0ff', 6)]
    for i in range(160):
        a = rnd.uniform(0, math.tau)
        env.append(A.sphere('Bulb%d' % i, (math.cos(a) * rnd.uniform(9, 14), math.sin(a) * rnd.uniform(9, 14) + 3, rnd.uniform(0.5, 7)), 0.08, bulbs[i % 3], segments=8, outline=0))
    # Riesiger Automat mit 3 Walzen hinter Hakari
    body = A.toon('SlotBody', '#c0186a', shade='#5c0a32')
    env.append(A.cube('Slot', (0, 9, 4), (4.2, 0.8, 3.0), body, outline=0.03))
    env.append(A.cube('SlotTop', (0, 9, 7.4), (3.0, 0.7, 0.6), A.glow('SlotTopM', '#ffe27a', 3), outline=0.02))
    reel_mat = A.toon('Reel', '#f7f2ea', shade='#bfb6a6')
    seven = A.glow('Seven', '#ff2a3a', 4)
    reels = []
    for i, x in enumerate((-2.4, 0, 2.4)):
        r = A.cylinder('Reel%d' % i, (x, 8.15, 4), 1.4, 1.8, reel_mat, rot=(0, PI / 2, 0), verts=40, outline=0.02)
        t = text_obj('Seven%d' % i, '7', 1.6, seven, extrude=0.05)
        t.location = (x, 6.72, 4)
        t.rotation_euler = (PI / 2, 0, 0)
        env += [r, t]
        A.key(t, 1, scale=0.001)
        A.key(t, 196 + i * 5, scale=0.001)
        A.key(t, 199 + i * 5, scale=1.15)
        A.key(t, 203 + i * 5, scale=1.0)
        for f in range(139, 197 + i * 5, 2):
            A.key(r, f, rot=(f * 0.9, PI / 2, 0))
        reels.append(r)
    jp = text_obj('Jackpot', 'JACKPOT', 0.9, A.glow('JPM', '#ffe27a', 6), extrude=0.06)
    jp.location = (0, 6.5, 7.6)
    jp.rotation_euler = (PI / 2, 0, 0)
    A.key(jp, 1, scale=0.001)
    A.key(jp, 210, scale=0.001)
    A.key(jp, 214, scale=1.3)
    A.key(jp, 218, scale=1.0)
    env.append(jp)
    expand(ctx, s, env=env)
    # Hakari stürmt los und schlägt zu – Gegner fliegt weg
    C.place(W, 1, (WX, 0, 0))
    C.place(W, 216, (WX, 0, 0))
    C.place(W, 222, (FX - 0.75, 0, 0))
    C.pose(W, 216, **{'upper.R': (-30, 0, 20), 'fore.R': (-100, 0, 0), 'spine': (15, 0, 0)})
    C.pose(W, 222, **{'upper.R': (-95, 0, 5), 'fore.R': (0, 0, 0), 'spine': (25, 0, 0)})
    flash_at(ctx, [223])
    C.place(Fo, 1, (FX, 0, 0))
    C.place(Fo, 223, (FX, 0, 0))
    Fo['arm'].rotation_euler = (0, 0, -PI / 2)
    Fo['arm'].keyframe_insert('rotation_euler', frame=223)
    C.place(Fo, 240, (FX + 9, 0, 3.5))
    Fo['arm'].rotation_euler = (0, 2.5, -PI / 2 + 3)
    Fo['arm'].keyframe_insert('rotation_euler', frame=240)
    ring = A.glow('ImpactR', '#ffe27a', 6)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.03, location=(FX - 0.2, 0, 1.4), rotation=(0, PI / 2, 0))
    imp = bpy.context.active_object
    A.set_mat(imp, ring)
    A.key(imp, 223, scale=0.1)
    A.key(imp, 232, scale=6)
    show_from([imp], 223, 233)
    hide_fig('Foe', 244)
    ctx['win_end_x'] = FX - 0.75
    camera_track(ctx)
    return ctx


def katana(name, loc, rot, steel, hilt, s=1.0):
    root = A.empty(name, loc)
    root.rotation_euler = rot
    parts = [A.cube(name + 'Bl', (0, 0, 0.55 * s), (0.025 * s, 0.006 * s, 0.55 * s), steel, outline=0.004),
             A.cylinder(name + 'Gu', (0, 0, 0), 0.06 * s, 0.02 * s, hilt, outline=0.004),
             A.cylinder(name + 'Hi', (0, 0, -0.17 * s), 0.02 * s, 0.32 * s, hilt, outline=0.004)]
    for p in parts:
        p.parent = root
    return root, parts


def d_swords():
    dom = {'char': 'yuta', 'aura': '#ff7cc4', 'arena': '#1a1218',
           'signPose': {'upper.R': (-80, 0, 30), 'fore.R': (-90, 0, 0), 'upper.L': (-80, 0, -30), 'fore.L': (-90, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('SwordSky', '#f6d3e6', '#7a4a66', cloud='#ffffff', cloud_scale=1.2)
    env = [A.cube('SwordGround', (0, 0, -0.02), (40, 40, 0.02), A.toon('SG', '#c9bfc8', shade='#7d7380'))]
    steel = A.toon('Steel', '#e9eef6', shade='#8f9bb0', highlight='#ffffff')
    hilt = A.toon('Hilt', '#2a1d2a')
    flyers = []
    for i in range(130):
        x, y = rnd.uniform(-14, 14), rnd.uniform(-3, 16)
        if abs(x - WX) < 1 and abs(y) < 1 or abs(x - FX) < 1.2 and abs(y) < 1.2:
            continue
        root, parts = katana('Kat%d' % i, (x, y, 0.4), (rnd.uniform(-0.35, 0.35) + PI, rnd.uniform(-0.35, 0.35), rnd.uniform(0, 6)), steel, hilt, s=rnd.uniform(0.9, 1.4))
        env += parts
        if i < 26:
            flyers.append(root)
    expand(ctx, s, env=env)
    # Schwerter heben ab und regnen auf den Gegner
    target = Vector((FX, 0, 1.2))
    for i, root in enumerate(flyers):
        p0 = root.location.copy()
        f0 = 186 + i
        A.key(root, f0, loc=p0, rot=tuple(root.rotation_euler))
        up = p0 + Vector((0, 0, 3 + rnd.uniform(0, 2)))
        A.key(root, f0 + 8, loc=up, rot=(0, 0, rnd.uniform(0, 6)))
        d = (target - up).normalized()
        rot = Vector((0, 0, 1)).rotation_difference(-d).to_euler()
        A.key(root, f0 + 16, loc=target + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.5, 0.5))), rot=tuple(rot))
    C.pose(W, 184, **{'upper.R': (-80, 0, 30), 'fore.R': (-90, 0, 0)})
    C.pose(W, 192, **{'upper.R': (-170, 0, 10), 'fore.R': (-10, 0, 0)})
    C.pose(W, 214, **{'upper.R': (-80, 0, 20), 'fore.R': (-20, 0, 0)})
    flash_at(ctx, [214])
    hide_fig('Foe', 215)
    shards('FoeSw', (FX, 0, 0), ['#2a1236', '#120b16', '#9a8aa8'], 215, n=60, spread=2.2)
    camera_track(ctx)
    return ctx


def fish(name, loc, mat, s=0.25):
    root = A.empty(name, loc)
    parts = [A.sphere(name + 'B', (0, 0, 0), (0.45 * s, 0.18 * s, 0.22 * s), mat, segments=12, outline=0.006),
             A.cone(name + 'T', (-0.5 * s, 0, 0), 0.18 * s, 0.3 * s, mat, rot=(0, PI / 2, 0), verts=4, outline=0.005)]
    for p in parts:
        p.parent = root
    return root, parts


def d_beach():
    dom = {'char': 'dagon', 'aura': '#22d3ee', 'arena': '#0c1820', 'eyeZ': 1.9, 'eyeFront': 0.19,
           'signPose': {'upper.R': (-80, 0, 25), 'fore.R': (-80, 0, 0), 'upper.L': (-80, 0, -25), 'fore.L': (-80, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('BeachSky', '#3fb6ff', '#bfeaff', cloud='#ffffff', cloud_scale=1.5, strength=1.0)
    env = [A.cube('Sand', (0, -6, -0.02), (40, 12, 0.02), A.toon('SandM', '#f2d48a', shade='#c8a560')),
           A.cube('Sea', (0, 18, -0.04), (40, 12, 0.02), A.toon('SeaM', '#18b3d6', shade='#0a6f8a', highlight='#9ff2ff'))]
    env.append(A.sphere('Sun', (-10, 40, 18), 3.2, A.glow('SunM', '#fff3a6', 4), outline=0))
    for i in range(6):   # Palmen
        x = rnd.uniform(-12, -5) if i % 2 else rnd.uniform(5, 12)
        trunk = A.cylinder('Palm%d' % i, (x, rnd.uniform(-2, 4), 2.0), 0.12, 4.0, A.toon('Trunk', '#8a5a30'), r2=0.08, rot=(0, rnd.uniform(-0.2, 0.2), 0), outline=0.01)
        env.append(trunk)
        for k in range(6):
            leaf = C.strand('Leaf%d_%d' % (i, k), [(x, trunk.location.y, 4), (x + math.cos(k) * 0.8, trunk.location.y + math.sin(k) * 0.8, 4.2),
                                                    (x + math.cos(k) * 1.6, trunk.location.y + math.sin(k) * 1.6, 3.5)], 0.18, A.toon('LeafM', '#2fa34a', shade='#16602a'), flat=0.25)
            env.append(leaf)
    expand(ctx, s, env=env)
    # Fischschwarm wirbelt um den Gegner und reißt ihn ins Meer
    fmats = [A.toon('Fish%d' % i, c) for i, c in enumerate(('#0e7490', '#155e75', '#f97316', '#e2e8f0'))]
    for i in range(60):
        root, parts = fish('Fsh%d' % i, (0, 0, 0), fmats[i % 4], s=rnd.uniform(0.18, 0.32))
        ph = rnd.uniform(0, math.tau)
        r = rnd.uniform(0.6, 1.4)
        h = rnd.uniform(0.3, 2.2)
        for f in range(182, 236, 3):
            a = ph + (f - 182) * 0.25
            rr = r * (1 - (f - 182) / 90)
            A.key(root, f, loc=(FX + math.cos(a) * rr, math.sin(a) * rr, h), rot=(0, 0, a + PI / 2))
        A.key(root, 246, loc=(FX + 3, 14, -1))
        show_from(parts, 182, 247)
    C.place(Fo, 1, (FX, 0, 0))
    C.place(Fo, 226, (FX, 0, 0))
    C.place(Fo, 244, (FX + 3, 14, -1.5))
    hide_fig('Foe', 245)
    camera_track(ctx)
    return ctx


def d_frames():
    dom = {'char': 'naoya', 'aura': '#a5b4fc', 'arena': '#0d0c1f',
           'signPose': {'upper.R': (-80, 0, 15), 'fore.R': (-60, 0, 0)}}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('FramesSky', '#1f1d55', '#05040f', cloud='#2e2a7a', cloud_scale=2)
    env = [A.cube('FrFloor', (0, 0, -0.02), (40, 40, 0.02), A.toon('FrF', '#0b0a1e'))]
    env.append(A.sphere('Moon', (0, 30, 14), 5, A.glow('MoonM', '#eef0ff', 3), outline=0))
    frame_mat = A.glow('FrameM', '#c7d2fe', 2.5)
    for i in range(40):
        x, y, z = rnd.uniform(-12, 12), rnd.uniform(-2, 16), rnd.uniform(0.5, 8)
        w, h = 1.6, 1.0
        for (dx, dz, sx, sz) in ((0, h, w, 0.03), (0, -h, w, 0.03), (w, 0, 0.03, h), (-w, 0, 0.03, h)):
            env.append(A.cube('Fr%d_%.1f_%.1f' % (i, dx, dz), (x + dx, y, z + dz), (sx, 0.02, sz), frame_mat))
    expand(ctx, s, env=env)
    # Naoya springt Bild für Bild (24 fps!) um den Gegner, der Gegner friert im Filmbild ein
    path = [(WX, 0), (0.0, -1.5), (FX - 1.2, 1.2), (FX + 1.0, -1.0), (FX - 0.8, 0)]
    for i, (x, y) in enumerate(path):
        W['arm'].location = (x, y, 0)
        W['arm'].keyframe_insert('location', frame=184 + i * 6)
    A.set_interp(W['arm'], 'CONSTANT')
    glass = A.cube('FreezeFrame', (FX, -0.4, 1.0), (0.7, 0.02, 1.1), A.glow('Glass', '#c7d2fe', 0.5, alpha=0.18))
    border = []
    for (dx, dz, sx, sz) in ((0, 1.1, 0.72, 0.04), (0, -1.1, 0.72, 0.04), (0.7, 0, 0.04, 1.12), (-0.7, 0, 0.04, 1.12)):
        border.append(A.cube('FFB%.1f%.1f' % (dx, dz), (FX + dx, -0.42, 1.0 + dz), (sx, 0.03, sz), A.glow('FFBm', '#ffffff', 5)))
    show_from([glass] + border, 200, 222)
    flash_at(ctx, [221])
    hide_fig('Foe', 222)
    shards('Glassy', (FX, -0.4, 0), ['#c7d2fe', '#e0e7ff', '#2a1236'], 222, n=70, spread=2.6)
    ctx['win_end_x'] = FX - 0.8
    camera_track(ctx)
    return ctx


DOMAINS = {'void': d_void, 'shrine': d_shrine, 'shadow': d_shadow, 'hands': d_hands, 'volcano': d_volcano,
           'court': d_court, 'gamble': d_gamble, 'swords': d_swords, 'beach': d_beach, 'frames': d_frames}

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    name, mode, out = argv[0], argv[1], argv[2]
    os.makedirs(out, exist_ok=True)
    DOMAINS[name]()
    if mode == 'preview':
        A.render_frames(out, [20, 50, 90, 125, 160, 190, 205, 220, 232, 270])
    else:
        A.render_frames(out)
    print('FERTIG', name)
