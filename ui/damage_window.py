import tkinter as tk
from tkinter import ttk

from utils.damage_window_logic import DamageWindowLogic


class DamageWindow(tk.Toplevel):
    def __init__(self, parent, db_data):
        """实战伤害推演窗口。

        外部参数来源：
        - parent: 由主窗口传入，作为本窗口父级。
        - db_data: 由数据管理层传入的精灵数据库字典。
        """
        super().__init__(parent)
        self.title("实战伤害推演计算器")
        self.geometry("1180x720")

        self.atk_type_values = ["物攻", "魔攻", "状态"]
        self.attr_values = ["无", "普通", "火", "水", "草", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"]
        self.iv_values = ["0", "7", "8", "9", "10"]
        self.nature_values = ["0.9", "1.0", "1.1", "1.2"]
        self.style = ttk.Style(self)

        self.setup_styles()
        self.setup_ui()
        self.logic = DamageWindowLogic(self, db_data)

    def setup_styles(self):
        """配置本窗口统一的输入框与下拉框样式。"""
        self.style.configure("Damage.TEntry", fieldbackground="white")
        self.style.configure("Damage.TCombobox", fieldbackground="white", background="white")
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
        """搭建界面骨架：精灵区域 -> 加载 -> 参数 -> 属性 -> 伤害计算。"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        pet_area = ttk.LabelFrame(main_frame, text="精灵区域")
        pet_area.pack(fill="x", pady=(0, 6))
        pet_area.columnconfigure(0, weight=1)
        pet_area.columnconfigure(1, weight=1)

        self.left_ui = self.create_identity_panel(
            pet_area,
            column=0,
            title="本人",
            name_label_text="本人精灵名:",
            skill_label_text="本人技能名:",
        )
        self.right_ui = self.create_identity_panel(
            pet_area,
            column=1,
            title="对方",
            name_label_text="对方精灵名:",
            skill_label_text="对方技能名:",
        )

        load_frame = ttk.Frame(main_frame)
        load_frame.pack(fill="x", pady=(0, 6))
        load_frame.columnconfigure(0, weight=1)
        load_frame.rowconfigure(0, weight=1)
        load_frame.configure(height=50)
        load_frame.pack_propagate(False)
        self.load_all_button = ttk.Button(load_frame, text="加载", width=10)
        self.load_all_button.grid(row=0, column=0)

        skill_area = ttk.LabelFrame(main_frame, text="技能与环境参数")
        skill_area.pack(fill="x", pady=(0, 6))
        skill_area.columnconfigure(0, weight=1)
        skill_area.columnconfigure(1, weight=1)
        self.create_skill_panel(skill_area, self.left_ui, 0, "本人")
        self.create_skill_panel(skill_area, self.right_ui, 1, "对方")

        stats_area = ttk.LabelFrame(main_frame, text="实战属性")
        stats_area.pack(fill="both", expand=True, pady=(0, 6))
        stats_area.columnconfigure(0, weight=1)
        stats_area.columnconfigure(1, weight=1)
        self.create_stats_panel(stats_area, self.left_ui, 0, "本人")
        self.create_stats_panel(stats_area, self.right_ui, 1, "对方")

        result_frame = ttk.LabelFrame(main_frame, text="伤害计算")
        result_frame.pack(fill="x")
        result_frame.columnconfigure(0, weight=1)
        result_frame.columnconfigure(1, weight=1)
        result_frame.columnconfigure(2, weight=1)
        result_frame.rowconfigure(0, weight=1)

        left_group = ttk.Frame(result_frame)
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

        self.reset_button = ttk.Button(result_frame, text="重置")
        self.reset_button.grid(row=0, column=1)

        right_group = ttk.Frame(result_frame)
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

    def create_identity_panel(self, parent, column, title, name_label_text, skill_label_text):
        """创建精灵输入区域（精灵名/技能名 + 两个候选列表框）。

        参数来源说明（文件+代码位置）：
        - parent / column / title / name_label_text / skill_label_text：
          - 来源文件：`ui/damage_window.py`
          - 调用位置：`setup_ui()` 中两处调用 `self.create_identity_panel(...)`
            （约在本文件 53-66 行代码段，左侧本人与右侧对方各一次）。
        """
        panel_frame = ttk.LabelFrame(parent, text=title)
        panel_frame.grid(row=0, column=column, sticky="nsew", padx=6, pady=6)

        top_frame = ttk.Frame(panel_frame)
        top_frame.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(top_frame, text=name_label_text).grid(row=0, column=0, padx=4, pady=4, sticky="w")
        name_entry = ttk.Entry(top_frame, width=14, style="Damage.TEntry")
        name_entry.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        ttk.Label(top_frame, text=skill_label_text).grid(row=0, column=2, padx=4, pady=4, sticky="w")
        skill_entry = ttk.Entry(top_frame, width=18, style="Damage.TEntry")
        skill_entry.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(3, weight=1)

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
            "skill_entry": skill_entry,
            "top_frame": top_frame,
            "pet_result_frame": pet_result_frame,
            "pet_result_listbox": pet_result_listbox,
            "skill_result_frame": skill_result_frame,
            "skill_result_listbox": skill_result_listbox,
        }

    def create_skill_panel(self, parent, ui_map, column, title):
        """创建技能与环境参数区域，并把控件引用写回 ui_map。

        参数来源说明（文件+代码位置）：
        - parent / ui_map / column / title：
          - 来源文件：`ui/damage_window.py`
          - 调用位置：`setup_ui()` 中两处 `self.create_skill_panel(...)`
            （约在本文件 81-82 行代码段，分别传入 left_ui/right_ui）。
        """
        skill_frame = ttk.LabelFrame(parent, text=title)
        skill_frame.grid(row=0, column=column, sticky="ew", padx=6, pady=6)

        ttk.Label(skill_frame, text="技能类型").grid(row=0, column=0, padx=4, pady=4)
        atk_type = ttk.Combobox(skill_frame, values=self.atk_type_values, width=8, state="readonly", style="Damage.TCombobox")
        atk_type.set("物攻")
        atk_type.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(skill_frame, text="技能属性").grid(row=0, column=2, padx=4, pady=4)
        atk_attr = ttk.Combobox(skill_frame, values=self.attr_values, width=8, style="Damage.TCombobox")
        atk_attr.set("无")
        atk_attr.grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(skill_frame, text="技能威力").grid(row=0, column=4, padx=4, pady=4)
        power_entry = ttk.Entry(skill_frame, width=6, style="Damage.TEntry")
        power_entry.insert(0, "0")
        power_entry.grid(row=0, column=5, padx=4, pady=4)

        ttk.Label(skill_frame, text="本系加成").grid(row=1, column=0, padx=4, pady=4)
        stab_combo = ttk.Combobox(skill_frame, values=["1.25", "1"], width=8, state="readonly", style="Damage.TCombobox")
        stab_combo.set("1")
        stab_combo.grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(skill_frame, text="属性克制").grid(row=1, column=2, padx=4, pady=4)
        element_combo = ttk.Combobox(skill_frame, values=["3", "2", "1", "0.5", "0.33"], width=8, style="Damage.TCombobox")
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
        """创建实战属性区域，并把统计控件引用写回 ui_map。

        参数来源说明（文件+代码位置）：
        - parent / ui_map / column / title：
          - 来源文件：`ui/damage_window.py`
          - 调用位置：`setup_ui()` 中两处 `self.create_stats_panel(...)`
            （约在本文件 88-89 行代码段，分别传入 left_ui/right_ui）。
        """
        stats_frame = ttk.LabelFrame(parent, text=title)
        stats_frame.grid(row=0, column=column, sticky="nsew", padx=6, pady=6)

        headers = ["属性", "种族", "个体", "性格", "面板值"]
        for col, header in enumerate(headers):
            ttk.Label(stats_frame, text=header).grid(row=0, column=col, padx=4, pady=4)

        stats_ui = {}
        row = 1
        for stat_name in ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]:
            ttk.Label(stats_frame, text=stat_name).grid(row=row, column=0, padx=4, pady=4)

            base_label = ttk.Label(stats_frame, text="0")
            base_label.grid(row=row, column=1, padx=4, pady=4)

            iv_combo = ttk.Combobox(stats_frame, values=self.iv_values, width=4, state="readonly", style="Damage.TCombobox")
            iv_combo.set("0")
            iv_combo.grid(row=row, column=2, padx=4, pady=4)

            nature_combo = ttk.Combobox(stats_frame, values=self.nature_values, width=5, state="readonly", style="Damage.TCombobox")
            nature_combo.set("1.0")
            nature_combo.grid(row=row, column=3, padx=4, pady=4)

            result_label = ttk.Label(stats_frame, text="0", foreground="blue", font=("Arial", 10, "bold"))
            result_label.grid(row=row, column=4, padx=4, pady=4)

            stats_ui[stat_name] = {
                "base": base_label,
                "iv": iv_combo,
                "nat": nature_combo,
                "res": result_label,
            }
            row += 1

        info_frame = ttk.LabelFrame(stats_frame, text="战斗信息")
        info_frame.grid(row=1, column=5, rowspan=6, padx=(14, 4), pady=4, sticky="nsew")
        stats_frame.columnconfigure(5, weight=1)

        energy_label = ttk.Label(info_frame, text="当前能量：10", anchor="w")
        energy_label.pack(fill="x", padx=8, pady=(8, 4))

        trait_name_label = ttk.Label(info_frame, text="特性：-", anchor="w")
        trait_name_label.pack(fill="x", padx=8, pady=(2, 2))

        trait_desc_label = ttk.Label(info_frame, text="效果：-", anchor="w", justify="left", wraplength=260)
        trait_desc_label.pack(fill="x", padx=8, pady=(2, 4))

        status_label = ttk.Label(info_frame, text="状态", anchor="w")
        status_label.pack(fill="x", padx=8, pady=(2, 8))

        ui_map.update(
            {
                "stats": stats_ui,
                "energy_label": energy_label,
                "trait_name_label": trait_name_label,
                "trait_desc_label": trait_desc_label,
                "status_label": status_label,
            }
        )
