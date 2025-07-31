#!/usr/bin/env python
"""
运行Phone Agent示例

展示如何单独启动和运行Phone Agent，用于测试和演示
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径，便于导入
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入Phone Agent模块
from dual_agent.phone_agent import (
    PhoneAgent, LLMProvider, TTSProvider
)
from dual_agent.phone_agent.thinking_engine import LLMProvider


async def main(args):
    """
    主函数，初始化并运行Phone Agent
    
    参数:
        args: 命令行参数
    """
    print("初始化Phone Agent...")
    
    # 配置快慢思考提供商和模型
    if args.dummy:
        fast_provider = LLMProvider.DUMMY
        deep_provider = LLMProvider.DUMMY
        fast_model = "dummy"
        deep_model = "dummy"
    else:
        fast_provider = LLMProvider.OPENAI
        deep_provider = LLMProvider.OPENAI
        fast_model = args.fast_model
        deep_model = args.deep_model
    
    # 配置TTS提供商
    if args.tts == "dummy":
        tts_provider = TTSProvider.DUMMY
    elif args.tts == "openai":
        tts_provider = TTSProvider.OPENAI
    elif args.tts == "elevenlabs":
        tts_provider = TTSProvider.ELEVENLABS
    elif args.tts == "azure":
        tts_provider = TTSProvider.AZURE
    else:
        tts_provider = TTSProvider.DUMMY
    
    # 系统提示词
    system_prompt = """
    你是一个助手，正在通过电话帮助用户填写网页表单。
    回答要简洁、自然，专注于帮助用户完成表单填写。
    在处理时，要及时向用户反馈当前状态，避免让用户等待。
    如果网页操作遇到问题，请用平静、友好的语气向用户解释情况。
    """
    
    # 创建Phone Agent实例
    agent = PhoneAgent(
        # VAD配置
        vad_threshold=args.vad_threshold,
        vad_sampling_rate=16000,
        
        # ASR配置
        use_api_asr=not args.local_asr,
        asr_api_key=os.environ.get("OPENAI_API_KEY"),
        asr_model=args.asr_model,
        asr_language=args.language,
        
        # 思考引擎配置
        fast_provider=fast_provider,
        deep_provider=deep_provider,
        fast_model=fast_model,
        deep_model=deep_model,
        fast_api_key=os.environ.get("OPENAI_API_KEY"),
        deep_api_key=os.environ.get("OPENAI_API_KEY"),
        system_prompt=system_prompt,
        
        # TTS配置
        tts_provider=tts_provider,
        tts_api_key=os.environ.get(f"{args.tts.upper()}_API_KEY"),
        tts_voice=args.tts_voice,
        
        # 其他配置
        enable_thinking_while_listening=not args.disable_thinking_while_listening,
        debug=args.debug
    )

    # Workaround for chunk size issue
    # The VAD model requires a specific chunk size. We enforce it here.
    # This should ideally be handled within the VAD class itself.
    required_samples = 512 # For 16kHz
    agent.vad.window_size_samples = required_samples
    
    print(f"Phone Agent初始化完成，正在启动...")
    
    try:
        # 启动Phone Agent
        await agent.start(device_index=args.device_index)
    except KeyboardInterrupt:
        print("\n用户中断，正在停止Phone Agent...")
    finally:
        # 确保Phone Agent正常停止
        await agent.stop()
        print("Phone Agent已停止")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行Phone Agent")
    
    # VAD参数
    parser.add_argument("--vad-threshold", type=float, default=0.5,
                        help="VAD检测阈值 (0.0-1.0)")
    parser.add_argument("--device-index", type=int, default=0,
                        help="麦克风设备索引")
    
    # ASR参数
    parser.add_argument("--local-asr", action="store_true",
                        help="使用本地ASR模型而非API")
    parser.add_argument("--asr-model", type=str, default="whisper-1",
                        help="ASR模型名称")
    parser.add_argument("--language", type=str, default="zh",
                        help="语言代码")
    
    # LLM参数
    parser.add_argument("--fast-model", type=str, default="gpt-4o-mini",
                        help="快思考模型名称")
    parser.add_argument("--deep-model", type=str, default="gpt-4o",
                        help="深度思考模型名称")
    
    # TTS参数
    parser.add_argument("--tts", type=str, default="openai",
                        choices=["openai", "elevenlabs", "azure", "dummy"],
                        help="TTS提供商")
    parser.add_argument("--tts-voice", type=str, default="alloy",
                        help="TTS语音音色")
    
    # 其他参数
    parser.add_argument("--disable-thinking-while-listening", action="store_true",
                        help="禁用边听边想功能")
    parser.add_argument("--debug", action="store_true",
                        help="启用调试模式")
    parser.add_argument("--dummy", action="store_true",
                        help="使用模拟模式，不调用实际API")
    
    args = parser.parse_args()
    
    # 运行主函数
    asyncio.run(main(args)) 