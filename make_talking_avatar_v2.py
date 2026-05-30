from __future__ import annotations

import math
import wave
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parent
REFERENCE_PROJECT = ROOT.parent / "\u7ba1\u7406\u5b78\u9662\u7684\u4ecb\u7d39"
FFMPEG = REFERENCE_PROJECT / "node_modules" / "ffmpeg-static" / "ffmpeg.exe"
SOURCE_IMAGE = (
    Path.home()
    / "Pictures"
    / "AI_design"
    / "ChatGPT Image 2026\u5e745\u670828\u65e5 \u4e0b\u534803_10_51 (2).png"
)
OUT_DIR = ROOT / "talking_avatar_output"
VOICE_MP3 = OUT_DIR / "xiaozheng_edge_neural_voice.mp3"
VOICE_WAV = OUT_DIR / "xiaozheng_edge_neural_voice.wav"
SILENT_VIDEO = OUT_DIR / "xiaozheng_talking_avatar_v2_silent.mp4"
OUT_VIDEO = OUT_DIR / "xiaozheng_talking_avatar_v2.mp4"

SEGMENTS = [
    ("\u4f60\u597d\uff0c\u4e3b\u4eba\uff0c\u6211\u662f\u5c0f\u6b63\u52a9\u7406\u3002", 0.35),
    ("\u6211\u662f\u4e00\u4f4d AI \u5c0f\u52a9\u624b\uff0c\u5f88\u9ad8\u8208\u80fd\u5920\u966a\u4f34\u4f60\u3002", 0.35),
    ("\u6211\u53ef\u4ee5\u66ff\u4f60\u5b8c\u6210\u5f88\u591a\u4e8b\u60c5\uff0c\u50cf\u662f\u63d0\u9192\u884c\u7a0b\u3001\u6574\u7406\u8cc7\u6599\u3001\u67e5\u8a62\u8cc7\u8a0a\u3001\u56de\u7b54\u554f\u984c\uff0c\u4e5f\u53ef\u4ee5\u5354\u52a9\u4f60\u63a7\u5236\u5404\u7a2e\u667a\u6167\u8a2d\u5099\u3002", 0.45),
    ("\u672a\u4f86\uff0c\u6211\u6703\u76e1\u529b\u5e6b\u52a9\u4f60\uff0c\u8b93\u5de5\u4f5c\u3001\u5b78\u7fd2\u548c\u751f\u6d3b\u8b8a\u5f97\u66f4\u7c21\u55ae\u3001\u66f4\u6709\u6548\u7387\u3002", 0.40),
    ("\u5e0c\u671b\u4f60\u6703\u559c\u6b61\u6211\u3002", 0.35),
    ("\u5f9e\u73fe\u5728\u958b\u59cb\uff0c\u5c31\u8b93\u6211\u6210\u70ba\u4f60\u6700\u8cbc\u5fc3\u7684 AI \u5c0f\u52a9\u624b\u3002", 0.0),
]


WIDE_CHARS = set("\u4f60\u662f\u4e00\u4f4d\u7406\u63d0\u9192\u884c\u8cc7\u8a0a\u984c\u4e5f\u5354\u8a2d\u5099\u672a\u529b\u5b78\u7fd2\u7c21\u6548\u7387\u559c\u958b\u59cb\u8cbc\u5fc3\u7684")
ROUND_CHARS = set("\u4e3b\u6211\u5c0f\u6b63\u52a9\u624b\u5f88\u5920\u591a\u505a\u56de\u554f\u63a7\u7a2e\u667a\u6167\u6703\u5f9e\u5de5\u4f5c\u751f\u6d3b")
OPEN_CHARS = set("\u597d\u4eba\u9ad8\u4f34\u5b8c\u7b54\u8b93\u55ae\u6b61\u67e5\u6599\u50cf\u5e0c\u671b")
CLOSED_CHARS = set("\u6211\u4f4d\u966a\u4f34\u5e6b\u5099\u8b8a\u554f")


def run_ffmpeg(args: list[str | Path]) -> None:
    import subprocess

    subprocess.run([str(arg) for arg in args], check=True)


def resize_canvas(img: Image.Image, target_h: int = 1280) -> Image.Image:
    scale = target_h / img.height
    return img.resize((round(img.width * scale), target_h), Image.Resampling.LANCZOS)


def wav_envelope(fps: int) -> np.ndarray:
    with wave.open(str(VOICE_WAV), "rb") as wav:
        rate = wav.getframerate()
        channels = wav.getnchannels()
        raw = wav.readframes(wav.getnframes())

    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)

    step = max(1, int(rate / fps))
    count = math.ceil(len(audio) / step)
    env = np.zeros(count, dtype=np.float32)
    for i in range(count):
        chunk = audio[i * step : (i + 1) * step]
        if len(chunk):
            env[i] = float(np.sqrt(np.mean(chunk * chunk)))
    if env.max() > 0:
        env /= max(1.0, np.percentile(env, 95))
    env = np.clip(env, 0, 1)
    env = np.convolve(env, np.array([0.05, 0.16, 0.28, 0.32, 0.14, 0.05], dtype=np.float32), mode="same")
    return np.clip(env, 0, 1)


