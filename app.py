# +===============================+
# |        E x R F y  B o t       |
# |          R e m a k e          |
# +===============================+

from loguru import logger
logger.add('app.log')
import websocket
import varlist as vars
import json
import builtins
import os, sys
import tarfile
import datetime
from config import config
from openai import OpenAI
builtins.config = config
from functions import qq_group_message, qq_private_message
from functions.ai_manager import AIManager
from functions.ai_functions import auto_save_all_memories, has_unsaved_memory, load_auto_saved_memories
from feature import compress_logs
print(vars.banner)
if not os.path.exists('logs'):
    os.makedirs('logs')

# 初始化AI客户端
ai_client = OpenAI(
    api_key=config["ai_settings"]["ai_key"],
    base_url=config["ai_settings"]["ai_base_url"])

# 初始化AI管理器
ai_manager = AIManager(rules_dir="rules", default_rule="default.txt")

# 加载自动保存的AI记忆
loaded_count = load_auto_saved_memories(config["ai_settings"].get('ai_memory_dir', 'ai_memory'), config=config)
if loaded_count > 0:
    print(f"已自动加载 {loaded_count} 个群的AI记忆")

def on_message(ws, message):
    """接收消息时的回调"""
    msg = json.loads(message)
    message_type = msg.get('message_type')
    status = msg.get('status')
    echo = msg.get('echo')
    logger.info(f"收到消息: {message}")
    if message_type == "group":
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
    

def main():
    ws = websocket.WebSocketApp(f"ws://localhost:3001/?access_token=ExRFy123",on_open=on_open,on_message=on_message,on_error=on_error,on_close=on_close)
    ws.run_forever()
    return 0

if __name__ == "__main__":
    main()

