# 发送群/私聊消息
import json
from loguru import logger


def send_group_msg(ws, group_id, message_text, auto_escape=True):
    payload = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": message_text,
            "auto_escape": auto_escape  # True 表示把内容当纯文本，不解析CQ码
        },
        "echo": "send_group_msg"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
    logger.info(f"已发送消息到群 {group_id}: {repr(message_text)}")

def send_group_msg_nolog_for_screenshot(ws, group_id, message_text, auto_escape=True):
    payload = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": message_text,
            "auto_escape": auto_escape  # True 表示把内容当纯文本，不解析CQ码
        },
        "echo": f"send_group_msg_nolog_for_screenshot&{group_id}"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
    logger.info(f"已发送消息到群 {group_id}: 这是PEEKServer的截图")

def send_private_msg(ws,user_id,message):
    payload = {
    "action": "send_private_msg",
    "params": {
        "user_id": user_id,
        "message": [
            {
                "type": "text",
                "data": {
                    "text": message
                }
            }
        ]
        },
    "echo": "send_private_msg"
    }
    ws.send(json.dumps(payload))
