"""
页面分析模块

基于多模态LLM和页面内容分析，理解网页结构和元素，支持智能的表单填写和页面操作
"""

import asyncio
import base64
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto
from dataclasses import dataclass, field

import openai
from bs4 import BeautifulSoup
from PIL import Image
import io

from dual_agent.computer_agent.browser_automation import BrowserAutomation, ActionResult

class LLMProvider(Enum):
    """LLM提供商枚举"""
    OPENAI = auto()
    ANTHROPIC = auto()
    SILICONFLOW = auto()
    DOUBAO = auto()
    DUMMY = auto()

class ElementType(Enum):
    """页面元素类型枚举"""
    INPUT_TEXT = auto()
    INPUT_EMAIL = auto()
    INPUT_PASSWORD = auto()
    INPUT_NUMBER = auto()
    INPUT_DATE = auto()
    INPUT_PHONE = auto()
    TEXTAREA = auto()
    SELECT = auto()
    BUTTON = auto()
    LINK = auto()
    CHECKBOX = auto()
    RADIO = auto()
    UNKNOWN = auto()

@dataclass
class PageElement:
    """页面元素信息"""
    id: str
    element_type: ElementType
    selector: str
    text: str = ""
    placeholder: str = ""
    value: str = ""
    required: bool = False
    label: str = ""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FormInfo:
    """表单信息"""
    id: str
    action: str
    method: str
    elements: List[PageElement] = field(default_factory=list)
    completion_rate: float = 0.0

@dataclass
class PageAnalysis:
    """页面分析结果"""
    url: str
    title: str
    forms: List[FormInfo] = field(default_factory=list)
    interactive_elements: List[PageElement] = field(default_factory=list)
    main_content: str = ""
    page_type: str = "unknown"
    analysis_confidence: float = 0.0
    suggestions: List[str] = field(default_factory=list)

