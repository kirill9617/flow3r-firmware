from st3m.ui import colours
import math


class ColorTheme:
    def __init__(self, bg_hsv, fg_hsv, alt_hsv, hi_hsv):
        self.bg = colours.hsv_to_rgb(*bg_hsv)
        self.fg = colours.hsv_to_rgb(*fg_hsv)
        self.alt = colours.hsv_to_rgb(*alt_hsv)
        self.hi = colours.hsv_to_rgb(*hi_hsv)


colorthemes = {}
colorthemes["standard"] = ColorTheme(
    [0, 0, 0],
    [math.tau * 5 / 6, 1, 1],
    [math.tau * 3 / 6, 1, 1],
    [math.tau * 1 / 6, 1, 1],
)

colorthemes["flow3r"] = ColorTheme(
    [0, 0, 0],
    [math.tau - 0.7254329, 0.7131474, 0.9843138],
    [0, 0, 1],
    [1.952882, 0.8705882, 1.0],
)
