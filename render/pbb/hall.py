"""Building shell and structure: floor, walls with openings, low-pitch roof, steel portal frames, services."""
import math

from mathutils import Vector

from .util import (EH, HX, HZ, RH, WT, P, beam_between, boxes, cuboid, cylinder, ibeam_profile, prism, tube, under_y,
                   use_collection, wall_pieces)

FRAME_Z = [-22.75 + i * 6.5 for i in range(8)]
WIN = {"w": 1.6, "y0": 3.0, "y1": 4.1, "z": (-15.0, 0.0, 15.0)}
SIDE_DOORS = [(-1, 8.0), (-1, -20.0), (1, -20.0)]          # (side, z) 1.0 x 2.1 m
ENT = {"w": 5.6, "h": 3.2}
XE, ZV, TH = HX + WT + 0.55, HZ + WT + 1.3, 0.17           # roof overhang edge, verge, roof thickness


def floor(L):
    use_collection("hall")
    cuboid("floor_slab", 2 * HX, 0.3, 2 * HZ, (0, -0.15, 0), L["floor"])
    # saw-cut joints of the polished slab, every 5.5 m
    joints = [(x, 0.0004, 0, 0.006, 0.001, 2 * HZ) for x in (-5.5, 0.0, 5.5)]
    joints += [(0, 0.0004, z, 2 * HX, 0.001, 0.006) for z in (-22, -16.5, -11, -5.5, 0, 5.5, 11, 16.5, 22)]
    boxes("floor_joints", joints, L["rubber"])


def walls(L):
    use_collection("hall")
    h_out = under_y(HX + WT)
    for sd in (-1, 1):
        ops = [(z, WIN["w"], WIN["y0"], WIN["y1"]) for z in WIN["z"]]
        ops += [(z, 1.0, 0.0, 2.1) for s, z in SIDE_DOORS if s == sd]
        inner = [(sd * (HX + 0.1), (y0 + y1) / 2, (a + b) / 2, 0.2, y1 - y0, b - a) for a, b, y0, y1 in wall_pieces("z", -HZ, HZ, EH, ops)]
        outer = [(sd * (HX + 0.3), (y0 + y1) / 2, (a + b) / 2, 0.2, y1 - y0, b - a) for a, b, y0, y1 in wall_pieces("z", -HZ - WT, HZ + WT, h_out, ops)]
        boxes(f"wall_long_in_{sd}", inner, L["wall_in"])
        boxes(f"wall_long_out_{sd}", outer, L["stucco"])
    # gables: front (entrance) and back; rectangular part with openings, triangle above
    for sz in (-1, 1):
        ops = [(0.0, ENT["w"], 0.0, ENT["h"]), (-7.0, 1.6, WIN["y0"], WIN["y1"]), (7.0, 1.6, WIN["y0"], WIN["y1"])] if sz > 0 else []
        inner = [((a + b) / 2, (y0 + y1) / 2, sz * (HZ + 0.1), b - a, y1 - y0, 0.2) for a, b, y0, y1 in wall_pieces("x", -HX, HX, EH, ops)]
        outer = [((a + b) / 2, (y0 + y1) / 2, sz * (HZ + 0.3), b - a, y1 - y0, 0.2) for a, b, y0, y1 in wall_pieces("x", -HX - WT, HX + WT, h_out, ops)]
        boxes(f"gable_in_{sz}", inner, L["wall_in"])
        boxes(f"gable_out_{sz}", outer, L["stucco"])
        prism(f"gable_tri_in_{sz}", [(-HX, EH), (HX, EH), (0, RH)], sz * HZ, sz * (HZ + 0.2), L["wall_in"])
        prism(f"gable_tri_out_{sz}", [(-HX - WT, h_out), (HX + WT, h_out), (0, RH + 0.02)], sz * (HZ + 0.2), sz * (HZ + WT), L["stucco"])
    # dark plinth band outside
    ox, oz = HX + WT, HZ + WT
    boxes("plinth", [(sd * (ox + 0.02), 0.21, 0, 0.04, 0.42, 2 * oz + 0.08) for sd in (-1, 1)] +
          [(0, 0.21, sd * (oz + 0.02), 2 * ox + 0.08, 0.42, 0.04) for sd in (-1, 1)], L["plinth"])


