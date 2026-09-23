"""Cut the chocolate-and-white dog out of dog8_src.jpg for the Chihuahua 8 icon: u2net matte on
the head-and-chest crop, upscaled 3x before the matte (as for cat seven - a trimap drawn at the
photo's own size left staircase edges along the ear fringes), largest piece kept. The white chest
sits against a cream cabinet in the photo and u2net still finds it, so no neck needs making up.
The photo itself stays out of the repository; cutout8_u2net.png is what make_icons_v3.py uses."""
import os

import numpy as np
from PIL import Image
from rembg import remove, new_session
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dog8_src.jpg")
OUT = os.path.join(HERE, "cutout8_u2net.png")
CROP = (360, 240, 880, 790)
UP = 3
EYES = (637, 383)    # between the eyes in the photo: the icon's anchor

src = Image.open(SRC).convert("RGB").crop(CROP)
src = src.resize((src.width * UP, src.height * UP), Image.LANCZOS)
out = remove(src, session=new_session("u2net"), alpha_matting=True,
             alpha_matting_foreground_threshold=240,
             alpha_matting_background_threshold=20,
             alpha_matting_erode_size=12)
arr = np.asarray(out).astype(np.float32)
a = arr[..., 3]
solid = a > 128
lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
keep = ndimage.binary_dilation(lab == (int(np.argmax(sizes)) + 1), iterations=8)
a[~keep] = 0
arr[..., 3] = a
im = Image.fromarray(arr.astype(np.uint8), "RGBA")
al = np.asarray(im.getchannel("A"))
ys, xs = np.where(al > 0)
box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
im = im.crop(box)
im.save(OUT)
anchor = ((EYES[0] - CROP[0]) * UP - box[0], (EYES[1] - CROP[1]) * UP - box[1])
print("components", n, "bbox", box, "->", im.size, "anchor", anchor)
