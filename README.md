# Dual Agent: 边打电话边操作电脑的Agent系统 (改进版)

本项目实现了一个基于LLM驱动和工具调用通信的智能双Agent系统，完全符合vibe-coding课题六的要求。

## 🆕 重要改进 (基于课题要求)

### ✅ 集成现成开源框架
- **browser-use框架**：替代自研Playwright封装，使用成熟的浏览器自动化框架
- **anthropic-computer-use** (备选)：支持Anthropic官方计算机操作框架
- **完全移除自研实现**：不再自己实现浏览器操作逻辑

### ✅ 基于工具调用的Agent通信
- **Phone Agent工具**：`send_message_to_computer_agent` - 发送消息给Computer Agent
- **Computer Agent工具**：`send_message_to_phone_agent` - 发送消息给Phone Agent  
- **标准化通信协议**：使用JSON格式的工具调用参数
- **自然对话模式**：两个Agent像人一样自然交流

### ✅ LLM驱动的智能表单处理
- **完全禁止硬编码**：移除所有字符串匹配和正则表达式
- **LLM自然语言理解**：直接让LLM分析用户输入提取表单信息
- **智能意图识别**：LLM理解用户真实意图并生成操作指令
- **通用性设计**：支持各种不同结构的网页和表单

## ✨ 系统特点

- **🎤 Phone Agent**: 负责语音交互 (保持原有功能)：
  - 实时语音检测和识别
  - 边听边想的理解能力
  - 快慢思考结合的智能响应
  - 自然语音合成和播放
  - **新增工具调用能力**
  
- **💻 智能Computer Agent**: 基于LLM驱动的浏览器操作：
  - **LLM分析用户输入**：智能理解用户意图
  - **现成框架操作**：使用browser-use执行浏览器操作
  - **自适应网页结构**：无需硬编码选择器
  - **智能表单填写**：从自然语言中提取表单信息

- **🔄 工具调用通信**: 基于工具调用的Agent间通信：
  - 标准化的工具调用格式
  - 可靠的双向通信
  - 异步消息处理
  - 通用性设计支持各种任务场景

## 快速开始

### 1. 环境准备

