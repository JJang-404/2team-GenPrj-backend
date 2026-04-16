
from fastapi import Body, APIRouter
router = APIRouter(prefix="/addhelper/model", tags=["addhelper-model"])
import uuid
import threading
vlmgpt_jobs = {}

def _run_vlmgpt_job(job_id, payload):
    try:
        image_base64 = payload.get("image_base64")
        if not image_base64:
            vlmgpt_jobs[job_id]["status"] = "failed"
            vlmgpt_jobs[job_id]["error"] = "image_base64 필수 입력"
            return
        if image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[-1]
        image_bytes = base64.b64decode(image_base64)
        client = comfyui.ComfyUIClient()
        vlm_text = client.florence_vlm(image_bytes=image_bytes, image_name="input.png")
        prompt = payload.get("prompt", "")
        positive_prompt = payload.get("positive_prompt", "")
        negative_prompt = payload.get("negative_prompt", "")
        openai_job = openai.OpenAiJob()
        prompt_bundle = openai_job.build_prompt_bundle(
            prompt=vlm_text if not prompt else prompt,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
        )
        images = client.generate_images(
            positive_text=prompt_bundle.positive_prompt,
            negative_text=prompt_bundle.negative_prompt,
        )
        if not images:
            vlmgpt_jobs[job_id]["status"] = "failed"
            vlmgpt_jobs[job_id]["error"] = "ComfyUI 이미지 생성 실패"
            return
        image_bytes_out = images[0]
        image_base64_out = base64.b64encode(image_bytes_out).decode("utf-8")
        vlmgpt_jobs[job_id]["status"] = "done"
        vlmgpt_jobs[job_id]["result"] = {
            "vlm_text": vlm_text,
            "positive_prompt": prompt_bundle.positive_prompt,
            "negative_prompt": prompt_bundle.negative_prompt,
            "image_base64": image_base64_out,
            "content_type": "image/png",
        }
    except Exception as ex:
        vlmgpt_jobs[job_id]["status"] = "failed"
        vlmgpt_jobs[job_id]["error"] = str(ex)

@router.post("/generate_vlm_gpt_image/jobs")
async def create_vlmgpt_job(payload: dict = Body(...)):
    job_id = str(uuid.uuid4())
    vlmgpt_jobs[job_id] = {"status": "queued"}
    thread = threading.Thread(target=_run_vlmgpt_job, args=(job_id, payload))
    thread.start()
    return {"job_id": job_id, "status": "queued"}

@router.get("/generate_vlm_gpt_image/jobs/{job_id}")
def get_vlmgpt_job(job_id: str):
    job = vlmgpt_jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job_id not found"})
    return {"job_id": job_id, "status": job["status"], "error": job.get("error")}

@router.get("/generate_vlm_gpt_image/jobs/{job_id}/result")
def get_vlmgpt_job_result(job_id: str):
    job = vlmgpt_jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job_id not found"})
    if job["status"] == "done":
        return job["result"]
    elif job["status"] == "failed":
        return JSONResponse(status_code=500, content={"error": job.get("error", "failed")})
    else:
        return JSONResponse(status_code=409, content={"error": "not ready"})
import base64
import tempfile
from app.models import comfyui, openai
from pathlib import Path
# VLM+GPT+ComfyUI 통합 이미지 생성 API
@router.post("/generate_vlm_gpt_image")
async def generate_vlm_gpt_image(
    payload: dict = Body(...)
):
    try:
        # 1. 이미지 디코딩
        image_base64 = payload.get("image_base64")
        if not image_base64:
            return JSONResponse(content=get_error_response("image_base64 필수 입력"))
        if image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[-1]
        image_bytes = base64.b64decode(image_base64)

        # 2. Florence VLM으로 이미지 설명 추출
        client = comfyui.ComfyUIClient()
        vlm_text = client.florence_vlm(image_bytes=image_bytes, image_name="input.png")

        # 3. GPT로 프롬프트 번들 최적화
        prompt = payload.get("prompt", "")
        positive_prompt = payload.get("positive_prompt", "")
        negative_prompt = payload.get("negative_prompt", "")
        openai_job = openai.OpenAiJob()
        prompt_bundle = openai_job.build_prompt_bundle(
            prompt=vlm_text if not prompt else prompt,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
        )

        # 4. ComfyUI로 이미지 생성 (positive_prompt/negative_prompt 사용)
        images = client.generate_images(
            positive_text=prompt_bundle.positive_prompt,
            negative_text=prompt_bundle.negative_prompt,
        )
        if not images:
            return JSONResponse(content=get_error_response("ComfyUI 이미지 생성 실패"))
        image_bytes_out = images[0]
        image_base64_out = base64.b64encode(image_bytes_out).decode("utf-8")

        return JSONResponse(content={
            "result": "ok",
            "vlm_text": vlm_text,
            "positive_prompt": prompt_bundle.positive_prompt,
            "negative_prompt": prompt_bundle.negative_prompt,
            "image_base64": image_base64_out,
            "content_type": "image/png",
        })
    except Exception as ex:
        return JSONResponse(content={
            "result": "error",
            "error": str(ex),
        })


