# 这是ExRFy写给自己用的功能，反正默认是开着的，需要手动改config.py把“i_am_exrfy”关了才会不生效

import json, builtins, random, html, threading
from loguru import logger
from . import etypes
from .languages_choicer import L
from feature.group_manage.poke import unique_identifier
from feature.messages.send import send_group_msg
from feature.group_manage.special_title import set_group_special_title
from feature.group_manage.ban import set_group_ban
from feature.messages.manage import set_emoji_like, get_stranger_info_sync, get_group_member_info_sync
from feature.messages.forward import send_group_forward_msg

def ex_qq_group_message(ws,message):
    msg = json.loads(message)
    post_type = msg.get('post_type')          # 消息类型：message
    message_type = msg.get('message_type')    # 群消息：group
    group_id = msg.get('group_id')            # 群号
    group_name = msg.get('group_name')        # 群名称
    user_id = msg.get('sender', {}).get('user_id')  # 发送者QQ
    self_id = msg.get('self_id')
    sub_type = msg.get('sub_type')
    nickname = msg.get('sender', {}).get('nickname')  # 昵称
    msgtime = msg.get('time')
    message_id = msg.get('message_id')
    # raw_message 可能被框架进行 HTML 转义（如 &#91; -> [），统一还原后再使用
    raw_message = html.unescape(msg.get('raw_message') or '')
    message_segments = msg.get("message", [])

    if raw_message == "test":
        send_group_msg(ws,group_id,L["status_normal"])
        return etypes.EX_BREAK_MESSAGE
    
    # ex.fake_msg：伪造聊天记录，以合并转发形式发送（换行即消息分段标记）
    # 必须在后台线程处理：_get_nickname 的同步 API 调用会阻塞等待 WS 响应，
    # 若在主线程（on_message 回调）里同步等待，响应永远无法进入回调，必然 3 秒超时
    if raw_message.startswith(f"{builtins.config['command_prefix']}fake_msg"):
        threading.Thread(
            target=_handle_fake_msg,
            args=(ws, group_id, raw_message),
            daemon=True
        ).start()
        return etypes.EX_BREAK_MESSAGE
    
    if raw_message.startswith("戳戳我"):
        unique_identifier(ws,group_id,user_id)
        return etypes.EX_BREAK_MESSAGE

    if "/kel" in raw_message or "[CQ:face,id=111,sub_type=1]" in raw_message:
        set_emoji_like(ws,message_id,111)
        return etypes.EX_DO_NOTHING
    
    if group_id == builtins.config["bot_group"]:
        if raw_message.startswith("我要头衔 ") or raw_message.startswith("头衔测试 "):
            raw_title = raw_message[5:]
            if len(raw_title) > 16:
                prefix = raw_title[:16]
                suffix = raw_title[16:]
                num_groups = (len(suffix) + 1) // 2
                title = prefix + L["title_padding"] * num_groups
            else:
                title = raw_title
            if "群主" in raw_message[4:].replace(" ", ""):
                set_group_special_title(ws, group_id, user_id, title)
            else:
                if user_id == 2051621535 or user_id == 3955986019:
                    set_group_ban(ws, group_id, user_id, random.randint(180, 300))
                    return etypes.EX_BREAK_MESSAGE
                else:
                    set_group_special_title(ws, group_id, user_id, title)
                    return etypes.EX_BREAK_MESSAGE

        if user_id in builtins.config["bot_admin_ids"] or user_id in [1610915093]:
            if raw_message in ["召唤鱼","召唤fish","召唤西湖醋鱼"]:
                send_group_msg(ws,group_id,"[CQ:at,qq=2975227763] " + L["summon_fish_reply"],False)
                return etypes.EX_BREAK_MESSAGE
        
        if raw_message.startswith("那我呢") and user_id == 2051621535 or user_id == 3955986019 and raw_message.startswith("那我呢"):
            set_group_ban(ws,group_id,user_id,random.randint(180,300))
            return etypes.EX_BREAK_MESSAGE

        if user_id != self_id:
            try:
                a = int(raw_message)
                if not raw_message.startswith("-"):
                    send_group_msg(ws,group_id,str(a+1))
                else:
                    send_group_msg(ws,group_id,str(a-1))
            except:
                pass

    return etypes.EX_DO_NOTHING


def _get_nickname(ws, user_id, group_id=None):
    """获取用户昵称，失败时回退为QQ号

    优先调用 get_stranger_info（取 nickname / card / name）；
    拿不到时若提供了群号，再调用 get_group_member_info 取群名片或群内昵称；
    仍然失败则回退为 str(user_id)。

    Args:
        ws: WebSocket 连接
        user_id: 用户QQ号
        group_id: 群号（提供时作为第二级兜底来源）

    Returns:
        昵称字符串
    """
    try:
        data = get_stranger_info_sync(ws, user_id, timeout=3.0)
        if data:
            nickname = data.get("nickname") or data.get("card") or data.get("name")
            if nickname:
                return nickname
            logger.warning(f"get_stranger_info 返回 {user_id} 数据无昵称字段: {data!r}")
    except Exception as e:
        logger.warning(f"get_stranger_info 获取用户 {user_id} 昵称失败: {e}")

    if group_id is not None:
        try:
            data = get_group_member_info_sync(ws, group_id, user_id, timeout=3.0)
            if data:
                nickname = data.get("card") or data.get("nickname") or data.get("name")
                if nickname:
                    return nickname
                logger.warning(f"get_group_member_info 返回 {user_id} 数据无昵称字段: {data!r}")
        except Exception as e:
            logger.warning(f"get_group_member_info 获取用户 {user_id} 昵称失败: {e}")

    logger.warning(f"获取用户 {user_id} 昵称失败（stranger与群成员接口均无可用昵称），回退为QQ号")
    return str(user_id)


def _handle_fake_msg(ws, group_id, raw_message):
    """处理 ex.fake_msg 命令：伪造聊天记录并以合并转发形式发送

    用法:
        ex.fake_msg
        QQ号1: 内容1
        QQ号2: 内容2

    第一行是命令，后续每行（换行即消息分段标记）是一条消息节点；
    每行按第一个冒号分割为 QQ号 和 消息内容，显示名称优先通过
    get_stranger_info 获取，失败时回退 get_group_member_info（群名片/群内昵称），
    仍失败则回退为QQ号。
    """
    prefix = f"{builtins.config['command_prefix']}fake_msg"
    body = raw_message[len(prefix):].strip()
    if not body:
        send_group_msg(ws, group_id, "用法: ex.fake_msg\\nQQ号: 内容\\nQQ号: 内容", True)
        return

    nodes = []
    errors = []
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            errors.append(f"格式错误（缺少冒号）: {line}")
            continue
        qq_str, content = line.split(":", 1)
        qq_str = qq_str.strip()
        content = content.strip()
        if not qq_str.isdigit():
            errors.append(f"无效QQ号: {qq_str}")
            continue
        if not content:
            errors.append(f"内容为空: {line}")
            continue
        user_id = int(qq_str)
        nodes.append({
            "type": "node",
            "data": {
                "uin": user_id,
                "name": _get_nickname(ws, user_id, group_id),
                "content": [{"type": "text", "data": {"text": content}}]
            }
        })

    if not nodes:
        send_group_msg(ws, group_id, "没有可转发的消息，用法: ex.fake_msg\\nQQ号: 内容", True)
        return

    send_group_forward_msg(ws, group_id, nodes)
    if errors:
        send_group_msg(ws, group_id, "以下行格式无效，已忽略:\n" + "\n".join(errors), True)
