# Lire les annonces de BigMarcel24 et récupérer l'image (navigateur de l'app Claude)

Testé le 2 novembre 2026 : le profil et les pages de posts se lisent même sans être connecté
(12 derniers posts visibles), l'image du post fait 1440×1440 et se télécharge par `fetch` depuis la page
(CORS autorisé). Le CDN Instagram n'est PAS joignable depuis le shell cloud : l'image passe donc
par l'outil `javascript_tool`, en morceaux base64 vérifiés par SHA-256.
Le téléchargement classique (lien `download`) ne dépose rien dans le dossier Téléchargements.

Outils : `mcp__remote-devices__Claude_Browser__*` (charger la skill `built-in-browser` avant).
Site à autoriser : `https://instagram.com` (scope « site »).

## 1. Liste des posts du profil

```js
// page : https://www.instagram.com/bigmarcel24/
[...document.querySelectorAll('a[href*="/p/"]')].map(a => ({
  code: a.getAttribute('href').split('/p/')[1].replace('/', ''),
  alt: (a.querySelector('img') || {}).alt
}))
```
Garder les codes absents de `state/seen.json`.

## 2. Texte de l'annonce

```js
// page : https://www.instagram.com/bigmarcel24/p/<code>/
await new Promise(r => setTimeout(r, 2500));
(document.querySelector('meta[property="og:description"]') || {}).content
```
Une annonce commence par « ***Fight Announcement*** ». Sinon : marquer vu et passer.

## 3. Image en morceaux

```js
const big = [...document.querySelectorAll('article img, main img')].find(i => i.naturalWidth >= 1000);
const bm = await createImageBitmap(await (await fetch(big.currentSrc || big.src)).blob());
const S = 1080, c = document.createElement('canvas');
c.width = S; c.height = Math.round(bm.height * S / bm.width);
c.getContext('2d').drawImage(bm, 0, 0, c.width, c.height);
window.__fw = c.toDataURL('image/jpeg', 0.86).split(',')[1];
({len: window.__fw.length, chunks: Math.ceil(window.__fw.length / 30000)})
```
Puis pour chaque i :
```js
const part = window.__fw.slice(i*30000, (i+1)*30000);
const sha = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(part))))
  .map(b => b.toString(16).padStart(2, '0')).join('');
({i, sha, part})
```
Écrire chaque `part` dans `work/chunk_<i>.txt`, vérifier `sha256sum` (sans retour à la ligne final),
concaténer, `base64 -d > work/post.jpg`.

## 4. Génération

Config JSON (textes vérifiés, voir README), puis :
`python3 gen.py work/config.json --post work/post.jpg`
