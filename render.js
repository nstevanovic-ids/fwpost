// Rendu du post vidéo FW : node render.js <sortie.mp4> [config.json]
//                  image fixe : node render.js --still <t> <sortie.png> [config.json]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const args = process.argv.slice(2);
  const still = args[0] === '--still';
  const out = still ? args[2] : args[0];
  const cfgPath = still ? args[3] : args[1];
  const cfg = cfgPath ? JSON.parse(fs.readFileSync(cfgPath, 'utf8')) : null;

  // petit serveur local : évite que le canvas soit « sali » par des images file://
  const http = require('http');
  const types = { '.html': 'text/html', '.png': 'image/png', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.js': 'text/javascript' };
  const srv = http.createServer((req, res) => {
    const p = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
    if (!p.startsWith(__dirname) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(res);
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const port = srv.address().port;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error('pageerror', e.message));
  if (cfg) await page.addInitScript(c => { window.POST = c; }, cfg);
  await page.goto(`http://127.0.0.1:${port}/post.html`);
  await page.evaluate(() => window.ready);

  const grab = async t => {
    const url = await page.evaluate(tt => { window.drawFrame(tt); return document.getElementById('cv').toDataURL('image/png'); }, t);
    return Buffer.from(url.split(',')[1], 'base64');
  };

  if (still) {
    fs.writeFileSync(out, await grab(parseFloat(args[1])));
    await browser.close(); srv.close();
    return;
  }

  const fps = 30;
  const dur = await page.evaluate(() => window.POST.duration);
  const n = Math.round(dur * fps);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000',
    '-map', '0:v', '-map', '1:a', '-shortest',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const buf = await grab(i / fps);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close(); srv.close();
  console.log(`rendered ${n} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s -> ${out}`);
})();
