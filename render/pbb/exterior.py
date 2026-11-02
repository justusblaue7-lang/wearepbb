"""Forecourt and entrance facade for the blue-hour exterior shot."""
import math

from .logo import logo
from .materials import BRAND
from .util import HX, HZ, WT, cuboid, cylinder, text, use_collection

LIGHTS = []


def ground(L):
    use_collection("exterior")
    cuboid("field", 8000, 0.04, 8000, (0, -0.06, 0), L["field"])
    cuboid("gravel", 120, 0.04, 120, (0, -0.025, 0), L["gravel"])
    cuboid("apron_front", 24.0, 0.04, 1.6, (0, -0.012, HZ + WT + 0.8), L["paving"])
    for sd in (-1, 1):
        cuboid(f"apron_side_{sd}", 1.2, 0.04, 2 * HZ + 3.2, (sd * 12.0, -0.012, 0), L["paving"])
    cuboid("path", 6.4, 0.04, 22.0, (0, -0.008, HZ + WT + 1.6 + 11.0), L["paving"])


def entrance(L):
    use_collection("exterior")
    z = HZ + WT / 2
    w, h = 5.6, 3.2
    cuboid("door_jamb_l", 0.12, h, 0.42, (-w / 2 - 0.02, h / 2, z), L["alu_black"], bev=0.004, seg=2)
    cuboid("door_jamb_r", 0.12, h, 0.42, (w / 2 + 0.02, h / 2, z), L["alu_black"], bev=0.004, seg=2)
    cuboid("door_head", w + 0.28, 0.14, 0.42, (0, h + 0.05, z), L["alu_black"], bev=0.004, seg=2)
    cuboid("door_transom", w, 0.07, 0.12, (0, 2.62, z), L["alu_black"], bev=0.003, seg=2)
    panels = (-2.1, -0.7, 0.7, 2.1)
    for i, cx in enumerate(panels):
        pw = 1.38
        for name, (u, v, sw, sh) in {"t": (0, 2.55, pw, 0.06), "b": (0, 0.05, pw, 0.1), "l": (-pw / 2 + 0.03, 1.3, 0.06, 2.5), "r": (pw / 2 - 0.03, 1.3, 0.06, 2.5)}.items():
            cuboid(f"door_{i}_{name}", sw, sh, 0.07, (cx + u, v, z + 0.02), L["alu_black"], bev=0.003, seg=2)
        cuboid(f"door_glass_{i}", pw - 0.1, 2.46, 0.012, (cx, 1.3, z + 0.02), L["glass_door"])
        if i in (1, 2):
            cylinder(f"door_handle_{i}", 0.015, 1.0, (cx + (0.52 if i == 1 else -0.52), 1.15, z + 0.08), L["chrome"], segs=16)
        cuboid(f"door_top_glass_{i}", pw - 0.04, 0.5, 0.012, (cx, 2.92, z), L["glass_door"])
    cuboid("door_step", 7.0, 0.08, 2.0, (0, 0.04, HZ + WT + 1.0), L["paving"], bev=0.01, seg=2)
    # canopy with downlights and a lilac line along its front edge
    cuboid("canopy", 8.0, 0.22, 3.0, (0, 3.76, HZ + WT + 1.5), L["alu_black"], bev=0.02, seg=3)
    cuboid("canopy_led", 7.7, 0.02, 0.025, (0, 3.64, HZ + WT + 2.94), L["led_lilac"])
    for x in (-3.8, 3.8):
        cylinder(f"canopy_post_{x}", 0.07, 3.66, (x, 1.83, HZ + WT + 2.75), L["alu_black"], segs=32)
    for x in (-2.6, 0.0, 2.6):
        cylinder(f"canopy_dl_{x}", 0.07, 0.01, (x, 3.645, HZ + WT + 1.6), L["led_warm"], segs=32)
        LIGHTS.append(("spot", (x, 3.62, HZ + WT + 1.6), {"target": (x, 0, HZ + WT + 1.9), "power": 70, "angle": 1.05, "blend": 0.55, "color": "#ffcf9a", "radius": 0.035}))
    # wall washers left and right of the canopy (up and down light on the render)
    for x in (-5.2, 5.2):
        cylinder(f"washer_{x}", 0.08, 0.32, (x, 3.0, HZ + WT + 0.17), L["alu_black"], segs=32)
        cylinder(f"washer_lens_up_{x}", 0.06, 0.004, (x, 3.161, HZ + WT + 0.17), L["led_warm"], segs=24)
        cylinder(f"washer_lens_dn_{x}", 0.06, 0.004, (x, 2.839, HZ + WT + 0.17), L["led_warm"], segs=24)
        LIGHTS.append(("spot", (x, 3.17, HZ + WT + 0.2), {"target": (x, 6.0, HZ + WT + 0.02), "power": 45, "angle": 0.55, "blend": 0.7, "color": "#ffcf9a", "radius": 0.03}))
        LIGHTS.append(("spot", (x, 2.83, HZ + WT + 0.2), {"target": (x, 0.0, HZ + WT + 0.02), "power": 45, "angle": 0.55, "blend": 0.7, "color": "#ffcf9a", "radius": 0.03}))


