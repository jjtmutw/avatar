from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent
FFMPEG = Path(r"C:\tmp\ffmpeg_bin\ffmpeg.exe")
PROBE_VIDEO = Path(r"C:\tmp\sadtalker_test\result_short4\2026_05_28_18.03.57.mp4")
FRAME_DIR = ROOT / "sadtalker_viseme_frames"
OUT = ROOT / "assets" / "face_visemes"

FRAME_MAP = {
    "neutral": 0.02,
    "closed": 0.04,
    "soft_smile": 0.10,
    "ee": 0.16,
    "aa": 0.24,
    "wide_open": 0.30,
    "oh": 0.40,
    "u": 0.50,
}


def run(args: list[str | Path]) -> None:
    subprocess.run([str(arg) for arg in args], check=True)


def soft_face_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    px = mask.load()
    for y in range(h):
        ny = ((y / max(1, h - 1)) - 0.50) / 0.55
        for x in range(w):
            nx = (x / max(1, w - 1)) * 2 - 1
            if (nx / 0.98) ** 2 + ny**2 <= 1:
                px[x, y] = 255
    return mask.filter(ImageFilter.GaussianBlur(9))


def crop_face_patch(frame_path: Path, out_path: Path) -> None:
    img = Image.open(frame_path).convert("RGBA")
    w, h = img.size

    cx = w * 0.50
    cy = h * 0.735
    patch_w = round(w * 0.58)
    patch_h = round(h * 0.40)
    box = (
        round(cx - patch_w / 2),
        round(cy - patch_h / 2),
        round(cx + patch_w / 2),
        round(cy + patch_h / 2),
    )
    patch = img.crop(box)
    patch.putalpha(soft_face_mask(patch.size))
    patch.save(out_path)


def main() -> None:
    if not PROBE_VIDEO.exists():
        raise FileNotFoundError(PROBE_VIDEO)
    FRAME_DIR.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    for name, timecode in FRAME_MAP.items():
        frame = FRAME_DIR / f"{name}.png"
        if not frame.exists():
            run([FFMPEG, "-y", "-ss", str(timecode), "-i", PROBE_VIDEO, "-frames:v", "1", "-update", "1", frame])
        crop_face_patch(frame, OUT / f"{name}.png")
        print(f"updated {OUT / f'{name}.png'}")


if __name__ == "__main__":
    main()
