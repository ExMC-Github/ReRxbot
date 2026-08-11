# 消息管理：撤回/标记已读/回应/获取/提取文本
import json


def delete_message(ws,msg):
    payload = {
        "action": "delete_msg",
        "params": {
            "message_id": msg.get('message_id')
        },
        "echo": "delete_message"
    }
    ws.send(json.dumps(payload))

def set_emoji_like(ws,message_id,emoji_id):
    """回应消息"""
    payload = {
    "action": "set_msg_emoji_like",
    "params": {
        "message_id": message_id,
        "emoji_id": emoji_id
        },
    "echo": "set_msg_emoji_like"
    }
    ws.send(json.dumps(payload))

def get_message_text(msg):
    """请输入文本"""
    message_segments = msg.get('message', [])
    text_parts = []
    for segment in message_segments:
        if segment.get('type') == 'text':
            text_parts.append(segment['data']['text'])
        # 如果有其他类型（如图片、@等），可根据需要处理
    return ''.join(text_parts)

def mark_msg_as_read(ws,message_id):
    """标记消息已读"""
    payload = {
    "action": "mark_msg_as_read",
    "params": {
        "message_id": message_id,
        },
    "echo": "mark_msg_as_read"
    }
    ws.send(json.dumps(payload))

def get_msg(ws,message_id):
    """使用消息ID获取消息"""
    payload = {
    "action": "get_msg",
    "params": {
        "message_id": message_id,
        },
    "echo": "get_msg"
    }
    ws.send(json.dumps(payload))
