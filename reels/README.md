# reels — 2 reels viraux à partir du dernier podcast Fight Week

Vidéos 9:16 (1080×1920, 30 i/s, −14 LUFS) découpées dans le dernier podcast de la chaîne
(@FightWeek_MMA), à la charte FW (fond `assets/back_clean.png`, logo blanc, Teko, rouge #E63026, or #FFC400).
Première version validée : podcast Habirora (14/11/2026), voir `examples/`.

## Mise en page (validée)

| Zone (px) | Contenu |
|---|---|
| 0 – 220 | vide (interface Reels/TikTok) |
| 236 – 340 | logo Fight Week blanc + étiquette or « PODCAST · ÉVÉNEMENT » |
| 400 – 600 | accroche, 2 lignes Teko 700, mots-clés en rouge / or |
| 630 – 1440 | caméra de celui qui parle (1080×810), filets rouges dessus/dessous |
| ≈ 1330 | sous-titres mot à mot, Teko Bold 116, mot prononcé en or |
| 1440 – 1920 | fond seul (légende Insta par-dessus) |

- La 1re image du reel **est** la couverture : accroche + plan, pas de sous-titre, jamais de fondu au noir.
- Une caméra à la fois (L = Niko, R = Aytac dans l'habillage OBS actuel), coupes franches aux changements de parole.
- Jump cuts dans les silences ; à chaque coupe sur la même caméra, zoom alterné 100 % / 112 %.
- Carte de fin 1,8 s : « L'ÉPISODE COMPLET SUR YOUTUBE · @FIGHTWEEK_MMA ».
- Aucune image de combat (PFL, UFC…) dans les reels.

## Chaîne de fabrication (depuis `reels/`)

```bash
bash setup.sh                                   # une fois par session (Teko, Whisper small, opencv)
mkdir -p work && cp "<MP4 du podcast>" work/src.mp4
python3 transcribe.py work/src.mp4 work/transcript.json      # ≈ 7 min pour 15 min de podcast
python3 -c "import json;d=json.load(open('work/transcript.json'));json.dump([w for s in d['segments'] for w in s['words']],open('work/words_all.json','w'),ensure_ascii=False)"
python3 speakers.py work/src.mp4 <début> <fin>  # qui parle (L / R) toutes les 0,5 s
python3 envcheck.py examples/<reel>.json        # énergie audio autour de chaque borne de coupe
python3 recut_words.py examples/<reel>.json --prompt "<noms du jour>"   # texte de chaque plan + mots recalés
python3 build.py examples/<reel>.json           # → out/<nom>/reel.mp4 + couverture.jpg + sous-titres.txt
```

| Fichier | Rôle |
|---|---|
| `transcribe.py` | Whisper small (CPU, int8), mots horodatés ; noms propres soufflés via `--prompt` |
| `speakers.py` | Caméra active : mouvement de la bouche (visage Haar) moins mouvement de la tête, par caméra |
| `envcheck.py` | Enveloppe audio (10 ms) autour des bornes, pour caler les coupes dans les silences |
| `recut_words.py` | Retranscrit chaque plan seul : vérifie qu'aucune coupe ne mange un mot et donne des horaires de mots plus fiables (à mettre dans `words`, avec `wordShift: 0`) |
| `build.py` | Calques, sous-titres ASS, plans, montage ffmpeg, couverture |
| `overlay.html` / `render_layers.js` | Calques fond + accroche et carte de fin (canvas, Playwright) |
| `setup.sh` | Dépendances, polices TekoFW pour libass, modèle Whisper (contrôle SHA-256) |

Repères : Whisper place les mots ≈ 0,1 s trop tôt (`wordShift`), coupe les élisions (`C` + `'est`, fusionnées
automatiquement) et écorche les noms (Habirora, Dafrawy, Thad Jean…) → corrections dans `edits`.
Toujours relire `sous-titres.txt` et regarder quelques images avant de livrer.
Les horaires Whisper peuvent varier de ± 0,4 s : se fier à `envcheck.py` pour les coupes, à `recut_words.py` pour le texte ;
un mot mal placé se recale avec un 4e champ dans `edits` (nouveau début). Si la 1re image tombe sur un clignement d'yeux,
`coverAt` prend la couverture à un autre instant de la source.

## Livrables par reel

`reel.mp4`, `couverture.jpg`, et une légende : post Instagram/TikTok, texte Short YouTube ≤ 100 caractères,
tags YouTube 480 – 500 caractères (noms en tête, variantes d'orthographe), faits vérifiés avec sources.
Catégories de poids en anglais, aucune citation inventée.
