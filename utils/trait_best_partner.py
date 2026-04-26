"""
"最好的伙伴"特性服务模块。

功能：独立处理"最好的伙伴"特性的运行态逻辑，包括状态初始化、倍率查询、
      状态文本构建、伤害后触发判定。不直接操作 UI 控件，仅处理数据。
外部依赖：
- utils/constants.py: TRAIT_AFFECTED_STATS（受影响的属性列表，仅参考）
"""

from utils.constants import TRAIT_AFFECTED_STATS


class BestPartnerTraitService:
    """
    "最好的伙伴"特性独立服务类。

    功能：提供特性运行态字段初始化（init_state）、状态文本构建（build_status_text）、
          倍率查询（current_multiplier）、伤害后触发判定（on_after_damage）四项能力。

    特性机制说明：
    - 每次对克制目标造成伤害时触发，攻防速属性 +20%（叠乘）。
    - 触发时恢复 2 点能量。
    - 倍率累乘：第一次触发 1.2，第二次 1.44，依次类推。

    内部常量：
    - TRAIT_NAME: 特性名称，用于判断当前精灵是否拥有该特性
    - TRIGGER_MULTIPLIER: 每次触发时的倍率增量（1.2 倍）
    - ENERGY_RECOVERY: 每次触发恢复的能量值（2 点）
    """

    TRAIT_NAME = "最好的伙伴"
    TRIGGER_MULTIPLIER = 1.2
    ENERGY_RECOVERY = 2

    @staticmethod
    def init_state(ui_map):
        """
        初始化与"最好的伙伴"特性相关的运行态字段。

        功能：在 ui_map 中写入 best_partner_multiplier（当前倍率，初始 1.0）
              和 best_partner_trigger_count（触发次数，初始 0）。

        外部参数：
        - ui_map (dict):
            来源文件：utils/damage_window_logic.py
            调用位置：init_panel_runtime_state() 和 load_pet_info() 中调用
            含义：面板 UI 控件引用字典，包含 stats、energy_label 等键

        内部参数：
        - ui_map["best_partner_multiplier"]: 当前攻防速倍率，初始为 1.0
        - ui_map["best_partner_trigger_count"]: 已触发次数，初始为 0
        """
        ui_map["best_partner_multiplier"] = 1.0
        ui_map["best_partner_trigger_count"] = 0

    @staticmethod
    def build_status_text(ui_map):
        """
        根据当前特性状态构建"状态"标签显示文本。

        功能：如果倍率 > 1.0，显示"攻防速+XX%（触发X次）"格式文本；
              否则显示"状态"。

        外部参数：
        - ui_map (dict):
            来源文件：utils/damage_window_logic.py
            调用位置：update_panel_status_label() 中调用
            含义：面板 UI 控件引用字典

        内部参数：
        - multiplier: 当前特性倍率（未触发则为 1.0）
        - trigger_count: 已触发次数
        - bonus_percent: 计算得到的提升百分比（(倍率-1)*100）

        返回值：
        - str: 状态标签显示文本
        """
        multiplier = ui_map.get("best_partner_multiplier", 1.0)
        trigger_count = ui_map.get("best_partner_trigger_count", 0)
        if multiplier <= 1.0:
            return "状态"
        bonus_percent = int((multiplier - 1.0) * 100)
        return f"状态：攻防速+{bonus_percent}%（触发{trigger_count}次）"

    @staticmethod
    def current_multiplier(ui_map):
        """
        返回当前"最好的伙伴"对面板的倍率。

        功能：供 refresh_stat_values() 调用，在计算面板值时乘上此倍率。

        外部参数：
        - ui_map (dict):
            来源文件：utils/damage_window_logic.py
            调用位置：refresh_stat_values() 中调用
            含义：面板 UI 控件引用字典

        返回值：
        - float: 当前倍率（默认 1.0）
        """
        return ui_map.get("best_partner_multiplier", 1.0)

    @classmethod
    def on_after_damage(cls, ui_map, element_mult, total_damage):
        """
        在一次伤害结算后判断是否触发"最好的伙伴"特性，返回能量变化。

        功能：检查三条件——精灵拥有该特性、属性克制生效（倍率>1）、
              造成伤害>0。满足时累乘倍率、增加触发计数、返回回能值。

        外部参数：
        - ui_map (dict):
            来源文件：utils/damage_window_logic.py
            调用位置：run_calc() 中传入 attacker_ui
            含义：攻击方面板的 UI 控件引用字典
        - element_mult (float):
            来源文件：utils/damage_window_logic.py
            生成方式：run_calc() 中 float(attacker_ui["element_combo"].get())
            含义：本次技能的属性克制倍率，>1 表示克制
        - total_damage (int):
            来源文件：utils/damage_window_logic.py
            生成方式：run_calc() 中 calculate_final_damage() 的返回值
            含义：本次计算得到的最终伤害值

        内部参数：
        - trait_name: 当前精灵的特性名称
        - energy_gain: 本次触发带来的回能值（触发=2，否则=0）

        返回值：
        - int: 能量恢复值（触发特性返回 2，否则返回 0）
        """
        trait_name = ui_map.get("trait_name", "")
        if trait_name != cls.TRAIT_NAME:
            return 0
        if element_mult <= 1 or total_damage <= 0:
            return 0

        # 每次满足"克制且造成伤害"都触发一次，倍率在上一次基础上继续放大
        ui_map["best_partner_multiplier"] = (
            ui_map.get("best_partner_multiplier", 1.0) * cls.TRIGGER_MULTIPLIER
        )
        ui_map["best_partner_trigger_count"] = (
            ui_map.get("best_partner_trigger_count", 0) + 1
        )
        return cls.ENERGY_RECOVERY
