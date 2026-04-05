from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from app.common import defines


class ChangeImageRequest(BaseModel):
	prompt: str = Field(..., min_length=1)
	image_base64: str = Field(..., min_length=1)
	strength: float = Field(default=0.45, ge=0.0, le=1.0)


class OpenAiJob:
	def __init__(self, model: str = "gpt-5-mini") -> None:
		self._api_key = self._read_open_api_key()
		self._base_prompt_msg = defines.BASE_PROMPT_MSG
		self._llm = ChatOpenAI(model=model, temperature=0, api_key=self._api_key)

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

	def change_kor_to_eng(self, kor_str: str) -> str:
		if not kor_str or not kor_str.strip():
			return ""

		try:
			messages = [
				SystemMessage(content=self._base_prompt_msg),
				HumanMessage(content=kor_str),
			]
			result = self._llm.invoke(messages)
			content = (result.content or "").strip()
			return content or kor_str
		except Exception as ex:
			print(f"[change_kor_to_eng Error] {type(ex).__name__}: {ex}")
			return kor_str

	# 기존 호출부 호환을 위한 래퍼
	def changeKor2Eng(self, korStr: str) -> str:
		return self.change_kor_to_eng(korStr)
