# 戳一戳群成员
import json


def unique_identifier(ws,group_id,user_id):
    """戳戳（群）某人"""
    payload = {
    "action": "group_poke",
    "params": {
        "group_id": group_id,
        "user_id": user_id,
        },
    "echo": "unique_identifier"
    }
    ws.send(json.dumps(payload))
