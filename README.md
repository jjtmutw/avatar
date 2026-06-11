# AI Avatar Realtime Assistant

這是一個即時 AI 虛擬助理網頁專案。網頁可透過 MQTT 收到文字後朗讀，並依語音狀態驅動虛擬人嘴型/臉形動畫；也支援瀏覽器線上 STT，將使用者語音辨識成文字後送到 MQTT。

## 功能

- 即時虛擬人畫面：`ai_avatar_realtime.html`
- MQTT 接收朗讀文字：預設訂閱 `jj/avatar/talk`
- STT 語音辨識：發布到 `jj/avatar/heard`
- ChatGPT 橋接程式：訂閱 `jj/avatar/heard`，回答後送到 `jj/avatar/talk`
- 可插拔外部 TTS：支援本機 TTS 轉接服務
- 預製嘴型與下半臉素材：`assets/visemes`、`assets/face_visemes`

## 快速啟動

1. 啟動網頁伺服器：

```bat
start_avatar_server.bat
```

2. 開啟：

```text
http://127.0.0.1:8765/ai_avatar_realtime.html?mqtt=1
```

3. 網頁左下角按「連線」連接 MQTT。

4. 若要使用語音辨識，按「傾聽」，並允許瀏覽器麥克風權限。

## ChatGPT 橋接

執行：

```bat
start_mqtt_chatgpt_bridge.bat
```

程式會要求貼上 `OPENAI_API_KEY`。啟動後：

- 訂閱：`jj/avatar/heard`
- 回覆：`jj/avatar/talk`

## 設定檔

- `avatar_mqtt_config.js`：MQTT broker、輸入/輸出 topic
- `avatar_tts_config.js`：外部 TTS 端點設定

## Google Cloud Text-to-Speech

1. 到 Google Cloud 啟用 Text-to-Speech API，並建立 API key。
2. 執行：

```bat
start_google_tts_server.bat
```

3. 貼上 `GOOGLE_TTS_API_KEY`。
4. 網頁可使用：

```text
ai_avatar_realtime.html?mqtt=1&tts=google&ttsEndpoint=http://127.0.0.1:5058/tts
```

如果網頁放在 GitHub Pages 或手機上使用，`ttsEndpoint` 必須是 HTTPS 網址，例如透過 Cloudflare Tunnel 或 ngrok 對外公開。

## 注意

請不要把 OpenAI API Key 寫進 HTML 或提交到 GitHub。啟動橋接程式時在本機輸入即可。
