from encryption import rotor
import pyconcrete
from rotor_key import key
rot_temp = rotor.newrotor(key)
aikey = rot_temp.decrypt(b'\xd2D\x89\x13\x0f\x80z\x04\x08\xb7\x9aN\x10\xe4\x86E\xbc\x8b1\x05\x01\xe0\x15\xa3#\xc2e\xe9sa\x14z\xa239').decode('utf-8')
vit_ai_key = rot_temp.decrypt(b'\xd2D\x89\x8c\x96\xd1\xda\x9d9\x0c\xdb\x8b|7s?\xaaR\xcc\xe5!\x9dADX\xad\xb0\x16s*\xa3\xffI(=V\x84\x7f{\x0er\xdc:\xea\x88\x19]\xc6\xa4\x97=').decode('utf-8')
boto3_secret_key = rot_temp.decrypt(b"\xe2\xc8 \xc2Y/>\x9f'\xe2C\xb2\x8c\x9a\xe0C\xa3!q\xa1\x0b\x0e\xebnW\xbd\x8c+>\x7f").decode('utf-8')
boto3_access_key = rot_temp.decrypt(b'\x1203&y\x1b\xe82F$bu\xec\x16P\xd4').decode('utf-8')
del rot_temp, key
config = {
    "bot_admin_ids": [3657936745,2545869165,2535246057,1610915093,2975227763,2450069268],
    "bot_group": 1081097838,
    "command_prefix": "ex.",
    "pokeme_msg": "不要戳了喵(#`Д´)ﾉ 要被戳扁了喵=*-*=",
    "bot_disable_settings":{
        "group_settings":{
            "771866544": {
                "is_only_admin_can_use": True,
                "ai_enabled": False
            }
        }
    },
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
            "access_key": boto3_access_key,
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