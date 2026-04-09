import json
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.common.util import error_response, ok_response
from app.db.SQLiteDB import SQLiteDB


router = APIRouter(prefix="/addhelper/design", tags=["addhelper-design"])


class DesignListRequest(BaseModel):
	user_id: str = Field(..., min_length=1)


@router.post("/saveprofile", response_model=None)
def save_design_profile(payload: Any = Body(default=None)):
	if payload is None:
		return JSONResponse(
			content=error_response("payload는 필수입니다."),
		)

	if not isinstance(payload, dict):
		return JSONResponse(
			content=error_response("payload는 JSON object 형태여야 합니다."),
		)

	user_id = str(payload.get("user_id", "")).strip()
	if not user_id:
		return JSONResponse(
			content=error_response("payload 내부 user_id는 필수입니다."),
		)

	try:
		profile_id = int(payload.get("profile_id", 0))
	except (TypeError, ValueError):
		return JSONResponse(
			content=error_response("payload 내부 profile_id는 숫자여야 합니다."),
		)

	if profile_id < 0:
		return JSONResponse(
			content=error_response("payload 내부 profile_id는 0 이상이어야 합니다."),
		)

	raw_ai_image_id = payload.get("ai_image_id", None)
	if raw_ai_image_id in (None, ""):
		ai_image_id = None
	else:
		try:
			parsed_ai_image_id = int(raw_ai_image_id)
		except (TypeError, ValueError):
			return JSONResponse(
				content=error_response("payload 내부 ai_image_id는 숫자 또는 null 이어야 합니다."),
			)
		ai_image_id = parsed_ai_image_id if parsed_ai_image_id > 0 else None

	print(f'user_id={user_id}, profile_id={profile_id}, ai_image_id={ai_image_id}, Received design profile: {payload}')

	try:
		db = SQLiteDB()
		profile_json = json.dumps(payload, ensure_ascii=False)
		saved_profile_id, save_msg = db.SaveDesignProfile(
			profile_id=profile_id,
			user_id=user_id,
			profile_json=profile_json,
			ai_image_id=ai_image_id,
		)
		if saved_profile_id <= 0:
			return JSONResponse(content=error_response(save_msg))

		return ok_response(
			{
				"data": "디자인 프로파일 저장 성공",
				"datalist": [
					{
						"profile_id": saved_profile_id,
						"user_id": user_id,
						"profile_json": profile_json,
						"ai_image_id": ai_image_id,
					}
				],
			}
		)
	except Exception as ex:
		return JSONResponse(
			content=error_response(str(ex)),
		)


@router.post("/list", response_model=None)
def list_design_profiles(req: DesignListRequest):
	try:
		db = SQLiteDB()
		rows = db.GetDesignProfilesByUserId(req.user_id)
		return ok_response(
			{
				"data": "디자인 프로파일 조회 성공",
				"datalist": rows,
			}
		)
	except Exception as ex:
		return JSONResponse(
			content=error_response(str(ex)),
		)
