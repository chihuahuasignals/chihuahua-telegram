"""Crisp sticker cut-out of the chihuahua (no heavy smoothing). Output: dog_sticker_v2.png (RGBA)."""
import cv2, numpy as np
from PIL import Image, ImageFilter

src = Image.open("cutout_u2net.png").convert("RGBA")
scale = 1400 / src.height
src = src.resize((round(src.width * scale), 1400), Image.LANCZOS)
rgba = np.array(src); rgb = rgba[:, :, :3].copy(); alpha = rgba[:, :, 3].copy()
H, W = alpha.shape

# ---- silhouette: keep fur character, drop stray whiskers, close small holes
sil = (alpha > 110).astype(np.uint8) * 255
sil = cv2.morphologyEx(sil, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
n, lab, stats, _ = cv2.connectedComponentsWithStats(sil)
if n > 2:
    big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]); sil = ((lab == big) * 255).astype(np.uint8)

# ---- bust bottom (half-ellipse) replaces the front paw
ys, xs = np.where(sil > 0)
top = ys.min(); y0 = int(top + (ys.max() - top) * 0.64)
row = np.where(sil[y0] > 0)[0]; x_left, x_right = row.min(), row.max()
cx = (x_left + x_right) / 2.0; rx = (x_right - x_left) / 2.0 * 0.99; ry = H - y0 + 60
bust = np.zeros_like(sil); cv2.ellipse(bust, (int(cx), y0), (int(rx), int(ry)), 0, 0, 360, 255, -1)
chest = rgb[y0 - 140:y0 - 20, int(cx) - 70:int(cx) + 70].reshape(-1, 3)
chest_col = np.median(chest, axis=0).astype(np.uint8)
hole = (bust > 0) & (alpha < 128); hole[:y0, :] = False
rgb[hole] = chest_col
sil[y0:, :] = bust[y0:, :]
# soft anti-aliased edge that still follows the fine alpha inside the silhouette
edge_soft = cv2.GaussianBlur(sil, (5, 5), 0).astype(np.float32) / 255.0
fine = np.clip((alpha.astype(np.float32) / 255.0 - 0.15) / 0.5, 0, 1)
a = np.where(sil > 0, np.maximum(edge_soft * 0.999, np.minimum(fine, edge_soft)), 0)
a[y0 + 5:, :] = edge_soft[y0 + 5:, :]                      # bust area: fully opaque inside
a = np.clip(a, 0, 1)

# ---- colour: de-fringe edge, gentle detail enhance, sharpen, pop
bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
fringe = ((sil > 0) & (alpha < 200) & ~hole).astype(np.uint8) * 255
bgr = cv2.inpaint(bgr, fringe, 4, cv2.INPAINT_TELEA)
bgr = cv2.bilateralFilter(bgr, d=7, sigmaColor=28, sigmaSpace=7)          # just enough to kill JPEG noise
bgr = cv2.detailEnhance(bgr, sigma_s=12, sigma_r=0.12)                    # crisp painterly detail
blur = cv2.GaussianBlur(bgr, (0, 0), 3)
bgr = cv2.addWeighted(bgr, 1.45, blur, -0.45, 0)                          # unsharp mask
hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.28, 0, 255)
hsv[:, :, 2] = np.clip((hsv[:, :, 2] - 128) * 1.10 + 136, 0, 255)
bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
rgb2 = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

dog = Image.fromarray(np.dstack([rgb2, (a * 255).astype(np.uint8)]), "RGBA")
dog = dog.crop(dog.getbbox())
dog.save("dog_sticker_v2.png")
print("dog_sticker_v2.png", dog.size, "bust y0", y0)
