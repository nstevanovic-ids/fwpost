// node render_layers.js <config.json> <outdir>  → bg.png (opaque) + end.png (transparent)
const fs = require('fs'), path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/npm-tools/node_modules/playwright')); }
(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const out = process.argv[3]; fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.join(__dirname, 'overlay.html'));
  await p.evaluate(c => { window.CFG = c; }, cfg);
  for (const layer of ['bg', 'end']) {
    await p.evaluate(l => window.renderLayer(l), layer);
    const el = await p.$('#cv');
    await el.screenshot({ path: path.join(out, layer + '.png'), omitBackground: true });
  }
  await b.close();
  console.log('layers ok');
})().catch(e => { console.error(e); process.exit(1); });
