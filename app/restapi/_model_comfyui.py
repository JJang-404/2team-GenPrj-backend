import base64

from pydantic import BaseModel, Field

from app.models.comfyui import ComfyUIClient
from app.models.gemma4ollama import Gemma4OllamaService
from app.models.openai import OpenAiJob, PromptBundle
import os
import uuid
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



class ChangeImageComfyUiRequest_opt(BaseModel):
    opt: int = Field(default=0, ge=0, le=2)
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



def _build_comfyui_prompt_bundle_opt(
    opt: int,
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
    bundle_map = translator.build_prompt_dual_prompt_opt(
        opt=opt,
        user_prompt=normalized_prompt,
        positive_prompt=normalized_positive,
        negative_prompt=normalized_negative,
    )
    if not isinstance(bundle_map, dict):
        raise RuntimeError("프롬프트 생성 결과가 올바르지 않습니다.")

    positive_text = translator.change_kor_to_eng(str(bundle_map.get("positive_prompt") or "").strip())
    negative_text = translator.change_kor_to_eng(str(bundle_map.get("negative_prompt") or "").strip())

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
    
    from pathlib import Path
    if req.strength < 0.0 or req.strength > 1.0:
        raise ValueError("strength는 0.0~1.0 범위여야 합니다.")

    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")
    image_bytes = base64.b64decode(raw_base64)
    prompt_bundle = _build_comfyui_prompt_bundle(
        prompt=req.prompt,
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
    )
    # 1. uuid로 파일명 생성
    file_uuid = str(uuid.uuid4())
    input_dir = Path(__file__).resolve().parents[2] / "data" / "comfyui" / "input"
    prompt_dir = Path(__file__).resolve().parents[2] / "data" / "comfyui" / "prompt"
    input_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    image_path = input_dir / f"{file_uuid}.png"
    prompt_path = prompt_dir / f"{file_uuid}.txt"
    # 2. 이미지 저장
    try:
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        print(f"[DEBUG] Saved input image: {image_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save input image: {image_path} - {e}")
    # 3. 프롬프트 저장
    try:
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(f"positive_prompt: {prompt_bundle.positive_prompt}\n")
            f.write(f"negative_prompt: {prompt_bundle.negative_prompt}\n")
        print(f"[DEBUG] Saved prompt: {prompt_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save prompt: {prompt_path} - {e}")
    # 4. comfyui에 업로드할 때 파일명 지정
    client = _create_comfyui_client()
    # change_image에서 업로드 파일명을 지정하고, 결과 이미지명도 반환하도록 comfyui.py를 수정해야 함
    images, result_image_name = client.change_image(
        positive_text=prompt_bundle.positive_prompt,
        negative_text=prompt_bundle.negative_prompt,
        image_bytes=image_bytes,
        strength=req.strength,
        image_name=f"{file_uuid}.png",
        return_result_image_name=True
    )
    # 5. 결과 이미지명으로 파일명 변경 (가능할 때만)
    if result_image_name:
        new_image_path = input_dir / result_image_name
        new_prompt_path = prompt_dir / (Path(result_image_name).stem + ".txt")
        try:
            os.rename(image_path, new_image_path)
            print(f"[DEBUG] Renamed input image to: {new_image_path}")
        except Exception as e:
            print(f"[ERROR] Failed to rename input image: {e}")
        try:
            os.rename(prompt_path, new_prompt_path)
            print(f"[DEBUG] Renamed prompt to: {new_prompt_path}")
        except Exception as e:
            print(f"[ERROR] Failed to rename prompt: {e}")
    return _extract_first_comfyui_image(images)





def _changeimagecomfyui_opt_sync_impl(req: ChangeImageComfyUiRequest_opt) -> tuple[bytes, str]:
    import os
    import uuid
    import time
    from pathlib import Path
    from app.models.langfuse import get_langfuse_singleton
    langfuse = get_langfuse_singleton()
    start_time = time.time()
    if req.strength < 0.0 or req.strength > 1.0:
        raise ValueError("strength는 0.0~1.0 범위여야 합니다.")

    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")
    image_bytes = base64.b64decode(raw_base64)
    prompt_bundle = _build_comfyui_prompt_bundle_opt(
        opt=req.opt,
        prompt=req.prompt,
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
    )
    # 1. uuid로 파일명 생성
    file_uuid = str(uuid.uuid4())
    input_dir = Path(__file__).resolve().parents[2] / "data" / "comfyui" / "input"
    prompt_dir = Path(__file__).resolve().parents[2] / "data" / "comfyui" / "prompt"
    input_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    image_path = input_dir / f"{file_uuid}.png"
    prompt_path = prompt_dir / f"{file_uuid}.txt"
    # 2. 이미지 저장
    try:
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        print(f"[DEBUG] Saved input image: {image_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save input image: {image_path} - {e}")
    # 3. 프롬프트 저장
    try:
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(f"positive_prompt: {prompt_bundle.positive_prompt}\n")
            f.write(f"negative_prompt: {prompt_bundle.negative_prompt}\n")
        print(f"[DEBUG] Saved prompt: {prompt_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save prompt: {prompt_path} - {e}")
    # 4. comfyui에 업로드할 때 파일명 지정
    client = _create_comfyui_client()
    images, result_image_name = client.change_image(
        positive_text=prompt_bundle.positive_prompt,
        negative_text=prompt_bundle.negative_prompt,
        image_bytes=image_bytes,
        strength=req.strength,
        image_name=f"{file_uuid}.png",
        return_result_image_name=True
    )
    # 5. 결과 이미지명으로 파일명 변경 (가능할 때만)
    if result_image_name:
        new_image_path = input_dir / result_image_name
        new_prompt_path = prompt_dir / (Path(result_image_name).stem + ".txt")
        try:
            os.rename(image_path, new_image_path)
            print(f"[DEBUG] Renamed input image to: {new_image_path}")
        except Exception as e:
            print(f"[ERROR] Failed to rename input image: {e}")
        try:
            os.rename(prompt_path, new_prompt_path)
            print(f"[DEBUG] Renamed prompt to: {new_prompt_path}")
        except Exception as e:
            print(f"[ERROR] Failed to rename prompt: {e}")
    elapsed = time.time() - start_time
    name = f"comfyui_change_image_opt_{req.opt}"
    langfuse.record_duration(
        trace_name=name ,
        elapsed=elapsed,
        metadata={"model": "comfyui", "function": name}
    )
    return _extract_first_comfyui_image(images)



def _makebgimagecomfyui_sync_impl(req: MakeBgImageRequest) -> tuple[bytes, str]:
    raw_base64 = _strip_and_validate_image_base64(req.image_base64, "image_base64는 필수입니다.")
    
    ollama = Gemma4OllamaService()
    positive_prompt = req.positive_prompt if req.positive_prompt is not None else ""
    negative_prompt = req.negative_prompt if req.negative_prompt is not None else ""
    results =  ollama.generate_background_byimage(
        raw_base64=raw_base64,
        prompt=req.prompt,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,)

    positive_prompt = results.get("positive_prompt", "")
    negative_prompt = results.get("negative_prompt", "")

    print(f"ComfyUI용 positive_prompt: {positive_prompt}")
    print(f"ComfyUI용 negative_prompt: {negative_prompt}")

    client = _create_comfyui_client()
    images = client.generate_images(
        positive_text=positive_prompt,
        negative_text=negative_prompt,
    )
    return _extract_first_comfyui_image(images)