def _slope(name, x0, x1, z0, z1, off, thick, mat, sd):
    """Roof layer following the pitch on side sd between |x| = x0..x1."""
    ya, yb = under_y(x0) + off, under_y(x1) + off
    poly = [(sd * x0, ya), (sd * x1, yb), (sd * x1, yb + thick), (sd * x0, ya + thick)]
    if sd < 0:
        poly = poly[::-1]
    return prism(name, poly, z0, z1, mat)


def roof(L):
    use_collection("hall")
    for sd in (-1, 1):
        _slope(f"roof_sheet_{sd}", 0.0, XE, -ZV, ZV, 0.02, TH, L["roof"], sd)
        _slope(f"ceiling_{sd}", 0.0, HX, -HZ, HZ, -0.004, 0.024, L["ceiling"], sd)
        # timber soffit of the overhangs (eaves and gable verges), as on the existing building
        _slope(f"soffit_eave_{sd}", HX + WT, XE, -ZV, ZV, 0.0, 0.02, L["timber"], sd)
        for sz in (-1, 1):
            _slope(f"soffit_verge_{sd}_{sz}", 0.0, HX + WT, sz * (HZ + WT), sz * ZV, 0.0, 0.02, L["timber"], sd)
            for i in range(10):     # exposed rafter ends under the verge
                x = 0.6 + i * 1.14
                cuboid(f"rafter_{sd}_{sz}_{i}", 0.11, 0.2, 1.3, (sd * x, under_y(x) - 0.08, sz * (HZ + WT + 0.65)), L["timber"], bev=0.006, seg=2)
        # fascia, gutter, downpipes
        cuboid(f"fascia_{sd}", 0.05, 0.28, 2 * ZV, (sd * XE, under_y(XE) + 0.06, 0), L["alu_black"], bev=0.004, seg=2)
        cylinder(f"gutter_{sd}", 0.075, 2 * ZV, (sd * (XE + 0.09), under_y(XE) - 0.02, 0), L["alu_black"], axis="z", segs=24)
        for z in (-24.2, 0.0, 24.2):
            hh = under_y(XE) - 0.1
            cylinder(f"downpipe_{sd}_{z}", 0.045, hh, (sd * (HX + WT + 0.12), hh / 2, z), L["alu_black"], segs=20)
        # barge boards along the sloping verge edges
        for sz in (-1, 1):
            beam_between(f"barge_{sd}_{sz}", (0, under_y(0) + 0.1, sz * ZV), (sd * XE, under_y(XE) + 0.1, sz * ZV),
                         [(-0.025, -0.15), (0.025, -0.15), (0.025, 0.15), (-0.025, 0.15)], L["alu_black"])
    cuboid("ridge_cap", 0.5, 0.1, 2 * ZV, (0, RH + TH + 0.06, 0), L["alu_black"], bev=0.01, seg=2)


def windows(L):
    """Black aluminium frames with clear glass in every wall opening (front gable windows + long walls)."""
    use_collection("hall")
    h, w = WIN["y1"] - WIN["y0"], WIN["w"]
    yc = (WIN["y0"] + WIN["y1"]) / 2
    spots = [(sd * (HX + WT / 2), z, math.pi / 2) for sd in (-1, 1) for z in WIN["z"]] + [(x, HZ + WT / 2, 0.0) for x in (-7.0, 7.0)]
    for i, (x, z, ry) in enumerate(spots):
        f, d = 0.06, 0.09
        parts = [(0, h / 2 - f / 2, w, f), (0, -h / 2 + f / 2, w, f), (-w / 2 + f / 2, 0, f, h), (w / 2 - f / 2, 0, f, h), (0, 0, f * 0.7, h)]
        for k, (u, v, pw, ph) in enumerate(parts):
            o = cuboid(f"win_{i}_{k}", pw, ph, d, (0, 0, 0), L["alu_black"], bev=0.004, seg=2)
            o.location = P(x, yc, z) + _rot(Vector((u, 0, v)), ry)
            o.rotation_euler = (0, 0, ry)
        g = cuboid(f"win_glass_{i}", w - 2 * f, h - 2 * f, 0.012, (0, 0, 0), L["glass"])
        g.location = P(x, yc, z)
        g.rotation_euler = (0, 0, ry)
        sill = cuboid(f"win_sill_{i}", w + 0.12, 0.04, 0.26, (0, 0, 0), L["alu_black"], bev=0.004, seg=2)
        sill.location = P(x, WIN["y0"] - 0.02, z) + _rot(Vector((0, -0.12, 0)), ry)
        sill.rotation_euler = (0, 0, ry)


