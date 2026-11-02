"""Turn the 16-bit PNG renders into the web images the site loads.

  python3 render/export_web.py [render/out/final] [shot ...]

Landscape renders -> assets/renders/<shot>-{1280,1920,2560,3840}.webp/.jpg
Portrait renders  -> assets/renders/<shot>-portrait-{1080,1440,2160}.webp
WebP for every browser that supports it, JPEG as fallback; 4:4:4 chroma so lilac edges stay clean.
"""
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "render" / "out" / "final"
ONLY = set(sys.argv[2:])          # optional: export just these shots (e.g. hero courts-portrait)
DST = ROOT / "assets" / "renders"
LANDSCAPE = (1280, 1920, 2560, 3840)
PORTRAIT = (1080, 1440, 2160)


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for png in sorted(SRC.glob("*.png")):
        if ONLY and png.stem not in ONLY:
            continue
        im = Image.open(png).convert("RGB")
        portrait = png.stem.endswith("-portrait")
        widths = PORTRAIT if portrait else LANDSCAPE
        for w in widths:
            if w > im.width:
                continue
            h = round(im.height * w / im.width)
            out = im if w == im.width else im.resize((w, h), Image.LANCZOS)
            base = DST / f"{png.stem}-{w}"
            out.save(base.with_suffix(".webp"), "WEBP", quality=88, method=6)
            if not portrait:
                out.save(base.with_suffix(".jpg"), "JPEG", quality=90, optimize=True, progressive=True, subsampling=0)
            print(f"{base.name}: {w}x{h}")


if __name__ == "__main__":
    main()
