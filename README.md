# United Backend Service (FastAPI)

이 프로젝트는 AI 광고 생성 플랫폼의 백엔드 시스템입니다. FastAPI를 기반으로 다양한 AI 모델 연동 및 데이터 관리를 담당합니다.

## 브랜치 정보
- **Target Branch**: `feature/United1_1`

## 🛠 기술 스택
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Web Server**: Uvicorn
- **AI Integration**: Langchain, OpenAI SDK
- **Data handling**: SQLite, python-multipart

## 설치 및 설정

### 1. 가상환경 구축 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 필요한 API Key 및 설정을 추가하십시오. (OpenAI API Key 등)

## 실행 방법

### 개발 서버 실행
```bash
python run_server.py
```
서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

## API 연동 가이드

### 주요 엔드포인트
- **/generate_ad_copy**: 사용자의 가게 정보를 바탕으로 AI 광고 카피 생성 (OpenAI 연동)
- **/generate_background**: AI 기반 제품 배경 생성 및 합성
- **/docs**: Swagger UI를 통한 API 명세 확인

### 프론트엔드 연동 (CORS)
현재 `http://localhost:5173` (Vite 기본 포트)에서의 접근이 허용되어 있습니다. 다른 도메인에서 접속이 필요할 경우 `app/main.py`의 `CORSMiddleware` 설정을 수정하십시오.

## 프로젝트 구조
- `app/main.py`: 애플리케이션 진입점 및 라우터 등록
- `app/restapi/`: 각 도메인별 API 핸들러 (Adver, Model, Design 등)
- `app/common/`: 공통 유틸리티 및 전역 설정
- `run_server.py`: Uvicorn 서버 실행 스크립트

---
**주의**: 실제 배송 환경에서는 `app/main.py`의 `/shutdown` 엔드포인트를 반드시 제거하십시오.
