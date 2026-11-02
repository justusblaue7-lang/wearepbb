"""Geometry helpers. Coordinates follow the old web model: x across the hall, y up, z towards the entrance
(metres). P() converts them to Blender (Z up). Hall interior: x -11..11, z -25..25, entrance at z = +25."""
import math
import pathlib

import bmesh
import bpy
from mathutils import Matrix, Vector

HX, HZ, WT = 11.0, 25.0, 0.4          # half width, half length, wall thickness
EH, RH = 6.2, 8.4                     # eave and ridge height of the roof underside
K = (RH - EH) / HX


def under_y(x):
    """Height of the roof underside at |x|."""
    return EH + K * (HX - min(abs(x), 13.0))


def P(x, y, z):
    return Vector((x, -z, y))


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


_current = {"coll": None}


def use_collection(name):
    _current["coll"] = collection(name)
    return _current["coll"]


def link(obj, coll=None):
    (coll or _current["coll"] or bpy.context.scene.collection).objects.link(obj)
    return obj


def box_uv(bm, scale=1.0):
    """Cube projection in object metres, so tiling textures keep real-world size on every face."""
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            c = lp.vert.co
            if ax == 0:
                u, v = (c.y if n.x > 0 else -c.y), c.z
            elif ax == 1:
                u, v = (-c.x if n.y > 0 else c.x), c.z
            else:
                u, v = c.x, (c.y if n.z > 0 else -c.y)
            lp[uv].uv = (u * scale, v * scale)


