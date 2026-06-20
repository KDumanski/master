const path = require('path');
const puppeteer = require('c:/Propcheck Git/front-end/node_modules/puppeteer');
const BASE = 'http://localhost:4322';
const OUT = path.join(__dirname, '..', '.shots');
require('fs').mkdirSync(OUT, { recursive: true });
const shots = [
  { name: 'master-dark', theme: 'dark', vp: { width: 1440, height: 900 } },
  { name: 'master-light', theme: 'light', vp: { width: 1440, height: 900 } },
  { name: 'master-mobile', theme: 'dark', vp: { width: 390, height: 844 } },
];
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  for (const s of shots) {
    const page = await browser.newPage();
    await page.setViewport(s.vp);
    await page.evaluateOnNewDocument((t) => { try { localStorage.setItem('hub-theme', t); } catch (e) {} }, s.theme);
    await page.goto(BASE + '/', { waitUntil: 'networkidle0', timeout: 30000 });
    await page.evaluate(async () => {
      const step = window.innerHeight * 0.8;
      for (let y = 0; y <= document.body.scrollHeight; y += step) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 100)); }
      window.scrollTo(0, 0);
    });
    await new Promise((r) => setTimeout(r, 800));
    await page.screenshot({ path: path.join(OUT, s.name + '.png'), fullPage: true });
    console.log('shot', s.name);
    await page.close();
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
