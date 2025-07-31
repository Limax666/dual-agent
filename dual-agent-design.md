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
- **多模态LLM**: 处理屏幕截图和DOM结构，理解网页内容和布局
- **浏览器自动化**: 基于browser-use或Playwright框架实现浏览器操作
  - 支持元素定位、点击、输入、滚动等基本操作
  - 能够提取页面内容和结构信息
- **状态管理**: 跟踪当前操作状态和执行进度
- **异常处理**: 处理页面加载失败、元素不可见等异常情况

#### 2.2.2 工作模式
- **页面分析**: 基于网页截图和DOM分析页面结构，识别关键元素
- **表单操作**: 根据来自Phone Agent的信息执行表单填写操作
- **操作验证**: 执行操作后验证是否成功，并处理可能的错误情况
- **状态报告**: 将操作结果和当前状态及时反馈给Phone Agent

### 2.3 通信机制

#### 2.3.1 基于Google A2A协议的消息通道
- **协议设计**: 采用Google Agent-to-Agent(A2A)通信协议设计思想
  - 使用标准化的JSON格式消息结构
  - 支持异步通信和实时状态更新
  - 提供可靠的消息传递和错误处理机制
- **消息类型**:
  - `Task`: 代表一个需要执行的任务，包含唯一ID和详细信息
  - `Message`: 代表Agent之间的通信内容，包含多种模态
  - `Artifact`: 代表任务执行产生的结果或中间产物
  - `Part`: 消息或结果的基本组成单位，支持文本、结构化数据等
- **消息结构**: 
  ```json
  {
    "source": "phone|computer",
    "type": "info|error|request|status|action",
    "task_id": "unique_identifier",
    "content": { ... },
    "timestamp": 1633456789
  }
  ```

#### 2.3.2 上下文融合
- **Phone Agent上下文**: `用户输入 + [FROM_COMPUTER_AGENT] 电脑消息`
  - 例如: "我的全名是张三... [FROM_COMPUTER_AGENT] 已找到名字输入框并填写'张'"
- **Computer Agent上下文**: `屏幕状态 + [FROM_PHONE_AGENT] 电话消息`
  - 例如: "[截图数据] + [FROM_PHONE_AGENT] 用户表示他的邮箱是zhang@example.com"

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
  - browser: 基于browser-use的浏览器自动化控制
  - vision_llm: 多模态大语言模型
  - message_queue: A2A消息队列接口
  - state_manager: 操作状态管理器
  
  # 核心方法
  + initialize(url): 初始化浏览器并访问指定URL
  + captureScreenshot(): 捕获当前页面截图
  + extractPageContent(): 提取当前页面DOM和文本内容
  + analyzePageContent(content, screenshot): 分析页面内容并识别可操作元素
  + takeBrowserAction(action): 执行浏览器操作(点击、输入等)
    - findElement(selector): 查找页面元素
    - clickElement(element): 点击元素
    - inputText(element, text): 在元素中输入文本
    - scrollPage(direction): 滚动页面
  + verifyAction(action, expected_result): 验证操作结果
  + handlePhoneMessage(message): 处理来自Phone Agent的消息
  + sendMessageToPhone(message): 发送消息到Phone Agent
  + reportStatus(): 报告当前状态和操作进度
```

### 3.3 实现步骤
1. **设置基础环境和依赖**
   - 配置Siliconflow API密钥和访问凭证
   - 安装browser-use或Playwright
   - 设置A2A消息通信系统
2. **实现Phone Agent核心功能**
   - 实现VAD和Siliconflow ASR集成
   - 开发基于doubao-seed-1-6-flash-250615和doubao-seed-1-6-thinking-250615的快慢思考双路径
   - 完成边听边想功能
   - 开发Siliconflow TTS响应生成
3. **实现Computer Agent核心功能**
   - 集成browser-use框架
   - 实现页面分析和操作功能（使用doubao-seed-1-6-thinking-250615）
   - 开发元素定位和交互能力
4. **设计并实现A2A通信机制**
   - 定义消息格式和通信协议
   - 实现消息队列和处理逻辑
   - 开发上下文融合机制
5. **集成测试与优化**
   - 单元测试各组件功能
   - 进行端到端测试
   - 优化性能和响应速度

## 4. 技术选型

### 4.1 Phone Agent
- **VAD**: Silero VAD (高精度语音活动检测)
- **ASR**: Siliconflow FunAudioLLM/SenseVoiceSmall模型 (支持中文语音识别，高精度实时转录)
- **LLM**:
  - 快思考: doubao-seed-1-6-flash-250615 (Siliconflow平台)
  - 慢思考: doubao-seed-1-6-thinking-250615 (Siliconflow平台)
- **TTS**: Siliconflow fishaudio/fish-speech-1.5模型 (自然语音合成)

### 4.2 Computer Agent
- **浏览器自动化**: browser-use或Playwright
  - browser-use提供更高级的浏览器控制能力和易用API
  - 支持截图、DOM提取和元素交互
- **多模态LLM**: doubao-seed-1-6-thinking-250615 (Siliconflow平台，支持图像理解)
- **元素定位策略**: 
  - XPath和CSS选择器定位
  - 视觉定位(基于截图和坐标)

### 4.3 通信层
- **消息队列**: 基于Redis的异步消息系统
  - 支持发布/订阅模式
  - 提供消息持久化和重试机制
- **Web服务器**: FastAPI作为系统后端
  - 提供RESTful API接口
  - 支持WebSocket进行实时通信

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