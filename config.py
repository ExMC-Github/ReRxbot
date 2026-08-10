from encryption import rotor
import pyconcrete
from rotor_key import key
rot_temp = rotor.newrotor(key)
aikey = rot_temp.decrypt(b'\xd2D\x89}!r\x0f\x9d\xc8\xac\x9a\xdf,QNEs\xb8\\\xec\xf0\xe0\xa5r\xe1\xf2\xd0\xa4\xb7$\x14zE\xccP').decode('utf-8')
vit_ai_key = rot_temp.decrypt(b"\xd2D\x89\xa5\x7f\x17\xcc\xe4b\x91\xba\x93\xc6\xc3\x86\xd8\x80!\x0b\xdd\r\xce\x1d{c\xac*'\xe6\x1e\x14\xf5\xe3N=\xb6\xf7\xed\x89\xd8\r?\xb7\xe5\xb4\x9a] \xd6%\xd1").decode('utf-8')
boto3_secret_key = rot_temp.decrypt(b'PI B\x87\x80\xda\xc8\xa4\x87\xf85s\x9eau#\x16\x8ct\xcb/A\xceI\x9fo\xf0S\xb5').decode('utf-8')
del rot_temp, key
config = {
    "bot_admin_ids": [3657936745,2545869165,2535246057,1610915093,2975227763],
    "bot_group": 1081097838,
    "command_prefix": "ex.",
    "ai_settings": {
        "ai_base_url": "https://api.deepseek.com",
        "ai_key": aikey,
        "ai_name": "DeepSeek",
        "ai_shortname": "dpsk",
        "ai_model": "deepseek-v4-pro",
        "ai_timeout_retry": 2,
        "at_ai_enable": True,
        "ai_owner_group_future_mode": True,
        "ai_memory_dir": "ai_memory",
        "ai_memory_boto3_backup": True,
        "ai_memory_boto3_config": {
            "api": "https://cn-sy1.rains3.com",
            "access_key": "e8WlL0NMElbA5rN9",
            "secret_key": boto3_secret_key,
            "bucket_name": "rerxbot-memory"
        },
        "rules_defined": {
            "normal": "modern.txt",
            "defined": "defined.txt",
            "at": "modern.txt"
        },
        "vit_enable": True,
        "vit_base_url": "https://yunwu.ai/v1",
        "vit_api_key": vit_ai_key,
        "vit_model": "gemini-3-flash-preview",
        "vit_prompt": "用中文尽可能详细地描述这张图片",
        "vit_http_proxy": "http://127.0.0.1:7890",
        "vit_https_proxy": "http://127.0.0.1:7890",
        "ai_python_exec": "ai-embed-python/python.exe",
        "ai_tools_http_proxy": "http://127.0.0.1:7890",
        "ai_tools_https_proxy": "http://127.0.0.1:7890",
        "blacklist_files": ["rotor_key.py", "rotor_key.pye"]
    }
}
del aikey, vit_ai_key, boto3_secret_key