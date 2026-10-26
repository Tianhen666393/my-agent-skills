// Measure the wrapper page the way the printer will lay it out.
//
// Usage: node inspect_layout.mjs <article.html> [contentWidthPx]
//
// A page that looks fine on screen can still print with squashed screenshots:
// specifying `width` together with `max-height` makes Chrome clamp the height
// but keep the width. This script emulates print media, then compares each
// image's rendered rect with its natural size and flags any aspect mismatch.

import { spawn } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';

const [htmlPath, widthArg] = process.argv.slice(2);
if (!htmlPath) {
  console.error('usage: node inspect_layout.mjs <article.html> [contentWidthPx]');
  process.exit(2);
}
// A4 minus 0.55in margins at 96dpi is ~688px of content width.
const CONTENT_WIDTH = Number(widthArg) || 688;

const CANDIDATES = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);
const BROWSER = CANDIDATES.find((p) => existsSync(p));
if (!BROWSER) {
  console.error('no Chrome/Edge found; set CHROME_PATH');
  process.exit(2);
}

const PORT = 9334;
const profile = path.resolve('work/chrome-profile-inspect');
mkdirSync(profile, { recursive: true });

const chrome = spawn(BROWSER, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, 'about:blank',
], { stdio: ['ignore', 'ignore', 'ignore'] });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitForDevTools() {
  for (let i = 0; i < 120; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (res.ok) return res.json();
    } catch { /* not up yet */ }
    await sleep(250);
  }
  throw new Error('devtools endpoint did not come up');
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    ws.addEventListener('open', () => resolve(ws), { once: true });
    ws.addEventListener('error', () => reject(new Error('websocket error')), { once: true });
  });
}

function makeClient(ws) {
  let nextId = 1;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    }
  });
  return (method, params = {}) => {
    const id = nextId++;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  };
}

const fileUrl = 'file:///' + path.resolve(htmlPath).replace(/\\/g, '/');

try {
  await waitForDevTools();
  const created = await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(fileUrl)}`,
    { method: 'PUT' }).then((r) => r.json());
  const ws = await connect(created.webSocketDebuggerUrl);
  const send = makeClient(ws);
  await send('Page.enable');
  await sleep(1500);
  await send('Emulation.setDeviceMetricsOverride', {
    width: CONTENT_WIDTH, height: 1010, deviceScaleFactor: 1, mobile: false,
  });
  await send('Emulation.setEmulatedMedia', { media: 'print' });
  await sleep(600);

  const out = await send('Runtime.evaluate', {
    returnByValue: true,
    expression: `(() => {
      const imgs = [...document.images];
      return JSON.stringify({
        bodyWidth: Math.round(document.body.getBoundingClientRect().width * 10) / 10,
        images: imgs.map((im) => {
          const r = im.getBoundingClientRect();
          return {
            src: im.getAttribute('src'),
            w: Math.round(r.width * 10) / 10,
            h: Math.round(r.height * 10) / 10,
            natural: im.naturalWidth + 'x' + im.naturalHeight,
            ratio: Math.round((r.width / r.height) * 1000) / 1000,
            naturalRatio: Math.round((im.naturalWidth / im.naturalHeight) * 1000) / 1000,
          };
        }),
      });
    })()`,
  });
  const data = JSON.parse(out.result.value);
  console.log('content width:', data.bodyWidth, 'px (print media)');
  let bad = 0;
  for (const img of data.images) {
    const ok = Math.abs(img.ratio - img.naturalRatio) < 0.02;
    if (!ok) bad += 1;
    const line = [
      ok ? 'OK ' : 'BAD',
      String(img.w).padStart(7),
      'x',
      String(img.h).padEnd(7),
      'ratio=' + String(img.ratio).padEnd(6),
      'native=' + String(img.natural).padEnd(11),
      img.src,
    ].join(' ');
    console.log(line);
  }
  console.log(bad ? `!! ${bad} image(s) distorted` : 'all images keep their aspect ratio');
  if (bad) process.exitCode = 1;
} catch (err) {
  console.error('inspect failed:', err.message);
  process.exitCode = 1;
} finally {
  chrome.kill();
}
