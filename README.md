# Dual Agent: 边打电话边操作电脑的Agent系统

本项目实现了一个双Agent系统，由Phone Agent和Computer Agent组成，能够同时处理语音交互和浏览器操作，实现边打电话边填写表单等任务。

## ✨ 特点

- **🎤 Phone Agent**: 负责语音交互，实现了:
  - 实时语音检测和识别
  - 边听边想的理解能力
  - 快慢思考结合的智能响应
  - 自然语音合成和播放
  - 智能对话引导和上下文理解
  
- **💻 Computer Agent**: 负责浏览器操作，能够:
  - 分析网页内容和结构
  - 执行表单填写、点击、导航等操作
  - 捕获屏幕和DOM信息
  - 处理异常和错误情况
  - 实时响应Phone Agent的指令

- **🔄 Agent协同通信**: 基于Google A2A通信协议的消息传递机制，确保:
  - 标准化的消息格式
  - 可靠的双向通信
  - 上下文融合和共享
  - 实时协同工作

## 快速开始

### 1. 环境准备

- Python 3.9+
- 安装 [PyTorch](https://pytorch.org/get-started/locally/)
- 安装 [PortAudio](http://portaudio.com/docs/v19-doxydocs/tutorial_start.html) (用于PyAudio)
- 安装 `ffmpeg`

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

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

如果您想使用其他服务，例如Doubao，请设置相应的API密钥：

```bash
export VOLC_ACCESS_KEY_ID="YOUR_DOUBAO_ACCESS_KEY_ID"
export VOLC_SECRET_ACCESS_KEY="YOUR_DOUBAO_SECRET_ACCESS_KEY"
```

如果您想使用OpenAI，请设置相应的API密钥：

```bash
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
```

### 5. 运行双Agent

```bash
# 启动双Agent系统
# Agent默认会使用Doubao的TTS服务进行语音交互
python -m dual_agent.examples.run_dual_agent
```

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

## 项目结构
```
dual_agent/
├── common/                # 通用模块
│   ├── messaging.py       # Agent间消息队列
│   └── utils.py           # 工具函数
├── phone_agent/           # Phone Agent
│   ├── __init__.py
│   ├── phone_agent.py     # Phone Agent主类
│   ├── asr.py               # 自动语音识别
│   ├── thinking_engine.py # 思考引擎
│   ├── tts.py               # 文本到语音转换
│   └── vad.py               # 语音活动检测
├── computer_agent/        # Computer Agent
│   ├── __init__.py
│   ├── computer_agent.py  # Computer Agent主类
│   ├── browser_automation.py # 浏览器自动化
│   └── page_analyzer.py   # 页面分析
├── examples/              # 示例启动脚本
│   ├── run_phone_agent.py
│   └── run_dual_agent.py
├── tests/                 # 测试代码
└── 预下载模型.py            # 本地模型下载脚本
```

## 技术细节

### Phone Agent
Phone Agent是语音交互的核心，它通过一个流水线处理实时音频：
1.  **VAD**: 使用[Silero VAD](https://github.com/snakers4/silero-vad)检测用户是否在说话。
2.  **ASR**: 用户说话结束后，使用**Siliconflow的FunAudioLLM/SenseVoiceSmall**模型进行语音识别，专门针对中文优化。
3.  **Thinking Engine**:
    - **快思考 (Fast Thinking)**: ASR转录的同时，使用`doubao-seed-1-6-flash-250615`模型生成快速、简短的回应或填充词，实现低延迟响应。
    - **慢思考 (Deep Thinking)**: 完整的用户语句被转录后，使用`doubao-seed-1-6-thinking-250615`模型进行更深入的思考和任务规划，生成最终的指令或答案。
4.  **TTS**: 使用**Siliconflow的fishaudio/fish-speech-1.5**将LLM生成的文本转换为自然流畅的语音播放给用户。

### Computer Agent
Computer Agent负责执行Phone Agent生成的指令:
1.  **接收指令**: 通过消息队列从Phone Agent接收指令。
2.  **页面分析**: 使用多模态LLM (`doubao-seed-1-6-thinking-250615`)分析当前网页截图，理解页面结构和可交互元素。
3.  **执行动作**: 基于分析结果，使用Playwright执行点击、输入、滚动等浏览器操作。
4.  **反馈状态**: 将执行结果或观察到的页面变化反馈给Phone Agent。

### Agent间通信
- 使用Python内置的`asyncio.Queue`实现了一个简单的A2A (Agent-to-Agent) 消息传递系统。
- Phone Agent将指令发送到`computer_agent_queue`。
- Computer Agent将结果和观察发送到`phone_agent_queue`。

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