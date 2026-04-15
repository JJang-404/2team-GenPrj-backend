import json
import random
import time
import uuid
from pathlib import Path

import requests # pip install requests 필요


CREATE_IMAGE_JSON_PATH = Path(__file__).resolve().parents[2].joinpath("data", "comfyui", "createimage.json")
CHANGE_IMAGE_JSON_PATH = Path(__file__).resolve().parents[2].joinpath("data", "comfyui", "changeimage.json")
OUTPUT_PATH = Path(__file__).resolve().parents[2].joinpath("data", "comfyui", "output")

DEFAULT_COMFYUI_BASE_URL = "http://nabidream.duckdns.org:8188"


class ComfyUIClient:
    def __init__(
        self,
        base_url: str = DEFAULT_COMFYUI_BASE_URL,
        flow_path: Path = CREATE_IMAGE_JSON_PATH,
    ):
        self.base_url = base_url
        self.flow_path = flow_path

    @property
    def prompt_url(self) -> str:
        return f"{self.base_url}/prompt"

    def load_prompt_data(self, flow_path: Path | None = None) -> dict:
        target_path = flow_path or self.flow_path
        with target_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def apply_prompt_text(self, prompt_data: dict, positive_text: str, negative_text: str) -> dict:
        prompt_data["8"]["inputs"]["text"] = positive_text
        prompt_data["9"]["inputs"]["text"] = negative_text
        # 매 실행마다 seed를 랜덤화하여 캐시 히트 방지
        if "7" in prompt_data and "seed" in prompt_data["7"]["inputs"]:
            prompt_data["7"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        return prompt_data

    def queue_prompt(self, prompt: dict) -> str:
        p = {"prompt": prompt}
        data = json.dumps(p).encode("utf-8")
        response = requests.post(self.prompt_url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["prompt_id"]

    def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> dict:
        history_url = f"{self.base_url}/history/{prompt_id}"
        elapsed = 0.0
        while elapsed < timeout:
            response = requests.get(history_url, timeout=10)
            response.raise_for_status()
            history = response.json()
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"ComfyUI 작업이 {timeout}초 내에 완료되지 않았습니다. (prompt_id={prompt_id})")

    def fetch_output_images(self, history_entry: dict) -> list[bytes]:
        images = []
        outputs = history_entry.get("outputs", {})
        for node_output in outputs.values():
            for img_info in node_output.get("images", []):
                params = {
                    "filename": img_info["filename"],
                    "subfolder": img_info.get("subfolder", ""),
                    "type": img_info.get("type", "output"),
                }
                response = requests.get(f"{self.base_url}/view", params=params, timeout=30)
                response.raise_for_status()
                images.append(response.content)
        return images

    def upload_image(self, image_bytes: bytes, filename: str | None = None, image_type: str = "input") -> dict:
        upload_url = f"{self.base_url}/upload/image"
        target_filename = filename or f"copilot_{uuid.uuid4().hex}.png"
        response = requests.post(
            upload_url,
            data={"type": image_type, "overwrite": "true"},
            files={"image": (target_filename, image_bytes, "image/png")},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or not str(result.get("name") or "").strip():
            raise RuntimeError("ComfyUI 업로드 응답에 이미지 이름이 없습니다.")
        return result

    def apply_change_image(self, prompt_data: dict, image_name: str, strength: float) -> dict:
        prompt_data["14"]["inputs"]["image"] = image_name
        prompt_data["7"]["inputs"]["denoise"] = strength
        return prompt_data

    def generate_images(
        self,
        positive_text: str,
        negative_text: str,
        flow_path: Path | None = None,
    ) -> list[bytes]:
        prompt_data = self.load_prompt_data(flow_path)
        self.apply_prompt_text(prompt_data, positive_text, negative_text)
        prompt_id = self.queue_prompt(prompt_data)
        history_entry = self.wait_for_completion(prompt_id)
        return self.fetch_output_images(history_entry)

    def change_image(
        self,
        positive_text: str,
        negative_text: str,
        image_bytes: bytes,
        strength: float = 0.45,
        image_name: str | None = None,
        flow_path: Path | None = None,
    ) -> list[bytes]:
        upload_result = self.upload_image(image_bytes=image_bytes, filename=image_name)
        prompt_data = self.load_prompt_data(flow_path or CHANGE_IMAGE_JSON_PATH)
        self.apply_prompt_text(prompt_data, positive_text, negative_text)
        self.apply_change_image(prompt_data, image_name=str(upload_result["name"]), strength=strength)
        prompt_id = self.queue_prompt(prompt_data)
        history_entry = self.wait_for_completion(prompt_id)
        return self.fetch_output_images(history_entry)

    def process_flow_prompt(self, positive_text: str, negative_text: str) -> list[bytes]:
        return self.generate_images(positive_text=positive_text, negative_text=negative_text)


if __name__ == "__main__":
    import pprint

    client = ComfyUIClient()

    prompt_data = client.load_prompt_data()
    client.apply_prompt_text(
        prompt_data,
        positive_text="A futuristic cyber city street, neon lights, rainy night, high detail",
        negative_text="low quality, bad anatomy, text",
    )
    prompt_id = client.queue_prompt(prompt_data)
    print(f"prompt_id: {prompt_id}")

    history_entry = client.wait_for_completion(prompt_id)
    print("=== history_entry ===")
    pprint.pprint(history_entry)

    images = client.fetch_output_images(history_entry)
    print(f"ComfyUI 이미지 생성 완료! 총 {len(images)}장")
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    for i, img_bytes in enumerate(images):
        out_path = OUTPUT_PATH.joinpath(f"output_{i}.png")
        out_path.write_bytes(img_bytes)
        print(f"  저장: {out_path}")

