from __future__ import annotations

import math
import subprocess
import sys
import wave
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parent
REFERENCE_PROJECT = Path(r"C:\Users\jjpc2\Documents\管理學院的介紹")
TTS_PACKAGES = REFERENCE_PROJECT / ".py-tts"
FFMPEG = REFERENCE_PROJECT / "node_modules" / "ffmpeg-static" / "ffmpeg.exe"
SOURCE_IMAGE = Path(r"C:\Users\jjpc2\Pictures\AI_design\ChatGPT Image 2026年5月28日 下午03_10_51 (2).png")
OUT_DIR = ROOT / "talking_avatar_output"
VOICE_MP3 = OUT_DIR / "xiaozheng_edge_neural_voice.mp3"
VOICE_WAV = OUT_DIR / "xiaozheng_edge_neural_voice.wav"
SILENT_VIDEO = OUT_DIR / "xiaozheng_talking_avatar_silent.mp4"
OUT_VIDEO = OUT_DIR / "xiaozheng_talking_avatar.mp4"

SEGMENTS = [
    ("你好，主人，我是小正助理。", "-8%", "+5Hz", 0.35),
    ("我是一位 AI 小助手，很高興能夠陪伴你。", "-10%", "+4Hz", 0.35),
    ("我可以替你完成很多事情，像是提醒行程、整理資料、查詢資訊、回答問題，也可以協助你控制各種智慧設備。", "-9%", "+4Hz", 0.45),
    ("未來，我會盡力幫助你，讓工作、學習和生活變得更簡單、更有效率。", "-8%", "+5Hz", 0.4),
    ("希望你會喜歡我。", "-7%", "+6Hz", 0.35),
    ("從現在開始，就讓我成為你最貼心的 AI 小助手。", "-8%", "+5Hz", 0.0),
]


def run(args: list[str | Path]) -> None:
    subprocess.run([str(arg) for arg in args], cwd=OUT_DIR, check=True)


async def synthesize_voice() -> None:
    if str(TTS_PACKAGES) not in sys.path:
        sys.path.insert(0, str(TTS_PACKAGES))
    import edge_tts

    OUT_DIR.mkdir(exist_ok=True)
    for pattern in ("xiaozheng-part-*.mp3", "xiaozheng-pause-*.wav", "xiaozheng-list.txt"):
        for file in OUT_DIR.glob(pattern):
            file.unlink()

    concat_lines: list[str] = []
    for index, (text, rate, pitch, pause) in enumerate(SEGMENTS):
        part = OUT_DIR / f"xiaozheng-part-{index:02d}.mp3"
        communicate = edge_tts.Communicate(
            text=text,
            voice="zh-TW-HsiaoChenNeural",
            rate=rate,
            pitch=pitch,
            volume="+0%",
        )
        await communicate.save(str(part))
        concat_lines.append(f"file '{part.name}'")

        if pause:
            pause_file = OUT_DIR / f"xiaozheng-pause-{index:02d}.wav"
            run(
                [
                    FFMPEG,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=24000:cl=mono",
                    "-t",
                    str(pause),
                    "-acodec",
                    "pcm_s16le",
                    pause_file.name,
                ]
            )
            concat_lines.append(f"file '{pause_file.name}'")

    concat_file = OUT_DIR / "xiaozheng-list.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="ascii")
    run(
        [
            FFMPEG,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file.name,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            VOICE_MP3.name,
        ]
    )
    run(
        [
            FFMPEG,
            "-y",
            "-i",
            VOICE_MP3.name,
            "-ac",
            "1",
            "-ar",
            "24000",
            VOICE_WAV.name,
        ]
    )


def read_audio_envelope(fps: int) -> tuple[np.ndarray, int, int]:
    with wave.open(str(VOICE_WAV), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        raw = wav.readframes(frames)

    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)

    samples_per_frame = max(1, int(sample_rate / fps))
    frame_count = math.ceil(len(audio) / samples_per_frame)
    envelope = np.zeros(frame_count, dtype=np.float32)
    for i in range(frame_count):
        chunk = audio[i * samples_per_frame : (i + 1) * samples_per_frame]
        if len(chunk):
            envelope[i] = float(np.sqrt(np.mean(chunk * chunk)))

    # Smooth and normalize into gentle mouth-open values.
    if envelope.max() > 0:
        envelope /= np.percentile(envelope, 96)
        envelope = np.clip(envelope, 0, 1)
    kernel = np.array([0.08, 0.18, 0.48, 0.18, 0.08], dtype=np.float32)
    envelope = np.convolve(envelope, kernel, mode="same")
    envelope = np.clip(envelope * 1.15, 0, 1)
    return envelope, sample_rate, channels


