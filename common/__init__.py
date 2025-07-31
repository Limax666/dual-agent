"""
双Agent系统的公共组件包

包含：
- 消息通信相关类和接口
- 通用工具和辅助函数
"""

# 导出消息通信相关的核心类和函数
from .messaging import (
    # 枚举类
    MessageType,
    MessageSource,
    PartType,
    
    # 核心类
    Part,
    A2AMessage,
    A2AMessageQueue,
    
    # 全局实例
    message_queue,
    
    # 消息构建辅助函数
    create_info_message,
    create_error_message,
    create_request_message,
    create_status_message,
    create_action_message,
)

# 定义公开的API
__all__ = [
    # 枚举类
    "MessageType",
    "MessageSource", 
    "PartType",
    
    # 核心类
    "Part",
    "A2AMessage",
    "A2AMessageQueue",
    
    # 全局实例
    "message_queue",
    
    # 消息构建辅助函数
    "create_info_message",
    "create_error_message",
    "create_request_message", 
    "create_status_message",
    "create_action_message",
] 