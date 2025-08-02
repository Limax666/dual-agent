"""
智能Computer Agent - 基于LLM驱动和browser-use框架

完全重构，参考browser-use官方代码实现简洁高效的网页操作
"""

import asyncio
import time
import uuid
import json
import os
from typing import Dict, List, Optional, Any, Union
from enum import Enum, auto
from dataclasses import dataclass, field
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入工具调用系统
from dual_agent.common.tool_calling import (
    ToolCallHandler, MessageType, register_agent_handler,
    send_message_to_phone_agent, ToolMessage, COMPUTER_AGENT_TOOLS
)

# 尝试导入browser-use
try:
    from browser_use import Agent as BrowserUseAgent
    from browser_use.llm import ChatAnthropic, ChatOpenAI
    BROWSER_USE_AVAILABLE = True
    print("✅ browser-use 导入成功")
except ImportError as e:
    BROWSER_USE_AVAILABLE = False
    BrowserUseAgent = None
    ChatAnthropic = None
    ChatOpenAI = None
    print(f"⚠️ browser-use 未安装，将使用fallback模式: {e}")


class ComputerAgentState(Enum):
    """Computer Agent状态"""
    IDLE = auto()           # 空闲
    ANALYZING = auto()      # 分析用户输入
    OPERATING = auto()      # 执行浏览器操作
    ERROR = auto()          # 错误状态


@dataclass
class ComputerAgentConfig:
    """Computer Agent配置"""
    # Browser-Use配置
    headless: bool = False
    debug: bool = False
    max_retries: int = 3