class PageAnalyzer:
    """
    页面分析器
    
    结合多模态LLM和传统页面解析，实现智能的页面理解和元素识别
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider = LLMProvider.DOUBAO,
        model_name: str = "Doubao-1.5-Pro",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        debug: bool = False
    ):
        """
        初始化页面分析器
        
        参数:
            llm_provider: LLM提供商
            model_name: 模型名称
            api_key: API密钥
            debug: 是否调试模式
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.api_key = api_key
        self.debug = debug
        
        # 初始化LLM客户端
        self.api_base = api_base
        self.api_key = self._get_api_key()
        if not self.api_key:
            raise ValueError(f"未提供{self.llm_provider.name} API密钥，请通过api_key参数或环境变量设置")

        if self.llm_provider == LLMProvider.OPENAI:
            self.llm_client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self.llm_client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ValueError("Anthropic SDK not installed. Please install with 'pip install anthropic'")
        elif self.llm_provider == LLMProvider.SILICONFLOW:
            self.llm_client = openai.AsyncOpenAI(api_key=self.api_key, base_url="https://api.siliconflow.cn/v1")
        elif self.llm_provider == LLMProvider.DOUBAO:
            self.llm_client = openai.AsyncOpenAI(api_key=self.api_key, base_url="https://ark.cn-beijing.volces.com/api/v3")
        else:
            self.llm_client = None
    
    def _get_api_key(self) -> Optional[str]:
        """从环境变量或参数获取API密钥"""
        if self.api_key:
            return self.api_key
        if self.llm_provider == LLMProvider.OPENAI:
            return os.environ.get("OPENAI_API_KEY")
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            return os.environ.get("ANTHROPIC_API_KEY")
        elif self.llm_provider == LLMProvider.SILICONFLOW:
            return os.environ.get("SILICONFLOW_API_KEY")
        elif self.llm_provider == LLMProvider.DOUBAO:
            return os.environ.get("VOLC_API_KEY")
        return None

    async def analyze_page(
        self,
        browser: BrowserAutomation,
        use_vision: bool = True,
        analysis_goals: Optional[List[str]] = None
    ) -> PageAnalysis:
        """
        分析页面内容和结构
        
        参数:
            browser: 浏览器自动化实例
            use_vision: 是否使用视觉分析(需要多模态LLM)
            analysis_goals: 分析目标列表
            
        返回:
            页面分析结果
        """
        self.log("开始页面分析")
        
        # 提取基础页面信息
        content_result = await browser.extract_page_content()
        if not content_result.success:
            self.log("页面内容提取失败")
            return PageAnalysis(
                url=browser.current_url,
                title=browser.page_title,
                analysis_confidence=0.0
            )
        
        page_data = content_result.data
        
        # 解析DOM结构
        dom_analysis = self._analyze_dom_structure(page_data)
        
        # 视觉分析(如果启用)
        vision_analysis = None
        if use_vision and self.llm_client:
            screenshot_result = await browser.take_screenshot()
            if screenshot_result.success:
                vision_analysis = await self._analyze_page_visually(
                    screenshot_result.data["screenshot"],
                    page_data,
                    analysis_goals
                )
        
        # 合并分析结果
        final_analysis = self._merge_analysis_results(
            dom_analysis,
            vision_analysis,
            page_data
        )
        
        self.log(f"页面分析完成，发现 {len(final_analysis.forms)} 个表单")
        return final_analysis
    
    def _analyze_dom_structure(self, page_data: Dict[str, Any]) -> PageAnalysis:
        """
        分析DOM结构
        
        参数:
            page_data: 页面数据
            
        返回:
            基础分析结果
        """
        self.log("分析DOM结构")
        
        analysis = PageAnalysis(
            url=page_data["url"],
            title=page_data["title"],
            main_content=page_data["text"][:1000]  # 前1000字符
        )
        
        # 分析表单
        for form_data in page_data.get("forms", []):
            form_info = FormInfo(
                id=form_data["id"],
                action=form_data["action"],
                method=form_data["method"]
            )
            
            # 分析表单元素
            for element_data in form_data["elements"]:
                element = self._parse_form_element(element_data)
                form_info.elements.append(element)
            
            # 计算表单完成率
            if form_info.elements:
                filled_count = sum(1 for elem in form_info.elements if elem.value)
                form_info.completion_rate = filled_count / len(form_info.elements)
            
            analysis.forms.append(form_info)
        
        # 分析可交互元素
        for element_data in page_data.get("clickable_elements", []):
            element = PageElement(
                id=element_data.get("id", ""),
                element_type=ElementType.BUTTON if element_data["tag"] == "button" else ElementType.LINK,
                selector=f'#{element_data["id"]}' if element_data.get("id") else f'.{element_data.get("class", "").split()[0]}',
                text=element_data.get("text", ""),
                x=element_data.get("x", 0),
                y=element_data.get("y", 0),
                width=element_data.get("width", 0),
                height=element_data.get("height", 0),
                confidence=0.8
            )
            analysis.interactive_elements.append(element)
        
        # 判断页面类型
        analysis.page_type = self._classify_page_type(page_data)
        analysis.analysis_confidence = 0.7  # DOM分析基础置信度
        
        return analysis
    
    def _parse_form_element(self, element_data: Dict[str, Any]) -> PageElement:
        """
        解析表单元素
        
        参数:
            element_data: 元素数据
            
        返回:
            页面元素对象
        """
        # 确定元素类型
        tag = element_data.get("tag", "").lower()
        input_type = element_data.get("type", "").lower()
        
        if tag == "input":
            type_mapping = {
                "text": ElementType.INPUT_TEXT,
                "email": ElementType.INPUT_EMAIL,
                "password": ElementType.INPUT_PASSWORD,
                "number": ElementType.INPUT_NUMBER,
                "tel": ElementType.INPUT_PHONE,
                "date": ElementType.INPUT_DATE,
                "checkbox": ElementType.CHECKBOX,
                "radio": ElementType.RADIO,
            }
            element_type = type_mapping.get(input_type, ElementType.INPUT_TEXT)
        elif tag == "textarea":
            element_type = ElementType.TEXTAREA
        elif tag == "select":
            element_type = ElementType.SELECT
        else:
            element_type = ElementType.UNKNOWN
        
        # 生成选择器 - 优先使用name属性
        element_id = element_data.get("id", "")
        element_name = element_data.get("name", "")
        
        if element_name:
            selector = f'[name="{element_name}"]'
        elif element_id:
            selector = f'#{element_id}'
        else:
            selector = f'{tag}[type="{input_type}"]' if input_type else tag
        
        return PageElement(
            id=element_name or element_id or f"element_{hash(str(element_data))}",
            element_type=element_type,
            selector=selector,
            text=element_data.get("label", ""),
            placeholder=element_data.get("placeholder", ""),
            value=element_data.get("value", ""),
            required=element_data.get("required", False),
            label=element_data.get("label", ""),
            confidence=0.9
        )
    
    def _classify_page_type(self, page_data: Dict[str, Any]) -> str:
        """
        分类页面类型
        
        参数:
            page_data: 页面数据
            
        返回:
            页面类型
        """
        title = page_data.get("title", "").lower()
        text = page_data.get("text", "").lower()
        forms = page_data.get("forms", [])
        
        # 简单的页面类型判断
        if "login" in title or "sign in" in title:
            return "login"
        elif "register" in title or "sign up" in title:
            return "registration"
        elif "contact" in title or "contact us" in text:
            return "contact"
        elif "checkout" in title or "payment" in text:
            return "checkout"
        elif len(forms) > 0:
            return "form"
        elif "search" in text or "results" in title:
            return "search"
        else:
            return "content"
    
    async def _analyze_page_visually(
        self,
        screenshot_base64: str,
        page_data: Dict[str, Any],
        analysis_goals: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用多模态LLM进行视觉分析
        
        参数:
            screenshot_base64: base64编码的截图
            page_data: 页面数据
            analysis_goals: 分析目标
            
        返回:
            视觉分析结果
        """
        if not self.llm_client:
            return None
        
        try:
            self.log("进行视觉分析")
            
            # 构建分析提示
            goals_text = ""
            if analysis_goals:
                goals_text = f"特别关注以下目标: {', '.join(analysis_goals)}"
            
            system_prompt = f"""
            你是一个专业的网页分析助手。请分析这个网页截图，重点识别：
            1. 表单字段及其用途
            2. 可交互元素的功能
            3. 页面的主要目的和类型
            4. 用户可能需要执行的操作
            
            {goals_text}
            
            请提供JSON格式的分析结果，包含:
            - page_purpose: 页面主要目的
            - form_fields: 表单字段列表，每个包含 name, type, purpose, importance
            - interactive_elements: 可交互元素列表
            - suggested_actions: 建议的操作步骤
            - confidence: 分析置信度(0-1)
            """
            
            user_prompt = f"""
            页面标题: {page_data.get('title', 'Unknown')}
            页面URL: {page_data.get('url', 'Unknown')}
            
            请分析这个网页截图并提供详细的结构化分析。
            """
            
            # 调用多模态LLM
            if self.llm_provider in [LLMProvider.OPENAI, LLMProvider.SILICONFLOW, LLMProvider.DOUBAO]:
                response = await self.llm_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{screenshot_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )
                
                result_text = response.choices[0].message.content
                
                # 尝试解析JSON
                try:
                    # 提取JSON部分
                    start_idx = result_text.find('{')
                    end_idx = result_text.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_text = result_text[start_idx:end_idx]
                        return json.loads(json_text)
                except json.JSONDecodeError:
                    self.log("无法解析LLM返回的JSON")
                    return {"raw_response": result_text}
        
        except Exception as e:
            self.log(f"视觉分析失败: {str(e)}")
            return None
    
    def _merge_analysis_results(
        self,
        dom_analysis: PageAnalysis,
        vision_analysis: Optional[Dict[str, Any]],
        page_data: Dict[str, Any]
    ) -> PageAnalysis:
        """
        合并DOM分析和视觉分析结果
        
        参数:
            dom_analysis: DOM分析结果
            vision_analysis: 视觉分析结果
            page_data: 页面数据
            
        返回:
            合并后的分析结果
        """
        self.log("合并分析结果")
        
        result = dom_analysis
        
        if vision_analysis:
            # 更新页面类型和目的
            if "page_purpose" in vision_analysis:
                result.page_type = vision_analysis["page_purpose"]
            
            # 增强表单字段信息
            vision_fields = vision_analysis.get("form_fields", [])
            for vision_field in vision_fields:
                # 尝试匹配DOM中的表单字段
                for form in result.forms:
                    for element in form.elements:
                        if self._fields_match(element, vision_field):
                            # 更新元素信息
                            element.metadata["purpose"] = vision_field.get("purpose", "")
                            element.metadata["importance"] = vision_field.get("importance", "medium")
                            element.confidence = min(element.confidence + 0.2, 1.0)
            
            # 添加建议操作
            suggested_actions = vision_analysis.get("suggested_actions", [])
            result.suggestions.extend(suggested_actions)
            
            # 更新置信度
            vision_confidence = vision_analysis.get("confidence", 0.5)
            result.analysis_confidence = (result.analysis_confidence + vision_confidence) / 2
        
        return result
    
    def _fields_match(self, dom_element: PageElement, vision_field: Dict[str, Any]) -> bool:
        """
        判断DOM元素和视觉分析字段是否匹配
        
        参数:
            dom_element: DOM元素
            vision_field: 视觉分析字段
            
        返回:
            是否匹配
        """
        vision_name = vision_field.get("name", "").lower()
        vision_type = vision_field.get("type", "").lower()
        
        # 简单的匹配逻辑
        element_text = (dom_element.text + dom_element.placeholder + dom_element.label).lower()
        element_type = dom_element.element_type.name.lower()
        
        # 名称匹配
        if vision_name in element_text or any(word in element_text for word in vision_name.split()):
            return True
        
        # 类型匹配
        type_mapping = {
            "email": "input_email",
            "password": "input_password",
            "text": "input_text",
            "number": "input_number",
        }
        
        if type_mapping.get(vision_type) == element_type:
            return True
        
        return False
    
    async def suggest_form_completion(
        self,
        page_analysis: PageAnalysis,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        建议表单填写方案
        
        参数:
            page_analysis: 页面分析结果
            user_data: 用户数据
            
        返回:
            表单填写建议
        """
        self.log("生成表单填写建议")
        
        suggestions = {
            "form_actions": [],
            "missing_data": [],
            "confidence": 0.0
        }
        
        for form in page_analysis.forms:
            form_suggestion = {
                "form_id": form.id,
                "actions": [],
                "completion_possible": True
            }
            
            for element in form.elements:
                action = self._suggest_element_action(element, user_data)
                if action:
                    form_suggestion["actions"].append(action)
                elif element.required:
                    suggestions["missing_data"].append({
                        "element_id": element.id,
                        "label": element.label or element.placeholder,
                        "type": element.element_type.name
                    })
                    form_suggestion["completion_possible"] = False
            
            suggestions["form_actions"].append(form_suggestion)
        
        # 计算总体置信度
        total_actions = sum(len(f["actions"]) for f in suggestions["form_actions"])
        if total_actions > 0:
            suggestions["confidence"] = min(0.9, total_actions * 0.1)
        
        return suggestions
    
    def _suggest_element_action(
        self,
        element: PageElement,
        user_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        为单个元素建议操作
        
        参数:
            element: 页面元素
            user_data: 用户数据
            
        返回:
            操作建议或None
        """
        # 基于元素类型和标签匹配用户数据
        element_text = (element.text + element.placeholder + element.label).lower()
        
        # 常见字段映射
        field_mappings = {
            "name": ["name", "full_name", "full name", "姓名", "用户名"],
            "first_name": ["first_name", "first name", "given name", "名"],
            "last_name": ["last_name", "last name", "family name", "surname", "姓"],
            "email": ["email", "e-mail", "mail", "邮箱", "电子邮件"],
            "phone": ["phone", "telephone", "mobile", "手机", "电话"],
            "address": ["address", "street", "地址"],
            "city": ["city", "城市"],
            "country": ["country", "国家"],
            "company": ["company", "organization", "公司", "组织"],
        }
        
        for data_key, keywords in field_mappings.items():
            if any(keyword in element_text for keyword in keywords):
                if data_key in user_data:
                    return {
                        "type": "fill",
                        "selector": element.selector,
                        "value": str(user_data[data_key]),
                        "confidence": element.confidence
                    }
        
        return None
    
    def log(self, message: str) -> None:
        """
        记录日志
        
        参数:
            message: 日志消息
        """
        if self.debug:
            print(f"[PageAnalyzer] {message}")