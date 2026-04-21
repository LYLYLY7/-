import tkinter as tk
import os
from ui.main_window import PetApp
from utils.data_manager import DataManager

def main():
    # 1. 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 初始化数据管理器
    dm = DataManager(base_dir)
    
    # 3. 初始化 Tkinter 窗口
    root = tk.Tk()
    
    # --- 在这里修改顶部标题 ---
    root.title("洛克王国精灵管理工具 v1.0")
    
    # 4. 居中设置
    w, h = 800, 600
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")
    
    # 5. 启动应用
    app = PetApp(root, dm)
    
    root.mainloop()

if __name__ == "__main__":
    main()