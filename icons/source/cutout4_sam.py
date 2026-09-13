"""Cut the sleeping dog out of dog4_src.jpg for the Chihuahua 4 icon (python3 cutout4_sam.py).

The photo itself is not in the repository (it is a snapshot of the dog on its owner's chest);
the result, cutout4_sam.png, is.

u2net (used for the earlier dogs and the cat) sees nothing here - the dog fills the frame and
lies against skin of nearly the same colour as its tan fur - and isnet keeps half the chest.
So this one is segmented with SAM from a handful of clicks (blue = dog, red = skin, straps,
mesh), the hard mask is turned into a trimap and closed-form matting softens the fur edge.
The matting solver cannot run on an upscaled photo in this box (it is killed even at 2x), so
everything happens at the photo's own size and the RGBA result is upscaled 3x at the end.
"""
import os

import numpy as np
from PIL import Image, ImageDraw
from pymatting import estimate_alpha_cf, estimate_foreground_ml
from rembg import remove, new_session
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dog4_src.jpg")
OUT = os.path.join(HERE, "cutout4_sam.png")
ROTATE = 22.0

src = Image.open(SRC).convert("RGB")
pos = [(500, 420), (390, 700), (470, 200), (830, 560), (230, 400), (450, 900), (600, 600), (300, 520), (880, 480),
       (250, 680), (270, 760), (330, 830), (420, 870)]
neg = [(850, 250), (900, 800), (760, 230), (150, 1050), (600, 1150), (40, 830), (60, 300), (940, 900), (880, 1000), (300, 1200), (850, 350),
       (130, 560), (150, 640), (60, 900), (90, 750), (200, 960)]
prompt = [{"type": "point", "data": list(p), "label": 1} for p in pos] + \
         [{"type": "point", "data": list(p), "label": 0} for p in neg]
hard = np.asarray(remove(src, session=new_session("sam"), only_mask=True, sam_prompt=prompt).convert("L")) > 127
hard = ndimage.binary_closing(hard, iterations=6)
hard = ndimage.binary_fill_holes(hard)
lab, n = ndimage.label(hard)
sizes = ndimage.sum(hard, lab, range(1, n + 1))
hard = lab == (int(np.argmax(sizes)) + 1)

# trimap: sure dog well inside the mask, sure background well outside, a 28 px band unknown
fg = ndimage.binary_erosion(hard, iterations=14)
# SAM stopped 40-80 px short of the carrier strap along the left cheek, so the band is wider
# there: white fur against a mint strap is something the matting can settle on its own
yy0, xx0 = np.mgrid[0:hard.shape[0], 0:hard.shape[1]]
cheek = (xx0 < 340) & (yy0 > 500) & (yy0 < 900)
bg = ~np.where(cheek, ndimage.binary_dilation(hard, iterations=50),
               ndimage.binary_dilation(hard, iterations=14))
trimap = np.full(hard.shape, 0.5, np.float64)
trimap[fg] = 1.0
trimap[bg] = 0.0
img = np.asarray(src).astype(np.float64) / 255.0
alpha = estimate_alpha_cf(img, trimap)
fgc = estimate_foreground_ml(img, alpha)
rgba = np.dstack([np.clip(fgc, 0, 1), np.clip(alpha, 0, 1)]) * 255.0

# strip carrier colours that crept into the band (mint straps, yellow mesh)
r, g, b = img[..., 0] * 255, img[..., 1] * 255, img[..., 2] * 255
mint = (g > r + 12) & (g > b + 5) & (g > 120)
yellow = (r > 150) & (g > 150) & (b < 110) & (r - b > 100) & (np.abs(r - g) < 45)
# ...and the strap's shadowed edge, a dull olive (r = g, b well below) that no fur has
olive = (np.abs(r - g) < 16) & (g - b > 18) & (g > 60) & ((xx0 < 360) | (yy0 > 820))
drop = ndimage.binary_dilation(mint | yellow | olive, iterations=2)
# the strap's right edge runs from about (185, 520) down to (120, 800): nothing left of it is dog
drop |= (yy0 > 480) & (yy0 < 840) & (xx0 < 185 - 0.232 * (yy0 - 520) - 6)
a = rgba[..., 3]
a[drop & ~fg] = 0
solid = a > 128
lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
keep = ndimage.binary_dilation(lab == (int(np.argmax(sizes)) + 1), iterations=8)
a[~keep] = 0
rgba[..., 3] = a

# Below the chin the carrier's yellow flap hides the chest, which left a bite out of the cut-out
# right where the bubble shows it. Give the dog a neck instead: an ellipse under the chin, in
# the colour of the nearest real fur (blurred), so the bubble's rim - not a ragged edge - is
# what ends the dog, as it is for the other three. The bubble clips everything below y~1010.
H, W = a.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
neck = ((xx - 400.0) / 300.0) ** 2 + ((yy - 1000.0) / 250.0) ** 2 <= 1.0
neck &= yy >= 760
solid = a > 250
fill = neck & (a < 250)
# the neck's colour: the white fur of the chin, a touch darker towards the bottom, with a
# little grain so it does not read as a flat disc; the half-transparent fur edge is composited
# over it so there is no seam
dist, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
near = ndimage.gaussian_filter(rgba[..., :3][iy, ix], sigma=(10, 10, 0))
fur = np.array([176.0, 166.0, 160.0])          # lit white chest fur, a shade under the belly's
shade = 1.0 - 0.15 * np.clip((yy - 860.0) / 250.0, 0, 1)
rng = np.random.default_rng(4)
grain = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), (7.0, 1.6)) * 22.0
t = np.clip(dist / 45.0, 0, 1)[..., None]      # fur-edge colours melt into the neck colour
patch = near * (1 - t) + (fur[None, None, :] * shade[..., None]) * t + grain[..., None]
cover = (a / 255.0)[..., None]
rgba[..., :3] = np.where(fill[..., None], rgba[..., :3] * cover + patch * (1 - cover), rgba[..., :3])
a = np.where(fill, 255.0, a)
# and take the carrier's yellow reflection off the white chest fur
yy = np.arange(H)[:, None]
rr, gg, bb = rgba[..., 0], rgba[..., 1], rgba[..., 2]
w = np.clip((rr - bb - 30.0) / 60.0, 0, 1) * np.clip((yy - 800.0) / 80.0, 0, 1) * 0.75
grey = (0.3 * rr + 0.59 * gg + 0.11 * bb)[..., None]
rgba[..., :3] = rgba[..., :3] * (1 - w[..., None]) + grey * w[..., None]
rgba[..., 3] = ndimage.gaussian_filter(a, 1.0)

im = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")
im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
# level the face: in the photo the head lies tilted about 22 degrees clockwise
im = im.rotate(ROTATE, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
al = np.asarray(im.getchannel("A"))
ys, xs = np.where(al > 0)
box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
im = im.crop(box)
im.save(OUT)
# where "between the eyes" of the photo (456, 617) ended up, for make_icons_v3.py's anchor
mk = Image.new("L", (W * 3, H * 3), 0)
ImageDraw.Draw(mk).ellipse([456 * 3 - 4, 617 * 3 - 4, 456 * 3 + 4, 617 * 3 + 4], fill=255)
mk = mk.rotate(ROTATE, resample=Image.BICUBIC, expand=True, fillcolor=0).crop(box)
my, mx = np.where(np.asarray(mk) > 127)
print("bbox", box, "->", im.size, "components", n, "anchor", (int(mx.mean()), int(my.mean())))
