#!/usr/bin/env python
"""
简单的浏览器测试脚本，用于诊断浏览器初始化问题
"""
import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from computer_agent.browser_automation import BrowserAutomation, BrowserType

async def test_browser():
    """测试浏览器初始化和页面导航"""
    print("🔍 开始测试浏览器初始化...")
    
    try:
        # 创建浏览器自动化实例
        browser = BrowserAutomation(
            browser_type=BrowserType.CHROMIUM,
            headless=False,  # 非无头模式，便于调试
            debug=True
        )
        
        # 初始化浏览器
        print("📦 正在初始化浏览器...")
        init_result = await browser.initialize()
        
        if not init_result.success:
            print(f"❌ 浏览器初始化失败: {init_result.message}")
            return
        
        print("✅ 浏览器初始化成功")
        
        # 测试导航到目标页面
        target_url = "https://httpbin.org/forms/post"
        print(f"🌐 正在导航到: {target_url}")
        
        nav_result = await browser.navigate_to(target_url)
        
        if not nav_result.success:
            print(f"❌ 页面导航失败: {nav_result.message}")
        else:
            print(f"✅ 页面导航成功: {nav_result.data.get('title', 'Unknown')}")
            
            # 提取页面内容
            print("📄 正在提取页面内容...")
            content_result = await browser.extract_page_content()
            
            if content_result.success:
                forms = content_result.data.get('forms', [])
                print(f"📝 发现 {len(forms)} 个表单")
                for i, form in enumerate(forms):
                    print(f"  表单 {i+1}: {len(form.get('elements', []))} 个字段")
            else:
                print(f"❌ 内容提取失败: {content_result.message}")
        
        # 等待一会儿让用户看到结果
        print("⏳ 等待3秒钟...")
        await asyncio.sleep(3)
        
        # 关闭浏览器
        print("🔚 正在关闭浏览器...")
        await browser.close()
        print("✅ 测试完成")
        
    except Exception as e:
        print(f"💥 测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_browser())