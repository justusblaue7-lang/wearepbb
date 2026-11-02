"""Materials: scanned PBR sets from Poly Haven (render/assets/textures) plus tuned procedural shaders.

Brand colour: every lilac in the hall is the Flieder of the PBB neon sign (BRAND, the same value as --lilac on the
website). AgX rolls bright colours off towards white and turns violets blue, so colours are set for what the still
shows, not what the shader gets: emitters seen by the camera go through the inverse of the view transform
(on_screen), painted surfaces carry an albedo measured from test renders (FLIEDER)."""
import pathlib

import bpy
import numpy as np

TEX = pathlib.Path(__file__).resolve().parents[1] / "assets" / "textures"
VIEW, LOOK = "AgX", "AgX - Medium High Contrast"
BRAND = "#d7a7f3"            # tube colour of assets/brand/pbb-neon.jpg
BRAND_CORE = "#dcaef5"       # a touch lighter in the middle of a neon tube, so it reads round
# Linear albedo of the court paint (kitchens, floor logos): solved from the light passes of test renders so the kitchen
# shows as #c797e2 (the brand colour one step deeper) under the court high-bays at exposure 0. The warm light and AgX
# both pull violet towards white and pink, hence the strong blue and almost no green.
FLIEDER = (0.39, 0.024, 0.85)
# Hue of lilac fabrics under the warm pendants, measured the same way; flieder() scales it.
FABRIC = (0.45, 0.095, 1.0)
_cache = {}


def lin(hexstr):
    """sRGB hex -> linear RGBA. Tuples are taken as linear already."""
    if not isinstance(hexstr, str):
        return tuple(hexstr[:3]) + (1.0,)
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


def flieder(scale):
    """Brand-hue albedo for fabrics, felt and glass, `scale` = its blue reflectance."""
    return tuple(min(1.0, v * scale) for v in FABRIC) + (1.0,)


_agx = {}


def on_screen(hexstr):
    """Scene-linear RGB that the camera shows as this sRGB colour at exposure 0 (the view transform, inverted by
    Newton steps on the OCIO processor Blender itself uses)."""
    if "p" not in _agx:
        import PyOpenColorIO as ocio
        cfg = ocio.Config.CreateFromFile(str(pathlib.Path(bpy.utils.resource_path("LOCAL")) / "datafiles" / "colormanagement" / "config.ocio"))
        lv = ocio.LegacyViewingPipeline()
        lv.setDisplayViewTransform(ocio.DisplayViewTransform(src="Linear Rec.709", display="sRGB", view=VIEW))
        lv.setLooksOverrideEnabled(True)
        lv.setLooksOverride(LOOK)
        _agx["p"] = lv.getProcessor(cfg).getDefaultCPUProcessor()
    p = _agx["p"]
    h = hexstr.lstrip("#")
    target = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    shown = lambda y: np.array(p.applyRGB([float(v) for v in np.exp(y)]))
    y = np.log(np.maximum(np.array(lin(hexstr)[:3]), 1e-3))
    for _ in range(200):
        f = shown(y) - target
        if np.abs(f).max() < 2e-4:
            break
        J = np.column_stack([(shown(y + d) - shown(y - d)) / 0.04 for d in np.eye(3) * 0.02])
        y -= np.clip(np.linalg.lstsq(J, f, rcond=None)[0], -0.5, 0.5)
    return tuple(float(v) for v in np.exp(y)) + (1.0,)


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    return m, nt, out


def _img(nt, path, non_color, loc):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(str(path), check_existing=True)
    n.image.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    n.interpolation = "Cubic"
    n.location = loc
    return n


def _find(folder, short):
    for ext in ("jpg", "png", "exr"):
        p = folder / f"{short}.{ext}"
        if p.exists():
            return p
    return None


