"""Scanned CC0 models (render/assets/models): imported once into hidden library collections, placed as instances."""
import pathlib

import bpy
from mathutils import Vector

from .util import P, collection, link

MODELS = pathlib.Path(__file__).resolve().parents[1] / "assets" / "models"


def _library_root():
    root = collection("_library")
    lc = bpy.context.view_layer.layer_collection.children.get("_library")
    if lc:
        lc.exclude = True
    return root


def load(model):
    """Import a glTF; every mesh becomes its own library collection 'lib:<mesh name>', base centred on the origin."""
    root = _library_root()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(next((MODELS / model).glob("*.gltf"))))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
    meshes = [o for o in new if o.type == "MESH"]
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    # objects that share a model (pot + leaves + soil) stay together; multi-variant plant sheets get split per variant
    groups = {}
    for o in meshes:
        o.matrix_world = o.matrix_world.copy()
        o.parent = None
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        cx = round((min(v.x for v in bb) + max(v.x for v in bb)) / 2, 1)
        cy = round((min(v.y for v in bb) + max(v.y for v in bb)) / 2, 1)
        key = o.name if len(meshes) > 1 and _is_variant_sheet(model) else model
        groups.setdefault(key, []).append(o)
    names = []
    for key, obs in groups.items():
        bb = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
        base = Vector(((min(v.x for v in bb) + max(v.x for v in bb)) / 2, (min(v.y for v in bb) + max(v.y for v in bb)) / 2, min(v.z for v in bb)))
        c = bpy.data.collections.new("lib:" + key)
        root.children.link(c)
        for o in obs:
            o.location -= base
            c.objects.link(o)
        names.append(c.name)
    return names


def _is_variant_sheet(model):
    return model in ("anthurium_botany_01", "calathea_orbifolia_01", "fern_02")


def place(lib, name, at, rz=0.0, scale=1.0, coll=None):
    ob = bpy.data.objects.new(name, None)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = bpy.data.collections[lib]
    ob.location = P(*at)
    ob.rotation_euler = (0, 0, rz)
    ob.scale = (scale, scale, scale)
    return link(ob, coll)


def recolor(lib, slot_name, base_color=None, mat=None):
    """Swap a material on a library model, e.g. the orange chevron pillows for lilac velvet."""
    for o in bpy.data.collections[lib].all_objects:
        for i, m in enumerate(o.data.materials):
            if m and slot_name in m.name:
                if mat is not None:
                    o.data.materials[i] = mat
                elif base_color is not None:
                    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                    for l in list(b.inputs["Base Color"].links):
                        m.node_tree.links.remove(l)
                    b.inputs["Base Color"].default_value = base_color
