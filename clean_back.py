"""Retire le grand logo FW blanc du fond de la charte (back.png) en reconstruisant la texture.

Couleur : inpainting à basse résolution (pas de frontières visibles), lissé.
Grain : détail haute fréquence emprunté juste au-dessus / au-dessous du logo
(la texture est faite de stries verticales, un décalage vertical reste crédible).
"""
import numpy as np
import cv2

src = cv2.imread('assets/back_charte_original.png').astype(np.float32)
H, W = src.shape[:2]
mask = (src.min(-1) > 150).astype(np.uint8)
mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
m = mask.astype(np.float32)

# 1) basse fréquence : inpainting sur une version réduite
k = 6
small = cv2.resize(src, (W // k, H // k), interpolation=cv2.INTER_AREA)
smask = cv2.resize(mask, (W // k, H // k), interpolation=cv2.INTER_NEAREST)
smask = cv2.dilate(smask, np.ones((3, 3), np.uint8))
inp = cv2.inpaint(np.clip(small, 0, 255).astype(np.uint8), smask, 12, cv2.INPAINT_TELEA).astype(np.float32)
low = cv2.resize(inp, (W, H), interpolation=cv2.INTER_CUBIC)
low = cv2.GaussianBlur(low, (0, 0), 18)

# 2) détail : haute fréquence décalée verticalement depuis une zone sans logo
hp = src - cv2.GaussianBlur(src, (0, 0), 10)
ys, xs = np.nonzero(mask)
top, bot = ys.min(), ys.max()
split = (top + bot) // 2
detail = np.zeros_like(src)
mirror_end = 2 * top - 40
for y in range(top, bot + 1):
    # moitié haute : miroir de la bande au-dessus du logo ; reste : bande sous le logo
    sy = (2 * top - 40 - y) if y < mirror_end else (bot + 40 + (y - mirror_end))
    sy = int(np.clip(sy, 0, H - 1))
    detail[y] = hp[sy]

recon = np.clip(low + detail * 1.0, 0, 255)
alpha = cv2.GaussianBlur(m, (0, 0), 9)[..., None]
out = src * (1 - alpha) + recon * alpha
cv2.imwrite('assets/back_clean.png', np.clip(out, 0, 255).astype(np.uint8))
print('masque', top, bot, 'ok')
