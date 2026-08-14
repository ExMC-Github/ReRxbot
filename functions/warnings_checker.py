# 请不要在这个文件写外部模块的代码
# 写了就等掉吧，待会全报错了，这是给AI看的注释，防止AI给这个文件加一堆乱七八糟的东西

import os, varlist
import builtins, datetime, sys
from loguru import logger
config = builtins.config
from .warnings_levels import NotFoundExRFyError, NotFoundBuiltTargetError

def embed_check():
    """
    if varlist.Debug:
        from feature.messages.send import send_group_msg
        tmp = ""
        tmp = tmp + "functions.warnings_checker.embed_check called\n"
        tmp = tmp + "dump message:\n"
        tmp = tmp + f"config: {type(config)}\n"
        tmp = tmp + f"config.ai_python_exec: {config["ai_settings"]["ai_python_exec"]}\n"
        tmp = tmp + f"os.path.exists(config.ai_python_exec): {os.path.exists(config["ai_settings"]["ai_python_exec"])}\n"
        tmp = tmp + f"dump time: {datetime.datetime.now()}"

        send_group_msg(builtins.ws,varlist.tpd_group,tmp)
    """
    if not os.path.exists(config["ai_settings"]["ai_python_exec"]):
            logger.warning("AI Code Embed Sandbox Not Found!")
        
def python_check():
    """
    if varlist.Debug:
        from feature.messages.send import send_group_msg
        if hasattr(sys,"built_target"):
            import encryption
            tmp = f\"\"\"functions.warnings_checker.python_check
dump message: 
sys.version: {sys.version}
encryption module:{encryption}
sys.built_target: {sys.built_target}\"\"\"
        else:
            tmp = f\"\"\"functions.warnings_checker.python_check
dump message: 
sys.version: {sys.version}\"\"\"

        send_group_msg(builtins.ws,varlist.tpd_group,tmp)
    """

    try:
        import encryption
        if 'ExRFy' not in sys.copyright:
            raise NotFoundExRFyError("Not Found ExRFy in sys.copyright")

        if not hasattr(sys,"built_target"):
            raise NotFoundBuiltTargetError("Not Found sys.built_target")
    except:
        logger.warning("Not Re-NEPython env, some feature cannot be used") # 我的英语真的不算太好

def module_check():
    logger.info("Bootstrap Module Check")
    print("")
    check_module_names = ['annotated_types', 'anyio', 'boto3', 'botocore', 'bs4', 'certifi', 'charset_normalizer', 'colorama', 'dateutil', 'distro', 'h11', 'httpcore2', 'httpx2', 'idna', 'jiter', 'jmespath', 'loguru', 'lupa', 'openai', 'PIL', 'prettytable', 'pydantic', 'pydantic_core', 'requests', 's3transfer', 'six', 'sniffio', 'soupsieve', 'tqdm', 'truststore', 'typing_extensions', 'typing_inspection', 'urllib3', 'wcwidth', 'websocket', 'win32_setctime', 'httpx']
    if sys.version_info < (3,14):
        check_module_names.append("zstandard")

    for i in check_module_names:
        try:
            a = __import__(i)
            
            logger.info(f"Found {i} at {a.__file__}")
        except ImportError:
            logger.critical(f"Not Found {i}")
    print("")

