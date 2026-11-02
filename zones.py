# Superpose les zones couvertes par l'interface (Reels + TikTok, version prudente) sur une image 1080x1920
import sys
from PIL import Image, ImageDraw, ImageFont
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGBA')
ov = Image.new('RGBA', im.size, (0,0,0,0)); d = ImageDraw.Draw(ov)
Z = [  # (x0,y0,x1,y1)
  (0,0,1080,220),        # onglets en haut (Reels/Amis, Suivis/Pour toi)
  (0,1440,1080,1920),    # pseudo, légende, son
  (940,840,1080,1440),   # colonne j'aime / commentaires / partages
]
for z in Z: d.rectangle(z, fill=(0,220,255,95), outline=(0,220,255,255), width=4)
im = Image.alpha_composite(im, ov)
im.convert('RGB').resize((540,960)).save(out)