def _rot(v, ry):
    c, s = math.cos(ry), math.sin(ry)
    return Vector((v.x * c - v.y * s, v.x * s + v.y * c, v.z))


def structure(L):
    """Portal frames, purlins, bracing, ducts, baffles: the industrial ceiling you see in every interior shot."""
    use_collection("structure")
    col = ibeam_profile(0.30, 0.30, 0.025, 0.014)
    raf = ibeam_profile(0.42, 0.20, 0.022, 0.012)
    for i, z in enumerate(FRAME_Z):
        for sd in (-1, 1):
            xc = sd * 10.85
            eave = (xc, under_y(10.85) - 0.45, z)
            beam_between(f"column_{i}_{sd}", (xc, 0.0, z), eave, col, L["steel"], depth_dir=(1, 0, 0))
            beam_between(f"rafter_{i}_{sd}", eave, (0.0, RH - 0.23, z), raf, L["steel"])
            cuboid(f"haunch_{i}_{sd}", 0.012, 0.75, 0.2, (sd * 10.5, under_y(10.5) - 0.62, z), L["steel"])
            cuboid(f"baseplate_{i}_{sd}", 0.42, 0.03, 0.42, (xc, 0.015, z), L["steel"], bev=0.004, seg=1)
    for x in (1.5, 2.95, 4.4, 5.85, 7.3, 8.75, 10.2):
        for sd in (-1, 1):
            beam_between(f"purlin_{x}_{sd}", (sd * x, under_y(x) - 0.08, -HZ + 0.05), (sd * x, under_y(x) - 0.08, HZ - 0.05),
                         [(-0.035, -0.075), (0.035, -0.075), (0.035, 0.075), (-0.035, 0.075)], L["steel"], depth_dir=(-sd * 0.2, 0, 1))
    # wind bracing in the end bays
    for i in (0, 6):
        for sd in (-1, 1):
            z0, z1 = FRAME_Z[i], FRAME_Z[i + 1]
            for a, b in (((10.6, z0), (0.6, z1)), ((10.6, z1), (0.6, z0))):
                tube(f"brace_{i}_{sd}_{a}", [(sd * a[0], under_y(a[0]) - 0.3, a[1]), (sd * b[0], under_y(b[0]) - 0.3, b[1])], 0.012, L["steel"])
    # spiral ducts with seams and hangers
    for x in (-3.9, 3.9):
        cylinder(f"duct_{x}", 0.36, 34.0, (x, 5.45, -2.0), L["galv"], axis="z", segs=64)
        cylinder(f"duct_cap_{x}", 0.36, 0.02, (x, 5.45, 15.0), L["galv"], axis="z", segs=64)
        seams = []
        for k in range(23):
            seams.append(cylinder(f"duct_seam_{x}_{k}", 0.364, 0.025, (x, 5.45, -18.5 + k * 1.5), L["galv"], axis="z", segs=64))
        for z in range(-17, 14, 4):
            for dx in (-0.3, 0.3):
                tube(f"duct_hanger_{x}_{z}_{dx}", [(x + dx, 5.45, z), (x + dx, under_y(x) - 0.05, z)], 0.005, L["steel"])
    # acoustic baffles above the lounge
    for ix, x in enumerate((-2.7, -0.9, 0.9, 2.7)):
        for k in range(9):
            z = -16 + k * 3.4
            m = L["felt_lilac"] if (ix + k) % 3 == 0 else L["felt_grey"]
            cuboid(f"baffle_{ix}_{k}", 0.05, 0.9, 3.0, (x, 6.6, z), m, bev=0.012, seg=2)
            for dz in (-1.2, 1.2):
                tube(f"baffle_wire_{ix}_{k}_{dz}", [(x, 7.05, z + dz), (x, under_y(x) - 0.05, z + dz)], 0.0018, L["steel"])
    # cable tray + sprinkler main along the hall
    cuboid("cable_tray", 0.4, 0.06, 2 * HZ - 4, (-1.2, 6.45, 0), L["galv"])
    cylinder("sprinkler_main", 0.03, 2 * HZ - 4, (1.2, 6.55, 0), L["steel"], axis="z", segs=16)


