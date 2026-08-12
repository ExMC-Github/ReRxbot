# 消息管理：撤回/标记已读/回应/获取/提取文本
import json
import threading

# 同步请求-响应注册表: echo -> {"event": threading.Event, "data": dict}
_pending_sync_requests = {}
_pending_sync_lock = threading.Lock()
_pending_sync_counter = [0]


def get_msg_sync(ws, message_id, timeout=3.0):
    """通过 WebSocket 同步获取消息内容（内部使用 get_msg 动作 + echo 匹配）

    Args:
        ws: WebSocket 连接
        message_id: 要获取的消息ID（支持负数）
        timeout: 等待响应的超时时间（秒）

    Returns:
        成功返回 OneBot 响应的 data 字典（含 sender / message 等字段），失败或超时返回 None
    """
    with _pending_sync_lock:
        _pending_sync_counter[0] += 1
        echo = f"get_msg_sync&{_pending_sync_counter[0]}"
        entry = {"event": threading.Event(), "data": None}
        _pending_sync_requests[echo] = entry

    payload = {
        "action": "get_msg",
        "params": {"message_id": message_id},
        "echo": echo
    }
    try:
        ws.send(json.dumps(payload))
    except Exception:
        with _pending_sync_lock:
            _pending_sync_requests.pop(echo, None)
        return None

    if not entry["event"].wait(timeout):
        with _pending_sync_lock:
            _pending_sync_requests.pop(echo, None)
        return None

    with _pending_sync_lock:
        _pending_sync_requests.pop(echo, None)
    return entry["data"]


def resolve_sync_response(echo, data):
    """在 on_message 回调中调用，匹配并唤醒等待同步响应的线程

    Args:
        echo: 响应中的 echo 字段
        data: 响应中的 data 字段

    Returns:
        是否成功匹配（True 时上层应直接 return，不再当作普通消息处理）
    """
    if not (isinstance(echo, str) and echo.startswith("get_msg_sync&")):
        return False
    with _pending_sync_lock:
        entry = _pending_sync_requests.get(echo)
        if entry is not None:
            entry["data"] = data
            entry["event"].set()
    return True


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
