# 通用双Agent系统 (Dual Agent System)

基于设计文档实现的Phone Agent和Computer Agent协同工作系统，支持通过语音交互完成任意网页的操作。

## 系统架构

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│    用户     │◄───────┤ Phone Agent │◄───────┤Computer Agent│
│  (语音)    │───────►│  (语音处理) │───────►│  (浏览器操作)│
└─────────────┘        └─────────────┘        └─────────────┘
                            ▲  │                   │  ▲
                            │  │                   │  │
                            │  ▼                   ▼  │
                        ┌─────────────────────────────┐
                        │     A2A 通信协议通道        │
                        └─────────────────────────────┘
```

## 核心特性

- **🎤 语音交互**: 自然语音对话，支持实时语音识别和合成
- **🌐 通用网页操作**: 支持任意网站的访问、表单填写、页面交互
- **🤖 智能协同**: Phone Agent和Computer Agent实时通信协作
- **🔧 LLM驱动**: 完全基于LLM理解和执行，无硬编码逻辑
- **📊 实时反馈**: 操作过程实时反馈，异常处理机制完善

## 环境要求

### Python版本
- Python 3.8+

### 必需依赖
```bash
pip install torch numpy openai aiohttp browser-use
```

### 可选依赖 (语音功能)
```bash
pip install pyaudio pygame
```

### API密钥
需要设置以下环境变量：
```bash
export SILICONFLOW_API_KEY=your_siliconflow_key  # Phone Agent语音服务
export ARK_API_KEY=your_doubao_ark_key          # Phone Agent思考引擎
export OPENAI_API_KEY=your_openai_key           # Computer Agent
```

## 使用方法

### 基本使用
```bash
# 启动系统，运行时通过语音指定网站
python run_dual_agent.py

# 启动时指定目标网站
python run_dual_agent.py --url https://www.example.com

# 启用调试模式
python run_dual_agent.py --debug

# 使用文本输入模式（无需麦克风）
python run_dual_agent.py --text-mode
```

### 参数说明
- `--url URL`: 指定要打开的网站（可选）
- `--debug`: 启用调试模式，显示详细处理过程
- `--vad-threshold FLOAT`: 语音检测阈值 (0.0-1.0, 默认0.6)
- `--device-index INT`: 麦克风设备索引 (默认0)
- `--text-mode`: 强制使用文本输入模式

## 支持的操作类型

### 🌐 网页访问
```
👤: "打开百度首页"
👤: "访问 https://github.com"
👤: "打开谷歌搜索"
```

### 📝 表单填写
```
👤: "帮我填写这个注册表单"
👤: "我的名字是张三，邮箱是zhang@example.com"
👤: "提交表单"
```

### 🔍 信息搜索
```
👤: "搜索人工智能相关信息"
👤: "在这个网站上找到联系方式"
👤: "查看最新的新闻"
```

### 🖱️ 页面交互
```
👤: "点击登录按钮"
👤: "滚动到页面底部"
👤: "打开第一个链接"
```

## 工作流程

1. **启动系统**: Phone Agent和Computer Agent同时初始化
2. **语音交互**: 用户通过语音描述需求
3. **意图理解**: Phone Agent的LLM理解用户意图
4. **任务分发**: Phone Agent通过工具调用向Computer Agent发送指令
5. **网页操作**: Computer Agent使用browser-use框架执行操作
6. **结果反馈**: Computer Agent将结果反馈给Phone Agent
7. **用户播报**: Phone Agent向用户播报操作结果
8. **持续交互**: 循环进行，支持多轮对话

## 验收标准实现

系统完全实现了设计文档中的验收标准：

✅ **协同工作流程**:
- Phone Agent主动与用户对话
- 实时信息传递给Computer Agent
- Computer Agent智能识别和填写表单
- 流畅的双向通信，无明显阻塞

✅ **异常处理**:
- Computer Agent错误信息实时反馈
- Phone Agent转述问题并请求用户指导
- 完善的错误恢复机制

## 技术实现

### Phone Agent
- **VAD**: Silero VAD语音检测
- **ASR**: Siliconflow FunAudioLLM/SenseVoiceSmall
- **LLM**: Doubao快思考+深度思考混合引擎
- **TTS**: Siliconflow fishaudio/fish-speech-1.5

### Computer Agent
- **框架**: browser-use浏览器自动化
- **LLM**: OpenAI GPT-4系列
- **操作**: 完全LLM驱动，无硬编码

### 通信机制
- **协议**: 基于工具调用的A2A通信
- **消息类型**: 用户输入、任务结果、错误、页面分析
- **可靠性**: 异步消息队列，超时处理

## 故障排除

### 语音识别问题
- 检查麦克风权限和设备
- 调整VAD阈值参数
- 使用`--text-mode`进行测试

### 网页操作问题
- 检查网络连接
- 确认目标网站可访问
- 查看Computer Agent调试日志

### API调用问题
- 验证API密钥有效性
- 检查API余额
- 查看网络代理设置

## 扩展功能

当前系统支持：
- 任意网站访问
- 智能表单填写
- 页面内容分析
- 交互元素操作

未来可扩展：
- 多语言支持
- 自定义操作流程
- 批量操作处理
- 更多浏览器支持

## 开发和贡献

项目结构：
```
dual_agent/
├── phone_agent/          # Phone Agent模块
├── computer_agent/       # Computer Agent模块  
├── common/              # 通信和工具模块
├── dual_agent_system.py # 主系统控制器
└── run_dual_agent.py    # 启动脚本
```

欢迎贡献代码和反馈问题！