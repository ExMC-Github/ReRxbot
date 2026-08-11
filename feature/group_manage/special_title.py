# 给予/撤销群成员头衔
import json
from loguru import logger


def set_group_special_title(ws,group_id,user_id,special_title,duration=-1):
    """给予群头衔"""
    payload = {
        "action": "set_group_special_title",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "special_title": special_title,
            "duration": duration
        },
        "echo": "set_group_special_title"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
    if (special_title != ""):
        logger.info(f"已设置群({group_id})成员({user_id})有效期{duration}秒的头衔: {special_title}")
    else:
        logger.info(f"已撤销群({group_id})成员({user_id})的头衔")
