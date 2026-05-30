from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


API_URL = "https://api.openai.com/v1/audio/speech"
DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "coral"
DEFAULT_INSTRUCTIONS = "使用溫柔、自信、專業的台灣中文語氣，像可靠的 AI 助理。"


class Handler(BaseHTTPRequestHandler):
    server_version = "XiaozhengOpenAITTS/1.0"

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

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.send_json_error(500, "OPENAI_API_KEY is not set")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("missing text")

            request_body = {
                "model": payload.get("model") or DEFAULT_MODEL,
                "voice": payload.get("voice") or DEFAULT_VOICE,
                "input": text[:4096],
                "instructions": payload.get("instructions") or DEFAULT_INSTRUCTIONS,
                "response_format": "mp3",
                "speed": payload.get("speed") or payload.get("rate") or 1,
            }
            request = urllib.request.Request(
                API_URL,
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                audio = response.read()

            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio)))
            self.end_headers()
            self.wfile.write(audio)
        except urllib.error.HTTPError as exc:
            self.send_json_error(exc.code, exc.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            self.send_json_error(500, str(exc))

    def send_json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[OpenAI TTS] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 5056), Handler)
    print("OpenAI TTS server: http://127.0.0.1:5056/tts")
    server.serve_forever()


if __name__ == "__main__":
    main()
