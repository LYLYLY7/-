import tkinter as tk
from tkinter import ttk

from utils.main_window_logic import MainWindowLogic

class PetApp:
    def __init__(self, root, data_manager):
        self.root = root
        self.IV_OPTIONS = ["0", "7", "8", "9", "10"]
        self.NATURE_OPTIONS = ["0.9", "1.0", "1.1", "1.2"]

        self.setup_ui()
        self.logic = MainWindowLogic(self, data_manager)

    def setup_ui(self):
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        ally_panel = ttk.LabelFrame(left_frame, text="己方阵容")
        ally_panel.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.ally_lineup_selector = tk.Listbox(ally_panel, width=20, font=('Arial', 10), exportselection=False)
        self.ally_lineup_selector.pack(padx=5, pady=5, fill="both", expand=True)

        self.ally_new_lineup_button = ttk.Button(ally_panel, text="新建阵容")
        self.ally_new_lineup_button.pack(fill="x", padx=5, pady=2)
        self.ally_delete_lineup_button = ttk.Button(ally_panel, text="删除阵容")
        self.ally_delete_lineup_button.pack(fill="x", padx=5, pady=2)

        enemy_panel = ttk.LabelFrame(left_frame, text="对方阵容")
        enemy_panel.pack(side="bottom", fill="both", expand=True, padx=5, pady=5)

        self.enemy_lineup_selector = tk.Listbox(enemy_panel, width=20, font=('Arial', 10), exportselection=False)
        self.enemy_lineup_selector.pack(padx=5, pady=5, fill="both", expand=True)

        self.enemy_new_lineup_button = ttk.Button(enemy_panel, text="新建阵容")
        self.enemy_new_lineup_button.pack(fill="x", padx=5, pady=2)
        self.enemy_delete_lineup_button = ttk.Button(enemy_panel, text="删除阵容")
        self.enemy_delete_lineup_button.pack(fill="x", padx=5, pady=2)

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side="right", fill="both", expand=True)

        self.top_f = ttk.LabelFrame(right_panel, text="第一步：选择精灵")
        self.top_f.pack(fill="x", padx=10, pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.top_f, textvariable=self.search_var, font=('Arial', 11), style="White.TEntry")
        self.search_entry.pack(padx=10, pady=10, fill="x", expand=True)

        style = ttk.Style(self.root)
        style.configure("White.TCombobox", fieldbackground="white", background="white")
        style.map("White.TCombobox",
                  fieldbackground=[('readonly', 'white')],
                  background=[('readonly', 'white')])
        style.configure("White.TEntry", fieldbackground="white", background="white")

        self.pet_result_frame = ttk.Frame(right_panel)
        self.pet_result_scrollbar = ttk.Scrollbar(self.pet_result_frame, orient="vertical")
        self.pet_result_listbox = tk.Listbox(
            self.pet_result_frame,
            height=6,
            exportselection=False,
            font=("Arial", 10),
            yscrollcommand=self.pet_result_scrollbar.set
        )
        self.pet_result_scrollbar.config(command=self.pet_result_listbox.yview)
        self.pet_result_listbox.pack(side="left", fill="both", expand=True)
        self.pet_result_scrollbar.pack(side="right", fill="y")

        mid_f = ttk.Frame(right_panel)
        mid_f.pack(fill="both", expand=True)

        self.attr_f = ttk.LabelFrame(mid_f, text="第二步：数值配置")
        self.attr_f.pack(side="left", fill="both", expand=True, padx=10)
        self.inputs = {}
        headers = ["属性", "属性值", "个体值", "性格系数", "面板值"]
        for col, header in enumerate(headers):
            ttk.Label(self.attr_f, text=header, font=('Arial', 9, 'bold')).grid(row=0, column=col, pady=(10, 5), padx=5)

        stats = ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]
        for i, stat in enumerate(stats):
            row_idx = i + 1
            ttk.Label(self.attr_f, text=stat).grid(row=row_idx, column=0, pady=10, padx=5)
            base_l = ttk.Label(self.attr_f, text="-", width=5)
            base_l.grid(row=row_idx, column=1)
            
            iv_c = ttk.Combobox(self.attr_f, values=self.IV_OPTIONS, width=5, state="readonly", style="White.TCombobox")
            iv_c.set("0")
            iv_c.grid(row=row_idx, column=2, padx=5)
            
            nat_c = ttk.Combobox(self.attr_f, values=self.NATURE_OPTIONS, width=5, state="readonly", style="White.TCombobox")
            nat_c.set("1.0")
            nat_c.grid(row=row_idx, column=3, padx=5)
            
            res_l = ttk.Label(self.attr_f, text="0", foreground="blue", font=('Arial', 11, 'bold'))
            res_l.grid(row=row_idx, column=4, padx=10)
            self.inputs[stat] = {"base": base_l, "iv": iv_c, "nat": nat_c, "res": res_l}

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

        self.skill_result_frame = ttk.Frame(self.skill_f)
        self.skill_result_scrollbar = ttk.Scrollbar(self.skill_result_frame, orient="vertical")
        self.skill_result_listbox = tk.Listbox(
            self.skill_result_frame,
            height=6,
            exportselection=False,
            font=("Arial", 10),
            yscrollcommand=self.skill_result_scrollbar.set
        )
        self.skill_result_scrollbar.config(command=self.skill_result_listbox.yview)
        self.skill_result_listbox.pack(side="left", fill="both", expand=True)
        self.skill_result_scrollbar.pack(side="right", fill="y")

        self.skill_footer_separator = ttk.Separator(self.skill_f, orient="horizontal")
        self.skill_footer_separator.pack(fill="x", pady=10, padx=5)
        self.open_damage_button = ttk.Button(self.skill_f, text="实战伤害计算")
        self.open_damage_button.pack(fill="x", padx=10, pady=5)

        bottom_f = ttk.LabelFrame(right_panel, text="当前选中阵容的精灵名单")
        bottom_f.pack(fill="both", expand=True, padx=10, pady=10)

        list_frame = ttk.Frame(bottom_f)
        list_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal")
        scroll_x.pack(side="bottom", fill="x")
        
        scroll_y = ttk.Scrollbar(list_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        self.pet_listbox = tk.Listbox(list_frame, height=8, selectmode="browse", exportselection=False,
                                      xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set, font=('Arial', 10))
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
