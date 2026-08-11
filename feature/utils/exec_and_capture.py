# 在受限命名空间中执行代码并捕获标准输出/异常


def exec_and_capture(code: str,sys,io,traceback,ws) -> str:
    """执行代码并捕获标准输出及异常，返回输出的字符串"""
    # 创建字符串缓冲区来替代标准输出
    stdout_capture = io.StringIO()
    # 保存原始的标准输出
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    # 准备一个命名空间，可以预先放入一些安全模块或限制
    namespace = {'ws': ws}

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
