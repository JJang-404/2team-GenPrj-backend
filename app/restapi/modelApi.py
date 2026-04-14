
import base64
import json
import threading
import time
import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from typing import Any, Callable
from pydantic import BaseModel, Field
import configparser
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from app.common import defines
from app.common.util import ok_response, error_response
from app.models.gemma4ollama import Gemma4OllamaService
from app.models.openai import ChangeImageRequest, OpenAiJob, PromptBundle

router = APIRouter(prefix="/addhelper/model", tags=["addhelper-model"])

_ENGINE_JOB_POLL_INTERVAL_SECONDS = 1.0
_ASYNC_JOB_STORES: dict[str, dict[str, dict[str, Any]]] = {
    "generate": {},
    "changeimage": {},
    "makebgimage": {},
    "makebgimageollama": {},
}
_ASYNC_JOB_STORE_LOCK = threading.Lock()

# 성공 응답 포맷 생성 함수
def get_ok_response(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return ok_response(extra)

# 에러 응답 포맷 생성 함수
def get_error_response(message: str) -> dict[str, Any]:
    return error_response(message)


def _get_engine_base_url() -> str:
    default_url = "https://nabidream.duckdns.org/model/"
    if not defines.BACKEND_INI_PATH or not os.path.exists(defines.BACKEND_INI_PATH):
        return default_url

    config = configparser.ConfigParser()
    config.read(defines.BACKEND_INI_PATH, encoding="utf-8")
    url = config.get("engine", "engine_url", fallback=default_url).strip()
    return (url or default_url).rstrip("/")


def _get_engine_wait_time() -> int:
    default_wait_time = 600
    if not defines.BACKEND_INI_PATH or not os.path.exists(defines.BACKEND_INI_PATH):
        return default_wait_time

    config = configparser.ConfigParser()
    config.read(defines.BACKEND_INI_PATH, encoding="utf-8")

    try:
        wait_time = config.getint("engine", "wait_time", fallback=default_wait_time)
    except Exception:
        return default_wait_time

    return wait_time if wait_time > 0 else default_wait_time


def _build_prompt_bundle(
    prompt: str,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> PromptBundle:
    translator = OpenAiJob()
    prompt_bundle = translator.build_prompt_bundle(
        prompt=prompt,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
    )
    print(f"Positive prompt: {prompt_bundle.positive_prompt}")
    print(f"Negative prompt: {prompt_bundle.negative_prompt}")
    return prompt_bundle


def _extract_text_from_image_base64(raw_base64: str, task_prompt: str) -> str:
    engine_url = _get_engine_base_url()
    wait_time = _get_engine_wait_time()
    image2text_url = f"{engine_url}/image2text"
    payload = {
        "image_base64": raw_base64,
        "task_prompt": task_prompt,
    }
    request = Request(
        image2text_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=wait_time) as upstream_response:
        body = upstream_response.read()

    try:
        decoded = json.loads(body.decode("utf-8", errors="ignore"))
    except Exception as ex:
        raise RuntimeError("image2text 응답을 JSON으로 해석할 수 없습니다.") from ex

    text = ""
    if isinstance(decoded, dict):
        text = str(decoded.get("text") or decoded.get("caption") or decoded.get("data") or "").strip()

    if not text:
        raise RuntimeError("image2text 응답에 텍스트가 없습니다.")
    return text


def _decode_json_map(body: bytes, error_message: str) -> dict[str, Any]:
    try:
        decoded = json.loads(body.decode("utf-8", errors="ignore"))
    except Exception as ex:
        raise RuntimeError(error_message) from ex

    if not isinstance(decoded, dict):
        raise RuntimeError(error_message)
    return decoded


def _request_engine_json(
    url: str,
    timeout_seconds: float,
    method: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as upstream_response:
            body = upstream_response.read()
    except HTTPError as ex:
        error_body = ex.read()
        error_preview = error_body[:300].decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Upstream HTTP error: {ex.code} {ex.reason}. {error_preview}".strip()
        ) from ex
    except URLError as ex:
        raise RuntimeError(f"Upstream URL error: {ex.reason}") from ex

    return _decode_json_map(body, "업스트림 응답을 JSON으로 해석할 수 없습니다.")


def _fetch_engine_job_result(job_result_url: str, timeout_seconds: float) -> tuple[bytes, str]:
    request = Request(job_result_url, method="GET")

    try:
        with urlopen(request, timeout=timeout_seconds) as upstream_response:
            body = upstream_response.read()
            content_type = upstream_response.headers.get_content_type()
    except HTTPError as ex:
        error_body = ex.read()
        error_preview = error_body[:300].decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Upstream HTTP error: {ex.code} {ex.reason}. {error_preview}".strip()
        ) from ex
    except URLError as ex:
        raise RuntimeError(f"Upstream URL error: {ex.reason}") from ex

    return body, content_type


def _run_engine_image_job(job_path: str, payload: dict[str, Any]) -> tuple[bytes, str]:
    engine_url = _get_engine_base_url()
    wait_time = _get_engine_wait_time()
    create_url = f"{engine_url}{job_path}"
    create_response = _request_engine_json(
        url=create_url,
        timeout_seconds=wait_time,
        method="POST",
        payload=payload,
    )

    job_id = str(create_response.get("job_id") or "").strip()
    status = str(create_response.get("status") or "queued").strip().lower()
    if not job_id:
        raise RuntimeError("Upstream job create 응답에 job_id가 없습니다.")

    print(f"[engine-job] created path={job_path}, job_id={job_id}, status={status}")

    deadline = time.monotonic() + wait_time
    last_status = ""

    while True:
        if status == "done":
            break
        if status == "failed":
            error_message = str(create_response.get("error") or "").strip()
            raise RuntimeError(error_message or f"업스트림 작업이 실패했습니다. job_id={job_id}")
        if status not in {"queued", "running", ""}:
            raise RuntimeError(f"알 수 없는 업스트림 작업 상태입니다. status={status}")

        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise TimeoutError(f"업스트림 작업 대기 시간이 초과되었습니다. job_id={job_id}")

        status_url = f"{engine_url}{job_path}/{job_id}"
        status_response = _request_engine_json(
            url=status_url,
            timeout_seconds=max(1.0, min(wait_time, remaining_seconds)),
            method="GET",
        )
        status = str(status_response.get("status") or "").strip().lower()
        if status != last_status:
            print(f"[engine-job] polled path={job_path}, job_id={job_id}, status={status}")
            last_status = status
        if status == "failed":
            error_message = str(status_response.get("error") or "").strip()
            raise RuntimeError(error_message or f"업스트림 작업이 실패했습니다. job_id={job_id}")
        if status == "done":
            break

        time.sleep(min(_ENGINE_JOB_POLL_INTERVAL_SECONDS, max(0.0, deadline - time.monotonic())))

    result_url = f"{engine_url}{job_path}/{job_id}/result"
    print(f"[engine-job] fetching result path={job_path}, job_id={job_id}")
    result_body, content_type = _fetch_engine_job_result(
        job_result_url=result_url,
        timeout_seconds=max(1.0, min(wait_time, deadline - time.monotonic() + 1.0)),
    )
    print(
        "[engine-job] result fetched "
        f"path={job_path}, job_id={job_id}, content_type={content_type}, body_len={len(result_body)}"
    )
    return result_body, content_type


class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    positive_prompt: str | None = None
    negative_prompt: str | None = None


class MakeBgImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="배경 생성 스타일/분위기 지시 프롬프트")
    image_base64: str = Field(..., min_length=1, description="Base64 encoded image bytes")
    task_prompt: str = Field(default="<DETAILED_CAPTION>", description="업스트림 image2text task prompt")
    positive_prompt: str | None = Field(default=None, description="추가 positive prompt")
    negative_prompt: str | None = Field(default=None, description="추가 negative prompt")


