"""Qui parle ? Mouvement de la bouche par caméra (L / R), source à deux webcams côte à côte.
python3 speakers.py src.mp4 START END [--cams '{"L":[18,71,604,458],"R":[657,71,604,458]}']
Sortie : une ligne par fenêtre de 0,5 s  →  t  scoreL  scoreR  verdict
"""
import sys, json, subprocess, numpy as np, cv2, argparse
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('start', type=float); ap.add_argument('end', type=float)
ap.add_argument('--cams', default='{"L":[18,71,604,458],"R":[657,71,604,458]}'); ap.add_argument('--fps', type=int, default=10)
ap.add_argument('--json')
a = ap.parse_args(); cams = json.loads(a.cams)
W, H = 1280, 720
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(a.start), '-t', str(a.end - a.start), '-i', a.src,
                      '-vf', f'fps={a.fps},scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
casc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
box = {k: None for k in cams}; prev = {k: None for k in cams}; prevU = {k: None for k in cams}
rows = []; i = 0
while True:
    buf = p.stdout.read(W * H)
    if len(buf) < W * H: break
    f = np.frombuffer(buf, np.uint8).reshape(H, W)
    r = {}
    for k, (x, y, w, h) in cams.items():
        c = f[y:y + h, x:x + w]
        if i % 5 == 0 or box[k] is None:
            fs = casc.detectMultiScale(c, 1.15, 5, minSize=(110, 110))
            if len(fs):
                fx, fy, fw, fh = max(fs, key=lambda b: b[2] * b[3])
                box[k] = (fx, fy, fw, fh) if box[k] is None else tuple(int(0.6 * o + 0.4 * n) for o, n in zip(box[k], (fx, fy, fw, fh)))
        if box[k] is None: r[k] = 0.0; continue
        fx, fy, fw, fh = box[k]
        m = c[fy + int(fh * .68): fy + int(fh * 1.0), fx + int(fw * .25): fx + int(fw * .75)]
        u = c[fy + int(fh * .2): fy + int(fh * .45), fx + int(fw * .2): fx + int(fw * .8)]
        if m.size == 0 or u.size == 0: r[k] = 0.0; continue
        m = cv2.resize(m, (64, 32)).astype(np.float32); u = cv2.resize(u, (64, 32)).astype(np.float32)
        if prev[k] is not None:
            dm = np.abs(m - prev[k]).mean(); du = np.abs(u - prevU[k]).mean()
            r[k] = max(0.0, dm - 0.8 * du)
        else: r[k] = 0.0
        prev[k] = m; prevU[k] = u
    rows.append((a.start + i / a.fps, r.get('L', 0), r.get('R', 0))); i += 1
arr = np.array(rows); step = a.fps // 2
out = []
for j in range(0, len(arr), step):
    seg = arr[j:j + step]; L = seg[:, 1].mean(); R = seg[:, 2].mean()
    v = 'L' if L > R * 1.35 else 'R' if R > L * 1.35 else '?'
    out.append((round(seg[0, 0], 2), round(L, 2), round(R, 2), v))
    print(f'{seg[0,0]:7.2f}  L {L:5.2f}  R {R:5.2f}  {v}')
if a.json: json.dump(out, open(a.json, 'w'))
