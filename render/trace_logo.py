"""Trace the PBB neon sign photo into a centre-line SVG (one smooth stroke per neon tube).

  python3 render/trace_logo.py [assets/brand/pbb-neon.jpg] [assets/pbb-logo.svg]

The founders' logo is a neon sign: lilac tubes of one constant width on black. A filled outline would only work for
flat print, so this script recovers the tube centre lines instead; the website strokes them (tube + glow) and the
renders sweep a round tube along them. Steps: threshold the tube, skeletonise, turn the skeleton into a graph,
join the branches that run straight through a crossing, cut the distorted skeleton out of every junction, smooth,
then fit cubic Béziers (Schneider). Prints the measured tube width in viewBox units.
"""
import math
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "brand" / "pbb-neon.jpg"
DST = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets" / "pbb-logo.svg"
WIDTH = 640.0          # viewBox width the logo is scaled to
TUBE = "#d7a7f3"       # tube colour measured from the sign
MERGE = 30.0           # junction clusters closer than this (px) are one crossing (a shallow X skeletonises as two Ys)
CUT = 16.0             # minimum radius around a junction where the skeleton is replaced (grows for shallow angles)
STRAIGHT = math.radians(140)    # branches meeting at more than this angle continue through a junction
SIGMA = 4.0            # smoothing of the centre line along its length (px); a bent glass tube has no kinks
TOL = 0.5              # Bézier fit tolerance in source pixels (the tube is ~15 px wide)


def skeleton_graph(mask):
    sk = skeletonize(mask)
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    deg = np.where(sk, nb, 0)
    ys, xs = np.nonzero(sk)
    pix = set(zip(ys.tolist(), xs.tolist()))
    # junction pixels -> clusters; endpoints are their own nodes
    lab, n = ndi.label((deg >= 3) & sk, structure=np.ones((3, 3)))
    nodes, owner = [], {}
    for k in range(1, n + 1):
        pts = np.argwhere(lab == k)
        nodes.append({"c": pts.mean(axis=0)[::-1], "kind": "junction"})
        for p in map(tuple, pts):
            owner[p] = len(nodes) - 1
    for p in pix:
        if deg[p] == 1:
            nodes.append({"c": np.array([p[1], p[0]], float), "kind": "end"})
            owner[p] = len(nodes) - 1

    def nbrs(p):
        y, x = p
        return [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and (y + dy, x + dx) in pix]

    edges, done, touching = [], set(), set()
    for start in owner:
        for q in nbrs(start):
            if q in owner:
                key = frozenset((owner[start], owner[q]))
                if owner[q] != owner[start] and key not in touching:      # two nodes touching directly
                    touching.add(key)
                    edges.append({"a": owner[start], "b": owner[q], "pts": [start, q]})
                continue
            if q in done:          # this branch was already traced (from another pixel of the cluster or the far end)
                continue
            path, prev, cur = [start, q], start, q
            while cur not in owner:
                nxt = [r for r in nbrs(cur) if r != prev and r not in path[-3:]]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                path.append(cur)
            done.update(path[1:-1])
            if cur in owner:
                edges.append({"a": owner[start], "b": owner[cur], "pts": path})
    for e in edges:
        e["pts"] = np.array([(x, y) for y, x in e["pts"]], float)
    return nodes, edges


