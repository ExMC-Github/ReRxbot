# 这是ExRFy写的，部分是AI写的
from loguru import logger
import json, io, sys, traceback, base64
from PIL import ImageGrab
from feature.messages.send import send_group_msg, send_group_msg_nolog_for_screenshot
from feature.utils.exec_and_capture import exec_and_capture, lua_exec_and_capture
from feature.group_manage.special_title import set_group_special_title
from feature.group_manage.ban import set_group_ban
from feature.group_manage.poke import unique_identifier
from feature.group_manage.status import get_version_info, get_llbot_info
import builtins, random

def qq_group_message(ws, message, ai_client=None, ai_manager=None):
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
    raw_message = msg.get('raw_message')
    message_segments = msg.get("message", [])

    group_settings = builtins.config.get("bot_disable_settings", {}).get("group_settings", {}).get(str(group_id), {})
    if group_settings.get("is_only_admin_can_use", False) and user_id not in builtins.config["bot_admin_ids"]:
        return

    if self_id not in builtins.config["bot_admin_ids"]:
        builtins.config["bot_admin_ids"].append(self_id)
    after_at_text = []
    is_at_me = False
    for seg in message_segments:
        seg_type = seg.get("type")
        seg_data = seg.get("data", {})
        if seg_type == "at" and str(seg_data.get("qq")) == str(self_id):  # 统一转为字符串比较
            is_at_me = True
        elif is_at_me and seg_type == "text":
            after_at_text.append(seg_data.get("text", ""))
    at_full_text = "".join(after_at_text).strip() if is_at_me else ""
    
    if raw_message.startswith(f"{builtins.config["command_prefix"]}python.corun\n") or raw_message.startswith(f"{builtins.config["command_prefix"]}lua.corun\n"):
        if user_id in builtins.config["bot_admin_ids"]:
            if raw_message.startswith(f"{builtins.config["command_prefix"]}python.corun\n"):
                code = raw_message[len(f"{builtins.config["command_prefix"]}python.corun\n"):]
                result = exec_and_capture(code,sys,io,traceback,ws,group_id,self_id,user_id,msg)
            else:
                code = raw_message[len(f"{builtins.config["command_prefix"]}lua.corun\n"):]
                result = lua_exec_and_capture(code)
            send_group_msg(ws,group_id,str(result).rstrip('\r\n'))
        else:
            send_group_msg(ws,group_id,"权限不足，只有Bot管理员可以使用此命令")

    if raw_message == "test":
        send_group_msg(ws,group_id,"状态正常")

    if raw_message.startswith("戳戳我"):
        unique_identifier(ws,group_id,user_id)
    
    if raw_message == "get_version_info" or raw_message == f"{builtins.config['command_prefix']}get_version_info":
        get_version_info(ws,group_id)

    if raw_message == "#ll" or raw_message == "#llbot":
        get_llbot_info(ws,group_id)

    if raw_message == 'peekserver' or raw_message == f'{builtins.config["command_prefix"]}peekserver':
            if user_id in builtins.config["bot_admin_ids"]:
                screenshot = ImageGrab.grab()
                img_bytes = io.BytesIO()
                screenshot.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
                base64_str = base64.b64encode(img_bytes).decode('utf-8')
                send_group_msg_nolog_for_screenshot(ws,group_id,f'[CQ:image,file=base64://{base64_str}]',False)
            else:
                send_group_msg(ws,group_id,"权限不足，只有Bot管理员可以使用此命令")

    if group_id == builtins.config["bot_group"]:
        if raw_message.startswith("我要头衔 ") or raw_message.startswith("头衔测试 "):
            raw_title = raw_message[5:]
            if len(raw_title) > 16:
                prefix = raw_title[:16]
                suffix = raw_title[16:]
                num_groups = (len(suffix) + 1) // 2
                title = prefix + "锟斤拷" * num_groups
            else:
                title = raw_title
            if "群主" in raw_message[4:].replace(" ", ""):
                set_group_special_title(ws, group_id, user_id, title)
            else:
                if user_id == 2051621535 or user_id == 3955986019:
                    set_group_ban(ws, group_id, user_id, random.randint(180, 300))
                else:
                    set_group_special_title(ws, group_id, user_id, title)

        if raw_message.startswith("那我呢") and user_id == 2051621535 or user_id == 3955986019 and raw_message.startswith("那我呢"):
            set_group_ban(ws,group_id,user_id,random.randint(180,300))

        if user_id != self_id:
            try:
                a = int(raw_message)
                if not raw_message.startswith("-"):
                    send_group_msg(ws,group_id,str(a+1))
                else:
                    send_group_msg(ws,group_id,str(a-1))
            except:
                pass
    
    # 处理AI相关命令
    if ai_client and ai_manager:
        from . import ai_functions
        ai_functions.handle_ai_commands(
            ws, raw_message, group_id, msg, builtins.config, 
            ai_client, self_id, is_at_me, at_full_text, ai_manager
        )
        

def qq_private_message(ws,message):
    pass


def qq_notice_message(ws, message):
    """处理通知类事件（如：群内戳一戳）"""
    msg = json.loads(message)
    group_settings = builtins.config.get("bot_disable_settings", {}).get("group_settings", {}).get(str(msg.get("group_id")), {})
    if group_settings.get("is_only_admin_can_use", False) and msg.get('user_id') not in builtins.config["bot_admin_ids"]:
        return
    if msg.get('notice_type') == 'notify' and msg.get('sub_type') == 'poke':
        if msg.get('target_id') == msg.get('self_id'):
            group_id = msg.get('group_id')
            if group_id:
                send_group_msg(ws, group_id, f"[CQ:at,qq={msg.get("user_id")}] " + builtins.config["pokeme_msg"],False)
