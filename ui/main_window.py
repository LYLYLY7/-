"""
主窗口 UI 模块。

功能：定义主窗口的界面布局（PetApp 类），包括左侧阵容面板、右侧精灵搜索/
      数值配置/技能配置/阵容精灵名单区域。不包含业务逻辑，逻辑委托给
      utils/main_window_logic.py 的 MainWindowLogic 类。
外部依赖：
- utils/main_window_logic.py: 主窗口业务逻辑 MainWindowLogic
- utils/constants.py: IV_OPTIONS, NATURE_OPTIONS, STAT_NAMES
"""

import tkinter as tk
from tkinter import ttk

from utils.constants import IV_OPTIONS, NATURE_OPTIONS, STAT_NAMES
from utils.main_window_logic import MainWindowLogic


class PetApp:
    """
    主窗口应用类。

    功能：创建主窗口的完整 UI 布局，包括：
          1. 左侧：己方阵容和对方阵容的 Listbox 及新建/删除按钮
          2. 右侧上部：精灵搜索框（带自动补全弹出列表）
          3. 右侧中部：数值配置区（六维属性的种族值/个体值/性格系数/面板值）
          4. 右侧中部：技能名称输入区（4 个槽位 + 搜索弹出列表）
          5. 右侧下部：当前选中阵容的精灵名单 + 加入/删除/保存按钮
          初始化后创建 MainWindowLogic 绑定事件和业务逻辑。

    外部参数：
    - root (tk.Tk):
        来源文件：main.py 第 46-53 行创建的 Tkinter 根窗口
        含义：程序主窗口，标题为"洛克王国精灵管理工具 v1.0"，尺寸 800x600 居中
    - data_manager (DataManager):
        来源文件：main.py 第 43 行创建的 DataManager 实例
        含义：数据管理器，负责 all_pets_data.json 和 all_lineups.json 的读写

    内部参数：
    - self.root: 保存传入的根窗口
    - self.inputs: 六维属性输入控件的字典，结构见 setup_ui()
    - self.skill_vars: 4 个技能输入框的 StringVar 列表
    - self.skill_entries: 4 个技能 Entry 控件列表
    - self.logic: MainWindowLogic 实例（业务逻辑层）
    """

    def __init__(self, root, data_manager):
        """
        初始化主窗口 UI 和业务逻辑。

        外部参数：
        - root / data_manager: 见类文档

        内部参数：
        - self.inputs: 初始化后在 setup_ui() 中填充
        - self.skill_vars / self.skill_entries: 同上
        - self.logic: 创建的 MainWindowLogic 实例
        """
        self.root = root
        self.IV_OPTIONS = IV_OPTIONS
        self.NATURE_OPTIONS = NATURE_OPTIONS

        self.setup_ui()
        self.logic = MainWindowLogic(self, data_manager)

    def setup_ui(self):
        """
        搭建主窗口的完整 UI 布局。

        功能：创建左侧阵容面板（己方/对方各含 Listbox + 新建/删除按钮）、
              右侧搜索框（带样式配置）、数值配置区（种族/个体/性格/面板）、
              技能输入区（4 槽位 + 弹出列表）、阵容精灵名单区（含操作按钮）。

        外部参数：无（使用 self.root 作为容器）

        内部参数：
        - left_frame: 左侧容器 Frame
        - ally_panel: 己方阵容 LabelFrame
        - enemy_panel: 对方阵容 LabelFrame
        - right_panel: 右侧容器 Frame
        - style: ttk.Style 实例，配置白色背景输入框样式
        - top_f: 精灵搜索 LabelFrame
        - mid_f: 中间区域 Frame
        - attr_f: 数值配置 LabelFrame
        - headers: 属性配置表格列标题
        - stats: 六维属性名称列表（来自 STAT_NAMES）
        - row_idx: 表格行号
        - base_l / iv_c / nat_c / res_l: 各属性行控件
        - skill_f: 技能名称 LabelFrame
        - sf / sv: 技能输入容器 Frame 和 StringVar
        - bottom_f: 阵容精灵名单 LabelFrame
        - list_frame: 名单容器 Frame
        - scroll_x / scroll_y: 双向滚动条
        - btn_f: 操作按钮容器 Frame
        """
        # ==================== 左侧：阵容面板 ====================
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        # --- 己方阵容 ---
        ally_panel = ttk.LabelFrame(left_frame, text="己方阵容")
        ally_panel.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.ally_lineup_selector = tk.Listbox(
            ally_panel, width=20, font=("Arial", 10), exportselection=False
        )
        self.ally_lineup_selector.pack(padx=5, pady=5, fill="both", expand=True)

        self.ally_new_lineup_button = ttk.Button(ally_panel, text="新建阵容")
        self.ally_new_lineup_button.pack(fill="x", padx=5, pady=2)
        self.ally_delete_lineup_button = ttk.Button(ally_panel, text="删除阵容")
        self.ally_delete_lineup_button.pack(fill="x", padx=5, pady=2)

        # --- 对方阵容 ---
        enemy_panel = ttk.LabelFrame(left_frame, text="对方阵容")
        enemy_panel.pack(side="bottom", fill="both", expand=True, padx=5, pady=5)

        self.enemy_lineup_selector = tk.Listbox(
            enemy_panel, width=20, font=("Arial", 10), exportselection=False
        )
        self.enemy_lineup_selector.pack(padx=5, pady=5, fill="both", expand=True)

        self.enemy_new_lineup_button = ttk.Button(enemy_panel, text="新建阵容")
        self.enemy_new_lineup_button.pack(fill="x", padx=5, pady=2)
        self.enemy_delete_lineup_button = ttk.Button(enemy_panel, text="删除阵容")
        self.enemy_delete_lineup_button.pack(fill="x", padx=5, pady=2)

        # ==================== 右侧：搜索 + 配置 + 技能 + 名单 ====================
        right_panel = ttk.Frame(self.root)
        right_panel.pack(side="right", fill="both", expand=True)

        # --- 精灵搜索 ---
        self.top_f = ttk.LabelFrame(right_panel, text="第一步：选择精灵")
        self.top_f.pack(fill="x", padx=10, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            self.top_f, textvariable=self.search_var, font=("Arial", 11), style="White.TEntry"
        )
        self.search_entry.pack(padx=10, pady=10, fill="x", expand=True)

        # 配置白色背景样式
        style = ttk.Style(self.root)
        style.configure("White.TCombobox", fieldbackground="white", background="white")
        style.map(
            "White.TCombobox",
            fieldbackground=[("readonly", "white")],
            background=[("readonly", "white")],
        )
        style.configure("White.TEntry", fieldbackground="white", background="white")

        # --- 精灵搜索候选弹出列表 ---
        self.pet_result_frame = ttk.Frame(right_panel)
        self.pet_result_scrollbar = ttk.Scrollbar(self.pet_result_frame, orient="vertical")
        self.pet_result_listbox = tk.Listbox(
            self.pet_result_frame,
            height=6,
            exportselection=False,
            font=("Arial", 10),
            yscrollcommand=self.pet_result_scrollbar.set,
        )
        self.pet_result_scrollbar.config(command=self.pet_result_listbox.yview)
        self.pet_result_listbox.pack(side="left", fill="both", expand=True)
        self.pet_result_scrollbar.pack(side="right", fill="y")

        # --- 数值配置 + 技能名称 ---
        mid_f = ttk.Frame(right_panel)
        mid_f.pack(fill="both", expand=True)

        # 数值配置表
        self.attr_f = ttk.LabelFrame(mid_f, text="第二步：数值配置")
        self.attr_f.pack(side="left", fill="both", expand=True, padx=10)
        self.inputs = {}
        headers = ["属性", "属性值", "个体值", "性格系数", "面板值"]
        for col, header in enumerate(headers):
            ttk.Label(self.attr_f, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, pady=(10, 5), padx=5
            )

        for i, stat in enumerate(STAT_NAMES):
            row_idx = i + 1
            ttk.Label(self.attr_f, text=stat).grid(
                row=row_idx, column=0, pady=10, padx=5
            )
            base_l = ttk.Label(self.attr_f, text="-", width=5)
            base_l.grid(row=row_idx, column=1)

            iv_c = ttk.Combobox(
                self.attr_f,
                values=self.IV_OPTIONS,
                width=5,
                state="readonly",
                style="White.TCombobox",
            )
            iv_c.set("0")
            iv_c.grid(row=row_idx, column=2, padx=5)

            nat_c = ttk.Combobox(
                self.attr_f,
                values=self.NATURE_OPTIONS,
                width=5,
                state="readonly",
                style="White.TCombobox",
            )
            nat_c.set("1.0")
            nat_c.grid(row=row_idx, column=3, padx=5)

            res_l = ttk.Label(
                self.attr_f,
                text="0",
                foreground="blue",
                font=("Arial", 11, "bold"),
            )
            res_l.grid(row=row_idx, column=4, padx=10)
            self.inputs[stat] = {
                "base": base_l,
                "iv": iv_c,
                "nat": nat_c,
                "res": res_l,
            }

        # 技能名称输入区
        self.skill_f = ttk.LabelFrame(mid_f, text="第三步：技能名称")
        self.skill_f.pack(side="right", fill="both", expand=True, padx=10)
        self.skill_vars = []
        self.skill_entries = []
        for i in range(4):
            sf = ttk.Frame(self.skill_f)
            sf.pack(fill="x", pady=5)
            sv = tk.StringVar()
            entry = ttk.Entry(sf, textvariable=sv, style="White.TEntry")
            entry.pack(side="left", fill="x", expand=True, padx=5)
            self.skill_vars.append(sv)
            self.skill_entries.append(entry)

        # 技能候选弹出列表
        self.skill_result_frame = ttk.Frame(self.skill_f)
        self.skill_result_scrollbar = ttk.Scrollbar(
            self.skill_result_frame, orient="vertical"
        )
        self.skill_result_listbox = tk.Listbox(
            self.skill_result_frame,
            height=6,
            exportselection=False,
            font=("Arial", 10),
            yscrollcommand=self.skill_result_scrollbar.set,
        )
        self.skill_result_scrollbar.config(command=self.skill_result_listbox.yview)
        self.skill_result_listbox.pack(side="left", fill="both", expand=True)
        self.skill_result_scrollbar.pack(side="right", fill="y")

        # 分隔线和伤害计算按钮
        self.skill_footer_separator = ttk.Separator(self.skill_f, orient="horizontal")
        self.skill_footer_separator.pack(fill="x", pady=10, padx=5)
        self.open_damage_button = ttk.Button(self.skill_f, text="实战伤害计算")
        self.open_damage_button.pack(fill="x", padx=10, pady=5)

        # --- 阵容精灵名单 ---
        bottom_f = ttk.LabelFrame(right_panel, text="当前选中阵容的精灵名单")
        bottom_f.pack(fill="both", expand=True, padx=10, pady=10)

        list_frame = ttk.Frame(bottom_f)
        list_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")
        scroll_y = ttk.Scrollbar(list_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        self.pet_listbox = tk.Listbox(
            list_frame,
            height=8,
            selectmode="browse",
            exportselection=False,
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
            font=("Arial", 10),
        )
        self.pet_listbox.pack(side="left", fill="both", expand=True)
        scroll_x.config(command=self.pet_listbox.xview)
        scroll_y.config(command=self.pet_listbox.yview)

        btn_f = ttk.Frame(bottom_f)
        btn_f.pack(side="right", padx=10)
        self.add_ally_button = ttk.Button(btn_f, text="加入己方阵容")
        self.add_ally_button.pack(fill="x", pady=2)
        self.add_enemy_button = ttk.Button(btn_f, text="加入对方阵容")
        self.add_enemy_button.pack(fill="x", pady=2)
        self.delete_pet_button = ttk.Button(btn_f, text="删除该精灵")
        self.delete_pet_button.pack(fill="x", pady=2)
        self.save_button = ttk.Button(btn_f, text="保存所有阵容")
        self.save_button.pack(fill="x", pady=10)
