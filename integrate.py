"""Intégration d'un combattant détouré dans le fond de la charte FW (sans effet de contour).

Placement automatique : la tête est mise à l'échelle (largeur cible), le haut du crâne et le
centre du visage sont calés sur des positions fixes, à gauche ou à droite.

Étapes : décontamination des bords (retire le blanc du fond d'origine), couleur des bords prise
à l'intérieur, détourage resserré puis adouci, étalonnage, teinte du fond projetée,
light wrap discret, lumière rouge large côté centre, bas du corps qui s'enfonce dans le noir.

Usage : python3 integrate.py <cut.png> <raw.png> <L|R> <out_prefix> <placement.json> [back.png]
"""
import sys, json
import numpy as np
import cv2

UP = 2
cut_p, raw_p, side, prefix, place_p = sys.argv[1:6]
back_p = sys.argv[6] if len(sys.argv) > 6 else 'assets/back_clean.png'
# cibles sur le canvas 1080x1920 (calées sur la v7 validée)
HEAD_TOP, HEAD_W = 455.0, 236.0
FACE_X = 284.0 if side == 'L' else 798.0
CROP_FRAC = 0.90          # on coupe le bas (short, icônes éventuelles)


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def gblur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


cut = cv2.imread(cut_p, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0   # BGRA
raw = cv2.imread(raw_p).astype(np.float32) / 255.0                         # BGR, fond blanc d'origine
CROP = int(round(cut.shape[0] * CROP_FRAC))
cut, raw = cut[:CROP], raw[:CROP]
h, w = cut.shape[:2]
cut = cv2.resize(cut, (w * UP, h * UP), interpolation=cv2.INTER_LANCZOS4)
raw = cv2.resize(raw, (w * UP, h * UP), interpolation=cv2.INTER_LANCZOS4)
H, W = cut.shape[:2]
a = np.clip(cut[..., 3], 0, 1)
C = raw  # couleur observée (avant détourage)

# placement automatique (sur l'alpha brut, en coordonnées de la couche)
_m = a > 0.5
_rows = np.nonzero(_m.sum(1) > 3 * UP)[0]
_top = int(_rows[0])
_band = _m[_top + int(0.04 * H):_top + int(0.09 * H)]
_hw = float(np.median(_band.sum(1)))
_cx = float(np.nonzero(_band)[1].mean())
s_can = HEAD_W / max(_hw, 1.0)                 # couche -> canvas
FW = W * s_can
TOP = HEAD_TOP - _top * s_can
X = FACE_X - _cx * s_can
# bord intérieur coupé par le cadrage ? -> fondu sur ce bord
_edge_col = _m[:, -1] if side == 'L' else _m[:, 0]
inner_fade = int(0.116 * (W / UP)) if _edge_col.mean() > 0.05 else 0
json.dump({'x': round(X, 2), 'top': round(TOP, 2), 'w': round(FW, 2), 'innerFade': inner_fade},
          open(place_p, 'w'))

# 1) décontamination : couleur du fond d'origine estimée autour du sujet
bgw = (a < 0.02).astype(np.float32)
num = gblur(C * bgw[..., None], 25)
den = gblur(bgw, 25)[..., None]
B = num / np.maximum(den, 1e-3)
B[den[..., 0] < 1e-3] = C[den[..., 0] < 1e-3]
Fdec = np.clip((C - (1 - a[..., None]) * B) / np.maximum(a[..., None], 0.08), 0, 1)
# uniquement sur le vrai bord (près du fond) : à l'intérieur, l'alpha un peu sous 1 ne doit rien changer
near_bg = cv2.dilate((a < 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (6 * UP + 1, 6 * UP + 1)))
near_bg = gblur(near_bg.astype(np.float32), 1.5 * UP)
wd = (np.clip((0.98 - a) / 0.4, 0, 1) * near_bg)[..., None]
F = C * (1 - wd) + Fdec * wd

# 1b) bords : la couleur des pixels de bord est remplacée par celle de l'intérieur tout proche
#     (supprime tout liseré clair, en particulier sur les cheveux sombres)
core = (a > 0.96).astype(np.float32)
core = cv2.erode(core, np.ones((3, 3), np.uint8))
ext = gblur(F * core[..., None], 2.5 * UP) / np.maximum(gblur(core, 2.5 * UP)[..., None], 1e-4)
far = gblur(core, 2.5 * UP) < 1e-3
ext[far] = F[far]
wedge = (np.clip((0.96 - a) / 0.5, 0, 1) * near_bg)[..., None]
F = F * (1 - wedge) + ext * wedge

# 2) détourage : léger resserrement + adoucissement d'un pixel
a = np.clip((a - 0.12) / 0.80, 0, 1)
a = gblur(a, 0.9 * UP)

ys = np.linspace(0, 1, H)[:, None]
xs = np.linspace(0, 1, W)[None, :]
inner = xs if side == 'L' else 1 - xs          # 1 = côté centre

# 3) étalonnage de base
lum = (F * [0.0722, 0.7152, 0.2126]).sum(-1, keepdims=True)  # BGR
F = lum + (F - lum) * 0.82
F = np.clip((F - 0.03) / 0.97, 0, 1) ** 1.15
F = np.clip(0.5 + (F - 0.5) * 1.10, 0, 1)
F = F * (0.70 + 0.30 * ss(0.0, 0.8, inner))[..., None]       # clair-obscur doux

# fond de la charte à l'emplacement du combattant (pour teinte + light wrap)
back = cv2.imread(back_p).astype(np.float32) / 255.0
M = np.float32([[s_can, 0, X], [0, s_can, TOP]])  # couche -> canvas
Minv = cv2.invertAffineTransform(M)
bg_local = cv2.warpAffine(back, Minv, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
bg_soft = gblur(bg_local, 40)

# teinte de l'environnement : « soft light » du fond flouté, à faible dose
def soft_light(base, blend):
    return np.where(blend < 0.5, base - (1 - 2 * blend) * base * (1 - base),
                    base + (2 * blend - 1) * (np.sqrt(base) - base))
F = F * 0.72 + soft_light(F, bg_soft) * 0.28

# 4) light wrap : le fond flouté déborde sur une bande fine du bord (couleur du fond, pas blanc)
band = a * np.clip(1 - gblur(a, 3 * UP), 0, 1) * 1.6
band = np.clip(band, 0, 1)[..., None]
wrapc = gblur(bg_local, 10)
F = F * (1 - 0.14 * band) + wrapc * (0.14 * band)

# 5) lumière rouge large côté centre (calque séparé pour l'animation)
# distance horizontale depuis le contour côté centre, ligne par ligne (contour lissé verticalement)
m5 = a > 0.5
idx = np.arange(W, dtype=np.float32)[None, :]
has = m5.any(1)
if side == 'R':
    x0 = np.where(has, m5.argmax(1), W).astype(np.float32)
else:
    x0 = np.where(has, W - 1 - m5[:, ::-1].argmax(1), -1).astype(np.float32)
x0 = cv2.GaussianBlur(x0.reshape(-1, 1), (0, 0), sigmaX=0.1, sigmaY=6 * UP).ravel()
dist = (idx - x0[:, None]) if side == 'R' else (x0[:, None] - idx)
lit = np.exp(-np.clip(dist, 0, None) / (34 * UP)) * a
lit = gblur(lit, 3 * UP)
lit = np.clip(lit * 1.25, 0, 1) * a
skin = (F * [0.0722, 0.7152, 0.2126]).sum(-1)
lit = lit * (0.35 + 0.65 * np.clip(skin * 1.6, 0, 1))       # suit le relief, pas un trait
lit = lit * (1 - ss(0.42, 0.85, ys))                          # surtout tête, épaules
red_bgr = np.array([38, 48, 230], np.float32) / 255.0

# 6) le bas s'enfonce dans le noir, puis disparaît
dark = ss(0.50, 0.86, ys)
F = F * (1 - 0.85 * dark)[..., None]
fade = 1 - ss(0.72, 0.985, ys)
a = a * fade
if inner_fade:
    px = inner_fade * UP
    ramp = np.ones(W, np.float32)
    r = ss(0, 1, np.linspace(0, 1, px))
    if side == 'L':
        ramp[-px:] = r[::-1]
    else:
        ramp[:px] = r
    a = a * ramp[None, :]
    lit = lit * ramp[None, :]


def save(rgb_bgr, alpha, path):
    out = np.dstack([np.clip(rgb_bgr, 0, 1), np.clip(alpha, 0, 1)])
    cv2.imwrite(path, (out * 255 + 0.5).astype(np.uint8))


save(F, a, f'{prefix}_body.png')
save(np.broadcast_to(red_bgr, F.shape), lit * fade, f'{prefix}_rimred.png')
save(np.zeros_like(F), np.zeros_like(a), f'{prefix}_rimcold.png')
print(prefix, W, H, 'ok')
