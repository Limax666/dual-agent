"""
Phone Agent主模块

集成VAD、ASR、混合思考引擎和TTS组件，实现完整的语音交互功能
"""

import asyncio
import time
import uuid
import json
import torch
import numpy as np
from typing import Dict, List, Optional, Union, Any, Callable, Tuple
from enum import Enum, auto
from pathlib import Path
import os
from dataclasses import dataclass, field
from typing import Optional
import asyncio
import os
import time
import uuid
from enum import Enum, auto
import torch
from dual_agent.phone_agent.vad import SileroVAD
from dual_agent.phone_agent.asr import StreamingASR, ASRProvider
from dual_agent.phone_agent.thinking_engine import MixedThinkingEngine, LLMProvider
from dual_agent.phone_agent.tts import TTSEngine, TTSProvider
from dual_agent.common.messaging import message_queue, A2AMessage, MessageType, MessageSource

class PhoneAgentState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    THINKING = auto()
    SPEAKING = auto()
    ERROR = auto()

@dataclass
class PhoneAgentConfig:
    vad_threshold: float = 0.5
    vad_sampling_rate: int = 16000
    asr_provider: ASRProvider = ASRProvider.SILICONFLOW
    asr_api_key: Optional[str] = None
    asr_model_name: str = "FunAudioLLM/SenseVoiceSmall"
    language: str = "zh"
    fast_think_provider: LLMProvider = LLMProvider.SILICONFLOW
    deep_think_provider: LLMProvider = LLMProvider.SILICONFLOW
    fast_think_model_name: Optional[str] = "doubao-seed-1-6-flash-250615"
    deep_think_model_name: Optional[str] = "doubao-seed-1-6-thinking-250615"
    tts_provider: TTSProvider = TTSProvider.SILICONFLOW
    tts_voice: str = "fishaudio/fish-speech-1.5:alex"
    device_index: int = 0
    disable_thinking_while_listening: bool = False
    debug: bool = False

