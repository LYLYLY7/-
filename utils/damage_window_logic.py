"""
伤害窗口业务逻辑模块。

功能：定义 DamageWindowLogic 类，处理伤害推演窗口（DamageWindow）的所有
      事件响应和业务逻辑，包括精灵/技能搜索与选择、阵容加载、面板属性计算、
      技能参数自动填充、伤害结算、"最好的伙伴"特性联动等。
外部依赖：
- utils/calculator.py: calc_stat, calculate_stab, calculate_element_multiplier, calculate_final_damage
- utils/trait_best_partner.py: BestPartnerTraitService
- utils/constants.py: SKILL_FIELDS, PET_BASIC_FIELDS, ELEMENT_TYPES, SKILL_CATEGORY_KEYS,
                      STAT_NAMES, LINEUP_FILE, CACHE_FILE
- utils/ui_helpers.py: show_lineup_selection_dialog
"""

import json
from pathlib import Path
from tkinter import messagebox

from utils.calculator import (
    calc_stat,
    calculate_element_multiplier,
    calculate_final_damage,
    calculate_stab,
)
from utils.constants import (
    CACHE_FILE as CACHE_FILE_PATH,
    ELEMENT_TYPES,
    LINEUP_FILE as LINEUP_FILE_PATH,
    PET_BASIC_FIELDS,
    SKILL_CATEGORY_KEYS,
    SKILL_FIELDS,
    STAT_NAMES,
)
from utils.trait_best_partner import BestPartnerTraitService
from utils.ui_helpers import show_lineup_selection_dialog


