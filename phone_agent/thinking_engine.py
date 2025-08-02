"""
混合思考引擎模块

实现快慢思考结合的边听边想能力，通过快思考路径提供实时反馈，
同时通过慢思考路径进行深度分析与复杂推理
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Union, Any, Callable, Tuple
from enum import Enum, auto
import os
import aiohttp
from openai import AsyncOpenAI

# 尝试导入Anthropic库
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class ThinkingMode(Enum):
    """思考模式枚举"""
    FAST = auto()   # 快思考模式，低延迟
    DEEP = auto()   # 深度思考模式，高质量


class ThinkingStatus(Enum):
    """思考状态枚举"""
    IDLE = auto()       # 空闲
    THINKING = auto()   # 思考中
    COMPLETED = auto()  # 完成
    ERROR = auto()      # 错误


class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = auto()     # OpenAI
    ANTHROPIC = auto()  # Anthropic
    DEEPSEEK = auto()   # DeepSeek
    SILICONFLOW = auto() # SiliconFlow
    DOUBAO = auto()      # Doubao
    CUSTOM = auto()     # 自定义API
    DUMMY = auto()      # 测试模式


class MixedThinkingEngine:
    """混合思考引擎，支持Siliconflow和Doubao API调用"""

    def __init__(
        self,
        fast_model_name: str = "doubao-seed-1-6-flash-250615",
        deep_model_name: str = "doubao-seed-1-6-thinking-250615",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        provider: LLMProvider = LLMProvider.SILICONFLOW,
        system_prompt: Optional[str] = None,
        debug: bool = False
    ):
        self.fast_model_name = fast_model_name
        self.deep_model_name = deep_model_name
        self.debug = debug
        self.provider = provider

        # 根据提供商自动配置API参数
        if provider == LLMProvider.SILICONFLOW:
            self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY")
            self.api_base = api_base or "https://api.siliconflow.cn/v1"
            if not self.api_key:
                raise ValueError("请设置 SILICONFLOW_API_KEY 环境变量或通过参数提供")
        elif provider == LLMProvider.DOUBAO:
            self.api_key = api_key or os.environ.get("ARK_API_KEY") or os.environ.get("VOLC_API_KEY")
            self.api_base = api_base or "https://ark.cn-beijing.volces.com/api/v3"
            if not self.api_key:
                raise ValueError("请设置 ARK_API_KEY 或 VOLC_API_KEY 环境变量或通过参数提供")
        else:
            # 其他提供商的配置
            self.api_key = api_key
            self.api_base = api_base
            if not self.api_key:
                raise ValueError(f"请为{provider.name}提供API密钥")

        # 创建客户端时不传递可能导致冲突的参数
        client_kwargs = {
            "api_key": self.api_key,
            "base_url": self.api_base
        }
        self.client = AsyncOpenAI(**client_kwargs)
        
        self.system_prompt = system_prompt or """你是一个通用的AI助手，能够协助用户与各种网页进行交互。

核心原则 - 完全依赖Computer Agent的实时分析：
1. 你完全不知道当前网页的内容 - 所有页面信息都来自Computer Agent的实时分析
2. 绝对不要预设任何表单字段（如姓名、邮箱、电话）- 必须等待Computer Agent告知实际字段
3. 当用户开始交互时，如果没有页面信息，主动请求Computer Agent分析当前页面
4. 根据Computer Agent提供的实际页面信息来引导用户，包括：
   - 页面类型（表单、商品、服务等）
   - 实际可用的输入字段和选项
   - 具体的操作指导
5. 快思考：基于实际页面信息给出简短回应
6. 深度思考：请求Computer Agent进行页面分析或执行具体操作

