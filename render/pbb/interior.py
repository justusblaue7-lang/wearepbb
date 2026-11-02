"""Lounge, planters, back wall with neon sign, DJ stage, bar, VIP corner and foyer."""
import math

import bmesh
import bpy

from . import assets
from .logo import logo
from .materials import BRAND, flieder, glass, principled
from .util import HX, HZ, P, boxes, cuboid, cylinder, mesh_obj, subsurf, tube, under_y, use_collection

LIGHTS = []   # (kind, three.js position, params) collected here, created in lighting.py


def local(at, ry, u, y, w):
    """Point u/w in an object's own frame (w = its front) -> three.js coordinates."""
    c, s = math.cos(ry), math.sin(ry)
    return (at[0] + u * c + w * s, y, at[2] - u * s + w * c)


def piece(name, at, ry, u, y, w, size, mat, bev=0.0, seg=3, rx=0.0, soft=0):
    ob = cuboid(name, *size, local(at, ry, u, y, w), mat, ry=ry, bev=bev, seg=seg)
    if rx:
        ob.rotation_euler = (rx, 0, ry)
    if soft:
        subsurf(ob, soft)
    return ob


# ---------------------------------------------------------------- lounge
def sofa(name, at, ry, L, fabric, length=2.3):
    """Low modular sofa: recessed plinth, upholstered base, arms, back, loose seat and back cushions, velvet pillows."""
    half = length / 2
    piece(f"{name}_plinth", at, ry, 0, 0.04, -0.02, (length - 0.12, 0.08, 0.86), L["steel"])
    piece(f"{name}_base", at, ry, 0, 0.215, 0, (length, 0.27, 0.98), fabric, bev=0.035, seg=4)
    piece(f"{name}_back", at, ry, 0, 0.56, -0.37, (length, 0.52, 0.24), fabric, bev=0.05, seg=5)
    for s in (-1, 1):
        piece(f"{name}_arm_{s}", at, ry, s * (half - 0.11), 0.47, 0.0, (0.22, 0.52, 0.98), fabric, bev=0.05, seg=5)
    n, cw = 2, (length - 0.44) / 2
    for i in range(n):
        u = -cw / 2 + i * cw if n == 2 else 0
        piece(f"{name}_seat_{i}", at, ry, u, 0.43, 0.08, (cw - 0.01, 0.17, 0.72), fabric, bev=0.07, seg=6)
        piece(f"{name}_backcush_{i}", at, ry, u, 0.68, -0.19, (cw - 0.02, 0.44, 0.2), fabric, bev=0.08, seg=6, rx=-0.2)
    piece(f"{name}_pillow_a", at, ry, -half + 0.48, 0.72, -0.05, (0.46, 0.44, 0.15), L["velvet_lilac"], bev=0.06, seg=4, rx=-0.32, soft=2)
    piece(f"{name}_pillow_b", at, ry, half - 0.5, 0.71, -0.06, (0.44, 0.42, 0.14), L["sofa_stone"] if fabric is L["sofa_graphite"] else L["sofa_graphite"], bev=0.06, seg=4, rx=-0.28, soft=2)


def rug(name, x, z, w, d, L):
    cuboid(f"{name}", w, 0.012, d, (x, 0.006, z), L["rug"], bev=0.004, seg=2)
    b, t = 0.07, 0.0125
    boxes(f"{name}_border", [(x, t, z - d / 2 + 0.16, w - 0.24, 0.002, b), (x, t, z + d / 2 - 0.16, w - 0.24, 0.002, b),
                             (x - w / 2 + 0.16, t, z, b, 0.002, d - 0.24), (x + w / 2 - 0.16, t, z, b, 0.002, d - 0.24)], L["rug_border"])


def pendant(name, x, y, z):
    """Scanned white dome pendant on a cable to the roof, with a warm lamp inside."""
    assets.place("lib:modern_ceiling_lamp_01", name, (x, y, z), rz=0.3)
    tube(f"{name}_cable", [(x, y + 0.94, z), (x, under_y(x) - 0.05, z)], 0.002, bpy.data.materials["steel_powder_black"])
    LIGHTS.append(("point", (x, y + 0.16, z), {"power": 90, "radius": 0.06, "color": "#ffb871"}))


