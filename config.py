config = {
    "bot_admin_ids": [3657936745,2545869165,2535246057,1610915093,2975227763],
    "bot_group": 1081097838,
    "ai_base_url": "https://api.deepseek.com",
    "ai_key": "sk-f7ee59e46e1f4e54b86e28a485d2c41e",
    "ai_name": "DeepSeek",
    "ai_shortname": "dpsk",
    "ai_model": "deepseek-chat",
    "command_prefix": "ex.",
    "at_ai_enable": True,
    "ai_owner_group_future_mode": True,
    "ai_memory_dir": "ai_memory",
    "rules_defined": {
        "normal": "default.txt",
        "defined": "defined.txt",
        "at": "default.txt"
    },
    # 视觉(VIT)配置 - 让AI能看图片
    "vit_enable": True,
    "vit_base_url": "https://yunwu.ai/v1",
    "vit_api_key": "sk-R2ObQ5uXm4m4mGUpz70YWfzEIPX2bEBFVDmPnlMvbFDVoPvj",
    "vit_model": "gemini-3-flash-preview",
    "vit_prompt": "用中文尽可能详细地描述这张图片",
    "vit_http_proxy": "http://192.168.11.117:7890",
    "vit_https_proxy": "http://192.168.11.117:7890",
    # AI代码执行Python解释器路径（留空则使用系统默认Python）
    "ai_python_exec": "ai-embed-python/python.exe"
}