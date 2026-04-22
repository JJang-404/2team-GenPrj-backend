import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.common.util import error_response, ok_response
from app.models.openai import OpenAiJob
from ._model_job_store import _create_async_job, _build_job_status_response, _build_job_result_response


router = APIRouter(prefix="/addhelper/adver", tags=["addhelper-adver"])
class AdCopyRequest(BaseModel):
	input_text: str = Field(..., min_length=1)
	tone: str | None = None
	target_audience: str | None = None
	count: int = Field(default=3, ge=1, le=5)

class DualPromptRequest(BaseModel):
	opt: int = Field(..., ge=0)
	user_prompt: str | None = None
	positive_prompt: str | None = None
	negative_prompt: str | None = None
	input_text: str = Field(..., min_length=1)
	

@router.post("/generate", response_model=None)
def generate_ad_copy(req: AdCopyRequest):
	try:
		openai_job = OpenAiJob()
		ad_copy = openai_job.build_ad_copy(
			input_text=req.input_text,
			tone=req.tone,
			target_audience=req.target_audience,
			count=req.count,
		)
		return ok_response(
			{
				"data": ad_copy.main_copy,
				"datalist": ad_copy.variants,
			}
		)
	except Exception as ex:
		return JSONResponse(
			content=error_response(str(ex)),
		)


# 동기 구현 분리
def make_daul_prompt_sync_impl(req: DualPromptRequest) -> tuple[bytes, str]:
	openai_job = OpenAiJob()
	user_prompt = req.user_prompt or ""
	positive_prompt = req.positive_prompt or ""
	negative_prompt = req.negative_prompt or ""
	result = openai_job.build_prompt_dual_prompt_opt(
		opt=req.opt,
		user_prompt=user_prompt,
		positive_prompt=positive_prompt,
		negative_prompt=negative_prompt,
	)
	# dict를 json bytes로 반환
	return json.dumps(ok_response({"data": result}), ensure_ascii=False).encode("utf-8"), "application/json"

@router.post("/makedaulprompt", response_model=None)
def make_daul_prompt(req: DualPromptRequest):
	try:
		body, content_type = make_daul_prompt_sync_impl(req)
		return JSONResponse(content=json.loads(body.decode("utf-8")))
	except Exception as ex:
		return JSONResponse(
			content=error_response(str(ex)),
		)

# 비동기 잡 생성
@router.post("/makedaulprompt/jobs")
async def create_makedaulprompt_job(req: DualPromptRequest):
	job = _create_async_job("makedaulprompt", lambda: make_daul_prompt_sync_impl(req))
	return JSONResponse(content=job)

# 잡 상태 조회
@router.get("/makedaulprompt/jobs/{job_id}")
def get_makedaulprompt_job(job_id: str):
	return _build_job_status_response("makedaulprompt", job_id)

# 잡 결과 조회
@router.get("/makedaulprompt/jobs/{job_id}/result")
def get_makedaulprompt_job_result(job_id: str):
	return _build_job_result_response("makedaulprompt", job_id)
	