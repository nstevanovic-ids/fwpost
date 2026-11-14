"""Affiche l'enveloppe audio (10 ms, 0-9) autour des bornes de coupe d'un reel.json."""
import json, sys, subprocess, numpy as np
C = json.load(open(sys.argv[1]))
def env(t0, d=0.7):
    raw = subprocess.run(['ffmpeg','-v','error','-ss',f'{t0}','-t',f'{d}','-i',C['src'],'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(float)
    return ''.join(str(min(9, int(np.sqrt((a[i:i+160]**2).mean())/250))) for i in range(0, len(a)-160, 160))
for c in C['cuts']:
    print(f"START {c[0]:.2f}  [{c[0]-0.35:.2f}] {env(c[0]-0.35)}")
    print(f"END   {c[1]:.2f}  [{c[1]-0.35:.2f}] {env(c[1]-0.35)}")
