from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "avatar.png"
OUT = ROOT / "assets" / "visemes"


SHAPES = {
    "neutral": {"open": 0.05, "wide": 0.44, "round": 0.10, "smile": 0.18},
    "closed": {"open": 0.01, "wide": 0.42, "round": 0.08, "smile": 0.12},
    "aa": {"open": 0.90, "wide": 0.56, "round": 0.12, "smile": 0.10},
    "ee": {"open": 0.38, "wide": 0.95, "round": 0.04, "smile": 0.26},
    "oh": {"open": 0.62, "wide": 0.28, "round": 0.88, "smile": 0.06},
    "u": {"open": 0.36, "wide": 0.18, "round": 1.0, "smile": 0.04},
    "wide_open": {"open": 0.78, "wide": 0.88, "round": 0.08, "smile": 0.16},
    "soft_smile": {"open": 0.16, "wide": 0.68, "round": 0.08, "smile": 0.40},
}


def resize_canvas(img: Image.Image, target_h: int = 1280) -> Image.Image:
    scale = target_h / img.height
    return img.resize((round(img.width * scale), target_h), Image.Resampling.LANCZOS)


def soft_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(-1, 1, h)[:, None]
    arr = (((x / 0.98) ** 2 + (y / 0.74) ** 2) <= 1).astype(np.uint8) * 255
    return Image.fromarray(arr, "L").filter(ImageFilter.GaussianBlur(7))


def make_patch(base: Image.Image, shape: dict[str, float]) -> Image.Image:
    w, h = base.size
    cx, cy = int(w * 0.505), int(h * 0.468)
    pw, ph = int(w * 0.245), int(h * 0.105)
    x0, y0 = cx - pw // 2, cy - ph // 2
    patch = base.crop((x0, y0, x0 + pw, y0 + ph)).convert("RGBA")

    overlay = Image.new("RGBA", patch.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    pcx, pcy = pw * 0.50, ph * 0.52

    mouth_w = pw * (0.31 + shape["wide"] * 0.22 - shape["round"] * 0.10)
    mouth_h = ph * (0.035 + shape["open"] * 0.45 + shape["round"] * 0.12)
    if shape["round"] > 0.55:
        mouth_w *= 0.68
        mouth_h *= 1.20
    if shape["open"] < 0.04:
        mouth_h = ph * 0.020
        mouth_w *= 0.92

    left = pcx - mouth_w / 2
    right = pcx + mouth_w / 2
    top = pcy - mouth_h / 2
    bottom = pcy + mouth_h / 2

    shadow = Image.new("RGBA", patch.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse(
        [pcx - mouth_w * 0.62, pcy + mouth_h * 0.20, pcx + mouth_w * 0.62, pcy + mouth_h * 1.08],
        fill=(0, 0, 0, int(44 * shape["open"])),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    patch = Image.alpha_composite(patch, shadow)

    draw.ellipse([left, top, right, bottom], fill=(17, 3, 8, int(180 + shape["open"] * 50)))
    if shape["open"] > 0.30 and shape["round"] < 0.70:
        draw.rounded_rectangle(
            [
                left + mouth_w * 0.22,
                top + mouth_h * 0.10,
                right - mouth_w * 0.22,
                top + mouth_h * 0.10 + max(2, mouth_h * 0.12),
            ],
            radius=3,
            fill=(242, 219, 204, int(48 + shape["open"] * 52)),
        )

    lip = (130, 48, 62, 142)
    dark = (58, 18, 29, 150)
    high = (246, 136, 136, 70)
    draw.arc([left - 5, top - 8, right + 5, bottom + 2], 190, 350, fill=lip, width=4)
    draw.arc([left - 2, top + 2, right + 2, bottom + 8], 10, 170, fill=dark, width=4)
    draw.line(
        [left, pcy + shape["smile"] * 6, pcx, pcy + mouth_h * 0.10, right, pcy + shape["smile"] * 6],
        fill=(38, 12, 20, 100),
        width=2,
    )
    draw.arc(
        [left + mouth_w * 0.15, top + mouth_h * 0.08, right - mouth_w * 0.15, bottom + mouth_h * 0.26],
        205,
        335,
        fill=high,
        width=2,
    )

    overlay = overlay.filter(ImageFilter.GaussianBlur(0.35))
    patch = Image.alpha_composite(patch, overlay)
    alpha = soft_mask(patch.size)
    patch.putalpha(alpha)
    return patch


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = resize_canvas(Image.open(SOURCE).convert("RGB"))
    for name, shape in SHAPES.items():
        make_patch(base, shape).save(OUT / f"{name}.png")
    print(OUT)


if __name__ == "__main__":
    main()