def _create_image_response(body: bytes, content_type: str) -> Response:
    if not content_type.startswith("image/"):
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response("Upstream did not return image data."))
        out_map["upstream_content_type"] = content_type
        out_map["upstream_body_preview"] = body[:300].decode("utf-8", errors="ignore")
        return JSONResponse(content=out_map)

    return Response(content=body, media_type=content_type)


def _strip_and_validate_image_base64(image_base64: str, empty_message: str) -> str:
    raw_base64 = (image_base64 or "").strip()
    if not raw_base64:
        raise ValueError(empty_message)

    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]

    try:
        base64.b64decode(raw_base64, validate=True)
    except Exception as ex:
        raise ValueError("유효한 base64 이미지가 아닙니다.") from ex

    return raw_base64


def _get_async_job(job_kind: str, job_id: str) -> dict[str, Any] | None:
    with _ASYNC_JOB_STORE_LOCK:
        job = _ASYNC_JOB_STORES[job_kind].get(job_id)
        return dict(job) if job is not None else None


def _update_async_job(job_kind: str, job_id: str, **updates: Any) -> None:
    with _ASYNC_JOB_STORE_LOCK:
        job = _ASYNC_JOB_STORES[job_kind].get(job_id)
        if job is None:
            return
        job.update(updates)


def _run_async_job(job_kind: str, job_id: str, runner: Callable[[], tuple[bytes, str]]) -> None:
    _update_async_job(job_kind, job_id, status="running")
    try:
        body, content_type = runner()
    except Exception as ex:
        print(f"[async-job Error] kind={job_kind}, job_id={job_id}, error={type(ex).__name__}: {ex}")
        _update_async_job(job_kind, job_id, status="failed", error=str(ex))
        return

    _update_async_job(
        job_kind,
        job_id,
        status="done",
        error=None,
        result_body=body,
        content_type=content_type,
    )


def _create_async_job(job_kind: str, runner: Callable[[], tuple[bytes, str]]) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    with _ASYNC_JOB_STORE_LOCK:
        _ASYNC_JOB_STORES[job_kind][job_id] = {
            "job_id": job_id,
            "status": "queued",
            "error": None,
            "content_type": None,
            "result_body": None,
        }

    worker = threading.Thread(
        target=_run_async_job,
        args=(job_kind, job_id, runner),
        daemon=True,
    )
    worker.start()
    return {"job_id": job_id, "status": "queued"}


