"""
主窗口业务逻辑模块。

功能：定义 MainWindowLogic 类，处理主窗口（PetApp）的所有事件响应和业务逻辑，
      包括阵容增删改查、精灵搜索/加载、技能搜索/加载、数值实时计算、阵容保存、
      打开伤害推演窗口等。
外部依赖：
- ui/damage_window.py: DamageWindow 类（实战伤害推演窗口）
- utils/calculator.py: calc_stat() 面板属性计算
- utils/constants.py: SKILL_CATEGORY_KEYS（技能分类键名）
- utils/ui_helpers.py: ask_lineup_name()（阵容名称输入对话框）
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ui.damage_window import DamageWindow
from utils.calculator import calc_stat
from utils.constants import SKILL_CATEGORY_KEYS
from utils.ui_helpers import ask_lineup_name


class MainWindowLogic:
    """
    主窗口业务逻辑类。

    功能：绑定 PetApp UI 控件的事件回调，处理：
          - 阵容浏览（on_lineup_change）/ 新建（add_new_lineup）/ 删除（delete_lineup）
          - 精灵搜索输入（绑 KeyRelease 实时过滤，Return/Double-Click 确认）
          - 精灵加载（load_pet）：加载数据库中的精灵数据到数值配置区
          - 技能搜索输入（绑 KeyRelease 实时过滤，Return/Double-Click 确认）
          - 面板属性实时计算（update_calc）：个体值/性格系数变化时自动刷新
          - 精灵加入阵容（add_pet_to_ally / add_pet_to_enemy）
          - 精灵删除（delete_selected_pet）/ 阵容保存（save_to_disk）
          - 实战伤害推演窗口（open_damage_calculator）

    外部参数：
    - view (PetApp):
        来源文件：ui/main_window.py PetApp.__init__() 中创建
        含义：主窗口 UI 实例，包含所有控件引用
    - data_manager (DataManager):
        来源文件：main.py 中创建的 DataManager 实例
        含义：数据管理器，用于读写精灵数据库和阵容 JSON 文件

    内部参数：
    - self.root: 根窗口（view.root）
    - self.dm: 数据管理器
    - self.db: 精灵数据库字典 {名字: 数据}（从 all_pets_data.json 加载）
    - self.all_lineups: 阵容数据字典（从 all_lineups.json 加载）
    - self.current_pet_data: 当前选中的精灵完整数据
    - self.full_skill_pool: 当前精灵的全部技能名称列表（已排序去重）
    - self.pet_search_candidates: 精灵搜索候选列表
    - self.active_skill_index: 当前激活的技能输入框索引（0-3）
    - self.current_side: 当前选中的阵容侧（"己方" / "对方" / None）
    """

    def __init__(self, view, data_manager):
        """
        初始化业务逻辑：加载数据库、阵容数据、绑定事件、刷新列表。

        外部参数：
        - view / data_manager: 见类文档

        内部参数：
        - self.db: 通过 self.dm.load_pet_db() 加载
        - self.all_lineups: 通过 self.dm.load_lineups() 加载
        """
        self.view = view
        self.root = view.root
        self.dm = data_manager

        self.db = self.dm.load_pet_db()
        self.all_lineups = self.dm.load_lineups()
        self.current_pet_data = None
        self.full_skill_pool = []
        self.pet_search_candidates = []
        self.active_skill_index = None
        self.current_side = None

        self.bind_events()
        self.refresh_ally_lineup_list()
        self.refresh_enemy_lineup_list()

    def bind_events(self):
        """
        绑定 PetApp 中所有控件的事件和回调。

        功能：将 MainWindowLogic 的方法绑定到 PetApp 的控件事件：
          - 阵容 Listbox: <<ListboxSelect>> 触发 on_lineup_change
          - 阵容按钮: config(command=...) 绑定新建/删除方法
          - 伤害计算按钮: 绑定 open_damage_calculator
          - 精灵操作按钮: 绑定 add/delete/save 方法
          - 搜索框: 绑定 KeyRelease/Return/Down/FocusOut 事件
          - 精灵候选 Listbox: 绑定 Click/Return/DoubleClick
          - 个体/性格下拉框: 绑定 <<ComboboxSelected>> 触发 update_calc
          - 技能输入框: 绑定 KeyRelease/Return/Down/FocusOut 事件
          - 技能候选 Listbox: 绑定 Click/Return/DoubleClick

        外部参数：无（使用 self.view 中的控件引用）

        内部参数：无
        """
        # --- 阵容选择事件 ---
        self.view.ally_lineup_selector.bind(
            "<<ListboxSelect>>", lambda event: self.on_lineup_change("己方")
        )
        self.view.enemy_lineup_selector.bind(
            "<<ListboxSelect>>", lambda event: self.on_lineup_change("对方")
        )

        # --- 阵容操作按钮 ---
        self.view.ally_new_lineup_button.config(
            command=lambda: self.add_new_lineup("己方")
        )
        self.view.ally_delete_lineup_button.config(
            command=lambda: self.delete_lineup("己方")
        )
        self.view.enemy_new_lineup_button.config(
            command=lambda: self.add_new_lineup("对方")
        )
        self.view.enemy_delete_lineup_button.config(
            command=lambda: self.delete_lineup("对方")
        )

        # --- 功能按钮 ---
        self.view.open_damage_button.config(command=self.open_damage_calculator)
        self.view.add_ally_button.config(command=self.add_pet_to_ally)
        self.view.add_enemy_button.config(command=self.add_pet_to_enemy)
        self.view.delete_pet_button.config(command=self.delete_selected_pet)
        self.view.save_button.config(command=self.save_to_disk)

        # --- 精灵搜索输入事件 ---
        self.view.search_entry.bind("<KeyRelease>", self.on_pet_type)
        self.view.search_entry.bind("<Return>", self.confirm_pet_input)
        self.view.search_entry.bind("<Down>", self.focus_pet_popup)
        self.view.search_entry.bind("<FocusOut>", self.on_pet_entry_focus_out)

        # --- 精灵候选列表事件 ---
        self.view.pet_result_listbox.bind(
            "<ButtonRelease-1>", self.on_pet_popup_click
        )
        self.view.pet_result_listbox.bind("<Return>", self.on_pet_popup_confirm)
        self.view.pet_result_listbox.bind(
            "<Double-Button-1>", self.on_pet_popup_confirm
        )

        # --- 个体/性格下拉更新事件 ---
        for stat, widgets in self.view.inputs.items():
            widgets["iv"].bind(
                "<<ComboboxSelected>>", lambda event: self.update_calc()
            )
            widgets["nat"].bind(
                "<<ComboboxSelected>>", lambda event: self.update_calc()
            )

        # --- 技能输入事件 ---
        for idx, entry in enumerate(self.view.skill_entries):
            entry.bind(
                "<KeyRelease>", lambda event, i=idx: self.on_skill_type(event, i)
            )
            entry.bind(
                "<Return>", lambda event, i=idx: self.confirm_skill_input(i)
            )
            entry.bind(
                "<Down>", lambda event, i=idx: self.focus_skill_popup(i)
            )
            entry.bind("<FocusOut>", self.on_skill_entry_focus_out)

        # --- 技能候选列表事件 ---
        self.view.skill_result_listbox.bind(
            "<ButtonRelease-1>", self.on_skill_popup_click
        )
        self.view.skill_result_listbox.bind(
            "<Return>", self.on_skill_popup_confirm
        )
        self.view.skill_result_listbox.bind(
            "<Double-Button-1>", self.on_skill_popup_confirm
        )

    # ==================== 伤害计算窗口 ====================

    def open_damage_calculator(self):
        """
        打开实战伤害推演窗口（独立模式），并隐藏主窗口。

        功能：创建 DamageWindow 实例，传入 use_lineup_load=True 启用阵容加载模式，
              主窗口调用 withdraw() 隐藏。
              绑定 WM_DELETE_WINDOW 协议：关闭伤害窗口时调用 self.root.destroy() 关闭整个程序。

        外部参数：无（使用 self.db 和 self.root）

        内部参数：
        - dw: DamageWindow 实例

        返回值：无
        """
        if not self.db:
            messagebox.showwarning("提示", "精灵数据库为空，请先同步数据！")
            return
        dw = DamageWindow(self.root, self.db, use_lineup_load=True)
        self.root.withdraw()
        dw.protocol("WM_DELETE_WINDOW", self.root.destroy)

    # ==================== 阵容管理 ====================

    def delete_selected_pet(self):
        """
        从当前选中的阵容中删除指定精灵。

        功能：检查是否有选中阵容和选中精灵，从 all_lineups 中移除该精灵条目，
              调用 dm.save_lineups 持久化，刷新阵容显示。

        外部参数：无（使用 self.current_side / self.view.pet_listbox 等）

        内部参数：
        - selector: 当前侧对应的阵容 Listbox
        - lineup_name: 当前选中的阵容名称
        - pet_idx: 要删除的精灵在阵容中的索引
        """
        if not self.current_side:
            messagebox.showwarning("提示", "请先选择一个阵容")
            return
        pet_indices = self.view.pet_listbox.curselection()
        if not pet_indices:
            messagebox.showwarning("提示", "请先在名单中点击选中一只精灵")
            return
        selector = (
            self.view.ally_lineup_selector
            if self.current_side == "己方"
            else self.view.enemy_lineup_selector
        )
        lineup_name = selector.get(selector.curselection()[0])
        pet_idx = pet_indices[0]
        self.all_lineups[self.current_side][lineup_name].pop(pet_idx)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change(self.current_side)

    def save_to_disk(self):
        """
        保存所有阵容数据到文件。

        功能：调用 dm.save_lineups() 将当前内存中的 all_lineups 写入 JSON 文件。

        外部参数：无（使用 self.all_lineups）

        返回值：无
        """
        self.dm.save_lineups(self.all_lineups)
        messagebox.showinfo("成功", "所有阵容已同步至 data 目录")

    def on_lineup_change(self, side):
        """
        当用户在阵容 Listbox 中选择一个阵容时触发。

        功能：重新从文件加载阵容数据（同步多窗口修改），切换 current_side，
              清空对方的高亮，在 pet_listbox 中显示选中阵容的精灵列表
              （含实战属性和技能配置摘要）。

        外部参数：
        - side (str):
            来源：bind_events() 中 <<ListboxSelect>> 事件回调传入 "己方" 或 "对方"
            含义：当前操作的是己方还是对方阵容

        内部参数：
        - selector: 当前侧阵容 Listbox
        - selection: 当前选中的条目索引
        - lineup_name: 选中条目的阵容名称
        - pet: 阵容中的精灵条目 dict
        - stats: 精灵的实战属性 dict
        - stats_str: 属性格式化字符串
        - skills: 精灵的技能配置列表
        - skills_str: 技能格式化字符串
        """
        self.all_lineups = self.dm.load_lineups()
        self.current_side = side
        if side == "己方":
            self.view.enemy_lineup_selector.selection_clear(0, tk.END)
        else:
            self.view.ally_lineup_selector.selection_clear(0, tk.END)

        selector = (
            self.view.ally_lineup_selector
            if side == "己方"
            else self.view.enemy_lineup_selector
        )
        self.view.pet_listbox.delete(0, tk.END)
        selection = selector.curselection()
        if not selection:
            self.current_side = None
            return

        lineup_name = selector.get(selection[0])
        for pet in self.all_lineups[side].get(lineup_name, []):
            stats = pet.get("实战属性", {})
            stats_str = " ".join([f"{k}:{v}" for k, v in stats.items()])
            skills = pet.get("技能配置", [])
            skills_str = " | ".join(
                [s["名称"] for s in skills if s.get("名称")]
            )
            if not skills_str:
                skills_str = "未携带技能"
            display_text = (
                f"【{pet['名字']}】 属性: [{stats_str}] 技能: [{skills_str}]"
            )
            self.view.pet_listbox.insert(tk.END, display_text)

    # ==================== 面板计算 ====================

    def update_calc(self):
        """
        按当前个体值/性格系数重新计算并刷新所有面板值。

        功能：遍历六维属性，对每项调用 calc_stat() 计算面板值，
              将结果显示在对应的 result Label 上。

        外部参数：无（使用 self.view.inputs 中的控件值 + self.current_pet_data）

        内部参数：
        - stat: 属性名
        - widgets: 当前属性的控件字典 {"base", "iv", "nat", "res"}
        - value: calc_stat() 返回的面板值
        """
        if not self.current_pet_data:
            return
        for stat, widgets in self.view.inputs.items():
            value = calc_stat(
                widgets["base"].cget("text"),
                widgets["iv"].get(),
                widgets["nat"].get(),
                stat == "生命",
            )
            widgets["res"].config(text=str(value))

    def reset_current_pet_state(self):
        """
        切换精灵前，清空上一只精灵遗留的输入状态。

        功能：将 current_pet_data 置空，清空技能池，隐藏技能弹出列表，
              重置六维属性的种族值显示、个体值/性格系数下拉、面板值，
              清空 4 个技能输入框内容。

        外部参数：无
        内部参数：无
        """
        self.current_pet_data = None
        self.full_skill_pool = []
        self.hide_skill_popup()
        for stat, widgets in self.view.inputs.items():
            widgets["base"].config(text="-")
            widgets["iv"].set("0")
            widgets["nat"].set("1.0")
            widgets["res"].config(text="0")
        for skill_var in self.view.skill_vars:
            skill_var.set("")

    # ==================== 阵容列表刷新 ====================

    def refresh_lineup_list(self):
        """刷新左侧阵容列表（兼容旧版单列表模式，当前未使用）。"""
        self.view.lineup_selector.delete(0, tk.END)
        for name in self.all_lineups.keys():
            self.view.lineup_selector.insert(tk.END, name)

    def refresh_ally_lineup_list(self):
        """
        刷新己方阵容 Listbox。

        功能：清空 ally_lineup_selector，将 self.all_lineups["己方"] 中的所有
              阵容名称（键名）插入列表。
        """
        self.view.ally_lineup_selector.delete(0, tk.END)
        for name in self.all_lineups["己方"].keys():
            self.view.ally_lineup_selector.insert(tk.END, name)

    def refresh_enemy_lineup_list(self):
        """
        刷新对方阵容 Listbox。

        功能：清空 enemy_lineup_selector，将 self.all_lineups["对方"] 中的所有
              阵容名称（键名）插入列表。
        """
        self.view.enemy_lineup_selector.delete(0, tk.END)
        for name in self.all_lineups["对方"].keys():
            self.view.enemy_lineup_selector.insert(tk.END, name)

    # ==================== 新建/删除阵容 ====================

    def add_new_lineup(self, side):
        """
        为指定侧添加一个新的空阵容。

        功能：调用 ui_helpers.ask_lineup_name() 弹出对话框获取名称，
              名称非空且不重复时在 all_lineups 中添加新条目并持久化，
              刷新对应侧的阵容列表。

        外部参数：
        - side (str):
            来源：按钮 command lambda 传入 "己方" 或 "对方"
            含义：添加阵容的目标侧

        内部参数：
        - new_name: 用户输入的新阵容名称
        """
        new_name = ask_lineup_name(self.root)
        if new_name and new_name not in self.all_lineups[side]:
            self.all_lineups[side][new_name] = []
            self.dm.save_lineups(self.all_lineups)
            if side == "己方":
                self.refresh_ally_lineup_list()
            else:
                self.refresh_enemy_lineup_list()

    def delete_lineup(self, side):
        """
        删除指定侧当前选中的阵容。

        功能：获取当前选中的阵容名称，从 all_lineups 中移除，
              持久化，刷新列表，清空精灵名单显示。

        外部参数：
        - side (str):
            来源：按钮 command lambda 传入 "己方" 或 "对方"
            含义：删除阵容的目标侧

        内部参数：
        - selector: 当前侧阵容 Listbox
        - selection: 当前选中的索引
        - name: 要删除的阵容名称
        """
        selector = (
            self.view.ally_lineup_selector
            if side == "己方"
            else self.view.enemy_lineup_selector
        )
        selection = selector.curselection()
        if selection:
            name = selector.get(selection[0])
            del self.all_lineups[side][name]
            self.dm.save_lineups(self.all_lineups)
            if side == "己方":
                self.refresh_ally_lineup_list()
            else:
                self.refresh_enemy_lineup_list()
            self.view.pet_listbox.delete(0, tk.END)
            self.current_side = None

    # ==================== 精灵加载 ====================

    def load_pet(self):
        """
        从数据库加载当前搜索框中指定的精灵数据到 UI 面板。

        功能：获取搜索框文本，在 db 中查找精灵。找到后将基础属性加载到
              数值配置区，构建技能名称池（从精灵技能/血脉技能/技能石中提取），
              调用 update_calc() 刷新面板值。

        外部参数：无（使用 self.view.search_var 和 self.db）

        内部参数：
        - name: 搜索框中的精灵名称
        - pool: 当前精灵的全部技能名称列表（合并三个技能分类后去重排序）
        - key: SKILL_CATEGORY_KEYS 中的技能分类键名
        - skill: 技能 dict
        """
        name = self.view.search_var.get().strip()
        self.hide_pet_popup()
        self.reset_current_pet_state()
        if name in self.db:
            self.current_pet_data = self.db[name]
            for stat, widgets in self.view.inputs.items():
                widgets["base"].config(
                    text=str(self.current_pet_data["基础属性"].get(stat, 0))
                )

            # 从所有技能分类中提取技能名称
            pool = []
            for key in SKILL_CATEGORY_KEYS:
                pool.extend(
                    [
                        skill["技能名称"]
                        for skill in self.current_pet_data.get(key, [])
                    ]
                )
            self.full_skill_pool = sorted(list(set(pool)))
            self.update_calc()
        else:
            messagebox.showwarning("提示", "未找到该精灵")

    # ==================== 精灵搜索弹出列表 ====================

    def on_pet_type(self, event):
        """
        精灵搜索框的键盘输入事件处理。

        功能：按按键类型分发：
          - Return → confirm_pet_input
          - Escape → 隐藏弹出列表
          - Down → 焦点移到弹出列表
          - 其他（Tab/Shift/Ctrl）→ 忽略
          - 其余按键 → 显示过滤后的弹出列表

        外部参数：
        - event (tk.Event):
            来源：search_entry 的 <KeyRelease> 事件
            含义：键盘事件对象，含 keysym 属性
        """
        if event.keysym == "Return":
            return self.confirm_pet_input()
        if event.keysym == "Escape":
            self.hide_pet_popup()
            return "break"
        if event.keysym == "Down":
            return self.focus_pet_popup()
        if event.keysym in {"Up", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        self.show_pet_popup()

    def confirm_pet_input(self, event=None, use_popup_selection=False):
        """
        确认精灵输入：将弹出列表中的选择同步到搜索框并加载精灵。

        功能：如果 use_popup_selection 为 True 且弹出列表有选中项，
              则将选中值写入搜索框。然后将焦点回到搜索框，隐藏弹出列表，
              调用 load_pet() 加载精灵。

        外部参数：
        - event (tk.Event | None):
            来源：Return 事件或按钮点击
            含义：可选事件对象，未使用
        - use_popup_selection (bool):
            来源：on_pet_popup_click / on_pet_popup_confirm 传入 True
            含义：是否使用弹出列表中的选中值
        """
        if use_popup_selection and self.view.pet_result_listbox.curselection():
            selected_value = self.view.pet_result_listbox.get(
                self.view.pet_result_listbox.curselection()[0]
            )
            self.view.search_var.set(selected_value)

        self.view.search_entry.focus_set()
        self.view.search_entry.icursor(tk.END)
        self.hide_pet_popup()
        self.load_pet()
        return "break"

    def get_filtered_pets(self):
        """
        按搜索框中的文本过滤精灵名称列表。

        功能：如果搜索框为空，返回全部精灵名；否则返回名称中包含
              搜索文本的精灵名列表。

        返回值：
        - list: 过滤后的精灵名称列表
        """
        value = self.view.search_var.get().strip()
        pet_names = sorted(self.db.keys())
        if not value:
            return pet_names
        return [name for name in pet_names if value in name]

    def show_pet_popup(self):
        """
        显示精灵候选弹出列表。

        功能：获取过滤后的精灵列表，填充到 pet_result_listbox，
              选中第一项，调整高度，若列表尚未显示则 pack 显示。
        """
        filtered = self.get_filtered_pets()
        if not filtered:
            self.hide_pet_popup()
            return

        self.pet_search_candidates = filtered
        self.view.pet_result_listbox.delete(0, tk.END)
        for name in filtered:
            self.view.pet_result_listbox.insert(tk.END, name)

        self.view.pet_result_listbox.selection_clear(0, tk.END)
        self.view.pet_result_listbox.selection_set(0)
        self.view.pet_result_listbox.activate(0)
        self.view.pet_result_listbox.config(height=min(len(filtered), 6))
        if not self.view.pet_result_frame.winfo_ismapped():
            self.view.pet_result_frame.pack(
                fill="both", expand=True, padx=10, pady=(0, 5),
                after=self.view.top_f,
            )

    def hide_pet_popup(self):
        """隐藏精灵候选弹出列表。"""
        self.pet_search_candidates = []
        if self.view.pet_result_frame.winfo_ismapped():
            self.view.pet_result_frame.pack_forget()

    def focus_pet_popup(self, event=None):
        """将键盘焦点移到精灵候选列表。"""
        filtered = self.get_filtered_pets()
        if not filtered:
            return "break"
        self.show_pet_popup()
        self.view.pet_result_listbox.focus_set()
        return "break"

    def on_pet_popup_click(self, event):
        """精灵候选列表点击事件 → 确认选择。"""
        return self.confirm_pet_input(use_popup_selection=True)

    def on_pet_popup_confirm(self, event):
        """精灵候选列表 Return/DoubleClick 事件 → 确认选择。"""
        return self.confirm_pet_input(use_popup_selection=True)

    def on_pet_entry_focus_out(self, event):
        """搜索框失焦后延迟判断是否隐藏候选列表。"""
        self.root.after(120, self.hide_pet_popup_if_needed)

    def hide_pet_popup_if_needed(self):
        """
        根据当前焦点决定是否隐藏精灵候选列表。

        功能：如果焦点仍在搜索框或候选列表上则不隐藏，否则隐藏。
        """
        try:
            focused = self.root.focus_get()
        except KeyError:
            focused = None
        if focused in (self.view.search_entry, self.view.pet_result_listbox):
            return
        self.hide_pet_popup()

    # ==================== 技能搜索弹出列表 ====================

    def on_skill_type(self, event, idx):
        """
        技能输入框的键盘输入事件处理。

        功能：按按键类型分发（同 on_pet_type），调用 show_skill_popup。

        外部参数：
        - event: 键盘事件
        - idx (int):
            来源：bind_events() 中遍历绑定，固定为 0-3
            含义：技能输入框索引
        """
        if event.keysym == "Return":
            self.confirm_skill_input(idx, use_popup_selection=False)
            return "break"
        if event.keysym == "Escape":
            self.hide_skill_popup()
            return "break"
        if event.keysym == "Down":
            return self.focus_skill_popup(idx)
        if event.keysym in {"Up", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        self.show_skill_popup(idx)

    def confirm_skill_input(self, idx, use_popup_selection=True):
        """
        确认技能输入：将弹出列表中的选择同步到技能输入框。

        功能：如果 use_popup_selection=True 且弹出列表有选中项，
              将选中值写入指定索引的技能输入框 StringVar。

        外部参数：
        - idx (int): 技能输入框索引（0-3）
        - use_popup_selection (bool): 是否使用弹出列表选中值
        """
        if (
            use_popup_selection
            and self.active_skill_index == idx
            and self.view.skill_result_listbox.curselection()
        ):
            selected_value = self.view.skill_result_listbox.get(
                self.view.skill_result_listbox.curselection()[0]
            )
            self.view.skill_vars[idx].set(selected_value)

        entry = self.view.skill_entries[idx]
        entry.focus_set()
        entry.icursor(tk.END)
        self.hide_skill_popup()
        return "break"

    def get_filtered_skills(self, idx):
        """
        按当前输入过滤技能名称列表。

        外部参数：
        - idx (int): 技能输入框索引

        返回值：
        - list: 过滤后的技能名称列表
        """
        value = self.view.skill_vars[idx].get().strip()
        if not value:
            return self.full_skill_pool[:]
        return [skill for skill in self.full_skill_pool if value in skill]

    def show_skill_popup(self, idx):
        """
        显示技能候选弹出列表。

        外部参数：
        - idx (int): 技能输入框索引
        """
        filtered = self.get_filtered_skills(idx)
        if not filtered:
            self.hide_skill_popup()
            return

        self.active_skill_index = idx
        self.view.skill_result_listbox.delete(0, tk.END)
        for skill in filtered:
            self.view.skill_result_listbox.insert(tk.END, skill)

        self.view.skill_result_listbox.selection_clear(0, tk.END)
        self.view.skill_result_listbox.selection_set(0)
        self.view.skill_result_listbox.activate(0)
        self.view.skill_result_listbox.config(height=min(len(filtered), 6))
        if not self.view.skill_result_frame.winfo_ismapped():
            self.view.skill_result_frame.pack(
                fill="both", expand=True, padx=5, pady=(6, 0),
                before=self.view.skill_footer_separator,
            )

    def hide_skill_popup(self):
        """隐藏技能候选弹出列表。"""
        self.active_skill_index = None
        if self.view.skill_result_frame.winfo_ismapped():
            self.view.skill_result_frame.pack_forget()

    def focus_skill_popup(self, idx):
        """将键盘焦点移到技能候选列表。"""
        filtered = self.get_filtered_skills(idx)
        if not filtered:
            return "break"
        self.show_skill_popup(idx)
        self.view.skill_result_listbox.focus_set()
        return "break"

    def on_skill_popup_click(self, event):
        """技能候选列表点击事件 → 确认选择。"""
        if self.active_skill_index is None:
            return
        self.confirm_skill_input(self.active_skill_index, use_popup_selection=True)

    def on_skill_popup_confirm(self, event):
        """技能候选列表 Return/DoubleClick 事件 → 确认选择。"""
        if self.active_skill_index is None:
            return "break"
        return self.confirm_skill_input(self.active_skill_index, use_popup_selection=True)

    def on_skill_entry_focus_out(self, event):
        """技能输入框失焦后延迟判断是否隐藏候选列表。"""
        self.root.after(120, self.hide_skill_popup_if_needed)

    def hide_skill_popup_if_needed(self):
        """根据当前焦点决定是否隐藏技能候选列表。"""
        if self.active_skill_index is None:
            return
        try:
            focused = self.root.focus_get()
        except KeyError:
            focused = None
        if focused in (
            self.view.skill_entries[self.active_skill_index],
            self.view.skill_result_listbox,
        ):
            return
        self.hide_skill_popup()

    # ==================== 加入阵容 ====================

    def add_pet_to_current(self):
        """
        将当前精灵加入选中的阵容（兼容旧版单按钮模式，当前未使用）。

        功能：检查 current_side 和 current_pet_data 有效后，
              构建精灵条目（名字、实战属性、技能配置），添加到阵容中，
              持久化并刷新列表。
        """
        if not self.current_side:
            messagebox.showwarning("提示", "请先选择一个阵容")
            return
        if not self.current_pet_data:
            messagebox.showwarning("提示", "请先载入一只精灵")
            return

        selector = (
            self.view.ally_lineup_selector
            if self.current_side == "己方"
            else self.view.enemy_lineup_selector
        )
        lineup_name = selector.get(selector.curselection()[0])
        pet_entry = {
            "名字": self.current_pet_data["名字"],
            "实战属性": {
                key: int(widgets["res"].cget("text"))
                for key, widgets in self.view.inputs.items()
            },
            "技能配置": [
                {"名称": skill_var.get()}
                for skill_var in self.view.skill_vars
                if skill_var.get()
            ],
        }
        self.all_lineups[self.current_side][lineup_name].append(pet_entry)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change(self.current_side)

    def get_current_config(self):
        """
        获取当前数值配置（基础属性 + IV + 性格系数）。

        返回值：
        - dict: {"基础属性": {...}, "IV": {...}, "性格系数": {...}}
        """
        config = {
            "基础属性": {
                stat: int(self.view.inputs[stat]["base"].cget("text"))
                for stat in self.view.inputs
            },
            "IV": {
                stat: self.view.inputs[stat]["iv"].get() for stat in self.view.inputs
            },
            "性格系数": {
                stat: self.view.inputs[stat]["nat"].get()
                for stat in self.view.inputs
            },
        }
        return config

    def get_pet_info(self, key):
        """
        获取当前精灵数据的指定字段。

        外部参数：
        - key (str): 字段键名，如"克制表"、"特性"

        返回值：
        - any: 字段值，不存在返回空 dict
        """
        if self.current_pet_data and key in self.current_pet_data:
            return self.current_pet_data[key]
        return {}

    def get_skill_details(self, skill_names):
        """
        从当前精灵数据库中获取指定技能名称的详细信息。

        功能：遍历当前精灵的所有技能分类，查找与 skill_names 匹配的技能，
              返回完整的技能详情列表。

        外部参数：
        - skill_names (list):
            来源：add_pet_to_ally/enemy 中从技能输入框提取
            含义：要查询详情的技能名称列表

        内部参数：
        - details: 技能详情列表
        - all_skills: 当前精灵全部技能（合并三个分类）
        - name: 要查找的技能名称
        - skill: 匹配到的技能 dict

        返回值：
        - list: 技能详情 dict 列表，每项含 名称/属性/消耗/类型/威力/描述
        """
        details = []
        if not self.current_pet_data:
            return details
        all_skills = []
        for skill_list in SKILL_CATEGORY_KEYS:
            if skill_list in self.current_pet_data:
                all_skills.extend(self.current_pet_data[skill_list])
        for name in skill_names:
            for skill in all_skills:
                if skill.get("技能名称") == name:
                    details.append(
                        {
                            "名称": name,
                            "属性": skill.get("属性", ""),
                            "消耗": skill.get("消耗", 0),
                            "类型": skill.get("类型", ""),
                            "威力": skill.get("威力", 0),
                            "描述": skill.get("描述", ""),
                        }
                    )
                    break
        return details

    def add_pet_to_ally(self):
        """
        将当前精灵加入己方阵容。

        功能：检查精灵数据和己方阵容选择，构建完整精灵条目
              （含数值配置、实战属性、克制表、特性、技能详情），
              添加到阵容并持久化，刷新己方阵容显示。

        外部参数：无（使用 self.current_pet_data / self.view.inputs 等）
        """
        if not self.current_pet_data:
            messagebox.showwarning("提示", "请先载入一只精灵")
            return
        selection = self.view.ally_lineup_selector.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先在己方阵容中选择一个阵容")
            return
        lineup_name = self.view.ally_lineup_selector.get(selection[0])
        pet_entry = {
            "名字": self.current_pet_data["名字"],
            "数值配置": self.get_current_config(),
            "实战属性": {
                key: int(widgets["res"].cget("text"))
                for key, widgets in self.view.inputs.items()
            },
            "克制表": self.get_pet_info("克制表"),
            "特性": self.get_pet_info("特性"),
            "技能配置": self.get_skill_details(
                [
                    skill_var.get()
                    for skill_var in self.view.skill_vars
                    if skill_var.get()
                ]
            ),
        }
        self.all_lineups["己方"][lineup_name].append(pet_entry)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change("己方")

    def add_pet_to_enemy(self):
        """
        将当前精灵加入对方阵容。

        功能：同 add_pet_to_ally，但目标为"对方"侧。
        """
        if not self.current_pet_data:
            messagebox.showwarning("提示", "请先载入一只精灵")
            return
        selection = self.view.enemy_lineup_selector.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先在对方阵容中选择一个阵容")
            return
        lineup_name = self.view.enemy_lineup_selector.get(selection[0])
        pet_entry = {
            "名字": self.current_pet_data["名字"],
            "数值配置": self.get_current_config(),
            "实战属性": {
                key: int(widgets["res"].cget("text"))
                for key, widgets in self.view.inputs.items()
            },
            "克制表": self.get_pet_info("克制表"),
            "特性": self.get_pet_info("特性"),
            "技能配置": self.get_skill_details(
                [
                    skill_var.get()
                    for skill_var in self.view.skill_vars
                    if skill_var.get()
                ]
            ),
        }
        self.all_lineups["对方"][lineup_name].append(pet_entry)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change("对方")
