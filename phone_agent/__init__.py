"""
Phone Agent包

提供基于语音交互的Agent，实现边听边想、快慢思考结合的能力
"""

# 导出主要类和组件
from .vad import SileroVAD
from .asr import StreamingASR
from .thinking_engine import (
    MixedThinkingEngine, ThinkingMode, ThinkingStatus, LLMProvider
)
from .tts import TTSEngine, TTSProvider
from .phone_agent import PhoneAgent, PhoneAgentState

__all__ = [
    'SileroVAD',
    'StreamingASR',
    'MixedThinkingEngine',
    'ThinkingMode',
    'ThinkingStatus',
    'LLMProvider',
    'TTSEngine',
    'TTSProvider',
    'PhoneAgent',
    'PhoneAgentState',
] 