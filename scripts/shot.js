/**
 * Headless screenshot helper for static sites (reuses front-end's Puppeteer).
 * Usage: node scripts/shot.js <url> <outPngBase> [vw] [vh]
 * Produces <outPngBase>.png (viewport) and <outPngBase>-full.png (full page).
 */
const path = require('path');
const puppeteer = require(path.join('c:', 'Propcheck Git', 'front-end', 'node_modules', 'puppeteer'));

(async () => {
  const [url, outBase, vw = '1400', vh = '900'] = process.argv.slice(2);
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: +vw, height: +vh, deviceScaleFactor: 2 });
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise((r) => setTimeout(r, 2000));
    // hero (above the fold)
    await page.screenshot({ path: `${outBase}.png` });

    // auto-scroll through the page to trigger all scroll-reveal animations
    await page.evaluate(async () => {
      await new Promise((resolve) => {
        let y = 0;
        const step = window.innerHeight * 0.6;
        const timer = setInterval(() => {
          window.scrollTo(0, y);
          y += step;
          if (y > document.body.scrollHeight) { clearInterval(timer); resolve(); }
        }, 220);
      });
    });
    await new Promise((r) => setTimeout(r, 1200));

    // capture each named section at viewport size
    const sections = ['work', 'process', 'about', 'press', 'exhibitions', 'contact'];
    for (const id of sections) {
      const el = await page.$(`#${id}`);
      if (!el) continue;
      await page.evaluate((sid) => document.getElementById(sid).scrollIntoView({ block: 'start' }), id);
      await new Promise((r) => setTimeout(r, 700));
      await page.screenshot({ path: `${outBase}-${id}.png` });
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await new Promise((r) => setTimeout(r, 400));
    await page.screenshot({ path: `${outBase}-full.png`, fullPage: true });
    console.log('OK wrote viewport, per-section, and full screenshots for', outBase);
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
