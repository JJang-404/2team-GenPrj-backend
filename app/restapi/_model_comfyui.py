import base64

from pydantic import BaseModel, Field

from app.models.comfyui import ComfyUIClient
from app.models.openai import OpenAiJob, PromptBundle

from ._model_engine import (
    MakeBgImageRequest,
    _extract_text_from_image_base64,
    _strip_and_validate_image_base64,
)


class GenerateComfyUiRequest(BaseModel):
    prompt: str | None = ""
    positive_prompt: str | None = None
    negative_prompt: str | None = None


class ChangeImageComfyUiRequest(BaseModel):
    prompt: str | None = ""
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    image_base64: str = Field(..., min_length=1)
    strength: float = Field(default=0.45, ge=0.0, le=1.0)


def _create_comfyui_client() -> ComfyUIClient:
    return ComfyUIClient()


def _extract_first_comfyui_image(images: list[bytes]) -> tuple[bytes, str]:
    if not images:
        raise RuntimeError("ComfyUI 결과 이미지가 없습니다.")
    return images[0], "image/png"


def _build_comfyui_prompt_bundle(
    prompt: str | None,
    positive_prompt: str | None,
    negative_prompt: str | None,
) -> PromptBundle:
    normalized_prompt = (prompt or "").strip()
    normalized_positive = (positive_prompt or "").strip()
    normalized_negative = (negative_prompt or "").strip()

    # ComfyUI는 최종적으로 positive/negative 텍스트만 받으므로,
    # prompt가 있으면 OpenAI로 positive/negative를 보완하고 결과를 영문화해 전달한다.
    if not normalized_prompt and not normalized_positive:
        raise ValueError("ComfyUI 요청은 prompt 또는 positive_prompt 중 하나가 필요합니다.")

    translator = OpenAiJob()
    bundle = translator.build_prompt_bundle(
        prompt=normalized_prompt,
        positive_prompt=normalized_positive,
        negative_prompt=normalized_negative,
    )
    positive_text = translator.change_kor_to_eng((bundle.positive_prompt or "").strip())
    negative_text = translator.change_kor_to_eng((bundle.negative_prompt or "").strip())

    if not positive_text:
        raise RuntimeError("ComfyUI용 positive_prompt를 생성하지 못했습니다.")

    return PromptBundle(
        positive_prompt=positive_text,
        negative_prompt=negative_text,
    )


def _generate_image_comfyui_sync_impl(
    prompt: str | None = None,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
) -> tuple[bytes, str]:
    prompt_bundle = _build_comfyui_prompt_bundle(
        prompt=prompt,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
    )
    client = _create_comfyui_client()
    images = client.generate_images(
        positive_text=prompt_bundle.positive_prompt,
        negative_text=prompt_bundle.negative_prompt,
    )
    return _extract_first_comfyui_image(images)


def _changeimagecomfyui_sync_impl(req: ChangeImageComfyUiRequest) -> tuple[bytes, str]:
    if req.strength < 0.0 or req.strength > 1.0:
        raise ValueError("strength는 0.0~1.0 범위여야 합니다.")

    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")
    image_bytes = base64.b64decode(raw_base64)
    prompt_bundle = _build_comfyui_prompt_bundle(
        prompt=req.prompt,
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
    )
    client = _create_comfyui_client()
    images = client.change_image(
        positive_text=prompt_bundle.positive_prompt,
        negative_text=prompt_bundle.negative_prompt,
        image_bytes=image_bytes,
        strength=req.strength,
    )
    return _extract_first_comfyui_image(images)


def _makebgimagecomfyui_sync_impl(req: MakeBgImageRequest) -> tuple[bytes, str]:
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
        "[makebgimagecomfyui] english normalized "
        f"positive_len={len(prompt_bundle.positive_prompt)}, "
        f"negative_len={len(prompt_bundle.negative_prompt)}"
    )

    client = _create_comfyui_client()
    images = client.generate_images(
        positive_text=prompt_bundle.positive_prompt,
        negative_text=prompt_bundle.negative_prompt,
    )
    return _extract_first_comfyui_image(images)
