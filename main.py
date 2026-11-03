import os
import sys

from astrbot.api import logger
from astrbot.api.star import Context, Star, register

# 关键点：Provider 必须在本模块「导入时」完成注册。
# register_provider_adapter 是装饰器副作用，写在类方法里会受插件启用状态 /
# 实例化时机影响，导致 WebUI「模型提供商」页面里看不到该提供商。
try:
    from .volcengine_plan_tts_provider import ProviderVolcenginePlanTTS  # noqa: F401
    from .volcengine_plan_stt_provider import ProviderVolcenginePlanSTT  # noqa: F401
except ImportError:  # 兼容以非包方式加载本模块的场景
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from volcengine_plan_tts_provider import ProviderVolcenginePlanTTS  # noqa: F401
    from volcengine_plan_stt_provider import ProviderVolcenginePlanSTT  # noqa: F401


@register(
    "astrbot_plugin_volcengine_plan_voice",
    "reboot1215",
    "通过火山方舟 Agent Plan 为 AstrBot 同时提供文字转语音（TTS，doubao-seed-tts-2.0）与语音转文字（STT，doubao-seed-asr-2.0），一次安装、一份 API Key 即可使用。",
    "1.0.1",
    "https://ark.volcengine.com/region:cn-beijing/docs/agent-plan-personal-voice-model",
)
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        logger.info(
            "[volcengine_plan_voice] 已注册语音套件 Provider adapters: "
            "TTS type=volcengine_plan_tts (text_to_speech) | "
            "STT type=volcengine_plan_stt (speech_to_text)"
        )
