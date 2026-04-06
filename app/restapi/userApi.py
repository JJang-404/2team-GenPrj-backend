import hashlib
import sqlite3
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.common.util import error_response, ok_response
from app.db.SQLiteDB import SQLiteDB

router = APIRouter(prefix="/addhelper/user", tags=["addhelper-user"])

class UserSignupRequest(BaseModel):
	user_id: str = Field(..., min_length=1)
	user_name: str = Field(..., min_length=1)
	user_passwd: str = Field(..., min_length=1)


class UserLoginRequest(BaseModel):
	user_id: str = Field(..., min_length=1)
	user_passwd: str = Field(..., min_length=1)


def _hash_password(raw_password: str) -> str:
	return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


@router.post("/signup", response_model=None)
def signup(req: UserSignupRequest):
	db = SQLiteDB()
	if db.GetUserByLoginId(req.user_id):
		return JSONResponse(
			status_code=400,
			content=error_response("이미 존재하는 로그인 아이디입니다."),
		)

	try:
		new_user_no = db.InsertUser(req.user_id, req.user_name, _hash_password(req.user_passwd))
	except sqlite3.IntegrityError:
		return JSONResponse(
			status_code=400,
			content=error_response("이미 존재하는 로그인 아이디입니다."),
		)

	return ok_response(
		{
			"data": "회원가입 성공",
			"datalist": [
				{
					"user_no": new_user_no,
					"user_id": req.user_id,
					"user_name": req.user_name,
				}
			],
		}
	)


@router.post("/login", response_model=None)
def login(req: UserLoginRequest):
	db = SQLiteDB()
	user = db.VerifyUser(req.user_id, _hash_password(req.user_passwd))
	if not user:
		return JSONResponse(
			status_code=401,
			content=error_response("아이디 또는 비밀번호가 올바르지 않습니다."),
		)

	return ok_response(
		{
			"data": "로그인 성공",
			"datalist": [user],
		}
	)