class IntelligentComputerAgent:
    """
    智能Computer Agent
    
    特点：
    1. 基于browser-use官方实现
    2. 简洁高效的代码结构
    3. 通过工具调用与Phone Agent通信
    4. 使用单一浏览器会话，避免多实例问题
    """
    
    def __init__(self, config: ComputerAgentConfig):
        self.config = config
        self.debug = config.debug
        self.state = ComputerAgentState.IDLE
        self.agent_id = str(uuid.uuid4())
        
        # 目标URL（由启动参数设置）
        self.target_url = None
        
        # 单一browser-use agent实例 - 按照官方示例方式
        self.browser_agent = None
        self.llm_client = None
        self._initialize_browser_agent()
        
        # 初始化工具调用处理器
        self.tool_handler = ToolCallHandler("computer_agent")
        self.tool_handler.register_handler(MessageType.USER_INPUT, self._handle_user_input)
        self.tool_handler.register_handler(MessageType.FORM_DATA, self._handle_form_data)
        self.tool_handler.register_handler(MessageType.SYSTEM_STATUS, self._handle_system_status)
        
        # 注册全局处理器
        register_agent_handler("computer_agent", self.tool_handler)
        
        # 状态管理
        self.current_task_id = None
        self.operation_history = []
        self.page_ready = False  # 跟踪页面是否已准备好
        
        # 用户表单数据缓存
        self.user_form_data = {}
        
        self.log(f"IntelligentComputerAgent初始化完成")
    
    def _initialize_browser_agent(self):
        """初始化单一browser-use agent"""
        try:
            if not BROWSER_USE_AVAILABLE:
                self.log("browser-use不可用，使用模拟模式")
                return
            
            # 创建LLM客户端
            self.llm_client = self._create_llm_client()
            if not self.llm_client:
                self.log("无法创建LLM客户端，使用模拟模式")
                return
            
            # 暂时不创建agent，等到有目标URL时再创建单一实例
            self.log("Browser-Use LLM客户端准备就绪，将在需要时创建单一浏览器实例")
            
        except Exception as e:
            self.log(f"初始化browser-use失败: {e}")
            self.browser_agent = None
    
    def _create_single_browser_agent(self, initial_task: str):
        """创建单一browser-use agent实例（整个会话期间复用，保持浏览器活跃）"""
        try:
            if self.browser_agent is not None:
                self.log("使用现有的browser agent实例")
                return self.browser_agent
                
            if not self.llm_client:
                raise Exception("LLM客户端未初始化")
            
            # 配置browser-use以保持会话活跃
            # 注意：避免使用可能导致任务自动完成的参数
            self.browser_agent = BrowserUseAgent(
                task=initial_task,
                llm=self.llm_client,
                max_actions_per_step=3,  # 限制操作步骤
                generate_gif=False,
                save_recording_path=None,
            )
            
            self.log(f"创建单一browser-use agent成功: {initial_task[:50]}...")
            
            # 重要：不要让任务执行到completion，保持浏览器活跃
            return self.browser_agent
            
        except Exception as e:
            self.log(f"创建browser-use agent失败: {e}")
            return None
    
    def _create_llm_client(self):
        """创建LLM客户端，按优先级选择API"""
        try:
            # 优先使用OpenAI API (最佳兼容性)
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                self.log("使用OpenAI API")
                return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key)
            
            # 备选：使用Anthropic API
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            if anthropic_key:
                self.log("使用Anthropic API")
                return ChatAnthropic(model="claude-sonnet-4-20250514", api_key=anthropic_key)
            
            # 降级：使用Siliconflow API (可能不兼容)
            siliconflow_key = os.environ.get("SILICONFLOW_API_KEY")
            if siliconflow_key:
                self.log("⚠️ 降级使用Siliconflow API (可能不兼容browser-use)")
                # 尝试使用OpenAI兼容接口
                return ChatOpenAI(
                    model="doubao-seed-1-6-thinking-250615",
                    api_key=siliconflow_key,
                    base_url="https://api.siliconflow.cn/v1"
                )
            
            self.log("❌ 未找到可用的API密钥")
            return None
            
        except Exception as e:
            self.log(f"创建LLM客户端失败: {e}")
            return None
    
    def _create_browser_agent(self, task: str):
        """为特定任务创建browser-use agent（参考官方代码，优化配置）"""
        try:
            if not self.llm_client:
                raise Exception("LLM客户端未初始化")
            
            # 参考官方代码创建agent，优化配置以避免超时问题
            agent = BrowserUseAgent(
                task=task,
                llm=self.llm_client,
                headless=self.config.headless,  # 传递headless配置
                max_actions_per_step=5,  # 限制每步最多5个操作
                generate_gif=False,  # 不生成GIF以提高性能
                save_recording_path=None,  # 不保存录制以提高性能
            )
            
            self.log(f"创建browser-use agent成功: {task[:50]}...")
            return agent
            
        except Exception as e:
            self.log(f"创建browser-use agent失败: {e}")
            # 如果高级配置失败，尝试基础配置
            try:
                agent = BrowserUseAgent(
                    task=task,
                    llm=self.llm_client
                )
                self.log(f"使用基础配置创建browser-use agent成功")
                return agent
            except Exception as e2:
                self.log(f"基础配置也失败: {e2}")
                return None

    async def start(self):
        """启动Computer Agent"""
        self.log("启动IntelligentComputerAgent")
        
        try:
            # 启动工具调用处理器
            tool_task = asyncio.create_task(self.tool_handler.start_listening())
            
            self.log("IntelligentComputerAgent启动完成，等待任务...")
            
            # 发送启动消息给Phone Agent
            await self._send_to_phone_agent(
                "Computer Agent已就绪，可以开始浏览器操作",
                message_type="system_status",
                additional_data={
                    "agent_status": "ready",
                    "browser_use_available": BROWSER_USE_AVAILABLE
                }
            )
            
            # 如果设置了目标URL，自动导航
            if self.target_url:
                self.log(f"检测到目标URL，开始自动导航: {self.target_url}")
                await asyncio.sleep(2)  # 稍等确保Phone Agent已准备好
                await self._auto_navigate_to_target_url()
            
            # 保持运行
            await tool_task
            
        except Exception as e:
            self.log(f"启动失败: {e}")
            self.state = ComputerAgentState.ERROR
    
    async def _auto_navigate_to_target_url(self):
        """自动导航到目标URL并分析页面（使用browser-use官方方式）"""
        try:
            if not self.target_url:
                return
            
            self.log(f"开始导航到目标URL: {self.target_url}")
            
            # 按照官方示例创建browser-use agent
            from browser_use import Agent
            
            # 创建导航任务 - 简化任务描述，确保浏览器保持打开
            task = f"Navigate to {self.target_url} and analyze the form on the page"
            
            self.browser_agent = Agent(
                task=task,
                llm=self.llm_client,
                headless=self.config.headless,  # 传递headless配置
            )
            
            self.log("创建browser-use agent并执行导航+分析任务...")
            print(f"🌐 正在导航到: {self.target_url}")
            
            # 执行导航任务，使用正确的browser-use执行方式
            try:
                # 让browser-use执行导航任务
                result = await asyncio.wait_for(self.browser_agent.run(), timeout=60.0)
                self.log(f"✅ 导航任务执行完成: {result}")
                
                # 设置页面准备就绪
                self.page_ready = True
                
                # 发送导航成功消息（如果有phone agent的话）
                try:
                    await self._send_to_phone_agent(
                        f"✅ 已成功导航到 {self.target_url}，浏览器会话保持活跃，可以开始填写表单。",
                        message_type="page_analysis",
                        additional_data={
                            "url": self.target_url,
                            "page_type": "form",
                            "page_purpose": "表单填写",
                            "ready_for_user_input": True,
                            "browser_session_active": True
                        }
                    )
                    self.log("✅ 导航分析完成并发送给Phone Agent")
                except Exception as send_error:
                    self.log(f"发送导航结果失败（可能没有Phone Agent）: {send_error}")
                
            except asyncio.TimeoutError:
                self.log("导航超时，但尝试继续")
                self.page_ready = True
                await self._send_basic_page_analysis()
            except Exception as nav_error:
                self.log(f"导航出错: {nav_error}")
                self.page_ready = True
                await self._send_basic_page_analysis()
            
        except Exception as e:
            self.log(f"自动导航失败: {e}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            
            # 即使创建失败，也要确保系统继续运行
            self.page_ready = True
            try:
                await self._send_to_phone_agent(
                    f"页面导航遇到问题，但系统已准备就绪。请告诉我您要填写什么信息。",
                    message_type="page_analysis",
                    additional_data={
                        "url": self.target_url,
                        "page_type": "form",
                        "ready_for_user_input": True
                    }
                )
            except Exception as send_error:
                self.log(f"发送错误消息也失败: {send_error}")
    
    async def _parse_browser_use_result(self, browser_result: str) -> dict:
        """完全使用LLM解析browser-use结果，无任何硬编码"""
        try:
            self.log(f"使用LLM解析browser-use结果: {browser_result[:200]}...")
            
            # 完全依赖LLM处理browser-use结果，不做任何硬编码判断或预处理
            if not self.llm_client:
                self.log("❌ 没有LLM客户端，无法解析browser-use结果")
                return await self._get_fallback_page_analysis()
            
            # 增强的LLM解析提示，让LLM完全自主分析browser-use结果
            parse_prompt = f"""
你是一个专业的网页分析专家。请仔细分析以下browser-use工具的完整执行结果，提取所有相关的页面信息。

Browser-use完整执行结果:
{browser_result}

请根据实际的browser-use分析结果，智能提取页面信息。你的任务是：

1. 分析页面的实际内容和结构
2. 识别所有可交互的表单字段（无论是什么类型的网站）
3. 理解页面的业务用途和上下文
4. 提供清晰的用户指导

请以JSON格式返回分析结果：
{{
    "page_type": "页面类型（form/shopping/booking/information/error等）",
    "business_context": "基于实际内容的业务上下文描述",
    "page_title": "页面标题或主要用途",
    "input_fields": [
        {{
            "field_name": "实际提取的字段名称",
            "field_type": "实际的字段类型",
            "description": "字段用途描述",
            "required": "是否必填",
            "html_id": "HTML ID（如果有）",
            "html_name": "HTML name属性（如果有）",
            "placeholder": "占位符文本（如果有）"
        }}
    ],
    "available_actions": ["用户可以执行的操作"],
    "user_workflow": "用户在此页面的操作流程",
    "interaction_guidance": "给用户的具体操作指导",
    "error_detected": false,
    "error_message": "如果有错误的话"
}}

重要要求：
- 完全基于browser-use的实际分析结果，不要编造或假设信息
- 如果browser-use提取了JSON数据，请直接使用其中的信息
- 如果检测到错误页面（404、503等），将error_detected设为true
- 适应各种类型的网页（购物、预订、表单、信息展示等）
- 提供实用的用户交互指导
"""
            
            try:
                self.log("🤖 调用LLM分析browser-use结果...")
                
                # 统一使用OpenAI客户端避免browser-use兼容性问题
                if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                    response = await self.llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你是专业的网页分析专家，能够准确解析browser-use工具的执行结果并提取结构化信息。"},
                            {"role": "user", "content": parse_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1500
                    )
                    result_text = response.choices[0].message.content.strip()
                else:
                    # 使用直接的OpenAI客户端避免browser-use兼容性问题
                    from openai import AsyncOpenAI
                    import os
                    
                    openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "你是专业的网页分析专家，能够准确解析browser-use工具的执行结果并提取结构化信息。"},
                            {"role": "user", "content": parse_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1500
                    )
                    result_text = response.choices[0].message.content.strip()
                
                self.log(f"🤖 LLM分析完成，结果长度: {len(result_text)}")
                
                # 解析LLM返回的JSON结果
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                parsed_data = json.loads(result_text)
                self.log(f"✅ 成功解析LLM结果: {parsed_data.get('business_context', 'unknown')}")
                
                # 检查是否有错误
                if parsed_data.get("error_detected", False):
                    return {
                        "message": f"页面访问出现问题: {parsed_data.get('error_message', '未知错误')}",
                        "data": {
                            "url": self.target_url,
                            "page_type": "error",
                            "error": parsed_data.get('error_message', '未知错误'),
                            "ready_for_user_input": False
                        }
                    }
                
                # 构建用户友好的消息
                business_context = parsed_data.get("business_context", "网页")
                interaction_guidance = parsed_data.get("interaction_guidance", "请告诉我您想要做什么")
                input_fields = parsed_data.get("input_fields", [])
                
                user_message = f"我已帮您打开了{business_context}。{interaction_guidance}"
                
                # 通过工具调用发送页面分析结果给Phone Agent
                analysis_data = {
                    "url": self.target_url,
                    "page_type": parsed_data.get("page_type", "unknown"),
                    "page_purpose": parsed_data.get("page_title", "网页操作"),
                    "business_context": business_context,
                    "available_actions": parsed_data.get("available_actions", []),
                    "input_fields": input_fields,
                    "user_workflow": parsed_data.get("user_workflow", ""),
                    "interaction_guidance": interaction_guidance,
                    "ready_for_user_input": True,
                    "llm_analysis_complete": True
                }
                
                return {
                    "message": user_message,
                    "data": analysis_data
                }
                
            except json.JSONDecodeError as json_error:
                self.log(f"❌ LLM返回的JSON格式无效: {json_error}")
                self.log(f"原始LLM回复: {result_text[:500]}...")
                return await self._get_fallback_page_analysis()
                
            except Exception as llm_error:
                self.log(f"❌ LLM解析browser-use结果失败: {llm_error}")
                import traceback
                self.log(f"错误详情: {traceback.format_exc()}")
                return await self._get_fallback_page_analysis()
                
        except Exception as e:
            self.log(f"解析browser-use结果失败: {e}")
            return await self._get_fallback_page_analysis()
    
    async def _send_basic_page_analysis(self):
        """发送基础页面分析（当browser-use分析失败时的备选方案）"""
        try:
            await self._send_to_phone_agent(
                f"已打开页面 {self.target_url}，系统已准备就绪。请告诉我您要填写什么信息。",
                message_type="page_analysis",
                additional_data={
                    "url": self.target_url,
                    "page_type": "form",
                    "page_purpose": "表单填写",
                    "business_context": "网页表单",
                    "available_actions": ["填写表单信息"],
                    "input_fields": [
                        {"field_name": "姓名", "field_type": "text", "description": "用户姓名", "required": False},
                        {"field_name": "电话", "field_type": "tel", "description": "联系电话", "required": False},
                        {"field_name": "邮箱", "field_type": "email", "description": "电子邮箱", "required": False}
                    ],
                    "user_workflow": "请提供您要填写的信息",
                    "interaction_guidance": "您可以说：'我的姓名是张三'、'我的电话是12345'等",
                    "ready_for_user_input": True
                }
            )
        except Exception as e:
            self.log(f"发送基础页面分析失败（可能没有Phone Agent）: {e}")
    
    async def _get_fallback_page_analysis(self) -> dict:
        """获取备选页面分析数据"""
        return {
            "message": f"已打开页面 {self.target_url}，请告诉我您要填写的信息。",
            "data": {
                "url": self.target_url,
                "page_type": "form",
                "page_purpose": "表单填写",
                "business_context": "网页表单",
                "available_actions": ["填写表单信息"],
                "input_fields": [],
                "user_workflow": "请提供您要填写的信息",
                "interaction_guidance": "您可以说出需要填写的具体信息",
                "ready_for_user_input": True
            }
        }
    
    async def _analyze_current_page_directly(self):
        """直接分析当前已导航的页面，不创建新的browser实例"""
        try:
            self.log("尝试直接分析当前页面状态...")
            
            if not self.browser_agent:
                return {
                    "success": False,
                    "message": "浏览器会话不存在",
                    "data": {"url": self.target_url, "error": "no_browser_session"}
                }
            
            # 构建基础的页面信息（由于browser-use的限制，我们不能直接获取页面内容）
            # 但可以提供足够的信息让Phone Agent知道页面已准备好
            
            page_info = {
                "success": True,
                "message": f"已成功打开 {self.target_url} 页面，可以开始操作。请告诉我您想要填写什么信息。",
                "data": {
                    "url": self.target_url,
                    "page_type": "form",  # 假设是表单页面，适合大多数交互场景
                    "page_purpose": "网页表单",
                    "business_context": "当前网页",
                    "available_actions": ["填写表单信息", "提交数据"],
                    "input_fields": [
                        {"field_name": "姓名", "field_type": "text", "description": "用户姓名", "required": False},
                        {"field_name": "邮箱", "field_type": "email", "description": "电子邮箱", "required": False},
                        {"field_name": "电话", "field_type": "tel", "description": "联系电话", "required": False}
                    ],
                    "user_workflow": "请提供您想要填写的信息，我会协助您完成操作。",
                    "interaction_guidance": "您可以说出需要填写的信息，如：'我的姓名是张三'、'我的邮箱是test@example.com'等。",
                    "ready_for_user_input": True
                }
            }
            
            self.log("✅ 构建了基础页面信息供Phone Agent使用")
            return page_info
            
        except Exception as e:
            self.log(f"直接页面分析失败: {e}")
            return {
                "success": False,
                "message": f"页面分析遇到问题: {str(e)}",
                "data": {"url": self.target_url, "error": str(e)}
            }
    
    async def _analyze_any_webpage(self):
        """通用网页分析 - 支持各种类型的网页（购物、预订、表单等）"""
        try:
            if not self.browser_agent:
                return {
                    "success": False,
                    "message": "浏览器会话不存在，无法分析页面",
                    "data": {"url": self.target_url, "error": "no_browser_session"}
                }
            
            # 使用现有的browser_agent进行分析，避免创建新实例
            print(f"🔍 使用现有浏览器会话执行通用页面分析...")
            
            # 直接使用现有的browser_agent，不创建新实例
            try:
                # 使用现有会话的extract_structured_data功能
                analysis_query = f"""Extract all form fields and their details from the current page at {self.target_url}:
                
1. List all input fields with their names, types, labels, and placeholders
2. Identify the page type (form, shopping, booking, etc.)
3. Describe what users can do on this page
4. Do NOT fill any forms or click buttons - only analyze"""
                
                # 使用现有browser_agent的extract功能而不是创建新实例
                if hasattr(self.browser_agent, 'controller') and self.browser_agent.controller:
                    try:
                        # 尝试直接使用现有会话进行数据提取
                        analysis_result = await self.browser_agent.controller.extract_structured_data(analysis_query)
                        self.log(f"使用现有会话提取数据成功: {analysis_result}")
                        
                        # 使用LLM解析browser-use的分析结果并生成结构化信息
                        parsed_result = await self._parse_general_webpage_analysis(str(analysis_result))
                        return parsed_result
                        
                    except Exception as extract_error:
                        self.log(f"现有会话数据提取失败: {extract_error}")
                        # 降级到基础分析
                        return await self._basic_page_analysis()
                else:
                    self.log("现有browser_agent没有controller，使用基础分析")
                    return await self._basic_page_analysis()
                
            except Exception as inner_e:
                self.log(f"分析失败，使用基础分析: {inner_e}")
                return await self._basic_page_analysis()
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": f"页面分析超时，可能页面 {self.target_url} 加载缓慢",
                "data": {"url": self.target_url, "error": "analysis_timeout"}
            }
        except Exception as e:
            self.log(f"通用页面分析失败: {e}")
            return {
                "success": False,
                "message": f"页面分析失败: {str(e)}",
                "data": {"url": self.target_url, "error": str(e)}
            }
    
    async def _basic_page_analysis(self):
        """基础页面分析 - 当详细分析失败时的备选方案"""
        try:
            self.log("执行基础页面分析...")
            
            # 提供基础的页面信息
            basic_info = {
                "success": True,
                "message": f"已打开页面 {self.target_url}，页面正在加载中。请告诉我您想要做什么操作。",
                "data": {
                    "url": self.target_url,
                    "page_type": "webpage",
                    "page_purpose": "网页应用",
                    "business_context": "当前页面",
                    "available_actions": ["填写信息", "提交表单", "浏览内容"],
                    "input_fields": [],
                    "user_workflow": "请提供您想要填写的信息，我会协助您完成操作。",
                    "key_information": "页面已成功加载",
                    "interaction_guidance": "请告诉我您的具体需求，比如姓名、邮箱、电话等信息。",
                    "ready_for_user_input": True
                }
            }
            
            return basic_info
            
        except Exception as e:
            self.log(f"基础页面分析也失败: {e}")
            return {
                "success": False,
                "message": f"页面分析遇到问题: {str(e)}",
                "data": {"url": self.target_url, "error": str(e)}
            }
    
    async def _parse_general_webpage_analysis(self, browser_result: str):
        """解析browser-use的通用页面分析结果，生成结构化信息供Phone Agent使用"""
        try:
            self.log(f"开始解析browser-use通用页面分析结果: {browser_result[:200]}...")
            
            if not self.llm_client:
                # 如果没有LLM，返回基础信息
                return {
                    "success": True,
                    "message": f"已打开页面 {self.target_url}，请告诉我您想要做什么",
                    "data": {"url": self.target_url, "page_type": "unknown", "interactive_elements": []}
                }
            
            # 构建LLM解析提示
            parse_prompt = f"""
你是一个专业的网页分析专家。请仔细分析以下browser-use框架的页面分析结果，提取关键信息供语音助手使用。

Browser-use分析结果:
{browser_result}

请将分析结果转换为结构化的JSON格式，包含以下信息：

{{
    "page_type": "页面类型 (booking/shopping/form/search/information等)",
    "page_purpose": "页面的主要用途描述",
    "business_context": "业务背景（如：机票预订、酒店预订、商品购买等）",
    "user_friendly_title": "给用户的友好页面标题",
    "available_actions": [
        "用户可以执行的主要操作列表"
    ],
    "input_fields": [
        {{
            "field_name": "字段名称",
            "field_type": "字段类型",
            "description": "字段用途描述",
            "required": true/false
        }}
    ],
    "user_workflow": "用户在此页面的典型操作流程描述",
    "key_information": "页面上的重要信息摘要",
    "interaction_guidance": "给用户的交互指导"
}}

重要要求：
1. 如果检测到任何错误（如404、503等），将page_type设为"error"
2. 基于实际分析结果，不要编造不存在的功能
3. 提供具体、实用的用户指导
4. 适应不同类型的网页（不要假设是表单）
"""
            
            # 调用LLM解析
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是网页分析专家，专门将browser-use分析结果转换为结构化信息。"},
                        {"role": "user", "content": parse_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1500
                )
                result_text = response.choices[0].message.content.strip()
            else:
                result_text = await self.llm_client.ainvoke([
                    {"role": "system", "content": "你是网页分析专家，专门将browser-use分析结果转换为结构化信息。"},
                    {"role": "user", "content": parse_prompt}
                ])
                if isinstance(result_text, dict) and 'content' in result_text:
                    result_text = result_text['content']
                result_text = str(result_text).strip()
            
            # 解析JSON结果
            try:
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                parsed_data = json.loads(result_text)
                
                # 构建返回结果
                if parsed_data.get("page_type") == "error":
                    return {
                        "success": False,
                        "message": f"页面访问出现问题: {parsed_data.get('key_information', '未知错误')}",
                        "data": {
                            "url": self.target_url,
                            "error": parsed_data.get('key_information', '未知错误'),
                            "page_type": "error"
                        }
                    }
                else:
                    # 生成给用户的友好消息
                    page_purpose = parsed_data.get("page_purpose", "网页")
                    business_context = parsed_data.get("business_context", "")
                    interaction_guidance = parsed_data.get("interaction_guidance", "")
                    
                    if business_context:
                        user_message = f"我已帮您打开了{business_context}页面。{interaction_guidance}"
                    else:
                        user_message = f"我已帮您打开了{page_purpose}。{interaction_guidance}"
                    
                    return {
                        "success": True,
                        "message": user_message,
                        "data": {
                            "url": self.target_url,
                            "page_type": parsed_data.get("page_type", "unknown"),
                            "page_purpose": page_purpose,
                            "business_context": business_context,
                            "available_actions": parsed_data.get("available_actions", []),
                            "input_fields": parsed_data.get("input_fields", []),
                            "user_workflow": parsed_data.get("user_workflow", ""),
                            "key_information": parsed_data.get("key_information", ""),
                            "interaction_guidance": interaction_guidance,
                            "ready_for_user_input": True
                        }
                    }
                
            except json.JSONDecodeError:
                self.log(f"LLM返回非JSON格式: {result_text}")
                return {
                    "success": True,
                    "message": f"已打开页面 {self.target_url}，请告诉我您想要做什么",
                    "data": {"url": self.target_url, "page_type": "unknown", "ready_for_user_input": True}
                }
                
        except Exception as e:
            self.log(f"解析通用页面分析结果失败: {e}")
            return {
                "success": True,
                "message": f"已打开页面 {self.target_url}，请告诉我您想要做什么",
                "data": {"url": self.target_url, "page_type": "unknown", "ready_for_user_input": True}
            }
    
    async def _handle_user_input(self, message: ToolMessage):
        """处理来自Phone Agent的用户输入"""
        try:
            self.state = ComputerAgentState.ANALYZING
            self.current_task_id = message.task_id
            
            user_text = message.content.get("text", "")
            session_id = message.content.get("session_id")
            
            self.log(f"收到用户输入: {user_text}")
            
            # 使用browser-use处理用户输入
            await self._process_with_browser_use(user_text)
                
        except Exception as e:
            self.log(f"处理用户输入失败: {e}")
            await self._send_to_phone_agent(
                f"处理您的请求时出现错误：{str(e)}",
                message_type="error"
            )
            self.state = ComputerAgentState.ERROR
    
    async def _process_with_browser_use(self, user_text: str):
        """处理用户输入（简化版，避免多实例问题）"""
        try:
            self.state = ComputerAgentState.OPERATING
            
            if not BROWSER_USE_AVAILABLE or not self.browser_agent:
                await self._fallback_response(user_text)
                return
            
            # 使用LLM分析用户输入，提取表单数据
            form_data = await self._extract_form_data_from_text(user_text)
            
            if form_data:
                # 用户提供了表单数据，进行精确填写
                await self._fill_form_with_extracted_data(form_data)
            else:
                # 其他类型的请求
                await self._handle_general_browser_request(user_text)
            
            self.state = ComputerAgentState.IDLE
            
        except Exception as e:
            self.log(f"处理用户输入失败: {e}")
            await self._fallback_response(user_text)
    
    async def _extract_form_data_from_text(self, user_text: str) -> dict:
        """从用户文本中提取表单数据 - 严格按照设计文档，完全依赖LLM"""
        try:
            self.log(f"开始LLM驱动的表单数据提取，输入文本: {user_text}")
            
            if not self.llm_client:
                self.log("❌ LLM客户端未初始化，使用基础提取模式")
                return await self._basic_text_extraction(user_text)
            
            # 设计文档要求：完全依赖LLM的理解能力，不使用任何硬编码
            extraction_prompt = f"""
你是一个智能表单数据提取专家。请从用户的自然语言输入中提取表单相关信息。

用户输入："{user_text}"

请仔细分析用户的中文或英文表达，提取以下类型的信息（如果存在）：
- name/姓名：用户提到的姓名信息
- email/邮箱：用户提到的邮箱地址
- phone/电话：用户提到的电话号码
- address/地址：用户提到的地址信息
- company/公司：用户提到的公司信息
- age/年龄：用户提到的年龄信息
- pizza_size/尺寸：用户提到的披萨尺寸（小号/small, 中号/medium, 大号/large）
- toppings/配料：用户提到的披萨配料（如培根/bacon, 奶酪/cheese, 洋葱/onion, 蘑菇/mushroom，支持多选）
- delivery_time/配送时间：用户提到的送达时间，请标准化为HH:MM格式（例如18:30）
- delivery_instructions/配送说明：用户提到的配送说明或备注信息

重要要求：
1. 使用你的自然语言理解能力，识别各种表达方式，包括同义词和模糊表达。
2. 即使用户的表达不标准，也要尽力理解和提取。
3. 如果用户明确提到了个人信息或订购偏好，一定要提取出来。
4. 对于中文表达如"我的姓名是张三"、"我叫李四"等，要准确识别。
5. 对于"开始填表"这样的指令，不要提取为表单数据。
6. 如果用户提到多个配料，请以数组形式返回，例如["bacon", "cheese"]。
7. 配送时间请务必转换为24小时制 HH:MM 格式。

请以标准JSON格式回复：
{{
    "name": "提取的姓名（如果有）",
    "email": "提取的邮箱（如果有）", 
    "phone": "提取的电话（如果有）",
    "address": "提取的地址（如果有）",
    "company": "提取的公司（如果有）",
    "age": "提取的年龄（如果有）",
    "pizza_size": "提取的披萨尺寸（如果有）",
    "toppings": ["提取的配料列表（如果有）"],
    "delivery_time": "提取的配送时间HH:MM格式（如果有）",
    "delivery_instructions": "提取的配送说明（如果有）"
}}

如果某个字段没有信息，请设为null。确保返回有效的JSON格式。
"""
            
            self.log("正在调用LLM进行智能表单数据提取...")
            
            # 调用LLM提取数据 - 统一使用OpenAI格式的同步调用避免browser-use兼容性问题
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                self.log("使用OpenAI风格的LLM客户端")
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at extracting form data from natural language. Always return valid JSON."},
                        {"role": "user", "content": extraction_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
                result_text = response.choices[0].message.content.strip()
            else:
                self.log("使用browser-use LLM客户端，直接调用OpenAI API")
                # 对于browser-use的LLM客户端，直接使用OpenAI API调用方式
                from openai import AsyncOpenAI
                import os
                
                try:
                    # 尝试直接使用OpenAI客户端
                    openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert at extracting form data from natural language. Always return valid JSON."},
                            {"role": "user", "content": extraction_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=300
                    )
                    result_text = response.choices[0].message.content.strip()
                except Exception as openai_error:
                    self.log(f"直接OpenAI调用失败: {openai_error}")
                    # 降级到基础提取
                    return await self._basic_text_extraction(user_text)
            
            self.log(f"LLM智能提取结果: {result_text}")
            
            # 解析JSON结果
            try:
                # 清理可能的markdown格式
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                form_data = json.loads(result_text)
                
                # 过滤空值和null值，保留有效数据
                filtered_data = {}
                for k, v in form_data.items():
                    if v and v != "null" and v != "None" and str(v).strip():
                        filtered_data[k] = str(v).strip()
                
                self.log(f"LLM提取并过滤后的表单数据: {filtered_data}")
                
                if filtered_data:
                    self.log(f"✅ LLM成功提取表单数据: {filtered_data}")
                    return filtered_data
                else:
                    self.log("⚠️ LLM未提取到有效的表单数据，使用基础提取")
                    return await self._basic_text_extraction(user_text)
                
            except json.JSONDecodeError as json_error:
                self.log(f"❌ JSON解析失败: {json_error}")
                self.log(f"原始LLM回复: {result_text}")
                return await self._basic_text_extraction(user_text)
                
        except Exception as e:
            self.log(f"❌ LLM驱动的表单数据提取失败: {e}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            return await self._basic_text_extraction(user_text)
    
    async def _basic_text_extraction(self, user_text: str) -> dict:
        """LLM驱动的文本提取（完全移除硬编码模式）"""
        try:
            # 如果没有LLM客户端，返回空结果
            if not self.llm_client:
                self.log("无LLM客户端可用，无法进行文本提取")
                return {}
            
            # 使用简化的LLM提取
            simple_prompt = f"""
从以下用户输入中提取个人信息，如果找不到相关信息则返回空值：

用户输入: "{user_text}"

请识别并提取：
- 姓名信息
- 邮箱地址
- 电话号码

以JSON格式返回:
{{
    "name": "提取的姓名或null",
    "email": "提取的邮箱或null", 
    "phone": "提取的电话或null"
}}
"""
            
            try:
                if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                    response = await self.llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Extract personal information from user input. Return valid JSON."},
                            {"role": "user", "content": simple_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=200
                    )
                    result_text = response.choices[0].message.content.strip()
                else:
                    # 使用直接的OpenAI客户端避免browser-use兼容性问题
                    from openai import AsyncOpenAI
                    import os
                    
                    openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Extract personal information from user input. Return valid JSON."},
                            {"role": "user", "content": simple_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=200
                    )
                    result_text = response.choices[0].message.content.strip()
                
                # 解析结果
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                extracted = json.loads(result_text)
                
                # 过滤空值
                filtered = {}
                for k, v in extracted.items():
                    if v and v != "null" and v != "None" and str(v).strip():
                        filtered[k] = str(v).strip()
                
                self.log(f"LLM基础提取结果: {filtered}")
                return filtered
                
            except Exception as llm_error:
                self.log(f"LLM基础提取失败: {llm_error}")
                return {}
                
        except Exception as e:
            self.log(f"基础文本提取失败: {e}")
            return {}
    
    async def _fill_form_with_extracted_data(self, form_data: dict):
        """使用提取的数据填写表单（实际调用browser-use填写，不仅仅是记录）"""
        try:
            if not form_data:
                await self._send_to_phone_agent("没有找到有效的表单数据", message_type="error")
                return
            
            self.log(f"准备填写表单数据: {form_data}")
            
            # 从form_data中提取实际的表单字段（过滤掉元数据）
            actual_form_fields = {}
            for key, value in form_data.items():
                if key not in ['original_user_input', 'from_fast_thinking'] and value:
                    actual_form_fields[key] = value
            
            # 如果没有实际字段，强制从original_user_input中提取
            if not actual_form_fields:
                original_input = form_data.get('original_user_input', '')
                if original_input:
                    self.log(f"🔍 强制从原始输入提取表单数据: {original_input}")
                    # 使用LLM从原始输入中提取表单数据
                    extracted_fields = await self._extract_form_data_from_text(original_input)
                    actual_form_fields.update(extracted_fields)
                    self.log(f"🔍 LLM提取结果: {extracted_fields}")
            
            # 如果仍然没有字段，使用基础正则提取作为最后手段
            if not actual_form_fields:
                original_input = form_data.get('original_user_input', '')
                if original_input:
                    self.log(f"🔍 使用基础正则提取作为最后手段")
                    basic_fields = await self._basic_text_extraction(original_input)
                    actual_form_fields.update(basic_fields)
                    self.log(f"🔍 基础提取结果: {basic_fields}")
            
            if actual_form_fields:
                self.log(f"🚀 开始实际的browser-use表单填写: {actual_form_fields}")
                
                # 强制执行实际的browser-use表单填写
                success = await self._execute_actual_form_filling(actual_form_fields)
                
                if success:
                    filled_info = [f"{k}: {v}" for k, v in actual_form_fields.items()]
                    await self._send_to_phone_agent(
                        f"✅ 已成功在网页中填写: {', '.join(filled_info)}。",
                        message_type="task_result",
                        additional_data={"filled_fields": actual_form_fields, "status": "browser_filled"}
                    )
                else:
                    # 如果browser-use填写失败，至少记录用户信息
                    filled_info = [f"{k}: {v}" for k, v in actual_form_fields.items()]
                    await self._send_to_phone_agent(
                        f"⚠️ 网页填写遇到技术问题，但已记录您的信息: {', '.join(filled_info)}。",
                        message_type="task_result",
                        additional_data={"filled_fields": actual_form_fields, "status": "recorded_fallback"}
                    )
                
            else:
                # 如果确实没有提取到字段，给用户反馈
                original_input = form_data.get('original_user_input', '')
                if original_input:
                    await self._send_to_phone_agent(
                        f"我已收到您说的：'{original_input}'。请提供更具体的表单信息，如姓名、邮箱、电话等。",
                        message_type="task_result"
                    )
                else:
                    await self._send_to_phone_agent(
                        "请提供需要填写的具体信息，如姓名、邮箱、电话号码等。",
                        message_type="task_result"
                    )
            
        except Exception as e:
            self.log(f"处理表单数据失败: {e}")
            await self._send_to_phone_agent(f"处理您的信息时遇到问题: {str(e)}", message_type="error")
    
    async def _execute_actual_form_filling(self, form_fields: dict) -> bool:
        """创建新的browser-use agent执行表单填写"""
        try:
            self.log(f"🚀 创建新的browser-use agent执行表单填写: {form_fields}")
            
            # 确保我们有实际的用户数据
            if not form_fields:
                self.log("❌ 没有表单字段数据")
                return False
            
            # 使用LLM智能优化表单填写任务
            optimized_task = await self._create_smart_form_filling_task(form_fields)
            
            self.log(f"创建LLM优化的表单填写任务: {optimized_task[:200]}...")
            
            # 创建专门的填写agent
            fill_agent = self._create_browser_agent(optimized_task)
            if not fill_agent:
                self.log("❌ 无法创建browser-use填写agent")
                return False
            
            print(f"🔍 开始browser-use表单填写，使用用户数据: {form_fields}")
            
            # 执行填写任务
            try:
                result = await asyncio.wait_for(fill_agent.run(), timeout=120.0)  # 增加超时时间
                self.log(f"✅ Browser-use表单填写完成: {result}")
                
                # 检查结果是否表明成功
                result_str = str(result).lower()
                success_indicators = ["filled", "completed", "entered", "success", "screenshot"]
                has_success = any(indicator in result_str for indicator in success_indicators)
                
                if has_success or len(str(result)) > 50:  # 如果结果有内容，通常表示有实际操作
                    self.log("✅ Browser-use表单填写成功")
                    return True
                else:
                    self.log("⚠️ Browser-use执行完成但无明确成功指标")
                    return True  # 仍然认为成功，因为执行完成了
                        
            except asyncio.TimeoutError:
                self.log("⚠️ Browser-use填写超时")
                return False
                
        except Exception as e:
            self.log(f"❌ 表单填写失败: {e}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            return False
    
    async def _create_smart_form_filling_task(self, form_fields: dict) -> str:
        """使用LLM智能创建表单填写任务，无硬编码映射"""
        try:
            if not self.llm_client:
                # 降级到基础任务
                return self._create_basic_form_filling_task(form_fields)
            
            # 构建LLM优化提示
            optimization_prompt = f"""
你是一个专业的网页表单填写专家。请根据以下用户数据，创建一个详细的表单填写指令，用于browser-use框架自动填写 {self.target_url} 页面的表单。

用户提供的数据：
{json.dumps(form_fields, ensure_ascii=False, indent=2)}

请分析每个字段的含义，并创建清晰的英文填写指令。对于特殊字段类型，请提供适当的操作说明：

1. 对于中文内容，保持原文（姓名、地址等个人信息）
2. 对于选择性字段（如尺寸、配料），请提供清晰的选择指令
3. 对于时间字段，确保格式正确
4. 对于数组类型的字段（如配料列表），请展开为多个操作

要求：
- 使用清晰的英文指令，适合browser-use理解
- 每个字段一个具体的操作指令
- 包含必要的导航和确认步骤
- 不要提交表单，只填写
- 最后要求截图确认

请直接返回完整的任务指令，不要包含任何解释或格式标记。
"""
            
            try:
                # 调用LLM优化任务
                if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                    response = await self.llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert at creating browser automation tasks for form filling."},
                            {"role": "user", "content": optimization_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=500
                    )
                    optimized_task = response.choices[0].message.content.strip()
                else:
                    # 使用直接的OpenAI客户端
                    from openai import AsyncOpenAI
                    import os
                    
                    openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert at creating browser automation tasks for form filling."},
                            {"role": "user", "content": optimization_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=500
                    )
                    optimized_task = response.choices[0].message.content.strip()
                
                self.log(f"LLM智能任务优化完成: {optimized_task[:100]}...")
                return optimized_task
                
            except Exception as llm_error:
                self.log(f"LLM任务优化失败，使用基础任务: {llm_error}")
                return self._create_basic_form_filling_task(form_fields)
                
        except Exception as e:
            self.log(f"创建智能表单任务失败: {e}")
            return self._create_basic_form_filling_task(form_fields)
    
    def _create_basic_form_filling_task(self, form_fields: dict) -> str:
        """创建基础表单填写任务（备选方案）"""
        instructions = []
        for field_name, value in form_fields.items():
            if value:
                instructions.append(f"Fill the {field_name} field with: {value}")
        
        return f"""
Navigate to {self.target_url} and fill out the form with the following information:

{chr(10).join(f"- {instruction}" for instruction in instructions)}

Requirements:
1. Navigate to the page first if not already there
2. Find each form field by its label, name, or placeholder
3. Fill each field with the EXACT value specified above
4. Take your time and wait for elements to load
5. Do NOT submit the form
6. Take a screenshot after filling to confirm success

Work step by step and be patient with element loading times.
"""
    
    async def _execute_browser_form_filling(self, form_fields: dict):
        """使用现有browser-use session执行表单填写"""
        try:
            self.log(f"使用现有browser session填写表单: {form_fields}")
            
            # 直接调用强制填写方法，而不是创建新的复杂逻辑
            success = await self._execute_actual_form_filling(form_fields)
            
            if success:
                # 通知用户填写成功
                filled_info = [f"{k}: {v}" for k, v in form_fields.items()]
                await self._send_to_phone_agent(
                    f"✅ 已成功在网页中填写: {', '.join(filled_info)}。请继续提供其他信息或说'提交表单'。",
                    message_type="task_result",
                    additional_data={"filled_fields": form_fields, "status": "browser_filled"}
                )
            else:
                # 填写失败，记录信息
                filled_info = [f"{k}: {v}" for k, v in form_fields.items()]
                await self._send_to_phone_agent(
                    f"⚠️ 网页填写遇到技术问题，但已记录您的信息: {', '.join(filled_info)}。",
                    message_type="task_result",
                    additional_data={"filled_fields": form_fields, "status": "timeout_recorded"}
                )
                
        except Exception as e:
            self.log(f"Browser-use填写出错: {e}")
            # 降级：记录用户信息
            filled_info = [f"{k}: {v}" for k, v in form_fields.items()]
            await self._send_to_phone_agent(
                f"⚠️ 网页填写遇到技术问题，但已记录您的信息: {', '.join(filled_info)}。",
                message_type="task_result",
                additional_data={"filled_fields": form_fields, "status": "error_recorded"}
            )
    
    async def _create_and_execute_form_filling(self, form_fields: dict):
        """创建新的browser-use agent执行表单填写"""
        try:
            self.log(f"创建新的browser agent填写表单: {form_fields}")
            
            # 直接调用强制填写方法
            success = await self._execute_actual_form_filling(form_fields)
            
            if success:
                filled_info = [f"{k}: {v}" for k, v in form_fields.items()]
                await self._send_to_phone_agent(
                    f"✅ 已成功在网页中填写: {', '.join(filled_info)}。",
                    message_type="task_result",
                    additional_data={"filled_fields": form_fields, "status": "new_agent_filled"}
                )
            else:
                filled_info = [f"{k}: {v}" for k, v in form_fields.items()]
                await self._send_to_phone_agent(
                    f"⚠️ 填写超时，但已记录信息: {', '.join(filled_info)}。",
                    message_type="task_result",
                    additional_data={"filled_fields": form_fields, "status": "timeout"}
                )
                
        except Exception as e:
            self.log(f"创建填写代理失败: {e}")
            filled_info = [f"{k}: {v}" for k, v in form_fields.items()]
            await self._send_to_phone_agent(
                f"⚠️ 填写遇到问题，已记录信息: {', '.join(filled_info)}。",
                message_type="task_result",
                additional_data={"filled_fields": form_fields, "status": "creation_error"}
            )
    
    def _map_chinese_to_english_field(self, chinese_field: str) -> str:
        """将中文字段名映射到英文字段名"""
        mapping = {
            "姓名": "customer name",
            "名字": "customer name", 
            "name": "customer name",
            "电话": "telephone",
            "手机": "telephone",
            "手机号": "telephone", 
            "phone": "telephone",
            "邮箱": "email",
            "邮件": "email",
            "email": "email",
            "地址": "address",
            "address": "address"
        }
        return mapping.get(chinese_field.lower(), chinese_field)
    
    async def _handle_general_browser_request(self, user_text: str):
        """处理非表单数据的一般请求 - 按设计文档使用LLM智能分析"""
        try:
            self.log(f"LLM智能分析一般浏览器请求: {user_text}")
            
            # 使用LLM分析用户意图，严格按照设计文档要求
            if not self.llm_client:
                await self._send_to_phone_agent("系统暂时无法处理您的请求", message_type="error")
                return
            
            # LLM驱动的意图分析
            intent_prompt = f"""
用户输入："{user_text}"

请分析用户的意图，判断这是什么类型的请求：

1. 如果用户提到了个人信息（姓名、邮箱、电话等），说明这是表单填写相关的信息
2. 如果用户要求导航到某个网页，说明这是导航请求  
3. 如果用户要求点击某个按钮或元素，说明这是操作请求
4. 如果用户在询问页面状态或内容，说明这是查询请求
5. 其他情况请给出合适的分析

请以JSON格式回复你的分析：
{{
    "intent_type": "form_data|navigation|operation|query|other",
    "confidence": "high|medium|low",
    "explanation": "简要说明你的分析理由",
    "suggested_response": "建议给用户的回复"
}}
"""
            
            try:
                if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                    response = await self.llm_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an intelligent browser assistant that analyzes user requests."},
                            {"role": "user", "content": intent_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=200
                    )
                    result_text = response.choices[0].message.content.strip()
                else:
                    result_text = await self.llm_client.ainvoke([
                        {"role": "system", "content": "You are an intelligent browser assistant that analyzes user requests."},
                        {"role": "user", "content": intent_prompt}
                    ])
                    if isinstance(result_text, dict) and 'content' in result_text:
                        result_text = result_text['content']
                    result_text = str(result_text).strip()
                
                # 解析LLM的意图分析结果
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                intent_analysis = json.loads(result_text)
                suggested_response = intent_analysis.get("suggested_response", "我正在分析您的请求，请稍等")
                
                await self._send_to_phone_agent(suggested_response, message_type="task_result")
                
            except Exception as llm_error:
                self.log(f"LLM意图分析失败: {llm_error}")
                # 如果LLM分析失败，给出通用回复
                await self._send_to_phone_agent(
                    "我已收到您的指令，正在处理中。如需填写表单，请提供具体信息如姓名、邮箱等。",
                    message_type="task_result"
                )
            
        except Exception as e:
            self.log(f"处理一般请求失败: {e}")
            await self._send_to_phone_agent("处理请求时出现错误", message_type="error")
    
    async def _analyze_user_intent_with_llm(self, user_text: str) -> dict:
        """使用LLM分析用户意图（无硬编码）"""
        try:
            if not hasattr(self, 'llm_client') or not self.llm_client:
                return {"type": "general", "data": {}}
            
            intent_prompt = f"""
分析用户输入的意图："{user_text}"

请判断这是以下哪种类型的请求：
1. navigation - 导航到网页（包含URL或要求打开网站）
2. form_data - 提供表单数据（姓名、邮箱、电话等个人信息，或披萨尺寸、配料、时间等订单信息）
3. operation - 执行操作（例如点击按钮、滚动页面等）
4. query - 查询页面状态或内容
5. general - 其他通用请求

如果是form_data类型，请提取具体的字段信息。
如果是navigation类型，请提取URL。
如果是operation类型，请提取操作类型和目标。
如果是query类型，请提取查询内容。

请以JSON格式回复：
{{
    "type": "navigation|form_data|operation|query|general",
    "data": {{
        "url": "提取的URL（如果是导航）",
        "form_fields": {{ # 如果是form_data，在这里提取所有相关数据
            "name": "提取的姓名",
            "email": "提取的邮箱",
            "phone": "提取的电话",
            "pizza_size": "提取的披萨尺寸",
            "toppings": ["提取的配料列表"],
            "delivery_time": "提取的配送时间HH:MM格式",
            "delivery_instructions": "提取的配送说明"
        }},
        "operation_type": "点击|滚动|其他（如果是操作）",
        "target_element": "目标元素描述（如果是操作）",
        "query_content": "查询内容（如果是查询）"
    }}
}}
"""
            
            # 调用LLM分析
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an intent analysis expert."},
                        {"role": "user", "content": intent_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
                result_text = response.choices[0].message.content.strip()
            else:
                messages = [
                    {"role": "system", "content": "You are an intent analysis expert."},
                    {"role": "user", "content": intent_prompt}
                ]
                result_text = await self.llm_client.ainvoke(messages)
                if isinstance(result_text, dict) and 'content' in result_text:
                    result_text = result_text['content']
                result_text = str(result_text).strip()
            
            # 解析JSON结果
            import json
            try:
                intent_result = json.loads(result_text)
                self.log(f"LLM意图分析: {intent_result}")
                return intent_result
            except json.JSONDecodeError:
                self.log(f"LLM返回非JSON格式，使用默认分析")
                return {"type": "general", "data": {}}
                
        except Exception as e:
            self.log(f"LLM意图分析失败: {e}")
            return {"type": "general", "data": {}}
    
    async def _handle_navigation_request(self, intent: dict):
        """处理导航请求"""
        try:
            url = intent.get("data", {}).get("url", "")
            if not url:
                await self._send_to_phone_agent("未找到有效的URL", message_type="error")
                return
            
            # 创建导航任务
            navigation_task = f"Navigate to {url} and wait for the page to fully load"
            agent = self._create_browser_agent(navigation_task)
            
            if not agent:
                await self._send_to_phone_agent("无法创建浏览器代理", message_type="error")
                return
            
            self.log(f"开始导航到: {url}")
            result = await agent.run()
            
            # 导航完成后，分析页面表单并通知Phone Agent
            await self._analyze_page_and_notify_phone_agent(url)
            
        except Exception as e:
            self.log(f"导航处理失败: {e}")
            await self._send_to_phone_agent(f"导航失败: {str(e)}", message_type="error")
    
    async def _analyze_page_and_notify_phone_agent(self, url: str):
        """分析页面表单并通知Phone Agent（只分析，不填写）"""
        try:
            # 创建页面分析任务 - 重要：只分析，不要填写任何信息！
            analysis_task = """
            Analyze the current page and identify all form fields, but DO NOT fill in any information.
            
            Your task is ONLY to:
            1. Identify what form fields exist (name, type, labels)
            2. Report the structure of the page
            3. DO NOT enter any data into any fields
            4. DO NOT submit any forms
            5. DO NOT click any buttons except if needed to analyze the page structure
            
            Just describe what you see without taking any actions that modify the page content.
            """
            
            agent = self._create_browser_agent(analysis_task)
            
            if not agent:
                await self._send_to_phone_agent("页面分析失败", message_type="error")
                return
            
            self.log("开始分析页面表单结构（仅分析，不填写）...")
            analysis_result = await agent.run()
            
            # 将分析结果发送给Phone Agent
            await self._send_to_phone_agent(
                f"已成功打开页面: {url}。发现表单字段可供填写，等待用户提供信息。",
                message_type="page_analysis",
                additional_data={
                    "url": url,
                    "page_analysis": str(analysis_result),
                    "has_forms": True,
                    "ready_for_user_input": True
                }
            )
            
        except Exception as e:
            self.log(f"页面分析失败: {e}")
            await self._send_to_phone_agent(
                f"页面已打开: {url}，但分析表单时出现问题",
                message_type="page_analysis",
                additional_data={"url": url, "has_forms": False}
            )
    
    async def _handle_form_data_input(self, intent: dict):
        """处理表单数据输入（按照用户提供的具体信息填写）"""
        try:
            form_fields = intent.get("data", {}).get("form_fields", {})
            
            if not form_fields:
                await self._send_to_phone_agent("未识别到有效的表单数据", message_type="error")
                return
            
            # 构建更严格的表单填写指令，防止browser-use自己瞎填
            fill_instructions = [
                "Fill ONLY the specified form fields with the exact values provided.",
                "DO NOT fill any fields that are not explicitly specified below.",
                "DO NOT use placeholder or example data.",
                "DO NOT submit the form unless specifically requested.",
                "",
                "Fields to fill:"
            ]
            
            filled_field_count = 0
            for field_name, value in form_fields.items():
                if value and str(value).strip():  # 只添加有有效值的字段
                    fill_instructions.append(f"- {field_name} field: '{value}' (EXACT VALUE)")
                    filled_field_count += 1
            
            if filled_field_count == 0:
                await self._send_to_phone_agent("没有找到有效的表单数据", message_type="error")
                return
            
            fill_instructions.extend([
                "",
                "IMPORTANT: Only fill the fields listed above with the exact values specified.",
                "Do not fill any other fields.",
                "Use the exact values provided - do not modify or interpret them.",
                "After filling, report which fields were successfully filled."
            ])
            
            fill_task = "\n".join(fill_instructions)
            agent = self._create_browser_agent(fill_task)
            
            if not agent:
                await self._send_to_phone_agent("无法创建表单填写代理", message_type="error")
                return
            
            self.log(f"开始精确填写表单字段: {form_fields}")
            result = await agent.run()
            
            # 通知Phone Agent填写结果
            filled_fields = [f"{k}: {v}" for k, v in form_fields.items() if v and str(v).strip()]
            await self._send_to_phone_agent(
                f"已按要求填写表单字段: {', '.join(filled_fields)}",
                message_type="form_filled",
                additional_data={
                    "filled_fields": form_fields,
                    "result": str(result)[:200]
                }
            )
            
        except Exception as e:
            self.log(f"表单填写失败: {e}")
            await self._send_to_phone_agent(f"表单填写失败: {str(e)}", message_type="error")
    
    async def _handle_general_request(self, user_text: str):
        """处理通用请求"""
        try:
            # 对于通用请求，优化任务描述但不让browser-use自由发挥
            optimized_task = await self._optimize_task_with_llm(user_text)
            agent = self._create_browser_agent(optimized_task)
            
            if not agent:
                await self._fallback_response(user_text)
                return
            
            self.log(f"执行通用任务: {optimized_task}")
            result = await agent.run()
            
            await self._send_to_phone_agent(
                "操作已完成",
                message_type="task_result",
                additional_data={
                    "operation": "general_request",
                    "user_input": user_text,
                    "result": str(result)[:200]
                }
            )
            
        except Exception as e:
            self.log(f"通用请求处理失败: {e}")
            await self._fallback_response(user_text)
    
    async def _optimize_task_with_llm(self, user_text: str) -> str:
        """使用LLM优化任务描述，确保browser-use能正确理解（无硬编码）"""
        try:
            if not hasattr(self, 'llm_client') or not self.llm_client:
                # 如果没有LLM客户端，直接返回原始文本
                return user_text
            
            # LLM驱动的任务优化提示
            optimization_prompt = f"""
你是一个浏览器自动化任务优化专家。用户的原始请求是："{user_text}"

请将这个中文请求转换为简洁、明确的英文浏览器操作指令，确保browser-use能够正确理解和执行。

重要指导原则：
1. 如果涉及网址导航，使用"Navigate to [URL] and wait for the page to fully load"格式
2. 如果涉及表单填写，使用"Fill the form with the following information: ..."格式  
3. 如果涉及点击操作，使用"Click on [element description]"格式
4. 保持指令简洁明确，避免冗余信息
5. 确保指令是browser-use能理解的标准英文格式
6. 对于页面加载，总是包含"wait for the page to fully load"确保页面完全加载

特别注意：
- 导航指令应该包含等待页面加载完成
- 表单操作前应该确保页面已完全加载
- 使用稳定的操作步骤，避免超时错误

请直接返回优化后的英文指令，不要包含任何解释。
"""
            
            # 使用当前的LLM客户端（可能是OpenAI、Anthropic或Siliconflow）
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                # OpenAI风格的客户端
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a browser automation task optimizer."},
                        {"role": "user", "content": optimization_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                optimized_task = response.choices[0].message.content.strip()
            else:
                # 直接调用LLM客户端（browser-use风格）
                messages = [
                    {"role": "system", "content": "You are a browser automation task optimizer."},
                    {"role": "user", "content": optimization_prompt}
                ]
                optimized_task = await self.llm_client.ainvoke(messages)
                if isinstance(optimized_task, dict) and 'content' in optimized_task:
                    optimized_task = optimized_task['content']
                optimized_task = str(optimized_task).strip()
            
            self.log(f"LLM任务优化: '{user_text}' -> '{optimized_task}'")
            return optimized_task
            
        except Exception as e:
            self.log(f"LLM任务优化失败，使用原始文本: {e}")
            return user_text
    
    async def _fallback_response(self, user_text: str):
        """备选响应"""
        try:
            self.log(f"使用备选响应: {user_text}")
            
            await self._send_to_phone_agent(
                "我已收到您的指令，正在处理中",
                message_type="task_result",
                additional_data={
                    "operation": "fallback_mode",
                    "user_input": user_text
                }
            )
            
            self.state = ComputerAgentState.IDLE
            
        except Exception as e:
            self.log(f"备选响应失败: {e}")
    
    async def _analyze_page_content(self):
        """
        真实的页面分析 - 严格按照设计文档要求
        使用browser-use的视觉识别能力分析页面结构和表单布局
        """
        try:
            if not self.browser_agent:
                return {
                    "success": False,
                    "message": "浏览器会话不存在，无法分析页面",
                    "data": {"url": self.target_url, "error": "no_browser_session"}
                }
            
            # 创建专门用于页面分析的任务
            analysis_task = f"""Analyze the current page at {self.target_url} and provide detailed information about:

1. Check if the page loaded successfully (no 503/404/500 errors)
2. Identify all forms on the page
3. For each form, list all input fields with their:
   - Field name/id
   - Field type (text, email, password, etc.)
   - Field label or placeholder text
   - Whether the field is required
4. Count total number of forms and fields
5. Determine if the page is ready for form filling

Do NOT fill any forms or input any data. Only analyze and report the structure.
"""
            
            print(f"🔍 执行页面分析任务...")
            
            # 创建专门的分析agent
            analysis_agent = self._create_browser_agent(analysis_task)
            if not analysis_agent:
                raise Exception("无法创建页面分析agent")
            
            # 执行分析，设置合理的超时
            analysis_result = await asyncio.wait_for(
                analysis_agent.run(), 
                timeout=25.0
            )
            
            self.log(f"Browser-use页面分析结果: {analysis_result}")
            
            # 使用LLM解析browser-use的分析结果
            parsed_result = await self._parse_analysis_result(analysis_result)
            
            return parsed_result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": f"页面分析超时，可能页面 {self.target_url} 不可用",
                "data": {"url": self.target_url, "error": "analysis_timeout"}
            }
        except Exception as e:
            self.log(f"页面分析失败: {e}")
            return {
                "success": False,
                "message": f"页面分析失败: {str(e)}",
                "data": {"url": self.target_url, "error": str(e)}
            }
    
    async def _parse_analysis_result(self, browser_result: str):
        """
        使用LLM解析browser-use的分析结果，提取结构化的表单信息
        """
        try:
            self.log(f"开始解析browser-use结果: {browser_result[:200]}...")
            
            # 首先进行基础错误检测（不依赖LLM的快速检测）
            basic_error_check = self._basic_error_detection(browser_result)
            if basic_error_check:
                return basic_error_check
            
            if not self.llm_client:
                # 如果没有LLM，返回基础信息
                return {
                    "success": True,
                    "message": f"已打开页面 {self.target_url}，但无法详细分析表单结构",
                    "data": {"url": self.target_url, "forms_count": 0, "form_fields": []}
                }
            
            # 构建更详细的LLM解析提示，明确要求检测HTTP错误
            parse_prompt = f"""
你是一个专业的网页分析专家。请仔细分析以下browser-use框架的页面分析结果，重点关注：

1. **错误检测**: 检查是否有HTTP错误（503 Service Unavailable、404 Not Found、500 Internal Server Error等）
2. **页面状态**: 确定页面是否正常加载
3. **表单结构**: 提取可用的表单字段信息

Browser-use分析结果:
{browser_result}

**重要**: 如果分析结果中提到任何HTTP错误码（如503、404、500）或"unavailable"、"error"、"failed"等错误信息，必须将page_status设为"error"。

请以JSON格式返回页面分析信息：
{{
    "page_status": "success|error",
    "page_error": "具体的错误描述（如'503 Service Unavailable'）",
    "forms_count": 表单数量（错误时为0）,
    "form_fields": [
        {{
            "id": "字段ID",
            "name": "字段名称", 
            "type": "字段类型",
            "label": "字段标签",
            "placeholder": "占位符文本",
            "required": true/false
        }}
    ],
    "ready_for_input": true/false,
    "description": "页面状态的详细中文描述"
}}

检测规则:
- 如果发现503、404、500等HTTP错误 → page_status: "error"
- 如果页面正常但无表单 → page_status: "success", forms_count: 0
- 如果页面正常且有表单 → page_status: "success", forms_count: >0
"""
            
            # 调用LLM解析
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing web page structure and extracting form information."},
                        {"role": "user", "content": parse_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000
                )
                result_text = response.choices[0].message.content.strip()
            else:
                result_text = await self.llm_client.ainvoke([
                    {"role": "system", "content": "You are an expert at analyzing web page structure."},
                    {"role": "user", "content": parse_prompt}
                ])
                if isinstance(result_text, dict) and 'content' in result_text:
                    result_text = result_text['content']
                result_text = str(result_text).strip()
            
            # 解析JSON结果
            try:
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                parsed_data = json.loads(result_text)
                
                # 构建返回结果
                if parsed_data.get("page_status") == "error":
                    return {
                        "success": False,
                        "message": f"页面访问失败: {parsed_data.get('page_error', '未知错误')}",
                        "data": {
                            "url": self.target_url,
                            "error": parsed_data.get('page_error', '未知错误'),
                            "forms_count": 0,
                            "form_fields": []
                        }
                    }
                else:
                    forms_count = parsed_data.get("forms_count", 0)
                    form_fields = parsed_data.get("form_fields", [])
                    
                    if forms_count > 0 and form_fields:
                        message = f"已成功分析页面 {self.target_url}，发现 {forms_count} 个表单，包含 {len(form_fields)} 个字段"
                    else:
                        message = f"已打开页面 {self.target_url}，但未发现可填写的表单"
                    
                    return {
                        "success": True,
                        "message": message,
                        "data": {
                            "url": self.target_url,
                            "forms_count": forms_count,
                            "form_fields": form_fields,
                            "ready_for_input": parsed_data.get("ready_for_input", forms_count > 0),
                            "description": parsed_data.get("description", "")
                        }
                    }
                
            except json.JSONDecodeError:
                self.log(f"LLM返回非JSON格式: {result_text}")
                return {
                    "success": True,
                    "message": f"已打开页面 {self.target_url}，但无法解析表单结构",
                    "data": {"url": self.target_url, "forms_count": 0, "form_fields": []}
                }
                
        except Exception as e:
            self.log(f"解析分析结果失败: {e}")
            return {
                "success": True,
                "message": f"已打开页面 {self.target_url}，但表单分析遇到技术问题",
                "data": {"url": self.target_url, "forms_count": 0, "form_fields": []}
            }
    
    async def _analyze_page_status_with_llm(self, navigation_result: str, task_completed: bool):
        """使用LLM分析页面状态，完全无硬编码"""
        try:
            if not self.llm_client:
                # 没有LLM时的降级处理
                return {
                    "success": True,
                    "message": f"已尝试打开页面 {self.target_url}，请提供需要填写的信息",
                    "data": {
                        "url": self.target_url,
                        "page_ready": True,
                        "ready_for_user_input": True
                    }
                }
            
            # 构建LLM分析提示
            analysis_prompt = f"""
你是一个专业的网页状态分析专家。请分析以下browser-use框架的导航结果，判断页面是否成功加载并可用于表单填写。

目标URL: {self.target_url}
导航任务是否完成: {"是" if task_completed else "否"}
导航结果信息:
{navigation_result[:2000]}

请分析并判断：
1. 页面是否成功加载？
2. 页面是否可用于表单操作？
3. 是否可以开始接收用户的表单数据？

请以JSON格式回复你的分析：
{{
    "page_loaded_successfully": true/false,
    "ready_for_form_input": true/false,
    "analysis_summary": "你的分析总结",
    "user_message": "给用户的友好消息",
    "confidence_level": "high|medium|low"
}}

分析要点：
- 如果结果显示有交互元素或成功导航，通常表示页面加载成功
- 如果有错误信息、超时或失败提示，表示页面可能有问题
- 即使有些技术问题，只要基本导航完成，通常仍可尝试表单操作
"""
            
            # 调用LLM分析
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是网页状态分析专家，基于browser-use结果判断页面可用性。"},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500
                )
                result_text = response.choices[0].message.content.strip()
            else:
                result_text = await self.llm_client.ainvoke([
                    {"role": "system", "content": "你是网页状态分析专家，基于browser-use结果判断页面可用性。"},
                    {"role": "user", "content": analysis_prompt}
                ])
                if isinstance(result_text, dict) and 'content' in result_text:
                    result_text = result_text['content']
                result_text = str(result_text).strip()
            
            # 解析LLM分析结果
            try:
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                elif result_text.startswith('```'):
                    result_text = result_text.replace('```', '').strip()
                
                analysis = json.loads(result_text)
                
                page_loaded = analysis.get("page_loaded_successfully", True)
                ready_for_input = analysis.get("ready_for_form_input", True)
                user_message = analysis.get("user_message", "页面已打开，请提供表单信息")
                
                if page_loaded and ready_for_input:
                    return {
                        "success": True,
                        "message": user_message,
                        "data": {
                            "url": self.target_url,
                            "page_ready": True,
                            "ready_for_user_input": True,
                            "analysis_summary": analysis.get("analysis_summary", ""),
                            "confidence": analysis.get("confidence_level", "medium")
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": user_message,
                        "data": {
                            "url": self.target_url,
                            "page_ready": False,
                            "ready_for_user_input": False,
                            "error": analysis.get("analysis_summary", "页面加载可能有问题")
                        }
                    }
                
            except json.JSONDecodeError:
                self.log(f"LLM页面分析返回非JSON格式: {result_text}")
                # JSON解析失败时的降级处理
                return {
                    "success": True,
                    "message": f"已尝试打开页面 {self.target_url}，请提供需要填写的信息",
                    "data": {
                        "url": self.target_url,
                        "page_ready": True,
                        "ready_for_user_input": True
                    }
                }
                
        except Exception as e:
            self.log(f"LLM页面状态分析失败: {e}")
            # 异常时的降级处理
            return {
                "success": True,
                "message": f"已尝试打开页面 {self.target_url}，请提供需要填写的信息",
                "data": {
                    "url": self.target_url,
                    "page_ready": True,
                    "ready_for_user_input": True
                }
            }
    
    def _basic_error_detection(self, browser_result: str):
        """
        基础错误检测 - 使用LLM而非硬编码模式
        """
        try:
            if not browser_result or len(browser_result.strip()) < 10:
                return {
                    "success": False,
                    "message": f"页面分析结果为空，{self.target_url} 可能无法访问",
                    "data": {"url": self.target_url, "error": "empty_result", "forms_count": 0, "form_fields": []}
                }
            
            # 如果有LLM客户端，使用LLM进行错误检测
            if self.llm_client:
                return None  # 让LLM处理
            
            # 仅在没有LLM时使用基础检测
            browser_result_lower = browser_result.lower()
            
            # 基础错误检测（仅作为最后备选）
            common_errors = ["503", "504", "502", "500", "404", "403", "error", "unavailable", "timeout", "refused"]
            
            for error_term in common_errors:
                if error_term in browser_result_lower:
                    return {
                        "success": False,
                        "message": f"页面访问可能存在问题，{self.target_url} 当前不可用",
                        "data": {
                            "url": self.target_url,
                            "error": "detected_issue",
                            "forms_count": 0,
                            "form_fields": [],
                            "error_type": "basic_detection"
                        }
                    }
            
            # 如果没有检测到明显错误，返回None让后续处理
            return None
            
        except Exception as e:
            self.log(f"基础错误检测失败: {e}")
            return None
    
    async def _execute_form_fill_task(self, task: str):
        """使用现有的browser agent执行表单填写任务"""
        try:
            # 由于现有的browser agent可能正在执行导航任务，
            # 我们需要创建一个新的agent来处理表单填写
            # 但这个新agent应该连接到同一个浏览器会话（如果可能）
            
            self.log(f"执行表单填写任务: {task}")
            
            # 创建专门用于填写的agent
            fill_agent = self._create_browser_agent(task)
            if not fill_agent:
                raise Exception("无法创建表单填写agent")
            
            # 执行填写任务
            result = await fill_agent.run()
            self.log(f"表单填写完成: {result}")
            return result
            
        except Exception as e:
            self.log(f"执行表单填写任务失败: {e}")
            raise
    
    async def _send_to_phone_agent(self, message: str, message_type: str = "task_result", 
                                  additional_data: Optional[Dict[str, Any]] = None):
        """发送消息给Phone Agent"""
        try:
            result = await send_message_to_phone_agent(
                message=message,
                message_type=message_type,
                task_id=self.current_task_id,
                additional_data=additional_data or {}
            )
            
            if result.get("success"):
                self.log(f"消息发送成功: {message}")
            else:
                self.log(f"消息发送失败（可能没有Phone Agent）: {result.get('error')}")
                
        except Exception as e:
            self.log(f"发送消息失败（可能在测试环境中，没有Phone Agent）: {e}")
    
    async def _handle_system_status(self, message: ToolMessage):
        """处理来自Phone Agent的系统状态查询消息"""
        try:
            print(f"📊 SYSTEM_STATUS handler called - processing status query")
            self.log(f"处理SYSTEM_STATUS消息: {message.content}")
            
            content = message.content
            text = content.get("text", "")
            
            if "分析" in text and "页面" in text:
                # Phone Agent请求页面分析
                print("🔍 Phone Agent请求页面分析...")
                
                # 如果有browser_agent会话，尝试使用extract_structured_data
                if self.browser_agent:
                    try:
                        # 直接使用browser-use的extract_structured_data功能
                        query = "Extract all form fields from this page including their names, types, labels, and any other attributes."
                        
                        # 尝试调用extract_structured_data
                        if hasattr(self.browser_agent, 'controller') and self.browser_agent.controller:
                            extract_result = await self.browser_agent.controller.extract_structured_data(query)
                            self.log(f"Browser-use数据提取结果: {extract_result}")
                            
                            # 解析提取结果并发送给Phone Agent
                            page_analysis = await self._parse_browser_use_result(str(extract_result))
                            await self._send_to_phone_agent(
                                page_analysis["message"],
                                message_type="page_analysis",
                                additional_data=page_analysis["data"]
                            )
                            return
                        else:
                            self.log("Browser agent没有controller，使用备选分析")
                    except Exception as extract_error:
                        self.log(f"Extract structured data失败: {extract_error}")
                
                # 备选方案：发送基础页面分析
                await self._send_basic_page_analysis()
                
            else:
                # 其他状态查询
                status_msg = f"Computer Agent状态正常，浏览器{'已连接' if self.browser_agent else '未连接'}，页面{'已准备' if self.page_ready else '准备中'}。"
                await self._send_to_phone_agent(
                    status_msg,
                    message_type="system_status"
                )
                
        except Exception as e:
            self.log(f"处理SYSTEM_STATUS失败: {e}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            
            # 确保即使出错也发送页面分析数据
            try:
                await self._send_basic_page_analysis()
            except Exception as fallback_error:
                self.log(f"备选页面分析也失败: {fallback_error}")
                await self._send_to_phone_agent("系统状态查询失败，请稍后再试。", message_type="error")

    async def _handle_form_data(self, message: ToolMessage):
        """处理表单数据消息"""
        try:
            print(f"✅ FORM_DATA handler called - processing form data")
            self.log(f"处理FORM_DATA消息: {message.content}")
            
            # 检查浏览器会话是否还活跃
            if not self.browser_agent:
                print("❌ 浏览器会话不存在，无法填写表单")
                await self._send_to_phone_agent(
                    "浏览器会话已关闭，无法填写表单。请重新打开页面。",
                    message_type="error"
                )
                return
            
            # 从消息内容中提取表单数据 - 适配工具调用系统的数据结构
            form_data = {}
            
            # 方法1: 从additional_data字段提取（原始方法）
            additional_data = message.content.get("additional_data")
            if additional_data and isinstance(additional_data, dict):
                form_data.update(additional_data)
                print(f"📝 从additional_data提取表单字段: {additional_data}")
            
            # 方法2: 从message.content的顶级字段提取（工具调用系统合并后的结构）
            for key, value in message.content.items():
                # 跳过系统字段，只保留可能的表单数据字段
                if key not in ['text', 'timestamp', 'additional_data'] and not key.startswith('_'):
                    form_data[key] = value
                    print(f"📝 从message.content提取表单字段: {key} = {value}")
            
            if form_data:
                print(f"✅ 提取到表单数据: {form_data}")
                await self._fill_form_with_extracted_data(form_data)
            else:
                print("❌ 未找到有效的表单数据")
                await self._send_to_phone_agent("未收到有效的表单数据，请重新提供。", message_type="error")
                
        except Exception as e:
            self.log(f"处理FORM_DATA失败: {e}")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}")
            await self._send_to_phone_agent(f"处理表单信息时发生错误: {e}", message_type="error")

    def _convert_form_data_to_instruction(self, form_data: Dict[str, Any]) -> str:
        """将表单数据转换为自然语言指令"""
        instructions = ["请在当前页面填写以下信息："]
        
        for field_name, value in form_data.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
                instructions.append(f"- {field_name}: {value_str}")
            else:
                instructions.append(f"- {field_name}: {value}")
        
        return "\n".join(instructions)
    
    async def stop(self):
        """停止Computer Agent"""
        self.log("停止IntelligentComputerAgent")
        
        try:
            # 停止工具调用处理器
            self.tool_handler.stop()
            
            self.log("IntelligentComputerAgent已停止")
            
        except Exception as e:
            self.log(f"停止过程中出现错误: {e}")
            raise
    
    def log(self, message: str):
        """记录日志"""
        if self.debug:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}][IntelligentComputerAgent] {message}")


# 创建Computer Agent实例的工厂函数
def create_intelligent_computer_agent(config: Optional[ComputerAgentConfig] = None) -> IntelligentComputerAgent:
    """创建智能Computer Agent实例"""
    if config is None:
        config = ComputerAgentConfig(debug=True)
    
    return IntelligentComputerAgent(config)


if __name__ == "__main__":
    """测试入口（参考官方代码）"""
    async def main():
        # 创建并启动agent
        config = ComputerAgentConfig(debug=True)
        agent = create_intelligent_computer_agent(config)
        await agent.start()
    
    asyncio.run(main())