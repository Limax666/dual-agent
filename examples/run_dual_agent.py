#!/usr/bin/env python
"""
改进后的双Agent协同运行示例

演示基于工具调用通信和LLM驱动的智能双Agent系统
- 完全移除硬编码字符串匹配
- 集成现成浏览器自动化框架
- 基于工具调用的Agent间通信
"""

import argparse
import asyncio
import os
import signal
from dual_agent.phone_agent.phone_agent import PhoneAgent, PhoneAgentConfig
from dual_agent.phone_agent.thinking_engine import LLMProvider as PhoneLLMProvider
from dual_agent.phone_agent.tts import TTSProvider
from dual_agent.phone_agent.asr import ASRProvider
from dual_agent.computer_agent.intelligent_computer_agent import (
    IntelligentComputerAgent, 
    ComputerAgentConfig
)

class ImprovedDualAgentCoordinator:
    """改进的双Agent协调器 - 基于工具调用通信"""

    def __init__(self, args):
        self.args = args
        self.phone_agent = None
        self.computer_agent = None
        self.stop_event = asyncio.Event()

    async def initialize_agents(self):
        """初始化两个Agent"""
        print("🚀 初始化改进后的双Agent系统...")
        print("📋 系统特点:")
        print("   ✅ 基于工具调用的Agent间通信")
        print("   ✅ LLM驱动的智能表单填写")
        print("   ✅ 集成现成浏览器自动化框架")
        print("   ✅ 完全移除硬编码字符串匹配")

        # Phone Agent 配置 (保持语音处理功能不变)
        print("\n📞 初始化Phone Agent...")
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

        # Computer Agent 配置 (使用新的智能Computer Agent)
        print("💻 初始化智能Computer Agent...")
            
        computer_config = ComputerAgentConfig(
            headless=self.args.headless,
            debug=self.args.debug
        )
        
        self.computer_agent = IntelligentComputerAgent(computer_config)
        
        # 如果指定了目标URL，设置给Computer Agent
        if self.args.target_url:
            self.computer_agent.target_url = self.args.target_url
        print("✅ 改进的双Agent系统初始化完成")

    async def start_agents(self):
        """启动两个Agent并处理协同工作"""
        print("🔄 启动改进的双Agent系统...")
        
        # 确定要访问的URL (如果指定的话)
        target_url = self.args.target_url
        
        # 并行启动两个Agent
        print("💻 启动智能Computer Agent...")
        computer_task = asyncio.create_task(self.computer_agent.start())
        
        print("🎤 启动Phone Agent...")
        phone_task = asyncio.create_task(self.phone_agent.start())
        
        # 等待Agent初始化完成
        await asyncio.sleep(3)  # 增加等待时间确保browser-use完全准备好
        
        # Computer Agent会自动导航到target_url（如果设置了的话）
        print(f"🌐 Computer Agent将自动处理目标URL...")
        
        print_improved_startup_message(target_url)
        
        # 等待任意一个Agent完成（通常是用户中断）
        await asyncio.gather(phone_task, computer_task, return_exceptions=True)

    async def _request_navigation(self, url: str):
        """请求Computer Agent导航到指定URL"""
        try:
            # 使用browser-use进行导航
            await self.computer_agent._process_with_browser_use(f"请打开网页: {url}")
            print(f"✅ 成功导航到: {url}")
        except Exception as e:
            print(f"⚠️ 导航失败，但系统将继续运行: {e}")

    async def stop_agents(self):
        """停止所有Agent"""
        print("\n🛑 正在优雅地关闭改进的双Agent系统...")
        if self.phone_agent:
            await self.phone_agent.stop()
        if self.computer_agent:
            await self.computer_agent.stop()
        print("👋 系统已停止")

def print_improved_startup_message(target_url):
    """打印改进系统的启动信息"""
    print("\n" + "="*70)
    print("🎉 改进后的双Agent系统已启动！")
    print("\n🔄 系统改进点:")
    print("   ✅ 基于工具调用的Agent间通信 (替代硬编码消息队列)")
    print("   ✅ LLM驱动的智能表单填写 (替代字符串匹配)")
    print("   ✅ 集成browser-use框架 (替代自研Playwright封装)")
    print("   ✅ 通用化设计支持各种网页操作")
    
    print("\n📞 Phone Agent: 等待您的语音输入...")
    print("💻 Computer Agent: LLM驱动的智能浏览器操作")
    
    if target_url:
        print(f"🌐 目标页面: {target_url}")
    else:
        print("🌐 可以通过语音指令打开任何网页")
    
    print("\n💡 使用示例:")
    print("   🗣️  '我叫张三，邮箱是zhang@example.com'")
    print("   🗣️  '请帮我打开百度网站'")
    print("   🗣️  '填写表单，我的电话是138****8888'")
    print("   🗣️  '点击提交按钮'")
    
    print("\n🧠 智能特性:")
    print("   • LLM自动理解用户意图")
    print("   • 智能提取表单信息")
    print("   • 自适应网页结构")
    print("   • 自然语言交互")
    
    print("\n⌨️  按 Ctrl+C 退出系统")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="运行改进后的双Agent系统")
    parser.add_argument("--target-url", type=str, help="Computer Agent要访问的目标URL (可选)")
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

    # 检查环境变量
    if not args.dummy:
        if not os.environ.get("SILICONFLOW_API_KEY"):
            print("❌ 错误: 请设置 SILICONFLOW_API_KEY 环境变量")
            print("💡 或者使用 --dummy 参数运行模拟模式")
            return
        
        # 检查Browser-Use API配置
        browser_apis = [
            os.environ.get("OPENAI_API_KEY"),
            os.environ.get("ANTHROPIC_API_KEY")
        ]
        
        if not any(browser_apis):
            print("⚠️  警告: 未检测到Browser-Use专用API密钥")
            print("   🥇 推荐: 设置 OPENAI_API_KEY (兼容性最佳)")
            print("   🥈 备选: 设置 ANTHROPIC_API_KEY (高质量)")
            print("   🥉 降级: 将使用 SILICONFLOW_API_KEY (可能不兼容)")
            print("   💡 系统将自动选择最佳可用API")
            print()
        else:
            if os.environ.get("OPENAI_API_KEY"):
                print("✅ 检测到 OPENAI_API_KEY - Browser-Use将使用OpenAI API")
            elif os.environ.get("ANTHROPIC_API_KEY"):
                print("✅ 检测到 ANTHROPIC_API_KEY - Browser-Use将使用Anthropic API")
            print()

    coordinator = ImprovedDualAgentCoordinator(args)
    loop = asyncio.get_event_loop()

    def signal_handler(sig, frame):
        print("\n💡 收到中断信号，正在优雅地关闭系统...")
        if not coordinator.stop_event.is_set():
            coordinator.stop_event.set()
            loop.create_task(coordinator.stop_agents())

    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("🎯 改进后的双Agent系统")
        print("📝 基于题目要求的改进:")
        print("   • 集成现成开源工具 (browser-use)")
        print("   • 工具调用通信机制")
        print("   • LLM驱动的表单处理")
        print("   • 通用性和泛化性设计")
        print()
        
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