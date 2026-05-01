import { mkdir, readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = fileURLToPath(new URL('..', import.meta.url));
const outputPath = join(root, 'public', 'assets', 'social', 'cbbs-social-card.png');
const logoPath = join(root, 'public', 'assets', 'brand', 'logo-icon.svg');
const logoData = await readFile(logoPath);
const logoHref = `data:image/svg+xml;base64,${logoData.toString('base64')}`;

const svg = `<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <rect width="1200" height="630" fill="#08111f"/>
  <rect x="760" y="0" width="440" height="630" fill="#0c2138"/>
  <path d="M72 478 C270 392 376 532 574 442 C684 392 718 336 794 290 C914 218 1016 226 1136 154" fill="none" stroke="#00b6d8" stroke-width="4" stroke-opacity="0.78"/>
  <path d="M778 500 L1138 500" stroke="#f2cc8f" stroke-width="2" stroke-opacity="0.72"/>
  <path d="M820 104 h246 a26 26 0 0 1 26 26 v132 a26 26 0 0 1 -26 26 h-246 a26 26 0 0 1 -26 -26 v-132 a26 26 0 0 1 26 -26 z" fill="#08111f" stroke="#18435d" stroke-width="2"/>
  <path d="M842 144 h204 M842 190 h204 M842 236 h142" stroke="#1c7c71" stroke-width="3" stroke-linecap="round" stroke-opacity="0.8"/>
  <path d="M858 164 h76 M858 210 h132 M858 256 h72" stroke="#7af0fb" stroke-width="5" stroke-linecap="round" stroke-opacity="0.8"/>
  <image href="${logoHref}" x="84" y="76" width="92" height="92"/>
  <text x="200" y="116" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="800" fill="#7af0fb" letter-spacing="4">CBBS / CLARTK BBS</text>
  <text x="82" y="236" font-family="Arial, Helvetica, sans-serif" font-size="68" font-weight="900" fill="#f6fbff">Off-grid field</text>
  <text x="82" y="312" font-family="Arial, Helvetica, sans-serif" font-size="68" font-weight="900" fill="#f6fbff">bulletin boards</text>
  <text x="82" y="388" font-family="Arial, Helvetica, sans-serif" font-size="68" font-weight="900" fill="#f6fbff">for field teams</text>
  <text x="86" y="462" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="600" fill="#cfe1e6">Records, mesh paths, operator consoles,</text>
  <text x="86" y="506" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="600" fill="#cfe1e6">and Nextion/P070 display surfaces.</text>
  <rect x="86" y="528" width="304" height="48" rx="8" fill="#00b6d8"/>
  <text x="112" y="560" font-family="Arial, Helvetica, sans-serif" font-size="23" font-weight="900" fill="#041217">cyberpivots.github.io</text>
  <circle cx="922" cy="408" r="70" fill="none" stroke="#00b6d8" stroke-width="6" stroke-opacity="0.78"/>
  <circle cx="922" cy="408" r="15" fill="#7af0fb"/>
  <circle cx="856" cy="385" r="11" fill="#f2cc8f"/>
  <circle cx="984" cy="366" r="11" fill="#f2cc8f"/>
  <circle cx="984" cy="456" r="11" fill="#f2cc8f"/>
  <path d="M868 388 L908 404 M936 398 L974 372 M936 416 L974 450" stroke="#7af0fb" stroke-width="4" stroke-linecap="round"/>
</svg>`;

await mkdir(dirname(outputPath), { recursive: true });
await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toFile(outputPath);

console.log(`Generated ${outputPath}`);
