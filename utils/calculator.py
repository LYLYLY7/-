import math  # 导入数学库，用于对计算结果进行向下取整

def round_half_up(value):
    """使用传统四舍五入规则，避免 Python 内置 round 的银行家舍入。"""
    return math.floor(float(value) + 0.5)

def calc_stat(base, iv, nature, is_hp=False):
    """
    计算精灵的面板属性值（实战中看到的数值）
    base: 种族值 | iv: 个体值 | nature: 性格修正系数
    """
    try:
        # 将输入值转换为浮点数，确保计算精度并防止字符串输入导致报错
        base, iv, nature = float(base), float(iv), float(nature)
        
        if is_hp:
            # 原公式保留，便于后续回溯：
            # val = (1.7 * (base + 3 * iv) + 70) * nature + 100
            #
            # 当前改为分步四舍五入：
            # 先分别处理种族项和个体项，再乘性格，最后再次四舍五入到面板值。
            val = round_half_up(1.7 * (base+ (3 * iv)) + 70) * nature + 100
        else:
            # 原公式保留，便于后续回溯：
            # val = (1.1 * (base + 3 * iv) + 10) * nature + 50
            #
            # 当前改为分步四舍五入：
            # 先分别处理种族项和个体项，再乘性格，最后再次四舍五入到面板值。
            val = round_half_up(1.1 * (base + (3 * iv)) + 10) * nature + 50
            
        # 原显示取整方式保留，便于后续回溯：
        # return math.floor(val + 0.4)
        return round_half_up(val)
    except:
        # 如果输入数据非法（比如空值），返回0，保证程序不闪退
        return 0

def calculate_stab(skill_type, skill_attr, pet_elements):
    """
    自动计算技能是否享受本系加成（STAB）。

    功能说明：
    - 只有当技能类型为“物攻”或“魔攻”时，才可能触发本系加成。
    - 当技能属性存在于精灵元素列表中时，返回 1.25。
    - 其他情况一律返回 1。

    参数：
    - skill_type: 技能类型，例如 "物攻"、"魔攻"、"状态"
    - skill_attr: 技能属性，例如 "火"、"水"
    - pet_elements: 精灵元素列表，例如 ["火"] 或 ["火", "龙"]
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
    自动计算技能属性克制倍率。

    功能说明：
    - 只有当技能威力不为 0 时，才进行属性克制判断。
    - 如果技能属性出现在对方精灵克制表的“被克制”列表中，返回 2。
    - 如果技能属性出现在对方精灵克制表的“抵抗”列表中，返回 0.5。
    - 其他情况一律返回 1。

    参数：
    - skill_attr: 技能属性，例如 "火"、"水"
    - skill_power: 技能威力，可以是字符串或数字
    - defender_kz_table: 对方精灵的克制表字典
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

def calculate_final_damage(pwr, atk_val, dfn_val, stab=1.0, element_mult=1.0, buff_mult=1.0, hits=1, other_mult=1.0):
    """
    核心伤害计算逻辑
    物攻造成伤害 = 0.9 * 技能威力 * 物攻值 * 修正系数 / 对方物防值
    魔攻造成伤害 = 0.9 * 技能威力 * 魔攻值 * 修正系数 / 对方魔防值
    """
    try:
        # --- 1. 参数初始化与强制类型转换 ---
        pwr = float(pwr)                # 技能威力 (例如: 100)
        atk_val = float(atk_val)        # 攻击方属性值 (物攻或魔攻面板)
        dfn_val = float(dfn_val)        # 防御方属性值 (物防或魔防面板)
        
        # --- 2. 修正系数拆解 (根据你的要求定义取值) ---
        # 本系加成 (stab): 有则 1.25，无则 1
        stab = float(stab)
        # 属性克制 (element_mult): 取值范围 [3, 2, 1, 0.5, 0.33]
        element_mult = float(element_mult)
        # 增减益 (buff_mult): 默认值为 1
        buff_mult = float(buff_mult)
        # 连击数 (hits): 默认值为 1
        hits = int(hits)
        # 其他修正 (other_mult): 默认值为 1
        other_mult = float(other_mult)
        
        # --- 3. 安全检查 ---
        # 如果防御值为0，将其设为1，防止数学上的“除以0”错误导致程序崩溃
        if dfn_val <= 0:
            dfn_val = 1
            
        # --- 4. 计算综合修正系数 ---
        # 公式：修正系数 = 本系加成 * 属性克制 * 增减益 * 连击数 * 其他
        correction_factor = stab * element_mult * buff_mult * hits * other_mult
        
        # --- 5. 执行核心伤害公式 ---
        # 统一公式：伤害 = 0.9 * 技能威力 * 攻击值 * 修正系数 / 对方防御值
        # 注意：物攻/魔攻的区分在 UI 调用传入 atk_val 和 dfn_val 时完成
        damage = 0.9 * pwr * atk_val * correction_factor / dfn_val
        
        # --- 6. 结果处理 ---
        # 返回最终伤害数字，并五舍六入到整数（实战中通常显示整数伤害）
        return round_half_up(damage)
        
    except Exception as e:
        # 如果计算出错（如参数类型不对），在控制台打印错误并返回0
        print(f"伤害计算模块异常: {e}")
        return 0
