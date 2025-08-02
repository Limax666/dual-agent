#!/usr/bin/env python
"""
Computer Agent Browser-Use功能测试脚本

专门测试IntelligentComputerAgent的browser-use功能
目标URL: https://httpbin.org/forms/post
"""

import asyncio
import os
import sys
import time
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from computer_agent.intelligent_computer_agent import (
    IntelligentComputerAgent, 
    ComputerAgentConfig
)
from common.tool_calling import ToolMessage, MessageType


class TestComputerAgentBrowserUse:
    """Computer Agent Browser-Use功能测试类"""
    
    def __init__(self):
        self.target_url = "https://httpbin.org/forms/post"
        self.agent = None
        self.test_results = []
        
    async def setup(self):
        """初始化测试环境"""
        print("🔧 初始化测试环境...")
        
        # 创建Computer Agent配置 - 设置为非无头模式以便观察
        config = ComputerAgentConfig(
            headless=False,  # 显示浏览器窗口
            debug=True,
            max_retries=3
        )
        
        # 创建Computer Agent实例并设置目标URL
        self.agent = IntelligentComputerAgent(config)
        self.agent.target_url = self.target_url
        
        print(f"✅ Computer Agent已创建，目标URL: {self.target_url}")
        
    async def test_browser_use_availability(self):
        """测试browser-use框架是否可用"""
        test_name = "Browser-Use可用性检查"
        print(f"🧪 测试: {test_name}")
        
        try:
            # 检查browser-use导入状态
            from computer_agent.intelligent_computer_agent import BROWSER_USE_AVAILABLE
            
            if BROWSER_USE_AVAILABLE:
                print("✅ browser-use框架可用")
                self.test_results.append((test_name, "PASS", "browser-use框架导入成功"))
                return True
            else:
                print("❌ browser-use框架不可用")
                self.test_results.append((test_name, "FAIL", "browser-use框架导入失败"))
                return False
                
        except Exception as e:
            print(f"❌ 检查browser-use可用性时出错: {e}")
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def test_llm_client_creation(self):
        """测试LLM客户端创建"""
        test_name = "LLM客户端创建"
        print(f"🧪 测试: {test_name}")
        
        try:
            # 检查环境变量
            openai_key = os.environ.get("OPENAI_API_KEY")
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            siliconflow_key = os.environ.get("SILICONFLOW_API_KEY")
            
            available_apis = []
            if openai_key:
                available_apis.append("OpenAI")
            if anthropic_key:
                available_apis.append("Anthropic")
            if siliconflow_key:
                available_apis.append("Siliconflow")
            
            if available_apis:
                print(f"✅ 可用的API: {', '.join(available_apis)}")
                self.test_results.append((test_name, "PASS", f"检测到API: {', '.join(available_apis)}"))
                return True
            else:
                print("❌ 未找到可用的API密钥")
                self.test_results.append((test_name, "FAIL", "未配置API密钥"))
                return False
                
        except Exception as e:
            print(f"❌ 检查LLM客户端时出错: {e}")
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def test_agent_initialization(self):
        """测试Agent初始化"""
        test_name = "Agent初始化"
        print(f"🧪 测试: {test_name}")
        
        try:
            if self.agent.llm_client:
                print("✅ LLM客户端初始化成功")
                self.test_results.append((test_name, "PASS", "LLM客户端创建成功"))
                return True
            else:
                print("❌ LLM客户端初始化失败")
                self.test_results.append((test_name, "FAIL", "LLM客户端未创建"))
                return False
                
        except Exception as e:
            print(f"❌ Agent初始化测试失败: {e}")
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def test_navigation_to_target(self):
        """测试导航到目标页面"""
        test_name = "页面导航测试"
        print(f"🧪 测试: {test_name}")
        
        try:
            print(f"🌐 开始导航到: {self.target_url}")
            
            # 手动调用导航方法
            await self.agent._auto_navigate_to_target_url()
            
            if self.agent.page_ready:
                print("✅ 页面导航成功，页面已就绪")
                self.test_results.append((test_name, "PASS", "页面导航并分析成功"))
                return True
            else:
                print("⚠️ 页面导航完成但状态未就绪")
                self.test_results.append((test_name, "PARTIAL", "页面导航完成但状态异常"))
                return False
                
        except Exception as e:
            print(f"❌ 页面导航失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def test_form_data_extraction(self):
        """测试表单数据提取功能"""
        test_name = "表单数据提取"
        print(f"🧪 测试: {test_name}")
        
        test_inputs = [
            "我的姓名是张三",
            "我的邮箱是zhangsan@example.com", 
            "我的电话是13888888888",
            "我叫李四，邮箱是lisi@test.com，电话是13999999999"
        ]
        
        try:
            extraction_results = []
            
            for test_input in test_inputs:
                print(f"📝 测试输入: {test_input}")
                
                # 使用agent的数据提取方法
                extracted_data = await self.agent._extract_form_data_from_text(test_input)
                
                if extracted_data:
                    print(f"✅ 提取结果: {extracted_data}")
                    extraction_results.append(extracted_data)
                else:
                    print(f"⚠️ 未提取到数据")
            
            if extraction_results:
                print(f"✅ 成功提取了 {len(extraction_results)} 条数据")
                self.test_results.append((test_name, "PASS", f"成功提取 {len(extraction_results)} 条数据"))
                return True
            else:
                print("❌ 未能提取任何数据")
                self.test_results.append((test_name, "FAIL", "数据提取全部失败"))
                return False
                
        except Exception as e:
            print(f"❌ 表单数据提取测试失败: {e}")
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def test_form_filling_simulation(self):
        """测试表单填写模拟"""
        test_name = "表单填写模拟"
        print(f"🧪 测试: {test_name}")
        
        # 准备测试表单数据
        test_form_data = {
            "name": "张三",
            "email": "zhangsan@example.com",
            "phone": "13888888888"
        }
        
        try:
            print(f"📝 准备填写表单数据: {test_form_data}")
            
            # 需要导入uuid
            import uuid
            
            # 模拟用户输入消息
            user_message = ToolMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.USER_INPUT,
                sender="test_agent",
                recipient="computer_agent",
                content={
                    "text": "我的姓名是张三，邮箱是zhangsan@example.com，电话是13888888888,我要订一份小号披萨，披萨配料选择洋葱和培根，送达时间定位12点",
                    "additional_data": test_form_data
                },
                timestamp=time.time(),
                task_id="test_task_" + str(int(time.time()))
            )
            
            # 处理用户输入
            await self.agent._handle_user_input(user_message)
            
            print("✅ 表单填写模拟完成")
            self.test_results.append((test_name, "PASS", "表单填写流程执行成功"))
            return True
            
        except Exception as e:
            print(f"❌ 表单填写模拟失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def test_complete_workflow(self):
        """测试完整工作流程"""
        test_name = "完整工作流程"
        print(f"🧪 测试: {test_name}")
        
        try:
            print("🔄 执行完整的browser-use工作流程...")
            
            # 1. 确保页面已导航（在之前的测试中完成）
            if not self.agent.page_ready:
                print("⚠️ 页面未就绪，跳过完整工作流程测试")
                self.test_results.append((test_name, "SKIP", "页面未就绪"))
                return False
            
            # 2. 模拟接收表单数据消息  
            import uuid
            
            form_message = ToolMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.FORM_DATA,
                sender="test_agent",
                recipient="computer_agent",
                content={
                    "name": "测试用户",
                    "email": "test@example.com", 
                    "additional_data": {
                        "name": "测试用户",
                        "email": "test@example.com"
                    }
                },
                timestamp=time.time(),
                task_id="workflow_test_" + str(int(time.time()))
            )
            
            # 3. 处理表单数据
            await self.agent._handle_form_data(form_message)
            
            print("✅ 完整工作流程测试完成")
            self.test_results.append((test_name, "PASS", "完整流程执行成功"))
            return True
            
        except Exception as e:
            print(f"❌ 完整工作流程测试失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    async def cleanup(self):
        """清理资源"""
        print("🧹 清理测试资源...")
        
        try:
            if self.agent:
                await self.agent.stop()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️ 清理过程中出现错误: {e}")
    
    def print_results(self):
        """打印测试结果"""
        print("\n" + "="*60)
        print("📊 测试结果汇总")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed = sum(1 for _, status, _ in self.test_results if status == "PASS")
        failed = sum(1 for _, status, _ in self.test_results if status == "FAIL")
        errors = sum(1 for _, status, _ in self.test_results if status == "ERROR")
        partial = sum(1 for _, status, _ in self.test_results if status == "PARTIAL")
        skipped = sum(1 for _, status, _ in self.test_results if status == "SKIP")
        
        for test_name, status, message in self.test_results:
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌", 
                "ERROR": "💥",
                "PARTIAL": "⚠️",
                "SKIP": "⏭️"
            }.get(status, "❓")
            
            print(f"{status_icon} {test_name}: {status} - {message}")
        
        print("\n" + "-"*60)
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"错误: {errors}")
        print(f"部分成功: {partial}")
        print(f"跳过: {skipped}")
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        print("="*60)
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Computer Agent Browser-Use功能测试")
        print(f"🎯 目标URL: {self.target_url}")
        print("-"*60)
        
        try:
            # 初始化
            await self.setup()
            
            # 运行测试
            await self.test_browser_use_availability()
            await self.test_llm_client_creation()
            await self.test_agent_initialization()
            await self.test_navigation_to_target()
            await self.test_form_data_extraction()
            await self.test_form_filling_simulation()
            await self.test_complete_workflow()
            
        except KeyboardInterrupt:
            print("\n⏹️ 测试被用户中断")
        except Exception as e:
            print(f"\n💥 测试过程中发生未处理的异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理资源
            await self.cleanup()
            
            # 打印结果
            self.print_results()


async def main():
    """主函数"""
    # 检查环境变量提示
    print("💡 确保已设置以下环境变量之一:")
    print("   - OPENAI_API_KEY")
    print("   - ANTHROPIC_API_KEY") 
    print("   - SILICONFLOW_API_KEY")
    print()
    
    # 运行测试
    tester = TestComputerAgentBrowserUse()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())