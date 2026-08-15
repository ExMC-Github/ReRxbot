# 语言选择器：根据环境变量 / config 选择语言字典，并加载到 builtins.language
#
# 用法：
#   主进程：app.py 在 module_check() 之后调用 languages_choicer.setup()
#   各模块：from functions.languages_choicer import L
#   语言字典：data/language_zh.py（中文）/ data/language_en.py（英文）/
#            data/language_pseudo.py（微软式伪本地化），均由 bindict 编译
#   语言来源（按优先级）：
#     1. 环境变量 BOT_LANGUAGE（zh / en / pseudo）
#     2. config 配置项 bot_language（zh / en / pseudo）
#     3. 缺省 zh；无效值回落 zh
import os
import builtins

try:
    from data import language_zh
    from data import language_en
    from data import language_pseudo
    _LANGUAGES = {
        "zh": language_zh,
        "en": language_en,
        "pseudo": language_pseudo,
    }
except Exception:
    # bindict 不可用（如未在 .venv 环境运行）：语言表置空，保证导入链不中断
    _LANGUAGES = {}

_DEFAULT = "zh"


def _select_name():
    name = os.environ.get("BOT_LANGUAGE", "").strip().lower()
    if name and name in _LANGUAGES:
        return name
    cfg = getattr(builtins, "config", None)
    if cfg:
        name = str(cfg.get("bot_language", "")).strip().lower()
        if name in _LANGUAGES:
            return name
    return _DEFAULT if _DEFAULT in _LANGUAGES else next(iter(_LANGUAGES), None)


def _load_language(mod):
    """加载语言字典。

    自动执行 mod.verify_bin_str()（crc32 校验）：通过才返回真实字典；
    校验失败或加载异常时，返回键齐全、值全为空字符串的字典
    （静默降级，避免调用方 KeyError）。
    """
    if mod is None:
        return {}
    if mod.verify_bin_str():
        try:
            return mod.data
        except Exception:
            pass
    for candidate in _LANGUAGES.values():
        try:
            keys = candidate.data.keys()
        except Exception:
            continue
        return {key: "" for key in keys}
    return {}


def setup():
    """选择语言并加载到 builtins.language（dict），返回该 dict。

    语言字典校验失败时所有键的值为空字符串（静默降级）。
    """
    name = _select_name()
    lang = _load_language(_LANGUAGES.get(name)) if name else {}
    builtins.language = lang
    return lang


def get_language_name():
    """返回当前生效的语言名（zh / en）"""
    return _select_name()


class _LanguageProxy:
    """惰性语言代理：每次 __getitem__ 实时读取 builtins.language。

    语言切换（重新 setup / 替换 builtins.language）后自动生效；
    builtins.language 未初始化时（如独立子进程）兜底默认语言。
    """

    def __getitem__(self, key):
        lang = getattr(builtins, "language", None)
        if lang is None:
            name = _select_name()
            lang = _load_language(_LANGUAGES.get(name)) if name else {}
        try:
            return lang[key]
        except KeyError:
            return ""


L = _LanguageProxy()