def court_fixtures(L, courts):
    """Linear LED high-bays above the courts (geometry; the light itself comes from lighting.py)."""
    use_collection("structure")
    spots = []
    for c in courts:
        for dx in (-1.9, 1.9):
            for dz in (-4.6, 0.0, 4.6):
                x, z = c["x"] + dx, c["z"] + dz
                cuboid(f"highbay_{c['n']}_{dx}_{dz}", 0.16, 0.07, 1.26, (x, 5.32, z), L["alu_black"], bev=0.01, seg=2)
                cuboid(f"highbay_lens_{c['n']}_{dx}_{dz}", 0.13, 0.008, 1.2, (x, 5.282, z), L["led_white"])
                for o in (-0.45, 0.45):
                    tube(f"highbay_wire_{c['n']}_{dx}_{dz}_{o}", [(x, 5.36, z + o), (x, under_y(x) - 0.05, z + o)], 0.0018, L["steel"])
                spots.append((x, 5.27, z))
    return spots


def wall_fittings(L):
    """Acoustic felt panels, wall protection, skirting, vertical lilac LED lines, fire extinguishers."""
    use_collection("hall")
    for sd in (-1, 1):
        cuboid(f"wall_guard_{sd}", 0.05, 1.1, 33.0, (sd * 10.97, 0.55, -1.0), L["rubber"], bev=0.01, seg=2)
        cuboid(f"skirting_{sd}", 0.03, 0.1, 2 * HZ - 0.2, (sd * 10.985, 0.05, 0), L["rubber"])
    panels = [(-1, -9.5), (-1, 0.0), (-1, 6.5), (-1, 12.0), (1, -9.5), (1, 0.0), (1, 6.5), (1, 12.0)]
    # slatted acoustic panels (black felt backing, stained slats), the same language as the back wall
    for i, (sd, z) in enumerate(panels):
        for k, o in enumerate((-1.25, 1.25)):
            zc = z + o
            cuboid(f"wall_acoustic_{i}_{k}", 0.02, 2.4, 2.4, (sd * 10.985, 2.7, zc), L["felt_dark"])
            boxes(f"wall_acoustic_slats_{i}_{k}", [(sd * 10.955, 2.7, zc - 1.17 + j * 0.0757, 0.035, 2.4, 0.042) for j in range(31)], L["slat"])
    for i, z in enumerate(FRAME_Z):
        if i % 2 and i < 7:
            for sd in (-1, 1):
                cuboid(f"led_line_ch_{i}_{sd}", 0.04, 4.7, 0.05, (sd * 10.97, 3.05, z + 3.25), L["alu_black"])
                cuboid(f"led_line_{i}_{sd}", 0.012, 4.6, 0.03, (sd * 10.948, 3.05, z + 3.25), L["led_lilac"])
    for sd, z in ((-1, -6.0), (1, 14.0)):
        cylinder(f"extinguisher_{sd}", 0.075, 0.5, (sd * 10.85, 1.0, z), L["red"], segs=32)
        cylinder(f"extinguisher_top_{sd}", 0.03, 0.09, (sd * 10.85, 1.3, z), L["steel"], segs=16)
