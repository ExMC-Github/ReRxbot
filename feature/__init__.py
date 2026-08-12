# feature 包：对外统一导出，兼容旧的 `from feature import xxx` 写法
#
# 子包划分：
#   messages     - 消息收发、分段、合并转发与消息管理（send/forward/manage）
#   group_manage - 群组状态查询与管理（status/special_title/like/sign/group_list/poke/ban）
#   utils        - 通用工具（compress_logs/right/exec_and_capture）

from .messages import (
    send_group_msg,
    send_group_msg_nolog_for_screenshot,
    send_private_msg,
    send_group_single_forward_msg,
    send_group_forward_msg,
    send_group_msg_forward_segmented,
    split_text_into_chunks,
    delete_message,
    set_emoji_like,
    get_message_text,
    mark_msg_as_read,
    get_msg,
    get_msg_sync,
    resolve_sync_response,
)
from .group_manage import (
    get_status,
    get_version_info,
    get_llbot_info,
    set_group_special_title,
    like_someone,
    send_group_sign,
    send_get_group_list,
    get_group_list_and_sign_all_group,
    unique_identifier,
    set_group_ban,
)
from .utils import (
    compress_logs,
    right,
    exec_and_capture,
)

__all__ = [
    # messages
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
    # group_manage
    "get_status",
    "get_version_info",
    "get_llbot_info",
    "set_group_special_title",
    "like_someone",
    "send_group_sign",
    "send_get_group_list",
    "get_group_list_and_sign_all_group",
    "unique_identifier",
    "set_group_ban",
    # utils
    "compress_logs",
    "right",
    "exec_and_capture",
]
