"""
Phone Agent测试模块

测试Phone Agent的各个组件和集成功能
"""

import asyncio
import pytest
import os
import torch
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any
import sys
from pathlib import Path

# 将项目根目录添加到Python路径中
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入被测试模块
from dual_agent.phone_agent.vad import SileroVAD
from dual_agent.phone_agent.asr import StreamingASR
from dual_agent.phone_agent.thinking_engine import (
    MixedThinkingEngine, ThinkingMode, ThinkingStatus, LLMProvider
)
from dual_agent.phone_agent.tts import TTSEngine, TTSProvider
from dual_agent.phone_agent.phone_agent import PhoneAgent, PhoneAgentState


# ========== VAD测试 ==========

@pytest.fixture
def mock_audio_tensor():
    """创建模拟音频张量"""
    # 创建一个1秒16kHz的静音音频
    return torch.zeros(16000, dtype=torch.float32)

@pytest.mark.asyncio
async def test_vad_initialization():
    """测试VAD初始化"""
    try:
        vad = SileroVAD(threshold=0.5, sampling_rate=16000)
        assert vad.model is not None, "VAD模型应该被正确加载"
        assert vad.threshold == 0.5, "阈值应该被正确设置"
    except Exception as e:
        pytest.skip(f"跳过VAD测试，可能缺少依赖: {str(e)}")

@pytest.mark.asyncio
async def test_vad_speech_detection(mock_audio_tensor):
    """测试VAD语音检测"""
    try:
        vad = SileroVAD()
        is_speech, confidence = vad.is_speech(mock_audio_tensor)
        
        # 由于是静音，应该返回False
        assert is_speech is False, "静音应该被正确识别"
        assert confidence is not None, "置信度应该有值"
    except Exception as e:
        pytest.skip(f"跳过VAD测试，可能缺少依赖: {str(e)}")


# ========== ASR测试 ==========

@pytest.fixture
def mock_asr():
    """创建模拟ASR实例"""
    with patch('dual_agent.phone_agent.asr.StreamingASR._transcribe_with_api') as mock_api:
        mock_api.return_value = {"text": "测试文本", "segments": [], "language": "zh"}
        
        # 使用DUMMY模式避免实际调用API
        asr = StreamingASR(use_api=False, local_model_size="base")
        
        # 替换内部方法，避免实际调用模型
        asr._transcribe_with_local_model = mock_api
        
        yield asr

@pytest.mark.asyncio
async def test_asr_process_audio(mock_asr, mock_audio_tensor):
    """测试ASR处理音频"""
    result = await mock_asr.process_audio_segment(mock_audio_tensor)
    
    assert result["text"] == "测试文本", "ASR应该返回预期的转录结果"
    assert result["language"] == "zh", "应该正确处理语言信息"


# ========== 混合思考引擎测试 ==========

@pytest.fixture
def mock_thinking_engine():
    """创建模拟思考引擎"""
    # 使用DUMMY提供商避免实际API调用
    engine = MixedThinkingEngine(
        fast_provider=LLMProvider.DUMMY,
        deep_provider=LLMProvider.DUMMY,
        system_prompt="你是一个测试助手"
    )
    return engine

@pytest.mark.asyncio
async def test_thinking_engine_fast_thinking(mock_thinking_engine):
    """测试快思考功能"""
    result = await mock_thinking_engine.fast_thinking(
        query="这是一个测试查询",
        partial=True
    )
    
    assert result.startswith("[快速思考]"), "快思考应该返回预期的前缀"
    assert mock_thinking_engine.fast_status == ThinkingStatus.COMPLETED, "状态应该被正确更新"

@pytest.mark.asyncio
async def test_thinking_engine_deep_thinking(mock_thinking_engine):
    """测试深度思考功能"""
    result = await mock_thinking_engine.deep_thinking(
        query="这是一个测试查询"
    )
    
    assert result.startswith("[深度思考]"), "深度思考应该返回预期的前缀"
    assert mock_thinking_engine.deep_status == ThinkingStatus.COMPLETED, "状态应该被正确更新"

@pytest.mark.asyncio
async def test_thinking_engine_filler_generation(mock_thinking_engine):
    """测试填充语生成"""
    filler = await mock_thinking_engine.generate_filler("用户正在说")
    assert isinstance(filler, str), "应该生成字符串类型的填充语"
    assert len(filler) > 0, "填充语不应为空"


# ========== TTS测试 ==========

@pytest.fixture
def mock_tts():
    """创建模拟TTS引擎"""
    # 使用DUMMY提供商避免实际API调用
    return TTSEngine(provider=TTSProvider.DUMMY)

