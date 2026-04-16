import json
import requests
import base64
from PIL import Image
import io

# 1. 설정 정보
COMFYUI_ADDRESS = "http://nabidream.duckdns.org:8188"  # 로컬 ComfyUI 주소
OLLAMA_URL = "http://nabidream.duckdns.org:11139/" # 사용자 설정 Ollama 주소
INPUT_IMAGE_PATH = "/project/2team-GenPrj-backend/data/test/iceamericano.jpg"  # 분석할 이미지 경로

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def send_prompt(workflow):
    p = {"prompt": workflow}
    data = json.dumps(p).encode('utf-8')
    res = requests.post(f"{COMFYUI_ADDRESS}/prompt", data=data)
    return res.json()

# 2. 워크플로우 데이터 구성 (업로드하신 JSON 기반)
def create_workflow(image_name):
    return {
        "18": { # LoadImage
            "inputs": {
                "image": image_name,
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
                "text_input": "", # 에러 방지를 위해 비워둠
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
                "url": OLLAMA_URL,
                "model": "gemma4:e4b", # 사용 중인 모델 설정
                "keep_alive": 0
            },
            "class_type": "OllamaConnectivityV2"
        },
        "19": { # OllamaGenerate
            "inputs": {
                "connectivity": ["14", 0],
                "system": "You are a professional prompt engineer...", # 지시문 포함
                "prompt": ["15", 2], # Florence2의 caption 연결
                "format": "text"
            },
            "class_type": "OllamaGenerateV2"
        },
        "20": { # PreviewAny (결과 확인용)
            "inputs": {
                "source": ["19", 0]
            },
            "class_type": "PreviewAny"
        }
    }

# 3. 실행 프로세스
def main():
    # 이미지 업로드 (필요 시)
    # requests.post(f"{COMFYUI_ADDRESS}/upload/image", files={'image': open(INPUT_IMAGE_PATH, 'rb')})
    
    workflow = create_workflow(INPUT_IMAGE_PATH)
    print("워크플로우를 ComfyUI에 전송합니다...")
    
    prompt_res = send_prompt(workflow)
    prompt_id = prompt_res.get('prompt_id')
    print(f"작업 시작 (Prompt ID: {prompt_id})")

    # 실제 환경에서는 WebSocket을 통해 결과를 트래킹하거나 
    # /history/{prompt_id} 엔드포인트를 호출하여 텍스트 결과를 가져올 수 있습니다.
    print("Ollama가 응답을 생성 중입니다. 완료 후 'PreviewAny' 노드에서 결과를 확인하세요.")

if __name__ == "__main__":
    main()