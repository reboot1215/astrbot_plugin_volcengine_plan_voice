"""火山方舟 Agent Plan 语音识别（ASR）Provider for AstrBot。

接口：wss://openspeech.bytedance.com/api/v3/plan/sauc/bigmodel_nostream
鉴权：X-Api-Key（方舟 Agent Plan 专属 API Key）
资源：volc.seedasr.sauc.duration（doubao-seed-asr-2.0）
协议：WebSocket 二进制协议（4 字节头 + [sequence] + payload_size + gzip(payload)）
"""

import asyncio
import gzip
import json
import os
import shutil
import struct
import uuid
import wave

try:
    import websockets
except ImportError:  # 缺依赖时不阻断插件加载，否则 WebUI 里连配置项都不会出现
    websockets = None

from astrbot.api import logger
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import STTProvider
from astrbot.core.provider.register import (
    provider_cls_map,
    register_provider_adapter,
)
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.core.utils.media_utils import MediaResolver

# ---- 二进制协议常量 ----
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ERROR_RESPONSE = 0b1111

NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_WITH_SEQUENCE = 0b0011

NO_SERIALIZATION = 0b0000
JSON_SERIALIZATION = 0b0001
NO_COMPRESSION = 0b0000
GZIP_COMPRESSION = 0b0001

# 默认端点（可在提供商配置的 url 字段里改）
DEFAULT_PLAN_ASR_URL = "wss://openspeech.bytedance.com/api/v3/plan/sauc/bigmodel_nostream"
PLAN_ASR_URL = DEFAULT_PLAN_ASR_URL  # 兼容旧引用
DEFAULT_RESOURCE_ID = "volc.seedasr.sauc.duration"

# ---- ffmpeg 探测（环境变量 > 系统 PATH > imageio-ffmpeg 自带二进制）----
_FFMPEG_PATH: str | None = None
_FFMPEG_REPORTED = False


def _resolve_ffmpeg(report: bool = False) -> str | None:
    """按优先级解析可用的 ffmpeg 可执行文件路径，结果缓存。

    优先级：
    1. 环境变量 ASTRBOT_FFMPEG_PATH（显式指定）
    2. 系统 PATH 中的 ffmpeg（shutil.which）
    3. pip 包 imageio-ffmpeg 自带的静态二进制（requirements.txt 已含，随插件自动安装）
    """
    global _FFMPEG_PATH
    if _FFMPEG_PATH is not None:
        return _FFMPEG_PATH

    env_path = os.environ.get("ASTRBOT_FFMPEG_PATH", "").strip()
    if env_path and os.path.isfile(env_path):
        _FFMPEG_PATH = env_path
        if report:
            logger.info("[volcengine_plan_stt] ffmpeg(环境变量 ASTRBOT_FFMPEG_PATH): %s", env_path)
        return _FFMPEG_PATH

    which_path = shutil.which("ffmpeg")
    if which_path:
        _FFMPEG_PATH = which_path
        if report:
            logger.info("[volcengine_plan_stt] ffmpeg(系统 PATH): %s", which_path)
        return _FFMPEG_PATH

    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        _FFMPEG_PATH = bundled
        if report:
            logger.info("[volcengine_plan_stt] ffmpeg(imageio-ffmpeg 自带二进制): %s", bundled)
        return _FFMPEG_PATH
    except Exception:
        if report and not _FFMPEG_REPORTED:
            logger.warning(
                "[volcengine_plan_stt] ffmpeg 未检测到（环境变量 / 系统 PATH / imageio-ffmpeg 均不可用）。"
                "仅 16kHz/单声道/16bit 音频可正常识别。"
                "修复方式任选其一：① pip install imageio-ffmpeg；② 系统安装 ffmpeg 并加入 PATH；"
                "③ 设置环境变量 ASTRBOT_FFMPEG_PATH。"
            )
            _FFMPEG_REPORTED = True
        return None


