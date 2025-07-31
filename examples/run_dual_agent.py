#!/usr/bin/env python
"""
双Agent协同运行示例

同时启动Phone Agent和Computer Agent，演示实时语音交互和浏览器操作的协同工作
"""

import argparse
import asyncio
import os
import signal
from dual_agent.phone_agent.phone_agent import PhoneAgent, PhoneAgentConfig
from dual_agent.phone_agent.thinking_engine import LLMProvider as PhoneLLMProvider
from dual_agent.phone_agent.tts import TTSProvider
from dual_agent.phone_agent.asr import ASRProvider
from dual_agent.computer_agent.computer_agent import ComputerAgent
from dual_agent.computer_agent.page_analyzer import LLMProvider as ComputerLLMProvider

class DualAgentCoordinator:
    """双Agent协调器"""

    def __init__(self, args):
        self.args = args
        self.phone_agent = None
        self.computer_agent = None
        self.stop_event = asyncio.Event()

    async def initialize_agents(self):
        """初始化两个Agent"""
        print("🚀 初始化双Agent系统...")

        # Phone Agent 配置
        print("📞 初始化Phone Agent...")
        phone_config = PhoneAgentConfig(
            vad_threshold=self.args.vad_threshold,
            device_index=self.args.device_index,
            asr_provider=ASRProvider[self.args.asr.upper()],
            asr_model_name=self.args.asr_model,
            language=self.args.language,
            fast_think_model_name=self.args.fast_model,
            deep_think_model_name=self.args.deep_model,
            tts_provider=TTSProvider[self.args.tts.upper()],
            tts_voice=self.args.tts_voice,
            disable_thinking_while_listening=self.args.disable_thinking_while_listening,
            debug=self.args.debug
        )
        if not self.args.dummy:
            phone_config.fast_think_provider = PhoneLLMProvider.SILICONFLOW
            phone_config.deep_think_provider = PhoneLLMProvider.SILICONFLOW
        else:
            phone_config.fast_think_provider = PhoneLLMProvider.DUMMY
            phone_config.deep_think_provider = PhoneLLMProvider.DUMMY
            phone_config.tts_provider = TTSProvider.DUMMY
            
        self.phone_agent = PhoneAgent(phone_config)

        # Computer Agent 配置
        print("💻 初始化Computer Agent...")
        computer_llm_provider = ComputerLLMProvider.DUMMY if self.args.dummy else ComputerLLMProvider.SILICONFLOW
        self.computer_agent = ComputerAgent(
            headless=self.args.headless,
            llm_provider=computer_llm_provider,
            model_name=self.args.computer_model,
            debug=self.args.debug,
            session_id=self.phone_agent.session_id
        )
        print("✅ 双Agent系统初始化完成")

    async def start_agents(self):
        """启动两个Agent并处理协同工作"""
        print("🔄 启动双Agent系统...")
        
        # 确定要访问的URL
        target_url = self.args.target_url or "https://httpbin.org/forms/post"
        
        # 先启动Computer Agent
        print("💻 启动Computer Agent...")
        computer_task = asyncio.create_task(self.computer_agent.start())
        
        # 立即启动Phone Agent，确保它能接收到页面分析消息
        print("🎤 启动Phone Agent...")
        phone_task = asyncio.create_task(self.phone_agent.start())
        
        # 等待双Agent都初始化完成
        await asyncio.sleep(3)
        
        # 现在导航到目标页面并分析（此时Phone Agent已经在监听消息）
        print(f"🌐 导航到目标页面: {target_url}")
        try:
            await self.computer_agent.navigate_and_analyze(target_url, "initial_task")
            print("✅ 页面导航和分析完成，信息已发送给Phone Agent")
        except Exception as e:
            print(f"⚠️ 导航失败，但将继续运行: {e}")
        
        print_startup_message(target_url)
        
        # 等待任意一个Agent完成（通常是用户中断）
        await asyncio.gather(phone_task, computer_task, return_exceptions=True)

    async def _start_computer_agent(self, target_url):
        """启动Computer Agent并导航到页面"""
        try:
            # 启动Computer Agent（会自动初始化浏览器）并立即开始监听消息
            computer_start_task = asyncio.create_task(self.computer_agent.start())
            
            # 等待浏览器启动
            await asyncio.sleep(3)
            
            # 导航到目标页面
            print(f"🌐 导航到目标页面: {target_url}")
            try:
                await self.computer_agent.navigate_and_analyze(target_url, "initial_task")
                print("✅ 页面导航和分析完成，Computer Agent进入监听状态")
            except Exception as e:
                print(f"⚠️ 导航失败，但将继续运行: {e}")
            
            # 不等待Computer Agent主循环完成，让它在后台运行
            # Computer Agent会持续监听Phone Agent的消息
            print("💻 Computer Agent已准备就绪，等待Phone Agent指令...")
            
        except Exception as e:
            print(f"❌ Computer Agent启动失败: {e}")

    async def _start_phone_agent(self):
        """启动Phone Agent"""
        try:
            # 稍等一下让Computer Agent完成页面导航
            await asyncio.sleep(5)  # 给Computer Agent更多时间完成导航
            print("🎤 启动Phone Agent...")
            await self.phone_agent.start()
        except Exception as e:
            print(f"❌ Phone Agent启动失败: {e}")

    async def stop_agents(self):
        """停止所有Agent"""
        print(" gracefully shutting down...")
        if self.phone_agent and not self.phone_agent.stop_event.is_set():
            await self.phone_agent.stop()
        if self.computer_agent and not self.computer_agent.stop_event.is_set():
            await self.computer_agent.stop()

