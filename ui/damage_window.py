"""
实战伤害推演窗口 UI 模块。

功能：定义伤害推演窗口的完整 UI 布局（DamageWindow 类），包含精灵输入区域、
      技能与环境参数区域、实战属性区域、伤害计算结果区域。UI 控件通过 dict
      (left_ui / right_ui) 组织，供逻辑层（DamageWindowLogic）操作。
外部依赖：
- utils/damage_window_logic.py: 伤害窗口业务逻辑 DamageWindowLogic
- utils/constants.py: ELEMENT_TYPES, ATK_TYPES, IV_OPTIONS, NATURE_OPTIONS,
                      STAB_OPTIONS, ELEMENT_MULT_OPTIONS, STAT_NAMES
"""

import tkinter as tk
from tkinter import ttk

from utils.constants import (
    ATK_TYPES,
    ELEMENT_MULT_OPTIONS,
    ELEMENT_TYPES,
    IV_OPTIONS,
    NATURE_OPTIONS,
    STAB_OPTIONS,
    STAT_NAMES,
)
from utils.damage_window_logic import DamageWindowLogic


class DamageWindow(tk.Toplevel):
    """
    实战伤害推演窗口类。

    功能：创建独立的伤害推演窗口，包含双方精灵的身份/技能/属性面板。
          支持两种启动模式：
          - 独立启动（use_lineup_load=False）：用户手动输入精灵名和技能
          - 阵容加载模式（use_lineup_load=True）：从主窗口启动，提供阵容加载按钮
          UI 布局分为五行：
            行0: 精灵区域（双方精灵名 + 技能输入 + 候选列表）
            行1: 操作区域（技能按钮 + 阵容加载 + 愿力/首领化/聚能/退场）
            行2: 技能与环境参数区域（类型/属性/威力/本系加成/克制等）
            行3: 实战属性区域（种族/个体/性格/面板值 + 战斗信息）
            行4: 伤害计算结果区域（攻击按钮 + 结果标签 + 重置）

    外部参数：
    - parent (tk.Tk / tk.Toplevel):
        来源文件：main.py 或 utils/main_window_logic.py open_damage_calculator()
        含义：父窗口，DamageWindow 作为其 Toplevel 子窗口
    - db_data (dict):
        来源文件：utils/data_manager.py load_pet_db() 返回值
        含义：精灵数据库字典，{精灵名称(str): 精灵数据(dict)}，用于按名查询
    - use_lineup_load (bool):
        来源文件：utils/main_window_logic.py open_damage_calculator() 传入 True
        含义：是否使用阵容加载模式（True=显示"阵容加载"按钮，False=显示"加载"按钮）

    内部参数：
    - self.left_ui: 左侧（本人）UI 控件引用字典
    - self.right_ui: 右侧（对方）UI 控件引用字典
    - self.logic: DamageWindowLogic 实例
    - self.atk_type_values: 技能类型下拉选项
    - self.attr_values: 属性下拉选项（19 系）
    - self.iv_values: 个体值下拉选项
    - self.nature_values: 性格系数下拉选项
    - self.style: 本窗口专用的 ttk.Style
    - self.main_frame: 主容器 Frame（grid 布局）
    - self.pet_area: 精灵区域 LabelFrame（行0）
    - self.load_frame: 操作区域 Frame（行1）
    - self.skill_area: 技能参数 LabelFrame（行2）
    - self.stats_area: 实战属性 LabelFrame（行3）
    - self.result_frame: 伤害计算 LabelFrame（行4）
    """

    def __init__(self, parent, db_data, use_lineup_load=False):
        """
        初始化伤害推演窗口。

        外部参数：
        - parent / db_data / use_lineup_load: 见类文档

        内部参数：
        - self.atk_type_values / self.attr_values / self.iv_values / self.nature_values:
          从 constants 模块导入的 UI 下拉选项
        """
        super().__init__(parent)
        self.title("实战伤害推演计算器")
        self.geometry("960x830")

        self.use_lineup_load = use_lineup_load
        self.atk_type_values = ATK_TYPES
        self.attr_values = ELEMENT_TYPES
        self.iv_values = IV_OPTIONS
        self.nature_values = NATURE_OPTIONS
        self.style = ttk.Style(self)

        self.setup_styles()
        self.setup_ui()
        self.update_idletasks()
        self.freeze_default_layout()
        self.logic = DamageWindowLogic(self, db_data)

    def setup_styles(self):
        """
        配置本窗口统一的输入框与下拉框样式。

        功能：自定义 Damage.TEntry 和 Damage.TCombobox 样式，确保输入框
              背景为白色，下拉列表背景也为白色。应用于本窗口的所有 Entry 和 Combobox。

        外部参数：无

        内部参数：
        - self.style: ttk.Style 实例，通过 configure/map 设置样式属性
        """
        self.style.configure("Damage.TEntry", fieldbackground="white")
        self.style.configure(
            "Damage.TCombobox", fieldbackground="white", background="white"
        )
        self.style.map(
            "Damage.TCombobox",
            fieldbackground=[("readonly", "white"), ("!disabled", "white")],
            selectbackground=[("readonly", "white"), ("!disabled", "white")],
            selectforeground=[("readonly", "black"), ("!disabled", "black")],
        )
        self.option_add("*TCombobox*Listbox.background", "white")
        self.option_add("*TCombobox*Listbox.foreground", "black")
        self.option_add("*Entry.background", "white")

    def setup_ui(self):
        """
        搭建界面骨架：精灵区域 → 操作区域 → 技能参数 → 实战属性 → 伤害计算。

        功能：使用 grid 布局创建 5 行 1 列的主框架，依次放置：
          - 行0: pet_area（精灵区域，含双方精灵名和技能输入）
          - 行1: load_frame（操作区域，含技能按钮和阵容加载）
          - 行2: skill_area（技能与环境参数区域）
          - 行3: stats_area（实战属性区域）
          - 行4: result_frame（伤害计算结果区域）

        外部参数：无

        内部参数：
        - self.main_frame: 主容器，grid(row=0, column=0) 填充窗口
        - self.pet_area: 精灵区域 LabelFrame，行0
        - self.load_frame: 操作区域 Frame，行1
        - self.skill_area: 技能与环境参数 LabelFrame，行2
        - self.stats_area: 实战属性 LabelFrame，行3
        - self.result_frame: 伤害计算 LabelFrame，行4
        - self.left_ui: create_identity_panel 返回的左侧 UI 字典
        - self.right_ui: create_identity_panel 返回的右侧 UI 字典
        """
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.columnconfigure(0, weight=1)
        for r in range(5):
            self.main_frame.rowconfigure(r, weight=0)
        self.main_frame.rowconfigure(3, weight=1)  # stats_area 可以垂直扩展

        # ====== 行0: 精灵区域 ======
        self.pet_area = ttk.LabelFrame(self.main_frame, text="精灵区域")
        self.pet_area.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.pet_area.columnconfigure(0, weight=1)
        self.pet_area.columnconfigure(1, weight=1)

        self.left_ui = self.create_identity_panel(
            self.pet_area,
            column=0,
            title="本人",
            name_label_text="精灵名称:",
            skill_label_text="技能名称:",
        )
        self.right_ui = self.create_identity_panel(
            self.pet_area,
            column=1,
            title="对方",
            name_label_text="精灵名称:",
            skill_label_text="技能名称:",
        )

        # ====== 行1: 操作区域 ======
        self.load_frame = ttk.Frame(self.main_frame)
        self.load_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.load_frame.columnconfigure(0, weight=1)
        self.load_frame.columnconfigure(1, weight=0)
        self.load_frame.columnconfigure(2, weight=1)
        self.load_frame.rowconfigure(0, weight=1)
        self.create_action_panel(self.load_frame, self.left_ui, 0, "本人操作")
        button_text = "阵容加载" if self.use_lineup_load else "加载"
        self.load_button = ttk.Button(self.load_frame, text=button_text, width=10)
        self.load_button.grid(row=0, column=1, padx=12)
        self.create_action_panel(self.load_frame, self.right_ui, 2, "对方操作")

        # ====== 行2: 技能与环境参数 ======
        self.skill_area = ttk.LabelFrame(self.main_frame, text="技能与环境参数")
        self.skill_area.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.skill_area.columnconfigure(0, weight=1)
        self.skill_area.columnconfigure(1, weight=1)
        self.create_skill_panel(self.skill_area, self.left_ui, 0, "本人")
        self.create_skill_panel(self.skill_area, self.right_ui, 1, "对方")

        # ====== 行3: 实战属性 ======
        self.stats_area = ttk.LabelFrame(self.main_frame, text="实战属性")
        self.stats_area.grid(row=3, column=0, sticky="nsew", pady=(0, 6))
        self.stats_area.columnconfigure(0, weight=1)
        self.stats_area.columnconfigure(1, weight=1)
        self.stats_area.rowconfigure(0, weight=1)
        self.create_stats_panel(self.stats_area, self.left_ui, 0, "本人")
        self.create_stats_panel(self.stats_area, self.right_ui, 1, "对方")

        # ====== 行4: 伤害计算 ======
        self.result_frame = ttk.LabelFrame(self.main_frame, text="伤害计算")
        self.result_frame.grid(row=4, column=0, sticky="ew")
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.columnconfigure(1, weight=1)
        self.result_frame.columnconfigure(2, weight=1)
        self.result_frame.rowconfigure(0, weight=1)

        left_group = ttk.Frame(self.result_frame)
        left_group.grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.left_to_right_button = ttk.Button(left_group, text="本人开始")
        self.left_to_right_button.pack(side="left", padx=(0, 10))
        self.left_to_right_result = ttk.Label(
            left_group,
            text="造成伤害: 0",
            font=("微软雅黑", 12, "bold"),
            foreground="red",
        )
        self.left_to_right_result.pack(side="left")

        self.reset_button = ttk.Button(self.result_frame, text="重置")
        self.reset_button.grid(row=0, column=1)

        right_group = ttk.Frame(self.result_frame)
        right_group.grid(row=0, column=2, sticky="e", padx=10, pady=10)
        self.right_to_left_result = ttk.Label(
            right_group,
            text="造成伤害: 0",
            font=("微软雅黑", 12, "bold"),
            foreground="blue",
        )
        self.right_to_left_result.pack(side="left", padx=(0, 10))
        self.right_to_left_button = ttk.Button(right_group, text="对方开始")
        self.right_to_left_button.pack(side="left")

    def freeze_default_layout(self):
        """
        记录窗口各区域的默认最小尺寸，防止缩小时过度压缩。

        功能：遍历 main_frame 和所有子面板，调用 _freeze_grid_minsizes
              将当前 grid_bbox 尺寸记录为 grid_columnconfigure/rowconfigure 的 minsize。

        外部参数：无
        内部参数：无
        """
        self._freeze_grid_minsizes(self.main_frame, columns=[0], rows=[0, 1, 2, 3, 4])
        self._freeze_grid_minsizes(self.pet_area, columns=[0, 1], rows=[0])
        self._freeze_grid_minsizes(self.load_frame, columns=[0, 1, 2], rows=[0])
        self._freeze_grid_minsizes(self.skill_area, columns=[0, 1], rows=[0])
        self._freeze_grid_minsizes(self.stats_area, columns=[0, 1], rows=[0])
        self._freeze_grid_minsizes(self.result_frame, columns=[0, 1, 2], rows=[0])

        for panel in (self.left_ui, self.right_ui):
            self._freeze_grid_minsizes(
                panel["top_frame"], columns=[0, 1], rows=[0]
            )
            self._freeze_grid_minsizes(
                panel["name_frame"], columns=[0], rows=[0, 1]
            )
            self._freeze_grid_minsizes(
                panel["skill_input_frame"], columns=[0, 1], rows=[0, 1, 2]
            )
            self._freeze_grid_minsizes(
                panel["action_frame"], columns=[0, 1, 2, 3], rows=[0, 1]
            )
            self._freeze_grid_minsizes(
                panel["skill_param_frame"],
                columns=[0, 1, 2, 3, 4, 5],
                rows=[0, 1, 2],
            )
            self._freeze_grid_minsizes(
                panel["stats_frame"],
                columns=[0, 1, 2, 3, 4, 5],
                rows=[0, 1, 2, 3, 4, 5, 6],
            )

    def _freeze_grid_minsizes(self, widget, columns=None, rows=None):
        """
        将指定 widget 的当前 grid 单元格尺寸记录为最小尺寸。

        功能：读取 widget 的 grid_bbox 获取当前单元格宽度/高度，
              若>0则设为对应列的 minsize / 对应行的 minsize。

        外部参数：
        - widget (ttk.Frame): 要冻结的 grid 容器
        - columns (list): 要冻结的列索引列表
        - rows (list): 要冻结的行索引列表

        内部参数：无
        """
        columns = columns or []
        rows = rows or []
        for column in columns:
            _, _, width, _ = widget.grid_bbox(column, 0)
            if width > 0:
                widget.grid_columnconfigure(column, minsize=width)
        for row in rows:
            _, _, _, height = widget.grid_bbox(0, row)
            if height > 0:
                widget.grid_rowconfigure(row, minsize=height)

    def create_identity_panel(self, parent, column, title, name_label_text, skill_label_text):
        """
        创建单侧精灵身份输入区域（精灵名 + 技能输入 + 候选列表）。

        功能：在一个 LabelFrame 中创建：
          - 顶部: 精灵名称输入（Combobox）+ 4 个技能输入框（Entry）
          - 中部: 精灵候选弹出列表（Listbox）
          - 底部: 技能候选弹出列表（Listbox）
          所有控件引用以 dict 形式返回，供逻辑层访问。

        外部参数：
        - parent (ttk.LabelFrame):
            来源：本文件 setup_ui() 中传入 self.pet_area
            含义：精灵区域 LabelFrame，左右两侧共用一个父容器
        - column (int):
            来源：setup_ui() 中 left=0, right=1
            含义：在父容器 grid 中的列位置
        - title (str):
            来源：setup_ui() 中 "本人" / "对方"
            含义：LabelFrame 的标题文本
        - name_label_text (str):
            来源：setup_ui() 中固定为 "精灵名称:"
            含义：精灵名称标签文本
        - skill_label_text (str):
            来源：setup_ui() 中固定为 "技能名称:"
            含义：技能标签文本

        内部参数：
        - panel_frame: 当前面板的 LabelFrame 容器
        - top_frame: 顶部容器（名称 + 技能输入）
        - name_frame: 名称区域容器
        - name_var: 精灵名称 StringVar
        - name_entry: 精灵名称 Combobox（支持下拉和输入）
        - skill_frame: 技能输入区容器
        - skill_entries: 4 个技能 Entry 列表
        - pet_result_frame/listbox: 精灵候选列表
        - skill_result_frame/listbox: 技能候选列表

        返回值：
        - dict: 包含所有控件引用的字典，键包括:
          "frame", "name_entry", "name_var", "skill_entries",
          "top_frame", "name_frame", "skill_input_frame",
          "pet_result_frame", "pet_result_listbox",
          "skill_result_frame", "skill_result_listbox"
        """
        panel_frame = ttk.LabelFrame(parent, text=title)
        panel_frame.grid(row=0, column=column, sticky="nsew", padx=6, pady=6)
        parent.rowconfigure(0, weight=1)

        top_frame = ttk.Frame(panel_frame)
        top_frame.pack(fill="x", padx=8, pady=(8, 4))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        name_frame = ttk.Frame(top_frame)
        name_frame.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        name_frame.columnconfigure(0, weight=1)

        ttk.Label(name_frame, text=name_label_text).grid(
            row=0, column=0, padx=4, pady=4, sticky="w"
        )
        name_var = tk.StringVar()
        name_entry = ttk.Combobox(
            name_frame,
            width=10,
            state="normal",
            textvariable=name_var,
            style="Damage.TCombobox",
        )
        name_entry.grid(row=1, column=0, padx=4, pady=4, sticky="ew")

        skill_frame = ttk.Frame(top_frame)
        skill_frame.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")
        ttk.Label(skill_frame, text="技能输入区").grid(
            row=0, column=0, columnspan=2, padx=4, pady=(0, 4), sticky="w"
        )
        skill_entries = []
        for skill_index in range(4):
            row_index = (skill_index // 2) + 1
            column_index = skill_index % 2
            skill_entry = ttk.Entry(skill_frame, width=10, style="Damage.TEntry")
            skill_entry.grid(
                row=row_index,
                column=column_index,
                padx=4,
                pady=(0, 4),
                sticky="ew",
            )
            skill_entries.append(skill_entry)

        skill_frame.columnconfigure(0, weight=1)
        skill_frame.columnconfigure(1, weight=1)

        # 精灵候选弹出列表
        pet_result_frame = ttk.Frame(panel_frame)
        pet_result_scrollbar = ttk.Scrollbar(pet_result_frame, orient="vertical")
        pet_result_listbox = tk.Listbox(
            pet_result_frame,
            height=5,
            exportselection=False,
            font=("Arial", 10),
            yscrollcommand=pet_result_scrollbar.set,
        )
        pet_result_scrollbar.config(command=pet_result_listbox.yview)
        pet_result_listbox.pack(side="left", fill="both", expand=True)
        pet_result_scrollbar.pack(side="right", fill="y")

        # 技能候选弹出列表
        skill_result_frame = ttk.Frame(panel_frame)
        skill_result_scrollbar = ttk.Scrollbar(skill_result_frame, orient="vertical")
        skill_result_listbox = tk.Listbox(
            skill_result_frame,
            height=5,
            exportselection=False,
            font=("Arial", 10),
            yscrollcommand=skill_result_scrollbar.set,
        )
        skill_result_scrollbar.config(command=skill_result_listbox.yview)
        skill_result_listbox.pack(side="left", fill="both", expand=True)
        skill_result_scrollbar.pack(side="right", fill="y")

        return {
            "frame": panel_frame,
            "name_entry": name_entry,
            "name_var": name_var,
            "skill_entries": skill_entries,
            "top_frame": top_frame,
            "name_frame": name_frame,
            "skill_input_frame": skill_frame,
            "pet_result_frame": pet_result_frame,
            "pet_result_listbox": pet_result_listbox,
            "skill_result_frame": skill_result_frame,
            "skill_result_listbox": skill_result_listbox,
        }

    def create_action_panel(self, parent, ui_map, column, title):
        """
        创建单侧操作区域（技能按钮 + 愿力/首领化/聚能/退场按钮）。

        功能：在一个 LabelFrame 中创建 4 个技能按钮（技能1~技能4）和
              4 个功能按钮（愿力强化、首领化、聚能、退场），
              将按钮引用写回 ui_map 字典。

        外部参数：
        - parent (ttk.Frame):
            来源：本文件 setup_ui() 中传入 self.load_frame
            含义：操作区域 Frame
        - ui_map (dict):
            来源：setup_ui() 中传入 self.left_ui 或 self.right_ui
            含义：面板 UI 控件引用字典
        - column (int):
            来源：setup_ui() 中传入 0（左侧本人）或 2（右侧对方）
            含义：在父容器 grid 中的列位置
        - title (str):
            来源：setup_ui() 中传入 "本人操作" / "对方操作"
            含义：LabelFrame 标题

        内部参数：
        - action_frame: LabelFrame 容器
        - skill_buttons: 4 个技能按钮列表
        - wish_button / boss_button / energy_button / retreat_button: 功能按钮
        - button_column: 列索引（0-3），用于配置 columnconfigure

        返回值：无（按钮引用写入 ui_map）
        """
        action_frame = ttk.LabelFrame(parent, text=title)
        action_frame.grid(row=0, column=column, sticky="nsew", padx=6, pady=6)

        skill_buttons = []
        for skill_index in range(4):
            button = ttk.Button(action_frame, text=f"技能{skill_index + 1}", width=10)
            button.grid(
                row=skill_index // 4,
                column=skill_index % 4,
                padx=4,
                pady=4,
                sticky="ew",
            )
            skill_buttons.append(button)

        wish_button = ttk.Button(action_frame, text="愿力强化", width=10)
        wish_button.grid(row=1, column=0, padx=4, pady=4, sticky="ew")

        boss_button = ttk.Button(action_frame, text="首领化", width=10)
        boss_button.grid(row=1, column=1, padx=4, pady=4, sticky="ew")

        energy_button = ttk.Button(action_frame, text="聚能", width=10)
        energy_button.grid(row=1, column=2, padx=4, pady=4, sticky="ew")

        retreat_button = ttk.Button(action_frame, text="退场", width=10)
        retreat_button.grid(row=1, column=3, padx=4, pady=4, sticky="ew")

        for button_column in range(4):
            action_frame.columnconfigure(button_column, weight=1)

        ui_map.update(
            {
                "action_frame": action_frame,
                "skill_buttons": skill_buttons,
                "wish_button": wish_button,
                "boss_button": boss_button,
                "energy_button": energy_button,
                "retreat_button": retreat_button,
            }
        )

    def create_skill_panel(self, parent, ui_map, column, title):
        """
        创建单侧技能与环境参数区域。

        功能：在一个 LabelFrame 中创建技能类型、技能属性、技能威力、
              本系加成、属性克制、增减益乘区、连击数、其他修正、耗能 9 个参数输入控件，
              引用写入 ui_map。

        外部参数：
        - parent (ttk.LabelFrame):
            来源：setup_ui() 中传入 self.skill_area
            含义：技能与环境参数 LabelFrame
        - ui_map (dict):
            来源：setup_ui() 中传入 self.left_ui / self.right_ui
            含义：面板 UI 控件引用字典
        - column (int):
            来源：setup_ui() 中传入 0（本人）或 1（对方）
            含义：在父容器 grid 中的列位置
        - title (str):
            来源：setup_ui() 中传入 "本人" / "对方"
            含义：LabelFrame 标题

        内部参数：
        - skill_frame: LabelFrame 容器
        - atk_type: 技能类型 Combobox（物攻/魔攻/状态）
        - atk_attr: 技能属性 Combobox（19 系）
        - power_entry: 技能威力 Entry
        - stab_combo: 本系加成 Combobox（1.25/1）
        - element_combo: 属性克制 Combobox（3/2/1/0.5/0.33）
        - buff_entry / hits_entry / other_entry: 增减益/连击数/其他修正 Entry
        - cost_entry: 耗能 Entry

        返回值：无（控件引用写入 ui_map）
        """
        skill_frame = ttk.LabelFrame(parent, text=title)
        skill_frame.grid(row=0, column=column, sticky="ew", padx=6, pady=6)
        for column_index in range(6):
            skill_frame.columnconfigure(
                column_index, weight=1 if column_index % 2 == 1 else 0
            )

        ttk.Label(skill_frame, text="技能类型").grid(row=0, column=0, padx=4, pady=4)
        atk_type = ttk.Combobox(
            skill_frame,
            values=self.atk_type_values,
            width=8,
            state="readonly",
            style="Damage.TCombobox",
        )
        atk_type.set("物攻")
        atk_type.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(skill_frame, text="技能属性").grid(row=0, column=2, padx=4, pady=4)
        atk_attr = ttk.Combobox(
            skill_frame,
            values=self.attr_values,
            width=8,
            style="Damage.TCombobox",
        )
        atk_attr.set("无")
        atk_attr.grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(skill_frame, text="技能威力").grid(row=0, column=4, padx=4, pady=4)
        power_entry = ttk.Entry(skill_frame, width=6, style="Damage.TEntry")
        power_entry.insert(0, "0")
        power_entry.grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(skill_frame, text="本系加成").grid(row=1, column=0, padx=4, pady=4)
        stab_combo = ttk.Combobox(
            skill_frame,
            values=STAB_OPTIONS,
            width=8,
            state="readonly",
            style="Damage.TCombobox",
        )
        stab_combo.set("1")
        stab_combo.grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(skill_frame, text="属性克制").grid(row=1, column=2, padx=4, pady=4)
        element_combo = ttk.Combobox(
            skill_frame,
            values=ELEMENT_MULT_OPTIONS,
            width=8,
            style="Damage.TCombobox",
        )
        element_combo.set("1")
        element_combo.grid(row=1, column=3, padx=4, pady=4)

        ttk.Label(skill_frame, text="增减益乘区").grid(row=1, column=4, padx=4, pady=4)
        buff_entry = ttk.Entry(skill_frame, width=8, style="Damage.TEntry")
        buff_entry.insert(0, "1")
        buff_entry.grid(row=1, column=5, padx=4, pady=4)

        ttk.Label(skill_frame, text="连击数").grid(row=2, column=0, padx=4, pady=4)
        hits_entry = ttk.Entry(skill_frame, width=8, style="Damage.TEntry")
        hits_entry.insert(0, "1")
        hits_entry.grid(row=2, column=1, padx=4, pady=4)

        ttk.Label(skill_frame, text="其他修正").grid(row=2, column=2, padx=4, pady=4)
        other_entry = ttk.Entry(skill_frame, width=8, style="Damage.TEntry")
        other_entry.insert(0, "1")
        other_entry.grid(row=2, column=3, padx=4, pady=4)

        ttk.Label(skill_frame, text="耗能").grid(row=2, column=4, padx=4, pady=4)
        cost_entry = ttk.Entry(skill_frame, width=8, style="Damage.TEntry")
        cost_entry.insert(0, "0")
        cost_entry.grid(row=2, column=5, padx=4, pady=4)

        ui_map.update(
            {
                "skill_param_frame": skill_frame,
                "atk_type": atk_type,
                "atk_attr": atk_attr,
                "power_entry": power_entry,
                "stab_combo": stab_combo,
                "element_combo": element_combo,
                "buff_entry": buff_entry,
                "hits_entry": hits_entry,
                "other_entry": other_entry,
                "cost_entry": cost_entry,
            }
        )

    def create_stats_panel(self, parent, ui_map, column, title):
        """
        创建单侧实战属性区域（六维面板 + 战斗信息）。

        功能：在一个 LabelFrame 中创建：
          - 6 行属性行，每行含属性名、种族值 Label、个体值 Combobox、
            性格系数 Combobox、面板值 Label
          - 战斗信息区域（当前能量、特性名、特性效果、状态）
          所有控件引用写入 ui_map。

        外部参数：
        - parent (ttk.LabelFrame):
            来源：setup_ui() 中传入 self.stats_area
            含义：实战属性 LabelFrame
        - ui_map (dict):
            来源：setup_ui() 中传入 self.left_ui / self.right_ui
            含义：面板 UI 控件引用字典
        - column (int):
            来源：setup_ui() 中传入 0（本人）或 1（对方）
            含义：在父容器 grid 中的列位置
        - title (str):
            来源：setup_ui() 中传入 "本人" / "对方"
            含义：LabelFrame 标题

        内部参数：
        - stats_frame: LabelFrame 容器
        - headers: 表头列表 ["属性", "种族", "个体", "性格", "面板值"]
        - stats_ui: 六维属性控件字典
        - row: 当前行号（从 1 开始）
        - stat_name: 属性名（来自 STAT_NAMES）
        - base_label: 种族值 Label
        - iv_combo: 个体值 Combobox
        - nature_combo: 性格系数 Combobox
        - result_label: 面板值 Label
        - info_frame: 战斗信息 LabelFrame
        - energy_label: 当前能量 Label
        - trait_name_label: 特性名 Label
        - trait_desc_label: 特性效果 Label
        - status_label: 状态 Label

        返回值：无（控件引用写入 ui_map）
        """
        stats_frame = ttk.LabelFrame(parent, text=title)
        stats_frame.grid(row=0, column=column, sticky="nsew", padx=6, pady=6)
        parent.rowconfigure(0, weight=1)

        headers = ["属性", "种族", "个体", "性格", "面板值"]
        for col, header in enumerate(headers):
            ttk.Label(stats_frame, text=header).grid(
                row=0, column=col, padx=4, pady=4
            )

        stats_ui = {}
        row = 1
        for stat_name in STAT_NAMES:
            ttk.Label(stats_frame, text=stat_name).grid(
                row=row, column=0, padx=4, pady=4
            )

            base_label = ttk.Label(stats_frame, text="0")
            base_label.grid(row=row, column=1, padx=4, pady=4)

            iv_combo = ttk.Combobox(
                stats_frame,
                values=self.iv_values,
                width=4,
                state="readonly",
                style="Damage.TCombobox",
            )
            iv_combo.set("0")
            iv_combo.grid(row=row, column=2, padx=4, pady=4)

            nature_combo = ttk.Combobox(
                stats_frame,
                values=self.nature_values,
                width=5,
                state="readonly",
                style="Damage.TCombobox",
            )
            nature_combo.set("1.0")
            nature_combo.grid(row=row, column=3, padx=4, pady=4)

            result_label = ttk.Label(
                stats_frame,
                text="0",
                foreground="blue",
                font=("Arial", 10, "bold"),
            )
            result_label.grid(row=row, column=4, padx=4, pady=4)

            stats_ui[stat_name] = {
                "base": base_label,
                "iv": iv_combo,
                "nat": nature_combo,
                "res": result_label,
            }
            row += 1

        # 战斗信息区域
        info_frame = ttk.LabelFrame(stats_frame, text="战斗信息")
        info_frame.grid(
            row=1, column=5, rowspan=6, padx=(14, 4), pady=4, sticky="nsew"
        )
        stats_frame.columnconfigure(5, weight=1)
        for row_index in range(1, 7):
            stats_frame.rowconfigure(row_index, weight=1)

        energy_label = ttk.Label(info_frame, text="当前能量：10", anchor="w")
        energy_label.pack(fill="x", padx=8, pady=(8, 4))

        trait_name_label = ttk.Label(info_frame, text="特性：-", anchor="w")
        trait_name_label.pack(fill="x", padx=8, pady=(2, 2))

        trait_desc_label = ttk.Label(
            info_frame,
            text="效果：-",
            anchor="w",
            justify="left",
            wraplength=260,
        )
        trait_desc_label.pack(fill="x", padx=8, pady=(2, 4))

        status_label = ttk.Label(info_frame, text="状态", anchor="w")
        status_label.pack(fill="x", padx=8, pady=(2, 8))

        ui_map.update(
            {
                "stats_frame": stats_frame,
                "stats": stats_ui,
                "energy_label": energy_label,
                "trait_name_label": trait_name_label,
                "trait_desc_label": trait_desc_label,
                "status_label": status_label,
            }
        )
