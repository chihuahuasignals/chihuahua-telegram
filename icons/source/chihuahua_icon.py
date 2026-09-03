"""Shared drawing code for the Chihuahua icons (Android + desktop).
background(size, variant): diagonal gradient + sunburst rays + glow + vignette (RGBA, opaque).
sticker(size, visible_frac, head_frac, top_frac): transparent layer with the dog sticker."""
import os
import numpy as np
from PIL import Image, ImageFilter

VARIANTS = {
    "ocean":  ((0x2A, 0xA8, 0xF2), (0x6B, 0x3F, 0xE0), (255, 255, 255)),   # blue → violet
    "sunset": ((0xFF, 0xB0, 0x3A), (0xFF, 0x4E, 0x6A), (255, 255, 255)),   # orange → pink-red
    "candy":  ((0x3D, 0xD5, 0xC8), (0x2F, 0x6F, 0xE8), (255, 255, 255)),   # mint-teal → blue
}
HERE = os.path.dirname(os.path.abspath(__file__))
_dog = None


def dog():
    global _dog
    if _dog is None:
        _dog = Image.open(os.path.join(HERE, "dog_sticker_v2.png")).convert("RGBA")
    return _dog


def background(size, variant="sunset", cx=0.5, cy=0.44):
    C1, C2, RAY = VARIANTS[variant]
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    t = np.clip((x + y) / 2.0, 0, 1)
    arr = np.zeros((size, size, 3), np.float32)
    for i in range(3):
        arr[..., i] = C1[i] * (1 - t) + C2[i] * t
    ang = np.arctan2(y - cy, x - cx)
    rays = 0.5 + 0.5 * np.cos(ang * 16)
    rays = np.clip((rays - 0.55) / 0.45, 0, 1) ** 1.5
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    rays *= np.clip(1.15 - dist * 1.1, 0, 1)
    arr += rays[..., None] * np.array(RAY, np.float32) * 0.13
    glow = np.exp(-(dist / 0.30) ** 2)
    arr += glow[..., None] * np.array(RAY, np.float32) * 0.22
    vig = np.clip(1.0 - (dist - 0.42) * 0.9, 0.72, 1.0)
    arr *= vig[..., None]
    rng = np.random.default_rng(7)
    arr += rng.normal(0, 1.6, (size, size, 1))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def sticker(size, visible_frac, head_frac, top_frac):
    d0 = dog()
    vis = size * visible_frac
    sc = (vis * head_frac) / d0.width
    d = d0.resize((max(1, round(d0.width * sc)), max(1, round(d0.height * sc))), Image.LANCZOS)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - d.width) // 2 + round(size * 0.004)
    y = round((size - vis) / 2 + vis * top_frac)
    border_px = max(1, round(vis * 0.028))
    alpha = d.getchannel("A")
    big = Image.new("L", (size, size), 0); big.paste(alpha, (x, y))
    border = big.filter(ImageFilter.MaxFilter(border_px * 2 + 1)).filter(ImageFilter.GaussianBlur(0.6))
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow.putalpha(border.filter(ImageFilter.GaussianBlur(max(0.5, vis * 0.02))))
    sh = np.array(shadow); sh[..., 3] = (sh[..., 3] * 0.35).astype(np.uint8)
    layer.alpha_composite(Image.fromarray(sh, "RGBA"), (0, round(vis * 0.02)))
    white = Image.new("RGBA", (size, size), (255, 255, 255, 0)); white.putalpha(border)
    layer.alpha_composite(white)
    layer.alpha_composite(d, (x, y))
    return layer


def composed(size, variant="sunset", head_frac=0.76, top_frac=0.06):
    """Full-bleed square composition (background + sticker) at `size` px."""
    return Image.alpha_composite(background(size, variant), sticker(size, 1.0, head_frac, top_frac))
