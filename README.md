# AdHelper - AI 광고 지원 솔루션 백엔드

AI 엔지니어 6기 고급 과정 2팀의 광고 이미지 및 카피 문구 생성 프로젝트 백엔드 리포지토리입니다.
이 서버는 **FastAPI**를 기반으로 하며, **ComfyUI, Ollama, OpenAI** 엔진을 통합하여 마케팅 자동화를 지원합니다.

---

## 1. 프로젝트 개요
* **프로젝트명**: AD-Gen-Pro (광고 이미지 및 카피 생성 서비스 - 가명)
* **개발 기간**: 2026.03 - 2026.04
* **핵심 목표**: 
  * 사용자의 요구에 맞춘 고품질 광고 이미지 생성 (ComfyUI 기반)
  * 마케팅에 최적화된 광고 카피 문구 생성 (OpenAI/Ollama LLM 활용)
  * 생성된 리소스의 이력 관리 및 사용자 맞춤형 서비스 제공

---

## 2. 기술 스택

### Backend Framework
* **FastAPI**: 비동기 처리를 지원하는 고성능 파이썬 웹 프레임워크

### AI Engine & LLM
* **ComfyUI**: 이미지 생성 및 변환 (Stable Diffusion 워크플로우 제어)
* **OpenAI (GPT-4o)**: 광고 카피 생성 및 프롬프트 최적화
* **Ollama (Gemma)**: 로컬 기반 LLM 처리 (보조 엔진)
* **LangChain / Langfuse**: LLM 오케스트레이션 및 추적 관리

### Database & Storage
* **SQLite**: 가볍고 빠른 데이터베이스 관리 (SQLAlchemy ORM 활용)
* **File System**: 생성된 이미지 데이터 및 로그 저장

---

## 3. 디렉토리 구조

```text
D:\01.project\2team-GenPrj-backend\
├── app\                    # FastAPI 애플리케이션 소스
│   ├── common\             # 공통 유틸리티, 상수, 설정 정의
│   ├── db\                 # 데이터베이스 스키마 및 작업 로직
│   ├── models\             # AI 엔진 연동 모듈 (ComfyUI, Ollama, OpenAI)
│   └── restapi\            # API 엔드포인트 (라우터)
├── data\                   # DB 파일, 생성된 이미지 및 로그 데이터
├── docs\                   # API 명세서 및 가이드 문서
├── .security\              # 환경 변수(.env) 등 보안 설정
└── requirements.txt        # 프로젝트 의존성 목록
```

---

## 4. 시작 가이드

### 환경 구축 (Local)

1. **가상환경 설정 및 패키지 설치**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **환경 변수 설정**
   `.security/.env` 파일을 생성하고 필요한 API 키와 설정을 입력합니다.
   ```env
   OPENAI_API_KEY=your_api_key_here
   LANGFUSE_PUBLIC_KEY=...
   LANGFUSE_SECRET_KEY=...
   ```

3. **서버 실행**
   ```powershell
   python run_server.py
   # 또는
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 5. 주요 API 서비스

* **Model API (`/addhelper/model`)**: 이미지 생성 및 접속 테스트
* **Adver API (`/addhelper/adver`)**: 광고 카피 문구 생성 및 관리
* **Design API (`/addhelper/design`)**: 디자인 관련 작업 지원
* **Image API (`/addhelper/image`)**: 생성된 이미지 조회 및 처리
* **User API (`/addhelper/user`)**: 사용자 정보 및 권한 관리
* **SQLite API (`/addhelper/sqlite`)**: DB 직접 관리 및 조회

---

## 6. 문서 및 리소스
* [설치 가이드](docs/SETUP_GUIDE.md)
* [API 명세서](docs/API.md)
* [코딩 컨벤션](docs/CONVENTION.md)
