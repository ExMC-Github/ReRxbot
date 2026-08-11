# 获取群列表
import json


def send_get_group_list(ws):
    """获取群列表"""
    # 构造请求 payload，加入 echo 用于识别响应
    payload = {
        "action": "get_group_list",
        "params": {},
        "echo": "get_group_list"  # 自定义标识，可根据需要修改
    }

    # 发送请求
    ws.send(json.dumps(payload))

def get_group_list_and_sign_all_group(ws):
    """获取群列表然后给所有群打卡"""
    # 构造请求 payload，加入 echo 用于识别响应
    payload = {
        "action": "get_group_list",
        "params": {},
        "echo": "get_group_list_and_sign_all_group"  # 自定义标识，可根据需要修改
    }

    # 发送请求
    ws.send(json.dumps(payload))
