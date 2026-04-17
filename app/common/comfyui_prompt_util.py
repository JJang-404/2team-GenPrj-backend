import json
from pathlib import Path

def get_prompts_from_json(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    positive = None
    negative = None
    for node in data.get("nodes", []):
        if node.get("id") == 8 and node.get("type") == "CLIPTextEncode":
            if node.get("widgets_values"):
                positive = node["widgets_values"][0]
        if node.get("id") == 9 and node.get("type") == "CLIPTextEncode":
            if node.get("widgets_values"):
                negative = node["widgets_values"][0]
    return positive, negative

def set_prompts_to_json(json_path, positive=None, negative=None):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for node in data.get("nodes", []):
        if node.get("id") == 8 and node.get("type") == "CLIPTextEncode" and positive is not None:
            if node.get("widgets_values"):
                node["widgets_values"][0] = positive
        if node.get("id") == 9 and node.get("type") == "CLIPTextEncode" and negative is not None:
            if node.get("widgets_values"):
                node["widgets_values"][0] = negative
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    json_path = "data/comfyui/createimage.json"
    pos, neg = get_prompts_from_json(json_path)
    print("[추출] positive:", pos)
    print("[추출] negative:", neg)
    # 예시: 프롬프트 수정
    # set_prompts_to_json(json_path, positive="새로운 positive", negative="새로운 negative")
