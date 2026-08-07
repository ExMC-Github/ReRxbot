# +==============================+
# |    A I  F u n c t i o n s    |
# |          By ExRFy            |
# +==============================+
import threading
import re
import random
import json
import os
import pickle
import sys
from loguru import logger


# 视觉模型客户端缓存（按AI类型隔离：ai / at / defined）
_vit_clients = {}


def get_vit_client(config, client_type="ai"):
    """获取指定AI类型的视觉模型客户端（懒加载，按类型隔离）
    
    Args:
        config: 配置字典
        client_type: AI类型（"ai" / "at" / "defined"）
    """
    if client_type not in _vit_clients:
        from openai import OpenAI
        # 配置代理（如果配置中指定）
        http_client = None
        http_proxy = config.get('vit_http_proxy', '')
        https_proxy = config.get('vit_https_proxy', '')
        if http_proxy or https_proxy:
            import httpx
            mounts = {}
            if http_proxy:
                mounts["http://"] = httpx.HTTPTransport(proxy=http_proxy)
            if https_proxy:
                mounts["https://"] = httpx.HTTPTransport(proxy=https_proxy)
            http_client = httpx.Client(mounts=mounts)
        _vit_clients[client_type] = OpenAI(
            api_key=config.get('vit_api_key', ''),
            base_url=config.get('vit_base_url', ''),
            http_client=http_client
        )
    return _vit_clients[client_type]


def analyze_image(image_url, config, client_type="ai"):
    """分析单张图片并返回文字描述
    
    Args:
        image_url: 图片URL
        config: 配置字典
        client_type: AI类型（"ai" / "at" / "defined"），用于隔离视觉客户端
        
    Returns:
        图片的文字描述
    """
    if not config.get('vit_enable', False):
        return "[图片识别功能未启用]"
    
    # 去除URL中的反引号（QQ消息中URL可能被反引号包裹）
    image_url = image_url.strip('`').strip()
    
    if not image_url:
        return "[图片URL为空]"
    
    try:
        vit_client = get_vit_client(config, client_type)
        prompt = config.get('vit_prompt', '用中文尽可能详细地描述这张图片')
        response = vit_client.chat.completions.create(
            model=config.get('vit_model', 'gemini-3-flash-preview'),
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            stream=False
        )
        
        description = response.choices[0].message.content or ""
        logger.info(f"[{client_type}] 图片分析完成: {description[:100]}...")
        return description
    except Exception as e:
        logger.error(f"[{client_type}] 图片分析失败: {e}")
        return f"[图片分析失败: {str(e)}]"


def extract_image_descriptions(msg, config, client_type="ai"):
    """从消息中提取所有图片并分析，返回图片描述文本
    
    Args:
        msg: OneBot消息对象
        config: 配置字典
        client_type: AI类型（"ai" / "at" / "defined"），用于隔离视觉客户端
        
    Returns:
        图片描述文本（多张图片用换行分隔），无图片时返回空字符串
    """
    if not config.get('vit_enable', False):
        return ""
    
    message_segments = msg.get('message', [])
    image_descriptions = []
    
    for segment in message_segments:
        if segment.get('type') == 'image':
            image_data = segment.get('data', {})
            image_url = image_data.get('url', '')
            if image_url:
                description = analyze_image(image_url, config, client_type)
                image_descriptions.append(f"【图片】{description}【/图片】")
    
    return '\n'.join(image_descriptions)


# 存储每个群的对话历史
ai_conversation_history = {}
ai_threads = {}
at_ai_conversation_history = {}
at_ai_threads = {}
defined_conversation_history = {}
defined_threads = {}

# 被AI忽略的用户（非机器人群中的"禁言"等效为忽略，AI不再接收该用户消息）
# 格式: {group_id: set(user_ids)}
ignored_users = {}


# 定义可用的工具函数
def get_available_tools():
    """定义AI可以调用的工具"""
    return [
        {
            "type": "function",
            "function": {
                "name": "mute",
                "description": "禁言或忽略群内指定用户。在机器人群中将真实禁言，在其他群中将忽略该用户（AI不再接收其消息）。可以指定当前用户或其他用户，支持自定义时长（仅在机器人群中生效）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "要禁言/忽略的用户QQ号，如果不指定则针对当前用户"
                        },
                        "duration": {
                            "type": "integer",
                            "description": "禁言时长（秒），仅在机器人群中生效，如果不指定则随机1-5分钟"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "unmute",
                "description": "解除禁言或取消忽略群内指定用户。在机器人群中解除真实禁言，在其他群中取消忽略（AI恢复接收该用户消息）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "要解除禁言/取消忽略的用户QQ号，如果不指定则针对当前用户"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "filedir",
                "description": "列出指定目录的文件和子目录列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "要列出的目录路径，如果不指定则列出当前目录"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_code",
                "description": "执行Python代码",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string"
                        }
                    },
                    "required": ["code"]
                }
            }
        }
    ]


