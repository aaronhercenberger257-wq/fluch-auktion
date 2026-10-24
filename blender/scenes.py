"""Domain-Siegesanimationen (alle 10 Domains) – gemeinsame Dramaturgie + eigene Welt & Finisher.

Aufruf:
  blender -b --factory-startup -P blender/scenes.py -- <domain> preview|full <ordner> [bilder] [foe=<figur>]
  foe = Skin des Gegners (gojo, sukuna, megumi, mahito, jogo, higuruma, hakari, yuta, dagon, naoya; Standard: foe)
Domains: void shrine shadow hands volcano court gamble swords beach frames

Zeitplan: gebaut mit 288 Bildern, danach auf 432 Bilder = 18 s gestreckt (finish_scene → retime).
Endgültige Bilder (24 fps):
  S1    1– 60  Totale: die Energie beider Kämpfer prallt aufeinander (Schockwellen)
  S2   61– 84  Reißschwenk auf den Sieger (Speedlines)
  S3   85–150  Fingerzeichen (Untersicht)            → Schrift „領域展開“ (HTML, 3,55 s)
  S4  151–190  Augen extrem nah, Augen glühen auf    → Titelkarte (HTML, 6,3 s)
  S5  191–280  Domain entfaltet sich; zweite Einstellung aus der Untersicht ab 236
  S6  281–380  Finisher (je Domain), Impact-Frames, Kamera-Wackeln
  S7  381–432  Sieger-Kamerafahrt                    → „SIEG!“ (HTML, 15,9 s)
Tonspuren: tools/sfx/soundtrack.mjs (gleiche Zeitumrechnung).
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
HEAD_Z = 1.761          # Augenhöhe (chars.HEAD_C)
rnd = random.Random(11)
FOE_KEY = 'foe'          # Skin des Gegners (Besitzer seiner Domain), per Aufruf-Argument foe=<figur>


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
    A.ink()
    ctx = {'dom': dom}
    W = cast.build_char(dom['char'], 'Win', loc=(WX, 0, 0), facing=PI / 2)
    Fo = cast.build_char(FOE_KEY, 'Foe', loc=(FX, 0, 0), facing=-PI / 2, sign=False)
    ctx['W'], ctx['F'] = W, Fo
    # Grundhaltung + leichtes Atmen
    for fig, seed in ((W, 1), (Fo, 2)):
        for f in range(1, FR + 1, 24):
            C.pose(fig, f, chest=(2 + (f // 24) % 2 * 2, 0, 0))
        C.pose(fig, 1, **{'upper.L': (0, 0, -10), 'upper.R': (0, 0, 10), 'fore.L': (-12, 0, 0), 'fore.R': (-12, 0, 0)})
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
    # Handhaltung fürs Zeichen (z. B. Gojo: gekreuzte Finger, Sukuna: flache Hände)
    for side, kind in W['cfg'].get('signHands', {}).items():
        if (side, kind) in W['hands']:
            C.hand_switch(W, 1, side, 'relaxed' if (side, 'relaxed') in W['hands'] else W['cfg']['hands'][side][0])
            C.hand_switch(W, 66, side, kind)
            C.hand_switch(W, 178, side, W['cfg']['hands'][side][0])
    # Gojo nimmt für die Augen-Nahaufnahme die Binde ab
    bf = bpy.data.objects.get('WinBlindfold')
    if bf:
        A.visible(bf, 1, True)
        A.visible(bf, 111, False)
    for side in ('L', 'R'):
        if ('L' if side == 'L' else 'R', 'fist') in Fo['hands']:
            C.hand_switch(Fo, 1, side, 'fist')
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
    ctx.setdefault('flashes', []).extend(frames)
    for f in frames:
        A.visible(ctx['flash'], f, True)
        A.visible(ctx['flash'], f + 2, False)


def expand(ctx, sky_obj, radius=60, f0=139, f1=158, env=(), ink=False):
    """Domain-Welt ausbreiten: Himmelskugel wächst vom Sieger, Welt erscheint, Arena verschwindet."""
    sky_obj.location = (WX, 0, 1.0)
    A.key(sky_obj, 1, scale=0.001)
    A.key(sky_obj, f0, scale=0.001)
    A.key(sky_obj, f1, scale=radius)
    A.key(sky_obj, f1 + 1, loc=(0, 0, 0))
    A.key(sky_obj, f1, loc=(WX, 0, 1.0))
    show_from([sky_obj], f0)
    show_from(list(env), 151)
    if not ink:   # Umgebung ohne Freestyle-Linien (schneller, Linien nur an Figuren)
        for o in env:
            A.no_ink(o)
    A.visible(ctx['ground'], 1, True)
    A.visible(ctx['ground'], 151, False)
    flash_at(ctx, [151])


def camera_track(ctx, fin_shots=None):
    """Kamerafahrten aller Einstellungen. fin_shots ersetzt die Finisher-Kamera (181–246)."""
    cam, tgt = ctx['cam'], ctx['tgt']
    ex = WX + ctx['dom'].get('eyeFront', 0.112)  # Augen (der Sieger schaut nach +X)
    ez = ctx['dom'].get('eyeZ', HEAD_Z)
    K = [
        (1, (0, -9.5, 2.2), (0, 0, 1.3), 28), (42, (0, -7.6, 1.9), (0, 0, 1.3), 28),
        (48, (WX + 0.85, -2.0, 1.75), (WX, 0, 1.65), 50), (62, (WX + 0.75, -1.85, 1.72), (WX, 0, 1.68), 52),
        (63, (WX + 0.9, -0.95, 1.4), (WX + 0.15, 0, 1.75), 38), (110, (WX + 0.8, -0.8, 1.48), (WX + 0.15, 0, 1.78), 44),
        (111, (ex + 0.9, -0.05, ez + 0.02), (ex, 0, ez + 0.01), 85), (138, (ex + 0.62, -0.03, ez + 0.02), (ex, 0, ez + 0.01), 100),
    ] + (ctx.get('reveal') or [(139, (1.2, -6.0, 3.0), (WX + 0.5, 0, 1.4), 22)])[:1]   # Ende der Einstellung setzt finish_scene (Bild 235)
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
    env_extra = []
    # ── cooler: Sternenmeer, Akkretionsscheibe ums Schwarze Loch, Informationsströme ──
    stars = [A.glow('StarW', '#ffffff', 6), A.glow('StarB', '#9fd0ff', 6), A.glow('StarP', '#d6b0ff', 6)]
    for i in range(420):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.5, 1))).normalized()
        st = A.cube('Star%d' % i, tuple(Vector((0, 2, 2)) + d * rnd.uniform(22, 40)), (0.04,) * 3, stars[i % 3])
        st.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
        env_extra.append(st)
    disk_m = bpy.data.materials.new('AccDisk')
    disk_m.use_nodes = True
    nt = disk_m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    grad = nt.nodes.new('ShaderNodeTexGradient')
    grad.gradient_type = 'SPHERICAL'
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 6
    noise.inputs['Detail'].default_value = 8
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.05
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    e2 = ramp.color_ramp.elements.new(0.35)
    e2.color = (*A._lin('#6a5cff'), 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*A._lin('#ffffff'), 1)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tc.outputs['Object'], grad.inputs['Vector'])
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(grad.outputs['Fac'], mul.inputs[0])
    nt.links.new(noise.outputs['Fac'], mul.inputs[1])
    nt.links.new(mul.outputs[0], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(ramp.outputs['Color'], mix.inputs['Fac'])
    em.inputs['Strength'].default_value = 4.0
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    disk_m.surface_render_method = 'BLENDED'
    disk = A.cylinder('AccretionDisk', tuple(bh_c), 7.5, 0.02, disk_m, verts=96, outline=0)
    disk.rotation_euler = (1.25, 0.25, 0)
    A.key(disk, 139, rot=(1.25, 0.25, 0))
    A.key(disk, FR, rot=(1.25, 0.25, 4.5))
    A.set_interp(disk, 'LINEAR')
    env_extra.append(disk)
    # Lichtströme (unendliche Information), die durch den Raum rasen
    lm = A.glow('InfoStream', '#bfe4ff', 8)
    for i in range(46):
        a = rnd.uniform(0, math.tau)
        rr = rnd.uniform(3, 14)
        y0 = rnd.uniform(-8, 25)
        ln = A.cube('Stream%d' % i, (math.cos(a) * rr, y0, 2 + math.sin(a) * rr * 0.6), (0.012, rnd.uniform(1.0, 3.0), 0.012), lm)
        sp = rnd.uniform(0.5, 1.4)
        A.key(ln, 139, loc=(math.cos(a) * rr, y0 + 30, 2 + math.sin(a) * rr * 0.6))
        A.key(ln, FR, loc=(math.cos(a) * rr, y0 - 30 * sp, 2 + math.sin(a) * rr * 0.6))
        A.set_interp(ln, 'LINEAR')
        env_extra.append(ln)
    # Lila Nebelschwaden
    for i in range(10):
        b = blob('Nebula%d' % i, rnd.uniform(4, 8), A.glow('NebM%d' % (i % 2), '#5a2a9a' if i % 2 else '#1a3a8a', 0.7, alpha=0.35), 400 + i)
        b.location = (rnd.uniform(-20, 20), rnd.uniform(10, 30), rnd.uniform(-2, 12))
        env_extra.append(b)
    expand(ctx, s, env=[hole, corona] + blobs + env_extra)
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
    # Kopf fliegt (stilisiert, ohne Blut), Körper kippt.
    # Fix: Hals des Körpers hängt nicht mehr am Kopf-Knochen (sonst wird er beim Abreißen lang gezogen)
    fb = bpy.data.objects['FoeBody']
    hg, ng = fb.vertex_groups.get('head'), fb.vertex_groups.get('neck')
    if hg and ng:
        for v in fb.data.vertices:
            for g in v.groups:
                if g.group == hg.index and g.weight > 0:
                    ng.add([v.index], g.weight, 'ADD')
        fb.vertex_groups.remove(hg)
    neck_top = Vector((FX, 0, 1.66))
    shards('NeckSpark', tuple(neck_top - Vector((0, 0, 1.0))), ['#bfe4ff', '#ffffff', '#6a5cff'], 228, n=26, spread=0.9, up=1.5, size=0.03, seed=21)
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


def cow_skull(name, loc, bone, horn, s=0.3, rot=0.0):
    """Rinderschädel mit geschwungenen Hörnern (Schädelberge des Schreins)."""
    L = Vector(loc)
    parts = []
    sk = C.ellipsoid(name, (0, 0, 0), (s * 0.55, s * 0.9, s * 0.5), bone, seg=16)
    for v in sk.data.vertices:          # Schnauze schmaler
        if v.co.y < 0:
            v.co.x *= 1 - 0.45 * (-v.co.y / (s * 0.9))
    parts.append(sk)
    hole = A.flat('SkullHole', '#120404')
    for sx in (-1, 1):
        parts.append(C.ellipsoid(name + 'E%d' % sx, (sx * s * 0.24, -s * 0.35, s * 0.28), (s * 0.12, s * 0.06, s * 0.1), hole, seg=10))
        parts.append(C.sweep(name + 'H%d' % sx, [(sx * s * 0.4, s * 0.25, s * 0.25), (sx * s * 1.0, s * 0.3, s * 0.45), (sx * s * 1.25, s * 0.05, s * 0.95)],
                             [s * 0.13, s * 0.08, s * 0.01], horn, ring_n=8, rings=8))
    root = A.empty(name + 'Root', L)
    root.rotation_euler = (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.3, 0.3), rot)
    for p in parts:
        p.parent = root
        A.add_outline(p, 0.01 * s / 0.3)
    return parts


def spider_bush(name, loc, n, height, mat, tip):
    """Dunkelrote, nach außen gebogene Dornen (wie die Pflanzen vor dem Schrein in der Vorlage)."""
    L = Vector(loc)
    parts = []
    r = random.Random(hash(name) & 0xffff)
    for i in range(n):
        a = r.uniform(0, math.tau)
        h = height * r.uniform(0.6, 1.1)
        out = Vector((math.cos(a), math.sin(a), 0))
        pts = [L + out * 0.1, L + out * h * 0.25 + Vector((0, 0, h * 0.55)), L + out * h * 0.6 + Vector((0, 0, h * 0.9)), L + out * h * 0.95 + Vector((0, 0, h * 0.75))]
        o = C.sweep(name + '%d' % i, pts, [0.05 * height, 0.035 * height, 0.02 * height, 0.002], mat, ring_n=8, rings=12)
        A.add_outline(o, 0.008)
        parts.append(o)
        if i % 3 == 0:
            parts.append(A.sphere(name + 'T%d' % i, tuple(pts[-1]), 0.035 * height, tip, segments=8, outline=0))
    return parts


def lantern(name, loc, glow_c):
    L = Vector(loc)
    pole = A.cylinder(name + 'Pole', L + Vector((0, 0, 1.2)), 0.05, 2.4, A.toon('LantPole', '#1a0a0a'), outline=0.01)
    box = A.cube(name + 'Box', L + Vector((0, 0, 2.6)), (0.22, 0.22, 0.3), A.glow('LantGlow', glow_c, 6), outline=0.012)
    cap = A.cone(name + 'Cap', L + Vector((0, 0, 3.05)), 0.38, 0.3, A.toon('LantCap', '#120606'), verts=4, outline=0.012)
    cap.rotation_euler.z = PI / 4
    li = bpy.data.lights.new(name + 'L', 'POINT')
    li.energy = 260
    li.color = A._lin(glow_c)
    lo = bpy.data.objects.new(name + 'L', li)
    bpy.context.collection.objects.link(lo)
    lo.location = L + Vector((0, 0, 2.6))
    show_from([lo], 151)
    return [pole, box, cap]


def mirror_water(name, color='#06080e', tint='#1a0404'):
    """Spiegelndes, dunkles Wasser (EEVEE-Raytracing + planare Sonde)."""
    m = bpy.data.materials.new(name + 'M')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pb.inputs['Base Color'].default_value = (*A._lin(color), 1)
    pb.inputs['Roughness'].default_value = 0.04
    pb.inputs['Emission Color'].default_value = (*A._lin(tint), 1)
    pb.inputs['Emission Strength'].default_value = 1.0
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.04
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], pb.inputs['Normal'])
    nt.links.new(pb.outputs[0], out.inputs['Surface'])
    w = A.cube(name, (0, 0, -0.02), (60, 60, 0.02), m)
    s = bpy.context.scene
    try:
        s.eevee.use_raytracing = True
        s.eevee.ray_tracing_method = 'SCREEN'
    except Exception as e:
        print('Raytracing:', e)
    try:
        pd = bpy.data.lightprobes.new(name + 'Probe', 'PLANE')
        po = bpy.data.objects.new(name + 'Probe', pd)
        bpy.context.collection.objects.link(po)
        po.location = (0, 0, 0.0)
        po.scale = (60, 60, 1)
    except Exception as e:
        print('Planar-Sonde:', e)
    return w


def tile_roof_mat(name, base, shade, line):
    """Dach mit Ziegelreihen: Toon-Stufen × dunkle Streifen (Wave-Textur)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
    s2r = nt.nodes.new('ShaderNodeShaderToRGB')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = (*A._lin(shade), 1)
    ramp.color_ramp.elements[1].position = 0.35
    ramp.color_ramp.elements[1].color = (*A._lin(base), 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 7.0
    lines = nt.nodes.new('ShaderNodeValToRGB')
    lines.color_ramp.interpolation = 'CONSTANT'
    lines.color_ramp.elements[0].color = (*A._lin(line), 1)
    lines.color_ramp.elements[1].position = 0.12
    lines.color_ramp.elements[1].color = (1, 1, 1, 1)
    mul = nt.nodes.new('ShaderNodeMix')
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(tc.outputs['Object'], wave.inputs['Vector'])
    nt.links.new(wave.outputs['Fac'], lines.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], mul.inputs[6])
    nt.links.new(lines.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def d_shrine():
    """Malevolent Shrine (nach Vorlage): roter Wolkenhimmel, spiegelndes schwarzes Wasser, Tempel mit Maul aus Zähnen,
    Hörner auf den Dächern, Berge aus Rinderschädeln, dunkelrote Dornenbüsche, blaue Laternen. Sukuna mit Enma-Zeichen."""
    dom = {'char': 'sukuna', 'aura': '#ff4b4b', 'arena': '#1a0d0d',
           'signPose': {'upper.R': (-48, 0, 34), 'fore.R': (-98, 0, 18), 'upper.L': (-48, 0, -34), 'fore.L': (-98, 0, -18), 'head': (6, 0, 0),
                        'hand.R': (0, 0, 0), 'hand.L': (0, 0, 0)}}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    C.pose(W, 62, **{'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0)})
    C.pose(W, 70, **{'upper.L': (-48, 0, -34), 'fore.L': (-98, 0, -18)})
    C.pose(W, 176, **{'upper.L': (-48, 0, -34), 'fore.L': (-98, 0, -18)})
    s = sky('ShrineSky', '#7a1410', '#150202', cloud='#c0281a', cloud_scale=1.6, strength=1.1)
    env = [mirror_water('BloodWater')]
    base = Vector((-5.5, 9.0, 0))
    before = set(bpy.data.objects)
    stone = A.toon('ShrStone', '#2a1414', shade='#0e0505', highlight='#4a2420')
    wood = A.toon('ShrWood', '#6a1210', shade='#2a0505', highlight='#a02a1a')
    dark = A.toon('ShrDark', '#1c0808', shade='#0a0202')
    roofm = tile_roof_mat('ShrRoof', '#2a1414', '#0c0404', '#050101')
    jade = tile_roof_mat('ShrRoofJ', '#1f5a5a', '#0a2224', '#041214')
    trim = A.toon('ShrTrim', '#c9902a', shade='#6a4410', highlight='#ffd070')
    teethm = A.toon('ShrTeeth', '#f0e6d0', shade='#a8987c', highlight='#ffffff')
    horn = A.toon('ShrHorn', '#e8dcc4', shade='#9a8a70')
    # Stufen-Sockel
    for i, (w, d) in enumerate(((5.6, 4.6), (5.0, 4.0), (4.4, 3.4))):
        env.append(A.cube('ShrStep%d' % i, base + Vector((0, 0, 0.2 + 0.4 * i)), (w / 2, d / 2, 0.2), stone, outline=0.02))
    # Halle
    hz0, hz1 = 1.2, 4.2
    env.append(A.cube('ShrHall', base + Vector((0, 0.2, (hz0 + hz1) / 2)), (1.9, 1.4, (hz1 - hz0) / 2), dark, outline=0.02))
    for x in (-1.95, -0.9, 0.9, 1.95):
        env.append(A.cylinder('ShrPillar', base + Vector((x, -1.25, (hz0 + hz1) / 2)), 0.13, hz1 - hz0, wood, outline=0.015))
    env.append(A.cube('ShrBeam', base + Vector((0, -1.3, hz1 - 0.15)), (2.15, 0.14, 0.14), wood, outline=0.015))
    env.append(A.cube('ShrBeamT', base + Vector((0, -1.3, hz1 - 0.15)), (2.18, 0.15, 0.03), trim, outline=0))
    # Maul in der Front: dunkle, rot glühende Öffnung + obere und untere Zahnreihe auf einem Bogen
    mc = base + Vector((0, -1.24, 2.55))
    maw = A.cylinder('ShrMaw', mc, 1.3, 0.1, A.glow('MawIn', '#04161c', 1.0), rot=(PI / 2, 0, 0), verts=48, outline=0.02)
    maw.scale = (1.0, 0.85, 1.0)
    env.append(maw)
    throat = A.sphere('ShrThroat', mc + Vector((0, 0.3, -0.1)), (0.8, 0.2, 0.55), A.glow('Throat', '#3ad7ff', 3.5), outline=0)
    gum = A.toon('ShrGum', '#8a1420', shade='#3a060a', highlight='#c02030')
    bpy.ops.mesh.primitive_torus_add(major_radius=1.22, minor_radius=0.12, location=tuple(mc + Vector((0, -0.08, 0))), rotation=(PI / 2, 0, 0))
    gums = bpy.context.active_object
    gums.name = 'ShrGums'
    gums.scale = (1.0, 0.85, 1.0)
    A.set_mat(gums, gum)
    A.add_outline(gums, 0.015)
    env += [throat, gums]
    mlight = bpy.data.lights.new('MawLight', 'POINT')
    mlight.energy = 1800
    mlight.color = A._lin('#3ad7ff')
    mlo = bpy.data.objects.new('MawLight', mlight)
    bpy.context.collection.objects.link(mlo)
    mlo.location = mc + Vector((0, -0.8, 0))
    show_from([mlo], 151)
    for i in range(13):
        t = -1 + 2 * i / 12
        x = t * 1.15
        zt = 1.0 * math.sqrt(max(0.0, 1 - t * t)) * 0.85 + 0.0
        top = mc + Vector((x, -0.12, zt * 0.95 + 0.05))
        tooth = A.cone('ToothU%d' % i, top + Vector((0, 0, -0.22)), 0.12, 0.5 - 0.15 * abs(t), teethm, rot=(PI, 0, -t * 0.4), verts=10, outline=0.008)
        env.append(tooth)
        bot = mc + Vector((x * 0.95, -0.12, -zt * 0.8 - 0.05))
        env.append(A.cone('ToothD%d' % i, bot + Vector((0, 0, 0.2)), 0.11, 0.45 - 0.15 * abs(t), teethm, rot=(0, 0, t * 0.4), verts=10, outline=0.008))
    # Zwei geschwungene Dächer, an den Ecken und oben Hörner
    for lvl, (z, w, d) in enumerate(((hz1 + 0.35, 3.2, 2.5), (hz1 + 1.6, 2.4, 1.85), (hz1 + 2.75, 1.7, 1.3))):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=1.0, radius2=0.12, depth=0.9)
        for v in bm.verts:
            if v.co.z < 0:
                v.co.z += 0.35
        r = mesh_obj('Roof%d' % lvl, bm, jade if lvl % 2 else roofm, outline=0.02)
        r.location = base + Vector((0, 0.1, z))
        r.rotation_euler = (0, 0, PI / 4)
        r.scale = (w, d, 1.0)
        env.append(r)
        for sx in (-1, 1):
            for sy in (-1, 1):
                p = base + Vector((sx * w * 0.69, 0.1 + sy * d * 0.69, z - 0.1))
                env.append(C.sweep('RoofHorn%d%d%d' % (lvl, sx, sy), [p, p + Vector((sx * 0.3, sy * 0.3, 0.25)), p + Vector((sx * 0.35, sy * 0.25, 0.75))],
                                   [0.12, 0.08, 0.005], horn, ring_n=10, rings=10))
        if lvl >= 1:
            env.append(A.cube('Floor%d' % (lvl + 1), base + Vector((0, 0.1, z - 0.55)), (1.3 - 0.25 * (lvl - 1), 1.0 - 0.2 * (lvl - 1), 0.45), wood, outline=0.015))
            # leuchtende Gitterfenster
            for k in range(5):
                env.append(A.cube('Lattice%d_%d' % (lvl, k), base + Vector((-0.8 + k * 0.4, 0.1 - (1.0 - 0.2 * (lvl - 1)) - 0.01, z - 0.55)), (0.03, 0.01, 0.3),
                                  A.glow('LatticeM', '#ffb04a', 3)))
        # Traufbalken mit Konsolen rund um das Dach
        for k in range(14):
            t = -1 + 2 * k / 13
            for sy in (-1, 1):
                env.append(A.cube('Eave%d_%d_%d' % (lvl, k, sy), base + Vector((t * w * 0.62, 0.1 + sy * d * 0.66, z - 0.42)), (0.07, 0.12, 0.07), trim, outline=0.004))
        env.append(A.cube('EaveBeam%d' % lvl, base + Vector((0, 0.1 - d * 0.66, z - 0.36)), (w * 0.66, 0.05, 0.05), wood, outline=0.006))
    # drei Rinderschädel hängen vorn am Dach (wie im Poster)
    for k, x in enumerate((-0.7, 0.0, 0.7)):
        env += cow_skull('RoofSkull%d' % k, base + Vector((x, -1.85, hz1 + 1.25)), A.toon('RoofSkullM', '#d8452a', shade='#6a1408', highlight='#ff8a5a'),
                         A.toon('HornS2', '#2a1a14'), s=0.34, rot=PI)
    top = base + Vector((0, 0.1, hz1 + 3.4))
    for sx in (-1, 1):   # große Ochsenhörner auf der Spitze
        env.append(C.sweep('TopHorn%d' % sx, [top, top + Vector((sx * 0.6, 0, 0.35)), top + Vector((sx * 1.1, 0, 1.2)), top + Vector((sx * 0.85, 0, 1.75))],
                           [0.2, 0.15, 0.08, 0.005], horn, ring_n=12, rings=16))
    env.append(A.sphere('TopOrb', top + Vector((0, 0, 0.2)), 0.22, A.glow('TopOrbM', '#ff4a2a', 4), outline=0.01))
    for o in env:
        if o.type == 'MESH' and o.name.startswith(('RoofHorn', 'TopHorn')):
            A.add_outline(o, 0.015)
    # Schädelberge links und rechts vom Schrein + vor den Stufen
    bone = A.toon('Bone', '#ece2cc', shade='#9a8d74', highlight='#ffffff')
    hornd = A.toon('HornS', '#3a2a22', shade='#160e0a')
    for pile, (cx, cy, rad, n) in enumerate(((-3.6, 0.5, 2.4, 40), (3.6, 0.6, 2.4, 40), (0, -2.6, 2.6, 26))):
        for i in range(n):
            a = rnd.uniform(0, math.tau)
            r = rad * math.sqrt(rnd.uniform(0, 1))
            z = max(0.1, 1.8 - r * 0.7) * rnd.uniform(0.4, 1.0) if pile < 2 else 0.12 + rnd.uniform(0, 0.25)
            env += cow_skull('Skull%d_%d' % (pile, i), base + Vector((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.6, z)), bone, hornd,
                             s=rnd.uniform(0.22, 0.36), rot=rnd.uniform(-0.8, 0.8) + PI)
    # Schrein-Anlage drehen: Front (Maul) schaut zu Sukuna, steht direkt hinter ihm (wie im Poster)
    root = A.empty('ShrineRoot', base)
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o not in before and o.parent is None and o is not root]:
        A.parent_keep(o, root)
    # Größenverhältnis wie im Anime: der Schrein ist riesig, Sukuna winzig davor
    root.location = (WX - 25.0, -1.8, 0)
    root.scale = (3.2, 3.2, 3.2)
    root.rotation_euler = (0, 0, PI / 2)
    shrine_parts = [o for o in env if o.name.startswith(('Shr', 'Roof', 'Tooth', 'TopHorn', 'Floor', 'Eave', 'Lattice', 'Platform', 'Pillar'))]
    ctx['second'] = ((WX + 3.0, -4.2, 0.25), (WX - 18.0, 0.0, 10.5), (WX + 2.2, -3.4, 0.4), (WX - 18.0, 0.0, 12.0), 20)
    ctx['reveal'] = [(139, (WX + 8.5, -6.5, 0.45), (WX - 18.0, 0, 10.5), 18), (180, (WX + 7.0, -5.4, 0.6), (WX - 18.0, 0, 10.0), 19)]
    # Dornenbüsche + blaue Laternen in normaler Größe zwischen Sukuna und dem Schrein
    bush = A.toon('Bush', '#7a0d14', shade='#2a0306', highlight='#c02030')
    tipm = A.glow('BushTip', '#ff3048', 3)
    for i in range(16):
        side = 1 if i % 2 else -1
        x = WX - rnd.uniform(3, 16)
        y = side * rnd.uniform(2.5, 11)
        env += spider_bush('Bush%d' % i, (x, y, 0), 14, rnd.uniform(1.2, 2.8), bush, tipm)
    for i, (x, y) in enumerate(((WX - 6, -3.2), (WX - 6, 3.2), (WX - 11, -4.5), (WX - 11, 4.5))):
        env += lantern('Lant%d' % i, (x, y, 0), '#6ae8ff')
    # roter Nebel
    for i in range(16):
        b = blob('Mist%d' % i, rnd.uniform(1.5, 3.5), A.glow('MistR', '#6a0a0a', 0.5, alpha=0.4), 100 + i)
        b.location = (rnd.uniform(-14, 10), rnd.uniform(2, 16), rnd.uniform(0.1, 0.5))
        env.append(b)
    expand(ctx, s, env=env)
    for o in shrine_parts:
        A.to_ink(o)
    # ── Finisher: Dismantle & Cleave – Schnitt-Gewitter, der Gegner zerfällt ──
    hc = Vector((FX, 0, 1.2))
    for i in range(70):
        f = 184 + int(i * 0.5)
        slash_line('Cut%d' % i, f, hc + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.6, 0.2), rnd.uniform(-0.8, 0.9))),
                   rnd.uniform(-1.4, 1.4), length=rnd.uniform(1.4, 3.2), color='#ffffff' if i % 3 else '#ff6b6b', tilt=rnd.uniform(-0.5, 0.5))
    for f in range(184, 220, 2):
        C.pose(Fo, f, spine=(rnd.uniform(-10, 14), rnd.uniform(-8, 8), 0), head=(rnd.uniform(-15, 15), 0, rnd.uniform(-15, 15)))
    flash_at(ctx, [218])
    hide_fig('Foe', 219)
    shards('FoeBits', (FX, 0, 0), ['#2a1236', '#120b16', '#a898b4', '#7a1f3a'], 219, n=80, spread=2.8)
    slash_line('BigCut1', 216, hc + Vector((0, -0.4, 0.3)), 0.8, length=5.0, color='#ffffff', life=8)
    slash_line('BigCut2', 217, hc + Vector((0, -0.4, 0.3)), -0.8, length=5.0, color='#ff8080', life=8)
    # Sukuna: Klauenhand nach vorn (Schnitte), dann gelassen
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


