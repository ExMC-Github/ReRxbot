# 这是ExRFy写的，主要是我想学类似控制台的那种返回值机制，所以就写了这个
# 什么，你问我为什么是etypes这个名字，因为types被标准库占用了，虽然说一般导入都是from . import etypes，根本不走标准库

EX_DO_NOTHING = 0
EX_BREAK_MESSAGE = 1
ALL_TYPES = [EX_DO_NOTHING, EX_BREAK_MESSAGE]