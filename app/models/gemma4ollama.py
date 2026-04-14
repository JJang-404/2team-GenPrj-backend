from __future__ import annotations

import configparser
import json
from typing import Any
from urllib.request import Request, urlopen

from app.common import defines
from app.models.openai import PromptBundle, OpenAiJob


class Gemma4OllamaService:
    _DEFAULT_MODEL_NAME = "gemma4:e4b"
    _DEFAULT_OLLAMA_URL = "http://localhost:11434"
    _DEFAULT_OLLAMA_WAIT_TIME = 600

    _VLM_FUSION_PROMPT = (
        "You are a VLM Prompt Engineer for SD 3.5.\n"
        "Step 1: Analyze the input image's layout and color.\n"
        "Step 2: Extract any visible text from the image and include it in the scene understanding.\n"
        "Step 3: Combine image analysis with the user's request: {user_input}.\n"
        "Step 4: Follow these STRICT RULES:\n"
        "- First 60 tokens: environment + composition + inherited visual traits.\n"
        "- Subject > Style > Composition > Lighting > Color > Details.\n"
        "- For background scenes: Ensure 'empty scene, no people' is prioritized.\n"
        "Return only JSON with 'positive_prompt' and 'negative_prompt'."
    )

    _DEFAULT_NEGATIVE_PROMPT = (
        "low quality, blurry, distorted, deformed, bad anatomy, bad hands, extra fingers, "
        "cropped, watermark, text, logo, duplicate, oversaturated"
    )

    _DEFAULT_BG_NEGATIVE_PROMPT = (
        "person, people, human, face, body, animal, pet, car, vehicle, "
        "product, object, logo, text, watermark, foreground subject"
    )

    def __init__(self) -> None:
        self.model_name, self.ollama_url, self.ollama_wait_time = self._load_ollama_config()
        print(
            "[Gemma4OllamaService] initialized "
            f"model_name={self.model_name}, ollama_url={self.ollama_url}, "
            f"wait_time={self.ollama_wait_time}"
        )

    def _load_ollama_config(self) -> tuple[str, str, int]:
        model_name = self._DEFAULT_MODEL_NAME
        ollama_url = self._DEFAULT_OLLAMA_URL
        ollama_wait_time = self._DEFAULT_OLLAMA_WAIT_TIME

        if defines.BACKEND_INI_PATH:
            config = configparser.ConfigParser()
            config.read(defines.BACKEND_INI_PATH, encoding="utf-8")
            model_name = config.get("ollama", "model_name", fallback=model_name).strip() or model_name
            ollama_url = config.get("ollama", "ollama_url", fallback=ollama_url).strip() or ollama_url
            try:
                parsed_wait_time = config.getint("ollama", "wait_time", fallback=ollama_wait_time)
                ollama_wait_time = parsed_wait_time if parsed_wait_time > 0 else ollama_wait_time
            except Exception:
                ollama_wait_time = self._DEFAULT_OLLAMA_WAIT_TIME

        print(
            "[Gemma4OllamaService] config loaded "
            f"backend_ini_path={defines.BACKEND_INI_PATH}, model_name={model_name}, "
            f"ollama_url={ollama_url}, wait_time={ollama_wait_time}"
        )
        return model_name, ollama_url.rstrip("/"), ollama_wait_time

    def _strip_code_fence(self, content: str) -> str:
        cleaned = (content or "").strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 3:
                return parts[1].replace("json", "", 1).strip()
        return cleaned

    def _parse_prompt_bundle(self, raw_text: str) -> PromptBundle:
        cleaned = self._strip_code_fence(raw_text)
        start_index = cleaned.find("{")
        end_index = cleaned.rfind("}")
        if start_index >= 0 and end_index > start_index:
            cleaned = cleaned[start_index:end_index + 1]

        print(
            "[Gemma4OllamaService] parsing prompt bundle "
            f"raw_len={len(raw_text or '')}, cleaned_len={len(cleaned)}"
        )
        parsed = json.loads(cleaned)
        positive = str(parsed.get("positive_prompt") or parsed.get("positive") or "").strip()
        negative = str(parsed.get("negative_prompt") or parsed.get("negative") or "").strip()

        return PromptBundle(
            positive_prompt=positive,
            negative_prompt=negative or self._DEFAULT_NEGATIVE_PROMPT,
        )

    def _build_user_input(
        self,
        prompt: str,
        positive_prompt: str | None,
        negative_prompt: str | None,
    ) -> str:
        payload = {
            "prompt": (prompt or "").strip(),
            "positive_prompt": (positive_prompt or "").strip(),
            "negative_prompt": (negative_prompt or "").strip(),
        }
        return json.dumps(payload, ensure_ascii=False)

    def _normalize_background_prompt_bundle(self, bundle: PromptBundle) -> PromptBundle:
        generated_positive = (bundle.positive_prompt or "").strip()
        generated_negative = (bundle.negative_prompt or "").strip()

        if "no foreground subject" not in generated_positive.lower():
            generated_positive = (
                f"{generated_positive}, no foreground subject"
                if generated_positive
                else "empty environment background scene, cinematic atmosphere, no foreground subject"
            )

        if "person" not in generated_negative.lower():
            generated_negative = (
                f"{generated_negative}, person, people, human"
                if generated_negative
                else self._DEFAULT_BG_NEGATIVE_PROMPT
            )

        # 업스트림 generate 안정성을 위해 과도한 길이는 제한합니다.
        max_prompt_len = 1200
        if len(generated_positive) > max_prompt_len:
            generated_positive = generated_positive[:max_prompt_len].rstrip(", ")
        if len(generated_negative) > max_prompt_len:
            generated_negative = generated_negative[:max_prompt_len].rstrip(", ")

        return PromptBundle(
            positive_prompt=generated_positive,
            negative_prompt=generated_negative or self._DEFAULT_BG_NEGATIVE_PROMPT,
        )

    def generate_background_prompt_bundle(
        self,
        raw_base64: str,
        prompt: str,
        positive_prompt: str | None = None,
        negative_prompt: str | None = None,
    ) -> PromptBundle:
        print(
            "[Gemma4OllamaService] generate_background_prompt_bundle start "
            f"prompt_len={len((prompt or '').strip())}, "
            f"has_positive={bool((positive_prompt or '').strip())}, "
            f"has_negative={bool((negative_prompt or '').strip())}, "
            f"image_base64_len={len(raw_base64 or '')}"
        )
        # 한글 프롬프트를 영문으로 번역
        translator = OpenAiJob()
        translated_prompt = translator.change_kor_to_eng((prompt or "").strip())
        translated_positive_prompt = translator.change_kor_to_eng((positive_prompt or "").strip()) if positive_prompt else None
        translated_negative_prompt = translator.change_kor_to_eng((negative_prompt or "").strip()) if negative_prompt else None
        
        print(
            "[Gemma4OllamaService] translated prompts "
            f"original_prompt_len={len((prompt or '').strip())}, translated_len={len(translated_prompt)}"
        )
        
        user_input = self._build_user_input(
            prompt=translated_prompt,
            positive_prompt=translated_positive_prompt,
            negative_prompt=translated_negative_prompt,
        )
        fusion_prompt = self._VLM_FUSION_PROMPT.format(user_input=user_input)

        request_payload = {
            "model": self.model_name,
            "prompt": fusion_prompt,
            "images": [raw_base64],
            "stream": False,
            "format": "json",
        }
        request = Request(
            f"{self.ollama_url}/api/generate",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        print(
            "[Gemma4OllamaService] calling ollama generate "
            f"url={self.ollama_url}/api/generate, model={self.model_name}"
        )

        with urlopen(request, timeout=self.ollama_wait_time) as upstream_response:
            body = upstream_response.read()
        print(f"[Gemma4OllamaService] ollama response received body_len={len(body)}")

        decoded = json.loads(body.decode("utf-8", errors="ignore"))
        response_text = str(decoded.get("response") or "").strip()
        if not response_text:
            raise RuntimeError("Ollama 응답에 response 텍스트가 없습니다.")

        bundle = self._parse_prompt_bundle(response_text)
        if not bundle.positive_prompt:
            raise RuntimeError("Ollama 응답에 positive_prompt가 없습니다.")
        bundle = self._normalize_background_prompt_bundle(bundle)
        print(
            "[Gemma4OllamaService] prompt bundle created "
            f"positive_len={len(bundle.positive_prompt)}, negative_len={len(bundle.negative_prompt)}"
        )
        return bundle
    