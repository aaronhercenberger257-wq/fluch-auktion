"""Anime-Toon-Baukasten für Blender 5.x (wird von den Domain-Szenen importiert).

Stil: Cel-Shading (harte Schattenstufen über Shader-to-RGB + konstante Farbrampe),
schwarze Umrisse per „Inverted Hull“, Leuchteffekte über Emission.
"""
import bpy
import math
import random
from mathutils import Vector, Euler

FPS = 24


# ───────────────────────── Szene ─────────────────────────
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


# ───────────────────────── Tusche (Freestyle-Linien) ─────────────────────────
def ink_collection():
    """Sammlung für alles, was Freestyle-Linien bekommt (Figuren)."""
    col = bpy.data.collections.get('Ink')
    if not col:
        col = bpy.data.collections.new('Ink')
        bpy.context.scene.collection.children.link(col)
    return col


def no_ink(obj):
    """Objekt aus der Tusche-Sammlung nehmen (z. B. Gesichts-Decals)."""
    col = ink_collection()
    if obj.name in col.objects:
        col.objects.unlink(obj)
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)


def to_ink(obj):
    col = ink_collection()
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def ink(thickness=1.4, color='#120c14', crease=136, taper=True):
    """Freestyle: Umriss-, Kanten- und Faltenlinien für die Sammlung „Ink“ (Anime-Lineart)."""
    s = bpy.context.scene
    s.render.use_freestyle = True
    s.render.line_thickness_mode = 'ABSOLUTE'
    s.render.line_thickness = 1.0
    vl = s.view_layers[0]
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(crease)
    fs.use_culling = True
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('Ink')
    ls.select_by_collection = True
    ls.collection = ink_collection()
    ls.select_by_visibility = True
    ls.visibility = 'VISIBLE'
    ls.select_by_edge_types = True
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_contour = True
    ls.select_external_contour = True
    ls.select_material_boundary = False
    st = ls.linestyle
    if st is None:
        st = bpy.data.linestyles.new('InkStyle')
        ls.linestyle = st
    st.color = _lin(color)
    st.thickness = thickness
    st.thickness_position = 'CENTER'
    st.chaining = 'PLAIN'
    st.use_same_object = True
    if taper and not any(m.type == 'ALONG_STROKE' for m in st.thickness_modifiers):
        m = st.thickness_modifiers.new('Taper', 'ALONG_STROKE')
        m.mapping = 'CURVE'
        m.value_min = 0.35
        m.value_max = 1.0
        cm = m.curve
        pts = cm.curves[0].points
        pts[0].location = (0.0, 0.0)
        pts[1].location = (1.0, 0.0)
        pts.new(0.15, 1.0)
        pts.new(0.85, 1.0)
        cm.update()
    return ls


def setup_render(frames, res=(1280, 720), samples=16, motion_blur=True):
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, frames
    s.eevee.taa_render_samples = samples
    s.render.use_motion_blur = motion_blur
    s.render.motion_blur_shutter = 0.6
    s.view_settings.view_transform = 'Standard'
    s.view_settings.look = 'None'
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    world = bpy.data.worlds.new('World')
    s.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0, 0, 0, 1)
    bg.inputs['Strength'].default_value = 0
    return s


def set_world_color(rgb, strength=1.0):
    bg = bpy.context.scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (*rgb, 1)
    bg.inputs['Strength'].default_value = strength
    return bg


def add_bloom(size=6, threshold=0.9, mix=0.35):
    """Leuchten (Glare) im Compositor – Blender 5 nutzt eine eigene Node-Gruppe."""
    s = bpy.context.scene
    try:
        tree = bpy.data.node_groups.new('AnimeComp', 'CompositorNodeTree')
        s.compositing_node_group = tree
        rl = tree.nodes.new('CompositorNodeRLayers')
        glare = tree.nodes.new('CompositorNodeGlare')
        out = tree.nodes.new('NodeGroupOutput')
        tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        for name, val in (('Type', 'Bloom'), ('Quality', 'High')):
            if name in glare.inputs:
                try:
                    glare.inputs[name].default_value = val
                except Exception:
                    pass
        for attr, val in (('glare_type', 'BLOOM'), ('quality', 'HIGH')):
            if hasattr(glare, attr):
                try:
                    setattr(glare, attr, val)
                except Exception:
                    pass
        for name, val in (('Threshold', threshold), ('Size', size / 9 if size > 1 else size), ('Strength', mix)):
            if name in glare.inputs:
                try:
                    glare.inputs[name].default_value = val
                except Exception:
                    pass
        tree.links.new(rl.outputs['Image'], glare.inputs['Image'])
        tree.links.new(glare.outputs['Image'], out.inputs[0])
        return True
    except Exception as e:  # Compositor-API anders → ohne Bloom weiter
        print('BLOOM nicht verfügbar:', e)
        return False


