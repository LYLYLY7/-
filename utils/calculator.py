"""
伤害计算核心模块。

功能：提供精灵面板属性计算（calc_stat）、本系加成判定（calculate_stab）、
      属性克制判定（calculate_element_multiplier）、最终伤害计算
      （calculate_final_damage）四项纯函数计算能力。
外部依赖：
- math: 用于向下取整
"""

import math

from utils.constants import STAT_NAMES


def round_half_up(value):
    """
    传统四舍五入工具函数。

    功能：使用 math.floor(value + 0.5) 实现四舍五入，避免 Python 内置
          round() 的银行家舍入（偶舍奇入）行为。

    外部参数：
    - value (float/str): 需要四舍五入的数值

    内部参数：无

    返回值：
    - int: 四舍五入后的整数值
    """
    return math.floor(float(value) + 0.5)


def calc_stat(base, iv, nature, is_hp=False):
    """
    计算精灵的单面板属性值（实战中显示的数值）。

    功能：根据种族值、个体值、性格系数，使用洛克王国面板公式计算。
          HP 公式与五围公式不同，由 is_hp 参数区分。

    公式说明：
    - HP:   round(1.7 × (种族 + 3 × 个体) + 70) × 性格 + 100
    - 五围: round(1.1 × (种族 + 3 × 个体) + 10) × 性格 + 50

    外部参数：
    - base (str/int/float):
        来源文件：ui/main_window.py 或 ui/damage_window.py 中 base_label 的 text
        含义：精灵的种族值（从数据库"基础属性"字段提取）
    - iv (str/int/float):
        来源文件：用户从 IV 下拉框选择的值（"0"/"7"/"8"/"9"/"10"）
        含义：个体值（0-10 的整数，通常使用 0/7/8/9/10）
    - nature (str/int/float):
        来源文件：用户从性格系数下拉框选择的值（"0.9"/"1.0"/"1.1"/"1.2"）
        含义：性格对当前属性的修正系数
    - is_hp (bool):
        来源文件：调用方参数（如 update_calc() 中 stat == "生命"）
        含义：是否为 HP 面板（True=HP，False=五围）

    内部参数：
    - base, iv, nature: 转为 float 后的计算值
    - val: 计算过程中的面板中间值

    返回值：
    - int: 计算后的面板值，异常返回 0
    """
    try:
        base, iv, nature = float(base), float(iv), float(nature)

        if is_hp:
            val = round_half_up(1.7 * (base + 3 * iv) + 70) * nature + 100
        else:
            val = round_half_up(1.1 * (base + 3 * iv) + 10) * nature + 50

        return round_half_up(val)
    except Exception:
        return 0


def calculate_stab(skill_type, skill_attr, pet_elements):
    """
    自动计算技能是否享受本系加成（STAB, Same-Type Attack Bonus）。

    功能：判断技能类型是否为"物攻"或"魔攻"、技能属性是否非空且非"无"、
          技能属性是否出现在精灵的元素列表中。满足条件返回 1.25，否则返回 1。

    外部参数：
    - skill_type (str):
        来源文件：ui/damage_window.py 中 atk_type 下拉框
        含义：技能类型，"物攻"/"魔攻"/"状态"
    - skill_attr (str):
        来源文件：ui/damage_window.py 中 atk_attr 下拉框
        含义：技能属性，如"火"、"水"、"无"等
    - pet_elements (list):
        来源文件：utils/damage_window_logic.py 从数据库提取
        含义：精灵的元素列表，如 ["火"] 或 ["火", "龙"]

    返回值：
    - float: 1.25（本系加成触发）或 1（未触发）
    """
    if skill_type not in {"物攻", "魔攻"}:
        return 1

    if not skill_attr or skill_attr == "无":
        return 1

    if skill_attr in (pet_elements or []):
        return 1.25

    return 1


