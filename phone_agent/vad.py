"""
语音活动检测(VAD)模块

使用Silero VAD进行高精度的语音活动检测，识别用户何时开始说话和停止说话
"""

import io
import os
import torch
import torchaudio
import asyncio
import numpy as np
from typing import Callable, Optional, List, Tuple, Union
import sys

class SileroVAD:
    """使用Silero VAD模型的语音活动检测器"""

    def __init__(
        self,
        threshold: float = 0.5,
        sampling_rate: int = 16000,
        device: str = "cpu",
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500,
        window_size_samples: int = 512,
        noise_threshold: float = 0.02  # 新增：噪声阈值
    ):
        """
        初始化Silero VAD
        
        参数:
            threshold: 语音检测阈值，越高越严格
            sampling_rate: 音频采样率，默认16kHz
            device: 运行模型的设备，默认为CPU
            min_speech_duration_ms: 最小语音持续时长(毫秒)
            min_silence_duration_ms: 最小静默持续时长(毫秒)
            window_size_samples: 处理窗口大小
            noise_threshold: 音频噪声阈值，低于此值的音频被认为是噪声
        """
        self.threshold = threshold
        self.sampling_rate = sampling_rate
        self.device = device
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.window_size_samples = window_size_samples
        self.noise_threshold = noise_threshold  # 新增
        
        # 加载Silero VAD模型
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False
        )
        
        self.model = self.model.to(device)
        
        # 获取模型的辅助函数
        (
            self.get_speech_timestamps,
            self.save_audio,
            self.read_audio,
            self.VADIterator,
            self.collect_chunks
        ) = utils
        
        self.reset_state()
        
        print("Silero VAD initialized")
    
    def reset_state(self) -> None:
        """重置VAD状态"""
        self.model.reset_states()
    
    def is_speech(self, audio_chunk: torch.Tensor) -> bool:
        """
        检查音频块是否包含语音
        
        参数:
            audio_chunk: 音频数据块
            
        返回:
            是否检测到语音
        """
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.squeeze()
        
        if len(audio_chunk) < self.window_size_samples:
            return False
        
        # 首先检查音频能量，过滤低能量噪声
        audio_energy = torch.mean(torch.abs(audio_chunk)).item()
        if audio_energy < self.noise_threshold:
            return False
        
        # 运行VAD模型
        speech_prob = self.model(audio_chunk, self.sampling_rate).item()
        
        # 对于低能量音频，提高阈值要求
        effective_threshold = self.threshold
        if audio_energy < self.noise_threshold * 3:  # 能量较低时
            effective_threshold = min(0.8, self.threshold + 0.2)  # 提高阈值
        
        return speech_prob >= effective_threshold
    
    def get_timestamps(self, audio: torch.Tensor) -> List[dict]:
        """
        获取音频中的语音时间戳
        
        参数:
            audio: 音频数据
            
        返回:
            语音片段的时间戳列表
        """
        if audio.ndim > 1:
            audio = audio.squeeze()
        
        # 获取语音时间戳
        speech_timestamps = self.get_speech_timestamps(
            audio,
            self.model,
            threshold=self.threshold,
            sampling_rate=self.sampling_rate,
            min_speech_duration_ms=self.min_speech_duration_ms,
        )
        
        return speech_timestamps
        
    def process_audio_file(self, file_path: str) -> Tuple[List[dict], torch.Tensor]:
        """
        处理音频文件，提取语音时间戳和分段
        
        参数:
            file_path: 音频文件路径
            
        返回:
            (语音时间戳, 原始音频数据)
        """
        # 读取音频文件
        audio = self.read_audio(file_path, self.sampling_rate)
        
        # 获取语音时间戳
        speech_timestamps = self.get_timestamps(audio)
        
        return speech_timestamps, audio
    
    def extract_speech_segments(self, audio: torch.Tensor, timestamps: List[dict]) -> List[torch.Tensor]:
        """
        根据时间戳从音频中提取语音片段
        
        参数:
            audio: 音频数据
            timestamps: 语音时间戳
            
        返回:
            语音片段列表
        """
        speech_segments = []
        
        for ts in timestamps:
            start_sample = int(ts['start'])
            end_sample = int(ts['end'])
            segment = audio[start_sample:end_sample]
            speech_segments.append(segment)
        
        return speech_segments
    
    async def stream_from_microphone(
        self,
        audio_queue: asyncio.Queue,
        device_index: int = 0,
        stop_event: Optional[asyncio.Event] = None
    ) -> None:
        """
        从麦克风流式获取音频并进行VAD处理 (异步回调版本)
        
        参数:
            audio_queue: 用于放置音频块的队列
            device_index: 麦克风设备索引
            stop_event: 用于停止捕获的事件
        """
        try:
            import sounddevice as sd
        except ImportError:
            raise ImportError("请安装sounddevice库: pip install sounddevice")

        loop = asyncio.get_event_loop()

        def audio_callback(indata, frames, time, status):
            """sounddevice在单独的线程中调用此回调"""
            if status:
                print(status, file=sys.stderr)
            # 使用call_soon_threadsafe将数据从线程安全地传递到asyncio事件循环
            loop.call_soon_threadsafe(audio_queue.put_nowait, torch.tensor(indata.copy().flatten(), dtype=torch.float32))

        # 使用InputStream以非阻塞方式捕获音频
        stream = sd.InputStream(
            samplerate=self.sampling_rate,
            blocksize=self.window_size_samples,
            device=device_index,
            channels=1,
            dtype='float32',
            callback=audio_callback
        )
        
        # 使用stream上下文管理器来确保流的正确启动和停止
        stream.start()
        self.log("麦克风流已启动")

        # 保持流运行直到stop_event被设置
        if stop_event:
            await stop_event.wait()

        # 停止并关闭流
        stream.stop()
        stream.close()
        self.log("麦克风流已停止")
        
        # 发送结束信号
        loop.call_soon_threadsafe(audio_queue.put_nowait, None)
        
    def log(self, message: str):
        """记录日志"""
        print(f"[VAD] {message}") 