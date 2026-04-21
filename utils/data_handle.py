import json
import os

def extract_traits_and_skills():
    print("开始解析精灵数据，提取特性与技能...")
    
    # ================= 1. 路径自动识别 =================
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 判断当前脚本是在根目录还是在 utils 目录下，从而正确锁定 data 文件夹
    if os.path.basename(current_dir) == 'utils':
        project_root = os.path.dirname(current_dir)
    else:
        project_root = current_dir
        
    data_dir = os.path.join(project_root, 'data')
    input_file = os.path.join(data_dir, 'all_pets_data.json')
    output_file = os.path.join(data_dir, 'data_handle.json')

    # ================= 2. 读取原始数据 =================
    if not os.path.exists(input_file):
        print(f"❌ 错误: 找不到输入文件 {input_file}")
        print("请确保你已经运行过爬虫并生成了 all_pets_data.json")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
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
        # 定义需要遍历的技能列表字段
        skill_categories = ["精灵技能列表", "血脉技能列表", "可学技能石列表"]
        for category in skill_categories:
            skill_list = pet.get(category)
            if skill_list and isinstance(skill_list, list):
                for skill in skill_list:
                    s_name = skill.get("技能名称")
                    s_desc = skill.get("描述")
                    if s_name and s_desc:
                        unique_skills[s_name.strip()] = s_desc.strip()

    # ================= 4. 格式化数据并输出 =================
    # 将去重后的字典转换为结构化的列表，方便阅读和后续代码调用
    output_data = {
        "特性库": [{"名称": name, "效果描述": desc} for name, desc in unique_traits.items()],
        "技能库": [{"技能名称": name, "描述": desc} for name, desc in unique_skills.items()]
    }

    # 确保 data 目录存在（虽然前面读取成功说明大概率存在，但保险起见）
    os.makedirs(data_dir, exist_ok=True)
    
    # 写入目标文件
    with open(output_file, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 保证中文正常显示，indent=4 保证文件格式美观
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