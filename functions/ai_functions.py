# 曾经是ExRFy写的，现在基本上不是ExRFy写的了，因为AI太神秘了，openai的事情就应该AI自己写
# 所以呢？这个文件现在基本上是全AI写的，虽然说AI也参考了老代码(没Re的RxBot)
import threading
import re
import random
import json
import os
import pickle
import sys
import html
from loguru import logger
from .languages_choicer import L


# 视觉模型客户端缓存（按AI类型隔离：ai / at / defined）
_vit_clients = {}

# boto3 客户端缓存
_boto3_client = None
_boto3_config_cache = None


def _get_boto3_client(config):
    """获取 boto3 S3 客户端（懒加载单例）
    
    Args:
        config: 配置字典
        
    Returns:
        boto3 S3 客户端实例
    """
    global _boto3_client, _boto3_config_cache
    
    boto3_config = config["ai_settings"].get('ai_memory_boto3_config', {})
    config_key = str(boto3_config)
    
    # 如果配置没变且客户端已存在，直接返回
    if _boto3_client is not None and _boto3_config_cache == config_key:
        return _boto3_client
    
    import boto3
    from botocore.config import Config as BotoConfig
    
    s3_config = BotoConfig(
        signature_version='s3v4',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    
    _boto3_client = boto3.client(
        's3',
        endpoint_url=boto3_config.get('api', ''),
        aws_access_key_id=boto3_config.get('access_key', ''),
        aws_secret_access_key=boto3_config.get('secret_key', ''),
        config=s3_config
    )
    _boto3_config_cache = config_key
    
    logger.info("boto3 S3 客户端已初始化")
    return _boto3_client


def _is_boto3_backup_enabled(config):
    """检查是否启用了 boto3 备份
    
    Args:
        config: 配置字典
        
    Returns:
        是否启用 boto3 备份
    """
    return config["ai_settings"].get('ai_memory_boto3_backup', False)


def _compress_data(data):
    """压缩数据（通用方法）"""
    serialized_data = pickle.dumps(data)
    if sys.version_info >= (3, 14):
        import compression.zstd as zstd
    else:
        if hasattr(sys, "built_target"):
            import zstd
        else:
            import zstandard as zstd
    return zstd.compress(serialized_data)


def _decompress_data(compressed_data):
    """解压数据（通用方法）"""
    if sys.version_info >= (3, 14):
        import compression.zstd as zstd
    else:
        if hasattr(sys, "built_target"):
            import zstd
        else:
            import zstandard as zstd
    serialized_data = zstd.decompress(compressed_data)
    return pickle.loads(serialized_data)


def _is_timeout_error(e):
    """判断异常是否为超时错误"""
    error_str = str(e).lower()
    timeout_keywords = ["timed out", "timeout", "deadline exceeded"]
    return any(kw in error_str for kw in timeout_keywords)


def ai_chat_completion_with_retry(ai_client, config, **kwargs):
    """带超时自动重试的 AI 聊天补全调用
    
    Args:
        ai_client: OpenAI 客户端实例
        config: 配置字典
        **kwargs: 传递给 chat.completions.create 的参数
        
    Returns:
        API 响应结果
        
    Raises:
        非超时错误，或重试次数用尽后的超时错误
    """
    max_retries = config["ai_settings"].get('ai_timeout_retry', 0)
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            response = ai_client.chat.completions.create(**kwargs)
            if attempt > 0:
                logger.info(f"AI API 调用成功（第 {attempt + 1} 次尝试）")
            return response
        except Exception as e:
            if _is_timeout_error(e) and attempt < max_retries:
                logger.warning(f"AI API 调用超时，正在进行第 {attempt + 1}/{max_retries} 次重试...")
                last_error = e
                continue
            else:
                raise
    
    # 理论上不会走到这里，兜底
    if last_error:
        raise last_error


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
        http_proxy = config["ai_settings"].get('vit_http_proxy', '')
        https_proxy = config["ai_settings"].get('vit_https_proxy', '')
        if http_proxy or https_proxy:
            import httpx
            mounts = {}
            if http_proxy:
                mounts["http://"] = httpx.HTTPTransport(proxy=http_proxy)
            if https_proxy:
                mounts["https://"] = httpx.HTTPTransport(proxy=https_proxy)
            http_client = httpx.Client(mounts=mounts)
        _vit_clients[client_type] = OpenAI(
            api_key=config["ai_settings"].get('vit_api_key', ''),
            base_url=config["ai_settings"].get('vit_base_url', ''),
            http_client=http_client
        )
    return _vit_clients[client_type]


def analyze_image(image_url, config, client_type="ai", prompt=None):
    """分析单张图片并返回文字描述
    
    Args:
        image_url: 图片URL（支持 http(s) 链接或 data:image/...;base64 数据URL）
        config: 配置字典
        client_type: AI类型（"ai" / "at" / "defined"），用于隔离视觉客户端
        prompt: 自定义分析提示词，不指定时使用配置中的 vit_prompt
        
    Returns:
        图片的文字描述
    """
    if not config["ai_settings"].get('vit_enable', False):
        return L["image_recognition_disabled"]
    
    # 去除URL中的反引号（QQ消息中URL可能被反引号包裹）
    image_url = image_url.strip('`').strip()
    
    if not image_url:
        return L["image_url_empty"]
    
    try:
        vit_client = get_vit_client(config, client_type)
        analysis_prompt = (prompt or "").strip() or config["ai_settings"].get('vit_prompt', '用中文尽可能详细地描述这张图片')
        response = vit_client.chat.completions.create(
            model=config["ai_settings"].get('vit_model', 'gemini-3-flash-preview'),
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    },
                    {
                        "type": "text",
                        "text": analysis_prompt
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
        return L["image_analysis_failed"].format(err=str(e))


def extract_image_descriptions(msg, config, client_type="ai"):
    """从消息中提取所有图片并分析，返回图片描述文本
    
    Args:
        msg: OneBot消息对象
        config: 配置字典
        client_type: AI类型（"ai" / "at" / "defined"），用于隔离视觉客户端
        
    Returns:
        图片描述文本（多张图片用换行分隔），无图片时返回空字符串
    """
    if not config["ai_settings"].get('vit_enable', False):
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


def get_reply_message_text(msg, ws, timeout=3.0, config=None, client_type="ai"):
    """提取消息开头引用的（reply）消息内容

    引用段只出现在消息开头：{"type": "reply", "data": {"id": "..."}}
    通过 get_msg 同步获取被引用的消息，并拼接为可读文本。
    被引用消息中的图片会走视觉模型（vit）生成描述（需传入 config 且 vit_enable 开启）。

    Args:
        msg: OneBot 消息对象（含 message 段数组）
        ws: WebSocket 连接
        timeout: 获取被引用消息的超时时间（秒）
        config: 配置字典（用于 vit 图片分析，传 None 时图片只显示占位符）
        client_type: AI类型（"ai" / "at" / "defined"），用于隔离视觉客户端

    Returns:
        引用内容字符串（如 "[引用消息] 昵称: 内容"），无引用或获取失败时返回 None
    """
    import re
    from feature.messages.manage import get_msg_sync

    message_segments = msg.get('message', [])
    reply_id = None

    if message_segments and message_segments[0].get('type') == 'reply':
        reply_id = message_segments[0].get('data', {}).get('id')
    elif not message_segments:
        # 兜底：从 raw_message 的 CQ 码中提取（raw_message 可能被框架 HTML 转义，先还原）
        raw_message = html.unescape(msg.get('raw_message', ''))
        match = re.match(r'\[CQ:reply,id=(-?\d+)\]', raw_message)
        if match:
            reply_id = match.group(1)

    if reply_id is None:
        return None

    try:
        reply_id = int(reply_id)
    except (ValueError, TypeError):
        return None

    reply_msg = get_msg_sync(ws, reply_id, timeout=timeout)
    if not reply_msg:
        return None

    # 提取被引用消息的内容（文本/图片/表情等）
    vit_enabled = bool(config) and config["ai_settings"].get('vit_enable', False)
    reply_text_parts = []
    for segment in reply_msg.get('message', []):
        seg_type = segment.get('type')
        seg_data = segment.get('data', {})
        if seg_type == 'text' and seg_data.get('text'):
            reply_text_parts.append(seg_data['text'])
        elif seg_type == 'image':
            image_url = seg_data.get('url', '')
            if vit_enabled and image_url:
                description = analyze_image(image_url, config, client_type)
                reply_text_parts.append(f"【图片】{description}【/图片】")
            else:
                file_name = seg_data.get('file', '')
                reply_text_parts.append(f"[图片:{file_name}]" if file_name else '[图片]')
        elif seg_type == 'face':
            reply_text_parts.append('[表情]')

    reply_text = ''.join(reply_text_parts).strip()
    if not reply_text:
        return None

    # 附带被引用消息的发送者信息（昵称 + QQ号）
    sender = reply_msg.get('sender', {}) or {}
    sender_nickname = sender.get('nickname', '未知用户')
    sender_id = sender.get('user_id')
    if sender_id:
        return f"[引用消息] {sender_nickname}(QQ:{sender_id}): {reply_text}"
    return f"[引用消息] {sender_nickname}: {reply_text}"


# AI输入过滤：以下词汇在发送给AI前会被视为空字符串（替换为""）
AI_INPUT_FILTER_WORDS = ("滚木",)


def filter_ai_input(text):
    """过滤发送给AI的用户输入，将过滤词视为空字符串

    Args:
        text: 原始用户输入文本

    Returns:
        过滤后的文本
    """
    if not text:
        return text
    for word in AI_INPUT_FILTER_WORDS:
        text = text.replace(word, "")
    return text


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

# 每个群的AI工具启停设置（仅内存管理，不保存到config，机器人重启后重置）
# 格式: {group_id: {tool_name: {"enabled": bool, "off_feedback": str}}}
group_ai_tool_settings = {}

# 可管理的AI工具名称及其说明
AI_TOOL_NAMES = {
    "dpsk": "DeepSeek 对话 (ex.dpsk)",
    "at": "被@触发的AI对话",
    "defined": "defined 模式对话",
    "mute": "AI禁言/忽略工具",
    "unmute": "AI解除禁言/取消忽略工具",
    "filedir": "AI目录浏览工具",
    "execute_code": "AI代码执行工具",
    "web_fetch": "AI网页访问工具",
    "take_server_screenshot": "AI服务器截图工具",
}


def get_tool_setting(group_id, tool_name):
    """获取某个群某个AI工具的设置，未设置时返回None"""
    return group_ai_tool_settings.get(str(group_id), {}).get(tool_name)


def is_tool_enabled(group_id, tool_name):
    """判断某个群某个AI工具是否启用（默认启用）"""
    setting = get_tool_setting(group_id, tool_name)
    if setting is None:
        return True
    return setting.get("enabled", True)


def get_tool_off_feedback(group_id, tool_name, default_feedback):
    """获取某个群某个AI工具关闭时的反馈文案，未设置反馈时使用默认文案"""
    setting = get_tool_setting(group_id, tool_name)
    if setting:
        feedback = (setting.get("off_feedback") or "").strip()
        if feedback:
            return feedback
    return default_feedback


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
        },
        {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": "访问指定URL的网页，获取网页的文本内容。支持通过代理访问，可以获取网页的HTML或纯文本内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "要访问的网页URL，必须以http://或https://开头"
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "返回内容的最大字符数，默认5000，防止内容过长"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "请求超时时间（秒），默认30秒"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "take_server_screenshot",
                "description": "截取服务器当前画面，并交给视觉模型(Gemini)分析，返回截图内容的文字描述。截图失败（如未接入显示器）或视觉分析不可用时会返回错误信息。仅机器人管理员可使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "对截图内容的分析要求，不指定时使用默认分析提示词"
                        }
                    },
                    "required": []
                }
            }
        }
    ]


