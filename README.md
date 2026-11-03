# astrbot_plugin_volcengine_plan_voice

[English](./README_EN.md) | 简体中文

**火山方舟语音套件（语音转文字 + 文字转语音）** —— 一个 AstrBot 插件同时提供 STT 与 TTS 两个 Provider：

- 🔤 **语音转文字（STT）**：豆包流式语音识别大模型 2.0（`doubao-seed-asr-2.0`），WebSocket 流式调用
- 🔊 **文字转语音（TTS）**：豆包语音合成大模型 2.0（`doubao-seed-tts-2.0`），支持音色下拉选择与匹配矫正

已订阅火山方舟 **Agent Plan（个人版）** 即可使用专属 API Key 配置即用，无需另开火山引擎语音合成/识别服务。一次安装、一份 Key，在 AstrBot 服务提供商中分别添加即可使用。

## ✨ 特性

- **TTS**
  - 音色下拉选择（WebUI 配置项内直接挑选音色，无需手填）
  - 音色与模型匹配矫正（自动校验所选音色与端点模型的兼容性）
  - 端点地址可配置（默认方舟 Agent Plan 专属 TTS 端点）
  - 流式接收（逐块读取 chunked 响应，完整还原音频）
- **STT**
  - WebSocket 流式识别，支持 wav/mp3 等常见格式
  - 端点地址可配置
  - 自动用 ffmpeg 固定参数转码兼容多种媒体路径

## 📦 安装

### 方式一：插件市场

在 AstrBot WebUI 的「插件市场」中搜索 `火山方舟语音套件` 安装。

### 方式二：手动安装

```bash
# 在 AstrBot 的 data/plugins 目录下
git clone https://github.com/reboot1215/astrbot_plugin_volcengine_plan_voice.git
# 依赖会自动安装（含 imageio-ffmpeg，内置 ffmpeg 二进制，无需手动装 ffmpeg）
```

或在 WebUI「插件」页面选择从 zip/仓库安装。

## ⚙️ 配置

1. 在 AstrBot WebUI →「服务提供商」中新建提供商：
   - **语音转文字**：提供商类型选 `volcengine_plan_stt`
   - **文字转语音**：提供商类型选 `volcengine_plan_tts`
2. 填入火山方舟 **Agent Plan 专属 API Key**（获取方式见 [官方文档](https://ark.volcengine.com/region:cn-beijing/docs/agent-plan-personal-voice-model)）
3. TTS 可按需选择音色（下拉列表）；两个 Provider 的端点地址均已提供默认值，一般无需修改。

## 📄 License

本项目以 [AGPL-3.0](./LICENSE) 协议发布。Copyright (c) 2026 reboot1215

## 🙏 引用与声明

本插件为原创编写，未复制下列项目的任何源码，仅调用其公开接口/插件 API：

| 引用程序 | 性质 | 用途 |
|---|---|---|
| [AstrBot](https://github.com/AstrBotDevs/AstrBot) | 开源框架（AGPL-3.0） | 本插件基于 AstrBot 的 Provider 插件 API（`register_provider_adapter` / `TTSProvider` / `STTProvider`）开发，运行于 AstrBot 4.29+。未复制其源码。 |
| 火山方舟 Agent Plan API | 火山引擎商业云服务 | 通过其专属 HTTP/WebSocket 端点调用豆包语音大模型（`doubao-seed-tts-2.0` / `doubao-seed-asr-2.0`）。仅调用公开接口，不包含、不分发其任何代码。 |

**AI 编写声明**：本插件代码由 AI（大语言模型）辅助编写，由仓库所有者 [reboot1215](https://github.com/reboot1215) 完成需求定义、功能迭代、调试、测试与维护，并对代码负责。
