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

def paginate_text(text, newline_threshold=5, char_threshold=500):
    """按 multi_textbox 配置将文本分页（用于合并转发的节点切分）

    触发条件：换行数 >= newline_threshold 或 字符数 >= char_threshold。
    分页规则：优先按换行切分，每页最多包含 newline_threshold 个换行，
    且每页字符数不超过 char_threshold；单段超长或无换行时按字符硬切。
    不满足触发条件时返回 [text]（单页）。

    Args:
        text: 待分页文本
        newline_threshold: 分页的换行数阈值（每页最多包含的换行数）
        char_threshold: 分页的字符数阈值（每页最大字符数，AI不换行时的兜底）
    Returns:
        分页后的字符串列表
    """
    if not text:
        return []
    char_threshold = max(char_threshold, 1)
    if text.count('\n') < newline_threshold and len(text) < char_threshold:
        return [text]

    pages = []
    cur = ''
    cur_newlines = 0
    lines = text.split('\n')
    for i, line in enumerate(lines):
        seg = line if i == len(lines) - 1 else line + '\n'
        # 单段超长：先封当前页，再按字符硬切成多页
        if len(seg) > char_threshold:
            if cur:
                pages.append(cur)
                cur = ''
                cur_newlines = 0
            for j in range(0, len(seg), char_threshold):
                pages.append(seg[j:j + char_threshold])
            continue
        # 当前页已满：换页
        if cur_newlines >= newline_threshold or len(cur) + len(seg) > char_threshold:
            if cur:
                pages.append(cur)
            cur = ''
            cur_newlines = 0
        cur += seg
        cur_newlines += 1
    if cur:
        pages.append(cur)
    return pages

def send_group_msg_forward_paginated(ws, group_id, text, uin, name, newline_threshold=5, char_threshold=500):
    """按 multi_textbox 配置分页后以合并转发发送

    将文本按换行数/字符数分页，每页作为一条合并转发节点。
    文本无需分页时退化为单条合并转发。

    Args:
        ws: websocket连接对象
        group_id: 目标群号
        text: 待发送的长文本
        uin: 转发节点显示的QQ号
        name: 转发节点显示的名字
        newline_threshold: 分页的换行数阈值
        char_threshold: 分页的字符数阈值
    """
    pages = paginate_text(text, newline_threshold=newline_threshold, char_threshold=char_threshold)
    if len(pages) <= 1:
        send_group_single_forward_msg(ws, group_id, uin, name, text)
        return
    nodes = []
    for page in pages:
        nodes.append({
            "type": "node",
            "data": {
                "uin": uin,
                "name": name,
                "content": [{"type": "text", "data": {"text": page}}]
            }
        })
    send_group_forward_msg(ws, group_id, nodes)
