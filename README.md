# AI 광고 이미지 생성기 — 아키텍처 문서

## 전체 흐름

```
사용자 입력 (CLI or API)
  가게명 / 상품명(한국어) / 가격 / 전화번호 / 스타일 / 광고문구
          │
          ▼
  ┌─────────────────────────────────────────────────────┐
  │  [0단계] 번역 레이어                                 │
  │  deep-translator (Google Translate)                  │
  │  "아이스 아메리카노" → "Iced Americano"              │
  └────────────────────┬────────────────────────────────┘
                       │
          ▼
  ┌─────────────────────────────────────────────────────┐
  │  [0.5단계] 광고 문구 생성 레이어                     │
  │  현재: 규칙 기반 템플릿                              │
  │  추후: OpenAI GPT-4o-mini API 교체 예정              │
  └────────────────────┬────────────────────────────────┘
                       │
          ▼
  ┌─────────────────────────────────────────────────────┐
  │  [1단계] AI 이미지 생성 레이어                       │
  │  Stable Diffusion XL (SDXL)                          │
  │  stabilityai/stable-diffusion-xl-base-1.0            │
  │  영어 프롬프트 + 스타일 키워드 → 제품 이미지 생성    │
  └────────────────────┬────────────────────────────────┘
                       │
          ▼
  ┌─────────────────────────────────────────────────────┐
  │  [2단계] 그래픽 합성 레이어                          │
  │  Pillow (PIL)                                        │
  │  생성 이미지 + 반투명 패널 + 텍스트 오버레이         │
  │  템플릿 기반 레이아웃 (우측 사이드바 / 하단 오버레이)│
  └────────────────────┬────────────────────────────────┘
                       │
          ▼
  ┌─────────────────────────────────────────────────────┐
  │  [3단계] API 서빙 레이어                             │
  │  FastAPI                                             │
  │  POST /generate-ad       → 단일 상품 → PNG 반환      │
  │  POST /generate-ad/multi → 다중 상품 → ZIP 반환      │
  └─────────────────────────────────────────────────────┘
```

---

## 파일 구조

```
2team-GenPrj-backend/
├── ad_generator.py       # 메인 코드 (전체 레이어 포함)
├── fonts/
│   └── NeoHyundai_B.ttf  # 커스텀 한글 폰트
├── ARCHITECTURE.md       # 이 파일
└── SETUP.md              # 설치 및 트러블슈팅 가이드
```

---

## 레이어별 상세 설명

### [0단계] 번역 레이어

| 항목 | 내용 |
|------|------|
| 라이브러리 | `deep-translator` |
| 방식 | Google Translate API 호출 (모델 로드 없음) |
| 역할 | 한국어 상품명 → 영어 변환 후 SDXL 프롬프트에 삽입 |
| 이유 | SDXL은 영어 프롬프트에서만 좋은 품질 보장 |

```python
_translator = GoogleTranslator(source="ko", target="en")
product_en = _translator.translate("아이스 아메리카노")
# → "Iced Americano"
```

---

### [0.5단계] 광고 문구 생성 레이어

| 항목 | 내용 |
|------|------|
| 현재 방식 | 스타일별 고정 문구 템플릿 |
| 추후 교체 | OpenAI `gpt-4o-mini` API |

**스타일별 자동 문구:**

| 스타일 | 문구 |
|--------|------|
| 모던함 | 깔끔하게, 담백하게 |
| 따뜻함 | 한 잔의 여유, {가게명} |
| 고급스러움 | 특별한 순간을 위한 선택 |
| 귀여움 | 오늘도 달콤하게 ☕ |

**ChatGPT 교체 방법** (`ad_generator.py` 내 주석 해제):
```python
# pip install openai 후 아래 코드 활성화
client = openai.OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": f"{store_name}의 {product} 광고 문구..."}]
)
```

---

### [1단계] AI 이미지 생성 레이어

| 항목 | 내용 |
|------|------|
| 모델 | `stabilityai/stable-diffusion-xl-base-1.0` |
| 정밀도 | `float16` (GPU 메모리 절약) |
| 추론 스텝 | 30 steps |
| GPU | CUDA 필수 |

