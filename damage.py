"""
伤害推演窗口独立启动入口。

功能：单独启动实战伤害推演计算窗口（不经过主窗口）。
      用于独立测试伤害计算功能。
外部依赖：
- ui/damage_window.py: 伤害推演窗口 UI 类 DamageWindow
- utils/data_manager.py: 数据管理器 DataManager
"""

import tkinter as tk
import os
from ui.damage_window import DamageWindow
from utils.data_manager import DataManager


def test_damage_window():
    """
    启动伤害推演窗口。

    功能：完成以下流程：
          1. 获取项目根目录，初始化数据管理器
          2. 从 all_pets_data.json 加载精灵数据库（db）
          3. 创建隐藏的 Tkinter 根窗口（root.withdraw()）
          4. 实例化 DamageWindow，将 db 数据传入
          5. 将 DamageWindow 提升到前台显示
          6. 进入 Tkinter 事件主循环

    外部参数：无

    内部参数：
    - base_dir: 项目根目录
    - dm: DataManager 实例
    - db: 精灵数据库字典 {名字: 精灵数据}，从 all_pets_data.json 加载
    - root: 隐藏的 Tkinter 根窗口（作为 DamageWindow 的父窗口）
    - damage_win: DamageWindow 实例，实战伤害推演窗口

    返回值：无（mainloop 结束后退出）

    异常处理：
    - 如果精灵数据库为空（db 为 None），弹出错误提示并终止执行
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dm = DataManager(base_dir)
    db = dm.load_pet_db()

    root = tk.Tk()
    root.withdraw()

    if not db:
        from tkinter import messagebox

        messagebox.showerror("错误", "未找到精灵数据库，请先运行crawler同步数据！")
        root.destroy()
        return

    print("正在启动实战伤害模拟窗口...")
    root.update_idletasks()
    damage_win = DamageWindow(root, db)
    damage_win.update_idletasks()
    damage_win.deiconify()
    damage_win.lift()
    damage_win.attributes("-topmost", True)
    damage_win.after(300, lambda: damage_win.attributes("-topmost", False))
    damage_win.after(50, damage_win.focus_force)
    damage_win.protocol("WM_DELETE_WINDOW", root.destroy)

    root.mainloop()


if __name__ == "__main__":
    test_damage_window()
