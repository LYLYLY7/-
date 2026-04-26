"""
数据提取工具模块。

功能：从精灵数据库（all_pets_data.json）中提取去重的特性库和技能库，
      输出到 data_handle.json，供其他模块直接引用。
外部依赖：
- utils/constants.py: DATA_DIR, PET_DB_FILE, SKILL_CATEGORY_KEYS
"""

import json
import os
from utils.constants import DATA_DIR, PET_DB_FILE, SKILL_CATEGORY_KEYS


def extract_traits_and_skills():
    """
    提取所有精灵的独立特性与独立技能，去重后写入 data_handle.json。

    功能：完成以下流程：
          1. 自动识别项目根目录，构造 data/ 下输入输出文件路径
          2. 从 all_pets_data.json 读取全部精灵数据
          3. 遍历每只精灵，提取"特性"（名称+效果描述）和"技能"（技能名称+描述），
             以名称为键进行去重（字典方式）
          4. 将去重结果格式化为列表结构，输出到 data_handle.json
          5. 打印统计结果（特性数、技能数、保存路径）

    外部参数：无（从文件系统自动读取）

    内部参数：
    - current_dir: 当前脚本所在目录（通过 os.path.abspath(__file__) 自动获取）
    - project_root: 项目根目录（如果 current_dir 是 utils 则取上级，否则取自身）
    - data_dir: data 目录路径（os.path.join(project_root, DATA_DIR)）
    - input_file: 输入文件路径，即 all_pets_data.json 完整路径
    - output_file: 输出文件路径，即 data/data_handle.json 完整路径
    - all_pets: 从 input_file 加载的完整精灵列表（每个元素是一只精灵的 dict）
    - unique_traits: 去重后的特性字典，{特性名称(str): 效果描述(str)}
    - unique_skills: 去重后的技能字典，{技能名称(str): 描述(str)}
    - pet: 当前遍历的单个精灵 dict
    - trait: 当前精灵的特性 dict（含 "名称"、"效果描述" 键）
    - t_name / t_desc: 特性的名称和效果描述
    - category: 当前遍历的技能分类键名（来自 SKILL_CATEGORY_KEYS）
    - skill_list: 当前分类下的技能列表
    - skill: 当前技能 dict
    - s_name / s_desc: 技能的名称和描述
    - output_data: 最终输出结构 {"特性库": [...], "技能库": [...]}

    返回值：无（结果写入 data/data_handle.json 文件）

    异常处理：
    - 如果 all_pets_data.json 不存在或格式损坏，打印错误信息并提前返回
    """
    print("开始解析精灵数据，提取特性与技能...")

    # ================= 1. 路径自动识别 =================
    # 获取当前脚本所在目录，判断是在根目录还是 utils 下
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) == "utils":
        project_root = os.path.dirname(current_dir)
    else:
        project_root = current_dir

    data_dir = os.path.join(project_root, DATA_DIR)
    input_file = os.path.join(project_root, PET_DB_FILE)
    output_file = os.path.join(data_dir, "data_handle.json")

    # ================= 2. 读取原始数据 =================
    if not os.path.exists(input_file):
        print(f"❌ 错误: 找不到输入文件 {input_file}")
        print("请确保你已经运行过爬虫并生成了 all_pets_data.json")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        try:
            all_pets = json.load(f)
        except json.JSONDecodeError:
            print("❌ 错误: all_pets_data.json 文件格式损坏！")
            return

    # ================= 3. 数据提取与去重 =================
    # 使用字典进行去重：键为名称，值为描述
    unique_traits = {}
    unique_skills = {}

    for pet in all_pets:
        # --- 提取特性 ---
        trait = pet.get("特性")
        if trait and isinstance(trait, dict):
            t_name = trait.get("名称")
            t_desc = trait.get("效果描述")
            # 过滤掉空的或者名为"无"的无效特性
            if t_name and t_name.strip() != "无" and t_desc:
                unique_traits[t_name.strip()] = t_desc.strip()

        # --- 提取技能 ---
        # 遍历所有技能分类：精灵技能、血脉技能、可学技能石
        for category in SKILL_CATEGORY_KEYS:
            skill_list = pet.get(category)
            if skill_list and isinstance(skill_list, list):
                for skill in skill_list:
                    s_name = skill.get("技能名称")
                    s_desc = skill.get("描述")
                    if s_name and s_desc:
                        unique_skills[s_name.strip()] = s_desc.strip()

    # ================= 4. 格式化数据并输出 =================
    output_data = {
        "特性库": [
            {"名称": name, "效果描述": desc}
            for name, desc in unique_traits.items()
        ],
        "技能库": [
            {"技能名称": name, "描述": desc}
            for name, desc in unique_skills.items()
        ],
    }

    # 确保 data 目录存在
    os.makedirs(data_dir, exist_ok=True)

    # 写入目标文件
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    # ================= 5. 打印统计结果 =================
    print("-" * 30)
    print("✅ 数据提取完成！")
    print(f"🌟 共提取到独立特性: {len(unique_traits)} 个")
    print(f"⚔️ 共提取到独立技能: {len(unique_skills)} 个")
    print(f"📁 结果已成功保存至: {output_file}")
    print("-" * 30)


if __name__ == "__main__":
    extract_traits_and_skills()
