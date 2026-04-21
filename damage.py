import tkinter as tk
import os
from ui.damage_window import DamageWindow
from utils.data_manager import DataManager

def test_damage_window():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dm = DataManager(base_dir)
    db = dm.load_pet_db()

    root = tk.Tk()
    root.withdraw()

    if not db:
        from tkinter import messagebox
        messagebox.showerror("错误", "未找到精灵数据库，请先运行爬虫同步数据！")
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
