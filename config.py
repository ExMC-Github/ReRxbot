from encryption import rotor
import pyconcrete
from rotor_key import key
rot_temp = rotor.newrotor(key)
aikey = rot_temp.decrypt(b'\xd2D\x89}\x7f\xd6r\x9d\xd2\xca\x05P,U\x86E\xdc\x8do\xec\xd2\x0e\x03\xf5\xfc\xad\xd3p\xb7\xc6\xed\xf5\xa5\x9fP').decode('utf-8')
vit_ai_key = rot_temp.decrypt(b'\xd2D\x89}\xec?%C\\1O\xf9\xfdM\xfe#\xbc\xe8\xf1=\xab\x9d\xa1\xbeIV\xd0\xc4\x8b\n>E\xf6\xca\xf1\xd8*(Y\x8b\x80\xea+Z\xd0\xcc\xfbT\x02\xc3.').decode('utf-8')
boto3_secret_key = rot_temp.decrypt(b"\x9a\x9d\x9f'\xfc\x96&\xce\xfa\xd2*{Y\xd9\xb9\xd8\xf4M\xe8;\x9d\xade\xfbOb}N\x83\x08").decode('utf-8')
boto3_access_key = rot_temp.decrypt(b'\xfe\xcf)\x93\x8d\xe1z\x01\xc3\xb9o7\x1bq\x8f\xf0').decode('utf-8')
del rot_temp, key
config = {
    "bot_admin_ids": [3657936745,2545869165,2535246057,2450069268],
    "bot_group": 1081097838,
    "command_prefix": "ex.",
    "i_am_exrfy": True,
    "bot_language": "zh",
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
        "ai_model": "deepseek-v4-flash",
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
del aikey, vit_ai_key, boto3_secret_key, boto3_access_key