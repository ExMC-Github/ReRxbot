# 这是Ai写的，不关ExRFy的事情
"""AI代码审核GUI - 独立子进程运行，避免Tcl_AsyncDelete线程错误

通信协议:
  输入: stdin 接收代码文本
  输出: stdout 输出 JSON {"approved": bool, "timeout": bool, "extra": str|None}
"""
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


def main():
    # 从 stdin 读取代码（UTF-8 解码，避免 Windows GBK 编码问题）
    code = sys.stdin.buffer.read().decode('utf-8')
    if not code:
        # 确保 stdout 使用 UTF-8 输出
        sys.stdout.buffer.write(json.dumps({"approved": False, "timeout": False, "extra": None}).encode('utf-8'))
        return

    code_lines = code.split('\n')
    num_lines = len(code_lines)
    max_line_len = max((len(line) for line in code_lines), default=0)
    visible_lines = min(num_lines, 30)

    if num_lines > 100:
        win_width = 640
        win_height = 560
    else:
        # overhead: 标题(40) + 计时器(30) + 按钮区(55) + 边距(55) ≈ 180
        win_height = max(min(visible_lines * 22 + 180, 560), 260)
        win_width = max(min(max_line_len * 9 + 50, 640), 420)

    root = tk.Tk()
    root.title("AI代码审核")
    root.geometry(f"{win_width}x{win_height}")

    style = ttk.Style()
    try:
        style.theme_use('vista')
    except Exception:
        pass

    # 使用可变容器，循环中重置内容
    state = {"approved": None, "timeout": False, "cancelled": False}
    remaining = [30]
    after_id = [None]

    # 标题
    ttk.Label(root, text="AI 请求执行以下 Python 代码，请审核：",
              font=("宋体", 10, "bold")).pack(pady=(10, 5))

    # 代码文本区
    text_frame = ttk.Frame(root)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

    text_widget = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 10),
                          height=visible_lines, background="#f5f5f5",
                          relief="solid", borderwidth=1)
    text_widget.insert("1.0", code)
    text_widget.config(state=tk.DISABLED)

    y_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
    x_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
    text_widget.config(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

    text_widget.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)

    # 计时器
    timer_label = ttk.Label(root, text=f"剩余审核时间: {remaining[0]} 秒",
                            foreground="red", font=("宋体", 9))
    timer_label.pack(pady=(4, 2))

    # 按钮区
    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=(2, 12))

    def finish(approved, cancelled=False):
        if after_id[0] is not None:
            root.after_cancel(after_id[0])
            after_id[0] = None
        state["approved"] = approved
        state["cancelled"] = cancelled
        root.quit()

    ttk.Button(btn_frame, text="确定", width=12,
               command=lambda: finish(True)).pack(side=tk.LEFT, padx=15)
    ttk.Button(btn_frame, text="取消", width=12,
               command=lambda: finish(False, cancelled=True)).pack(side=tk.LEFT, padx=15)

    # 处理窗口关闭按钮(X) —— 与取消按钮区分，关X不弹附加内容框
    root.protocol("WM_DELETE_WINDOW", lambda: finish(False))

    # 确保窗口最小尺寸能显示所有组件
    root.update_idletasks()
    root.minsize(win_width, 180)

    def tick():
        if state["approved"] is not None:
            return
        remaining[0] -= 1
        timer_label.config(text=f"剩余审核时间: {remaining[0]} 秒")
        if remaining[0] <= 0:
            state["approved"] = False
            state["timeout"] = True
            root.quit()
        else:
            after_id[0] = root.after(1000, tick)

    # 主循环：审核 → 确认 →（执行 或 退回审核）
    while True:
        # 每轮重置状态
        state["approved"] = None
        state["timeout"] = False
        state["cancelled"] = False
        remaining[0] = 30
        after_id[0] = None
        timer_label.config(text=f"剩余审核时间: {remaining[0]} 秒")

        # 确保窗口可见并获取焦点
        root.deiconify()
        root.lift()
        root.attributes('-topmost', True)
        root.after(100, lambda: root.attributes('-topmost', False))
        root.focus_force()

        after_id[0] = root.after(1000, tick)
        root.mainloop()

        approved = state["approved"]

        # 超时或关闭窗口(X)：不弹附加内容，直接结束
        if not approved and not state["cancelled"]:
            root.destroy()
            sys.stdout.buffer.write(json.dumps({"approved": False, "timeout": state["timeout"], "extra": None}).encode('utf-8'))
            return

        # 取消按钮：弹附加内容框（可选），不执行，结束
        if not approved and state["cancelled"]:
            extra = simpledialog.askstring(
                "附加内容",
                "请输入附加内容（可选，作为上下文随结果返回给AI）：\n留空或点击取消则无附加内容",
                parent=root
            )
            if extra is None:
                extra = ""
            root.destroy()
            sys.stdout.buffer.write(json.dumps({"approved": False, "timeout": False, "extra": extra if extra else None}).encode('utf-8'))
            return

        # 点确定：不隐藏窗口，直接弹确认对话框（覆盖在审核窗口上方）
        do_execute = messagebox.askyesno(
            "执行确认",
            '是否执行此代码？\n\n选"是"：执行代码\n选"否"：返回代码审核',
            parent=root
        )

        if do_execute:
            # 点"是"：弹附加内容框，执行
            extra = simpledialog.askstring(
                "附加内容",
                "请输入附加内容（可选，作为上下文随执行结果返回给AI）：\n留空或点击取消则无附加内容",
                parent=root
            )
            if extra is None:
                extra = ""
            root.destroy()
            sys.stdout.buffer.write(json.dumps({"approved": True, "timeout": False, "extra": extra if extra else None}).encode('utf-8'))
            return
        else:
            # 点"否"：退回代码审核阶段，循环继续
            continue


if __name__ == "__main__":
    main()
