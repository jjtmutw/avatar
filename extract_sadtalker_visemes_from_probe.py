from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent
FFMPEG = Path(r"C:\tmp\ffmpeg_bin\ffmpeg.exe")
PROBE_VIDEO = Path(r"C:\tmp\sadtalker_test\result_short4\2026_05_28_18.03.57.mp4")
FRAME_DIR = ROOT / "sadtalker_viseme_frames"
OUT = ROOT / "assets" / "visemes"

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


def make_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    px = mask.load()
    for y in range(h):
        ny = (y / max(1, h - 1)) * 2 - 1
        for x in range(w):
            nx = (x / max(1, w - 1)) * 2 - 1
            if (nx / 0.98) ** 2 + (ny / 0.78) ** 2 <= 1:
                px[x, y] = 255
    return mask.filter(ImageFilter.GaussianBlur(5))


def crop_patch(frame_path: Path, out_path: Path) -> None:
    img = Image.open(frame_path).convert("RGBA")
    w, h = img.size
    # SadTalker output is square and face-centered. Crop only the mouth band,
    # then pad it back to the original mouth-patch ratio so the HTML overlay
    # keeps the same size without carrying the nose into the viseme image.
    cx = w * 0.50
    cy = h * 0.73
    pw = round(w * 0.51)
    crop_h = round(h * 0.13)
    canvas_h = round(h * 0.25)
    box = (
        round(cx - pw / 2),
        round(cy - crop_h / 2),
        round(cx + pw / 2),
        round(cy + crop_h / 2),
    )
    mouth_band = img.crop(box)
    mouth_band.putalpha(make_mask(mouth_band.size))

    patch = Image.new("RGBA", (pw, canvas_h), (0, 0, 0, 0))
    patch.alpha_composite(mouth_band, (0, round((canvas_h - crop_h) / 2)))
    patch.save(out_path)


def main() -> None:
    if not PROBE_VIDEO.exists():
        raise FileNotFoundError(PROBE_VIDEO)
    FRAME_DIR.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    for name, timecode in FRAME_MAP.items():
        frame = FRAME_DIR / f"{name}.png"
        run([FFMPEG, "-y", "-ss", str(timecode), "-i", PROBE_VIDEO, "-frames:v", "1", "-update", "1", frame])
        crop_patch(frame, OUT / f"{name}.png")
        print(f"updated {OUT / f'{name}.png'}")


if __name__ == "__main__":
    main()
