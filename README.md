# FastAPI 프로젝트 실행 방법

1. 가상환경 활성화(Windows):
   
	```powershell
	.venv\Scripts\activate
	```

2. 서버 실행:
   
	```powershell
	uvicorn app.main:app --reload
	```

## 코딩 컨벤션
- 자세한 규칙은 doc/CONVENTION.md 참고
# AI 6기 2팀 음식 이미지 생성 프로젝트

AI 고급 과정 6기 2팀의 생성 프로젝트 리포지토리에 오신 것을 환영합니다.
본 프로젝트는 사용자의 요구에 맞는 고품질의 음식 이미지를 생성하고 관리하는 서비스를 목표로 합니다.

---

## 1. 프로젝트 개요
* **프로젝트명**: Food Image Generator (음식 이미지 생성 서비스)
* **개발 기간**: 2026.03 - 2026.04
* **주요 기능**: 사용자의 텍스트 입력을 기반으로 한 음식 이미지 생성 및 갤러리 관리

---

## 2. 기술 스택

### Frontend
* React
* Styled Components / Tailwind CSS
* Axios (API Communication)

### Backend & AI
* FastAPI (Python)
* PyTorch / Diffusers (Stable Diffusion 기반 모델)
* Docker (Deployment)

---

## 3. 주요 기능
* **이미지 생성**: 프롬프트를 입력하여 실사 수준의 음식 이미지 생성
* **커스텀 필터**: 한식, 일식, 양식 등 스타일별 최적화된 생성 옵션 제공
* **이미지 저장 및 공유**: 생성된 이미지를 고화질로 저장하고 관리

---

## 4. 시작 가이드

### 프론트엔드 실행 (React)
1. 저장소 클론: git clone [Frontend-Repo-URL]
2. 패키지 설치: npm install
3. 서비스 시작: npm start

### 백엔드 실행 (Server/AI)
1. 저장소 클론: git clone [Backend-Repo-URL]
2. 가상환경 설정: python -m venv venv
3. 필수 라이브러리 설치: pip install -r requirements.txt
4. 서버 실행: uvicorn main:app --reload

---

## 5. 팀 정보 (AI 6기 2팀)
* **팀원 1**: [장우정/역할] - 
* **팀원 2**: [김경태/역할] - 
* **팀원 3**: [김영욱/역할] - 
* **팀원 3**: [오현석/역할] - 
---

## 6. 라이선스
본 프로젝트는 교육적 목적으로 제작되었으며, 관련 라이선스 정책을 준수합니다.