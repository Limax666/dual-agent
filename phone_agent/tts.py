"""
文本到语音(TTS)模块

将文本响应转换为自然的语音输出，支持多种TTS服务
"""

import os
import io
import asyncio
import tempfile
from typing import Optional, Union, Dict, Any, List, Tuple
from enum import Enum, auto
from pathlib import Path
import time

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_TTS_AVAILABLE = True
except ImportError:
    OPENAI_TTS_AVAILABLE = False

try:
    import elevenlabs
    from elevenlabs.client import AsyncElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_TTS_AVAILABLE = True
except ImportError:
    AZURE_TTS_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from volcengine.tts_service import TtsService
    VOLC_TTS_AVAILABLE = True
except ImportError:
    VOLC_TTS_AVAILABLE = False


class TTSProvider(Enum):
    """TTS提供商枚举"""
    OPENAI = auto()         # OpenAI TTS
    ELEVENLABS = auto()     # ElevenLabs TTS
    AZURE = auto()          # Azure TTS
    SILICONFLOW = auto()    # SiliconFlow TTS
    DOUBAO = auto()         # Doubao TTS
    DUMMY = auto()          # 测试用，不生成实际语音

class TTSEngine:
    """TTS引擎，支持多种TTS服务"""

    def __init__(
        self,
        provider: TTSProvider = TTSProvider.DOUBAO,
        api_key: Optional[str] = None,
        voice: str = "zh_female_qingxin",
        language: str = "zh",
        model: Optional[str] = None,
        speech_rate: float = 1.0,
        output_format: str = "mp3",
        debug: bool = False
    ):
        self.debug = debug
        self.provider = provider
        self.api_key = api_key
        self.voice = voice
        self.language = language
        self.model = model
        self.output_format = output_format
        self.speech_rate = speech_rate
        
        if provider == TTSProvider.DOUBAO:
            if not self.api_key:
                if os.environ.get("VOLC_ACCESS_KEY_ID") and os.environ.get("VOLC_SECRET_ACCESS_KEY"):
                    self.access_key_id = os.environ["VOLC_ACCESS_KEY_ID"]
                    self.secret_access_key = os.environ["VOLC_SECRET_ACCESS_KEY"]
                else:
                    raise ValueError("未提供Doubao API密钥，请设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY环境变量")
            self.tts_service = TtsService(
                access_key_id=self.access_key_id,
                secret_access_key=self.secret_access_key
            )
        elif provider == TTSProvider.SILICONFLOW:
            self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY")
            if not self.api_key:
                raise ValueError("未提供Siliconflow API密钥，请设置SILICONFLOW_API_KEY环境变量")
            self.base_url = "https://api.siliconflow.cn/v1"
        # Other providers are omitted for brevity in this final step
        
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        if not text:
            return b""
        if self.provider == TTSProvider.DOUBAO:
            return await self._doubao_tts(text)
        elif self.provider == TTSProvider.SILICONFLOW:
            return await self._siliconflow_tts(text)
        # Other providers are omitted for brevity
        return b""

    async def _doubao_tts(self, text: str) -> bytes:
        """使用Doubao TTS"""
        try:
            resp = self.tts_service.synthesis(
                text=text,
                voice_type=self.voice,
                format=self.output_format,
                rate=int(self.speech_rate * 16000)
            )
            return resp.data
        except Exception as e:
            print(f"Doubao TTS错误: {str(e)}")
            return b""

    async def _siliconflow_tts(self, text: str) -> bytes:
        """使用Siliconflow TTS (fishaudio/fish-speech-1.5)"""
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 根据文档使用fish-speech-1.5模型
            data = {
                "model": "fishaudio/fish-speech-1.5",
                "input": text,
                "voice": "fishaudio/fish-speech-1.5:alex",  # 默认使用alex音色
                "response_format": self.output_format if self.output_format else "mp3",
                "speed": self.speech_rate
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/audio/speech",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        error_text = await response.text()
                        print(f"Siliconflow TTS错误: {response.status} - {error_text}")
                        return b""
        except Exception as e:
            print(f"Siliconflow TTS错误: {str(e)}")
            return b"" 