from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from app.common.util import ok_response, error_response
from app.models.openai import ChangeImageRequest

from ._model_engine import (
    GenerateImageRequest,
    MakeBgImageRequest,
    _changeimage_sync_impl,
    _generate_image_sync_impl,
    _makebgimage_sync_impl,
)
from ._model_job_store import (
    _build_job_result_response,
    _build_job_status_response,
    _create_async_job,
)
from ._model_ollama import _makebgimageollama_sync_impl
from ._model_comfyui import (
    ChangeImageComfyUiRequest,
    GenerateComfyUiRequest,
    _changeimagecomfyui_sync_impl,
    _generate_image_comfyui_sync_impl,
    _makebgimagecomfyui_sync_impl,
)



def get_ok_response(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return ok_response(extra)


def get_error_response(message: str) -> dict[str, Any]:
    return error_response(message)


def _create_image_response(body: bytes, content_type: str) -> Response:
    if not content_type.startswith("image/"):
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response("Upstream did not return image data."))
        out_map["upstream_content_type"] = content_type
        out_map["upstream_body_preview"] = body[:300].decode("utf-8", errors="ignore")
        return JSONResponse(content=out_map)
    return Response(content=body, media_type=content_type)


# 필요에 따라 추가 엔드포인트 구현 가능
@router.get("/test")
def test_connection() -> dict[str, Any]:
    return get_ok_response({"data": "접속 테스트 성공"})


@router.get("/generate_sync")
def generate_image_sync(
    prompt: str,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> Response:
    try:
        body, content_type = _generate_image_sync_impl(prompt, positive_prompt, negative_prompt)
        return _create_image_response(body, content_type)
    except Exception as ex:
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response(str(ex)))
        return JSONResponse(content=out_map)


@router.post("/generate/jobs")
async def create_generate_job(req: GenerateImageRequest) -> JSONResponse:
    job = _create_async_job(
        "generate",
        lambda: _generate_image_sync_impl(req.prompt, req.positive_prompt, req.negative_prompt),
    )
    return JSONResponse(content=job)


@router.get("/generate/jobs/{job_id}")
def get_generate_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("generate", job_id)


@router.get("/generate/jobs/{job_id}/result")
def get_generate_job_result(job_id: str) -> Response:
    return _build_job_result_response("generate", job_id)


@router.post("/makebgimagecomfyui_sync")
async def makebgimagecomfyui_sync(req: MakeBgImageRequest) -> Response:
    try:
        body, content_type = _makebgimagecomfyui_sync_impl(req)
        return _create_image_response(body, content_type)
    except Exception as ex:
        print(f"[makebgimagecomfyui Error] {type(ex).__name__}: {ex}")
        return JSONResponse(content=get_error_response(str(ex)))


@router.post("/changeimage_sync")
async def changeimage_sync(req: ChangeImageRequest) -> Response:
    try:
        body, content_type = _changeimage_sync_impl(req)
        return _create_image_response(body, content_type)
    except Exception as ex:
        return JSONResponse(content=get_error_response(str(ex)))


@router.post("/changeimage/jobs")
async def create_changeimage_job(req: ChangeImageRequest) -> JSONResponse:
    job = _create_async_job("changeimage", lambda: _changeimage_sync_impl(req))
    return JSONResponse(content=job)


@router.get("/changeimage/jobs/{job_id}")
def get_changeimage_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("changeimage", job_id)


@router.get("/changeimage/jobs/{job_id}/result")
def get_changeimage_job_result(job_id: str) -> Response:
    return _build_job_result_response("changeimage", job_id)


@router.post("/makebgimageollama_sync")
async def makebgimageollama_sync(req: MakeBgImageRequest) -> Response:
    try:
        body, content_type = _makebgimageollama_sync_impl(req)
        return _create_image_response(body, content_type)
    except Exception as ex:
        print(f"[makebgimageollama Error] {type(ex).__name__}: {ex}")
        return JSONResponse(content=get_error_response(str(ex)))


