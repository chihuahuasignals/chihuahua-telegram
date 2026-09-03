"""Desktop (Telegram Desktop) icon set: round icons like the official ones.
Usage: python3 make_desktop_icons.py [variant] [outdir]   → icons/desktop/"""
import os, sys
from PIL import Image, ImageDraw
from chihuahua_icon import composed

variant = sys.argv[1] if len(sys.argv) > 1 else "sunset"
outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "desktop")
os.makedirs(outdir, exist_ok=True)

BIG = 1024
base = composed(BIG, variant)                       # square, full bleed
circle_mask = Image.new("L", (BIG, BIG), 0)
ImageDraw.Draw(circle_mask).ellipse([0, 0, BIG - 1, BIG - 1], fill=255)
round_full = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0)); round_full.paste(base, (0, 0), circle_mask)


def with_margin(size, margin_frac=0.04):
    """Circle inset by a small transparent margin (matches logo_256.png / icon*.png framing)."""
    inner = round(size * (1 - 2 * margin_frac))
    im = round_full.resize((inner, inner), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(im, ((size - inner) // 2, (size - inner) // 2))
    return out


# logo_256.png (margin) / logo_256_no_margin.png (full bleed) — window + tray icon
with_margin(256).save(f"{outdir}/logo_256.png", optimize=True)
round_full.resize((256, 256), Image.LANCZOS).save(f"{outdir}/logo_256_no_margin.png", optimize=True)
# icon<N>.png and @2x — shell icons on other platforms, kept consistent
for n in (16, 32, 48, 64, 128, 256, 512):
    with_margin(n).save(f"{outdir}/icon{n}.png", optimize=True)
    with_margin(n * 2).save(f"{outdir}/icon{n}@2x.png", optimize=True)
round_full.save(f"{outdir}/icon_round512@2x.png", optimize=True)
# Windows .ico (exe icon): multi-size
ico_src = with_margin(256)
ico_src.save(f"{outdir}/icon256.ico", format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
# preview
pv = Image.new("RGB", (256 * 3 + 40, 256), (235, 235, 235))
pv.paste(with_margin(256).convert("RGBA"), (0, 0), with_margin(256))
pv.paste(round_full.resize((256, 256)).convert("RGBA"), (276, 0), round_full.resize((256, 256)))
pv.paste(with_margin(64).resize((64, 64)).convert("RGBA"), (552, 96), with_margin(64))
pv.paste(with_margin(32).convert("RGBA"), (640, 112), with_margin(32))
pv.save(f"{outdir}/preview.png")
print(variant, "->", outdir, len(os.listdir(outdir)), "files")
