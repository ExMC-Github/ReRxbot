# group_manage sub-package：群组状态查询与管理相关 API

from .status import get_status, get_version_info, get_llbot_info
from .special_title import set_group_special_title
from .like import like_someone
from .sign import send_group_sign
from .group_list import send_get_group_list, get_group_list_and_sign_all_group
from .poke import unique_identifier
from .ban import set_group_ban

__all__ = [
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
]
