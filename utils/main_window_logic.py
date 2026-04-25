import tkinter as tk
from tkinter import messagebox, ttk

from ui.damage_window import DamageWindow
from utils.calculator import calc_stat


class MainWindowLogic:
    def __init__(self, view, data_manager):
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
        self.view.ally_lineup_selector.bind("<<ListboxSelect>>", lambda event: self.on_lineup_change("己方"))
        self.view.enemy_lineup_selector.bind("<<ListboxSelect>>", lambda event: self.on_lineup_change("对方"))

        self.view.ally_new_lineup_button.config(command=lambda: self.add_new_lineup("己方"))
        self.view.ally_delete_lineup_button.config(command=lambda: self.delete_lineup("己方"))
        self.view.enemy_new_lineup_button.config(command=lambda: self.add_new_lineup("对方"))
        self.view.enemy_delete_lineup_button.config(command=lambda: self.delete_lineup("对方"))
        self.view.open_damage_button.config(command=self.open_damage_calculator)
        self.view.add_ally_button.config(command=self.add_pet_to_ally)
        self.view.add_enemy_button.config(command=self.add_pet_to_enemy)
        self.view.delete_pet_button.config(command=self.delete_selected_pet)
        self.view.save_button.config(command=self.save_to_disk)

        self.view.search_entry.bind("<KeyRelease>", self.on_pet_type)
        self.view.search_entry.bind("<Return>", self.confirm_pet_input)
        self.view.search_entry.bind("<Down>", self.focus_pet_popup)
        self.view.search_entry.bind("<FocusOut>", self.on_pet_entry_focus_out)

        self.view.pet_result_listbox.bind("<ButtonRelease-1>", self.on_pet_popup_click)
        self.view.pet_result_listbox.bind("<Return>", self.on_pet_popup_confirm)
        self.view.pet_result_listbox.bind("<Double-Button-1>", self.on_pet_popup_confirm)

        for stat, widgets in self.view.inputs.items():
            widgets["iv"].bind("<<ComboboxSelected>>", lambda event: self.update_calc())
            widgets["nat"].bind("<<ComboboxSelected>>", lambda event: self.update_calc())

        for idx, entry in enumerate(self.view.skill_entries):
            entry.bind("<KeyRelease>", lambda event, i=idx: self.on_skill_type(event, i))
            entry.bind("<Return>", lambda event, i=idx: self.confirm_skill_input(i))
            entry.bind("<Down>", lambda event, i=idx: self.focus_skill_popup(i))
            entry.bind("<FocusOut>", self.on_skill_entry_focus_out)

        self.view.skill_result_listbox.bind("<ButtonRelease-1>", self.on_skill_popup_click)
        self.view.skill_result_listbox.bind("<Return>", self.on_skill_popup_confirm)
        self.view.skill_result_listbox.bind("<Double-Button-1>", self.on_skill_popup_confirm)

    def open_damage_calculator(self):
        if not self.db:
            messagebox.showwarning("提示", "精灵数据库为空，请先同步数据！")
            return
        DamageWindow(self.root, self.db)

    def delete_selected_pet(self):
        if not self.current_side:
            messagebox.showwarning("提示", "请先选择一个阵容")
            return
        pet_indices = self.view.pet_listbox.curselection()
        if not pet_indices:
            messagebox.showwarning("提示", "请先在名单中点击选中一只精灵")
            return
        selector = self.view.ally_lineup_selector if self.current_side == "己方" else self.view.enemy_lineup_selector
        lineup_name = selector.get(selector.curselection()[0])
        pet_idx = pet_indices[0]
        self.all_lineups[self.current_side][lineup_name].pop(pet_idx)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change(self.current_side)

    def save_to_disk(self):
        self.dm.save_lineups(self.all_lineups)
        messagebox.showinfo("成功", "所有阵容已同步至 data 目录")

    def on_lineup_change(self, side):
        self.all_lineups = self.dm.load_lineups()  # 重新加载以同步文件数据
        self.current_side = side
        if side == "己方":
            self.view.enemy_lineup_selector.selection_clear(0, tk.END)
        else:
            self.view.ally_lineup_selector.selection_clear(0, tk.END)

        selector = self.view.ally_lineup_selector if side == "己方" else self.view.enemy_lineup_selector
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
            skills_str = " | ".join([s["名称"] for s in skills if s.get("名称")])
            if not skills_str:
                skills_str = "未携带技能"
            display_text = f"【{pet['名字']}】 属性: [{stats_str}] 技能: [{skills_str}]"
            self.view.pet_listbox.insert(tk.END, display_text)

    def update_calc(self):
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
        """切换精灵前，清空上一只精灵遗留的输入状态。"""
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

    def refresh_lineup_list(self):
        self.view.lineup_selector.delete(0, tk.END)
        for name in self.all_lineups.keys():
            self.view.lineup_selector.insert(tk.END, name)

    def refresh_ally_lineup_list(self):
        self.view.ally_lineup_selector.delete(0, tk.END)
        for name in self.all_lineups["己方"].keys():
            self.view.ally_lineup_selector.insert(tk.END, name)

    def refresh_enemy_lineup_list(self):
        self.view.enemy_lineup_selector.delete(0, tk.END)
        for name in self.all_lineups["对方"].keys():
            self.view.enemy_lineup_selector.insert(tk.END, name)

    def add_new_lineup(self, side):
        new_name = self.ask_lineup_name()
        if new_name and new_name not in self.all_lineups[side]:
            self.all_lineups[side][new_name] = []
            self.dm.save_lineups(self.all_lineups)
            if side == "己方":
                self.refresh_ally_lineup_list()
            else:
                self.refresh_enemy_lineup_list()

    def ask_lineup_name(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("新建阵容")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()

        result = {"value": None}

        container = ttk.Frame(dialog, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="名称:").pack(anchor="w")
        name_var = tk.StringVar()
        entry = ttk.Entry(container, textvariable=name_var, width=24)
        entry.pack(fill="x", pady=(6, 10))

        button_frame = ttk.Frame(container)
        button_frame.pack(fill="x")

        def submit():
            value = name_var.get().strip()
            if not value:
                messagebox.showwarning("提示", "请输入阵容名称", parent=dialog)
                return
            result["value"] = value
            dialog.destroy()

        def cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="确定", command=submit).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(button_frame, text="取消", command=cancel).pack(side="left", expand=True, fill="x", padx=(4, 0))

        dialog.bind("<Return>", lambda event: submit())
        dialog.bind("<Escape>", lambda event: cancel())
        dialog.protocol("WM_DELETE_WINDOW", cancel)

        entry.focus_set()
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        self.root.wait_window(dialog)
        return result["value"]

    def delete_lineup(self, side):
        selector = self.view.ally_lineup_selector if side == "己方" else self.view.enemy_lineup_selector
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

    def load_pet(self):
        name = self.view.search_var.get().strip()
        self.hide_pet_popup()
        self.reset_current_pet_state()
        if name in self.db:
            self.current_pet_data = self.db[name]
            for stat, widgets in self.view.inputs.items():
                widgets["base"].config(text=str(self.current_pet_data["基础属性"].get(stat, 0)))

            pool = []
            for key in ["精灵技能列表", "血脉技能列表", "可学技能石列表"]:
                pool.extend([skill["技能名称"] for skill in self.current_pet_data.get(key, [])])
            self.full_skill_pool = sorted(list(set(pool)))
            self.update_calc()
        else:
            messagebox.showwarning("提示", "未找到该精灵")

    def on_pet_type(self, event):
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
        if use_popup_selection and self.view.pet_result_listbox.curselection():
            selected_value = self.view.pet_result_listbox.get(self.view.pet_result_listbox.curselection()[0])
            self.view.search_var.set(selected_value)

        self.view.search_entry.focus_set()
        self.view.search_entry.icursor(tk.END)
        self.hide_pet_popup()
        self.load_pet()
        return "break"

    def get_filtered_pets(self):
        value = self.view.search_var.get().strip()
        pet_names = sorted(self.db.keys())
        if not value:
            return pet_names
        return [name for name in pet_names if value in name]

    def show_pet_popup(self):
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
            self.view.pet_result_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5), after=self.view.top_f)

    def hide_pet_popup(self):
        self.pet_search_candidates = []
        if self.view.pet_result_frame.winfo_ismapped():
            self.view.pet_result_frame.pack_forget()

    def focus_pet_popup(self, event=None):
        filtered = self.get_filtered_pets()
        if not filtered:
            return "break"
        self.show_pet_popup()
        self.view.pet_result_listbox.focus_set()
        return "break"

    def on_pet_popup_click(self, event):
        return self.confirm_pet_input(use_popup_selection=True)

    def on_pet_popup_confirm(self, event):
        return self.confirm_pet_input(use_popup_selection=True)

    def on_pet_entry_focus_out(self, event):
        self.root.after(120, self.hide_pet_popup_if_needed)

    def hide_pet_popup_if_needed(self):
        try:
            focused = self.root.focus_get()
        except KeyError:
            focused = None
        if focused in (self.view.search_entry, self.view.pet_result_listbox):
            return
        self.hide_pet_popup()

    def on_skill_type(self, event, idx):
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
        if (
            use_popup_selection
            and self.active_skill_index == idx
            and self.view.skill_result_listbox.curselection()
        ):
            selected_value = self.view.skill_result_listbox.get(self.view.skill_result_listbox.curselection()[0])
            self.view.skill_vars[idx].set(selected_value)

        entry = self.view.skill_entries[idx]
        entry.focus_set()
        entry.icursor(tk.END)
        self.hide_skill_popup()
        return "break"

    def get_filtered_skills(self, idx):
        value = self.view.skill_vars[idx].get().strip()
        if not value:
            return self.full_skill_pool[:]
        return [skill for skill in self.full_skill_pool if value in skill]

    def show_skill_popup(self, idx):
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
            self.view.skill_result_frame.pack(fill="both", expand=True, padx=5, pady=(6, 0), before=self.view.skill_footer_separator)

    def hide_skill_popup(self):
        self.active_skill_index = None
        if self.view.skill_result_frame.winfo_ismapped():
            self.view.skill_result_frame.pack_forget()

    def focus_skill_popup(self, idx):
        filtered = self.get_filtered_skills(idx)
        if not filtered:
            return "break"
        self.show_skill_popup(idx)
        self.view.skill_result_listbox.focus_set()
        return "break"

    def on_skill_popup_click(self, event):
        if self.active_skill_index is None:
            return
        self.confirm_skill_input(self.active_skill_index, use_popup_selection=True)

    def on_skill_popup_confirm(self, event):
        if self.active_skill_index is None:
            return "break"
        return self.confirm_skill_input(self.active_skill_index, use_popup_selection=True)

    def on_skill_entry_focus_out(self, event):
        self.root.after(120, self.hide_skill_popup_if_needed)

    def hide_skill_popup_if_needed(self):
        if self.active_skill_index is None:
            return
        try:
            focused = self.root.focus_get()
        except KeyError:
            focused = None
        if focused in (self.view.skill_entries[self.active_skill_index], self.view.skill_result_listbox):
            return
        self.hide_skill_popup()

    def add_pet_to_current(self):
        if not self.current_side:
            messagebox.showwarning("提示", "请先选择一个阵容")
            return
        if not self.current_pet_data:
            messagebox.showwarning("提示", "请先载入一只精灵")
            return

        selector = self.view.ally_lineup_selector if self.current_side == "己方" else self.view.enemy_lineup_selector
        lineup_name = selector.get(selector.curselection()[0])
        pet_entry = {
            "名字": self.current_pet_data["名字"],
            "实战属性": {key: int(widgets["res"].cget("text")) for key, widgets in self.view.inputs.items()},
            "技能配置": [{"名称": skill_var.get()} for skill_var in self.view.skill_vars if skill_var.get()],
        }
        self.all_lineups[self.current_side][lineup_name].append(pet_entry)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change(self.current_side)

    def get_current_config(self):
        config = {
            "基础属性": {stat: int(self.view.inputs[stat]["base"].cget("text")) for stat in self.view.inputs},
            "IV": {stat: self.view.inputs[stat]["iv"].get() for stat in self.view.inputs},
            "性格系数": {stat: self.view.inputs[stat]["nat"].get() for stat in self.view.inputs}
        }
        return config

    def get_pet_info(self, key):
        if self.current_pet_data and key in self.current_pet_data:
            return self.current_pet_data[key]
        return {}

    def get_skill_details(self, skill_names):
        details = []
        if not self.current_pet_data:
            return details
        all_skills = []
        for skill_list in ["精灵技能列表", "血脉技能列表", "可学技能石列表"]:
            if skill_list in self.current_pet_data:
                all_skills.extend(self.current_pet_data[skill_list])
        for name in skill_names:
            for skill in all_skills:
                if skill.get("技能名称") == name:
                    details.append({
                        "名称": name,
                        "属性": skill.get("属性", ""),
                        "消耗": skill.get("消耗", 0),
                        "类型": skill.get("类型", ""),
                        "威力": skill.get("威力", 0),
                        "描述": skill.get("描述", "")
                    })
                    break
        return details

    def add_pet_to_ally(self):
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
            "实战属性": {key: int(widgets["res"].cget("text")) for key, widgets in self.view.inputs.items()},
            "克制表": self.get_pet_info("克制表"),
            "特性": self.get_pet_info("特性"),
            "技能配置": self.get_skill_details([skill_var.get() for skill_var in self.view.skill_vars if skill_var.get()])
        }
        self.all_lineups["己方"][lineup_name].append(pet_entry)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change("己方")

    def add_pet_to_enemy(self):
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
            "实战属性": {key: int(widgets["res"].cget("text")) for key, widgets in self.view.inputs.items()},
            "克制表": self.get_pet_info("克制表"),
            "特性": self.get_pet_info("特性"),
            "技能配置": self.get_skill_details([skill_var.get() for skill_var in self.view.skill_vars if skill_var.get()])
        }
        self.all_lineups["对方"][lineup_name].append(pet_entry)
        self.dm.save_lineups(self.all_lineups)
        self.on_lineup_change("对方")