def execute_tool_call(ws, group_id, tool_name, tool_args, user_id):
    """执行工具调用"""
    from feature import set_group_ban
    import builtins
    
    try:
        if tool_name == "mute":
            target_id = tool_args.get("user_id", user_id)
            duration = tool_args.get("duration", random.randint(60, 300))
            if target_id in builtins.config["bot_admin_ids"]:
                logger.warning(f"执行工具 {tool_name} 失败: 不能禁言/忽略机器人管理员")
                return "Permission Denied"
            
            # 机器人群使用真实禁言，其他群改为忽略用户（AI不再接收该用户消息）
            if group_id == builtins.config.get("bot_group"):
                logger.info(f"执行工具 {tool_name} 成功: 禁言用户 {target_id} {duration} 秒")
                set_group_ban(ws, group_id, target_id, duration)
                return f"已禁言用户 {target_id} {duration} 秒"
            else:
                if group_id not in ignored_users:
                    ignored_users[group_id] = set()
                ignored_users[group_id].add(target_id)
                logger.info(f"执行工具 {tool_name} 成功: 在非机器人群 {group_id} 忽略用户 {target_id}")
                return f"已忽略用户 {target_id}（非机器人群，AI将不再接收该用户的消息）"
        
        elif tool_name == "unmute":
            target_id = tool_args.get("user_id", user_id)
            if group_id == builtins.config.get("bot_group"):
                set_group_ban(ws, group_id, target_id, 0)
                logger.info(f"执行工具 {tool_name} 成功: 解除禁言用户 {target_id}")
                return f"已解除禁言用户 {target_id}"
            else:
                if group_id in ignored_users and target_id in ignored_users[group_id]:
                    ignored_users[group_id].discard(target_id)
                    logger.info(f"执行工具 {tool_name} 成功: 取消忽略用户 {target_id}")
                    return f"已取消忽略用户 {target_id}（AI将重新接收该用户的消息）"
                else:
                    return f"用户 {target_id} 未被忽略，无需操作"
        
        elif tool_name == "filedir":
            path = tool_args.get("path", ".")
            if not os.path.exists(path):
                return f"路径不存在: {path}"
            
            try:
                items = os.listdir(path)
                result_lines = [f"目录 {path} 的内容:"]
                for item in items:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        result_lines.append(f"📁 {item}/")
                    else:
                        result_lines.append(f"📄 {item}")
                return "\n".join(result_lines)
            except PermissionError:
                return f"无权限访问目录: {path}"
            except Exception as e:
                return f"列出目录失败: {str(e)}"
        
        elif tool_name == "execute_code":
            # 鉴权：非管理员直接拒绝，不弹窗
            if user_id not in builtins.config["bot_admin_ids"]:
                logger.warning(f"执行工具 {tool_name} 失败: 用户 {user_id} 无权限（非管理员）")
                return "Permission Denied: 仅机器人管理员可执行代码"
            
            code = tool_args.get("code", "")
            if not code:
                return "代码内容为空，未执行"
            
            approved, final_code, timed_out, extra_content = review_and_execute_code(code)
            
            if timed_out:
                logger.warning(f"执行工具 {tool_name}: 代码审核超时（30秒未操作）")
                return "代码审核超时（30秒内未操作），未执行代码"
            
            if not approved:
                logger.info(f"执行工具 {tool_name}: 代码审核被拒绝")
                reject_msg = "代码审核被拒绝（用户选择不执行），未执行代码"
                if extra_content:
                    reject_msg = f"{reject_msg}\n\n[附加内容]\n{extra_content}"
                return reject_msg
            
            logger.info(f"执行工具 {tool_name}: 代码审核通过，开始执行")
            result = execute_python_code(final_code)
            logger.info(f"执行工具 {tool_name}: 代码执行完成")
            
            if extra_content:
                result = f"{result}\n\n[附加内容]\n{extra_content}"
            return result
        
        else:
            logger.warning(f"执行工具 {tool_name} 失败: 未知工具")
            return f"Unknown Tool"
    
    except Exception as e:
        logger.error(f"执行工具 {tool_name} 失败: {e}")
        return f"执行工具 {tool_name} 失败: {str(e)}"


