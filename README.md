# 에디터 지원 백엔드 (Node.js)

프론트엔드(`Frontend/`)의 2단계 에디터에 템플릿, 배경 생성, AI 연동 기능을 제공하는 Express 서버입니다.

---

## 폴더 구조

```
backend/
├── src/
│   ├── server.js                    ← 서버 진입점 (포트 4000)
│   ├── routes/
│   │   └── editorRoutes.js          ← API 라우터
│   └── services/
│       ├── templateService.js       ← 템플릿 4종 정의 및 사이드바 추천
│       ├── backgroundService.js     ← 배경 후보 생성 (CSS + AI 이미지)
│       ├── promptService.js         ← 한→영 프롬프트 번역
│       ├── externalAiService.js     ← HuggingFace / OpenAI API 연동
│       ├── bridgeService.js         ← 페이지 간 데이터 브리지 (토큰 방식)
│       └── utils/assets.js          ← SVG 배경 이미지 생성 유틸
├── scripts/
│   └── apply_alpha_mask.py          ← 배경 제거 마스크 합성 (Python 필요)
├── package.json
└── README1.md                       ← 이 파일
```

---

## 실행 방법

### 1) 환경변수 설정

프로젝트 루트(backend/ 상위 폴더)에 `.env` 파일을 만듭니다.

```
# 필수 항목 없음 — API 키 없어도 핵심 기능 동작
PORT=4000
HOST=127.0.0.1

# AI 기능 사용 시 필요 (선택)
HF_TOKEN=hf_your_token_here
OPENAI_API_KEY=sk-your_key_here
```

### 2) 패키지 설치 및 실행

```bash
cd backend
npm install
npm run dev      # 개발 모드 (파일 변경 감지)
# 또는
npm start        # 일반 실행
```

서버 실행 확인: http://localhost:4000/api/health 접속 시 `{"ok":true}` 반환

---

## API 목록

| 메서드 | 경로 | 설명 | 키 필요 |
|--------|------|------|---------|
| GET | `/api/health` | 서버 상태 확인 | 없음 |
| GET | `/api/editor/bootstrap` | 템플릿 4종 + 사이드바 추천 목록 반환 | 없음 |
| POST | `/api/backgrounds/generate` | 배경 후보 생성 (단색/그라데이션/다중색/AI) | AI 모드만 HF_TOKEN |
| POST | `/api/images/remove-background` | 제품 사진 배경 제거 | HF_TOKEN |
| POST | `/api/prompts/translate` | 한국어 프롬프트 → 영어 번역 | OPENAI_API_KEY (없으면 기본 번역) |
| POST | `/api/bridge/editing` | 페이지 간 데이터 브리지 토큰 생성 | 없음 |
| GET | `/api/bridge/editing/:token` | 브리지 토큰으로 데이터 조회 (1회용) | 없음 |

---

## 핵심 서비스 설명

### templateService.js

백엔드가 반환하는 템플릿 4종을 정의합니다. 각 템플릿은 텍스트/이미지 요소의 초기 위치와 스타일을 포함합니다.

| 템플릿 ID | 이름 | 특징 |
|-----------|------|------|
| `template-split-hero` | 분할 히어로 | 좌우 분할 배경, 제품 단독 컷 |
| `template-dual-drink` | 듀얼 쇼케이스 | 두 제품 비교 노출 |
| `template-pop-board` | 팝 보드 | 대각선 분할, 행사형 구성 |
| `template-arch-premium` | 아치 프리미엄 | 아치 구조, 고급 브랜딩 |

1단계에서 선택한 드래프트 인덱스(0~3)가 이 템플릿 순서와 대응합니다.

### backgroundService.js

배경 생성 요청을 처리합니다.

- **단색/그라데이션/다중색**: CSS로 즉시 생성, 백엔드 AI 호출 없음.
- **AI 이미지 모드**: HuggingFace `image-to-image` API로 실제 이미지 생성 (`HF_TOKEN` 필요).
- 프롬프트에 `BG_SOLID(#hex)`, `BG_GRADIENT(#hex,#hex)`, `BG_MULTI(#hex,#hex)` 토큰이 포함되면 해당 색상으로 배경을 생성합니다.

### promptService.js

한국어 프롬프트를 영어로 번역합니다.

- `OPENAI_API_KEY`가 있으면 GPT 모델로 번역.
- 없으면 키워드 기반 휴리스틱 번역으로 자동 대체 (서버 오류 없이 동작).

### externalAiService.js

HuggingFace 및 OpenAI API를 직접 호출하는 모듈입니다.

- 배경 제거: HuggingFace `imageSegmentation` → Python 스크립트(`apply_alpha_mask.py`)로 알파 채널 합성.
- 배경 생성: HuggingFace `imageToImage` → `stabilityai/stable-diffusion-3.5-medium` 모델 사용.

### bridgeService.js

두 페이지 간 데이터를 토큰으로 전달하는 서비스입니다. 현재 SPA 통합으로 React State를 사용하므로 실제로는 사용되지 않지만, 향후 분리 배포 시 활용 가능합니다. 토큰 유효 시간은 10분입니다.

---

## 배경 제거 기능 설정 (선택)

배경 제거(`/api/images/remove-background`)는 Python 스크립트를 추가로 사용합니다.

```bash
# 프로젝트 루트에서 Python 가상환경 생성
python -m venv .venv
.venv/Scripts/activate    # Windows
pip install Pillow
```

Python이 없거나 가상환경이 없으면 배경 제거 API 호출 시 오류가 발생합니다. 해당 기능을 사용하지 않는다면 무시해도 됩니다.

---

## 프론트엔드와의 연동 방식

프론트엔드(`Frontend/`)는 Vite 개발 서버의 프록시를 통해 이 백엔드와 통신합니다.

```
브라우저 (localhost:5174)
    ↓  /api/... 요청
Vite 프록시
    ↓  자동 전달
이 백엔드 (localhost:4000)
```

`Frontend/vite.config.ts`에 다음과 같이 설정되어 있습니다:

```ts
server: {
  proxy: {
    '/api': 'http://localhost:4000',
  },
}
```

프론트엔드 코드에서 `/api/...`로 fetch 하면 자동으로 이 백엔드로 전달됩니다.

---

## 의존 패키지

| 패키지 | 용도 |
|--------|------|
| `express` | HTTP 서버 |
| `cors` | 크로스 오리진 요청 허용 |
| `dotenv` | 환경변수 로드 |
| `@huggingface/inference` | HuggingFace API 클라이언트 |
