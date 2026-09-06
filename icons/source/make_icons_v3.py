"""Chihuahua launcher icon v3: the real dog inside a chat bubble.

A speech bubble (azure, white outline, small tail bottom-left) on a navy-to-blue gradient — the
Windows 98 title-bar colours of the Chihuahua 98 theme — with the dog's head photo inside it,
the ears breaking out over the bubble's rim.  Everything is drawn from the soft-edged cut-out
(cutout_u2net.png) at 2048 px and downsampled, so every size is crisp.

Usage: python3 make_icons_v3.py [outdir]        (default: the icons/ folder next to source/)
Writes the same file set the build expects: background-*/foreground-* (adaptive icon layers),
launcher-*/launcher_round-* (legacy 48 dp icons), dr-*.webp, preview.png.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..")

# ---- palette (Chihuahua 98: navy title bar -> bright blue) --------------------------------------
BG_TOP = (0x0B, 0x1F, 0x8E)        # deep navy, top-left
BG_BOTTOM = (0x1C, 0x8B, 0xE8)     # azure, bottom-right
BUBBLE_TOP = (0x5C, 0xC3, 0xFF)    # bubble fill, lighter at the top
BUBBLE_BOTTOM = (0x22, 0x9C, 0xF0)
STROKE = (255, 255, 255)

# ---- geometry, in dp of the 108 dp adaptive-icon canvas -----------------------------------------
# launcher shows the middle 72 dp; anything outside the 66 dp "safe" circle may be masked away.
CX, CY, R = 55.0, 53.0, 28.5       # bubble circle
STROKE_W = 2.3
TAIL_TIP = (31.2, 76.8)            # inside the safe circle (dist from (54,54) = 32.3 < 33)
TAIL_ANGLES = (118.0, 154.0)       # where the tail meets the circle (degrees, y down)
DOG_SCALE = 0.0555                 # dp per source pixel
DOG_ANCHOR = (600, 632)            # source px placed at DOG_AT: between the eyes
DOG_AT = (55.0, 51.0)
OVERFLOW_ABOVE = CY - 8            # above this line the dog may leave the bubble (the ears)
OVERFLOW_REACH = 1.2               # dp the ears may extend past the outline at full strength
OVERFLOW_FADE = 2.6                # ...then fade to nothing over this many dp

_dog = None


def dog():
    global _dog
    if _dog is None:
        im = Image.open(os.path.join(HERE, "cutout_u2net.png")).convert("RGBA")
        alpha = im.getchannel("A")
        # de-fringe: the half-transparent fur strands along the cut-out edge still carry the
        # grey of the photo's background; give them the colour of the nearest solid fur instead
        a = np.asarray(alpha, np.float32) / 255.0
        rgb = np.asarray(im.convert("RGB"), np.float32)
        solid = a > 0.92
        _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
        w = np.clip((0.92 - a) / 0.92, 0, 1) ** 0.6
        rgb = rgb * (1 - w[..., None]) + rgb[iy, ix] * w[..., None]
        rgb = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
        rgb = ImageEnhance.Color(rgb).enhance(1.12)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
        rgb = ImageEnhance.Brightness(rgb).enhance(1.03)
        im = rgb.convert("RGBA")
        im.putalpha(alpha)
        _dog = im
    return _dog


def dp(size):
    return size / 108.0


def background(size):
    """Diagonal navy->azure gradient, a soft highlight top-left, gentle vignette, fine grain."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    t = np.clip((x * 0.55 + y * 0.45), 0, 1)
    t = t ** 1.15
    arr = np.zeros((size, size, 3), np.float32)
    for i in range(3):
        arr[..., i] = BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t
    hl = np.exp(-(((x - 0.30) ** 2 + (y - 0.22) ** 2) / 0.16))
    arr += hl[..., None] * np.array((90, 140, 255), np.float32) * 0.16
    d = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
    arr *= np.clip(1.0 - (d - 0.45) * 0.55, 0.78, 1.0)[..., None]
    rng = np.random.default_rng(3)
    arr += rng.normal(0, 1.2, (size, size, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def bubble_mask(size, ss=4):
    """Anti-aliased L mask of circle + tail."""
    big = size * ss
    s = dp(big)
    m = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([(CX - R) * s, (CY - R) * s, (CX + R) * s, (CY + R) * s], fill=255)
    a0, a1 = np.radians(TAIL_ANGLES)
    p0 = (CX + R * np.cos(a0), CY + R * np.sin(a0))
    p1 = (CX + R * np.cos(a1), CY + R * np.sin(a1))
    tip = TAIL_TIP
    # slightly concave sides: quadratic curves from each base point to the tip
    def curve(p, q, pull=0.55):
        ctrl = ((p[0] + q[0]) / 2 + (CX - (p[0] + q[0]) / 2) * pull * 0.35,
                (p[1] + q[1]) / 2 + (CY - (p[1] + q[1]) / 2) * pull * 0.35)
        pts = []
        for i in range(21):
            u = i / 20
            pts.append(((1 - u) ** 2 * p[0] + 2 * (1 - u) * u * ctrl[0] + u ** 2 * q[0],
                        (1 - u) ** 2 * p[1] + 2 * (1 - u) * u * ctrl[1] + u ** 2 * q[1]))
        return pts
    poly = curve(p0, tip) + curve(tip, p1)[1:]
    # close through the circle centre so the polygon fully overlaps the disc
    poly.append((CX, CY))
    d.polygon([(px * s, py * s) for px, py in poly], fill=255)
    return m.resize((size, size), Image.LANCZOS)


def ring(mask, width_px):
    """Outer outline of `mask`, width_px wide, anti-aliased from the mask's own edge."""
    a = np.asarray(mask, np.float32) / 255.0
    inside = a > 0.5
    dist = ndimage.distance_transform_edt(~inside)
    band = np.clip(width_px + 0.5 - dist, 0, 1)      # 1 inside the band, soft outer edge
    band *= (1 - a)                                   # nothing over the fill itself
    band += np.clip(a, 0, 1) * 0.0
    return Image.fromarray((band * 255).astype(np.uint8), "L")


def bubble(size):
    """Transparent layer: shadow, azure bubble with vertical gradient, white outline, the dog."""
    s = dp(size)
    mask = bubble_mask(size)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # drop shadow under the whole bubble (outline included)
    outline = ring(mask, STROKE_W * s)
    whole = Image.fromarray(np.maximum(np.asarray(mask), np.asarray(outline)), "L")
    sh = whole.filter(ImageFilter.GaussianBlur(3.2 * s))
    shadow = Image.new("RGBA", (size, size), (6, 14, 60, 0))
    shadow.putalpha(Image.fromarray((np.asarray(sh, np.float32) * 0.55).astype(np.uint8), "L"))
    layer.alpha_composite(shadow, (0, round(2.2 * s)))

    # fill: vertical gradient
    y = np.mgrid[0:size, 0:size][0].astype(np.float32)
    t = np.clip((y - (CY - R) * s) / (2 * R * s), 0, 1) ** 0.9
    fill = np.zeros((size, size, 4), np.float32)
    for i in range(3):
        fill[..., i] = BUBBLE_TOP[i] * (1 - t) + BUBBLE_BOTTOM[i] * t
    fill[..., 3] = np.asarray(mask, np.float32)
    layer.alpha_composite(Image.fromarray(fill.astype(np.uint8), "RGBA"))

    # the dog, clipped to the bubble below the ear line
    d0 = dog()
    sc = DOG_SCALE * s
    dw, dh = max(1, round(d0.width * sc)), max(1, round(d0.height * sc))
    d = d0.resize((dw, dh), Image.LANCZOS)
    d = d.filter(ImageFilter.UnsharpMask(radius=max(0.6, 0.9 * s), percent=55, threshold=2))
    x = round(DOG_AT[0] * s - DOG_ANCHOR[0] * sc)
    yy = round(DOG_AT[1] * s - DOG_ANCHOR[1] * sc)
    dog_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dog_layer.alpha_composite(d, (x, yy))
    clip = np.asarray(mask, np.float32) / 255.0
    above = (np.mgrid[0:size, 0:size][0] < OVERFLOW_ABOVE * s).astype(np.float32)
    # feather the transition between "clipped to bubble" and "free" so no hard line can show
    above = ndimage.gaussian_filter(above, 1.5 * s)
    # outside the bubble the ears may cross the outline and a little beyond, then fade out, so
    # the tufts break the rim but loose strands of fur do not fly off over the background
    yy_, xx_ = np.mgrid[0:size, 0:size].astype(np.float32)
    dist_c = np.sqrt((xx_ - CX * s) ** 2 + (yy_ - CY * s) ** 2) / s      # dp from bubble centre
    reach = np.clip((R + STROKE_W + OVERFLOW_REACH + OVERFLOW_FADE - dist_c) / OVERFLOW_FADE, 0, 1)
    above = above * reach
    clip = np.maximum(clip, above)
    da = np.asarray(dog_layer).astype(np.float32)
    # outside the bubble only the solid part of each ear tuft may show: a morphological opening
    # drops the single hairs (thinner than ~1.4 dp), which looked scraggly across the white ring
    k = max(3, int(round(1.4 * s)) | 1)
    opened = ndimage.grey_opening(da[..., 3], size=(k, k))
    opened = np.clip((opened - 90.0) / 90.0, 0, 1) * 255.0      # crisp edge, no pale smear over the ring
    inside = np.asarray(mask, np.float32) / 255.0
    da[..., 3] = da[..., 3] * inside + opened * (1 - inside)
    da[..., 3] *= clip
    dog_layer = Image.fromarray(da.astype(np.uint8), "RGBA")
    # inner shadow along the bubble's lower rim so the clipped chest sits "inside"
    inner = np.asarray(mask, np.float32) / 255.0
    edge = inner - ndimage.gaussian_filter(inner, 4.5 * s)
    edge = np.clip(edge, 0, 1)
    lower = np.clip((y - CY * s) / (R * s), 0, 1)
    ish = Image.new("RGBA", (size, size), (10, 40, 110, 0))
    ish.putalpha(Image.fromarray((edge * lower * 0.7 * 255).astype(np.uint8), "L"))
    layer.alpha_composite(dog_layer)
    layer.alpha_composite(ish)

    # white outline on top of everything (the ears cross it — that is the point)
    white = Image.new("RGBA", (size, size), STROKE + (0,))
    white.putalpha(outline)
    # ...but let the dog's ears stay in front of the stroke where they leave the bubble:
    ears = da[..., 3] / 255.0 * above
    wa = np.asarray(white).astype(np.float32)
    wa[..., 3] *= (1 - ears * 0.85)
    layer.alpha_composite(Image.fromarray(wa.astype(np.uint8), "RGBA"))
    return layer


def composed(size):
    return Image.alpha_composite(background(size), bubble(size))


MASTER = 2048
_master = None


def master():
    global _master
    if _master is None:
        _master = composed(MASTER)
    return _master


def crop_visible(im, frac=72 / 108):
    off = round(im.width * (1 - frac) / 2)
    return im.crop((off, off, im.width - off, im.height - off))


def masked(im, shape):
    size = im.width
    m = Image.new("L", (size, size), 0)
    if shape == "circle":
        ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    elif shape == "squircle":
        ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 3, fill=255)
    else:
        ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), m)
    return out


DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def main():
    os.makedirs(OUT, exist_ok=True)
    bg_master = background(MASTER)
    fg_master = bubble(MASTER)
    full = Image.alpha_composite(bg_master, fg_master)
    for dname, mult in DENS.items():
        px = round(108 * mult)
        bg_master.resize((px, px), Image.LANCZOS).save(f"{OUT}/background-{dname}.png", optimize=True)
        fg_master.resize((px, px), Image.LANCZOS).save(f"{OUT}/foreground-{dname}.png", optimize=True)
        lp = round(48 * mult)
        vis = crop_visible(full)
        for shape, fname in (("square", "launcher"), ("circle", "launcher_round")):
            out = masked(vis, shape).resize((lp, lp), Image.LANCZOS)
            out.save(f"{OUT}/{fname}-{dname}.png", optimize=True)
            if shape == "circle":
                out.save(f"{OUT}/dr-{dname}.webp", "WEBP", quality=92, method=6)
    # preview: how launchers show it (circle / squircle), big and small, on light and dark
    vis = crop_visible(full)
    pv = Image.new("RGBA", (384 * 2 + 40 + 168 * 2 + 60 + 96 * 2 + 40 + 40, 384), (255, 255, 255, 255))
    pv.alpha_composite(masked(vis, "circle").resize((384, 384), Image.LANCZOS), (0, 0))
    pv.alpha_composite(masked(vis, "squircle").resize((384, 384), Image.LANCZOS), (424, 0))
    pv.alpha_composite(masked(vis, "circle").resize((168, 168), Image.LANCZOS), (868, 100))
    pv.alpha_composite(masked(vis, "squircle").resize((168, 168), Image.LANCZOS), (1056, 100))
    dark = Image.new("RGBA", (96 * 2 + 40, 384), (28, 28, 30, 255))
    dark.alpha_composite(masked(vis, "circle").resize((96, 96), Image.LANCZOS), (0, 144))
    dark.alpha_composite(masked(vis, "squircle").resize((96, 96), Image.LANCZOS), (136, 144))
    pv.alpha_composite(dark, (1284, 0))
    pv.convert("RGB").save(f"{OUT}/preview.png")
    print("v3 ->", OUT, len(os.listdir(OUT)), "files")


if __name__ == "__main__":
    main()
