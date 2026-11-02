# Pickleball Buddies – Website

Static website for Pickleball Buddies (PBB) in Lübbecke. The hall visuals are path-traced 4K stills of the planned
venue, rendered from a procedural Blender scene that lives in this repository.

```
index.html            page content (German)
css/style.css         graphite + lilac design
js/main.js            scroll crossfade between renders, navigation, waitlist, legal dialogs
assets/brand/         the founders' neon sign (pbb-neon.jpg), source of the logo and the brand colour
assets/pbb-logo.svg   the PBB signature as centre lines of the neon tubes (also used by the 3D signs)
assets/renders/       web images generated from the renders (WebP + JPEG)
render/               Blender scene + render pipeline
```

## Run locally

Any static file server works, for example:

```
python3 -m http.server 8000
```

then open http://localhost:8000.

## Logo and colour

The mark is the founders' neon sign `assets/brand/pbb-neon.jpg`. `render/trace_logo.py` turns it into
`assets/pbb-logo.svg`: one smooth stroke per neon tube (centre lines, joined straight through every crossing, cubic
Béziers within half a pixel of the photo) plus the measured tube width. The website draws that path as a Flieder tube
with the sign's violet halo; the renders sweep a round tube along it. After changing the source image:

```
python3 render/trace_logo.py
```

then copy the new `d` into the `pbb-logo` symbol in `index.html` and `assets/favicon.svg`.

Flieder `#d7a7f3` is the tube colour of the sign. It is `--lilac` on the website and every LED strip, neon tube and
light lettering in the renders. AgX (the renders' view transform) would bleach bright lilac to white and push violet
paint towards blue, so `render/pbb/materials.py` sets colours by what the still shows: emitters seen by the camera go
through the inverse of the view transform, and the court paint (kitchens, floor logos) carries an albedo solved from
test renders so the kitchen shows as `#c797e2` (`--kitchen`), the brand colour one step deeper. `render.py --exr`
writes the light passes used for that.

## Renders

The images are made with Blender 4.5 LTS (Cycles, GPU) from `render/pbb/`, a Python package that builds the hall:
22 × 50 m shell with steel portal frames, four courts in official dimensions, lounge, DJ stage, bar, foyer and the
entrance facade. Materials use scanned CC0 textures and models from Poly Haven; the PBB neon signs and the large PBB
painted between the two courts of each side are built from the same SVG path as the website logo.

```
python3 render/fetch_assets.py                                   # once: CC0 textures, models, font (~160 MB)
blender -b --factory-startup --python render/render.py -- \
        --res 3840x2160 --samples 1024 --out render/out/final     # landscape 4K, all shots
python3 render/export_web.py                                     # PNG -> assets/renders/*.webp|jpg
```

`--shots hero,courts` renders a subset, `--res 960x540 --samples 48` gives a quick preview.
Camera positions are in `render/pbb/shots.py`. On an Apple M2 (8 GB) a 4K frame takes 1.3 (exterior) to 3.3 hours (hero).

## Open points before go-live

- Waitlist form is not connected; entries stay in the visitor's browser.
- Impressum and Datenschutz are placeholders.
- The renders show the planned final state, labelled as "Visualisierung" on the page.
- Kids play on the regular courts; there is no separate kids area.
- Team photos (`assets/team/`, 720 px squares) share one framing: eyes 20 % of the width apart at 47 % height, so the
  whole head and the shoulders show. Justus's photo was too tight and got plain wall added around it; Sarita's
  source is small (588 × 450), so a larger photo of her would sharpen her card. Asset URLs carry `?v=` so browsers
  pick up new versions; bump it in `index.html` after changing CSS, JS or photos.
- The `konzept` (facade) and `lounge` stills are not used on the page any more; phones crop the landscape renders.
