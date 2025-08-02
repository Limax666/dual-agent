"""
工具调用通信机制

实现Phone Agent和Computer Agent之间基于工具调用的通信
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum, auto


class MessageType(Enum):
    """消息类型枚举"""
    USER_INPUT = "user_input"           # 用户输入消息
    SYSTEM_STATUS = "system_status"     # 系统状态消息
    TASK_RESULT = "task_result"         # 任务执行结果
    ERROR = "error"                     # 错误消息
    FORM_DATA = "form_data"            # 表单数据消息
    PAGE_ANALYSIS = "page_analysis"     # 页面分析消息
    TASK_COMPLETION = "task_completion" # 任务完成通知消息


@dataclass
class ToolMessage:
    """工具调用消息格式"""
    message_id: str
    message_type: MessageType
    sender: str  # "phone_agent" 或 "computer_agent"
    recipient: str  # "phone_agent" 或 "computer_agent"
    content: Dict[str, Any]
    timestamp: float
    task_id: Optional[str] = None


class ToolCallHandler:
    """工具调用处理器"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
    def register_handler(self, message_type: MessageType, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        
    async def start_listening(self):
        """开始监听消息"""
        self.running = True
        while self.running:
            try:
                # 等待消息
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ {self.agent_name} 处理消息时出错: {e}")
                
    async def _handle_message(self, message: ToolMessage):
        """处理接收到的消息"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                print(f"❌ {self.agent_name} 消息处理器执行失败: {e}")
        else:
            print(f"⚠️ {self.agent_name} 没有找到 {message.message_type.value} 类型的处理器")
            
    async def send_message(self, recipient: str, message_type: MessageType, 
                          content: Dict[str, Any], task_id: Optional[str] = None) -> ToolMessage:
        """发送消息到另一个Agent"""
        message = ToolMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender=self.agent_name,
            recipient=recipient,
            content=content,
            timestamp=time.time(),
            task_id=task_id
        )
        
        # 找到目标Agent的处理器并发送消息
        target_handler = get_agent_handler(recipient)
        if target_handler:
            await target_handler.receive_message(message)
            print(f"📤 {self.agent_name} -> {recipient}: {message_type.value}")
            return message
        else:
            raise Exception(f"找不到目标Agent: {recipient}")
            
    async def receive_message(self, message: ToolMessage):
        """接收来自另一个Agent的消息"""
        await self.message_queue.put(message)
        print(f"📥 {self.agent_name} <- {message.sender}: {message.message_type.value}")
        
    def stop(self):
        """停止监听"""
        self.running = False


# 全局Agent处理器注册表
_agent_handlers: Dict[str, ToolCallHandler] = {}


def register_agent_handler(agent_name: str, handler: ToolCallHandler):
    """注册Agent处理器"""
    _agent_handlers[agent_name] = handler
    print(f"✅ 注册Agent处理器: {agent_name}")
    print(f"   当前已注册的处理器: {list(_agent_handlers.keys())}")


def get_agent_handler(agent_name: str) -> Optional[ToolCallHandler]:
    """获取Agent处理器"""
    return _agent_handlers.get(agent_name)


# 工具调用函数定义
async def send_message_to_computer_agent(
    message: str,
    message_type: str = "user_input",
    task_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Phone Agent调用此工具发送消息给Computer Agent
    
    Args:
        message: 要发送的消息内容
        message_type: 消息类型
        task_id: 任务ID（可选）
        additional_data: 额外数据（可选）
        
    Returns:
        发送结果
    """
    try:
        # 获取Phone Agent的处理器，带重试机制
        phone_handler = get_agent_handler("phone_agent")
        if not phone_handler:
            # 等待一小段时间再重试（处理异步注册时机问题）
            await asyncio.sleep(0.1)
            phone_handler = get_agent_handler("phone_agent")
            
        if not phone_handler:
            # 调试信息：显示当前注册的处理器
            registered_agents = list(_agent_handlers.keys())
            return {"success": False, "error": f"Phone Agent处理器未注册，当前已注册: {registered_agents}"}
            
        # 构建消息内容
        content = {
            "text": message,
            "timestamp": time.time()
        }
        
        if additional_data:
            content.update(additional_data)
            
        # 发送消息
        msg_type = MessageType(message_type) if message_type in [t.value for t in MessageType] else MessageType.USER_INPUT
        sent_message = await phone_handler.send_message(
            recipient="computer_agent",
            message_type=msg_type,
            content=content,
            task_id=task_id
        )
        
        return {
            "success": True,
            "message_id": sent_message.message_id,
            "sent_at": sent_message.timestamp
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def send_message_to_phone_agent(
    message: str,
    message_type: str = "task_result",
    task_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computer Agent调用此工具发送消息给Phone Agent
    
    Args:
        message: 要发送的消息内容
        message_type: 消息类型
        task_id: 任务ID（可选）
        additional_data: 额外数据（可选）
        
    Returns:
        发送结果
    """
    try:
        # 获取Computer Agent的处理器
        computer_handler = get_agent_handler("computer_agent")
        if not computer_handler:
            return {"success": False, "error": "Computer Agent处理器未注册"}
            
        # 构建消息内容
        content = {
            "text": message,
            "timestamp": time.time()
        }
        
        if additional_data:
            content.update(additional_data)
            
        # 发送消息
        msg_type = MessageType(message_type) if message_type in [t.value for t in MessageType] else MessageType.TASK_RESULT
        sent_message = await computer_handler.send_message(
            recipient="phone_agent",
            message_type=msg_type,
            content=content,
            task_id=task_id
        )
        
        return {
            "success": True,
            "message_id": sent_message.message_id,
            "sent_at": sent_message.timestamp
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# 工具定义（用于LLM调用）
PHONE_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_message_to_computer_agent",
            "description": "发送消息给Computer Agent，让其执行浏览器操作或填写表单",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "要发送给Computer Agent的消息内容，应该包含用户的具体需求"
                    },
                    "message_type": {
                        "type": "string",
                        "enum": ["user_input", "system_status", "form_data"],
                        "description": "消息类型",
                        "default": "user_input"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "任务ID，用于关联相关消息",
                        "required": False
                    },
                    "additional_data": {
                        "type": "object",
                        "description": "额外的数据，如提取的表单信息",
                        "required": False
                    }
                },
                "required": ["message"]
            }
        }
    }
]

COMPUTER_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_message_to_phone_agent",
            "description": "发送消息给Phone Agent，反馈操作结果或请求更多信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "要发送给Phone Agent的消息内容"
                    },
                    "message_type": {
                        "type": "string",
                        "enum": ["task_result", "system_status", "error", "page_analysis"],
                        "description": "消息类型",
                        "default": "task_result"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "任务ID，用于关联相关消息",
                        "required": False
                    },
                    "additional_data": {
                        "type": "object",
                        "description": "额外的数据，如操作结果详情",
                        "required": False
                    }
                },
                "required": ["message"]
            }
        }
    }
]