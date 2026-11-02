"""Lights and world. Everything is physically placed: high-bays above the courts, lamps in their fittings, neon and LED
strips light the room through their own emission. The world is a dark night for interiors and a twilight sky outside."""
import math

import bpy

from .materials import lin
from .util import P, collection

HIGHBAY_W = 140.0      # per linear LED high-bay (24 above the courts)


def _light(kind, name, at, power, color, radius=0.05):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = power
    ld.color = lin(color)[:3]
    if kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    ob.visible_camera = False      # the fitting glows, not an abstract light disc
    ob.location = P(*at)
    collection("lights").objects.link(ob)
    return ob


def _aim(ob, target):
    d = P(*target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def build(highbays, extra):
    for i, at in enumerate(highbays):
        ob = _light("AREA", f"highbay_{i}", at, HIGHBAY_W, "#fff1e2")
        ob.data.shape = "RECTANGLE"
        ob.data.size = 0.13
        ob.data.size_y = 1.2
        ob.data.spread = math.radians(120)
    for i, (kind, at, p) in enumerate(extra):
        if kind == "point":
            _light("POINT", f"point_{i}", at, p["power"], p["color"], p.get("radius", 0.05))
        elif kind == "spot":
            ob = _light("SPOT", f"spot_{i}", at, p["power"], p["color"], p.get("radius", 0.05))
            ob.data.spot_size = p["angle"]
            ob.data.spot_blend = p["blend"]
            _aim(ob, p["target"])
        elif kind == "area":
            ob = _light("AREA", f"area_{i}", at, p["power"], p["color"])
            ob.data.shape = "RECTANGLE"
            ob.data.size, ob.data.size_y = p["size"]
            ob.rotation_euler = p.get("rot", (0, 0, 0))


def world(kind):
    w = bpy.data.worlds.get("pbb_world") or bpy.data.worlds.new("pbb_world")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs[0], out.inputs[0])
    if kind == "twilight":
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "NISHITA"
        sky.sun_disc = False
        sky.sun_elevation = math.radians(-2.4)
        sky.sun_rotation = math.radians(205)
        sky.altitude = 120
        sky.air_density = 1.0
        sky.dust_density = 1.6
        sky.ozone_density = 1.4
        nt.links.new(sky.outputs[0], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 1.0
    else:
        bg.inputs["Color"].default_value = lin("#0a0c12")
        bg.inputs["Strength"].default_value = 0.02