# ───────────────────────── Materialien ─────────────────────────
_mats = {}


def _lin(c):
    """sRGB-Hex → lineares RGB (Blender erwartet linear)."""
    if isinstance(c, str):
        c = c.lstrip('#')
        c = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def toon(name, color, shade=None, highlight=None, steps=(0.38, 0.86)):
    """Cel-Shading: Licht → Shader-to-RGB → harte Farbstufen → Emission (flache Anime-Farben)."""
    key = ('toon', name)
    if key in _mats:
        return _mats[key]
    base = _lin(color)
    sh = _lin(shade) if shade else tuple(x * 0.38 for x in base)
    hi = _lin(highlight) if highlight else tuple(min(1, x * 1.25 + 0.06) for x in base)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
    s2r = nt.nodes.new('ShaderNodeShaderToRGB')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    em = nt.nodes.new('ShaderNodeEmission')
    cr = ramp.color_ramp
    cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*sh, 1)
    cr.elements[1].position = steps[0]
    cr.elements[1].color = (*base, 1)
    e = cr.elements.new(steps[1])
    e.color = (*hi, 1)
    nt.links.new(diff.outputs['BSDF'], s2r.inputs['Shader'])
    nt.links.new(s2r.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    _mats[key] = m
    return m


def flat(name, color):
    """Unbeleuchtete Flächenfarbe (für Augen, Wimpern, Tattoos)."""
    key = ('flat', name)
    if key in _mats:
        return _mats[key]
    m = glow(name, color, 1.0)
    _mats[key] = m
    return m


def glow(name, color, strength=6.0, alpha=1.0):
    key = ('glow', name)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*_lin(color), 1)
    em.inputs['Strength'].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mix = nt.nodes.new('ShaderNodeMixShader')
        mix.inputs['Fac'].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
        m.surface_render_method = 'BLENDED'
    else:
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    _mats[key] = m
    return m


def outline_mat():
    key = ('outline',)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new('Outline')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1)
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = True
    _mats[key] = m
    return m


