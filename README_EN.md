# astrbot_plugin_volcengine_plan_voice

English | [简体中文](./README.md)

**Volcengine Ark Voice Suite (STT + TTS)** — a single AstrBot plugin providing both STT and TTS providers:

- 🔤 **Speech-to-Text (STT)**: Doubao streaming ASR 2.0 (`doubao-seed-asr-2.0`), supports common formats such as wav/mp3
- 🔊 **Text-to-Speech (TTS)**: Doubao TTS 2.0 (`doubao-seed-tts-2.0`), pick a voice from a dropdown in the WebUI with automatic voice–model correction

Works with a Volcengine Ark **Agent Plan (Personal)** subscription and its dedicated API Key — no separate Volcengine speech service needed. One install, one Key; add the two providers separately in AstrBot.

## ✨ Features

- **TTS**: voice dropdown selection with matching correction; configurable endpoint (defaults work out of the box)
- **STT**: WebSocket streaming recognition; ffmpeg-based transcoding handled automatically at install time (no manual ffmpeg install)

## 📦 Installation

- **Plugin market**: AstrBot WebUI → "Plugin Market", search `火山方舟语音套件` (if not listed yet, use the next option).
- **Manual**: install from the repo URL or a zip via WebUI → "Plugins"; or clone into AstrBot's `data/plugins` directory — dependencies install automatically.

```bash
git clone https://github.com/reboot1215/astrbot_plugin_volcengine_plan_voice.git
```

## ⚙️ Configuration

1. WebUI → "Providers", create a new provider:
   - **Speech-to-Text**: provider type `volcengine_plan_stt`
   - **Text-to-Speech**: provider type `volcengine_plan_tts`
2. Fill in your Agent Plan API Key (see the [official docs](https://ark.volcengine.com/region:cn-beijing/docs/agent-plan-personal-voice-model)).
3. Endpoint URLs ship with working defaults — normally leave them unchanged; pick a TTS voice from the dropdown as needed.

## ❓ FAQ

**Plugin install fails with `Failed to install dependencies ... error code 1`**

In most cases the pip index configured in AstrBot is currently unusable — unrelated to this plugin. Switch the pip index (`pypi_index_url`) to a working mirror per the [official AstrBot configuration docs](https://docs.astrbot.app/dev/astrbot-config.html), restart AstrBot, and install again.

## 📄 License

Released under the [AGPL-3.0](./LICENSE) license. Copyright (c) 2026 reboot1215

## 🙏 Credits & Declaration

This plugin is original work; no source code from the following projects was copied — only their public interfaces / plugin APIs are used:

| Referenced project | Nature | Usage |
|---|---|---|
| [AstrBot](https://github.com/AstrBotDevs/AstrBot) | Open-source framework (AGPL-3.0) | Built on AstrBot's provider plugin API (`register_provider_adapter` / `TTSProvider` / `STTProvider`), running on AstrBot 4.29+. No source copied. |
| Volcengine Ark Agent Plan API | Commercial cloud service (Volcengine) | Calls Doubao voice models (`doubao-seed-tts-2.0` / `doubao-seed-asr-2.0`) via its dedicated HTTP/WebSocket endpoints. Public interfaces only; none of its code is included or distributed. |

**AI disclosure**: the code was written with the assistance of AI (a large language model). The repo owner [reboot1215](https://github.com/reboot1215) defined the requirements, iterated, debugged, tested, and maintains it, and is responsible for the code.
