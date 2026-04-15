from app.models.gemma4ollama import Gemma4OllamaService

from ._model_engine import (
    MakeBgImageRequest,
    _run_engine_image_job,
    _strip_and_validate_image_base64,
)


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
