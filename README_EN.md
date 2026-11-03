# astrbot_plugin_volcengine_plan_voice

English | [简体中文](./README.md)

**Volcengine Ark Voice Suite (STT + TTS)** — a single AstrBot plugin that provides both STT and TTS providers:

- 🔤 **Speech-to-Text (STT)**: Doubao streaming ASR model 2.0 (`doubao-seed-asr-2.0`), WebSocket streaming
- 🔊 **Text-to-Speech (TTS)**: Doubao speech synthesis model 2.0 (`doubao-seed-tts-2.0`), with voice dropdown selection and voice–model matching correction

If you have subscribed to Volcengine Ark **Agent Plan (Personal)**, it works out of the box with the plan's dedicated API Key — no separate Volcengine speech synthesis/recognition service needed. One installation, one API Key; add the two providers separately in AstrBot.

## ✨ Features

- **TTS**
  - Voice dropdown selection (pick a voice directly in the WebUI config, no manual ID entry)
  - Voice–model matching correction (auto-validates the selected voice against the endpoint model)
  - Configurable endpoint URL (defaults to the Ark Agent Plan dedicated TTS endpoint)
  - Streaming reception (chunked response reading for full audio fidelity)
- **STT**
  - WebSocket streaming recognition, supports common formats such as wav/mp3
  - Configurable endpoint URL
  - Automatic ffmpeg transcoding (fixed args) for various media paths

## 📦 Installation

### Option 1: Plugin Market

Search for `火山方舟语音套件` in the AstrBot WebUI plugin market.

### Option 2: Manual Installation

```bash
# Inside AstrBot's data/plugins directory
git clone https://github.com/reboot1215/astrbot_plugin_volcengine_plan_voice.git
# Dependencies install automatically (including imageio-ffmpeg with a bundled ffmpeg binary — no manual ffmpeg install needed)
```

Alternatively, install from a zip/repo in the WebUI "Plugins" page.

## ⚙️ Configuration

1. In the AstrBot WebUI → "Service Providers", create a new provider:
   - **Speech-to-Text**: choose provider type `volcengine_plan_stt`
   - **Text-to-Speech**: choose provider type `volcengine_plan_tts`
2. Fill in the Volcengine Ark **Agent Plan dedicated API Key** (see the [official docs](https://ark.volcengine.com/region:cn-beijing/docs/agent-plan-personal-voice-model))
3. For TTS, pick a voice from the dropdown as needed; both providers ship with default endpoint URLs that generally need no changes.

## 📄 License

Released under the [AGPL-3.0](./LICENSE) license. Copyright (c) 2026 reboot1215

## 🙏 Attribution & Declarations

This plugin is original work. No source code from the following projects was copied; only their public APIs are used:

| Component | Nature | Usage |
|---|---|---|
| [AstrBot](https://github.com/AstrBotDevs/AstrBot) | Open-source framework (AGPL-3.0) | Built on AstrBot's Provider plugin API (`register_provider_adapter` / `TTSProvider` / `STTProvider`), runs on AstrBot 4.29+. No source code copied. |
| Volcengine Ark Agent Plan API | Commercial cloud service (Volcengine) | Calls Doubao voice models (`doubao-seed-tts-2.0` / `doubao-seed-asr-2.0`) via its dedicated HTTP/WebSocket endpoints. Public API calls only; no code or models included or redistributed. |

**AI Authorship Notice**: This plugin's code was written with AI (LLM) assistance. The repository owner [reboot1215](https://github.com/reboot1215) defined the requirements, led feature iterations, and handles debugging, testing, and maintenance, and is responsible for the code.
