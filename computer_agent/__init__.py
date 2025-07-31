"""
Computer Agent包

提供基于浏览器自动化的Agent，能够执行网页操作和表单填写
"""

from dual_agent.computer_agent.browser_automation import (
    BrowserAutomation, BrowserType, ActionType, ActionResult
)
from dual_agent.computer_agent.page_analyzer import (
    PageAnalyzer, LLMProvider, ElementType, PageElement, 
    FormInfo, PageAnalysis
)
from dual_agent.computer_agent.computer_agent import (
    ComputerAgent, ComputerAgentState, TaskContext
)

__all__ = [
    'BrowserAutomation',
    'BrowserType', 
    'ActionType',
    'ActionResult',
    'PageAnalyzer',
    'LLMProvider',
    'ElementType',
    'PageElement',
    'FormInfo',
    'PageAnalysis',
    'ComputerAgent',
    'ComputerAgentState',
    'TaskContext',
] 