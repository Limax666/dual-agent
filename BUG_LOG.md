pygame 2.6.1 (SDL 2.28.4, Python 3.9.21)
Hello from the pygame community. https://www.pygame.org/contribute.html
==================================================================== test session starts ====================================================================
platform win32 -- Python 3.9.21, pytest-8.4.1, pluggy-1.6.0 -- D:\anaconda\envs\myenv\python.exe       
cachedir: .pytest_cache
rootdir: E:\AI Agent\ai-agent-projects-main
plugins: anyio-4.8.0, hydra-core-1.3.2, langsmith-0.4.6, asyncio-1.1.0, typeguard-4.3.0
asyncio: mode=strict, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 9 items

dual_agent/tests/test_phone_agent.py::test_vad_initialization Using cache found in C:\Users\59216/.cache\torch\hub\snakers4_silero-vad_master
Silero VAD initialized
PASSED
dual_agent/tests/test_phone_agent.py::test_vad_speech_detection Using cache found in C:\Users\59216/.cache\torch\hub\snakers4_silero-vad_master
Silero VAD initialized
SKIPPED (跳过VAD测试，可能缺少依赖: The following operation failed in the TorchScr...)       
dual_agent/tests/test_phone_agent.py::test_asr_process_audio 正在加载本地Whisper模型: base...
本地Whisper模型加载完成
PASSED
dual_agent/tests/test_phone_agent.py::test_thinking_engine_fast_thinking PASSED
dual_agent/tests/test_phone_agent.py::test_thinking_engine_deep_thinking PASSED
dual_agent/tests/test_phone_agent.py::test_thinking_engine_filler_generation PASSED
dual_agent/tests/test_phone_agent.py::test_tts_text_to_speech PASSED
dual_agent/tests/test_phone_agent.py::test_phone_agent_initialization Using cache found in C:\Users\59216/.cache\torch\hub\snakers4_silero-vad_master
Silero VAD initialized
正在加载本地Whisper模型: base...
本地Whisper模型加载完成
PASSED
dual_agent/tests/test_phone_agent.py::test_process_complete_speech Using cache found in C:\Users\59216/.cache\torch\hub\snakers4_silero-vad_master
Silero VAD initialized
正在加载本地Whisper模型: base...
本地Whisper模型加载完成
[15:15:52] 处理完整语音
[15:15:52] 完整转录: 这是测试语音
FAILED

========================================================================= FAILURES ========================================================================== 
_______________________________________________________________ test_process_complete_speech ________________________________________________________________ 

mock_phone_agent = (<dual_agent.phone_agent.phone_agent.PhoneAgent object at 0x0000020D8D3BA430>, <MagicMock name='SileroVAD()' id='22572...1616'>, <MagicMock name='MixedThinkingEngine()' id='2257227257552'>, <MagicMock name='TTSEngine()' id='2257227232640'>)

    @pytest.mark.asyncio
    async def test_process_complete_speech(mock_phone_agent):
        """测试处理完整语音"""
        agent, _, mock_asr, mock_engine, _ = mock_phone_agent

        # 模拟ASR结果
        mock_asr.process_audio_segment.return_value = asyncio.Future()
        mock_asr.process_audio_segment.return_value.set_result({"text": "这是测试语音", "segments": []})

        # 模拟思考引擎结果
        mock_engine.think.return_value = asyncio.Future()
        mock_engine.think.return_value.set_result(("快速回复", "深度回复"))

        # *** FIX: Configure generate_filler to be awaitable ***
        mock_engine.generate_filler.return_value = asyncio.Future()
        mock_engine.generate_filler.return_value.set_result("嗯，让我想想...")

        # 替换发送消息函数，避免实际发送
        agent.send_message_to_computer = MagicMock()
        agent.send_message_to_computer.return_value = asyncio.Future()
        agent.send_message_to_computer.return_value.set_result(None)

        # 替换speak函数，避免实际播放
        agent.speak = MagicMock()
        agent.speak.return_value = asyncio.Future()
        agent.speak.return_value.set_result(None)

        # 模拟音频段
        mock_audio = torch.zeros(16000)

        # 执行测试
>       await agent.process_complete_speech(mock_audio)

dual_agent\tests\test_phone_agent.py:226:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
        # 模拟音频段
        mock_audio = torch.zeros(16000)

        # 执行测试
>       await agent.process_complete_speech(mock_audio)

dual_agent\tests\test_phone_agent.py:226:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
        mock_audio = torch.zeros(16000)

        # 执行测试
>       await agent.process_complete_speech(mock_audio)

dual_agent\tests\test_phone_agent.py:226:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

        # 执行测试
>       await agent.process_complete_speech(mock_audio)

dual_agent\tests\test_phone_agent.py:226:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
>       await agent.process_complete_speech(mock_audio)

