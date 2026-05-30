from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
TTS_PACKAGES = ROOT / "tts_packages"
DEFAULT_VOICE = "zh-TW-HsiaoChenNeural"

if str(TTS_PACKAGES) not in sys.path:
    sys.path.insert(0, str(TTS_PACKAGES))

import edge_tts  # noqa: E402


def edge_rate(value: object) -> str:
    if isinstance(value, str) and value.strip().endswith("%"):
        return value.strip()
    try:
        percent = round((float(value) - 1) * 100)
    except (TypeError, ValueError):
        percent = 0
    return f"{percent:+d}%"


def edge_pitch(value: object) -> str:
    if isinstance(value, str) and value.strip().endswith("Hz"):
        return value.strip()
    try:
        hz = round((float(value) - 1) * 20)
    except (TypeError, ValueError):
        hz = 0
    return f"{hz:+d}Hz"


async def synthesize(text: str, voice: str, rate: object, pitch: object) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=ROOT) as tmp:
        out_path = Path(tmp.name)
    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice or DEFAULT_VOICE,
            rate=edge_rate(rate),
            pitch=edge_pitch(pitch),
            volume="+0%",
        )
        await communicate.save(str(out_path))
        return out_path.read_bytes()
    finally:
        out_path.unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "XiaozhengEdgeTTS/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/tts":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("missing text")
            if len(text) > 2000:
                text = text[:2000]

            audio = asyncio.run(
                synthesize(
                    text=text,
                    voice=str(payload.get("voice") or DEFAULT_VOICE),
                    rate=payload.get("rate", 1),
                    pitch=payload.get("pitch", 1),
                )
            )
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)
        except Exception as exc:
            message = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[Edge TTS] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 5055), Handler)
    print("Edge TTS server: http://127.0.0.1:5055/tts")
    server.serve_forever()


if __name__ == "__main__":
    main()
