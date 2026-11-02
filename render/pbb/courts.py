"""Four pickleball courts (6.10 x 13.41 m, kitchen 2.13 m), nets, posts, benches, divider fences, and one large PBB
painted between the two courts of each side, in the kitchen colour."""
import math

from .logo import logo
from .util import HX, P, boxes, cuboid, cylinder, grid_mesh, tube, use_collection, wireframe

COURT_W, COURT_L, NVZ = 6.10, 13.41, 2.134
BLOCK_W, BLOCK_L, CX = 7.4, 16.0, 7.3
COURTS = [{"n": 1, "x": -CX, "z": -9.0}, {"n": 2, "x": CX, "z": -9.0}, {"n": 3, "x": -CX, "z": 7.0}, {"n": 4, "x": CX, "z": 7.0}]
GAP_Z = -1.0          # middle of the 2.6 m between the baselines of the back and front court on each side
FLOOR_LOGO_W = 3.0    # metres; the painted mark is then about 1.95 m deep and keeps 30 cm to both baselines


def _net_top(x):
    """Net height: 91.4 cm at the posts, 86.4 cm in the middle."""
    return 0.914 - 0.05 * (1 - (x / 3.35) ** 2)


def court(c, L):
    use_collection(f"court_{c['n']}")
    x, z = c["x"], c["z"]
    # coating layers (the run-off is one slab per side, see runoff()): playing area, kitchen, 5 cm lines
    cuboid(f"c{c['n']}_play", COURT_W, 0.002, COURT_L, (x, 0.0125, z), L["court_play"])
    cuboid(f"c{c['n']}_kitchen", COURT_W, 0.002, 2 * NVZ, (x, 0.0135, z), L["court_kitchen"])
    lw, ly = 0.05, 0.0145
    lines = []
    for s in (-1, 1):
        lines.append((x + s * (COURT_W / 2 - lw / 2), ly, z, lw, 0.002, COURT_L))
        lines.append((x, ly, z + s * (COURT_L / 2 - lw / 2), COURT_W, 0.002, lw))
        lines.append((x, ly, z + s * NVZ, COURT_W, 0.002, lw))
        half = COURT_L / 2 - NVZ
        lines.append((x, ly, z + s * (NVZ + half / 2), lw, 0.002, half))
    boxes(f"c{c['n']}_lines", lines, L["court_line"])
    # posts, net, tape, centre strap
    for s in (-1, 1):
        cylinder(f"c{c['n']}_post_{s}", 0.045, 1.06, (x + s * 3.4, 0.53, z), L["alu_black"], segs=32)
        cylinder(f"c{c['n']}_postcap_{s}", 0.048, 0.03, (x + s * 3.4, 1.075, z), L["chrome"], segs=32)
        cylinder(f"c{c['n']}_postbase_{s}", 0.19, 0.012, (x + s * 3.4, 0.006, z), L["alu_black"], segs=48)
    net = grid_mesh(f"c{c['n']}_net", 6.7, 0.86, 168, 21, L["net"], shape=lambda u, t: 0.07 + (_net_top(u) - 0.075) * t)
    net.location = P(x, 0, z)
    wireframe(net, 0.0024)
    tape = grid_mesh(f"c{c['n']}_tape", 6.74, 0.055, 64, 1, L["net_tape"], shape=lambda u, t: _net_top(u) - 0.055 + 0.055 * t)
    tape.location = P(x, 0, z)
    sol = tape.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.012
    sol.offset = 0
    cuboid(f"c{c['n']}_strap", 0.05, 0.82, 0.008, (x, 0.47, z), L["net_tape"])
    tube(f"c{c['n']}_bottomcord", [(x - 3.35, 0.07, z), (x + 3.35, 0.07, z)], 0.003, L["net"])
    # benches along the wall
    wx = math.copysign(HX - 0.45, x)
    for dz in (-3.2, 3.2):
        cuboid(f"c{c['n']}_bench_{dz}", 0.42, 0.05, 1.7, (wx, 0.45, z + dz), L["walnut"], bev=0.012, seg=3)
        legs = [(wx + m, 0.21, z + dz + l, 0.04, 0.42, 0.04) for l in (-0.7, 0.7) for m in (-0.15, 0.15)]
        legs += [(wx, 0.4, z + dz + l, 0.34, 0.03, 0.04) for l in (-0.7, 0.7)]
        boxes(f"c{c['n']}_bench_frame_{dz}", legs, L["steel"])


def runoff(L):
    """One continuous run-off coating per side (no seam between the courts) with the big PBB painted in the gap,
    readable from the entrance; same paint as the kitchens."""
    use_collection("courts_shared")
    z0, z1 = min(c["z"] for c in COURTS) - BLOCK_L / 2, max(c["z"] for c in COURTS) + BLOCK_L / 2
    for sd in (-1, 1):
        cuboid(f"runoff_{sd}", BLOCK_W, 0.012, z1 - z0, (sd * CX, 0.006, (z0 + z1) / 2), L["court_run"], bev=0.004, seg=1)
        logo(f"floor_logo_{sd}", FLOOR_LOGO_W, L["court_kitchen"], (sd * CX, 0.0128, GAP_Z), lie_flat=True, flat=True, weight=1.4)


def fences(L):
    """Low mesh fences between lounge and courts, with a lilac floor strip on the lounge side."""
    use_collection("courts_shared")
    for x in (-3.6, 3.6):
        for z0, z1 in ((-16.8, -1.6), (-0.4, 14.8)):
            ln, cz = z1 - z0, (z0 + z1) / 2
            panel = grid_mesh(f"fence_mesh_{x}_{z0}", ln, 0.98, int(ln / 0.05), 20, L["steel"])
            panel.location = P(x, 0.62, cz)
            panel.rotation_euler = (0, 0, math.pi / 2)
            wireframe(panel, 0.003)
            n = max(2, round(ln / 2.2))
            parts = [(x, 0.58, z0 + ln * i / n, 0.06, 1.16, 0.06) for i in range(n + 1)]
            parts += [(x, 1.13, cz, 0.06, 0.05, ln), (x, 0.11, cz, 0.04, 0.04, ln)]
            boxes(f"fence_frame_{x}_{z0}", parts, L["steel"])
            cuboid(f"fence_led_{x}_{z0}", 0.03, 0.01, ln, (x - math.copysign(0.14, x), 0.005, cz), L["led_lilac"])


def build(L):
    for c in COURTS:
        court(c, L)
    runoff(L)
    fences(L)
    return COURTS
