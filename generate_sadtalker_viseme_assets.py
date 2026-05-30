from __future__ import annotations

import shutil
import subprocess
import os
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent
SADTALKER = Path(r"C:\tmp\SadTalker_src\SadTalker-main")
PYTHON = Path(r"C:\tmp\sadtalker_env\Scripts\python.exe")
FFMPEG = Path(r"C:\tmp\ffmpeg_bin\ffmpeg.exe")
SOURCE_IMAGE = ROOT / "assets" / "avatar.png"
WORK = ROOT / "sadtalker_viseme_work"
OUT = ROOT / "assets" / "visemes"

VISEMES = [
    ("neutral", "嗯。", 0.42),
    ("closed", "嗯。", 0.30),
    ("aa", "啊。", 0.42),
    ("ee", "衣。", 0.42),
    ("oh", "喔。", 0.42),
    ("u", "嗚。", 0.42),
    ("wide_open", "愛。", 0.42),
    ("soft_smile", "嘿。", 0.42),
]


def run(args: list[str | Path], cwd: Path | None = None) -> None:
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def synthesize_clip(name: str, text: str) -> Path:
    wav = WORK / f"{name}.wav"
    ps1 = WORK / f"speak_{name}.ps1"
    escaped_text = text.replace("'", "''")
    escaped_wav = str(wav).replace("'", "''")
    ps1.write_text(
        "\n".join(
            [
                "Add-Type -AssemblyName System.Speech",
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                "$s.SelectVoice('Microsoft Hanhan Desktop')",
                "$s.Rate = -3",
                "$s.Volume = 100",
                f"$s.SetOutputToWaveFile('{escaped_wav}')",
                f"$s.Speak('{escaped_text}')",
                "$s.Dispose()",
            ]
        ),
        encoding="utf-8-sig",
    )
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1])
    return wav


def latest_mp4(result_dir: Path) -> Path:
    files = sorted(result_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No mp4 output in {result_dir}")
    return files[0]


def crop_mouth_patch(frame: Path, dest: Path) -> None:
    img = Image.open(frame).convert("RGBA")
    # SadTalker 256 output usually centers the face. Use a generous mouth/lower-face crop
    # so the HTML can blend it back into the original portrait.
    w, h = img.size
    cx = w * 0.50
    cy = h * 0.56
    pw = w * 0.52
    ph = h * 0.25
    box = (
        round(cx - pw / 2),
        round(cy - ph / 2),
        round(cx + pw / 2),
        round(cy + ph / 2),
    )
    patch = img.crop(box)
    alpha = Image.new("L", patch.size, 0)
    aw, ah = patch.size
    mask = Image.new("L", patch.size, 0)
    px = mask.load()
    for y in range(ah):
        ny = (y / max(1, ah - 1)) * 2 - 1
        for x in range(aw):
            nx = (x / max(1, aw - 1)) * 2 - 1
            if (nx / 0.98) ** 2 + (ny / 0.74) ** 2 <= 1:
                px[x, y] = 255
    alpha = mask.filter(ImageFilter.GaussianBlur(8))
    patch.putalpha(alpha)
    patch.save(dest)


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    portrait = WORK / "portrait.png"
    shutil.copy2(SOURCE_IMAGE, portrait)

    env = {
        "TORCH_HOME": r"C:\tmp\torch_cache",
        "MPLCONFIGDIR": r"C:\tmp\matplotlib_cache",
        "SADTALKER_FFMPEG": str(FFMPEG),
    }

    for name, text, extract_at in VISEMES:
        print(f"=== {name}: {text} ===", flush=True)
        wav = synthesize_clip(name, text)
        result_dir = WORK / f"result_{name}"
        result_dir.mkdir(exist_ok=True)
        subprocess.run(
            [
                str(PYTHON),
                "inference.py",
                "--driven_audio",
                str(wav),
                "--source_image",
                str(portrait),
                "--checkpoint_dir",
                str(SADTALKER / "checkpoints"),
                "--result_dir",
                str(result_dir),
                "--size",
                "256",
                "--preprocess",
                "crop",
                "--still",
                "--cpu",
                "--batch_size",
                "1",
            ],
            cwd=SADTALKER,
            check=True,
            env={**os.environ, **env},
        )
        mp4 = latest_mp4(result_dir)
        frame = WORK / f"{name}_frame.png"
        run([FFMPEG, "-y", "-ss", str(extract_at), "-i", mp4, "-frames:v", "1", "-update", "1", frame])
        crop_mouth_patch(frame, OUT / f"{name}.png")
        print(f"saved {OUT / f'{name}.png'}", flush=True)


if __name__ == "__main__":
    main()
