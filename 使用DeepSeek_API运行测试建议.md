# 使用DeepSeek API运行Dual Agent项目的测试建议

## 方案概述

由于您有DeepSeek API key而非OpenAI API key，以下提供几种不修改项目代码的测试方案，按推荐程度排序。

## 🎯 方案一：混合模式（推荐）

### 配置说明
使用本地模型处理语音，DeepSeek API处理对话逻辑，dummy模式处理TTS。

### 环境准备
```bash
# 1. 安装项目依赖
pip install -r requirements.txt

# 2. 安装本地语音处理依赖
pip install faster-whisper
pip install sounddevice

# 3. 设置环境变量（关键步骤）
export OPENAI_API_KEY=your_deepseek_api_key
export OPENAI_API_BASE=https://api.deepseek.com/v1
```

### 运行命令
```bash
python -m dual_agent.examples.run_phone_agent \
    --local-asr \
    --tts dummy \
    --debug \
    --fast-model deepseek-chat \
    --deep-model deepseek-chat
```

### 工作原理
- **ASR**: 使用本地faster-whisper模型进行语音识别
- **LLM**: 通过设置OPENAI_API_BASE环境变量将请求转发到DeepSeek API
- **TTS**: 使用dummy模式，在控制台显示要说的内容而不实际播放语音
- **VAD**: 使用本地Silero VAD模型进行语音检测

## 🔧 方案二：完全本地测试模式

### 配置说明
使用项目内置的dummy模式测试完整架构流程。

### 运行命令
```bash
python -m dual_agent.examples.run_phone_agent \
    --dummy \
    --debug \
    --tts dummy
```

### 工作原理
- 所有AI调用都使用模拟数据
- 可以测试完整的语音处理流程
- 验证各组件间的通信机制
- 适合理解项目架构

## 🌐 方案三：API代理模式

### 配置说明
通过第三方服务或自建代理将OpenAI API调用转换为DeepSeek API调用。

### 使用one-api代理服务
```bash
# 1. 部署one-api代理服务（Docker方式）
docker run -d --name one-api \
    -p 3000:3000 \
    -e SQL_DSN="one-api.db" \
    -v $(pwd)/data:/app/data \
    justsong/one-api:latest

# 2. 在one-api中配置DeepSeek渠道

# 3. 设置环境变量
export OPENAI_API_KEY=your_one_api_token
export OPENAI_API_BASE=http://localhost:3000/v1

# 4. 运行项目
python -m dual_agent.examples.run_phone_agent --debug
```

## 📋 测试步骤建议

### 1. 环境检查
```bash
# 检查Python版本（建议3.8+）
python --version

# 检查音频设备
python -c "import sounddevice as sd; print(sd.query_devices())"

# 检查依赖安装
python -c "import torch, torchaudio; print('PyTorch OK')"
```

### 2. 分步测试

#### 步骤1：测试VAD组件
```python
# 创建test_vad.py
import asyncio
from dual_agent.phone_agent.vad import SileroVAD

async def test_vad():
    vad = SileroVAD()
    print("VAD初始化成功")
    
asyncio.run(test_vad())
```

#### 步骤2：测试ASR组件
```python
# 创建test_asr.py
import asyncio
from dual_agent.phone_agent.asr import StreamingASR

async def test_asr():
    asr = StreamingASR(use_api=False, local_model_size="base")
    print("ASR初始化成功")
    
asyncio.run(test_asr())
```

#### 步骤3：测试完整流程
使用上述推荐的运行命令。

## 🔍 预期效果

### 成功运行的标志
```
初始化Phone Agent...
Silero VAD initialized
正在加载本地Whisper模型: base...
本地Whisper模型加载完成
Phone Agent初始化完成，正在启动...
[时间戳] 启动Phone Agent
[时间戳] 进入主循环
[时间戳] 开始说话: 你好，我是你的电话助手，请问有什么可以帮助你的吗？
```

### 交互测试
1. 对着麦克风说话
2. 观察控制台输出：
   - VAD检测到语音活动
   - ASR转录结果
   - 快思考和深度思考的响应
   - TTS输出内容（如果使用dummy模式）

## ⚠️ 注意事项

### 1. DeepSeek API兼容性
DeepSeek API基本兼容OpenAI格式，但可能存在细微差异：
- 模型名称使用`deepseek-chat`而非`gpt-4o`
- 某些参数可能不完全兼容

### 2. 本地模型资源需求
- faster-whisper模型会占用一定磁盘空间和内存
- 首次运行会下载Silero VAD模型

### 3. 音频设备权限
确保Python程序有麦克风访问权限。

## 🚀 进阶配置

### DeepSeek模型优化配置
```bash
python -m dual_agent.examples.run_phone_agent \
    --local-asr \
    --tts dummy \
    --debug \
    --fast-model deepseek-chat \
    --deep-model deepseek-chat \
    --vad-threshold 0.3 \
    --language zh
```

### 自定义提示词测试
可以通过修改运行示例中的`system_prompt`变量来测试不同的对话场景。

## 📊 故障排除

### 常见问题
1. **模型下载失败**: 检查网络连接，可能需要科学上网
2. **音频设备错误**: 使用`--device-index`参数指定正确的麦克风设备
3. **API调用失败**: 检查DeepSeek API key和网络连接

### 调试建议
使用`--debug`参数获取详细日志，帮助定位问题。

这些方案可以让您在不修改项目代码的情况下体验Dual Agent的核心功能，特别是创新的"边听边想"语音交互能力。

## 🎪 Windows系统特别说明

如果您使用的是Windows系统，环境变量设置方式稍有不同：

### PowerShell设置环境变量
```powershell
$env:OPENAI_API_KEY="your_deepseek_api_key"
$env:OPENAI_API_BASE="https://api.deepseek.com/v1"
```

### CMD设置环境变量
```cmd
set OPENAI_API_KEY=your_deepseek_api_key
set OPENAI_API_BASE=https://api.deepseek.com/v1
```

### 运行命令（Windows）
```cmd
python -m dual_agent.examples.run_phone_agent --local-asr --tts dummy --debug --fast-model deepseek-chat --deep-model deepseek-chat
```

## 💡 额外提示

1. **首次运行较慢**: 第一次运行会下载VAD和Whisper模型，请耐心等待
2. **内存使用**: 本地模型会占用一定内存，建议至少8GB RAM
3. **测试建议**: 先使用dummy模式验证基本流程，再切换到实际API模式