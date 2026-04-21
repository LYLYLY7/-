"""最好的伙伴特性模块。

这个文件只负责处理“最好的伙伴”特性，不直接操作 UI 控件。
窗口逻辑层（DamageWindowLogic）会把运行时数据传给这里，由这里返回结果。
"""


class BestPartnerTraitService:
    """处理“最好的伙伴”特性的独立服务类。"""

    TRAIT_NAME = "最好的伙伴"
    TRIGGER_MULTIPLIER = 1.2
    ENERGY_RECOVERY = 2

    @staticmethod
    def init_state(ui_map):
        """初始化与特性有关的运行态字段。

        参数：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`init_panel_runtime_state()` 与 `load_pet_info()`
            中 `BestPartnerTraitService.init_state(ui_map)`（约在该文件 21 行、533 行附近）。
          - 上游对象来源：`ui/damage_window.py` 的 `setup_ui()` 中创建的
            `self.left_ui / self.right_ui` 字典。
        """
        ui_map["best_partner_multiplier"] = 1.0
        ui_map["best_partner_trigger_count"] = 0

    @staticmethod
    def build_status_text(ui_map):
        """根据当前特性状态构建“状态”显示文本。

        参数来源说明（文件+代码位置）：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`update_panel_status_label()` 中
            `BestPartnerTraitService.build_status_text(ui_map)`（约在该文件 26 行附近）。
        """
        multiplier = ui_map.get("best_partner_multiplier", 1.0)
        trigger_count = ui_map.get("best_partner_trigger_count", 0)
        if multiplier <= 1.0:
            return "状态"
        bonus_percent = int((multiplier - 1.0) * 100)
        return f"状态：攻防速+{bonus_percent}%（触发{trigger_count}次）"

    @staticmethod
    def current_multiplier(ui_map):
        """返回当前“最好的伙伴”对面板的倍率。

        参数来源说明（文件+代码位置）：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`refresh_stat_values()` 中
            `BestPartnerTraitService.current_multiplier(ui_map)`（约在该文件 547 行附近）。
        """
        return ui_map.get("best_partner_multiplier", 1.0)

    @classmethod
    def on_after_damage(cls, ui_map, element_mult, total_damage):
        """在一次伤害结算后判断是否触发特性，并返回能量变化。

        参数：
        - ui_map:
          - 来源文件：`utils/damage_window_logic.py`
          - 调用位置：`run_calc()` 中
            `BestPartnerTraitService.on_after_damage(attacker_ui, element_mult, total_damage)`
            （约在该文件 610 行附近）。
          - 实际对象：`attacker_ui`（left_ui 或 right_ui）。
        - element_mult:
          - 来源文件：`utils/damage_window_logic.py`
          - 生成位置：`run_calc()` 中
            `element_mult = float(attacker_ui["element_combo"].get())`（约在 606 行附近）。
        - total_damage:
          - 来源文件：`utils/damage_window_logic.py`
          - 生成位置：`run_calc()` 中 `calculate_final_damage(...)` 的返回值
            （约在 592-601 行代码段）。

        返回：
        - energy_gain: 本次特性带来的回能值（触发返回2，否则0）。
        """
        trait_name = ui_map.get("trait_name", "")
        if trait_name != cls.TRAIT_NAME:
            return 0
        if element_mult <= 1 or total_damage <= 0:
            return 0

        # 每次满足“克制且造成伤害”都触发一次，倍率在上一次基础上继续放大。
        ui_map["best_partner_multiplier"] = ui_map.get("best_partner_multiplier", 1.0) * cls.TRIGGER_MULTIPLIER
        ui_map["best_partner_trigger_count"] = ui_map.get("best_partner_trigger_count", 0) + 1
        return cls.ENERGY_RECOVERY
