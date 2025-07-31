#!/usr/bin/env python
"""
测试双Agent交互流程

验证Phone Agent和Computer Agent的正确交互流程
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dual_agent.examples.run_dual_agent import DualAgentCoordinator
import argparse

async def test_interaction_flow():
    """测试交互流程"""
    print("🧪 测试双Agent交互流程")
    print("=" * 50)
    
    # 创建测试参数
    class TestArgs:
        target_url = "https://httpbin.org/forms/post"
        debug = True
        dummy = True
        vad_threshold = 0.5
        device_index = 0
        local_asr = True
        asr_model = "whisper-1"
        language = "zh"
        fast_model = "dummy"
        deep_model = "dummy"
        disable_thinking_while_listening = False
        tts = "dummy"
        tts_voice = "alloy"
        headless = True
        computer_model = "dummy"
    
    coordinator = DualAgentCoordinator(TestArgs())
    
    try:
        # 初始化Agent
        print("1. 初始化Agent...")
        await coordinator.initialize_agents()
        
        # 启动Computer Agent
        print("2. 启动Computer Agent...")
        coordinator.computer_task = asyncio.create_task(
            coordinator.computer_agent.start()
        )
        await asyncio.sleep(1)
        
        # 静默导航到页面
        print("3. 静默导航到测试页面...")
        await coordinator._silent_navigate_to_page(TestArgs.target_url)
        await asyncio.sleep(1)
        
        # 检查Computer Agent状态
        print("4. 检查Computer Agent状态...")
        if coordinator.computer_agent.current_task:
            task = coordinator.computer_agent.current_task
            print(f"   - 任务目标: {task.goal}")
            print(f"   - 目标URL: {task.target_url}")
            if task.page_analysis:
                print(f"   - 发现表单: {len(task.page_analysis.forms)} 个")
                print(f"   - 页面标题: {task.page_analysis.title}")
            else:
                print("   - 页面分析: 未完成")
        else:
            print("   - 没有活动任务")
        
        print("\n✅ 测试完成！")
        print("📋 预期行为:")
        print("   1. Computer Agent静默导航到页面")
        print("   2. 预先分析页面但不发送消息")
        print("   3. Phone Agent只说简单问候语")
        print("   4. 等待用户语音输入后才开始真正的交互")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        print("\n🧹 清理资源...")
        await coordinator.stop_agents()

if __name__ == "__main__":
    asyncio.run(test_interaction_flow())