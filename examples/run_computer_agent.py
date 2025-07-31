"""
Computer Agent运行示例

演示Computer Agent的基本功能，包括页面导航、分析和表单填写
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dual_agent.computer_agent import (
    ComputerAgent, ComputerAgentState, BrowserType, LLMProvider
)
from dual_agent.common.messaging import (
    create_action_message, create_info_message, MessageSource
)

async def demo_basic_functionality():
    """演示基本功能"""
    print("=== Computer Agent基本功能演示 ===\n")
    
    # 创建Computer Agent
    agent = ComputerAgent(
        browser_type=BrowserType.CHROMIUM,
        headless=False,  # 显示浏览器界面
        llm_provider=LLMProvider.DUMMY,  # 使用DUMMY模式避免API调用
        debug=True
    )
    
    try:
        print("1. 初始化浏览器...")
        # 直接初始化浏览器，不启动整个Agent
        init_result = await agent.browser.initialize()
        
        if not init_result.success:
            print(f"浏览器初始化失败: {init_result.message}")
            return
        
        print("✓ 浏览器初始化成功\n")
        
        # 演示页面导航和分析
        print("2. 导航到示例页面...")
        test_url = "https://httpbin.org/forms/post"  # 一个简单的表单页面
        
        nav_result = await agent.browser.navigate_to(test_url)
        if nav_result.success:
            print(f"✓ 导航成功: {nav_result.message}")
            
            # 分析页面
            print("3. 分析页面内容...")
            analysis = await agent.page_analyzer.analyze_page(
                agent.browser,
                use_vision=False,  # 不使用视觉分析以避免API调用
                analysis_goals=["表单识别", "可交互元素分析"]
            )
            
            print(f"✓ 页面分析完成:")
            print(f"   - 页面标题: {analysis.title}")
            print(f"   - 页面类型: {analysis.page_type}")
            print(f"   - 发现表单: {len(analysis.forms)} 个")
            print(f"   - 可交互元素: {len(analysis.interactive_elements)} 个\n")
            
            # 如果有表单，显示表单信息
            if analysis.forms:
                print("4. 表单详细信息:")
                for i, form in enumerate(analysis.forms):
                    print(f"   表单 {i+1}: {form.id}")
                    print(f"   - 提交地址: {form.action}")
                    print(f"   - 方法: {form.method}")
                    print(f"   - 字段数量: {len(form.elements)}")
                    for j, element in enumerate(form.elements[:3]):  # 只显示前3个字段
                        print(f"     字段 {j+1}: {element.label or element.id} ({element.element_type.name})")
                print()
        
        # 演示截图功能
        print("5. 截取页面截图...")
        screenshot_result = await agent.browser.take_screenshot()
        
        if screenshot_result.success:
            print("✓ 页面截图成功")
            print(f"   - 截图大小: {len(screenshot_result.data['screenshot'])} 字符 (base64)")
            print()
        
        # 演示用户数据提取
        print("6. 测试用户数据提取...")
        test_texts = [
            "我的名字是张三，邮箱是zhangsan@example.com",
            "电话号码是13800138000",
            "我叫李四"
        ]
        
        for text in test_texts:
            extracted_data = agent.extract_user_data_from_text(text)
            if extracted_data:
                print(f"   从'{text}'中提取到: {extracted_data}")
        print()
        
        # 保持浏览器打开一段时间供观察
        print("7. 保持浏览器打开10秒供观察...")
        await asyncio.sleep(10)
        
    except Exception as e:
        print(f"演示过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("8. 关闭浏览器...")
        await agent.browser.close()
        print("✓ 浏览器已关闭")

async def demo_form_filling():
    """演示表单填写功能"""
    print("=== Computer Agent表单填写演示 ===\n")
    
    # 创建Computer Agent
    agent = ComputerAgent(
        browser_type=BrowserType.CHROMIUM,
        headless=False,
        llm_provider=LLMProvider.DUMMY,
        debug=True
    )
    
    try:
        print("1. 初始化浏览器...")
        init_result = await agent.browser.initialize()
        
        if not init_result.success:
            print(f"浏览器初始化失败: {init_result.message}")
            return
        
        print("✓ 浏览器初始化成功\n")
        
        # 导航到表单页面
        print("2. 导航到表单页面...")
        form_url = "https://httpbin.org/forms/post"
        
        nav_result = await agent.browser.navigate_to(form_url)
        if nav_result.success:
            print(f"✓ 导航成功: {nav_result.message}")
        
        # 分析页面
        print("3. 分析页面内容...")
        analysis = await agent.page_analyzer.analyze_page(
            agent.browser,
            use_vision=False
        )
        
        print(f"✓ 页面分析完成，发现 {len(analysis.forms)} 个表单\n")
        
        # 演示手动填写
        print("4. 演示手动字段填写...")
        
        # 填写客户姓名
        fill_result = await agent.browser.type_text('[name="custname"]', "张三")
        if fill_result.success:
            print("✓ 客户姓名填写成功: 张三")
        
        await asyncio.sleep(1)
        
        # 填写电话
        fill_result = await agent.browser.type_text('[name="custtel"]', "13800138000")
        if fill_result.success:
            print("✓ 电话填写成功: 13800138000")
        
        await asyncio.sleep(1)
        
        # 填写邮箱
        fill_result = await agent.browser.type_text('[name="custemail"]', "zhangsan@example.com")
        if fill_result.success:
            print("✓ 邮箱填写成功: zhangsan@example.com")
        
        await asyncio.sleep(1)
        
        # 选择尺寸
        fill_result = await agent.browser.click_element('[value="medium"]')
        if fill_result.success:
            print("✓ 尺寸选择成功: medium")
        
        await asyncio.sleep(1)
        
        # 填写备注
        fill_result = await agent.browser.type_text('[name="comments"]', "这是一个测试订单，请忽略。")
        if fill_result.success:
            print("✓ 备注填写成功")
        
        print("\n5. 演示批量填写功能...")
        
        # 测试表单填写建议
        user_data = {
            "name": "李四",
            "email": "lisi@example.com",
            "phone": "13900139000"
        }
        
        suggestions = await agent.page_analyzer.suggest_form_completion(analysis, user_data)
        
        if suggestions.get("form_actions"):
            print(f"✓ 生成了 {len(suggestions['form_actions'])} 个表单的填写建议")
            
            for form_suggestion in suggestions["form_actions"]:
                print(f"   表单: {form_suggestion['form_id']}")
                print(f"   建议操作数: {len(form_suggestion['actions'])}")
        
        print("\n6. 表单填写演示完成，保持浏览器打开15秒供观察...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print(f"表单填写演示中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("7. 关闭浏览器...")
        await agent.browser.close()
        print("✓ 浏览器已关闭")

async def demo_integration_test():
    """演示完整的集成测试场景"""
    print("=== Computer Agent集成测试演示 ===\n")
    
    # 创建Computer Agent
    agent = ComputerAgent(
        browser_type=BrowserType.CHROMIUM,
        headless=False,
        llm_provider=LLMProvider.DUMMY,
        debug=True
    )
    
    try:
        print("1. 启动Computer Agent...")
        # 使用完整的Agent启动来测试消息系统
        start_task = asyncio.create_task(agent.start())
        
        # 等待一下让Agent启动
        await asyncio.sleep(2)
        print("✓ Computer Agent启动成功\n")
        
        # 模拟Phone Agent发送的导航指令
        print("2. 模拟Phone Agent发送导航指令...")
        nav_action = create_action_message(
            action="navigate",
            task_id="integration_test",
            source=MessageSource.PHONE,
            parameters={"url": "https://httpbin.org/forms/post"}
        )
        
        await agent.execute_action(nav_action)
        await asyncio.sleep(3)
        print("✓ 导航指令执行完成\n")
        
        # 模拟Phone Agent发送用户信息
        print("3. 模拟Phone Agent发送用户信息...")
        user_info = create_info_message(
            text="用户说：我的名字是王五，电话是13700137000，邮箱是wangwu@example.com",
            task_id="integration_test",
            source=MessageSource.PHONE
        )
        
        await agent.handle_phone_message(user_info)
        await asyncio.sleep(2)
        print("✓ 用户信息处理完成\n")
        
        # 模拟Phone Agent发送表单填写指令
        print("4. 模拟Phone Agent发送表单填写指令...")
        form_action = create_action_message(
            action="fill_form",
            task_id="integration_test",
            source=MessageSource.PHONE,
            parameters={
                "data": {
                    "custname": "王五",
                    "custtel": "13700137000",
                    "custemail": "wangwu@example.com",
                    "size": "large",  # 这会尝试选择对应的radio按钮
                    "comments": "集成测试订单"
                }
            }
        )
        
        await agent.execute_action(form_action)
        await asyncio.sleep(3)
        print("✓ 表单填写指令执行完成\n")
        
        # 获取当前状态
        print("5. 获取当前状态信息...")
        task_info = agent.get_current_task_info()
        if task_info:
            print("✓ 当前任务状态:")
            print(f"   - 任务ID: {task_info['task_id']}")
            print(f"   - 目标: {task_info['goal']}")
            print(f"   - Agent状态: {task_info['state']}")
            print(f"   - 已完成页面分析: {task_info['has_page_analysis']}")
        
        print("\n6. 集成测试完成，保持浏览器打开10秒供观察...")
        await asyncio.sleep(10)
        
        # 停止Agent
        await agent.stop()
        start_task.cancel()
        
    except Exception as e:
        print(f"集成测试中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("7. 确保Agent完全关闭...")
        try:
            await agent.stop()
        except:
            pass
        print("✓ Computer Agent已关闭")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Computer Agent运行示例")
    parser.add_argument(
        "--demo",
        choices=["basic", "form", "integration"],
        default="basic",
        help="选择演示类型 (default: basic)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式运行浏览器"
    )
    
    args = parser.parse_args()
    
    print("Computer Agent运行示例")
    print("=====================\n")
    
    if args.headless:
        print("注意: 运行在无头模式，无法看到浏览器界面\n")
    
    # 运行对应的演示
    if args.demo == "basic":
        asyncio.run(demo_basic_functionality())
    elif args.demo == "form":
        asyncio.run(demo_form_filling()) 
    elif args.demo == "integration":
        asyncio.run(demo_integration_test())

if __name__ == "__main__":
    main()