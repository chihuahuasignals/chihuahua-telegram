"""Build the Chihuahua launcher icon set from dog_cartoon.png. Usage: python3 make_icons.py <variant> <outdir>"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw

VARIANTS = {"sky": ((190, 232, 255), (52, 140, 232)),
            "peach": ((255, 228, 182), (255, 146, 78)),
            "mint": ((208, 250, 230), (48, 186, 146))}
variant = sys.argv[1] if len(sys.argv) > 1 else "sky"
outdir = sys.argv[2] if len(sys.argv) > 2 else "out_" + variant
os.makedirs(outdir, exist_ok=True)
C_IN, C_OUT = VARIANTS[variant]
dog = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dog_cartoon.png")).convert("RGBA")
DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

def gradient(size, cx_frac=0.5, cy_frac=0.46, reach=0.75):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((x - size*cx_frac)**2 + (y - size*cy_frac)**2) / (size*reach)
    d = np.clip(d, 0, 1) ** 1.15
    arr = np.zeros((size, size, 4), np.float32)
    for i in range(3):
        arr[..., i] = C_IN[i]*(1-d) + C_OUT[i]*d
    arr[..., 3] = 255
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def dog_layer(size, visible_frac, head_frac=0.73, top_frac=0.075):
    """Transparent size×size layer; the dog's head spans head_frac of the visible diameter,
    ear tips start top_frac of the visible diameter below its top edge."""
    vis = size * visible_frac
    sc = (vis * head_frac) / dog.width
    d = dog.resize((max(1, round(dog.width*sc)), max(1, round(dog.height*sc))), Image.LANCZOS)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - d.width)//2 + round(size*0.005)
    y = round((size - vis)/2 + vis*top_frac)
    layer.alpha_composite(d, (x, y))
    return layer

for dname, mult in DENS.items():
    # adaptive icon layers: 108dp canvas, launcher shows the centre 72dp
    px = round(108*mult)
    gradient(px).save(f"{outdir}/background-{dname}.png", optimize=True)
    dog_layer(px, 72/108).save(f"{outdir}/foreground-{dname}.png", optimize=True)
    # legacy icons: 48dp full-bleed shapes
    lp = round(48*mult); big = lp*4
    comp = Image.alpha_composite(gradient(big), dog_layer(big, 1.0, head_frac=0.70, top_frac=0.07))
    for shape, fname in (("square", "launcher"), ("round", "launcher_round")):
        m = Image.new("L", (big, big), 0)
        if shape == "square":
            ImageDraw.Draw(m).rounded_rectangle([0, 0, big-1, big-1], radius=big//5, fill=255)
        else:
            ImageDraw.Draw(m).ellipse([0, 0, big-1, big-1], fill=255)
        out = Image.new("RGBA", (big, big), (0, 0, 0, 0)); out.paste(comp, (0, 0), m)
        out = out.resize((lp, lp), Image.LANCZOS); out.save(f"{outdir}/{fname}-{dname}.png", optimize=True)
        if shape == "round":
            out.save(f"{outdir}/dr-{dname}.webp", "WEBP", quality=90, method=6)

# preview: what the launcher shows (centre 72dp) as circle + squircle, at 192px, plus the 48dp legacy
def launcher_view(shape, size=384):
    px = 432
    comp = Image.alpha_composite(gradient(px), dog_layer(px, 72/108))
    off = round(px*(1-72/108)/2); vis = comp.crop((off, off, px-off, px-off)).resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    if shape == "circle":
        ImageDraw.Draw(m).ellipse([0, 0, size-1, size-1], fill=255)
    else:
        ImageDraw.Draw(m).rounded_rectangle([0, 0, size-1, size-1], radius=size//3, fill=255)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0)); out.paste(vis, (0, 0), m)
    return out
pv = Image.new("RGBA", (384*2+40, 384), (255, 255, 255, 255))
pv.alpha_composite(launcher_view("circle"), (0, 0)); pv.alpha_composite(launcher_view("squircle"), (424, 0))
pv.convert("RGB").save(f"{outdir}/preview.png")
print(variant, "->", outdir, len(os.listdir(outdir)), "files")
