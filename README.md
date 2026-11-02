# fwpost — post vidéo d'annonce de combat Fight Week

Vidéo 9:16 (1080×1920, 10 s, très légèrement animée) + image de couverture, à partir d'une annonce
de combat (format BigMarcel24 : deux portraits UFC côte à côte sur fond blanc + texte).

## Utilisation

```bash
npm install                      # police Teko
pip install --break-system-packages "rembg[cpu]" opencv-python-headless scipy pillow numpy
python3 gen.py examples/cutelaba-tuchalov.json --post <image_du_post.jpg>
#   ou : --left a.png --right b.png    (deux portraits séparés)
#   --cover-only : couverture seule, pour un contrôle rapide
```

Sorties : `out/<name>.mp4` et `out/<name>_couverture.png` (+ `.jpg`).
Playwright + Chromium doivent être disponibles (`require('playwright')`), ainsi que ffmpeg.

## Fichiers

| Fichier | Rôle |
|---|---|
| `gen.py` | Tout-en-un : découpe du post, détourage (rembg isnet), intégration, couverture, vidéo |
| `integrate.py` | Intégration d'un combattant dans le fond (voir ci-dessous) + placement automatique |
| `post.html` | Modèle animé (canvas). La config arrive dans `window.POST` |
| `render.js` | Rendu image par image (Playwright) → ffmpeg ; `--still <t>` pour une image fixe |
| `zones.py` | Superpose les zones d'interface Reels/TikTok sur une image (contrôle) |
| `clean_back.py` | A servi à retirer le grand logo FW du fond de la charte (`assets/back_clean.png`) |
| `state/seen.json` | Posts BigMarcel déjà traités (veille automatique) |

## Charte validée (v7, 2 novembre 2026)

- Fond : texture rouge / bleu-gris de la charte fwtool, **sans** le grand logo FW, léger flou.
- En haut : logo Fight Week **blanc** (octogone + FIGHT WEEK), puis « ÉVÉNEMENT · LIEU » (Teko 600, 46 px)
  et la date en or (Teko 500, 32 px). Le lieu = la ville tant que la salle n'est pas officielle.
- Noms : **nom de famille seulement, jamais de prénom**, Teko 700 152 px, empilés.
  « VERSUS » exactement à mi-distance entre le bas du 1er nom et le haut du 2e (la virgule du Ț ne compte pas).
- Palmarès discret (42 px) : MMA en gros, « UFC · ÂGE » en petit dessous ; deux colonnes, filet or.
- Catégorie **toujours en anglais** dans la barre dorée : « LIGHT HEAVYWEIGHT DIVISION · 93 KG ».
- Pas de punchline, pas d'étiquette « NOUVEAU COMBAT ».
- Combattants : aucun contour (ni liseré clair, ni ombre interne / biseau). Bords décontaminés,
  teinte du fond projetée, light wrap discret, lumière rouge large côté centre, bas du corps dans le noir.
- Police : Teko partout.
- Zones d'interface respectées (Reels + TikTok, version prudente) : rien d'important au-dessus de 220 px,
  sous 1440 px, ni à droite de 940 px à partir de 840 px de haut. Vérifier avec `zones.py`.
- Couverture prise à t = 8,0 s (tout en place, aucun reflet en cours), en RGB.
- Mode `noRed: true` pour les combats de Ziam (pas de rouge).

## Veille automatique BigMarcel24 (tâche planifiée)

À 9 h, 12 h, 15 h, 18 h et 21 h (Paris), sur le PC « ids-sig10 », navigateur intégré de l'app Claude.

**Phase 1, proposition (sans GO, pas de vidéo)**
1. Ouvrir `https://www.instagram.com/bigmarcel24/`, repérer les posts absents de `state/seen.json`.
2. Lire le texte ; seules les annonces « ***Fight Announcement*** » sont proposées.
3. Envoyer à Nikola une liste numérotée (noms, catégorie, événement, date, palmarès, intérêt pour FW),
   notification push, puis ajouter les codes à `state/seen.json` (commit + push) et attendre.

**Phase 2, après « GO » (ou « GO 1, 3 ») de Nikola**
1. Vérifier chaque donnée (skill `fw-post-annonce` : deux sources concordantes, palmarès MMA et UFC séparés…).
2. Récupérer l'image du post (voir `docs/recuperer-image.md`).
3. Écrire la config, lancer `gen.py`, contrôler la couverture et `zones.py`.
4. Livrer vidéo + couverture + légende (post Instagram + version courte ≤ 100 caractères) + notes + sources.

Rien n'est jamais publié automatiquement.