PLANTERS = [-15.3, -11.2, -7.2, -3.2, 0.9, 4.9, 8.9, 13.0]
PLANT_SETS = [
    [("lib:anthurium_botany_01_a", 1.35, (0.0, 0.05), 0.4), ("lib:fern_02_b", 1.1, (0.18, -0.2), 1.9)],
    [("lib:calathea_orbifolia_01_a", 1.55, (0.0, 0.0), 0.9), ("lib:fern_02_c", 1.0, (-0.2, 0.18), 2.6)],
    [("lib:anthurium_botany_01_b", 1.6, (0.05, 0.0), 2.2), ("lib:calathea_orbifolia_01_c", 1.3, (-0.18, -0.2), 0.3)],
    [("lib:fern_02_b", 1.35, (0.0, 0.0), 1.1), ("lib:anthurium_botany_01_c", 1.25, (0.15, 0.2), 3.0)],
]


def planter(i, z, L):
    x = 0.0
    cuboid(f"planter_{i}", 0.95, 0.62, 0.95, (x, 0.31, z), L["planter"], bev=0.012, seg=2)
    cuboid(f"planter_soil_{i}", 0.86, 0.02, 0.86, (x, 0.6, z), L["soil"])
    cuboid(f"planter_led_{i}", 1.0, 0.006, 1.0, (x, 0.003, z), L["led_lilac"])
    for k, (lib, s, (dx, dz), rot) in enumerate(PLANT_SETS[i % len(PLANT_SETS)]):
        assets.place(lib, f"plant_{i}_{k}", (x + dx, 0.6, z + dz), rz=rot, scale=s)


def lounge(L):
    use_collection("lounge")
    for gi, z in enumerate((-13.0, -5.0, 3.0, 11.0)):
        for sd in (-1, 1):
            fabric = L["sofa_graphite"] if (gi + (sd > 0)) % 2 == 0 else L["sofa_stone"]
            sofa(f"sofa_{gi}_{sd}", (sd * 1.75, 0, z), sd * math.pi / 2, L, fabric)
            assets.place("lib:coffee_table_round_01", f"coffee_{gi}_{sd}", (sd * 2.95, 0, z), scale=0.66)
            assets.place("lib:potted_plant_04", f"succulent_{gi}_{sd}", (sd * 2.95 + 0.12, 0.325, z - 0.1), rz=gi * 1.3, scale=1.0)
            rug(f"rug_{gi}_{sd}", sd * 2.35, z, 2.2, 3.3, L)
            pendant(f"pendant_{gi}_{sd}", sd * 2.95, 2.2, z)
    for i, z in enumerate(PLANTERS):
        planter(i, z, L)


# ---------------------------------------------------------------- back wall, DJ, bar, VIP
def back_wall(L):
    use_collection("back_wall")
    z0 = -HZ + 0.02
    cuboid("slatwall_backing", 16.0, 5.4, 0.02, (0, 2.75, z0), L["steel"])
    pitch, n = 0.075, int(16.0 / 0.075)
    boxes("slatwall_slats", [(-8.0 + pitch / 2 + i * pitch, 2.75, z0 + 0.035, 0.045, 5.4, 0.03) for i in range(n)], L["slat"])
    logo("neon_pbb_backwall", 4.0, L["neon"], (0, 3.65, z0 + 0.14))
    # grazing uplight along the foot of the slat wall
    cuboid("slatwall_uplight", 15.6, 0.04, 0.08, (0, 0.02, z0 + 0.16), L["alu_black"])
    LIGHTS.append(("area", (0, 0.06, z0 + 0.18), {"size": (15.4, 0.05), "power": 900, "color": "#ffd9bd", "rot": (math.pi, 0, 0)}))
    for x in (-10.2, -9.1, 9.1, 10.2):
        cuboid(f"backwall_led_ch_{x}", 0.05, 4.7, 0.04, (x, 3.1, z0 + 0.02), L["alu_black"])
        cuboid(f"backwall_led_{x}", 0.03, 4.6, 0.012, (x, 3.1, z0 + 0.045), L["led_lilac"])


