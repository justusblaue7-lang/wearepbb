"""Camera positions for the website stills, in three.js coordinates (x across, y up, z towards the entrance).
lens in mm on a 36 mm sensor; portrait uses a vertical frame from the same spot."""

SHOTS = {
    # elevated view from above the foyer down the whole hall: courts left and right, lounge in the middle, neon at the back
    "hero":    {"cam": (0.0, 5.2, 13.2), "look": (0.0, 0.7, -13.0), "lens": 22, "lens_portrait": 18, "exposure": 0.0, "world": "night"},
    # blue hour in front of the entrance
    "konzept": {"cam": (-11.5, 1.6, 47.0), "look": (-0.6, 4.1, 25.4), "lens": 30, "lens_portrait": 20, "exposure": 1.4, "world": "twilight"},
    # standing at the baseline of court 3, looking over the net towards court 1; placed so the lounge pendants
    # stay clear of the neon on the back wall
    "courts":  {"cam": (-5.5, 1.62, 15.1), "look": (-8.75, 0.8, 3.0), "lens": 26, "lens_portrait": 18, "exposure": 0.0, "world": "night"},
    # seated eye level in the lounge, looking down the planter row
    "lounge":  {"cam": (1.05, 1.32, 14.3), "look": (-0.3, 1.05, -8.0), "lens": 28, "lens_portrait": 20, "exposure": 0.3, "world": "night"},
    # DJ stage, neon wall and bar
    "events":  {"cam": (-2.2, 1.65, -12.6), "look": (2.4, 2.0, -24.5), "lens": 24, "lens_portrait": 18, "exposure": 0.85, "world": "night"},
}
