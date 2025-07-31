"""
浏览器自动化模块

基于Playwright实现浏览器操作，支持截图、DOM提取、元素交互等功能
"""

import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum, auto

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, ElementHandle
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError

class BrowserType(Enum):
    """浏览器类型枚举"""
    CHROMIUM = auto()
    FIREFOX = auto()
    WEBKIT = auto()

class ActionType(Enum):
    """操作类型枚举"""
    CLICK = auto()
    TYPE = auto()
    SCROLL = auto()
    HOVER = auto()
    SELECT = auto()
    PRESS_KEY = auto()
    WAIT = auto()

class ActionResult:
    """操作结果类"""
    def __init__(self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }

class BrowserAutomation:
    """
    浏览器自动化类
    
    提供完整的浏览器控制功能，包括页面导航、元素交互、内容提取等
    """
    
    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = False,
        debug: bool = False,
        user_data_dir: Optional[str] = None,
        viewport_size: Tuple[int, int] = (1280, 720)
    ):
        """
        初始化浏览器自动化
        
        参数:
            browser_type: 浏览器类型
            headless: 是否无头模式
            debug: 是否调试模式
            user_data_dir: 用户数据目录(保持会话)
            viewport_size: 视窗大小
        """
        self.browser_type = browser_type
        self.headless = headless
        self.debug = debug
        self.user_data_dir = user_data_dir
        self.viewport_size = viewport_size
        
        # 浏览器实例
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 状态管理
        self.is_initialized = False
        self.current_url = ""
        self.page_title = ""
        
        # 操作历史
        self.action_history = []
        
    async def initialize(self) -> ActionResult:
        """
        初始化浏览器
        
        返回:
            操作结果
        """
        try:
            self.log("初始化浏览器自动化")
            
            # 启动Playwright
            self.playwright = await async_playwright().start()
            
            # 选择浏览器类型
            if self.browser_type == BrowserType.CHROMIUM:
                self.browser = await self.playwright.chromium.launch( # 启动浏览器返回browser对象
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            elif self.browser_type == BrowserType.FIREFOX:
                self.browser = await self.playwright.firefox.launch(headless=self.headless)
            else:
                self.browser = await self.playwright.webkit.launch(headless=self.headless)
            
            # 创建浏览器上下文
            context_options = {
                "viewport": {"width": self.viewport_size[0], "height": self.viewport_size[1]},
                "ignore_https_errors": True,
            }
            
            if self.user_data_dir:
                context_options["storage_state"] = self.user_data_dir
                
            self.context = await self.browser.new_context(**context_options)
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 设置默认超时
            self.page.set_default_timeout(30000)  # 30秒
            
            self.is_initialized = True
            self.log("浏览器初始化完成")
            
            return ActionResult(True, "浏览器初始化成功")
            
        except Exception as e:
            error_msg = f"浏览器初始化失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def navigate_to(self, url: str) -> ActionResult:
        """
        导航到指定URL
        
        参数:
            url: 目标URL
            
        返回:
            操作结果
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log(f"导航到URL: {url}")
            
            # 导航到页面
            response = await self.page.goto(url, wait_until="networkidle")
            
            # 更新状态
            self.current_url = self.page.url
            self.page_title = await self.page.title()
            
            # 记录操作
            action = {
                "type": "navigate",
                "url": url,
                "timestamp": time.time(),
                "success": True
            }
            self.action_history.append(action)
            
            result_data = {
                "url": self.current_url,
                "title": self.page_title,
                "status": response.status if response else None
            }
            
            self.log(f"导航成功: {self.page_title}")
            return ActionResult(True, f"成功导航到 {self.page_title}", result_data)
            
        except Exception as e:
            error_msg = f"导航失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def take_screenshot(self, full_page: bool = False) -> ActionResult:
        """
        截取页面截图
        
        参数:
            full_page: 是否截取完整页面
            
        返回:
            操作结果，包含base64编码的截图
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log("截取页面截图")
            
            # 截图
            screenshot_bytes = await self.page.screenshot(
                full_page=full_page,
                type="png"
            )
            
            # 转换为base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            result_data = {
                "screenshot": screenshot_base64,
                "url": self.current_url,
                "title": self.page_title,
                "full_page": full_page
            }
            
            self.log("截图完成")
            return ActionResult(True, "截图成功", result_data)
            
        except Exception as e:
            error_msg = f"截图失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def extract_page_content(self) -> ActionResult:
        """
        提取页面内容
        
        返回:
            操作结果，包含DOM结构和文本内容
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log("提取页面内容")
            
            # 获取页面HTML
            html_content = await self.page.content()
            
            # 获取页面文本
            text_content = await self.page.evaluate("() => document.body.innerText")
            
            # 获取所有表单元素
            form_elements = await self.page.evaluate("""
                () => {
                    const forms = [];
                    document.querySelectorAll('form').forEach((form, formIndex) => {
                        const formData = {
                            id: form.id || `form_${formIndex}`,
                            action: form.action,
                            method: form.method,
                            elements: []
                        };
                        
                        form.querySelectorAll('input, textarea, select').forEach((element, elementIndex) => {
                            formData.elements.push({
                                tag: element.tagName.toLowerCase(),
                                type: element.type || 'text',
                                name: element.name || `element_${elementIndex}`,
                                id: element.id || `element_${elementIndex}`,
                                placeholder: element.placeholder || '',
                                value: element.value || '',
                                required: element.required || false,
                                label: element.labels && element.labels[0] ? element.labels[0].innerText : ''
                            });
                        });
                        
                        forms.push(formData);
                    });
                    return forms;
                }
            """)
            
            # 获取所有可点击元素
            clickable_elements = await self.page.evaluate("""
                () => {
                    const elements = [];
                    document.querySelectorAll('button, a, [onclick], [role="button"]').forEach((element, index) => {
                        const rect = element.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            elements.push({
                                tag: element.tagName.toLowerCase(),
                                text: element.innerText || element.textContent || '',
                                id: element.id || `clickable_${index}`,
                                class: element.className || '',
                                href: element.href || '',
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            });
                        }
                    });
                    return elements;
                }
            """)
            
            result_data = {
                "url": self.current_url,
                "title": self.page_title,
                "html": html_content,
                "text": text_content,
                "forms": form_elements,
                "clickable_elements": clickable_elements
            }
            
            self.log(f"页面内容提取完成，发现 {len(form_elements)} 个表单，{len(clickable_elements)} 个可点击元素")
            return ActionResult(True, "页面内容提取成功", result_data)
            
        except Exception as e:
            error_msg = f"页面内容提取失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def find_element(self, selector: str, timeout: int = 5000) -> Optional[ElementHandle]:
        """
        查找页面元素
        
        参数:
            selector: CSS选择器或XPath
            timeout: 超时时间(毫秒)
            
        返回:
            元素句柄或None
        """
        if not self.is_initialized:
            return None
        
        try:
            # 判断是否为XPath
            if selector.startswith('//') or selector.startswith('xpath='):
                if selector.startswith('xpath='):
                    selector = selector[6:]
                element = await self.page.wait_for_selector(f"xpath={selector}", timeout=timeout)
            else:
                element = await self.page.wait_for_selector(selector, timeout=timeout)
            
            return element
            
        except PlaywrightTimeoutError:
            self.log(f"元素未找到: {selector}")
            return None
        except Exception as e:
            self.log(f"查找元素失败: {str(e)}")
            return None
    
    async def click_element(self, selector: str, timeout: int = 5000) -> ActionResult:
        """
        点击元素
        
        参数:
            selector: 元素选择器
            timeout: 超时时间
            
        返回:
            操作结果
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log(f"点击元素: {selector}")
            
            # 查找并点击元素
            element = await self.find_element(selector, timeout)
            if not element:
                return ActionResult(False, f"未找到元素: {selector}")
            
            await element.click()
            
            # 等待页面稳定
            await asyncio.sleep(0.5)
            
            # 记录操作
            action = {
                "type": "click",
                "selector": selector,
                "timestamp": time.time(),
                "success": True
            }
            self.action_history.append(action)
            
            self.log(f"点击成功: {selector}")
            return ActionResult(True, f"成功点击元素: {selector}")
            
        except Exception as e:
            error_msg = f"点击失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def type_text(self, selector: str, text: str, clear: bool = True, timeout: int = 5000) -> ActionResult:
        """
        在元素中输入文字
        
        参数:
            selector: 元素选择器
            text: 要输入的文字
            clear: 是否先清空
            timeout: 超时时间
            
        返回:
            操作结果
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log(f"输入文字到 {selector}: {text}")
            
            # 查找元素
            element = await self.find_element(selector, timeout)
            if not element:
                return ActionResult(False, f"未找到元素: {selector}")
            
            # 清空并输入
            if clear:
                await element.fill("")
            await element.type(text)
            
            # 记录操作
            action = {
                "type": "type",
                "selector": selector,
                "text": text,
                "timestamp": time.time(),
                "success": True
            }
            self.action_history.append(action)
            
            self.log(f"输入成功: {text}")
            return ActionResult(True, f"成功输入文字: {text}")
            
        except Exception as e:
            error_msg = f"输入失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def scroll_page(self, direction: str = "down", pixels: int = 300) -> ActionResult:
        """
        滚动页面
        
        参数:
            direction: 滚动方向 ("up", "down", "left", "right")
            pixels: 滚动像素数
            
        返回:
            操作结果
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log(f"滚动页面: {direction} {pixels}px")
            
            # 执行滚动
            if direction == "down":
                await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            elif direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
            elif direction == "right":
                await self.page.evaluate(f"window.scrollBy({pixels}, 0)")
            elif direction == "left":
                await self.page.evaluate(f"window.scrollBy(-{pixels}, 0)")
            else:
                return ActionResult(False, f"不支持的滚动方向: {direction}")
            
            # 等待滚动完成
            await asyncio.sleep(0.5)
            
            # 记录操作
            action = {
                "type": "scroll",
                "direction": direction,
                "pixels": pixels,
                "timestamp": time.time(),
                "success": True
            }
            self.action_history.append(action)
            
            return ActionResult(True, f"页面滚动成功: {direction} {pixels}px")
            
        except Exception as e:
            error_msg = f"滚动失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> ActionResult:
        """
        等待元素出现
        
        参数:
            selector: 元素选择器
            timeout: 超时时间
            
        返回:
            操作结果
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log(f"等待元素出现: {selector}")
            
            element = await self.find_element(selector, timeout)
            if element:
                return ActionResult(True, f"元素已出现: {selector}")
            else:
                return ActionResult(False, f"等待超时，元素未出现: {selector}")
                
        except Exception as e:
            error_msg = f"等待元素失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def get_element_text(self, selector: str) -> ActionResult:
        """
        获取元素文本
        
        参数:
            selector: 元素选择器
            
        返回:
            操作结果，包含元素文本
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            element = await self.find_element(selector)
            if not element:
                return ActionResult(False, f"未找到元素: {selector}")
            
            text = await element.inner_text()
            return ActionResult(True, "获取文本成功", {"text": text})
            
        except Exception as e:
            error_msg = f"获取文本失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def execute_javascript(self, script: str) -> ActionResult:
        """
        执行JavaScript代码
        
        参数:
            script: JavaScript代码
            
        返回:
            操作结果
        """
        if not self.is_initialized:
            return ActionResult(False, "浏览器未初始化")
        
        try:
            self.log(f"执行JavaScript: {script[:100]}...")
            
            result = await self.page.evaluate(script)
            
            return ActionResult(True, "JavaScript执行成功", {"result": result})
            
        except Exception as e:
            error_msg = f"JavaScript执行失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    async def close(self) -> ActionResult:
        """
        关闭浏览器
        
        返回:
            操作结果
        """
        try:
            self.log("关闭浏览器")
            
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.is_initialized = False
            
            return ActionResult(True, "浏览器关闭成功")
            
        except Exception as e:
            error_msg = f"关闭浏览器失败: {str(e)}"
            self.log(error_msg)
            return ActionResult(False, error_msg)
    
    def get_action_history(self) -> List[Dict[str, Any]]:
        """
        获取操作历史
        
        返回:
            操作历史列表
        """
        return self.action_history.copy()
    
    def clear_action_history(self) -> None:
        """清空操作历史"""
        self.action_history = []
    
    def log(self, message: str) -> None:
        """
        记录日志
        
        参数:
            message: 日志消息
        """
        if self.debug:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[BrowserAutomation {timestamp}] {message}")