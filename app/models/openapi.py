from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from app.common import defines


class ChangeImageRequest(BaseModel):
	prompt: str = Field(..., min_length=1)
	positive_prompt: str | None = None
	negative_prompt: str | None = None
	image_base64: str = Field(..., min_length=1)
	strength: float = Field(default=0.45, ge=0.0, le=1.0)


class PromptBundle(BaseModel):
	positive_prompt: str = Field(default="")
	negative_prompt: str = Field(default="")


class OpenAiJob:
	def __init__(self, model: str = "gpt-5-mini") -> None:
		self._api_key = self._read_open_api_key()
		self._base_prompt_msg = defines.BASE_PROMPT_MSG
		self._translate_prompt_msg = (
			"Translate the given Korean or mixed-language image prompt into concise English. "
			"Return only the English prompt text without explanations."
		)
		self._default_negative_prompt = (
			"low quality, blurry, distorted, deformed, bad anatomy, bad hands, extra fingers, "
			"cropped, watermark, text, logo, duplicate, oversaturated"
		)
		self._llm = ChatOpenAI(model=model, temperature=0, api_key=SecretStr(self._api_key))

	def _read_open_api_key(self) -> str:
		env_path = Path(__file__).resolve().parents[2] / ".security" / ".env"
		if not env_path.exists():
			raise RuntimeError(f"Environment file not found: {env_path}")

		for line in env_path.read_text(encoding="utf-8").splitlines():
			raw = line.strip()
			if not raw or raw.startswith("#") or "=" not in raw:
				continue

			key, value = raw.split("=", 1)
			if key.strip() == "OPEN_API_KEY":
				token = value.strip().strip('"').strip("'")
				if token:
					return token
				break

		raise RuntimeError("OPEN_API_KEY is missing in .security/.env")

	def _contains_korean(self, text: str) -> bool:
		return any("가" <= char <= "힣" for char in text)

	def _strip_code_fence(self, content: str) -> str:
		cleaned = (content or "").strip()
		if cleaned.startswith("```"):
			parts = cleaned.split("```")
			if len(parts) >= 3:
				return parts[1].replace("json", "", 1).strip()
		return cleaned

	def _parse_prompt_bundle(self, content: str) -> PromptBundle:
		cleaned = self._strip_code_fence(content)
		start_index = cleaned.find("{")
		end_index = cleaned.rfind("}")
		if start_index >= 0 and end_index > start_index:
			cleaned = cleaned[start_index:end_index + 1]

		parsed = json.loads(cleaned)
		return PromptBundle(
			positive_prompt=str(parsed.get("positive_prompt") or parsed.get("positive") or "").strip(),
			negative_prompt=str(parsed.get("negative_prompt") or parsed.get("negative") or "").strip(),
		)

	def _message_content_to_text(self, content: str | list[str | dict[Any, Any]]) -> str:
		if isinstance(content, str):
			return content.strip()

		parts: list[str] = []
		for item in content:
			if isinstance(item, str):
				parts.append(item)
			elif isinstance(item, dict):
				text_value = item.get("text")
				if isinstance(text_value, str):
					parts.append(text_value)

		return "\n".join(part.strip() for part in parts if part).strip()

	def change_kor_to_eng(self, kor_str: str) -> str:
		if not kor_str or not kor_str.strip():
			return ""

		try:
			messages = [
				SystemMessage(content=self._translate_prompt_msg),
				HumanMessage(content=kor_str),
			]
			result = self._llm.invoke(messages)
			content = self._message_content_to_text(result.content)
			return content or kor_str
		except Exception as ex:
			print(f"[change_kor_to_eng Error] {type(ex).__name__}: {ex}")
			return kor_str

	# 기존 호출부 호환을 위한 래퍼
	def changeKor2Eng(self, korStr: str) -> str:
		return self.change_kor_to_eng(korStr)

	def build_prompt_bundle(
		self,
		prompt: str,
		positive_prompt: str | None = None,
		negative_prompt: str | None = None,
	) -> PromptBundle:
		normalized_prompt = (prompt or "").strip()
		normalized_positive = (positive_prompt or "").strip()
		normalized_negative = (negative_prompt or "").strip()

		if not normalized_prompt and not normalized_positive:
			return PromptBundle(positive_prompt="", negative_prompt=normalized_negative or self._default_negative_prompt)

		needs_llm = (
			not normalized_negative
			or not normalized_positive
			or self._contains_korean(normalized_prompt)
			or self._contains_korean(normalized_positive)
			or self._contains_korean(normalized_negative)
		)

		if not needs_llm:
			return PromptBundle(
				positive_prompt=normalized_positive or normalized_prompt,
				negative_prompt=normalized_negative or self._default_negative_prompt,
			)

		try:
			request_payload = {
				"prompt": normalized_prompt,
				"positive_prompt": normalized_positive,
				"negative_prompt": normalized_negative,
			}
			messages = [
				SystemMessage(content=self._base_prompt_msg),
				HumanMessage(content=json.dumps(request_payload, ensure_ascii=False)),
			]
			result = self._llm.invoke(messages)
			bundle = self._parse_prompt_bundle(self._message_content_to_text(result.content))
			return PromptBundle(
				positive_prompt=bundle.positive_prompt or normalized_positive or self.change_kor_to_eng(normalized_prompt),
				negative_prompt=bundle.negative_prompt or normalized_negative or self._default_negative_prompt,
			)
		except Exception as ex:
			print(f"[build_prompt_bundle Error] {type(ex).__name__}: {ex}")
			fallback_positive = normalized_positive or self.change_kor_to_eng(normalized_prompt)
			fallback_negative = normalized_negative or self._default_negative_prompt
			return PromptBundle(
				positive_prompt=fallback_positive,
				negative_prompt=fallback_negative,
			)
