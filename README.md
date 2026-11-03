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

### 依赖装不上怎么办（WebUI 报 `error code 1`）

插件自身不带依赖，`websockets` 与 `imageio-ffmpeg` 由 AstrBot 安装时自动 `pip install`。如果 WebUI 报：

```
Failed to install dependencies for plugin astrbot_plugin_volcengine_plan_voice: Installation failed with error code 1
```

**绝大多数情况是 pip 索引（源）不可用，不是插件的问题。** 按顺序查：

**① 找到当前用的源。** 看 AstrBot 日志里的 `Looking in indexes: <地址>` 那一行。

**② 验证这个源到底有没有包。** 把 `<源>` 换成上一步的地址：

```bash
pip install --dry-run --ignore-installed 'imageio-ffmpeg>=0.5' -i <源>
```

出现 `Could not find a version that satisfies ... (from versions: none)` 就是源不可用或缺这个版本。
注意**响应快不等于可用**：实测有镜像 0.15 秒响应但缺目标版本，也有镜像直接返回 HTTP 567。

**③ 换源。** 改 AstrBot 的 `data/cmd_config.json`：

```json
"pypi_index_url": "https://pypi.tuna.tsinghua.edu.cn/simple",
"pip_install_arg": "--extra-index-url https://pypi.org/simple"
```

`--extra-index-url` 是兜底：镜像缺某个版本时还能回落到官方源。该文件带 UTF-8 BOM，用编辑器直接改，别用脚本覆盖成无 BOM，改完重启 AstrBot 再装一次。

**④ 或手动补装**，装到 AstrBot 的专用依赖目录（Docker 部署即容器内执行）：

```bash
python -m pip install -r requirements.txt \
  --target /AstrBot/data/site-packages \
  --upgrade --upgrade-strategy only-if-needed
```

`data/site-packages` 在数据卷上，容器重建不丢；装进系统 `site-packages` 只在镜像层，容器重建即失效。

> ⚠️ 手动装时别对 `websockets` 用无版本约束的 `--ignore-installed`：会被解析到 16+，顶掉宿主已有的 `websockets<16` 依赖（如 `lark-oapi` 要求 `<16`）。本插件的 `requirements.txt` 已锁 `<16`，照它装就不会撞。

## ⚙️ 配置

1. 在 AstrBot WebUI →「服务提供商」中新建提供商：
   - **语音转文字**：提供商类型选 `volcengine_plan_stt`
   - **文字转语音**：提供商类型选 `volcengine_plan_tts`
2. 填入火山方舟 **Agent Plan 专属 API Key**（获取方式见 [官方文档](https://ark.volcengine.com/region:cn-beijing/docs/agent-plan-personal-voice-model)）
3. TTS 可按需选择音色（下拉列表）；两个 Provider 的端点地址均已提供默认值，一般无需修改。

**更新日志**：[CHANGELOG.md](./CHANGELOG.md)

## 📄 License

本项目以 [AGPL-3.0](./LICENSE) 协议发布。Copyright (c) 2026 reboot1215

## 🙏 引用与声明

本插件为原创编写，未复制下列项目的任何源码，仅调用其公开接口/插件 API：

| 引用程序 | 性质 | 用途 |
|---|---|---|
| [AstrBot](https://github.com/AstrBotDevs/AstrBot) | 开源框架（AGPL-3.0） | 本插件基于 AstrBot 的 Provider 插件 API（`register_provider_adapter` / `TTSProvider` / `STTProvider`）开发，运行于 AstrBot 4.29+。未复制其源码。 |
| 火山方舟 Agent Plan API | 火山引擎商业云服务 | 通过其专属 HTTP/WebSocket 端点调用豆包语音大模型（`doubao-seed-tts-2.0` / `doubao-seed-asr-2.0`）。仅调用公开接口，不包含、不分发其任何代码。 |

**AI 编写声明**：本插件代码由 AI（大语言模型）辅助编写，由仓库所有者 [reboot1215](https://github.com/reboot1215) 完成需求定义、功能迭代、调试、测试与维护，并对代码负责。
