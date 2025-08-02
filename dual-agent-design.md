# 课题六：边打电话边操作电脑的 Agent 设计文档

## 1. 系统架构概览

### 1.1 双Agent架构
- **Phone Agent**: 负责语音交互，使用ASR+LLM+TTS流水线，基于快慢思考结合的边听边想能力
- **Computer Agent**: 负责浏览器操作，基于浏览器自动化框架如browser-use实现

### 1.2 系统工作流
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

  1. 🔴 检测到语音 → 2. 🔇 语音结束 → 3. 🧠 开始处理用户语音 → 4. 🔄
  开始ASR转录 → 5. ✅ ASR转录成功 → 6. 🤔 思考引擎开始工作 → 7. ⚡/🧠
  快速/深度思考 → 8. 🔊 正在生成语音回应 → 9. ✅ 语音处理完成


1. 语音检测阶段：

  - 音量显示: 🎵 音量: ████ (0.234)
  - VAD检测: 🎯 语音概率: 0.756 (阈值: 0.5)
  - 录音状态: 🔴 检测到语音，🔇 语音结束

  2. ASR语音识别阶段：

  - 🔄 开始Siliconflow ASR转录
  - 📁 WAV文件大小: xxx 字节
  - 🚀 正在调用Siliconflow ASR API...
  - ✅ ASR转录成功: 'xxx'

  3. 思考引擎阶段：

  - 🤔 思考引擎开始工作...
  - ⚡ 启动快思考 / 🧠 启动深度思考
  - ✅ 思考完成 - 快速: xx字符, 深度: xx字符

  4. TTS语音合成阶段：

  - 🔊 正在生成语音回应...
  - ✅ 语音处理完成，继续监听...


## 2. 详细设计

### 2.1 Phone Agent 设计

#### 2.1.1 组件构成
- **语音检测(VAD)**: 使用Silero VAD检测语音活动，实现更自然的对话交互
- **语音识别(ASR)**: 使用Siliconflow的FunAudioLLM/SenseVoiceSmall模型实时将用户语音转换为文本，支持流式输入以实现边听边想
- **混合思考引擎**: 结合快思考与慢思考的双路径处理模式
  - **快思考路径**: 使用Siliconflow的doubao-seed-1-6-flash-250615模型实现即时反馈和对话流畅性维护
  - **慢思考路径**: 使用Siliconflow的doubao-seed-1-6-thinking-250615模型进行深度推理和复杂任务规划
- **语音合成(TTS)**: 使用Siliconflow的fishaudio/fish-speech-1.5模型将文本响应转换为自然的语音输出

#### 2.1.2 工作模式
- **边听边想(Thinking While Listening)**: 在用户说话的同时，实时分析不完整的语句并开始思考，形成初步内部推理
- **快速响应机制**: 用户停止讲话后，快速生成临时回应，避免尴尬沉默
- **深度处理**: 同时在后台继续深度思考，准备更完整的回答
- **情境维护**: 始终跟踪对话上下文和表单填写进度
- **处理Computer Agent消息**: 接收并自然融合来自Computer Agent的状态更新信息

#### 2.1.3 特殊处理
- **消息优先级处理**: 用户输入 > Computer Agent消息，确保用户体验流畅
- **发言权判断(Turn-taking)**: 分析用户语义完整性，判断是否继续等待用户输入
- **填充语生成**: 在等待深度思考结果时生成自然的填充语，保持对话连贯
- **打断机制**: 能够根据用户语音内容智能识别打断意图，区分确认性附和与实质性打断

### 2.2 Computer Agent 设计

