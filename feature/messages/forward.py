# 合并转发消息：单条/多条/长文本自动分段转发
import json


def send_group_single_forward_msg(ws,group_id,uin,name,text):
    """发送群合并转发消息（单条）"""
    payload = {
    "action": "send_group_forward_msg",
    "params": 
                {
                    "group_id": group_id,
                    "messages": [
                    {
                        "type": "node",
                        "data": {
                            "uin": uin,
                            "name": name,
                            "content": [
                                {
                                    "type": "text",
                                    "data": {
                                        "text": text
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
    "echo": "send_group_single_forward_msg"
    }
    ws.send(json.dumps(payload))

def split_text_into_chunks(text, max_len=299):
    """将长文本智能分段，每段不超过 max_len 字符

    断点优先级：段落空行 > 换行 > 句末标点(。！？；) > 逗号/空格 > 字符硬切
    Args:
        text: 待分段文本
        max_len: 每段最大字符数（默认299，QQ单条消息上限）
    Returns:
        分段后的字符串列表
    """
    import re
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    # 按优先级寻找窗口内的最优断点（断点需落在窗口后半部分，避免切出碎片段）
    def find_break(window):
        # 1. 段落空行
        pos = window.rfind('\n\n')
        if pos >= max_len // 2:
            return pos
        # 2. 换行
        pos = window.rfind('\n')
        if pos >= max_len // 2:
            return pos
        # 3. 句末标点
        for sep in ('。', '！', '？', '；'):
            pos = window.rfind(sep)
            if pos >= max_len // 2:
                return pos + 1
        # 4. 逗号/空格等弱断点
        for sep in ('，', '、', ',', ' ', ';'):
            pos = window.rfind(sep)
            if pos >= max_len // 2:
                return pos + 1
        # 5. 硬切
        return max_len

    chunks = []
    remaining = text
    while len(remaining) > max_len:
        window = remaining[:max_len]
        pos = find_break(window)
        chunk = window[:pos].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[pos:].lstrip('\n')
    tail = remaining.strip()
    if tail:
        chunks.append(tail)
    return chunks

def send_group_forward_msg(ws, group_id, nodes):
    """发送群合并转发消息（支持多条消息节点，每条节点一条消息）

    Args:
        ws: websocket连接对象
        group_id: 目标群号
        nodes: 消息节点列表，每个节点结构为：
            {
                "type": "node",
                "data": {
                    "uin": 发送者QQ号,
                    "name": 发送者昵称,
                    "content": [{"type": "text", "data": {"text": "文本内容"}}]
                }
            }
    """
    payload = {
        "action": "send_group_forward_msg",
        "params": {
            "group_id": group_id,
            "messages": nodes
        },
        "echo": "send_group_forward_msg"
    }
    ws.send(json.dumps(payload))

def send_group_msg_forward_segmented(ws, group_id, text, uin, name, max_len=299):
    """自动分段后以合并转发发送长消息（参考 about 命令的分段方式）

    将超过 max_len 的长文本按段落/换行/句子智能分段，
    每段作为一条合并转发节点发送，避免单条消息过长。
    文本无需分段时退化为单条合并转发。

    Args:
        ws: websocket连接对象
        group_id: 目标群号
        text: 待发送的长文本
        uin: 转发节点显示的QQ号
        name: 转发节点显示的名字
        max_len: 每段最大字符数
    """
    chunks = split_text_into_chunks(text, max_len=max_len)
    if len(chunks) <= 1:
        send_group_single_forward_msg(ws, group_id, uin, name, text)
        return
    nodes = []
    for chunk in chunks:
        nodes.append({
            "type": "node",
            "data": {
                "uin": uin,
                "name": name,
                "content": [{"type": "text", "data": {"text": chunk}}]
            }
        })
    send_group_forward_msg(ws, group_id, nodes)
