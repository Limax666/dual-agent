E:\AI Agent\ai-agent-projects-main\dual_agent\examples\run_dual_agent.py:216: DeprecationWarning: There is no current event loop
  loop = asyncio.get_event_loop()
🎯 改进后的双Agent系统
📝 基于题目要求的改进:
   • 集成现成开源工具 (browser-use)
   • 工具调用通信机制
   • LLM驱动的表单处理
   • 通用性和泛化性设计

🚀 初始化改进后的双Agent系统...
📋 系统特点:
   ✅ 基于工具调用的Agent间通信
   ✅ LLM驱动的智能表单填写
   ✅ 集成现成浏览器自动化框架
   ✅ 完全移除硬编码字符串匹配

📞 初始化Phone Agent...
Using cache found in C:\Users\59216/.cache\torch\hub\snakers4_silero-vad_master
Silero VAD initialized
✅ 注册Agent处理器: phone_agent
💻 初始化智能Computer Agent...
✅ 注册Agent处理器: computer_agent
✅ 改进的双Agent系统初始化完成
🔄 启动改进的双Agent系统...
💻 启动智能Computer Agent...
🎤 启动Phone Agent...
📥 phone_agent <- computer_agent: system_status
📤 computer_agent -> phone_agent: system_status
🎤 Phone Agent正在启动...
👋 Phone Agent开始问候...
📊 Computer Agent状态: Computer Agent已就绪，可以开始浏览器操作
🤖 AI说: 您好！我是您的AI助手。我正在等待Computer Agent分析当前页面，请稍等片刻，然后告诉我您想要做什么。
INFO     [browser_use.telemetry.service] Anonymized telemetry enabled. See https://docs.browser-use.com/development/telemetry for more information.
INFO     [browser_use.agent.service] 💾 File system path: C:\Users\59216\AppData\Local\Temp\browser_use_agent_0688cf7d-cf9c-7d6b-8000-f681ca68209a
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 92] 🧠 Starting a browser-use agent 0.5.7 with base   _model=gpt-4o-mini +vision extraction_model=gpt-4o-mini +file_system🌐 正在导航到: https://httpbin.org/forms/post
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 92] 🚀 Starting task: Navigate to https://httpbin.o   rg/forms/post, then extract structured data about all form fields on the page including their names, types, labels, and other attributes.
🌐 Computer Agent将自动处理目标URL...

======================================================================
🎉 改进后的双Agent系统已启动！

🔄 系统改进点:
   ✅ 基于工具调用的Agent间通信 (替代硬编码消息队列)
   ✅ LLM驱动的智能表单填写 (替代字符串匹配)
   ✅ 集成browser-use框架 (替代自研Playwright封装)
   ✅ 通用化设计支持各种网页操作

📞 Phone Agent: 等待您的语音输入...
💻 Computer Agent: LLM驱动的智能浏览器操作
🌐 目标页面: https://httpbin.org/forms/post

💡 使用示例:
   🗣️  '我叫张三，邮箱是zhang@example.com'
   🗣️  '请帮我打开百度网站'
   🗣️  '填写表单，我的电话是138****8888'
   🗣️  '点击提交按钮'

🧠 智能特性:
   • LLM自动理解用户意图
   • 智能提取表单信息
   • 自适应网页结构
   • 自然语言交互

⌨️  按 Ctrl+C 退出系统
======================================================================

