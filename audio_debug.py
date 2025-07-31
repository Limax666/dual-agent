#!/usr/bin/env python
"""
音频设备检测工具
检测系统中的音频输入设备和PyAudio配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_audio_devices():
    """检测音频设备"""
    print("🔍 检测音频设备...")
    
    try:
        import pyaudio
        print("✅ PyAudio 已安装")
    except ImportError:
        print("❌ PyAudio 未安装，请运行: pip install pyaudio")
        return
    
    # 初始化PyAudio
    p = pyaudio.PyAudio()
    
    print(f"\n📊 系统音频信息:")
    print(f"PyAudio版本: {pyaudio.__version__}")
    print(f"设备总数: {p.get_device_count()}")
    
    print(f"\n🎤 输入设备列表:")
    input_devices = []
    
    for i in range(p.get_device_count()):
        try:
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                input_devices.append((i, device_info))
                print(f"  设备 {i}: {device_info['name']}")
                print(f"    - 最大输入通道: {device_info['maxInputChannels']}")
                print(f"    - 默认采样率: {device_info['defaultSampleRate']}")
                print(f"    - API: {p.get_host_api_info_by_index(device_info['hostApi'])['name']}")
        except Exception as e:
            print(f"  设备 {i}: 获取信息失败 - {e}")
    
    # 获取默认设备
    try:
        default_input = p.get_default_input_device_info()
        print(f"\n🎯 默认输入设备:")
        print(f"  索引: {default_input['index']}")
        print(f"  名称: {default_input['name']}")
        print(f"  采样率: {default_input['defaultSampleRate']}")
    except Exception as e:
        print(f"\n❌ 无法获取默认输入设备: {e}")
    
    p.terminate()
    
    return input_devices

def test_microphone(device_index=None, duration=3):
    """测试麦克风录音"""
    print(f"\n🎤 测试麦克风录音 (时长: {duration}秒)...")
    
    try:
        import pyaudio
        import numpy as np
        import time
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        return
    
    # 音频配置
    chunk_size = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 16000
    
    p = pyaudio.PyAudio()
    
    try:
        # 打开音频流
        if device_index is not None:
            print(f"使用设备索引: {device_index}")
        else:
            print("使用默认设备")
            
        stream = p.open(
            format=format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=chunk_size
        )
        
        print("🔴 开始录音，请说话...")
        
        frames = []
        max_amplitude = 0
        
        for i in range(int(rate / chunk_size * duration)):
            try:
                data = stream.read(chunk_size, exception_on_overflow=False)
                frames.append(data)
                
                # 计算音频幅度
                audio_np = np.frombuffer(data, dtype=np.int16)
                amplitude = np.max(np.abs(audio_np))
                max_amplitude = max(max_amplitude, amplitude)
                
                # 显示音量条
                volume_bar = "█" * int(amplitude / 3276.8)  # 0-10的音量条
                print(f"\r音量: {volume_bar:<10} ({amplitude:5d})", end="", flush=True)
                
            except Exception as e:
                print(f"\n录音错误: {e}")
                break
        
        print(f"\n🛑 录音结束")
        print(f"最大音量: {max_amplitude}")
        
        if max_amplitude > 1000:
            print("✅ 麦克风工作正常，检测到音频输入")
        else:
            print("⚠️ 麦克风可能有问题，音频输入很弱或没有输入")
        
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"❌ 麦克风测试失败: {e}")
    finally:
        p.terminate()

def test_vad():
    """测试VAD模型"""
    print(f"\n🧠 测试VAD模型...")
    
    try:
        import torch
        from dual_agent.phone_agent.vad import SileroVAD
        
        print("✅ 正在加载Silero VAD模型...")
        vad = SileroVAD(threshold=0.5, sampling_rate=16000)
        print("✅ VAD模型加载成功")
        
        # 创建测试音频（静音）
        test_audio = torch.zeros(16000)  # 1秒静音
        speech_prob = vad.model(test_audio, 16000).item()
        print(f"静音测试 - 语音概率: {speech_prob:.3f}")
        
        # 创建测试音频（随机噪声）
        noise_audio = torch.randn(16000) * 0.1
        speech_prob = vad.model(noise_audio, 16000).item()
        print(f"噪声测试 - 语音概率: {speech_prob:.3f}")
        
        print("✅ VAD模型测试完成")
        
    except Exception as e:
        print(f"❌ VAD测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Phone Agent 音频诊断工具")
    print("=" * 60)
    
    # 1. 检测音频设备
    input_devices = check_audio_devices()
    
    # 2. 测试VAD
    test_vad()
    
    # 3. 测试麦克风
    if input_devices:
        print(f"\n请选择要测试的麦克风设备:")
        for i, (device_index, device_info) in enumerate(input_devices):
            print(f"  {i}: 设备{device_index} - {device_info['name']}")
        
        try:
            choice = input(f"\n输入设备编号 (0-{len(input_devices)-1}) 或按Enter使用默认: ")
            if choice.strip():
                device_idx = input_devices[int(choice)][0]
            else:
                device_idx = None
            
            test_microphone(device_idx, duration=5)
            
        except (ValueError, IndexError):
            print("无效输入，使用默认设备")
            test_microphone(None, duration=5)
        except KeyboardInterrupt:
            print("\n测试被中断")
    
    print(f"\n✅ 诊断完成")