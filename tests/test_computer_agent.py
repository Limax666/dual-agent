"""
Computer Agent测试模块

测试Computer Agent的各个组件和集成功能
"""

import asyncio
import pytest
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any
import sys
from pathlib import Path

# 将项目根目录添加到Python路径中
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入被测试模块
from dual_agent.computer_agent.browser_automation import (
    BrowserAutomation, BrowserType, ActionResult
)
from dual_agent.computer_agent.page_analyzer import (
    PageAnalyzer, LLMProvider, ElementType, PageElement, PageAnalysis
)
from dual_agent.computer_agent.computer_agent import (
    ComputerAgent, ComputerAgentState, TaskContext
)
from dual_agent.common.messaging import (
    A2AMessage, MessageSource, MessageType, A2AMessageQueue,
    create_info_message, create_action_message
)


# ========== 浏览器自动化测试 ==========

@pytest.fixture
def mock_browser():
    """创建模拟浏览器自动化实例"""
    browser = BrowserAutomation(headless=True, debug=False)
    
    # Mock Playwright相关组件
    with patch('dual_agent.computer_agent.browser_automation.async_playwright') as mock_playwright:
        mock_playwright_instance = AsyncMock()
        mock_browser_instance = AsyncMock()
        mock_context_instance = AsyncMock()
        mock_page_instance = AsyncMock()
        
        # 配置mock链
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser_instance)
        mock_browser_instance.new_context = AsyncMock(return_value=mock_context_instance)
        mock_context_instance.new_page = AsyncMock(return_value=mock_page_instance)
        
        # 配置页面方法
        mock_page_instance.goto = AsyncMock(return_value=MagicMock(status=200))
        mock_page_instance.title = AsyncMock(return_value="测试页面")
        mock_page_instance.url = "https://example.com"
        mock_page_instance.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
        mock_page_instance.content = AsyncMock(return_value="<html><body>测试内容</body></html>")
        
        # 设置浏览器实例的mock组件
        browser.playwright = mock_playwright_instance
        browser.browser = mock_browser_instance
        browser.context = mock_context_instance
        browser.page = mock_page_instance
        
        yield browser

@pytest.mark.asyncio
async def test_browser_initialization():
    """测试浏览器初始化"""
    with patch('dual_agent.computer_agent.browser_automation.async_playwright') as mock_playwright:
        mock_playwright_instance = AsyncMock()
        mock_browser_instance = AsyncMock()
        mock_context_instance = AsyncMock()
        mock_page_instance = AsyncMock()
        
        # 配置mock链
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser_instance)
        mock_browser_instance.new_context = AsyncMock(return_value=mock_context_instance)
        mock_context_instance.new_page = AsyncMock(return_value=mock_page_instance)
        mock_page_instance.set_default_timeout = MagicMock()
        
        browser = BrowserAutomation(headless=True, debug=False)
        result = await browser.initialize()
        
        assert result.success, f"浏览器初始化应该成功: {result.message}"
        assert browser.is_initialized, "浏览器应该标记为已初始化"

@pytest.mark.asyncio
async def test_browser_navigation(mock_browser):
    """测试浏览器导航"""
    mock_browser.is_initialized = True
    
    result = await mock_browser.navigate_to("https://example.com")
    
    assert result.success, f"导航应该成功: {result.message}"
    assert "success" in result.message.lower() or "导航" in result.message

@pytest.mark.asyncio
async def test_browser_screenshot(mock_browser):
    """测试页面截图"""
    mock_browser.is_initialized = True
    
    result = await mock_browser.take_screenshot()
    
    assert result.success, f"截图应该成功: {result.message}"
    assert "screenshot" in result.data, "结果应该包含截图数据"

@pytest.mark.asyncio
async def test_browser_content_extraction(mock_browser):
    """测试页面内容提取"""
    mock_browser.is_initialized = True
    mock_browser.current_url = "https://example.com"
    mock_browser.page_title = "测试页面"
    
    # Mock页面评估结果
    mock_browser.page.evaluate = AsyncMock(side_effect=[
        "页面文本内容",  # text_content
        [],  # form_elements
        []   # clickable_elements
    ])
    
    result = await mock_browser.extract_page_content()
    
    assert result.success, f"内容提取应该成功: {result.message}"
    assert "url" in result.data, "结果应该包含URL"
    assert "title" in result.data, "结果应该包含标题"


