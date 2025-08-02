# Computer Agent Browser-Use 测试指南

这是一个专门用于测试 Computer Agent 的 browser-use 功能的独立测试脚本。

## 目标

测试 Computer Agent 对 `https://httpbin.org/forms/post` 页面的以下功能：
- 页面导航和加载
- 页面内容分析 
- 表单数据提取
- 表单填写功能
- 完整的 browser-use 工作流程

## 环境要求

### 1. Python依赖
确保已安装项目的所有依赖项：
```bash
pip install -r requirements.txt
```

### 2. Browser-Use框架
确保已安装 browser-use：
```bash
pip install browser-use
```

### 3. API密钥配置
需要设置以下环境变量之一（按优先级排序）：

**选项1: OpenAI API（推荐）**
```bash
export OPENAI_API_KEY="your_openai_api_key"
```

**选项2: Anthropic API**
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

**选项3: Siliconflow API**
```bash
export SILICONFLOW_API_KEY="your_siliconflow_api_key"
```

## 运行测试

### 基本运行
在 `dual_agent` 目录下执行：
```bash
python test_computer_agent_browser_use.py
```

### 运行示例
```bash
cd /path/to/dual_agent
export OPENAI_API_KEY="your_api_key_here"
python test_computer_agent_browser_use.py
```

## 测试内容

测试脚本会依次执行以下测试：

1. **Browser-Use可用性检查** - 验证 browser-use 框架是否正确导入
2. **LLM客户端创建** - 检查 API 密钥配置和 LLM 客户端初始化
3. **Agent初始化** - 测试 Computer Agent 的基本初始化
4. **页面导航测试** - 导航到 httpbin.org 表单页面并分析
5. **表单数据提取** - 测试从自然语言中提取表单数据的能力
6. **表单填写模拟** - 模拟用户输入并测试表单填写流程
7. **完整工作流程** - 端到端测试完整的 browser-use 操作流程

## 预期结果

成功运行后，你会看到：
- 浏览器窗口自动打开（非无头模式）
- 自动导航到 httpbin.org/forms/post
- 页面分析和表单字段识别
- LLM驱动的数据提取演示
- 表单填写操作（如果配置正确）

## 故障排除

### 常见问题

**1. browser-use导入失败**
```bash
pip install browser-use
```

**2. API密钥未配置**
- 检查环境变量是否正确设置
- 确认API密钥有效且有足够额度

**3. 浏览器启动失败**
- 确保系统已安装Chrome或Chromium
- 检查Playwright浏览器依赖：
```bash
playwright install chromium
```

**4. 页面导航超时**
- 检查网络连接
- httpbin.org 可能暂时不可用，等待后重试

### 调试模式

测试脚本默认启用调试模式，会输出详细的执行日志。如需更多调试信息，可以：

1. 查看浏览器窗口中的实际操作
2. 检查控制台输出中的错误信息
3. 如果需要，修改 `headless=False` 以观察浏览器行为

## 自定义测试

### 修改目标URL
在 `test_computer_agent_browser_use.py` 中修改：
```python
self.target_url = "https://your-custom-form-url.com"
```

### 修改测试数据
在测试方法中修改表单数据：
```python
test_form_data = {
    "name": "你的姓名",
    "email": "your@email.com",
    "phone": "你的电话号码"
}
```

## 注意事项

- 测试会打开真实的浏览器窗口
- 会向真实的网页发送请求
- 确保有稳定的网络连接
- 某些测试可能需要几分钟完成
- 测试结束后会自动清理资源

## 支持

如果遇到问题，请检查：
1. 项目依赖是否完整安装
2. API密钥是否正确配置
3. browser-use框架是否正常工作
4. 网络连接是否稳定