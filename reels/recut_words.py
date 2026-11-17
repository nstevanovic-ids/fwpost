"""Retranscrit chaque plan d'un reel séparément (mots horodatés plus précis qu'en passe longue)
et affiche le texte de chaque plan, pour vérifier qu'aucune coupe ne mange ou n'ajoute un mot.
python3 recut_words.py examples/<reel>.json [--out work/<reel>_words.json] [--prompt "..."]
Le fichier produit remplace `words` dans la config (wordShift: 0 conseillé).
"""
import argparse, json, os, subprocess, wave
import numpy as np
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser(); ap.add_argument('config'); ap.add_argument('--out'); ap.add_argument('--prompt', default='')
ap.add_argument('--align', action='store_true', help='expérimental : répartir les mots sur les trames voisées (mauvais sur la parole très douce)')
ap.add_argument('--model', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'whisper-small'))
a = ap.parse_args()
C = json.load(open(a.config))
out = a.out or os.path.splitext(C['words'])[0] + '_' + os.path.splitext(os.path.basename(a.config))[0] + '.json'
m = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=os.cpu_count())
words = []
for i, c in enumerate(C['cuts']):
    s, e = c[0], c[1]
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{s}', '-t', f'{e - s}', '-i', C['src'], '-ac', '1', '-ar', '16000',
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    au = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    au = np.concatenate([np.zeros(4000, np.float32), au, np.zeros(4000, np.float32)])   # 0,25 s de marge
    segs, _ = m.transcribe(au, language='fr', beam_size=5, word_timestamps=True, vad_filter=False,
                           condition_on_previous_text=False, initial_prompt=a.prompt or None)
    txt = []
    piece = []
    for sg in segs:
        for w in sg.words or []:
            ws = max(s, s + w.start - 0.25); we = min(e, s + w.end - 0.25)
            piece.append({'start': round(ws, 3), 'end': round(max(we, ws + 0.05), 3), 'w': w.word.strip(), 'p': round(w.probability, 3)})
            txt.append(w.word.strip())
    if a.align and piece:
        # recalage : on répartit les mots sur les seules trames voisées (10 ms), au prorata du nombre de lettres
        raw16 = np.frombuffer(raw, np.int16).astype(np.float32)
        n = len(raw16) // 160
        en = np.sqrt((raw16[:n * 160].reshape(n, 160) ** 2).mean(1))
        en = np.convolve(en, np.ones(3) / 3, mode='same')
        thr = max(250.0, 0.12 * np.percentile(en, 95))
        voiced = np.where(en > thr)[0]
        if len(voiced) > 5:
            weights = np.array([max(1, len(''.join(ch for ch in p['w'] if ch.isalnum()))) + 1 for p in piece], float)
            cum = np.concatenate([[0], np.cumsum(weights)]) / weights.sum()
            def at(f):
                k = min(len(voiced) - 1, int(round(f * (len(voiced) - 1))))
                return s + voiced[k] * 0.01
            for j, p in enumerate(piece):
                p['start'] = round(at(cum[j]), 3); p['end'] = round(max(at(cum[j + 1]), p['start'] + 0.05), 3)
    words += piece
    print(f'{i:2d} [{s:.2f}-{e:.2f}] {c[2]}  {" ".join(txt)}', flush=True)
json.dump(words, open(out, 'w'), ensure_ascii=False)
print('→', out)
