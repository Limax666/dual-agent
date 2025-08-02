# Simple Phone Agent - 双API架构

## 概述

基于设计文档重构的简化版Phone Agent，专注于实时语音交互功能，采用双API架构以实现最佳性能：

- **Doubao ARK API**: 用于快思考和深度思考模型
- **Siliconflow API**: 用于语音识别(ASR)和语音合成(TTS)

## 架构设计

### API服务分工

| 服务 | 提供商 | 用途 | 模型 |
|------|--------|------|------|
| 快思考 | Doubao | 实时对话响应 | doubao-seed-1-6-flash-250615 |
| 深度思考 | Doubao | 复杂推理分析 | doubao-seed-1-6-thinking-250615 |
| ASR语音识别 | Siliconflow | 语音转文本 | FunAudioLLM/SenseVoiceSmall |
| TTS语音合成 | Siliconflow | 文本转语音 | fishaudio/fish-speech-1.5:alex |

### 核心功能

1. **实时语音检测**: 使用Silero VAD进行语音活动检测
2. **边听边想**: 在用户说话过程中实时分析和思考
3. **混合思考引擎**: 快思考提供即时反馈，深度思考进行复杂分析
4. **自然语音交互**: 高质量的语音识别和合成

## 安装和配置

### 1. 依赖安装

```bash
pip install torch numpy openai aiohttp pyaudio pygame
```

### 2. API密钥配置

需要设置两个API密钥：

```bash
# Linux/macOS
export ARK_API_KEY=your_doubao_ark_api_key
export SILICONFLOW_API_KEY=your_siliconflow_api_key

# Windows
set ARK_API_KEY=your_doubao_ark_api_key
set SILICONFLOW_API_KEY=your_siliconflow_api_key
```

## 使用方法

### 运行测试脚本

```bash
python test_simple_phone_agent.py
```

### 测试流程

1. **初始化检查**: 系统会检查API密钥和依赖
2. **配置确认**: 显示双API架构配置信息
3. **设备检测**: 检测音频设备并显示可用设备列表
4. **问候语播放**: 使用Siliconflow TTS播放问候语
5. **实时对话**: 开始监听用户语音输入

### 对话流程

```
🎤 用户说话 
↓
🎯 VAD语音检测
↓
🔄 Siliconflow ASR识别
↓
🤔 Doubao混合思考引擎处理
↓
🔊 Siliconflow TTS语音回应
```

## 配置选项

### SimplePhoneAgentConfig参数

```python
config = SimplePhoneAgentConfig(
    # VAD配置
    vad_threshold=0.6,              # 语音检测阈值 (0.0-1.0)
    vad_sampling_rate=16000,        # 采样率
    
    # ASR配置 (Siliconflow)
    asr_model_name="FunAudioLLM/SenseVoiceSmall",
    language="zh",                  # 语言代码
    
    # 思考引擎配置 (Doubao)
    fast_think_model_name="doubao-seed-1-6-flash-250615",
    deep_think_model_name="doubao-seed-1-6-thinking-250615",
    
    # TTS配置 (Siliconflow)
    tts_voice="fishaudio/fish-speech-1.5:alex",
    
    # 设备配置
    device_index=0,                 # 麦克风设备索引
    
    # 功能开关
    enable_thinking_while_listening=True,  # 启用边听边想
    debug=True,                     # 调试模式
    
    # API密钥
    siliconflow_api_key=None,       # 自动从环境变量获取
    ark_api_key=None                # 自动从环境变量获取
)
```

## 故障排除

### 常见问题

1. **API密钥错误**
   - 确保设置了两个环境变量: `ARK_API_KEY` 和 `SILICONFLOW_API_KEY`
   - 检查密钥是否有效和有足够余额

2. **音频设备问题**
   - 确保麦克风正常工作
   - 检查设备索引是否正确 (默认为0)
   - 安装pyaudio: `pip install pyaudio`

3. **网络连接问题**
   - 确保网络连接正常
   - 检查防火墙设置
   - 某些地区可能需要代理

4. **依赖缺失**
   - 运行依赖检查: 脚本会自动检测缺失的依赖
   - 安装缺失的包: `pip install package_name`

### 调试模式

启用调试模式可以看到详细的处理过程：

```python
config.debug = True
```

调试信息包括：
- VAD语音检测概率
- ASR识别结果
- 思考引擎处理过程
- TTS语音生成状态
- 音频设备信息

## 性能优化

### VAD调整

如果误检率高，可以调整VAD阈值：

```python
config.vad_threshold = 0.7  # 提高阈值减少误检
```

### 思考引擎优化

- 快思考模型专注于即时响应，简短回复
- 深度思考模型进行复杂分析，详细理解

### 网络优化

- Doubao API延迟较低，适合实时交互
- Siliconflow API针对语音优化，音质更好

## 扩展功能

当前版本专注于基础语音交互，后续可以扩展：

1. **多轮对话管理**: 增强上下文理解
2. **情绪识别**: 基于语音特征识别情绪
3. **多语言支持**: 支持其他语言识别和合成
4. **自定义唤醒词**: 添加语音唤醒功能
5. **Agent间通信**: 与Computer Agent集成

## 版本信息

- **当前版本**: Simple Phone Agent v1.0
- **基于**: dual-agent-design.md 设计文档
- **最后更新**: 2025年
- **支持的Python版本**: 3.8+