# ========== 页面分析器测试 ==========

@pytest.fixture
def mock_page_analyzer():
    """创建模拟页面分析器"""
    analyzer = PageAnalyzer(
        llm_provider=LLMProvider.DUMMY,
        debug=False
    )
    return analyzer

@pytest.mark.asyncio
async def test_page_analyzer_dom_analysis(mock_page_analyzer, mock_browser):
    """测试DOM结构分析"""
    mock_browser.is_initialized = True
    
    # Mock页面内容数据
    mock_page_data = {
        "url": "https://example.com",
        "title": "测试表单页面",
        "text": "这是一个测试页面",
        "forms": [
            {
                "id": "test_form",
                "action": "/submit",
                "method": "POST",
                "elements": [
                    {
                        "tag": "input",
                        "type": "text",
                        "name": "username",
                        "id": "username",
                        "placeholder": "用户名",
                        "value": "",
                        "required": True,
                        "label": "用户名"
                    },
                    {
                        "tag": "input",
                        "type": "email",
                        "name": "email",
                        "id": "email",
                        "placeholder": "邮箱地址",
                        "value": "",
                        "required": True,
                        "label": "邮箱"
                    }
                ]
            }
        ],
        "clickable_elements": [
            {
                "tag": "button",
                "text": "提交",
                "id": "submit_btn",
                "class": "btn btn-primary",
                "x": 100,
                "y": 200,
                "width": 80,
                "height": 30
            }
        ]
    }
    
    # Mock browser.extract_page_content
    mock_browser.extract_page_content = AsyncMock(
        return_value=ActionResult(True, "成功", mock_page_data)
    )
    
    # 执行分析
    analysis = await mock_page_analyzer.analyze_page(mock_browser, use_vision=False)
    
    assert analysis.url == "https://example.com", "URL应该正确"
    assert analysis.title == "测试表单页面", "标题应该正确"
    assert len(analysis.forms) == 1, "应该发现1个表单"
    assert len(analysis.forms[0].elements) == 2, "表单应该有2个元素"
    assert len(analysis.interactive_elements) == 1, "应该发现1个可交互元素"

@pytest.mark.asyncio
async def test_page_analyzer_form_completion_suggestion(mock_page_analyzer):
    """测试表单填写建议"""
    # 创建测试页面分析结果
    page_analysis = PageAnalysis(
        url="https://example.com",
        title="测试页面"
    )
    
    # 添加表单元素
    from dual_agent.computer_agent.page_analyzer import FormInfo
    form = FormInfo(id="test_form", action="/submit", method="POST")
    
    # 添加用户名字段
    username_element = PageElement(
        id="username",
        element_type=ElementType.INPUT_TEXT,
        selector="#username",
        label="用户名",
        placeholder="请输入用户名"
    )
    
    # 添加邮箱字段
    email_element = PageElement(
        id="email",
        element_type=ElementType.INPUT_EMAIL,
        selector="#email",
        label="邮箱地址",
        placeholder="请输入邮箱"
    )
    
    form.elements = [username_element, email_element]
    page_analysis.forms = [form]
    
    # 用户数据
    user_data = {
        "name": "张三",
        "email": "zhangsan@example.com"
    }
    
    # 获取填写建议
    suggestions = await mock_page_analyzer.suggest_form_completion(
        page_analysis, user_data
    )
    
    assert "form_actions" in suggestions, "应该包含表单操作建议"
    assert len(suggestions["form_actions"]) == 1, "应该有1个表单的建议"
    
    form_suggestion = suggestions["form_actions"][0]
    assert len(form_suggestion["actions"]) >= 1, "应该至少有1个填写操作"


# ========== Computer Agent集成测试 ==========

