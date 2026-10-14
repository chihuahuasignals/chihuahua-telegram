"""Desktop-shortcut icons for the two virtual phones on Sean's PC (Chihuahua PC / Chihuahua PC 2).

A phone (silver rim, black bezel) whose screen shows the Chihuahua 1 app icon, with a big
numbered badge in the bottom-right corner (green 1, orange 2) so the two shortcuts — and the
round Chihuahua desktop-app icon — are told apart at a glance. The rim is light because his
desktop wallpaper is black; the Windows shortcut arrow sits bottom-left, clear of the badge.

Usage: python3 make_pc_icons.py [outdir]   → chihuahua_pc1.ico, chihuahua_pc2.ico, preview.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, "..", "..", "icons")
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
S = 2048                                   # working canvas, downsampled for every icon size
SIZES = [256, 128, 96, 64, 48, 40, 32, 24, 20, 16]
BADGES = {1: ((67, 214, 104), (24, 150, 66)),     # top / bottom of the badge gradient
          2: ((255, 166, 64), (236, 96, 0))}


def rrect_mask(box, radius, size=S):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=radius, fill=255)
    return m


def vgradient(size, top, bottom, diagonal=False):
    """size-square RGBA gradient from top colour to bottom colour (or top-left → bottom-right)."""
    y = np.linspace(0.0, 1.0, size)[:, None]
    t = (y + np.linspace(0.0, 1.0, size)[None, :]) / 2 if diagonal else np.broadcast_to(y, (size, size))
    arr = np.empty((size, size, 4), np.uint8)
    for i in range(3):
        arr[..., i] = np.round(top[i] + (bottom[i] - top[i]) * t)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def phone_layer():
    """The phone with the app on its screen, on a transparent S×S canvas (plus its shadow)."""
    cx, top, bottom = 0.455 * S, 0.03 * S, 0.97 * S
    half_w = (bottom - top) * 0.5 / 2
    outer = (round(cx - half_w), round(top), round(cx + half_w), round(bottom))
    r_out = round(0.095 * S)
    rim, bezel = round(0.013 * S), round(0.024 * S)
    inset = rim + bezel
    screen = (outer[0] + inset, outer[1] + inset, outer[2] - inset, outer[3] - inset)
    r_scr = r_out - inset

    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # soft shadow (shows on light wallpapers, harmless on black)
    sh = rrect_mask((outer[0], outer[1] + round(0.012 * S), outer[2], outer[3] + round(0.012 * S)), r_out)
    sh = sh.filter(ImageFilter.GaussianBlur(0.02 * S)).point(lambda v: v * 0.45)
    layer.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (S, S), 0)] * 3, sh)))
    # silver rim: diagonal light-to-dark metal
    metal = vgradient(S, (240, 243, 248), (120, 126, 137), diagonal=True)
    rim_mask = rrect_mask(outer, r_out)
    layer.paste(metal, (0, 0), rim_mask)
    # black bezel
    bez_box = (outer[0] + rim, outer[1] + rim, outer[2] - rim, outer[3] - rim)
    layer.paste((14, 16, 20, 255), (0, 0), rrect_mask(bez_box, r_out - rim))

    # screen: the app's blue gradient background + the bubble-with-dog foreground
    sw, sh_ = screen[2] - screen[0], screen[3] - screen[1]
    bg = Image.open(os.path.join(ICONS, "background-xxxhdpi.png")).convert("RGBA")
    side = max(sw, sh_)
    bg = bg.resize((side, side), Image.LANCZOS).crop(((side - sw) // 2, (side - sh_) // 2,
                                                       (side - sw) // 2 + sw, (side - sh_) // 2 + sh_))
    scr = Image.new("RGBA", (sw, sh_), (0, 0, 0, 0))
    scr.alpha_composite(bg)
    fg = Image.open(os.path.join(ICONS, "foreground-xxxhdpi.png")).convert("RGBA")
    fg = fg.crop(fg.getbbox())                         # the bubble (with the ears breaking its rim)
    fw = round(sw * 0.86)
    fh = round(fg.height * fw / fg.width)
    fg = fg.resize((fw, fh), Image.LANCZOS)
    scr.alpha_composite(fg, ((sw - fw) // 2, round(sh_ * 0.47 - fh / 2)))
    d = ImageDraw.Draw(scr)
    cam = round(0.02 * S)                              # punch-hole camera
    d.ellipse((sw // 2 - cam // 2, round(0.035 * S) - cam // 2, sw // 2 + cam // 2, round(0.035 * S) + cam // 2),
              fill=(8, 9, 12, 255))
    pill_w, pill_h = round(sw * 0.32), round(0.008 * S)  # home indicator
    d.rounded_rectangle((sw // 2 - pill_w // 2, sh_ - round(0.03 * S) - pill_h, sw // 2 + pill_w // 2, sh_ - round(0.03 * S)),
                        radius=pill_h // 2, fill=(255, 255, 255, 170))
    # faint glass reflection across the top-left of the screen
    glare = Image.new("L", (sw, sh_), 0)
    ImageDraw.Draw(glare).polygon([(0, 0), (round(sw * 0.75), 0), (0, round(sh_ * 0.55))], fill=34)
    glare = glare.filter(ImageFilter.GaussianBlur(0.01 * S))
    scr.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (sw, sh_), 255)] * 3, glare)))
    scr_mask = Image.new("L", (sw, sh_), 0)
    ImageDraw.Draw(scr_mask).rounded_rectangle((0, 0, sw - 1, sh_ - 1), radius=r_scr, fill=255)
    scr.putalpha(ImageChops.multiply(scr.getchannel("A"), scr_mask))
    layer.alpha_composite(scr, (screen[0], screen[1]))
    return layer


def badge_layer(n):
    top_c, bot_c = BADGES[n]
    cx, cy, r = 0.735 * S, 0.775 * S, 0.195 * S
    ring = round(0.024 * S)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # shadow
    sh = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sh).ellipse((cx - r, cy - r + 0.015 * S, cx + r, cy + r + 0.015 * S), fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(0.018 * S)).point(lambda v: v * 0.5)
    layer.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (S, S), 0)] * 3, sh)))
    # white ring, then the coloured disc
    d = ImageDraw.Draw(layer)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255))
    m = Image.new("L", (S, S), 0)
    ri = r - ring
    ImageDraw.Draw(m).ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill=255)
    # gradient spans just the disc's height
    g = vgradient(round(2 * ri), top_c, bot_c)
    full = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    full.paste(g, (round(cx - ri), round(cy - ri)))
    layer.paste(full, (0, 0), m)
    # the digit, optically centred on its own ink
    font = ImageFont.truetype(FONT, round(0.30 * S))
    txt = str(n)
    l, t, rr, b = font.getbbox(txt)
    tw, th = rr - l, b - t
    tl = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tl).text((cx - tw / 2 - l, cy - th / 2 - t), txt, font=font, fill=255)
    tshadow = tl.filter(ImageFilter.GaussianBlur(0.006 * S)).point(lambda v: v * 0.35)
    layer.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (S, S), 0)] * 3, ImageChops.offset(tshadow, 0, round(0.006 * S)))))
    layer.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (S, S), 255)] * 3, tl)))
    return layer


def sized(master, n):
    im = master.resize((n, n), Image.LANCZOS)
    if n <= 48:                                        # keep small sizes crisp
        im = im.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    phone = phone_layer()
    masters = {}
    for n in (1, 2):
        m = phone.copy()
        m.alpha_composite(badge_layer(n))
        masters[n] = m.resize((1024, 1024), Image.LANCZOS)
        frames = [sized(masters[n], s) for s in SIZES]
        frames[0].save(os.path.join(OUT, f"chihuahua_pc{n}.ico"), format="ICO",
                       sizes=[(s, s) for s in SIZES], append_images=frames[1:])
    # preview on a black desktop like his: 48 px (desktop size), 96 px, and 256 px
    pv = Image.new("RGBA", (40 + 2 * (256 + 96 + 48 + 60), 300), (0, 0, 0, 255))
    x = 20
    for n in (1, 2):
        for s in (256, 96, 48):
            im = sized(masters[n], s)
            pv.alpha_composite(im, (x, 150 - s // 2))
            x += s + 20
        x += 20
    pv.convert("RGB").save(os.path.join(OUT, "preview.png"))


if __name__ == "__main__":
    main()
