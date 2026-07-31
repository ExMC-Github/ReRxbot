from loguru import logger
import json, io, dis, sys, traceback
from feature import send_group_msg, exec_and_capture, set_group_special_title, set_group_ban
import builtins, random

def qq_group_message(ws, message, ai_client=None, ai_manager=None):
    msg = json.loads(message)
    post_type = msg.get('post_type')          # 消息类型：message
    message_type = msg.get('message_type')    # 群消息：group
    group_id = msg.get('group_id')            # 群号
    group_name = msg.get('group_name')        # 群名称
    user_id = msg.get('sender', {}).get('user_id')  # 发送者QQ
    self_id = msg.get('self_id')
    nickname = msg.get('sender', {}).get('nickname')  # 昵称
    msgtime = msg.get('time')
    message_id = msg.get('message_id')
    raw_message = msg.get('raw_message')
    message_segments = msg.get("message", [])

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
    
    if raw_message.startswith("ex.python.corun\n"):
        if user_id in builtins.config["bot_admin_ids"]:
            code = raw_message[len("ex.python.corun\n"):]
            result = exec_and_capture(code,sys,io,traceback,ws)
            send_group_msg(ws,group_id,str(result).rstrip('\r\n'))
        else:
            send_group_msg(ws,group_id,str(builtins.config["bot_admin_ids"])+" | "+str(user_id in builtins.config["bot_admin_ids"])+" | "+str(user_id)+" | "+str(self_id))

    if group_id == builtins.config["bot_group"]:
        if raw_message.startswith("我要头衔 ") or raw_message.startswith("头衔测试 "):
            set_group_special_title(ws,group_id,user_id,raw_message[5:])

        if raw_message.startswith("那我呢") and user_id == 2051621535 or user_id == 3955986019:
            set_group_ban(ws,group_id,user_id,random.randint(180,300))
    
    # 处理AI相关命令
    if ai_client and ai_manager:
        from . import ai_functions
        ai_functions.handle_ai_commands(
            ws, raw_message, group_id, msg, builtins.config, 
            ai_client, self_id, is_at_me, at_full_text, ai_manager
        )
        

def qq_private_message(ws,message):
    pass