def merge_close(nodes, edges):
    """Collapse short edges between junctions into one crossing node."""
    parent = list(range(len(nodes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    short = lambda e: nodes[e["a"]]["kind"] == nodes[e["b"]]["kind"] == "junction" and len(e["pts"]) < MERGE
    for e in edges:
        if short(e):
            parent[find(e["a"])] = find(e["b"])
    keep = [e for e in edges if not short(e)]
    groups = {}
    for i in range(len(nodes)):
        groups.setdefault(find(i), []).append(i)
    remap, out = {}, []
    for root, members in groups.items():
        c = np.mean([nodes[m]["c"] for m in members], axis=0)
        out.append({"c": c, "kind": nodes[root]["kind"]})
        for m in members:
            remap[m] = len(out) - 1
    for e in keep:
        e["a"], e["b"] = remap[e["a"]], remap[e["b"]]
    return out, keep


def end_dir(pts, at_start, reach=34.0):
    """Unit direction leaving the node along the edge, measured beyond the distorted zone."""
    p = pts if at_start else pts[::-1]
    d = np.cumsum(np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)])
    i0 = np.searchsorted(d, min(CUT, d[-1] * 0.4))
    i1 = np.searchsorted(d, min(reach + CUT, d[-1]))
    v = p[min(i1, len(p) - 1)] - p[min(i0, len(p) - 1)]
    return v / (np.linalg.norm(v) + 1e-9)


def build_strokes(nodes, edges):
    ends = {}            # node -> [(edge index, at_start)]
    for i, e in enumerate(edges):
        ends.setdefault(e["a"], []).append((i, True))
        ends.setdefault(e["b"], []).append((i, False))
    pair = {}
    for n, lst in ends.items():
        cand = []
        for x in range(len(lst)):
            for y in range(x + 1, len(lst)):
                (ea, sa), (eb, sb) = lst[x], lst[y]
                if ea == eb:
                    continue
                da = end_dir(edges[ea]["pts"], sa)
                db = end_dir(edges[eb]["pts"], sb)
                ang = math.acos(max(-1, min(1, float(da @ db))))
                if ang > STRAIGHT:
                    cand.append((ang, lst[x], lst[y]))
        for ang, a, b in sorted(cand, reverse=True):
            if a not in pair and b not in pair:
                pair[a], pair[b] = b, a
    strokes, used = [], set()

    def walk(ei, forward):
        """Follow edges through paired junctions; returns ordered list of (edge, forward)."""
        seq = [(ei, forward)]
        used.add(ei)
        while True:
            e, f = seq[-1]
            tail = (e, not f)          # the end we leave from
            nxt = pair.get(tail)
            if nxt is None or nxt[0] in used:
                closed = nxt is not None and nxt[0] == seq[0][0]
                return seq, closed
            seq.append((nxt[0], nxt[1]))
            used.add(nxt[0])

    for i in range(len(edges)):
        if i in used:
            continue
        seq, closed = walk(i, True)
        if not closed:                 # extend backwards from the start too
            back = pair.get((i, True))
            if back is not None and back[0] not in used:
                pre, _ = walk(back[0], back[1])
                seq = [(e, not f) for e, f in reversed(pre)] + seq
        strokes.append((seq, closed))
    return strokes


def cut_radius(nodes, edges, tube):
    """Radius around each junction where the skeleton is distorted. Two tubes meeting at angle a overlap over
    tube / sin(a) of their length, so shallow crossings and V joins need a wider cut than steep ones."""
    out = {}
    for n, node in enumerate(nodes):
        if node["kind"] != "junction":
            continue
        dirs = [end_dir(ed["pts"], at_start) for ed in edges for at_start in (True, False) if (ed["a"] if at_start else ed["b"]) == n]
        r = CUT
        for i in range(len(dirs)):
            for j in range(i + 1, len(dirs)):
                s = abs(dirs[i][0] * dirs[j][1] - dirs[i][1] * dirs[j][0])     # |sin| of the angle between two lines
                if s > 0.15:
                    r = max(r, tube / s + tube / 2)
        out[n] = min(r, 42.0)
    return out


def stroke_points(seq, closed, nodes, edges, cuts):
    """Concatenate edge polylines, replacing every junction neighbourhood with a smooth Hermite bridge."""
    runs, ends = [], []
    for e, f in seq:
        ed = edges[e]
        p = ed["pts"] if f else ed["pts"][::-1]
        na, nb = (ed["a"], ed["b"]) if f else (ed["b"], ed["a"])
        keep = np.ones(len(p), bool)
        for n in (na, nb):
            if n in cuts:
                keep &= np.linalg.norm(p - nodes[n]["c"], axis=1) > cuts[n]
        runs.append(p[keep])
        ends.append((na, nb))
    # a short edge between two close junctions can vanish completely; the bridge then spans both junctions
    runs = [r for r in runs if len(r) >= 3]
    pts = [runs[0]]
    for k in range(1, len(runs)):
        pts.append(bridge(runs[k - 1], runs[k]))
        pts.append(runs[k])
    if closed:
        pts.append(bridge(runs[-1], runs[0]))
    out = np.vstack(pts)
    if not closed:
        # a stroke that stops on another tube (T or V join) runs on to that tube's centre line
        if ends[0][0] in cuts:
            out = extend(out[::-1], nodes[ends[0][0]]["c"])[::-1]
        if ends[-1][1] in cuts:
            out = extend(out, nodes[ends[-1][1]]["c"])
    return out


def tangent(p, at_end, reach=26.0):
    """Unit direction at one end of a polyline (pointing outwards), from a line fit over `reach` pixels."""
    q = p[::-1] if at_end else p
    d = np.cumsum(np.r_[0, np.linalg.norm(np.diff(q, axis=0), axis=1)])
    seg = q[:max(3, np.searchsorted(d, reach))]
    c = seg - seg.mean(axis=0)
    v = np.linalg.svd(c, full_matrices=False)[2][0]
    return v if v @ (q[0] - seg[-1]) > 0 else -v


def bridge(a, b):
    p0, p1 = a[-1], b[0]
    t0, t1 = tangent(a, True), -tangent(b, False)
    L = np.linalg.norm(p1 - p0)
    s = np.linspace(0, 1, max(3, int(L)))[1:-1, None]
    h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
    return h00 * p0 + h10 * L * t0 + h01 * p1 + h11 * L * t1


def extend(p, target):
    t = tangent(p, True)
    L = np.linalg.norm(target - p[-1])
    # Hermite from the last kept point into the junction centre, leaving along the stroke direction
    s = np.linspace(0, 1, max(3, int(L)))[1:, None]
    t1 = (target - p[-1]) / (L + 1e-9)
    h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
    return np.vstack([p, h00 * p[-1] + h10 * L * t + h01 * target + h11 * L * t1])


def resample(p, step=1.0, closed=False):
    if closed:
        p = np.vstack([p, p[:1]])
    d = np.cumsum(np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)])
    n = max(4, int(d[-1] / step))
    s = np.linspace(0, d[-1], n + 1)
    q = np.c_[np.interp(s, d, p[:, 0]), np.interp(s, d, p[:, 1])]
    return q[:-1] if closed else q


