# 更新日志 / Changelog

遵循 [语义化版本](https://semver.org/lang/zh-CN/)。本项目从 `1.0.0` 起记版本号。

---

## v1.0.1 — 2026-11-03

兼容性与文档修正；功能、配置项、Provider 类型名均无变化，升级无需改配置。

- **依赖约束**：`websockets` 限制在 `<16`。无上限时可能被解析到 16+ 并覆盖宿主环境已有的 `websockets<16`（如飞书 SDK 依赖），导致相关功能异常。
- **文档**：补充安装失败（`error code 1`）说明——多为 AstrBot 配置的 pip 源不可用，按官方文档换源后重装即可。
- **市场信息**：`metadata.yaml` 补充框架版本要求（`astrbot_version`）与标签，便于市场搜索与过滤。

## v1.0.0 — 2026-11-03

首个版本：一个插件同时提供文字转语音与语音转文字，共用一份火山方舟 Agent Plan API Key。

---

# Changelog (English)

## v1.0.1 — 2026-11-03

Compatibility and documentation fixes only; features, config options, and provider type names are unchanged — no config edits needed when upgrading.

- **Dependency**: `websockets` is now capped below 16. Without the cap it could resolve to 16+ and shadow the host's existing `websockets<16` requirement (e.g. the Lark SDK), breaking related features.
- **Docs**: added a note for install failures (`error code 1`) — usually caused by the pip index configured in AstrBot; switch to a working mirror per the official docs and reinstall.
- **Market metadata**: added `astrbot_version` requirement and tags to `metadata.yaml` for better search and filtering.

## v1.0.0 — 2026-11-03

First release: one plugin provides both text-to-speech and speech-to-text, sharing a single Volcengine Ark Agent Plan API Key.
