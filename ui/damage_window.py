import tkinter as tk
from tkinter import ttk

from utils.damage_window_logic import DamageWindowLogic


class DamageWindow(tk.Toplevel):
    def __init__(self, parent, db_data):
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
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vs_frame = ttk.Frame(main_frame)
        vs_frame.pack(fill="both", expand=True)

        self.left_ui = self.create_pet_panel(vs_frame, "本人精灵", "left")
        self.right_ui = self.create_pet_panel(vs_frame, "对方精灵", "right")

        result_frame = ttk.LabelFrame(main_frame, text="伤害计算")
        result_frame.pack(fill="x", pady=10)

        self.left_to_right_button = ttk.Button(result_frame, text="本人打对方")
        self.left_to_right_button.pack(side="left", padx=10, pady=10)

        self.left_to_right_result = ttk.Label(
            result_frame,
            text="本人打对方伤害: 0",
            font=("微软雅黑", 12, "bold"),
            foreground="red",
        )
        self.left_to_right_result.pack(side="left", padx=15)

        self.right_to_left_button = ttk.Button(result_frame, text="对方打本人")
        self.right_to_left_button.pack(side="left", padx=30, pady=10)

        self.right_to_left_result = ttk.Label(
            result_frame,
            text="对方打本人伤害: 0",
            font=("微软雅黑", 12, "bold"),
            foreground="blue",
        )
        self.right_to_left_result.pack(side="left", padx=15)

    def create_pet_panel(self, parent, title, side):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(side=side, fill="both", expand=True, padx=6)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(top_frame, text="精灵名:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        name_entry = ttk.Entry(top_frame, width=14, style="Damage.TEntry")
        name_entry.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        ttk.Label(top_frame, text="技能名:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        skill_entry = ttk.Entry(top_frame, width=18, style="Damage.TEntry")
        skill_entry.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        load_button = ttk.Button(top_frame, text="加载", width=6)
        load_button.grid(row=0, column=4, padx=4, pady=4)

        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(3, weight=1)

        pet_result_frame = ttk.Frame(frame)
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

        skill_result_frame = ttk.Frame(frame)
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

        skill_frame = ttk.LabelFrame(frame, text="技能与环境参数")
        skill_frame.pack(fill="x", padx=8, pady=6)

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

        stats_frame = ttk.LabelFrame(frame, text="实战属性")
        stats_frame.pack(fill="both", expand=True, padx=8, pady=(6, 8))

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

        return {
            "frame": frame,
            "name_entry": name_entry,
            "skill_entry": skill_entry,
            "load_button": load_button,
            "top_frame": top_frame,
            "pet_result_frame": pet_result_frame,
            "pet_result_listbox": pet_result_listbox,
            "skill_result_frame": skill_result_frame,
            "skill_result_listbox": skill_result_listbox,
            "atk_type": atk_type,
            "atk_attr": atk_attr,
            "power_entry": power_entry,
            "stab_combo": stab_combo,
            "element_combo": element_combo,
            "buff_entry": buff_entry,
            "hits_entry": hits_entry,
            "other_entry": other_entry,
            "stats": stats_ui,
        }
