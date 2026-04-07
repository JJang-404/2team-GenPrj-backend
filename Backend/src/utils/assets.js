function svgData(svg) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export function createDrinkSvg(primary, secondary, accent) {
  return svgData(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 500">
      <defs>
        <linearGradient id="drink" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${primary}" />
          <stop offset="100%" stop-color="${secondary}" />
        </linearGradient>
      </defs>
      <path d="M90 20 L230 20 L260 390 Q265 445 210 465 L130 485 Q85 475 70 412 Z" fill="rgba(255,255,255,0.92)" stroke="rgba(255,255,255,0.55)" stroke-width="6"/>
      <path d="M98 56 L222 56 L242 378 Q246 422 197 440 L134 455 Q94 446 84 400 Z" fill="url(#drink)" />
      <ellipse cx="166" cy="57" rx="72" ry="20" fill="rgba(255,255,255,0.44)" />
      <ellipse cx="182" cy="118" rx="30" ry="10" fill="rgba(255,255,255,0.14)" />
      <ellipse cx="144" cy="220" rx="28" ry="12" fill="rgba(255,255,255,0.1)" />
      <ellipse cx="182" cy="324" rx="36" ry="14" fill="rgba(0,0,0,0.18)" />
      <path d="M110 0 L214 0 L190 36 L124 36 Z" fill="${accent}" opacity="0.9" />
    </svg>
  `);
}

export function createSplashSvg(primary, secondary) {
  return svgData(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">
      <defs>
        <radialGradient id="splash" cx="50%" cy="40%" r="65%">
          <stop offset="0%" stop-color="${secondary}" />
          <stop offset="100%" stop-color="${primary}" />
        </radialGradient>
      </defs>
      <path d="M96 20 C122 40 116 80 146 84 C188 89 219 128 203 164 C189 194 142 212 98 209 C54 206 18 176 21 135 C23 98 55 86 67 62 C79 38 71 12 96 20 Z" fill="url(#splash)" />
    </svg>
  `);
}

export function createBadgeSvg(fill, stroke, text) {
  return svgData(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180">
      <circle cx="90" cy="90" r="76" fill="${fill}" stroke="${stroke}" stroke-width="8"/>
      <text x="90" y="86" text-anchor="middle" font-size="28" font-weight="800" fill="${stroke}" font-family="Arial">${text}</text>
      <text x="90" y="118" text-anchor="middle" font-size="20" font-weight="700" fill="${stroke}" font-family="Arial">SPECIAL</text>
    </svg>
  `);
}

export function createBackgroundSvg({ colors, variant, grain = false }) {
  const [c1, c2, c3, c4 = c3 ?? c2] = colors;
  const shapes = {
    split: `<rect width="50%" height="100%" fill="${c1}"/><rect x="50%" width="50%" height="100%" fill="${c2}"/>`,
    diagonal: `<path d="M0 0 H1080 V400 L0 820 Z" fill="${c1}"/><path d="M1080 0 V1920 H0 V910 Z" fill="${c2}"/>`,
    halo: `<rect width="100%" height="100%" fill="${c1}"/><circle cx="780" cy="420" r="280" fill="${c2}" opacity="0.45"/><circle cx="240" cy="1450" r="220" fill="${c3}" opacity="0.38"/>`,
    arch: `<rect width="100%" height="100%" fill="${c1}"/><path d="M150 1920 V920 C150 640 330 420 540 420 C750 420 930 640 930 920 V1920 Z" fill="${c2}"/><circle cx="540" cy="1180" r="210" fill="${c3}" opacity="0.24"/>`,
    collage: `<rect width="100%" height="100%" fill="${c1}"/><path d="M0 0 H1080 V280 L620 820 H0 Z" fill="${c2}"/><path d="M1080 300 V1920 H460 L720 980 Z" fill="${c3}"/><rect x="720" y="60" width="260" height="260" rx="36" fill="${c4}"/><rect x="90" y="1360" width="280" height="280" rx="140" fill="${c2}"/>`,
    ribbon: `<rect width="100%" height="100%" fill="${c1}"/><path d="M0 180 H1080 V470 H0 Z" fill="${c2}"/><path d="M0 720 H1080 V1060 H0 Z" fill="${c3}"/><path d="M0 1320 H1080 V1700 H0 Z" fill="${c4}"/>`,
    burst: `<rect width="100%" height="100%" fill="${c1}"/><path d="M540 960 L540 0 L1080 0 Z" fill="${c2}"/><path d="M540 960 L1080 0 L1080 1920 Z" fill="${c3}"/><path d="M540 960 L1080 1920 L0 1920 Z" fill="${c4}"/><path d="M540 960 L0 1920 L0 0 Z" fill="${c2}"/><circle cx="540" cy="960" r="150" fill="${c1}"/>`,
    cafe: `<defs><radialGradient id="g1" cx="30%" cy="18%" r="58%"><stop offset="0%" stop-color="${c2}" stop-opacity="0.95"/><stop offset="48%" stop-color="${c1}" stop-opacity="0.42"/><stop offset="100%" stop-color="${c1}" stop-opacity="0"/></radialGradient><linearGradient id="desk" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${c2}"/><stop offset="100%" stop-color="${c3}"/></linearGradient></defs><rect width="100%" height="100%" fill="${c1}"/><rect y="1440" width="100%" height="480" fill="url(#desk)"/><rect y="1380" width="100%" height="18" fill="rgba(255,255,255,0.12)"/><circle cx="300" cy="320" r="480" fill="url(#g1)"/><rect x="780" y="-40" width="160" height="760" rx="80" fill="rgba(255,255,255,0.06)" transform="rotate(15 860 340)"/>`,
    landscape: `<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${c1}"/><stop offset="60%" stop-color="${c2}"/><stop offset="100%" stop-color="${c3}"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#sky)"/><circle cx="540" cy="430" r="180" fill="rgba(255,245,214,0.8)"/><path d="M0 1220 C110 1040 220 930 380 900 C470 884 560 924 620 988 C728 842 854 816 1080 1110 V1920 H0 Z" fill="rgba(63,87,59,0.84)"/><path d="M0 1380 C120 1260 252 1170 360 1160 C468 1150 540 1208 622 1310 C712 1202 858 1120 1080 1300 V1920 H0 Z" fill="rgba(23,58,38,0.88)"/><rect y="1470" width="100%" height="450" fill="rgba(129,92,58,0.88)"/>`,
    studio: `<defs><radialGradient id="spot" cx="50%" cy="28%" r="52%"><stop offset="0%" stop-color="${c2}" stop-opacity="0.95"/><stop offset="44%" stop-color="${c1}" stop-opacity="0.45"/><stop offset="100%" stop-color="${c1}" stop-opacity="0"/></radialGradient><linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${c3}" stop-opacity="0.9"/><stop offset="100%" stop-color="${c1}" stop-opacity="0.96"/></linearGradient></defs><rect width="100%" height="100%" fill="${c1}"/><circle cx="540" cy="520" r="520" fill="url(#spot)"/><path d="M0 1380 C190 1280 340 1250 540 1250 C740 1250 900 1280 1080 1380 V1920 H0 Z" fill="url(#floor)"/><ellipse cx="540" cy="1440" rx="280" ry="60" fill="rgba(255,255,255,0.08)"/>`,
  };

  return svgData(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920">
      ${shapes[variant]}
      ${grain ? `<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" opacity="0.08" filter="url(#n)"/>` : ''}
    </svg>
  `);
}
