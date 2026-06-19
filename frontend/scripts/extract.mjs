import { chromium } from 'playwright';
import fs from 'fs';

const URL = 'https://chatgpt.com/';
const OUT = 'docs';

async function run() {
  fs.mkdirSync(`${OUT}/design-references`, { recursive: true });
  fs.mkdirSync(`${OUT}/research`, { recursive: true });

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox','--disable-setuid-sandbox'] });
  
  // Test at multiple viewports
  for (const [label, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(e => {});
    await page.waitForTimeout(12000);
    
    console.log(`\n===== ${label} (${width}x${height}) =====`);
    console.log('URL:', page.url());
    
    // Screenshots
    await page.screenshot({ path: `${OUT}/design-references/${label}-full.png`, fullPage: true }).catch(e => {});
    await page.screenshot({ path: `${OUT}/design-references/${label}-viewport.png` }).catch(e => {});
    
    // Text
    const text = await page.evaluate(() => document.body.innerText).catch(() => '');
    console.log('TEXT:', text.slice(0, 3000));
    
    // All elements
    const els = await page.evaluate(() => {
      const items = [];
      try {
        const all = document.querySelectorAll('*');
        all.forEach(el => {
          try {
            const r = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) return;
            const cs = getComputedStyle(el);
            const text = (el.innerText || '').trim().slice(0, 120);
            const aria = el.getAttribute('aria-label') || '';
            const testid = el.getAttribute('data-testid') || '';
            if (!text && !aria && !testid && el.children.length === 0 && el.tagName !== 'IMG' && el.tagName !== 'svg' && el.tagName !== 'path') return;
            items.push({
              tag: el.tagName.toLowerCase(),
              id: el.id,
              cls: (el.className && typeof el.className === 'string') ? el.className.slice(0, 80) : '',
              text: text || aria.slice(0, 60) || null,
              testid: testid || null,
              role: el.getAttribute('role') || null,
              w: Math.round(r.width), h: Math.round(r.height),
              y: Math.round(r.top), x: Math.round(r.left),
              display: cs.display,
              pos: cs.position,
              bg: cs.backgroundColor,
              col: cs.color,
              fs: cs.fontSize,
              fw: cs.fontWeight
            });
          } catch(e) {}
        });
      } catch(e) {}
      return items;
    }).catch(() => []);
    
    console.log(`\n--- Elements (${els.length}) ---`);
    const visible = els.filter(e => e.y >= 0 && e.y < 2000);
    visible.forEach(e => {
      const line = `y:${e.y} x:${e.x} ${e.tag}${e.id?'#'+e.id:''} [${e.w}x${e.h}] ${e.text || e.testid || e.role || ''} fg:${e.col} bg:${e.bg} fs:${e.fs}`;
      console.log(line.slice(0, 300));
    });
    
    await page.close();
  }
  
  await browser.close();
  console.log('\nDONE');
}

run().catch(e => { console.error(e); process.exit(1); });
