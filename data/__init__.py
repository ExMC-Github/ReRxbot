# data 包：数据层
# 目前包含编译后的多语言字典 language_zh（bindict 格式），
# 通过 language_zh.get_dict() 获取语言字典。

from . import language_zh

__all__ = [
    "language_zh",
]
