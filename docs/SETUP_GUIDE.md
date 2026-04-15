# 프로젝트 초기 설정 및 실행 가이드

이 문서는 Git에서 프로젝트를 새로 받은 후, 로컬 환경에서 백엔드 서버를 설정하고 실행하는 방법을 안내합니다.

## 1. 가상환경 설정 및 패키지 설치

가장 먼저 파이썬 가상환경을 생성하고 필요한 라이브러리들을 설치해야 합니다.

```powershell
# 1. 가상환경 생성 (최초 1회)
python -m venv venv

# 2. 가상환경 활성화 (Windows PowerShell 기준)
.\venv\Scripts\activate

# 3. 필수 라이브러리 설치
pip install -r requirements.txt

# 4. pip 업데이트
python.exe -m pip install --upgrade pip
```

## 2. 데이터베이스(DB) 초기화

Git에는 데이터베이스 파일(`.db`)이 포함되어 있지 않으므로, 아래 명령어를 실행하여 로컬 DB 파일을 생성하고 테이블을 초기화해야 합니다.

```powershell
# 4. SQLite 데이터베이스 파일 생성 및 테이블/컬럼 초기화
python -m app.db.SQLiteCreate
```
*이 과정에서 `app/db/SQLiteCreate.sql` 파일을 기반으로 테이블이 생성되며, 최신 마이그레이션이 자동으로 적용됩니다.*

## 3. 백엔드 서버 실행

모든 설정이 완료되면 FastAPI 서버를 실행합니다.

```powershell
# 5. 백엔드 서버 실행 (8000번 포트)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* `--reload`: 코드 수정 시 서버가 자동으로 재시작됩니다.
* `--host 0.0.0.0`: 외부 기기(프론트엔드 등)에서의 접속을 허용합니다.

## 4. 추가 확인 사항

### 4-1. 설정 파일 (backend.ini)
`app/common/backend.ini` 파일이 올바르게 구성되어 있는지 확인하세요. 특히 Ollama 서버 주소나 API 키 설정이 필요할 수 있습니다.

### 4-2. 이미지 데이터
생성된 이미지는 `data/images/` 폴더에 저장됩니다. 만약 기존 이미지 데이터가 필요하다면 팀원으로부터 해당 폴더의 내용을 전달받아 복사해야 합니다.

### 4-3. API 문서 확인
서버 실행 후 브라우저에서 아래 주소에 접속하면 Swagger UI를 통해 API 명세를 확인할 수 있습니다.
* `http://localhost:8000/docs`
