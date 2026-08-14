# 这是Ai写的，不关ExRFy的事情
# ExRFy上其实也可以的，因为这个其实看起来挺简单的

import datetime
from data import language_zh
L = language_zh.get_dict()

# 记录机器人启动时间（模块被导入时即为启动时刻）
_start_time = datetime.datetime.now()


def get_start_time():
    """获取机器人启动时间（datetime.datetime 格式）"""
    return _start_time


def get_uptime():
    """获取机器人启动至今已运行的时间（datetime.timedelta 格式）"""
    return datetime.datetime.now() - _start_time


def get_start_time_str(fmt="%Y-%m-%d %H:%M:%S"):
    """获取格式化后的启动时间字符串"""
    return _start_time.strftime(fmt)


def get_uptime_str():
    """获取格式化后的运行时长字符串（如: 1天 2小时 3分 4秒）"""
    delta = get_uptime()
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(str(days) + L["unit_day"])
    if hours:
        parts.append(str(hours) + L["unit_hour"])
    if minutes:
        parts.append(str(minutes) + L["unit_minute"])
    parts.append(str(seconds) + L["unit_second"])
    return " ".join(parts)
