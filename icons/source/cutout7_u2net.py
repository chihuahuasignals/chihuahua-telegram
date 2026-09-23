"""Cut the grey tabby out of cat7_src.jpg for the Chihuahua 7 icon.

The cat crouches with its body rising behind the head, so a matte of the whole cat puts a wall of
back fur above the ears, exactly where the icon wants the bubble's blue and the ear tips crossing
the rim. u2net, run on the crop around the cat, sees only the head and drops the body on its
own, with a soft fur edge along the top of the skull - which is what the icon wants. The crop is
upscaled 3x before the matte, not after: the head is only ~150 px across in the photo, and a
trimap drawn at that size came back as blocky half-transparent patches around the cheeks.
Right under the chin the photo shows deck, not chest (the head is pushed forward), so the head
gets a neck the way dog four did: its bottom edge extruded down, with the real shoulder fur
wherever an isnet matte of the whole cat finds some and the colour of the nearest fur elsewhere,
so the bubble's rim - not a floating chin - is what ends the cat. Then the head is levelled (the
cat looks up at the camera with its head tipped about 14 degrees). The photo itself stays out of
the repository; cutout7_u2net.png is what make_icons_v3.py uses."""
import os

import numpy as np
from PIL import Image
from rembg import remove, new_session
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "cat7_src.jpg")
OUT = os.path.join(HERE, "cutout7_u2net.png")
CROP = (330, 520, 780, 860)
UP = 3               # upscale before the matte (see above); all pixel numbers below are x3
ROTATE = 14          # degrees counter-clockwise: lifts the right side so the eyes sit level
SKULL = (527, 643)   # middle of the skull in the photo, between the ear bases: the icon's anchor

src = Image.open(SRC).convert("RGB").crop(CROP)
src = src.resize((src.width * UP, src.height * UP), Image.LANCZOS)
MATTING = dict(alpha_matting=True, alpha_matting_foreground_threshold=240,
               alpha_matting_background_threshold=20, alpha_matting_erode_size=12)
out = remove(src, session=new_session("u2net"), **MATTING)
whole = remove(src, session=new_session("isnet-general-use"), **MATTING)
rgba = np.asarray(out).astype(np.float64)
real = np.asarray(src).astype(np.float64)
wa = (np.asarray(whole).astype(np.float64)[..., 3] / 255.0)[..., None]
a = rgba[..., 3]
# a crisper edge: the matte's soft band is a few px of the deck's light colour bleeding into the
# light cheek fur, which at icon size read as a pale halo down the left cheek
a = np.clip((a - 40.0) / 175.0, 0, 1)
a = (a * a * (3 - 2 * a)) * 255.0
rgba[..., 3] = a
solid = a > 128
lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
keep = ndimage.binary_dilation(lab == (int(np.argmax(sizes)) + 1), iterations=8)
a[~keep] = 0

# the neck: the head's bottom edge extruded straight down under the face (every column whose
# lowest solid pixel is a cheek or the chin, not an ear), only where the head matte is not
# already solid. The bubble shows a band under the chin and nothing else of it, so a plain
# extrusion reads as the neck, and its sides drop from the cheeks outside the bubble.
H, W = a.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
solid = a > 250
lowest = np.where(solid.any(axis=0), H - 1 - np.argmax(solid[::-1, :], axis=0), -1)
neck = (yy > lowest[None, :]) & (yy <= 900) & (lowest[None, :] > 510)
fill = neck & ~solid
dist, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
near = ndimage.gaussian_filter(rgba[..., :3][iy, ix], sigma=(12, 12, 0))
# the neck's colour: the body's own coat, sampled where the isnet matte found real fur in the
# extruded band (the shoulder), so the made-up part matches what sits beside it
body = fill & (wa[..., 0] > 0.9)
fur = real[body].mean(axis=0) if body.any() else np.array([160.0, 152.0, 145.0])
shade = 1.0 - 0.18 * np.clip((yy - 675.0) / 210.0, 0, 1)
rng = np.random.default_rng(7)
grain = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), (7.0, 1.8)) * 14.0
t = np.clip(dist / 36.0, 0, 1)[..., None]      # fur-edge colours melt into the neck colour
patch = near * (1 - t) + (fur[None, None, :] * shade[..., None]) * t + grain[..., None]
patch = real * wa + patch * (1 - wa)             # real fur where the photo has some
cover = (a / 255.0)[..., None]
rgba[..., :3] = np.where(fill[..., None], rgba[..., :3] * cover + patch * (1 - cover), rgba[..., :3])
a = np.where(fill, 255.0, a)
rgba[..., 3] = ndimage.gaussian_filter(a, 1.0)

im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
im = im.rotate(ROTATE, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
al = np.asarray(im.getchannel("A"))
ys, xs = np.where(al > 0)
box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
im = im.crop(box)
im.save(OUT)

# where the skull point of the photo ended up, for make_icons_v3.py's anchor
mk = Image.new("L", src.size, 0)
mk.putpixel(((SKULL[0] - CROP[0]) * UP, (SKULL[1] - CROP[1]) * UP), 255)
mk = mk.rotate(ROTATE, resample=Image.BICUBIC, expand=True, fillcolor=0).crop(box)
my, mx = np.where(np.asarray(mk) > 0)
print("components", n, "bbox", box, "->", im.size, "anchor", (int(mx.mean()), int(my.mean())))
