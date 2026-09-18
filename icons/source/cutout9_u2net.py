"""Cut both dogs out of dog9_src.jpg for the Chihuahua 9 icon (python3 cutout9_u2net.py): u2net
matte at the photo's own size on the heads-and-chests crop, the half-sure chest made solid from
u2net's own mask, the pillow between the chests filled with fur, largest piece kept, upscaled 3x.
The photo itself stays out of the repository; cutout9_u2net.png is what make_icons_v3.py uses."""
import os

import numpy as np
from PIL import Image
from rembg import remove, new_session
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dog9_src.jpg")
OUT = os.path.join(HERE, "cutout9_u2net.png")

src = Image.open(SRC).convert("RGB").crop((0, 0, 960, 900))
session = new_session("u2net")
out = remove(src, session=session, alpha_matting=True,
             alpha_matting_foreground_threshold=240,
             alpha_matting_background_threshold=20,
             alpha_matting_erode_size=10)
arr = np.asarray(out).astype(np.float32)
a = arr[..., 3]
# The matting left the chocolate dog's white chest half-transparent - white fur on a pale
# pillow gives it nothing to separate. Where u2net itself is sure (its plain mask, well inside
# the outline) the pixel is dog, whatever the matting made of it; the fur edge keeps its matte.
mask = np.asarray(remove(src, session=session, only_mask=True).convert("L")).astype(np.float32)
# u2net is only half sure of that chest too (~130 of 255), but it is far surer of it than of
# the pillow (under 50), so a low bar with a little erosion picks up the chest and body and
# leaves the pillow out; the matte's own soft edge stays in the band outside it.
sure = ndimage.binary_erosion(mask > 100, iterations=4)
sure = ndimage.binary_fill_holes(sure)
a = np.where(sure, 255.0, np.maximum(a, np.where(mask > 100, a * 1.4, a)))
a = np.clip(a, 0, 255)
solid = a > 128
lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
keep = ndimage.binary_dilation(lab == (int(np.argmax(sizes)) + 1), iterations=8)
a[~keep] = 0
# The pillow shows between the two chests, a blue wedge at the bottom of the bubble. Treat the
# bottom and right edges of the crop as dog, so every patch of pillow the dogs enclose becomes a
# hole, and fill the holes with the nearest fur (blurred, a little grain): the two chests meet.
walled = a > 250
walled[-1, :] = True
walled[:, -1] = True
holes = ndimage.binary_fill_holes(walled) & ~(a > 250)
holes &= np.arange(a.shape[0])[:, None] > 480          # only below the chins
_, (iy, ix) = ndimage.distance_transform_edt(~(a > 250), return_indices=True)
near = ndimage.gaussian_filter(arr[..., :3][iy, ix], sigma=(9, 9, 0))
rng = np.random.default_rng(9)
grain = ndimage.gaussian_filter(rng.normal(0, 1, a.shape), (6.0, 1.5)) * 14.0
cover = (a / 255.0)[..., None]
patch = np.clip(near + grain[..., None], 0, 255)
arr[..., :3] = np.where(holes[..., None], arr[..., :3] * cover + patch * (1 - cover), arr[..., :3])
a = np.where(holes, 255.0, a)
arr[..., 3] = a
im = Image.fromarray(arr.astype(np.uint8), "RGBA")
im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
al = np.asarray(im.getchannel("A"))
ys, xs = np.where(al > 0)
box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
im = im.crop(box)
im.save(OUT)
print("components", n, "bbox", box, "->", im.size)
