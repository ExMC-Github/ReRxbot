# +===================+
# |  O n e B o t 1 1  |
# |      A P I s      |
# +===================+
import json
from loguru import logger

def delete_message(ws,msg):
    payload = {
        "action": "delete_msg",
        "params": {
            "message_id": msg.get('message_id')
        },
        "echo": "delete_message"
    }
    ws.send(json.dumps(payload))

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

def send_group_msg(ws, group_id, message_text, auto_escape=True):
    payload = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": message_text,
            "auto_escape": auto_escape  # True 表示把内容当纯文本，不解析CQ码
        },
        "echo": "send_group_msg"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
    logger.info(f"已发送消息到群 {group_id}: {repr(message_text)}")

def send_group_msg_nolog_for_screenshot(ws, group_id, message_text, auto_escape=True):
    payload = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": message_text,
            "auto_escape": auto_escape  # True 表示把内容当纯文本，不解析CQ码
        },
        "echo": f"send_group_msg_nolog_for_screenshot&{group_id}"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
    logger.info(f"已发送消息到群 {group_id}: 这是PEEKServer的截图")

def set_group_special_title(ws,group_id,user_id,special_title,duration=-1):
    """给予群头衔"""
    payload = {
        "action": "set_group_special_title",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "special_title": special_title,
            "duration": duration
        },
        "echo": "set_group_special_title"  # 可选，用于在响应中识别这次请求
    }
    ws.send(json.dumps(payload))
    if (special_title != ""):
        logger.info(f"已设置群({group_id})成员({user_id})有效期{duration}秒的头衔: {special_title}")
    else:
        logger.info(f"已撤销群({group_id})成员({user_id})的头衔")

def compress_logs(os,datetime,tarfile,sys):
    """压缩日志文件"""
    try:
        # 获取当前时间作为文件名
        now = datetime.datetime.now()
        filename = now.strftime("%Y%m%d-%H%M%S") + ".txt.zst"
        filepath = os.path.join('logs', filename)
        
        # 检查app.log是否存在
        if not os.path.exists('app.log'):
            logger.warning("app.log不存在，无需压缩")
            return
        
        # 创建tar.gz压缩文件
        with open(f"logs/{filename}","wb") as f:
            if sys.version_info >= (3,14):
                import compression.zstd as zstd
            else:
                if hasattr(sys,"built_target"):
                    import zstd
                else:
                    import zstandard as zstd
            with open("app.log",'rb') as g:
                f.write(zstd.compress(g.read()))
        
        # 删除原日志文件
        os.remove('app.log')
        
        logger.info(f"日志已压缩保存到: {filepath}")
        logger.info("新日志文件已创建")
        
    except Exception as e:
        logger.error(f"压缩日志时出错: {e}")

def right(text, length):
    """
    自定义right函数，类似于其他语言的right函数
    """
    if length <= 0:
        return ""
    if length >= len(text):
        return text
    return text[-length:]

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

def exec_and_capture(code: str,sys,io,traceback,ws) -> str:
    """执行代码并捕获标准输出及异常，返回输出的字符串"""
    # 创建字符串缓冲区来替代标准输出
    stdout_capture = io.StringIO()
    # 保存原始的标准输出
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    # 准备一个命名空间，可以预先放入一些安全模块或限制
    namespace = {'ws': ws}

    try:
        # 使用 compile 编译代码，指定模式为 'exec'
        compiled = compile(code, '<script>', 'exec')
        # 执行编译后的代码，传入命名空间
        exec(compiled, namespace)
    except Exception:
        # 捕获执行过程中的异常，并将异常信息写入输出
        sys.stdout = old_stdout  # 先恢复，避免 traceback 打印到我们的缓冲区外
        return traceback.format_exc()
    finally:
        # 恢复标准输出
        sys.stdout = old_stdout

    # 获取缓冲区的内容
    output = stdout_capture.getvalue()
    stdout_capture.close()
    return output

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

def send_private_msg(ws,user_id,message):
    payload = {
    "action": "send_private_msg",
    "params": {
        "user_id": user_id,
        "message": [
            {
                "type": "text",
                "data": {
                    "text": message
                }
            }
        ]
        },
    "echo": "send_private_msg"
    }
    ws.send(json.dumps(payload))

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