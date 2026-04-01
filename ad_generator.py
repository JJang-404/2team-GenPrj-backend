"""
AI 광고 이미지 생성기
입력: 가게명, 상품, 가격, 전화번호, 스타일
출력: 광고 이미지 (제품 사진 + 텍스트 합성)
"""

import os
import textwrap
import torch
from diffusers import StableDiffusion3Pipeline
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import io
import zipfile
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# [0단계] 번역 (한국어 → 영어)
# ──────────────────────────────────────────────
_translator = GoogleTranslator(source="ko", target="en")


def translate_ko_to_en(text: str) -> str:
    return _translator.translate(text)


# ──────────────────────────────────────────────
# [0.5단계] LLM 광고 문구 생성
# 지금은 규칙 기반 문구 사용 → 나중에 ChatGPT API로 교체 예정
# ──────────────────────────────────────────────


def generate_tagline(store_name: str, product: str, style: str) -> str:
    """
    광고 문구(tagline) 생성.

    ── 현재: 규칙 기반 템플릿 ──────────────────────
    ── 추후: OpenAI ChatGPT API 로 교체 ────────────
    교체 방법:
        pip install openai
        아래 주석 해제 후 OPENAI_API_KEY 환경변수 설정

    # import openai
    # client = openai.OpenAI()
    # resp = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[{
    #         "role": "user",
    #         "content": (
    #             f"{store_name}의 {product} 광고 문구를 한 줄로 써줘. "
    #             f"분위기는 {style}이야. 20자 이내로."
    #         )
    #     }]
    # )
    # return resp.choices[0].message.content.strip()
    """
    taglines = {
        "모던함": f"깔끔하게, 담백하게",
        "따뜻함": f"한 잔의 여유, {store_name}",
        "고급스러움": f"특별한 순간을 위한 선택",
        "귀여움": f"오늘도 달콤하게 ☕",
    }
    return taglines.get(style, f"{store_name}의 {product}")


# ──────────────────────────────────────────────
# [1단계] AI 레이어: SDXL 모델 로드
# ──────────────────────────────────────────────
print("이미지 생성 모델 로드 중...")
pipe = StableDiffusion3Pipeline.from_pretrained(
    "stabilityai/stable-diffusion-3.5-medium",
    torch_dtype=torch.float16,
    variant="fp16",
    use_safetensors=True,
).to("cuda")
print("이미지 생성 모델 로드 완료")

STYLE_MAP = {
    "모던함": "Ultra-modern, minimalist, sterile white space, sharp edges, high-tech commercial shot",
    "따뜻함": "Sun-drenched, rustic charm, cozy organic textures, soft amber glow, inviting atmosphere",
    "고급스러움": "Opulence, premium matte finish, gold leaf accents, moody chiaroscuro lighting, elite aesthetic",
    "귀여움": "Whimsical, playful, vibrant pastels, 3D claymation style, soft rounded shapes, cheerful",
    "센스있는": "Sophisticated, curated, artistic composition, muted tones, effortless elegance, avant-garde",
    "깔롱지는": "Sleek, trendy, high-contrast, street-style aesthetic, neon highlights, bold and flashy",
    "생동감": "Vibrant, high-speed splash, motion blur, energetic, crisp textures, exploding flavors",
    "내추럴": "Raw, earthy, botanical, hyper-realistic textures, daylight, sustainable vibe",
}


def build_prompt(product: str, style: str) -> str:
    product_en = translate_ko_to_en(product)
    style_keywords = STYLE_MAP.get(style, "professional, clean")
    print(f"[번역] '{product}' → '{product_en}'")
    return (
        f"{product_en}, professional food advertisement photo, "
        f"{style_keywords}, high quality, 8k, bokeh background, studio lighting, "
        f"no text, no watermark"
    )


def generate_image(product: str, style: str) -> Image.Image:
    prompt = build_prompt(product, style)
    print(f"[프롬프트] {prompt}")
    image = pipe(prompt=prompt, num_inference_steps=30).images[0]
    return image


