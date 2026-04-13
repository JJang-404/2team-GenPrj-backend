from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.common.util import error_response, ok_response
from app.models.openai import OpenAiJob


router = APIRouter(prefix="/addhelper/adver", tags=["addhelper-adver"])


class AdCopyRequest(BaseModel):
	input_text: str = Field(..., min_length=1)
	tone: str | None = None
	target_audience: str | None = None
	count: int = Field(default=3, ge=1, le=5)


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
	