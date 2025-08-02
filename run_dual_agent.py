#!/usr/bin/env python
"""
通用双Agent系统运行脚本

支持用户指定任意URL，通过语音交流与双Agent系统协作完成各种网页操作：
- 网页打开和浏览
- 表单填写
- 信息搜索
- 页面交互

使用方法：
python run_dual_agent.py [--url URL] [--debug] [--text-mode]
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dual_agent_system import DualAgentSystem, DualAgentSystemConfig

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="通用双Agent系统 - 支持任意网页的语音交互操作",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python run_dual_agent.py
  python run_dual_agent.py --url https://www.example.com
  python run_dual_agent.py --url https://forms.gle/abc123 --debug
  python run_dual_agent.py --text-mode  # 使用文本输入模式

支持的操作类型：
  - 表单填写 (注册页面、联系表单、调查问卷等)
  - 信息搜索 (搜索引擎、商品搜索等)
  - 页面浏览 (新闻网站、博客、文档等)
  - 数据输入 (CRM系统、管理后台等)
        """
    )
    
    parser.add_argument(
        "--url", 
        type=str, 
        default=None,
        help="要打开的目标网页URL (如果不指定，可在运行时通过语音告诉系统)"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="启用调试模式，显示详细的处理过程"
    )
    
    parser.add_argument(
        "--vad-threshold", 
        type=float, 
        default=0.6,
        help="语音检测阈值 (0.0-1.0, 默认0.6)"
    )
    
    parser.add_argument(
        "--device-index", 
        type=int, 
        default=0,
        help="麦克风设备索引 (默认0)"
    )
    
    parser.add_argument(
        "--text-mode", 
        action="store_true",
        help="强制使用文本输入模式而非语音"
    )
    
    return parser.parse_args()

def check_api_keys():
    """检查必要的API密钥"""
    required_keys = {
        "SILICONFLOW_API_KEY": "Phone Agent的语音服务 (TTS/ASR)",
        "ARK_API_KEY": "Phone Agent的思考引擎 (Doubao)",
        "OPENAI_API_KEY": "Computer Agent的网页操作 (GPT)"
    }
    
    missing_keys = []
    available_keys = {}
    
    for key, description in required_keys.items():
        value = os.environ.get(key)
        if value:
            available_keys[key] = value
            print(f"✅ {key}: {value[:10]}... ({description})")
        else:
            missing_keys.append(key)
            print(f"❌ {key}: 未设置 ({description})")
    
    if missing_keys:
        print(f"\n❌ 缺少必要的API密钥: {', '.join(missing_keys)}")
        print("\n💡 请设置环境变量:")
        print("export SILICONFLOW_API_KEY=your_siliconflow_key")
        print("export ARK_API_KEY=your_doubao_ark_key") 
        print("export OPENAI_API_KEY=your_openai_key")
        return False, {}
    
    return True, available_keys

def show_welcome_message(args):
    """显示欢迎信息"""
    print("🤖 通用双Agent系统")
    print("=" * 60)
    print("📞 Phone Agent: 语音交互界面")
    print("💻 Computer Agent: 智能网页操作")
    print("🔗 通信机制: 实时协同工作")
    print("=" * 60)
    
    if args.url:
        print(f"🌐 目标网站: {args.url}")
    else:
        print("🌐 目标网站: 运行时通过语音指定")
    
    print(f"🎤 语音检测: 阈值 {args.vad_threshold}, 设备 {args.device_index}")
    print(f"🔧 调试模式: {'启用' if args.debug else '禁用'}")
    print(f"⌨️  输入模式: {'文本' if args.text_mode else '语音'}")
    print()

def show_usage_examples():
    """显示使用示例"""
    print("💡 使用示例：")
    print()
    print("📋 表单填写：")
    print("  👤: '打开 https://forms.gle/abc123'")
    print("  🤖: '好的，正在打开表单页面...'")
    print("  👤: '帮我填写这个表单，我的名字是张三'")
    print("  🤖: '好的，已填写姓名。请告诉我您的邮箱地址。'")
    print()
    print("🔍 信息搜索：")
    print("  👤: '打开百度搜索人工智能'")
    print("  🤖: '好的，正在打开百度并搜索人工智能...'")
    print()
    print("📰 页面浏览：")
    print("  👤: '打开GitHub首页'")
    print("  🤖: '好的，正在打开GitHub...'")
    print("  👤: '帮我找到登录按钮'")
    print("  🤖: '我找到了登录按钮，需要我点击吗？'")
    print()

async def create_and_run_system(args, api_keys):
    """创建并运行双Agent系统"""
    
    # 创建系统配置
    config = DualAgentSystemConfig(
        # Computer Agent配置
        computer_target_url=args.url,  # 可能为None，运行时指定
        computer_debug=args.debug,
        
        # Phone Agent配置
        phone_vad_threshold=args.vad_threshold,
        phone_device_index=args.device_index,
        phone_debug=args.debug,
        
        # 系统配置
        enable_communication=True,
        system_debug=args.debug,
        
        # API密钥
        siliconflow_api_key=api_keys.get("SILICONFLOW_API_KEY"),
        ark_api_key=api_keys.get("ARK_API_KEY"),
        openai_api_key=api_keys.get("OPENAI_API_KEY")
    )
    
    # 如果指定了文本模式，模拟PyAudio不可用
    if args.text_mode:
        print("📝 使用文本输入模式")
        # 这将在系统中触发文本模拟模式
    
    print("\n🚀 启动双Agent系统...")
    
    try:
        # 创建并启动系统
        system = DualAgentSystem(config)
        await system.start()
        
    except Exception as e:
        print(f"❌ 系统运行失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 显示欢迎信息
    show_welcome_message(args)
    
    # 检查API密钥
    print("🔑 检查API密钥...")
    keys_ok, api_keys = check_api_keys()
    if not keys_ok:
        return
    
    print("✅ API密钥检查通过")
    
    # 显示使用示例
    show_usage_examples()
    
    # 等待用户确认
    if args.url:
        confirm_msg = f"按回车键启动系统并打开 {args.url}..."
    else:
        confirm_msg = "按回车键启动系统，您可以通过语音告诉我要打开哪个网站..."
    
    input(confirm_msg)
    
    # 创建并运行系统
    await create_and_run_system(args, api_keys)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()