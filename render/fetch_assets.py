"""Download the CC0 textures and models the hall renders use (Poly Haven, https://polyhaven.com).

Run once before rendering:  python3 render/fetch_assets.py
Files land in render/assets/ (not versioned). Every file is checked against the MD5 the API reports.
"""
import hashlib
import json
import os
import pathlib
import re
import ssl
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent / "assets"
API = "https://api.polyhaven.com/files/"

# python.org builds on macOS ship without CA certificates; fall back to the system bundle
_CTX = ssl.create_default_context()
if not _CTX.get_ca_certs() and os.path.exists("/etc/ssl/cert.pem"):
    _CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")

# texture id -> resolution; maps: colour, OpenGL normal, roughness (+ displacement where it matters)
TEXTURES = {
    "concrete_floor_worn_001": "4k",   # polished hall floor
    "painted_concrete_02": "2k",       # interior walls
    "white_stucco_02": "2k",           # facade render
    "box_profile_metal_sheet": "2k",   # trapezoid roof sheet
    "poly_wool_herringbone": "2k",     # sofa upholstery
    "velour_velvet": "2k",             # cushions
    "leather_white": "2k",             # leather, tinted per use
    "smoked_walnut_veneer": "2k",      # furniture veneer
    "gravel_floor_02": "2k",           # forecourt
    "concrete_pavement": "2k",         # entrance path and apron
    "rubberized_track": "2k",          # fine grain for the court surface
}
DISPLACEMENT = {"gravel_floor_02", "concrete_pavement"}

# model id -> resolution (glTF with textures)
MODELS = {
    "potted_plant_02": "2k",
    "potted_plant_04": "2k",
    "calathea_orbifolia_01": "2k",
    "anthurium_botany_01": "2k",
    "fern_02": "2k",
    "coffee_table_round_01": "2k",
    "modern_ceiling_lamp_01": "2k",
    "mid_century_lounge_chair": "2k",
    "modern_arm_chair_01": "2k",
    "Ottoman_01": "2k",
}


UA = {"User-Agent": "pbb-website-render/1.0 (Pickleball Buddies hall renders)"}


# OFL font for physical lettering on signs. A static instance from the Google Fonts CSS API: the variable font has
# overlapping outlines that Blender's curve fill turns into holes.
FONTS = {
    "BricolageGrotesque-SemiBold.ttf": "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@24,600",
}


def merge_outlines(path):
    """Union overlapping glyph contours (needs: pip install fonttools skia-pathops)."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.ttLib.removeOverlaps import removeOverlaps
    except ImportError:
        print("  note: pip install fonttools skia-pathops, then run again for clean sign lettering")
        return
    font = TTFont(path)
    removeOverlaps(font)
    font.save(path)
    print("  merged glyph outlines in", path.name)


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60, context=_CTX) as r:
        return json.load(r)


def download(url, dest, md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (md5 is None or hashlib.md5(dest.read_bytes()).hexdigest() == md5):
        return False
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300, context=_CTX) as r:
        data = r.read()
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise RuntimeError(f"checksum mismatch for {url}")
    dest.write_bytes(data)
    return True


def fetch_texture(tid, res):
    files = get_json(API + tid)
    maps = {"Diffuse": "diff", "nor_gl": "nor_gl", "Rough": "rough"}
    if tid in DISPLACEMENT:
        maps["Displacement"] = "disp"
    for key, short in maps.items():
        entry = files[key][res]["jpg"] if "jpg" in files[key][res] else files[key][res]["png"]
        ext = entry["url"].rsplit(".", 1)[1]
        new = download(entry["url"], ROOT / "textures" / tid / f"{short}.{ext}", entry.get("md5"))
        print(("  got " if new else "  ok  ") + f"{tid}/{short}.{ext}")


def fetch_model(mid, res):
    gl = get_json(API + mid)["gltf"][res]["gltf"]
    folder = ROOT / "models" / mid
    download(gl["url"], folder / f"{mid}.gltf", gl.get("md5"))
    for rel, inc in gl["include"].items():
        download(inc["url"], folder / rel, inc.get("md5"))
    print(f"  ok  model {mid}")


def main():
    only = set(sys.argv[1:])
    for tid, res in TEXTURES.items():
        if not only or tid in only:
            fetch_texture(tid, res)
    for mid, res in MODELS.items():
        if not only or mid in only:
            fetch_model(mid, res)
    for name, css in FONTS.items():
        with urllib.request.urlopen(urllib.request.Request(css, headers=UA), timeout=60, context=_CTX) as r:
            url = re.search(r"url\((https://[^)]+\.ttf)\)", r.read().decode()).group(1)
        path = ROOT / "fonts" / name
        new = download(url, path)
        print(("  got " if new else "  ok  ") + "font " + name)
        merge_outlines(path)
    print("assets ready in", ROOT)


if __name__ == "__main__":
    main()
