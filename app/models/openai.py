from __future__ import annotations

import json
import importlib
import os
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


class AdCopyBundle(BaseModel):
	main_copy: str = Field(default="")
	variants: list[str] = Field(default_factory=list)


class OpenAiJob:
	def __init__(self, model: str = "gpt-5-mini") -> None:
		env_map = self._read_env_map()
		self._api_key = self._read_open_api_key(env_map)
		self._base_prompt_msg = defines.BASE_PROMPT_MSG
		self._ad_copy_prompt_msg = defines.AD_COPY_PROMPT_MSG
		self._model = model
		
		self._translate_prompt_msg = (
			"Translate the given Korean or mixed-language image prompt into optimized English for Stable Diffusion 3.5. "

			"IMPORTANT RULES:\n"
			"1. Put the MOST IMPORTANT visual elements FIRST (subject, style, composition).\n"
			"2. Keep the first 60~70 tokens highly information-dense.\n"
			"3. Less important details (lighting nuances, minor descriptors) MUST go at the end.\n"
			"4. Keep the total prompt concise (prefer under 100 tokens).\n"
			"5. Use comma-separated keyword style, NOT long sentences.\n"
			"6. Prioritize in this order:\n"
			"   subject > style > composition > lighting > color > details\n"
			
			"Return only the final prompt."
		)

		self._bg_prompt_msg = (
			"You prepare Stable Diffusion 3.5 prompts for background-only scenes.\n"
			
			"STRICT RULES:\n"
			"1. The first 60 tokens MUST define the environment and composition clearly.\n"
			"2. Start with scene type, environment, and camera composition.\n"
			"3. Ensure the scene is explicitly empty (no subject).\n"
			"4. Less important atmosphere details go at the end.\n"
			
			"FORMAT RULES:\n"
			"- Use comma-separated keywords\n"
			"- No long sentences\n"
			
			"Return strict JSON only with keys positive_prompt and negative_prompt."
		)
		self._translate_to_sd35_dual_prompt = (
			"Translate the given Korean or mixed-language image prompt into optimized English for Stable Diffusion 3.5. "
			"You are an expert prompt engineer for Stable Diffusion 3.5. "
			"Your task is to take image descriptions (from Vision LLM) and user prompts (Korean/English) "
			"to generate a structured 'Positive Prompt' and 'Negative Prompt'.\n\n"

			"### POSITIVE PROMPT RULES:\n"
			"1. Structure: [Subject], [Style], [Composition], [Lighting], [Color], [Details].\n"
			"2. Priority: Put the most critical visual elements in the first 60~70 tokens.\n"
			"3. Style: Use comma-separated keywords, NOT full sentences.\n"
			"4. Length: Concise, ideally under 100 tokens total.\n\n"

			"### NEGATIVE PROMPT RULES:\n"
			"1. List elements that should NEVER appear (e.g., anatomical errors, low quality, text, blurry).\n"
			"2. Standard SD 3.5 negative constraints: (low quality, worst quality, text, watermark, deformed, ugly, blurry).\n\n"

			"### OUTPUT FORMAT:\n"
			"You MUST return the result in the following format exactly:\n"
			"Positive: [The generated positive prompt]\n"
			"Negative: [The generated negative prompt]"
		)
			
		self._default_negative_prompt = (
			"low quality, blurry, distorted, deformed, bad anatomy, bad hands, extra fingers, "
			"cropped, watermark, text, logo, duplicate, oversaturated"
		)
		self._langfuse_client = self._build_langfuse_client(env_map)
		self._langfuse_handler = self._build_langfuse_handler(env_map)
		self._llm = ChatOpenAI(model=model, temperature=0, api_key=SecretStr(self._api_key))

	def _read_env_map(self) -> dict[str, str]:
		env_path = Path(__file__).resolve().parents[2] / ".security" / ".env"
		if not env_path.exists():
			raise RuntimeError(f"Environment file not found: {env_path}")

		env_map: dict[str, str] = {}
		for line in env_path.read_text(encoding="utf-8").splitlines():
			raw = line.strip()
			if not raw or raw.startswith("#") or "=" not in raw:
				continue

			key, value = raw.split("=", 1)
			env_map[key.strip()] = value.strip().strip('"').strip("'")

		return env_map

	def _read_open_api_key(self, env_map: dict[str, str]) -> str:
		token = (env_map.get("OPEN_API_KEY") or "").strip()
		if token:
			return token

		raise RuntimeError("OPEN_API_KEY is missing in .security/.env")

	def _build_langfuse_handler(self, env_map: dict[str, str]) -> Any | None:
		callback_handler_cls = None
		try:
			langfuse_langchain = importlib.import_module("langfuse.langchain")
			callback_handler_cls = getattr(langfuse_langchain, "CallbackHandler", None)
		except Exception:
			try:
				langfuse_callback = importlib.import_module("langfuse.callback")
				callback_handler_cls = getattr(langfuse_callback, "CallbackHandler", None)
			except Exception:
				callback_handler_cls = None

		if callback_handler_cls is None:
			print("[Langfuse] langfuse 패키지가 없어 trace를 비활성화합니다.")
			return None

		public_key = (env_map.get("LANGFUSE_PUBLIC_KEY") or "").strip()
		secret_key = (env_map.get("LANGFUSE_SECRET_KEY") or "").strip()
		base_url = (env_map.get("LANGFUSE_BASE_URL") or "").strip()
		if not (public_key and secret_key and base_url):
			return None

		# Langfuse 4.x LangChain CallbackHandler는 secret_key/host를 생성자 인자로 받지 않아
		# 환경변수 기반 설정으로 주입합니다.
		os.environ["LANGFUSE_SECRET_KEY"] = secret_key
		os.environ["LANGFUSE_HOST"] = base_url

		try:
			return callback_handler_cls(
				public_key=public_key,
			)
		except Exception as ex:
			print(f"[Langfuse] 초기화 실패: {type(ex).__name__}: {ex}")
			return None

	def _build_langfuse_client(self, env_map: dict[str, str]) -> Any | None:
		public_key = (env_map.get("LANGFUSE_PUBLIC_KEY") or "").strip()
		secret_key = (env_map.get("LANGFUSE_SECRET_KEY") or "").strip()
		base_url = (env_map.get("LANGFUSE_BASE_URL") or "").strip()
		if not (public_key and secret_key and base_url):
			return None

		try:
			langfuse_mod = importlib.import_module("langfuse")
			langfuse_cls = getattr(langfuse_mod, "Langfuse", None)
			if langfuse_cls is None:
				return None

			return langfuse_cls(
				public_key=public_key,
				secret_key=secret_key,
				host=base_url,
			)
		except Exception as ex:
			print(f"[Langfuse] client 초기화 실패: {type(ex).__name__}: {ex}")
			return None

	def _invoke_llm(self, messages: list[SystemMessage | HumanMessage], trace_name: str):
		if self._langfuse_handler is None:
			return self._llm.invoke(messages)

		return self._llm.invoke(
			messages,
			config={
				"callbacks": [self._langfuse_handler],
				"run_name": trace_name,
				"metadata": {"model": self._model},
			},
		)

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

	def _parse_ad_copy_bundle(self, content: str) -> AdCopyBundle:
		cleaned = self._strip_code_fence(content)
		start_index = cleaned.find("{")
		end_index = cleaned.rfind("}")
		if start_index >= 0 and end_index > start_index:
			cleaned = cleaned[start_index:end_index + 1]

		parsed = json.loads(cleaned)
		variants = parsed.get("variants") or []
		if not isinstance(variants, list):
			variants = []
		return AdCopyBundle(
			main_copy=str(parsed.get("main_copy") or "").strip(),
			variants=[str(item).strip() for item in variants if str(item).strip()],
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
			result = self._invoke_llm(messages, trace_name="change_kor_to_eng")
			content = self._message_content_to_text(result.content)
			return content or kor_str
		except Exception as ex:
			print(f"[change_kor_to_eng Error] {type(ex).__name__}: {ex}")
			return kor_str

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
			result = self._invoke_llm(messages, trace_name="build_prompt_bundle")
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
		

	def build_prompt_dual_prompt(
		self,
		vlmtext: str,
		user_prompt: str,
		positive_prompt: str = "",
		negative_prompt: str = "",
		style: str = "",
		composition: str = "",
	) -> dict:
		"""
		Vision LLM 텍스트(vlmtext), 유저 프롬프트, 스타일, 컴포지션 등 4가지 텍스트를 받아
		_translate_to_sd35_dual_prompt 프롬프트로 GPT에 전달하여 positive/negative 프롬프트를 생성합니다.
		"""
		# 입력 정규화
		vlmtext = (vlmtext or "").strip()
		user_prompt = (user_prompt or "").strip()
		positive_prompt = (positive_prompt or "").strip()
		negative_prompt = (negative_prompt or "").strip()
		style = (style or "").strip()
		composition = (composition or "").strip()

		# GPT에 넘길 입력 포맷 구성
		input_payload = {
			"vlmtext": vlmtext,
			"user_prompt": user_prompt,
			"positive_prompt": positive_prompt,
			"negative_prompt": negative_prompt,
			"style": style,
			"composition": composition,
		}
		# 프롬프트 메시지 생성
		system_msg = self._translate_to_sd35_dual_prompt
		# 입력을 보기 좋게 JSON이 아닌 텍스트로 전달
		human_msg = (
			f"[VLM TEXT]: {vlmtext}\n"
			f"[USER PROMPT]: {user_prompt}\n"
			f"[POSITIVE PROMPT]: {positive_prompt}\n"
			f"[NEGATIVE PROMPT]: {negative_prompt}\n"
			f"[STYLE]: {style}\n"
			f"[COMPOSITION]: {composition}"
		)
		try:
			messages = [
				SystemMessage(content=system_msg),
				HumanMessage(content=human_msg),
			]
			result = self._invoke_llm(messages, trace_name="build_prompt_dual_prompt")
			# 결과 파싱: "Positive: ...\nNegative: ..." 형태
			content = self._message_content_to_text(result.content)
			positive, negative = "", ""
			for line in content.splitlines():
				if line.strip().lower().startswith("positive:"):
					positive = line.split(":", 1)[-1].strip()
				elif line.strip().lower().startswith("negative:"):
					negative = line.split(":", 1)[-1].strip()
			if not positive:
				positive = vlmtext or user_prompt
			if not negative:
				negative = self._default_negative_prompt
			return {
				"positive_prompt": positive,
				"negative_prompt": negative,
			}
		except Exception as ex:
			print(f"[build_prompt_dual_prompt Error] {type(ex).__name__}: {ex}")
			return {
				"positive_prompt": vlmtext or user_prompt,
				"negative_prompt": self._default_negative_prompt,
			}
	

	def build_ad_copy(
		self,
		input_text: str,
		tone: str | None = None,
		target_audience: str | None = None,
		count: int = 3,
	) -> AdCopyBundle:
		normalized_text = (input_text or "").strip()
		normalized_tone = (tone or "").strip()
		normalized_target = (target_audience or "").strip()
		variant_count = count if count > 0 else 3

		if not normalized_text:
			return AdCopyBundle(main_copy="", variants=[])

		request_payload = {
			"input_text": normalized_text,
			"tone": normalized_tone,
			"target_audience": normalized_target,
			"variant_count": variant_count,
		}

		try:
			messages = [
				SystemMessage(content=self._ad_copy_prompt_msg),
				HumanMessage(content=json.dumps(request_payload, ensure_ascii=False)),
			]
			result = self._invoke_llm(messages, trace_name="build_ad_copy")
			bundle = self._parse_ad_copy_bundle(self._message_content_to_text(result.content))
			variants = bundle.variants[:variant_count]
			main_copy = bundle.main_copy or (variants[0] if variants else normalized_text)
			if main_copy and main_copy not in variants:
				variants = [main_copy, *variants]
			return AdCopyBundle(main_copy=main_copy, variants=variants[:variant_count])
		except Exception as ex:
			print(f"[build_ad_copy Error] {type(ex).__name__}: {ex}")
			fallback_variants = [normalized_text]
			if normalized_tone:
				fallback_variants.append(f"{normalized_tone} 분위기로 {normalized_text}")
			if normalized_target:
				fallback_variants.append(f"{normalized_target}을 위한 {normalized_text}")
			return AdCopyBundle(main_copy=fallback_variants[0], variants=fallback_variants[:variant_count])

	def build_background_prompt_bundle(
		self,
		caption_text: str,
		user_prompt: str | None = None,
		positive_prompt: str | None = None,
		negative_prompt: str | None = None,
	) -> PromptBundle:
		normalized_caption = (caption_text or "").strip()
		normalized_user_prompt = (user_prompt or "").strip()
		normalized_positive = (positive_prompt or "").strip()
		normalized_negative = (negative_prompt or "").strip()

		request_payload = {
			"caption_text": normalized_caption,
			"user_prompt": normalized_user_prompt,
			"positive_prompt": normalized_positive,
			"negative_prompt": normalized_negative,
		}

		fallback_positive_parts = [
			"empty environment background scene",
			"cinematic atmosphere",
			"no foreground subject",
			"no people, no animals, no products",
		]
		if normalized_user_prompt:
			fallback_positive_parts.insert(1, self.change_kor_to_eng(normalized_user_prompt))
		fallback_positive = ", ".join(part for part in fallback_positive_parts if part)
		fallback_negative = (
			normalized_negative
			or "person, people, human, face, body, animal, pet, car, vehicle, product, object, logo, text, watermark, foreground subject"
		)

		try:
			messages = [
				SystemMessage(content=self._bg_prompt_msg),
				HumanMessage(content=json.dumps(request_payload, ensure_ascii=False)),
			]
			result = self._invoke_llm(messages, trace_name="build_background_prompt_bundle")
			bundle = self._parse_prompt_bundle(self._message_content_to_text(result.content))
			generated_positive = (bundle.positive_prompt or "").strip()
			if "no foreground subject" not in generated_positive.lower():
				generated_positive = f"{generated_positive}, no foreground subject" if generated_positive else fallback_positive

			generated_negative = (bundle.negative_prompt or "").strip() or fallback_negative
			if "person" not in generated_negative.lower():
				generated_negative = f"{generated_negative}, person, people, human"

			return PromptBundle(
				positive_prompt=generated_positive or fallback_positive,
				negative_prompt=generated_negative,
			)
		except Exception as ex:
			print(f"[build_background_prompt_bundle Error] {type(ex).__name__}: {ex}")
			return PromptBundle(
				positive_prompt=fallback_positive,
				negative_prompt=fallback_negative,
			)
