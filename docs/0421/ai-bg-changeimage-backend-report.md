# AI 배경 생성 백엔드 보정 — 변경 보고서

- 작성일: 2026-04-21
- 대상 범위: **backend** 수정만 (`2team-GenPrj-backend`)
- 관련 프런트 보고서: `2team-GenPrj-frontend/doc/0421/ai-bg-changeimage-opt-fix-report.md`

---

## 1. 수정 배경

프런트 측에서 `_opt` 비동기 병렬 호출(opt=0/1/2)이 blob 응답 패턴으로 정상 연동된 뒤, 실제 생성된 배경 이미지의 **시각적 품질**이 아래 두 가지 이유로 기대에 미치지 못했다.

1. **SD 가중치 구문이 LLM에 의해 유실됨** — `(foo:1.3)` 같은 Stable Diffusion weight syntax가 영어로 이미 완성된 상태로 `change_kor_to_eng`에 들어가도, LLM이 한 번 더 재작성하면서 괄호·가중치·줄바꿈이 흐트러지는 현상이 있었음.
2. **ComfyUI `changeimage.json` 워크플로가 원본 이미지 구조를 너무 강하게 따라감** — 사용자 제품 사진을 그대로 img2img 레퍼런스로 넣으면 배경에 원본의 형태(컵·테이블·벽면)가 잔류해 "광고 스튜디오 배경"이라는 의도와 어긋남.

이 보고서는 두 지점에 대한 최소 침습 수정만 기록한다. FastAPI 라우터나 비동기 job store 계약은 변경하지 않았다.

---

## 2. 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| [app/models/openai.py](../../app/models/openai.py) | `_contains_hangul` 정적 메서드 신규 + `change_kor_to_eng` 선제 가드 추가 |
| [data/comfyui/changeimage.json](../../data/comfyui/changeimage.json) | KSampler 파라미터 튜닝, CLIP positive/negative 교체, 참조 이미지 경로 갱신, 8×8→1024×1024 다운·업스케일 노드 추가 |

검증: 두 파일 모두 구문 검사(Python, JSON) 통과. 기존 API 시그니처/라우터 영향 없음.

---

## 3. `openai.py` — SD 가중치 보존 가드

### 3.1 변경 내용

`change_kor_to_eng`는 기존에 입력이 비어있지 않으면 무조건 LLM 번역 파이프라인으로 보냈다. 하지만 `build_prompt_dual_prompt_opt(opt=1/2)` 경로에서는 호출자가 넘긴 `positive_prompt`/`negative_prompt`가 이미 영어 + SD weight syntax(`(masterpiece:1.3)`)인 경우가 많다. LLM이 이 문자열을 한 번 더 다듬으면 가중치/괄호/`\n`이 소실된다.

