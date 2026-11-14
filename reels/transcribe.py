"""Transcription mot à mot d'un podcast FW (faster-whisper small int8, CPU).
python3 transcribe.py <video> <out.json> [--start S] [--end E]
Écrit <out.json> (segments + mots horodatés) et <out>.txt (lecture rapide [mm:ss]).
"""
import argparse, json, subprocess, os, tempfile
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('out')
ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=0)
ap.add_argument('--model', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'whisper-small'))
ap.add_argument('--prompt', default="Fight Week MMA, Niko, Aytac. Patrick Habirora, Omar El Dafrawy, PFL Dubai, "
                "guillotine, Thad Jean, Cédric Doumbè, Jake Paul, Nakisa Bidarian, welterweight, Belgian Bomber, MVP.")
a = ap.parse_args()

wav = tempfile.mktemp(suffix='.wav')
cmd = ['ffmpeg', '-v', 'error', '-y']
if a.start: cmd += ['-ss', str(a.start)]
cmd += ['-i', a.video]
if a.end: cmd += ['-t', str(a.end - a.start)]
cmd += ['-vn', '-ac', '1', '-ar', '16000', wav]
subprocess.run(cmd, check=True)

import wave, numpy as np
with wave.open(wav) as wf:
    audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
m = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=os.cpu_count())
segs, info = m.transcribe(audio, language='fr', beam_size=5, word_timestamps=True, vad_filter=True,
                          initial_prompt=a.prompt, condition_on_previous_text=True)
out = []
for s in segs:
    out.append({'start': round(s.start + a.start, 3), 'end': round(s.end + a.start, 3), 'text': s.text.strip(),
                'words': [{'start': round(w.start + a.start, 3), 'end': round(w.end + a.start, 3),
                           'w': w.word.strip(), 'p': round(w.probability, 3)} for w in (s.words or [])]})
    print(f"[{int(s.start + a.start)//60:02d}:{(s.start + a.start) % 60:05.2f}] {s.text.strip()}", flush=True)
json.dump({'segments': out}, open(a.out, 'w'), ensure_ascii=False, indent=1)
with open(os.path.splitext(a.out)[0] + '.txt', 'w') as f:
    for s in out:
        f.write(f"[{int(s['start'])//60:02d}:{s['start'] % 60:05.2f}-{int(s['end'])//60:02d}:{s['end'] % 60:05.2f}] {s['text']}\n")
os.remove(wav)
