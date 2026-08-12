# 合并转发消息：单条/多条/长文本自动分段转发
import json

# AI 自主分段标记：AI 在回复中单独一行输出该标记，程序据此将回复切成多条消息发送
AI_SEGMENT_MARKER = '<<<SEP>>>'


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

def split_text_by_ai_marker(text, marker=AI_SEGMENT_MARKER):
    """按AI输出的分段标记切分文本

    优先按分段标记切分；文本中没有标记时原样返回单段。

    Args:
        text: AI回复文本
        marker: 分段标记
    Returns:
        切分后的字符串列表（已去除每段首尾空白）
    """
    if not text:
        return []
    if marker not in text:
        return [text.strip()] if text.strip() else []
    parts = []
    for part in text.split(marker):
        part = part.strip().strip('\n')
        if part:
            parts.append(part)
    return parts


def clean_ai_segment_markers(text, marker=AI_SEGMENT_MARKER):
    """移除AI回复中的分段标记，用于写入对话历史

    Args:
        text: AI回复文本
        marker: 分段标记
    Returns:
        去除标记并压缩多余空行后的文本
    """
    import re
    if not text:
        return ''
    cleaned = text.replace(marker, '')
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def send_group_msg_ai_segmented(ws, group_id, text, uin, name, footer='', max_len=299):
    """按AI自己的分段标记发送消息

    AI在回复中单独一行输出 <<<SEP>>> 标记需要断开的位置，
    程序据此将回复切分成多条消息，以合并转发形式发送（每段一条节点）。
    AI未分段但内容超过 max_len（QQ单条消息上限）时，使用智能断点兜底硬切。
    内容较短无需分段时返回 False，由调用方作为单条普通消息发送。

    Args:
        ws: websocket连接对象
        group_id: 目标群号
        text: AI回复文本
        uin: 转发节点显示的QQ号
        name: 转发节点显示的名字
        footer: 追加在最后一段末尾的文本（如AI生成提示）
        max_len: 每段最大字符数兜底上限
    Returns:
        bool: True 表示已通过合并转发发送，False 表示应作为单条消息发送
    """
    parts = split_text_by_ai_marker(text)
    if len(parts) <= 1:
        single = parts[0] if parts else text
        if not single or len(single) <= max_len:
            return False
        send_group_msg_forward_segmented(ws, group_id, single + footer, uin, name, max_len=max_len)
        return True
    if footer:
        parts[-1] = parts[-1] + footer
    nodes = []
    for part in parts:
        nodes.append({
            "type": "node",
            "data": {
                "uin": uin,
                "name": name,
                "content": [{"type": "text", "data": {"text": part}}]
            }
        })
    send_group_forward_msg(ws, group_id, nodes)
    return True
