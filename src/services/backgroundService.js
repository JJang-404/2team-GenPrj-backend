import { createBackgroundSvg } from '../utils/assets.js';
import { generateImageToImageVariants } from './externalAiService.js';
import { buildNegativePrompt, translatePromptToEnglish } from './promptService.js';

const palettes = {
  solid: [
    { name: '분할 올리브', colors: ['#f8f4ee', '#6f7f09', '#ffffff'], variant: 'split', note: '참고 이미지처럼 좌우 면 분할' },
    { name: '브라운-라임', colors: ['#5f452c', '#c6ff66', '#91ad46'], variant: 'split', note: '강한 대비의 투톤 배경' },
    { name: '코코아 블록', colors: ['#f3e4d4', '#8e5e43', '#e3c68b'], variant: 'arch', note: '매장 브랜딩용 단색 블록' },
    { name: '네이비 크림', colors: ['#1f2a44', '#e6ddce', '#f7f2ec'], variant: 'diagonal', note: '프리미엄 인쇄물 톤' },
  ],
  gradient: [
    { name: '그린 미스트', colors: ['#eef5d9', '#7ca126', '#304f13'], variant: 'halo', note: '말차 포스터용 깊이감' },
    { name: '멜팅 카카오', colors: ['#f4d6c0', '#8b563d', '#341810'], variant: 'halo', note: '초콜릿/커피 계열에 적합' },
    { name: '크림 선셋', colors: ['#fff2d1', '#f4b157', '#ba6d61'], variant: 'diagonal', note: '디저트 행사 분위기' },
    { name: '슬레이트 골드', colors: ['#e7e2db', '#53627c', '#b69058'], variant: 'arch', note: '고급 라떼 브랜드용' },
  ],
  pastel: [
    { name: '버터 피치', colors: ['#fff1d4', '#f6be9a', '#f09b8c', '#c93f33'], variant: 'collage', note: '과일 포스터형 다중색 배치' },
    { name: '민트 밀크', colors: ['#edf8ec', '#c4e8d1', '#9fd3be', '#2f7b5e'], variant: 'ribbon', note: '브랜드 리본형 다중색 구성' },
    { name: '라일락 크림', colors: ['#f7f0ff', '#decdf8', '#bcaedb', '#8e62d9'], variant: 'burst', note: '강한 포인트의 레이어드 배치' },
    { name: '코튼 샌드', colors: ['#f6efe6', '#dbcfc0', '#baa98d', '#8c6648'], variant: 'collage', note: '빈티지 포스터형 다중색 면 구성' },
  ],
  'ai-image': [
    { name: 'AI 카페 스튜디오', colors: ['#1f120e', '#6d4a2b', '#3d2317'], variant: 'cafe', note: '어두운 카페 조명과 우드 테이블 무드', grain: true },
    { name: 'AI 골든 밸리', colors: ['#88a8ad', '#f4d986', '#5f7d45'], variant: 'landscape', note: '산맥과 들판이 있는 시네마틱 배경', grain: true },
    { name: 'AI 프리미엄 스튜디오', colors: ['#140f0c', '#9b7d56', '#3e2415'], variant: 'studio', note: '광고 촬영 세트 같은 집중 조명', grain: true },
    { name: 'AI 새벽 카페 창가', colors: ['#263845', '#d0c0a0', '#6b4d32'], variant: 'cafe', note: '창가 햇살과 짙은 실내 그림자', grain: true },
  ],
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function hexToRgb(hex) {
  const normalized = hex.replace('#', '').trim();
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return null;
  return {
    r: Number.parseInt(normalized.slice(0, 2), 16),
    g: Number.parseInt(normalized.slice(2, 4), 16),
    b: Number.parseInt(normalized.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }) {
  return `#${[r, g, b].map((value) => clamp(Math.round(value), 0, 255).toString(16).padStart(2, '0')).join('')}`;
}

function mixHex(baseHex, targetHex, ratio) {
  const base = hexToRgb(baseHex);
  const target = hexToRgb(targetHex);
  if (!base || !target) return baseHex;
  return rgbToHex({
    r: base.r + (target.r - base.r) * ratio,
    g: base.g + (target.g - base.g) * ratio,
    b: base.b + (target.b - base.b) * ratio,
  });
}

function adjustHex(hex, amount) {
  return amount >= 0 ? mixHex(hex, '#ffffff', amount) : mixHex(hex, '#000000', Math.abs(amount));
}

function extractBackgroundToken(promptKo = '', type) {
  const matched = promptKo.match(new RegExp(`BG_${type}\\(([^)]*)\\)`));
  if (!matched) return null;
  return matched[1]
    .split(',')
    .map((item) => item.trim())
    .filter((item) => /^#[0-9a-fA-F]{6}$/.test(item) || /^#[0-9a-fA-F]{3}$/.test(item));
}

function parseGuideSummary(guideSummary = '') {
  const brandColorMatch = /brand color:\s*(#[0-9a-fA-F]{6})/.exec(guideSummary);
  const templateMatch = /template:\s*([^|]+)/.exec(guideSummary);
  const productMatches = [...guideSummary.matchAll(/product \d+:/g)];

  return {
    brandColor: brandColorMatch?.[1] ?? null,
    templateName: templateMatch?.[1]?.trim() ?? '',
    productCount: productMatches.length,
  };
}

function inferFlavor(promptKo = '', templateId = '') {
  const lower = `${promptKo} ${templateId}`.toLowerCase();
  if (lower.includes('말차') || lower.includes('녹차') || lower.includes('matcha')) return 'matcha';
  if (lower.includes('초코') || lower.includes('초콜릿') || lower.includes('choco') || lower.includes('chocolate')) return 'chocolate';
  if (lower.includes('커피') || lower.includes('coffee') || lower.includes('라떼') || lower.includes('latte')) return 'coffee';
  if (lower.includes('아이스크림') || lower.includes('cream')) return 'dessert';
  return 'neutral';
}

function getRequestedColors(promptKo = '') {
  const solid = extractBackgroundToken(promptKo, 'SOLID');
  const gradient = extractBackgroundToken(promptKo, 'GRADIENT');
  const multi = extractBackgroundToken(promptKo, 'MULTI');
  return { solid, gradient, multi };
}

function buildRequestedPalettes(backgroundMode, requestedColors) {
  if (backgroundMode === 'solid' && requestedColors.solid?.[0]) {
    const base = requestedColors.solid[0];
    return [
      {
        name: '사용자 단색 1',
        colors: [base, base, base],
        variant: 'split',
        note: `사용자 지정 단색 ${base}`,
        cssBackground: base,
      },
      {
        name: '사용자 단색 2',
        colors: [base, base, base],
        variant: 'arch',
        note: `사용자 지정 단색 ${base}`,
        cssBackground: base,
      },
      {
        name: '사용자 단색 3',
        colors: [base, base, base],
        variant: 'diagonal',
        note: `사용자 지정 단색 ${base}`,
        cssBackground: base,
      },
      {
        name: '사용자 단색 4',
        colors: [base, base, base],
        variant: 'split',
        note: `사용자 지정 단색 ${base}`,
        cssBackground: base,
      },
    ];
  }

  if (backgroundMode === 'gradient' && requestedColors.gradient?.length >= 2) {
    const stops = requestedColors.gradient;
    const first = stops[0];
    const last = stops[stops.length - 1];
    const angled = stops.join(', ');
    const reverse = [...stops].reverse().join(', ');
    const vertical = stops.join(', ');
    return [
      {
        name: '사용자 그라데이션 1',
        colors: stops,
        variant: 'halo',
        note: `사용자 지정 그라데이션 ${stops.join(' → ')}`,
        cssBackground: `linear-gradient(135deg, ${angled})`,
      },
      {
        name: '사용자 그라데이션 2',
        colors: stops,
        variant: 'arch',
        note: `사용자 지정 그라데이션 ${stops.join(' → ')}`,
        cssBackground: `linear-gradient(180deg, ${vertical})`,
      },
      {
        name: '사용자 그라데이션 3',
        colors: [first, last, last],
        variant: 'split',
        note: `사용자 지정 그라데이션 ${stops.join(' → ')}`,
        cssBackground: `linear-gradient(90deg, ${angled})`,
      },
      {
        name: '사용자 그라데이션 4',
        colors: [last, first, first],
        variant: 'diagonal',
        note: `사용자 지정 그라데이션 ${stops.join(' → ')}`,
        cssBackground: `linear-gradient(45deg, ${reverse})`,
      },
    ];
  }

  if (backgroundMode === 'pastel' && requestedColors.multi?.length >= 2) {
    const colors = requestedColors.multi;
    const fallback = colors[colors.length - 1];
    const c1 = colors[0];
    const c2 = colors[1] ?? fallback;
    const c3 = colors[2] ?? fallback;
    const c4 = colors[3] ?? c2;
    return [
      {
        name: '사용자 다중색 1',
        colors: [c1, c2, c3, c4],
        variant: 'collage',
        note: `사용자 지정 다중색 ${colors.join(', ')}`,
      },
      {
        name: '사용자 다중색 2',
        colors: [c2, c1, c3, c4],
        variant: 'ribbon',
        note: `사용자 지정 다중색 ${colors.join(', ')}`,
      },
      {
        name: '사용자 다중색 3',
        colors: [c1, c3, c2, c4],
        variant: 'burst',
        note: `사용자 지정 다중색 ${colors.join(', ')}`,
      },
      {
        name: '사용자 다중색 4',
        colors: [c4, c1, c2, c3],
        variant: 'collage',
        note: `사용자 지정 다중색 ${colors.join(', ')}`,
      },
    ];
  }

  return null;
}

function makeFlavorAccent(flavor, fallback) {
  const presets = {
    matcha: '#6f8f18',
    chocolate: '#7a4a34',
    coffee: '#6b4b32',
    dessert: '#f0b35d',
    neutral: fallback || '#64748b',
  };
  return presets[flavor] ?? fallback ?? '#64748b';
}

function personalizePalette(backgroundMode, palette, context, index) {
  const baseAccent = context.brandColor || makeFlavorAccent(context.flavor, palette.colors[1]);
  const isMultiProduct = context.productCount >= 2;
  const templateBias =
    context.templateId === 'template-dual-drink' ? 'split'
      : context.templateId === 'template-arch-premium' ? 'arch'
      : palette.variant;

  const accentA = backgroundMode === 'solid' ? adjustHex(baseAccent, 0.3) : adjustHex(baseAccent, 0.15);
  const accentB = backgroundMode === 'pastel' ? adjustHex(baseAccent, 0.58) : adjustHex(baseAccent, -0.12);
  const accentC = backgroundMode === 'gradient' ? adjustHex(baseAccent, -0.34) : adjustHex(baseAccent, 0.74);

  const flavorNames = {
    matcha: '말차',
    chocolate: '초코',
    coffee: '커피',
    dessert: '디저트',
    neutral: '브랜드',
  };

  const countNames = {
    0: '기본',
    1: '싱글',
    2: '듀얼',
    3: '멀티',
  };

  let colors = palette.colors;
  if (backgroundMode === 'solid') {
    colors = isMultiProduct
      ? [adjustHex(accentA, 0.72), accentB, adjustHex(accentB, 0.28)]
      : [adjustHex(accentA, 0.88), accentA, adjustHex(accentA, 0.62)];
  }
  if (backgroundMode === 'gradient') {
    colors = [adjustHex(accentA, 0.78), accentA, accentC];
  }
  if (backgroundMode === 'pastel') {
    colors = [adjustHex(accentA, 0.9), adjustHex(accentB, 0.16), adjustHex(accentC, 0.58)];
  }

  if (backgroundMode === 'solid' && context.requestedColors.solid?.[0]) {
    const base = context.requestedColors.solid[0];
    colors = [base, base, base];
  }
  if (backgroundMode === 'gradient' && context.requestedColors.gradient?.length >= 2) {
    const requested = context.requestedColors.gradient;
    colors = requested;
  }
  if (backgroundMode === 'pastel' && context.requestedColors.multi?.length >= 2) {
    const requested = context.requestedColors.multi;
    const first = requested[0];
    const second = requested[1] ?? requested[0];
    const third = requested[2] ?? adjustHex(second, 0.18);
    colors = [first, second, third];
  }

  const variant = isMultiProduct ? templateBias : palette.variant;
  const countLabel = countNames[Math.min(context.productCount, 3)] ?? '멀티';
  const flavorLabel = flavorNames[context.flavor] ?? '브랜드';

  return {
    ...palette,
    colors,
    variant,
    name: `${countLabel} ${flavorLabel} ${palette.name}`,
    note: `${palette.note} | ${context.productCount || 1}개 제품, ${context.brandColor ?? '기본'} 기준으로 조정`,
    grain: palette.grain,
  };
}

function createCandidate(backgroundMode, palette, index, translatedPrompt, negativePrompt, guideSummary, noteSuffix = '') {
  const cssBackground =
    palette.cssBackground
      ? palette.cssBackground
      : backgroundMode === 'solid'
      ? palette.colors[1]
      : backgroundMode === 'pastel'
        ? '#f8fafc'
        : `linear-gradient(135deg, ${palette.colors.join(', ')})`;

  return {
    id: `${backgroundMode}-${index + 1}`,
    name: palette.name,
    mode: backgroundMode,
    cssBackground,
    imageUrl: createBackgroundSvg(palette),
    note: [palette.note, guideSummary ? `layout-guided: ${guideSummary}` : 'guide image applied', noteSuffix]
      .filter(Boolean)
      .join(' | '),
    translatedPrompt,
    negativePrompt,
  };
}

export async function generateBackgroundCandidates({ templateId, backgroundMode, promptKo, guideImage, guideSummary }) {
  const translatedPrompt = await translatePromptToEnglish(promptKo, backgroundMode, guideSummary);
  const negativePrompt = buildNegativePrompt();
  const parsedGuide = parseGuideSummary(guideSummary);
  const context = {
    templateId,
    brandColor: parsedGuide.brandColor,
    productCount: parsedGuide.productCount,
    flavor: inferFlavor(promptKo, templateId),
    requestedColors: getRequestedColors(promptKo),
  };
  const requestedVariants = buildRequestedPalettes(backgroundMode, context.requestedColors);
  const variants = (requestedVariants ?? (palettes[backgroundMode] ?? palettes.solid).map((palette, index) =>
    personalizePalette(backgroundMode, palette, context, index)
  ));

  if (backgroundMode === 'ai-image' && guideImage) {
    try {
      const generated = await generateImageToImageVariants({
        guideImage,
        translatedPrompt,
        negativePrompt,
        count: 4,
      });

      return {
        translatedPrompt,
        negativePrompt,
        guideApplied: true,
        candidates: generated.map((item, index) => ({
          id: `ai-image-live-${index + 1}`,
          name: item.name,
          mode: 'ai-image',
          cssBackground: 'linear-gradient(135deg, #111827, #374151)',
          imageUrl: item.imageUrl,
          note: `HF image-to-image result | ${item.note}`,
          translatedPrompt,
          negativePrompt,
        })),
      };
    } catch (error) {
      return {
        translatedPrompt,
        negativePrompt,
        guideApplied: true,
        candidates: variants.map((palette, index) =>
          createCandidate(
            backgroundMode,
            { ...palette, name: `${palette.name} (실사 생성 실패 폴백)` },
            index,
            translatedPrompt,
            negativePrompt,
            guideSummary,
            `실제 HF img2img 생성 실패. 현재는 그래픽 폴백입니다: ${error instanceof Error ? error.message : 'unknown error'}`
          )
        ),
      };
    }
  }

  return {
    translatedPrompt,
    negativePrompt,
    guideApplied: Boolean(guideImage),
    candidates: variants.map((palette, index) =>
      createCandidate(backgroundMode, palette, index, translatedPrompt, negativePrompt, guideSummary)
    ),
  };
}