@router.post("/makebgimageollama/jobs")
async def create_makebgimageollama_job(req: MakeBgImageRequest) -> JSONResponse:
    job = _create_async_job("makebgimageollama", lambda: _makebgimageollama_sync_impl(req))
    return JSONResponse(content=job)


@router.get("/makebgimageollama/jobs/{job_id}")
def get_makebgimageollama_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("makebgimageollama", job_id)


@router.get("/makebgimageollama/jobs/{job_id}/result")
def get_makebgimageollama_job_result(job_id: str) -> Response:
    return _build_job_result_response("makebgimageollama", job_id)


@router.post("/makebgimage_sync")
async def makebgimage_sync(req: MakeBgImageRequest) -> Response:
    try:
        body, content_type = _makebgimage_sync_impl(req)
        return _create_image_response(body, content_type)
    except Exception as ex:
        return JSONResponse(content=get_error_response(str(ex)))


@router.post("/makebgimage/jobs")
async def create_makebgimage_job(req: MakeBgImageRequest) -> JSONResponse:
    job = _create_async_job("makebgimage", lambda: _makebgimage_sync_impl(req))
    return JSONResponse(content=job)


@router.get("/makebgimage/jobs/{job_id}")
def get_makebgimage_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("makebgimage", job_id)


@router.get("/makebgimage/jobs/{job_id}/result")
def get_makebgimage_job_result(job_id: str) -> Response:
    return _build_job_result_response("makebgimage", job_id)


@router.get("/generatecomfyui_sync")
def generate_imagecomfyui_sync(
    prompt: str | None = None,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> Response:
    try:
        body, content_type = _generate_image_comfyui_sync_impl(prompt, positive_prompt, negative_prompt)
        return _create_image_response(body, content_type)
    except Exception as ex:
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response(str(ex)))
        return JSONResponse(content=out_map)


@router.post("/generatecomfyui/jobs")
async def create_generatecomfyui_job(req: GenerateComfyUiRequest) -> JSONResponse:
    job = _create_async_job(
        "generatecomfyui",
        lambda: _generate_image_comfyui_sync_impl(req.prompt, req.positive_prompt, req.negative_prompt),
    )
    return JSONResponse(content=job)


@router.get("/generatecomfyui/jobs/{job_id}")
def get_generatecomfyui_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("generatecomfyui", job_id)


@router.get("/generatecomfyui/jobs/{job_id}/result")
def get_generatecomfyui_job_result(job_id: str) -> Response:
    return _build_job_result_response("generatecomfyui", job_id)


@router.post("/changeimagecomfyui_sync")
async def changeimagecomfyui_sync(req: ChangeImageComfyUiRequest) -> Response:
    try:
        body, content_type = _changeimagecomfyui_sync_impl(req)
        return _create_image_response(body, content_type)
    except Exception as ex:
        return JSONResponse(content=get_error_response(str(ex)))


@router.post("/changeimagecomfyui/jobs")
async def create_changeimagecomfyui_job(req: ChangeImageComfyUiRequest) -> JSONResponse:
    job = _create_async_job("changeimagecomfyui", lambda: _changeimagecomfyui_sync_impl(req))
    return JSONResponse(content=job)


@router.get("/changeimagecomfyui/jobs/{job_id}")
def get_changeimagecomfyui_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("changeimagecomfyui", job_id)


@router.get("/changeimagecomfyui/jobs/{job_id}/result")
def get_changeimagecomfyui_job_result(job_id: str) -> Response:
    return _build_job_result_response("changeimagecomfyui", job_id)


@router.post("/makebgimagecomfyui/jobs")
async def create_makebgimagecomfyui_job(req: MakeBgImageRequest) -> JSONResponse:
    job = _create_async_job("makebgimagecomfyui", lambda: _makebgimagecomfyui_sync_impl(req))
    return JSONResponse(content=job)


@router.get("/makebgimagecomfyui/jobs/{job_id}")
def get_makebgimagecomfyui_job(job_id: str) -> JSONResponse:
    return _build_job_status_response("makebgimagecomfyui", job_id)


@router.get("/makebgimagecomfyui/jobs/{job_id}/result")
def get_makebgimagecomfyui_job_result(job_id: str) -> Response:
    return _build_job_result_response("makebgimagecomfyui", job_id)