def print_startup_message(target_url):
    """打印启动信息"""
    print("\n" + "="*60)
    print("🎤 双Agent系统已启动！")
    print("\n📞 Phone Agent: 等待您的语音输入...")
    print("💻 Computer Agent: 已在后台准备就绪")
    if target_url:
        print(f"🌐 目标页面: {target_url}")
        if "httpbin.org/forms/post" in target_url:
            print("📝 已加载表单测试页面，可以测试表单填写功能")
    print("\n💡 使用提示:")
    print("   1. 直接说话，例如: '帮我填写表单'")
    print("   2. 提供信息，例如: '我的邮箱是test@example.com，评论是这是一个测试'")
    print("   3. Agent会自动操作浏览器并与您语音交互")
    print("\n⌨️  按 Ctrl+C 退出系统")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="运行双Agent系统")
    parser.add_argument("--target-url", type=str, help="Computer Agent要访问的目标URL")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--dummy", action="store_true", help="使用模拟模式，不调用实际API")

    phone_group = parser.add_argument_group("Phone Agent配置")
    phone_group.add_argument("--vad-threshold", type=float, default=0.5, help="VAD检测阈值 (0.0-1.0)")
    phone_group.add_argument("--device-index", type=int, default=0, help="麦克风设备索引")
    phone_group.add_argument("--language", type=str, default="zh", help="语音识别和生成的语言")
    phone_group.add_argument("--disable-thinking-while-listening", action="store_true", help="禁用边听边想功能")

    asr_group = parser.add_argument_group("ASR 配置")
    asr_group.add_argument("--asr", type=str, default="siliconflow", choices=["siliconflow", "doubao", "local", "openai"], help="ASR提供商")
    asr_group.add_argument("--asr-model", type=str, default="FunAudioLLM/SenseVoiceSmall", help="ASR模型名称")
    
    llm_group = parser.add_argument_group("LLM 配置")
    llm_group.add_argument("--fast-model", type=str, default="doubao-seed-1-6-flash-250615", help="快思考LLM模型名称")
    llm_group.add_argument("--deep-model", type=str, default="doubao-seed-1-6-thinking-250615", help="慢思考LLM模型名称")
    
    tts_group = parser.add_argument_group("TTS 配置")
    tts_group.add_argument("--tts", type=str, default="siliconflow", choices=["siliconflow", "doubao", "openai", "dummy"], help="TTS提供商")
    tts_group.add_argument("--tts-voice", type=str, default="fishaudio/fish-speech-1.5:alex", help="TTS语音音色")

    computer_group = parser.add_argument_group("Computer Agent 配置")
    computer_group.add_argument("--headless", action="store_true", help="无头模式运行浏览器")
    computer_group.add_argument("--computer-model", type=str, default=None, help="Computer Agent使用的LLM模型")

    args = parser.parse_args()

    coordinator = DualAgentCoordinator(args)
    loop = asyncio.get_event_loop()

    def signal_handler(sig, frame):
        print("\n💡 收到中断信号，正在优雅地关闭系统...")
        if not coordinator.stop_event.is_set():
            coordinator.stop_event.set()
            loop.create_task(coordinator.stop_agents())
            # Give tasks a moment to clean up
            tasks = [t for t in asyncio.all_tasks(loop=loop) if t is not asyncio.current_task(loop=loop)]
            if tasks:
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))


    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        loop.run_until_complete(coordinator.initialize_agents())
        loop.run_until_complete(coordinator.start_agents())
    except KeyboardInterrupt:
        print("系统被用户中断")
    finally:
        print("系统关闭")
        if not coordinator.stop_event.is_set():
             loop.run_until_complete(coordinator.stop_agents())
        loop.close()

if __name__ == "__main__":
    main()