@pytest.fixture
def mock_computer_agent():
    """创建模拟Computer Agent"""
    with patch('dual_agent.computer_agent.computer_agent.BrowserAutomation') as mock_browser_class, \
         patch('dual_agent.computer_agent.computer_agent.PageAnalyzer') as mock_analyzer_class:
        
        # 创建mock实例
        mock_browser_instance = AsyncMock()
        mock_analyzer_instance = AsyncMock()
        
        # 配置mock类返回mock实例
        mock_browser_class.return_value = mock_browser_instance
        mock_analyzer_class.return_value = mock_analyzer_instance
        
        # 配置browser方法
        mock_browser_instance.initialize = AsyncMock(
            return_value=ActionResult(True, "初始化成功")
        )
        mock_browser_instance.navigate_to = AsyncMock(
            return_value=ActionResult(True, "导航成功")
        )
        mock_browser_instance.current_url = "https://example.com"
        mock_browser_instance.page_title = "测试页面"
        mock_browser_instance.close = AsyncMock(
            return_value=ActionResult(True, "关闭成功")
        )
        
        # 配置analyzer方法
        mock_analysis = PageAnalysis(
            url="https://example.com",
            title="测试页面",
            page_type="form"
        )
        mock_analyzer_instance.analyze_page = AsyncMock(return_value=mock_analysis)
        
        # 创建Computer Agent
        agent = ComputerAgent(
            headless=True,
            llm_provider=LLMProvider.DUMMY,
            debug=False
        )
        
        yield agent, mock_browser_instance, mock_analyzer_instance

def test_computer_agent_initialization(mock_computer_agent):
    """测试Computer Agent初始化"""
    agent, _, _ = mock_computer_agent
    
    assert agent.state == ComputerAgentState.IDLE, "初始状态应该是IDLE"
    assert agent.session_id is not None, "应该生成会话ID"

@pytest.mark.asyncio
async def test_computer_agent_navigation_and_analysis(mock_computer_agent):
    """测试Computer Agent导航和页面分析"""
    agent, mock_browser, mock_analyzer = mock_computer_agent
    
    # Mock消息队列
    agent.message_queue = AsyncMock()
    agent.message_queue.send_to_phone = AsyncMock()
    
    # 执行导航和分析
    await agent.navigate_and_analyze("https://example.com", "test_task_id")
    
    # 验证浏览器方法被调用
    mock_browser.navigate_to.assert_called_once_with("https://example.com")
    mock_analyzer.analyze_page.assert_called_once()
    
    # 验证消息发送
    assert agent.message_queue.send_to_phone.call_count >= 1, "应该发送至少1条消息"
    
    # 验证任务状态
    assert agent.current_task is not None, "应该创建当前任务"
    assert agent.current_task.target_url == "https://example.com", "任务URL应该正确"

@pytest.mark.asyncio
async def test_computer_agent_user_data_extraction():
    """测试用户数据提取"""
    agent = ComputerAgent(debug=False)
    
    # 测试邮箱提取
    text1 = "我的邮箱是 test@example.com"
    data1 = agent.extract_user_data_from_text(text1)
    assert "email" in data1, "应该提取到邮箱"
    assert data1["email"] == "test@example.com", "邮箱应该正确"
    
    # 测试电话号码提取
    text2 = "我的电话是 123-456-7890"
    data2 = agent.extract_user_data_from_text(text2)
    assert "phone" in data2, "应该提取到电话号码"
    
    # 测试名字提取
    text3 = "我叫张三"
    data3 = agent.extract_user_data_from_text(text3)
    assert "name" in data3, "应该提取到名字"
    assert data3["name"] == "张三", "名字应该正确"

@pytest.mark.asyncio
async def test_computer_agent_message_handling(mock_computer_agent):
    """测试Computer Agent消息处理"""
    agent, mock_browser, mock_analyzer = mock_computer_agent
    
    # Mock消息队列
    agent.message_queue = AsyncMock()
    agent.message_queue.send_to_phone = AsyncMock()
    
    # 创建测试消息
    info_message = create_info_message(
        text="我的邮箱是 test@example.com",
        task_id="test_task",
        source=MessageSource.PHONE
    )
    
    # 处理消息
    await agent.handle_phone_message(info_message)
    
    # 验证消息发送(确认消息)
    agent.message_queue.send_to_phone.assert_called_once()

