import base64
import io
import json
import sys
from PIL import Image, ImageOps


def decode_data_url(value):
    if "," in value:
        header, data = value.split(",", 1)
        mime = "image/png"
        if header.startswith("data:") and ";" in header:
            mime = header[5:].split(";", 1)[0]
        return mime, base64.b64decode(data)
    return "image/png", base64.b64decode(value)


def average_region(mask, box):
    region = mask.crop(box)
    histogram = region.histogram()
    total = sum(histogram)
    if not total:
        return 0
    return sum(index * count for index, count in enumerate(histogram)) / total


def maybe_invert(mask):
    width, height = mask.size
    border = Image.new("L", mask.size, 0)
    border.paste(mask.crop((0, 0, width, max(1, height // 8))), (0, 0))
    border.paste(mask.crop((0, height - max(1, height // 8), width, height)), (0, height - max(1, height // 8)))
    center_box = (
        width // 4,
        height // 4,
        max(width // 4 + 1, (width * 3) // 4),
        max(height // 4 + 1, (height * 3) // 4),
    )
    center_brightness = average_region(mask, center_box)
    border_brightness = average_region(
        border,
        (0, 0, width, height),
    )
    if border_brightness > center_brightness:
        return ImageOps.invert(mask)
    return mask


def main():
    payload = json.load(sys.stdin)
    _, image_bytes = decode_data_url(payload["image_data"])
    _, mask_bytes = decode_data_url(payload["mask_data"])

    original = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mask = Image.open(io.BytesIO(mask_bytes)).convert("L").resize(original.size)
    mask = maybe_invert(mask)

    rgba = original.copy()
    rgba.putalpha(mask)

    output = io.BytesIO()
    rgba.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("utf-8")
    sys.stdout.write(json.dumps({"image_data_url": f"data:image/png;base64,{encoded}"}))


if __name__ == "__main__":
    main()