def resize_canvas(img: Image.Image, target_h: int = 1280) -> Image.Image:
    scale = target_h / img.height
    return img.resize((round(img.width * scale), target_h), Image.Resampling.LANCZOS)


def make_frame(base: Image.Image, mouth_open: float, index: int, fps: int) -> Image.Image:
    frame = base.copy()
    w, h = frame.size

    # Coordinates are proportional to the supplied portrait, keeping the face and outfit unchanged.
    cx = int(w * 0.505)
    cy = int(h * 0.468)
    mw = int(w * 0.138)
    mh = int(h * 0.043)
    open_px = int(2 + mouth_open * h * 0.018)

    box = (cx - mw // 2, cy - mh // 2, cx + mw // 2, cy + mh // 2)
    mouth = frame.crop(box)
    top = mouth.crop((0, 0, mw, mh // 2))
    bottom = mouth.crop((0, mh // 2, mw, mh))

    canvas = Image.new("RGB", (mw, mh + open_px), (18, 8, 10))
    canvas.paste(top, (0, 0))
    canvas.paste(bottom, (0, mh // 2 + open_px))

    # Subtle inner shadow keeps the opening from looking pasted on.
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    yy = mh // 2 + open_px // 2
    for y in range(max(0, yy - open_px), min(canvas.height, yy + open_px + 2)):
        alpha = int(95 * (1 - abs(y - yy) / max(1, open_px + 2)))
        shadow.putalpha(0)
    canvas = ImageEnhance.Contrast(canvas).enhance(1.03)
    canvas = canvas.filter(ImageFilter.SMOOTH_MORE)
    canvas = canvas.resize((mw, mh), Image.Resampling.BICUBIC)

    mask = Image.new("L", (mw, mh), 0)
    mx = np.linspace(-1, 1, mw)[None, :]
    my = np.linspace(-1, 1, mh)[:, None]
    oval = ((mx / 0.98) ** 2 + (my / 0.72) ** 2) <= 1
    mask_arr = (oval.astype(np.uint8) * 255)
    mask_arr = np.minimum(mask_arr, 210)
    mask = Image.fromarray(mask_arr, "L").filter(ImageFilter.GaussianBlur(radius=3))
    frame.paste(canvas, box[:2], mask)

    # Natural micro motion: tiny breathing/head steadiness and occasional blink.
    t = index / fps
    glow = 1.0 + 0.012 * math.sin(t * 2.0)
    frame = ImageEnhance.Brightness(frame).enhance(glow)

    blink_phase = (t % 4.8)
    if 0.0 < blink_phase < 0.12:
        draw = np.array(frame).copy()
        for ex in (int(w * 0.406), int(w * 0.595)):
            ey = int(h * 0.347)
            ew = int(w * 0.084)
            eh = int(h * 0.009)
            y0 = max(0, ey - eh)
            y1 = min(h, ey + eh)
            x0 = max(0, ex - ew // 2)
            x1 = min(w, ex + ew // 2)
            patch = draw[y0:y1, x0:x1]
            if patch.size:
                color = patch.mean(axis=(0, 1)).astype(np.uint8)
                draw[y0:y1, x0:x1] = (0.65 * patch + 0.35 * color).astype(np.uint8)
        frame = Image.fromarray(draw)

    return frame


def encode_video() -> None:
    import asyncio

    fps = 30
    asyncio.run(synthesize_voice())
    envelope, _, _ = read_audio_envelope(fps)
    base = resize_canvas(Image.open(SOURCE_IMAGE).convert("RGB"))

    container = av.open(str(SILENT_VIDEO), mode="w")
    video_stream = container.add_stream("libx264", rate=fps)
    video_stream.width = base.width
    video_stream.height = base.height
    video_stream.pix_fmt = "yuv420p"
    video_stream.options = {"crf": "20", "preset": "medium"}

    for i, amount in enumerate(envelope):
        frame_img = make_frame(base, float(amount), i, fps)
        frame = av.VideoFrame.from_image(frame_img)
        for packet in video_stream.encode(frame):
            container.mux(packet)
    for packet in video_stream.encode():
        container.mux(packet)

    container.close()
    run(
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
            "160k",
            "-shortest",
            OUT_VIDEO,
        ]
    )


if __name__ == "__main__":
    encode_video()
    print(OUT_VIDEO)
