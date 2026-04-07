import { createBadgeSvg, createDrinkSvg, createSplashSvg } from '../utils/assets.js';

function textElement(overrides) {
  return {
    kind: 'text',
    rotation: 0,
    opacity: 1,
    fontWeight: 700,
    lineHeight: 1,
    letterSpacing: 0,
    align: 'left',
    ...overrides,
  };
}

function imageElement(overrides) {
  return {
    kind: 'image',
    rotation: 0,
    opacity: 1,
    imageFit: 'contain',
    ...overrides,
  };
}

function shapeElement(overrides) {
  return {
    kind: 'shape',
    rotation: 0,
    opacity: 1,
    borderRadius: 0,
    ...overrides,
  };
}

const matcha = createDrinkSvg('#8ca91f', '#60790d', '#d9ec8a');
const chocolate = createDrinkSvg('#7d4b38', '#2f180f', '#f0d0a4');
const cream = createDrinkSvg('#fff1d0', '#d89f33', '#ffffff');
const splashGreen = createSplashSvg('#6d8b14', '#cfe97d');
const splashBrown = createSplashSvg('#8d5a42', '#d5a280');
const badgeBlue = createBadgeSvg('#f7f3de', '#143b8a', 'MINI');

export function getTemplates() {
  return [
    {
      id: 'template-split-hero',
      name: '분할 히어로',
      headline: 'ICED MATCHA',
      description: '좌우 분할 배경과 대형 타이포, 제품 단독 컷',
      priceText: '4,800원',
      storeName: 'MATCHA STAND',
      accent: '#6b7f08',
      previewNote: '단색 배경과 가장 잘 맞는 세로 분할형',
      defaultPromptKo: '녹차 음료 포스터에 어울리는 올리브 단색 배경, 제품이나 사람 없이 색면과 미세한 질감만 구성',
      elements: [
        textElement({ id: 'store', label: '가게명', x: 73, y: 6, width: 22, height: 40, rotation: 90, text: 'MATCHA', fontSize: 56, fontWeight: 900, color: '#ffffff', align: 'center', zIndex: 8 }),
        textElement({ id: 'headline', label: '메인 타이틀', x: 7, y: 18, width: 28, height: 18, text: 'ICED\nMATCHA', fontSize: 42, fontWeight: 900, color: '#334117', zIndex: 9 }),
        textElement({ id: 'subcopy', label: '광고 문구', x: 8, y: 37, width: 32, height: 10, text: 'Drink & tasty', fontSize: 24, fontWeight: 500, color: '#9c5f1e', zIndex: 9 }),
        textElement({ id: 'description', label: '설명', x: 8, y: 49, width: 25, height: 18, text: '고소한 말차 향과 부드러운 밸런스를 가진 시즌 시그니처 메뉴', fontSize: 14, fontWeight: 500, lineHeight: 1.3, color: '#253018', zIndex: 9 }),
        textElement({ id: 'price', label: '가격', x: 8, y: 79, width: 25, height: 8, text: 'OPEN DAILY\n4,800원', fontSize: 18, fontWeight: 800, lineHeight: 1.2, color: '#9c5f1e', zIndex: 9 }),
        imageElement({ id: 'product', label: '메인 객체', x: 31, y: 18, width: 52, height: 70, imageUrl: matcha, zIndex: 10 }),
        imageElement({ id: 'splash', label: '장식 스플래시', x: 48, y: 20, width: 26, height: 18, imageUrl: splashGreen, zIndex: 7 }),
      ],
    },
    {
      id: 'template-dual-drink',
      name: '듀얼 쇼케이스',
      headline: 'CHOCO / MATCHA',
      description: '두 제품 분할 노출과 좌우 세로 텍스트 구성',
      priceText: '5,500원',
      storeName: 'DUAL BAR',
      accent: '#6d5135',
      previewNote: '비교형 광고나 시즌 2종 소개에 적합',
      defaultPromptKo: '두 가지 음료를 대비시키는 광고 배경, 제품 이미지 없이 초록과 브라운 계열 배경만 구성',
      elements: [
        textElement({ id: 'left-vertical', label: '왼쪽 세로문구', x: 4, y: 19, width: 18, height: 58, rotation: -90, text: 'CHOCOLATE', fontSize: 34, fontWeight: 900, color: '#b9815e', align: 'center', zIndex: 8 }),
        textElement({ id: 'right-vertical', label: '오른쪽 세로문구', x: 78, y: 20, width: 18, height: 58, rotation: 90, text: 'MATCHA', fontSize: 34, fontWeight: 900, color: '#9eca7a', align: 'center', zIndex: 8 }),
        imageElement({ id: 'left-product', label: '좌측 객체', x: 16, y: 30, width: 34, height: 54, imageUrl: chocolate, zIndex: 10 }),
        imageElement({ id: 'right-product', label: '우측 객체', x: 48, y: 28, width: 35, height: 56, imageUrl: matcha, zIndex: 10 }),
        imageElement({ id: 'left-splash', label: '초코 스플래시', x: 21, y: 8, width: 20, height: 20, imageUrl: splashBrown, zIndex: 7 }),
        imageElement({ id: 'right-splash', label: '말차 스플래시', x: 56, y: 9, width: 20, height: 20, imageUrl: splashGreen, zIndex: 7 }),
        textElement({ id: 'cta', label: '하단 문구', x: 33, y: 84, width: 34, height: 9, text: 'Order Here\n5,500원', fontSize: 18, fontWeight: 800, color: '#d0ae7f', align: 'center', lineHeight: 1.2, zIndex: 9 }),
      ],
    },
    {
      id: 'template-pop-board',
      name: '팝 보드',
      headline: '헤이즐넛 소프트',
      description: '대각선 분할과 스티커형 가격 강조',
      priceText: '2,800원',
      storeName: 'MINI SOFT',
      accent: '#f0b14f',
      previewNote: '행사 포스터처럼 정보량이 많은 구성',
      defaultPromptKo: '밝은 행사형 디저트 포스터 배경, 오렌지와 브라운 파스텔 색면 위주로 구성하고 객체는 생성하지 마세요',
      elements: [
        shapeElement({ id: 'diagonal', label: '대각선 면', x: -5, y: 44, width: 110, height: 34, rotation: -6, shapeCss: '#b06c5d', zIndex: 2 }),
        textElement({ id: 'headline-top', label: '상단 타이틀', x: 7, y: 8, width: 44, height: 18, rotation: -8, text: '단팥\n헤이즐넛', fontSize: 38, fontWeight: 900, color: '#55200f', zIndex: 8 }),
        textElement({ id: 'sub-title', label: '보조 타이틀', x: 38, y: 9, width: 26, height: 12, rotation: -8, text: 'Soft\nIce Cream', fontSize: 20, fontWeight: 500, color: '#fff5e6', zIndex: 8 }),
        imageElement({ id: 'left-product', label: '좌측 제품', x: 6, y: 44, width: 34, height: 39, rotation: -9, imageUrl: cream, zIndex: 9 }),
        imageElement({ id: 'right-product', label: '우측 제품', x: 58, y: 21, width: 35, height: 42, rotation: 6, imageUrl: cream, zIndex: 9 }),
        imageElement({ id: 'badge', label: '로고 배지', x: 61, y: 48, width: 18, height: 18, imageUrl: badgeBlue, zIndex: 10 }),
        textElement({ id: 'price', label: '가격 스티커', x: 43, y: 31, width: 16, height: 9, rotation: -5, text: '2,800원', fontSize: 19, fontWeight: 900, color: '#fff8ea', align: 'center', zIndex: 10 }),
        textElement({ id: 'footer-copy', label: '하단 안내', x: 59, y: 75, width: 28, height: 10, text: '소프트크림과\n베이스를 섞어 즐겨요', fontSize: 13, lineHeight: 1.3, fontWeight: 700, color: '#5a2a14', zIndex: 10 }),
      ],
    },
    {
      id: 'template-arch-premium',
      name: '아치 프리미엄',
      headline: 'VELVET LATTE',
      description: '중앙 아치 구조와 상하 정보 분리형',
      priceText: '6,200원',
      storeName: 'VELVET ROAST',
      accent: '#313a51',
      previewNote: '고급 원두, 디저트 브랜딩 소개형',
      defaultPromptKo: '프리미엄 라떼 포스터용 아치형 배경, 네이비와 크림 계열의 세련된 배경만 만들고 컵이나 사람은 넣지 마세요',
      elements: [
        shapeElement({ id: 'arch-panel', label: '아치 패널', x: 19, y: 10, width: 62, height: 72, shapeCss: 'rgba(255,255,255,0.18)', borderRadius: 999, zIndex: 2 }),
        textElement({ id: 'store-name', label: '브랜드명', x: 33, y: 11, width: 34, height: 8, text: 'VELVET ROAST', fontSize: 18, fontWeight: 800, color: '#ecf0f7', align: 'center', zIndex: 8 }),
        textElement({ id: 'headline', label: '메인 타이틀', x: 24, y: 20, width: 52, height: 15, text: 'VELVET\nLATTE', fontSize: 34, fontWeight: 900, color: '#ffffff', align: 'center', zIndex: 8 }),
        imageElement({ id: 'product', label: '메인 라떼', x: 28, y: 34, width: 45, height: 40, imageUrl: chocolate, zIndex: 10 }),
        textElement({ id: 'copy', label: '설명 문구', x: 28, y: 74, width: 45, height: 9, text: 'Signature roast with silky foam\n6,200원', fontSize: 14, fontWeight: 700, lineHeight: 1.35, color: '#f6f0e4', align: 'center', zIndex: 10 }),
        textElement({ id: 'side-copy', label: '세로 카피', x: 7, y: 18, width: 12, height: 52, rotation: -90, text: 'LIMITED BLEND', fontSize: 20, fontWeight: 900, color: '#e9d6b7', align: 'center', zIndex: 8 }),
      ],
    },
  ];
}

export function getSidebarRecommendations() {
  return [
    {
      title: '배치 보정',
      items: ['스냅 정렬', '앞뒤 순서 변경', '안전 영역 표시'],
    },
    {
      title: '텍스트 편집',
      items: ['폰트 변경', '자간/행간', '가격 강조 프리셋'],
    },
    {
      title: '배경 워크플로우',
      items: ['배경 재생성', '프롬프트 히스토리', '배경 잠금'],
    },
  ];
}
