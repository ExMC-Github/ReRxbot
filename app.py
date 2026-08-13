#!/usr/bin/env python3

from loguru import logger
logger.add('app.log')
import websocket, json, builtins, os, sys, platform, tarfile, datetime
import varlist as vars
from config import config
from openai import OpenAI
builtins.config = config
from functions import qq_group_message, qq_private_message, qq_notice_message, botstatus, warnings_checker
from functions.ai_manager import AIManager
from functions.ai_functions import auto_save_all_memories, has_unsaved_memory, load_auto_saved_memories
from feature.messages.send import send_group_msg
from feature.messages.manage import resolve_sync_response
from feature.utils.compress_logs import compress_logs
print(vars.banner)
if not os.path.exists('logs'):
    os.makedirs('logs')


ai_client = OpenAI(api_key=config["ai_settings"]["ai_key"],base_url=config["ai_settings"]["ai_base_url"])
ai_manager = AIManager(rules_dir="rules", default_rule="default.txt")
loaded_count = load_auto_saved_memories(config["ai_settings"].get('ai_memory_dir', 'ai_memory'), config=config)
if loaded_count > 0:
    logger.info(f"已自动加载 {loaded_count} 个群的AI记忆")

def on_message(ws, message):
    """接收消息时的回调"""
    msg = json.loads(message)
    post_type = msg.get('post_type')
    message_type = msg.get('message_type')
    status = msg.get('status')
    echo = msg.get('echo')
    logger.info(f"收到消息: {message}")
    if echo is not None and resolve_sync_response(echo, msg.get('data')):
        return
    
    if echo is not None and echo.startswith("get_version_info"):
        echo_args = echo.split('&')
        send_group_msg(ws, echo_args[1], str(msg.get('data')))
    
    if echo is not None and echo.startswith("llbot_info"):
        echo_args = echo.split('&')
        data = msg.get('data') or {}
        send_group_msg(ws, echo_args[1],
            f"LLOneBot (LuckyLilliaBot)\n"
            f"版本：{data.get('app_version')}\n"
            f"平台：{sys.platform} ({platform.architecture()[0]})\n"
            f"运行时长：{botstatus.get_uptime_str()}")

    if (echo is not None and echo.startswith("send_group_msg_nolog_for_screenshot")):
            echo_args = echo.split('&')
            if vars.Debug == False:
                send_group_msg(ws,echo_args[1],"服务器画面截图已完成")
            else:
                send_group_msg(ws,echo_args[1],"调试端画面截图已完成")
    
    if post_type == "notice":
        qq_notice_message(ws, message)
    elif message_type == "group":
        qq_group_message(ws, message, ai_client, ai_manager)
    elif message_type == "private":
        qq_private_message(ws,message)
        
def on_error(ws, error):
    """错误回调"""
    if error is not None:
        if repr(error) != "KeyboardInterrupt()":
            logger.error(f"错误: {error}")
    

def on_close(ws, close_status_code, close_msg):
    """连接关闭回调"""
    logger.info("连接已关闭")
    
    # 自动保存所有群的AI记忆
    if has_unsaved_memory():
        logger.info("检测到未保存的AI记忆，正在保存...")
        saved_count = auto_save_all_memories(config["ai_settings"].get('ai_memory_dir', 'ai_memory'), config=config)
        logger.info(f"已自动保存 {saved_count} 个群的AI记忆")
    
    logger.remove()
    compress_logs(os,datetime,tarfile,sys)

def on_open(ws):
    """连接建立后的回调"""
    logger.info("连接已打开")
    warnings_checker.embed_check()
    warnings_checker.python_check()
    

def main():
    ws = websocket.WebSocketApp(f"ws://localhost:3001/?access_token=ExRFy123",on_open=on_open,on_message=on_message,on_error=on_error,on_close=on_close)
    builtins.ws = ws
    ws.run_forever()
    return 0

if __name__ == "__main__":
    main()

