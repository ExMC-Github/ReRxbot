# 群打卡
import json


def send_group_sign(ws,group_id):
    """发送打卡请求"""
    payload = {
        "action": "send_group_sign",
        "params": {
            "group_id": group_id
        },
        "echo": f"send_group_sign"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