def duration_seconds(path: Path) -> float:
    container = av.open(str(path))
    try:
        if container.duration:
            return float(container.duration / av.time_base)
        stream = container.streams.audio[0]
        return float(stream.duration * stream.time_base)
    finally:
        container.close()


def build_timeline() -> list[tuple[float, float, str]]:
    timeline: list[tuple[float, float, str]] = []
    cursor = 0.0
    for index, (text, pause) in enumerate(SEGMENTS):
        part = OUT_DIR / f"xiaozheng-part-{index:02d}.mp3"
        duration = duration_seconds(part)
        chars = [ch for ch in text if ch.strip() and ch not in "\uff0c\u3001\u3002"]
        total_weight = sum(1.25 if ch in "AI" else 1.0 for ch in chars) or 1.0
        unit = duration / total_weight
        for ch in chars:
            weight = 1.25 if ch in "AI" else 1.0
            start = cursor
            cursor += unit * weight
            timeline.append((start, cursor, ch))
        cursor += pause
    return timeline


def char_at(t: float, timeline: list[tuple[float, float, str]]) -> str:
    lo, hi = 0, len(timeline) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        start, end, ch = timeline[mid]
        if start <= t < end:
            return ch
        if t < start:
            hi = mid - 1
        else:
            lo = mid + 1
    return ""


def viseme(ch: str, amp: float, t: float) -> dict[str, float]:
    # Values are intentionally restrained: natural assistant speech, not theatrical lip-sync.
    pulse = 0.5 + 0.5 * math.sin(t * 34.0)
    amount = max(0.05, amp)
    if not ch:
        return {"open": 0.03, "wide": 0.45, "round": 0.15, "smile": 0.18, "closed": 0.8}
    if ch in CLOSED_CHARS and pulse < 0.38:
        return {"open": 0.02, "wide": 0.48, "round": 0.12, "smile": 0.14, "closed": 1.0}
    if ch in WIDE_CHARS:
        return {"open": 0.16 + 0.34 * amount, "wide": 0.9, "round": 0.05, "smile": 0.24, "closed": 0.0}
    if ch in ROUND_CHARS:
        return {"open": 0.18 + 0.44 * amount, "wide": 0.28, "round": 0.95, "smile": 0.08, "closed": 0.0}
    if ch in OPEN_CHARS:
        return {"open": 0.30 + 0.55 * amount, "wide": 0.62, "round": 0.22, "smile": 0.12, "closed": 0.0}
    return {"open": 0.18 + 0.42 * amount, "wide": 0.58, "round": 0.18, "smile": 0.16, "closed": 0.0}


def soft_ellipse_mask(size: tuple[int, int], rx: float = 0.95, ry: float = 0.75, blur: int = 6) -> Image.Image:
    w, h = size
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(-1, 1, h)[:, None]
    arr = (((x / rx) ** 2 + (y / ry) ** 2) <= 1).astype(np.uint8) * 255
    return Image.fromarray(arr, "L").filter(ImageFilter.GaussianBlur(blur))


