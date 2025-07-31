"""
Agent-to-Agent(A2A)通信模块

基于Google A2A协议设计的消息通信系统，实现Phone Agent和Computer Agent之间的标准化通信
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Callable


class MessageType(Enum):
    """消息类型枚举"""
    INFO = auto()      # 信息性消息
    ERROR = auto()     # 错误消息
    REQUEST = auto()   # 请求消息
    STATUS = auto()    # 状态更新
    ACTION = auto()    # 操作指令


class MessageSource(Enum):
    """消息来源枚举"""
    PHONE = auto()     # 来自Phone Agent的消息
    COMPUTER = auto()  # 来自Computer Agent的消息


class PartType(Enum):
    """消息内容部分类型枚举"""
    TEXT = auto()      # 文本内容
    DATA = auto()      # 结构化数据
    FILE = auto()      # 文件内容
    IMAGE = auto()     # 图像内容


@dataclass
class Part:
    """消息内容部分，基于Google A2A协议设计"""
    part_type: PartType
    content: Any
    mime_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class A2AMessage:
    """
    Agent-to-Agent(A2A)消息，基于Google A2A协议设计
    
    包含:
    - 消息来源: phone或computer
    - 消息类型: info, error, request, status, action
    - 消息内容: 字典形式
    - 任务ID: 关联相关消息
    - 时间戳: 发送时间
    """
    source: MessageSource
    type: MessageType
    content: Dict[str, Any]
    task_id: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    parts: List[Part] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """将消息转换为字典形式"""
        return {
            "message_id": self.message_id,
            "source": self.source.name.lower(),
            "type": self.type.name.lower(),
            "content": self.content,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "parts": [
                {
                    "part_type": part.part_type.name.lower(),
                    "content": part.content,
                    "mime_type": part.mime_type,
                    "metadata": part.metadata
                }
                for part in self.parts
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """从字典创建消息对象"""
        source = MessageSource[data["source"].upper()]
        msg_type = MessageType[data["type"].upper()]
        
        parts = []
        for part_data in data.get("parts", []):
            part_type = PartType[part_data["part_type"].upper()]
            parts.append(Part(
                part_type=part_type,
                content=part_data["content"],
                mime_type=part_data.get("mime_type", "text/plain"),
                metadata=part_data.get("metadata", {})
            ))
        
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            source=source,
            type=msg_type,
            content=data["content"],
            task_id=data["task_id"],
            timestamp=data.get("timestamp", time.time()),
            parts=parts
        )
    
    def to_json(self) -> str:
        """将消息序列化为JSON"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        """从JSON创建消息对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class A2AMessageQueue:
    """
    Agent-to-Agent消息队列
    
    管理Phone Agent和Computer Agent之间的消息传递
    """
    
    def __init__(self):
        # 延迟初始化队列，避免事件循环问题
        self.phone_to_computer = None
        self.computer_to_phone = None
        
        # 消息处理回调
        self._phone_message_handlers = []
        self._computer_message_handlers = []
        
        # 消息历史
        self.message_history = []
        
    def _ensure_queues_initialized(self):
        """确保队列已初始化"""
        if self.phone_to_computer is None:
            self.phone_to_computer = asyncio.Queue()
        if self.computer_to_phone is None:
            self.computer_to_phone = asyncio.Queue()
        
    async def send_to_computer(self, message: A2AMessage) -> None:
        """
        发送消息到Computer Agent
        
        参数:
            message: 要发送的消息
        """
        # 确保队列已初始化
        self._ensure_queues_initialized()
        
        # 设置消息来源
        message.source = MessageSource.PHONE
        
        # 记录消息
        self.message_history.append(message)
        
        # 放入队列
        await self.phone_to_computer.put(message)
        
    async def send_to_phone(self, message: A2AMessage) -> None:
        """
        发送消息到Phone Agent
        
        参数:
            message: 要发送的消息
        """
        # 确保队列已初始化
        self._ensure_queues_initialized()
        
        # 设置消息来源
        message.source = MessageSource.COMPUTER
        
        # 记录消息
        self.message_history.append(message)
        
        # 放入队列
        await self.computer_to_phone.put(message)
        
    async def receive_from_computer(self) -> A2AMessage:
        """
        接收来自Computer Agent的消息
        
        返回:
            消息对象
        """
        # 确保队列已初始化
        self._ensure_queues_initialized()
        
        message = await self.computer_to_phone.get()
        
        # 触发消息处理回调
        for handler in self._phone_message_handlers:
            asyncio.create_task(handler(message))
            
        return message
        
    async def receive_from_phone(self) -> A2AMessage:
        """
        接收来自Phone Agent的消息
        
        返回:
            消息对象
        """
        # 确保队列已初始化
        self._ensure_queues_initialized()
        
        message = await self.phone_to_computer.get()
        
        # 触发消息处理回调
        for handler in self._computer_message_handlers:
            asyncio.create_task(handler(message))
            
        return message
    
    def register_phone_message_handler(self, handler: Callable[[A2AMessage], None]) -> None:
        """
        注册Phone消息处理回调
        
        参数:
            handler: 消息处理回调函数
        """
        self._phone_message_handlers.append(handler)
        
    def register_computer_message_handler(self, handler: Callable[[A2AMessage], None]) -> None:
        """
        注册Computer消息处理回调
        
        参数:
            handler: 消息处理回调函数
        """
        self._computer_message_handlers.append(handler)
    
    def clear_queues(self) -> None:
        """清空所有消息队列"""
        # 确保队列已初始化
        self._ensure_queues_initialized()
        
        while not self.phone_to_computer.empty():
            try:
                self.phone_to_computer.get_nowait()
            except asyncio.QueueEmpty:
                break
                
        while not self.computer_to_phone.empty():
            try:
                self.computer_to_phone.get_nowait()
            except asyncio.QueueEmpty:
                break