def dj(L):
    use_collection("dj")
    zs, y0 = -22.9, 0.3
    cuboid("stage", 9.8, y0, 4.1, (0, y0 / 2, zs), L["steel"], bev=0.01, seg=2)
    cuboid("stage_led", 9.7, 0.014, 0.02, (0, y0 - 0.03, zs + 2.06), L["led_lilac"])
    zb = -22.0
    cuboid("booth", 3.8, 1.0, 0.9, (0, y0 + 0.5, zb), L["walnut_dark"], bev=0.02, seg=3)
    boxes("booth_fluting", [(-1.85 + i * 0.05, y0 + 0.5, zb + 0.46, 0.03, 0.94, 0.02) for i in range(75)], L["walnut_dark"])
    cuboid("booth_top", 3.9, 0.05, 1.0, (0, y0 + 1.025, zb), L["stone_dark"], bev=0.012, seg=3)
    cuboid("booth_led", 3.7, 0.012, 0.012, (0, y0 + 0.05, zb + 0.5), L["led_lilac"])
    top = y0 + 1.05
    for x in (-0.6, 0.6):
        cuboid(f"cdj_{x}", 0.32, 0.08, 0.42, (x, top + 0.04, zb), L["speaker"], bev=0.012, seg=3)
        cylinder(f"cdj_jog_{x}", 0.1, 0.012, (x, top + 0.086, zb + 0.04), L["alu_black"], segs=64)
        cylinder(f"cdj_ring_{x}", 0.03, 0.014, (x, top + 0.088, zb + 0.04), L["led_lilac"], segs=32)
        cuboid(f"cdj_screen_{x}", 0.16, 0.002, 0.07, (x, top + 0.081, zb - 0.14), L["led_white_soft"])
    cuboid("mixer", 0.32, 0.08, 0.42, (0, top + 0.04, zb), L["speaker"], bev=0.012, seg=3)
    for i in range(4):
        cylinder(f"mixer_knob_{i}", 0.012, 0.02, (-0.1 + i * 0.066, top + 0.09, zb - 0.12), L["chrome"], segs=16)
        cuboid(f"mixer_fader_{i}", 0.008, 0.004, 0.08, (-0.1 + i * 0.066, top + 0.082, zb + 0.08), L["led_lilac"])
    for s in (-1, 1):
        x = s * 4.25
        cuboid(f"pa_top_{s}", 0.6, 1.5, 0.55, (x, y0 + 1.6, -23.6), L["speaker"], bev=0.02, seg=3)
        cuboid(f"pa_grille_{s}", 0.54, 1.42, 0.01, (x, y0 + 1.6, -23.32), L["grille"])
        cuboid(f"pa_sub_{s}", 0.9, 0.85, 0.8, (x, y0 + 0.425, -23.6), L["speaker"], bev=0.02, seg=3)
        cuboid(f"pa_sub_grille_{s}", 0.84, 0.78, 0.01, (x, y0 + 0.425, -23.195), L["grille"])
    # square truss with moving heads
    zt, yt = -22.4, 4.7
    for sy in (-1, 1):
        for sz in (-1, 1):
            cylinder(f"truss_chord_{sy}_{sz}", 0.025, 9.4, (0, yt + sy * 0.2, zt + sz * 0.2), L["steel"], axis="x", segs=16)
    for i in range(19):
        x = -4.5 + i * 0.5
        for (a, b) in (((x, yt - 0.2, zt - 0.2), (x + 0.25, yt + 0.2, zt - 0.2)), ((x + 0.25, yt + 0.2, zt - 0.2), (x + 0.5, yt - 0.2, zt - 0.2)),
                       ((x, yt - 0.2, zt + 0.2), (x + 0.25, yt + 0.2, zt + 0.2)), ((x + 0.25, yt + 0.2, zt + 0.2), (x + 0.5, yt - 0.2, zt + 0.2)),
                       ((x, yt - 0.2, zt - 0.2), (x, yt - 0.2, zt + 0.2)), ((x, yt + 0.2, zt - 0.2), (x, yt + 0.2, zt + 0.2))):
            if a[0] <= 4.7 and b[0] <= 4.7:
                tube(f"truss_d_{i}_{a}", [a, b], 0.009, L["steel"], res=8)
    for i, x in enumerate((-3.6, -2.1, -0.7, 0.7, 2.1, 3.6)):
        cuboid(f"mh_yoke_{i}", 0.3, 0.05, 0.08, (x, yt - 0.26, zt + 0.25), L["speaker"], bev=0.01, seg=2)
        cylinder(f"mh_head_{i}", 0.11, 0.3, (x, yt - 0.47, zt + 0.25), L["speaker"], segs=32, r2=0.13)
        cylinder(f"mh_lens_{i}", 0.085, 0.004, (x, yt - 0.622, zt + 0.25), L["led_lilac"], segs=32)
    for x in (-4.0, 4.0):
        tube(f"truss_wire_{x}", [(x, yt + 0.2, zt), (x, under_y(x) - 0.05, zt)], 0.003, L["steel"])
    LIGHTS.append(("spot", (0, 5.4, -20.0), {"target": (0, 0.9, -23.5), "power": 220, "angle": 0.9, "blend": 0.6, "color": BRAND, "radius": 0.08}))
    for x in (-2.8, 0.0, 2.8):      # warm truss spots on the booth and stage front
        LIGHTS.append(("spot", (x, 4.45, -22.2), {"target": (x * 0.6, 0.6, -21.2), "power": 600, "angle": 0.75, "blend": 0.7, "color": "#ffd2a8", "radius": 0.05}))