def mesh_obj(name, bm, mats, loc=(0, 0, 0), rot_z=0.0, coll=None, uv=True, smooth=False):
    if uv:
        box_uv(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats if isinstance(mats, (list, tuple)) else [mats]:
        me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    return link(ob, coll)


def bevel(ob, width, segments=3, angle=40):
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.harden_normals = True
    ob.data.shade_smooth() if hasattr(ob.data, "shade_smooth") else None
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def subsurf(ob, levels=2):
    m = ob.modifiers.new("subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    return ob


def cuboid(name, w, h, d, at, mat, ry=0.0, bev=0.0, seg=3, coll=None):
    """Box of width w (x), height h (y up), depth d (z), centred at three.js point `at`, turned ry about the vertical."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, d, h), verts=bm.verts)
    ob = mesh_obj(name, bm, mat, loc=P(*at), rot_z=ry, coll=coll)
    if bev > 0:
        bevel(ob, bev, seg)
    return ob


def cylinder(name, r, h, at, mat, segs=48, axis="y", r2=None, coll=None, cap=True, ry=0.0):
    """Cylinder of height h along the three.js axis ('y' vertical, 'x', 'z'), centred at `at`."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
    if axis == "x":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    elif axis == "z":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    ob = mesh_obj(name, bm, mat, loc=P(*at), rot_z=ry, coll=coll)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.polygons.foreach_set("use_smooth", [len(p.vertices) == 4 for p in ob.data.polygons])
    return ob


def tube(name, pts, r, mat, coll=None, res=12):
    """Round tube through three.js points (poly line), e.g. hanger rods, rails."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = max(2, res // 4)
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        v = P(*p)
        sp.points[i].co = (v.x, v.y, v.z, 1)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    return link(ob, coll)


def extrude_profile(name, profile, length, mat, coll=None):
    """Extrude a 2D profile [(u, v)] along +Y (Blender) by `length`; returns object at origin."""
    bm = bmesh.new()
    vs = [bm.verts.new((u, 0, v)) for u, v in profile]
    face = bm.faces.new(vs)
    ret = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, length, 0), verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat, coll=coll)


def ibeam_profile(h, b, tf, tw):
    a, c, d = b / 2, h / 2, tw / 2
    return [(-a, -c), (a, -c), (a, -c + tf), (d, -c + tf), (d, c - tf), (a, c - tf), (a, c), (-a, c), (-a, c - tf), (-d, c - tf), (-d, -c + tf), (-a, -c + tf)]


def beam_between(name, a, b, profile, mat, depth_dir=None, coll=None):
    """Steel member with `profile` (u = flange width, v = depth) running from three.js point a to b.
    depth_dir: Blender vector the profile depth should point along (default: in the cross-hall plane)."""
    pa, pb = P(*a), P(*b)
    L = (pb - pa).length
    ob = extrude_profile(name, profile, L, mat, coll)
    y = (pb - pa).normalized()
    z = Vector(depth_dir) if depth_dir is not None else y.cross(Vector((0, 1, 0)))
    if z.length < 1e-6:
        z = Vector((1, 0, 0))
    z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    ob.matrix_world = Matrix.Translation(pa) @ rot
    return ob


def boxes(name, items, mat, coll=None):
    """Many boxes in one mesh. items: (cx, cy, cz, w, h, d) in three.js terms (w along x, h up, d along z)."""
    bm = bmesh.new()
    for cx, cy, cz, w, h, d in items:
        r = bmesh.ops.create_cube(bm, size=1.0)
        vs = r["verts"]
        bmesh.ops.scale(bm, vec=(w, d, h), verts=vs)
        bmesh.ops.translate(bm, vec=P(cx, cy, cz), verts=vs)
    return mesh_obj(name, bm, mat, coll=coll)


def wall_pieces(along, a0, a1, height, openings):
    """Split a wall run a0..a1 (0..height) around rectangular openings [(centre, width, y0, y1)] into solid pieces."""
    out, pos = [], a0
    for c, w, y0, y1 in sorted(openings):
        s0, s1 = c - w / 2, c + w / 2
        if s0 > pos:
            out.append((pos, s0, 0.0, height))
        if y0 > 0:
            out.append((s0, s1, 0.0, y0))
        if y1 < height:
            out.append((s0, s1, y1, height))
        pos = s1
    if pos < a1:
        out.append((pos, a1, 0.0, height))
    return out


def prism(name, poly, z0, z1, mat, coll=None):
    """Polygon [(x, y)] in the three.js x/y plane, extruded from z0 to z1 (e.g. a gable triangle)."""
    bm = bmesh.new()
    vs = [bm.verts.new(P(x, y, z0)) for x, y in poly]
    f = bm.faces.new(vs)
    ret = bmesh.ops.extrude_face_region(bm, geom=[f])
    moved = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=P(0, 0, z1 - z0) - P(0, 0, 0), verts=moved)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, mat, coll=coll)


FONT = pathlib.Path(__file__).resolve().parents[1] / "assets" / "fonts" / "BricolageGrotesque-SemiBold.ttf"


def text(name, body, size, at, mat, ry=0.0, spacing=1.0, extrude=0.002, align="CENTER", coll=None):
    """Upright physical lettering facing +z (towards the entrance) before ry is applied."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.space_character = spacing
    if FONT.exists():
        cu.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    ob.rotation_euler = (math.pi / 2, 0, ry)
    ob.location = P(*at)
    return link(ob, coll)


def grid_mesh(name, w, h, nx, ny, mat, shape=None, coll=None):
    """Vertical grid in the local x/y plane (three.js), optionally reshaped by shape(x, t) -> y for t in 0..1."""
    bm = bmesh.new()
    rows = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -w / 2 + w * i / nx
            y = shape(x, j / ny) if shape else -h / 2 + h * j / ny
            row.append(bm.verts.new(P(x, y, 0)))
        rows.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    return mesh_obj(name, bm, mat, coll=coll)


def wireframe(ob, thickness):
    m = ob.modifiers.new("cords", "WIREFRAME")
    m.thickness = thickness
    m.use_even_offset = True
    m.use_relative_offset = False
    m.use_replace = True
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def instance_of(coll_name, name, at, rz=0.0, scale=1.0, coll=None):
    ob = bpy.data.objects.new(name, None)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = bpy.data.collections[coll_name]
    ob.location = P(*at)
    ob.rotation_euler = (0, 0, rz)
    ob.scale = (scale, scale, scale)
    return link(ob, coll)
