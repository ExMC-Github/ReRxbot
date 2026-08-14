# -*- coding: utf-8 -*-
"""打包脚本：把项目根目录下除 .git / __pycache__ / .venv / logs / log.txt 之外
的全部文件打包成 qqbot.tar.xz（tar + xz 压缩）。

用法：python build_archive.py
"""
import os
import tarfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "no_commit", "qqbot.tar.xz")
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "logs"}
EXCLUDE_FILES = {"log.txt", "app.log", "qqbot.tar.xz"}


def main():
    count = 0
    with tarfile.open(OUTPUT, "w:xz") as tar:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            # 原地过滤需要整体跳过的目录（含任意层级的同名目录）
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for name in filenames:
                if name in EXCLUDE_FILES:
                    continue
                full = os.path.join(dirpath, name)
                arcname = os.path.relpath(full, ROOT)
                tar.add(full, arcname=arcname)
                count += 1
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"done: {OUTPUT} ({count} files, {size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
