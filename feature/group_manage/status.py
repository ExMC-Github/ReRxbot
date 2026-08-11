# 群状态与框架版本信息查询
import json


def get_status(ws,group_id):
    payload = {
        "action": "get_status",
        "echo": f"get_status&{group_id}"
    }
    ws.send(json.dumps(payload))

def get_version_info(ws,group_id):
    payload = {
        "action": "get_version_info",
        "echo": f"get_version_info&{group_id}"
    }
    ws.send(json.dumps(payload))

def get_llbot_info(ws,group_id):
    """查询框架版本信息（#ll / #llbot 命令专用回声）"""
    payload = {
        "action": "get_version_info",
        "echo": f"llbot_info&{group_id}"
    }
    ws.send(json.dumps(payload))
