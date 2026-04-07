from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from app.common.defines import SERVER_PORT

from app.restapi.modelApi import  router as adhelper_router
from app.restapi.adverApi import router as adver_router
from app.restapi.imageApi import router as image_router
from app.restapi.userApi import router as user_router


# 라우터 등록 및 서버 실행 설정

app = FastAPI(title="addhelper Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(adhelper_router)
app.include_router(adver_router)
app.include_router(image_router)
app.include_router(user_router)


@app.get("/")
def get_root():
    """루트 엔드포인트: 서비스 상태 확인용"""
    return {"message": "Hello, getPrj Backend!"}

# 테스트용 엔드포인트: 서버 종료 개발중에만 사용, 실제 서비스에서는 제거할 것
@app.get("/shutdown")
def shutdown():
    exit(0)
    return {"message": "Shutting down Backend!"}


if __name__ == "__main__":
    # 환경변수 PORT가 있으면 해당 포트, 없으면 backend.ini의 [server] port 사용
    port = int(os.environ.get("BACKEND_PORT", SERVER_PORT))
    #export BACKEND_PORT=8000
    print(f"(1.0)genPrj Backend Server is running on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
