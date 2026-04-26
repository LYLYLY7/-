"""
数据完整性检查工具。

功能：检查精灵数据库中各精灵的数据是否完整（基础属性、技能列表、克制表三项）。
外部依赖：无
"""


def list_broken_pets(db_data):
    """
    检查数据库中数据不完整的精灵。

    功能：遍历精灵数据库，检查每一只精灵是否同时具备以下三项完整数据：
          1. 基础属性（6项数值非空）
          2. 至少有一个技能（精灵技能列表或血脉技能列表非空）
          3. 克制关系表完整（克制/被克制/抵抗/被抵抗四个方向至少有一项非空）
          不满足任意一项则视为"有问题"精灵。

    外部参数：
    - db_data (dict):
        来源文件：utils/data_manager.py 的 load_pet_db() 返回值
        含义：精灵数据库字典，格式为 {精灵名称(str): 精灵数据(dict)}
              精灵数据包含 "基础属性"、"精灵技能列表"、"血脉技能列表"、"克制表" 等字段

    内部参数：
    - broken_names (list): 存储有问题的精灵名称列表
    - name (str): 当前遍历的精灵名称
    - pet (dict): 当前精灵的完整数据
    - has_stats (bool): 是否有基础属性
    - has_skills (bool): 是否有技能（精灵技能或血脉技能）
    - kz (dict): 克制表数据
    - has_kz (bool): 克制表是否完整（四项中至少有一项非空）

    返回值：
    - list: 数据不完整的精灵名称列表，如果全部完整则返回空列表
    """
    broken_names = []

    for name, pet in db_data.items():
        # 检查三项完整性指标
        has_stats = bool(pet.get("基础属性"))
        has_skills = bool(pet.get("精灵技能列表") or pet.get("血脉技能列表"))
        kz = pet.get("克制表", {})
        has_kz = any([kz.get("克制"), kz.get("被克制"), kz.get("抵抗"), kz.get("被抵抗")])

        # 任意一项缺失即加入问题列表
        if not (has_stats and has_skills and has_kz):
            broken_names.append(name)

    return broken_names