def _generate_header(
    message_type: int,
    serialization: int = JSON_SERIALIZATION,
    compression: int = GZIP_COMPRESSION,
    flags: int = NO_SEQUENCE,
) -> bytes:
    header = bytearray()
    header.append((PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE)
    header.append((message_type << 4) | flags)
    header.append((serialization << 4) | compression)
    header.append(0x00)
    return bytes(header)


def _build_full_client_request(config: dict) -> bytes:
    header = _generate_header(
        CLIENT_FULL_REQUEST, JSON_SERIALIZATION, GZIP_COMPRESSION, NO_SEQUENCE
    )
    payload = gzip.compress(json.dumps(config, ensure_ascii=False).encode("utf-8"))
    return header + struct.pack(">I", len(payload)) + payload


def _build_audio_request(audio: bytes) -> bytes:
    header = _generate_header(
        CLIENT_AUDIO_ONLY_REQUEST, NO_SERIALIZATION, GZIP_COMPRESSION, NO_SEQUENCE
    )
    payload = gzip.compress(audio)
    return header + struct.pack(">I", len(payload)) + payload


def _build_last_audio_request() -> bytes:
    header = _generate_header(
        CLIENT_AUDIO_ONLY_REQUEST, NO_SERIALIZATION, GZIP_COMPRESSION, NEG_SEQUENCE
    )
    payload = gzip.compress(b"")
    return header + struct.pack(">I", len(payload)) + payload


def _parse_response(message: bytes) -> dict:
    """解析服务端二进制响应，返回 {error, payload, sequence}。"""
    if len(message) < 4:
        return {"error": "message too short", "payload": None, "sequence": None}

    header = message[:4]
    header_size = (header[0] & 0x0F) * 4
    message_type = header[1] >> 4
    flags = header[1] & 0x0F
    serialization = header[2] >> 4
    compression = header[2] & 0x0F
    offset = header_size

    sequence = None
    if flags in (POS_SEQUENCE, NEG_WITH_SEQUENCE) and len(message) >= offset + 4:
        sequence = struct.unpack(">i", message[offset : offset + 4])[0]
        offset += 4

    if message_type == SERVER_ERROR_RESPONSE:
        if len(message) < offset + 8:
            return {"error": "malformed error response", "payload": None, "sequence": sequence}
        error_code = struct.unpack(">I", message[offset : offset + 4])[0]
        offset += 4
        error_size = struct.unpack(">I", message[offset : offset + 4])[0]
        offset += 4
        error_msg = message[offset : offset + error_size].decode("utf-8", errors="ignore")
        return {"error": f"{error_code}: {error_msg}", "payload": None, "sequence": sequence}

    if len(message) < offset + 4:
        return {"error": "malformed response", "payload": None, "sequence": sequence}

    payload_size = struct.unpack(">I", message[offset : offset + 4])[0]
    offset += 4
    payload_bytes = message[offset : offset + payload_size]

    if compression == GZIP_COMPRESSION and payload_bytes:
        try:
            payload_bytes = gzip.decompress(payload_bytes)
        except OSError:
            pass

    payload = None
    if serialization == JSON_SERIALIZATION and payload_bytes:
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            payload = None

    return {"error": None, "payload": payload, "sequence": sequence}


def _ws_connect(url: str, headers: dict, **kwargs):
    """兼容 websockets 新旧版本的 header 参数名。"""
    if websockets is None:
        raise RuntimeError(
            "缺少依赖 websockets，无法连接方舟语音识别服务。"
            "请在插件目录执行 pip install websockets（或重启 AstrBot 让其按 requirements.txt 自动安装）。"
        )
    try:
        return websockets.connect(url, additional_headers=headers, **kwargs)
    except TypeError:
        return websockets.connect(url, extra_headers=headers, **kwargs)


PROVIDER_TYPE_NAME = "volcengine_plan_stt"
PROVIDER_DESC = "方舟 Agent Plan 语音识别 (doubao-seed-asr-2.0)"
PROVIDER_DISPLAY_NAME = "方舟 Agent Plan 语音识别"

# provider_type / provider 必须写进模板：WebUI 用 template.provider_type 判断
# 该提供商归属哪个标签页（speech_to_text / text_to_speech / ...）。
DEFAULT_CONFIG_TMPL = {
    "provider_type": "speech_to_text",
    "provider": "volcengine",
    "api_key": "方舟 Agent Plan 专属 API Key",
    "url": DEFAULT_PLAN_ASR_URL,
    "resource_id": DEFAULT_RESOURCE_ID,
    "timeout": 60,
}


class ProviderVolcenginePlanSTT(STTProvider):
    """调用火山方舟 Agent Plan 语音识别（doubao-seed-asr-2.0）。

    与 AstrBot 内置 STT 不同：走方舟 Agent Plan 专属端点
    (/api/v3/plan/sauc/...)，使用方舟「专属 API Key」鉴权。
    """

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        # 兼容两种字段命名：providers 用 api_key，provider_sources 用 key
        self.api_key = provider_config.get("api_key") or provider_config.get("key") or ""
        self.resource_id = provider_config.get("resource_id", DEFAULT_RESOURCE_ID)
        try:
            self.timeout = int(provider_config.get("timeout", 60))
        except (TypeError, ValueError):
            self.timeout = 60
        # 链接可换：留空或未配置时回落到官方默认端点
        self.url = self._resolve_url(provider_config.get("url"))
        logger.info("[volcengine_plan_stt] 提供商初始化: url=%s", self.url)
        # 启动时探测 ffmpeg 并在日志中报告（环境变量 > 系统 PATH > imageio-ffmpeg 自带二进制）
        ffmpeg = _resolve_ffmpeg(report=True)
        if ffmpeg:
            logger.info("[volcengine_plan_stt] ffmpeg 就绪: %s", ffmpeg)
        else:
            logger.warning(
                "[volcengine_plan_stt] 未检测到 ffmpeg：仅当输入音频为 16kHz/单声道/16bit 时可正常识别。"
                "修复方式任选其一：① pip install imageio-ffmpeg；② 系统安装 ffmpeg 并加入 PATH；"
                "③ 设置环境变量 ASTRBOT_FFMPEG_PATH 指向 ffmpeg 可执行文件。"
            )

    @staticmethod
    def _resolve_url(raw_url) -> str:
        url = str(raw_url or "").strip()
        if not url:
            return DEFAULT_PLAN_ASR_URL
        if not url.lower().startswith(("ws://", "wss://")):
            logger.warning(
                "[volcengine_plan_stt] 配置的 url 不是 ws(s):// 地址，已改用默认端点：%s",
                DEFAULT_PLAN_ASR_URL,
            )
            return DEFAULT_PLAN_ASR_URL
        return url

    async def _ensure_16k_mono_wav(self, path: str) -> str:
        """方舟 ASR 仅支持 16kHz / 16bit / 单声道，必要时用 ffmpeg 重采样。"""
        try:
            with wave.open(path, "rb") as w:
                rate, channels, sampwidth = (
                    w.getframerate(),
                    w.getnchannels(),
                    w.getsampwidth(),
                )
        except Exception:
            return path

        if rate == 16000 and channels == 1 and sampwidth == 2:
            return path

        ffmpeg = _resolve_ffmpeg()
        if not ffmpeg:
            logger.warning(
                "音频为 %sHz/%sch/%sbit，非 ASR 要求的 16kHz/单声道/16bit，"
                "且未检测到 ffmpeg，识别可能失败。",
                rate,
                channels,
                sampwidth * 8,
            )
            return path

        temp_dir = get_astrbot_temp_path()
        os.makedirs(temp_dir, exist_ok=True)
        out_path = os.path.join(temp_dir, f"asr_{uuid.uuid4().hex}_16k.wav")
        proc = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-y",
            "-i",
            path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return out_path if os.path.exists(out_path) else path

    async def _transcribe(self, audio: bytes) -> str:
        headers = {
            "X-Api-Key": self.api_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Api-Sequence": "-1",
        }
        config = {
            "user": {"uid": "astrbot"},
            "audio": {
                "format": "wav",
                "codec": "raw",
                "rate": 16000,
                "bits": 16,
                "channel": 1,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
                "enable_nonstream": False,
            },
        }

        final_text = ""
        async with _ws_connect(
            self.url,
            headers,
            max_size=16 * 1024 * 1024,
            open_timeout=15,
            close_timeout=5,
        ) as ws:
            await ws.send(_build_full_client_request(config))

            chunk_size = 6400  # 200ms @16kHz/16bit/mono
            for i in range(0, len(audio), chunk_size):
                await ws.send(_build_audio_request(audio[i : i + chunk_size]))
                await asyncio.sleep(0.01)
            await ws.send(_build_last_audio_request())

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                except asyncio.TimeoutError:
                    logger.warning("方舟 ASR 接收超时（%ss），返回已收到的文本", self.timeout)
                    break
                except websockets.ConnectionClosed:
                    break

                result = _parse_response(message)
                if result["error"]:
                    raise RuntimeError(f"方舟 ASR 错误: {result['error']}")

                payload = result["payload"]
                if payload:
                    text = (payload.get("result") or {}).get("text") or ""
                    if text:
                        final_text = text

                seq = result.get("sequence")
                if seq is not None and seq < 0:
                    break

        return final_text

    async def get_text(self, audio_url: str) -> str:
        if not self.api_key or self.api_key == "方舟 Agent Plan 专属 API Key":
            raise ValueError("未配置方舟 Agent Plan 专属 API Key (api_key)")

        async with MediaResolver(
            audio_url,
            media_type="audio",
            default_suffix=".wav",
        ).as_path(target_format="wav") as audio_path:
            # 兼容不同 AstrBot 版本：as_path() 在 4.29.x 返回 ResolvedMediaFile
            # 对象（含 .path 属性），旧版本返回纯字符串路径。直接把对象 repr
            # 当路径传给 open() 会报 [Errno 2]（如健康检查 stt_health_check.wav）。
            if hasattr(audio_path, "path"):
                audio_path = audio_path.path
            wav_path = await self._ensure_16k_mono_wav(str(audio_path))
            with open(wav_path, "rb") as f:
                audio_bytes = f.read()

        if not audio_bytes:
            raise ValueError("音频内容为空")

        text = await self._transcribe(audio_bytes)
        if not text:
            raise RuntimeError("方舟 ASR 未返回识别文本（请检查音频质量/格式）")
        return text


def register() -> None:
    """幂等注册本 Provider。

    AstrBot 的插件卸载/重载不会清理 `provider_cls_map`，若直接使用
    `@register_provider_adapter` 装饰器，重载时会因「适配器已注册」抛出 ValueError
    导致插件加载失败（表现为适配器报错、插件无法启用）。这里先查表：不存在才注册，
    已存在则就地刷新元数据。
    """
    tmpl = dict(DEFAULT_CONFIG_TMPL)
    tmpl.setdefault("type", PROVIDER_TYPE_NAME)
    tmpl.setdefault("enable", False)
    tmpl.setdefault("id", PROVIDER_TYPE_NAME)

    # WebUI 的提供商配置表单 = 该模板的字段清单，因此这里要能自证 api_key 已写入模板
    logger.info(
        "[volcengine_plan_stt] 注册模板字段: %s（provider_type=%s）",
        ", ".join(sorted(tmpl.keys())),
        tmpl.get("provider_type"),
    )

    existing = provider_cls_map.get(PROVIDER_TYPE_NAME)
    if existing is not None:
        existing.desc = PROVIDER_DESC
        existing.provider_type = ProviderType.SPEECH_TO_TEXT
        existing.cls_type = ProviderVolcenginePlanSTT
        existing.default_config_tmpl = tmpl
        existing.provider_display_name = PROVIDER_DISPLAY_NAME
        logger.info(
            "[volcengine_plan_stt] Provider 已存在，已刷新注册元数据（热重载场景）"
        )
        return

    register_provider_adapter(
        PROVIDER_TYPE_NAME,
        PROVIDER_DESC,
        provider_type=ProviderType.SPEECH_TO_TEXT,
        default_config_tmpl=tmpl,
        provider_display_name=PROVIDER_DISPLAY_NAME,
    )(ProviderVolcenginePlanSTT)
    logger.info("[volcengine_plan_stt] Provider 注册成功")


register()