dual_agent\tests\test_phone_agent.py:226:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\tests\test_phone_agent.py:226:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
dual_agent\phone_agent\phone_agent.py:333: in process_complete_speech
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
    asyncio.create_task(self.speak(filler))
D:\anaconda\envs\myenv\lib\asyncio\tasks.py:361: in create_task
    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <ProactorEventLoop running=False closed=False debug=False>, coro = <Future finished result=None>

    task = loop.create_task(coro)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <ProactorEventLoop running=False closed=False debug=False>, coro = <Future finished result=None>


self = <ProactorEventLoop running=False closed=False debug=False>, coro = <Future finished result=None>


    def create_task(self, coro, *, name=None):
        """Schedule a coroutine object.

        Return a task object.
    def create_task(self, coro, *, name=None):
        """Schedule a coroutine object.

        Return a task object.

        Return a task object.
        """
        self._check_closed()
        Return a task object.
        """
        self._check_closed()
        """
        self._check_closed()
        if self._task_factory is None:
        self._check_closed()
        if self._task_factory is None:
        if self._task_factory is None:
>           task = tasks.Task(coro, loop=self, name=name)
>           task = tasks.Task(coro, loop=self, name=name)
E           TypeError: a coroutine was expected, got <Future finished result=None>

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError



D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError


D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)


D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 

D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
D:\anaconda\envs\myenv\lib\asyncio\base_events.py:438: TypeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================================== short test summary info ================================================================== 
FAILED dual_agent/tests/test_phone_agent.py::test_process_complete_speech - TypeError: a coroutine was expected, got <Future finished result=None>
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
==================================================== 1 failed, 7 passed, 1 skipped, 1 warning in 11.42s ===================================================== 

Round 2:
========================================================================= FAILURES ========================================================================== 
_______________________________________________________________ test_process_complete_speech ________________________________________________________________ 

mock_phone_agent = (<dual_agent.phone_agent.phone_agent.PhoneAgent object at 0x00000208E1DC69A0>, <MagicMock name='SileroVAD()' id='22371...4224'>, <MagicMock name='MixedThinkingEngine()' id='2237172337728'>, <MagicMock name='TTSEngine()' id='2237172284144'>)

    @pytest.mark.asyncio
    async def test_process_complete_speech(mock_phone_agent):
        """测试处理完整语音"""
        agent, _, mock_asr, mock_engine, _ = mock_phone_agent

        # 模拟ASR结果
        mock_asr.process_audio_segment.return_value = asyncio.Future()
        mock_asr.process_audio_segment.return_value.set_result({"text": "这是测试语音", "segments": []})

        # 模拟思考引擎结果
        mock_engine.think.return_value = asyncio.Future()
        mock_engine.think.return_value.set_result(("快速回复", "深度回复"))

        # *** FIX: Configure generate_filler to be awaitable ***
        mock_engine.generate_filler.return_value = asyncio.Future()
        mock_engine.generate_filler.return_value.set_result("嗯，让我想想...")

        # 使用AsyncMock确保mock的异步方法返回协程对象，提高代码一致性和健壮性
        agent.send_message_to_computer = AsyncMock()

        # 使用AsyncMock确保mock的异步方法返回协程对象，以兼容asyncio.create_task()
        agent.speak = AsyncMock()

        # 模拟音频段
        mock_audio = torch.zeros(16000)

        # 执行测试
        await agent.process_complete_speech(mock_audio)

        # 验证ASR被调用
        mock_asr.process_audio_segment.assert_called_once_with(mock_audio)

        # 验证思考引擎被调用
>       mock_engine.think.assert_awaited_once()

dual_agent\tests\test_phone_agent.py:228:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <MagicMock name='MixedThinkingEngine().think' id='2237153480176'>, name = 'assert_awaited_once'

    def __getattr__(self, name):
        if name in {'_mock_methods', '_mock_unsafe'}:
            raise AttributeError(name)
        elif self._mock_methods is not None:
            if name not in self._mock_methods or name in _all_magics:
                raise AttributeError("Mock object has no attribute %r" % name)
        elif _is_magic(name):
            raise AttributeError(name)
        if not self._mock_unsafe:
            if name.startswith(('assert', 'assret')):
>               raise AttributeError("Attributes cannot start with 'assert' "
                                     "or 'assret'")
E               AttributeError: Attributes cannot start with 'assert' or 'assret'

D:\anaconda\envs\myenv\lib\unittest\mock.py:635: AttributeError
===================================================================== warnings summary ====================================================================== 
D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290
  D:\anaconda\envs\myenv\lib\site-packages\_pytest\config\__init__.py:1290: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; anyio 
    self._mark_plugins_for_rewrite(hook, disable_autoload)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================================== short test summary info ================================================================== 
FAILED dual_agent/tests/test_phone_agent.py::test_process_complete_speech - AttributeError: Attributes cannot start with 'assert' or 'assret'
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
==================================================== 1 failed, 7 passed, 1 skipped, 1 warning in 11.04s ===================================================== 