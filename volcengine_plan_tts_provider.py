import uuid
import os
import json
import base64

import aiohttp

from astrbot.api import logger
from astrbot.core.provider.provider import TTSProvider
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.register import (
    provider_cls_map,
    register_provider_adapter,
)
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.core.utils.datetime_utils import generate_timestamp_id

# 方舟 Agent Plan 专属 HTTP 单向流式 TTS 接口（默认值，可在提供商配置的 url 字段里改）
DEFAULT_PLAN_TTS_URL = "https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional"
PLAN_TTS_URL = DEFAULT_PLAN_TTS_URL  # 兼容旧引用

# 默认音色（可在提供商配置的 speaker 字段里改）
DEFAULT_SPEAKER = "zh_female_vv_uranus_bigtts"

# 经方舟 Agent Plan 账号（doubao-seed-tts-2.0）实测可用的音色清单。
# 注入到 AstrBot 的 provider 配置 schema 后，WebUI 配置表单里的 speaker
# 字段会渲染成下拉列表（见 _inject_speaker_options）。
SPEAKER_OPTIONS = [
    "zh_female_vv_uranus_bigtts",              # 温柔女声（默认）
    "zh_female_xiaohe_uranus_bigtts",          # 活泼女声
    "zh_female_gaolengyujie_uranus_bigtts",    # 高冷御姐
    "zh_female_kefunvsheng_uranus_bigtts",     # 客服女声
    "zh_male_yangguangqingnian_uranus_bigtts",  # 阳光青年
    "zh_male_shaonianzixin_uranus_bigtts",     # 少年自信
]

PROVIDER_TYPE_NAME = "volcengine_plan_tts"
PROVIDER_DESC = "方舟 Agent Plan 语音合成 (doubao-seed-tts-2.0)"
PROVIDER_DISPLAY_NAME = "方舟 Agent Plan 语音合成"

# provider_type / provider 必须显式写进模板：AstrBot 4.29.x 的 WebUI 用
# template.provider_type 与当前标签页（chat_completion / speech_to_text /
# text_to_speech / embedding / rerank）匹配来决定是否展示该提供商。
DEFAULT_CONFIG_TMPL = {
    "provider_type": "text_to_speech",
    "provider": "volcengine",
    "api_key": "方舟 Agent Plan 专属 API Key",
    "url": DEFAULT_PLAN_TTS_URL,
    "speaker": DEFAULT_SPEAKER,
    "format": "mp3",
    "sample_rate": 24000,
    "speed_ratio": 0,
}


class ProviderVolcenginePlanTTS(TTSProvider):
    """调用火山方舟 Agent Plan 语音合成 (doubao-seed-tts-2.0)。

    与 AstrBot 原生「火山引擎 TTS」不同，本 Provider 走方舟 Agent Plan 专属端点
    (/api/v3/plan/tts/...)，使用方舟「专属 API Key」鉴权，而非火山引擎控制台的
    AppID/Token。
    """

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)
        self.api_key = provider_config.get("api_key", "")
        # 音色可换：留空或未配置时回落到默认音色
        self.speaker = (
            str(provider_config.get("speaker") or "").strip() or DEFAULT_SPEAKER
        )
        self.fmt = str(provider_config.get("format") or "mp3").strip() or "mp3"
        try:
            self.sample_rate = int(provider_config.get("sample_rate", 24000))
        except (TypeError, ValueError):
            self.sample_rate = 24000
        try:
            self.speed_ratio = int(provider_config.get("speed_ratio", 0))
        except (TypeError, ValueError):
            self.speed_ratio = 0
        # 链接可换：留空或未配置时回落到官方默认端点
        self.url = self._resolve_url(provider_config.get("url"))
        logger.info("[volcengine_plan_tts] 提供商初始化: %s", self._usage_desc())

    @staticmethod
    def _resolve_url(raw_url) -> str:
        url = str(raw_url or "").strip()
        if not url:
            return DEFAULT_PLAN_TTS_URL
        if not url.lower().startswith(("http://", "https://")):
            logger.warning(
                "[volcengine_plan_tts] 配置的 url 不是 http(s) 地址，已改用默认端点：%s",
                DEFAULT_PLAN_TTS_URL,
            )
            return DEFAULT_PLAN_TTS_URL
        return url

    def _usage_desc(self) -> str:
        return f"url={self.url} speaker={self.speaker}"

    async def get_audio(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise ValueError("TTS 输入文本为空")
        if not self.api_key or self.api_key == "方舟 Agent Plan 专属 API Key":
            raise ValueError("未配置方舟 Agent Plan 专属 API Key (api_key)")

        temp_dir = get_astrbot_temp_path()
        os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, f"ark_plan_tts_{generate_timestamp_id()}.{self.fmt}")

        headers = {
            "X-Api-Key": self.api_key,
            "X-Api-Resource-Id": "seed-tts-2.0",
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Control-Require-Usage-Tokens-Return": "*",
            "Content-Type": "application/json",
        }
        payload = {
            "user": {"uid": "astrbot"},
            "req_params": {
                "text": text,
                "speaker": self.speaker,
                "audio_params": {
                    "format": self.fmt,
                    "sample_rate": self.sample_rate,
                    "speech_rate": self.speed_ratio,
                },
            },
        }

        audio = bytearray()
        # 保持默认 TLS 证书校验（请求头携带 API Key，必须防止中间人窃取）
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(self.url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"方舟 TTS 请求失败 HTTP {resp.status}: {body[:500]}"
                        f"（{self._usage_desc()}）"
                    )
                # HTTP Chunked 流式返回多个 JSON 对象：逐块累积全文再按行解析，data 为 base64 音频
                chunks = bytearray()
                async for chunk in resp.content.iter_chunked(65536):
                    chunks += chunk
                body_text = bytes(chunks).decode("utf-8", errors="ignore")
                for line in body_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    code = obj.get("code")
                    if code == 0 and obj.get("data"):
                        audio += base64.b64decode(obj["data"])
                    elif code not in (0, None, 20000000):
                        raise RuntimeError(
                            f"方舟 TTS 错误 code={code} message={obj.get('message')}"
                            f"（{self._usage_desc()}）"
                        )

        if not audio:
            raise RuntimeError(
                f"方舟 TTS 未返回音频数据 (请检查文本/音色/Key)：{self._usage_desc()}"
            )

        with open(path, "wb") as f:
            f.write(bytes(audio))
        return path