def sign(L):
    use_collection("exterior")
    zf = HZ + WT
    cuboid("sign_frame", 7.5, 3.4, 0.12, (0, 5.66, zf + 0.06), L["alu_black"], bev=0.02, seg=3)
    cuboid("sign_panel", 7.3, 3.2, 0.02, (0, 5.66, zf + 0.125), L["sign_panel"])
    logo("neon_pbb_facade", 3.1, L["neon"], (0, 6.08, zf + 0.2))
    text("sign_lettering", "PICKLEBALL BUDDIES", 0.24, (0, 4.42, zf + 0.14), L["led_lilac"], spacing=1.35, extrude=0.006)
    for y in (4.0, 7.32):
        cuboid(f"sign_led_{y}", 7.3, 0.02, 0.02, (0, y, zf + 0.13), L["led_lilac"])
    # side board on the left long wall, seen from the forecourt
    xs, zs, face = -(HX + WT), 15.2, -math.pi / 2
    cuboid("side_sign_frame", 0.1, 1.2, 4.9, (xs - 0.05, 4.9, zs), L["alu_black"], bev=0.015, seg=2)
    cuboid("side_sign_panel", 0.02, 1.08, 4.78, (xs - 0.105, 4.9, zs), L["sign_panel"])
    logo("neon_pbb_side", 1.1, L["neon_small"], (xs - 0.17, 4.9, zs - 1.7), ry=face)
    text("side_sign_lettering", "PICKLEBALL BUDDIES", 0.2, (xs - 0.12, 5.02, zs + 0.45), L["led_lilac"], ry=face, spacing=1.2, extrude=0.004)
    text("side_sign_sub", "COURTS · LOUNGE · DRINKS", 0.11, (xs - 0.12, 4.68, zs + 0.45), L["led_lilac"], ry=face, spacing=1.6, extrude=0.003)


def bollards(L):
    use_collection("exterior")
    for x in (-3.6, 3.6):
        for z in (31.0, 37.0, 43.0):
            cylinder(f"bollard_{x}_{z}", 0.1, 0.9, (x, 0.45, z), L["alu_black"], segs=48)
            cylinder(f"bollard_ring_{x}_{z}", 0.102, 0.05, (x, 0.83, z), L["led_lilac"], segs=48)
            cylinder(f"bollard_cap_{x}_{z}", 0.104, 0.03, (x, 0.915, z), L["alu_black"], segs=48)
            LIGHTS.append(("point", (x, 0.83, z), {"power": 6, "radius": 0.1, "color": BRAND}))


def build(L):
    ground(L)
    entrance(L)
    sign(L)
    bollards(L)
    return LIGHTS
