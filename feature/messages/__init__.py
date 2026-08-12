# messages sub-package：消息收发、分段、合并转发与消息管理相关 API

from .send import send_group_msg, send_group_msg_nolog_for_screenshot, send_private_msg
from .forward import (
    send_group_single_forward_msg,
    send_group_forward_msg,
    send_group_msg_forward_segmented,
    split_text_into_chunks,
)
from .manage import delete_message, set_emoji_like, get_message_text, mark_msg_as_read, get_msg, get_msg_sync, resolve_sync_response

__all__ = [
    "send_group_msg",
    "send_group_msg_nolog_for_screenshot",
    "send_private_msg",
    "send_group_single_forward_msg",
    "send_group_forward_msg",
    "send_group_msg_forward_segmented",
    "split_text_into_chunks",
    "delete_message",
    "set_emoji_like",
    "get_message_text",
    "mark_msg_as_read",
    "get_msg",
    "get_msg_sync",
    "resolve_sync_response",
]
