# AI Backlit — AI 배경 생성 에디팅 서비스 (Backend)

AI Backlit 은 사용자가 업로드한 상품 이미지의 배경을 AI로 자유롭게 재구성하고 편집할 수 있는 에디팅 서비스입니다.
본 저장소는 해당 서비스의 백엔드(API) 코드베이스로, FastAPI 기반의 REST API와 ComfyUI / OpenAI / Ollama(Gemma) / Florence VLM 등을 연동한 이미지 파이프라인을 제공합니다.

> AI 6기 2팀 생성 프로젝트 — Food Image / Product Backlit Generator

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 구조](#2-시스템-구조)
3. [기술 스택](#3-기술-스택)
4. [핵심 기능](#4-핵심-기능)
5. [디렉터리 구조](#5-디렉터리-구조)
6. [실행 가이드](#6-실행-가이드)
7. [API 명세](#7-api-명세)
8. [응답 포맷](#8-응답-포맷)
9. [참고 문서](#9-참고-문서)
10. [팀 정보](#10-팀-정보)
11. [라이선스](#11-라이선스)

---

## 1. 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | AI Backlit — AI 배경 생성 에디팅 서비스 |
| 저장소 | 2team-GenPrj-backend |
| 개발 기간 | 2026.03 — 2026.04 |
| 도메인(서비스) | https://gen-proj.duckdns.org |
| 백엔드 포트(내부) | 8990 (Docker), 로컬 개발 시 8000 |
| 핵심 가치 | 상품/음식 이미지의 배경을 AI 프롬프트로 즉시 교체·재구성 |

주요 사용 시나리오는 다음과 같습니다.

- 상품 이미지를 업로드하면 VLM이 이미지 컨텍스트를 분석하여 어울리는 배경을 자동 생성
- 텍스트 프롬프트만으로 새 이미지 생성 (Text-to-Image)
- 기존 이미지를 강도(strength) 기반으로 변형 (Image-to-Image)
- 광고 카피, 디자인 프로파일, 사용자/이미지 갤러리 관리

---

## 2. 시스템 구조

ComfyUI 기반의 이미지 생성 엔진과 Docker 위에 올라간 FastAPI 백엔드, 그리고 NGINX(HTTPS) 프록시로 구성된 GCP 기반 아키텍처입니다.

![시스템 구조](docs/%EC%8B%9C%EC%8A%A4%ED%85%9C%EA%B5%AC%EC%A1%B0.png)

### 2-1. 컴포넌트 요약

| 영역 | 컴포넌트 | 설명 |
| --- | --- | --- |
| Edge | NGINX (HTTPS) | `https://gen-proj.duckdns.org` (Port 443) — 외부 트래픽 진입점 |
| Web | Docker / Backend | FastAPI(REST API), DB Module, Model Relay, OpenAI 연동. 내부 포트 8990, SSH 10022 |
| AI Engine | ComfyUI | `stabilityai/stable-diffusion-3.5-large` (양자화 버전) 기반 이미지 생성 |
| Storage | SQLite | 사용자/이미지/디자인 프로파일 저장 |
| LLM | gpt-5-mini (OpenAI) | 입력 영문화 및 SD 3.5용 프롬프트 정교화 |
| VLM | Ollama / Gemma + Florence-2 | 이미지 시각 분석 → 배경 묘사 텍스트 추출 |
| Frontend | React | 상품 이미지/정보를 백엔드로 전송 |

### 2-2. 요청 흐름

```
[User] → [Frontend(React)] → NGINX(HTTPS) → Backend(FastAPI)
              ↘                         ↙          ↘
           genPrj 퍼블리싱        Model Relay    OpenAI gpt-5-mini
                                      ↓
                                   ComfyUI
                              (SD 3.5 + Florence VLM
                               + Ollama/Gemma)
                                      ↓
                                  생성 이미지
```

---

## 3. 기술 스택

### Backend
- Python 3.x
- FastAPI / Uvicorn
- SQLite (`data/db/genprj.db`)
- Pydantic (요청 모델 정의)
- LangChain · langchain-openai · Langfuse (Trace)

### AI / Model
- ComfyUI (Workflow Engine)
- Stable Diffusion 3.5 Large (양자화)
- OpenAI `gpt-5-mini` (프롬프트 정교화 / 광고 카피)
- Ollama Gemma (`gemma4:e4b`) — VLM Prompt Fusion
- Florence-2 — 이미지 캡셔닝(VLM)

### Infra
- Docker (Web/Backend 컨테이너)
- NGINX (HTTPS 리버스 프록시, DuckDNS 도메인)
- Google Cloud Platform

---

## 4. 핵심 기능

### 4-1. 텍스트 → 이미지 생성 (Text-to-Image)
- 사용자의 한국어/영어 프롬프트를 OpenAI 로 SD 3.5 용 Positive/Negative 프롬프트로 정교화
- ComfyUI `createimage.json` 워크플로우로 이미지 생성

### 4-2. 이미지 → 이미지 변환 (Image-to-Image)
- 업로드된 이미지를 ComfyUI 서버에 업로드 후 `changeimage.json` 워크플로우 실행
- `strength`(기본 0.45)로 원본 보존 정도 제어

### 4-3. 배경 생성 (VLM Background Generation)
- Florence-2 / Ollama Gemma 로 이미지의 피사체·조명·구도·텍스처를 분석 (`vlmtext`)
- OpenAI(gpt-5-mini)가 분석 결과 + 사용자 프롬프트를 융합해 최종 SD 3.5 프롬프트를 산출
- `no foreground subject`, `empty environment` 등 배경 생성 키워드를 자동 보강
- ComfyUI 로 새로운 배경 이미지를 생성

### 4-4. 비동기 Job 처리
- 대기시간이 긴 이미지 생성은 `*/jobs` 엔드포인트로 비동기 실행
- `jobs/{job_id}` 로 상태 조회, `jobs/{job_id}/result` 로 결과(이미지 바이너리/JSON) 반환

### 4-5. 사용자 / 갤러리 / 디자인
- 회원가입 · 로그인 (SHA-256 해시)
- 이미지 업로드/조회/다운로드 (`data/images/<YYYYMM>/`)
- 디자인 프로파일 저장 및 조회
- 광고 카피 자동 생성

---

## 5. 디렉터리 구조

```
2team-GenPrj-backend/
├── app/
│   ├── main.py                  # FastAPI 엔트리포인트, 라우터 등록
│   ├── common/
│   │   ├── defines.py           # 전역 상수 / 경로 / 설정 로더
│   │   ├── backend.ini          # 서버·엔진·OpenAI·Ollama·ComfyUI 설정
│   │   └── util.py              # 공통 응답 포맷(ok_response/error_response)
│   ├── db/
│   │   ├── SQLiteCreate.py      # DB 초기화 및 마이그레이션
│   │   └── SQLiteDB.py          # SQLite 클라이언트 (User/Image/Design)
│   ├── models/
│   │   ├── openai.py            # OpenAI 프롬프트/광고 카피 빌더
│   │   ├── comfyui.py           # ComfyUI Client (Florence VLM, generate)
│   │   ├── gemma4ollama.py      # Ollama Gemma VLM Fusion 프롬프트
│   │   └── langfuse.py          # 추적/로깅 연동
│   └── restapi/
│       ├── modelApi.py          # /addhelper/model/* (이미지 생성/변환/배경)
│       ├── adverApi.py          # /addhelper/adver/*  (광고 카피/듀얼 프롬프트)
│       ├── designApi.py         # /addhelper/design/* (디자인 프로파일)
│       ├── imageApi.py          # /addhelper/image/*  (업로드/리스트/다운로드)
│       ├── userApi.py           # /addhelper/user/*   (회원가입/로그인)
│       ├── SQLiteApi.py         # /addhelper/sqlite/* (디버그용 SQL 실행)
│       ├── _model_engine.py     # 외부 model 엔진 호출 동기 구현
│       ├── _model_comfyui.py    # ComfyUI 호출 동기 구현
│       ├── _model_ollama.py     # Ollama 기반 배경 생성 구현
│       └── _model_job_store.py  # 비동기 Job 저장소
├── data/
│   ├── db/genprj.db             # SQLite DB (자동 생성)
│   ├── images/<YYYYMM>/         # 업로드된 사용자 이미지
│   └── comfyui/                 # ComfyUI 워크플로우 JSON / 입력·프롬프트
├── docs/
│   ├── SETUP_GUIDE.md
│   ├── COMFYUI_PROCESS.md
│   ├── GIT_GUIDE.md
│   └── 시스템구조.png
├── requirements.txt
├── run_server.py
└── README.md
```

---

## 6. 실행 가이드

자세한 설정은 [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md) 를 참고하세요.

### 6-1. 가상환경 및 의존성 설치 (Windows PowerShell)

```powershell
# 1) 가상환경 생성 (최초 1회)
python -m venv venv

# 2) 가상환경 활성화
.\venv\Scripts\activate

# 3) 의존성 설치
pip install -r requirements.txt
python -m pip install --upgrade pip
```

### 6-2. 데이터베이스 초기화

```powershell
python -m app.db.SQLiteCreate
```

`data/db/genprj.db` 가 생성되며, `SQLiteCreate.sql` 기반으로 테이블이 초기화됩니다.

### 6-3. 서버 실행

```powershell
# 개발 모드 (자동 재시작)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는
python run_server.py
```

### 6-4. 설정 파일

`app/common/backend.ini`

| 섹션 | 키 | 설명 |
| --- | --- | --- |
| `[server]` | `port` | 백엔드 포트 (기본 8990) |
| `[engine]` | `engine_url`, `wait_time` | 외부 모델 엔진 URL / 타임아웃 |
| `[openai]` | `ad_copy_prompt_msg` | 광고 카피용 시스템 프롬프트 |
| `[ollama]` | `model_name`, `ollama_url`, `wait_time` | Ollama Gemma 설정 |
| `[comfyui]` | `comfyui_address` | ComfyUI 서버 주소 |

OpenAI API Key 등 비밀값은 `.security/.env` 의 `OPEN_API_KEY` 로 주입합니다.

### 6-5. API 문서

서버 실행 후 Swagger UI 에서 모든 엔드포인트를 확인할 수 있습니다.

```
http://localhost:8000/docs
```

---

## 7. API 명세

라우터 prefix 는 모두 `/addhelper/*` 로 통일되어 있습니다.

### 7-1. 시스템

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/` | 헬스 체크 |
| GET | `/addhelper/model/test` | 접속 테스트 |

### 7-2. 이미지 생성/변환 — `/addhelper/model`

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/generate_sync` | Text→Image (외부 엔진, 동기) |
| POST | `/generate/jobs` | Text→Image 비동기 Job |
| POST | `/changeimage_sync` | Image→Image (동기) |
| POST | `/changeimage/jobs` | Image→Image 비동기 Job |
| POST | `/makebgimage_sync` | 배경 생성 (동기, 외부 엔진) |
| POST | `/makebgimageollama_sync` | 배경 생성 (Ollama VLM) |
| POST | `/makebgimagecomfyui_sync` | 배경 생성 (ComfyUI + VLM Fusion) |
| GET | `/generatecomfyui_sync` | Text→Image (ComfyUI 직결) |
| POST | `/changeimagecomfyui_sync` | Image→Image (ComfyUI 직결) |
| POST | `/changeimagecomfyui_opt/jobs` | Image→Image 옵션 워크플로우 |
| POST | `/generate_vlm_gpt_image` | Florence VLM + GPT + ComfyUI 통합 |
| GET/POST | `*/jobs/{job_id}`, `*/jobs/{job_id}/result` | Job 상태/결과 조회 |

### 7-3. 광고 카피 / 듀얼 프롬프트 — `/addhelper/adver`

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/generate` | 광고 카피(메인 + 변형 1~5개) 생성 |
| POST | `/makedaulprompt` | Positive/Negative 듀얼 프롬프트 빌드 |
| POST | `/makedaulprompt/jobs` | 동일 작업 비동기 처리 |

### 7-4. 디자인 프로파일 — `/addhelper/design`

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/saveprofile` | 사용자별 디자인 프로파일 저장 |
| POST | `/list` | 사용자별 프로파일 목록 조회 |

### 7-5. 이미지 갤러리 — `/addhelper/image`

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/upload` | 이미지 업로드 (png/jpg) |
| POST | `/list` | 이미지 목록 조회 (user_id / file_name / file_desc) |
| POST | `/info` | 이미지 메타 단건 조회 |
| POST | `/download` | 이미지 파일 다운로드 |

### 7-6. 사용자 — `/addhelper/user`

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/signup` | 회원가입 (SHA-256 해시 저장) |
| POST | `/login` | 로그인 검증 |

### 7-7. SQLite (개발용) — `/addhelper/sqlite`

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/putsql` | 임의 SQL 실행 (SELECT / DML) |

---

## 8. 응답 포맷

### 8-1. 공통 JSON 응답

```json
{
    "statusCode": 200,
    "statusMsg": "OK",
    "datalist": [],
    "data": null
}
```

### 8-2. 성공 예시 — `GET /addhelper/model/test`

```json
{
    "statusCode": 200,
    "statusMsg": "OK",
    "datalist": [],
    "data": "접속 테스트 성공"
}
```

### 8-3. 이미지 API 성공 응답

이미지 생성/변환 API 는 성공 시 **이미지 바이너리** 를 반환합니다.

```
HTTP/1.1 200 OK
Content-Type: image/png
```

### 8-4. 이미지 API 실패 응답

업스트림이 이미지를 반환하지 않으면 JSON 에러를 반환합니다.

```json
{
    "statusCode": 100,
    "statusMsg": "Upstream did not return image data.",
    "datalist": [],
    "data": null,
    "upstream_content_type": "application/json",
    "upstream_body_preview": "..."
}
```

### 8-5. changeimage 요청 예시

```http
POST /addhelper/model/changeimage_sync
Content-Type: application/json
```

```json
{
    "prompt": "카툰 스타일로 바꿔주세요",
    "positive_prompt": "cartoon style, clean outline, vivid color",
    "negative_prompt": "blurry, low quality, watermark, text",
    "image_base64": "iVBORw0KGgoAAAANSUhEUg...",
    "strength": 0.45
}
```

### 8-6. 검증 실패 예시

```json
{
    "statusCode": 100,
    "statusMsg": "유효한 base64 이미지가 아닙니다.",
    "datalist": [],
    "data": null
}
```

> 정리: 이미지 API 성공 시에는 이미지 바이너리, 그 외(test, 사용자/디자인/갤러리, 오류 응답)는 모두 `statusCode / statusMsg / datalist / data` 공통 JSON 포맷을 따릅니다.

---

## 9. 참고 문서

| 문서 | 설명 |
| --- | --- |
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | 로컬 개발 환경 설치 및 실행 가이드 |
| [docs/COMFYUI_PROCESS.md](docs/COMFYUI_PROCESS.md) | 이미지 생성 / 변환 / 배경 생성 파이프라인 상세 |
| [docs/GIT_GUIDE.md](docs/GIT_GUIDE.md) | Git 사용 및 .gitignore 가이드 |
| [docs/시스템구조.png](docs/%EC%8B%9C%EC%8A%A4%ED%85%9C%EA%B5%AC%EC%A1%B0.png) | GCP / Docker / ComfyUI 시스템 구조 다이어그램 |

코딩 컨벤션은 `docs/CONVENTION.md` 를 따릅니다.

---

## 10. 팀 정보 (AI 엔지니어 6기 2팀)

| 팀원 | 이름 | 역할 |
| --- | --- | --- |
| 팀원 1 | 장우정 | Project Management & Core Frontend Development |
| 팀원 2 | 김경태 | Frontend Optimization & Technical Research |
| 팀원 3 | 김영욱 | Backend Infrastructure & System Architecture |
| 팀원 4 | 오현석 | AI Workflow Integration & Full-stack Implementation |

---

## 11. 라이선스

본 프로젝트는 **교육용** 으로 제작되었으며, 사용된 모델 및 라이브러리(Stable Diffusion 3.5, OpenAI, Ollama, ComfyUI 등)의 라이선스 정책을 준수합니다.
