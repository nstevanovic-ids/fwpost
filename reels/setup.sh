#!/usr/bin/env bash
# Installe tout ce qu'il faut pour monter des reels FW (à lancer une fois par session, depuis reels/).
# - police Teko (npm, à la racine du dépôt) + copies TTF renommées « TekoFW » pour libass (reels/fonts/)
# - faster-whisper, opencv (détection de la caméra active), fonttools
# - modèle Whisper small (CTranslate2 int8), récupéré sur le registre npm en 4 morceaux, contrôlé par SHA-256
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."
[ -d node_modules/@fontsource/teko ] || npm install --silent --ignore-scripts
pip install --break-system-packages -q faster-whisper fonttools brotli "opencv-python-headless<5" numpy 2>&1 | grep -v -E "WARNING|already" || true

# --- polices pour libass ---
mkdir -p "$HERE/fonts"
python3 - "$HERE/fonts" <<'EOF'
import sys
from fontTools.ttLib import TTFont
out = sys.argv[1]
for w, name in [(500, 'TekoFW Medium'), (600, 'TekoFW SemiBold'), (700, 'TekoFW Bold')]:
    f = TTFont(f'node_modules/@fontsource/teko/files/teko-latin-{w}-normal.woff2'); f.flavor = None
    for rec in f['name'].names:
        if rec.nameID in (1, 4, 16): rec.string = name
        elif rec.nameID == 6: rec.string = name.replace(' ', '-')
        elif rec.nameID in (2, 17): rec.string = 'Regular'
    f['OS/2'].usWeightClass = 400
    f['OS/2'].fsSelection = (f['OS/2'].fsSelection & ~0b100001) | 0b1000000
    f['head'].macStyle = 0
    f.save(f'{out}/TekoFW-{w}.ttf')
print('polices ok')
EOF

# --- modèle Whisper small ---
M="$HERE/models/whisper-small"
if [ ! -f "$M/model.bin" ]; then
  T="$(mktemp -d)"; mkdir -p "$M"
  ( cd "$T" && for i in 0 1 2 3; do npm pack --silent "@skillninja/shortmovie-telop-model-p$i@1.0.0" >/dev/null; done
    for f in *.tgz; do d="${f%.tgz}"; mkdir -p "$d"; tar xzf "$f" -C "$d"; done )
  cat "$T"/*p0*/package/model.bin.part0 "$T"/*p1*/package/model.bin.part1 \
      "$T"/*p2*/package/model.bin.part2 "$T"/*p3*/package/model.bin.part3 > "$M/model.bin"
  cp "$T"/*p0*/package/{config.json,preprocessor_config.json,tokenizer.json,vocabulary.json} "$M/"
  echo "ca732cb1379efc49417d028465f543d83a39de2c61f3027678de103dc404ce73  $M/model.bin" | sha256sum -c -
  rm -rf "$T"
fi
python3 -c "import faster_whisper, cv2; print('faster-whisper', faster_whisper.__version__, '| opencv', cv2.__version__)"
echo "setup ok"
