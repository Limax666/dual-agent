"""
自动语音识别(ASR)模块

使用Whisper API或本地Whisper模型实现实时语音转文本，支持流式输入以实现边听边想
"""

import asyncio
import io
import os
import time
import wave
import tempfile
import numpy as np
import torch
from typing import Dict, List, Optional, Union, Callable, Tuple, Any
from pathlib import Path
from enum import Enum, auto
from typing import Optional, Dict, Any
import os
import torch
from faster_whisper import WhisperModel
# from volcengine.asr_service import AsrService

# 尝试导入OpenAI库，如果不可用则使用faster-whisper本地模型
try:
    import openai
    OPENAI_API_AVAILABLE = True
except ImportError:
    OPENAI_API_AVAILABLE = False

# 尝试导入faster-whisper库，用于本地处理
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class ASRProvider(Enum):
    """ASR提供商枚举"""
    LOCAL = auto()
    OPENAI = auto()
    DOUBAO = auto()
    SILICONFLOW = auto()

class StreamingASR:
    """流式ASR处理，支持本地和API"""
    def __init__(
        self,
        provider: ASRProvider = ASRProvider.DOUBAO,
        model_size_or_name: str = "base",
        language: str = "zh",
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.language = language
        self.model_size_or_name = model_size_or_name

        if self.provider == ASRProvider.LOCAL:
            self.model = WhisperModel(model_size_or_name, device="cpu", compute_type="int8")
        elif self.provider == ASRProvider.OPENAI:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        elif self.provider == ASRProvider.DOUBAO:
            if not api_key:
                if os.environ.get("VOLC_ACCESS_KEY_ID") and os.environ.get("VOLC_SECRET_ACCESS_KEY"):
                    self.access_key_id = os.environ["VOLC_ACCESS_KEY_ID"]
                    self.secret_access_key = os.environ["VOLC_SECRET_ACCESS_KEY"]
                else:
                    raise ValueError("未提供Doubao API密钥，请设置VOLC_ACCESS_KEY_ID和VOLC_SECRET_ACCESS_KEY环境变量")
            self.asr_service = AsrService(
                access_key_id=self.access_key_id,
                secret_access_key=self.secret_access_key
            )
        elif self.provider == ASRProvider.SILICONFLOW:
            self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY")
            if not self.api_key:
                raise ValueError("未提供Siliconflow API密钥，请设置SILICONFLOW_API_KEY环境变量")
            self.base_url = "https://api.siliconflow.cn/v1"

    async def process_audio_segment(self, audio_tensor: torch.Tensor) -> Dict[str, Any]:
        """处理一个音频片段"""
        if self.provider == ASRProvider.LOCAL:
            # This part needs to be implemented based on how you want to handle local transcription
            return {"text": "Local transcription not implemented yet."}
        elif self.provider == ASRProvider.OPENAI:
             # This part needs to be implemented based on how you want to handle OpenAI transcription
            return {"text": "OpenAI transcription not implemented yet."}
        elif self.provider == ASRProvider.DOUBAO:
            return await self._transcribe_with_doubao(audio_tensor)
        elif self.provider == ASRProvider.SILICONFLOW:
            return await self._transcribe_with_siliconflow(audio_tensor)
        else:
            raise ValueError(f"Unsupported ASR provider: {self.provider}")

    async def _transcribe_with_doubao(self, audio_tensor: torch.Tensor) -> Dict[str, Any]:
        """使用Doubao ASR"""
        try:
            audio_bytes = audio_tensor.numpy().tobytes()
            resp = self.asr_service.recognize(
                audio_bytes,
                self.language,
                self.model_size_or_name
            )
            return {"text": resp.result}
        except Exception as e:
            print(f"Doubao ASR错误: {str(e)}")
            return {"text": ""}

    async def _transcribe_with_siliconflow(self, audio_tensor: torch.Tensor) -> Dict[str, Any]:
        """使用Siliconflow ASR (FunAudioLLM/SenseVoiceSmall)"""
        try:
            print(f"🔄 开始Siliconflow ASR转录，音频长度: {len(audio_tensor)} 样本")
            
            from openai import AsyncOpenAI
            import io
            import wave
            
            # 创建Siliconflow客户端
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
            
            print(f"✅ Siliconflow客户端已创建，API URL: {self.base_url}")
            
            # 将torch tensor转换为wav格式的字节流
            audio_numpy = audio_tensor.numpy()
            audio_bytes = io.BytesIO()
            
            print(f"🎵 音频数据范围: [{audio_numpy.min():.3f}, {audio_numpy.max():.3f}]")
            
            with wave.open(audio_bytes, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(16000)  # 16kHz采样率
                wav_file.writeframes((audio_numpy * 32767).astype(np.int16).tobytes())
            
            audio_bytes.seek(0)
            audio_data = audio_bytes.read()
            print(f"📁 WAV文件大小: {len(audio_data)} 字节")
            
            # 使用FunAudioLLM/SenseVoiceSmall模型进行转录
            print("🚀 正在调用Siliconflow ASR API...")
            transcription = await client.audio.transcriptions.create(
                model="FunAudioLLM/SenseVoiceSmall",
                file=("audio.wav", audio_data, "audio/wav"),
                language=self.language,  # 指定语言可以提高准确率
                prompt="这是一段对话录音"  # 提供上下文
            )
            
            result_text = transcription.text.strip()
            print(f"✅ ASR转录成功: '{result_text}'")
            
            return {"text": result_text}
            
        except Exception as e:
            print(f"❌ Siliconflow ASR错误: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return {"text": "", "error": str(e)}
