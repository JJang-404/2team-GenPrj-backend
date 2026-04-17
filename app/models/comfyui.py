import requests
import time

def create_florence_vlm_workflow(image_path, ollama_url="http://nabidream.duckdns.org:11139/"):
    """
    test.py 스타일의 Florence VLM 워크플로우 dict 생성
    """
    return {
        "18": { # LoadImage
            "inputs": {
                "image": image_path,
                "upload": "image"
            },
            "class_type": "LoadImage"
        },
        "16": { # Florence2ModelLoader
            "inputs": {
                "model": "Florence-2-large",
                "precision": "fp16"
            },
            "class_type": "Florence2ModelLoader"
        },
        "15": { # Florence2Run
            "inputs": {
                "image": ["18", 0],
                "florence2_model": ["16", 0],
                "text_input": "",
                "task": "more_detailed_caption",
                "fill_mask": True,
                "keep_model_loaded": False,
                "max_new_tokens": 1024,
                "num_beams": 3,
                "do_sample": True
            },
            "class_type": "Florence2Run"
        },
        "14": { # OllamaConnectivity
            "inputs": {
                "url": ollama_url,
                "model": "gemma4:e4b",
                "keep_alive": 0
            },
            "class_type": "OllamaConnectivityV2"
        },
        "19": { # OllamaGenerate
            "inputs": {
                "connectivity": ["14", 0],
                "system": "You are a professional prompt engineer...",
                "prompt": ["15", 2],
                "format": "text"
            },
            "class_type": "OllamaGenerateV2"
        },
        "20": { # PreviewAny
            "inputs": {
                "source": ["19", 0]
            },
            "class_type": "PreviewAny"
        }
    }