class DamageWindowLogic:
    """
    伤害窗口业务逻辑类。

    功能：绑定 DamageWindow UI 控件的事件回调，处理：
          - 精灵名称输入/选择（on_pet_name_change / confirm_pet_input）
          - 技能名称输入/选择（on_skill_name_change / confirm_skill_entry）
          - 阵容加载模式（load_lineup_from_all_lineups）
          - 普通加载模式（load_all_data → build_cached_panel_data → load_panel_data）
          - 面板属性计算刷新（refresh_stat_values）
          - 技能按钮（load_skill_from_slot → fill_skill_fields）
          - 属性克制自动计算（update_element_multiplier_for_loaded_skill）
          - 伤害结算（run_calc）：选择物攻/魔攻路线，扣能，计算伤害，触发特性
          - 聚能（charge_energy）/ 重置（reset_all）

    外部参数：
    - view (DamageWindow):
        来源文件：ui/damage_window.py 中 DamageWindow.__init__() 创建
        含义：伤害窗口 UI 实例，包含 left_ui / right_ui 等控件引用
    - db_data (dict):
        来源文件：utils/data_manager.py DataManager.load_pet_db() 返回值
        含义：精灵数据库字典 {名称: 精灵数据}，用于按名称查找精灵详情

    内部参数：
    - self.view: 保存传入的 DamageWindow 实例
    - self.db_data: 精灵数据库字典
    - self.attr_values: 19 系属性下拉选项（来自 constants.ELEMENT_TYPES）
    - self.pet_names: 所有精灵名称的排序列表
    - self.cached_data: 从缓存文件读取的双方精灵+技能数据
    - self._setting_programmatically: 编程设置标志（用于阵容加载时防止重复触发）
    """

    # 缓存文件和阵容文件的路径（相对项目根目录 data/）
    CACHE_FILE = Path(__file__).resolve().parents[1] / CACHE_FILE_PATH
    LINEUPS_FILE = Path(__file__).resolve().parents[1] / LINEUP_FILE_PATH

    def __init__(self, view, db_data):
        """
        初始化伤害窗口业务逻辑。

        外部参数：
        - view / db_data: 见类文档

        内部参数：
        - self.pet_names: 从 db_data 的键（精灵名）排序得到
        - self.cached_data: 初始为空，加载后从缓存文件读取
        - self._setting_programmatically: 编程设置标志，用于 StringVar trace 回调
        """
        self.view = view
        self.db_data = db_data
        self.attr_values = ELEMENT_TYPES
        self.pet_names = sorted(db_data.keys())
        self.cached_data = {}
        self._setting_programmatically = False

        self.bind_events()

    # ==================== 面板运行态初始化 ====================

    def init_panel_runtime_state(self, ui_map):
        """
        初始化单个面板的运行时状态字段。

        功能：在 ui_map 中设置运行态初始值：
          - current_energy: 初始能量 10
          - trait_name: 特性名初始为空
          - active_skill_index / active_skill_entry: 默认选中第一个技能槽
          - loaded_pet_data / loaded_skills: 初始为空
          - 调用 BestPartnerTraitService.init_state()

        外部参数：
        - ui_map (dict):
            来源：bind_events() 中遍历 left_ui / right_ui 时传入
            含义：面板 UI 控件引用字典
        """
        ui_map["current_energy"] = 10
        ui_map["trait_name"] = ""
        ui_map["active_skill_index"] = 0
        ui_map["active_skill_entry"] = ui_map["skill_entries"][0]
        ui_map["loaded_pet_data"] = {}
        ui_map["loaded_skills"] = [{}, {}, {}, {}]
        BestPartnerTraitService.init_state(ui_map)

    def update_panel_status_label(self, ui_map):
        """
        将面板当前运行态同步到"状态"文本控件。

        功能：通过 BestPartnerTraitService.build_status_text() 构建状态文本，
              更新 status_label 控件的显示。

        外部参数：
        - ui_map: 面板 UI 控件引用字典
        """
        ui_map["status_label"].config(
            text=BestPartnerTraitService.build_status_text(ui_map)
        )

    # ==================== 事件绑定 ====================

    def bind_events(self):
        """
        绑定 DamageWindow 所有控件的事件和回调。

        功能：为以下控件绑定事件：
          - load_button: 阵容加载或普通加载（由 use_lineup_load 决定）
          - reset_button: 重置所有面板
          - left_to_right_button / right_to_left_button: 伤害计算按钮
          - 每个面板（left_ui / right_ui）：
            - atk_attr: 技能属性输入过滤
            - name_entry: 精灵名输入（KeyRelease/Return/Down/FocusOut）
            - name_var: StringVar trace（阵容模式下捕获下拉切换）
            - skill_entries: 技能输入（FocusIn/KeyRelease/Return/Down/FocusOut）
            - pet_result_listbox: 精灵候选列表点击/确认
            - skill_result_listbox: 技能候选列表点击/确认
            - skill_buttons: 技能槽位加载
            - wish/boss/retreat/energy/iv/nat: 功能按钮和下拉

        外部参数：无（使用 self.view.left_ui / self.view.right_ui）
        """
        # 加载按钮（阵容加载 or 普通加载）
        command = (
            self.load_lineup_from_all_lineups
            if self.view.use_lineup_load
            else self.load_all_data
        )
        self.view.load_button.config(command=command)

        # 重置按钮
        self.view.reset_button.config(command=self.reset_all)

        # 伤害计算按钮
        self.view.left_to_right_button.config(
            command=lambda: self.run_calc(
                self.view.left_ui,
                self.view.right_ui,
                self.view.left_to_right_result,
                "本人打对方伤害",
            )
        )
        self.view.right_to_left_button.config(
            command=lambda: self.run_calc(
                self.view.right_ui,
                self.view.left_ui,
                self.view.right_to_left_result,
                "对方打本人伤害",
            )
        )

        # 遍历左右两个面板
        for panel in (self.view.left_ui, self.view.right_ui):
            panel["panel_key"] = panel["frame"].cget("text")  # "本人" / "对方"
            self.init_panel_runtime_state(panel)

            # --- 技能属性输入过滤 ---
            panel["atk_attr"].bind(
                "<KeyRelease>",
                lambda event, combo=panel["atk_attr"]: self.on_attr_type(event, combo),
            )

            # --- 精灵名称输入事件 ---
            panel["name_entry"].bind(
                "<KeyRelease>",
                lambda event, ui_map=panel: self.on_pet_name_change(event, ui_map),
            )
            panel["name_entry"].bind(
                "<Return>",
                lambda event, ui_map=panel: self.confirm_pet_input(ui_map),
            )
            panel["name_entry"].bind(
                "<Down>",
                lambda event, ui_map=panel: self.focus_pet_popup(ui_map),
            )
            panel["name_entry"].bind(
                "<FocusOut>",
                lambda event, ui_map=panel: self.on_panel_entry_focus_out(
                    ui_map, "pet"
                ),
            )

            # --- 精灵名称 StringVar trace（捕获下拉框值变化） ---
            def on_name_var_changed(*args, ui_map=panel):
                self._on_name_var_changed(ui_map)

            panel["name_var"].trace_add("write", on_name_var_changed)

            # --- 技能输入事件 ---
            for skill_index, skill_entry in enumerate(panel["skill_entries"]):
                skill_entry.bind(
                    "<FocusIn>",
                    lambda event, ui_map=panel, idx=skill_index: self.set_active_skill_entry(
                        ui_map, idx
                    ),
                )
                skill_entry.bind(
                    "<KeyRelease>",
                    lambda event, ui_map=panel, idx=skill_index: self.on_skill_name_change(
                        event, ui_map, idx
                    ),
                )
                skill_entry.bind(
                    "<Return>",
                    lambda event, ui_map=panel, idx=skill_index: self.confirm_skill_entry(
                        ui_map, idx
                    ),
                )
                skill_entry.bind(
                    "<Down>",
                    lambda event, ui_map=panel, idx=skill_index: self.focus_skill_popup(
                        ui_map, idx
                    ),
                )
                skill_entry.bind(
                    "<FocusOut>",
                    lambda event, ui_map=panel: self.on_panel_entry_focus_out(
                        ui_map, "skill"
                    ),
                )

            # --- 精灵/技能候选列表事件 ---
            panel["pet_result_listbox"].bind(
                "<ButtonRelease-1>",
                lambda event, ui_map=panel: self.confirm_pet_input(
                    ui_map, use_popup_selection=True
                ),
            )
            panel["pet_result_listbox"].bind(
                "<Return>",
                lambda event, ui_map=panel: self.confirm_pet_input(
                    ui_map, use_popup_selection=True
                ),
            )
            panel["pet_result_listbox"].bind(
                "<Double-Button-1>",
                lambda event, ui_map=panel: self.confirm_pet_input(
                    ui_map, use_popup_selection=True
                ),
            )
            panel["skill_result_listbox"].bind(
                "<ButtonRelease-1>",
                lambda event, ui_map=panel: self.confirm_skill_entry(
                    ui_map, use_popup_selection=True
                ),
            )
            panel["skill_result_listbox"].bind(
                "<Return>",
                lambda event, ui_map=panel: self.confirm_skill_entry(
                    ui_map, use_popup_selection=True
                ),
            )
            panel["skill_result_listbox"].bind(
                "<Double-Button-1>",
                lambda event, ui_map=panel: self.confirm_skill_entry(
                    ui_map, use_popup_selection=True
                ),
            )

            # --- 技能按钮 ---
            for skill_index, button in enumerate(panel["skill_buttons"]):
                button.config(
                    command=lambda ui_map=panel, idx=skill_index: self.load_skill_from_slot(
                        ui_map, idx
                    )
                )

            # --- 功能按钮（部分为占位） ---
            panel["wish_button"].config(command=self.do_nothing)
            panel["boss_button"].config(command=self.do_nothing)
            panel["retreat_button"].config(command=self.do_nothing)
            panel["energy_button"].config(
                command=lambda ui_map=panel: self.charge_energy(ui_map)
            )

            # --- 个体/性格下拉更新事件 ---
            for widgets in panel["stats"].values():
                widgets["iv"].bind(
                    "<<ComboboxSelected>>",
                    lambda event, ui_map=panel: self.refresh_stat_values(ui_map),
                )
                widgets["nat"].bind(
                    "<<ComboboxSelected>>",
                    lambda event, ui_map=panel: self.refresh_stat_values(ui_map),
                )

            self.reset_skill_button_texts(panel)

    # ==================== 工具方法 ====================

    def do_nothing(self):
        """占位按钮响应函数：无操作。"""
        return

    def set_active_skill_entry(self, ui_map, skill_index):
        """
        记录当前正在编辑的技能输入框索引和引用。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - skill_index (int): 技能输入框索引（0-3）
        """
        ui_map["active_skill_index"] = skill_index
        ui_map["active_skill_entry"] = ui_map["skill_entries"][skill_index]

    def get_skill_entry(self, ui_map, skill_index=None):
        """
        获取指定（或当前激活）技能槽位的输入框引用。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - skill_index (int | None): 索引，None 则用 active_skill_index

        返回值：
        - ttk.Entry: 技能输入框控件
        """
        if skill_index is None:
            skill_index = ui_map.get("active_skill_index", 0)
        return ui_map["skill_entries"][skill_index]

    def get_skill_input(self, ui_map, skill_index):
        """
        读取指定技能槽位的输入文本。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - skill_index (int): 技能索引

        返回值：
        - str: 技能输入框中的文本
        """
        return self.get_skill_entry(ui_map, skill_index).get().strip()

    def reset_skill_button_texts(self, ui_map):
        """
        将所有技能按钮重置为默认文案"技能1"~"技能4"。

        外部参数：
        - ui_map: 面板 UI 引用字典
        """
        for skill_index, button in enumerate(ui_map["skill_buttons"]):
            button.config(text=f"技能{skill_index + 1}")

    def update_skill_button_texts_from_loaded(self, ui_map):
        """
        加载后按缓存的技能数据更新按钮文案。

        功能：遍历 4 个技能槽，如果 loaded_skills 中有技能名称，
              则更新对应按钮文本为技能名，否则保留默认文案。

        外部参数：
        - ui_map: 面板 UI 引用字典（含 loaded_skills 字段）
        """
        for skill_index, button in enumerate(ui_map["skill_buttons"]):
            skill_data = ui_map.get("loaded_skills", [{}, {}, {}, {}])[skill_index]
            skill_name = skill_data.get("技能名称") or skill_data.get("名称", "")
            button.config(text=skill_name if skill_name else f"技能{skill_index + 1}")

    def show_warning(self, message):
        """
        统一错误提示入口，确保提示框在主窗口前方居中显示。

        功能：提升窗口至顶层，显示 messagebox.showwarning 后恢复。

        外部参数：
        - message (str): 警告消息文本
        """
        self.view.update_idletasks()
        self.view.lift()
        self.view.focus_force()
        self.view.attributes("-topmost", True)
        try:
            messagebox.showwarning("提示", message, parent=self.view)
        finally:
            self.view.attributes("-topmost", False)

    # ==================== 重置 ====================

    def reset_all(self):
        """
        将整个页面恢复到初始打开状态。

        功能：清空 cached_data，遍历左右面板，恢复所有输入控件到默认值，
              重置技能按钮文本，清空伤害显示。
        """
        self.cached_data = {}
        for panel in (self.view.left_ui, self.view.right_ui):
            panel["name_entry"]["state"] = "normal"
            panel["name_entry"]["values"] = []
            panel["name_var"].set("")
            panel["name_entry"].delete(0, "end")
            panel["lineup_pets_data"] = {}
            self.reset_panel_inputs(panel, clear_skill_entries=True)
            self.hide_pet_popup(panel)
            self.hide_skill_popup(panel)
            self.reset_skill_button_texts(panel)

        self.view.left_to_right_result.config(text="造成伤害: 0")
        self.view.right_to_left_result.config(text="造成伤害: 0")
        self.view.update_idletasks()

    # ==================== 普通加载模式 ====================

    def load_all_data(self):
        """
        统一加载入口：校验输入 → 构建缓存数据 → 写入缓存 → 加载面板。

        功能：验证双方精灵名和技能名非空，调用 build_cached_panel_data()
              构建双方缓存数据，写入 battle_pet_cache.json，再调用
              load_panel_data() 加载到 UI 面板。

        外部参数：无（从 self.view.left_ui / right_ui 读取输入）

        内部参数：
        - left_name / left_first_skill / right_name: 校验输入非空
        - payload: 缓存数据字典，键为 "本人" / "对方"
        """
        left_name = self.view.left_ui["name_entry"].get().strip()
        left_first_skill = self.get_skill_input(self.view.left_ui, 0)
        right_name = self.view.right_ui["name_entry"].get().strip()

        if not left_name:
            self.show_warning("请输入本人精灵名称")
            return
        if not left_first_skill:
            self.show_warning("请输入本人技能名称")
            return
        if not right_name:
            self.show_warning("请输入对方精灵名称")
            return

        payload = {}
        for panel in (self.view.left_ui, self.view.right_ui):
            cached_panel_data = self.build_cached_panel_data(
                panel, require_first_skill=(panel is self.view.left_ui)
            )
            if not cached_panel_data:
                return
            payload[panel["panel_key"]] = cached_panel_data

        self.write_cache_file(payload)
        self.cached_data = self.read_cache_file()

        if not self.load_panel_data(self.view.left_ui):
            return
        if not self.load_panel_data(self.view.right_ui):
            return

        self.update_skill_button_texts_from_loaded(self.view.left_ui)
        self.update_skill_button_texts_from_loaded(self.view.right_ui)

    # ==================== 阵容加载模式 ====================

    def load_lineup_from_all_lineups(self):
        """
        阵容加载入口：弹出选择对话框 → 填充下拉框 → 默认加载第一个精灵。

        功能：调用 ui_helpers.show_lineup_selection_dialog() 显示阵容选择对话框，
              获取用户选择的己方/对方阵容名和阵容数据，将阵容中的精灵名称填充到
              双方精灵下拉框，默认加载各自第一个精灵的数据到面板。

        外部参数：无（调用 show_lineup_selection_dialog 获取用户选择）

        内部参数：
        - selection: (己方阵容名, 对方阵容名, 完整阵容数据) 三元组
        - ally_name / enemy_name: 用户选中的阵容名
        - lineup_data: 完整阵容数据 dict
        - ally_pets / enemy_pets: 对应阵容中的精灵列表
        """
        selection = show_lineup_selection_dialog(self.view, self.read_all_lineups_file())
        if selection is None:
            return

        ally_name, enemy_name, lineup_data = selection
        ally_pets = lineup_data["己方"][ally_name]
        enemy_pets = lineup_data["对方"][enemy_name]

        if not ally_pets:
            self.show_warning(f"己方阵容「{ally_name}」为空")
            return

        if not enemy_pets:
            self.show_warning(f"对方阵容「{enemy_name}」为空")
            return

        self._setup_lineup_panel(self.view.left_ui, ally_pets)
        self._setup_lineup_panel(self.view.right_ui, enemy_pets)

    def _setup_lineup_panel(self, ui_map, pets_in_lineup):
        """
        将面板切换到阵容模式：填充精灵下拉框并默认加载第一个精灵。

        功能：从阵容精灵列表提取名称填充到 Combobox 的 values，
              将 state 设为 readonly 禁止手动输入，创建名称→精灵条目的映射字典，
              默认选中第一个精灵并加载其面板数据。

        外部参数：
        - ui_map (dict):
            来源：load_lineup_from_all_lineups() 中传入 left_ui / right_ui
            含义：面板 UI 控件引用字典
        - pets_in_lineup (list):
            来源：load_lineup_from_all_lineups() 中从阵容数据提取
            含义：阵容中的精灵条目列表

        内部参数：
        - pet_names: 阵容中所有精灵的名称列表
        - combobox: 精灵名称 Combobox 控件
        """
        pet_names = [p.get("名字", "") for p in pets_in_lineup if p.get("名字")]
        ui_map["lineup_pets_data"] = {
            p["名字"]: p for p in pets_in_lineup if p.get("名字")
        }

        combobox = ui_map["name_entry"]
        combobox["values"] = pet_names
        combobox["state"] = "readonly"
        self.hide_pet_popup(ui_map)
        self.hide_skill_popup(ui_map)

        if pet_names:
            self._setting_programmatically = True
            try:
                combobox.set(pet_names[0])
                self.apply_lineup_pet_to_panel(ui_map, pets_in_lineup[0])
            finally:
                self._setting_programmatically = False

    def _on_name_var_changed(self, ui_map):
        """
        StringVar 值变化回调（捕获阵容模式下下拉框的值变化）。

        功能：当用户在下拉框中选择其他精灵时触发（排除编程设置），
              调用 on_pet_combobox_select() 加载对应精灵数据。

        外部参数：
        - ui_map: 面板 UI 引用字典

        内部逻辑：三个守卫条件——
          1. _setting_programmatically 为 True 时跳过
          2. readonly 状态才处理（只在下拉模式触发）
          3. lineup_pets_data 存在才处理
        """
        if self._setting_programmatically:
            return
        if ui_map["name_entry"].cget("state") != "readonly":
            return
        if not ui_map.get("lineup_pets_data"):
            return
        self.on_pet_combobox_select(ui_map)

    def on_pet_combobox_select(self, ui_map):
        """
        精灵下拉框选择时加载对应精灵的数据到面板。

        功能：从 StringVar 获取选中精灵名，在 lineup_pets_data 中查找条目，
              调用 apply_lineup_pet_to_panel 填充面板。

        外部参数：
        - ui_map: 面板 UI 引用字典（含 lineup_pets_data 字段）

        内部参数：
        - pet_name: 用户选中的精灵名称
        - pet_entry: 阵容中对应的精灵条目 dict
        """
        if ui_map["name_entry"].cget("state") != "readonly":
            return
        pet_name = ui_map["name_var"].get()
        pet_entry = ui_map.get("lineup_pets_data", {}).get(pet_name)
        if pet_entry:
            self.apply_lineup_pet_to_panel(ui_map, pet_entry)

    def read_all_lineups_file(self):
        """
        读取阵容数据文件（all_lineups.json）。

        功能：从 LINEUPS_FILE 路径读取 JSON 文件，返回阵容数据字典。

        返回值：
        - dict: 阵容数据，失败时返回 None
        """
        if not self.LINEUPS_FILE.exists():
            self.show_warning("找不到 data/all_lineups.json")
            return None
        try:
            with self.LINEUPS_FILE.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as exc:
            self.show_warning(f"读取all_lineups.json失败：{exc}")
            return None

    def apply_lineup_pet_to_panel(self, ui_map, pet_entry):
        """
        将阵容中的精灵条目数据应用到面板（属性/技能/战斗信息）。

        功能：加载阵容精灵的数值配置到面板：
          1. 设置精灵名称到 Combobox
          2. 加载数值配置（基础属性、IV、性格系数）到 stats 区域
          3. 从数据库加载技能候选列表
          4. 加载技能配置（名称、详细数据）到技能输入框和按钮
          5. 加载克制表、特性到战斗信息
          6. 刷新面板值和技能按钮

        外部参数：
        - ui_map (dict):
            来源：on_pet_combobox_select() 传入面板 ui_map
            含义：面板 UI 控件引用字典
        - pet_entry (dict):
            来源：on_pet_combobox_select() 从 lineup_pets_data 获取
            含义：阵容中的精灵条目，含"名字"、"数值配置"、"技能配置"等字段

        内部参数：
        - pet_name: 精灵名称
        - pet_config: 数值配置 dict
        - base_stats / iv_values / nature_values: 属性/个体/性格数据
        - raw_skills: 技能配置原始列表（最多 4 个）
        - normalized_skills: 规范化后的技能数据列表
        - stat_name / widgets: 遍历六维属性
        - skill_name: 当前技能名称
        - entry / idx: 技能输入框及其索引
        """
        pet_name = pet_entry.get("名字", "")
        ui_map["name_entry"].set(pet_name)

        self.hide_pet_popup(ui_map)
        self.hide_skill_popup(ui_map)
        ui_map["skill_candidates"] = []
        ui_map["active_skill_index"] = 0
        ui_map["active_skill_entry"] = ui_map["skill_entries"][0]

        # 加载数值配置
        pet_config = pet_entry.get("数值配置", {})
        base_stats = pet_config.get("基础属性", {})
        iv_values = pet_config.get("IV", {})
        nature_values = pet_config.get("性格系数", {})

        for stat_name, widgets in ui_map["stats"].items():
            widgets["base"].config(text=str(base_stats.get(stat_name, 0)))
            widgets["iv"].set(str(iv_values.get(stat_name, "0")))
            widgets["nat"].set(str(nature_values.get(stat_name, "1.0")))

        ui_map["loaded_pet_data"] = pet_entry
        self.populate_skill_options(ui_map, self.db_data.get(pet_name, {}))

        # 加载技能配置
        raw_skills = pet_entry.get("技能配置", [])
        if len(raw_skills) > 4:
            raw_skills = raw_skills[:4]
        normalized_skills = [
            self.normalize_skill_entry(skill) for skill in raw_skills
        ]
        ui_map["loaded_skills"] = normalized_skills + [{}] * (
            4 - len(normalized_skills)
        )
        for idx in range(4):
            entry = ui_map["skill_entries"][idx]
            entry.delete(0, "end")
            skill_name = ui_map["loaded_skills"][idx].get("技能名称", "")
            if skill_name:
                entry.insert(0, skill_name)
            ui_map["skill_buttons"][idx].config(
                text=skill_name or f"技能{idx + 1}"
            )

        # 加载精灵特性/克制信息
        self.load_pet_stats(
            ui_map,
            {
                "名字": pet_name,
                "基础属性": base_stats,
                "克制表": pet_entry.get("克制表", {}),
                "特性": pet_entry.get("特性", {}),
            },
        )

        self.refresh_stat_values(ui_map)
        self.update_skill_button_texts_from_loaded(ui_map)

    # ==================== 缓存数据构建 ====================

    def build_cached_panel_data(self, ui_map, require_first_skill):
        """
        从原始数据库构建单侧缓存数据。

        功能：读取用户输入的精灵名和技能名，从 db_data 获取精灵数据和技能详情，
              组装为缓存 dict（含名字/种族/基础属性/克制表/特性/技能列表）。

        外部参数：
        - ui_map (dict):
            来源：load_all_data() 中传入 left_ui / right_ui
            含义：面板 UI 引用字典
        - require_first_skill (bool):
            来源：load_all_data() 中本人面板传入 True，对方面板传入 False
            含义：是否要求第一个技能非空（本人必须填写技能）

        内部参数：
        - pet_name: 面板中的精灵名称
        - skill_names: 4 个技能输入框的文本列表
        - pet_data: 从 db_data 获取的精灵数据
        - cached_panel: 缓存 dict 结构
        - skill_data: 查找到的技能详情

        返回值：
        - dict: 构建成功的缓存数据
        - None: 精灵或技能未找到
        """
        pet_name = ui_map["name_entry"].get().strip()
        skill_names = [entry.get().strip() for entry in ui_map["skill_entries"]]

        pet_data = self.db_data.get(pet_name)
        if not pet_data:
            self.show_warning(f"未找到精灵: {pet_name}")
            return None

        if require_first_skill and not skill_names[0]:
            self.show_warning("请输入本人技能名称")
            return None

        cached_panel = {
            field: pet_data.get(field, {} if field != "名字" else pet_name)
            for field in PET_BASIC_FIELDS
        }
        cached_panel["技能列表"] = []

        for skill_name in skill_names:
            if not skill_name:
                cached_panel["技能列表"].append({})
                continue

            skill_data = self.find_skill_data(pet_data, skill_name)
            if not skill_data:
                self.show_warning(f"未找到技能: {skill_name}")
                return None
            cached_panel["技能列表"].append(
                {field: skill_data.get(field, "") for field in SKILL_FIELDS}
            )

        return cached_panel

    def write_cache_file(self, payload):
        """
        把当前加载结果写入缓存文件（battle_pet_cache.json）。

        外部参数：
        - payload (dict):
            来源：load_all_data() 中构建的 {"本人": {...}, "对方": {...}}
            含义：要写入缓存的双方精灵+技能数据
        """
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with self.CACHE_FILE.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=4)

    def read_cache_file(self):
        """
        读取缓存文件内容。

        返回值：
        - dict: 缓存数据，文件不存在时返回空 dict
        """
        if not self.CACHE_FILE.exists():
            return {}
        with self.CACHE_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    # ==================== 属性输入过滤 ====================

    def on_attr_type(self, event, combo):
        """
        技能属性输入时提供下拉筛选功能。

        功能：在 Combobox 中输入时，按输入文本动态过滤下拉选项列表。

        外部参数：
        - event: 键盘事件
        - combo (ttk.Combobox):
            来源：bind_events() 中 panel["atk_attr"]
            含义：技能属性下拉框控件
        """
        value = combo.get()
        if value == "":
            combo["values"] = self.attr_values
        else:
            combo["values"] = [item for item in self.attr_values if value in item]
        combo.event_generate("<Down>")

    # ==================== 面板数据加载 ====================

    def load_panel_data(self, ui_map):
        """
        从缓存中加载单侧精灵与技能数据到 UI 面板。

        功能：从 cached_data 中取出对应 panel_key 的数据，加载精灵属性、
              技能候选，默认加载第一个技能的参数。

        外部参数：
        - ui_map: 面板 UI 引用字典

        内部参数：
        - cached_panel_data: 缓存中的该侧数据
        - pet_name: 精灵名

        返回值：
        - bool: 加载成功 True，失败 False
        """
        cached_panel_data = self.cached_data.get(ui_map["panel_key"], {})
        pet_name = cached_panel_data.get("名字", "")
        if not pet_name:
            return False

        self.hide_pet_popup(ui_map)
        self.hide_skill_popup(ui_map)
        self.reset_panel_inputs(ui_map, clear_skill_entries=False)

        ui_map["loaded_pet_data"] = cached_panel_data
        ui_map["loaded_skills"] = list(cached_panel_data.get("技能列表", []))
        while len(ui_map["loaded_skills"]) < 4:
            ui_map["loaded_skills"].append({})

        self.load_pet_stats(ui_map, cached_panel_data)
        self.populate_skill_options(ui_map, self.db_data.get(pet_name, {}))

        if ui_map["loaded_skills"][0].get("技能名称"):
            self.load_skill_from_slot(ui_map, 0, silent=True)

        return True

    def reset_panel_inputs(self, ui_map, clear_skill_entries):
        """
        恢复当前面板所有输入控件到默认值。

        功能：清空技能输入（可选）、技能候选、运行态字段，
              重置技能参数（类型/属性/威力/本系加成/克制等）、
              重置六维属性值、战斗信息、能量、特性显示。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - clear_skill_entries (bool):
            来源：load_panel_data() 传入 False，reset_all() 传入 True
            含义：是否同时清空技能输入框内容
        """
        if clear_skill_entries:
            for skill_entry in ui_map["skill_entries"]:
                skill_entry.delete(0, "end")

        ui_map["skill_candidates"] = []
        ui_map["active_skill_index"] = 0
        ui_map["active_skill_entry"] = ui_map["skill_entries"][0]
        ui_map["loaded_pet_data"] = {}
        ui_map["loaded_skills"] = [{}, {}, {}, {}]
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

    # ==================== 精灵名称搜索/选择 ====================

    def on_pet_name_change(self, event, ui_map):
        """
        处理精灵名输入变化事件。

        功能：在非 readonly 模式下（普通加载模式），按按键类型分发：
          - Return → confirm_pet_input
          - Escape → 隐藏弹出列表
          - Down → 焦点移到弹出列表
          - 其他（Tab/Shift/Ctrl）→ 忽略
          - 其余按键 → 更新技能候选（如果精灵已存在）、显示弹出列表

        外部参数：
        - event: 键盘事件
        - ui_map: 面板 UI 引用字典
        """
        if ui_map["name_entry"].cget("state") == "readonly":
            return
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
        """
        确认精灵名称输入。

        功能：在非 readonly 模式下，如果 use_popup_selection 为 True，
              将弹出列表选中值写入输入框。然后设置焦点、隐藏列表。
              如果输入精灵在 db_data 中存在，更新技能候选列表。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - use_popup_selection (bool): 是否使用弹出列表选中值
        """
        if ui_map["name_entry"].cget("state") == "readonly":
            return "break"
        if use_popup_selection and ui_map["pet_result_listbox"].curselection():
            selected = ui_map["pet_result_listbox"].get(
                ui_map["pet_result_listbox"].curselection()[0]
            )
            ui_map["name_entry"].delete(0, "end")
            ui_map["name_entry"].insert(0, selected)

        ui_map["name_entry"].focus_set()
        ui_map["name_entry"].icursor("end")
        self.hide_pet_popup(ui_map)

        pet_name = ui_map["name_entry"].get().strip()
        if pet_name in self.db_data:
            self.populate_skill_options(ui_map, self.db_data[pet_name])
        return "break"

    # ==================== 属性加载 ====================

    def load_pet_stats(self, ui_map, pet_data):
        """
        将精灵基础属性加载到面板 stats 区域并刷新实战属性。

        功能：遍历六维属性，将基础属性数据写入对应 base Label，
              调用 load_pet_info() 加载特性和刷新计算。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - pet_data (dict):
            来源：apply_lineup_pet_to_panel() 或 load_panel_data()
            含义：精灵数据（含"基础属性"字段）
        """
        base_stats = pet_data.get("基础属性", {})
        for stat_name in STAT_NAMES:
            if stat_name in ui_map["stats"]:
                ui_map["stats"][stat_name]["base"].config(
                    text=str(base_stats.get(stat_name, 0))
                )
        self.load_pet_info(ui_map, pet_data)
        self.refresh_stat_values(ui_map)

    def populate_skill_options(self, ui_map, pet_data):
        """
        根据原始精灵数据构建技能候选列表。

        功能：从精灵数据的三个技能分类中提取技能名称，去重排序后存入
              ui_map["skill_candidates"]。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - pet_data (dict): 精灵原始数据（来自 db_data）
        """
        skill_names = []
        for key in SKILL_CATEGORY_KEYS:
            skill_names.extend(
                [
                    skill.get("技能名称", "")
                    for skill in pet_data.get(key, [])
                    if skill.get("技能名称")
                ]
            )
        ui_map["skill_candidates"] = sorted(set(skill_names))

    def find_skill_data(self, pet_data, skill_name):
        """
        在精灵所有技能集合中查找指定名称的技能详情。

        功能：遍历三个技能分类，按"技能名称"或"名称"字段匹配。

        外部参数：
        - pet_data (dict): 精灵原始数据
        - skill_name (str): 要查找的技能名称

        返回值：
        - dict: 匹配的技能详情，未找到返回 None
        """
        for key in SKILL_CATEGORY_KEYS:
            for skill in pet_data.get(key, []):
                if (
                    skill.get("技能名称") == skill_name
                    or skill.get("名称") == skill_name
                ):
                    return skill
        return None

    def normalize_skill_entry(self, skill_data):
        """
        规范化技能数据条目，确保包含所有标准字段。

        功能：用 SKILL_FIELDS 中的字段名补齐缺失字段，若"技能名称"为空
              则尝试使用"名称"字段。

        外部参数：
        - skill_data (dict | None):
            来源：阵容文件中技能配置的条目
            含义：原始技能数据，可能使用"名称"而非"技能名称"键

        返回值：
        - dict: 规范化后的技能数据，含"技能名称"/"属性"/"消耗"/"类型"/"威力"/"描述"
        """
        if not skill_data:
            return {}
        normalized = {field: skill_data.get(field, "") for field in SKILL_FIELDS}
        if not normalized.get("技能名称"):
            normalized["技能名称"] = skill_data.get("名称", "")
        return normalized

    # ==================== 技能参数自动填充 ====================

    def fill_skill_fields(self, ui_map, skill_data):
        """
        把技能详情数据写入"技能与环境参数"区域。

        功能：根据技能数据设置技能类型、技能属性、威力、耗能，
              自动计算本系加成（调用 calculate_stab）。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - skill_data (dict): 技能详情数据

        内部参数：
        - skill_type: 技能类型（物攻/魔攻/状态）
        - skill_attr: 技能属性（如"火"）
        - power: 技能威力
        - cost: 技能耗能
        - pet_name: 精灵名
        - pet_elements: 精灵的元素列表
        """
        skill_type = skill_data.get("类型", "物攻")
        skill_attr = skill_data.get("属性", "无") or "无"
        power = skill_data.get("威力", "0")
        cost = skill_data.get("消耗", "0")
        pet_name = ui_map.get("loaded_pet_data", {}).get("名字", "")
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
        ui_map["stab_combo"].set(
            str(calculate_stab(skill_type, skill_attr, pet_elements))
        )

    def load_skill_from_slot(self, ui_map, skill_index, silent=False):
        """
        按缓存技能槽位加载技能详情到参数区。

        功能：从 loaded_skills[skill_index] 获取技能数据，调用
              fill_skill_fields 填入参数区，再调用
              update_element_multiplier_for_loaded_skill 自动计算克制倍率。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - skill_index (int): 技能槽位索引（0-3）
        - silent (bool):
            来源：load_panel_data() 传入 True
            含义：失败时是否静默（不弹警告）
        """
        self.set_active_skill_entry(ui_map, skill_index)

        loaded_skills = ui_map.get("loaded_skills", [{}, {}, {}, {}])
        skill_data = (
            loaded_skills[skill_index]
            if skill_index < len(loaded_skills)
            else {}
        )
        skill_data = self.normalize_skill_entry(skill_data)
        if not skill_data or not skill_data.get("技能名称"):
            if not silent:
                self.show_warning(f"第{skill_index + 1}个技能尚未填写")
            return False

        self.fill_skill_fields(ui_map, skill_data)
        self.update_element_multiplier_for_loaded_skill(ui_map)
        return True

    def update_element_multiplier_for_loaded_skill(self, attacker_ui):
        """
        加载技能后自动按对方克制表刷新属性克制倍率。

        功能：确定防守方，获取防守方的克制表，读取攻击方技能的属性和威力，
              调用 calculate_element_multiplier 自动计算，填入 element_combo。

        外部参数：
        - attacker_ui (dict):
            来源：load_skill_from_slot() 中传入
            含义：攻击方面板 UI 引用字典

        内部参数：
        - defender_ui: 防守方面板 UI（攻击方的对面）
        - defender_kz_table: 防守方精灵的克制表
        - skill_attr: 技能属性
        - skill_power: 技能威力
        - multiplier: 计算得到的克制倍率
        """
        defender_ui = (
            self.view.right_ui if attacker_ui is self.view.left_ui else self.view.left_ui
        )
        defender_kz_table = defender_ui.get("loaded_pet_data", {}).get("克制表", {})
        skill_attr = attacker_ui["atk_attr"].get().strip()
        skill_power = attacker_ui["power_entry"].get().strip()
        multiplier = calculate_element_multiplier(
            skill_attr, skill_power, defender_kz_table
        )
        attacker_ui["element_combo"].set(str(multiplier))

    # ==================== 精灵弹出列表 ====================

    def get_filtered_pets(self, ui_map):
        """
        按当前输入过滤精灵候选列表。

        外部参数：
        - ui_map: 面板 UI 引用字典

        返回值：
        - list: 过滤后的精灵名称列表
        """
        value = ui_map["name_entry"].get().strip()
        if not value:
            return self.pet_names[:]
        return [name for name in self.pet_names if value in name]

    def show_pet_popup(self, ui_map):
        """
        显示精灵候选弹出列表。

        功能：获取过滤后的精灵列表，填充到 pet_result_listbox，
              选中第一项，调整高度，若未显示则 pack 显示。

        外部参数：
        - ui_map: 面板 UI 引用字典
        """
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
            ui_map["pet_result_frame"].pack(
                fill="x", padx=8, pady=(0, 4), after=ui_map["top_frame"]
            )

    def hide_pet_popup(self, ui_map):
        """隐藏精灵候选弹出列表。"""
        if ui_map["pet_result_frame"].winfo_ismapped():
            ui_map["pet_result_frame"].pack_forget()

    def focus_pet_popup(self, ui_map):
        """将键盘焦点移到精灵候选列表。"""
        filtered = self.get_filtered_pets(ui_map)
        if not filtered:
            return "break"
        self.show_pet_popup(ui_map)
        ui_map["pet_result_listbox"].focus_set()
        return "break"

    # ==================== 技能弹出列表 ====================

    def get_filtered_skills(self, ui_map):
        """
        按当前输入过滤技能候选列表。

        外部参数：
        - ui_map: 面板 UI 引用字典

        返回值：
        - list: 过滤后的技能名称列表
        """
        active_entry = ui_map.get("active_skill_entry", ui_map["skill_entries"][0])
        value = active_entry.get().strip()
        candidates = ui_map.get("skill_candidates", [])
        if not value:
            return candidates[:]
        return [name for name in candidates if value in name]

    def on_skill_name_change(self, event, ui_map, skill_index):
        """
        处理技能名输入变化事件。

        功能：记录当前激活的技能输入框，按按键类型分发：
          - Return → confirm_skill_entry
          - Escape → 隐藏
          - Down → 焦点移到列表
          - 其他 → 更新技能候选并显示弹出列表

        外部参数：
        - event: 键盘事件
        - ui_map: 面板 UI 引用字典
        - skill_index (int): 技能索引
        """
        self.set_active_skill_entry(ui_map, skill_index)

        if event.keysym == "Return":
            return self.confirm_skill_entry(ui_map, skill_index)
        if event.keysym == "Escape":
            self.hide_skill_popup(ui_map)
            return "break"
        if event.keysym == "Down":
            return self.focus_skill_popup(ui_map, skill_index)
        if event.keysym in {"Up", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return

        pet_name = ui_map["name_entry"].get().strip()
        if pet_name in self.db_data:
            self.populate_skill_options(ui_map, self.db_data[pet_name])
        self.show_skill_popup(ui_map)

    def confirm_skill_entry(self, ui_map, skill_index=None, use_popup_selection=False):
        """
        确认技能输入：将弹出列表选择同步到技能输入框。

        功能：如果 use_popup_selection 为 True 且列表有选中项，则使用选中值；
              否则使用列表第一项（仅在无选中时）。将值写入输入框。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - skill_index (int | None): 技能索引，None 则使用 active_skill_index
        - use_popup_selection (bool): 是否使用弹出列表选中值

        内部参数：
        - target_entry: 目标技能输入框
        - selected: 从弹出列表获取的选中值
        - current_selection: 当前列表选中项
        """
        if skill_index is not None:
            self.set_active_skill_entry(ui_map, skill_index)

        target_entry = ui_map.get("active_skill_entry", ui_map["skill_entries"][0])
        selected = None
        if ui_map["skill_result_listbox"].size() > 0:
            current_selection = ui_map["skill_result_listbox"].curselection()
            if current_selection:
                selected = ui_map["skill_result_listbox"].get(current_selection[0])
            elif not use_popup_selection:
                selected = ui_map["skill_result_listbox"].get(0)

        if selected:
            target_entry.delete(0, "end")
            target_entry.insert(0, selected)

        target_entry.focus_set()
        target_entry.icursor("end")
        self.hide_skill_popup(ui_map)
        return "break"

    def show_skill_popup(self, ui_map):
        """
        显示技能候选弹出列表。

        功能：获取过滤后的技能列表，至少输入 1 个字符才显示，
              填充到 skill_result_listbox，选中第一项。

        外部参数：
        - ui_map: 面板 UI 引用字典
        """
        filtered = self.get_filtered_skills(ui_map)
        active_entry = ui_map.get("active_skill_entry", ui_map["skill_entries"][0])
        if len(active_entry.get().strip()) < 1 or not filtered:
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
            after_widget = (
                ui_map["pet_result_frame"]
                if ui_map["pet_result_frame"].winfo_ismapped()
                else ui_map["top_frame"]
            )
            ui_map["skill_result_frame"].pack(
                fill="x", padx=8, pady=(0, 4), after=after_widget
            )

    def hide_skill_popup(self, ui_map):
        """隐藏技能候选弹出列表。"""
        if ui_map["skill_result_frame"].winfo_ismapped():
            ui_map["skill_result_frame"].pack_forget()

    def focus_skill_popup(self, ui_map, skill_index=None):
        """将键盘焦点移到技能候选列表。"""
        if skill_index is not None:
            self.set_active_skill_entry(ui_map, skill_index)
        filtered = self.get_filtered_skills(ui_map)
        if not filtered:
            return "break"
        self.show_skill_popup(ui_map)
        ui_map["skill_result_listbox"].focus_set()
        return "break"

    # ==================== 失焦处理 ====================

    def on_panel_entry_focus_out(self, ui_map, popup_type):
        """
        输入框失焦后延迟判断是否需要隐藏候选列表。

        功能：延迟 120ms 后调用 hide_popup_if_needed。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - popup_type (str): "pet" 或 "skill"，指定要隐藏的弹出类型
        """
        self.view.after(120, lambda: self.hide_popup_if_needed(ui_map, popup_type))

    def hide_popup_if_needed(self, ui_map, popup_type):
        """
        根据当前焦点决定是否关闭候选列表。

        功能：检查焦点是否在弹出列表的 popdown 窗口上（Combobox 弹出菜单）、
              或仍在对应的输入框/候选列表上，如果在则保留，否则隐藏。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - popup_type (str): "pet" 或 "skill"
        """
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
            return

        if focused == ui_map["skill_result_listbox"] or focused in ui_map["skill_entries"]:
            return
        self.hide_skill_popup(ui_map)

    # ==================== 战斗信息 ====================

    def load_pet_info(self, ui_map, pet_data):
        """
        把精灵特性信息写到"战斗信息"区域。

        功能：从 pet_data 提取特性名称和效果描述，更新到 trait_name_label
              和 trait_desc_label，初始化"最好的伙伴"运行时状态，重置能量显示。

        外部参数：
        - ui_map: 面板 UI 引用字典
        - pet_data (dict):
            来源：load_pet_stats() 中传入
            含义：精灵数据（含"特性"字段）
        """
        trait_data = pet_data.get("特性", {})
        trait_name = trait_data.get("名称", "-")
        trait_desc = trait_data.get("效果描述", "-")
        ui_map["trait_name"] = trait_name
        BestPartnerTraitService.init_state(ui_map)
        ui_map["energy_label"].config(text="当前能量：10")
        ui_map["trait_name_label"].config(text=f"特性：{trait_name}")
        ui_map["trait_desc_label"].config(text=f"效果：{trait_desc}")
        self.update_panel_status_label(ui_map)

    def charge_energy(self, ui_map):
        """
        聚能操作：恢复 5 点能量并同步显示。

        外部参数：
        - ui_map: 面板 UI 引用字典（含 current_energy 和 energy_label）
        """
        ui_map["current_energy"] = ui_map.get("current_energy", 10) + 5
        ui_map["energy_label"].config(
            text=f"当前能量：{ui_map['current_energy']}"
        )

    def refresh_stat_values(self, ui_map):
        """
        按当前个体值/性格系数/特性状态重新计算并刷新面板值。

        功能：遍历六维属性，调用 calc_stat() 计算基础面板值，
              受"最好的伙伴"影响的属性（攻防速）乘以特性倍率，
              结果写入 result Label。

        外部参数：
        - ui_map: 面板 UI 引用字典

        内部参数：
        - panel_multiplier: 最好的伙伴特性当前倍率
        - base_result: calc_stat 计算的基础面板值
        - shown_result: 乘以特性倍率后的显示值
        """
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

    # ==================== 伤害计算 ====================

    def run_calc(self, attacker_ui, defender_ui, result_label, label_prefix):
        """
        执行一次完整的伤害计算流程。

        功能：完成以下步骤：
          1. 刷新双方面板值
          2. 根据攻击类型（物攻/魔攻/状态）选择对应的攻防属性
          3. 验证能量是否满足技能消耗
          4. 调用 calculate_final_damage 计算伤害
          5. 调用 BestPartnerTraitService.on_after_damage 触发特性
          6. 更新攻击方能量（扣能 + 特性回能）
          7. 更新伤害结果标签

        外部参数：
        - attacker_ui (dict):
            来源：bind_events() 中传入 left_ui 或 right_ui
            含义：攻击方面板 UI 引用字典
        - defender_ui (dict):
            来源：bind_events() 中传入对应的防守方 UI
            含义：防守方面板 UI 引用字典
        - result_label (ttk.Label):
            来源：bind_events() 中传入 left_to_right_result 或 right_to_left_result
            含义：显示"造成伤害: XXX"的标签
        - label_prefix (str):
            来源：bind_events() 中传入的描述文本
            含义：日志用描述，如"本人打对方伤害"

        内部参数：
        - atk_type: 技能类型（物攻/魔攻/状态）
        - atk_val: 对应攻击属性面板值
        - dfn_val: 对应防御属性面板值
        - skill_cost: 技能消耗能量
        - current_energy: 攻击方当前能量
        - total_damage: 计算得到的最终伤害
        - element_mult: 属性克制倍率
        - energy_gain: 特性触发带来的能量恢复
        """
        self.refresh_stat_values(attacker_ui)
        self.refresh_stat_values(defender_ui)

        # --- 攻击/防御属性选择 ---
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

        # --- 能量校验 ---
        try:
            skill_cost = int(float(attacker_ui["cost_entry"].get()))
        except (TypeError, ValueError):
            skill_cost = 0
        if skill_cost < 0:
            skill_cost = 0

        current_energy = attacker_ui.get("current_energy", 10)
        if current_energy < skill_cost:
            self.show_warning(
                f"能量不足：当前能量{current_energy}，技能耗能{skill_cost}"
            )
            return

        # --- 核心伤害计算 ---
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

        # --- 特性触发判定 ---
        try:
            element_mult = float(attacker_ui["element_combo"].get())
        except (TypeError, ValueError):
            element_mult = 1

        energy_gain = BestPartnerTraitService.on_after_damage(
            attacker_ui, element_mult, total_damage
        )
        if energy_gain > 0:
            self.update_panel_status_label(attacker_ui)

        # --- 能量更新 ---
        attacker_ui["current_energy"] = max(
            0, current_energy - skill_cost + energy_gain
        )
        attacker_ui["energy_label"].config(
            text=f"当前能量：{attacker_ui['current_energy']}"
        )

        # --- 结果更新 ---
        result_label.config(text=f"造成伤害: {total_damage}")
        self.refresh_stat_values(attacker_ui)
        self.refresh_stat_values(defender_ui)
