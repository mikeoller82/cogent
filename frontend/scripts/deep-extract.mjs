import { chromium } from 'playwright';
import fs from 'fs';

const URL = 'https://chatgpt.com/';
const OUT = 'docs';

async function run() {
  fs.mkdirSync(`${OUT}/design-references`, { recursive: true });
  fs.mkdirSync(`${OUT}/research/components`, { recursive: true });
  fs.mkdirSync(`${OUT}/research`, { recursive: true });

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox','--disable-setuid-sandbox'] });
  
  // Full extraction at desktop 1440
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(8000);
  
  // Full page screenshot
  await page.screenshot({ path: `${OUT}/design-references/full-page.png`, fullPage: true });
  
  // 1. Extract computed styles for EVERY visible element
  const styles = await page.evaluate(() => {
    const all = document.querySelectorAll('*');
    const result = [];
    all.forEach(el => {
      try {
        const r = el.getBoundingClientRect();
        if (r.width < 5 || r.height < 5) return;
        if (r.top > 2000) return;
        if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'LINK') return;
        const cs = getComputedStyle(el);
        const text = el.innerText?.trim().slice(0, 150) || '';
        const aria = el.getAttribute('aria-label') || '';
        const role = el.getAttribute('role') || '';
        const testid = el.getAttribute('data-testid') || '';
        if (!text && !aria && !role && !testid && el.children.length === 0 && el.tagName !== 'IMG' && el.tagName !== 'SVG' && el.tagName !== 'PATH') return;
        result.push({
          tag: el.tagName.toLowerCase(),
          id: el.id,
          cls: el.className?.toString().slice(0, 100) || '',
          text: text.slice(0, 120) || null,
          aria, role, testid,
          rect: `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.w)}x${Math.round(r.h)}`,
          bg: cs.backgroundColor,
          col: cs.color,
          ff: cs.fontFamily,
          fs: cs.fontSize,
          fw: cs.fontWeight,
          lh: cs.lineHeight,
          ls: cs.letterSpacing,
          display: cs.display,
          pos: cs.position,
          shadow: cs.boxShadow,
          radius: cs.borderRadius,
          opacity: cs.opacity,
          mixBlend: cs.mixBlendMode,
          backdrop: cs.backdropFilter,
          transform: cs.transform,
          border: cs.border,
          zIndex: cs.zIndex
        });
      } catch(e) {}
    });
    return result;
  });
  
  console.log('\n=== ALL VISIBLE ELEMENTS ===');
  styles.forEach(s => {
    console.log(`[${s.rect}] ${s.tag}${s.id?'#'+s.id:''}.${s.cls.split(' ')[0] || ''} "${s.text || s.aria || s.testid || s.role || ''}"`);
    console.log(`  bg:${s.bg} fg:${s.col} f:${s.fs}/${s.lh} w:${s.fw} ff:${s.ff?.split(',')[0]} display:${s.display} pos:${s.pos} radius:${s.radius} shadow:${s.shadow} border:${s.border}`);
  });
  
  // 2. Extract the full HTML of the page body
  const bodyHTML = await page.evaluate(() => document.body.innerHTML);
  fs.writeFileSync(`${OUT}/research/body-html.txt`, bodyHTML);
  
  // 3. Extract the SVG logo
  const svgLogo = await page.evaluate(() => {
    const svg = document.querySelector('svg');
    return svg ? svg.outerHTML : null;
  });
  if (svgLogo) {
    console.log('\n=== SVG LOGO ===');
    console.log(svgLogo.slice(0, 1000));
  }
  
  // 4. Extract all CSS variables
  const cssVars = await page.evaluate(() => {
    const cs = getComputedStyle(document.documentElement);
    const vars = {};
    for (let i = 0; i < cs.length; i++) {
      const prop = cs[i];
      if (prop.startsWith('--')) vars[prop] = cs.getPropertyValue(prop).trim();
    }
    return vars;
  });
  console.log('\n=== CSS VARIABLES ===');
  Object.entries(cssVars).forEach(([k,v]) => console.log(`  ${k}: ${v}`));
  
  // 5. Extract all link/script tags from head
  const head = await page.evaluate(() => {
    const links = [...document.querySelectorAll('link')].map(l => ({ rel: l.rel, href: l.href, type: l.type }));
    const scripts = [...document.querySelectorAll('script')].map(s => ({ src: s.src, type: s.type }));
    const meta = [...document.querySelectorAll('meta')].map(m => ({ name: m.name, content: m.content?.slice(0, 100), property: m.getAttribute('property') }));
    return { links, scripts, meta };
  });
  console.log('\n=== HEAD ===');
  console.log(JSON.stringify(head, null, 2).slice(0, 2000));
  
  // 6. Extract page bg
  const pageBg = await page.evaluate(() => {
    const cs = getComputedStyle(document.body);
    return { bg: cs.backgroundColor, bgImage: cs.backgroundImage, htmlBg: getComputedStyle(document.documentElement).backgroundColor };
  });
  console.log('\n=== PAGE BACKGROUND ===');
  console.log(JSON.stringify(pageBg));
  
  await page.close();
  
  // 7. Check on mobile too
  const pageM = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await pageM.goto(URL, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await pageM.waitForTimeout(5000);
  await pageM.screenshot({ path: `${OUT}/design-references/mobile-full.png`, fullPage: true });
  await pageM.close();
  
  await browser.close();
  console.log('\nDONE');
}

run().catch(e => { console.error(e); process.exit(1); });
