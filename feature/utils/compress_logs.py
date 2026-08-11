# 压缩日志文件为 .zst 存档并删除原 app.log
from loguru import logger


def compress_logs(os,datetime,tarfile,sys):
    """压缩日志文件"""
    try:
        # 获取当前时间作为文件名
        now = datetime.datetime.now()
        filename = now.strftime("%Y%m%d-%H%M%S") + ".txt.zst"
        filepath = os.path.join('logs', filename)

        # 检查app.log是否存在
        if not os.path.exists('app.log'):
            logger.warning("app.log不存在，无需压缩")
            return

        # 创建tar.gz压缩文件
        with open(f"logs/{filename}","wb") as f:
            if sys.version_info >= (3,14):
                import compression.zstd as zstd
            else:
                if hasattr(sys,"built_target"):
                    import zstd
                else:
                    import zstandard as zstd
            with open("app.log",'rb') as g:
                f.write(zstd.compress(g.read()))

        # 删除原日志文件
        os.remove('app.log')

        logger.info(f"日志已压缩保存到: {filepath}")
        logger.info("新日志文件已创建")

    except Exception as e:
        logger.error(f"压缩日志时出错: {e}")
