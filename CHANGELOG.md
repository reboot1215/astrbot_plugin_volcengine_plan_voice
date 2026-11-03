# 更新日志 / Changelog

遵循 [语义化版本](https://semver.org/lang/zh-CN/)。本项目从 `1.0.0` 起记版本号。

---

## v1.0.1 — 2026-11-03

**兼容性与文档修正，功能、配置项、Provider 类型名均无变化，升级无需改配置。**

### 1. `requirements.txt`：`websockets` 加上限 `<16`

**升级原因**：AstrBot 把插件依赖装进 `data/site-packages`，该目录的优先级高于系统 `site-packages`。实测在没有版本约束时，`websockets` 被解析到 **17.4**，顶掉宿主原有的 `websockets<16` 依赖——`lark-oapi 1.7.5` 明确要求 `<16`，重启后相关 SDK 直接不可用。锁上限后不会再撞。

附带踩到的一个细节：降级后 `importlib.metadata.version()` 仍返回 17.4，因为目录里残留了旧的 `dist-info`。所以这类问题要看「代码版本 + 元数据版本」两处，不能只看 import 是否成功。

### 2. README 补充「依赖装不上怎么办」

**升级原因**：在 WebUI 安装本插件时实际出现过

```
Failed to install dependencies for plugin astrbot_plugin_volcengine_plan_voice: Installation failed with error code 1
```

排查结论：**根因是 AstrBot 配置的 pip 索引不可用，与插件代码无关**。定位过程：

1. 插件依赖只有 `websockets`（环境已装 15.0.1）与 `imageio-ffmpeg`，焦点落在后者；
2. 容器内手动 `pip install imageio-ffmpeg` 成功（68 MB / 2 秒）→ 包与网络均排除；
3. 读 AstrBot 源码，发现索引取自 `cmd_config.json` 的 `pypi_index_url`；
4. 配置里是某云厂商镜像，容器内访问返回 **HTTP 567**；强制走该源复现：`from versions: none` → 退出码 1。

这个配置插件改不了，但用户会误以为是插件坏了。因此把「找源 → 验源 → 换源 → 手动补装」四步写进 README，并记录两条实测教训：

- **响应快 ≠ 可用**：实测有镜像 0.15 秒响应却缺目标版本；
- `--extra-index-url https://pypi.org/simple` 作为兜底，镜像缺版本时仍可回落到官方源。

### 3. `metadata.yaml` 补齐市场字段

**升级原因**：原文件缺 `astrbot_version`、`tags`、`social_link`，市场无法按框架版本过滤，搜索命中率也低。本次补：

```yaml
astrbot_version: ">=4.29.0"
tags: [tts, stt, 语音转文字, 文字转语音, 火山方舟, 豆包, volcengine]
social_link: https://github.com/reboot1215
```

同时 `version` 写法由 `v1.0.0` 规范为 `1.0.1`；`main.py` 中 `register` 的版本号同步为 `1.0.1`。

---

## v1.0.0 — 2026-11-03

首个发布：TTS + STT 双 Provider 合一，一份 Agent Plan API Key 同时可用。

---

# Changelog (English)

## v1.0.1 — 2026-11-03

**Compatibility and documentation fixes only. Features, config options, and provider type names are unchanged — no config edits needed when upgrading.**

### 1. `requirements.txt`: `websockets` capped below 16

**Why**: AstrBot installs plugin dependencies into `data/site-packages`, which takes priority over system site-packages. Measured without a version cap, `websockets` resolved to **17.4** and shadowed existing `websockets<16` requirements on the host — `lark-oapi 1.7.5` requires `<16`, and the affected SDKs broke after a restart. The cap prevents this.

A related gotcha: after downgrading, `importlib.metadata.version()` still reported 17.4 because a stale `dist-info` directory was left behind. Always check both the imported code version and the metadata version.

### 2. README: added "Dependencies failed to install"

**Why**: installing via the WebUI produced

```
Failed to install dependencies for plugin astrbot_plugin_volcengine_plan_voice: Installation failed with error code 1
```

Root cause: **the pip index configured in AstrBot was unusable — unrelated to the plugin code.** How it was traced:

1. The plugin needs only `websockets` (already 15.0.1 in the environment) and `imageio-ffmpeg`, narrowing the focus to the latter;
2. A manual `pip install imageio-ffmpeg` inside the container succeeded (68 MB / 2 s) — ruling out both the package and network;
3. Reading AstrBot's source showed the index comes from `pypi_index_url` in `cmd_config.json`;
4. The configured mirror returned **HTTP 567** from inside the container; forcing that index reproduced `from versions: none` → exit code 1.

The plugin cannot change that setting, but users would otherwise assume the plugin is broken. The README now documents the four steps — find the index, verify it, switch it, install manually — plus two measured lessons:

- **Fast response ≠ usable**: one mirror answered in 0.15 s yet lacked the target version;
- `--extra-index-url https://pypi.org/simple` as a fallback so pip can still reach the official index.

### 3. `metadata.yaml`: missing market fields added

**Why**: `astrbot_version`, `tags`, and `social_link` were absent, preventing version-based filtering in the market and hurting search visibility. Also normalized `version` from `v1.0.0` to `1.0.1`, and synced the version in `main.py`'s `register` call to `1.0.1`.

## v1.0.0 — 2026-11-03

First release: TTS and STT providers in one plugin, sharing a single Agent Plan API Key.
