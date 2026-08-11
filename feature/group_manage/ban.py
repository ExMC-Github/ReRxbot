# 禁言群成员
import json


def set_group_ban(ws,group_id,user_id,duration):
    """禁言某人"""
    payload = {
    "action": "set_group_ban",
    "params": {
        "group_id": group_id,
        "user_id": user_id,
        "duration": duration
        },
    "echo": "set_group_ban"
    }
    ws.send(json.dumps(payload))
