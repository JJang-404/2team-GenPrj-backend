import base64
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from typing import Any
import configparser
import os
from urllib.request import Request, urlopen
from app.common import defines
from app.common.util import ok_response, error_response
from app.models.openai import ChangeImageRequest, OpenAiJob, PromptBundle

router = APIRouter(prefix="/addhelper/model", tags=["addhelper-model"])


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


# 필요에 따라 추가 엔드포인트 구현 가능
@router.get("/test")
def test_connection() -> dict[str, Any]:
    return get_ok_response({"data": "접속 테스트 성공"})


# backend.ini의 [engine] engine_url(기본값: https://nabidream.duckdns.org/model/) 업스트림의 /generate를 호출하여 이미지를 반환합니다.
@router.get("/generate")
def generate_image(
    prompt: str,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> Response:
    try:
        prompt_bundle = _build_prompt_bundle(
            prompt=prompt,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
        )
        # 업스트림 이미지 생성 API 결과를 그대로 프록시하여 실제 이미지를 반환합니다.
        engine_url = _get_engine_base_url()
        image_url = f"{engine_url}/generate"
        payload = {
            "positive_prompt": prompt_bundle.positive_prompt,
            "negative_prompt": prompt_bundle.negative_prompt,
        }
        request = Request(
            image_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=300) as upstream_response:
            body = upstream_response.read()
            content_type = upstream_response.headers.get_content_type()

        if not content_type.startswith("image/"):
            out_map: dict[str, Any] = {}
            out_map.update(get_error_response("Upstream did not return image data."))
            out_map["upstream_content_type"] = content_type
            out_map["upstream_body_preview"] = body[:300].decode(
                "utf-8", errors="ignore"
            )
            # 업그레이드: 이미지가 아닌 경우 500 에러를 반환하여 프론트엔드에서 catch되게 합니다.
            return JSONResponse(content=out_map, status_code=500)

        return Response(content=body, media_type=content_type)
    except Exception as ex:
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response(str(ex)))
        return JSONResponse(content=out_map, status_code=500)


# backend.ini의 [engine] engine_url(기본값: https://nabidream.duckdns.org/model/) 업스트림의 /changeimage 호출하여 이미지를 반환합니다
@router.post("/changeimage")
async def changeimage(req: ChangeImageRequest) -> Response:
    if req.strength < 0.0 or req.strength > 1.0:
        return JSONResponse(
            content=get_error_response("strength는 0.0~1.0 범위여야 합니다."),
        )

    raw_base64 = (req.image_base64 or "").strip()
    if not raw_base64:
        return JSONResponse(
            content=get_error_response("image_base64는 필수입니다."),
        )

    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]

    try:
        # 유효한 base64 문자열인지 선검증 후 업스트림으로 전달합니다.
        base64.b64decode(raw_base64, validate=True)
    except Exception:
        return JSONResponse(
            content=get_error_response("유효한 base64 이미지가 아닙니다."),
        )

    try:
        prompt_bundle = _build_prompt_bundle(
            prompt=req.prompt,
            positive_prompt=req.positive_prompt,
            negative_prompt=req.negative_prompt,
        )
        engine_url = _get_engine_base_url()
        image_url = f"{engine_url}/changeimage"
        payload = {
            "positive_prompt": prompt_bundle.positive_prompt,
            "negative_prompt": prompt_bundle.negative_prompt,
            "image_base64": raw_base64,
            "strength": req.strength,
        }

        # 마스크 이미지 처리
        raw_mask_base64 = (req.mask_base64 or "").strip()
        if raw_mask_base64:
            if "," in raw_mask_base64:
                raw_mask_base64 = raw_mask_base64.split(",", 1)[1]
            try:
                base64.b64decode(raw_mask_base64, validate=True)
                payload["mask_image_base64"] = raw_mask_base64
            except Exception:
                return JSONResponse(
                    content=get_error_response(
                        "유효한 base64 마스크 이미지가 아닙니다."
                    ),
                )

        request = Request(
            image_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=180) as upstream_response:
            body = upstream_response.read()
            content_type = upstream_response.headers.get_content_type()

        if not content_type.startswith("image/"):
            out_map: dict[str, Any] = {}
            out_map.update(get_error_response("Upstream did not return image data."))
            out_map["upstream_content_type"] = content_type
            try:
                out_map["upstream_body_preview"] = body[:300].decode(
                    "utf-8", errors="ignore"
                )
            except:
                pass
            return JSONResponse(content=out_map, status_code=500)

        return Response(content=body, media_type=content_type)

    except Exception as ex:
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response(str(ex)))
        return JSONResponse(content=out_map, status_code=500)
