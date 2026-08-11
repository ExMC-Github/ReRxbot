# 从字符串末尾截取指定长度的字符


def right(text, length):
    """
    自定义right函数，类似于其他语言的right函数
    """
    if length <= 0:
        return ""
    if length >= len(text):
        return text
    return text[-length:]
