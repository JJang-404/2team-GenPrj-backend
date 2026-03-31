from PIL import Image, ImageDraw, ImageFont
import os
import math
from datetime import datetime

# ── 입력값 ──────────────────────────────────────────
now = datetime.now()
print(f"현재 일(day): {now.day}")
date = f"{now.strftime('%B')}. {now.day}"
# date = datetime.now().strftime("%B. %-d") # GCP 버전
restaurant = "코드잇"
food_name = "블루베리 팬케이크"
store_name = "카페 코드잇"
store_phone = "02-1234-5678"
store_hours = "매일 11:00 - 21:00"
store_ad = "신선한 재료로 만든 홈메이드 팬케이크"
# ────────────────────────────────────────────────────

W, H = 1080, 1350  # Instagram 표준 4:5 (기존 400×600 → ×2.7/×2.25 스케일)
WHITE = (255, 255, 255, 255)
BOX_FILL = (0, 0, 0, 140)  # 반투명 검정 박스
BOX_OUTLINE = (255, 255, 255, 180)  # 반투명 흰 테두리

# ── 음식 이미지 중앙 크롭 → 배경으로 사용 ──────────
food_img = Image.open("블루베리_팬케이크_깔롱.png").convert("RGBA")
img_w, img_h = food_img.size
target_ratio = W / H  # 1080/1350 = 0.8

if img_w / img_h > target_ratio:  # 원본이 더 가로로 넓을 때 → 좌우 크롭
    new_w = int(img_h * target_ratio)
    left = (img_w - new_w) // 2
    food_img = food_img.crop((left, 0, left + new_w, img_h))
else:  # 원본이 더 세로로 길 때 → 상하 크롭
    new_h = int(img_w / target_ratio)
    top = (img_h - new_h) // 2
    food_img = food_img.crop((0, top, img_w, top + new_h))

bg = food_img.resize((W, H), Image.LANCZOS)

# ── RGBA 오버레이 레이어 ──────────────────────────────
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))  # 투명 레이어
draw = ImageDraw.Draw(overlay)

# ── 폰트 경로 ──────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_KO = os.path.join(BASE_DIR, "font", "NeoHyundai_B.ttf")
FONT_KO2 = os.path.join(BASE_DIR, "font", "ZEN-SERIF-TTF-Regular.ttf")
FONT_EN = os.path.join(BASE_DIR, "font", "Nicholas.ttf")

font_date = ImageFont.truetype(FONT_KO2, 35)  # 13 × 2.7
font_title = ImageFont.truetype(FONT_EN, 110)  # 42 × 2.7
font_sub = ImageFont.truetype(FONT_KO2, 48)  # 18 × 2.7
font_body = ImageFont.truetype(FONT_KO2, 40)  # 15 × 2.7
font_small = ImageFont.truetype(FONT_KO2, 35)  # 13 × 2.7


# ── 헬퍼: 텍스트 중앙 정렬 ──────────────────────────
def draw_centered(text, y, font, color=WHITE, x_start=0, x_end=W):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = x_start + (x_end - x_start - tw) // 2
    draw.text((x, y), text, font=font, fill=color)


# ── 반투명 박스 헬퍼 ────────────────────────────────
def draw_box(x1, y1, x2, y2, fill=BOX_FILL, outline=BOX_OUTLINE, radius=16):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=None)


# ── 텍스트에 딱 맞는 박스 + 텍스트 그리기 ───────────
PAD_X, PAD_Y = 24, 16  # 텍스트 여백


def draw_text_box(
    text, x, y, font, color=WHITE, fill=BOX_FILL, radius=16, center_x=None
):
    """텍스트 크기에 맞게 박스를 자동 계산하고 그린다.
    center_x: 지정 시 해당 x 기준으로 가운데 정렬
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if center_x is not None:
        x = center_x - tw // 2 - PAD_X
    bx1, by1 = x, y
    bx2, by2 = x + tw + PAD_X * 2, y + th + PAD_Y * 2
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=radius, fill=fill)
    draw.text((bx1 + PAD_X, by1 + PAD_Y), text, font=font, fill=color)
    return by2  # 다음 요소 배치에 사용 가능한 y 반환


# ── 물결 하단 영역 헬퍼 ─────────────────────────────
def draw_wave_bottom(
    draw_obj, width, height, wave_color, amplitude=10, frequency=0.02, offset_y=None
):
    if offset_y is None:
        offset_y = height - 100
    points = [(0, height)]
    for x in range(0, width + 1):
        y = offset_y + amplitude * math.sin(x * frequency * math.pi)
        points.append((x, y))
    points.append((width, height))
    draw_obj.polygon(points, fill=wave_color)


# ════════════════════════════════════════════════════
# 1) 날짜 (박스 없음)
# ════════════════════════════════════════════════════
draw.text((43, 40), f"{date}", font=font_date, fill=WHITE, stroke_fill=WHITE)

# ════════════════════════════════════════════════════
# 2) 타이틀 박스 (텍스트 크기에 맞춤, 중앙 정렬)
# ════════════════════════════════════════════════════
draw_text_box("DELICIOUS", 0, 99, font_title, center_x=W // 2)

# ════════════════════════════════════════════════════
# 3) 식당 이름 박스 (중앙 정렬)
# ════════════════════════════════════════════════════
draw_text_box(restaurant, 0, 280, font_sub, center_x=W // 2)

# ════════════════════════════════════════════════════
# 4) 음식 이름 박스 (우측)
# ════════════════════════════════════════════════════
draw_text_box(food_name, W // 2, 410, font_body)

# ════════════════════════════════════════════════════
# 5) 가게 정보 박스 (하단 좌측, 가장 긴 텍스트 기준 단일 박스)
# ════════════════════════════════════════════════════
store_lines = [store_name, store_phone, store_hours]
line_height = draw.textbbox((0, 0), store_name, font=font_body)[3] + PAD_Y
max_w = max(draw.textbbox((0, 0), t, font=font_body)[2] for t in store_lines)
bx1, by1 = 27, 810
bx2 = bx1 + max_w + PAD_X * 2
by2 = by1 + line_height * len(store_lines) + PAD_Y
draw.rounded_rectangle([bx1, by1, bx2, by2], radius=16, fill=BOX_FILL)
for i, line in enumerate(store_lines):
    draw.text(
        (bx1 + PAD_X, by1 + PAD_Y + i * line_height), line, font=font_body, fill=WHITE
    )

# ════════════════════════════════════════════════════
# 6) 가게 광고 - 물결 하단 영역
# ════════════════════════════════════════════════════
WAVE_COLOR = (0, 0, 0, 160)  # 반투명 물결
draw_wave_bottom(
    draw, W, H, wave_color=WAVE_COLOR, amplitude=32, frequency=0.003, offset_y=1148
)
draw.text((54, 1193), store_ad, font=font_body, fill=WHITE)

# ── 합성 및 저장 ─────────────────────────────────────
result = Image.alpha_composite(bg, overlay)
output_path = "output_layout.png"
result.convert("RGB").save(output_path)
print(f"저장 완료: {output_path}")
result.show()