def web_fetch_url(tool_args, config):
    """访问指定URL的网页并返回内容
    
    Args:
        tool_args: 工具参数字典，包含 url, max_length, timeout
        config: 配置字典
        
    Returns:
        网页内容字符串
    """
    import requests
    
    url = tool_args.get("url", "").strip()
    max_length = tool_args.get("max_length", 5000)
    timeout = tool_args.get("timeout", 30)
    
    if not url:
        return L["web_fetch_url_empty"]
    
    if not url.startswith(("http://", "https://")):
        return L["web_fetch_url_invalid"]
    
    # 自定义User-Agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0 ReRxBot/2026.8.10"
    
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # 配置代理
    proxies = None
    http_proxy = config["ai_settings"].get('ai_tools_http_proxy', '').strip()
    https_proxy = config["ai_settings"].get('ai_tools_https_proxy', '').strip()
    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
    
    try:
        logger.info(f"web_fetch 正在访问: {url}")
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            timeout=timeout,
            allow_redirects=True
        )
        
        response.raise_for_status()
        
        # 尝试检测编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'
        
        content = response.text
        
        # 尝试提取纯文本（去除HTML标签）
        try:
            # 优先使用 beautifulsoup4 提取纯文本
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # 移除不需要的标签
                for tag in soup(['script', 'style', 'noscript', 'meta', 'head', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                
                # 获取纯文本
                plain_text = soup.get_text(separator='\n', strip=True)
                
                # 清理多余的空行
                lines = [line.strip() for line in plain_text.splitlines() if line.strip()]
                plain_text = '\n'.join(lines)
                
                if plain_text and len(plain_text) > 50:
                    content = plain_text
            except ImportError:
                # 如果没有 beautifulsoup4，使用内置的 HTMLParser
                from html.parser import HTMLParser
                
                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_parts = []
                        self.skip = False
                        self.skip_tags = {'script', 'style', 'noscript', 'meta', 'head'}
                    
                    def handle_starttag(self, tag, attrs):
                        if tag.lower() in self.skip_tags:
                            self.skip = True
                    
                    def handle_endtag(self, tag):
                        if tag.lower() in self.skip_tags:
                            self.skip = False
                    
                    def handle_data(self, data):
                        if not self.skip:
                            text = data.strip()
                            if text:
                                self.text_parts.append(text)
                
                extractor = TextExtractor()
                extractor.feed(content)
                plain_text = '\n'.join(extractor.text_parts)
                
                if plain_text and len(plain_text) > 50:
                    content = plain_text
        except Exception:
            # 如果纯文本提取失败，返回原始内容
            pass
        
        # 限制返回内容长度
        if len(content) > max_length:
            content = content[:max_length] + L["web_fetch_truncated"].format(length=len(response.text))
        
        logger.info(f"web_fetch 访问成功，返回内容长度: {len(content)} 字符")
        return content
    
    except requests.exceptions.ProxyError as e:
        logger.error(f"web_fetch 代理错误: {e}")
        return L["web_fetch_proxy_error"].format(err=str(e))
    except requests.exceptions.Timeout:
        logger.error(f"web_fetch 请求超时: {url}")
        return L["web_fetch_timeout"].format(seconds=timeout)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"web_fetch 连接错误: {e}")
        return L["web_fetch_conn_error"].format(err=str(e))
    except requests.exceptions.HTTPError as e:
        logger.error(f"web_fetch HTTP错误: {e}")
        return L["web_fetch_http_error"].format(err=str(e))
    except requests.exceptions.RequestException as e:
        logger.error(f"web_fetch 请求异常: {e}")
        return L["web_fetch_request_failed"].format(err=str(e))
    except Exception as e:
        logger.error(f"web_fetch 未知错误: {e}")
        return L["web_fetch_unknown_error"].format(err=str(e))


# ============ blacklist_files 文件访问保护 ============

# 注入到AI执行代码前的Hook源码（在子进程中自包含运行，不依赖本模块）
# 占位符 __BLACKLIST__ / __MODULE_BASES__ 在 build_blacklist_hook 中替换为实际的标准化列表
_BLACKLIST_HOOK_SRC = """\
# ===== blacklist_files 文件访问保护（由机器人自动注入） =====
import builtins as _b
import io as _io
import os as _os
import glob as _glob


def _install_blx_guard(blacklist, module_bases):
    def _blx_norm(p):
        try:
            p = _os.fsdecode(p)
        except Exception:
            p = str(p)
        return p.replace("\\\\", "/").strip().lower()

    def _blx_hit(path):
        n = _blx_norm(path)
        base = n.rsplit("/", 1)[-1]
        return n in blacklist or base in blacklist

    def _blx_deny(path, op):
        if _blx_hit(path):
            raise PermissionError(
                f"[blacklist_files] 禁止访问黑名单文件 {path!r}（{op}）")

    _orig_open = _b.open

    def _safe_open(file, *args, **kwargs):
        if isinstance(file, (str, bytes, _os.PathLike)):
            _blx_deny(file, "open")
        return _orig_open(file, *args, **kwargs)

    _b.open = _safe_open
    _io.open = _safe_open

    _orig_open_code = _io.open_code

    def _safe_open_code(path, *args, **kwargs):
        _blx_deny(path, "open_code")
        return _orig_open_code(path, *args, **kwargs)

    _io.open_code = _safe_open_code

    _orig_os_open = _os.open

    def _safe_os_open(path, *args, **kwargs):
        _blx_deny(path, "os.open")
        return _orig_os_open(path, *args, **kwargs)

    _os.open = _safe_os_open

    _orig_remove = _os.remove

    def _safe_remove(path, *args, **kwargs):
        _blx_deny(path, "remove")
        return _orig_remove(path, *args, **kwargs)

    _os.remove = _safe_remove

    _orig_unlink = _os.unlink

    def _safe_unlink(path, *args, **kwargs):
        _blx_deny(path, "unlink")
        return _orig_unlink(path, *args, **kwargs)

    _os.unlink = _safe_unlink

    _orig_rename = _os.rename

    def _safe_rename(src, dst, *args, **kwargs):
        _blx_deny(src, "rename")
        _blx_deny(dst, "rename")
        return _orig_rename(src, dst, *args, **kwargs)

    _os.rename = _safe_rename

    _orig_replace = _os.replace

    def _safe_replace(src, dst, *args, **kwargs):
        _blx_deny(src, "replace")
        _blx_deny(dst, "replace")
        return _orig_replace(src, dst, *args, **kwargs)

    _os.replace = _safe_replace

    _orig_stat = _os.stat

    def _safe_stat(path, *args, **kwargs):
        _blx_deny(path, "stat")
        return _orig_stat(path, *args, **kwargs)

    _os.stat = _safe_stat

    _orig_lstat = _os.lstat

    def _safe_lstat(path, *args, **kwargs):
        _blx_deny(path, "lstat")
        return _orig_lstat(path, *args, **kwargs)

    _os.lstat = _safe_lstat

    # Python 3.13+ 的 os.path 探测/元数据函数走C实现，绕过 os.stat 的hook，
    # 需要逐一包装：探测类对外表现为"不存在"，元数据类直接拒绝
    _osp = _os.path
    for _fname in ("exists", "lexists", "isfile", "isdir", "islink",
                   "ismount", "isjunction"):
        _orig_pf = getattr(_osp, _fname, None)
        if _orig_pf is None:
            continue

        def _safe_probe(path, *args, _orig_pf=_orig_pf, _fname=_fname, **kwargs):
            if _blx_hit(path):
                return False
            return _orig_pf(path, *args, **kwargs)

        setattr(_osp, _fname, _safe_probe)

    for _fname in ("getsize", "getmtime", "getatime", "getctime", "realpath"):
        _orig_pf = getattr(_osp, _fname, None)
        if _orig_pf is None:
            continue

        def _safe_meta(path, *args, _orig_pf=_orig_pf, _fname=_fname, **kwargs):
            _blx_deny(path, "os.path." + _fname)
            return _orig_pf(path, *args, **kwargs)

        setattr(_osp, _fname, _safe_meta)

    _orig_listdir = _os.listdir

    def _safe_listdir(path=".", *args, **kwargs):
        items = _orig_listdir(path, *args, **kwargs)
        return [it for it in items
                if not _blx_hit(it)
                and not _blx_hit(_os.path.join(path, it))]

    _os.listdir = _safe_listdir

    _orig_scandir = _os.scandir

    class _FilteredScandir:
        # 同时支持迭代与 with 上下文管理（os.walk/glob 内部使用 with scandir）

        def __init__(self, gen):
            self._gen = gen

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._gen)

        def close(self):
            close_fn = getattr(self._gen, "close", None)
            if close_fn is not None:
                close_fn()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()

    def _safe_scandir(path=".", *args, **kwargs):
        def _gen():
            for entry in _orig_scandir(path, *args, **kwargs):
                if _blx_hit(entry.name) or _blx_hit(
                        _os.path.join(path, entry.name)):
                    continue
                yield entry

        return _FilteredScandir(_gen())

    _os.scandir = _safe_scandir

    _orig_glob = _glob.glob

    def _safe_glob(pathname, *args, **kwargs):
        return [p for p in _orig_glob(pathname, *args, **kwargs)
                if not _blx_hit(p)]

    _glob.glob = _safe_glob

    _orig_iglob = _glob.iglob

    def _safe_iglob(pathname, *args, **kwargs):
        for p in _orig_iglob(pathname, *args, **kwargs):
            if not _blx_hit(p):
                yield p

    _glob.iglob = _safe_iglob

    _orig_import = _b.__import__

    def _safe_import(name, *args, **kwargs):
        if name.split(".")[0].lower() in module_bases:
            raise PermissionError(
                f"[blacklist_files] 禁止导入黑名单模块 {name!r}")
        return _orig_import(name, *args, **kwargs)

    _b.__import__ = _safe_import


_install_blx_guard(__BLACKLIST__, __MODULE_BASES__)
del _install_blx_guard
"""


def _get_blacklist_norm(config):
    """读取配置中的 blacklist_files 并标准化（小写、正斜杠、去空白）"""
    blacklist = config["ai_settings"].get('blacklist_files', []) or []
    blacklist_norm = set()
    for entry in blacklist:
        entry = str(entry).replace("\\", "/").strip().lower()
        if entry:
            blacklist_norm.add(entry)
    return blacklist_norm


def _is_blacklisted(path, blacklist_norm):
    """判断路径是否命中黑名单（按完整路径或文件名匹配，大小写不敏感）

    Args:
        path: 文件路径或文件名
        blacklist_norm: _get_blacklist_norm 返回的标准化黑名单集合
    """
    norm = str(path).replace("\\", "/").strip().lower()
    base = norm.rsplit("/", 1)[-1]
    return norm in blacklist_norm or base in blacklist_norm


def build_blacklist_hook(blacklist):
    """构造注入到AI代码执行前的文件访问保护Hook源码

    Args:
        blacklist: blacklist_files 配置项（文件名字符串列表）

    Returns:
        Hook源码字符串；未配置黑名单时返回空字符串
    """
    blacklist_norm = set()
    module_bases = set()
    for entry in blacklist or []:
        entry = str(entry).replace("\\", "/").strip().lower()
        if not entry:
            continue
        blacklist_norm.add(entry)
        base = entry.rsplit("/", 1)[-1]
        if "." in base:
            base = base.rsplit(".", 1)[0]
        module_bases.add(base)
    if not blacklist_norm:
        return ""
    return _BLACKLIST_HOOK_SRC.replace(
        "__BLACKLIST__", repr(sorted(blacklist_norm))
    ).replace(
        "__MODULE_BASES__", repr(sorted(module_bases))
    )


def execute_tool_call(ws, group_id, tool_name, tool_args, user_id):
    """执行工具调用"""
    from feature.group_manage.ban import set_group_ban
    import builtins
    
    try:
        # 检查该AI工具是否在本群被关闭（由 ex.dpsk.set 设置，仅内存生效）
        if not is_tool_enabled(group_id, tool_name):
            feedback = get_tool_off_feedback(group_id, tool_name, L["tool_disabled_feedback"].format(tool=tool_name))
            logger.info(f"AI工具 {tool_name} 在本群 {group_id} 已关闭，返回反馈")
            return L["tool_disabled_feedback"].format(tool=tool_name) + "：" + feedback
        
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
                return L["mute_success"].format(uid=target_id, duration=duration)
            else:
                if group_id not in ignored_users:
                    ignored_users[group_id] = set()
                ignored_users[group_id].add(target_id)
                logger.info(f"执行工具 {tool_name} 成功: 在非机器人群 {group_id} 忽略用户 {target_id}")
                return L["ignore_success"].format(uid=target_id)
        
        elif tool_name == "unmute":
            target_id = tool_args.get("user_id", user_id)
            if group_id == builtins.config.get("bot_group"):
                set_group_ban(ws, group_id, target_id, 0)
                logger.info(f"执行工具 {tool_name} 成功: 解除禁言用户 {target_id}")
                return L["unmute_success"].format(uid=target_id)
            else:
                if group_id in ignored_users and target_id in ignored_users[group_id]:
                    ignored_users[group_id].discard(target_id)
                    logger.info(f"执行工具 {tool_name} 成功: 取消忽略用户 {target_id}")
                    return L["unignore_success"].format(uid=target_id)
                else:
                    return L["not_ignored"].format(uid=target_id)
        
        elif tool_name == "filedir":
            path = tool_args.get("path", ".")
            if not os.path.exists(path):
                return L["path_not_found"].format(path=path)
            
            try:
                items = os.listdir(path)
                blacklist_norm = _get_blacklist_norm(builtins.config)
                result_lines = [L["filedir_header"].format(path=path)]
                for item in items:
                    # 过滤 blacklist_files 黑名单文件，不让AI发现它们
                    if blacklist_norm and _is_blacklisted(item, blacklist_norm):
                        continue
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        result_lines.append(f"📁 {item}/")
                    else:
                        result_lines.append(f"📄 {item}")
                return "\n".join(result_lines)
            except PermissionError:
                return L["filedir_no_permission"].format(path=path)
            except Exception as e:
                return L["filedir_failed"].format(err=str(e))
        
        elif tool_name == "execute_code":
            # 鉴权：非管理员直接拒绝，不弹窗
            if user_id not in builtins.config["bot_admin_ids"]:
                logger.warning(f"执行工具 {tool_name} 失败: 用户 {user_id} 无权限（非管理员）")
                return L["exec_code_permission_denied"]
            
            code = tool_args.get("code", "")
            if not code:
                return L["code_empty"]

            # 纵深防御：代码文本中引用 blacklist_files 黑名单文件名时直接拒绝
            blacklist_norm = _get_blacklist_norm(builtins.config)
            if blacklist_norm:
                code_lower = code.lower()
                hit_entries = sorted(
                    e for e in blacklist_norm
                    if e in code_lower or e.rsplit("/", 1)[-1] in code_lower)
                if hit_entries:
                    logger.warning(
                        f"执行工具 execute_code 失败: 代码引用了blacklist_files黑名单文件 {hit_entries}")
                    return L["code_blacklist_refused"].format(files=', '.join(hit_entries))
            
            approved, final_code, timed_out, extra_content = review_and_execute_code(code)
            
            if timed_out:
                logger.warning(f"执行工具 {tool_name}: 代码审核超时（30秒未操作）")
                return L["code_review_timeout"]
            
            if not approved:
                logger.info(f"执行工具 {tool_name}: 代码审核被拒绝")
                reject_msg = L["code_review_rejected"]
                if extra_content:
                    reject_msg = reject_msg + "\n\n" + L["extra_content_marker"] + "\n" + extra_content
                return reject_msg
            
            logger.info(f"执行工具 {tool_name}: 代码审核通过，开始执行")
            result = execute_python_code(final_code)
            logger.info(f"执行工具 {tool_name}: 代码执行完成")
            
            if extra_content:
                result = result + "\n\n" + L["extra_content_marker"] + "\n" + extra_content
            return result
        
        elif tool_name == "web_fetch":
            return web_fetch_url(tool_args, builtins.config)
        
        elif tool_name == "take_server_screenshot":
            # 鉴权：非管理员直接拒绝（与 execute_code / peekserver 一致）
            if user_id not in builtins.config["bot_admin_ids"]:
                logger.warning(f"执行工具 {tool_name} 失败: 用户 {user_id} 无权限（非管理员）")
                return L["screenshot_tool_permission_denied"]
            
            # 截取服务器画面（含错误反馈：未接入显示器/无桌面会话等）
            import io as _io
            import base64 as _base64
            try:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
            except Exception as e:
                logger.error(f"执行工具 {tool_name} 截图失败: {e}")
                return L["screenshot_tool_failed"].format(err=str(e))
            
            # 编码为 base64 数据URL
            try:
                img_bytes = _io.BytesIO()
                screenshot.save(img_bytes, format='PNG')
                base64_str = _base64.b64encode(img_bytes.getvalue()).decode('utf-8')
                data_url = f"data:image/png;base64,{base64_str}"
            except Exception as e:
                logger.error(f"执行工具 {tool_name} 图片编码失败: {e}")
                return L["screenshot_tool_failed"].format(err=str(e))
            
            # 交给视觉模型(Gemini)分析
            custom_prompt = tool_args.get("prompt", "")
            description = analyze_image(data_url, builtins.config, "ai", prompt=custom_prompt)
            logger.info(f"执行工具 {tool_name} 完成，分析结果长度: {len(description)}")
            return L["screenshot_tool_result"].format(result=description)
        
        else:
            logger.warning(f"执行工具 {tool_name} 失败: 未知工具")
            return f"Unknown Tool"
    
    except Exception as e:
        logger.error(f"执行工具 {tool_name} 失败: {e}")
        return L["tool_exec_failed"].format(tool=tool_name, err=str(e))


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
        python_exec = builtins.config["ai_settings"].get('ai_python_exec', '').strip()
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

        # 注入 blacklist_files 文件访问保护Hook（在子进程中拦截文件API）
        blacklist = builtins.config["ai_settings"].get('blacklist_files', []) or []
        hook = build_blacklist_hook(blacklist)
        final_code = (hook + "\n\n" + code) if hook else code

        # 使用子进程执行代码
        # UTF-8 编码：避免子进程输出非 GBK 字符（如 emoji、伪本地化字符）时抛 UnicodeEncodeError
        proc = subprocess.run(
            [python_exec, '-c', final_code],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
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
            result = L["code_exec_no_output"]

        return result

    except subprocess.TimeoutExpired:
        return L["code_exec_timeout"]
    except Exception as e:
        tb = traceback.format_exc()
        return L["code_exec_error"].format(tb=tb)


def process_tool_calls(ws, group_id, message, user_id, ai_client, conversation_history):
    """处理AI的工具调用"""
    from feature.messages.send import send_group_msg
    
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
    from feature.messages.manage import get_message_text
    from feature.messages.send import send_group_msg
    from feature.messages.forward import send_group_msg_forward_segmented, send_group_single_forward_msg, send_group_msg_ai_segmented, clean_ai_segment_markers
    
    user_input = get_message_text(msg)[len("defined "):]
    user_id = msg.get('sender', {}).get('user_id')
    nickname = msg.get('sender', {}).get('nickname')
    message_id = msg.get('message_id')  # 获取消息ID
    
    # 提取并分析图片
    image_content = extract_image_descriptions(msg, config, client_type="defined")
    if image_content:
        user_input = f"{user_input}\n{image_content}" if user_input.strip() else image_content
    
    # 提取引用消息内容（引用只会出现在消息开头，引用的图片走vit）
    reply_content = get_reply_message_text(msg, ws, config=config, client_type="defined")
    if reply_content:
        user_input = f"{reply_content}\n{user_input}" if user_input.strip() else reply_content
    
    # 过滤AI输入（过滤词视为空字符串，如"滚木"）
    user_input = filter_ai_input(user_input)
    
    # 构建额外的提示信息
    ai_append_words = f"当前提问者QQ号为{user_id} | 提问者名字为{nickname} | bot管理员是{config['bot_admin_ids']}"
    
    # 获取或初始化该群的历史消息
    if group_id not in defined_conversation_history:
        # 使用配置中defined对应的规则文件
        rules_defined = config["ai_settings"].get('rules_defined', {})
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
        # 调用 AI API（带超时重试）
        response = ai_chat_completion_with_retry(
            ai_client, config,
            model=config["ai_settings"]['ai_model'],
            messages=defined_conversation_history[group_id],
            tools=get_available_tools(),
            tool_choice="auto",
            stream=False
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用（如果需要）—— 所有群均启用工具调用
        if config["ai_settings"].get('ai_owner_group_future_mode', False):
            while process_tool_calls(ws, group_id, assistant_message, user_id, ai_client, defined_conversation_history[group_id]):
                response = ai_chat_completion_with_retry(
                    ai_client, config,
                    model=config["ai_settings"]['ai_model'],
                    messages=defined_conversation_history[group_id],
                    tools=get_available_tools(),
                    tool_choice="auto",
                    stream=False
                )
                assistant_message = response.choices[0].message
        
        # 获取最终回复
        assistant_reply = (assistant_message.content or "").lstrip('\n')
        
        # 将助手的回复添加到历史（去除AI分段标记）
        if assistant_message.content:
            defined_conversation_history[group_id].append({"role": "assistant", "content": clean_ai_segment_markers(assistant_reply)})
        
        # 发送回复：由AI自己决定分段，分段时以合并转发发送,不添加回复和@
        if assistant_reply:
            if not send_group_msg_ai_segmented(ws, group_id, assistant_reply, self_id, L["forward_name_defined"]):
                # 普通消息,添加回复和@,关闭auto_escape
                reply_message = f"[CQ:reply,id={message_id}][CQ:at,qq={user_id}] {assistant_reply}"
                send_group_msg(ws, group_id, reply_message, auto_escape=False)
    
    except Exception as e:
        error_msg = L["defined_api_error"].format(err=str(e))
        logger.error(error_msg)
        send_group_single_forward_msg(ws, group_id, self_id, L["defined_error_node_name"], error_msg)
        if group_id in defined_conversation_history and defined_conversation_history[group_id][-1]["role"] == "user":
            defined_conversation_history[group_id].pop()
    finally:
        if group_id in defined_threads:
            del defined_threads[group_id]


def ai_worker(ws, group_id, msg, config, ai_client, self_id, ai_manager):
    """处理AI对话的工作线程"""
    from feature.messages.manage import get_message_text
    from feature.messages.send import send_group_msg
    from feature.messages.forward import send_group_msg_forward_segmented, send_group_single_forward_msg, send_group_msg_ai_segmented, clean_ai_segment_markers
    import datetime

    user_input = get_message_text(msg)[len(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']} "):]
    user_id = msg.get('sender', {}).get('user_id')
    nickname = msg.get('sender', {}).get('nickname')
    
    # 提取并分析图片
    image_content = extract_image_descriptions(msg, config, client_type="ai")
    if image_content:
        user_input = f"{user_input}\n{image_content}" if user_input.strip() else image_content
    
    # 提取引用消息内容（引用只会出现在消息开头，引用的图片走vit）
    reply_content = get_reply_message_text(msg, ws, config=config, client_type="ai")
    if reply_content:
        user_input = f"{reply_content}\n{user_input}" if user_input.strip() else reply_content
    
    # 过滤AI输入（过滤词视为空字符串，如"滚木"）
    user_input = filter_ai_input(user_input)
    
    # 构建额外的提示信息
    ai_append_words = f"当前提问者QQ号为{user_id} | 提问者名字为{nickname} | bot管理员是{config['bot_admin_ids']} | 当前时间是{datetime.datetime.now()}"
    
    # 获取或初始化该群的历史消息
    if group_id not in ai_conversation_history:
        # 使用配置中normal对应的规则文件
        rules_defined = config["ai_settings"].get('rules_defined', {})
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
        # 第一次调用AI API（带超时重试）
        response = ai_chat_completion_with_retry(
            ai_client, config,
            model=config["ai_settings"]['ai_model'],
            messages=ai_conversation_history[group_id],
            tools=get_available_tools(),
            tool_choice="auto",
            stream=False
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用（如果需要）—— 所有群均启用工具调用
        if config["ai_settings"].get('ai_owner_group_future_mode', False):
            while process_tool_calls(ws, group_id, assistant_message, user_id, ai_client, ai_conversation_history[group_id]):
                # AI执行了工具调用，需要再次调用AI获取最终回复
                response = ai_chat_completion_with_retry(
                    ai_client, config,
                    model=config["ai_settings"]['ai_model'],
                    messages=ai_conversation_history[group_id],
                    tools=get_available_tools(),
                    tool_choice="auto",
                    stream=False
                )
                assistant_message = response.choices[0].message
        
        # 获取最终回复
        assistant_reply = (assistant_message.content or "").lstrip('\n')
        
        # 将助手的回复添加到历史（去除AI分段标记）
        if assistant_message.content:
            ai_conversation_history[group_id].append({"role": "assistant", "content": clean_ai_segment_markers(assistant_reply)})
        
        # 发送回复：由AI自己决定分段，分段时以合并转发发送
        if assistant_reply:
            if not send_group_msg_ai_segmented(ws, group_id, assistant_reply, self_id,
                                               config["ai_settings"]['ai_name'],
                                               footer="\n\n" + L["ai_disclaimer"]):
                send_group_msg(ws, group_id, assistant_reply + "\n\n" + L["ai_disclaimer"])
    
    except Exception as e:
        error_msg = L["ai_api_error"].format(ai_name=config['ai_settings']['ai_name'], err=str(e))
        logger.error(error_msg)
        send_group_single_forward_msg(ws, group_id, self_id, L["ai_error_node_name"].format(ai_name=config['ai_settings']['ai_name']), error_msg)
        if group_id in ai_conversation_history and ai_conversation_history[group_id][-1]["role"] == "user":
            ai_conversation_history[group_id].pop()
    finally:
        if group_id in ai_threads:
            del ai_threads[group_id]


def at_ai_worker(ws, group_id, user_input, original_msg, config, ai_client, self_id, ai_manager):
    """处理@触发的AI对话的工作线程"""
    from feature.messages.send import send_group_msg
    from feature.messages.forward import send_group_msg_forward_segmented, send_group_single_forward_msg, send_group_msg_ai_segmented, clean_ai_segment_markers
    import datetime
    
    user_id = original_msg.get('sender', {}).get('user_id')
    nickname = original_msg.get('sender', {}).get('nickname')
    
    # 提取并分析图片
    image_content = extract_image_descriptions(original_msg, config, client_type="at")
    if image_content:
        user_input = f"{user_input}\n{image_content}" if user_input.strip() else image_content
    
    # 提取引用消息内容（引用只会出现在消息开头，引用的图片走vit）
    reply_content = get_reply_message_text(original_msg, ws, config=config, client_type="at")
    if reply_content:
        user_input = f"{reply_content}\n{user_input}" if user_input.strip() else reply_content
    
    # 过滤AI输入（过滤词视为空字符串，如"滚木"）
    user_input = filter_ai_input(user_input)
    
    ai_append_words = f"当前提问者QQ号为{user_id} | 提问者名字为{nickname} | bot管理员是{config['bot_admin_ids']} | 当前时间是{datetime.datetime.now()}"
    
    if group_id not in at_ai_conversation_history:
        # 使用配置中at对应的规则文件
        rules_defined = config["ai_settings"].get('rules_defined', {})
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
        response = ai_chat_completion_with_retry(
            ai_client, config,
            model=config["ai_settings"]['ai_model'],
            messages=at_ai_conversation_history[group_id],
            tools=get_available_tools(),
            tool_choice="auto",
            stream=False
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用 —— 所有群均启用工具调用
        if config["ai_settings"].get('ai_owner_group_future_mode', False):
            while process_tool_calls(ws, group_id, assistant_message, user_id, ai_client, at_ai_conversation_history[group_id]):
                response = ai_chat_completion_with_retry(
                    ai_client, config,
                    model=config["ai_settings"]['ai_model'],
                    messages=at_ai_conversation_history[group_id],
                    tools=get_available_tools(),
                    tool_choice="auto",
                    stream=False
                )
                assistant_message = response.choices[0].message
        
        assistant_reply = (assistant_message.content or "").lstrip('\n')
        
        if assistant_message.content:
            at_ai_conversation_history[group_id].append({"role": "assistant", "content": clean_ai_segment_markers(assistant_reply)})
        
        # 发送回复：由AI自己决定分段，分段时以合并转发发送
        if assistant_reply:
            if not send_group_msg_ai_segmented(ws, group_id, assistant_reply, self_id,
                                               config["ai_settings"]['ai_name'],
                                               footer="\n\n" + L["ai_disclaimer"]):
                send_group_msg(ws, group_id, assistant_reply + "\n\n" + L["ai_disclaimer"])
    
    except Exception as e:
        error_msg = L["ai_api_error"].format(ai_name=config['ai_settings']['ai_name'], err=str(e))
        logger.error(error_msg)
        send_group_single_forward_msg(ws, group_id, self_id, L["ai_error_node_name"].format(ai_name=config['ai_settings']['ai_name']), error_msg)
        if group_id in at_ai_conversation_history and at_ai_conversation_history[group_id][-1]["role"] == "user":
            at_ai_conversation_history[group_id].pop()
    finally:
        if group_id in at_ai_threads:
            del at_ai_threads[group_id]


def handle_ai_tool_set(ws, group_id, raw_message, config, user_id):
    """处理 ex.dpsk.set 命令：设置本群AI工具启停状态

    设置仅保存在内存中，不写入config，机器人重启后重置。
    用法:
        ex.dpsk.set <工具名> on                  （启用工具，无需关闭反馈）
        ex.dpsk.set <工具名> off [关闭反馈]      （关闭工具，可指定关闭反馈文案）
        ex.dpsk.set list                         （查看本群工具状态）
    """
    from feature.messages.send import send_group_msg

    prefix = f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.set"
    arg_str = raw_message[len(prefix):].strip()

    # 非管理员拒绝
    if user_id not in config.get("bot_admin_ids", []):
        send_group_msg(ws, group_id, L["tool_set_permission_denied"], True)
        return

    # 查看本群工具状态
    if not arg_str or arg_str.lower() in ("list", "status"):
        lines = [L["tool_status_header"]]
        group_settings = group_ai_tool_settings.get(str(group_id), {})
        if not group_settings:
            lines.append(L["tool_status_all_default"])
        else:
            for tool_name in AI_TOOL_NAMES:
                setting = group_settings.get(tool_name)
                if setting is None:
                    lines.append("  " + tool_name + ": " + L["tool_enabled_state"])
                else:
                    state = L["tool_enabled_state"] if setting.get("enabled", True) else L["tool_disabled_state"]
                    feedback = setting.get("off_feedback", "")
                    lines.append("  " + tool_name + ": " + state + (L["tool_feedback_suffix"].format(feedback=feedback) if feedback else ""))
        send_group_msg(ws, group_id, "\n".join(lines), True)
        return

    # 解析参数: 工具名 状态 [关闭反馈]
    args = arg_str.split(" ", 2)
    tool_name = args[0].strip().lower()
    status = args[1].strip().lower() if len(args) > 1 else ""
    feedback = args[2].strip() if len(args) > 2 else ""

    # 校验工具名
    if tool_name not in AI_TOOL_NAMES:
        send_group_msg(ws, group_id,
                       L["tool_unknown"].format(tool=tool_name, tools=', '.join(AI_TOOL_NAMES.keys())), True)
        return

    # 校验状态
    if status not in ("on", "off"):
        send_group_msg(ws, group_id,
                       L["tool_status_invalid"], True)
        return

    # 写入内存（不保存到config）
    group_settings = group_ai_tool_settings.setdefault(str(group_id), {})
    if status == "on":
        # 切换到on状态不需要关闭反馈，同时清空之前的反馈文案
        group_settings[tool_name] = {"enabled": True, "off_feedback": ""}
        send_group_msg(ws, group_id, L["tool_enabled"].format(tool=tool_name), True)
    else:
        group_settings[tool_name] = {"enabled": False, "off_feedback": feedback}
        reply = L["tool_disabled"].format(tool=tool_name)
        if feedback:
            reply += L["tool_off_feedback"].format(feedback=feedback)
        send_group_msg(ws, group_id, reply, True)

    logger.info(f"群 {group_id} 设置AI工具 {tool_name} = {status}（关闭反馈: {feedback}）")


def _get_rule_file(config, memory_type="normal"):
    """根据配置获取指定对话类型对应的规则文件名（与各 worker 保持一致）"""
    rules_defined = config["ai_settings"].get('rules_defined', {})
    if memory_type == "at":
        return rules_defined.get('at', 'default.txt')
    if memory_type == "defined":
        return rules_defined.get('defined', 'defined.txt')
    return rules_defined.get('normal', 'default.txt')


def _refresh_loaded_system_prompt(history, config, ai_manager, memory_type="normal"):
    """刷新恢复的记忆中的系统提示为当前配置的规则内容，确保规则文件修改后能生效"""
    if not ai_manager or not history or not history[0] or history[0].get("role") != "system":
        return
    rule_file = _get_rule_file(config, memory_type)
    system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
    if not system_prompt:
        return
    history[0]["content"] = f"{system_prompt}\n\n\n额外规则：用户说的话后面的括号由程序添加，你必须遵循"


def handle_ai_commands(ws, raw_message, group_id, msg, config, ai_client, self_id, 
                       is_at_me, at_full_text, ai_manager):
    """处理AI相关的命令"""
    from feature.messages.send import send_group_msg
    
    user_id = msg.get('sender', {}).get('user_id')
    
    # ex.dpsk.set：设置本群AI工具启停状态（仅内存生效，不保存到config）
    if raw_message.startswith(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.set"):
        handle_ai_tool_set(ws, group_id, raw_message, config, user_id)
        return
    
    # bot_disable_settings: ai_enabled = False 时禁用AI，不回复（什么也不做，也不发消息）
    group_settings = config.get("bot_disable_settings", {}).get("group_settings", {}).get(str(group_id), {})
    if not group_settings.get("ai_enabled", True):
        return
    
    # 检查该用户是否被AI忽略（非机器人群中mute等效为忽略，AI不再接收其消息）
    # 机器人管理员不受忽略限制
    if user_id and user_id in ignored_users.get(group_id, set()) and user_id not in config.get('bot_admin_ids', []):
        return
    
    # 处理defined命令(使用defined.txt提示词)
    if raw_message.startswith("defined "):
        if not is_tool_enabled(group_id, "defined"):
            feedback = get_tool_off_feedback(group_id, "defined", L["defined_disabled_feedback"])
            send_group_msg(ws, group_id, feedback, True)
            return
        if group_id in defined_threads and defined_threads[group_id].is_alive():
            send_group_msg(ws, group_id, L["defined_busy"], True)
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
    elif raw_message.startswith(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']} "):
        if not is_tool_enabled(group_id, "dpsk"):
            feedback = get_tool_off_feedback(group_id, "dpsk", L["ai_disabled_feedback"].format(ai_name=config['ai_settings']['ai_name']))
            send_group_msg(ws, group_id, feedback, True)
            return
        if group_id in ai_threads and ai_threads[group_id].is_alive():
            send_group_msg(ws, group_id, L["ai_busy"].format(ai_name=config['ai_settings']['ai_name']), True)
        else:
            send_group_msg(ws, group_id, L["ai_processing"], True)
            thread = threading.Thread(
                target=ai_worker,
                args=(ws, group_id, msg, config, ai_client, self_id, ai_manager)
            )
            ai_threads[group_id] = thread
            thread.start()
    
    elif raw_message == f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.reset":
        if group_id in ai_conversation_history:
            # 使用配置中normal对应的规则文件（与ai_worker保持一致，避免回落到default.txt）
            rule_file = _get_rule_file(config, "normal")
            system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
            ai_conversation_history[group_id] = [{"role": "system", "content": system_prompt}]
            send_group_msg(ws, group_id, L["ai_reset_done"].format(ai_name=config['ai_settings']['ai_name']), True)
        else:
            send_group_msg(ws, group_id, L["ai_reset_none"].format(ai_name=config['ai_settings']['ai_name']), True)
    
    elif is_at_me and (at_full_text or any(seg.get("type") == "image" for seg in msg.get("message", []))):
        if config["ai_settings"].get('at_ai_enable', False):
            if not is_tool_enabled(group_id, "at"):
                feedback = get_tool_off_feedback(group_id, "at", L["at_ai_disabled_feedback"].format(ai_name=config['ai_settings']['ai_name']))
                send_group_msg(ws, group_id, feedback, True)
                return
            if group_id in at_ai_threads and at_ai_threads[group_id].is_alive():
                send_group_msg(ws, group_id, L["at_ai_busy"].format(ai_name=config['ai_settings']['ai_name']), True)
            else:
                thread = threading.Thread(
                    target=at_ai_worker,
                    args=(ws, group_id, at_full_text, msg, config, ai_client, self_id, ai_manager)
                )
                at_ai_threads[group_id] = thread
                thread.start()
    
    elif raw_message == f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.at.reset":
        if group_id in at_ai_conversation_history:
            # 使用配置中at对应的规则文件（与at_ai_worker保持一致，避免回落到default.txt）
            rule_file = _get_rule_file(config, "at")
            system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
            at_ai_conversation_history[group_id] = [{"role": "system", "content": system_prompt}]
            send_group_msg(ws, group_id, L["at_ai_reset_done"].format(ai_name=config['ai_settings']['ai_name']), True)
        else:
            send_group_msg(ws, group_id, L["at_ai_reset_none"].format(ai_name=config['ai_settings']['ai_name']), True)
    
    elif raw_message == f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.defined.reset":
        if group_id in defined_conversation_history:
            # 使用配置中defined对应的规则文件
            rules_defined = config["ai_settings"].get('rules_defined', {})
            rule_file = rules_defined.get('defined', 'defined.txt')
            system_prompt = ai_manager.get_rule(rule_file.replace('.txt', ''))
            defined_conversation_history[group_id] = [{"role": "system", "content": system_prompt}]
            send_group_msg(ws, group_id, L["defined_reset_done"], True)
        else:
            send_group_msg(ws, group_id, L["defined_reset_none"], True)
    
    elif raw_message.startswith(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.save "):
        # 保存AI记忆 ex.dpsk.save 记忆名称
        memory_name = raw_message[len(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.save "):].strip()
        if memory_name:
            success, result = save_group_memory(group_id, memory_name, config["ai_settings"].get('ai_memory_dir', 'ai_memory'), config=config)
            if success:
                send_group_msg(ws, group_id, L["memory_save_done"].format(ai_name=config['ai_settings']['ai_name'], result=result), True)
            else:
                send_group_msg(ws, group_id, L["memory_save_failed"].format(ai_name=config['ai_settings']['ai_name'], result=result), True)
        else:
            send_group_msg(ws, group_id, L["memory_name_required"].format(example=config['command_prefix'] + config['ai_settings']['ai_shortname'] + ".save my_memory"), True)
    
    elif raw_message.startswith(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.load "):
        # 加载AI记忆 ex.dpsk.load 记忆名称
        memory_name = raw_message[len(f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.load "):].strip()
        if memory_name:
            success, result = load_group_memory(group_id, memory_name, config["ai_settings"].get('ai_memory_dir', 'ai_memory'), config=config)
            if success:
                send_group_msg(ws, group_id, L["memory_load_done"].format(ai_name=config['ai_settings']['ai_name'], result=result), True)
            else:
                send_group_msg(ws, group_id, L["memory_load_failed"].format(ai_name=config['ai_settings']['ai_name'], result=result), True)
        else:
            send_group_msg(ws, group_id, L["memory_name_required"].format(example=config['command_prefix'] + config['ai_settings']['ai_shortname'] + ".load my_memory"), True)
    
    elif raw_message == f"{config['command_prefix']}{config['ai_settings']['ai_shortname']}.list":
        # 列出当前群的记忆列表
        memories = list_group_memories(group_id, config["ai_settings"].get('ai_memory_dir', 'ai_memory'), config=config)
        if memories:
            memory_list = "\n".join([f"• {mem}" for mem in memories])
            send_group_msg(ws, group_id, L["memory_list_header"].format(ai_name=config['ai_settings']['ai_name'], memory_list=memory_list), True)
        else:
            send_group_msg(ws, group_id, L["memory_list_empty"].format(ai_name=config['ai_settings']['ai_name']), True)


def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    # 定义非法字符
    illegal_chars = ['.', '..', '\\', '/', '|', ':', '*', '?', '"', '<', '>']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename


def save_group_memory(group_id, memory_name=None, memory_dir="ai_memory", auto_save=False, memory_type="normal", config=None):
    """保存单个群的AI记忆
    
    Args:
        group_id: 群号
        memory_name: 记忆名称(手动保存时需要)
        memory_dir: 记忆目录
        auto_save: 是否自动保存
        memory_type: 记忆类型 ("normal", "at", "defined")
        config: 配置字典（用于 boto3 备份）
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
            return False, L["memory_type_invalid"]
        
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
                return False, L["memory_name_empty"]
        
        # 压缩数据
        compressed_data = _compress_data(data)
        
        # 本地备份（默认开启，保持旧配置兼容）
        if not config or config["ai_settings"].get('ai_memory_local_backup', True):
            memory_file = os.path.join(memory_dir, filename)
            with open(memory_file, 'wb') as f:
                f.write(compressed_data)
            logger.info(f"群 {group_id} AI记忆已保存到本地: {memory_file}")
        else:
            logger.info(f"群 {group_id} AI记忆未保存到本地（ai_memory_local_backup=False）")
        
        # boto3 备份（如果启用）
        if config and _is_boto3_backup_enabled(config):
            try:
                s3_client = _get_boto3_client(config)
                bucket_name = config["ai_settings"]['ai_memory_boto3_config'].get('bucket_name', '')
                s3_key = f"memories/{filename}"
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=compressed_data
                )
                logger.info(f"群 {group_id} AI记忆已备份到 S3: {s3_key}")
            except Exception as e:
                logger.error(f"群 {group_id} AI记忆备份到 S3 失败: {e}")
        
        return True, filename
    
    except Exception as e:
        logger.error(f"保存群 {group_id} AI记忆失败: {e}")
        return False, str(e)


def load_group_memory(group_id, memory_name, memory_dir="ai_memory", config=None):
    """加载单个群的AI记忆
    
    Args:
        group_id: 群号
        memory_name: 记忆名称
        memory_dir: 记忆目录
        config: 配置字典（用于 boto3 恢复）
    """
    global ai_conversation_history, at_ai_conversation_history
    
    try:
        # 清理记忆名称
        memory_name = sanitize_filename(memory_name)
        filename = f"{group_id}_{memory_name}.dat"
        memory_file = os.path.join(memory_dir, filename)
        
        compressed_data = None
        source = None
        
        # 优先从本地加载（读取不受备份开关限制）
        if os.path.exists(memory_file):
            with open(memory_file, 'rb') as f:
                compressed_data = f.read()
            source = L["memory_source_local"]
        # 本地没有，尝试从 boto3 恢复
        elif config and _is_boto3_backup_enabled(config):
            try:
                s3_client = _get_boto3_client(config)
                bucket_name = config["ai_settings"]['ai_memory_boto3_config'].get('bucket_name', '')
                s3_key = f"memories/{filename}"
                response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                compressed_data = response['Body'].read()
                source = L["memory_source_s3"]
                logger.info(f"群 {group_id} 从 S3 恢复记忆: {s3_key}")
                
                # 同时保存到本地，便于下次快速加载（受本地备份开关控制，默认开启）
                if not config or config["ai_settings"].get('ai_memory_local_backup', True):
                    if not os.path.exists(memory_dir):
                        os.makedirs(memory_dir)
                    with open(memory_file, 'wb') as f:
                        f.write(compressed_data)
                    logger.info(f"群 {group_id} 记忆已同步到本地: {memory_file}")
            except Exception as e:
                logger.warning(f"从 S3 加载记忆失败: {e}")
        
        if compressed_data is None:
            return False, L["memory_file_not_found"].format(name=memory_name)
        
        # 解压数据
        data = _decompress_data(compressed_data)
        
        # 恢复记忆
        ai_conversation_history[group_id] = data.get('ai_conversation_history', [])
        at_ai_conversation_history[group_id] = data.get('at_ai_conversation_history', [])
        
        logger.info(f"群 {group_id} AI记忆已从{source}加载")
        return True, L["memory_loaded"].format(name=memory_name, source=source)
    
    except Exception as e:
        logger.error(f"加载群 {group_id} AI记忆失败: {e}")
        return False, str(e)


def list_group_memories(group_id, memory_dir="ai_memory", config=None):
    """列出指定群的记忆文件列表（合并本地和S3）
    
    Args:
        group_id: 群号
        memory_dir: 记忆目录
        config: 配置字典（用于 boto3）
    """
    import re
    
    try:
        memory_set = set()
        
        # 从本地获取
        if os.path.exists(memory_dir):
            pattern = re.compile(rf'^{group_id}_(.+)\.dat$')
            for filename in os.listdir(memory_dir):
                if filename.endswith('.dat'):
                    match = pattern.match(filename)
                    if match:
                        memory_set.add(match.group(1))
        
        # 从 S3 获取（如果启用）
        if config and _is_boto3_backup_enabled(config):
            try:
                s3_client = _get_boto3_client(config)
                bucket_name = config["ai_settings"]['ai_memory_boto3_config'].get('bucket_name', '')
                prefix = f"memories/{group_id}_"
                pattern_s3 = re.compile(rf'^memories/{group_id}_(.+)\.dat$')
                
                paginator = s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            key = obj['Key']
                            match = pattern_s3.match(key)
                            if match:
                                memory_set.add(match.group(1))
            except Exception as e:
                logger.warning(f"从 S3 列出记忆失败: {e}")
        
        return sorted(memory_set)
    
    except Exception as e:
        logger.error(f"列出群 {group_id} 记忆文件失败: {e}")
        return []


def auto_save_all_memories(memory_dir="ai_memory", config=None):
    """自动保存所有有对话历史的群的记忆
    
    Args:
        memory_dir: 记忆目录
        config: 配置字典（用于 boto3 备份）
    """
    saved_count = 0
    
    # 本地备份和 boto3 备份都关闭时才跳过自动保存（本地备份默认开启，保持旧配置兼容）
    local_enabled = not config or config["ai_settings"].get('ai_memory_local_backup', True)
    boto3_enabled = bool(config and _is_boto3_backup_enabled(config))
    if not local_enabled and not boto3_enabled:
        logger.info("自动保存已跳过（ai_memory_local_backup 和 ai_memory_boto3_backup 均为 False）")
        return saved_count
    
    # 保存所有有AI对话历史的群
    for group_id in ai_conversation_history.keys():
        if ai_conversation_history[group_id]:  # 只保存有内容的记忆
            success, _ = save_group_memory(group_id, None, memory_dir, auto_save=True, memory_type="normal", config=config)
            if success:
                saved_count += 1
    
    # 保存所有有@AI对话历史的群
    for group_id in at_ai_conversation_history.keys():
        if at_ai_conversation_history[group_id]:  # 只保存有内容的记忆
            success, _ = save_group_memory(group_id, None, memory_dir, auto_save=True, memory_type="at", config=config)
            if success:
                saved_count += 1
    
    # 保存所有有defined对话历史的群
    for group_id in defined_conversation_history.keys():
        if defined_conversation_history[group_id]:  # 只保存有内容的记忆
            success, _ = save_group_memory(group_id, None, memory_dir, auto_save=True, memory_type="defined", config=config)
            if success:
                saved_count += 1
    
    return saved_count


def has_unsaved_memory():
    """检查是否有未保存的记忆"""
    # 检查是否有群有对话历史（超过系统提示的内容）
    for group_id, history in ai_conversation_history.items():
        if len(history) > 1:  # 有用户和AI的对话内容
            return True
    
    for group_id, history in at_ai_conversation_history.items():
        if len(history) > 1:  # 有用户和AI的对话内容
            return True
    
    for group_id, history in defined_conversation_history.items():
        if len(history) > 1:  # 有用户和AI的对话内容
            return True
    
    return False


def load_auto_saved_memories(memory_dir="ai_memory", config=None, ai_manager=None):
    """启动时自动加载所有自动保存的记忆并删除文件
    
    Args:
        memory_dir: 记忆目录
        config: 配置字典（用于 boto3 恢复）
        ai_manager: AI管理器（用于恢复时刷新系统提示为当前配置的规则）
    """
    import re
    
    loaded_count = 0
    
    try:
        pattern = re.compile(r'^(normal|at|defined)_autosave_(\d+)_(\d{8}_\d{6})\.dat$')
        
        # 从本地加载自动保存的记忆（读取不受备份开关限制）
        if os.path.exists(memory_dir):
            for filename in os.listdir(memory_dir):
                if filename.endswith('.dat'):
                    match = pattern.match(filename)
                    if match:
                        memory_type = match.group(1)
                        group_id = int(match.group(2))
                        memory_file = os.path.join(memory_dir, filename)
                        
                        try:
                            with open(memory_file, 'rb') as f:
                                compressed_data = f.read()
                            
                            data = _decompress_data(compressed_data)
                            
                            # 恢复记忆
                            if memory_type == "normal":
                                global ai_conversation_history
                                ai_conversation_history[group_id] = data.get('ai_conversation_history', [])
                                _refresh_loaded_system_prompt(ai_conversation_history[group_id], config, ai_manager, memory_type)
                            elif memory_type == "at":
                                global at_ai_conversation_history
                                at_ai_conversation_history[group_id] = data.get('at_ai_conversation_history', [])
                                _refresh_loaded_system_prompt(at_ai_conversation_history[group_id], config, ai_manager, memory_type)
                            elif memory_type == "defined":
                                global defined_conversation_history
                                defined_conversation_history[group_id] = data.get('defined_conversation_history', [])
                                _refresh_loaded_system_prompt(defined_conversation_history[group_id], config, ai_manager, memory_type)
                            
                            # 删除已加载的自动保存文件
                            os.remove(memory_file)
                            
                            logger.info(f"已自动加载群 {group_id} 的 {memory_type} 记忆（本地）并删除文件: {filename}")
                            loaded_count += 1
                        
                        except Exception as e:
                            logger.error(f"加载自动保存文件 {filename} 失败: {e}")
        
        # 从 S3 加载自动保存的记忆（如果启用且本地没有加载到任何记忆）
        if config and _is_boto3_backup_enabled(config):
            try:
                s3_client = _get_boto3_client(config)
                bucket_name = config["ai_settings"]['ai_memory_boto3_config'].get('bucket_name', '')
                prefix = "memories/"
                
                paginator = s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            key = obj['Key']
                            filename = key[len(prefix):]  # 去掉 "memories/" 前缀
                            match = pattern.match(filename)
                            if match:
                                memory_type = match.group(1)
                                group_id = int(match.group(2))
                                
                                # 如果该类型的记忆在本地已经有了（非空），则跳过 S3 的
                                has_local = False
                                if memory_type == "normal" and group_id in ai_conversation_history and len(ai_conversation_history[group_id]) > 0:
                                    has_local = True
                                elif memory_type == "at" and group_id in at_ai_conversation_history and len(at_ai_conversation_history[group_id]) > 0:
                                    has_local = True
                                elif memory_type == "defined" and group_id in defined_conversation_history and len(defined_conversation_history[group_id]) > 0:
                                    has_local = True
                                
                                if has_local:
                                    continue
                                
                                try:
                                    response = s3_client.get_object(Bucket=bucket_name, Key=key)
                                    compressed_data = response['Body'].read()
                                    data = _decompress_data(compressed_data)
                                    
                                    # 恢复记忆
                                    if memory_type == "normal":
                                        ai_conversation_history[group_id] = data.get('ai_conversation_history', [])
                                        _refresh_loaded_system_prompt(ai_conversation_history[group_id], config, ai_manager, memory_type)
                                    elif memory_type == "at":
                                        at_ai_conversation_history[group_id] = data.get('at_ai_conversation_history', [])
                                        _refresh_loaded_system_prompt(at_ai_conversation_history[group_id], config, ai_manager, memory_type)
                                    elif memory_type == "defined":
                                        defined_conversation_history[group_id] = data.get('defined_conversation_history', [])
                                        _refresh_loaded_system_prompt(defined_conversation_history[group_id], config, ai_manager, memory_type)
                                    
                                    # 同步保存到本地
                                    if not os.path.exists(memory_dir):
                                        os.makedirs(memory_dir)
                                    local_file = os.path.join(memory_dir, filename)
                                    with open(local_file, 'wb') as f:
                                        f.write(compressed_data)
                                    # 加载后删除本地自动保存文件（保持与本地逻辑一致）
                                    os.remove(local_file)
                                    
                                    logger.info(f"已自动加载群 {group_id} 的 {memory_type} 记忆（S3备份）: {filename}")
                                    loaded_count += 1
                                    
                                except Exception as e:
                                    logger.error(f"从 S3 加载自动保存文件 {filename} 失败: {e}")
            except Exception as e:
                logger.warning(f"从 S3 加载自动保存记忆失败: {e}")
        
        return loaded_count
    
    except Exception as e:
        logger.error(f"自动加载记忆失败: {e}")
        return loaded_count