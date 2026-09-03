"""Chihuahua launcher icon v2: crisp sticker dog (white border + shadow) on a vivid gradient with
soft sunburst rays, glow and vignette.  Usage: python3 make_icons_v2.py <variant> <outdir>"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VARIANTS = {
    # name: (gradient top-left, gradient bottom-right, ray colour)
    "ocean":  ((0x2A, 0xA8, 0xF2), (0x6B, 0x3F, 0xE0), (255, 255, 255)),   # blue → violet
    "sunset": ((0xFF, 0xB0, 0x3A), (0xFF, 0x4E, 0x6A), (255, 255, 255)),   # orange → pink-red
    "candy":  ((0x3D, 0xD5, 0xC8), (0x2F, 0x6F, 0xE8), (255, 255, 255)),   # mint-teal → blue
}
variant = sys.argv[1] if len(sys.argv) > 1 else "ocean"
outdir = sys.argv[2] if len(sys.argv) > 2 else "v2_" + variant
os.makedirs(outdir, exist_ok=True)
C1, C2, RAY = VARIANTS[variant]
HERE = os.path.dirname(os.path.abspath(__file__))
dog = Image.open(os.path.join(HERE, "dog_sticker_v2.png")).convert("RGBA")
DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def background(size, cx=0.5, cy=0.44):
    """Diagonal gradient + sunburst rays + centre glow + vignette, all at `size` px."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    t = np.clip((x + y) / 2.0, 0, 1)                                  # diagonal
    arr = np.zeros((size, size, 3), np.float32)
    for i in range(3):
        arr[..., i] = C1[i] * (1 - t) + C2[i] * t
    # sunburst rays (16 wedges, soft edges)
    ang = np.arctan2(y - cy, x - cx)
    rays = 0.5 + 0.5 * np.cos(ang * 16)
    rays = np.clip((rays - 0.55) / 0.45, 0, 1) ** 1.5
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    rays *= np.clip(1.15 - dist * 1.1, 0, 1)                           # fade rays toward edges
    arr += rays[..., None] * np.array(RAY, np.float32) * 0.13
    # centre glow behind the head
    glow = np.exp(-(dist / 0.30) ** 2)
    arr += glow[..., None] * np.array(RAY, np.float32) * 0.22
    # vignette
    vig = np.clip(1.0 - (dist - 0.42) * 0.9, 0.72, 1.0)
    arr *= vig[..., None]
    # fine grain so the gradient doesn't band
    rng = np.random.default_rng(7)
    arr += rng.normal(0, 1.6, (size, size, 1))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, "RGB").convert("RGBA")
    return out


def sticker(size, visible_frac, head_frac, top_frac):
    """Transparent layer with the dog, white sticker border and soft drop shadow."""
    vis = size * visible_frac
    sc = (vis * head_frac) / dog.width
    d = dog.resize((max(1, round(dog.width * sc)), max(1, round(dog.height * sc))), Image.LANCZOS)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - d.width) // 2 + round(size * 0.004)
    y = round((size - vis) / 2 + vis * top_frac)
    # border: dilate the alpha
    border_px = max(2, round(vis * 0.028))
    alpha = d.getchannel("A")
    big = Image.new("L", (size, size), 0); big.paste(alpha, (x, y))
    border = big.filter(ImageFilter.MaxFilter(border_px * 2 + 1))
    border = border.filter(ImageFilter.GaussianBlur(0.6))
    # shadow: blurred, offset down
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow.putalpha(border.filter(ImageFilter.GaussianBlur(vis * 0.02)))
    sh = np.array(shadow); sh[..., 3] = (sh[..., 3] * 0.35).astype(np.uint8)
    shadow = Image.fromarray(sh, "RGBA")
    layer.alpha_composite(shadow, (0, round(vis * 0.02)))
    white = Image.new("RGBA", (size, size), (255, 255, 255, 0)); white.putalpha(border)
    layer.alpha_composite(white)
    layer.alpha_composite(d, (x, y))
    return layer


for dname, mult in DENS.items():
    px = round(108 * mult)
    background(px).save(f"{outdir}/background-{dname}.png", optimize=True)
    sticker(px, 72 / 108, 0.80, 0.05).save(f"{outdir}/foreground-{dname}.png", optimize=True)
    lp = round(48 * mult); big = lp * 4
    comp = Image.alpha_composite(background(big), sticker(big, 1.0, 0.76, 0.06))
    for shape, fname in (("square", "launcher"), ("round", "launcher_round")):
        m = Image.new("L", (big, big), 0)
        if shape == "square":
            ImageDraw.Draw(m).rounded_rectangle([0, 0, big - 1, big - 1], radius=big // 5, fill=255)
        else:
            ImageDraw.Draw(m).ellipse([0, 0, big - 1, big - 1], fill=255)
        out = Image.new("RGBA", (big, big), (0, 0, 0, 0)); out.paste(comp, (0, 0), m)
        out = out.resize((lp, lp), Image.LANCZOS); out.save(f"{outdir}/{fname}-{dname}.png", optimize=True)
        if shape == "round":
            out.save(f"{outdir}/dr-{dname}.webp", "WEBP", quality=92, method=6)


def launcher_view(shape, size):
    px = 432
    comp = Image.alpha_composite(background(px), sticker(px, 72 / 108, 0.80, 0.05))
    off = round(px * (1 - 72 / 108) / 2)
    vis = comp.crop((off, off, px - off, px - off)).resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    if shape == "circle":
        ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    else:
        ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 3, fill=255)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0)); out.paste(vis, (0, 0), m)
    return out


pv = Image.new("RGBA", (384 * 2 + 40 + 180 * 2 + 60, 384), (255, 255, 255, 255))
pv.alpha_composite(launcher_view("circle", 384), (0, 0))
pv.alpha_composite(launcher_view("squircle", 384), (424, 0))
pv.alpha_composite(launcher_view("circle", 168), (868, 100))
pv.alpha_composite(launcher_view("squircle", 168), (1056, 100))
pv.convert("RGB").save(f"{outdir}/preview.png")
print(variant, "->", outdir, len(os.listdir(outdir)), "files")
