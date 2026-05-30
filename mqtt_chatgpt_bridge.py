from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

import paho.mqtt.client as mqtt


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MQTT_URL = "mqtt://broker.emqx.io:1883"
DEFAULT_HEARD_TOPIC = "jj/avatar/heard"
DEFAULT_TALK_TOPIC = "jj/avatar/talk"


INSTRUCTIONS = """
你是小正助理，一位溫柔、自信、專業的 AI 虛擬助理。
使用繁體中文回答，口吻親切、簡潔、自然，適合被 TTS 朗讀。
避免太長的段落；一般回答控制在 1 到 4 句。
如果使用者只是打招呼，請自然回應並主動詢問需要什麼協助。
""".strip()


@dataclass
class MqttSettings:
    host: str
    port: int
    transport: str
    use_tls: bool
    heard_topic: str
    talk_topic: str


class ChatGptBridge:
    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.previous_response_id: str | None = None

    def ask(self, user_text: str) -> str:
        if not self.api_key:
            return "尚未設定 OpenAI API Key，請先設定 OPENAI_API_KEY。"

        body: dict[str, object] = {
            "model": self.model,
            "instructions": INSTRUCTIONS,
            "input": user_text,
            "max_output_tokens": 500,
        }
        if self.previous_response_id:
            body["previous_response_id"] = self.previous_response_id

        request = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"[OpenAI] HTTP {exc.code}: {detail}")
            return "我暫時無法連上 ChatGPT，請稍後再試。"
        except Exception as exc:
            print(f"[OpenAI] {type(exc).__name__}: {exc}")
            return "我剛剛連線時遇到問題，請稍後再試。"

        self.previous_response_id = data.get("id") or self.previous_response_id
        return extract_response_text(data) or "我收到你的訊息了，但剛剛沒有產生可朗讀的回覆。"


def extract_response_text(data: dict[str, object]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    parts: list[str] = []
    for item in data.get("output", []) if isinstance(data.get("output"), list) else []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(part.strip() for part in parts if part.strip()).strip()


def parse_mqtt_settings() -> MqttSettings:
    mqtt_url = os.environ.get("MQTT_URL", DEFAULT_MQTT_URL)
    parsed = urlparse(mqtt_url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname or "broker.emqx.io"
    port = parsed.port

    if scheme in {"ws", "wss"}:
        transport = "websockets"
        use_tls = scheme == "wss"
        port = port or (8084 if use_tls else 8083)
    else:
        transport = "tcp"
        use_tls = scheme == "mqtts"
        port = port or (8883 if use_tls else 1883)

    return MqttSettings(
        host=host,
        port=port,
        transport=transport,
        use_tls=use_tls,
        heard_topic=os.environ.get("MQTT_HEARD_TOPIC", DEFAULT_HEARD_TOPIC),
        talk_topic=os.environ.get("MQTT_TALK_TOPIC", DEFAULT_TALK_TOPIC),
    )


def main() -> None:
    settings = parse_mqtt_settings()
    bridge = ChatGptBridge()

    client = mqtt.Client(
        client_id=f"xiaozheng-chatgpt-bridge-{int(time.time())}",
        transport=settings.transport,
    )
    if settings.use_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    def publish_reply(text: str) -> None:
        client.publish(settings.talk_topic, text, qos=0, retain=False)
        print(f"[MQTT -> {settings.talk_topic}] {text}")

    def on_connect(_client: mqtt.Client, _userdata: object, _flags: dict, rc: int) -> None:
        if rc == 0:
            print(f"[MQTT] connected {settings.host}:{settings.port}")
            client.subscribe(settings.heard_topic)
            print(f"[MQTT] listening: {settings.heard_topic}")
            print(f"[MQTT] replying:  {settings.talk_topic}")
        else:
            print(f"[MQTT] connect failed rc={rc}")

    def on_message(_client: mqtt.Client, _userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            user_text = message.payload.decode("utf-8", errors="replace").strip()
            if not user_text:
                return
            print(f"[{settings.heard_topic}] {user_text}")
            reply = bridge.ask(user_text)
            publish_reply(reply)
        except Exception as exc:
            print(f"[Bridge] {type(exc).__name__}: {exc}")
            publish_reply("我剛剛處理訊息時遇到問題，請再說一次。")

    client.on_connect = on_connect
    client.on_message = on_message

    print("[Bridge] starting new ChatGPT conversation")
    print(f"[OpenAI] model: {bridge.model}")
    client.connect(settings.host, settings.port, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
