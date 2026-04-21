import httpx              # 异步网络请求库
from bs4 import BeautifulSoup  # 网页解析库
import json               # JSON 处理
import asyncio            # 异步编程核心库
import urllib3            # 网络工具
import re                 # 正则表达式
import os                 # --- 新增：用于路径处理 ---

# --- 1. 【初始化配置】 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/rocom/"
}

# 洛克王国 18 系属性池
ELEMENT_FILTER = ["普通", "火", "水", "草", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"]

# 并发限制（降低并发防止请求过快被 Bwiki 风控拦截）
CONCURRENCY_LIMIT = 3

# --- 2. 【解析工具：克制/抵抗关系】 ---
def get_elements_from_section(soup, label_text):
    """提取克制或抵抗属性图标"""
    result = []
    label_p = soup.find("p", string=re.compile(f"^{label_text}$"))
    if label_p:
        for sibling in label_p.find_next_siblings():
            if sibling.name == "img":
                alt_text = sibling.get("alt", "")
                for e in ELEMENT_FILTER:
                    if e in alt_text:
                        result.append(e)
                        break
            elif sibling.name in ["p", "div"]:
                break
    return list(set(result))

# --- 3. 【解析工具：技能列表】 ---
def parse_skill_boxes(container):
    """解析技能卡片信息"""
    skills = []
    if not container: return skills
    
    boxes = container.find_all("div", class_="rocom_sprite_skill_box")
    for box in boxes:
        lv = box.find("div", class_="rocom_sprite_skill_level")
        name = box.find("div", class_="rocom_sprite_skillName")
        cost = box.find("div", class_="rocom_sprite_skillDamage")
        s_type = box.find("div", class_="rocom_sprite_skillType")
        power = box.find("div", class_="rocom_sprite_skill_power")
        desc = box.find("div", class_="rocom_sprite_skillContent")
        
        s_attr = ""
        attr_img = box.select_one('.rocom_sprite_skill_img img.rocom_sprite_skill_attr')
        if attr_img:
            alt = attr_img.get('alt', '')
            for e in ELEMENT_FILTER:
                if e in alt:
                    s_attr = e
                    break

        skills.append({
            "等级": lv.get_text(strip=True) if lv else "",
            "属性": s_attr,
            "技能名称": name.get_text(strip=True) if name else "未知",
            "消耗": cost.get_text(strip=True) if cost else "0",
            "类型": s_type.get_text(strip=True) if s_type else "未知",
            "威力": power.get_text(strip=True) if power else "0",
            "描述": desc.get_text(strip=True).replace('✦', '') if desc else "无描述"
        })
    return skills

# --- 4. 【核心：抓取单精灵详情】 ---
async def fetch_one_pet(client, semaphore, pet_info):
    """进入详情页抠取所有数据（带被风控重试机制）"""
    async with semaphore:
        for attempt in range(3):  # 最多重试3次
            try:
                if attempt > 0:
                    print(f"[重试 {attempt}/2] {pet_info['名字']} 等待避开风控...")
                    await asyncio.sleep(2 + attempt) # 延长等待
                else:
                    print(f"[爬取中] {pet_info['名字']}")
                    
                resp = await client.get(pet_info["详情连接"], follow_redirects=True)
                
                # 核心拦截：检测 HTTP 状态码
                if resp.status_code != 200:
                    print(f"!!! HTTP拦截 {pet_info['名字']} 状态码: {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 核心拦截：检测页面是否因为频率过高而返回空结构
                title_div = soup.find("div", class_="rocom_sprite_info_title")
                if not title_div:
                    print(f"!!! 页面结构异常(疑似被风控) {pet_info['名字']}")
                    continue
                
                detail = {
                    "精灵ID": pet_info["编号"],
                    "名字": pet_info["名字"],
                    "详情连接": pet_info["详情连接"],
                    "元素": [],
                    "种族值": "",
                    "基础属性": {},
                    "克制表": {
                        "克制": get_elements_from_section(soup, "克制"),
                        "被克制": get_elements_from_section(soup, "被克制"),
                        "抵抗": get_elements_from_section(soup, "抵抗"),
                        "被抵抗": get_elements_from_section(soup, "被抵抗")
                    },
                    "特性": {"名称": "", "效果描述": ""},
                    "精灵技能列表": parse_skill_boxes(soup.find("div", id="精灵技能") or soup.select_one(".tabbertab[title='精灵技能']")),
                    "血脉技能列表": parse_skill_boxes(soup.find("div", id="血脉技能") or soup.select_one(".tabbertab[title='血脉技能']")),
                    "可学技能石列表": parse_skill_boxes(soup.find("div", id="可学技能石") or soup.select_one(".tabbertab[title='可学技能石']"))
                }

                attr_div = soup.find("div", class_="rocom_sprite_grament_attributes")
                if attr_div:
                    detail["元素"] = [p.get_text(strip=True) for p in attr_div.find_all("p")]

                if title_div and len(title_div.find_all("p")) >= 2:
                    detail["种族值"] = title_div.find_all("p")[1].get_text(strip=True)

                stats_p = soup.find_all("p", class_="rocom_sprite_info_qualification_value")
                if len(stats_p) >= 6:
                    keys = ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]
                    detail["基础属性"] = {keys[i]: stats_p[i].get_text(strip=True) for i in range(6)}

                char_title = soup.find("p", class_="rocom_sprite_info_characteristic_title")
                char_desc = soup.find("p", class_="rocom_sprite_info_characteristic_text")
                if char_title: detail["特性"]["名称"] = char_title.get_text(strip=True)
                if char_desc: detail["特性"]["效果描述"] = char_desc.get_text(strip=True)
                
                return detail
                
            except Exception as e:
                print(f"!!! 无法抓取 {pet_info['名字']} (第{attempt+1}次): {e}")
                
        print(f"XXX 彻底失败 {pet_info['名字']}，放弃抓取。")
        return None

# --- 5. 【核心入口：改为可导出的 start_crawl】 ---
async def start_crawl():
    list_url = "https://wiki.biligame.com/rocom/%E7%B2%BE%E7%81%B5%E5%9B%BE%E9%89%B4"
    base_url = "https://wiki.biligame.com"
    
    async with httpx.AsyncClient(headers=HEADERS, verify=False, timeout=30.0) as client:
        print("--- 步骤1：正在获取过滤后的精灵名单 ---")
        resp = await client.get(list_url)
        soup_list = BeautifulSoup(resp.text, 'html.parser')
        
        pet_links = []
        seen_urls = set()
        trash_words = ["版本", "文件:", "页面", "编辑", "图鉴", "首页", "分类", "讨论", "[h]", "模板", "Help:"]
        
        all_a_tags = soup_list.find_all("a", href=True)
        count = 1
        for a in all_a_tags:
            name = a.get("title")
            href = a.get("href")
            if name and href and href.startswith("/rocom/") and href not in seen_urls:
                if not any(word in name for word in trash_words):
                    if len(name) < 20:
                        pet_links.append({
                            "编号": f"{count:03d}",
                            "名字": name,
                            "详情连接": f"{base_url}{href}"
                        })
                        seen_urls.add(href)
                        count += 1
        
        print(f"筛选完毕，合法精灵共计 {len(pet_links)} 个。")

        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        tasks = [fetch_one_pet(client, semaphore, link) for link in pet_links]
        results = await asyncio.gather(*tasks)
        
        final_data = [r for r in results if r is not None]
        # 使用当前脚本目录的相对路径
        current_dir = os.path.dirname(os.path.abspath(__file__)) 
        project_root = os.path.dirname(current_dir) # 向上跳一级到项目根目录
        data_dir = os.path.join(project_root, "data")
        
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        save_path = os.path.join(data_dir, "all_pets_data.json")
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        
        print(f"\n任务圆满结束！数据已存入 {save_path}")

# 为了兼容直接运行，保留此入口
if __name__ == "__main__":
    asyncio.run(start_crawl())