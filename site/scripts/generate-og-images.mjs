import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import sharp from 'sharp';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fontRoot = path.join(siteRoot, 'node_modules', '@fontsource', 'noto-sans-kr', 'files');
const outputRoot = path.join(siteRoot, 'public', 'brand');

async function embeddedFont(fileName) {
  const value = await readFile(path.join(fontRoot, fileName));
  return value.toString('base64');
}

const fonts = {
  latinRegular: await embeddedFont('noto-sans-kr-latin-400-normal.woff2'),
  latinBold: await embeddedFont('noto-sans-kr-latin-700-normal.woff2'),
  koreanRegular: await embeddedFont('noto-sans-kr-korean-400-normal.woff2'),
  koreanBold: await embeddedFont('noto-sans-kr-korean-700-normal.woff2'),
};

const cards = [
  {
    locale: 'en',
    fileName: 'og-en-v2',
    legacyFileName: 'og',
    eyebrow: 'PYHOOKKIT · MICROSOFT TEAMS',
    title: 'Teams Webhook notification guide',
    subtitle: 'Start direct. Add routing only when needed.',
    steps: ['1. Posting identity', '2. Power Automate', '3. Optional router'],
  },
  {
    locale: 'ko',
    fileName: 'og-ko-v2',
    legacyFileName: 'og.ko',
    eyebrow: 'PYHOOKKIT · MICROSOFT TEAMS',
    title: 'Teams Webhook 알림 가이드',
    subtitle: '직접 전송으로 시작하고 필요할 때만 라우팅하세요.',
    steps: ['1. 게시 계정', '2. Power Automate', '3. 선택적 라우터'],
  },
];

function fontStyles() {
  return `<style>
    @font-face {
      font-family: 'Noto Latin';
      font-style: normal;
      font-weight: 400;
      src: url(data:font/woff2;base64,${fonts.latinRegular}) format('woff2');
    }
    @font-face {
      font-family: 'Noto Latin';
      font-style: normal;
      font-weight: 700;
      src: url(data:font/woff2;base64,${fonts.latinBold}) format('woff2');
    }
    @font-face {
      font-family: 'Noto Korean';
      font-style: normal;
      font-weight: 400;
      src: url(data:font/woff2;base64,${fonts.koreanRegular}) format('woff2');
    }
    @font-face {
      font-family: 'Noto Korean';
      font-style: normal;
      font-weight: 700;
      src: url(data:font/woff2;base64,${fonts.koreanBold}) format('woff2');
    }
  </style>`;
}

function svg(card) {
  const family = card.locale === 'ko' ? "'Noto Korean','Noto Latin',sans-serif" : "'Noto Latin',sans-serif";
  const titleSize = card.locale === 'ko' ? 58 : 50;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title description">
  <title id="title">${card.title}</title>
  <desc id="description">${card.subtitle}</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#11131f"/>
      <stop offset="0.52" stop-color="#20275c"/>
      <stop offset="1" stop-color="#5534a5"/>
    </linearGradient>
    <radialGradient id="glow" cx="70%" cy="15%" r="70%">
      <stop offset="0" stop-color="#6ee7f9" stop-opacity=".45"/>
      <stop offset="1" stop-color="#6ee7f9" stop-opacity="0"/>
    </radialGradient>
    ${fontStyles()}
  </defs>
  <rect width="1200" height="630" rx="36" fill="url(#background)"/>
  <rect width="1200" height="630" rx="36" fill="url(#glow)"/>
  <g transform="translate(76 72)" font-family="${family}">
    <rect width="1048" height="486" rx="30" fill="#fff" fill-opacity=".06" stroke="#fff" stroke-opacity=".16"/>
    <text x="54" y="102" fill="#b9c7ff" font-size="24" font-weight="700" letter-spacing="4">${card.eyebrow}</text>
    <text x="54" y="200" fill="#fff" font-size="${titleSize}" font-weight="700">${card.title}</text>
    <text x="54" y="270" fill="#e6e9ff" font-size="28" font-weight="400">${card.subtitle}</text>
    <g transform="translate(54 336)" font-size="21" font-weight="700">
      <rect width="280" height="82" rx="20" fill="#2563eb"/>
      <text x="140" y="52" fill="#fff" text-anchor="middle">${card.steps[0]}</text>
      <rect x="304" width="304" height="82" rx="20" fill="#9333ea"/>
      <text x="456" y="52" fill="#fff" text-anchor="middle">${card.steps[1]}</text>
      <rect x="632" width="302" height="82" rx="20" fill="#0369a1"/>
      <text x="783" y="52" fill="#fff" text-anchor="middle">${card.steps[2]}</text>
    </g>
  </g>
</svg>`;
}

for (const card of cards) {
  const source = svg(card);
  await sharp(Buffer.from(source))
    .png()
    .toFile(path.join(outputRoot, `${card.fileName}.png`));
  await sharp(Buffer.from(source))
    .png()
    .toFile(path.join(outputRoot, `${card.legacyFileName}.png`));
}

console.log(`Generated ${cards.length} localized Open Graph images with embedded fonts.`);