class PhoneAgent:
    """电话Agent，负责处理语音交互"""

    def __init__(self, config: PhoneAgentConfig):
        self.config = config
        self.debug = config.debug
        self.state = PhoneAgentState.IDLE
        self.session_id = str(uuid.uuid4())
        self.logs = []
        
        self.log(f"Initializing VAD with threshold: {config.vad_threshold}")
        self.vad = SileroVAD(threshold=config.vad_threshold, sampling_rate=config.vad_sampling_rate)
        
        self.log(f"Initializing ASR. Provider: {config.asr_provider.name}, Model: {config.asr_model_name}")
        self.asr = StreamingASR(provider=config.asr_provider, model_size_or_name=config.asr_model_name, language=config.language)
        
        self.log(f"Initializing Thinking Engine. Fast: {self.config.fast_think_model_name}, Deep: {self.config.deep_think_model_name}")
        self.thinking_engine = MixedThinkingEngine(
            fast_model_name=config.fast_think_model_name, 
            deep_model_name=config.deep_think_model_name,
            provider=LLMProvider.DOUBAO,  # 强制使用DOUBAO provider进行思考
            debug=config.debug
        )
        
        self.log(f"Initializing TTS with provider: {config.tts_provider.name}")
        self.tts = TTSEngine(provider=config.tts_provider, voice=config.tts_voice, debug=config.debug)
        
        self.message_queue = message_queue
        
        # 添加控制属性
        self.stop_event = asyncio.Event()
        self.is_running = False
        
        # 存储当前页面信息，用于Agent间通信
        self.current_page_info = None
        self.current_form_fields = []  # 存储当前页面的实际表单字段

    def log(self, message: str):
        if self.debug:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}][PhoneAgent] {message}")
        self.logs.append((time.time(), message))

    async def start(self):
        """启动Phone Agent"""
        print("🎤 Phone Agent正在启动...")
        self.log("Starting Phone Agent...")
        self.is_running = True
        self.stop_event.clear()
        
        try:
            # 首先打招呼
            print("👋 Phone Agent开始问候...")
            await self._speak_greeting()
            
            # 开始音频处理循环
            print("🔊 Phone Agent开始监听语音输入...")
            await self._audio_processing_loop()
                
        except Exception as e:
            self.log(f"Error in Phone Agent: {e}")
            print(f"❌ Phone Agent出错: {e}")
        finally:
            self.is_running = False
            self.log("Phone Agent stopped")
            print("🛑 Phone Agent已停止")

    async def _speak_greeting(self):
        """播放开场问候语"""
        # 等待一下，让Computer Agent有时间发送页面信息
        await asyncio.sleep(1)
        
        # 检查是否收到了页面信息
        await self._check_computer_messages()
        
        # 根据是否有页面信息生成不同的问候语
        if self.current_page_info:
            page_title = self.current_page_info['title']
            forms_count = self.current_page_info['forms_count']
            if forms_count > 0:
                greeting = f"您好！我是您的AI助手。我看到Computer Agent已经为您打开了'{page_title}'页面，该页面有{forms_count}个表单可以填写。请告诉我您需要填写什么信息，比如姓名、电话、邮箱等。"
            else:
                greeting = f"您好！我是您的AI助手。我看到Computer Agent已经为您打开了'{page_title}'页面。请告诉我您需要做什么操作。"
        else:
            # 默认问候语（当没有页面信息时）
            greeting = "您好！我是您的AI助手，我可以帮助您填写网页表单。请告诉我您需要填写什么信息，或者说'开始填表'来开始。"
        
        self.log(f"Greeting: {greeting}")
        print(f"🤖 AI说: {greeting}")
        
        try:
            # 生成语音
            audio_data = await self.tts.text_to_speech(greeting)
            if audio_data:
                self.log("Playing greeting audio...")
                await self._play_audio(audio_data)
            else:
                self.log("Failed to generate greeting audio, using text display")
                # 即使TTS失败，也要等一下模拟说话时间
                await asyncio.sleep(3)
        except Exception as e:
            self.log(f"Error generating greeting: {e}")
            # 回退到等待时间
            await asyncio.sleep(3)

    async def _audio_processing_loop(self):
        """真实音频处理主循环 - 使用麦克风输入和扬声器输出"""
        self.log("Starting real-time audio processing loop...")
        
        try:
            import pyaudio
            import numpy as np
            import threading
            import queue
            
            # 使用真实的音频处理
            await self._real_audio_processing()
            
        except ImportError:
            self.log("PyAudio not available, using text-based simulation")
            print("⚠️ PyAudio未安装，使用文本模式模拟语音交互")
            print("💡 请在控制台输入文本来模拟语音输入")
            
            # 使用文本输入模拟语音交互
            await self._text_based_simulation()
    
    async def _real_audio_processing(self):
        """真实的音频处理逻辑"""
        import pyaudio
        import numpy as np
        import queue
        
        # 音频配置 - 调整为VAD模型要求的块大小
        rate = self.config.vad_sampling_rate  # 16000
        vad_chunk_size = 512  # Silero VAD要求16kHz时使用512样本
        audio_chunk_size = 1024  # PyAudio读取块大小
        format = pyaudio.paInt16
        channels = 1
        
        # 创建音频队列
        audio_queue = queue.Queue()
        
        # 初始化PyAudio
        p = pyaudio.PyAudio()
        
        # 显示音频设备信息
        self.log("=== 音频设备信息 ===")
        try:
            default_input = p.get_default_input_device_info()
            self.log(f"默认输入设备: {default_input['name']} (设备{default_input['index']})")
            print(f"🎤 使用麦克风: {default_input['name']}")
        except Exception as e:
            self.log(f"无法获取默认输入设备: {e}")
        
        # 显示可用输入设备
        self.log("可用输入设备:")
        for i in range(p.get_device_count()):
            try:
                device_info = p.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    self.log(f"  设备{i}: {device_info['name']} (通道: {device_info['maxInputChannels']})")
            except:
                pass
        
        # 打开麦克风输入流
        try:
            self.log(f"正在打开麦克风 (设备索引: {self.config.device_index})")
            stream_in = p.open(
                format=format,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=self.config.device_index,
                frames_per_buffer=audio_chunk_size
            )
            self.log(f"✅ 麦克风已成功打开 (设备 {self.config.device_index})")
            print(f"✅ 麦克风已就绪，VAD阈值: {self.config.vad_threshold}")
        except Exception as e:
            self.log(f"❌ 打开麦克风失败: {e}")
            print(f"❌ 麦克风打开失败: {e}")
            p.terminate()
            return
        
        # 语音状态跟踪
        is_speaking = False
        speech_frames = []
        silence_count = 0
        min_speech_frames = int(250 * rate / 1000 / vad_chunk_size)  # 250ms
        min_silence_frames = int(500 * rate / 1000 / vad_chunk_size)  # 500ms
        
        # 音频缓冲区用于累积到VAD所需的块大小
        audio_buffer = np.array([], dtype=np.float32)
        
        self.log(f"VAD参数: 块大小={vad_chunk_size}, 最小语音帧数={min_speech_frames}, 最小静默帧数={min_silence_frames}")
        print("🎤 请开始说话，系统正在监听...")
        
        frame_count = 0
        message_check_interval = int(rate // vad_chunk_size * 2)  # 每2秒检查一次消息
        
        try:
            while not self.stop_event.is_set():
                try:
                    # 读取音频数据
                    data = stream_in.read(audio_chunk_size, exception_on_overflow=False)
                    audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # 添加到缓冲区
                    audio_buffer = np.concatenate([audio_buffer, audio_np])
                    
                    # 当缓冲区有足够数据时，处理VAD检测
                    while len(audio_buffer) >= vad_chunk_size:
                        # 取出VAD所需的块大小
                        vad_chunk = audio_buffer[:vad_chunk_size]
                        audio_buffer = audio_buffer[vad_chunk_size:]
                        
                        # 计算音量用于调试
                        volume = np.max(np.abs(vad_chunk))
                        frame_count += 1
                        
                        # 每2秒显示一次音量信息和检查Computer Agent消息
                        if frame_count % message_check_interval == 0:
                            volume_bar = "█" * min(int(volume * 20), 20)
                            print(f"🎵 音量: {volume_bar:<20} ({volume:.3f})")
                            
                            # 检查Computer Agent消息
                            try:
                                await self._check_computer_messages()
                            except Exception as msg_error:
                                self.log(f"检查Computer Agent消息时出错: {msg_error}")
                        
                        # 转换为torch tensor用于VAD
                        audio_tensor = torch.from_numpy(vad_chunk)
                        
                        # VAD检测 - 确保使用正确的输入格式
                        try:
                            speech_prob = self.vad.model(audio_tensor, rate).item()
                        except Exception as vad_error:
                            self.log(f"VAD检测错误: {vad_error}")
                            # 使用简单的音量检测作为备选
                            speech_prob = 1.0 if volume > 0.01 else 0.0
                        
                        # 调试: 当检测到较高语音概率时显示
                        if speech_prob > self.config.vad_threshold * 0.5:  # 显示接近阈值的检测
                            self.log(f"🎯 语音概率: {speech_prob:.3f} (阈值: {self.config.vad_threshold})")
                        
                        if speech_prob > self.config.vad_threshold:
                            # 检测到语音
                            if not is_speaking:
                                self.log("🎤 开始检测到语音，正在录音...")
                                print(f"🔴 检测到语音 (概率: {speech_prob:.3f})，开始录音...")
                                is_speaking = True
                                speech_frames = []
                            
                            speech_frames.append(audio_tensor)
                            silence_count = 0
                        else:
                            # 静默
                            if is_speaking:
                                silence_count += 1
                                speech_frames.append(audio_tensor)
                                
                                # 如果静默时间足够长，结束录音
                                if silence_count >= min_silence_frames and len(speech_frames) >= min_speech_frames:
                                    duration_ms = len(speech_frames) * vad_chunk_size / rate * 1000
                                    self.log(f"🔇 语音结束，处理录音 (时长: {duration_ms:.1f}ms)...")
                                    print(f"🔇 语音结束，处理录音 (时长: {duration_ms:.1f}ms)")
                                    
                                    # 合并音频帧
                                    full_audio = torch.cat(speech_frames)
                                    
                                    # 同步处理语音，确保处理完成
                                    print("🚀 开始处理用户语音任务...")
                                    try:
                                        await self._process_user_speech(full_audio)
                                    except Exception as process_error:
                                        print(f"❌ 语音处理任务失败: {process_error}")
                                        import traceback
                                        traceback.print_exc()
                                    
                                    # 重置状态
                                    is_speaking = False
                                    speech_frames = []
                                    silence_count = 0
                
                except Exception as e:
                    self.log(f"音频处理循环错误: {e}")
                    await asyncio.sleep(0.1)
                
        finally:
            # 清理资源
            stream_in.stop_stream()
            stream_in.close()
            p.terminate()
            self.log("音频处理已停止")
    
    async def _text_based_simulation(self):
        """文本模拟语音交互"""
        import sys
        
        while not self.stop_event.is_set():
            try:
                print("\n🎤 请输入文本 (输入'退出'结束): ", end="", flush=True)
                
                # 使用异步方式获取用户输入
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, sys.stdin.readline)
                user_input = user_input.strip()
                
                if user_input.lower() in ['退出', 'quit', 'exit']:
                    print("👋 再见！")
                    break
                
                if user_input:
                    print(f"👤 用户说: {user_input}")
                    
                    # 模拟语音处理
                    await self._process_text_input(user_input)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.log(f"Error in text simulation: {e}")
                await asyncio.sleep(1)
    
    async def _process_text_input(self, text):
        """处理文本输入（模拟语音处理）"""
        try:
            self.log(f"👤 User said: {text}")
            
            # 添加用户消息到对话历史
            self.thinking_engine.add_message("user", text)
            
            # 如果有当前页面信息，添加到上下文中（与语音处理保持一致）
            if self.current_page_info:
                page_context = f"[页面上下文] 当前Computer Agent已打开页面: '{self.current_page_info['title']}' ({self.current_page_info['url']})，该页面有{self.current_page_info['forms_count']}个表单。"
                self.thinking_engine.add_message("system", page_context)
                print(f"🔄 已添加页面上下文到思考引擎")
            
            # 使用思考引擎生成回应
            fast_response, deep_response = await self.thinking_engine.think(
                message_queue=self.message_queue, 
                user_text=text
            )
            
            # 语音输出优先使用快速思考（简短），深度思考用于理解分析
            response_text = fast_response.strip() if fast_response.strip() else deep_response.strip()
            # 深度思考用于更好地理解用户意图和表单信息
            analysis_text = deep_response.strip() if deep_response.strip() else fast_response.strip()
            
            if response_text.strip():
                self.log(f"🤖 AI response: {response_text}")
                print(f"🤖 AI说: {response_text}")
                
                # 播放AI回应（模拟）
                await self._speak_response(response_text)
                
                # 添加AI回应到对话历史
                self.thinking_engine.add_message("assistant", analysis_text)
                
                # 检查是否还需要发送深度分析的表单信息（避免重复发送）
                await self._analyze_and_send_additional_computer_instructions(text, analysis_text)
            else:
                print("🤖 AI说: 我没有理解您的意思，请再说一遍。")
            
        except Exception as e:
            self.log(f"Error processing text input: {e}")
            print(f"❌ 处理输入时出错: {e}")

    async def _process_user_speech(self, audio_tensor):
        """处理用户语音输入"""
        try:
            print("=" * 50)
            print("🧠 开始处理用户语音...")
            print(f"🔍 音频tensor形状: {audio_tensor.shape}")
            self.log("🧠 Processing speech...")
            
            # 使用ASR转录语音
            print("🔄 正在进行语音识别...")
            self.log("Starting ASR transcription...")
            transcription_result = await self.asr.process_audio_segment(audio_tensor)
            
            print(f"🔍 ASR结果: {transcription_result}")
            self.log(f"ASR result: {transcription_result}")
            
            user_text = transcription_result.get("text", "").strip()
            
            if user_text:
                print(f"👤 用户说: {user_text}")
                self.log(f"👤 User said: {user_text}")
                
                # 添加用户消息到对话历史
                self.thinking_engine.add_message("user", user_text)
                
                # 如果有当前页面信息，添加到上下文中
                if self.current_page_info:
                    page_context = f"[页面上下文] 当前Computer Agent已打开页面: '{self.current_page_info['title']}' ({self.current_page_info['url']})，该页面有{self.current_page_info['forms_count']}个表单。"
                    self.thinking_engine.add_message("system", page_context)
                    print(f"🔄 已添加页面上下文到思考引擎")
                
                # 使用思考引擎生成回应
                print("🤔 正在思考回应...")
                self.log("Starting thinking process...")
                fast_response, deep_response = await self.thinking_engine.think(
                    message_queue=self.message_queue, 
                    user_text=user_text
                )
                
                print(f"💭 快速思考: {fast_response[:100]}...")
                print(f"🧠 深度思考: {deep_response[:100]}...")
                
                # 语音输出优先使用快速思考（简短），深度思考用于理解分析
                speech_text = fast_response.strip() if fast_response.strip() else deep_response.strip()
                # 深度思考用于更好地理解用户意图和表单信息
                analysis_text = deep_response.strip() if deep_response.strip() else fast_response.strip()
                
                if speech_text:
                    print(f"🎙️ 语音输出: {speech_text}")
                    print(f"📋 分析理解: {analysis_text[:100]}...")
                    self.log(f"🤖 Speech output: {speech_text}")
                    self.log(f"🤖 Analysis: {analysis_text}")
                    
                    # 播放简短的AI回应
                    print("🔊 正在生成语音回应...")
                    await self._speak_response(speech_text)
                    
                    # 添加AI回应到对话历史（使用分析文本）
                    self.thinking_engine.add_message("assistant", analysis_text)
                    
                    # 检查是否还需要发送深度分析的表单信息（只有在快思考阶段没有提取到数据时才发送）
                    await self._analyze_and_send_additional_computer_instructions(user_text, analysis_text)
                    
                    print("✅ 语音处理完成，继续监听...")
                    print("=" * 50)
                else:
                    print("⚠️ AI没有生成有效回应")
                    self.log("AI generated empty response")
            else:
                print("❌ 语音识别未获得文本结果")
                self.log("No text detected from speech")
                
                # 检查ASR是否真的失败了
                if isinstance(transcription_result, dict) and "error" in transcription_result:
                    print(f"ASR错误: {transcription_result['error']}")
                    self.log(f"ASR error: {transcription_result['error']}")
            
        except Exception as e:
            print(f"❌ 处理语音时出错: {e}")
            self.log(f"Error processing user speech: {e}")
            import traceback
            traceback.print_exc()
            print("=" * 50)

    async def _speak_response(self, text):
        """播放AI回应语音"""
        try:
            self.log("🔊 Generating speech...")
            
            # 生成语音
            audio_data = await self.tts.text_to_speech(text)
            if audio_data:
                self.log("🔊 Playing response...")
                await self._play_audio(audio_data)
            else:
                self.log("Failed to generate speech audio, using text display")
                # 即使TTS失败，也要等一下模拟说话时间
                estimated_duration = len(text) * 0.1  # 假设每个字符0.1秒
                await asyncio.sleep(max(1.0, estimated_duration))
        except Exception as e:
            self.log(f"Error generating speech: {e}")
            # 回退到等待时间
            await asyncio.sleep(2.0)

    async def _play_audio(self, audio_data):
        """播放音频数据"""
        try:
            import pygame
            import io
            
            # 初始化pygame mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            
            # 创建音频对象并播放
            audio_file = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
        except ImportError:
            self.log("pygame not available, using simulated playback")
            # 模拟播放时间
            estimated_duration = len(audio_data) / 16000  # 粗略估计
            await asyncio.sleep(max(1.0, estimated_duration))
        except Exception as e:
            self.log(f"Error playing audio: {e}")
            # 回退到模拟播放
            await asyncio.sleep(2.0)

    async def _analyze_and_send_additional_computer_instructions(self, user_text, ai_response):
        """分析对话并发送额外的深度分析指令给Computer Agent（避免与快思考阶段重复）"""
        try:
            import uuid
            print("🔍 检查是否需要发送额外的深度分析信息...")
            
            # 扩展的表单相关关键词
            form_keywords = ["填写", "表单", "输入", "名字", "姓名", "邮箱", "email", "电话", "手机", "地址", "提交", "填表", "开始填"]
            has_form_keyword = any(keyword in user_text for keyword in form_keywords)
            
            # 使用更智能的信息提取
            extracted_data = self._extract_form_data_from_text(user_text)
            
            # 只有在快思考阶段没有提取到数据，但现在通过深度分析发现了额外信息时才发送
            if (has_form_keyword or extracted_data) and ai_response and len(ai_response) > 100:
                # 深度分析可能包含了快思考阶段没有的信息
                print(f"📝 深度分析阶段发现额外表单信息")
                
                # 发送深度分析消息给Computer Agent
                from dual_agent.common.messaging import A2AMessage, MessageType, MessageSource
                
                message = A2AMessage(
                    source=MessageSource.PHONE,
                    type=MessageType.ACTION,
                    task_id=str(uuid.uuid4()),
                    content={
                        "action": "analyze_form",
                        "user_input": user_text,
                        "ai_deep_analysis": ai_response,  # 使用深度分析的结果
                        "extracted_data": extracted_data,
                        "immediate": False,  # 标记为非立即执行
                        "from_deep_thinking": True  # 标记来自深度思考
                    }
                )
                
                await self.message_queue.send_to_computer(message)
                print(f"📤 已发送深度分析指令给Computer Agent")
                self.log(f"📤 Sent deep analysis instruction to Computer Agent: {user_text}")
            else:
                print("ℹ️ 无需发送额外的深度分析信息")
                
        except Exception as e:
            self.log(f"Error sending additional computer instructions: {e}")
            print(f"❌ 发送额外Computer Agent指令时出错: {e}")
    
    def _extract_form_data_from_text(self, text):
        """从文本中智能提取表单数据，基于实际页面的表单字段"""
        import re
        
        extracted = {}
        text_lower = text.lower()
        
        print(f"🔍 基于实际表单字段提取数据，当前字段数: {len(self.current_form_fields)}")
        
        if not self.current_form_fields:
            print("⚠️ 没有表单字段信息，使用基础提取模式")
            # 如果没有表单字段信息，使用基础提取模式
            return self._basic_form_data_extraction(text)
        
        # 基于实际表单字段进行提取
        for field in self.current_form_fields:
            field_id = field.get("id", "").lower()
            field_label = field.get("label", "").lower()
            field_placeholder = field.get("placeholder", "").lower()
            field_type = field.get("type", "").lower()
            
            # 构建该字段的关键词列表
            keywords = []
            if field_label:
                keywords.append(field_label)
            if field_placeholder:
                keywords.append(field_placeholder)
            if field_id:
                keywords.append(field_id)
            
            print(f"🎯 检查字段 {field_id}: {keywords}")
            
            # 根据字段类型和关键词匹配用户输入
            field_value = self._extract_field_value_by_keywords(text, keywords, field_type)
            
            if field_value:
                # 使用字段ID作为键名
                extracted[field_id] = field_value
                print(f"✅ 提取到字段 {field_id}: {field_value}")
        
        if extracted:
            print(f"📊 基于实际表单字段提取到数据: {extracted}")
        else:
            print("ℹ️ 未能从用户输入中提取到匹配的表单数据")
        
        return extracted
    
    def _extract_field_value_by_keywords(self, text, keywords, field_type):
        """根据关键词和字段类型提取值"""
        import re
        
        print(f"      🎯 字段匹配尝试: 关键词={keywords}, 类型={field_type}, 文本='{text}'")
        
        # 增强关键词列表，添加中英文对应关系
        enhanced_keywords = list(keywords)
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 姓名字段的中英文对应
            if any(name_word in keyword_lower for name_word in ['name', 'custname', 'customer']):
                enhanced_keywords.extend(['姓名', '名字', '客户姓名', '用户姓名'])
            # 邮箱字段的中英文对应
            elif any(email_word in keyword_lower for email_word in ['email', 'mail', 'custemail']):
                enhanced_keywords.extend(['邮箱', '邮件', '电子邮件', 'email'])
            # 电话字段的中英文对应
            elif any(phone_word in keyword_lower for phone_word in ['phone', 'tel', 'telephone', 'custtel']):
                enhanced_keywords.extend(['电话', '手机', '联系方式', '电话号码'])
            # 评论字段的中英文对应
            elif any(comment_word in keyword_lower for comment_word in ['comment', 'message', 'comments']):
                enhanced_keywords.extend(['评论', '留言', '消息', '内容'])
        
        print(f"      🔍 增强关键词列表: {enhanced_keywords}")
        
        # 特定字段类型的处理
        if "email" in field_type.lower():
            # 邮箱字段
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            if emails:
                print(f"      ✅ 邮箱字段匹配成功: {emails[0]}")
                return emails[0]
        
        elif "tel" in field_type.lower() or "phone" in field_type.lower():
            # 电话字段
            phone_patterns = [
                r'(?:电话|手机|联系方式)(?:是|为|号码是)([0-9]{4,15})',
                r'\b(?:\+?86[-.\\s]?)?1[3-9]\d{9}\b',  # 中国手机号
                r'\b([0-9]{6,15})\b'  # 一般数字
            ]
            for pattern in phone_patterns:
                phones = re.findall(pattern, text)
                if phones:
                    result = re.sub(r'[-.\\s()]+', '', phones[0])
                    print(f"      ✅ 电话字段匹配成功: {result}")
                    return result
        
        # 根据增强的关键词匹配
        for keyword in enhanced_keywords:
            if keyword and keyword in text.lower():
                print(f"      🔍 关键词'{keyword}'在文本中找到，尝试提取值...")
                # 尝试提取关键词后的值
                patterns = [
                    rf'{re.escape(keyword)}(?:是|为|：|:)\s*([^，,。\s]{{1,100}})',
                    rf'(?:我的|我是){re.escape(keyword)}([^，,。\s]{{1,100}})',
                    rf'{re.escape(keyword)}([^，,。\s]{{1,100}})'
                ]
                
                for i, pattern in enumerate(patterns):
                    print(f"        尝试模式 {i+1}: {pattern}")
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        value = matches[0].strip()
                        if value and len(value) > 0:
                            print(f"        ✅ 模式匹配成功，提取值: {value}")
                            return value
                    else:
                        print(f"        ❌ 模式不匹配")
        
        print(f"      ❌ 无法提取字段值")
        return None
    
    def _basic_form_data_extraction(self, text):
        """基础表单数据提取（当没有表单字段信息时的备选方案）"""
        import re
        
        extracted = {}
        text_lower = text.lower()
        
        # 只提取最基础的信息
        # 邮箱提取
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            extracted["email"] = emails[0]
        
        # 电话号码提取
        phone_patterns = [
            r'(?:电话|手机|联系方式)(?:是|为|号码是)([0-9]{4,15})',
            r'\b(?:\+?86[-.\\s]?)?1[3-9]\d{9}\b',  # 中国手机号
            r'\b([0-9]{6,15})\b'  # 备选：任何6-15位数字
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = re.sub(r'[-.\\s()]+', '', phones[0])
                extracted["phone"] = phone
                break
        
        # 姓名提取
        name_patterns = [
            r'(?:我叫|我的名字是|名字是|姓名是|我是)([^，,。\\s]{1,10})',
            r'(?:叫|名字)([^，,。\\s]{1,10})',
            r'姓名([^，,。\\s]{1,10})',                         # 新增：姓名张三
            r'名字([^，,。\\s]{1,10})',                         # 新增：名字张三
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            if matches:
                name = matches[0].strip()
                if len(name) <= 10 and name:  # 合理的名字长度
                    extracted["name"] = name
                break
        
        return extracted

    async def _check_computer_messages(self):
        """检查来自Computer Agent的消息"""
        try:
            # 检查消息队列中是否有来自Computer Agent的消息（非阻塞）
            while True:
                try:
                    # 尝试立即获取消息（非阻塞）
                    message = await asyncio.wait_for(
                        self.message_queue.receive_from_computer(), 
                        timeout=0.1
                    )
                    
                    print(f"📥 收到Computer Agent消息: {message.type.name}")
                    self.log(f"📥 Received message from Computer Agent: {message.content}")
                    
                    # 根据消息类型处理
                    if message.type == MessageType.INFO:
                        # Computer Agent信息消息（页面分析结果等）
                        text = message.content.get("text", "")
                        data = message.content.get("data", {})
                        
                        if data:
                            # 解析页面信息
                            page_title = data.get("title", "未知页面")
                            page_url = data.get("url", "")
                            forms_count = data.get("forms_count", 0)
                            
                            # 检查是否是表单填写结果
                            filled_count = data.get("filled_count")
                            if filled_count is not None:
                                # 这是表单填写结果，播报给用户
                                total_count = data.get("total_count", 0)
                                if filled_count > 0:
                                    await self._speak_response(f"好的，已成功填写{filled_count}个字段")
                                else:
                                    await self._speak_response("抱歉，没有找到可填写的表单字段")
                                print(f"📢 已播报表单填写结果给用户")
                            elif page_title != "未知页面":
                                # 提取和存储详细的表单字段信息
                                form_fields_info = data.get("form_fields", [])
                                self.current_form_fields = []
                                field_names = []
                                
                                for form_info in form_fields_info:
                                    for field in form_info.get("fields", []):
                                        field_data = {
                                            "id": field.get("id", ""),
                                            "type": field.get("type", ""),
                                            "label": field.get("label", ""),
                                            "placeholder": field.get("placeholder", ""),
                                            "required": field.get("required", False)
                                        }
                                        self.current_form_fields.append(field_data)
                                        # 收集字段名用于显示
                                        display_name = field.get("label") or field.get("placeholder") or field.get("id")
                                        if display_name:
                                            field_names.append(display_name)
                                
                                print(f"📋 更新表单字段信息: {field_names}")
                                
                                # 更新Phone Agent的上下文信息
                                self.current_page_info = {
                                    "title": page_title,
                                    "url": page_url,
                                    "forms_count": forms_count,
                                    "message": text,
                                    "form_fields": form_fields_info
                                }
                                
                                print(f"🌐 页面信息已更新: {page_title} ({forms_count}个表单)")
                                self.log(f"Page info updated: {page_title}, forms: {forms_count}")
                                
                                # 如果有表单，主动告知用户实际的字段信息
                                if forms_count > 0 and field_names:
                                    field_list = "、".join(field_names[:5])  # 最多显示5个字段
                                    if len(field_names) > 5:
                                        field_list += f"等{len(field_names)}个字段"
                                    context_message = f"我看到Computer Agent已经打开了页面'{page_title}'，该页面有{forms_count}个表单，包含这些字段：{field_list}。请告诉我您要填写的信息。"
                                    # 将此信息添加到思考引擎的上下文中
                                    self.thinking_engine.add_message("system", context_message)
                                    print(f"🔄 已更新AI上下文: {context_message}")
                                elif forms_count > 0:
                                    context_message = f"我看到Computer Agent已经打开了页面'{page_title}'，该页面有{forms_count}个表单可以填写。"
                                    # 将此信息添加到思考引擎的上下文中
                                    self.thinking_engine.add_message("system", context_message)
                                    print(f"🔄 已更新AI上下文: {context_message}")
                        else:
                            # 普通文本信息，检查是否需要播报
                            if "填写" in text or "完成" in text or "成功" in text:
                                await self._speak_response(text)
                                print(f"📢 已播报Computer Agent信息给用户: {text}")
                        
                    elif message.type == MessageType.STATUS:
                        # Computer Agent状态更新
                        status = message.content.get("status", "")
                        self.log(f"Computer Agent status: {status}")
                        
                    elif message.type == MessageType.ACTION:
                        # Computer Agent执行结果
                        result = message.content.get("result", "")
                        if result:
                            # 向用户播报结果
                            await self._speak_response(f"操作完成：{result}")
                    
                except asyncio.TimeoutError:
                    # 没有新消息，跳出循环
                    break
                
        except Exception as e:
            self.log(f"Error checking computer messages: {e}")
            print(f"❌ 检查Computer Agent消息时出错: {e}")

    async def stop(self):
        """停止Phone Agent"""
        self.log("Stopping Phone Agent...")
        self.stop_event.set()
        
        # 等待运行循环结束
        timeout = 5.0
        start_time = time.time()
        while self.is_running and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
            
        if self.is_running:
            self.log("Warning: Phone Agent did not stop gracefully within timeout")
        else:
            self.log("Phone Agent stopped successfully") 