def review_and_execute_code(code):
    """通过独立子进程运行 tkinter(ttk) 弹窗审核代码
    使用子进程彻底避免 Tcl_AsyncDelete 线程错误
    返回 (是否执行, 代码, 是否超时, 附加内容)
    """
    import subprocess
    import json

    gui_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_review_gui.py")

    try:
        # 用 UTF-8 编码传输，避免 Windows GBK 无法编码 emoji
        code_bytes = code.encode('utf-8')
        proc = subprocess.run(
            [sys.executable, gui_script],
            input=code_bytes,
            capture_output=True,
            timeout=300
        )
        stdout_str = proc.stdout.decode('utf-8', errors='replace')
        stderr_str = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ""

        if proc.returncode == 0 and stdout_str:
            result = json.loads(stdout_str.strip())
            return result.get("approved", False), code, result.get("timeout", False), result.get("extra")
        else:
            logger.error(f"代码审核GUI异常退出(returncode={proc.returncode}): {stderr_str}")
            return False, code, False, None
    except subprocess.TimeoutExpired:
        logger.warning("代码审核GUI子进程超时")
        return False, code, True, None
    except Exception as e:
        logger.error(f"代码审核GUI调用失败: {e}")
        return False, code, False, None


def execute_python_code(code):
    """执行 Python 代码并返回输出结果（使用配置的Python解释器）"""
    import subprocess
    import builtins
    import traceback

    try:
        # 获取配置的Python解释器路径
        python_exec = builtins.config.get('ai_python_exec', '').strip()
        if not python_exec:
            python_exec = sys.executable  # 未配置时使用当前Python

        # 如果是相对路径，转换为绝对路径（相对于工作目录）
        if not os.path.isabs(python_exec):
            python_exec = os.path.abspath(python_exec)

        # 检查解释器是否存在
        if not os.path.exists(python_exec):
            logger.warning(f"配置的Python解释器不存在: {python_exec}，使用默认Python")
            python_exec = sys.executable

        logger.info(f"使用Python解释器: {python_exec}")

        # 使用子进程执行代码
        proc = subprocess.run(
            [python_exec, '-c', code],
            capture_output=True,
            text=True,
            timeout=60  # 60秒超时
        )

        result = ""
        if proc.stdout:
            result += proc.stdout
        if proc.stderr:
            if result:
                result += "\n[stderr]\n" + proc.stderr
            else:
                result = "[stderr]\n" + proc.stderr

        if not result.strip():
            result = "代码执行完成（无输出）"

        return result

    except subprocess.TimeoutExpired:
        return "代码执行超时（60秒）"
    except Exception as e:
        tb = traceback.format_exc()
        return f"代码执行出错:\n{tb}"


def process_tool_calls(ws, group_id, message, user_id, ai_client, conversation_history):
    """处理AI的工具调用"""
    from feature import send_group_msg
    
    # 检查是否有工具调用
    if hasattr(message, 'tool_calls') and message.tool_calls:
        # 将助手的消息添加到历史（包含工具调用）
        conversation_history.append(message.to_dict())
        
        # 执行每个工具调用
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"AI调用工具: {tool_name}, 参数: {tool_args}")
            
            # 执行工具
            result = execute_tool_call(ws, group_id, tool_name, tool_args, user_id)
            
            # 将工具结果添加到历史
            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
        
        # 再次调用AI，让它根据工具结果继续生成回复
        return True
    
    return False