@pytest.mark.asyncio
async def test_computer_agent_action_execution(mock_computer_agent):
    """测试Computer Agent操作执行"""
    agent, mock_browser, mock_analyzer = mock_computer_agent
    
    # Mock消息队列
    agent.message_queue = AsyncMock()
    agent.message_queue.send_to_phone = AsyncMock()
    
    # 创建导航操作消息
    action_message = create_action_message(
        action="navigate",
        task_id="test_task",
        source=MessageSource.PHONE,
        parameters={"url": "https://example.com"}
    )
    
    # 执行操作
    await agent.execute_action(action_message)
    
    # 验证浏览器导航被调用
    mock_browser.navigate_to.assert_called_once_with("https://example.com")
    
    # 验证页面分析被调用
    mock_analyzer.analyze_page.assert_called_once()


# ========== 集成测试场景 ==========

@pytest.mark.asyncio
async def test_form_filling_workflow():
    """测试完整的表单填写工作流程"""
    # 这是一个集成测试，测试从页面分析到表单填写的完整流程
    
    with patch('dual_agent.computer_agent.computer_agent.BrowserAutomation') as mock_browser_class, \
         patch('dual_agent.computer_agent.computer_agent.PageAnalyzer') as mock_analyzer_class:
        
        # 创建mock实例
        mock_browser = AsyncMock()
        mock_analyzer = AsyncMock()
        
        mock_browser_class.return_value = mock_browser
        mock_analyzer_class.return_value = mock_analyzer
        
        # 配置mock方法
        mock_browser.initialize = AsyncMock(return_value=ActionResult(True, "成功"))
        mock_browser.navigate_to = AsyncMock(return_value=ActionResult(True, "成功"))
        mock_browser.type_text = AsyncMock(return_value=ActionResult(True, "成功"))
        mock_browser.current_url = "https://form.example.com"
        mock_browser.page_title = "注册表单"
        mock_browser.close = AsyncMock(return_value=ActionResult(True, "成功"))
        
        # 创建表单分析结果
        from dual_agent.computer_agent.page_analyzer import FormInfo
        form = FormInfo(id="register_form", action="/register", method="POST")
        
        username_element = PageElement(
            id="username",
            element_type=ElementType.INPUT_TEXT,
            selector="#username",
            label="用户名"
        )
        
        email_element = PageElement(
            id="email", 
            element_type=ElementType.INPUT_EMAIL,
            selector="#email",
            label="邮箱"
        )
        
        form.elements = [username_element, email_element]
        
        page_analysis = PageAnalysis(
            url="https://form.example.com",
            title="注册表单",
            page_type="registration",
            forms=[form]
        )
        
        mock_analyzer.analyze_page = AsyncMock(return_value=page_analysis)
        mock_analyzer.suggest_form_completion = AsyncMock(return_value={
            "form_actions": [{
                "form_id": "register_form",
                "actions": [
                    {"type": "fill", "selector": "#username", "value": "testuser", "confidence": 0.9},
                    {"type": "fill", "selector": "#email", "value": "test@example.com", "confidence": 0.9}
                ]
            }],
            "missing_data": [],
            "confidence": 0.9
        })
        
        # 创建Computer Agent
        agent = ComputerAgent(debug=False, llm_provider=LLMProvider.DUMMY)
        agent.message_queue = AsyncMock()
        agent.message_queue.send_to_phone = AsyncMock()
        
        # 1. 导航到页面
        await agent.navigate_and_analyze("https://form.example.com", "test_task")
        
        # 2. 设置用户数据
        agent.current_task.user_data = {
            "name": "testuser",
            "email": "test@example.com"
        }
        
        # 3. 自动填写表单
        await agent.auto_fill_forms()
        
        # 验证
        assert mock_browser.navigate_to.called, "应该调用导航"
        assert mock_analyzer.analyze_page.called, "应该调用页面分析"
        assert mock_browser.type_text.call_count == 2, "应该填写2个字段"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])