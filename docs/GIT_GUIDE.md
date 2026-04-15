# Git 관리 가이드

이 문서는 프로젝트 내 Git 사용 및 불필요한 파일 배제에 관한 가이드입니다.

## 1. 스테이징 취소하기 (git add 취소)

`git add .` 명령어로 너무 많은 파일이 추가되었을 때, 다음 명령어로 스테이징을 취소할 수 있습니다.

### 전체 취소
```bash
git reset
```

### 특정 파일/폴더만 취소
```bash
git reset <경로>
# 예: git reset venv/
```

## 2. .gitignore 설정 가이드

프로젝트 관리에 불필요한 파일은 `.gitignore`에 등록하여 관리합니다.

### 현재 적용된 주요 패턴
- **가상환경**: `venv/`, `.venv/`
- **파이썬 캐시**: `__pycache__/`, `*.py[cod]`
- **설정 및 보안**: `.env` (모든 경로의 .env 파일 제외)
- **로그**: `*.log`, `server.log`
- **데이터 및 결과물**: `data/images/*/`, `data/comfyui/output/`

### .security 폴더 관리
- `.env` 파일은 제외되도록 설정되어 있습니다.
- `.security` 폴더 내의 다른 파일들을 포함시키려면 폴더 자체를 제외하지 않아야 합니다. (현재 폴더는 유지되도록 설정됨)

## 3. Git 상태 확인

```bash
# 상태 확인
git status

# 무시되는 파일 확인 (디버깅용)
git check-ignore -v <파일명>
```
