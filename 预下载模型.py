#!/usr/bin/env python3
"""
预下载本地模型脚本
在正式运行项目前，可以先运行此脚本下载所需模型
"""

import torch
import asyncio
from pathlib import Path

async def download_models():
    print("🚀 开始预下载模型...")
    
    try:
        # 1. 下载Silero VAD模型
        print("\n📥 下载Silero VAD模型...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False
        )
        print("✅ Silero VAD模型下载完成")
        
        # 2. 下载faster-whisper模型
        print("\n📥 下载faster-whisper模型...")
        try:
            from faster_whisper import WhisperModel
            
            # 下载base模型（推荐）
            print("正在下载whisper base模型（约74MB）...")
            model = WhisperModel("base", device="cpu")
            print("✅ faster-whisper base模型下载完成")
            
            # 可选：下载tiny模型（更小更快）
            print("正在下载whisper tiny模型（约39MB）...")
            model_tiny = WhisperModel("tiny", device="cpu")
            print("✅ faster-whisper tiny模型下载完成")
            
        except ImportError:
            print("⚠️  faster-whisper未安装，请先运行: pip install faster-whisper")
            return False
            
    except Exception as e:
        print(f"❌ 模型下载出错: {str(e)}")
        return False
    
    print("\n🎉 所有模型下载完成！现在可以离线运行项目了。")
    
    # 显示模型存储位置
    import os
    cache_dir = os.path.expanduser("~/.cache")
    print(f"\n📁 模型存储位置:")
    print(f"   PyTorch Hub: {cache_dir}/torch/hub/")
    print(f"   Hugging Face: {cache_dir}/huggingface/hub/")
    
    return True

if __name__ == "__main__":
    # 检查网络连接
    print("🌐 检查网络连接...")
    try:
        import urllib.request
        urllib.request.urlopen('https://pytorch.org', timeout=10)
        print("✅ 网络连接正常")
    except:
        print("❌ 网络连接异常，请检查网络或代理设置")
        exit(1)
    
    # 运行下载
    asyncio.run(download_models())