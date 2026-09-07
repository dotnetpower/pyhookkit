import path from 'node:path';
import { fileURLToPath } from 'node:url';

import * as fontkit from 'fontkit';
import sharp from 'sharp';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fontRoot = path.join(siteRoot, 'node_modules', '@fontsource', 'noto-sans-kr', 'files');
const outputRoot = path.join(siteRoot, 'public', 'brand');

const fonts = {
  latinRegular: fontkit.openSync(path.join(fontRoot, 'noto-sans-kr-latin-400-normal.woff2')),
  latinBold: fontkit.openSync(path.join(fontRoot, 'noto-sans-kr-latin-700-normal.woff2')),
  koreanRegular: fontkit.openSync(path.join(fontRoot, 'noto-sans-kr-korean-400-normal.woff2')),
  koreanBold: fontkit.openSync(path.join(fontRoot, 'noto-sans-kr-korean-700-normal.woff2')),
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

function textPath({ font, text, x, y, size, fill, anchor = 'start', letterSpacing = 0 }) {
  const run = font.layout(text);
  const scale = size / font.unitsPerEm;
  const tracking = letterSpacing / scale;
  const width =
    run.positions.reduce((total, position) => total + position.xAdvance, 0) + tracking * (run.glyphs.length - 1);
  const start = anchor === 'middle' ? x - (width * scale) / 2 : x;
  let cursor = 0;
  const paths = run.glyphs
    .map((glyph, index) => {
      const position = run.positions[index];
      const transform = `translate(${cursor + position.xOffset} ${position.yOffset})`;
      cursor += position.xAdvance + tracking;
      const data = glyph.path.toSVG();
      return data ? `<path d="${data}" transform="${transform}"/>` : '';
    })
    .join('');
  return `<g fill="${fill}" transform="translate(${start} ${y}) scale(${scale} ${-scale})">${paths}</g>`;
}

function svg(card) {
  const regular = card.locale === 'ko' ? fonts.koreanRegular : fonts.latinRegular;
  const bold = card.locale === 'ko' ? fonts.koreanBold : fonts.latinBold;
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
  </defs>
  <rect width="1200" height="630" rx="36" fill="url(#background)"/>
  <rect width="1200" height="630" rx="36" fill="url(#glow)"/>
  <g transform="translate(76 72)">
    <rect width="1048" height="486" rx="30" fill="#fff" fill-opacity=".06" stroke="#fff" stroke-opacity=".16"/>
    ${textPath({ font: fonts.latinBold, text: card.eyebrow, x: 54, y: 102, size: 24, fill: '#b9c7ff', letterSpacing: 4 })}
    ${textPath({ font: bold, text: card.title, x: 54, y: 200, size: titleSize, fill: '#ffffff' })}
    ${textPath({ font: regular, text: card.subtitle, x: 54, y: 270, size: 28, fill: '#e6e9ff' })}
    <g transform="translate(54 336)">
      <rect width="280" height="82" rx="20" fill="#2563eb"/>
      ${textPath({ font: bold, text: card.steps[0], x: 140, y: 52, size: 21, fill: '#ffffff', anchor: 'middle' })}
      <rect x="304" width="304" height="82" rx="20" fill="#9333ea"/>
      ${textPath({ font: bold, text: card.steps[1], x: 456, y: 52, size: 21, fill: '#ffffff', anchor: 'middle' })}
      <rect x="632" width="302" height="82" rx="20" fill="#0369a1"/>
      ${textPath({ font: bold, text: card.steps[2], x: 783, y: 52, size: 21, fill: '#ffffff', anchor: 'middle' })}
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