def calculate_element_multiplier(skill_attr, skill_power, defender_kz_table):
    """
    自动计算技能属性对对方精灵的克制倍率。

    功能：判断技能威力非零、技能属性非空且非"无"后，在对方克制表中查找：
          - 技能属性在"被克制"列表中 → 返回 2（克制）
          - 技能属性在"抵抗"列表中   → 返回 0.5（抵抗）
          - 其他情况                 → 返回 1（正常）

    外部参数：
    - skill_attr (str):
        来源文件：ui/damage_window.py 中 atk_attr 下拉框
        含义：技能属性，如"火"、"水"
    - skill_power (str/int/float):
        来源文件：ui/damage_window.py 中 power_entry 输入框
        含义：技能威力值，0 表示无威力（不进行克制判断）
    - defender_kz_table (dict):
        来源文件：utils/damage_window_logic.py 从阵容缓存或数据库获取
        含义：对方精灵的克制表，结构为 {"克制": [...], "被克制": [...], "抵抗": [...], "被抵抗": [...]}

    返回值：
    - float: 2（克制） / 0.5（抵抗） / 1（正常）
    """
    try:
        if float(skill_power) == 0:
            return 1
    except (TypeError, ValueError):
        return 1

    if not skill_attr or skill_attr == "无":
        return 1

    defender_kz_table = defender_kz_table or {}
    if skill_attr in defender_kz_table.get("被克制", []):
        return 2
    if skill_attr in defender_kz_table.get("抵抗", []):
        return 0.5
    return 1


def calculate_final_damage(
    pwr, atk_val, dfn_val, stab=1.0, element_mult=1.0, buff_mult=1.0, hits=1, other_mult=1.0
):
    """
    核心伤害计算函数。

    公式：伤害 = 0.9 × 技能威力 × 攻击值 × 修正系数 / 防御值
    修正系数 = STAB × 属性克制 × 增减益 × 连击数 × 其他修正

    调用方在传入 atk_val/dfn_val 时区分物攻/魔攻：
    - 物攻: atk_val = 物攻面板, dfn_val = 对方物防面板
    - 魔攻: atk_val = 魔攻面板, dfn_val = 对方魔防面板

    外部参数：
    - pwr (str/int/float):
        来源文件：ui/damage_window.py 中 power_entry 输入框
        含义：技能威力值
    - atk_val (str/int/float):
        来源文件：utils/damage_window_logic.py 中 run_calc() 从 stats 区域读取
        含义：攻击方对应面板值（物攻或魔攻）
    - dfn_val (str/int/float):
        来源文件：utils/damage_window_logic.py 中 run_calc() 从 stats 区域读取
        含义：防守方对应面板值（物防或魔防）
    - stab (str/float):
        来源文件：ui/damage_window.py 中 stab_combo 下拉框
        含义：本系加成倍率，1.25 或 1
    - element_mult (str/float):
        来源文件：ui/damage_window.py 中 element_combo 下拉框
        含义：属性克制倍率，可选 3/2/1/0.5/0.33
    - buff_mult (str/float):
        来源文件：ui/damage_window.py 中 buff_entry 输入框
        含义：增减益乘区，默认 1
    - hits (str/int):
        来源文件：ui/damage_window.py 中 hits_entry 输入框
        含义：连击数，默认为 1
    - other_mult (str/float):
        来源文件：ui/damage_window.py 中 other_entry 输入框
        含义：其他修正系数，默认 1

    内部参数：
    - pwr/atk_val/dfn_val/stab/element_mult/buff_mult/hits/other_mult: 转为对应类型后的计算值
    - correction_factor: 各修正系数的乘积

    返回值：
    - int: 最终伤害值（四舍五入到整数），异常返回 0
    """
    try:
        # --- 1. 参数初始化与强制类型转换 ---
        pwr = float(pwr)
        atk_val = float(atk_val)
        dfn_val = float(dfn_val)

        # --- 2. 修正系数拆解 ---
        stab = float(stab)
        element_mult = float(element_mult)
        buff_mult = float(buff_mult)
        hits = int(hits)
        other_mult = float(other_mult)

        # --- 3. 安全检查 ---
        if dfn_val <= 0:
            dfn_val = 1

        # --- 4. 计算综合修正系数 ---
        correction_factor = stab * element_mult * buff_mult * hits * other_mult

        # --- 5. 执行核心伤害公式 ---
        damage = 0.9 * pwr * atk_val * correction_factor / dfn_val

        # --- 6. 结果处理 ---
        return round_half_up(damage)

    except Exception as e:
        print(f"伤害计算模块异常: {e}")
        return 0
