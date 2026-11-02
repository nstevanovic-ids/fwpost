"""Générateur de post vidéo d'annonce Fight Week (Reel / TikTok / Short, 1080x1920).

Entrées :
  - un fichier de config JSON (textes déjà vérifiés, voir examples/cutelaba-tuchalov.json)
  - l'image du post d'annonce (deux portraits UFC côte à côte, fond blanc, comme chez BigMarcel24)
    OU deux portraits séparés via --left / --right.

Sorties dans out/ : <nom>.mp4 (10 s, H.264 + piste son muette) et <nom>_couverture.png/.jpg.

Usage :
  python3 gen.py examples/cutelaba-tuchalov.json --post examples/cutelaba-tuchalov_post.jpg
  python3 gen.py config.json --left a.png --right b.png
  options : --cover-only (couverture seule, pour contrôle rapide)
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
COVER_T = 8.0   # instant de la couverture : tout est en place, aucun reflet en cours


def split_post(path):
    """Coupe l'image du post en deux portraits, au niveau du filet clair central."""
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.float32)
    W = a.shape[1]
    lo, hi = int(W * 0.40), int(W * 0.60)
    col_std = a[:, lo:hi].std(axis=(0, 2))
    i = int(np.argmin(col_std))
    if col_std[i] < 15:                      # filet uniforme (clair ou sombre) entre les deux photos
        j0 = j1 = i
        while j0 > 0 and col_std[j0 - 1] < 15: j0 -= 1
        while j1 < len(col_std) - 1 and col_std[j1 + 1] < 15: j1 += 1
        x0, x1 = lo + j0, lo + j1 + 1
    else:
        x0 = x1 = W // 2
    left, right = im.crop((0, 0, x0, im.height)), im.crop((x1, 0, W, im.height))
    print(f'découpe du post : séparation x={x0}-{x1} sur {W}px')
    return left, right


def cutout(img, out_path):
    from rembg import remove, new_session
    global _session
    try:
        _session
    except NameError:
        _session = new_session('isnet-general-use')
    remove(img, session=_session).save(out_path)


def run(cmd):
    print('$', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config')
    ap.add_argument('--post')
    ap.add_argument('--left')
    ap.add_argument('--right')
    ap.add_argument('--cover-only', action='store_true')
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding='utf-8'))
    name = cfg.get('name') or 'FW_post'
    os.makedirs('work', exist_ok=True); os.makedirs('out', exist_ok=True)

    if args.post:
        L, R = split_post(args.post)
    else:
        L, R = Image.open(args.left).convert('RGB'), Image.open(args.right).convert('RGB')
    L.save('work/left_raw.png'); R.save('work/right_raw.png')
    for side in ('left', 'right'):
        cutout(Image.open(f'work/{side}_raw.png'), f'work/{side}_cut.png')
        run([sys.executable, 'integrate.py', f'work/{side}_cut.png', f'work/{side}_raw.png',
             'L' if side == 'left' else 'R', f'work/{side}', f'work/{side}_place.json'])

    post = {
        'event': cfg['event'], 'date': cfg['date'], 'division': cfg['division'],
        'noRed': bool(cfg.get('noRed', False)), 'duration': cfg.get('duration', 10),
    }
    for side in ('left', 'right'):
        place = json.load(open(f'work/{side}_place.json'))
        post[side] = {**cfg[side], 'img': f'work/{side}', 'x': place['x'], 'top': place['top'], 'w': place['w']}
    json.dump(post, open('work/post.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    cover = f'out/{name}_couverture.png'
    run(['node', 'render.js', '--still', str(COVER_T), cover, 'work/post.json'])
    im = Image.open(cover).convert('RGB'); im.save(cover, optimize=True); im.save(cover[:-4] + '.jpg', quality=95)
    if not args.cover_only:
        run(['node', 'render.js', f'out/{name}.mp4', 'work/post.json'])
    print('OK ->', f'out/{name}.mp4' if not args.cover_only else '', cover)


if __name__ == '__main__':
    main()
