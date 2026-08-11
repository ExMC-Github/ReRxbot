# 为群成员点赞
import json


def like_someone(ws,user_id,times,group_id):
    """为某人点赞"""
    payload = {
        "action": "send_like",
        "params": {
            "user_id": user_id,
            "times": times,
        },
        "echo": f"send_like&{group_id}&{user_id}"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