INFO     [browser_use.BrowserSession🆂 209a:None #96] 🎭 Launching new local browser playwright:chro mium keep_alive=False user_data_dir= ~\.config\browseruse\profiles\default
INFO     [browser_use.utils] ✅ Extensions ready: 3 extensions loaded (uBlock Origin, I still don't care about cookies, ClearURLs)
INFO     [browser_use.BrowserSession🆂 209a:None #96]  ↳ Spawning Chrome subprocess listening on CDP  http://127.0.0.1:58813/ with user_data_dir= ~\.config\browseruse\profiles\default
INFO     [browser_use.BrowserSession🆂 209a:58813 #96] 🌎 Connecting to newly spawned browser via CD P http://127.0.0.1:58813/ -> browser_pid=7636 (local)
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 📍 Step 2: Evaluating page with 0 interactive e   lements on: about:blank
🔊 Phone Agent开始监听语音输入...
🎤 使用麦克风: 麦克风 (Realtek(R) Audio)
✅ 麦克风已就绪，VAD阈值: 0.5
🎤 请开始说话，系统正在监听...
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 💡 Thinking:
The user has requested to navigate to the specified URL and extract structured data about all form fields present on the page. Currently, I am on an empty page, so I need to navigate to 'https://httpbin.org/forms/post'. After that, I will extract the structured data regarding the form fields.
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] ❔ Eval: No actions have been taken yet as I nee   d to navigate to the specified URL first. Verdict: Pending.
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 🧠 Memory: The task is to navigate to 'https://   httpbin.org/forms/post' and extract information about form fields. No previous actions have been recorded.
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 🎯 Next goal: Navigate to 'https://httpbin.org/   forms/post' and then extract structured data about all form fields on the page.

INFO     [cost] 🧠 gpt-4o-mini | 📥 4.9k | 📤 200
🎵 音量:                      (0.002)
INFO     [browser_use.controller.service] 🔗 Navigated to https://httpbin.org/forms/post
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] ☑️ Executed action 1/1: go_to_url()
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 📍 Step 2: Ran 1 actions in 21.01s: ✅ 1
🎵 音量:                      (0.002)
INFO     [browser_use.BrowserSession🆂 209a:58813 #96] ➡️ Page navigation [0]httpbin.org/forms/post  took 2.00s
🎵 音量:                      (0.002)
🎵 音量:                      (0.001)
🎵 音量:                      (0.002)
INFO     [browser_use.sync.auth] ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
INFO     [browser_use.sync.auth] 🌐  View the details of this run in Browser Use Cloud:
INFO     [browser_use.sync.auth]     👉  https://cloud.browser-use.com/hotlink?user_code=JQUBPFBCU95JXXWX
INFO     [browser_use.sync.auth] ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────       

🎵 音量:                      (0.005)
🎵 音量:                      (0.003)
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 📍 Step 3: Evaluating page with 27 interactive    elements on: https://httpbin.org/forms/post
🎵 音量:                      (0.001)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
🎵 音量:                      (0.004)
🎵 音量:                      (0.003)
🎵 音量:                      (0.002)
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 💡 Thinking:
I have successfully navigated to the specified URL, which contains a form with various input fields. The next step is to extract structured data about these form fields, including their names, types, labels, and other attributes. The interactive elements indicate that there are text inputs, radio buttons, checkboxes, a textarea, and a submit button.
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 👍 Eval: Successfully navigated to the page con   taining the form. Verdict: Success.
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 🧠 Memory: Visited the page at https://httpbin.   org/forms/post. The form includes fields for customer name, telephone, email, pizza size (radio buttons), pizza toppings (checkboxes), preferred delivery time, delivery instructions, and a submit button.
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 🎯 Next goal: Extract structured data about all    form fields on the page, including their names, types, labels, and 
other attributes.

INFO     [cost] 🧠 gpt-4o-mini | 🆕 40.4k + 💾 1.8k | 📤 225
🎵 音量:                      (0.003)
🎵 音量:                      (0.001)
🎵 音量:                      (0.002)
🎵 音量:                      (0.003)
INFO     [browser_use.controller.service] 📄 Page Link: https://httpbin.org/forms/post
Query: Extract all form fields including names, types, labels, and attributes.
Extracted Content:
```json
{
  "content": "The webpage contains a form for placing a pizza order. It includes fields for customer information, pizza size selection, pizza toppings selection, preferred delivery time, and delivery instructions. However, the specific details about form fields such as names, types, labels, and attributes are not explicitly provided in the text.",
  "requested_information": "not_available"
}
```
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] ☑️ Executed action 1/1: extract_structured_data   ()
INFO     [browser_use.Agent🅰 209a on 🆂 209a 🅟 88] 📍 Step 3: Ran 1 actions in 39.68s: ✅ 1
INFO     [cost] 🧠 gpt-4o-mini | 📥 202 | 📤 80
INFO     [cost] 📊 Per-Model Usage Breakdown:
INFO     [cost]   🤖 gpt-4o-mini: 47.8k tokens | ⬅️ 47.3k | ➡️ 505 | 📞 3 calls | 📈 15.9k/call
🎵 音量:                      (0.003)
INFO     [browser_use.agent.service] Cloud authentication started - continuing in background
🎵 音量:                      (0.002)
🎵 音量:                      (0.003)
🎵 音量:                      (0.002)
🎵 音量:                      (0.003)
🎵 音量:                      (0.002)
🎵 音量:                      (0.002)
INFO     [browser_use.BrowserSession🆂 209a:58813 #96] 🛑 Closing cdp_url=http://127.0.0.1:58813/ br owser context  <Browser type=<BrowserType name=chromium executable_path=C:\Users\59216\AppData\Local\ms-playwright\chromium-1181\chrome-win\chrome.exe> version=139.0.7258.5>
🎵 音量:                      (0.002)
INFO     [browser_use.BrowserSession🆂 209a:58813 #96]  ↳ Killing browser_pid=7636 ~\AppData\Local\m s-playwright\chromium-1181\chrome-win\chrome.exe (terminate() called)
📥 phone_agent <- computer_agent: page_analysis
📤 computer_agent -> phone_agent: page_analysis
🎵 音量:                      (0.003)
🌐 页面分析消息: 已打开页面 https://httpbin.org/forms/post，系统已准备就绪。请告诉我您要填写什么信息。
🎵 音量:                      (0.004)