def add_outline(obj, thickness=0.018):
    """Inverted Hull: eine etwas größere, nach innen gedrehte schwarze Hülle = Anime-Umriss."""
    if obj.type != 'MESH':
        return
    obj.data.materials.append(outline_mat())
    mod = obj.modifiers.new('Outline', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = len(obj.data.materials) - 1


def set_mat(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ───────────────────────── Primitive ─────────────────────────
def _active():
    return bpy.context.active_object


def sphere(name, loc, scale, mat, segments=32, outline=0.018, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments // 2, location=loc)
    o = _active()
    o.name = name
    o.scale = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    set_mat(o, mat)
    if smooth:
        bpy.ops.object.shade_smooth()
    if outline:
        add_outline(o, outline)
    return o


def cylinder(name, loc, radius, depth, mat, rot=(0, 0, 0), r2=None, verts=24, outline=0.018):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = _active()
    o.name = name
    set_mat(o, mat)
    bpy.ops.object.shade_smooth()
    if outline:
        add_outline(o, outline)
    return o


def cone(name, loc, r1, depth, mat, rot=(0, 0, 0), r2=0.0, verts=12, outline=0.012):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = _active()
    o.name = name
    set_mat(o, mat)
    bpy.ops.object.shade_smooth()
    if outline:
        add_outline(o, outline)
    return o


def cube(name, loc, scale, mat, rot=(0, 0, 0), outline=0.0, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = _active()
    o.name = name
    o.scale = scale
    set_mat(o, mat)
    if bevel:
        mod = o.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
    if outline:
        add_outline(o, outline)
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def parent_keep(child, parent):
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


# ───────────────────────── Figuren ─────────────────────────
def build_figure(prefix, cfg, loc=(0, 0, 0), facing=0.0):
    """Stilisierte Anime-Figur aus Grundformen mit Gelenken (Empties).

    cfg: skin, hair, hairStyle, coat, coatShade, trim, eyes, eyeGlow, extra(fn)
    Rückgabe: dict mit Gelenken root/hips/chest/neck/head/sh_l/sh_r/el_l/el_r/hip_l/hip_r
    """
    bpy.context.view_layer.update()
    skin = toon(prefix + 'Skin', cfg.get('skin', '#f3d6c4'), shade='#c99a86')
    coat = toon(prefix + 'Coat', cfg['coat'], shade=cfg.get('coatShade'))
    trim = toon(prefix + 'Trim', cfg.get('trim', '#334155'))
    hair = toon(prefix + 'Hair', cfg['hair'], shade=cfg.get('hairShade'))
    shoe = toon(prefix + 'Shoe', '#111111')

    J = {}
    root = empty(prefix + 'Root', loc)
    root.rotation_euler = (0, 0, facing)
    J['root'] = root
    hips = empty(prefix + 'Hips', (0, 0, 0.98), root)
    J['hips'] = hips
    chest = empty(prefix + 'Chest', (0, 0, 0.32), hips)
    J['chest'] = chest
    neck = empty(prefix + 'Neck', (0, 0, 0.36), chest)
    J['neck'] = neck
    head = empty(prefix + 'Head', (0, 0, 0.14), neck)
    J['head'] = head

    def at(obj, parent):
        obj.parent = parent
        return obj

    # Rumpf: Jacke (Kegelstumpf), Hüfte, hoher Kragen
    at(cylinder(prefix + 'Torso', (0, 0, 0.2), 0.19, 0.62, coat, r2=0.27, verts=28), hips).scale = (1.05, 0.7, 1)
    at(cylinder(prefix + 'NeckMesh', (0, 0, 0.06), 0.055, 0.16, skin, verts=16, outline=0.01), neck)
    at(cylinder(prefix + 'Waist', (0, 0, -0.05), 0.2, 0.18, coat, verts=28), hips).scale = (1, 0.75, 1)
    collar = at(cylinder(prefix + 'Collar', (0, 0, -0.02), 0.11, 0.16, coat, r2=0.12, verts=24), neck)
    collar.scale = (1, 0.95, 1)
    at(cylinder(prefix + 'Zip', (0, -0.18, 0.22), 0.012, 0.6, trim, outline=0), hips)
    # Kopf
    hd = at(sphere(prefix + 'HeadMesh', (0, 0, 0.12), (0.155, 0.15, 0.175), skin), head)
    J['headMesh'] = hd
    # Augen (Anime: große, flache Ovale)
    eyeMat = glow(prefix + 'Eye', cfg.get('eyes', '#38bdf8'), cfg.get('eyeGlow', 3.0))
    for sx in (-1, 1):
        e = at(sphere(prefix + 'Eye' + str(sx), (0.055 * sx, -0.135, 0.12), (0.035, 0.012, 0.022), eyeMat, outline=0.006), head)
        e.rotation_euler = (0, 0, 0.15 * sx)
    mouth = toon(prefix + 'Mouth', '#6b2a2a')
    at(sphere(prefix + 'MouthMesh', (0, -0.145, 0.03), (0.025, 0.006, 0.006), mouth, segments=12, outline=0), head)
    # Haare
    style = cfg.get('hairStyle', 'spiky')
    rnd = random.Random(hash(prefix) & 0xffff)
    at(sphere(prefix + 'HairCap', (0, 0.01, 0.17), (0.17, 0.165, 0.15), hair), head)
    if style in ('spiky', 'short'):
        n = 26 if style == 'spiky' else 18
        length = 0.24 if style == 'spiky' else 0.14
        for i in range(n):
            a = i / n * math.tau
            tilt = rnd.uniform(0.55, 1.05)
            r = 0.13
            p = (math.cos(a) * r * 0.9, math.sin(a) * r * 0.9 + 0.02, 0.2 + rnd.uniform(-0.02, 0.04))
            c = cone(prefix + 'Spike%d' % i, p, 0.06, length * rnd.uniform(0.8, 1.2), hair, outline=0.01)
            dirv = Vector((math.cos(a) * tilt, math.sin(a) * tilt, 1.0)).normalized()
            c.rotation_mode = 'QUATERNION'
            c.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(dirv)
            c.location += dirv * (length * 0.45)
            at(c, head)
        # Strähnen in die Stirn
        for i, x in enumerate((-0.07, 0.0, 0.07)):
            c = cone(prefix + 'Fringe%d' % i, (x, -0.13, 0.2), 0.04, 0.12, hair, rot=(math.radians(160), 0, x * 3), outline=0.008)
            at(c, head)
    # Arme (Schulter → Ellbogen → Hand)
    for side, sx in (('l', 1), ('r', -1)):
        sh = empty(prefix + 'Sh' + side, (0.27 * sx, 0, 0.27), chest)
        J['sh_' + side] = sh
        at(cylinder(prefix + 'Up' + side, (0, 0, -0.16), 0.065, 0.34, coat, r2=0.058), sh)
        at(sphere(prefix + 'ShBall' + side, (0, 0, 0), 0.075, coat), sh)
        el = empty(prefix + 'El' + side, (0, 0, -0.33), sh)
        J['el_' + side] = el
        at(cylinder(prefix + 'Fore' + side, (0, 0, -0.15), 0.056, 0.3, coat, r2=0.05), el)
        at(cylinder(prefix + 'Cuff' + side, (0, 0, -0.3), 0.052, 0.03, trim, outline=0.008), el)
        hand = at(sphere(prefix + 'Hand' + side, (0, 0, -0.36), (0.05, 0.035, 0.07), skin, outline=0.01), el)
        J['hand_' + side] = hand
        # Beine (Hüfte → Knie)
        hp = empty(prefix + 'Hip' + side, (0.1 * sx, 0, -0.08), hips)
        J['hip_' + side] = hp
        at(cylinder(prefix + 'Thigh' + side, (0, 0, -0.22), 0.09, 0.46, coat, r2=0.075), hp)
        kn = empty(prefix + 'Knee' + side, (0, 0, -0.45), hp)
        J['knee_' + side] = kn
        at(cylinder(prefix + 'Shin' + side, (0, 0, -0.22), 0.07, 0.44, coat, r2=0.06), kn)
        at(cube(prefix + 'Shoe' + side, (0, -0.04, -0.46), (0.06, 0.12, 0.04), shoe, outline=0.01, bevel=0.02), kn)
    if cfg.get('extra'):
        cfg['extra'](prefix, J)
    return J


# ───────────────────────── Animation ─────────────────────────
def key(obj, frame, loc=None, rot=None, scale=None, interp=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert('location', frame=frame)
    if rot is not None:
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = rot
        obj.keyframe_insert('rotation_euler', frame=frame)
    if scale is not None:
        obj.scale = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
        obj.keyframe_insert('scale', frame=frame)
    if interp:
        set_interp(obj, interp)


def set_interp(obj, interp='BEZIER', easing=None):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in _fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            if easing:
                kp.easing = easing


def _fcurves(action):
    """Blender 5: Animation steckt in Layern/Strips/Channelbags."""
    if hasattr(action, 'fcurves'):
        try:
            return list(action.fcurves)
        except Exception:
            pass
    out = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for cb in getattr(strip, 'channelbags', []):
                out.extend(cb.fcurves)
    return out


def key_value(socket_owner, path, frame, value):
    setattr(socket_owner, path, value) if not hasattr(socket_owner, 'default_value') else None
    if hasattr(socket_owner, 'default_value'):
        socket_owner.default_value = value
        socket_owner.keyframe_insert('default_value', frame=frame)
    else:
        socket_owner.keyframe_insert(path, frame=frame)


def camera(name='Cam', lens=35):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_end = 500
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    target = empty(name + 'Target')
    tc = cam.constraints.new('TRACK_TO')
    tc.target = target
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'
    return cam, target


def cam_key(cam, target, frame, pos, look, lens=None, roll=None):
    key(cam, frame, loc=pos)
    key(target, frame, loc=look)
    if lens is not None:
        cam.data.lens = lens
        cam.data.keyframe_insert('lens', frame=frame)


def sun(strength=3.0, rot=(math.radians(50), math.radians(10), math.radians(-30)), color=(1, 1, 1)):
    d = bpy.data.lights.new('Sun', 'SUN')
    d.energy = strength
    d.color = color
    d.angle = 0.0
    d.use_shadow = False  # sauberer Cel-Look: Schattierung nur über die Toon-Stufen
    o = bpy.data.objects.new('Sun', d)
    bpy.context.collection.objects.link(o)
    o.rotation_euler = rot
    return o


def visible(obj, frame, show):
    """Ein-/Ausblenden über Skalierung (funktioniert auch mit Eltern-Objekten)."""
    obj.hide_render = not show
    obj.keyframe_insert('hide_render', frame=frame)
    obj.hide_viewport = not show
    obj.keyframe_insert('hide_viewport', frame=frame)


def render_frames(out_dir, frames=None):
    s = bpy.context.scene
    if frames:
        for f in frames:
            s.frame_set(f)
            s.render.filepath = '%s/frame_%04d.png' % (out_dir, f)
            bpy.ops.render.render(write_still=True)
    else:
        s.render.filepath = out_dir + '/frame_'
        bpy.ops.render.render(animation=True)
