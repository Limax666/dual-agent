"""
Computer Agent主模块

集成浏览器自动化和页面分析，实现智能的网页操作和表单填写功能
"""

import asyncio
import time
import uuid
import json
from typing import Dict, List, Optional, Any, Callable
from enum import Enum, auto
from dataclasses import dataclass, field

from dual_agent.computer_agent.browser_automation import BrowserAutomation, BrowserType, ActionResult
from dual_agent.computer_agent.page_analyzer import PageAnalyzer, LLMProvider, PageAnalysis, FormInfo
from dual_agent.common.messaging import (
    A2AMessage, MessageSource, MessageType, A2AMessageQueue,
    message_queue, create_info_message, create_error_message, 
    create_status_message, create_request_message
)

class ComputerAgentState(Enum):
    """Computer Agent状态枚举"""
    IDLE = auto()           # 空闲
    NAVIGATING = auto()     # 导航中
    ANALYZING = auto()      # 分析页面中
    FILLING_FORM = auto()   # 填写表单中
    WAITING_INPUT = auto()  # 等待用户输入
    ERROR = auto()          # 错误状态

@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    goal: str
    target_url: str = ""
    current_step: int = 0
    total_steps: int = 0
    user_data: Dict[str, Any] = field(default_factory=dict)
    page_analysis: Optional[PageAnalysis] = None
    completion_status: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    max_retries: int = 3

