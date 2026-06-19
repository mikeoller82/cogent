import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const URL = 'https://chatgpt.com/';
const OUTPUT_DIR = 'docs';

async function run() {
  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });

  // ---- DESKTOP FULL PAGE ----
  await desktop.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
  await desktop.waitForTimeout(2000);
  await desktop.screenshot({ path: 'docs/design-references/chatgpt-desktop-full.png', fullPage: true });
  await desktop.screenshot({ path: 'docs/design-references/chatgpt-desktop-viewport.png', fullPage: false });

  // ---- MOBILE ----
  await mobile.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
  await mobile.waitForTimeout(2000);
  await mobile.screenshot({ path: 'docs/design-references/chatgpt-mobile-full.png', fullPage: true });

  // ---- EXTRACT FONTS ----
  const fonts = await desktop.evaluate(() => {
    const els = [...document.querySelectorAll('*')].slice(0, 300);
    const fonts = new Set();
    els.forEach(el => {
      const f = getComputedStyle(el).fontFamily;
      if (f && f !== 'none') fonts.add(f);
    });
    return [...fonts];
  });
  fs.writeFileSync(`${OUTPUT_DIR}/research/fonts.json`, JSON.stringify(fonts, null, 2));

  // ---- EXTRACT COLORS ----
  const colors = await desktop.evaluate(() => {
    const els = [...document.querySelectorAll('*')].slice(0, 300);
    const colors = new Set();
    els.forEach(el => {
      const cs = getComputedStyle(el);
      ['color', 'backgroundColor', 'borderColor'].forEach(p => {
        const v = cs[p];
        if (v && v !== 'rgba(0, 0, 0, 0)' && v !== 'transparent' && !v.includes('initial')) {
          colors.add(v);
        }
      });
    });
    return [...colors].sort();
  });
  fs.writeFileSync(`${OUTPUT_DIR}/research/colors.json`, JSON.stringify(colors, null, 2));

  // ---- EXTRACT PAGE STRUCTURE ----
  const structure = await desktop.evaluate(() => {
    function getSectionInfo(el) {
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(),
        id: el.id,
        class: el.className.slice(0, 100),
        text: el.innerText?.slice(0, 100),
        rect: { top: rect.top, height: rect.height },
        children: [...el.children].map(c => ({
          tag: c.tagName.toLowerCase(),
          id: c.id,
          class: c.className.slice(0, 80),
          text: c.innerText?.slice(0, 80)
        })).slice(0, 10)
      };
    }

    // Find major sections
    const sections = [...document.querySelectorAll('main > *, section, div[class*="section"], div[class*="container"]')]
      .filter(el => el.getBoundingClientRect().height > 50)
      .map(getSectionInfo);
    
    // Fixed/overlay elements
    const fixed = [...document.querySelectorAll('*')].filter(el => {
      try { return getComputedStyle(el).position === 'fixed'; }
      catch(e) { return false; }
    }).map(el => ({
      tag: el.tagName.toLowerCase(),
      class: el.className.slice(0, 100),
      text: el.innerText?.slice(0, 80)
    }));

    return { sections, fixed };
  });
  fs.writeFileSync(`${OUTPUT_DIR}/research/page-structure.json`, JSON.stringify(structure, null, 2));

  // ---- EXTRACT ASSETS ----
  const assets = await desktop.evaluate(() => {
    const images = [...document.querySelectorAll('img')].map(img => ({
      src: img.src || img.currentSrc,
      alt: img.alt,
      width: img.naturalWidth,
      height: img.naturalHeight,
      classes: img.className.slice(0, 80)
    }));
    
    const links = [...document.querySelectorAll('link[rel*="icon"], link[rel="apple-touch-icon"]')].map(l => ({
      rel: l.rel,
      href: l.href,
      sizes: l.sizes?.toString()
    }));

    const bgImages = [...document.querySelectorAll('*')]
      .filter(el => {
        try {
          const bg = getComputedStyle(el).backgroundImage;
          return bg && bg !== 'none' && bg.includes('url');
        } catch(e) { return false; }
      })
      .map(el => ({
        url: getComputedStyle(el).backgroundImage,
        tag: el.tagName.toLowerCase(),
        class: el.className.slice(0, 60)
      })).slice(0, 20);

    return { images, favicons: links, bgImages };
  });
  fs.writeFileSync(`${OUTPUT_DIR}/research/assets.json`, JSON.stringify(assets, null, 2));

  // ---- SECTION SCREENSHOTS (desktop) ----
  const sectionSelectors = ['main', 'header', 'footer', 'nav', 'form', 'section'];
  for (const sel of sectionSelectors) {
    const elements = await desktop.$$(sel);
    for (let i = 0; i < elements.length; i++) {
      try {
        const box = await elements[i].boundingBox();
        if (box && box.height > 30 && box.width > 100) {
          await elements[i].screenshot({ path: `docs/design-references/section-${sel}-${i}.png` });
        }
      } catch(e) {}
    }
  }

  // ---- EXTRACT BUTTONS AND INTERACTIVE ELEMENTS ----
  const interactive = await desktop.evaluate(() => {
    const buttons = [...document.querySelectorAll('button, a[href], [role="button"], input[type="submit"]')].map(el => ({
      tag: el.tagName.toLowerCase(),
      text: el.innerText?.slice(0, 60) || el.getAttribute('aria-label')?.slice(0, 60),
      href: el.href || null,
      class: el.className.slice(0, 80),
      rect: el.getBoundingClientRect()
    }));
    return buttons;
  });
  fs.writeFileSync(`${OUTPUT_DIR}/research/interactive.json`, JSON.stringify(interactive, null, 2));

  console.log('=== EXTRACTION COMPLETE ===');
  console.log('Fonts:', fonts);
  console.log('Colors sample:', colors.slice(0, 10));
  console.log('Sections:', structure.sections.length);
  console.log('Fixed elements:', structure.fixed.length);
  console.log('Images:', assets.images.length);
  console.log('Buttons:', interactive.length);

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