def giant_hand(name, kind, side, mat, s):
    """Riesenhand aus dem Figuren-Baukasten (mit fünf Fingern), Tusche-Linien wie in der Vorlage."""
    h = C.hand_mesh(name, side, kind, mat, scale=s)
    A.add_outline(h, 0.0025)
    return h


def orient_hand(h, wrist, finger_dir, palm_dir):
    """Hand (Finger entlang lokal −Z, Handfläche lokal +X) so drehen, dass die Finger in finger_dir zeigen."""
    from mathutils import Matrix
    z = -Vector(finger_dir).normalized()
    x = Vector(palm_dir)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    sc = h.scale.copy()
    h.matrix_world = Matrix.Translation(Vector(wrist)) @ m
    h.scale = sc


def d_hands():
    """Self-Embodiment of Perfection (nach Anime-Vorlage): Hinter Mahito wächst ein riesiger Arm empor, oben zwei
    ineinander verschränkte Hände, darunter fächern sich viele Hände wie Flügel auf (lavendel mit Tusche-Linien).
    Danach zoomt die Kamera auf Mahitos Gesicht – im weit aufgerissenen Mund formen kleine Hände das Fingerzeichen."""
    dom = {'char': 'mahito', 'aura': '#b9a2ff', 'arena': '#120c1e',
           'signPose': {'upper.R': (-70, 0, 30), 'fore.R': (-95, 0, 10), 'upper.L': (-70, 0, -30), 'fore.L': (-95, 0, -10)}}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    C.pose(W, 62, **{'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0)})
    C.pose(W, 70, **{'upper.L': (-70, 0, -30), 'fore.L': (-95, 0, -10)})
    # Arme weit ausbreiten, wenn die Hände erscheinen (wie in der Vorlage)
    spread = {'upper.R': (-10, 0, 78), 'fore.R': (-15, 0, 0), 'upper.L': (-10, 0, -78), 'fore.L': (-15, 0, 0), 'head': (-12, 0, 0), 'spine': (-6, 0, 0)}
    C.pose(W, 138, **{'upper.L': (-70, 0, -30), 'fore.L': (-95, 0, -10), 'upper.R': (-70, 0, 30), 'fore.R': (-95, 0, 10)})
    C.pose(W, 146, **spread)
    C.pose(W, 176, **spread)
    C.hand_switch(W, 140, 'R', 'open')
    C.hand_switch(W, 140, 'L', 'open')
    s = sky('HandsSky', '#1a0f30', '#040209', cloud='#2e1a52', cloud_scale=2.2, strength=0.8)
    env = []
    env.append(A.cube('HandsFloor', (0, 0, -0.02), (40, 40, 0.02), A.toon('HF', '#140a26', shade='#06030c')))
    # Lavendel wie in der Vorlage: hell, flach, dunkellila Schatten, Linien per Freestyle
    hm = A.toon('BigHandM', '#cdbcf6', shade='#8a72c8', highlight='#f0e8ff', steps=(0.45, 0.93))
    arm_m = A.toon('BigArmM', '#b9a4ec', shade='#7660b4', highlight='#e2d8ff', steps=(0.45, 0.93))
    base = Vector((WX - 4.0, 0.0, 0.0))     # hinter Mahito (er schaut nach +X, Kamera frontal)
    fwd = Vector((1, 0, 0))
    main = []      # bekommen Freestyle-Linien
    grow = []

    def hand(name, kind, side, s, wrist, fdir, palm, f0):
        h = giant_hand(name, kind, side, hm, s)
        orient_hand(h, wrist, fdir, palm)
        env.append(h)
        main.append(h)
        grow.append((h, f0 - 12, f0 - 5))
        return h

    def limb(name, pts, radii, f0):
        o = C.sweep(name, pts, radii, arm_m, ring_n=20, rings=20)
        A.add_outline(o, 0.02)
        env.append(o)
        main.append(o)
        grow.append((o, f0 - 12, f0 - 6))
        return o
    # 1) Unten: riesige Hand, Handfläche nach vorn, Finger zeigen nach UNTEN bis zu Mahitos Füßen
    hand('BottomHand', 'open', 'L', 44, base + Vector((-0.6, 0, 8.9)), (0, 0, -1), -fwd, 150)
    # 2) Unterarm steigt senkrecht auf
    limb('CentralArm', [base + Vector((-0.9, 0, 8.4)), base + Vector((-1.0, 0, 12.5)), base + Vector((-1.1, 0, 16.5))], [1.9, 1.75, 1.7], 150)
    # 3) Oben: zwei Fäuste greifen ineinander (wie in der Vorlage)
    hand('ClaspR', 'grip', 'R', 34, base + Vector((-0.4, -3.6, 17.2)), (0, 1, 0.25), fwd, 156)
    hand('ClaspL', 'grip', 'L', 34, base + Vector((0.2, 3.6, 18.4)), (0, -1, -0.2), -fwd, 158)
    limb('ClaspArmR', [base + Vector((-1.6, -9.0, 15.4)), base + Vector((-1.0, -6.6, 16.6)), base + Vector((-0.6, -4.2, 17.2))], [1.5, 1.45, 1.4], 154)
    limb('ClaspArmL', [base + Vector((-1.2, 9.0, 19.8)), base + Vector((-0.6, 6.6, 19.0)), base + Vector((0.0, 4.2, 18.4))], [1.5, 1.45, 1.4], 156)
    # 4) Ganz oben: offene Hand, Finger nach oben
    hand('TopHand', 'open', 'R', 40, base + Vector((-1.6, 0, 19.6)), (0, 0, 1), fwd, 160)
    # 5) Zu den Seiten: Arme wie Äste, an jedem eine Hand (Finger nach außen)
    side = [(28, 7.5, 'claw'), (2, 8.0, 'open'), (-26, 7.5, 'relaxed'), (-52, 6.5, 'claw')]
    for k, (deg, ln, kind) in enumerate(side):
        for sx in (-1, 1):
            a = math.radians(deg)
            d = Vector((-0.15, sx * math.cos(a), math.sin(a))).normalized()
            root = base + Vector((-1.4, 0, 12.0))
            wrist = root + d * ln
            limb('SideArm%d%d' % (k, sx), [root + d * 1.2, root + d * (ln * 0.55) + Vector((0, 0, 0.6)), wrist], [1.35, 1.1, 0.95], 152 + k * 2)
            hand('SideHand%d%d' % (k, sx), kind, 'R' if sx < 0 else 'L', 36 + 3 * (k % 2), wrist, d, fwd if sx < 0 else -fwd, 155 + k * 2)
    # weit hinten: dunklere Hände als Silhouetten (ohne Linien, günstig)
    pale = A.toon('PaleHandM', '#5a4a8a', shade='#30265a')
    for i in range(12):
        a = -PI * 0.15 + i / 11 * PI * 1.3
        p = base + Vector((-14, math.cos(a) * 20, 12 + math.sin(a) * 12))
        h = giant_hand('FarHand%d' % i, 'open', 'R', pale, rnd.uniform(40, 60))
        orient_hand(h, p, (0, math.cos(a), math.sin(a)), fwd)
        env.append(h)
    # alles wächst aus dem Nichts (Skalierung)
    for o, f0, f1 in grow:
        sc = tuple(o.scale)
        A.key(o, 1, scale=tuple(v * 0.001 for v in sc))
        A.key(o, f0, scale=tuple(v * 0.001 for v in sc))
        A.key(o, f1, scale=tuple(v * 1.05 for v in sc))
        A.key(o, f1 + 4, scale=sc)
    glow = bpy.data.lights.new('HandsGlow', 'POINT')
    glow.energy = 9000
    glow.color = A._lin('#c8a8ff')
    go = bpy.data.objects.new('HandsGlow', glow)
    bpy.context.collection.objects.link(go)
    go.location = tuple(base + Vector((8, 0, 12)))
    show_from([go], 151)
    sparks_rise('SoulMotes', tuple(base), '#e6d8ff', 50, 139, FR + 40, radius=10, height=18, size=0.02)
    expand(ctx, s, env=env)
    for o in main:     # nur die großen Hände/Arme vorn bekommen Freestyle-Linien (Finger, Knöchel)
        A.to_ink(o)
    # Gegner während der Enthüllung ausblenden (er stünde sonst mitten im Bild)
    for o in objs_of('Foe'):
        if o.type in ('MESH', 'ARMATURE', 'CURVE', 'FONT'):
            A.visible(o, 1, True)
            A.visible(o, 139, False)
            A.visible(o, 182, True)
    # Mund weit auf, darin das Fingerzeichen (für die Gesichts-Nahaufnahme)
    big = [o for o in bpy.data.objects if o.name.startswith(('WinBigMouth', 'WinMouthHand'))]
    small = [o for o in bpy.data.objects if o.name in ('WinMouthO', 'WinMouthL', 'WinTeethU', 'WinTeethD')]
    for o in big:
        A.visible(o, 1, False)
        A.visible(o, 156, True)
        A.visible(o, 182, False)
    for o in small:
        A.visible(o, 1, True)
        A.visible(o, 156, False)
        A.visible(o, 182, True)
    ctx['reveal'] = [(139, (WX + 12.0, -1.6, 1.1), (WX - 4.0, 0, 10.6), 17), (180, (WX + 10.5, -1.4, 1.2), (WX - 4.0, 0, 11.0), 17)]
    # Zweite Einstellung: Kamerafahrt auf das Gesicht, bis der Mund mit dem Zeichen das Bild füllt
    ctx['second'] = ((WX + 1.5, -0.1, 1.74), (WX + 0.1, 0, 1.71), (WX + 0.42, -0.02, 1.72), (WX + 0.1, 0, 1.70), 55)
    # Mahito tritt heran und berührt die Seele (Idle Transfiguration)
    C.place(W, 1, (WX, 0, 0))
    C.place(W, 190, (WX, 0, 0))
    C.place(W, 202, (FX - 0.7, 0, 0))
    C.pose(W, 200, **{'upper.R': (-72, 0, 28), 'fore.R': (-112, 0, 0), 'upper.L': (0, 0, -10), 'fore.L': (-12, 0, 0), 'head': (0, 0, 0), 'spine': (0, 0, 0)})
    C.pose(W, 206, **{'upper.R': (-90, 0, 5), 'fore.R': (-10, 0, 0)})
    arm = Fo['arm']

    def sc(f, bone, v):
        pb = arm.pose.bones[bone]
        pb.scale = v
        pb.keyframe_insert('scale', frame=f)
    # Idle Transfiguration: die Seele wird sauber verdreht (keine wilden Verzerrungen), lila Glühen, der Körper
    # schrumpft drehend zu einer kleinen Seelenkugel, die verlischt
    C.pose(Fo, 206, spine=(8, 0, 0), head=(0, 0, 0))
    C.pose(Fo, 218, spine=(20, 45, 0), head=(25, 30, 0), **{'upper.L': (-120, 0, -30), 'upper.R': (-120, 0, 30)})
    C.pose(Fo, 228, spine=(35, 90, 0), head=(40, 60, 0), **{'upper.L': (-160, 0, -40), 'upper.R': (-160, 0, 40)})
    soul = A.sphere('SoulGlow', (FX, 0, 1.1), 0.45, A.glow('SoulGlowM', '#b48cff', 3.0, alpha=0.2), outline=0)
    A.key(soul, 1, scale=0.001)
    A.key(soul, 206, scale=0.001)
    A.key(soul, 214, scale=1.0)
    A.key(soul, 236, scale=0.6)
    A.key(soul, 246, scale=0.05)
    show_from([soul], 206, 247)
    A.key(arm, 226, scale=arm.scale.z, rot=(0, 0, -PI / 2))
    A.key(arm, 244, scale=0.05, rot=(0, 0, -PI / 2 + 6.0))
    hide_fig('Foe', 245)
    ctx['win_end_x'] = FX - 0.7
    camera_track(ctx)
    return ctx


def lava_mat(name, strength=3.0, scale=1.5, speed=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = scale
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale * 3
    noise.inputs['Detail'].default_value = 6
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 0.12
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*A._lin('#fff0a0'), 1)
    cr.elements[1].position = 0.1
    cr.elements[1].color = (*A._lin('#ff7a10'), 1)
    e = cr.elements.new(0.22)
    e.color = (*A._lin('#7a1a04'), 1)
    e = cr.elements.new(0.4)
    e.color = (*A._lin('#1e0804'), 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], vor.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], mul.inputs[0])
    nt.links.new(vor.outputs['Distance'], add.inputs[0])
    nt.links.new(mul.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    if speed:
        loc = mp.inputs['Location']
        loc.default_value = (0, 0, 0)
        loc.keyframe_insert('default_value', frame=1)
        loc.default_value = (0, 0, speed)
        loc.keyframe_insert('default_value', frame=FR + 40)
        for fc in A._fcurves(m.node_tree.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return m


def rock_mat(name):
    """Fels mit glühenden Rissen."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
    s2r = nt.nodes.new('ShaderNodeShaderToRGB')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = (*A._lin('#1a0a06'), 1)
    ramp.color_ramp.elements[1].position = 0.3
    ramp.color_ramp.elements[1].color = (*A._lin('#4a1c0e'), 1)
    e = ramp.color_ramp.elements.new(0.75)
    e.color = (*A._lin('#8a3a18'), 1)
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 0.8
    dist = nt.nodes.new('ShaderNodeTexNoise')
    dist.inputs['Scale'].default_value = 1.2
    dist.inputs['Detail'].default_value = 4
    vmix = nt.nodes.new('ShaderNodeMix')
    vmix.data_type = 'VECTOR'
    vmix.inputs['Factor'].default_value = 0.35
    crack = nt.nodes.new('ShaderNodeValToRGB')
    crack.color_ramp.elements[0].position = 0.0
    crack.color_ramp.elements[0].color = (*A._lin('#ffb040'), 1)
    crack.color_ramp.elements[1].position = 0.018
    crack.color_ramp.elements[1].color = (0, 0, 0, 1)
    add = nt.nodes.new('ShaderNodeMix')
    add.data_type = 'RGBA'
    add.blend_type = 'ADD'
    add.inputs['Factor'].default_value = 1.0
    em = nt.nodes.new('ShaderNodeEmission')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(tc.outputs['Object'], vmix.inputs[4])
    nt.links.new(tc.outputs['Object'], dist.inputs['Vector'])
    nt.links.new(dist.outputs['Color'], vmix.inputs[5])
    nt.links.new(vmix.outputs[1], vor.inputs['Vector'])
    nt.links.new(vor.outputs['Distance'], crack.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], add.inputs[6])
    nt.links.new(crack.outputs['Color'], add.inputs[7])
    nt.links.new(add.outputs[2], em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.6
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def rock_lump(name, loc, size, mat, seed, outline=0.02):
    o = blob(name, 1.0, mat, seed, outline=0)
    o.location = loc
    o.scale = size
    if outline:
        A.add_outline(o, outline)
    return o


def d_volcano():
    """Coffin of the Iron Mountain (nach Vorlage): im Inneren eines Vulkans – Felsdecke über allem, Lavafälle an den
    Wänden, Lavaflüsse am Boden, glühende Brocken und Funken, alles in Orange/Rot getaucht."""
    dom = {'char': 'jogo', 'aura': '#ff8a2a', 'arena': '#1c0d06', 'eyeZ': 1.53, 'eyeFront': 0.115,
           'signPose': {'upper.R': (-80, 0, 15), 'fore.R': (-60, 0, 0), 'head': (0, 0, 0)}}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('VolcSky', '#3a0e04', '#100302', cloud='#7a2408', cloud_scale=2.0, strength=0.8)
    env = []
    rock = rock_mat('VolcRock')
    lava = lava_mat('LavaSea', 3.0, 0.8, speed=1.5)
    # Boden: Lava mit dunklen Felsplatten
    env.append(A.cube('LavaFloor', (0, 0, -0.06), (45, 45, 0.02), lava))
    for i in range(26):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(1.5, 16)
        p = Vector((math.cos(a) * r, math.sin(a) * r + 3, 0.0))
        if abs(p.y) < 2.2 and abs(p.x) < 4:
            continue
        env.append(rock_lump('Plate%d' % i, p, (rnd.uniform(0.8, 2.4), rnd.uniform(0.8, 2.0), rnd.uniform(0.1, 0.35)), rock, 300 + i, outline=0.03))
    env.append(rock_lump('Stage', (0, 0, -0.05), (5.0, 2.6, 0.1), rock, 7, outline=0.03))
    # Höhlendecke (Kuppel aus Fels) – von innen sichtbar
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    for v in bm.verts:
        n = v.co.copy()
        v.co *= 1.0 + 0.12 * math.sin(n.x * 9 + n.y * 4) * math.cos(n.z * 7) + 0.06 * math.sin(n.y * 15)
    dome = mesh_obj('CaveDome', bm, rock, outline=0)
    for p in dome.data.polygons:
        p.flip()
    dome.location = (0, 3, -2)
    dome.scale = (24, 22, 15)
    env.append(dome)
    # Stalaktiten mit Lavatropfen
    for i in range(30):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(3, 15)
        p = Vector((math.cos(a) * r, math.sin(a) * r + 4, 11.5 - r * 0.25))
        c = A.cone('Stalac%d' % i, p, rnd.uniform(0.4, 1.0), rnd.uniform(2, 5), rock, rot=(PI, 0, 0), verts=7, outline=0.03)
        env.append(c)
        if i % 3 == 0:
            d = A.sphere('Drip%d' % i, p - Vector((0, 0, 2)), 0.12, A.glow('DripM', '#ffb040', 6), segments=8, outline=0)
            f0 = rnd.randint(139, 200)
            A.key(d, 1, loc=p - Vector((0, 0, 1.5)))
            A.key(d, f0, loc=p - Vector((0, 0, 1.5)))
            A.key(d, f0 + 30, loc=Vector((p.x, p.y, -0.5)))
            env.append(d)
    # Lavafälle an den Wänden
    fall = lava_mat('LavaFall', 4.0, 1.2, speed=-6.0)
    for i in range(9):
        a = PI * 0.15 + i / 8 * PI * 0.7 + rnd.uniform(-0.08, 0.08)
        p = Vector((math.cos(a) * 17, math.sin(a) * 15 + 3, 0))
        f = A.cube('LavaFall%d' % i, p + Vector((0, 0, 6)), (rnd.uniform(0.5, 1.3), 0.25, 7), fall, rot=(0, 0, a + PI / 2))
        env.append(f)
        env.append(rock_lump('FallRock%d' % i, p + Vector((0, 0, 0.3)), (2.4, 1.6, 0.9), rock, 500 + i))
    # Lavaflüsse (glühende Bänder) und Felssäulen
    for i in range(6):
        x0 = rnd.uniform(-12, 12)
        env.append(A.cube('River%d' % i, (x0, 6 + i * 1.7, -0.03), (rnd.uniform(3, 8), 0.4, 0.02), A.glow('RiverM', '#ffb347', 6), rot=(0, 0, rnd.uniform(-0.4, 0.4))))
    for i in range(10):
        a = rnd.uniform(0, math.tau)
        p = Vector((math.cos(a) * rnd.uniform(8, 14), math.sin(a) * rnd.uniform(8, 13) + 3, 0))
        for k in range(3):
            env.append(rock_lump('Pillar%d_%d' % (i, k), p + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 1.0 + k * 1.9)), (1.4 - k * 0.3, 1.3 - k * 0.3, 1.3), rock, 700 + i * 3 + k))
    # Licht: warmes Glühen von unten
    for i, (p, e) in enumerate((((0, 0, 0.5), 1500), ((-8, 8, 3), 4000), ((8, 9, 3), 4000), ((0, 14, 6), 5000))):
        li = bpy.data.lights.new('LavaL%d' % i, 'POINT')
        li.energy = e
        li.color = A._lin('#ff7a2a')
        li.shadow_soft_size = 2
        lo = bpy.data.objects.new('LavaL%d' % i, li)
        bpy.context.collection.objects.link(lo)
        lo.location = p
        show_from([lo], 151)
    sparks_rise('Ember', (0, 3, 0), '#ffb35c', 70, 139, FR + 40, radius=11, height=9, size=0.02)
    sparks_rise('Ember2', (0, 3, 0), '#ff6a1a', 40, 139, FR + 40, radius=5, height=5, size=0.012)
    expand(ctx, s, env=env)
    # Finisher: Eruptionen unter dem Gegner, Gegner verbrennt zu Asche (wie bisher, kräftiger)
    em_mat = A.glow('Erupt', '#ffb347', 8)
    for i in range(9):
        a = i / 9 * math.tau
        p = (FX + math.cos(a) * 0.6, math.sin(a) * 0.6, 0)
        c = A.cylinder('Erupt%d' % i, p, 0.22, 1.0, em_mat, outline=0)
        A.key(c, 1, scale=(1, 1, 0.001), loc=p)
        A.key(c, 196 + i * 2, scale=(1, 1, 0.001), loc=p)
        A.key(c, 206 + i * 2, scale=(1, 1, 4.5), loc=(p[0], p[1], 2.2))
        A.key(c, 228, scale=(0.3, 0.3, 4.5), loc=(p[0], p[1], 2.2))
        show_from([c], 196 + i * 2, 230)
    pillar = A.cylinder('BigErupt', (FX, 0, 0), 0.9, 1.0, A.glow('BigE', '#fff1c4', 10), outline=0)
    A.key(pillar, 1, scale=(1, 1, 0.001), loc=(FX, 0, 0))
    A.key(pillar, 210, scale=(1, 1, 0.001), loc=(FX, 0, 0))
    A.key(pillar, 214, scale=(1, 1, 7.0), loc=(FX, 0, 3.5))
    A.key(pillar, 226, scale=(0.05, 0.05, 7.0), loc=(FX, 0, 3.5))
    show_from([pillar], 210, 228)
    C.pose(Fo, 200, **{'upper.L': (-30, 0, -18), 'upper.R': (-30, 0, 18)})
    C.pose(Fo, 210, **{'upper.L': (-160, 0, -30), 'upper.R': (-160, 0, 30)}, spine=(-20, 0, 0))
    hide_fig('Foe', 214)
    shards('Ash', (FX, 0, 0), ['#3a3a3a', '#6b6b6b', '#ff7a1a'], 214, n=70, spread=1.6, up=3.0, size=0.06)
    C.pose(W, 190, **{'upper.R': (-80, 0, 15), 'fore.R': (-60, 0, 0)})
    C.pose(W, 200, **{'upper.R': (-100, 0, 10), 'fore.R': (-5, 0, 0)})
    C.hand_switch(W, 190, 'R', 'open')
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


def slot_reel(name, center, radius, width, symbols, body, sym_mats, spin_keys):
    """Walze, die sich korrekt um ihre waagerechte Achse (X) dreht. Symbole sitzen rundherum.
    spin_keys: [(bild, winkel)] – Winkel 0 = Symbol 0 vorne."""
    pivot = A.empty(name, center)
    pivot.rotation_mode = 'XYZ'
    drum = A.cylinder(name + 'Drum', (0, 0, 0), radius, width, body, rot=(0, PI / 2, 0), verts=48, outline=0.02)
    drum.parent = pivot
    parts = [drum]
    n = len(symbols)
    for k, sym in enumerate(symbols):
        th = k / n * math.tau
        t = text_obj(name + 'Sym%d' % k, sym, radius * 0.62, sym_mats[k % len(sym_mats)] if sym != '7' else sym_mats[0], extrude=0.03)
        t.location = (0, -(radius + 0.02) * math.cos(th), -(radius + 0.02) * math.sin(th))
        t.rotation_euler = (PI / 2 - th, 0, 0)
        t.parent = pivot
        parts.append(t)
    for f, ang in spin_keys:
        A.key(pivot, f, rot=(ang, 0, 0))
    return pivot, parts


def d_gamble():
    """Idle Death Gamble: Pachinko-Halle, riesiger Automat mit drei echten Walzen (drehen sich um ihre Achse),
    Lauflichter, Kugelregen, JACKPOT 7-7-7 – Hakari tanzt, wird von Jackpot-Energie umhüllt und schlägt zu."""
    dom = {'char': 'hakari', 'aura': '#ff5fb0', 'arena': '#1a0a14',
           'signPose': {'upper.R': (-90, 0, 10), 'fore.R': (-80, 0, 0), 'upper.L': (-90, 0, -10), 'fore.L': (-80, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('GambleSky', '#3a0a2a', '#0a0208', cloud='#5a1040', cloud_scale=3)
    env = [A.cube('GFloor', (0, 0, -0.02), (40, 40, 0.02), A.toon('GF', '#1a0b18', shade='#0a0408'))]
    # Lauflichter in Reihen (blinken im Wechsel)
    cols = ['#ffe27a', '#ff6fb8', '#6ff0ff', '#9dff7a']
    bulb_mats = []
    for i, c in enumerate(cols):
        m = A.glow('Bulb%d' % i, c, 6)
        em = m.node_tree.nodes.get('Emission')
        for f in range(139, FR + 1, 4):
            em.inputs['Strength'].default_value = 8 if ((f // 4) + i) % 4 == 0 else 1.5
            em.inputs['Strength'].keyframe_insert('default_value', frame=f)
        bulb_mats.append(m)
    for row in range(4):
        for k in range(46):
            a = PI * 0.15 + k / 45 * PI * 0.7
            r = 11 + row * 0.9
            env.append(A.sphere('Bulb%d_%d' % (row, k), (math.cos(a) * r, math.sin(a) * r + 2, 0.6 + row * 1.6), 0.09, bulb_mats[(k + row) % 4], segments=8, outline=0))
    # Pachinko-Automaten als Wände
    side = A.toon('PachiBody', '#6a0f3a', shade='#2a0418', highlight='#c0186a')
    glass = A.glow('PachiGlass', '#ffb0d8', 1.6)
    for i in range(14):
        a = PI * 0.08 + i / 13 * PI * 0.84
        p = Vector((math.cos(a) * 15, math.sin(a) * 15 + 2, 2.0))
        env.append(A.cube('Pachi%d' % i, tuple(p), (1.0, 0.5, 2.0), side, rot=(0, 0, a + PI / 2), outline=0.02))
        env.append(A.cube('PachiG%d' % i, tuple(p + Vector((0, 0, 0.4)) - Vector((math.cos(a), math.sin(a), 0)) * 0.52), (0.75, 0.02, 1.2), glass, rot=(0, 0, a + PI / 2)))
    # Riesiger Automat hinter Hakari
    body = A.toon('SlotBody', '#c0186a', shade='#5c0a32', highlight='#ff5fb0')
    gold = A.toon('SlotGold', '#ffd24a', shade='#9a7010', highlight='#fff3b0')
    sx0, sy0 = -1.0, 9.0
    env.append(A.cube('Slot', (sx0, sy0 + 0.5, 4.2), (4.6, 1.0, 3.6), body, outline=0.03))
    env.append(A.cube('SlotFrame', (sx0, sy0 - 0.52, 4.0), (4.0, 0.05, 1.9), gold, outline=0.02))
    env.append(A.cube('SlotWindow', (sx0, sy0 - 0.5, 4.0), (3.7, 0.06, 1.6), A.flat('SlotWin', '#120610')))
    top = A.cube('SlotTop', (sx0, sy0 + 0.3, 8.3), (3.4, 0.8, 0.7), A.glow('SlotTopM', '#ffe27a', 3), outline=0.02)
    env.append(top)
    lever = A.cylinder('Lever', (sx0 + 5.0, sy0, 5.0), 0.08, 2.4, gold, outline=0.01)
    knob = A.sphere('LeverKnob', (sx0 + 5.0, sy0, 6.25), 0.28, A.glow('KnobM', '#ff2a3a', 3), outline=0.012)
    env += [lever, knob]
    reel_body = A.toon('Reel', '#fbf6ee', shade='#c9bfae', highlight='#ffffff')
    sym_mats = [A.glow('Seven', '#ff1a2e', 3.5), A.flat('SymB', '#1a1a2e'), A.flat('SymG', '#1a8a3a'), A.flat('SymP', '#c0186a')]
    symbols = ['7', '3', '5', '1', '9', '2', '6', '4']
    reels = []
    for i, x in enumerate((-2.3, 0, 2.3)):
        stop = 196 + i * 6
        keys = [(1, 0.0), (139, 0.0)]
        # schnelles Drehen (konstant), dann Abbremsen mit kleinem Rückfedern, Endwinkel = Vielfaches von 2π → „7“ vorne
        turns = 14 + i * 2
        keys += [(stop - 6, turns * math.tau - 0.9), (stop, turns * math.tau + 0.12), (stop + 3, turns * math.tau)]
        pv, parts = slot_reel('Reel%d' % i, (sx0 + x, sy0 - 0.15, 4.0), 1.45, 1.8, symbols, reel_body, sym_mats, keys)
        for fc in A._fcurves(pv.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR' if int(round(kp.co.x)) < stop - 6 else 'BEZIER'
        env += parts
        reels.append(pv)
    jp = text_obj('Jackpot', 'JACKPOT!!', 1.0, A.glow('JPM', '#ffe27a', 7), extrude=0.08)
    jp.location = (sx0, sy0 - 0.6, 8.4)
    jp.rotation_euler = (PI / 2, 0, 0)
    A.key(jp, 1, scale=0.001)
    A.key(jp, 210, scale=0.001)
    A.key(jp, 214, scale=1.4)
    A.key(jp, 218, scale=1.0)
    env.append(jp)
    # Hebel wird gezogen (Hakari zieht im Geiste – Hebel schnappt runter)
    lever_root = A.empty('LeverRoot', (sx0 + 5.0, sy0, 3.8))
    for o in (lever, knob):
        A.parent_keep(o, lever_root)
    A.key(lever_root, 139, rot=(0, 0, 0))
    A.key(lever_root, 145, rot=(-0.9, 0, 0))
    A.key(lever_root, 152, rot=(0, 0, 0))
    # Kugelregen (Pachinko-Kugeln) nach dem Jackpot
    ball = A.toon('Ball', '#e6e9ef', shade='#7a8090', highlight='#ffffff')
    for i in range(70):
        b = A.sphere('PBall%d' % i, (0, 0, 0), 0.09, ball, segments=10, outline=0.004)
        p0 = Vector((sx0 + rnd.uniform(-3.5, 3.5), sy0 - 1.0, 2.0))
        f0 = 212 + rnd.randint(0, 20)
        d = Vector((rnd.uniform(-4, 4), rnd.uniform(-9, -3), 0))
        A.key(b, 1, loc=p0)
        A.key(b, f0, loc=p0)
        A.key(b, f0 + 10, loc=p0 + d * 0.5 + Vector((0, 0, 1.5)))
        A.key(b, f0 + 22, loc=p0 + d + Vector((0, 0, -1.9)))
        show_from([b], f0, f0 + 23)
    expand(ctx, s, env=env)
    # Jackpot-Energie: grüne, unsterbliche Aura um Hakari (Reverse-Effekt)
    aura = A.sphere('JPAura', (0, 0, 1.0), 0.62, A.glow('JPAuraM', '#7dff9a', 2.5, alpha=0.14), outline=0)
    aura.parent = W['arm']
    A.key(aura, 1, scale=0.001)
    A.key(aura, 214, scale=0.001)
    A.key(aura, 220, scale=(1.0, 1.0, 1.35))
    for f in range(222, FR + 1, 6):
        A.key(aura, f, scale=(1.0 + 0.06 * math.sin(f), 1.0 + 0.06 * math.sin(f), 1.35))
    sparks_rise('JPSpark', (0, 0, 0), '#9dff7a', 30, 214, FR + 40, radius=0.7, height=2.8, size=0.008, parent=W['arm'])
    # Hakari tanzt (Fieber-Tanz), während die Walzen laufen
    for k, f in enumerate(range(160, 200, 6)):
        s_ = 1 if k % 2 else -1
        C.pose(W, f, **{'upper.R': (-150 if s_ > 0 else -40, 0, 30), 'fore.R': (-40, 0, 0), 'upper.L': (-40 if s_ > 0 else -150, 0, -30),
                        'fore.L': (-40, 0, 0), 'spine': (0, 12 * s_, 6 * s_), 'pelvis': (0, -10 * s_, 0), 'head': (0, 0, 10 * s_)})
    C.pose(W, 204, **{'upper.R': (-160, 0, 20), 'fore.R': (-10, 0, 0), 'upper.L': (-160, 0, -20), 'fore.L': (-10, 0, 0), 'spine': (-10, 0, 0),
                      'pelvis': (0, 0, 0), 'head': (-15, 0, 0)})
    # Hakari stürmt los und schlägt zu – Gegner fliegt weg
    C.place(W, 1, (WX, 0, 0))
    C.place(W, 216, (WX, 0, 0))
    C.place(W, 222, (FX - 0.75, 0, 0))
    C.pose(W, 216, **{'upper.R': (-30, 0, 20), 'fore.R': (-100, 0, 0), 'upper.L': (-20, 0, -20), 'fore.L': (-60, 0, 0), 'spine': (15, 0, 0)})
    C.pose(W, 222, **{'upper.R': (-95, 0, 5), 'fore.R': (0, 0, 0), 'spine': (25, 0, 0)})
    C.hand_switch(W, 214, 'R', 'fist')
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
    A.key(imp, 1, scale=0.1)
    A.key(imp, 223, scale=0.1)
    A.key(imp, 232, scale=6)
    show_from([imp], 223, 233)
    hide_fig('Foe', 244)
    ctx['win_end_x'] = FX - 0.75
    # Kamera: Walzen groß im Bild, während sie stoppen
    ctx['extra_cuts'] = [209]
    camera_track(ctx, [
        (181, (sx0 + 0.3, sy0 - 7.5, 4.2), (sx0, sy0, 4.1), 30), (209, (sx0 + 0.2, sy0 - 6.2, 4.3), (sx0, sy0, 4.2), 34),
        (210, (0.2, -4.4, 1.6), (0.6, 0, 1.5), 28), (246, (0.6, -4.8, 2.0), (0.8, 0, 1.5), 28),
    ])
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


def rika(name, loc, face_dir=0.0):
    """Rika (eigene Interpretation): riesige, bleiche Fluch-Gestalt hinter Yuta – Kopf mit langen Haaren,
    breites Maul, lange Arme mit Krallen; leuchtet rosa."""
    root = A.empty(name, loc)
    pale = A.toon(name + 'Pale', '#e8e2ec', shade='#9a8aa8', highlight='#ffffff')
    hairm = A.toon(name + 'Hair', '#1a1420', shade='#060408')
    dark = A.flat(name + 'Maw', '#1a0610')
    eye = A.glow(name + 'Eye', '#ff9ad0', 6)
    teeth = A.toon(name + 'Teeth', '#fbf8f2')
    parts = [C.ellipsoid(name + 'Head', (0, 0, 4.2), (0.9, 0.8, 1.0), pale, seg=28)]
    for sx in (-1, 1):
        parts.append(C.ellipsoid(name + 'Eye%d' % sx, (sx * 0.32, -0.72, 4.45), (0.16, 0.05, 0.1), eye, seg=12))
    parts.append(C.ellipsoid(name + 'MawO', (0, -0.62, 3.75), (0.55, 0.25, 0.28), dark, seg=20))
    for i in range(9):
        x = -0.44 + i * 0.11
        parts.append(C.sweep(name + 'T%d' % i, [(x, -0.78, 3.92), (x, -0.8, 3.8)], [0.035, 0.002], teeth, ring_n=6, rings=3))
        parts.append(C.sweep(name + 'B%d' % i, [(x, -0.78, 3.58), (x, -0.8, 3.7)], [0.035, 0.002], teeth, ring_n=6, rings=3))
    for i in range(18):   # lange Haare
        a = -PI * 0.9 + i / 17 * PI * 1.8
        r0 = Vector((math.sin(a) * 0.85, math.cos(a) * 0.5 + 0.2, 4.7))
        parts.append(C.sweep(name + 'H%d' % i, [r0, r0 + Vector((math.sin(a) * 0.4, 0.4, -1.0)), r0 + Vector((math.sin(a) * 0.7, 0.7, -2.6))],
                             [0.22, 0.16, 0.01], hairm, ring_n=8, rings=10, flat=0.5))
    parts.append(C.ellipsoid(name + 'Body', (0, 0.4, 2.3), (1.1, 0.9, 1.6), pale, seg=24))
    for sx in (-1, 1):
        sh = Vector((sx * 1.0, 0.0, 3.2))
        pts = [sh, sh + Vector((sx * 0.9, -0.6, -0.4)), sh + Vector((sx * 1.3, -1.6, -0.2)), sh + Vector((sx * 1.2, -2.4, 0.3))]
        parts.append(C.sweep(name + 'Arm%d' % sx, pts, [0.32, 0.26, 0.2, 0.16], pale, ring_n=14, rings=18))
        hand = C.hand_mesh(name + 'Hand%d' % sx, 'R' if sx < 0 else 'L', 'claw', pale, scale=7.0)
        hand.location = pts[-1]
        hand.rotation_euler = (math.radians(70), 0, sx * 0.4)
        parts.append(hand)
    for p in parts:
        p.parent = root
        A.no_ink(p)
        A.add_outline(p, 0.02)
    root.rotation_euler = (0, 0, face_dir)
    return root, parts


def d_swords():
    """Authentic Mutual Love: Feld aus Schwertern im Boden, Rika erscheint riesig hinter Yuta,
    die Schwerter steigen auf, drehen sich mit der SPITZE zum Gegner und schlagen in Wellen ein."""
    dom = {'char': 'yuta', 'aura': '#ff7cc4', 'arena': '#1a1218',
           'signPose': {'upper.R': (-80, 0, 30), 'fore.R': (-90, 0, 0), 'upper.L': (-80, 0, -30), 'fore.L': (-90, 0, 0)}, 'twoHands': True}
    ctx = common(dom)
    W, Fo = ctx['W'], ctx['F']
    s = sky('SwordSky', '#f6d3e6', '#7a4a66', cloud='#ffffff', cloud_scale=1.2)
    env = [A.cube('SwordGround', (0, 0, -0.02), (40, 40, 0.02), A.toon('SG', '#c9bfc8', shade='#7d7380'))]
    steel = A.toon('Steel', '#e9eef6', shade='#8f9bb0', highlight='#ffffff')
    hilt = A.toon('Hilt', '#2a1d2a')
    flyers = []
    for i in range(150):
        x, y = rnd.uniform(-14, 14), rnd.uniform(-3, 16)
        if abs(x - WX) < 1.2 and abs(y) < 1.5 or abs(x - FX) < 1.4 and abs(y) < 1.4:
            continue
        sc = rnd.uniform(0.9, 1.4)
        # im Boden: Klinge zeigt nach UNTEN (Spitze im Boden), Griff oben
        root, parts = katana('Kat%d' % i, (x, y, 0.75 * sc), (rnd.uniform(-0.25, 0.25) + PI, rnd.uniform(-0.25, 0.25), rnd.uniform(0, 6)), steel, hilt, s=sc)
        env += parts
        if len(flyers) < 34 and abs(y) < 9:
            flyers.append((root, sc))
    # Rika hinter Yuta
    rk, rparts = rika('Rika', (WX - 2.4, 1.4, -0.2), face_dir=-PI / 2 + 0.35)
    ctx['second'] = ((WX + 3.4, -2.6, 0.5), (WX - 1.6, 1.0, 2.8), (WX + 2.8, -2.2, 0.7), (WX - 1.6, 1.0, 3.1), 22)
    env += rparts
    A.key(rk, 1, scale=0.001)
    A.key(rk, 160, scale=0.001)
    A.key(rk, 176, scale=1.05)
    A.key(rk, 182, scale=1.0)
    li = bpy.data.lights.new('RikaGlow', 'POINT')
    li.energy = 2500
    li.color = A._lin('#ff7cc4')
    lo = bpy.data.objects.new('RikaGlow', li)
    bpy.context.collection.objects.link(lo)
    lo.location = (WX - 2.0, 0.0, 3.5)
    show_from([lo], 151)
    expand(ctx, s, env=env)
    # Schwerter heben ab, richten die SPITZE auf den Gegner und schlagen in drei Wellen ein
    target = Vector((FX, 0, 1.15))
    for i, (root, sc) in enumerate(flyers):
        p0 = root.location.copy()
        r0 = tuple(root.rotation_euler)
        wave = i % 3
        f0 = 184 + wave * 7 + (i // 3) % 4
        A.key(root, 1, loc=p0, rot=r0)
        A.key(root, f0, loc=p0, rot=r0)
        up = p0 + Vector((0, 0, 2.6 + rnd.uniform(0, 2.2)))
        hit = target + Vector((rnd.uniform(-0.22, 0.22), rnd.uniform(-0.25, 0.25), rnd.uniform(-0.55, 0.55)))
        d = (hit - up).normalized()
        aim = Vector((0, 0, 1)).rotation_difference(d).to_euler()   # Klinge (+Z) zeigt zum Ziel
        A.key(root, f0 + 6, loc=up, rot=r0)
        A.key(root, f0 + 9, loc=up + Vector((0, 0, 0.15)), rot=tuple(aim))
        # Spitze steckt im Gegner: Wurzel (Stichblatt) liegt 0,62 Klingenlängen vor dem Treffpunkt
        A.key(root, f0 + 13, loc=hit - d * 0.62 * sc, rot=tuple(aim))
        A.key(root, 246, loc=hit - d * 0.62 * sc, rot=tuple(aim))
        A.key(root, 247, loc=hit - d * 0.62 * sc + Vector((0, 0, -30)), rot=tuple(aim))
        for fc in A._fcurves(root.animation_data.action):
            for kp in fc.keyframe_points:
                if int(round(kp.co.x)) in (f0 + 9, 246):
                    kp.interpolation = 'LINEAR'
    C.pose(W, 184, **{'upper.R': (-80, 0, 30), 'fore.R': (-90, 0, 0)})
    C.pose(W, 192, **{'upper.R': (-170, 0, 10), 'fore.R': (-10, 0, 0)})
    C.pose(W, 214, **{'upper.R': (-80, 0, 20), 'fore.R': (-20, 0, 0)})
    for f in range(196, 230, 3):   # Gegner zuckt bei jedem Treffer
        C.pose(Fo, f, spine=(rnd.uniform(-12, 18), rnd.uniform(-8, 8), 0), head=(rnd.uniform(-20, 20), 0, rnd.uniform(-15, 15)))
    flash_at(ctx, [199, 206, 232])
    # Schluss: rosa Explosion, Gegner zerfällt
    burst = A.sphere('LoveBurst', tuple(target), 0.3, A.glow('LoveM', '#ff9ad0', 8, alpha=0.6), outline=0)
    A.key(burst, 1, scale=0.001)
    A.key(burst, 232, scale=0.001)
    A.key(burst, 240, scale=3.5)
    A.key(burst, 248, scale=5.0)
    show_from([burst], 232, 249)
    hide_fig('Foe', 233)
    shards('FoeSw', (FX, 0, 0), ['#2a1236', '#120b16', '#9a8aa8', '#ff9ad0'], 233, n=70, spread=2.6)
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
    dom = {'char': 'dagon', 'aura': '#22d3ee', 'arena': '#0c1820', 'eyeZ': 1.86, 'eyeFront': 0.163,
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


# ═════════════════════════ Länger & detailreicher ═════════════════════════
# Die Szenen werden mit 288 Bildern gebaut und danach auf 432 Bilder (18 s) gestreckt –
# jede Einstellung bekommt mehr Zeit, besonders Domain-Entfaltung und Finisher.
SEG_OLD = [1, 43, 63, 111, 139, 181, 247, 289]
SEG_NEW = [1, 61, 85, 151, 191, 281, 381, 433]
FR_LONG = 432


def T(f):
    """Altes Bild → neues Bild (stückweise linear)."""
    for i in range(len(SEG_OLD) - 1):
        a, b = SEG_OLD[i], SEG_OLD[i + 1]
        if f < b or i == len(SEG_OLD) - 2:
            A2, B2 = SEG_NEW[i], SEG_NEW[i + 1]
            return A2 + (f - a) * (B2 - A2) / (b - a)
    return f


def retime(seg_old=None, seg_new=None, frames=None):
    global SEG_OLD, SEG_NEW
    if seg_old:
        SEG_OLD, SEG_NEW = seg_old, seg_new
    for act in bpy.data.actions:
        for fc in A._fcurves(act):
            for kp in fc.keyframe_points:
                x = kp.co.x
                kp.co.x = T(x)
                kp.handle_left.x = T(kp.handle_left.x)
                kp.handle_right.x = T(kp.handle_right.x)
            fc.update()
    bpy.context.scene.frame_end = frames or FR_LONG


def speedlines(cam, ranges, color='#ffffff'):
    """Anime-Speedlines: dünne Streifen rund um die Bildmitte, direkt vor der Kamera."""
    mat = A.glow('SpeedM', color, 2.5, alpha=0.55)
    root = A.empty('Speed', (0, 0, -0.5))
    root.parent = cam
    lines = []
    r = random.Random(4)
    for i in range(46):
        a = i / 46 * math.tau + r.uniform(-0.05, 0.05)
        d = r.uniform(0.22, 0.32)
        ln = A.cube('Speed%d' % i, (math.cos(a) * (d + 0.12), math.sin(a) * (d + 0.12), 0), (0.12, 0.0016, 0.001), mat, rot=(0, 0, a))
        ln.parent = root
        lines.append(ln)
    for o in lines:
        A.visible(o, 1, False)
        for f0, f1 in ranges:
            A.visible(o, f0, True)
            A.visible(o, f1, False)
    # Größe an die Brennweite koppeln, damit die Linien immer am Bildrand liegen
    lens_fc = None
    if cam.data.animation_data and cam.data.animation_data.action:
        for fc in A._fcurves(cam.data.animation_data.action):
            if fc.data_path == 'lens':
                lens_fc = fc
    for f in range(1, FR_LONG, 2):
        lens = lens_fc.evaluate(f) if lens_fc else cam.data.lens
        k = 33.0 / max(lens, 10)
        A.key(root, f, rot=(0, 0, r.uniform(-0.15, 0.15)), scale=(k, k, 1))
    A.set_interp(root, 'CONSTANT')


def shake(cam, frames, strength=0.06, length=10):
    """Kamera-Wackeln nach Treffern (F-Kurven-Rauschen, zeitlich begrenzt)."""
    for fc in A._fcurves(cam.animation_data.action):
        if fc.data_path != 'location':
            continue
        for f in frames:
            m = fc.modifiers.new('NOISE')
            m.scale = 1.5
            m.strength = strength
            m.phase = f * 0.37 + fc.array_index * 11
            m.use_restricted_range = True
            m.frame_start = f
            m.frame_end = f + length
            m.blend_in = 1
            m.blend_out = length * 0.6


def shockwave(center, f0, color, life=16, size=6.0):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.025, location=center)
    t = bpy.context.active_object
    A.set_mat(t, A.glow('Shock_' + color, color, 5))
    A.key(t, 1, scale=0.05)
    A.key(t, f0, scale=0.05)
    A.key(t, f0 + life, scale=size)
    show_from([t], f0, f0 + life + 1)
    return t


def black_frames(ctx, frames):
    """Impact-Frame: ein schwarzes Bild direkt nach dem weißen Blitz."""
    bl = A.cube('ImpactBlack', (0, 0, -0.59), (2, 2, 0.01), A.glow('BlackM', '#000000', 0), outline=0)
    bl.parent = ctx['cam']
    A.visible(bl, 1, False)
    for f in frames:
        A.visible(bl, f, True)
        A.visible(bl, f + 1, False)


def finish_scene(ctx):
    """Nach dem Bauen: strecken, zweite Domain-Einstellung, Speedlines, Wackeln, Impact-Frames, Schockwellen."""
    flashes = sorted(set(ctx.get('flashes', [])))
    retime()
    cam, tgt = ctx['cam'], ctx['tgt']
    # Zweite Einstellung in der Domain-Welt: Untersicht hinter dem Sieger, langsamer Vorwärtsflug
    for o in (cam, tgt):
        o.animation_data.action  # sicherstellen, dass es existiert
    rv = ctx.get('reveal')
    if rv:
        A.cam_key(cam, tgt, 235, rv[-1][1], rv[-1][2], rv[-1][3])
    else:
        A.cam_key(cam, tgt, 235, (4.5, -6.3, 3.6), (0, 0, 1.3), 24)
    sec = ctx.get('second') or ((WX - 1.6, -1.1, 0.35), (WX + 3.0, 3.5, 2.6), (WX - 1.1, -0.8, 0.5), (WX + 3.0, 3.5, 2.8), 20)
    A.cam_key(cam, tgt, 236, sec[0], sec[1], sec[4])
    A.cam_key(cam, tgt, 279, sec[2], sec[3], sec[4])
    for o in (cam, tgt):
        for fc in A._fcurves(o.animation_data.action):
            for kp in fc.keyframe_points:
                if int(round(kp.co.x)) in (235, 279):
                    kp.interpolation = 'CONSTANT'
    newf = [int(T(f)) for f in flashes]
    speedlines(cam, [(61, 84), (281, 300)] + [(f, f + 8) for f in newf])
    shake(cam, [1, 191] + newf, strength=0.05, length=12)
    black_frames(ctx, [f + 2 for f in newf])
    dom = ctx['dom']
    shockwave((0, 0, 0.05), 6, dom['aura'], life=24, size=5)
    shockwave((0, 0, 0.05), 30, '#ffffff', life=24, size=6)
    shockwave((WX, 0, 0.05), 191, dom['aura'], life=30, size=14)
    for f in newf:
        shockwave((FX, 0, 0.05), f, '#ffffff', life=14, size=4)


DOMAINS = {'void': d_void, 'shrine': d_shrine, 'shadow': d_shadow, 'hands': d_hands, 'volcano': d_volcano,
           'court': d_court, 'gamble': d_gamble, 'swords': d_swords, 'beach': d_beach, 'frames': d_frames}

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    for a in list(argv):
        if a.startswith('foe='):
            FOE_KEY = a[4:]
            argv.remove(a)
    name, mode, out = argv[0], argv[1], argv[2]
    os.makedirs(out, exist_ok=True)
    ctx = DOMAINS[name]()
    finish_scene(ctx)
    if mode == 'preview':
        fr = [int(x) for x in argv[3].split(',')] if len(argv) > 3 else [20, 70, 110, 170, 215, 255, 300, 330, 350, 400]
        A.render_frames(out, fr)
    else:
        A.render_frames(out)
    print('FERTIG', name)
