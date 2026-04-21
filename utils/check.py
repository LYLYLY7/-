import json
import os

def list_broken_pets(db_data):
    """
    检查数据完整性
    参数 db_data: 字典格式的精灵数据库 {名字: 数据}
    返回: broken_names (list)
    """
    broken_names = []
    
    # 遍历内存中的数据库字典
    for name, pet in db_data.items():
        # 定义“有问题”的判断标准：
        # 1. 基础属性为空
        # 2. 精灵技能和血脉技能全是空的
        # 3. 克制关系表完全没爬到
        has_stats = bool(pet.get("基础属性"))
        has_skills = bool(pet.get("精灵技能列表") or pet.get("血脉技能列表"))
        kz = pet.get("克制表", {})
        has_kz = any([kz.get("克制"), kz.get("被克制"), kz.get("抵抗"), kz.get("被抵抗")])

        if not (has_stats and has_skills and has_kz):
            broken_names.append(name)
            
    return broken_names