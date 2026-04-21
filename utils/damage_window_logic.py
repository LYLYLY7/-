from tkinter import messagebox

from utils.calculator import calc_stat, calculate_element_multiplier, calculate_final_damage, calculate_stab


class DamageWindowLogic:
    def __init__(self, view, db_data):
        self.view = view
        self.db_data = db_data
        self.attr_values = ["无", "普通", "火", "水", "草", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"]
        self.pet_names = sorted(db_data.keys())

        self.bind_events()

    def bind_events(self):
        self.view.left_to_right_button.config(command=lambda: self.run_calc(self.view.left_ui, self.view.right_ui, self.view.left_to_right_result, "本人打对方伤害"))
        self.view.right_to_left_button.config(command=lambda: self.run_calc(self.view.right_ui, self.view.left_ui, self.view.right_to_left_result, "对方打本人伤害"))

        for panel in (self.view.left_ui, self.view.right_ui):
            panel["load_button"].config(command=lambda ui_map=panel: self.load_panel_data(ui_map))
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

    def on_attr_type(self, event, combo):
        value = combo.get()
        if value == "":
            combo["values"] = self.attr_values
        else:
            combo["values"] = [item for item in self.attr_values if value in item]
        combo.event_generate("<Down>")

    def load_panel_data(self, ui_map):
        pet_name = ui_map["name_entry"].get().strip()
        skill_name = ui_map["skill_entry"].get().strip()

        if pet_name not in self.db_data:
            messagebox.showwarning("提示", f"未找到精灵: {pet_name}")
            return

        self.hide_pet_popup(ui_map)
        self.hide_skill_popup(ui_map)
        self.reset_panel_inputs(ui_map)

        pet_data = self.db_data[pet_name]
        self.load_pet_stats(ui_map, pet_data)
        self.populate_skill_options(ui_map, pet_data)

        if skill_name:
            skill_data = self.find_skill_data(pet_data, skill_name)
            if skill_data:
                self.fill_skill_fields(ui_map, skill_data)
                self.update_element_multiplier_for_loaded_skill(ui_map)
            else:
                messagebox.showwarning("提示", f"未找到技能: {skill_name}")

    def reset_panel_inputs(self, ui_map):
        """切换精灵时，将当前面板除精灵名外的输入恢复到初始状态。"""
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

        ui_map["stab_combo"].set("1")
        ui_map["element_combo"].set("1")

        for stat_name, widgets in ui_map["stats"].items():
            widgets["base"].config(text="0")
            widgets["iv"].set("0")
            widgets["nat"].set("1.0")
            widgets["res"].config(text="0")

        ui_map["energy_label"].config(text="当前能量：10")
        ui_map["trait_name_label"].config(text="特性：-")
        ui_map["trait_desc_label"].config(text="效果：-")
        ui_map["status_label"].config(text="状态")

    def on_pet_name_change(self, event, ui_map):
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
        base_stats = pet_data.get("基础属性", {})
        for stat_name in ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]:
            if stat_name in ui_map["stats"]:
                ui_map["stats"][stat_name]["base"].config(text=str(base_stats.get(stat_name, 0)))
        self.load_pet_info(ui_map, pet_data)
        self.refresh_stat_values(ui_map)

    def populate_skill_options(self, ui_map, pet_data):
        skill_names = []
        for key in ["精灵技能列表", "血脉技能列表", "可学技能石列表"]:
            skill_names.extend([skill.get("技能名称", "") for skill in pet_data.get(key, []) if skill.get("技能名称")])

        unique_names = sorted(set(skill_names))
        ui_map["skill_candidates"] = unique_names

    def find_skill_data(self, pet_data, skill_name):
        for key in ["精灵技能列表", "血脉技能列表", "可学技能石列表"]:
            for skill in pet_data.get(key, []):
                if skill.get("技能名称") == skill_name:
                    return skill
        return None

    def fill_skill_fields(self, ui_map, skill_data):
        skill_type = skill_data.get("类型", "物攻")
        skill_attr = skill_data.get("属性", "无") or "无"
        power = skill_data.get("威力", "0")
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
        ui_map["stab_combo"].set(str(calculate_stab(skill_type, skill_attr, pet_elements)))

    def update_element_multiplier_for_loaded_skill(self, attacker_ui):
        defender_ui = self.view.right_ui if attacker_ui is self.view.left_ui else self.view.left_ui
        defender_name = defender_ui["name_entry"].get().strip()
        defender_kz_table = self.db_data.get(defender_name, {}).get("克制表", {})
        skill_attr = attacker_ui["atk_attr"].get().strip()
        skill_power = attacker_ui["power_entry"].get().strip()
        multiplier = calculate_element_multiplier(skill_attr, skill_power, defender_kz_table)
        attacker_ui["element_combo"].set(str(multiplier))

    def get_filtered_pets(self, ui_map):
        value = ui_map["name_entry"].get().strip()
        if not value:
            return self.pet_names[:]
        return [name for name in self.pet_names if value in name]

    def show_pet_popup(self, ui_map):
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
        if ui_map["pet_result_frame"].winfo_ismapped():
            ui_map["pet_result_frame"].pack_forget()

    def focus_pet_popup(self, ui_map):
        filtered = self.get_filtered_pets(ui_map)
        if not filtered:
            return "break"
        self.show_pet_popup(ui_map)
        ui_map["pet_result_listbox"].focus_set()
        return "break"

    def get_filtered_skills(self, ui_map):
        value = ui_map["skill_entry"].get().strip()
        candidates = ui_map.get("skill_candidates", [])
        if not value:
            return candidates[:]
        return [name for name in candidates if value in name]

    def on_skill_name_change(self, event, ui_map):
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
        if use_popup_selection and ui_map["skill_result_listbox"].curselection():
            selected = ui_map["skill_result_listbox"].get(ui_map["skill_result_listbox"].curselection()[0])
            ui_map["skill_entry"].delete(0, "end")
            ui_map["skill_entry"].insert(0, selected)

        ui_map["skill_entry"].focus_set()
        ui_map["skill_entry"].icursor("end")
        self.hide_skill_popup(ui_map)
        return "break"

    def show_skill_popup(self, ui_map):
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
        if ui_map["skill_result_frame"].winfo_ismapped():
            ui_map["skill_result_frame"].pack_forget()

    def focus_skill_popup(self, ui_map):
        filtered = self.get_filtered_skills(ui_map)
        if not filtered:
            return "break"
        self.show_skill_popup(ui_map)
        ui_map["skill_result_listbox"].focus_set()
        return "break"

    def on_panel_entry_focus_out(self, ui_map, popup_type):
        self.view.after(120, lambda: self.hide_popup_if_needed(ui_map, popup_type))

    def hide_popup_if_needed(self, ui_map, popup_type):
        focused = self.view.focus_get()
        if popup_type == "pet":
            if focused in (ui_map["name_entry"], ui_map["pet_result_listbox"]):
                return
            self.hide_pet_popup(ui_map)
        else:
            if focused in (ui_map["skill_entry"], ui_map["skill_result_listbox"]):
                return
            self.hide_skill_popup(ui_map)

    def load_pet_info(self, ui_map, pet_data):
        trait_data = pet_data.get("特性", {})
        trait_name = trait_data.get("名称", "-")
        trait_desc = trait_data.get("效果描述", "-")
        ui_map["energy_label"].config(text="当前能量：10")
        ui_map["trait_name_label"].config(text=f"特性：{trait_name}")
        ui_map["trait_desc_label"].config(text=f"效果：{trait_desc}")
        ui_map["status_label"].config(text="状态")

    def refresh_stat_values(self, ui_map):
        for stat_name, widgets in ui_map["stats"].items():
            result = calc_stat(
                widgets["base"].cget("text"),
                widgets["iv"].get(),
                widgets["nat"].get(),
                is_hp=(stat_name == "生命"),
            )
            widgets["res"].config(text=str(result))

    def run_calc(self, attacker_ui, defender_ui, result_label, label_prefix):
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
        result_label.config(text=f"{label_prefix}: {total_damage}")
