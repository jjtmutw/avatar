from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


GOOGLE_TTS_API = "https://texttospeech.googleapis.com/v1/text:synthesize"
LISTEN_HOST = os.environ.get("GOOGLE_TTS_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("GOOGLE_TTS_PORT", "5058"))
DEFAULT_LANGUAGE = os.environ.get("GOOGLE_TTS_LANGUAGE", "cmn-TW")
DEFAULT_VOICE = os.environ.get("GOOGLE_TTS_VOICE", "cmn-TW-Wavenet-A")


def clamp_float(value: object, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


class Handler(BaseHTTPRequestHandler):
    server_version = "XiaozhengGoogleTTS/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/health":
            body = json.dumps(
                {
                    "status": "ok",
                    "provider": "google-cloud-text-to-speech",
                    "voice": DEFAULT_VOICE,
                    "language": DEFAULT_LANGUAGE,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/tts":
            self.send_error(404, "Not found")
            return

        api_key = os.environ.get("GOOGLE_TTS_API_KEY", "").strip()
        if not api_key:
            self.send_json_error(500, "GOOGLE_TTS_API_KEY is not set")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(data.get("text", "")).strip()
            if not text:
                raise ValueError("missing text")

            language_code = str(data.get("lang") or data.get("languageCode") or DEFAULT_LANGUAGE)
            voice_name = str(data.get("voice") or DEFAULT_VOICE)
            body = {
                "input": {"text": text[:5000]},
                "voice": {
                    "languageCode": language_code,
                    "name": voice_name,
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": clamp_float(data.get("rate"), 1.0, 0.25, 4.0),
                    "pitch": clamp_float(data.get("pitch"), 0.0, -20.0, 20.0),
                },
            }

            request = urllib.request.Request(
                f"{GOOGLE_TTS_API}?key={api_key}",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))

            audio_content = result.get("audioContent")
            if not audio_content:
                raise ValueError("Google TTS response missing audioContent")

            audio = base64.b64decode(audio_content)
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
        print(f"[Google TTS] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"Google TTS server: http://{LISTEN_HOST}:{LISTEN_PORT}/tts")
    print(f"Voice: {DEFAULT_VOICE}, language: {DEFAULT_LANGUAGE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
