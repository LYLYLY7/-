"""
UI 辅助模块。

功能：抽取项目中通用的对话框创建函数和 UI 组件创建函数，减少各文件中的重复代码。
外部调用方：utils/main_window_logic.py、utils/damage_window_logic.py
"""

import tkinter as tk
from tkinter import ttk, messagebox


def ask_lineup_name(parent):
    """
    弹出输入对话框，让用户输入阵容名称。

    功能：创建一个模态对话框，包含文本输入框和"确定"/"取消"按钮。
         用户输入名称后点击确定返回该名称，点击取消返回 None。

    外部参数：
    - parent (tk.Toplevel / tk.Tk):
        来源文件：utils/main_window_logic.py 中 add_new_lineup() 方法传入 self.root
        含义：父窗口，对话框将作为其子窗口居中显示

    内部参数：
    - dialog: 新建的 Toplevel 对话框窗口
    - container: 对话框内的主容器 Frame（含 padding）
    - name_var: StringVar，绑定输入框的文本变量
    - entry: 名称输入框
    - result: dict，存储返回结果 {"value": str | None}
    - submit(): 内部函数，验证并提交名称
    - cancel(): 内部函数，取消关闭对话框
    - button_frame: 按钮容器 Frame

    返回值：
    - str: 用户输入的阵容名称（已去除首尾空格）
    - None: 用户取消操作
    """
    dialog = tk.Toplevel(parent)
    dialog.title("新建阵容")
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    result = {"value": None}

    container = ttk.Frame(dialog, padding=12)
    container.pack(fill="both", expand=True)

    ttk.Label(container, text="名称:").pack(anchor="w")
    name_var = tk.StringVar()
    entry = ttk.Entry(container, textvariable=name_var, width=24)
    entry.pack(fill="x", pady=(6, 10))

    button_frame = ttk.Frame(container)
    button_frame.pack(fill="x")

    def submit():
        """验证名称非空后提交结果并关闭对话框。"""
        value = name_var.get().strip()
        if not value:
            messagebox.showwarning("提示", "请输入阵容名称", parent=dialog)
            return
        result["value"] = value
        dialog.destroy()

    def cancel():
        """取消操作，关闭对话框。"""
        dialog.destroy()

    ttk.Button(button_frame, text="确定", command=submit).pack(
        side="left", expand=True, fill="x", padx=(0, 4)
    )
    ttk.Button(button_frame, text="取消", command=cancel).pack(
        side="left", expand=True, fill="x", padx=(4, 0)
    )

    dialog.bind("<Return>", lambda event: submit())
    dialog.bind("<Escape>", lambda event: cancel())
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    entry.focus_set()
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    parent.wait_window(dialog)
    return result["value"]


def show_lineup_selection_dialog(parent, lineup_data):
    """
    弹出阵容选择对话框，让用户选择己方和对方的阵容。

    功能：读取 all_lineups.json 中的阵容列表，分别用两个下拉框展示己方和对方阵容，
         用户确认后返回选中的阵容名和完整数据。

    外部参数：
    - parent (tk.Toplevel):
        来源文件：utils/damage_window_logic.py 中 load_lineup_from_all_lineups() 方法传入 self.view
        含义：父窗口，对话框将作为其子窗口居中显示
    - lineup_data (dict):
        来源文件：utils/damage_window_logic.py 中 read_all_lineups_file() 方法返回
        含义：从 data/all_lineups.json 读取的完整阵容数据
              结构: {"己方": {"阵容名": [精灵条目, ...]}, "对方": {"阵容名": [精灵条目, ...]}}

    内部参数：
    - ally_lineups: 己方阵容名称列表
    - enemy_lineups: 对方阵容名称列表
    - dialog: 新建的 Toplevel 对话框窗口
    - result: 存储选中的己方和对方阵容名
    - frame: 对话框内的主容器 Frame
    - ally_combo: 己方阵容下拉框
    - enemy_combo: 对方阵容下拉框
    - confirm(): 确认选择并关闭对话框
    - cancel(): 取消关闭对话框

    返回值：
    - tuple: (己方阵容名, 对方阵容名, 完整阵容数据) — 用户确认选择
    - None: 用户取消或数据不完整
    """
    ally_lineups = list(lineup_data.get("己方", {}).keys())
    enemy_lineups = list(lineup_data.get("对方", {}).keys())

    if not ally_lineups or not enemy_lineups:
        messagebox.showwarning("提示", "阵容数据不完整", parent=parent)
        return None

    dialog = tk.Toplevel(parent)
    dialog.title("选择阵容")
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    result = {"ally": None, "enemy": None}

    frame = ttk.Frame(dialog, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="己方阵容:").grid(row=0, column=0, padx=5, pady=8, sticky="w")
    ally_combo = ttk.Combobox(frame, values=ally_lineups, state="readonly", width=22)
    ally_combo.grid(row=0, column=1, padx=5, pady=8)
    ally_combo.set(ally_lineups[0])

    ttk.Label(frame, text="对方阵容:").grid(row=1, column=0, padx=5, pady=8, sticky="w")
    enemy_combo = ttk.Combobox(frame, values=enemy_lineups, state="readonly", width=22)
    enemy_combo.grid(row=1, column=1, padx=5, pady=8)
    enemy_combo.set(enemy_lineups[0])

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=(12, 0))

    def confirm():
        """记录选中的阵容名并关闭对话框。"""
        result["ally"] = ally_combo.get()
        result["enemy"] = enemy_combo.get()
        dialog.destroy()

    def cancel():
        """取消操作，关闭对话框。"""
        dialog.destroy()

    ttk.Button(btn_frame, text="确定", command=confirm).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="取消", command=cancel).pack(side="left", padx=6)

    dialog.bind("<Return>", lambda e: confirm())
    dialog.bind("<Escape>", lambda e: cancel())

    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    parent.wait_window(dialog)

    if result["ally"] and result["enemy"]:
        return result["ally"], result["enemy"], lineup_data
    return None


def create_scrolled_listbox(parent, height=5, font=("Arial", 10)):
    """
    创建带垂直滚动条的 Listbox 组件。

    功能：生成一个 Listbox + Scrollbar 的组合组件，用于展示候选列表。
    外部调用方：ui/damage_window.py 和 ui/main_window.py 中创建精灵/技能候选列表

    外部参数：
    - parent (ttk.Frame / ttk.LabelFrame):
        含义：父容器，Listbox 将被放置在此容器内
    - height (int):
        含义：Listbox 显示的行数，默认 5
    - font (tuple):
        含义：Listbox 的字体设置，默认 ("Arial", 10)

    内部参数：
    - scrollbar: 垂直滚动条
    - listbox: Listbox 组件

    返回值：
    - dict: {"frame": 父容器(ttk.Frame), "listbox": Listbox, "scrollbar": Scrollbar}
    """
    scrollbar = ttk.Scrollbar(parent, orient="vertical")
    listbox = tk.Listbox(
        parent,
        height=height,
        exportselection=False,
        font=font,
        yscrollcommand=scrollbar.set,
    )
    scrollbar.config(command=listbox.yview)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return {"frame": parent, "listbox": listbox, "scrollbar": scrollbar}