def defined_worker(ws, group_id, msg, config, ai_client, self_id, ai_manager):
    """处理defined对话的工作线程(使用defined.txt提示词)"""
    from feature import get_message_text, send_group_msg, send_group_single_forward_msg
    
    user_input = get_message_text(msg)[len("defined "):]
    user_id = msg.get('sender', {}).get('user_id')
    nickname = msg.get('sender', {}).get('nickname')
    message_id = msg.get('message_id')  # 获取消息ID
    
    # 提取并分析图片
    image_content = extract_image_descriptions(msg, config, client_type="defined")
    if image_content:
        user_input = f"{user_input}\n{image_content}" if user_input.strip() else image_content
    
    # 构建额外的提示信息
    ai_append_words = f"当前提问者QQ号为{user_id} | 提问者名字为{nickname} | bot管理员是{config['bot_admin_ids']}"
    
    # 获取或初始化该群的历史消息
    if group_id not in defined_conversation_history:
        # 使用配置中defined对应的规则文件
        rules_defined = config.get('rules_defined', {})
        rule_file = rules_defined.get('defined', 'defined.txt')
        system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
        defined_conversation_history[group_id] = [
            {"role": "system", "content": f"{system_prompt}\n\n\n额外规则：用户说的话后面的括号由程序添加，你必须遵循"}
        ]
    
    # 添加用户消息到历史
    defined_conversation_history[group_id].append({
        "role": "user",
        "content": f"{user_input} （{ai_append_words}）"
    })
    
    try:
        # 调用 AI API
        response = ai_client.chat.completions.create(
            model=config['ai_model'],
            messages=defined_conversation_history[group_id],
            tools=get_available_tools(),
            tool_choice="auto",
            stream=False
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用（如果需要）—— 所有群均启用工具调用
        if config.get('ai_owner_group_future_mode', False):
            while process_tool_calls(ws, group_id, assistant_message, user_id, ai_client, defined_conversation_history[group_id]):
                response = ai_client.chat.completions.create(
                    model=config['ai_model'],
                    messages=defined_conversation_history[group_id],
                    tools=get_available_tools(),
                    tool_choice="auto",
                    stream=False
                )
                assistant_message = response.choices[0].message
        
        # 获取最终回复
        assistant_reply = assistant_message.content or ""
        
        # 将助手的回复添加到历史
        if assistant_message.content:
            defined_conversation_history[group_id].append({"role": "assistant", "content": assistant_reply})
        
        # 发送回复
        if assistant_reply:
            if len(assistant_reply) > 299:
                # 合并转发消息,不添加回复和@
                send_group_single_forward_msg(ws, group_id, self_id, "杨诺轩", assistant_reply)
            else:
                # 普通消息,添加回复和@,关闭auto_escape
                reply_message = f"[CQ:reply,id={message_id}][CQ:at,qq={user_id}] {assistant_reply}"
                send_group_msg(ws, group_id, reply_message, auto_escape=False)
    
    except Exception as e:
        error_msg = f"DeepSeek API 调用出错: {str(e)}"
        logger.error(error_msg)
        send_group_single_forward_msg(ws, group_id, self_id, "DeepSeek 错误", error_msg)
        if group_id in defined_conversation_history and defined_conversation_history[group_id][-1]["role"] == "user":
            defined_conversation_history[group_id].pop()
    finally:
        if group_id in defined_threads:
            del defined_threads[group_id]


def ai_worker(ws, group_id, msg, config, ai_client, self_id, ai_manager):
    """处理AI对话的工作线程"""
    from feature import get_message_text, send_group_msg, send_group_single_forward_msg
    import datetime

    user_input = get_message_text(msg)[len(f"{config['command_prefix']}{config['ai_shortname']} "):]
    user_id = msg.get('sender', {}).get('user_id')
    nickname = msg.get('sender', {}).get('nickname')
    
    # 提取并分析图片
    image_content = extract_image_descriptions(msg, config, client_type="ai")
    if image_content:
        user_input = f"{user_input}\n{image_content}" if user_input.strip() else image_content
    
    # 构建额外的提示信息
    ai_append_words = f"当前提问者QQ号为{user_id} | 提问者名字为{nickname} | bot管理员是{config['bot_admin_ids']} | 当前时间是{datetime.datetime.now()}"
    
    # 获取或初始化该群的历史消息
    if group_id not in ai_conversation_history:
        # 使用配置中normal对应的规则文件
        rules_defined = config.get('rules_defined', {})
        rule_file = rules_defined.get('normal', 'default.txt')
        system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
        ai_conversation_history[group_id] = [
            {"role": "system", "content": f"{system_prompt}\n\n\n额外规则：用户说的话后面的括号由程序添加，你必须遵循"}
        ]
    
    # 添加用户消息到历史
    ai_conversation_history[group_id].append({
        "role": "user",
        "content": f"{user_input} （{ai_append_words}）"
    })
    
    try:
        # 第一次调用AI API
        response = ai_client.chat.completions.create(
            model=config['ai_model'],
            messages=ai_conversation_history[group_id],
            tools=get_available_tools(),
            tool_choice="auto",
            stream=False
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用（如果需要）—— 所有群均启用工具调用
        if config.get('ai_owner_group_future_mode', False):
            while process_tool_calls(ws, group_id, assistant_message, user_id, ai_client, ai_conversation_history[group_id]):
                # AI执行了工具调用，需要再次调用AI获取最终回复
                response = ai_client.chat.completions.create(
                    model=config['ai_model'],
                    messages=ai_conversation_history[group_id],
                    tools=get_available_tools(),
                    tool_choice="auto",
                    stream=False
                )
                assistant_message = response.choices[0].message
        
        # 获取最终回复
        assistant_reply = assistant_message.content or ""
        
        # 将助手的回复添加到历史
        if assistant_message.content:
            ai_conversation_history[group_id].append({"role": "assistant", "content": assistant_reply})
        
        # 发送回复
        if assistant_reply:
            if len(assistant_reply) > 299:
                send_group_single_forward_msg(ws, group_id, self_id, config['ai_name'], 
                                              assistant_reply + "\n\n（以上内容由AI生成，仅供参考）")
            else:
                send_group_msg(ws, group_id, assistant_reply + "\n\n（以上内容由AI生成，仅供参考）")
    
    except Exception as e:
        error_msg = f"{config['ai_name']} API 调用出错: {str(e)}"
        logger.error(error_msg)
        send_group_single_forward_msg(ws, group_id, self_id, f"{config['ai_name']} 错误", error_msg)
        if group_id in ai_conversation_history and ai_conversation_history[group_id][-1]["role"] == "user":
            ai_conversation_history[group_id].pop()
    finally:
        if group_id in ai_threads:
            del ai_threads[group_id]


def at_ai_worker(ws, group_id, user_input, original_msg, config, ai_client, self_id, ai_manager):
    """处理@触发的AI对话的工作线程"""
    from feature import send_group_msg, send_group_single_forward_msg
    import datetime
    
    user_id = original_msg.get('sender', {}).get('user_id')
    nickname = original_msg.get('sender', {}).get('nickname')
    
    # 提取并分析图片
    image_content = extract_image_descriptions(original_msg, config, client_type="at")
    if image_content:
        user_input = f"{user_input}\n{image_content}" if user_input.strip() else image_content
    
    ai_append_words = f"当前提问者QQ号为{user_id} | 提问者名字为{nickname} | bot管理员是{config['bot_admin_ids']} | 当前时间是{datetime.datetime.now()}"
    
    if group_id not in at_ai_conversation_history:
        # 使用配置中at对应的规则文件
        rules_defined = config.get('rules_defined', {})
        rule_file = rules_defined.get('at', 'default.txt')
        system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
        at_ai_conversation_history[group_id] = [
            {"role": "system", "content": f"{system_prompt}\n\n\n额外规则：用户说的话后面的括号由程序添加，你必须遵循"}
        ]
    
    at_ai_conversation_history[group_id].append({
        "role": "user",
        "content": f"{user_input} （{ai_append_words}）"
    })
    
    try:
        response = ai_client.chat.completions.create(
            model=config['ai_model'],
            messages=at_ai_conversation_history[group_id],
            tools=get_available_tools(),
            tool_choice="auto",
            stream=False
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用 —— 所有群均启用工具调用
        if config.get('ai_owner_group_future_mode', False):
            while process_tool_calls(ws, group_id, assistant_message, user_id, ai_client, at_ai_conversation_history[group_id]):
                response = ai_client.chat.completions.create(
                    model=config['ai_model'],
                    messages=at_ai_conversation_history[group_id],
                    tools=get_available_tools(),
                    tool_choice="auto",
                    stream=False
                )
                assistant_message = response.choices[0].message
        
        assistant_reply = assistant_message.content or ""
        
        if assistant_message.content:
            at_ai_conversation_history[group_id].append({"role": "assistant", "content": assistant_reply})
        
        if assistant_reply:
            if len(assistant_reply) > 299:
                send_group_single_forward_msg(ws, group_id, self_id, config['ai_name'],
                                              assistant_reply + "\n\n（以上内容由AI生成，仅供参考）")
            else:
                send_group_msg(ws, group_id, assistant_reply + "\n\n（以上内容由AI生成，仅供参考）")
    
    except Exception as e:
        error_msg = f"{config['ai_name']} API 调用出错: {str(e)}"
        logger.error(error_msg)
        send_group_single_forward_msg(ws, group_id, self_id, f"{config['ai_name']} 错误", error_msg)
        if group_id in at_ai_conversation_history and at_ai_conversation_history[group_id][-1]["role"] == "user":
            at_ai_conversation_history[group_id].pop()
    finally:
        if group_id in at_ai_threads:
            del at_ai_threads[group_id]


def handle_ai_commands(ws, raw_message, group_id, msg, config, ai_client, self_id, 
                       is_at_me, at_full_text, ai_manager):
    """处理AI相关的命令"""
    from feature import send_group_msg
    
    user_id = msg.get('sender', {}).get('user_id')
    
    # 检查该用户是否被AI忽略（非机器人群中mute等效为忽略，AI不再接收其消息）
    # 机器人管理员不受忽略限制
    if user_id and user_id in ignored_users.get(group_id, set()) and user_id not in config.get('bot_admin_ids', []):
        return
    
    # 处理defined命令(使用defined.txt提示词)
    if raw_message.startswith("defined "):
        if group_id in defined_threads and defined_threads[group_id].is_alive():
            send_group_msg(ws, group_id, f"本群已有defined对话正在进行，请等待完成后再试", True)
        else:
            pass
            # 使用defined提示词创建worker
            thread = threading.Thread(
                target=defined_worker,
                args=(ws, group_id, msg, config, ai_client, self_id, ai_manager)
            )
            defined_threads[group_id] = thread
            thread.start()
    
    # 处理原有的ex.dpsk命令
    elif raw_message.startswith(f"{config['command_prefix']}{config['ai_shortname']} "):
        if group_id in ai_threads and ai_threads[group_id].is_alive():
            send_group_msg(ws, group_id, f"本群已有 {config['ai_name']} 对话正在进行，请等待完成后再试", True)
        else:
            send_group_msg(ws, group_id, "AI正在处理您的问题，请稍后...", True)
            thread = threading.Thread(
                target=ai_worker,
                args=(ws, group_id, msg, config, ai_client, self_id, ai_manager)
            )
            ai_threads[group_id] = thread
            thread.start()
    
    elif raw_message == f"{config['command_prefix']}{config['ai_shortname']}.reset":
        if group_id in ai_conversation_history:
            system_prompt = ai_manager.get_rule()
            ai_conversation_history[group_id] = [{"role": "system", "content": system_prompt}]
            send_group_msg(ws, group_id, f"已重置当前群的 {config['ai_name']} 对话历史。", True)
        else:
            send_group_msg(ws, group_id, f"当前群没有活跃的 {config['ai_name']} 对话历史，无需重置。", True)
    
    elif is_at_me and (at_full_text or any(seg.get("type") == "image" for seg in msg.get("message", []))):
        if config.get('at_ai_enable', False):
            if group_id in at_ai_threads and at_ai_threads[group_id].is_alive():
                send_group_msg(ws, group_id, f"本群已有 {config['ai_name']} 对话（被@触发）正在进行，请等待完成后再试", True)
            else:
                thread = threading.Thread(
                    target=at_ai_worker,
                    args=(ws, group_id, at_full_text, msg, config, ai_client, self_id, ai_manager)
                )
                at_ai_threads[group_id] = thread
                thread.start()
    
    elif raw_message == f"{config['command_prefix']}{config['ai_shortname']}.at.reset":
        if group_id in at_ai_conversation_history:
            system_prompt = ai_manager.get_rule()
            at_ai_conversation_history[group_id] = [{"role": "system", "content": system_prompt}]
            send_group_msg(ws, group_id, f"已重置当前群的 {config['ai_name']} At 对话历史。", True)
        else:
            send_group_msg(ws, group_id, f"当前群没有活跃的 {config['ai_name']} At 对话历史，无需重置。", True)
    
    elif raw_message == f"{config['command_prefix']}{config['ai_shortname']}.defined.reset":
        if group_id in defined_conversation_history:
            # 使用配置中defined对应的规则文件
            rules_defined = config.get('rules_defined', {})
            rule_file = rules_defined.get('defined', 'defined.txt')
            system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
            defined_conversation_history[group_id] = [{"role": "system", "content": system_prompt}]
            send_group_msg(ws, group_id, f"已重置当前群的 defined 对话历史。", True)
        else:
            send_group_msg(ws, group_id, f"当前群没有活跃的 defined 对话历史，无需重置。", True)
    
    elif raw_message.startswith(f"{config['command_prefix']}{config['ai_shortname']}.save "):
        # 保存AI记忆 ex.dpsk.save 记忆名称
        memory_name = raw_message[len(f"{config['command_prefix']}{config['ai_shortname']}.save "):].strip()
        if memory_name:
            success, result = save_group_memory(group_id, memory_name, config.get('ai_memory_dir', 'ai_memory'))
            if success:
                send_group_msg(ws, group_id, f"已保存 {config['ai_name']} 对话记忆: {result}", True)
            else:
                send_group_msg(ws, group_id, f"保存 {config['ai_name']} 对话记忆失败: {result}", True)
        else:
            send_group_msg(ws, group_id, f"请指定记忆名称，例如: {config['command_prefix']}{config['ai_shortname']}.save my_memory", True)
    
    elif raw_message.startswith(f"{config['command_prefix']}{config['ai_shortname']}.load "):
        # 加载AI记忆 ex.dpsk.load 记忆名称
        memory_name = raw_message[len(f"{config['command_prefix']}{config['ai_shortname']}.load "):].strip()
        if memory_name:
            success, result = load_group_memory(group_id, memory_name, config.get('ai_memory_dir', 'ai_memory'))
            if success:
                send_group_msg(ws, group_id, f"已加载 {config['ai_name']} 对话记忆: {result}", True)
            else:
                send_group_msg(ws, group_id, f"加载 {config['ai_name']} 对话记忆失败: {result}", True)
        else:
            send_group_msg(ws, group_id, f"请指定记忆名称，例如: {config['command_prefix']}{config['ai_shortname']}.load my_memory", True)
    
    elif raw_message == f"{config['command_prefix']}{config['ai_shortname']}.list":
        # 列出当前群的记忆列表
        memories = list_group_memories(group_id, config.get('ai_memory_dir', 'ai_memory'))
        if memories:
            memory_list = "\n".join([f"• {mem}" for mem in memories])
            send_group_msg(ws, group_id, f"当前群的 {config['ai_name']} 记忆列表:\n{memory_list}", True)
        else:
            send_group_msg(ws, group_id, f"当前群没有保存的 {config['ai_name']} 记忆。", True)


def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    # 定义非法字符
    illegal_chars = ['.', '..', '\\', '/', '|', ':', '*', '?', '"', '<', '>']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename


def save_group_memory(group_id, memory_name=None, memory_dir="ai_memory", auto_save=False, memory_type="normal"):
    """保存单个群的AI记忆
    
    Args:
        group_id: 群号
        memory_name: 记忆名称(手动保存时需要)
        memory_dir: 记忆目录
        auto_save: 是否自动保存
        memory_type: 记忆类型 ("normal", "at", "defined")
    """
    import datetime
    
    try:
        # 确保记忆目录存在
        if not os.path.exists(memory_dir):
            os.makedirs(memory_dir)
        
        # 根据类型准备保存的数据
        if memory_type == "normal":
            data = {
                'ai_conversation_history': ai_conversation_history.get(group_id, [])
            }
        elif memory_type == "at":
            data = {
                'at_ai_conversation_history': at_ai_conversation_history.get(group_id, [])
            }
        elif memory_type == "defined":
            data = {
                'defined_conversation_history': defined_conversation_history.get(group_id, [])
            }
        else:
            return False, "无效的记忆类型"
        
        # 生成文件名
        if auto_save:
            # 自动保存格式: {类型}_autosave_{群号}_{时间}.dat
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{memory_type}_autosave_{group_id}_{timestamp}.dat"
        else:
            # 手动保存格式: {群号}_{记忆名称}.dat
            if memory_name:
                memory_name = sanitize_filename(memory_name)
                filename = f"{group_id}_{memory_name}.dat"
            else:
                return False, "记忆名称不能为空"
        
        # 序列化数据
        serialized_data = pickle.dumps(data)
        
        # 压缩数据
        if sys.version_info >= (3, 14):
            import compression.zstd as zstd
        else:
            if hasattr(sys, "built_target"):
                import zstd
            else:
                import zstandard as zstd
        
        compressed_data = zstd.compress(serialized_data)
        
        # 保存到文件
        memory_file = os.path.join(memory_dir, filename)
        with open(memory_file, 'wb') as f:
            f.write(compressed_data)
        
        logger.info(f"群 {group_id} AI记忆已保存到: {memory_file}")
        return True, filename
    
    except Exception as e:
        logger.error(f"保存群 {group_id} AI记忆失败: {e}")
        return False, str(e)


def load_group_memory(group_id, memory_name, memory_dir="ai_memory"):
    """加载单个群的AI记忆"""
    global ai_conversation_history, at_ai_conversation_history
    
    try:
        # 清理记忆名称
        memory_name = sanitize_filename(memory_name)
        filename = f"{group_id}_{memory_name}.dat"
        memory_file = os.path.join(memory_dir, filename)
        
        # 检查记忆文件是否存在
        if not os.path.exists(memory_file):
            logger.warning(f"AI记忆文件不存在: {memory_file}")
            return False, f"记忆文件不存在: {memory_name}"
        
        # 读取压缩数据
        with open(memory_file, 'rb') as f:
            compressed_data = f.read()
        
        # 解压数据
        if sys.version_info >= (3, 14):
            import compression.zstd as zstd
        else:
            if hasattr(sys, "built_target"):
                import zstd
            else:
                import zstandard as zstd
        
        serialized_data = zstd.decompress(compressed_data)
        
        # 反序列化数据
        data = pickle.loads(serialized_data)
        
        # 恢复记忆
        ai_conversation_history[group_id] = data.get('ai_conversation_history', [])
        at_ai_conversation_history[group_id] = data.get('at_ai_conversation_history', [])
        
        logger.info(f"群 {group_id} AI记忆已从 {memory_file} 加载")
        return True, f"已加载记忆: {memory_name}"
    
    except Exception as e:
        logger.error(f"加载群 {group_id} AI记忆失败: {e}")
        return False, str(e)


def list_group_memories(group_id, memory_dir="ai_memory"):
    """列出指定群的记忆文件列表"""
    import re
    
    try:
        # 检查记忆目录是否存在
        if not os.path.exists(memory_dir):
            return []
        
        # 获取所有记忆文件
        memory_files = []
        pattern = re.compile(rf'^{group_id}_(.+)\.dat$')
        
        for filename in os.listdir(memory_dir):
            if filename.endswith('.dat'):
                match = pattern.match(filename)
                if match:
                    memory_name = match.group(1)
                    memory_files.append(memory_name)
        
        return sorted(memory_files)
    
    except Exception as e:
        logger.error(f"列出群 {group_id} 记忆文件失败: {e}")
        return []


def auto_save_all_memories(memory_dir="ai_memory"):
    """自动保存所有有对话历史的群的记忆"""
    saved_count = 0
    
    # 保存所有有AI对话历史的群
    for group_id in ai_conversation_history.keys():
        if ai_conversation_history[group_id]:  # 只保存有内容的记忆
            success, _ = save_group_memory(group_id, None, memory_dir, auto_save=True, memory_type="normal")
            if success:
                saved_count += 1
    
    # 保存所有有@AI对话历史的群
    for group_id in at_ai_conversation_history.keys():
        if at_ai_conversation_history[group_id]:  # 只保存有内容的记忆
            success, _ = save_group_memory(group_id, None, memory_dir, auto_save=True, memory_type="at")
            if success:
                saved_count += 1
    
    # 保存所有有defined对话历史的群
    for group_id in defined_conversation_history.keys():
        if defined_conversation_history[group_id]:  # 只保存有内容的记忆
            success, _ = save_group_memory(group_id, None, memory_dir, auto_save=True, memory_type="defined")
            if success:
                saved_count += 1
    
    return saved_count


def has_unsaved_memory():
    """检查是否有未保存的记忆"""
    # 检查是否有群有对话历史
    for group_id, history in ai_conversation_history.items():
        if len(history) > 1:  # 超过系统提示的内容
            return True
    
    for group_id, history in at_ai_conversation_history.items():
        if len(history) > 1:  # 超过系统提示的内容
            return True
    
    for group_id, history in defined_conversation_history.items():
        if len(history) > 1:  # 超过系统提示的内容
            return True
    
    return False


def load_auto_saved_memories(memory_dir="ai_memory"):
    """启动时自动加载所有自动保存的记忆并删除文件"""
    import re
    
    loaded_count = 0
    
    try:
        # 检查记忆目录是否存在
        if not os.path.exists(memory_dir):
            return loaded_count
        
        # 遍历所有自动保存的文件
        pattern = re.compile(r'^(normal|at|defined)_autosave_(\d+)_(\d{8}_\d{6})\.dat$')
        
        for filename in os.listdir(memory_dir):
            if filename.endswith('.dat'):
                match = pattern.match(filename)
                if match:
                    memory_type = match.group(1)
                    group_id = int(match.group(2))
                    memory_file = os.path.join(memory_dir, filename)
                    
                    try:
                        # 读取压缩数据
                        with open(memory_file, 'rb') as f:
                            compressed_data = f.read()
                        
                        # 解压数据
                        if sys.version_info >= (3, 14):
                            import compression.zstd as zstd
                        else:
                            if hasattr(sys, "built_target"):
                                import zstd
                            else:
                                import zstandard as zstd
                        
                        serialized_data = zstd.decompress(compressed_data)
                        
                        # 反序列化数据
                        data = pickle.loads(serialized_data)
                        
                        # 恢复记忆
                        if memory_type == "normal":
                            global ai_conversation_history
                            ai_conversation_history[group_id] = data.get('ai_conversation_history', [])
                        elif memory_type == "at":
                            global at_ai_conversation_history
                            at_ai_conversation_history[group_id] = data.get('at_ai_conversation_history', [])
                        elif memory_type == "defined":
                            global defined_conversation_history
                            defined_conversation_history[group_id] = data.get('defined_conversation_history', [])
                        
                        # 删除已加载的自动保存文件
                        os.remove(memory_file)
                        
                        logger.info(f"已自动加载群 {group_id} 的 {memory_type} 记忆并删除文件: {filename}")
                        loaded_count += 1
                    
                    except Exception as e:
                        logger.error(f"加载自动保存文件 {filename} 失败: {e}")
        
        return loaded_count
    
    except Exception as e:
        logger.error(f"自动加载记忆失败: {e}")
        return loaded_count