Siliconflow：开源模型的最佳选择
Siliconflow 为 AI Agent 开发提供了完整的模型生态，包括 LLM、TTS（文本转语音）和 ASR（语音识别）。

LLM 模型
推荐用于 Agent 开发的模型：

Kimi K2 Instruct：moonshotai/Kimi-K2-Instruct
DeepSeek R1 0528：deepseek-ai/DeepSeek-R1
Qwen3 235B：Qwen/Qwen3-235B-A22B-Instruct-2507

"""
import requests

url = "https://api.siliconflow.cn/v1/chat/completions"

payload = {
    "model": "moonshotai/Kimi-K2-Instruct",
    "messages": [
        {
            "role": "user",
            "content": "What opportunities and challenges will the Chinese large model industry face in 2025?"
        }
    ],
    "stream": True  # Agent 开发推荐使用流式输出
}
headers = {
    "Authorization": "Bearer <SILICONFLOW_API_KEY>",
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers, stream=True)
# 处理流式响应...
"""

语音 Agent 开发套件
TTS 文本转语音
使用 Fish Audio 或 CosyVoice 进行语音合成：
"""
import requests
import os

url = "https://api.siliconflow.cn/v1/audio/speech"

payload = {
    "model": "fishaudio/fish-speech-1.5",
    "input": "Nice to meet you!",
    "voice": "fishaudio/fish-speech-1.5:alex",
    "response_format": "mp3",
    "speed": 1.0
}
headers = {
    "Authorization": "Bearer " + os.environ['SILICONFLOW_API_KEY'],
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers)

# 保存音频文件
with open("output.mp3", "wb") as f:
    f.write(response.content)
"""

ASR 语音识别
使用 SenseVoice 进行语音识别：
"""
from openai import OpenAI
import os

client = OpenAI(
  base_url="https://api.siliconflow.cn/v1",
  api_key=os.environ['SILICONFLOW_API_KEY'],
)

def transcribe_audio(speech_file_path):
    with open(speech_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="FunAudioLLM/SenseVoiceSmall", 
            file=audio_file,
            language="zh",  # 指定语言可以提高准确率
            prompt="这是一段对话录音"  # 提供上下文
        )
    return transcription.text

# 在实时语音 Agent 中的使用示例
def process_audio_chunk(audio_chunk):
    # 1. 使用 VAD 检测语音结束（推荐 Silero VAD）
    # 2. 调用 ASR 识别
    text = transcribe_audio(audio_chunk)
    # 3. 传递给 LLM 处理
    return text
"""