# 在受限命名空间中执行代码并捕获标准输出/异常
import traceback


def exec_and_capture(code: str,sys,io,traceback,ws,group_id=None,self_id=None,user_id=None,msg=None) -> str:
    """执行代码并捕获标准输出及异常，返回输出的字符串"""
    # 创建字符串缓冲区来替代标准输出
    stdout_capture = io.StringIO()
    # 保存原始的标准输出
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    # 准备一个命名空间，可以预先放入一些安全模块或限制
    namespace = {
        'ws': ws,
        'group_id': group_id,
        'self_id': self_id,
        'user_id': user_id,
        'msg': msg,
    }

    try:
        # 使用 compile 编译代码，指定模式为 'exec'
        compiled = compile(code, '<script>', 'exec')
        # 执行编译后的代码，传入命名空间
        exec(compiled, namespace)
    except Exception:
        # 捕获执行过程中的异常，并将异常信息写入输出
        sys.stdout = old_stdout  # 先恢复，避免 traceback 打印到我们的缓冲区外
        return traceback.format_exc()
    finally:
        # 恢复标准输出
        sys.stdout = old_stdout

    # 获取缓冲区的内容
    output = stdout_capture.getvalue()
    stdout_capture.close()
    return output


def lua_exec_and_capture(code: str) -> str:
    """使用 lupa 执行 Lua 代码并捕获输出/异常，返回输出的字符串"""
    try:
        from lupa import LuaRuntime
    except ImportError:
        return traceback.format_exc(limit=1) + "\n请先安装 lupa：pip install lupa"

    output_lines = []

    def lua_print(*args):
        # 将 Lua 的 print 输出捕获到列表中
        output_lines.append(" ".join(str(a) for a in args))

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().print = lua_print

    try:
        lua.execute(code)
    except Exception:
        return traceback.format_exc()
    return "\n".join(output_lines)