def smooth(p, sigma, closed):
    if closed:
        return np.c_[ndi.gaussian_filter1d(p[:, 0], sigma, mode="wrap"), ndi.gaussian_filter1d(p[:, 1], sigma, mode="wrap")]
    # pad by reflecting through the end points so the ends keep their position and direction
    k = int(4 * sigma)
    a = 2 * p[0] - p[1:k + 1][::-1]
    b = 2 * p[-1] - p[-k - 1:-1][::-1]
    q = np.vstack([a, p, b])
    q = np.c_[ndi.gaussian_filter1d(q[:, 0], sigma), ndi.gaussian_filter1d(q[:, 1], sigma)]
    return q[k:-k]


# ---------------------------------------------------------------- Schneider curve fitting
def _bez(b, t):
    t = np.asarray(t)[:, None]
    return (1 - t)**3 * b[0] + 3 * (1 - t)**2 * t * b[1] + 3 * (1 - t) * t**2 * b[2] + t**3 * b[3]


def _bez_d(b, t):
    t = np.asarray(t)[:, None]
    return 3 * (1 - t)**2 * (b[1] - b[0]) + 6 * (1 - t) * t * (b[2] - b[1]) + 3 * t**2 * (b[3] - b[2])


def _bez_dd(b, t):
    t = np.asarray(t)[:, None]
    return 6 * (1 - t) * (b[2] - 2 * b[1] + b[0]) + 6 * t * (b[3] - 2 * b[2] + b[1])


def _generate(pts, u, t1, t2):
    b0, b3 = pts[0], pts[-1]
    B = np.c_[3 * (1 - u)**2 * u, 3 * (1 - u) * u**2]
    a1, a2 = B[:, :1] * t1, B[:, 1:] * t2
    C = np.array([[np.sum(a1 * a1), np.sum(a1 * a2)], [np.sum(a1 * a2), np.sum(a2 * a2)]])
    base = (1 - u)[:, None]**3 * b0 + 3 * (1 - u)[:, None]**2 * u[:, None] * b0 + 3 * (1 - u)[:, None] * u[:, None]**2 * b3 + u[:, None]**3 * b3
    tmp = pts - base
    X = np.array([np.sum(a1 * tmp), np.sum(a2 * tmp)])
    det = C[0, 0] * C[1, 1] - C[0, 1]**2
    seg = np.linalg.norm(b3 - b0)
    if abs(det) > 1e-12:
        al = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det
        ar = (C[0, 0] * X[1] - C[0, 1] * X[0]) / det
    else:
        al = ar = seg / 3
    eps = 1e-6 * seg
    if al < eps or ar < eps:
        al = ar = seg / 3
    return np.array([b0, b0 + t1 * al, b3 + t2 * ar, b3])


