from fastapi import FastAPI
import uvicorn
import os
 
app = FastAPI()

@app.get("/")
def getRoot():
    """루트 엔드포인트: 서비스 상태 확인용"""
    return {"message": "Hello, getPrj Backend!"}


if __name__ == "__main__":
    # 환경변수 PORT가 있으면 해당 포트, 없으면 8119 사용
    port = int(os.environ.get("BACKEND_PORT", 8119))
    #export BACKEND_PORT=8000
    print(f"(1.0)genPrj Backend Server is running on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