def _inject_speaker_options() -> None:
    """把实测可用的音色清单注入 AstrBot 的 provider 配置 schema。

    AstrBot 的 WebUI「服务提供商」表单由 CONFIG_METADATA_2 的
    provider_group.metadata.provider.items 元数据驱动：字段元数据里带
    `options` 时，前端 ConfigItemRenderer 会将该字段渲染成 v-select 下拉框。
    因此在插件导入时把 `speaker` 的 options 写进去，speaker 就变成可选的
    音色下拉列表（幂等：重复调用 / 插件重载不会覆盖已有 options）。

    注意：这里不能带 description/hint/labels 等字段——服务端
    get_provider_schema() 会把这些属性替换成 i18n key，而插件注入的 key
    没有对应翻译，前端会原样显示 key 字符串。只有 type/options 会被原样保留。
    """
    try:
        from astrbot.core.config.default import CONFIG_METADATA_2
    except Exception as e:  # pragma: no cover - 结构异常时退化为纯文本框，不阻塞注册
        logger.warning("[volcengine_plan_tts] 无法读取 CONFIG_METADATA_2，跳过音色下拉注入: %s", e)
        return
    try:
        items = CONFIG_METADATA_2["provider_group"]["metadata"]["provider"]["items"]
        item = items.setdefault("speaker", {"type": "string"})
        item.setdefault("options", SPEAKER_OPTIONS)
        logger.info(
            "[volcengine_plan_tts] 已注入 speaker 音色下拉选项（%d 个）：%s",
            len(SPEAKER_OPTIONS),
            ", ".join(SPEAKER_OPTIONS),
        )
    except Exception as e:  # pragma: no cover
        logger.warning("[volcengine_plan_tts] 注入 speaker 下拉选项失败，退化为文本框: %s", e)


def register() -> None:
    """幂等注册本 Provider。

    AstrBot 的插件卸载/重载不会清理 `provider_cls_map`（只清 sys.modules、
    star_registry、handlers、平台适配器），若直接使用 `@register_provider_adapter`
    装饰器，重载时会因「适配器已注册」抛出 ValueError 导致插件加载失败。
    因此这里先查表：不存在才注册，已存在则就地刷新元数据（同时可让升级后的
    默认配置模板立即生效）。
    """
    tmpl = dict(DEFAULT_CONFIG_TMPL)
    tmpl.setdefault("type", PROVIDER_TYPE_NAME)
    tmpl.setdefault("enable", False)
    tmpl.setdefault("id", PROVIDER_TYPE_NAME)

    # 先注入 speaker 下拉选项（幂等），再刷新/注册元数据
    _inject_speaker_options()

    existing = provider_cls_map.get(PROVIDER_TYPE_NAME)
    if existing is not None:
        existing.desc = PROVIDER_DESC
        existing.provider_type = ProviderType.TEXT_TO_SPEECH
        existing.cls_type = ProviderVolcenginePlanTTS
        existing.default_config_tmpl = tmpl
        existing.provider_display_name = PROVIDER_DISPLAY_NAME
        logger.info(
            "[volcengine_plan_tts] Provider 已存在，已刷新注册元数据（热重载场景）"
        )
        return

    register_provider_adapter(
        PROVIDER_TYPE_NAME,
        PROVIDER_DESC,
        provider_type=ProviderType.TEXT_TO_SPEECH,
        default_config_tmpl=tmpl,
        provider_display_name=PROVIDER_DISPLAY_NAME,
    )(ProviderVolcenginePlanTTS)
    logger.info("[volcengine_plan_tts] Provider 注册成功")


register()
