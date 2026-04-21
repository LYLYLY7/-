from tkinter import messagebox

from utils.calculator import calc_stat, calculate_element_multiplier, calculate_final_damage, calculate_stab
from utils.trait_best_partner import BestPartnerTraitService


class DamageWindowLogic:
    OPTIONAL_SKILL_PLACEHOLDER = "可选"

    def __init__(self, view, db_data):
        """伤害窗口逻辑控制器。

        参数来源说明（文件+代码位置）：
        - view:
          - 来源文件：`ui/damage_window.py`
          - 调用位置：`DamageWindow.__init__()` 中
            `self.logic = DamageWindowLogic(self, db_data)`。
        - db_data:
          - 来源文件：`ui/damage_window.py`
          - 调用位置：同上，由窗口构造参数继续传入。
        """
        self.view = view
        self.db_data = db_data
        self.attr_values = ["无", "普通", "火", "水", "草", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"]
        self.pet_names = sorted(db_data.keys())

        self.bind_events()

    def init_panel_runtime_state(self, ui_map):
        """初始化一个面板的运行时状态（由 bind_events 调用）。"""
        ui_map["current_energy"] = 10
        ui_map["trait_name"] = ""
        BestPartnerTraitService.init_state(ui_map)

    def update_panel_status_label(self, ui_map):
        """把当前面板运行态同步到“状态”文本控件。"""
        ui_map["status_label"].config(text=BestPartnerTraitService.build_status_text(ui_map))

    def bind_events(self):
        """绑定所有控件事件和按钮回调。"""
        self.view.load_all_button.config(command=self.load_all_data)
        self.view.reset_button.config(command=self.reset_all)
        self.view.left_to_right_button.config(command=lambda: self.run_calc(self.view.left_ui, self.view.right_ui, self.view.left_to_right_result, "本人打对方伤害"))
        self.view.right_to_left_button.config(command=lambda: self.run_calc(self.view.right_ui, self.view.left_ui, self.view.right_to_left_result, "对方打本人伤害"))

        for panel in (self.view.left_ui, self.view.right_ui):
            self.init_panel_runtime_state(panel)
            panel["atk_attr"].bind("<KeyRelease>", lambda event, combo=panel["atk_attr"]: self.on_attr_type(event, combo))
            panel["name_entry"].bind("<KeyRelease>", lambda event, ui_map=panel: self.on_pet_name_change(event, ui_map))
            panel["name_entry"].bind("<Return>", lambda event, ui_map=panel: self.confirm_pet_input(ui_map))
            panel["name_entry"].bind("<Down>", lambda event, ui_map=panel: self.focus_pet_popup(ui_map))
            panel["name_entry"].bind("<FocusOut>", lambda event, ui_map=panel: self.on_panel_entry_focus_out(ui_map, "pet"))
            panel["skill_entry"].bind("<KeyRelease>", lambda event, ui_map=panel: self.on_skill_name_change(event, ui_map))
            panel["skill_entry"].bind("<Return>", lambda event, ui_map=panel: self.confirm_skill_entry(ui_map))
            panel["skill_entry"].bind("<Down>", lambda event, ui_map=panel: self.focus_skill_popup(ui_map))
            panel["skill_entry"].bind("<FocusOut>", lambda event, ui_map=panel: self.on_panel_entry_focus_out(ui_map, "skill"))
            panel["pet_result_listbox"].bind("<ButtonRelease-1>", lambda event, ui_map=panel: self.confirm_pet_input(ui_map, use_popup_selection=True))
            panel["pet_result_listbox"].bind("<Return>", lambda event, ui_map=panel: self.confirm_pet_input(ui_map, use_popup_selection=True))
            panel["pet_result_listbox"].bind("<Double-Button-1>", lambda event, ui_map=panel: self.confirm_pet_input(ui_map, use_popup_selection=True))
            panel["skill_result_listbox"].bind("<ButtonRelease-1>", lambda event, ui_map=panel: self.confirm_skill_entry(ui_map, use_popup_selection=True))
            panel["skill_result_listbox"].bind("<Return>", lambda event, ui_map=panel: self.confirm_skill_entry(ui_map, use_popup_selection=True))
            panel["skill_result_listbox"].bind("<Double-Button-1>", lambda event, ui_map=panel: self.confirm_skill_entry(ui_map, use_popup_selection=True))
            for widgets in panel["stats"].values():
                widgets["iv"].bind("<<ComboboxSelected>>", lambda event, ui_map=panel: self.refresh_stat_values(ui_map))
                widgets["nat"].bind("<<ComboboxSelected>>", lambda event, ui_map=panel: self.refresh_stat_values(ui_map))

        self.setup_optional_skill_placeholder(self.view.right_ui)

    def show_warning(self, message):
        """统一错误提示入口，确保提示框在主窗口前方居中显示。"""
        self.view.update_idletasks()
        self.view.lift()
        self.view.focus_force()
        self.view.attributes("-topmost", True)
        try:
            messagebox.showwarning("提示", message, parent=self.view)
        finally:
            self.view.attributes("-topmost", False)

    def reset_all(self):
        """将整个页面恢复到初始打开状态。"""
        for panel in (self.view.left_ui, self.view.right_ui):
            panel["name_entry"].delete(0, "end")
            self.reset_panel_inputs(panel)
            self.hide_pet_popup(panel)
            self.hide_skill_popup(panel)

        self.view.left_ui["skill_entry"].delete(0, "end")
        self.view.right_ui["skill_entry"].delete(0, "end")
        self.view.right_ui["skill_entry"].insert(0, self.OPTIONAL_SKILL_PLACEHOLDER)

        self.view.left_to_right_result.config(text="造成伤害: 0")
        self.view.right_to_left_result.config(text="造成伤害: 0")

    def setup_optional_skill_placeholder(self, ui_map):
        """为“对方技能名”输入框安装可选占位文本逻辑。

        参数来源说明（文件+代码位置）：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`bind_events()` 中 `self.setup_optional_skill_placeholder(self.view.right_ui)`。
        """
        entry = ui_map["skill_entry"]
        if not entry.get().strip():
            entry.insert(0, self.OPTIONAL_SKILL_PLACEHOLDER)
        entry.bind("<FocusIn>", lambda event, target=entry: self.clear_optional_placeholder(target))
        entry.bind("<FocusOut>", lambda event, target=entry: self.restore_optional_placeholder(target))

    def clear_optional_placeholder(self, entry_widget):
        """当输入框获得焦点时，清理“可选”占位文本。

        参数来源说明（文件+代码位置）：
        - entry_widget:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`setup_optional_skill_placeholder()` 中 `<FocusIn>` 绑定。
        """
        if entry_widget.get().strip() == self.OPTIONAL_SKILL_PLACEHOLDER:
            entry_widget.delete(0, "end")

    def restore_optional_placeholder(self, entry_widget):
        """当输入框失焦且为空时，恢复“可选”占位文本。

        参数来源说明（文件+代码位置）：
        - entry_widget:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`setup_optional_skill_placeholder()` 中 `<FocusOut>` 绑定。
        """
        if not entry_widget.get().strip():
            entry_widget.insert(0, self.OPTIONAL_SKILL_PLACEHOLDER)

    def get_skill_input(self, ui_map, allow_placeholder=False):
        """读取技能输入，并按配置决定是否把“可选”视为空值。

        参数来源说明（文件+代码位置）：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`load_all_data()`、`load_panel_data()`。
        - allow_placeholder:
          - 来源文件：`utils/damage_window_logic.py`
          - 传参位置：当前调用默认 False，用于把“可选”转为空。
        """
        value = ui_map["skill_entry"].get().strip()
        if not allow_placeholder and value == self.OPTIONAL_SKILL_PLACEHOLDER:
            return ""
        return value

    def load_all_data(self):
        """统一加载入口：校验输入后加载双方数据。"""
        left_name = self.view.left_ui["name_entry"].get().strip()
        left_skill = self.get_skill_input(self.view.left_ui)
        right_name = self.view.right_ui["name_entry"].get().strip()
        right_skill = self.get_skill_input(self.view.right_ui)

        if not left_name:
            self.show_warning("请输入本人精灵名称")
            return
        if not left_skill:
            self.show_warning("请输入本人技能名称")
            return
        if not right_name:
            self.show_warning("请输入对方精灵名称")
            return

        if not self.load_panel_data(self.view.left_ui, require_skill=True):
            return
        if not self.load_panel_data(self.view.right_ui, require_skill=False):
            return

        self.view.left_ui["name_entry"].delete(0, "end")
        self.view.left_ui["name_entry"].insert(0, left_name)
        self.view.left_ui["skill_entry"].delete(0, "end")
        self.view.left_ui["skill_entry"].insert(0, left_skill)

        self.view.right_ui["name_entry"].delete(0, "end")
        self.view.right_ui["name_entry"].insert(0, right_name)
        self.view.right_ui["skill_entry"].delete(0, "end")
        if right_skill:
            self.view.right_ui["skill_entry"].insert(0, right_skill)
        else:
            self.view.right_ui["skill_entry"].insert(0, self.OPTIONAL_SKILL_PLACEHOLDER)

    def on_attr_type(self, event, combo):
        """技能属性输入时提供下拉筛选。

        参数来源说明（文件+代码位置）：
        - event / combo:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`bind_events()` 中 `panel["atk_attr"].bind("<KeyRelease>", ...)`。
        """
        value = combo.get()
        if value == "":
            combo["values"] = self.attr_values
        else:
            combo["values"] = [item for item in self.attr_values if value in item]
        combo.event_generate("<Down>")

    def load_panel_data(self, ui_map, require_skill=True):
        """加载单侧精灵与技能数据到面板。

        参数来源说明：
        - ui_map:
          - 调用来源文件：`utils/damage_window_logic.py`
          - 调用位置：`load_all_data()` 中 `self.load_panel_data(self.view.left_ui, ...)`
            与 `self.load_panel_data(self.view.right_ui, ...)` 这两处调用代码段。
          - 数据最初来源：`ui/damage_window.py` 中 `setup_ui()` 创建
            `self.left_ui / self.right_ui`，并由 `create_identity_panel()`、
            `create_skill_panel()`、`create_stats_panel()` 逐步填充控件引用。
        - require_skill:
          - 调用来源文件：`utils/damage_window_logic.py`
          - 调用位置：`load_all_data()` 中左侧传 `True`（本人技能必填）、
            右侧传 `False`（对方技能可选）。
        """
        pet_name = ui_map["name_entry"].get().strip()
        skill_name = self.get_skill_input(ui_map)

        if pet_name not in self.db_data:
            self.show_warning(f"未找到精灵: {pet_name}")
            return False

        self.hide_pet_popup(ui_map)
        self.hide_skill_popup(ui_map)
        self.reset_panel_inputs(ui_map)
        ui_map["name_entry"].delete(0, "end")
        ui_map["name_entry"].insert(0, pet_name)
        ui_map["skill_entry"].delete(0, "end")
        if skill_name:
            ui_map["skill_entry"].insert(0, skill_name)
        elif ui_map is self.view.right_ui:
            ui_map["skill_entry"].insert(0, self.OPTIONAL_SKILL_PLACEHOLDER)

        pet_data = self.db_data[pet_name]
        self.load_pet_stats(ui_map, pet_data)
        self.populate_skill_options(ui_map, pet_data)

        if skill_name:
            skill_data = self.find_skill_data(pet_data, skill_name)
            if skill_data:
                self.fill_skill_fields(ui_map, skill_data)
                self.update_element_multiplier_for_loaded_skill(ui_map)
            else:
                self.show_warning(f"未找到技能: {skill_name}")
                return False
        elif require_skill:
            self.show_warning("该面板技能为必填项")
            return False
        return True

    def reset_panel_inputs(self, ui_map):
        """恢复当前面板默认值（不包含外部布局本身）。"""
        ui_map["skill_entry"].delete(0, "end")
        ui_map["skill_candidates"] = []
        ui_map["atk_type"].set("物攻")
        ui_map["atk_attr"].set("无")

        for entry_key in ["power_entry", "buff_entry", "hits_entry", "other_entry"]:
            ui_map[entry_key].delete(0, "end")
        ui_map["power_entry"].insert(0, "0")
        ui_map["buff_entry"].insert(0, "1")
        ui_map["hits_entry"].insert(0, "1")
        ui_map["other_entry"].insert(0, "1")
        ui_map["cost_entry"].delete(0, "end")
        ui_map["cost_entry"].insert(0, "0")

        ui_map["stab_combo"].set("1")
        ui_map["element_combo"].set("1")

        for stat_name, widgets in ui_map["stats"].items():
            widgets["base"].config(text="0")
            widgets["iv"].set("0")
            widgets["nat"].set("1.0")
            widgets["res"].config(text="0")

        self.init_panel_runtime_state(ui_map)
        ui_map["energy_label"].config(text="当前能量：10")
        ui_map["trait_name_label"].config(text="特性：-")
        ui_map["trait_desc_label"].config(text="效果：-")
        self.update_panel_status_label(ui_map)

    def on_pet_name_change(self, event, ui_map):
        """处理精灵名输入变化，驱动精灵候选与技能候选更新。

        参数来源说明（文件+代码位置）：
        - event / ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`bind_events()` 中 `panel["name_entry"].bind("<KeyRelease>", ...)`。
        """
        if event.keysym == "Return":
            return self.confirm_pet_input(ui_map)
        if event.keysym == "Escape":
            self.hide_pet_popup(ui_map)
            return "break"
        if event.keysym == "Down":
            return self.focus_pet_popup(ui_map)
        if event.keysym in {"Up", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return

        pet_name = ui_map["name_entry"].get().strip()
        if pet_name in self.db_data:
            self.populate_skill_options(ui_map, self.db_data[pet_name])
        else:
            ui_map["skill_candidates"] = []
            ui_map["skill_result_listbox"].delete(0, "end")

        self.show_pet_popup(ui_map)

    def confirm_pet_input(self, ui_map, use_popup_selection=False):
        """确认精灵输入（可来自手动回车或候选列表点击）。

        参数来源说明（文件+代码位置）：
        - ui_map / use_popup_selection:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`bind_events()` 的 `<Return>` 与候选列表点击/双击回调。
        """
        if use_popup_selection and ui_map["pet_result_listbox"].curselection():
            selected = ui_map["pet_result_listbox"].get(ui_map["pet_result_listbox"].curselection()[0])
            ui_map["name_entry"].delete(0, "end")
            ui_map["name_entry"].insert(0, selected)

        ui_map["name_entry"].focus_set()
        ui_map["name_entry"].icursor("end")
        self.hide_pet_popup(ui_map)
        pet_name = ui_map["name_entry"].get().strip()
        if pet_name in self.db_data:
            self.populate_skill_options(ui_map, self.db_data[pet_name])
        return "break"

    def load_pet_stats(self, ui_map, pet_data):
        """把精灵基础属性加载到面板，并刷新实战属性。

        参数来源说明：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 传入位置：`load_panel_data()` 中 `self.load_pet_stats(ui_map, pet_data)`。
        - pet_data:
          - 来源文件：`utils/damage_window_logic.py`
          - 生成位置：`load_panel_data()` 中 `pet_data = self.db_data[pet_name]`。
          - 上游数据来源：`db_data` 由 `ui/damage_window.py` 中
            `DamageWindow(..., db_data)` 传入当前逻辑类构造函数。
        """
        base_stats = pet_data.get("基础属性", {})
        for stat_name in ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]:
            if stat_name in ui_map["stats"]:
                ui_map["stats"][stat_name]["base"].config(text=str(base_stats.get(stat_name, 0)))
        self.load_pet_info(ui_map, pet_data)
        self.refresh_stat_values(ui_map)

    def populate_skill_options(self, ui_map, pet_data):
        """根据精灵数据构建技能候选列表。

        参数来源说明（文件+代码位置）：
        - ui_map / pet_data:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`load_panel_data()`、`on_pet_name_change()`、`confirm_pet_input()`。
        """
        skill_names = []
        for key in ["精灵技能列表", "血脉技能列表", "可学技能石列表"]:
            skill_names.extend([skill.get("技能名称", "") for skill in pet_data.get(key, []) if skill.get("技能名称")])

        unique_names = sorted(set(skill_names))
        ui_map["skill_candidates"] = unique_names

    def find_skill_data(self, pet_data, skill_name):
        """在精灵技能集合中查找指定技能详情。

        参数来源说明（文件+代码位置）：
        - pet_data / skill_name:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`load_panel_data()` 中 `self.find_skill_data(pet_data, skill_name)`。
        """
        for key in ["精灵技能列表", "血脉技能列表", "可学技能石列表"]:
            for skill in pet_data.get(key, []):
                if skill.get("技能名称") == skill_name:
                    return skill
        return None

    def fill_skill_fields(self, ui_map, skill_data):
        """把技能详情写入“技能与环境参数”区域。

        参数来源说明：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 传入位置：`load_panel_data()` 中 `self.fill_skill_fields(ui_map, skill_data)`。
        - skill_data:
          - 来源文件：`utils/damage_window_logic.py`
          - 生成位置：`load_panel_data()` 中 `self.find_skill_data(...)` 的返回值。
        """
        skill_type = skill_data.get("类型", "物攻")
        skill_attr = skill_data.get("属性", "无") or "无"
        power = skill_data.get("威力", "0")
        cost = skill_data.get("消耗", "0")
        pet_name = ui_map["name_entry"].get().strip()
        pet_elements = self.db_data.get(pet_name, {}).get("元素", [])

        if skill_type not in self.view.atk_type_values:
            skill_type = "物攻"
        if skill_attr not in self.attr_values:
            skill_attr = "无"

        ui_map["atk_type"].set(skill_type)
        ui_map["atk_attr"].set(skill_attr)
        ui_map["power_entry"].delete(0, "end")
        ui_map["power_entry"].insert(0, str(power))
        ui_map["cost_entry"].delete(0, "end")
        ui_map["cost_entry"].insert(0, str(cost))
        ui_map["stab_combo"].set(str(calculate_stab(skill_type, skill_attr, pet_elements)))

    def update_element_multiplier_for_loaded_skill(self, attacker_ui):
        """加载技能后，自动按对方克制表刷新属性倍率。"""
        defender_ui = self.view.right_ui if attacker_ui is self.view.left_ui else self.view.left_ui
        defender_name = defender_ui["name_entry"].get().strip()
        defender_kz_table = self.db_data.get(defender_name, {}).get("克制表", {})
        skill_attr = attacker_ui["atk_attr"].get().strip()
        skill_power = attacker_ui["power_entry"].get().strip()
        multiplier = calculate_element_multiplier(skill_attr, skill_power, defender_kz_table)
        attacker_ui["element_combo"].set(str(multiplier))

    def get_filtered_pets(self, ui_map):
        """按当前输入过滤精灵候选。"""
        value = ui_map["name_entry"].get().strip()
        if not value:
            return self.pet_names[:]
        return [name for name in self.pet_names if value in name]

    def show_pet_popup(self, ui_map):
        """展示精灵候选弹出列表。"""
        filtered = self.get_filtered_pets(ui_map)
        if not filtered:
            self.hide_pet_popup(ui_map)
            return

        ui_map["pet_result_listbox"].delete(0, "end")
        for name in filtered:
            ui_map["pet_result_listbox"].insert("end", name)
        ui_map["pet_result_listbox"].selection_clear(0, "end")
        ui_map["pet_result_listbox"].selection_set(0)
        ui_map["pet_result_listbox"].activate(0)
        ui_map["pet_result_listbox"].config(height=min(len(filtered), 5))
        if not ui_map["pet_result_frame"].winfo_ismapped():
            ui_map["pet_result_frame"].pack(fill="x", padx=8, pady=(0, 4), after=ui_map["top_frame"])

    def hide_pet_popup(self, ui_map):
        """隐藏精灵候选弹出列表。"""
        if ui_map["pet_result_frame"].winfo_ismapped():
            ui_map["pet_result_frame"].pack_forget()

    def focus_pet_popup(self, ui_map):
        """将键盘焦点移动到精灵候选列表。"""
        filtered = self.get_filtered_pets(ui_map)
        if not filtered:
            return "break"
        self.show_pet_popup(ui_map)
        ui_map["pet_result_listbox"].focus_set()
        return "break"

    def get_filtered_skills(self, ui_map):
        """按当前输入过滤技能候选。"""
        value = ui_map["skill_entry"].get().strip()
        candidates = ui_map.get("skill_candidates", [])
        if not value:
            return candidates[:]
        return [name for name in candidates if value in name]

    def on_skill_name_change(self, event, ui_map):
        """处理技能名输入变化，驱动技能候选更新。"""
        if event.keysym == "Return":
            return self.confirm_skill_entry(ui_map)
        if event.keysym == "Escape":
            self.hide_skill_popup(ui_map)
            return "break"
        if event.keysym == "Down":
            return self.focus_skill_popup(ui_map)
        if event.keysym in {"Up", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return

        pet_name = ui_map["name_entry"].get().strip()
        if pet_name in self.db_data:
            self.populate_skill_options(ui_map, self.db_data[pet_name])
        self.show_skill_popup(ui_map)

    def confirm_skill_entry(self, ui_map, use_popup_selection=False):
        """确认技能输入（可来自手动回车或候选列表点击）。"""
        if use_popup_selection and ui_map["skill_result_listbox"].curselection():
            selected = ui_map["skill_result_listbox"].get(ui_map["skill_result_listbox"].curselection()[0])
            ui_map["skill_entry"].delete(0, "end")
            ui_map["skill_entry"].insert(0, selected)

        ui_map["skill_entry"].focus_set()
        ui_map["skill_entry"].icursor("end")
        self.hide_skill_popup(ui_map)
        return "break"

    def show_skill_popup(self, ui_map):
        """展示技能候选弹出列表。"""
        filtered = self.get_filtered_skills(ui_map)
        if not filtered:
            self.hide_skill_popup(ui_map)
            return

        ui_map["skill_result_listbox"].delete(0, "end")
        for name in filtered:
            ui_map["skill_result_listbox"].insert("end", name)
        ui_map["skill_result_listbox"].selection_clear(0, "end")
        ui_map["skill_result_listbox"].selection_set(0)
        ui_map["skill_result_listbox"].activate(0)
        ui_map["skill_result_listbox"].config(height=min(len(filtered), 5))
        if not ui_map["skill_result_frame"].winfo_ismapped():
            ui_map["skill_result_frame"].pack(fill="x", padx=8, pady=(0, 4), after=ui_map["pet_result_frame"] if ui_map["pet_result_frame"].winfo_ismapped() else ui_map["top_frame"])

    def hide_skill_popup(self, ui_map):
        """隐藏技能候选弹出列表。"""
        if ui_map["skill_result_frame"].winfo_ismapped():
            ui_map["skill_result_frame"].pack_forget()

    def focus_skill_popup(self, ui_map):
        """将键盘焦点移动到技能候选列表。"""
        filtered = self.get_filtered_skills(ui_map)
        if not filtered:
            return "break"
        self.show_skill_popup(ui_map)
        ui_map["skill_result_listbox"].focus_set()
        return "break"

    def on_panel_entry_focus_out(self, ui_map, popup_type):
        """输入框失焦后延迟判断是否需要隐藏候选列表。"""
        self.view.after(120, lambda: self.hide_popup_if_needed(ui_map, popup_type))

    def hide_popup_if_needed(self, ui_map, popup_type):
        """根据当前焦点决定是否关闭候选列表（含 Tk popdown 兼容处理）。"""
        try:
            focus_name = self.view.tk.call("focus")
        except Exception:
            focus_name = ""
        if isinstance(focus_name, str) and "popdown" in focus_name:
            return

        try:
            focused = self.view.focus_get()
        except KeyError:
            return

        if popup_type == "pet":
            if focused in (ui_map["name_entry"], ui_map["pet_result_listbox"]):
                return
            self.hide_pet_popup(ui_map)
        else:
            if focused in (ui_map["skill_entry"], ui_map["skill_result_listbox"]):
                return
            self.hide_skill_popup(ui_map)

    def load_pet_info(self, ui_map, pet_data):
        """把精灵特性信息写到“战斗信息”区域。"""
        trait_data = pet_data.get("特性", {})
        trait_name = trait_data.get("名称", "-")
        trait_desc = trait_data.get("效果描述", "-")
        ui_map["trait_name"] = trait_name
        BestPartnerTraitService.init_state(ui_map)
        ui_map["energy_label"].config(text="当前能量：10")
        ui_map["trait_name_label"].config(text=f"特性：{trait_name}")
        ui_map["trait_desc_label"].config(text=f"效果：{trait_desc}")
        self.update_panel_status_label(ui_map)

    def refresh_stat_values(self, ui_map):
        """按当前个体/性格/特性状态计算并刷新面板值。"""
        panel_multiplier = BestPartnerTraitService.current_multiplier(ui_map)
        for stat_name, widgets in ui_map["stats"].items():
            base_result = calc_stat(
                widgets["base"].cget("text"),
                widgets["iv"].get(),
                widgets["nat"].get(),
                is_hp=(stat_name == "生命"),
            )
            if stat_name in {"物攻", "魔攻", "物防", "魔防", "速度"}:
                shown_result = int(base_result * panel_multiplier)
            else:
                shown_result = base_result
            widgets["res"].config(text=str(shown_result))

    def run_calc(self, attacker_ui, defender_ui, result_label, label_prefix):
        """执行一次伤害计算并结算特性/能量变化。

        参数来源：
        - attacker_ui / defender_ui：
          - 来源文件：`utils/damage_window_logic.py`
          - 绑定位置：`bind_events()` 中
            `self.view.left_to_right_button.config(command=lambda: self.run_calc(...))`
            与 `self.view.right_to_left_button.config(command=lambda: self.run_calc(...))`。
          - 实际对象来源：`self.view.left_ui / self.view.right_ui`，
            这两个对象由 `ui/damage_window.py` 的 `setup_ui()` 创建。
        - result_label：
          - 来源文件：`utils/damage_window_logic.py`
          - 绑定位置：同 `bind_events()` 两个按钮回调，分别传
            `self.view.left_to_right_result` 与 `self.view.right_to_left_result`。
          - 控件定义来源：`ui/damage_window.py` 的 `setup_ui()` 伤害计算区域。
        - label_prefix：
          - 来源文件：`utils/damage_window_logic.py`
          - 绑定位置：同 `bind_events()` 两个按钮回调，分别传
            `"本人打对方伤害"` 与 `"对方打本人伤害"`。
          - 用途：历史兼容参数，当前主要保留签名稳定性。
        """
        self.refresh_stat_values(attacker_ui)
        self.refresh_stat_values(defender_ui)

        atk_type = attacker_ui["atk_type"].get()
        if atk_type == "物攻":
            atk_val = attacker_ui["stats"]["物攻"]["res"].cget("text")
            dfn_val = defender_ui["stats"]["物防"]["res"].cget("text")
        elif atk_type == "魔攻":
            atk_val = attacker_ui["stats"]["魔攻"]["res"].cget("text")
            dfn_val = defender_ui["stats"]["魔防"]["res"].cget("text")
        else:
            atk_val = 0
            dfn_val = 1
        try:
            skill_cost = int(float(attacker_ui["cost_entry"].get()))
        except (TypeError, ValueError):
            skill_cost = 0
        if skill_cost < 0:
            skill_cost = 0

        current_energy = attacker_ui.get("current_energy", 10)
        if current_energy < skill_cost:
            self.show_warning(f"能量不足：当前能量{current_energy}，技能耗能{skill_cost}")
            return

        total_damage = calculate_final_damage(
            pwr=attacker_ui["power_entry"].get(),
            atk_val=atk_val,
            dfn_val=dfn_val,
            stab=attacker_ui["stab_combo"].get(),
            element_mult=attacker_ui["element_combo"].get(),
            buff_mult=attacker_ui["buff_entry"].get(),
            hits=attacker_ui["hits_entry"].get(),
            other_mult=attacker_ui["other_entry"].get(),
        )

        try:
            element_mult = float(attacker_ui["element_combo"].get())
        except (TypeError, ValueError):
            element_mult = 1

        energy_gain = BestPartnerTraitService.on_after_damage(attacker_ui, element_mult, total_damage)
        if energy_gain > 0:
            self.update_panel_status_label(attacker_ui)

        attacker_ui["current_energy"] = max(0, current_energy - skill_cost + energy_gain)
        attacker_ui["energy_label"].config(text=f"当前能量：{attacker_ui['current_energy']}")

        result_label.config(text=f"造成伤害: {total_damage}")
        self.refresh_stat_values(attacker_ui)
        self.refresh_stat_values(defender_ui)
