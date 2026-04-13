from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.common import defines
from app.common.util import error_response, ok_response
from app.db.SQLiteDB import SQLiteDB


router = APIRouter(prefix="/addhelper/image", tags=["addhelper-image"])


class ImageListRequest(BaseModel):
	user_id: str | None = None
	file_name: str | None = None
	file_desc: str | None = None


class ImageInfoRequest(BaseModel):
	image_id: int


def _normalize_ext(upload_file: UploadFile) -> str:
	content_type = (upload_file.content_type or "").lower()
	file_suffix = Path(upload_file.filename or "").suffix.lower()
	if content_type == "image/png" or file_suffix == ".png":
		return ".png"
	if content_type in ("image/jpeg", "image/jpg") or file_suffix in (".jpg", ".jpeg"):
		return ".jpg"
	return ""


@router.post("/upload", response_model=None)
async def upload_image(
	user_id: str = Form(...),
	file_desc: str = Form(default=""),
	image: UploadFile = File(...),
):
	db = SQLiteDB()
	if not db.GetUserById(user_id):
		return JSONResponse(content=error_response("존재하지 않는 사용자입니다."))

	file_ext = _normalize_ext(image)
	if not file_ext:
		return JSONResponse(content=error_response("png 또는 jpg 파일만 업로드할 수 있습니다."))

	file_bytes = await image.read()
	if not file_bytes:
		return JSONResponse(content=error_response("빈 파일은 업로드할 수 없습니다."))

	month_folder = datetime.now().strftime("%Y%m")
	target_dir = Path(defines.IMAGES_DIR) / month_folder
	target_dir.mkdir(parents=True, exist_ok=True)

	# uuid4 문자열은 하이픈 포함 36자리이며 충돌 가능성이 매우 낮습니다.
	stored_name = f"{uuid4()}{file_ext}"
	target_path = target_dir / stored_name
	while target_path.exists():
		stored_name = f"{uuid4()}{file_ext}"
		target_path = target_dir / stored_name

	target_path.write_bytes(file_bytes)
	relative_path = str(Path("images") / month_folder / stored_name)
	content_type = (image.content_type or "").lower() or ("image/png" if file_ext == ".png" else "image/jpeg")

	image_id = db.InsertUserImage(
		user_id=user_id,
		original_name=image.filename or stored_name,
		file_desc=(file_desc or "").strip(),
		stored_name=stored_name,
		stored_path=relative_path,
		content_type=content_type,
		file_ext=file_ext,
		file_size=len(file_bytes),
	)

	return ok_response(
		{
			"data": "이미지 업로드 성공",
			"datalist": [
				{
					"image_id": image_id,
					"user_id": user_id,
					"file_desc": (file_desc or "").strip(),
					"stored_name": stored_name,
					"stored_path": relative_path,
					"content_type": content_type,
					"file_size": len(file_bytes),
				}
			],
		}
	)


@router.post("/list", response_model=None)
def list_images(req: ImageListRequest):
	if req.user_id is None and not (req.file_name or "").strip() and not (req.file_desc or "").strip():
		return JSONResponse(
			content=error_response("user_id, file_name, file_desc 중 하나 이상은 필요합니다."),
		)

	db = SQLiteDB()
	rows = db.FindUserImages(user_id=req.user_id, file_name=req.file_name, file_desc=req.file_desc)
	return ok_response(
		{
			"data": "이미지 목록 조회 성공",
			"datalist": rows,
		}
	)


@router.post("/info", response_model=None)
def get_image_info_by_id(req: ImageInfoRequest):
	db = SQLiteDB()
	image_row = db.GetUserImageById(req.image_id)
	if not image_row:
		return JSONResponse(content=error_response("이미지 정보가 없습니다."))
	return ok_response({"data": "이미지 조회 성공", "datalist": [image_row]})


@router.post("/download", response_model=None)
def download_image_by_id(req: ImageInfoRequest):
	db = SQLiteDB()
	image_row = db.GetUserImageById(req.image_id)
	if not image_row:
		return JSONResponse(content=error_response("이미지 정보가 없습니다."))

	absolute_path = Path(defines.DATA_DIR) / image_row["stored_path"]
	if not absolute_path.exists():
		return JSONResponse(content=error_response("이미지 파일이 존재하지 않습니다."))

	return FileResponse(
		path=str(absolute_path),
		media_type=image_row["content_type"],
		filename=image_row["stored_name"],
	)

    