# ──────────────────────────────────────────────
# [2단계] Graphics 레이어: 템플릿 + Pillow로 텍스트 합성
# ──────────────────────────────────────────────


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    한글 폰트 로드 — 우선순위 순으로 탐색
    1. 프로젝트 내 fonts/ 폴더 (로컬·GCP 공통, 가장 확실)
    2. Windows 시스템 폰트
    3. Linux 시스템 폰트 (apt install fonts-nanum)
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "fonts")

    candidates = (
        [
            os.path.join(fonts_dir, "NeoHyundai_B.ttf"),
            "C:/Windows/Fonts/malgunbd.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        ]
        if bold
        else [
            os.path.join(fonts_dir, "NeoHyundai_B.ttf"),
            "C:/Windows/Fonts/malgun.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        ]
    )
    for path in candidates:
        print(f"[폰트 탐색] {path} → {'존재함' if os.path.exists(path) else '없음'}")
        if os.path.exists(path):
            print(f"[폰트 적용] {path}")
            return ImageFont.truetype(path, size)
    print("[경고] 한글 폰트를 찾지 못했습니다. 기본 폰트로 대체합니다.")
    return ImageFont.load_default()


def add_text_overlay(
    image: Image.Image,
    store_name: str,
    price: str,
    phone: str,
    tagline: str = "",
    template_name: str = "우측_사이드바",
) -> Image.Image:
    img = image.copy().convert("RGBA")
    w, h = img.size

    if template_name == "우측_사이드바":
        _draw_sidebar(img, w, h, store_name, price, phone, tagline)
    else:
        _draw_bottom(img, w, h, store_name, price, phone, tagline)

    return img.convert("RGB")


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """텍스트를 max_width 픽셀 너비에 맞게 줄바꿈"""
    lines, current = [], ""
    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        if bbox[2] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _draw_sidebar(img, w, h, store_name, price, phone, tagline):
    """오른쪽 38% 패널에 광고 정보를 구조적으로 배치"""
    panel_x = int(w * 0.60)
    panel_w = w - panel_x

    # 패널 배경 (진한 반투명)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    draw_ov.rectangle([(panel_x, 0), (w, h)], fill=(20, 20, 20, 210))
    img.alpha_composite(overlay)

    draw = ImageDraw.Draw(img)
    pad = int(w * 0.05)  # 패널 안쪽 여백
    tx = panel_x + pad  # 텍스트 시작 X
    max_text_w = panel_w - pad * 2  # 텍스트 최대 너비

    # ── 광고 문구 (tagline) — 패널 너비에 맞게 자동 줄바꿈 ──
    if tagline:
        font_tag = load_font(int(h * 0.030))
        lines = _wrap_text(tagline, font_tag, max_text_w)
        line_h = int(h * 0.035)
        for i, line in enumerate(lines[:3]):  # 최대 3줄
            draw.text(
                (tx, int(h * 0.07) + i * line_h), line, font=font_tag, fill="#AAAAAA"
            )

    # ── 가게명 (굵게, 크게) ───────────────────────
    font_store = load_font(int(h * 0.072), bold=True)
    draw.text((tx, int(h * 0.18)), store_name, font=font_store, fill="white")

    # 가게명 아래 강조선
    line_y = int(h * 0.30)
    line_x2 = panel_x + int((w - panel_x) * 0.75)
    draw.line([(tx, line_y), (line_x2, line_y)], fill="#FFD700", width=3)

    # ── 가격 라벨 ─────────────────────────────────
    font_label = load_font(int(h * 0.030))
    draw.text((tx, int(h * 0.34)), "PRICE", font=font_label, fill="#888888")

    # ── 가격 (금색, 굵게) ────────────────────────
    font_price = load_font(int(h * 0.062), bold=True)
    draw.text((tx, int(h * 0.40)), price, font=font_price, fill="#FFD700")

    # ── 구분선 ────────────────────────────────────
    sep_y = int(h * 0.55)
    draw.line([(tx, sep_y), (line_x2, sep_y)], fill="#444444", width=1)

    # ── 전화번호 라벨 ────────────────────────────
    draw.text((tx, int(h * 0.58)), "CONTACT", font=font_label, fill="#888888")

    # ── 전화번호 ─────────────────────────────────
    font_phone = load_font(int(h * 0.038))
    draw.text((tx, int(h * 0.63)), phone, font=font_phone, fill="#CCCCCC")


def _draw_bottom(img, w, h, store_name, price, phone, tagline):
    """하단 30% 영역에 광고 정보 배치"""
    overlay_y = int(h * 0.70)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    draw_ov.rectangle([(0, overlay_y), (w, h)], fill=(20, 20, 20, 200))
    img.alpha_composite(overlay)

    draw = ImageDraw.Draw(img)
    pad = int(w * 0.05)

    if tagline:
        font_tag = load_font(int(h * 0.030))
        draw.text(
            (pad, overlay_y + int(h * 0.01)), tagline, font=font_tag, fill="#AAAAAA"
        )

    font_store = load_font(int(h * 0.065), bold=True)
    draw.text(
        (pad, overlay_y + int(h * 0.05)), store_name, font=font_store, fill="white"
    )

    font_price = load_font(int(h * 0.055), bold=True)
    draw.text(
        (int(w * 0.55), overlay_y + int(h * 0.05)),
        price,
        font=font_price,
        fill="#FFD700",
    )

    font_phone = load_font(int(h * 0.033))
    draw.text((pad, overlay_y + int(h * 0.18)), phone, font=font_phone, fill="#CCCCCC")


# ──────────────────────────────────────────────
# [3단계] API 레이어: FastAPI로 서빙
# ──────────────────────────────────────────────

app = FastAPI(title="AI 광고 생성기")


class AdRequest(BaseModel):
    store_name: str
    product: str
    price: str
    phone: str
    style: str
    tagline: str = ""  # 비워두면 자동 생성, 직접 입력도 가능 (추후 ChatGPT로 대체)


@app.post("/generate-ad")
def generate_ad(req: AdRequest):
    """상품 1개 광고 이미지 생성"""
    tagline = req.tagline or generate_tagline(req.store_name, req.product, req.style)

    image = generate_image(req.product, req.style)
    final_image = add_text_overlay(
        image,
        store_name=req.store_name,
        price=req.price,
        phone=req.phone,
        tagline=tagline,
    )

    buf = io.BytesIO()
    final_image.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


class AdMultiRequest(BaseModel):
    store_name: str
    products: List[str]  # 상품 목록: ["아이스 아메리카노", "밀크티"]
    prices: List[str]  # 가격 목록: ["4,500원", "5,000원"] — products와 순서 일치
    phone: str
    style: str
    tagline: str = ""


@app.post("/generate-ad/multi")
def generate_ad_multi(req: AdMultiRequest):
    """
    상품/가격 여러 개 → 각각 이미지 생성 후 ZIP으로 반환
    예) products: ["아이스 아메리카노", "밀크티"]
        prices:   ["4,500원", "5,000원"]
        → ad_아이스 아메리카노.png, ad_밀크티.png 가 담긴 ZIP
    """
    if len(req.products) != len(req.prices):
        raise HTTPException(
            status_code=400, detail="products와 prices의 개수가 일치해야 합니다."
        )

    tagline = req.tagline or generate_tagline(
        req.store_name, req.products[0], req.style
    )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for product, price in zip(req.products, req.prices):
            print(f"[생성 중] {product} / {price}")
            image = generate_image(product, req.style)
            final = add_text_overlay(
                image,
                store_name=req.store_name,
                price=price,
                phone=req.phone,
                tagline=tagline,
            )
            img_buf = io.BytesIO()
            final.save(img_buf, format="PNG")
            zf.writestr(f"ad_{product}.png", img_buf.getvalue())

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ads.zip"},
    )


# ──────────────────────────────────────────────
# 로컬 테스트용 (FastAPI 없이 직접 실행)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=== AI 광고 이미지 생성기 ===")
    print(f"사용 가능한 스타일: {', '.join(STYLE_MAP.keys())}")
    print("상품명: 여러 개는 쉼표로 구분 (예: 아이스 아메리카노, 밀크티)\n")

    print(
        "※ 여러 개 입력 시 | 로 구분하세요. 예) 아메리카노|밀크티 / 4,500원|5,000원\n"
    )
    store_name = input("가게명: ").strip()
    product_input = input(
        "상품명 (여러 개는 | 로 구분, 예: 아메리카노|밀크티): "
    ).strip()
    price_input = input("가격   (여러 개는 | 로 구분, 예: 4,500원|5,000원): ").strip()
    phone = input("전화번호 (예: 031-000-000): ").strip()
    style = input(f"스타일 ({'/'.join(STYLE_MAP.keys())}): ").strip()
    tagline = input("광고 문구 (Enter=자동 생성): ").strip()

    products = [p.strip() for p in product_input.split("|") if p.strip()]
    prices = [p.strip() for p in price_input.split("|") if p.strip()]

    # 가격이 1개만 입력되면 모든 상품에 동일 가격 적용
    if len(prices) == 1:
        prices = prices * len(products)

    if len(products) != len(prices):
        print(
            f"[오류] 상품 {len(products)}개, 가격 {len(prices)}개 — 개수가 맞지 않습니다."
        )
        exit(1)

    if style not in STYLE_MAP:
        print(f"'{style}'은 없는 스타일입니다. '모던함'으로 대체합니다.")
        style = "모던함"
    if not tagline:
        tagline = generate_tagline(store_name, products[0], style)
        print(f"[자동 생성 문구] {tagline}")

    for i, (product, price) in enumerate(zip(products, prices)):
        print(f"\n[{i+1}/{len(products)}] '{product}' ({price}) 이미지 생성 중...")
        image = generate_image(product, style)

        print("텍스트 합성 중...")
        final = add_text_overlay(
            image,
            store_name=store_name,
            price=price,
            phone=phone,
            tagline=tagline,
        )

        output_path = "ad_output.png" if len(products) == 1 else f"ad_output_{i+1}.png"
        final.save(output_path)
        print(f"저장 완료: {output_path}")