# 全局消息队列实例
message_queue = A2AMessageQueue()


# 消息构建辅助函数
def create_info_message(
    text: str,
    task_id: str,
    source: MessageSource,
    data: Optional[Dict[str, Any]] = None
) -> A2AMessage:
    """
    创建信息消息
    
    参数:
        text: 消息文本
        task_id: 任务ID
        source: 消息来源
        data: 附加数据
        
    返回:
        A2AMessage对象
    """
    content = {"text": text}
    if data:
        content["data"] = data
        
    return A2AMessage(
        source=source,
        type=MessageType.INFO,
        content=content,
        task_id=task_id
    )


def create_error_message(
    text: str,
    task_id: str,
    source: MessageSource,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> A2AMessage:
    """
    创建错误消息
    
    参数:
        text: 错误消息
        task_id: 任务ID
        source: 消息来源
        error_code: 错误代码
        details: 错误详情
        
    返回:
        A2AMessage对象
    """
    content = {"text": text}
    if error_code:
        content["error_code"] = error_code
    if details:
        content["details"] = details
        
    return A2AMessage(
        source=source,
        type=MessageType.ERROR,
        content=content,
        task_id=task_id
    )


def create_request_message(
    text: str,
    task_id: str,
    source: MessageSource,
    request_type: str,
    required_fields: Optional[List[str]] = None
) -> A2AMessage:
    """
    创建请求消息
    
    参数:
        text: 请求描述
        task_id: 任务ID
        source: 消息来源
        request_type: 请求类型
        required_fields: 所需字段列表
        
    返回:
        A2AMessage对象
    """
    content = {
        "text": text,
        "request_type": request_type
    }
    if required_fields:
        content["required_fields"] = required_fields
        
    return A2AMessage(
        source=source,
        type=MessageType.REQUEST,
        content=content,
        task_id=task_id
    )


def create_status_message(
    status: str,
    task_id: str,
    source: MessageSource,
    progress: Optional[float] = None,
    details: Optional[str] = None
) -> A2AMessage:
    """
    创建状态消息
    
    参数:
        status: 状态描述
        task_id: 任务ID
        source: 消息来源
        progress: 进度(0-1)
        details: 详细信息
        
    返回:
        A2AMessage对象
    """
    content = {"status": status}
    if progress is not None:
        content["progress"] = progress
    if details:
        content["details"] = details
        
    return A2AMessage(
        source=source,
        type=MessageType.STATUS,
        content=content,
        task_id=task_id
    )


def create_action_message(
    action: str,
    task_id: str,
    source: MessageSource,
    parameters: Optional[Dict[str, Any]] = None
) -> A2AMessage:
    """
    创建操作消息
    
    参数:
        action: 操作名称
        task_id: 任务ID
        source: 消息来源
        parameters: 操作参数
        
    返回:
        A2AMessage对象
    """
    content = {"action": action}
    if parameters:
        content["parameters"] = parameters
        
    return A2AMessage(
        source=source,
        type=MessageType.ACTION,
        content=content,
        task_id=task_id
    ) 