def _reparam(b, pts, u):
    d = _bez(b, u) - pts
    d1, d2 = _bez_d(b, u), _bez_dd(b, u)
    num = np.sum(d * d1, axis=1)
    den = np.sum(d1 * d1, axis=1) + np.sum(d * d2, axis=1)
    return np.clip(u - np.where(np.abs(den) > 1e-12, num / den, 0), 0, 1)


def _chord(pts):
    d = np.cumsum(np.r_[0, np.linalg.norm(np.diff(pts, axis=0), axis=1)])
    return d / d[-1]


def _err(b, pts, u):
    e = np.sum((_bez(b, u) - pts)**2, axis=1)
    i = int(np.argmax(e[1:-1])) + 1 if len(e) > 2 else len(e) // 2
    return float(np.sqrt(e[i])), i


def fit(pts, t1, t2, tol):
    if len(pts) == 2:
        d = np.linalg.norm(pts[1] - pts[0]) / 3
        return [np.array([pts[0], pts[0] + t1 * d, pts[1] + t2 * d, pts[1]])]
    u = _chord(pts)
    b = _generate(pts, u, t1, t2)
    e, split = _err(b, pts, u)
    if e < tol:
        return [b]
    if e < tol * 6:
        for _ in range(30):
            u = _reparam(b, pts, u)
            b = _generate(pts, u, t1, t2)
            e, split = _err(b, pts, u)
            if e < tol:
                return [b]
    tc = pts[split - 1] - pts[split + 1]
    tc /= np.linalg.norm(tc)
    return fit(pts[:split + 1], t1, tc, tol) + fit(pts[split:], -tc, t2, tol)


def fit_stroke(p, closed):
    if closed:
        # start the loop where it is straightest, so the seam sits on a calm stretch
        k = len(p)
        a, b = np.roll(p, -6, axis=0) - p, p - np.roll(p, 6, axis=0)
        turn = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
        i0 = int(np.argmin(ndi.uniform_filter1d(turn, 15, mode="wrap")))
        p = np.vstack([np.roll(p, -i0, axis=0), np.roll(p, -i0, axis=0)[:1]])
        t = p[1] - p[-2]
        t /= np.linalg.norm(t)
        return fit(p, t, -t, TOL)
    t1 = p[min(3, len(p) - 1)] - p[0]
    t2 = p[max(-4, -len(p))] - p[-1]
    return fit(p, t1 / np.linalg.norm(t1), t2 / np.linalg.norm(t2), TOL)


def main():
    im = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    lum = im.mean(axis=2)
    mask = ndi.binary_opening(lum > 135, iterations=1)
    half = ndi.distance_transform_edt(mask)
    nodes, edges = skeleton_graph(mask)
    nodes, edges = merge_close(nodes, edges)
    strokes = build_strokes(nodes, edges)
    tube_px = 2 * float(np.median(half[skeletonize(mask)])) + 1.0
    cuts = cut_radius(nodes, edges, tube_px)
    beziers = []
    for seq, closed in strokes:
        p = stroke_points(seq, closed, nodes, edges, cuts)
        p = resample(p, 1.0, closed)
        p = smooth(p, SIGMA, closed)
        beziers.append(fit_stroke(p, closed))
    allp = np.vstack([np.vstack(b) for b in beziers])
    lo, hi = allp.min(axis=0) - tube_px, allp.max(axis=0) + tube_px
    s = WIDTH / (hi[0] - lo[0])
    vw, vh = WIDTH, round((hi[1] - lo[1]) * s, 1)
    f = lambda q: f"{(q[0] - lo[0]) * s:.2f} {(q[1] - lo[1]) * s:.2f}"
    d = []
    for segs in beziers:
        d.append("M" + f(segs[0][0]) + "".join("C" + " ".join(f(q) for q in b[1:]) for b in segs))
    tube = round(tube_px * s, 2)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:g} {vh:g}">'
           f'<path fill="none" stroke="{TUBE}" stroke-width="{tube}" stroke-linecap="round" stroke-linejoin="round" d="{"".join(d)}"/></svg>\n')
    DST.write_text(svg)
    print(f"{len(strokes)} strokes, {sum(len(b) for b in beziers)} Bézier segments, viewBox 0 0 {vw:g} {vh:g}, tube {tube} units -> {DST}")


if __name__ == "__main__":
    main()
