"""Monte un reel FW 9:16 (1080×1920) à partir d'extraits d'un podcast Fight Week.
Usage (depuis reels/) :  python3 build.py examples/<reel>.json

Config (voir examples/) :
  src        vidéo source (MP4 téléchargé depuis YouTube Studio)
  words      mots horodatés produits par transcribe.py (work/words_all.json)
  out        dossier de sortie → reel.mp4, couverture.png/.jpg, sous-titres.txt, cuts_snapped.json
  label      étiquette or sous le logo (« PODCAST · PFL DUBAI »)
  hook       accroche, lignes de segments {t, c} avec c = bone | red | gold
  cams       zones caméra dans la source (x, y, w, h) — L = Niko, R = Aytac (format OBS 2 webcams)
  cuts       [[début, fin, caméra, (zoom)], …] en secondes de la source ; une ligne = un plan (jump cut)
             bornes à placer dans les silences (vérifier avec envcheck.py), snap: false conseillé
  edits      corrections de sous-titres [début_du_mot, nb_de_mots, "remplacement"] ("" = supprimer)
  coverAt    (option) instant de la source utilisé pour couverture.jpg (ex. éviter un clignement) ; la vidéo, elle, démarre sur sa vraie 1re image
  tile/subY/subSize/maxChars/punch/tail/wordShift : mise en page et réglages (valeurs par défaut validées)
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(sys.argv[1]))
os.makedirs(C['out'], exist_ok=True)
OUT = os.path.abspath(C['out']); TAIL = C.get('tail', 1.8)
TX, TY, TW, TH = C.get('tile', [0, 630, 1080, 810])
PUNCH = C.get('punch', 1.10)

# ---------- 1. calques (fond + accroche, carte de fin) ----------
cfg = {'label': C['label'], 'hook': C['hook'], 'hookY': C.get('hookY', 400), 'hookSize': C.get('hookSize', 124),
       'logoY': C.get('logoY', 236), 'tiles': [{'rect': [TX, TY, TW, TH]}]}
json.dump(cfg, open(f'{OUT}/layers.json', 'w'), ensure_ascii=False)
subprocess.run(['node', f'{HERE}/render_layers.js', f'{OUT}/layers.json', OUT], check=True, cwd=HERE)

# ---------- 2. découpe : plages de la source (jump cuts) ----------
CUTS = [list(c) for c in C['cuts']]   # [[srcA, srcB, cam, (zoom)], ...]
import numpy as np
def env(t0, t1):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t0}', '-t', f'{t1 - t0}', '-i', C['src'], '-ac', '1', '-ar', '16000',
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)
    n = len(a) // 160
    return np.sqrt((a[:n * 160].reshape(n, 160) ** 2).mean(1))   # 10 ms
def snap(t, before, after):
    e = env(t - before, t + after)
    k = np.convolve(e, np.ones(3) / 3, mode='same')
    return round(t - before + int(np.argmin(k)) * 0.01, 3)
if C.get('snap', True):
    for c in CUTS:   # début : on ne recule que dans le silence avant le 1er mot ; fin : idem après le dernier
        c[0] = snap(c[0], 0.15, 0.02); c[1] = snap(c[1], 0.02, 0.15)
json.dump(CUTS, open(f'{OUT}/cuts_snapped.json', 'w'))
for c in CUTS:   # durées calées sur la trame 30 i/s : pas de dérive son/image entre les coupes
    c[1] = round(c[0] + round((c[1] - c[0]) * 30) / 30, 4)
offs = []; t = 0.0
for c in CUTS:
    offs.append(t); t += c[1] - c[0]
D = round(t, 3)
def map_t(x):
    for (a, b, *_), o in zip(CUTS, offs):
        if a - 0.02 <= x <= b + 0.02: return o + min(max(x, a), b) - a
    return None

# ---------- 3. sous-titres ASS mot à mot ----------
allw = json.load(open(C['words']))
# fusion des élisions / traits d'union découpés par Whisper (C + 'est, Va + -t + 'en, 11 + -0)
merged = []
for w in allw:
    t = w['w'].strip()
    if merged and (t.startswith("'") or t.startswith("’") or (t.startswith('-') and len(t) > 1) or t in ('?', '!')) and w['start'] - merged[-1]['end'] < 0.6:
        merged[-1]['w'] += t; merged[-1]['end'] = w['end']
    else:
        merged.append(dict(w, w=t))
# corrections manuelles : [début_du_mot, nb_de_mots, "remplacement"]
for ed in C.get('edits', []):   # [début, nb_mots, remplacement, (nouveau début)]
    t0, nw, rep = ed[:3]
    idx = min(range(len(merged)), key=lambda i: abs(merged[i]['start'] - t0))
    if abs(merged[idx]['start'] - t0) > 0.06: raise SystemExit(f'edit introuvable à {t0}')
    end = merged[idx + nw - 1]['end']
    new = dict(merged[idx], w=rep, end=end)
    if len(ed) > 3: new['start'] = ed[3]; new['end'] = max(end, ed[3] + 0.05)
    merged[idx:idx + nw] = [new] if rep else []
allw = merged
SH = C.get('wordShift', 0.10)   # Whisper place les mots un peu en avance
def in_cut(m):
    for (a, b, *_), o in zip(CUTS, offs):
        if a <= m <= b: return a, b, o
    return None
words = []
for w in allw:
    ws, we = w['start'] + SH, w['end'] + SH
    hit = None
    for (a, b, *_), o in zip(CUTS, offs):
        if a - 0.12 <= ws <= b - 0.08: hit = (a, b, o); break
    if not hit: continue
    a, b, o = hit
    s = o + max(ws, a) - a; e = o + min(we, b) - a
    words.append({'w': w['w'], 's': s, 'e': max(e, s + 0.05)})
words.sort(key=lambda w: w['s'])
FIX = C.get('fix', {})
FUNC = {'DE','DU','DES','LA','LE','LES','UN','UNE','EN','À','AU','AUX','QUI','ET','CE','SA','SON','SES','TA','TON','MA','MON','POUR','PAR','SUR','DANS','AVEC','IL','ELLE','TU','JE','ON','NE','PAS',"D'UNE","D'UN"}
def clean(t):
    t = t.upper().replace('’', "'")
    t = re.sub(r"[.,;:«»\"…]", '', t)
    return t.strip()
chunks, cur = [], []
for w in words:
    raw = w['w'].strip()
    if raw in FIX: raw = FIX[raw]
    txt = clean(raw)
    if not txt: continue
    w['T'] = txt
    if cur:
        n_chars = sum(len(x['T']) for x in cur) + len(txt)
        gap = w['s'] - cur[-1]['e']
        hard = gap > 0.35 or re.search(r'[.?!,;:]$', cur[-1]['w'])
        if hard or len(cur) >= C.get('maxWords', 3) or n_chars > C.get('maxChars', 16):
            carry = []
            if not hard and len(cur) > 1 and cur[-1]['T'] in FUNC: carry = [cur.pop()]
            chunks.append(cur); cur = carry
    cur.append(w)
if cur: chunks.append(cur)

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"
BONE, GOLD = '&HE8EDED&', '&H00C4FF&'
SUBY = C.get('subY', 1318); FS = C.get('subSize', 104)
ev = []
for ci, ch in enumerate(chunks):
    nxt = chunks[ci + 1][0]['s'] if ci + 1 < len(chunks) else None
    c_end = nxt if (nxt is not None and nxt - ch[-1]['e'] < 0.6) else ch[-1]['e'] + 0.25
    c_end = min(c_end, D)
    for wi, w in enumerate(ch):
        a = max(w['s'], 0.12) if ci == 0 and wi == 0 else w['s']
        b = ch[wi + 1]['s'] if wi + 1 < len(ch) else c_end
        if b <= a: continue
        parts = []
        for k, x in enumerate(ch):
            if k == wi: parts.append(f"{{\\c{GOLD}\\fscx106\\fscy106}}{x['T']}{{\\c{BONE}\\fscx100\\fscy100}}")
            else: parts.append(x['T'])
        pop = r'\fscx88\fscy88\t(0,90,\fscx100\fscy100)' if wi == 0 else ''
        ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},FW,,0,0,0,,{{\\pos(540,{SUBY}){pop}}}" + ' '.join(parts))
ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: FW,TekoFW Bold,{FS},&H00E8EDED,&H00E8EDED,&H00050505,&H96000000,0,0,0,0,100,100,1,0,1,7,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + '\n'.join(ev) + '\n'
open(f'{OUT}/subs.ass', 'w').write(ass)
with open(f'{OUT}/sous-titres.txt', 'w') as f:
    for c in chunks: f.write(f"{ts(c[0]['s'])}  {' '.join(x['T'] for x in c)}\n")

# ---------- 4. plans : caméra active, punch-in alterné à chaque coupe ----------
fg = []; inputs = []
prev_cam, z_toggle = None, False
for i, c in enumerate(CUTS):
    a, b, cam = c[0], c[1], c[2]
    k = i + 2
    inputs += ['-ss', f'{a}', '-t', f'{b - a:.3f}', '-i', C['src']]
    x, y, w, h = C['cams'][cam]
    tr = TW / TH
    if w / h > tr: cw, ch_ = round(h * tr), h
    else: cw, ch_ = w, round(w / tr)
    z_toggle = (not z_toggle) if cam == prev_cam else False
    prev_cam = cam
    z = c[3] if len(c) > 3 else (PUNCH if z_toggle else 1.0)
    cw2, ch2 = round(cw / z / 2) * 2, round(ch_ / z / 2) * 2
    fy = C.get('faceY', {}).get(cam, 0.40)
    cx = x + (w - cw2) // 2
    cy = y + (h - ch2) // 2 if z == 1.0 else y + min(max(0, round((h - ch2) * fy * 2 * 0.5 + (h * fy - ch2 * fy) * 0)), h - ch2)
    if z != 1.0: cy = y + min(max(0, round(h * fy - ch2 * fy)), h - ch2)
    dur = b - a
    fg.append(f"[{k}:v]fps=30,trim=0:{dur:.3f},setpts=PTS-STARTPTS,crop={cw2}:{ch2}:{cx}:{cy},scale={TW}:{TH}:flags=lanczos,setsar=1[v{i}]")
    fg.append(f"[{k}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={max(0, dur - 0.015):.3f}:d=0.015[a{i}]")
n = len(CUTS)
fg.append(''.join(f'[v{i}][a{i}]' for i in range(n)) + f"concat=n={n}:v=1:a=1[catv][cata]")
fg.append(f"[catv]tpad=stop_mode=clone:stop_duration={TAIL}[cam0]")
# la vidéo démarre sur sa vraie 1re image : coverAt ne sert qu'à couverture.jpg (sinon flash de 2 images au début)
fg.append("[cam0]null[cam]")
fg.append("[0:v]scale=1080:1920,setsar=1,format=yuv420p[bg]")
fg.append(f"[bg][cam]overlay={TX}:{TY}:shortest=1[c1]")
fg.append(f"[c1]ass={OUT}/subs.ass:fontsdir={HERE}/fonts[c2]")
fg.append(f"[c2][1:v]overlay=0:0:enable='gte(t,{D})'[c3]")
fg.append("[c3]noise=alls=4:allf=t,format=yuv420p[vout]")
fg.append(f"[cata]afade=t=out:st={max(0, D - 0.3):.3f}:d=0.3,apad=pad_dur={TAIL},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
T = D + TAIL
cmd = ['ffmpeg', '-v', 'error', '-y',
       '-loop', '1', '-framerate', '30', '-t', f'{T}', '-i', f'{OUT}/bg.png',
       '-loop', '1', '-framerate', '30', '-t', f'{T}', '-i', f'{OUT}/end.png'] + inputs + [
       '-filter_complex', ';'.join(fg), '-map', '[vout]', '-map', '[aout]', '-t', f'{T:.3f}',
       # -bf 0 : pas d'images B, donc pas de décalage de 2 images (edit list) que beaucoup de lecteurs affichent comme un flash au début
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-bf', '0', '-maxrate', '12M', '-bufsize', '24M', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', '30',
       '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'{OUT}/reel.mp4']
subprocess.run(cmd, check=True)
if C.get('coverAt') is not None:
    # couverture prise à un autre instant de la source (ex. éviter un clignement d'yeux), sans toucher à la vidéo
    x, y, w, h = C['cams'][CUTS[0][2]]
    tr = TW / TH
    cw, ch_ = (round(h * tr), h) if w / h > tr else (w, round(w / tr))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/bg.png', '-ss', f"{C['coverAt']}", '-i', C['src'], '-filter_complex',
                    f"[1:v]trim=end_frame=1,crop={cw}:{ch_}:{x + (w - cw) // 2}:{y + (h - ch_) // 2},scale={TW}:{TH}:flags=lanczos,setsar=1[cov];"
                    f"[0:v]scale=1080:1920,setsar=1[bg];[bg][cov]overlay={TX}:{TY},format=rgb24",
                    '-frames:v', '1', f'{OUT}/couverture.png'], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/reel.mp4', '-frames:v', '1', f'{OUT}/couverture.png'], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/couverture.png', '-q:v', '2', f'{OUT}/couverture.jpg'], check=True)
print('ok', OUT, f'{T:.1f}s', len(chunks), 'blocs de sous-titres')
