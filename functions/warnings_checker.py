import os, varlist
import builtins, datetime, sys
from loguru import logger
config = builtins.config
from feature.messages.send import send_group_msg
from .warnings_levels import NotFoundExRFyError, NotFoundBuiltTargetError

def embed_check():
    if varlist.Debug:
        tmp = ""
        tmp = tmp + "functions.warnings_checker.embed_check called\n"
        tmp = tmp + "dump message:\n"
        tmp = tmp + f"config: {type(config)}\n"
        tmp = tmp + f"config.ai_python_exec: {config["ai_settings"]["ai_python_exec"]}\n"
        tmp = tmp + f"os.path.exists(config.ai_python_exec): {os.path.exists(config["ai_settings"]["ai_python_exec"])}\n"
        tmp = tmp + f"什么？为什么我写python要用lua的语法，这里指的是dict用.访问，其实是我闲的，反正Real代码又不是这么写的\ndump time: {datetime.datetime.now()}"

        send_group_msg(builtins.ws,varlist.tpd_group,tmp)
    if not os.path.exists(config["ai_settings"]["ai_python_exec"]):
            logger.warning("AI独立Python沙箱可能不存在！")
        
def python_check():
    if varlist.Debug:
        tmp = f"""functions.warnings_checker.python_check
dump message: {sys.version}
"""
        send_group_msg(builtins.ws,varlist.tpd_group,tmp)
    
    try:
        import encryption
        if 'ExRFy' not in sys.copyright:
            raise NotFoundExRFyError("未在sys.copyright中找到ExRFy字样")

        if not hasattr(sys,"built_target"):
            raise NotFoundBuiltTargetError("未在sys模块中找到构建类型")
    except:
        logger.critical("不是Re-NEPython环境，机器人部分功能可能无法使用！")