def warp_mouth_region(region: Image.Image, shape: dict[str, float], frame_index: int) -> Image.Image:
    arr = np.asarray(region).astype(np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx - w / 2) / (w / 2)
    ny = (yy - h / 2) / (h / 2)
    r2 = nx * nx / 1.15 + ny * ny / 0.9
    weight = np.exp(-r2 * 2.2)

    open_amt = shape["open"]
    wide = shape["wide"]
    round_amt = shape["round"]
    smile = shape["smile"]
    wobble = math.sin(frame_index * 0.47) * 0.012

    scale_x = 1.0 + weight * (0.18 * wide - 0.17 * round_amt + wobble)
    scale_y = 1.0 + weight * (0.22 * open_amt + 0.12 * round_amt)
    curve = smile * (nx * nx - 0.25) * h * 0.04

    src_x = w / 2 + (xx - w / 2) / scale_x
    src_y = h / 2 + (yy - h / 2 - curve) / scale_y
    src_x = np.clip(src_x, 0, w - 1)
    src_y = np.clip(src_y, 0, h - 1)

    x0 = np.floor(src_x).astype(np.int32)
    y0 = np.floor(src_y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    ax = src_x - x0
    ay = src_y - y0
    warped = (
        arr[y0, x0] * (1 - ax)[..., None] * (1 - ay)[..., None]
        + arr[y0, x1] * ax[..., None] * (1 - ay)[..., None]
        + arr[y1, x0] * (1 - ax)[..., None] * ay[..., None]
        + arr[y1, x1] * ax[..., None] * ay[..., None]
    )
    return Image.fromarray(np.clip(warped, 0, 255).astype(np.uint8))


def draw_lips(region: Image.Image, shape: dict[str, float]) -> Image.Image:
    w, h = region.size
    result = region.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    cx, cy = w * 0.50, h * 0.51
    open_amt = shape["open"] * (1 - 0.82 * shape["closed"])
    mouth_w = w * (0.34 + 0.18 * shape["wide"] - 0.10 * shape["round"])
    mouth_h = h * (0.035 + 0.23 * open_amt + 0.10 * shape["round"])
    if shape["closed"] > 0.7:
        mouth_h = h * 0.018
        mouth_w *= 0.92

    if shape["round"] > 0.55:
        mouth_w *= 0.72
        mouth_h *= 1.28
    left = cx - mouth_w / 2
    right = cx + mouth_w / 2
    top = cy - mouth_h / 2
    bottom = cy + mouth_h / 2

    cavity_alpha = int(175 * min(1.0, open_amt + 0.15 * shape["round"]))
    draw.ellipse([left, top, right, bottom], fill=(18, 5, 8, cavity_alpha))
    if open_amt > 0.22 and shape["round"] < 0.7:
        teeth_h = max(1, int(h * 0.018 * open_amt))
        draw.rounded_rectangle(
            [left + mouth_w * 0.20, top + mouth_h * 0.10, right - mouth_w * 0.20, top + mouth_h * 0.10 + teeth_h],
            radius=2,
            fill=(236, 211, 194, int(75 * open_amt)),
        )

    lip_color = (125, 54, 63, 120)
    hi_color = (232, 134, 132, 80)
    line_y = cy + h * (0.004 + 0.03 * shape["smile"])
    draw.arc([left - 5, top - 5, right + 5, bottom + 2], 190, 350, fill=lip_color, width=3)
    draw.arc([left - 2, top + 2, right + 2, bottom + 8], 10, 170, fill=(92, 34, 45, 105), width=3)
    draw.line([left, line_y, cx, line_y + mouth_h * 0.10, right, line_y], fill=(45, 18, 25, 105), width=2)
    draw.arc([left + mouth_w * 0.16, cy, right - mouth_w * 0.16, bottom + h * 0.12], 25, 155, fill=hi_color, width=2)

    overlay = overlay.filter(ImageFilter.GaussianBlur(0.55))
    return Image.alpha_composite(result, overlay).convert("RGB")


def make_frame(base: Image.Image, env: np.ndarray, timeline: list[tuple[float, float, str]], index: int, fps: int) -> Image.Image:
    t = index / fps
    amp = float(env[min(index, len(env) - 1)])
    shape = viseme(char_at(t, timeline), amp, t)

    frame = base.copy()
    w, h = frame.size

    face_box = (int(w * 0.285), int(h * 0.255), int(w * 0.720), int(h * 0.585))
    face = frame.crop(face_box)
    face = ImageEnhance.Brightness(face).enhance(1.0 + 0.006 * math.sin(t * 2.7))
    frame.paste(face, face_box)

    cx = int(w * 0.505)
    cy = int(h * 0.470)
    mw = int(w * 0.205)
    mh = int(h * 0.078)
    box = (cx - mw // 2, cy - mh // 2, cx + mw // 2, cy + mh // 2)
    mouth_region = frame.crop(box)
    mouth_region = warp_mouth_region(mouth_region, shape, index)
    mouth_region = draw_lips(mouth_region, shape)
    mask = soft_ellipse_mask(mouth_region.size, 0.97, 0.72, 5)
    frame.paste(mouth_region, box[:2], mask)

    jaw_open = shape["open"] * amp
    if jaw_open > 0.08:
        shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(shadow)
        draw.ellipse(
            [int(w * 0.365), int(h * 0.505), int(w * 0.645), int(h * 0.640)],
            fill=(0, 0, 0, int(18 * jaw_open)),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        frame = Image.alpha_composite(frame.convert("RGBA"), shadow).convert("RGB")

    blink_phase = t % 5.3
    if blink_phase < 0.10:
        arr = np.array(frame).copy()
        for ex in (int(w * 0.406), int(w * 0.595)):
            ey = int(h * 0.347)
            ew = int(w * 0.085)
            eh = int(h * 0.010)
            y0, y1 = max(0, ey - eh), min(h, ey + eh)
            x0, x1 = max(0, ex - ew // 2), min(w, ex + ew // 2)
            patch = arr[y0:y1, x0:x1]
            if patch.size:
                color = patch.mean(axis=(0, 1)).astype(np.uint8)
                arr[y0:y1, x0:x1] = (0.55 * patch + 0.45 * color).astype(np.uint8)
        frame = Image.fromarray(arr)

    return frame


def encode() -> None:
    fps = 30
    env = wav_envelope(fps)
    timeline = build_timeline()
    base = resize_canvas(Image.open(SOURCE_IMAGE).convert("RGB"))

    container = av.open(str(SILENT_VIDEO), "w")
    stream = container.add_stream("libx264", rate=fps)
    stream.width = base.width
    stream.height = base.height
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "18", "preset": "medium"}

    for index in range(len(env)):
        frame = av.VideoFrame.from_image(make_frame(base, env, timeline, index, fps))
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()

    run_ffmpeg(
        [
            FFMPEG,
            "-y",
            "-i",
            SILENT_VIDEO,
            "-i",
            VOICE_MP3,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "144k",
            "-shortest",
            OUT_VIDEO,
        ]
    )
    print(OUT_VIDEO)


if __name__ == "__main__":
    encode()
