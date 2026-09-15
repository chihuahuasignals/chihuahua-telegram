"""Cut the chocolate-and-white dog out of dog5_src.jpg for the Chihuahua 5 icon: u2net matte at
the photo's own size on the head-and-chest crop, largest piece kept, upscaled 3x. The photo itself
stays out of the repository; cutout5_u2net.png is what make_icons_v3.py uses."""
import os

import numpy as np
from PIL import Image
from rembg import remove, new_session
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "dog5_src.jpg")
OUT = os.path.join(HERE, "cutout5_u2net.png")

src = Image.open(SRC).convert("RGB").crop((120, 60, 960, 980))
out = remove(src, session=new_session("u2net"), alpha_matting=True,
             alpha_matting_foreground_threshold=240,
             alpha_matting_background_threshold=20,
             alpha_matting_erode_size=10)
arr = np.asarray(out).astype(np.float32)
a = arr[..., 3]
solid = a > 128
lab, n = ndimage.label(solid)
sizes = ndimage.sum(solid, lab, range(1, n + 1))
keep = ndimage.binary_dilation(lab == (int(np.argmax(sizes)) + 1), iterations=8)
a[~keep] = 0
arr[..., 3] = a
im = Image.fromarray(arr.astype(np.uint8), "RGBA")
im = im.resize((im.width * 3, im.height * 3), Image.LANCZOS)
al = np.asarray(im.getchannel("A"))
ys, xs = np.where(al > 0)
box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
im = im.crop(box)
im.save(OUT)
print("components", n, "bbox", box, "->", im.size)