- **Python 3.11+** (**必需，browser-use框架要求**)
- 安装 [PyTorch](https://pytorch.org/get-started/locally/)
- 安装 [PortAudio](http://portaudio.com/docs/v19-doxydocs/tutorial_start.html) (用于PyAudio)
- 安装 `ffmpeg`

**创建Python 3.11虚拟环境** (推荐)：
```bash
# 确保使用Python 3.11+
python3.11 -m venv dual_agent_env
source dual_agent_env/bin/activate  # Linux/Mac
# 或
dual_agent_env\Scripts\activate     # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**新增依赖**：
- `browser-use>=0.1.0` - 浏览器自动化框架 (**需要Python 3.11+**)
- `playwright>=1.40.0` - 浏览器驱动
- `anthropic>=0.7.0` - Anthropic Computer Use支持

**⚠️ 重要提醒**：
- browser-use框架**要求Python 3.11或更高版本**
- 建议使用虚拟环境：`python3.11 -m venv venv && source venv/bin/activate`

### 3. 下载本地模型

项目需要使用本地模型进行语音活动检测(VAD)和自动语音识别(ASR)。请运行以下脚本进行下载：

```bash
python -m dual_agent.预下载模型
```

### 4. 配置API密钥

本项目默认使用[Siliconflow](https://siliconflow.cn)提供的LLM、TTS和ASR服务，为AI Agent开发提供了完整的模型生态。请设置您的API密钥：

```bash
export SILICONFLOW_API_KEY="YOUR_SILICONFLOW_API_KEY"
```

**🆕 Browser-Use框架API密钥配置**：

browser-use框架支持多种LLM提供商，请根据您的需求配置相应的API密钥：

```bash
# OpenAI (推荐用于browser-use)
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"

# Anthropic Claude (备选)
export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"

# Google Gemini (备选)
export GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"

# DeepSeek (备选)
export DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY"

# Azure OpenAI (备选)
export AZURE_OPENAI_ENDPOINT="YOUR_AZURE_ENDPOINT"
export AZURE_OPENAI_KEY="YOUR_AZURE_KEY"
```

如果您想使用其他服务，例如Doubao，请设置相应的API密钥：

```bash
export VOLC_ACCESS_KEY_ID="YOUR_DOUBAO_ACCESS_KEY_ID"
export VOLC_SECRET_ACCESS_KEY="YOUR_DOUBAO_SECRET_ACCESS_KEY"
```

**💡 API密钥优先级说明**：
- **Phone Agent**: 使用SILICONFLOW_API_KEY进行语音处理和思考
- **Computer Agent**: 
  - **LLM分析**: 使用SILICONFLOW_API_KEY (doubao-seed-1-6-thinking-250615)
  - **Browser-Use操作**: 智能选择API，优先级如下：
    1. 🥇 OPENAI_API_KEY → gpt-4o-mini (推荐，兼容性最佳)
    2. 🥈 ANTHROPIC_API_KEY → claude-3-sonnet (备选，高质量)
    3. 🥉 SILICONFLOW_API_KEY → doubao (降级模式，可能不兼容)
  - **无API密钥时**: 自动启用fallback模拟模式

**🎯 推荐配置方案**：

**方案一 (推荐)**：
```bash
export SILICONFLOW_API_KEY="your_siliconflow_key"  # Phone Agent + Computer Agent分析
export OPENAI_API_KEY="your_openai_key"            # Browser-Use专用 (最佳兼容性)
```

**方案二 (备选)**：
```bash
export SILICONFLOW_API_KEY="your_siliconflow_key"  # Phone Agent + Computer Agent分析  
export ANTHROPIC_API_KEY="your_anthropic_key"      # Browser-Use专用 (高质量)
```

**方案三 (最简)**：
```bash
export SILICONFLOW_API_KEY="your_siliconflow_key"  # 全部功能 (降级模式)
```

### 5. 运行改进的双Agent系统

```bash
# 启动改进的双Agent系统 (完整功能)
python examples/run_dual_agent.py --debug

# 指定目标网页
python examples/run_dual_agent.py --target-url "https://httpbin.org/forms/post" --debug

# 模拟模式 (无需API密钥，用于测试)
python examples/run_dual_agent.py --dummy --debug
```

**改进的系统特点**：
- ✅ 基于工具调用的Agent通信
- ✅ LLM驱动的智能表单处理  
- ✅ 集成browser-use框架
- ✅ 完全移除硬编码字符串匹配

### 6. 运行纯Phone Agent (for testing)

```bash
# 测试Phone Agent，默认使用Doubao TTS
python -m dual_agent.examples.run_phone_agent
```

## 命令行参数

### Phone Agent & Dual Agent

#### 通用配置
| 参数 | 描述 | 默认值 |
|---|---|---|
| `--debug` | 开启Debug模式 | |
| `--dummy` | 使用Dummy模式 (不调用实际API) | |
| `--vad-threshold`| VAD检测阈值 (0.0-1.0) | 0.5 |
| `--device-index` | 麦克风设备索引 | 0 |

#### ASR配置
| 参数 | 描述 | 默认值 |
|---|---|---|
| `--asr` | ASR提供商 (siliconflow/doubao/local/openai) | "siliconflow" |
| `--asr-model` | ASR模型名称 | "FunAudioLLM/SenseVoiceSmall" |

#### LLM配置
| 参数 | 描述 | 默认值 |
|---|---|---|
| `--fast-model` | 快思考LLM模型名称 | "doubao-seed-1-6-flash-250615" |
| `--deep-model` | 慢思考LLM模型名称 | "doubao-seed-1-6-thinking-250615" |

#### TTS配置
| 参数 | 描述 | 默认值 |
|---|---|---|
| `--tts` | TTS提供商 (siliconflow/doubao/openai/dummy) | "siliconflow" |
| `--tts-voice` | TTS语音音色 | "fishaudio/fish-speech-1.5:alex" |

### Computer Agent (仅`run_dual_agent`)
| 参数 | 描述 | 默认值 |
|---|---|---|
| `--headless` | 无头模式运行浏览器 | |
| `--start-url` | Computer Agent初始导航页面 | "https://www.google.com" |
| `--computer-model`| Computer Agent使用的LLM模型 | "Doubao-1.5-Pro" |

## 🎯 与原版对比

| 方面 | 原版 | 改进版 |
|------|------|--------|
| **Agent通信** | 硬编码消息队列 | ✅ 工具调用 |
| **表单处理** | 字符串匹配 | ✅ LLM驱动 |
| **浏览器操作** | 自研Playwright | ✅ browser-use框架 |
| **通用性** | 特化表单 | ✅ 通用对话模式 |
| **智能程度** | 规则匹配 | ✅ 自然语言理解 |

## 🧠 智能特性演示

### LLM驱动的表单信息提取
```
用户说："我叫张三，邮箱是zhang@example.com，电话是138****8888"
↓
LLM自动分析并提取：
{
  "name": "张三",
  "email": "zhang@example.com", 
  "phone": "138****8888"
}
↓
Computer Agent智能填写表单
```

### 工具调用通信示例
```json
{
  "tool_name": "send_message_to_computer_agent",
  "parameters": {
    "message": "用户提供了个人信息",
    "message_type": "user_input",
    "additional_data": {
      "extracted_info": {
        "name": "张三",
        "email": "zhang@example.com"
      }
    }
  }
}
```

## 📁 项目结构 (更新)
```
dual_agent/
├── common/                     # 通用模块
│   ├── messaging.py           # 原版消息队列 (保留)
│   ├── tool_calling.py        # 🆕 工具调用通信机制
│   └── utils.py               # 工具函数
├── phone_agent/               # Phone Agent
│   ├── __init__.py
│   ├── phone_agent.py         # 🔄 支持工具调用
│   ├── asr.py                 # 自动语音识别 (保持不变)
│   ├── thinking_engine.py     # 🔄 集成工具调用能力
│   ├── tts.py                 # 文本到语音转换 (保持不变)
│   └── vad.py                 # 语音活动检测 (保持不变)
├── computer_agent/            # Computer Agent
│   ├── __init__.py
│   ├── computer_agent.py      # 原版Computer Agent (保留)
│   ├── intelligent_computer_agent.py  # 🆕 智能Computer Agent
│   ├── browser_automation.py  # 原版浏览器自动化 (保留)
│   └── page_analyzer.py       # 原版页面分析 (保留)
├── examples/                  # 示例启动脚本
│   ├── run_phone_agent.py     # Phone Agent测试
│   └── run_dual_agent.py      # 🔄 启动改进的双Agent系统
├── tests/                     # 测试代码
└── 预下载模型.py                # 本地模型下载脚本
```

**🆕 新增文件说明**：
- `tool_calling.py`: 工具调用通信机制，替代硬编码消息队列
- `intelligent_computer_agent.py`: 基于LLM驱动的智能Computer Agent
- 修改的文件支持工具调用和LLM驱动处理

## 技术细节 (更新)

### Phone Agent (保持原有功能 + 新增工具调用)
Phone Agent继续作为语音交互的核心，处理实时音频流水线：
1.  **VAD**: 使用[Silero VAD](https://github.com/snakers4/silero-vad)检测用户是否在说话 (保持不变)
2.  **ASR**: 使用**Siliconflow的FunAudioLLM/SenseVoiceSmall**模型进行语音识别 (保持不变)
3.  **🆕 工具调用思考引擎**:
    - **快思考**: `doubao-seed-1-6-flash-250615`模型 + 工具调用能力
    - **深度思考**: `doubao-seed-1-6-thinking-250615`模型 + 工具调用能力
    - **智能决策**: LLM自主决定是否调用`send_message_to_computer_agent`工具
4.  **TTS**: 使用**Siliconflow的fishaudio/fish-speech-1.5**将文本转换为语音 (保持不变)

### 🆕 智能Computer Agent (完全重构)
新的Computer Agent基于LLM驱动，完全替代硬编码方式：
1.  **工具调用接收**: 通过`ToolCallHandler`接收来自Phone Agent的工具调用消息
2.  **LLM意图分析**: 使用`doubao-seed-1-6-thinking-250615`分析用户输入，理解真实意图
3.  **智能信息提取**: LLM从自然语言中提取表单数据，无需任何硬编码匹配
4.  **🆕 分离式API设计**: 
   - **分析层**: SILICONFLOW_API_KEY驱动意图理解和数据提取
   - **操作层**: OPENAI_API_KEY/ANTHROPIC_API_KEY驱动browser-use浏览器操作
   - **智能降级**: 无专用API时自动降级到SiliconFlow (兼容性警告)
5.  **智能验证**: LLM分析操作结果并验证成功性

**🎯 分离式API设计的优势**：
- **🚀 性能优化**: 不同任务使用最适合的模型
- **💰 成本控制**: 可为不同功能选择不同价格的API
- **⚡ 兼容性**: browser-use与OpenAI/Anthropic原生兼容
- **🛡️ 降级保护**: 单一API失效时系统仍可运行

### 🔄 工具调用通信 (替代原有消息队列)
- **异步工具调用**: 基于`ToolCallHandler`的异步消息处理
- **标准化格式**: JSON格式的工具调用参数和返回值
- **自然对话**: Agent间通信模拟人与人的自然对话模式
- **错误处理**: 内置重试机制和异常处理逻辑

### 🧠 LLM驱动的智能特性
```python
# 用户输入: "我叫张三，邮箱是zhang@example.com"
# LLM分析提示:
analysis_prompt = """
分析用户输入并提取表单信息："{user_input}"
请以JSON格式返回：
{
  "intent": "用户意图",
  "extracted_data": {
    "name": "提取的姓名",
    "email": "提取的邮箱"
  },
  "operation_plan": [...],
  "response_to_user": "给用户的回复"
}
"""
```

## 服务依赖
### LLM服务
- **Siliconflow (默认)**: `doubao-seed-1-6-flash-250615` 和 `doubao-seed-1-6-thinking-250615`
- **Doubao**: `Doubao-1.5-Lite` 和 `Doubao-1.5-Pro`
- **OpenAI**: GPT系列模型
- **DeepSeek**: DeepSeek系列模型

### TTS服务
- **Siliconflow (默认)**: fishaudio/fish-speech-1.5模型
- **Doubao**
- **OpenAI**
- **ElevenLabs**
- **Azure TTS**

### ASR服务
- **Siliconflow (默认)**: FunAudioLLM/SenseVoiceSmall模型
- **Doubao**
- **OpenAI Whisper API**
- **本地 faster-whisper** 