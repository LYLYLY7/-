"""
程序主入口文件。

功能：初始化数据管理器、创建主窗口、启动 Tkinter 事件循环。
外部依赖：
- ui/main_window.py: 主窗口 UI 类 PetApp
- utils/data_manager.py: 数据管理器 DataManager
"""

import tkinter as tk
import os
from ui.main_window import PetApp
from utils.data_manager import DataManager


def main():
    """
    主函数。

    功能：完成以下启动流程：
          1. 获取脚本所在目录作为项目根目录（base_dir）
          2. 初始化数据管理器（DataManager），用于读写精灵数据库和阵容数据
          3. 创建 Tkinter 根窗口（root），设置窗口标题和居中尺寸（800x600）
          4. 实例化主窗口应用（PetApp）
          5. 进入 Tkinter 事件主循环

    外部参数：无（从操作系统获取当前文件路径）

    内部参数：
    - base_dir: 项目根目录的绝对路径（通过 os.path.abspath(__file__) 自动获取）
    - dm: DataManager 实例，负责 data/*.json 的读写
    - root: Tkinter 根窗口对象
    - w, h: 窗口初始宽度(800)和高度(600)
    - x, y: 窗口居中时的屏幕坐标
    - app: PetApp 实例，管理主窗口 UI 和业务逻辑

    返回值：无（mainloop 结束后退出）
    """
    # 1. 获取当前脚本所在目录作为项目根目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. 初始化数据管理器（负责 JSON 文件的读写和迁移）
    dm = DataManager(base_dir)

    # 3. 初始化 Tkinter 根窗口，设置标题为"洛克王国精灵管理工具 v1.0"
    root = tk.Tk()
    root.title("洛克王国精灵管理工具 v1.0")

    # 4. 设置窗口大小为 800x600 并居中显示
    w, h = 800, 600
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    # 5. 启动主窗口应用
    app = PetApp(root, dm)

    # 6. 进入 Tkinter 事件主循环，直到窗口关闭
    root.mainloop()


if __name__ == "__main__":
    main()