@pytest.mark.asyncio
async def test_tts_text_to_speech(mock_tts):
    """测试文本转语音"""
    audio_data = await mock_tts.text_to_speech("这是一个测试文本")
    
    assert audio_data == b"DUMMY_AUDIO_DATA", "应该返回预期的模拟数据"


# ========== Phone Agent集成测试 ==========

@pytest.fixture
def mock_phone_agent():
    """创建模拟Phone Agent"""
    with patch('dual_agent.phone_agent.vad.SileroVAD') as mock_vad, \
         patch('dual_agent.phone_agent.asr.StreamingASR') as mock_asr, \
         patch('dual_agent.phone_agent.thinking_engine.MixedThinkingEngine') as mock_engine, \
         patch('dual_agent.phone_agent.tts.TTSEngine') as mock_tts:
        
        # 模拟组件方法
        mock_vad_instance = MagicMock()
        mock_asr_instance = MagicMock()
        mock_engine_instance = MagicMock()
        mock_tts_instance = MagicMock()
        
        # 配置返回值
        mock_vad.return_value = mock_vad_instance
        mock_asr.return_value = mock_asr_instance
        mock_engine.return_value = mock_engine_instance
        mock_tts.return_value = mock_tts_instance
        
        # 创建Phone Agent
        agent = PhoneAgent(
            vad_threshold=0.5,
            vad_sampling_rate=16000,
            use_api_asr=False,
            fast_provider=LLMProvider.DUMMY,
            deep_provider=LLMProvider.DUMMY,
            tts_provider=TTSProvider.DUMMY,
            debug=True
        )
        
        # 替换实际组件为模拟对象
        agent.vad = mock_vad_instance
        agent.asr = mock_asr_instance
        agent.thinking_engine = mock_engine_instance
        agent.tts = mock_tts_instance
        
        yield agent, mock_vad_instance, mock_asr_instance, mock_engine_instance, mock_tts_instance

def test_phone_agent_initialization(mock_phone_agent):
    """测试Phone Agent初始化"""
    agent, _, _, _, _ = mock_phone_agent
    
    assert agent.state == PhoneAgentState.IDLE, "初始状态应该是IDLE"
    assert agent.session_id is not None, "应该生成会话ID"
    assert agent.enable_thinking_while_listening is True, "默认应启用边听边想"

@pytest.mark.asyncio
async def test_process_complete_speech(mock_phone_agent):
    """测试处理完整语音"""
    agent, _, mock_asr, mock_engine, _ = mock_phone_agent

    # 将所有被await调用的mock方法替换为AsyncMock，以提供正确的返回类型和断言方法
    mock_asr.process_audio_segment = AsyncMock(return_value={"text": "这是测试语音", "segments": []})
    mock_engine.think = AsyncMock(return_value=("快速回复", "深度回复"))
    mock_engine.generate_filler = AsyncMock(return_value="嗯，让我想想...")
    agent.send_message_to_computer = AsyncMock()
    agent.speak = AsyncMock()

    mock_audio = torch.zeros(16000)
    await agent.process_complete_speech(mock_audio)

    # Give the event loop a chance to run the background task created by create_task
    await asyncio.sleep(0)

    # 验证ASR被正确调用
    mock_asr.process_audio_segment.assert_called_once_with(mock_audio)

    # 验证思考引擎和填充语生成器被正确await
    mock_engine.think.assert_awaited_once()
    mock_engine.generate_filler.assert_awaited_once()

    # 验证消息已正确await发送
    agent.send_message_to_computer.assert_awaited_once()

    # 验证speak被调用两次（一次填充语，一次深度回复）
    assert agent.speak.call_count == 2
    agent.speak.assert_any_await("嗯，让我想想...")
    agent.speak.assert_any_await("深度回复")


@pytest.mark.asyncio
async def test_process_complete_speech_no_filler(mock_phone_agent):
    """测试当已有快速回复时不生成填充语的情况"""
    agent, _, mock_asr, mock_engine, _ = mock_phone_agent

    # 设置已有快速回复，这将跳过填充语生成
    agent.last_fast_response = "之前的回复"

    # 配置Mocks
    mock_asr.process_audio_segment = AsyncMock(return_value={"text": "这是测试语音", "segments": []})
    mock_engine.think = AsyncMock(return_value=("快速回复", "深度回复"))
    mock_engine.generate_filler = AsyncMock(return_value="嗯，让我想想...")
    agent.send_message_to_computer = AsyncMock()
    agent.speak = AsyncMock()

    mock_audio = torch.zeros(16000)
    await agent.process_complete_speech(mock_audio)

    # 验证generate_filler没有被调用
    mock_engine.generate_filler.assert_not_awaited()

    # 验证speak只被调用一次（仅深度回复）
    agent.speak.assert_awaited_once_with("深度回复")


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 