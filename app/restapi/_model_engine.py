import base64
import configparser
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from app.common import defines
from app.models.openai import ChangeImageRequest, OpenAiJob, PromptBundle

_ENGINE_JOB_POLL_INTERVAL_SECONDS = 1.0


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


# ── 설정 읽기 ─────────────────────────────────────────────────────────────────

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


# ── 공유 유틸리티 ──────────────────────────────────────────────────────────────

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


# ── 엔진 HTTP 유틸리티 ─────────────────────────────────────────────────────────

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


# ── 엔진 sync 구현 ─────────────────────────────────────────────────────────────

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
