#!/usr/bin/env python
"""
测试TTS语音播放功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dual_agent.phone_agent.tts import TTSEngine, TTSProvider

async def test_tts():
    """测试TTS功能"""
    print("🔊 测试TTS语音播放功能")
    print("=" * 40)
    
    # 测试OpenAI TTS
    if os.environ.get("OPENAI_API_KEY"):
        print("\n1. 测试OpenAI TTS...")
        try:
            tts = TTSEngine(
                provider=TTSProvider.OPENAI,
                voice="alloy",
                debug=True
            )
            
            test_text = "你好，我是你的语音助手。这是一个语音播放测试。"
            print(f"   播放文本: {test_text}")
            await tts.speak(test_text)
            print("   ✅ OpenAI TTS测试完成")
            
        except Exception as e:
            print(f"   ❌ OpenAI TTS测试失败: {str(e)}")
    else:
        print("\n1. ⚠️ 跳过OpenAI TTS测试 (未设置API密钥)")
    
    # 测试Dummy TTS
    print("\n2. 测试Dummy TTS...")
    try:
        dummy_tts = TTSEngine(
            provider=TTSProvider.DUMMY,
            debug=True
        )
        
        test_text = "这是一个dummy模式测试。"
        print(f"   播放文本: {test_text}")
        await dummy_tts.speak(test_text)
        print("   ✅ Dummy TTS测试完成")
        
    except Exception as e:
        print(f"   ❌ Dummy TTS测试失败: {str(e)}")
    
    print("\n🎉 TTS测试完成！")
    print("\n💡 使用提示:")
    print("   - 如果听到语音，说明TTS工作正常")
    print("   - 如果只看到文本，检查系统音频设备")
    print("   - 建议使用 --tts openai 启动双Agent系统")

if __name__ == "__main__":
    asyncio.run(test_tts())