def run_florence_vlm_workflow(image_path, comfyui_address="http://nabidream.duckdns.org:8188", ollama_url="http://nabidream.duckdns.org:11139/"):
    """
    test.py 스타일로 워크플로우 전송 후, 최대 5분(300초)간 PreviewAny(20번) 노드의 결과를 폴링하여 반환
    """
    workflow = create_florence_vlm_workflow(image_path, ollama_url)
    # 1. 프롬프트 전송
    p = {"prompt": workflow}
    data = json.dumps(p).encode('utf-8')
    res = requests.post(f"{comfyui_address}/prompt", data=data)
    res.raise_for_status()
    prompt_id = res.json().get('prompt_id')
    if not prompt_id:
        raise RuntimeError("prompt_id를 받지 못했습니다.")

    # 2. 결과 폴링 (최대 5분)
    for _ in range(300):  # 300초(5분) 동안 1초마다 체크
        time.sleep(1)
        hist = requests.get(f"{comfyui_address}/history/{prompt_id}")
        hist.raise_for_status()
        outputs = hist.json().get(prompt_id, {}).get("outputs", {})
        if "20" in outputs:
            for key in ("source", "preview_text", "text"):
                val = outputs["20"].get(key)
                if isinstance(val, list) and val:
                    return val[0]
                if isinstance(val, str) and val.strip():
                    return val
    raise RuntimeError("5분 내에 PreviewAny(20) 결과를 찾을 수 없습니다.")
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
        # KeyError 방지: 노드 존재 여부 확인
        if "8" in prompt_data and "inputs" in prompt_data["8"]:
            prompt_data["8"]["inputs"]["text"] = positive_text
        else:
            print("[경고] prompt_data에 '8'번 노드가 없거나 구조가 다릅니다.")
        if "9" in prompt_data and "inputs" in prompt_data["9"]:
            prompt_data["9"]["inputs"]["text"] = negative_text
        else:
            print("[경고] prompt_data에 '9'번 노드가 없거나 구조가 다릅니다.")
        # 매 실행마다 seed를 랜덤화하여 캐시 히트 방지
        if "7" in prompt_data and "seed" in prompt_data["7"].get("inputs", {}):
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

    def upload_image(self, image_bytes: bytes, filename: str = "", image_type: str = "input") -> dict:
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
        image_name: str = "",
        flow_path: Path | None = None,
    ) -> list[bytes]:
        upload_result = self.upload_image(image_bytes=image_bytes, filename=image_name)
        prompt_data = self.load_prompt_data(flow_path or CHANGE_IMAGE_JSON_PATH)
        self.apply_prompt_text(prompt_data, positive_text, negative_text)
        self.apply_change_image(prompt_data, image_name=str(upload_result["name"]), strength=strength)
        prompt_id = self.queue_prompt(prompt_data)
        history_entry = self.wait_for_completion(prompt_id)
        return self.fetch_output_images(history_entry)

    def florence_vlm(self, image_bytes: bytes, image_name: str = "", text_input: str = "" , flow_path: Path = None) -> str:
        """
        Florence VLM 플로우(data/comfyui/florencevlm.json)에 이미지를 넣고,
        생성된 문자열(텍스트)을 반환합니다.
        text_input: 15번 노드의 text_input 입력값 (설명문 등)
        """
        flow_path = flow_path or Path(__file__).resolve().parents[2].joinpath("data", "comfyui", "florencevlm.json")
        # 1. 이미지 업로드
        upload_result = self.upload_image(image_bytes=image_bytes, filename=image_name)
        image_server_name = str(upload_result["name"])

        # 2. 플로우 로드 및 입력값 적용
        prompt_data = self.load_prompt_data(flow_path)
        # 18번 노드: 이미지 파일명 적용
        if "18" in prompt_data and "inputs" in prompt_data["18"]:
            prompt_data["18"]["inputs"]["image"] = image_server_name
        # 15번 노드: text_input 값 적용
        if "15" in prompt_data and "inputs" in prompt_data["15"]:
            prompt_data["15"]["inputs"]["text_input"] = text_input

        # 3. 프롬프트 전송 및 대기
        prompt_id = self.queue_prompt(prompt_data)
        history_entry = self.wait_for_completion(prompt_id)

        # 4. 결과 텍스트 추출 (여러 노드/필드 지원)
        outputs = history_entry.get("outputs", {})
        import pprint
        print("[DEBUG] ComfyUI outputs:")
        pprint.pprint(outputs)
        # 1. Florence2Run(15) text
        if "15" in outputs:
            text_outputs = outputs["15"].get("text", [])
            if text_outputs:
                return text_outputs[0]
        # 2. OllamaGenerateV2(19) source, preview_text, text
        if "19" in outputs:
            for key in ("source", "preview_text", "text"):
                val = outputs["19"].get(key)
                if isinstance(val, list) and val:
                    return val[0]
                if isinstance(val, str) and val.strip():
                    return val
        # 3. PreviewAny(20) source, preview_text, text
        if "20" in outputs:
            for key in ("source", "preview_text", "text"):
                val = outputs["20"].get(key)
                if isinstance(val, list) and val:
                    return val[0]
                if isinstance(val, str) and val.strip():
                    return val
        raise RuntimeError("Florence VLM 결과 텍스트를 찾을 수 없습니다.")


    def process_flow_prompt(self, positive_text: str, negative_text: str) -> list[bytes]:
        return self.generate_images(positive_text=positive_text, negative_text=negative_text)


if __name__ == "__main__":
    import pprint

    client = ComfyUIClient()

    imagefile = "/project/2team-GenPrj-backend/data/test/iceamericano.jpg"
    result = client.florence_vlm(image_bytes=open(imagefile, "rb").read(), image_name="iceamericano.jpg")
    print("=== Florence VLM Result ===")
    print(result)
    
    
    # prompt_data = client.load_prompt_data()
    # client.apply_prompt_text(
    #     prompt_data,
    #     positive_text="A futuristic cyber city street, neon lights, rainy night, high detail",
    #     negative_text="low quality, bad anatomy, text",
    # )
    # prompt_id = client.queue_prompt(prompt_data)
    # print(f"prompt_id: {prompt_id}")

    # history_entry = client.wait_for_completion(prompt_id)
    # print("=== history_entry ===")
    # pprint.pprint(history_entry)

    # images = client.fetch_output_images(history_entry)
    # print(f"ComfyUI 이미지 생성 완료! 총 {len(images)}장")
    # OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    # for i, img_bytes in enumerate(images):
    #     out_path = OUTPUT_PATH.joinpath(f"output_{i}.png")
    #     out_path.write_bytes(img_bytes)
    #     print(f"  저장: {out_path}")

