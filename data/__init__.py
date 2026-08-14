# data 包：数据层
# 目前包含编译后的多语言字典 language_zh / language_en / language_pseudo（bindict 格式），
# 通过 <模块名>.get_dict() 获取语言字典。

from . import language_zh
from . import language_en
from . import language_pseudo

__all__ = [
    "language_zh",
    "language_en",
    "language_pseudo",
]