#### 2.2.1 组件构成
- **Browser Automation框架**: 集成现成的开源浏览器自动化框架
  - **主选方案**: [Anthropic Computer Use](https://github.com/anthropics/anthropic-computer-use) - Anthropic官方计算机操作框架
  - **备选方案**: [Browser-Use](https://github.com/BrowserUse/browser-use) - 专业的浏览器自动化框架
  - 禁止自研实现，必须基于现有成熟框架
- **智能LLM分析器**: 使用LLM分析用户输入并生成操作指令
  - 直接理解用户的自然语言描述
  - 智能推断表单字段和填写内容
  - 生成具体的浏览器操作指令
- **状态管理**: 跟踪当前操作状态和执行进度
- **异常处理**: 处理页面加载失败、元素不可见等异常情况

#### 2.2.2 工作模式
- **智能页面分析**: 
  - 使用选定框架的视觉识别能力分析页面
  - 由LLM理解页面结构和表单布局
  - 识别所有可交互元素和表单字段
- **LLM驱动的表单操作**: 
  - **禁止硬编码**: 完全禁止使用字符串匹配等硬编码方式
  - **LLM智能解析**: 让LLM直接分析用户输入，理解用户意图
  - **自然语言理解**: LLM从用户的自然语言中提取表单信息
  - **动态操作生成**: 基于LLM分析结果生成具体的浏览器操作
- **框架驱动操作**: 使用选定框架执行具体的浏览器操作
- **智能验证**: 操作后由LLM分析结果并验证成功性
- **状态报告**: 将操作结果和当前状态及时反馈给Phone Agent

### 2.3 通信机制

#### 2.3.1 基于工具调用(Tool-use)的Agent间通信
- **通信方式**: 两个Agent通过工具调用进行通信，确保标准化和可靠性
  - **Phone Agent**: 调用 `send_message_to_computer_agent` 工具发送消息给Computer Agent
  - **Computer Agent**: 调用 `send_message_to_phone_agent` 工具发送消息给Phone Agent
- **工具调用格式**: 
  ```json
  {
    "tool_name": "send_message_to_computer_agent", 
    "parameters": {
      "message": "用户说他的名字叫张三，邮箱是zhang@example.com",
      "message_type": "user_info",
      "task_id": "unique_task_id"
    }
  }
  ```
- **通用性设计**: 
  - **避免表单特化**: 不要因为题目验收标准是表单就专门针对表单设计通信协议
  - **泛化交互模式**: 设计为通用的Agent对话模式，支持各种任务场景
  - **自然对话流**: 两个Agent之间的交互应该像两个人自然对话一样

#### 2.3.2 消息处理流程
- **Phone Agent收到用户输入** → **工具调用发送给Computer Agent** → **Computer Agent使用LLM分析** → **Computer Agent执行操作** → **工具调用反馈给Phone Agent**
- **LLM驱动的信息提取**: 
  - Computer Agent收到用户回答后，使用LLM从message中智能提取表单信息
  - 完全依赖LLM的理解能力，不使用任何硬编码的字符串匹配
  - LLM可以理解各种自然语言表达方式

## 3. 实现计划

### 3.1 Phone Agent 实现

```python
class PhoneAgent:
  # 核心组件
  - vad: Silero VAD语音活动检测模块
  - asr: Siliconflow ASR API模块
  - fast_llm: 快思考模型(doubao-seed-1-6-flash-250615)
  - deep_llm: 深度思考模型(doubao-seed-1-6-thinking-250615)
  - tts: Siliconflow TTS API模块
  - message_queue: A2A消息队列接口
  
  # 核心方法
  + initialize(): 初始化各模块和连接
  + startCall(): 开始通话会话
  + processAudioStream(audio_chunk): 处理音频流并触发VAD
  + handleUserSpeech(audio): 处理完整的用户语音段落
    - transcribeAudio(): 通过Siliconflow ASR转录音频为文本
    - startFastThinking(): 启动快思考处理(doubao-seed-1-6-flash-250615)
    - startDeepThinking(): 并行启动深度思考处理(doubao-seed-1-6-thinking-250615)
  + handleComputerMessage(message): 处理来自Computer Agent的消息
  + generateResponse(fast_response, deep_response): 生成最终响应
  + sendMessageToComputer(message): 发送消息到Computer Agent
  + synthesizeSpeech(text): 通过Siliconflow TTS将文本转换为语音并播放
```

### 3.2 Computer Agent 实现

```python
class ComputerAgent:
  # 核心组件
  - computer_use_client: Anthropic Computer Use客户端或Browser-Use客户端
  - llm_analyzer: 智能LLM分析器，用于理解用户输入和生成操作指令
  - message_tools: 工具调用接口，支持send_message_to_phone_agent
  - state_manager: 操作状态管理器
  
  # 核心方法
  + initialize(framework_type): 初始化选定的浏览器自动化框架
  + process_user_message(message): 使用LLM分析用户消息并生成操作计划
    - analyze_user_intent(): 让LLM理解用户意图
    - extract_form_data_with_llm(): 使用LLM从自然语言中提取表单数据
    - generate_browser_operations(): 基于LLM分析生成浏览器操作序列
  + execute_browser_operations(operations): 使用框架执行浏览器操作
    - 禁止硬编码选择器匹配
    - 全部依赖框架的智能识别能力
  + send_message_to_phone_agent(message): 工具调用发送消息给Phone Agent
  + verify_operations_with_llm(): 使用LLM验证操作结果
```

### 3.3 实现步骤
1. **选择和集成浏览器自动化框架**
   - 优先集成Anthropic Computer Use框架
   - 备选方案集成Browser-Use框架
   - 完全移除现有的自研Playwright封装
2. **实现Phone Agent的工具调用能力**
   - 实现send_message_to_computer_agent工具
   - 修改思考引擎输出格式支持工具调用
   - 保持现有的VAD、ASR、TTS功能不变
3. **重构Computer Agent为LLM驱动模式**
   - 移除所有硬编码的字符串匹配逻辑
   - 实现LLM驱动的用户输入分析
   - 集成选定的浏览器自动化框架
   - 实现send_message_to_phone_agent工具
4. **实现工具调用通信机制**
   - 建立基于工具调用的Agent间通信协议
   - 确保消息的可靠传递和处理
   - 实现异常处理和重试机制
5. **集成测试与优化**
   - 端到端测试Agent间协作
   - 验证LLM驱动的表单填写能力
   - 优化响应速度和准确性

## 4. 技术选型

### 4.1 Phone Agent
- **VAD**: Silero VAD (高精度语音活动检测)
- **ASR**: Siliconflow FunAudioLLM/SenseVoiceSmall模型 (支持中文语音识别，高精度实时转录)
- **LLM**:
  - 快思考: doubao-seed-1-6-flash-250615 (Siliconflow平台)
  - 慢思考: doubao-seed-1-6-thinking-250615 (Siliconflow平台)
- **TTS**: Siliconflow fishaudio/fish-speech-1.5模型 (自然语音合成)

### 4.2 Computer Agent
- **浏览器自动化框架**:
  - **主选**: [Anthropic Computer Use](https://github.com/anthropics/anthropic-computer-use)
    - Anthropic官方开发，专为AI Agent设计
    - 支持视觉识别和自然语言指令
    - 与Claude模型深度集成
  - **备选**: [Browser-Use](https://github.com/BrowserUse/browser-use)
    - 专业的浏览器自动化框架
    - 支持多种LLM集成
    - 提供丰富的浏览器操作API
- **LLM分析器**: doubao-seed-1-6-thinking-250615 (Siliconflow平台)
  - 用于分析用户输入和理解表单结构
  - 生成智能的浏览器操作指令
  - **完全禁止硬编码**: 不使用任何字符串匹配、正则表达式等硬编码方式
- **工具调用系统**: 
  - 实现标准化的send_message_to_phone_agent工具
  - 支持结构化的消息传递和状态同步

### 4.3 通信层
- **工具调用系统**: 基于LLM工具调用的Agent间通信
  - **send_message_to_computer_agent**: Phone Agent调用此工具发送消息
  - **send_message_to_phone_agent**: Computer Agent调用此工具发送消息
  - **消息格式标准化**: 使用JSON格式确保消息的结构化传递
- **异步处理**: 支持非阻塞的消息处理和响应
- **错误处理**: 内置重试机制和异常处理逻辑

### 4.4 Siliconflow API配置

#### 4.4.1 API配置要求
- **Base URL**: `https://api.siliconflow.cn/v1`
- **认证方式**: Bearer Token认证
- **环境变量**:
  - `SILICONFLOW_API_KEY`: Siliconflow平台的API密钥

#### 4.4.2 模型配置
- **快思考模型**: `doubao-seed-1-6-flash-250615`
  - 专门优化用于低延迟快速响应
  - 适合实时对话和填充语生成
  - 支持流式输出以提高响应速度
- **慢思考模型**: `doubao-seed-1-6-thinking-250615`
  - 具备深度推理和复杂任务规划能力
  - 支持工具调用和多模态输入
  - 适合复杂表单分析和决策制定

#### 4.4.3 API调用示例
```python
# LLM API调用
client = AsyncOpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1"
)

# 快思考调用（流式输出推荐）
fast_response = await client.chat.completions.create(
    model="doubao-seed-1-6-flash-250615",
    messages=messages,
    stream=True,
    max_tokens=150,
    temperature=0.7
)

# 慢思考调用
deep_response = await client.chat.completions.create(
    model="doubao-seed-1-6-thinking-250615",
    messages=messages,
    max_tokens=1000,
    temperature=0.3
)

# TTS API调用
tts_response = await aiohttp_session.post(
    "https://api.siliconflow.cn/v1/audio/speech",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "fishaudio/fish-speech-1.5",
        "input": text,
        "voice": "fishaudio/fish-speech-1.5:alex",
        "response_format": "mp3",
        "speed": 1.0
    }
)

# ASR API调用
asr_response = await client.audio.transcriptions.create(
    model="FunAudioLLM/SenseVoiceSmall",
    file=audio_file,
    language="zh",
    prompt="这是一段对话录音"
)
```

#### 4.4.4 Siliconflow平台优势
- **完整的模型生态**: 提供LLM、TTS、ASR一站式服务，减少服务商间的集成复杂度
- **优化的快慢思考模型**: doubao-seed系列模型专门针对实时交互和深度推理进行了优化
- **专业的语音模型**: 
  - FunAudioLLM/SenseVoiceSmall提供高精度中文语音识别
  - fishaudio/fish-speech-1.5提供自然流畅的语音合成
- **低延迟高性能**: 国内部署，访问延迟低，适合实时语音交互场景
- **统一的API接口**: 兼容OpenAI API格式，便于开发和调试
- **模型专业化分工**: 
  - 快思考模型专注实时响应，支持流式输出
  - 慢思考模型专注深度推理，支持复杂任务规划
  - 语音模型针对中文优化，提供更好的识别和合成效果

## 5. 测试计划

### 5.1 单元测试
- Phone Agent语音处理流程测试
- 快慢思考机制测试
- Computer Agent浏览器操作测试
- A2A消息传递机制测试

### 5.2 集成测试
- 双Agent并行工作测试
- 信息传递完整性测试
- 异常处理测试
- 边界情况测试(网络延迟、页面加载慢等)

### 5.3 场景测试
- 表单填写完整流程测试
- 用户提供错误信息场景测试
- 网页元素无法找到场景测试
- 多轮交互场景测试

## 6. 潜在挑战与解决方案

### 6.1 实时性挑战
- **问题**: 语音处理与浏览器操作可能存在延迟
- **解决方案**: 
  - 使用流式API处理语音和文本
  - 实现快思考路径提供即时响应
  - 优化模型参数减少延迟
  - 实现预加载和缓存机制

### 6.2 错误恢复
- **问题**: 浏览器操作失败可能导致状态不一致
- **解决方案**: 
  - 实现操作前状态保存和回滚机制
  - 开发智能重试策略
  - 设计故障转移路径
  - 实现操作结果验证

### 6.3 通信可靠性
- **问题**: Agent间通信可能丢失或延迟
- **解决方案**: 
  - 实现A2A协议中的消息确认机制
  - 开发消息重传和超时处理
  - 使用消息持久化确保可恢复性
  - 实现心跳检测机制监控Agent状态

### 6.4 边听边想的挑战
- **问题**: 基于不完整句子进行推理可能产生错误结论
- **解决方案**:
  - 实现信心评分机制，仅在高信心时执行操作
  - 设计渐进式思考框架，随输入更新调整推理
  - 加入自我纠错机制，允许基于完整信息修正早期判断

## 7. 进度规划

1. **第1天**: 系统架构设计与技术选型确认
2. **第2-3天**: Phone Agent基础实现
   - 实现VAD和ASR集成
   - 开发快慢思考双路径
   - 完成边听边想功能
3. **第4-5天**: Computer Agent基础实现
   - 集成browser-use框架
   - 实现页面分析和操作功能
   - 开发元素定位和交互能力
4. **第6天**: 通信机制实现与集成
   - 实现A2A协议消息传递
   - 开发上下文融合机制
   - 完成双Agent协同工作流程
5. **第7-8天**: 测试、调优和Bug修复
   - 执行单元测试和集成测试
   - 优化性能和响应速度
   - 修复发现的问题
6. **第9天**: 准备演示场景和文档
   - 设计示范场景
   - 完善技术文档
   - 准备演示材料
7. **第10天**: 最终测试与展示准备
   - 执行端到端测试
   - 制作演示视频
   - 最终调整和优化

## 8. 后续优化方向

1. **增强边听边想能力**
   - 研发更快的语义理解模型
   - 实现更精确的中断意图识别
   - 开发更自然的填充语生成机制
2. **优化快慢思考协同**
   - 设计更智能的模型切换策略
   - 实现部分结果快速预览
   - 开发自适应推理深度控制
3. **增强多轮对话理解能力**
   - 实现更长期的上下文记忆
   - 开发对话历史动态摘要
   - 增强指代消解能力
4. **提升浏览器操作可靠性**
   - 研发更稳健的元素定位策略
   - 实现更智能的错误恢复流程
   - 开发操作验证与自我纠正能力 