def principled(name, color="#808080", rough=0.5, metallic=0.0, **inputs):
    if name in _cache:
        return _cache[name]
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = lin(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    for k, v in inputs.items():
        b.inputs[k].default_value = lin(v) if isinstance(v, str) else v
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    _cache[name] = m
    return m


def _detail(nt, b, scale, strength, rough=None, rough_amp=0.08):
    """Fine procedural surface detail (paint orange peel, powder coat, felt) via noise bump + roughness variation."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if rough is not None:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough - rough_amp
        mr.inputs["To Max"].default_value = rough + rough_amp
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])


def painted(name, color, rough=0.5, metallic=0.0, scale=180.0, strength=0.06, **inputs):
    """Paint / powder coat: solid colour with micro texture."""
    if name in _cache:
        return _cache[name]
    m = principled(name, color, rough, metallic, **inputs)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    _detail(nt, b, scale, strength, rough)
    return m


def pbr(name, tex, tile=1.0, tint=None, sat=1.0, val=1.0, rough=(0.0, 1.0), normal=1.0, metallic=0.0, disp=0.0, **inputs):
    """Scanned material. tile = metres covered by one texture repeat; tint multiplies a (de)saturated albedo."""
    if name in _cache:
        return _cache[name]
    folder = TEX / tex
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (250, 0)
    b.inputs["Metallic"].default_value = metallic
    for k, v in inputs.items():
        b.inputs[k].default_value = lin(v) if isinstance(v, str) else v
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    diff = _img(nt, _find(folder, "diff"), False, (-600, 300))
    nt.links.new(mp.outputs[0], diff.inputs["Vector"])
    col = diff.outputs["Color"]
    if sat != 1.0 or val != 1.0:
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = sat
        hsv.inputs["Value"].default_value = val
        nt.links.new(col, hsv.inputs["Color"])
        col = hsv.outputs["Color"]
    if tint:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(col, mix.inputs[6])
        mix.inputs[7].default_value = lin(tint)
        col = mix.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    rp = _find(folder, "rough")
    if rp:
        r = _img(nt, rp, True, (-600, 0))
        nt.links.new(mp.outputs[0], r.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough[0]
        mr.inputs["To Max"].default_value = rough[1]
        nt.links.new(r.outputs["Color"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    npth = _find(folder, "nor_gl")
    if npth and normal > 0:
        n = _img(nt, npth, True, (-600, -300))
        nt.links.new(mp.outputs[0], n.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    dp = _find(folder, "disp")
    if dp and disp > 0:
        d = _img(nt, dp, True, (-600, -600))
        nt.links.new(mp.outputs[0], d.inputs["Vector"])
        dn = nt.nodes.new("ShaderNodeDisplacement")
        dn.inputs["Scale"].default_value = disp
        dn.inputs["Midlevel"].default_value = 0.5
        nt.links.new(d.outputs["Color"], dn.inputs["Height"])
        nt.links.new(dn.outputs[0], out.inputs["Displacement"])
        m.displacement_method = "BUMP"
    _cache[name] = m
    return m


def emission(name, color, strength):
    if name in _cache:
        return _cache[name]
    m, nt, out = _new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = lin(color)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    _cache[name] = m
    return m


def brand_light(name, strength, core=None):
    """Lilac LED strip or neon tube. Camera, mirror and through-glass rays see the brand colour exactly as it should
    appear in the still (on_screen); the light it throws into the room is Flieder at a physical strength. The
    'cam_gain' node is set to 2^-exposure for every shot (render.set_camera), so the colour is the same in all stills.
    core: a lighter colour for the middle of a round neon tube."""
    if name in _cache:
        return _cache[name]
    m, nt, out = _new(name)
    seen = nt.nodes.new("ShaderNodeEmission")
    if core:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.4
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = on_screen(core)
        mix.inputs[7].default_value = on_screen(BRAND)
        nt.links.new(lw.outputs["Facing"], mix.inputs["Factor"])
        nt.links.new(mix.outputs[2], seen.inputs["Color"])
    else:
        seen.inputs["Color"].default_value = on_screen(BRAND)
    gain = nt.nodes.new("ShaderNodeValue")
    gain.name = "cam_gain"
    gain.outputs[0].default_value = 1.0
    nt.links.new(gain.outputs[0], seen.inputs["Strength"])
    lit = nt.nodes.new("ShaderNodeEmission")
    lit.inputs["Color"].default_value = lin(BRAND)
    lit.inputs["Strength"].default_value = strength
    lp = nt.nodes.new("ShaderNodeLightPath")
    a = nt.nodes.new("ShaderNodeMath")
    a.operation = "MAXIMUM"
    nt.links.new(lp.outputs["Is Camera Ray"], a.inputs[0])
    nt.links.new(lp.outputs["Is Glossy Ray"], a.inputs[1])
    b = nt.nodes.new("ShaderNodeMath")
    b.operation = "MAXIMUM"
    nt.links.new(a.outputs[0], b.inputs[0])
    nt.links.new(lp.outputs["Is Transmission Ray"], b.inputs[1])
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(b.outputs[0], ms.inputs["Fac"])
    nt.links.new(lit.outputs[0], ms.inputs[1])
    nt.links.new(seen.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs["Surface"])
    _cache[name] = m
    return m


def glass(name, color="#ffffff", rough=0.0, ior=1.5):
    return principled(name, color, rough, 0.0, **{"Transmission Weight": 1.0, "IOR": ior})


def hazy_ground(name, color, haze, near, far):
    """Open field that fades into the horizon colour with distance (aerial perspective), so the ground meets the sky."""
    if name in _cache:
        return _cache[name]
    m = painted(name, color, 0.95, scale=40, strength=0.6)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    cam = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = near
    mr.inputs["From Max"].default_value = far
    nt.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = lin(haze)
    e.inputs["Strength"].default_value = 0.03
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs["Result"], mix.inputs["Fac"])
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def build_library():
    """All named materials used by the scene."""
    L = {}
    # architecture
    L["floor"] = pbr("floor_polished_concrete", "concrete_floor_worn_001", tile=2.6, tint="#a9a6ab", sat=0.25, rough=(0.16, 0.42), normal=0.45,
                     **{"Coat Weight": 0.35, "Coat Roughness": 0.06})
    L["wall_in"] = pbr("wall_paint_graphite", "painted_concrete_02", tile=3.0, tint="#4a4852", sat=0.0, val=0.62, rough=(0.62, 0.86), normal=0.35)
    L["stucco"] = pbr("facade_stucco", "white_stucco_02", tile=1.6, tint="#efe6d2", sat=0.2, rough=(0.82, 0.96), normal=0.9)
    L["plinth"] = painted("plinth_grey", "#4b4c51", 0.8)
    L["roof"] = pbr("roof_trapezoid", "box_profile_metal_sheet", tile=2.4, tint="#4a4c52", sat=0.0, val=0.7, rough=(0.32, 0.55), normal=1.0, metallic=0.55)
    L["ceiling"] = pbr("ceiling_trapezoid", "box_profile_metal_sheet", tile=2.4, tint="#3b3b42", sat=0.0, val=0.7, rough=(0.38, 0.6), normal=1.0, metallic=0.35)
    L["steel"] = painted("steel_powder_black", "#1d1d22", 0.42, 0.0, scale=220, strength=0.05)
    L["galv"] = painted("galvanised", "#b9bdc3", 0.34, 1.0, scale=40, strength=0.03)
    L["chrome"] = principled("chrome", "#d9dce1", 0.07, 1.0)
    L["brass"] = principled("brass_brushed", "#d6ae72", 0.26, 1.0)
    L["alu_black"] = painted("alu_anodised_black", "#16161a", 0.3, 0.85, scale=300, strength=0.02)
    L["timber"] = pbr("timber_spruce", "smoked_walnut_veneer", tile=1.4, tint="#e9cfa8", sat=0.6, val=1.25, rough=(0.55, 0.75), normal=0.6)
    L["glass"] = glass("glass_clear", "#f2f6f8", 0.0)
    L["glass_door"] = glass("glass_door", "#eef3f5", 0.0)
    L["rubber"] = painted("rubber_black", "#18181b", 0.78, scale=400, strength=0.08)
    L["sign_panel"] = principled("acrylic_black", "#0b0b0e", 0.12, 0.0, **{"Coat Weight": 0.8, "Coat Roughness": 0.03})
    # courts
    L["court_run"] = painted("court_runoff", "#1b1c21", 0.62, scale=900, strength=0.12)
    L["court_play"] = painted("court_play", "#2c2f37", 0.6, scale=900, strength=0.12)
    L["court_kitchen"] = painted("court_kitchen", FLIEDER, 0.58, scale=900, strength=0.12)
    L["court_line"] = painted("court_line", "#e7e4ec", 0.5, scale=900, strength=0.1)
    L["net"] = principled("net_cord", "#141418", 0.85)
    L["net_tape"] = principled("net_tape", "#ebe8ef", 0.6)
    # interior finishes
    L["felt_grey"] = painted("felt_grey", "#55545c", 0.98, scale=600, strength=0.35, **{"Sheen Weight": 0.4})
    L["felt_lilac"] = painted("felt_lilac", flieder(0.55), 0.98, scale=600, strength=0.35, **{"Sheen Weight": 0.4})
    L["felt_dark"] = painted("felt_dark", "#2c2c32", 0.98, scale=600, strength=0.35, **{"Sheen Weight": 0.4})
    L["sofa_graphite"] = pbr("upholstery_graphite", "poly_wool_herringbone", tile=0.35, tint="#55545c", sat=0.0, val=0.8, rough=(0.85, 1.0), normal=0.9,
                             **{"Sheen Weight": 0.6, "Sheen Roughness": 0.4})
    L["sofa_stone"] = pbr("upholstery_stone", "poly_wool_herringbone", tile=0.35, tint="#8b8690", sat=0.0, val=0.9, rough=(0.85, 1.0), normal=0.9,
                          **{"Sheen Weight": 0.6, "Sheen Roughness": 0.4})
    L["velvet_lilac"] = pbr("velvet_lilac", "velour_velvet", tile=0.5, tint=flieder(0.6), sat=0.0, val=1.0, rough=(0.75, 0.95), normal=0.6,
                            **{"Sheen Weight": 1.0, "Sheen Roughness": 0.35, "Sheen Tint": "#ecd3fb"})
    L["leather_black"] = pbr("leather_black", "leather_white", tile=0.6, tint="#2a292f", sat=0.0, val=0.75, rough=(0.32, 0.55), normal=0.7,
                             **{"Coat Weight": 0.15, "Coat Roughness": 0.2})
    L["walnut"] = pbr("walnut_veneer", "smoked_walnut_veneer", tile=1.2, rough=(0.3, 0.5), normal=0.4, **{"Coat Weight": 0.25, "Coat Roughness": 0.08})
    L["walnut_dark"] = pbr("walnut_dark", "smoked_walnut_veneer", tile=1.2, tint="#5a4a42", sat=0.6, val=0.7, rough=(0.3, 0.5), normal=0.4,
                           **{"Coat Weight": 0.25, "Coat Roughness": 0.08})
    L["stone_dark"] = painted("stone_top_dark", "#1b1b20", 0.22, scale=80, strength=0.02, **{"Coat Weight": 0.4, "Coat Roughness": 0.05})
    L["planter"] = painted("planter_powder_black", "#202024", 0.5, scale=260, strength=0.05)
    L["soil"] = pbr("soil_bark", "gravel_floor_02", tile=0.6, tint="#3a2d22", sat=0.4, val=0.45, rough=(0.85, 1.0), normal=1.0)
    L["rug"] = painted("rug_wool_graphite", "#2f2d36", 1.0, scale=900, strength=0.5, **{"Sheen Weight": 0.5})
    L["rug_border"] = painted("rug_wool_lilac", flieder(0.62), 1.0, scale=900, strength=0.5, **{"Sheen Weight": 0.5})
    L["slat"] = pbr("slat_black_stained", "smoked_walnut_veneer", tile=1.0, tint="#2a2422", sat=0.4, val=0.5, rough=(0.45, 0.65), normal=0.5)
    L["speaker"] = painted("speaker_cabinet", "#141417", 0.7, scale=500, strength=0.15)
    L["grille"] = painted("speaker_grille", "#1f1f24", 0.9, scale=1600, strength=0.4)
    L["white"] = painted("white_satin", "#e8e5ec", 0.35)
    L["red"] = painted("extinguisher_red", "#b3191b", 0.35)
    # light emitters
    L["led_white"] = emission("led_cool_white", "#fff4e8", 18.0)
    L["led_lilac"] = brand_light("led_lilac", 4.5)
    L["led_white_soft"] = emission("led_white_soft", "#f3f0f8", 2.5)
    L["led_warm"] = emission("led_warm", "#ffc890", 10.0)
    L["bulb_warm"] = emission("bulb_warm", "#ffbf80", 28.0)
    L["neon"] = brand_light("neon_lilac", 3.6, core=BRAND_CORE)
    L["neon_small"] = brand_light("neon_lilac_small", 3.0, core=BRAND_CORE)
    # exterior
    L["gravel"] = pbr("gravel_forecourt", "gravel_floor_02", tile=1.8, tint="#a39e95", sat=0.5, val=0.85, rough=(0.75, 0.95), normal=1.2, disp=0.03)
    L["paving"] = pbr("concrete_paving", "concrete_pavement", tile=3.0, sat=0.4, rough=(0.7, 0.92), normal=1.0, disp=0.01)
    L["field"] = hazy_ground("field_hazy", "#34332f", "#3d4658", 50.0, 700.0)
    return L
