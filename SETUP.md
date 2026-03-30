# 설치 가이드 & 트러블슈팅

## 환경

| 항목 | 내용 |
|------|------|
| 서버 | GCP VM (Ubuntu) |
| Python | 3.10 |
| GPU | CUDA 필수 (SDXL 실행) |
| 가상환경 경로 | `/home/spai0601/gen-server/.venv` |

---

## 설치 명령어 전체

```bash
# 1. 기본 패키지
pip install torch torchvision torchaudio   # CUDA 버전 필요 (아래 주의사항 참고)
pip install diffusers accelerate           # SDXL 이미지 생성
pip install transformers                   # HuggingFace 모델 공통
pip install Pillow                         # 이미지 합성
pip install fastapi uvicorn               # API 서버
pip install pydantic                       # 데이터 검증

# 2. 번역
pip install deep-translator               # Google Translate (한→영)

# 3. 폰트 (Linux 기본 한글 폰트)
sudo apt-get install fonts-nanum

# 4. 추후 ChatGPT 연동 시
pip install openai
```

---

## 실행 방법

### CLI 테스트 (터미널에서 직접 입력)
```bash
cd /home/spai0601/gen-server
python ad_generator.py
```

### FastAPI 서버 실행
```bash
uvicorn ad_generator:app --host 0.0.0.0 --port 8000
```

### API 호출 테스트 (단일 상품)
```bash
curl -X POST http://localhost:8000/generate-ad \
  -H "Content-Type: application/json" \
  -d '{
    "store_name": "카페 루나",
    "product": "아이스 아메리카노",
    "price": "4,500원",
    "phone": "031-000-0000",
    "style": "모던함",
    "tagline": ""
  }' --output ad_result.png
```

### API 호출 테스트 (다중 상품)
```bash
curl -X POST http://localhost:8000/generate-ad/multi \
  -H "Content-Type: application/json" \
  -d '{
    "store_name": "카페 루나",
    "products": ["아이스 아메리카노", "밀크티"],
    "prices": ["4,500원", "5,000원"],
    "phone": "031-000-0000",
    "style": "모던함",
    "tagline": ""
  }' --output ads.zip
```

---

## 트러블슈팅

### 1. `MarianTokenizer requires the SentencePiece library`

**원인:** `sentencepiece` 미설치 (초기에 MarianMT 번역 모델 사용 시 발생)

**해결:**
```bash
pip install sentencepiece
```

> **현재 코드는 MarianMT를 사용하지 않습니다.**
> `deep-translator`(Google Translate)로 교체하여 이 오류가 발생하지 않습니다.

---

### 2. `torch.load` 보안 취약점 오류 (CVE-2025-32434)

**오류 메시지:**
```
ValueError: Due to a serious vulnerability issue in `torch.load`...
we now require users to upgrade torch to at least v2.6
```

**원인:** torch 버전이 v2.6 미만

**해결 방법 A — torch 업그레이드:**
```bash
pip install --upgrade torch torchvision torchaudio
```

**해결 방법 B — 번역 방식 변경 (채택):**
MarianMT 대신 `deep-translator` 사용으로 torch.load 자체를 호출하지 않도록 변경

```bash
pip install deep-translator
```

---

### 3. 한글 폰트가 적용되지 않음

**디버그 출력 예시 (문제 상황):**
```
[폰트 탐색] /home/spai0601/gen-server/fonts/NeoHyundai_B.ttf → 없음
[폰트 탐색] C:/Windows/Fonts/malgun.ttf → 없음
[폰트 탐색] /usr/share/fonts/truetype/nanum/NanumGothic.ttf → 존재함
[폰트 적용] /usr/share/fonts/truetype/nanum/NanumGothic.ttf
```

**원인 1 — fonts 폴더가 서버에 없음:**
```bash
# 폴더 생성
mkdir -p /home/spai0601/gen-server/fonts

# 로컬 → 서버 파일 전송
scp -i ~/.ssh/id_ed25519 fonts/NeoHyundai_B.ttf \
  spai0601@[서버IP]:/home/spai0601/gen-server/fonts/
```

**원인 2 — 파일명 불일치 (공백 vs 언더스코어):**

| 상황 | 파일명 |
|------|--------|
| 코드에서 찾는 이름 | `NeoHyundai_B.ttf` (언더스코어) |
| 실제 파일명이 달랐던 경우 | `NeoHyundai B.ttf` (공백) |

```bash
# 실제 파일명 확인
ls -la /home/spai0601/gen-server/fonts/
```

파일명이 다르면 서버에서 이름 변경:
```bash
mv "fonts/NeoHyundai B.ttf" fonts/NeoHyundai_B.ttf
```

**나눔고딕 폴백 설치 (커스텀 폰트 없을 때):**
```bash
sudo apt-get install fonts-nanum
```

---

### 4. GCP SSH 접속 권한 오류

**오류 메시지:**
```
Permission denied (publickey)
```

**원인:** SSH 공개키가 GCP VM에 등록되지 않음

**해결 방법 A — GCP 콘솔에서 키 등록:**
```bash
# 1. 로컬에서 SSH 키 생성
ssh-keygen -t ed25519 -C "your-email@gmail.com"

# 2. 공개키 확인
cat ~/.ssh/id_ed25519.pub
```
GCP 콘솔 → Compute Engine → VM 인스턴스 → 수정 → SSH 키 → 붙여넣기 → 저장

```bash
# 3. 다시 접속
scp -i ~/.ssh/id_ed25519 fonts/NeoHyundai_B.ttf \
  spai0601@[서버외부IP]:/home/spai0601/gen-server/fonts/
```

**해결 방법 B — 브라우저 SSH로 파일 업로드 (가장 빠름):**
1. GCP 콘솔 → VM 인스턴스 → SSH 버튼 클릭
2. 브라우저 터미널 우측 상단 ⚙️ → 파일 업로드
3. 업로드 후 이동:
```bash
mkdir -p /home/spai0601/gen-server/fonts
mv ~/NeoHyundai_B.ttf /home/spai0601/gen-server/fonts/
```

---

### 5. 가격 여러 개 입력 시 잘못 쪼개짐

**원인:** `4,500원, 5,000원` 을 쉼표로 split하면 `["4", "500원", "5", "000원"]` 으로 분리됨

**해결:** 구분자를 `|` 로 변경

```
# 올바른 입력 방법
상품명: 아이스 아메리카노|밀크티
가격:   4,500원|5,000원
```

---

### 6. 스타일 입력 오류

**원인:** 입력값에 공백이 포함되거나 오타

```
'고급스움'은 없는 스타일입니다. '모던함'으로 대체합니다.
```

**해결:** 아래 중 하나를 정확히 입력

```
모던함 / 따뜻함 / 고급스러움 / 귀여움
```

---

## 폰트 탐색 우선순위 (참고)

```
1순위: {프로젝트}/fonts/NeoHyundai_B.ttf     ← 커스텀 폰트
2순위: C:/Windows/Fonts/malgun(bd).ttf        ← Windows
3순위: /usr/share/fonts/.../NanumGothic.ttf   ← Linux (apt install fonts-nanum)
```

---

## 주요 의존성 버전 참고

| 패키지 | 비고 |
|--------|------|
| `torch` | v2.6 이상 권장 (CVE-2025-32434) |
| `diffusers` | SDXL 지원 버전 |
| `deep-translator` | MarianMT 대체 (torch 버전 무관) |
| `Pillow` | 최신 버전 |
| `fastapi` + `uvicorn` | API 서버 |
