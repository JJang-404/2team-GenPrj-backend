import { translatePromptWithOpenAI } from './externalAiService.js';

export function translatePromptToEnglishHeuristic(promptKo, backgroundMode) {
  const lower = promptKo.trim();

  const subject = [
    lower.includes('말차') || lower.includes('녹차') ? 'matcha drink advertisement poster background' : '',
    lower.includes('라떼') ? 'latte campaign backdrop' : '',
    lower.includes('초코') || lower.includes('초콜릿') ? 'chocolate beverage poster background' : '',
    lower.includes('아이스크림') ? 'dessert promotion background' : '',
    lower.includes('커피') ? 'coffee advertising background' : '',
  ]
    .filter(Boolean)
    .join(', ');

  const mood = [
    lower.includes('세련') || lower.includes('고급') ? 'refined premium mood' : '',
    lower.includes('밝') ? 'bright and clean mood' : '',
    lower.includes('레트로') ? 'retro graphic mood' : '',
    lower.includes('파스텔') ? 'soft pastel tones' : '',
    lower.includes('단색') ? 'bold solid color blocking' : '',
    lower.includes('그라데이션') ? 'smooth layered gradients' : '',
    lower.includes('질감') ? 'subtle paper-like texture' : '',
    lower.includes('분할') || lower.includes('블록') ? 'split composition and geometric panels' : '',
    lower.includes('스튜디오') ? 'commercial studio lighting' : '',
    lower.includes('햇살') ? 'warm directional sunlight' : '',
  ]
    .filter(Boolean)
    .join(', ');

  const modeHint = {
    solid: 'clean solid-color composition with bold panels',
    gradient: 'smooth gradient backdrop with soft depth',
    pastel: 'airy pastel backdrop with subtle texture',
    'ai-image': 'photorealistic advertising background with cinematic lighting, natural materials, realistic shadows, and depth',
  }[backgroundMode];

  return [
    subject || 'advertising poster background',
    mood || 'photoreal commercial backdrop',
    modeHint,
    'background only',
    'preserve the uploaded object silhouette and text layout',
    'photorealistic',
    'commercial beverage photography',
    'real environment',
    'no illustration',
    'no vector graphics',
    'no graphic splash',
    'no floating cream',
    'no extra product',
    'no cup',
    'no bottle',
    'no people',
    'no hand',
    'no text',
    'no logo',
  ].join(', ');
}

export async function translatePromptToEnglish(promptKo, backgroundMode, guideSummary = '') {
  try {
    const translated = await translatePromptWithOpenAI(promptKo, backgroundMode, guideSummary);
    if (translated) {
      return translated;
    }
  } catch (_error) {
    // OpenAI 미설정 또는 일시 실패 시 휴리스틱 프롬프트로 폴백합니다.
  }

  return translatePromptToEnglishHeuristic(promptKo, backgroundMode);
}

export function buildNegativePrompt() {
  return 'product, cup, bottle, glass, food, person, hand, typography, logo, watermark, label, menu item, duplicate object, extra packaging, extra drink, illustration, vector art, graphic splash, cream splash, floating toppings, floating garnish';
}
