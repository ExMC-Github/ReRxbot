# 这是ExRFy写给自己用的功能，反正默认是开着的，需要手动改config.py把“i_am_exrfy”关了才会不生效

import json, builtins, random, html
from . import etypes
from data import language_zh
L = language_zh.get_dict()
from feature.group_manage.poke import unique_identifier
from feature.messages.send import send_group_msg
from feature.group_manage.special_title import set_group_special_title
from feature.group_manage.ban import set_group_ban
from feature.messages.manage import set_emoji_like

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
    
    if raw_message.startswith("戳戳我"):
        unique_identifier(ws,group_id,user_id)
        return etypes.EX_BREAK_MESSAGE

    if "/kel" in raw_message or "[CQ:face,id=111,sub_type=1]" in raw_message:
        set_emoji_like(ws,message_id,111)
        return etypes.EX_BREAK_MESSAGE
    
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
