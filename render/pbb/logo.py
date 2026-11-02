"""The PBB signature as real geometry: neon tubes for signs, flat paint strokes for the court floors.
Reads the same SVG the website uses (assets/pbb-logo.svg, traced from the founders' neon sign by trace_logo.py),
so print, web and render share one mark, including its tube thickness."""
import math
import pathlib
import re

import bpy

from .util import P, link

SVG = pathlib.Path(__file__).resolve().parents[2] / "assets" / "pbb-logo.svg"


def _paths():
    s = SVG.read_text()
    w, h = (float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s).groups())
    tube = float(re.search(r'stroke-width="([\d.]+)"', s).group(1))
    d = re.search(r'\sd="([^"]+)"', s).group(1)
    toks = re.findall(r"[MC]|-?\d+\.?\d*", d)
    subs, i = [], 0
    while i < len(toks):
        if toks[i] == "M":
            subs.append({"start": (float(toks[i + 1]), float(toks[i + 2])), "segs": []})
            i += 3
        elif toks[i] == "C":
            v = [float(t) for t in toks[i + 1:i + 7]]
            subs[-1]["segs"].append(((v[0], v[1]), (v[2], v[3]), (v[4], v[5])))
            i += 7
        else:
            i += 1
    return w, h, tube, subs


def logo(name, width, mat, at, ry=0.0, lie_flat=False, flat=False, weight=1.0, coll=None):
    """Logo centred at three.js point `at`, `width` metres wide (the SVG viewBox), tube as thick as in the sign
    (times `weight`, e.g. bolder paint for a floor mark seen at a grazing angle).
    Standing logos face +z (towards the entrance); ry turns them about the vertical. lie_flat puts it on the floor."""
    w, h, tube, subs = _paths()
    s = width / w
    radius = tube * s / 2 * weight
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    cu.resolution_u = 24
    X = lambda p: ((p[0] - w / 2) * s, 0.0, (h / 2 - p[1]) * s)
    for sub in subs:
        segs = sub["segs"]
        pts = [sub["start"]] + [seg[2] for seg in segs]
        closed = len(segs) > 2 and math.dist(pts[0], pts[-1]) < 0.5
        if closed:                      # a loop of tube (the big oval): one seamless cyclic spline
            pts = pts[:-1]
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(pts) - 1)
        for k, p in enumerate(pts):
            bp = sp.bezier_points[k]
            bp.co = X(p)
            bp.handle_left_type = bp.handle_right_type = "FREE"
            if k > 0:
                bp.handle_left = X(segs[k - 1][1])
            else:
                bp.handle_left = X(segs[-1][1]) if closed else X(p)
            bp.handle_right = X(segs[k][0]) if k < len(segs) else X(p)
        sp.use_cyclic_u = closed
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    # flat = painted stroke: squash the round tube to a thin film (local Y is the logo's depth axis)
    ob.scale = (1, 0.04 if flat else 1, 1)
    # lie_flat: -90 deg about X turns the logo face up, its top pointing to the back wall
    ob.rotation_euler = (-math.pi / 2 if lie_flat else 0, 0, ry)
    ob.location = P(*at)
    return link(ob, coll)