通用性要求：
- 适应任何类型的网页（购物、预订、注册、搜索等）
- 根据实际页面内容调整交互方式
- 不要假设任何特定的业务场景"""
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]
        self.log(f"思考引擎初始化完成，提供商: {provider.name}, API: {self.api_base}")
        self.log(f"快思考模型: {self.fast_model_name}, 慢思考模型: {self.deep_model_name}")

    def log(self, message: str):
        if self.debug:
            print(f"[{time.strftime('%H:%M:%S')}][ThinkingEngine] {message}")

    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def reset_history(self):
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]

    async def think(self, message_queue=None, user_text="") -> Tuple[str, str]:
        """同时执行快思考和深度思考，并支持工具调用发送消息给Computer Agent"""
        print("🤔 思考引擎开始工作...")
        print(f"💭 对话历史长度: {len(self.conversation_history)} 条消息")
        
        messages = self.conversation_history
        
        # 显示最后几条消息用于调试
        if messages:
            print("📝 最近的对话:")
            for msg in messages[-3:]:  # 显示最后3条消息
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:50]
                print(f"   {role}: {content}...")
        
        print("🚀 启动快思考和深度思考...")
        
        # 为快思考和深度思考添加工具调用能力
        tools = self._get_available_tools()
        
        fast_task = asyncio.create_task(self._fast_think_with_tools(messages, tools))
        deep_task = asyncio.create_task(self._deep_think_with_tools(messages, tools))
        
        try:
            # 等待快思考完成
            fast_response, fast_tool_calls = await fast_task
            print(f"⚡ 快思考完成: '{fast_response[:50]}...'")
            
            # 处理快思考的工具调用
            if fast_tool_calls and user_text:
                await self._handle_tool_calls(fast_tool_calls, user_text, from_fast_thinking=True)
            
            # 等待深度思考完成
            deep_response, deep_tool_calls = await deep_task
            print(f"✅ 思考完成 - 快速: {len(fast_response)}字符, 深度: {len(deep_response)}字符")
            
            # 处理深度思考的工具调用
            if deep_tool_calls and user_text:
                await self._handle_tool_calls(deep_tool_calls, user_text, from_fast_thinking=False)
                
            return fast_response, deep_response
            
        except Exception as e:
            print(f"❌ 思考过程出错: {e}")
            import traceback
            traceback.print_exc()
            return "抱歉，我现在无法回应。", ""
    
    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用的工具列表"""
        from dual_agent.common.tool_calling import PHONE_AGENT_TOOLS
        return PHONE_AGENT_TOOLS
    
    async def _fast_think_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict]) -> Tuple[str, Optional[List[Dict]]]:
        """带工具调用的快思考"""
        try:
            print(f"⚡ 启动快思考 (模型: {self.fast_model_name})...")
            self.log(f"启动快思考 (模型: {self.fast_model_name})...")
            
            response = await self.client.chat.completions.create(
                model=self.fast_model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # 让模型自动决定是否调用工具
                stream=False,  # 工具调用时不使用流式
                max_tokens=200,
                temperature=0.7,
                timeout=15
            )
            
            message = response.choices[0].message
            content = message.content or ""
            tool_calls = message.tool_calls if hasattr(message, 'tool_calls') else None
            
            print(f"⚡ 快思考完成: '{content[:50]}...'")
            if tool_calls:
                print(f"🔧 快思考生成了 {len(tool_calls)} 个工具调用")
                
            self.log(f"快思考完成: {content}")
            return content.strip(), tool_calls
            
        except Exception as e:
            print(f"❌ 快思考出错: {e}")
            self.log(f"快思考出错: {e}")
            import traceback
            traceback.print_exc()
            return "嗯...", None
    
    async def _deep_think_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict]) -> Tuple[str, Optional[List[Dict]]]:
        """带工具调用的深度思考"""
        try:
            print(f"🧠 启动深度思考 (模型: {self.deep_model_name})...")
            self.log(f"启动深度思考 (模型: {self.deep_model_name})...")
            
            # 为深度思考添加更详细的系统提示
            enhanced_messages = messages.copy()
            if enhanced_messages[0]["role"] == "system":
                enhanced_messages[0]["content"] += """

请进行深入思考，考虑以下要点：
1. 理解用户的真实意图
2. 分析所需的具体操作步骤  
3. 如果用户提供了表单信息，请使用send_message_to_computer_agent工具发送给Computer Agent
4. 提供准确、详细的回应"""
            
            response = await self.client.chat.completions.create(
                model=self.deep_model_name,
                messages=enhanced_messages,
                tools=tools,
                tool_choice="auto",
                stream=False,
                max_tokens=1000,
                temperature=0.3,
                timeout=30
            )
            
            message = response.choices[0].message
            content = message.content or ""
            tool_calls = message.tool_calls if hasattr(message, 'tool_calls') else None
            
            print(f"🧠 深度思考完成: '{content[:50]}...'")
            if tool_calls:
                print(f"🔧 深度思考生成了 {len(tool_calls)} 个工具调用")
                
            self.log(f"深度思考完成: {content}")
            return content.strip(), tool_calls
            
        except Exception as e:
            print(f"❌ 深度思考出错: {e}")
            self.log(f"深度思考出错: {e}")
            import traceback
            traceback.print_exc()
            return "让我想想...啊，抱歉，我刚刚走神了。", None
    
    async def _handle_tool_calls(self, tool_calls: List[Dict], user_text: str, from_fast_thinking: bool = False):
        """处理工具调用"""
        try:
            from dual_agent.common.tool_calling import send_message_to_computer_agent
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 执行工具调用: {function_name}")
                print(f"   参数: {function_args}")
                
                if function_name == "send_message_to_computer_agent":
                    # 添加原始用户输入到参数中
                    function_args["additional_data"] = function_args.get("additional_data", {})
                    function_args["additional_data"]["original_user_input"] = user_text
                    function_args["additional_data"]["from_fast_thinking"] = from_fast_thinking
                    
                    # 调用工具函数
                    result = await send_message_to_computer_agent(**function_args)
                    
                    if result.get("success"):
                        print(f"✅ 工具调用成功: {function_name}")
                    else:
                        print(f"❌ 工具调用失败: {result.get('error')}")
                        
        except Exception as e:
            print(f"❌ 处理工具调用时出错: {e}")
            self.log(f"处理工具调用失败: {e}")

    async def _fast_think_simple(self, prompt: str) -> Tuple[str, str]:
        """简单快思考 - 用于消息转换等简单任务"""
        try:
            messages = [
                {"role": "system", "content": "你是一个专门处理消息转换的助手，请按照用户要求精确转换消息。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.fast_model_name,
                messages=messages,
                stream=False,  # 不使用流式以简化处理
                max_tokens=100,  # 消息转换通常不需要太多token
                temperature=0.3,  # 低温度确保一致性
                timeout=8  # 8秒超时
            )
            
            content = response.choices[0].message.content or ""
            return content.strip(), content.strip()
            
        except Exception as e:
            self.log(f"简单快思考失败: {e}")
            return "", ""

    async def _fast_think(self, messages: List[Dict[str, str]]) -> str:
        """快思考路径 - 优化用于低延迟快速响应"""
        try:
            print(f"⚡ 启动快思考 (模型: {self.fast_model_name})...")
            self.log(f"启动快思考 (模型: {self.fast_model_name})...")
            response = await self.client.chat.completions.create(
                model=self.fast_model_name,
                messages=messages,
                stream=True,  # 启用流式响应以提高响应速度
                max_tokens=150,  # 限制token数量以减少延迟
                temperature=0.7,  # 适中的创造性
                timeout=10  # 10秒超时
            )
            
            print("🔄 正在接收快思考流式响应...")
            # 处理流式响应
            content = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
            
            print(f"⚡ 快思考完成: '{content[:50]}...'")
            self.log(f"快思考完成: {content}")
            return content.strip()
        except Exception as e:
            print(f"❌ 快思考出错: {e}")
            self.log(f"快思考出错: {e}")
            import traceback
            traceback.print_exc()
            return "嗯..."

    async def _deep_think(self, messages: List[Dict[str, str]]) -> str:
        """深度思考路径 - 优化用于复杂推理和任务规划"""
        try:
            print(f"🧠 启动深度思考 (模型: {self.deep_model_name})...")
            self.log(f"启动深度思考 (模型: {self.deep_model_name})...")
            
            # 为深度思考添加更详细的系统提示
            enhanced_messages = messages.copy()
            if enhanced_messages[0]["role"] == "system":
                enhanced_messages[0]["content"] += "\n\n请进行深入思考，考虑以下要点：\n1. 理解用户的真实意图\n2. 分析所需的具体操作步骤\n3. 考虑可能的异常情况\n4. 提供准确、详细的回应"
            
            response = await self.client.chat.completions.create(
                model=self.deep_model_name,
                messages=enhanced_messages,
                stream=False,  # 深度思考不需要流式响应
                max_tokens=1000,  # 允许更长的回应
                temperature=0.3,  # 较低的创造性，提高准确性
                timeout=30  # 30秒超时，允许更长的思考时间
            )
            content = response.choices[0].message.content
            print(f"🧠 深度思考完成: '{content[:50]}...'")
            self.log(f"深度思考完成: {content}")
            return content.strip()
        except Exception as e:
            print(f"❌ 深度思考出错: {e}")
            self.log(f"深度思考出错: {e}")
            import traceback
            traceback.print_exc()
            return "让我想想...啊，抱歉，我刚刚走神了。"

    async def generate_filler(self) -> str:
        """生成填充语"""
        try:
            response = await self.client.chat.completions.create(
                model=self.fast_model_name,
                messages=[
                    {"role": "system", "content": "你是一个对话填充语生成助手。"},
                    {"role": "user", "content": "生成一个简短、自然、表示正在思考的填充语，例如'嗯...'、'让我想想看'等。"}
                ],
                max_tokens=10,
                stream=False
            )
            filler = response.choices[0].message.content.strip(' "\'')
            return filler
        except Exception as e:
            self.log(f"填充语生成出错: {e}")
            return "嗯..."

    async def _extract_and_send_form_data_fast(self, message_queue, user_text: str, fast_response: str):
        """快思考完成后立即提取表单数据并发送给Computer Agent"""
        try:
            import uuid
            print("🚀 快思考完成，立即检查表单信息...")
            
            # 扩展的表单相关关键词
            form_keywords = [
                "填写", "表单", "输入", "名字", "姓名", "邮箱", "email", "电话", "手机", "地址", "提交", "填表", "开始填",
                "披萨", "pizza", "尺寸", "size", "small", "medium", "large", "小号", "中号", "大号",
                "配料", "topping", "toppings", "培根", "bacon", "奶酪", "cheese", "洋葱", "onion", "蘑菇", "mushroom",
                "送达", "delivery", "配送", "时间", "说明", "instructions", "备注", "comments"
            ]
            has_form_keyword = any(keyword in user_text for keyword in form_keywords)
            
            # 使用智能信息提取（简化版，避免提及不存在的字段）
            extracted_data = self._extract_basic_form_data_from_text(user_text)
            
            if has_form_keyword or extracted_data:
                print(f"📝 快思考阶段检测到表单相关操作或数据: {extracted_data}")
                
                # 立即发送消息给Computer Agent
                from dual_agent.common.messaging import A2AMessage, MessageType, MessageSource
                
                message = A2AMessage(
                    source=MessageSource.PHONE,
                    type=MessageType.ACTION,
                    task_id=str(uuid.uuid4()),
                    content={
                        "action": "fill_form",
                        "user_input": user_text,
                        "ai_fast_response": fast_response,  # 使用快思考的回应
                        "extracted_data": extracted_data,
                        "immediate": True,  # 标记为立即执行
                        "from_fast_thinking": True  # 标记来自快思考
                    }
                )
                
                await message_queue.send_to_computer(message)
                print(f"⚡ 已从快思考阶段发送表单操作指令给Computer Agent")
                self.log(f"⚡ Sent fast form instruction to Computer Agent: {user_text}")
                
                # 如果提取到了具体数据，记录确认信息
                if extracted_data:
                    data_summary = ", ".join([f"{k}: {v}" for k, v in extracted_data.items()])
                    print(f"📢 快速确认: 正在处理 {data_summary}")
                
        except Exception as e:
            self.log(f"快思考阶段发送Computer Agent指令时出错: {e}")
            print(f"❌ 快思考阶段发送Computer Agent指令时出错: {e}")
    
    def _extract_basic_form_data_from_text(self, text):
        """从文本中提取基础表单数据（避免提及不存在的字段）"""
        import re
        
        extracted = {}
        text_lower = text.lower()
        
        print(f"🔍 快思考阶段提取表单数据，输入文本: '{text}'")
        
        # 姓名提取 - 更灵活的模式
        name_patterns = [
            r'(?:我叫|我的名字是|名字是|姓名是|我是)([^，,。\s]{1,10})',
            r'(?:叫|名字)([^，,。\s]{1,10})',
            r'(?:姓名|名字)(?:填写|填入|是|为)([^，,。\s]{1,10})',  # 新增：姓名填写张三
            r'(?:填写|填入)(?:姓名|名字)([^，,。\s]{1,10})',     # 新增：填写姓名张三
            r'([^，,。\s]{1,10})(?:是我的名字|是我的姓名)',      # 新增：张三是我的名字
            r'姓名([^，,。\s]{1,10})',                         # 新增：姓名张三
            r'名字([^，,。\s]{1,10})',                         # 新增：名字张三
        ]
        for i, pattern in enumerate(name_patterns):
            print(f"   尝试姓名模式 {i+1}: {pattern}")
            matches = re.findall(pattern, text)
            if matches:
                name = matches[0].strip()
                if len(name) <= 10 and name:  # 合理的名字长度
                    extracted["name"] = name
                    extracted["custname"] = name
                    print(f"   ✅ 匹配成功，提取姓名: {name}")
                break
            else:
                print(f"   ❌ 模式不匹配")
        
        # 邮箱提取
        print(f"   📧 开始邮箱提取...")
        # 先尝试标准邮箱格式
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            extracted["email"] = emails[0]
            extracted["custemail"] = emails[0]
            print(f"   ✅ 提取标准邮箱: {emails[0]}")
        else:
            print(f"   ❌ 未找到标准邮箱格式")
            
            # 如果没有找到标准格式，尝试提取用户明确说明的邮箱
            email_statement_patterns = [
                r'(?:邮箱是|邮箱为|email是|email为|电子邮箱是)([^\s,，。]+)',
                r'(?:邮箱|email)[:：]([^\s,，。]+)',
                r'(?:填写|填入)(?:邮箱|email)([^\s,，。]+)',
            ]
            
            for i, pattern in enumerate(email_statement_patterns):
                print(f"   尝试邮箱声明模式 {i+1}: {pattern}")
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    email_value = matches[0].strip()
                    if email_value:
                        extracted["email"] = email_value
                        extracted["custemail"] = email_value
                        print(f"   ✅ 提取声明邮箱: {email_value}")
                    break
                else:
                    print(f"   ❌ 邮箱声明模式不匹配")
            
            if "email" not in extracted:
                print(f"   ❌ 未找到任何邮箱信息")
        
        # 电话号码提取
        print(f"   🔍 开始电话号码提取...")
        phone_patterns = [
            r'\b(?:\+?86[-.\\s]?)?1[3-9]\d{9}\b',  # 中国手机号
            r'\b(?:\+?1[-.\\s]?)?\(?[0-9]{3}\)?[-.\\s]?[0-9]{3}[-.\\s]?[0-9]{4}\b',  # 美国电话
        ]
        
        phone_found = False
        for i, pattern in enumerate(phone_patterns):
            print(f"   尝试标准电话模式 {i+1}: {pattern}")
            phones = re.findall(pattern, text, re.IGNORECASE)
            if phones:
                phone = re.sub(r'[-.\\s()]+', '', phones[0])
                extracted["phone"] = phone
                extracted["custtel"] = phone
                print(f"   ✅ 提取标准电话: {phone}")
                phone_found = True
                break
            else:
                print(f"   ❌ 标准电话模式不匹配")
        
        # 如果没有找到标准格式，尝试提取用户明确说明的电话
        if not phone_found:
            phone_statement_patterns = [
                r'(?:电话是|电话为|手机是|手机为|联系方式是)([0-9]+)',
                r'(?:电话|手机|联系方式)[:：]([0-9]+)',
                r'(?:填写|填入)(?:电话|手机)([0-9]+)',
                r'([0-9]{4,15})(?:是我的电话|是我的手机)',
            ]
            
            for i, pattern in enumerate(phone_statement_patterns):
                print(f"   尝试电话声明模式 {i+1}: {pattern}")
                phones = re.findall(pattern, text, re.IGNORECASE)
                if phones:
                    phone = re.sub(r'[-.\\s()]+', '', phones[0])
                    if len(phone) >= 4:  # 至少4位数字
                        extracted["phone"] = phone
                        extracted["custtel"] = phone
                        print(f"   ✅ 提取声明电话: {phone}")
                        phone_found = True
                    break
                else:
                    print(f"   ❌ 电话声明模式不匹配")
        
        if not phone_found:
            print(f"   ❌ 未找到任何电话信息")
        
        # Pizza尺寸提取
        print(f"   🍕 开始Pizza尺寸提取...")
        size_patterns = [
            r'(?:披萨|pizza)(?:尺寸|大小|size)(?:是|选择|要|为)?(小号|中号|大号|small|medium|large)',
            r'(?:选择|要|想要)(小号|中号|大号|small|medium|large)(?:的)?(?:披萨|pizza)?',
            r'(?:尺寸|大小|size)(?:是|选择|要|为)?(小号|中号|大号|small|medium|large)',
            r'(小号|中号|大号|small|medium|large)(?:披萨|pizza|的披萨)?',
            r'(?:我想要|我要)(?:一个)?(小号|中号|大号|small|medium|large)',
        ]
        
        for i, pattern in enumerate(size_patterns):
            print(f"   尝试尺寸模式 {i+1}: {pattern}")
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                size_value = matches[0].strip().lower()
                print(f"   🎯 匹配到尺寸值: {size_value}")
                # 标准化尺寸值
                size_mapping = {
                    '小号': 'small', '中号': 'medium', '大号': 'large',
                    'small': 'small', 'medium': 'medium', 'large': 'large'
                }
                if size_value in size_mapping:
                    extracted["size"] = size_mapping[size_value]
                    # 不要重复添加 pizza_size，避免重复处理
                    print(f"   ✅ 提取Pizza尺寸: {size_mapping[size_value]}")
                break
            else:
                print(f"   ❌ 尺寸模式不匹配")
        
        # Pizza配料提取
        print(f"   🥓 开始Pizza配料提取...")
        toppings_patterns = [
            r'(?:配料|topping|toppings?)(?:是|要|选择|加)([^,，。]+)',
            r'(?:加|要|选择)(?:配料|topping)?([^,，。]*(?:培根|bacon|奶酪|cheese|洋葱|onion|蘑菇|mushroom)[^,，。]*)',
            r'(培根|bacon|奶酪|cheese|洋葱|onion|蘑菇|mushroom)(?:配料)?',
            r'(?:和|加上|还有|以及)([^,，。]*(?:培根|bacon|奶酪|cheese|洋葱|onion|蘑菇|mushroom)[^,，。]*)',
        ]
        
        toppings = []
        for i, pattern in enumerate(toppings_patterns):
            print(f"   尝试配料模式 {i+1}: {pattern}")
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                topping_text = match.strip().lower()
                print(f"   🔍 分析配料文本: '{topping_text}'")
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
                        print(f"   ✅ 找到配料: {key} -> {value}")
        
        if toppings:
            extracted["toppings"] = toppings
            # 不要重复添加 pizza_toppings，避免重复处理
            print(f"   🍕 提取Pizza配料: {toppings}")
        else:
            print(f"   ❌ 未找到Pizza配料")
        
        # 送达时间提取
        print(f"   ⏰ 开始送达时间提取...")
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
        
        for i, pattern in enumerate(delivery_time_patterns):
            print(f"   尝试时间模式 {i+1}: {pattern}")
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
                
                extracted["delivery_time"] = normalized_time
                extracted["preferred_delivery_time"] = normalized_time  # 添加这个字段以匹配实际网页
                print(f"   ✅ 提取送达时间: {time_value} -> 标准化: {normalized_time}")
                break
            else:
                print(f"   ❌ 时间模式不匹配")

        # 配送说明提取
        print(f"   📝 开始配送说明提取...")
        delivery_instructions_patterns = [
            r'(?:配送说明|delivery instructions|送货说明)(?:是|为)?([^,，。]+)',
            r'(?:说明|instructions|备注|comments?)([^,，。]+)',
        ]
        
        for i, pattern in enumerate(delivery_instructions_patterns):
            print(f"   尝试说明模式 {i+1}: {pattern}")
            matches = re.findall(pattern, text)
            if matches:
                instructions = matches[0].strip()
                extracted["delivery_instructions"] = instructions
                # 不要重复添加 comments，避免重复处理
                print(f"   ✅ 提取配送说明: {instructions}")
                break
            else:
                print(f"   ❌ 说明模式不匹配")
        
        # 评论/消息内容提取（仅限明确相关的字段）
        print(f"   💬 开始消息内容提取...")
        message_patterns = [
            r'(?:评论是|留言是|消息内容是)([^。，,]{5,100})',
            r'(?:评论|留言)[:：]([^。，,]{5,100})',
        ]
        for i, pattern in enumerate(message_patterns):
            print(f"   尝试消息模式 {i+1}: {pattern}")
            matches = re.findall(pattern, text)
            if matches:
                message = matches[0].strip()
                if message:
                    extracted["message"] = message
                    extracted["comments"] = message
                    print(f"   ✅ 提取消息: {message}")
                break
            else:
                print(f"   ❌ 消息模式不匹配")
        
        if extracted:
            print(f"📊 快思考阶段提取到基础表单数据: {extracted}")
        else:
            print(f"⚠️ 快思考阶段未提取到任何表单数据")
        
        return extracted 