[app/models/openai.py:262-269](../../app/models/openai.py#L262-L269)
```python
@staticmethod
def _contains_hangul(text: str) -> bool:
    # 한글 음절(AC00-D7A3) / 자모(1100-11FF) / 호환 자모(3130-318F) 포함 여부
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F:
            return True
    return False
```

[app/models/openai.py:271-278](../../app/models/openai.py#L271-L278)
```python
def change_kor_to_eng(self, kor_str: str) -> str:
    # 한글 프롬프트를 영어로 번역 (LLM 사용)
    # 한글이 포함되어 있지 않으면 그대로 반환해 SD 가중치 구문 `(foo:1.3)` 등을
    # LLM 재작성으로 잃지 않도록 한다.
    if not kor_str or not kor_str.strip():
        return ""
    if not self._contains_hangul(kor_str):
        return kor_str
    ...
```

### 3.2 영향 범위

- `build_prompt_dual_prompt_opt`는 진입 직후 `positive_prompt`/`negative_prompt`를 `changeKor2Eng`로 통과시킨다(openai.py 기존 흐름). 한글이 없으면 **원문 그대로 보존**되어 이후 `_concat_prompt` 또는 LLM synthesis 경로에서 가중치 구문이 유지됨.
- 사용자 free-text(`user_prompt`, 한글 포함 가능)는 여전히 정상적으로 LLM 번역을 거친다.
- `_contains_korean`(기존 다른 위치의 헬퍼)은 그대로 유지 — 용도가 달라 중복이 아니다 (`build_prompt_bundle`의 LLM 필요 여부 판단용).

---

## 4. `changeimage.json` — ComfyUI 워크플로 튜닝

### 4.1 KSampler(노드 7) 파라미터 조정

| 항목 | Before | After | 의도 |
|------|--------|-------|------|
| `seed` | 488684581235404 | 660765690304600 | 결정적 재현용 baseline 재생성 (런타임에는 `apply_prompt_text`가 매번 랜덤 재설정하므로 이 값 자체는 실행에 영향 없음) |
| `steps` | 20 | 25 | 충분한 디테일 수렴 시간 확보 |
| `cfg` | 4.5 | 10 | positive 프롬프트의 가중치 구문이 실제로 반영되도록 classifier-free guidance 강화 |
| `denoise` | 1 (완전 재생성) | 0.9 | 원본 이미지의 색조/분위기를 10%만 남기고 나머지는 새로 생성 (아래 4.3 업스트림 구조와 연계) |

### 4.2 CLIP positive/negative 교체

**노드 8 (positive CLIP)** — 단순 문장 → 가중치 기반 광고 사진 지시문
```
Before: "A professional cafe interior poster background , high quality, cinematic lighting"

After:  (masterpiece:1.3), (best quality:1.3), (professional advertising photography:1.2),
        (highly polished luxury marble surface with subtle reflections:1.4),
        (cinematic studio lighting:1.3).
        (The entire scene is dynamically color-graded based on the dominant hues of the source image:1.5).
        A pristine, tight-frame bust-shot of an exclusive product pedestal. ...
        The entire background is (completely deconstructed into a soft, ethereal,
        and hazy wash of ambient light:1.6). ...
```

**노드 9 (negative CLIP)** — 단순 4-토큰 → 구조 제외 + 소품 제외 블록
```
Before: "text, watermark, blurry, person"

After:  (pillars:2.0), (arches:2.0), (building:2.0), (room:2.0), (hall:2.0),
        (large space:2.0), (distant view:2.0), (wide shot:2.0),
        (massive hall:1.8), (expansive background:1.8), (objects in background:1.7),
        cup, glass, coffee, beverage, drink, bottle, straw, liquid,
        text, logo, watermark, low quality.
```

> 의도: 배경에 기둥/아치/홀 등 건축 구조물과 음료 관련 소품이 생성되는 것을 억제하고, 제품이 놓인 받침대+앰비언트 광만 남긴다.

### 4.3 참조 이미지 파이프라인 재구성

**Before** — 노드 14 (LoadImage) → 노드 15 (VAE Encode) 직결
```
14 (coffee.png) ──▶ 15 (VAE Encode) ──▶ 3 (KSampler)
```
원본 이미지의 구조가 latent에 강하게 전달되어 img2img 결과에 형태가 잔류.

**After** — 8×8 다운스케일 → 1024×1024 업스케일 게이트 추가
```
14 (말차_1.jpg) ──▶ 22 (ImageScale 8×8) ──▶ 23 (ImageScale 1024×1024) ──▶ 15 (VAE Encode)
```

- 노드 22 (ImageScale, `nearest-exact`, 8×8, crop `disabled`) — 극단적 다운스케일로 형태 정보 소거, **색상 팔레트만** 잔류시킴
- 노드 23 (ImageScale, `nearest-exact`, 1024×1024) — VAE가 요구하는 해상도로 업스케일
- 노드 15의 `pixels` 소스를 `14` → `23`으로 교체
- 결과: "원본의 색은 따라가되 형태는 전부 날린" 상태로 img2img에 진입 → positive 프롬프트의 `dynamically color-graded based on the dominant hues of the source image` 지시문과 맞물려 의도된 앰비언트 배경 생성

### 4.4 기타 노드 변경

- 노드 14 (LoadImage) 기본값: `coffee.png` → `말차_1.jpg` (개발 환경 샘플 교체, 실제 요청 시에는 `apply_change_image`가 매번 덮어쓰므로 런타임 무관)
- 노드 24 (PreviewImage) 신규 — 워크플로 미리보기 편의용. `_extract_first_comfyui_image`는 SaveImage 계열 노드(11)에서 결과를 읽으므로 최종 응답엔 영향 없음

---

## 5. 런타임에서 실제로 반영되는 항목 (컨트랙트 확인)

ComfyUI 클라이언트의 `apply_prompt_text` / `apply_change_image`는 요청 시점에 워크플로 JSON을 **덮어쓴다**. 따라서 아래 표로 정리:

| `changeimage.json` 필드 | 런타임 동작 | 이번 변경의 실효성 |
|-------------------------|-----------|------------------|
| 노드 7 `seed` | `apply_prompt_text`가 매번 `random.randint`로 덮어씀 | JSON 값은 미사용 (베이스라인만 교체) |
| 노드 7 `steps`, `cfg`, `denoise` | 덮어쓰지 않음 | **실제 반영됨** ✓ |
| 노드 8 `text` (positive) | `apply_prompt_text`가 요청 positive로 덮어씀 | JSON 값은 opt=0 경우 LLM 재생성 결과로, opt=1/2는 `_concat_prompt` 결과로 대체됨 — **defaults로서 가치는 유지** |
| 노드 9 `text` (negative) | 동일 | 동일 |
| 노드 14 `image` | `apply_change_image`가 요청 `image_base64`로 교체 | JSON 값은 미사용 |
| 노드 22/23/15 연결 구조 | 덮어쓰지 않음 | **실제 반영됨** ✓ (핵심 품질 개선) |

즉 **정량적 파라미터(steps/cfg/denoise)와 참조 이미지 파이프라인 구조**가 이번 변경의 실제 효과를 내는 부분이다. 프롬프트 문자열은 opt 분기에 따라 런타임에 교체되므로 JSON의 것은 fallback/문서화 의미.

---

## 6. opt=0/1/2 분기와의 관계 (재확인, 변경 없음)

| opt | `build_prompt_dual_prompt_opt` 내 처리 | 이번 변경이 미치는 영향 |
|-----|-----------------------------------------|----------------------|
| 0 | `user_prompt` + `positive_prompt` + `negative_prompt` 모두 LLM에 전달, LLM이 재합성 | `_contains_hangul` 가드로 영어 positive/negative가 LLM 전처리 단계에서 **비파괴 통과** |
| 1 | `user_prompt` + 시스템 프롬프트만 LLM, 이후 `_concat_prompt(파라미터_pos, LLM_pos)` | 동일 — 파라미터 측 positive/negative의 가중치 구문 보존됨 |
| 2 | `user_prompt`만 LLM, 이후 `_concat_prompt` | 동일 |

프런트는 현재 `positive_prompt`/`negative_prompt`를 빈 문자열로 보내고 있으므로(프런트 보고서 참조) 실전 경로에서는 `_contains_hangul` 가드가 **조기 반환(`""` 체크)**에 먼저 걸린다. 다만 추후 프런트 또는 다른 호출자가 영어 가중치 문자열을 직접 전달하는 시나리오(예: 내부 테스트, 신규 기능)에서 이 가드가 회귀 방지 역할을 한다.

---

## 7. 검증

- [x] `app/models/openai.py` Python 구문 검사 통과
- [x] `data/comfyui/changeimage.json` JSON 구문 검사 통과
- [x] 기존 엔드포인트(`/model/changeimagecomfyui_opt/jobs`, `/result`) 시그니처 변경 없음 — 프런트 연동 영향 0
- [ ] ComfyUI 서버에서 실제 워크플로 실행 시 노드 15의 `pixels` 입력이 `23`로 정상 라우팅되는지 UI 확인 (사용자 검증)
- [ ] opt=0/1/2 3회 호출 결과 이미지에서 구조물 잔류가 이전 대비 감소했는지 육안 확인 (사용자 검증)

---

## 8. 남은 정리 대상 (out of scope)

- 노드 14의 기본 이미지 `말차_1.jpg`는 개발 중 빠르게 확인하려고 넣은 샘플. 커밋 전 중립적 이름(`placeholder.png` 등) 또는 원래의 `coffee.png`로 되돌리는 편이 협업에 유리할 수 있음.
- 노드 24 (PreviewImage)는 디버깅용. 운영 워크플로에서 불필요하면 정리 가능.
- `_contains_hangul`과 기존 `_contains_korean`은 판정 범위가 조금 다름(후자의 구현을 확인한 뒤 하나로 통합 가능).
- 노드 7의 고정 `seed` 값은 런타임에 덮어쓰이므로 baseline을 명시적 `0`이나 `-1`로 둬도 됨(가독성).
