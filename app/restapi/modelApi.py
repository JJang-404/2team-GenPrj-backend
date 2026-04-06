
import base64
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from typing import Any
import configparser
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from app.common import defines
from app.common.util import ok_response, error_response
from app.models.openapi import ChangeImageRequest, OpenAiJob

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


# 필요에 따라 추가 엔드포인트 구현 가능
@router.get("/test")
def test_connection() -> dict[str, Any]:
    return get_ok_response({"data": "접속 테스트 성공"})
 

# backend.ini의 [engine] engine_url(기본값: https://nabidream.duckdns.org/model/) 업스트림의 /generate를 호출하여 이미지를 반환합니다.
@router.get("/generate")
def generate_image(prompt: str) -> Response:
    try:

        # str로 들어온 prompt가 한글이므로 OpenAiJob 의 메소드를 이용해서 영문으로 변경해 주세요
        
        translator = OpenAiJob()
        prompt = translator.change_kor_to_eng(prompt)
        print(f"Translated prompt: {prompt}")
        # 업스트림 이미지 생성 API 결과를 그대로 프록시하여 실제 이미지를 반환합니다.
        query = urlencode({"prompt": prompt})
        engine_url = _get_engine_base_url()
        image_url = f"{engine_url}/generate?{query}"
        request = Request(image_url, method="GET")

        with urlopen(request, timeout=300) as upstream_response:
            body = upstream_response.read()
            content_type = upstream_response.headers.get_content_type()

        if not content_type.startswith("image/"):
            out_map: dict[str, Any] = {}
            out_map.update(get_error_response("Upstream did not return image data."))
            out_map["upstream_content_type"] = content_type
            out_map["upstream_body_preview"] = body[:300].decode("utf-8", errors="ignore")
            return JSONResponse(status_code=502, content=out_map)

        return Response(content=body, media_type=content_type)
    except Exception as ex:
        out_map: dict[str, Any] = {}
        out_map.update(get_error_response(str(ex)))
        return JSONResponse(status_code=500, content=out_map)


# backend.ini의 [engine] engine_url(기본값: https://nabidream.duckdns.org/model/) 업스트림의 /changeimage 호출하여 이미지를 반환합니다
@router.post("/changeimage")
async def changeimage(req: ChangeImageRequest) -> Response:
    if req.strength < 0.0 or req.strength > 1.0:
        return JSONResponse(
            status_code=400,
            content=get_error_response("strength는 0.0~1.0 범위여야 합니다."),
        )

    raw_base64 = (req.image_base64 or "").strip()
    if not raw_base64:
        return JSONResponse(
            status_code=400,
            content=get_error_response("image_base64는 필수입니다."),
        )

    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]

    try:
        # 유효한 base64 문자열인지 선검증 후 업스트림으로 전달합니다.
        base64.b64decode(raw_base64, validate=True)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=get_error_response("유효한 base64 이미지가 아닙니다."),
        )

    translator = OpenAiJob()
    translated_prompt = translator.change_kor_to_eng(req.prompt)
    print(f"Translated prompt: {translated_prompt}")

    try:
        engine_url = _get_engine_base_url()
        image_url = f"{engine_url}/changeimage"
        payload = {
            "prompt": translated_prompt,
            "image_base64": raw_base64,
            "strength": req.strength,
        }
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
            out_map["upstream_body_preview"] = body[:300].decode("utf-8", errors="ignore")
            return JSONResponse(status_code=502, content=out_map)

        return Response(content=body, media_type=content_type)
    except Exception as ex:
        return JSONResponse(status_code=500, content=get_error_response(str(ex)))