class ComputerAgent:
    """
    Computer Agent主类
    
    负责浏览器操作、页面分析和表单填写，与Phone Agent协同工作
    """
    
    def __init__(
        self,
        # 浏览器配置
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = False,
        viewport_size: tuple = (1280, 720),
        
        # LLM配置
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        model_name: str = "gpt-4-vision-preview",
        api_key: Optional[str] = None,
        
        # 其他配置
        session_id: Optional[str] = None,
        debug: bool = False
    ):
        """
        初始化Computer Agent
        
        参数:
            browser_type: 浏览器类型
            headless: 是否无头模式
            viewport_size: 视窗大小
            llm_provider: LLM提供商
            model_name: 模型名称
            api_key: API密钥
            session_id: 会话ID
            debug: 是否调试模式
        """
        self.debug = debug
        self.state = ComputerAgentState.IDLE
        self.session_id = session_id or str(uuid.uuid4())
        
        # 初始化组件
        self.browser = BrowserAutomation(
            browser_type=browser_type,
            headless=headless,
            debug=debug,
            viewport_size=viewport_size
        )
        
        self.page_analyzer = PageAnalyzer(
            llm_provider=llm_provider,
            model_name=model_name,
            api_key=api_key,
            debug=debug
        )
        
        # 消息队列
        self.message_queue = message_queue
        
        # 任务管理
        self.current_task: Optional[TaskContext] = None
        self.task_history = []
        
        # 控制事件
        self.stop_event = asyncio.Event()
        
        # 调试日志
        self.logs = []
        
    async def start(self) -> ActionResult:
        """
        启动Computer Agent
            
        返回:
            操作结果
        """
        self.log("启动Computer Agent")
        self.stop_event.clear()

        try:
            init_result = await self.browser.initialize()
            if not init_result.success:
                return init_result

            message_task = asyncio.create_task(self.receive_phone_messages())
            
            self.log("Computer Agent启动完成，正在等待指令...")
            # Keep the agent running until the stop event is set
            await self.stop_event.wait()
            
            message_task.cancel()
            await asyncio.gather(message_task, return_exceptions=True)

            return ActionResult(True, "Computer Agent正常停止")

        except Exception as e:
            error_msg = f"Computer Agent启动失败: {str(e)}"
            self.log(error_msg)
            self.state = ComputerAgentState.ERROR
            return ActionResult(False, error_msg)
    
    async def stop(self) -> ActionResult:
        """
        停止Computer Agent
        
        返回:
            操作结果
        """
        self.log("停止Computer Agent")
        self.stop_event.set()
        
        # 关闭浏览器
        await self.browser.close()
        
        return ActionResult(True, "Computer Agent已停止")
    
    async def receive_phone_messages(self) -> None:
        """接收来自Phone Agent的消息"""
        self.log("开始接收Phone Agent消息")
        
        while not self.stop_event.is_set():
            try:
                # 从消息队列接收消息
                message = await self.message_queue.receive_from_phone()
                
                self.log(f"收到Phone消息: {message.type.name}")
                
                # 处理消息
                await self.handle_phone_message(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"接收消息错误: {str(e)}")
    
    async def handle_phone_message(self, message: A2AMessage) -> None:
        """
        处理来自Phone Agent的消息
        
        参数:
            message: A2A消息
        """
        try:
            if message.type == MessageType.INFO:
                # 处理信息消息，可能包含用户数据
                await self.process_user_info(message)
                
            elif message.type == MessageType.ACTION:
                # 处理操作指令
                await self.execute_action(message)
                
            elif message.type == MessageType.REQUEST:
                # 处理请求消息
                await self.handle_request(message)
                
        except Exception as e:
            error_msg = f"处理Phone消息失败: {str(e)}"
            self.log(error_msg)
            
            # 发送错误消息
            error_response = create_error_message(
                text=error_msg,
                task_id=message.task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def process_user_info(self, message: A2AMessage) -> None:
        """
        处理用户信息
        
        参数:
            message: 包含用户信息的消息
        """
        self.log("处理用户信息")
        
        # 提取用户数据
        text = message.content.get("text", "")
        user_data = self.extract_user_data_from_text(text)
        
        if user_data:
            # 更新当前任务的用户数据
            if self.current_task:
                self.current_task.user_data.update(user_data)
                
                # 如果是第一次接收到用户信息且还没有播报过页面情况，主动播报
                if (self.current_task.goal == "silent_page_preparation" and 
                    self.current_task.page_analysis and 
                    len(self.current_task.page_analysis.forms) > 0):
                    
                    # 更新任务目标
                    self.current_task.goal = "form_filling"
                    
                    # 主动播报页面情况
                    page_title = self.current_task.page_analysis.title
                    forms_count = len(self.current_task.page_analysis.forms)
                    
                    page_info_response = create_info_message(
                        text=f"已到达页面: {page_title}",
                        task_id=message.task_id,
                        source=MessageSource.COMPUTER,
                        data={
                            "title": page_title,
                            "forms_count": forms_count,
                            "page_type": self.current_task.page_analysis.page_type
                        }
                    )
                    await self.message_queue.send_to_phone(page_info_response)
                    
                    # 发送表单填写请求
                    if forms_count > 0:
                        form_request = create_request_message(
                            text=f"发现 {forms_count} 个表单，是否需要填写？",
                            task_id=message.task_id,
                            source=MessageSource.COMPUTER,
                            request_type="form_filling_confirmation"
                        )
                        await self.message_queue.send_to_phone(form_request)
                
                # 尝试自动填写表单
                if self.current_task.page_analysis:
                    await self.auto_fill_forms()
                else:
                    # 如果还没有页面分析，先进行分析
                    await self.analyze_current_page()
                    if self.current_task.page_analysis:
                        await self.auto_fill_forms()
            else:
                # 如果没有当前任务，创建一个新任务
                self.current_task = TaskContext(
                    task_id=message.task_id,
                    goal="form_filling",
                    user_data=user_data
                )
                
                # 分析当前页面
                await self.analyze_current_page()
                
                # 尝试填写表单
                if self.current_task.page_analysis:
                    await self.auto_fill_forms()
            
            # 发送确认消息
            extracted_fields = list(user_data.keys())
            response = create_info_message(
                text=f"已接收到用户信息: {', '.join(extracted_fields)}",
                task_id=message.task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(response)
        else:
            # 如果没有提取到有效数据，通知Phone Agent
            response = create_info_message(
                text="未能从用户消息中提取到有效的表单信息",
                task_id=message.task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(response)
            
    async def analyze_current_page(self) -> None:
        """分析当前页面"""
        if not self.current_task:
            return
            
        self.log("分析当前页面")
        self.state = ComputerAgentState.ANALYZING
        
        try:
            # 分析页面
            page_analysis = await self.page_analyzer.analyze_page(
                self.browser,
                use_vision=True,
                analysis_goals=["表单识别", "可交互元素分析"]
            )
            
            self.current_task.page_analysis = page_analysis
            self.log(f"页面分析完成，发现 {len(page_analysis.forms)} 个表单")
            
        except Exception as e:
            self.log(f"页面分析失败: {str(e)}")
            self.state = ComputerAgentState.ERROR
    
    async def execute_action(self, message: A2AMessage) -> None:
        """
        执行操作指令
        
        参数:
            message: 操作消息
        """
        action = message.content.get("action", "")
        parameters = message.content.get("parameters", {})
        
        self.log(f"执行操作: {action}")
        
        try:
            if action == "navigate":
                url = parameters.get("url", "")
                await self.navigate_and_analyze(url, message.task_id)
                
            elif action == "fill_form":
                # 处理新的表单填写格式
                extracted_data = message.content.get("extracted_data", {})
                user_input = message.content.get("user_input", "")
                ai_analysis = message.content.get("ai_analysis", "")
                ai_fast_response = message.content.get("ai_fast_response", "")
                is_immediate = message.content.get("immediate", False)
                from_fast_thinking = message.content.get("from_fast_thinking", False)
                
                print(f"📝 Computer Agent收到表单填写指令:")
                print(f"   用户输入: {user_input}")
                print(f"   提取数据: {extracted_data}")
                print(f"   立即执行: {is_immediate}")
                print(f"   来自快思考: {from_fast_thinking}")
                
                if extracted_data:
                    # 有具体的表单数据，立即填写
                    await self.fill_form_with_extracted_data(extracted_data, message.task_id)
                else:
                    # 没有具体数据，使用旧的处理方式
                    form_data = message.content.get("data", {})
                    if form_data:
                        await self.fill_form_with_data(form_data, message.task_id)
                    else:
                        # 尝试从用户输入中提取数据
                        extracted_from_text = self.extract_user_data_from_text(user_input)
                        if extracted_from_text:
                            await self.fill_form_with_extracted_data(extracted_from_text, message.task_id)
                        else:
                            # 发送消息表示需要更多信息
                            response = create_info_message(
                                text="需要更具体的表单填写信息",
                                task_id=message.task_id,
                                source=MessageSource.COMPUTER
                            )
                            await self.message_queue.send_to_phone(response)
                
            elif action == "analyze_form":
                # 处理深度分析的表单操作
                extracted_data = message.content.get("extracted_data", {})
                user_input = message.content.get("user_input", "")
                ai_deep_analysis = message.content.get("ai_deep_analysis", "")
                from_deep_thinking = message.content.get("from_deep_thinking", False)
                
                print(f"🧠 Computer Agent收到深度分析指令:")
                print(f"   用户输入: {user_input}")
                print(f"   深度分析: {ai_deep_analysis[:100]}...")
                print(f"   来自深度思考: {from_deep_thinking}")
                
                # 深度分析可能包含更复杂的表单操作逻辑
                if extracted_data:
                    await self.fill_form_with_extracted_data(extracted_data, message.task_id)
                
                # 发送深度分析确认
                response = create_info_message(
                    text=f"已接收深度分析指令并处理",
                    task_id=message.task_id,
                    source=MessageSource.COMPUTER
                )
                await self.message_queue.send_to_phone(response)
                
            elif action == "click":
                selector = parameters.get("selector", "")
                await self.click_element(selector, message.task_id)
                
            elif action == "scroll":
                direction = parameters.get("direction", "down")
                await self.scroll_page(direction, message.task_id)
                
            else:
                error_msg = f"未知操作: {action}"
                self.log(error_msg)
                
                error_response = create_error_message(
                    text=error_msg,
                    task_id=message.task_id,
                    source=MessageSource.COMPUTER
                )
                await self.message_queue.send_to_phone(error_response)
                
        except Exception as e:
            error_msg = f"执行操作失败: {str(e)}"
            self.log(error_msg)
            
            error_response = create_error_message(
                text=error_msg,
                task_id=message.task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def navigate_and_analyze(self, url: str, task_id: str) -> None:
        """
        导航到页面并分析
        
        参数:
            url: 目标URL
            task_id: 任务ID
        """
        self.log(f"导航并分析页面: {url}")
        self.state = ComputerAgentState.NAVIGATING
        
        # 创建新任务上下文
        self.current_task = TaskContext(
            task_id=task_id,
            goal="page_navigation_and_analysis",
            target_url=url
        )
        
        try:
            # 导航到页面
            nav_result = await self.browser.navigate_to(url)
            if not nav_result.success:
                raise Exception(nav_result.message)
            
            # 分析页面
            self.state = ComputerAgentState.ANALYZING
            page_analysis = await self.page_analyzer.analyze_page(
                self.browser,
                use_vision=True,
                analysis_goals=["表单识别", "可交互元素分析"]
            )
            
            self.current_task.page_analysis = page_analysis
            
            # 发送分析结果，包括详细的表单字段信息
            form_fields_info = []
            for form in page_analysis.forms:
                form_info = {
                    "form_id": form.id,
                    "action": form.action,
                    "method": form.method,
                    "fields": []
                }
                for element in form.elements:
                    field_info = {
                        "id": element.id,
                        "type": element.element_type.name,
                        "selector": element.selector,
                        "label": element.label,
                        "placeholder": element.placeholder,
                        "required": element.required
                    }
                    form_info["fields"].append(field_info)
                form_fields_info.append(form_info)
            
            analysis_info = {
                "url": page_analysis.url,
                "title": page_analysis.title,
                "page_type": page_analysis.page_type,
                "forms_count": len(page_analysis.forms),
                "interactive_elements_count": len(page_analysis.interactive_elements),
                "form_fields": form_fields_info  # 添加详细的表单字段信息
            }
            
            response = create_info_message(
                text=f"已到达页面: {page_analysis.title}",
                task_id=task_id,
                source=MessageSource.COMPUTER,
                data=analysis_info
            )
            await self.message_queue.send_to_phone(response)
            
            # 如果发现表单，询问是否需要填写
            if page_analysis.forms:
                request_response = create_request_message(
                    text=f"发现 {len(page_analysis.forms)} 个表单，是否需要填写？",
                    task_id=task_id,
                    source=MessageSource.COMPUTER,
                    request_type="form_filling_confirmation"
                )
                await self.message_queue.send_to_phone(request_response)
            
            self.state = ComputerAgentState.IDLE
            
        except Exception as e:
            error_msg = f"页面导航和分析失败: {str(e)}"
            self.log(error_msg)
            self.state = ComputerAgentState.ERROR
            
            error_response = create_error_message(
                text=error_msg,
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def auto_fill_forms(self) -> None:
        """自动填写表单"""
        if not self.current_task or not self.current_task.page_analysis:
            return
        
        self.log("开始自动填写表单")
        self.state = ComputerAgentState.FILLING_FORM
        
        try:
            # 获取填写建议
            fill_suggestions = await self.page_analyzer.suggest_form_completion(
                self.current_task.page_analysis,
                self.current_task.user_data
            )
            
            filled_count = 0
            for form_suggestion in fill_suggestions["form_actions"]:
                for action in form_suggestion["actions"]:
                    if action["type"] == "fill":
                        # 获取对应的元素信息
                        element_info = None
                        for form in self.current_task.page_analysis.forms:
                            for element in form.elements:
                                if element.selector == action["selector"]:
                                    element_info = element
                                    break
                            if element_info:
                                break
                        
                        # 根据元素类型填写
                        success = False
                        if element_info:
                            success = await self._fill_element_by_type(element_info, action["value"])
                        else:
                            # 备用方法：直接尝试填写
                            result = await self.browser.type_text(action["selector"], action["value"])
                            success = result.success
                        
                        if success:
                            filled_count += 1
                            self.log(f"已填写字段: {action['selector']} = {action['value']}")
                        else:
                            self.log(f"填写失败: {action['selector']}")
            
            # 发送填写结果
            if filled_count > 0:
                response = create_info_message(
                    text=f"已自动填写 {filled_count} 个字段",
                    task_id=self.current_task.task_id,
                    source=MessageSource.COMPUTER
                )
                await self.message_queue.send_to_phone(response)
            
            # 检查是否还需要更多信息
            missing_data = fill_suggestions.get("missing_data", [])
            if missing_data:
                missing_fields = [field["label"] for field in missing_data]
                request_response = create_request_message(
                    text=f"还需要以下信息: {', '.join(missing_fields)}",
                    task_id=self.current_task.task_id,
                    source=MessageSource.COMPUTER,
                    request_type="missing_form_data",
                    required_fields=missing_fields
                )
                await self.message_queue.send_to_phone(request_response)
                self.state = ComputerAgentState.WAITING_INPUT
            else:
                self.state = ComputerAgentState.IDLE
                
        except Exception as e:
            error_msg = f"自动填写表单失败: {str(e)}"
            self.log(error_msg)
            self.state = ComputerAgentState.ERROR
    
    async def fill_form_with_data(self, form_data: Dict[str, Any], task_id: str) -> None:
        """
        使用指定数据填写表单
        
        参数:
            form_data: 表单数据
            task_id: 任务ID
        """
        self.log("使用指定数据填写表单")
        self.state = ComputerAgentState.FILLING_FORM
        
        try:
            filled_count = 0
            print(f"🔍 开始填写表单，共有 {len(form_data)} 个字段: {list(form_data.keys())}")
            
            for field_name, value in form_data.items():
                print(f"📝 尝试填写字段: {field_name} = {value}")
                
                # 获取页面分析中的元素信息
                element_info = None
                if self.current_task and self.current_task.page_analysis:
                    print(f"🔎 在页面分析中查找字段: {field_name}")
                    for form in self.current_task.page_analysis.forms:
                        for element in form.elements:
                            if (element.id == field_name or 
                                field_name in element.selector or
                                field_name.lower() in element.label.lower()):
                                element_info = element
                                print(f"✅ 找到匹配元素: {element.selector}")
                                break
                        if element_info:
                            break
                    
                    if not element_info:
                        print(f"⚠️ 在页面分析中未找到字段 {field_name}，将使用备用策略")
                else:
                    print(f"⚠️ 无页面分析数据，直接使用备用策略")
                
                # 根据元素类型选择填写策略
                success = False
                if element_info:
                    print(f"🎯 使用页面分析策略填写: {element_info.selector}")
                    # 保持原始value类型，不要转换为字符串
                    success = await self._fill_element_by_type(element_info, value)
                
                # 如果基于分析填写失败，使用备用策略
                if not success:
                    print(f"🔄 使用备用策略填写字段: {field_name}")
                    
                    # 特殊处理：如果是列表值且为toppings字段，直接调用专门的方法
                    if isinstance(value, list) and field_name.lower() in ['toppings', 'pizza_toppings']:
                        print(f"🍕 检测到toppings列表，调用专门处理方法")
                        success = await self._fill_multiple_toppings(value)
                    else:
                        success = await self._fill_element_fallback(field_name, str(value))
                
                if success:
                    filled_count += 1
                    self.log(f"已填写 {field_name}: {value}")
                    print(f"✅ 成功填写 {field_name}: {value}")
                else:
                    self.log(f"无法找到字段: {field_name}")
                    print(f"❌ 无法填写字段: {field_name}")
            
            print(f"📊 表单填写完成，成功填写 {filled_count}/{len(form_data)} 个字段")
            
            # 分析未成功填写的字段
            failed_fields = []
            if filled_count < len(form_data):
                for field_name, value in form_data.items():
                    # 这里需要跟踪哪些字段失败了，但由于当前架构限制，我们做一个简化处理
                    pass
            
            # 发送详细结果给Phone Agent
            if filled_count > 0:
                filled_fields = [f"{k}: {v}" for k, v in form_data.items()]
                result_text = f"已成功填写 {filled_count} 个字段: {', '.join(filled_fields[:3])}"  # 最多显示3个字段
                if len(filled_fields) > 3:
                    result_text += f" 等{len(filled_fields)}个字段"
            elif filled_count == 0:
                # 特殊处理：当没有任何字段被填写时
                missing_field_types = []
                for field_name in form_data.keys():
                    if field_name.lower() in ['delivery_time', 'preferred_delivery_time']:
                        if '配送时间' not in missing_field_types:
                            missing_field_types.append('配送时间')
                    elif field_name.lower() in ['delivery_instructions', 'instructions', 'comments']:
                        if '配送说明' not in missing_field_types:
                            missing_field_types.append('配送说明')
                    elif field_name.lower() in ['toppings', 'pizza_toppings']:
                        if '配料选择' not in missing_field_types:
                            missing_field_types.append('配料选择')
                    elif field_name.lower() in ['size', 'pizza_size']:
                        if '尺寸选择' not in missing_field_types:
                            missing_field_types.append('尺寸选择')
                    else:
                        missing_field_types.append(field_name)
                
                if missing_field_types:
                    result_text = f"当前表单没有以下字段：{', '.join(missing_field_types)}，无需填写这些信息"
                else:
                    result_text = f"未能填写任何字段，请检查页面表单结构"
            else:
                result_text = f"部分字段填写成功 ({filled_count}/{len(form_data)})，请检查未完成的字段"
            
            response = create_info_message(
                text=result_text,
                task_id=task_id,
                source=MessageSource.COMPUTER,
                data={
                    "filled_count": filled_count,
                    "total_count": len(form_data),
                    "filled_fields": list(form_data.keys())
                }
            )
            await self.message_queue.send_to_phone(response)
            
            self.state = ComputerAgentState.IDLE
            
        except Exception as e:
            error_msg = f"填写表单失败: {str(e)}"
            self.log(error_msg)
            self.state = ComputerAgentState.ERROR
            
            error_response = create_error_message(
                text=error_msg,
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def fill_form_with_extracted_data(self, extracted_data: Dict[str, Any], task_id: str) -> None:
        """
        使用提取的数据填写表单（与fill_form_with_data功能相同，但针对提取的数据优化）
        
        参数:
            extracted_data: 提取的表单数据
            task_id: 任务ID
        """
        self.log("使用提取的数据填写表单")
        # 直接调用现有的方法，因为功能相同
        await self.fill_form_with_data(extracted_data, task_id)
    
    async def _fill_element_by_type(self, element: 'PageElement', value: str) -> bool:
        """
        根据元素类型填写元素
        
        参数:
            element: 页面元素
            value: 要填写的值
            
        返回:
            是否成功
        """
        from dual_agent.computer_agent.page_analyzer import ElementType
        
        try:
            if element.element_type == ElementType.RADIO:
                # Radio按钮需要点击而不是填写
                # 使用element的name属性而不是id
                element_name = element.metadata.get("name", element.id)
                # 确保value是字符串类型
                radio_value = str(value) if not isinstance(value, str) else value
                
                # 构造多种可能的选择器
                radio_selectors = [
                    f'[name="{element_name}"][value="{radio_value}"]',
                    f'input[type="radio"][name="{element_name}"][value="{radio_value}"]',
                ]
                
                # 如果name包含空格，也尝试用引号包围
                if ' ' in element_name:
                    radio_selectors.extend([
                        f'[name="{element_name}"][value="{radio_value}"]',
                        f'input[type="radio"][name="{element_name}"][value="{radio_value}"]',
                    ])
                
                success = False
                for selector in radio_selectors:
                    result = await self.browser.click_element(selector)
                    if result.success:
                        success = True
                        break
                
                # 如果还是失败，尝试其他可能的选择器
                if not success:
                    # 尝试使用id作为name
                    alt_selector = f'[name="{element.id}"][value="{radio_value}"]'
                    result = await self.browser.click_element(alt_selector)
                    
                    # 如果还是失败，尝试直接使用value选择器
                    if not result.success:
                        value_selector = f'[value="{radio_value}"]'
                        result = await self.browser.click_element(value_selector)
                        success = result.success
                    else:
                        success = True
                
                return success
            
            elif element.element_type == ElementType.CHECKBOX:
                # 复选框需要根据value判断是否点击
                # 如果value是列表（如toppings），检查当前checkbox是否在列表中
                if isinstance(value, list):
                    # 对于toppings这种多选情况
                    element_value = element.metadata.get("value", "").lower()
                    element_name = element.metadata.get("name", element.id).lower()
                    element_label = element.label.lower()
                    
                    # 检查是否应该选中这个checkbox
                    should_check = False
                    for v in value:
                        v_lower = str(v).lower()
                        if (v_lower in element_value or 
                            v_lower in element_name or 
                            v_lower in element_label):
                            should_check = True
                            break
                    
                    if should_check:
                        # 构造多种可能的选择器
                        checkbox_selectors = [
                            element.selector,
                        ]
                        
                        # 如果有name属性，添加更多选择器
                        if element.metadata.get("name"):
                            name = element.metadata["name"]
                            checkbox_selectors.extend([
                                f'[name="{name}"]',
                                f'input[type="checkbox"][name="{name}"]',
                            ])
                        
                        # 尝试每个选择器
                        for selector in checkbox_selectors:
                            result = await self.browser.click_element(selector)
                            if result.success:
                                return True
                        return False
                    else:
                        return True  # 不需要选中，视为成功
                else:
                    # 单个checkbox，直接点击
                    result = await self.browser.click_element(element.selector)
                    return result.success
            
            elif element.element_type == ElementType.SELECT:
                # 下拉选择框需要特殊处理
                # 确保value是字符串类型
                select_value = str(value) if not isinstance(value, str) else value
                script = f"""
                const select = document.querySelector('{element.selector}');
                if (select) {{
                    select.value = '{select_value}';
                    select.dispatchEvent(new Event('change'));
                    return true;
                }}
                return false;
                """
                result = await self.browser.execute_javascript(script)
                return result.success and result.data.get("result", False)
            
            else:
                # 文本输入类元素
                # 如果value是列表，转换为字符串
                text_value = str(value) if not isinstance(value, str) else value
                result = await self.browser.type_text(element.selector, text_value)
                return result.success
                
        except Exception as e:
            self.log(f"填写元素失败: {str(e)}")
            return False
    
    async def _fill_element_fallback(self, field_name: str, value: str) -> bool:
        """
        备用填写策略
        
        参数:
            field_name: 字段名
            value: 值
            
        返回:
            是否成功
        """
        print(f"🔄 使用备用策略查找字段: {field_name}")
        
        # 根据字段名类型生成更多选择器
        base_selectors = [
            f'[name="{field_name}"]',
            f'#{field_name}',
            f'[id*="{field_name}"]',
            f'[placeholder*="{field_name}"]',
            # 添加针对pizza表单的通用选择器
            f'[name="pizza {field_name}"]',  # 如 "pizza size", "pizza toppings"
            f'[id="pizza {field_name}"]',
            f'[name*="pizza {field_name}"]',
            f'[id*="pizza {field_name}"]',
            # 添加针对preferred字段的选择器
            f'[name="preferred {field_name}"]',  # 如 "preferred delivery time" 
            f'[id="preferred {field_name}"]',
            f'[name*="preferred {field_name}"]',
            f'[id*="preferred {field_name}"]',
        ]
        
        # 针对姓名字段的特殊处理
        if field_name.lower() in ['name', 'custname', 'username', 'firstname', 'lastname']:
            name_selectors = [
                '[name*="name"]',
                '[id*="name"]',
                '[placeholder*="姓名"]',
                '[placeholder*="名字"]',
                '[placeholder*="Name"]',
                'input[type="text"]:first-of-type',  # 通常第一个文本框是姓名
            ]
            base_selectors.extend(name_selectors)
        
        # 针对邮箱字段的特殊处理
        elif field_name.lower() in ['email', 'custemail', 'mail']:
            email_selectors = [
                '[name*="email"]',
                '[id*="email"]', 
                '[placeholder*="邮箱"]',
                '[placeholder*="Email"]',
                '[type="email"]'
            ]
            base_selectors.extend(email_selectors)
        
        # 针对电话字段的特殊处理
        elif field_name.lower() in ['phone', 'custtel', 'tel', 'mobile']:
            phone_selectors = [
                '[name*="phone"]',
                '[name*="tel"]',
                '[id*="phone"]',
                '[id*="tel"]',
                '[placeholder*="电话"]',
                '[placeholder*="手机"]',
                '[type="tel"]'
            ]
            base_selectors.extend(phone_selectors)
        
        # 针对pizza size字段的特殊处理
        elif field_name.lower() in ['size', 'pizza_size']:
            size_selectors = [
                '[name*="size"]',
                '[id*="size"]',
                '[name="pizza size"]',  # 添加带空格的实际ID
                '[id="pizza size"]',    # 添加带空格的实际ID
                '[name*="pizza size"]',
                '[id*="pizza size"]',
                f'[value="{value}"]',  # 直接按value查找radio
                f'input[type="radio"][value="{value}"]',  # 明确指定radio类型
                f'input[type="radio"][name="pizza size"][value="{value}"]',  # 实际结构
                f'input[type="radio"][name*="pizza size"][value="{value}"]',
                f'input[type="radio"][name*="size"][value="{value}"]',
            ]
            base_selectors.extend(size_selectors)
        
        # 针对pizza toppings字段的特殊处理  
        elif field_name.lower() in ['toppings', 'pizza_toppings']:
            if isinstance(value, list):
                # 对于多个toppings，需要特殊处理
                return await self._fill_multiple_toppings(value)
            else:
                topping_selectors = [
                    '[name*="topping"]',
                    '[id*="topping"]',
                    '[name="pizza toppings"]',  # 添加带空格的实际ID
                    '[id="pizza toppings"]',    # 添加带空格的实际ID
                    '[name*="pizza toppings"]',
                    '[id*="pizza toppings"]',
                    f'[value="{value}"]',
                    f'input[type="checkbox"][value="{value}"]',
                ]
                base_selectors.extend(topping_selectors)
        
        # 针对配送时间字段的特殊处理
        elif field_name.lower() in ['delivery_time', 'preferred_delivery_time', 'delivery', 'time']:
            delivery_selectors = [
                # 最精确的匹配（优先尝试）
                'input[name="preferred delivery time"]',  # 精确匹配完整字段名
                'select[name="preferred delivery time"]',
                'input[id="preferred delivery time"]',
                'select[id="preferred delivery time"]',
                
                # 部分匹配的高优先级选择器
                'input[name*="preferred"][name*="delivery"][name*="time"]',
                'select[name*="preferred"][name*="delivery"][name*="time"]',
                'input[name*="preferred delivery time"]',
                'select[name*="preferred delivery time"]',
                'input[id*="preferred delivery time"]',
                'select[id*="preferred delivery time"]',
                
                # 标准的delivery time匹配
                'input[name="delivery time"]',
                'select[name="delivery time"]',
                'input[id="delivery time"]',
                'select[id="delivery time"]',
                'input[name*="delivery time"]',
                'select[name*="delivery time"]',
                'input[id*="delivery time"]',
                'select[id*="delivery time"]',
                
                # 基础选择器
                'input[name*="delivery"]',
                'select[name*="delivery"]',
                'input[id*="delivery"]',
                'select[id*="delivery"]',
                'input[name*="time"]',
                'select[name*="time"]',
                'input[id*="time"]',
                'select[id*="time"]',
                
                # HTML5时间类型（高优先级）
                'input[type="time"]',  # HTML5时间输入
                'input[type="datetime-local"]',  # 日期时间输入
                
                # 按placeholder匹配
                'input[placeholder*="time"]',
                'input[placeholder*="时间"]',
                'input[placeholder*="delivery"]',
                'input[placeholder*="配送"]',
                'select[placeholder*="time"]',
                'select[placeholder*="时间"]',
                
                # 按class匹配
                'input[class*="delivery"]',
                'select[class*="delivery"]',
                'input[class*="time"]',
                'select[class*="time"]',
                '[class*="delivery"]',
                '[class*="time"]',
                
                # 最宽泛的匹配
                'input[type="text"][pattern*="time"]',
                'textarea[name*="delivery"]',
                'textarea[name*="time"]',
            ]
            base_selectors.extend(delivery_selectors)
        
        # 针对配送说明字段的特殊处理
        elif field_name.lower() in ['delivery_instructions', 'instructions', 'comments']:
            instructions_selectors = [
                '[name*="instruction"]',
                '[id*="instruction"]',
                '[name*="comment"]',
                '[id*="comment"]',
                '[name="delivery instructions"]',  # 完整的实际ID
                '[id="delivery instructions"]',    # 完整的实际ID
                '[name*="delivery instructions"]',
                '[id*="delivery instructions"]',
                'textarea[name*="instruction"]',  # 可能是文本域
                'textarea[id*="instruction"]',
                'textarea[name*="comment"]',
                'textarea[id*="comment"]',
            ]
            base_selectors.extend(instructions_selectors)
        
        # 去重
        selectors = list(dict.fromkeys(base_selectors))
        print(f"🎯 尝试 {len(selectors)} 个选择器策略")
        
        for i, selector in enumerate(selectors):
            print(f"  {i+1}. 尝试选择器: {selector}")
            try:
                # 首先尝试普通填写
                result = await self.browser.type_text(selector, value)
                if result.success:
                    print(f"✅ 选择器成功: {selector}")
                    return True
                else:
                    print(f"   失败: {result.message}")
                
                # 如果填写失败，可能是radio或checkbox，尝试点击
                if "radio" in result.message.lower() or "checkbox" in result.message.lower() or field_name.lower() in ['size', 'pizza_size', 'toppings', 'pizza_toppings']:
                    # 先尝试点击对应值的radio/checkbox按钮
                    value_selector = f'{selector}[value="{value}"]'
                    click_result = await self.browser.click_element(value_selector)
                    if click_result.success:
                        print(f"✅ Radio/Checkbox按钮点击成功: {value_selector}")
                        return True
                    
                    # 如果还是失败，尝试直接点击元素（不带value）
                    click_result = await self.browser.click_element(selector)
                    if click_result.success:
                        print(f"✅ 元素点击成功: {selector}")
                        return True
            except Exception as e:
                print(f"   异常: {str(e)}")
                continue
        
        print(f"❌ 所有备用策略都失败了")
        
        # 智能失败处理：为特定字段类型提供有意义的反馈
        field_type_feedback = {
            'delivery_time': '该表单没有配送时间选择字段',
            'preferred_delivery_time': '该表单没有配送时间选择字段', 
            'delivery_instructions': '该表单没有配送说明字段',
            'toppings': '该表单没有配料选择字段',
            'pizza_toppings': '该表单没有配料选择字段',
            'size': '该表单没有尺寸选择字段',
            'pizza_size': '该表单没有尺寸选择字段',
        }
        
        feedback = field_type_feedback.get(field_name.lower(), f'该表单没有匹配的 {field_name} 字段')
        print(f"💡 智能反馈: {feedback}")
        
        return False
    
    async def _fill_multiple_toppings(self, toppings: List[str]) -> bool:
        """
        填写多个pizza toppings
        
        参数:
            toppings: toppings列表
            
        返回:
            是否成功
        """
        print(f"🍕 处理多个toppings: {toppings}")
        success_count = 0
        
        for topping in toppings:
            topping_lower = topping.lower()
            print(f"🔍 处理topping: {topping}")
            
            # 扩展的checkbox选择器，基于实际HTML结构
            topping_selectors = [
                # 按value匹配
                f'[value="{topping}"]',
                f'[value="{topping_lower}"]', 
                f'[value="{topping.title()}"]',  # 首字母大写
                f'[value="{topping.upper()}"]',  # 全大写
                
                # 按name匹配 - 包含带空格的实际ID
                f'[name="{topping_lower}"]',
                f'[name*="{topping_lower}"]',
                f'[name="pizza toppings"]',  # 实际的HTML name
                f'[name*="pizza toppings"]',
                f'[name*="topping"]',
                
                # 按id匹配 - 包含带空格的实际ID
                f'[id="{topping_lower}"]',
                f'[id*="{topping_lower}"]',
                f'[id="pizza toppings"]',   # 实际的HTML id
                f'[id*="pizza toppings"]',
                f'[id*="topping"]',
                
                # 明确指定checkbox类型
                f'input[type="checkbox"][value="{topping}"]',
                f'input[type="checkbox"][value="{topping_lower}"]',
                f'input[type="checkbox"][value="{topping.title()}"]',
                f'input[type="checkbox"][name*="{topping_lower}"]',
                f'input[type="checkbox"][name="pizza toppings"]',  # 实际的HTML结构
                f'input[type="checkbox"][name*="pizza toppings"]',
                f'input[type="checkbox"][name*="topping"]',
                
                # 通用的topping选择器
                f'input[type="checkbox"][name*="topping"][value*="{topping_lower}"]',
                f'input[type="checkbox"][id*="topping"][value*="{topping_lower}"]',
            ]
            
            # 特殊映射处理 - 扩展更多可能的值
            topping_mapping = {
                'bacon': ['bacon', 'Bacon', 'BACON'],
                'cheese': ['cheese', 'Cheese', 'CHEESE', 'Extra Cheese', 'extra cheese', 'extra_cheese'],
                'onion': ['onion', 'Onion', 'ONION'],
                'mushroom': ['mushroom', 'Mushroom', 'MUSHROOM', 'mushrooms', 'Mushrooms']
            }
            
            if topping_lower in topping_mapping:
                for mapped_value in topping_mapping[topping_lower]:
                    topping_selectors.extend([
                        f'[value="{mapped_value}"]',
                        f'input[type="checkbox"][value="{mapped_value}"]',
                        f'input[name*="{mapped_value.lower()}"]',
                        f'input[id*="{mapped_value.lower()}"]',
                        # 添加针对"pizza toppings"的特殊选择器
                        f'input[type="checkbox"][name="pizza toppings"][value="{mapped_value}"]',
                        f'input[type="checkbox"][name*="pizza toppings"][value="{mapped_value}"]',
                        f'input[type="checkbox"][id="pizza toppings"][value="{mapped_value}"]',
                        f'input[type="checkbox"][id*="pizza toppings"][value="{mapped_value}"]',
                    ])
            
            # 尝试每个选择器
            topping_success = False
            for i, selector in enumerate(topping_selectors):
                print(f"    {i+1}. 尝试选择器: {selector}")
                try:
                    result = await self.browser.click_element(selector, timeout=2000)  # 短超时
                    if result.success:
                        print(f"✅ Topping成功选中: {topping} (选择器: {selector})")
                        success_count += 1
                        topping_success = True
                        break
                    else:
                        print(f"    失败: {result.message}")
                except Exception as e:
                    print(f"    异常: {str(e)}")
                    continue
            
            if not topping_success:
                print(f"❌ Topping选择失败: {topping}")
                # 记录所有尝试过的选择器用于调试
                print(f"    尝试了 {len(topping_selectors)} 个选择器都失败")
        
        print(f"📊 Toppings处理完成: {success_count}/{len(toppings)} 成功")
        return success_count > 0
    
    async def click_element(self, selector: str, task_id: str) -> None:
        """
        点击元素
        
        参数:
            selector: 元素选择器
            task_id: 任务ID
        """
        self.log(f"点击元素: {selector}")
        
        try:
            result = await self.browser.click_element(selector)
            
            if result.success:
                response = create_info_message(
                    text=f"已点击元素: {selector}",
                    task_id=task_id,
                    source=MessageSource.COMPUTER
                )
            else:
                response = create_error_message(
                    text=f"点击失败: {result.message}",
                    task_id=task_id,
                    source=MessageSource.COMPUTER
                )
            
            await self.message_queue.send_to_phone(response)
            
        except Exception as e:
            error_msg = f"点击元素失败: {str(e)}"
            self.log(error_msg)
            
            error_response = create_error_message(
                text=error_msg,
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def scroll_page(self, direction: str, task_id: str) -> None:
        """
        滚动页面
        
        参数:
            direction: 滚动方向
            task_id: 任务ID
        """
        self.log(f"滚动页面: {direction}")
        
        try:
            result = await self.browser.scroll_page(direction)
            
            response = create_info_message(
                text=f"页面已{direction}滚动",
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(response)
            
        except Exception as e:
            error_msg = f"滚动页面失败: {str(e)}"
            self.log(error_msg)
            
            error_response = create_error_message(
                text=error_msg,
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def handle_request(self, message: A2AMessage) -> None:
        """
        处理请求消息
        
        参数:
            message: 请求消息
        """
        request_type = message.content.get("request_type", "")
        
        if request_type == "page_screenshot":
            # 截图请求
            await self.send_screenshot(message.task_id)
            
        elif request_type == "page_analysis":
            # 页面分析请求
            await self.send_page_analysis(message.task_id)
            
        elif request_type == "current_status":
            # 状态查询请求
            await self.send_current_status(message.task_id)
    
    async def send_screenshot(self, task_id: str) -> None:
        """发送页面截图"""
        try:
            screenshot_result = await self.browser.take_screenshot()
            
            if screenshot_result.success:
                response = create_info_message(
                    text="页面截图",
                    task_id=task_id,
                    source=MessageSource.COMPUTER,
                    data={"screenshot": screenshot_result.data["screenshot"]}
                )
            else:
                response = create_error_message(
                    text=f"截图失败: {screenshot_result.message}",
                    task_id=task_id,
                    source=MessageSource.COMPUTER
                )
            
            await self.message_queue.send_to_phone(response)
            
        except Exception as e:
            error_response = create_error_message(
                text=f"截图失败: {str(e)}",
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def send_page_analysis(self, task_id: str) -> None:
        """发送页面分析结果"""
        try:
            if self.current_task and self.current_task.page_analysis:
                analysis = self.current_task.page_analysis
                analysis_data = {
                    "url": analysis.url,
                    "title": analysis.title,
                    "page_type": analysis.page_type,
                    "forms_count": len(analysis.forms),
                    "suggestions": analysis.suggestions
                }
                
                response = create_info_message(
                    text="页面分析结果",
                    task_id=task_id,
                    source=MessageSource.COMPUTER,
                    data=analysis_data
                )
            else:
                response = create_error_message(
                    text="暂无页面分析结果",
                    task_id=task_id,
                    source=MessageSource.COMPUTER
                )
            
            await self.message_queue.send_to_phone(response)
            
        except Exception as e:
            error_response = create_error_message(
                text=f"获取分析结果失败: {str(e)}",
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    async def send_current_status(self, task_id: str) -> None:
        """发送当前状态"""
        try:
            status_data = {
                "state": self.state.name,
                "current_url": self.browser.current_url,
                "page_title": self.browser.page_title,
                "has_active_task": self.current_task is not None
            }
            
            if self.current_task:
                status_data["task_info"] = {
                    "goal": self.current_task.goal,
                    "progress": f"{self.current_task.current_step}/{self.current_task.total_steps}"
                }
            
            response = create_status_message(
                status=self.state.name,
                task_id=task_id,
                source=MessageSource.COMPUTER,
                details=json.dumps(status_data)
            )
            
            await self.message_queue.send_to_phone(response)
            
        except Exception as e:
            error_response = create_error_message(
                text=f"获取状态失败: {str(e)}",
                task_id=task_id,
                source=MessageSource.COMPUTER
            )
            await self.message_queue.send_to_phone(error_response)
    
    def extract_user_data_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取用户数据
        
        参数:
            text: 用户输入文本
            
        返回:
            提取的用户数据
        """
        # 清理文本，移除多余的分析说明
        text = text.replace("用户说：", "").strip()
        
        user_data = {}
        text_lower = text.lower()
        
        # 常见模式匹配
        import re
        
        # 邮箱匹配
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            user_data["email"] = emails[0]
            user_data["custemail"] = emails[0]  # 添加常见的表单字段名
        else:
            # 如果没有找到标准格式，尝试提取用户明确说明的邮箱
            email_statement_patterns = [
                r'(?:邮箱是|邮箱为|email是|email为|电子邮箱是)([^\s,，。]+)',
                r'(?:邮箱|email)[:：]([^\s,，。]+)',
                r'(?:填写|填入)(?:邮箱|email)([^\s,，。]+)',
            ]
            
            for pattern in email_statement_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    email_value = matches[0].strip()
                    if email_value:
                        user_data["email"] = email_value
                        user_data["custemail"] = email_value
                    break
        
        # 电话号码匹配 - 改进的模式
        phone_patterns = [
            r'\b(?:\+?86[-.\s]?)?1[3-9]\d{9}\b',  # 中国手机号
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',  # 美国电话
        ]
        
        phone_found = False
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = re.sub(r'[-.\s\(\)]', '', phones[0])  # 清理格式
                user_data["phone"] = phone
                user_data["custtel"] = phone  # 添加常见的表单字段名
                phone_found = True
                break
        
        # 如果没有找到标准格式，尝试提取用户明确说明的电话
        if not phone_found:
            phone_statement_patterns = [
                r'(?:电话是|电话号码是|电话为|电话号码为|手机是|手机号码是|手机为|手机号码为|联系方式是)([0-9]+)',
                r'(?:电话|手机|联系方式)[:：]([0-9]+)',
                r'(?:填写|填入)(?:电话|手机)([0-9]+)',
                r'([0-9]{4,15})(?:是我的电话|是我的手机)',
            ]
            
            for pattern in phone_statement_patterns:
                phones = re.findall(pattern, text, re.IGNORECASE)
                if phones:
                    phone = re.sub(r'[-.\s\(\)]', '', phones[0])
                    if len(phone) >= 4:  # 至少4位数字
                        user_data["phone"] = phone
                        user_data["custtel"] = phone
                        phone_found = True
                    break
        
        # 名字匹配 - 改进的逻辑
        name_patterns = [
            r'(?:我叫|我的名字是|名字是|姓名是)([^\s,，。]+)',
            r'(?:我是|叫做)([^\s,，。]+)',
            r'(?:姓名|名字)(?:填写|填入|是|为)([^\s,，。]+)',  # 新增：姓名填写张三
            r'(?:填写|填入)(?:姓名|名字)([^\s,，。]+)',     # 新增：填写姓名张三
            r'([^\s,，。]+)(?:是我的名字|是我的姓名)',      # 新增：张三是我的名字
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            if matches:
                name = matches[0].strip()
                if name and len(name) <= 10:  # 合理的名字长度
                    user_data["name"] = name
                    user_data["custname"] = name  # 添加常见的表单字段名
                break
        
        # 地址匹配
        address_patterns = [
            r'(?:地址是|住在|居住在|地址)([^,，。]{5,50})',
        ]
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text)
            if matches:
                address = matches[0].strip()
                user_data["address"] = address
                break
        
        # 公司匹配
        company_patterns = [
            r'(?:公司是|工作在|就职于|公司)([^,，。]{2,30})',
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            if matches:
                company = matches[0].strip()
                user_data["company"] = company
                break
        
        # Pizza尺寸匹配
        size_patterns = [
            r'(?:披萨|pizza)(?:尺寸|大小|size)(?:是|选择|要|为)?(小号|中号|大号|small|medium|large)',
            r'(?:选择|要|想要)(?:小号|中号|大号|small|medium|large)(?:的)?(?:披萨|pizza)?',
            r'(?:尺寸|大小|size)(?:是|选择|要|为)?(小号|中号|大号|small|medium|large)',
            r'(小号|中号|大号|small|medium|large)(?:披萨|pizza|的披萨)?',
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                size_value = matches[0].strip().lower()
                # 标准化尺寸值
                size_mapping = {
                    '小号': 'small', '中号': 'medium', '大号': 'large',
                    'small': 'small', 'medium': 'medium', 'large': 'large'
                }
                if size_value in size_mapping:
                    user_data["size"] = size_mapping[size_value]
                    user_data["pizza_size"] = size_mapping[size_value]  # 备用字段名
                break
        
        # Pizza配料匹配
        toppings_patterns = [
            r'(?:配料|topping|toppings?)(?:是|要|选择|加)([^,，。]+)',
            r'(?:加|要|选择)(?:配料|topping)?([^,，。]*(?:培根|bacon|奶酪|cheese|洋葱|onion|蘑菇|mushroom)[^,，。]*)',
            r'(培根|bacon|奶酪|cheese|洋葱|onion|蘑菇|mushroom)(?:配料)?',
        ]
        
        toppings = []
        for pattern in toppings_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                topping_text = match.strip().lower()
                # 标准化配料名称
                topping_mapping = {
                    '培根': 'bacon', 'bacon': 'bacon',
                    '奶酪': 'cheese', 'cheese': 'cheese', 'extra cheese': 'cheese',
                    '洋葱': 'onion', 'onion': 'onion', 
                    '蘑菇': 'mushroom', 'mushroom': 'mushroom'
                }
                for key, value in topping_mapping.items():
                    if key in topping_text and value not in toppings:
                        toppings.append(value)
        
        if toppings:
            extracted["toppings"] = toppings
            # 不要重复添加 pizza_toppings，避免重复处理
            print(f"   🍕 提取Pizza配料: {toppings}")
        else:
            print(f"   ❌ 未找到Pizza配料")
        
        # 送达时间匹配
        delivery_time_patterns = [
            # 明确的时间格式
            r'(?:送达时间|delivery time|配送时间)(?:是|为|选择)?([0-9]{1,2}[:\：][0-9]{2})',
            r'(?:时间|time)(?:是|为|选择)?([0-9]{1,2}[:\：][0-9]{2})',
            r'([0-9]{1,2}[:\：][0-9]{2})(?:送达|配送)',
            
            # 简单时点表达
            r'(?:送达时间|delivery time|配送时间)(?:是|为|选择)?([0-9]{1,2}点)',
            r'(?:时间|time)(?:是|为|选择)?([0-9]{1,2}点)',
            r'([0-9]{1,2}点)(?:送达|配送)',
            r'(?:选择|要|在)([0-9]{1,2}点)',
            
            # 通用时间提取
            r'(?:送达时间|delivery time|配送时间)(?:是|为|选择)?([^,，。]+)',
        ]
        
        for pattern in delivery_time_patterns:
            matches = re.findall(pattern, text)
            if matches:
                time_value = matches[0].strip()
                
                # 标准化时间格式
                if "点" in time_value:
                    # 将"12点"转换为"12:00"
                    hour = re.findall(r'([0-9]{1,2})点', time_value)
                    if hour:
                        normalized_time = f"{hour[0]}:00"
                    else:
                        normalized_time = time_value
                elif "选择" in time_value:
                    # 去除"选择"等前缀词
                    clean_time = time_value.replace("选择", "").strip()
                    if "点" in clean_time:
                        hour = re.findall(r'([0-9]{1,2})点', clean_time)
                        if hour:
                            normalized_time = f"{hour[0]}:00"
                        else:
                            normalized_time = clean_time
                    else:
                        normalized_time = clean_time
                else:
                    normalized_time = time_value
                
                user_data["delivery_time"] = normalized_time
                user_data["preferred_delivery_time"] = normalized_time  # 添加这个字段以匹配实际网页
                break
        
        # 配送说明匹配
        delivery_instructions_patterns = [
            r'(?:配送说明|delivery instructions|送货说明)(?:是|为)?([^,，。]+)',
            r'(?:说明|instructions|备注|comments?)([^,，。]+)',
        ]
        
        for pattern in delivery_instructions_patterns:
            matches = re.findall(pattern, text)
            if matches:
                instructions = matches[0].strip()
                user_data["delivery_instructions"] = instructions
                # 不要重复添加 comments，避免重复处理
                break
        
        self.log(f"从文本'{text[:50]}...'中提取数据: {user_data}")
        return user_data
    
    def get_current_task_info(self) -> Optional[Dict[str, Any]]:
        """
        获取当前任务信息
        
        返回:
            任务信息字典或None
        """
        if not self.current_task:
            return None
        
        return {
            "task_id": self.current_task.task_id,
            "goal": self.current_task.goal,
            "target_url": self.current_task.target_url,
            "current_step": self.current_task.current_step,
            "total_steps": self.current_task.total_steps,
            "state": self.state.name,
            "has_page_analysis": self.current_task.page_analysis is not None
        }
    
    def log(self, message: str) -> None:
        """
        记录日志
        
        参数:
            message: 日志消息
        """
        if self.debug:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[ComputerAgent {timestamp}] {message}")
        
        log_entry = {
            "timestamp": time.time(),
            "message": message
        }
        self.logs.append(log_entry)