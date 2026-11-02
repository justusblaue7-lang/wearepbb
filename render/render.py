"""Build the PBB hall in Blender and render the website stills with Cycles.

  blender -b --factory-startup --python render/render.py -- [options]

  --shots hero,courts     which shots (default: all in pbb/shots.py)
  --res 3840x2160         output size; portrait renders swap it automatically with --portrait
  --portrait              vertical framing for phones
  --samples 1024          max samples per pixel (adaptive sampling stops earlier where the image is clean)
  --out DIR               where PNGs go (default: render/out)
  --save-blend FILE       also save the built scene for inspection
  --exr                   write a multilayer EXR with light passes instead (colour calibration, see materials.FLIEDER)
"""
import argparse
import pathlib
import sys
import time

import bpy

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pbb import courts, exterior, hall, interior, lighting, materials  # noqa: E402
from pbb.materials import LOOK, VIEW  # noqa: E402
from pbb.shots import SHOTS  # noqa: E402
from pbb.util import P  # noqa: E402


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    L = materials.build_library()
    hall.floor(L)
    hall.walls(L)
    hall.roof(L)
    hall.windows(L)
    hall.structure(L)
    highbays = hall.court_fixtures(L, courts.COURTS)
    hall.wall_fittings(L)
    courts.build(L)
    extra = interior.build(L)
    extra += exterior.build(L)
    lighting.build(highbays, extra)


def setup_cycles(samples, w, h):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    cy = sc.cycles
    cy.device = "GPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.008
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.denoising_prefilter = "ACCURATE"
    for attr, val in (("denoising_quality", "HIGH"), ("denoising_use_gpu", True)):
        if hasattr(cy, attr):
            setattr(cy, attr, val)
    cy.max_bounces = 12
    cy.diffuse_bounces = 5
    cy.glossy_bounces = 6
    cy.transmission_bounces = 12
    cy.transparent_max_bounces = 16
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 0.5
    cy.sample_clamp_indirect = 8.0
    cy.use_light_tree = True
    sc.render.film_transparent = False
    sc.render.filter_size = 1.2
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "16"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = VIEW
    try:
        sc.view_settings.look = LOOK
    except TypeError:
        pass


GLARE_THRESHOLD = 1.2


def setup_glare():
    """Gentle photographic bloom around neon and lamps (what a real lens does at night)."""
    sc = bpy.context.scene
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    gl = nt.nodes.new("CompositorNodeGlare")
    out = nt.nodes.new("CompositorNodeComposite")
    gl.glare_type = "FOG_GLOW"
    for attr, val in (("quality", "HIGH"), ("threshold", GLARE_THRESHOLD), ("size", 8), ("mix", -0.82)):
        if hasattr(gl, attr):
            try:
                setattr(gl, attr, val)
            except (TypeError, AttributeError):
                pass
    for name, val in (("Threshold", GLARE_THRESHOLD), ("Highlights Threshold", GLARE_THRESHOLD), ("Strength", 0.18), ("Size", 0.6)):
        if name in gl.inputs:
            gl.inputs[name].default_value = val
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
    nt.links.new(gl.outputs["Image"], out.inputs["Image"])


def setup_passes():
    """Scene-linear multilayer EXR with the light passes and material index, for measuring surface colours."""
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    for p in ("use_pass_diffuse_direct", "use_pass_diffuse_indirect", "use_pass_diffuse_color", "use_pass_glossy_direct",
              "use_pass_glossy_indirect", "use_pass_glossy_color", "use_pass_material_index", "use_pass_emit"):
        setattr(vl, p, True)
    sc.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    sc.render.image_settings.color_depth = "32"
    sc.render.image_settings.exr_codec = "ZIP"
    for i, name in enumerate(("court_kitchen", "felt_lilac", "velvet_lilac", "rug_wool_lilac"), 1):
        bpy.data.materials[name].pass_index = i


def set_camera(shot, portrait):
    sc = bpy.context.scene
    cam = bpy.data.objects.get("camera")
    if cam is None:
        cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
        sc.collection.objects.link(cam)
    sc.camera = cam
    c = cam.data
    c.sensor_width = 36.0
    c.sensor_fit = "VERTICAL" if portrait else "HORIZONTAL"
    c.sensor_height = 36.0 if portrait else 24.0
    c.lens = shot["lens_portrait"] if portrait else shot["lens"]
    c.clip_start, c.clip_end = 0.05, 3000
    pos, look = P(*shot["cam"]), P(*shot["look"])
    cam.location = pos
    cam.rotation_euler = (look - pos).to_track_quat("-Z", "Y").to_euler()
    c.dof.use_dof = True
    c.dof.focus_distance = (look - pos).length
    c.dof.aperture_fstop = 8.0
    sc.view_settings.exposure = shot["exposure"]
    # brand emitters and the bloom threshold follow the exposure, so the neon shows the same Flieder in every still
    gain = 2.0 ** -shot["exposure"]
    for m in bpy.data.materials:
        if m.node_tree and "cam_gain" in m.node_tree.nodes:
            m.node_tree.nodes["cam_gain"].outputs[0].default_value = gain
    if sc.node_tree:
        for n in sc.node_tree.nodes:
            if n.type == "GLARE":
                for name in ("Threshold", "Highlights Threshold"):
                    if name in n.inputs:
                        n.inputs[name].default_value = GLARE_THRESHOLD * gain
                if hasattr(n, "threshold"):
                    n.threshold = GLARE_THRESHOLD * gain
    lighting.world(shot["world"])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=",".join(SHOTS))
    ap.add_argument("--res", default="3840x2160")
    ap.add_argument("--portrait", action="store_true")
    ap.add_argument("--samples", type=int, default=1024)
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--save-blend", default="")
    ap.add_argument("--exr", action="store_true")
    a = ap.parse_args(argv)
    w, h = (int(v) for v in a.res.lower().split("x"))
    if a.portrait:
        w, h = min(w, h), max(w, h)
    t0 = time.time()
    build_scene()
    print(f"[pbb] scene built in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects", flush=True)
    setup_cycles(a.samples, w, h)
    setup_glare()
    if a.exr:
        setup_passes()
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in a.shots.split(","):
        t1 = time.time()
        set_camera(SHOTS[name], a.portrait)
        sc = bpy.context.scene
        sc.render.filepath = str(out / f"{name}{'-portrait' if a.portrait else ''}.{'exr' if a.exr else 'png'}")
        bpy.ops.render.render(write_still=True)
        print(f"[pbb] {name}: {w}x{h} in {(time.time() - t1) / 60:.1f} min -> {sc.render.filepath}", flush=True)


if __name__ == "__main__":
    main()