def _bottle_meshes(L):
    prof = [(0.0, 0.0), (0.038, 0.0), (0.041, 0.012), (0.041, 0.19), (0.03, 0.235), (0.015, 0.27), (0.014, 0.325), (0.016, 0.33), (0.0, 0.335)]
    meshes = []
    for k, (sx, sy, col) in enumerate(((1.0, 1.0, "#b98a45"), (0.9, 1.12, "#3f6b45"), (1.05, 0.9, "#e9eef0"), (0.95, 1.05, "#5b3a26"), (1.1, 0.85, flieder(0.9)))):
        bm = bmesh.new()
        vs = [bm.verts.new((r * sx, 0, y * sy)) for r, y in prof]
        for a, b in zip(vs, vs[1:]):
            bm.edges.new((a, b))
        bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1), angle=2 * math.pi, steps=32, use_merge=True)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        me = bpy.data.meshes.new(f"bottle_{k}")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(glass(f"bottle_glass_{k}", col, 0.02))
        for p in me.polygons:
            p.use_smooth = True
        meshes.append(me)
    return meshes


def bar(L):
    use_collection("bar")
    bx, z0, z1 = 7.5, -24.3, -18.7
    zc, ln = (z0 + z1) / 2, z1 - z0
    cuboid("bar_body", 0.85, 1.02, ln, (bx, 0.53, zc), L["walnut_dark"], bev=0.01, seg=2)
    boxes("bar_fluting", [(bx - 0.44, 0.55, z0 + 0.04 + i * 0.05, 0.03, 0.94, 0.03) for i in range(int(ln / 0.05))], L["walnut_dark"])
    cuboid("bar_top", 1.08, 0.05, ln + 0.2, (bx, 1.065, zc), L["stone_dark"], bev=0.012, seg=3)
    cuboid("bar_kick", 0.75, 0.08, ln - 0.1, (bx + 0.05, 0.04, zc), L["steel"])
    cuboid("bar_kick_led", 0.012, 0.012, ln - 0.2, (bx - 0.36, 0.075, zc), L["led_lilac"])
    tube("bar_footrail", [(bx - 0.62, 0.2, z0 + 0.15), (bx - 0.62, 0.2, z1 - 0.15)], 0.025, L["brass"])
    # back bar against the right wall
    bb = 10.6
    cuboid("backbar", 0.66, 0.92, ln - 0.6, (bb, 0.46, zc), L["steel"], bev=0.01, seg=2)
    cuboid("backbar_top", 0.74, 0.04, ln - 0.6, (bb, 0.94, zc), L["stone_dark"], bev=0.01, seg=2)
    mirror = principled("mirror_dark", "#3a3a42", 0.04, 1.0)
    cuboid("backbar_mirror", 0.01, 1.4, ln - 0.8, (HX - 0.02, 1.85, zc), mirror)
    meshes = _bottle_meshes(L)
    k = 0
    for row, y in enumerate((1.3, 1.7, 2.1)):
        cuboid(f"shelf_{row}", 0.28, 0.03, ln - 0.9, (HX - 0.16, y, zc), L["walnut"], bev=0.006, seg=2)
        cuboid(f"shelf_led_{row}", 0.012, 0.008, ln - 1.0, (HX - 0.04, y - 0.02, zc), L["led_warm"])
        n = int((ln - 1.3) / 0.16)
        for i in range(n):
            me = meshes[(i * 3 + row * 2 + (i // 4)) % len(meshes)]
            ob = bpy.data.objects.new(f"bottle_{k}", me)
            ob.location = P(HX - 0.17, y + 0.015, z0 + 0.6 + i * 0.16)
            ob.rotation_euler = (0, 0, i * 1.7)
            bpy.data.collections["bar"].objects.link(ob)
            k += 1
    cuboid("espresso", 0.48, 0.36, 0.6, (bb, 1.14, -19.5), L["chrome"], bev=0.03, seg=4)
    cuboid("espresso_top", 0.5, 0.05, 0.62, (bb, 1.345, -19.5), L["speaker"], bev=0.01, seg=2)
    for i in range(5):
        z = z0 + 0.75 + i * 1.05
        x = bx - 0.95
        cylinder(f"stool_seat_{i}", 0.19, 0.08, (x, 0.74, z), L["leather_black"], segs=48)
        cylinder(f"stool_stem_{i}", 0.024, 0.68, (x, 0.36, z), L["chrome"], segs=24)
        cylinder(f"stool_base_{i}", 0.21, 0.02, (x, 0.012, z), L["chrome"], segs=48, r2=0.19)
        ring = bpy.data.objects.new(f"stool_ring_{i}", bpy.data.curves.new(f"stool_ring_{i}", "CURVE"))
        cu = ring.data
        cu.bevel_depth = 0.01
        sp = cu.splines.new("NURBS")
        pts = 16
        sp.points.add(pts - 1)
        for j in range(pts):
            a = 2 * math.pi * j / pts
            v = P(x + 0.16 * math.cos(a), 0.32, z + 0.16 * math.sin(a))
            sp.points[j].co = (v.x, v.y, v.z, 1)
        sp.use_cyclic_u = True
        cu.materials.append(L["chrome"])
        bpy.data.collections["bar"].objects.link(ring)
    for z in (-23.4, -21.5, -19.6):
        top = under_y(bx) - 0.08
        tube(f"bar_pend_cable_{z}", [(bx, 2.72, z), (bx, top, z)], 0.0025, L["steel"])
        cylinder(f"bar_pend_canopy_{z}", 0.035, 0.06, (bx, 2.64, z), L["alu_black"], segs=32)
        shade = cylinder(f"bar_pend_cone_{z}", 0.24, 0.22, (bx, 2.5, z), L["alu_black"], segs=64, r2=0.035, cap=False)
        sol = shade.modifiers.new("thick", "SOLIDIFY")
        sol.thickness = 0.004
        cylinder(f"bar_pend_bulb_{z}", 0.05, 0.08, (bx, 2.43, z), L["bulb_warm"], segs=24)
        LIGHTS.append(("point", (bx, 2.42, z), {"power": 120, "radius": 0.04, "color": "#ffb36a"}))
    LIGHTS.append(("area", (HX - 0.12, 2.35, zc), {"size": (0.06, ln - 1.0), "power": 60, "color": "#ffc890", "rot": (0, -math.pi / 2, 0)}))


def vip(L):
    use_collection("vip")
    rug("vip_rug", -8.4, -20.6, 3.2, 4.2, L)
    assets.place("lib:mid_century_lounge_chair", "vip_chair_a", (-9.4, 0, -22.0), rz=math.radians(-35))
    assets.place("lib:mid_century_lounge_chair", "vip_chair_b", (-7.3, 0, -22.1), rz=math.radians(30))
    assets.place("lib:modern_arm_chair_01", "vip_arm", (-9.6, 0, -19.3), rz=math.radians(-140))
    assets.place("lib:Ottoman_01", "vip_ottoman", (-7.2, 0, -19.3), rz=math.radians(15), scale=0.85)
    assets.place("lib:coffee_table_round_01", "vip_table", (-8.4, 0, -20.6), scale=0.62)
    assets.place("lib:potted_plant_02", "vip_plant", (-10.35, 0, -24.3), rz=0.6, scale=1.9)
    pendant("vip_pendant", -8.4, 2.25, -20.6)


def foyer(L):
    use_collection("foyer")
    zf0, y = 15.5, 3.5
    cuboid("foyer_ceiling", 2 * HX - 0.04, 0.3, HZ - zf0, (0, y, (zf0 + HZ) / 2), L["wall_in"])
    cuboid("foyer_header", 2 * HX - 0.04, 0.6, 0.18, (0, y - 0.3, zf0 - 0.09), L["steel"])
    cuboid("foyer_cove", 2 * HX - 0.4, 0.03, 0.03, (0, y - 0.6, zf0 - 0.2), L["led_lilac"])
    for z in (17.2, 19.3, 21.4, 23.5):
        for x in (-9, -6, -3, 0, 3, 6, 9):
            cylinder(f"downlight_{x}_{z}", 0.08, 0.01, (x, y - 0.155, z), L["led_warm"], segs=32)
            LIGHTS.append(("spot", (x, y - 0.17, z), {"target": (x, 0, z), "power": 30, "angle": 1.0, "blend": 0.5, "color": "#ffd2a0", "radius": 0.04}))
    rz = 20.2
    cuboid("reception", 6.0, 1.06, 0.8, (5.6, 0.53, rz), L["walnut_dark"], bev=0.01, seg=2)
    boxes("reception_fluting", [(2.62 + i * 0.05, 0.55, rz - 0.41, 0.03, 0.96, 0.02) for i in range(119)], L["walnut_dark"])
    cuboid("reception_top", 6.2, 0.05, 1.0, (5.6, 1.085, rz), L["stone_dark"], bev=0.012, seg=3)
    cuboid("reception_led", 5.9, 0.012, 0.012, (5.6, 0.06, rz - 0.42), L["led_lilac"])
    zw = HZ - 0.02
    cuboid("foyer_slat_backing", 6.4, 3.0, 0.02, (5.6, 1.5, zw), L["steel"])
    boxes("foyer_slats", [(2.45 + i * 0.075, 1.5, zw - 0.035, 0.045, 3.0, 0.03) for i in range(85)], L["slat"])
    logo("neon_pbb_foyer", 2.0, L["neon_small"], (5.6, 1.95, zw - 0.12), ry=math.pi)
    cuboid("entrance_mat", 3.4, 0.015, 1.8, (0, 0.0075, 23.8), L["rug"], bev=0.004, seg=2)
    for x in (-4.0, 4.0):
        assets.place("lib:potted_plant_02", f"foyer_plant_{x}", (x, 0, 24.0), rz=x, scale=1.9)


def build(L):
    for lib in ("potted_plant_02", "potted_plant_04", "calathea_orbifolia_01", "anthurium_botany_01", "fern_02", "coffee_table_round_01",
                "modern_ceiling_lamp_01", "mid_century_lounge_chair", "modern_arm_chair_01", "Ottoman_01"):
        assets.load(lib)
    lounge(L)
    back_wall(L)
    dj(L)
    bar(L)
    vip(L)
    foyer(L)
    return LIGHTS
