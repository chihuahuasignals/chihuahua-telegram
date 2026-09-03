"""Turn cutout_u2net.png (rembg output of the head/upper-body crop) into a cartoon sticker
with a smooth 'bust' bottom edge. Output: dog_cartoon.png"""
import cv2, numpy as np
from PIL import Image

src = Image.open("cutout_u2net.png").convert("RGBA")
scale = 1000 / src.height
src = src.resize((round(src.width * scale), 1000), Image.LANCZOS)
rgba = np.array(src); rgb = rgba[:, :, :3].copy(); alpha = rgba[:, :, 3].copy()
H, W = alpha.shape

# --- clean silhouette
sil = (alpha > 128).astype(np.uint8) * 255
sil = cv2.morphologyEx(sil, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
n, lab, stats, _ = cv2.connectedComponentsWithStats(sil)
if n > 2:
    big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]); sil = ((lab == big) * 255).astype(np.uint8)

# --- bust bottom: below y0 replace the body (and the front paw) by a smooth half-ellipse
ys, xs = np.where(sil > 0)
top = ys.min()
y0 = int(top + (ys.max() - top) * 0.66)
row = np.where(sil[y0] > 0)[0]
# chest span at y0, trimmed a little on the paw side (left)
x_left, x_right = row.min(), row.max()
cx = (x_left + x_right) / 2.0
rx = (x_right - x_left) / 2.0 * 0.98
ry = H - y0 + 40
bust = np.zeros_like(sil)
cv2.ellipse(bust, (int(cx), y0), (int(rx), int(ry)), 0, 0, 360, 255, -1)
new_sil = sil.copy()
new_sil[y0:, :] = np.minimum(sil[y0:, :], bust[y0:, :])
new_sil[y0:, :] = np.maximum(new_sil[y0:, :], (bust[y0:, :] & (sil[y0:, :] | 0)))  # keep ellipse ∩ body
# fill any transparent pixels inside the ellipse below y0 with chest fur colour
chest = rgb[y0 - 120:y0 - 20, int(cx) - 60:int(cx) + 60].reshape(-1, 3)
chest_col = np.median(chest, axis=0).astype(np.uint8)
inside_hole = (bust > 0) & (alpha < 128)
inside_hole[:y0, :] = False
rgb[inside_hole] = chest_col
new_sil[y0:, :] = bust[y0:, :] * (1) if True else new_sil[y0:, :]
sil = new_sil
soft = cv2.GaussianBlur(sil, (7, 7), 0)

# --- smoothing + poster look
bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
inpaint_mask = ((sil > 0) & (alpha < 200) & ~inside_hole).astype(np.uint8) * 255
bgr = cv2.inpaint(bgr, inpaint_mask, 5, cv2.INPAINT_TELEA)
light = cv2.bilateralFilter(bgr, d=7, sigmaColor=40, sigmaSpace=7)
sm = bgr
for _ in range(5):
    sm = cv2.bilateralFilter(sm, d=11, sigmaColor=70, sigmaSpace=11)
sm = cv2.edgePreservingFilter(sm, flags=cv2.RECURS_FILTER, sigma_s=50, sigma_r=0.4)
Z = sm.reshape(-1, 3).astype(np.float32)
_, labels, centers = cv2.kmeans(Z, 24, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
quant = centers[labels.flatten()].reshape(sm.shape).astype(np.uint8)
sm = cv2.addWeighted(sm, 0.55, quant, 0.45, 0)

# keep eye/nose detail
g0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
dark = (g0 < 75).astype(np.uint8) * 255
dark = cv2.dilate(dark, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
dark = cv2.GaussianBlur(dark, (15, 15), 0).astype(np.float32) / 255.0
dark *= (cv2.erode(sil, np.ones((15, 15), np.uint8)).astype(np.float32) / 255.0)
sm = np.clip(sm.astype(np.float32) * (1 - dark[..., None]) + light.astype(np.float32) * dark[..., None], 0, 255).astype(np.uint8)

hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV).astype(np.float32)
hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.4, 0, 255)
hsv[:, :, 2] = np.clip((hsv[:, :, 2] - 128) * 1.06 + 134, 0, 255)
sm = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

# ink on key features only
g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
can = cv2.Canny(g, 70, 170); can = cv2.dilate(can, np.ones((2, 2), np.uint8))
inner = cv2.erode(sil, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
inner[y0 - 10:, :] = 0                                  # no ink on the artificial bust edge
ink = (can.astype(np.float32) / 255.0) * (inner.astype(np.float32) / 255.0)
ink = cv2.GaussianBlur(ink, (3, 3), 0) * 0.5
ink_col = np.array([28, 40, 66], dtype=np.float32)
out = np.clip(sm.astype(np.float32) * (1 - ink[..., None]) + ink_col * ink[..., None], 0, 255).astype(np.uint8)
dog = Image.fromarray(np.dstack([cv2.cvtColor(out, cv2.COLOR_BGR2RGB), soft]), "RGBA")

# outline ring
ring = cv2.dilate(sil, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (16, 16)))
ring = cv2.GaussianBlur(ring, (5, 5), 0)
outline = Image.new("RGBA", dog.size, (70, 42, 22, 0)); outline.putalpha(Image.fromarray(ring))
sticker = Image.alpha_composite(outline, dog)
sticker = sticker.crop(sticker.getbbox())
sticker.save("dog_cartoon.png")
print("dog_cartoon.png", sticker.size, "bust y0 =", y0, "of", H)