**스타일 → 프롬프트 키워드 매핑 (`STYLE_MAP`):**

| 스타일 | 영어 키워드 |
|--------|------------|
| 모던함 | modern, minimalist, clean white background, sleek design |
| 따뜻함 | warm, cozy, soft lighting, wooden table, cafe atmosphere |
| 고급스러움 | luxury, elegant, dark background, golden accent |
| 귀여움 | cute, pastel color, kawaii style, soft focus |

**최종 프롬프트 구조:**
```
{상품 영어명}, professional food advertisement photo,
{스타일 키워드}, high quality, 8k, bokeh background,
studio lighting, no text, no watermark
```

---

### [2단계] 그래픽 합성 레이어

| 항목 | 내용 |
|------|------|
| 라이브러리 | `Pillow (PIL)` |
| 템플릿 방식 | 좌표를 이미지 크기 비율(0.0~1.0)로 지정 |
| 폰트 | NeoHyundai_B.ttf (프로젝트 내 fonts/) |

**레이아웃 구성 (우측 사이드바 기준):**

```
┌────────────────────┬──────────────────┐
│                    │ [광고 문구]       │  y=7%  회색
│   AI 생성          │ [가게명]          │  y=18% 흰색 Bold
│   제품 이미지       │ ━━━━━━━━━━━     │  강조선 금색
│                    │ PRICE            │  y=34% 회색 소문자
│                    │ [가격]           │  y=40% 금색 Bold
│                    │ ─────────        │  구분선
│                    │ CONTACT          │  y=58% 회색 소문자
│                    │ [전화번호]        │  y=63% 밝은 회색
└────────────────────┴──────────────────┘
```

**텍스트 자동 줄바꿈:** `_wrap_text()` 함수가 패널 너비에 맞게 글자 단위로 줄바꿈 처리

---

### [3단계] API 서빙 레이어

| 항목 | 내용 |
|------|------|
| 프레임워크 | FastAPI |
| 실행 명령 | `uvicorn ad_generator:app --host 0.0.0.0 --port 8000` |

**엔드포인트:**

#### `POST /generate-ad` — 단일 상품
```json
// Request Body
{
  "store_name": "카페 루나",
  "product": "아이스 아메리카노",
  "price": "4,500원",
  "phone": "031-000-0000",
  "style": "모던함",
  "tagline": ""
}
// Response: image/png
```

#### `POST /generate-ad/multi` — 다중 상품
```json
// Request Body
{
  "store_name": "카페 루나",
  "products": ["아이스 아메리카노", "밀크티"],
  "prices": ["4,500원", "5,000원"],
  "phone": "031-000-0000",
  "style": "모던함",
  "tagline": ""
}
// Response: application/zip (각 상품별 PNG 포함)
```

---

## 폰트 탐색 우선순위

```
1순위: {프로젝트}/fonts/NeoHyundai_B.ttf   ← 커스텀 폰트 (권장)
2순위: C:/Windows/Fonts/malgun.ttf          ← Windows 시스템
3순위: /usr/share/fonts/.../NanumGothic.ttf ← Linux 시스템
```

---

## CLI 실행 입력 형식

```
가게명:  카페 루나
상품명:  아이스 아메리카노|밀크티       ← 여러 개는 | 구분
가격:    4,500원|5,000원               ← 여러 개는 | 구분 (쉼표 포함 가능)
전화번호: 031-000-0000
스타일:  모던함 / 따뜻함 / 고급스러움 / 귀여움
광고문구: (Enter = 자동 생성)
```

---

## 향후 개선 계획

- [ ] ChatGPT API 연동 (`generate_tagline` 함수 교체)
- [ ] img2img 지원 (실제 제품 사진 업로드 → 광고 스타일 변환)
- [ ] LoRA 파인튜닝 (AI Hub 한국 음식 데이터 활용)
- [ ] 프론트엔드 연결 (React 등)
