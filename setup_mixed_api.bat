@echo off
REM 混合API配置脚本 - Windows版本
REM 
REM 这个配置允许您同时使用：
REM - Siliconflow API: ASR (语音识别) + TTS (语音合成)  
REM - Doubao API: LLM (快慢思考)

echo 🔧 配置混合API环境变量...
echo.

echo 请设置以下环境变量：
echo.

echo 1. SILICONFLOW_API_KEY (用于语音识别和合成):
echo    set SILICONFLOW_API_KEY=your_siliconflow_api_key_here
echo.

echo 2. ARK_API_KEY (用于Doubao快慢思考模型):
echo    set ARK_API_KEY=your_ark_api_key_here  
echo.

echo 📋 当前配置验证:
echo SILICONFLOW_API_KEY: %SILICONFLOW_API_KEY%
echo ARK_API_KEY: %ARK_API_KEY%
echo.

echo ✅ 配置完成后，运行以下命令启动系统:
echo cd dual_agent
echo python examples/run_dual_agent.py --debug
echo.

echo 🔄 系统将使用:
echo   🎤 ASR: Siliconflow FunAudioLLM/SenseVoiceSmall
echo   🔊 TTS: Siliconflow fishaudio/fish-speech-1.5  
echo   ⚡ 快思考: Doubao doubao-seed-1-6-flash-250615
echo   🧠 慢思考: Doubao doubao-seed-1-6-thinking-250615
echo.

pause