def _build_job_status_response(job_kind: str, job_id: str) -> JSONResponse:
    job = _get_async_job(job_kind, job_id)
    if job is None:
        return JSONResponse(content={"detail": "존재하지 않는 job_id입니다."}, status_code=404)

    return JSONResponse(
        content={
            "job_id": job_id,
            "status": job.get("status"),
            "error": job.get("error"),
        }
    )


def _build_job_result_response(job_kind: str, job_id: str) -> Response:
    job = _get_async_job(job_kind, job_id)
    if job is None:
        return JSONResponse(content={"detail": "존재하지 않는 job_id입니다."}, status_code=404)

    status = str(job.get("status") or "")
    if status in {"queued", "running"}:
        return JSONResponse(
            content={"detail": f"작업이 아직 완료되지 않았습니다. status={status}"},
            status_code=409,
        )
    if status == "failed":
        return JSONResponse(
            content={"detail": str(job.get("error") or "작업이 실패했습니다.")},
            status_code=500,
        )

    result_body = job.get("result_body")
    content_type = str(job.get("content_type") or "application/octet-stream")
    if not isinstance(result_body, bytes):
        return JSONResponse(content={"detail": "작업 결과가 없습니다."}, status_code=500)

    return Response(content=result_body, media_type=content_type)


def _generate_image_sync_impl(
    prompt: str,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> tuple[bytes, str]:
    prompt_bundle = _build_prompt_bundle(
        prompt=prompt,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
    )
    payload = {
        "positive_prompt": prompt_bundle.positive_prompt,
        "negative_prompt": prompt_bundle.negative_prompt,
    }
    return _run_engine_image_job("/generate/jobs", payload)


def _changeimage_sync_impl(req: ChangeImageRequest) -> tuple[bytes, str]:
    if req.strength < 0.0 or req.strength > 1.0:
        raise ValueError("strength는 0.0~1.0 범위여야 합니다.")

    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")
    prompt_bundle = _build_prompt_bundle(
        prompt=req.prompt,
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
    )
    payload = {
        "positive_prompt": prompt_bundle.positive_prompt,
        "negative_prompt": prompt_bundle.negative_prompt,
        "image_base64": raw_base64,
        "strength": req.strength,
    }
    return _run_engine_image_job("/changeimage/jobs", payload)


def _makebgimageollama_sync_impl(req: MakeBgImageRequest) -> tuple[bytes, str]:
    print(
        "[makebgimageollama] request received "
        f"prompt_len={len((req.prompt or '').strip())}, "
        f"has_positive={bool((req.positive_prompt or '').strip())}, "
        f"has_negative={bool((req.negative_prompt or '').strip())}, "
        f"image_base64_len={len((req.image_base64 or '').strip())}"
    )
    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")

    print("[makebgimageollama] creating Gemma4OllamaService")
    gemma_service = Gemma4OllamaService()
    print("[makebgimageollama] generating prompt bundle via ollama")
    prompt_bundle = gemma_service.generate_background_prompt_bundle(
        raw_base64=raw_base64,
        prompt=req.prompt,
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
    )
    print(
        "[makebgimageollama] prompt bundle generated "
        f"positive_len={len(prompt_bundle.positive_prompt)}, "
        f"negative_len={len(prompt_bundle.negative_prompt)}"
    )

    payload = {
        "positive_prompt": prompt_bundle.positive_prompt,
        "negative_prompt": prompt_bundle.negative_prompt,
    }
    print("[makebgimageollama] calling upstream generate jobs flow")
    body, content_type = _run_engine_image_job("/generate/jobs", payload)
    print(
        "[makebgimageollama] upstream response received "
        f"content_type={content_type}, body_len={len(body)}"
    )
    return body, content_type


def _makebgimage_sync_impl(req: MakeBgImageRequest) -> tuple[bytes, str]:
    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")
    caption_text = _extract_text_from_image_base64(
        raw_base64=raw_base64,
        task_prompt=(req.task_prompt or "<DETAILED_CAPTION>").strip() or "<DETAILED_CAPTION>",
    )

    translator = OpenAiJob()
    prompt_bundle = translator.build_background_prompt_bundle(
        caption_text=caption_text,
        user_prompt=req.prompt,
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
    )
    prompt_bundle = PromptBundle(
        positive_prompt=translator.change_kor_to_eng(prompt_bundle.positive_prompt),
        negative_prompt=translator.change_kor_to_eng(prompt_bundle.negative_prompt),
    )
    print(
        "[makebgimage] english normalized "
        f"positive_len={len(prompt_bundle.positive_prompt)}, "
        f"negative_len={len(prompt_bundle.negative_prompt)}"
    )

    payload = {
        "positive_prompt": prompt_bundle.positive_prompt,
        "negative_prompt": prompt_bundle.negative_prompt,
    }
    print("[makebgimage] calling upstream generate jobs flow")
    return _run_engine_image_job("/generate/jobs", payload)


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

