// Print a wrapper page to PDF with headless Chrome/Edge.
//
// Usage: node print_pdf.mjs <article.html> <out.pdf> [headerLeft] [headerRight] [footerLeft]
//
// The page is printed through the DevTools protocol so header/footer templates
// and real page numbers are available. The PDF is first written next to the
// target and then moved into place, because a PDF that is open in a viewer is
// locked on Windows and a direct write fails with EBUSY.

import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const [htmlPath, outPath, headerLeft, headerRight, footerLeft] = process.argv.slice(2);
if (!htmlPath || !outPath) {
  console.error('usage: node print_pdf.mjs <article.html> <out.pdf> [headerLeft] [headerRight] [footerLeft]');
  process.exit(2);
}

const CANDIDATES = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);
const BROWSER = CANDIDATES.find((p) => existsSync(p));
if (!BROWSER) {
  console.error('no Chrome/Edge found; set CHROME_PATH to the browser executable');
  process.exit(2);
}

const PORT = 9333;
const profile = path.resolve('work/chrome-profile');
mkdirSync(profile, { recursive: true });

const chrome = spawn(BROWSER, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--allow-file-access-from-files',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });
chrome.stderr.on('data', (d) => process.stderr.write('[browser] ' + d));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const esc = (s) => String(s ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

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
  const listeners = new Set();
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    } else if (msg.method) {
      for (const fn of listeners) fn(msg);
    }
  });
  return {
    send(method, params = {}) {
      const id = nextId++;
      return new Promise((resolve, reject) => {
        pending.set(id, { resolve, reject });
        ws.send(JSON.stringify({ id, method, params }));
      });
    },
    on(fn) { listeners.add(fn); },
  };
}

const fileUrl = 'file:///' + path.resolve(htmlPath).replace(/\\/g, '/');
const target = path.resolve(outPath);
const temp = `${target}.tmp-${process.pid}.pdf`;
const header = (left, right) => `<div style="width:100%;padding:0 0.55in;font-family:'Microsoft YaHei',sans-serif;font-size:7.5pt;color:#8b949e;display:flex;justify-content:space-between;"><span>${esc(left)}</span><span>${esc(right)}</span></div>`;
const footer = (left) => `<div style="width:100%;padding:0 0.55in;font-family:'Microsoft YaHei',sans-serif;font-size:7.5pt;color:#8b949e;display:flex;justify-content:space-between;"><span>${esc(left)}</span><span>第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</span></div>`;

try {
  const version = await waitForDevTools();
  console.log('browser:', version.Browser);

  const created = await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(fileUrl)}`,
    { method: 'PUT' }).then((r) => r.json());
  const ws = await connect(created.webSocketDebuggerUrl);
  const client = makeClient(ws);

  let loaded = false;
  client.on((msg) => { if (msg.method === 'Page.loadEventFired') loaded = true; });
  await client.send('Page.enable');
  for (let i = 0; i < 120 && !loaded; i += 1) await sleep(100);
  await sleep(1200);

  const info = await client.send('Runtime.evaluate', {
    returnByValue: true,
    expression: `(() => {
      const imgs = [...document.images];
      return JSON.stringify({
        title: document.title,
        images: imgs.length,
        loaded: imgs.filter(i => i.complete && i.naturalWidth > 0).length,
        broken: imgs.filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src')),
        sections: document.querySelectorAll('h2.sec').length,
        steps: document.querySelectorAll('h2.step').length,
        ready: window.__docReady === true,
        height: document.body.scrollHeight
      });
    })()`,
  });
  const doc = JSON.parse(info.result.value);
  console.log('doc:', JSON.stringify(doc));
  if (doc.broken.length) console.warn('WARNING broken images:', doc.broken);
  if (!doc.ready) console.warn('WARNING page cleanup script did not run');

  const pdf = await client.send('Page.printToPDF', {
    paperWidth: 8.27, paperHeight: 11.69,
    marginTop: 0.55, marginBottom: 0.62, marginLeft: 0.55, marginRight: 0.55,
    printBackground: true, scale: 1, displayHeaderFooter: true,
    headerTemplate: header(headerLeft, headerRight),
    footerTemplate: footer(footerLeft),
  });

  mkdirSync(path.dirname(target), { recursive: true });
  writeFileSync(temp, Buffer.from(pdf.data, 'base64'));

  for (let attempt = 1; attempt <= 6; attempt += 1) {
    try {
      renameSync(temp, target);
      console.log('pdf written: %s (%d bytes)', target, Buffer.from(pdf.data, 'base64').length);
      break;
    } catch (err) {
      if (attempt === 6) {
        console.error('could not replace %s (locked by a viewer?). Left it at %s\n%s', target, temp, err.message);
        process.exitCode = 1;
      } else {
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
  }
} catch (err) {
  console.error('print failed:', err.message);
  process.exitCode = 1;
} finally {
  chrome.kill();
  try { rmSync(temp, { force: true }); } catch { /* already moved */ }
}
