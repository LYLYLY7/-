"""
洛克王国 Bwiki 爬虫模块。

功能：从 Bilibili Wiki（https://wiki.biligame.com/rocom/）爬取全部精灵数据，
      包括精灵名称、元素属性、种族值、基础属性、克制关系、特性、技能列表等。
      输出到 data/all_pets_data.json。
外部依赖：
- httpx: 异步网络请求库
- BeautifulSoup (bs4): HTML 解析库
- asyncio: 异步编程核心库
- utils/constants.py: CRAWLER_HEADERS, ELEMENT_TYPES, CRAWLER_CONCURRENCY,
                       WIKI_LIST_URL, WIKI_BASE_URL, TRASH_WORDS
"""

import asyncio
import json
import os
import re

import httpx
import urllib3
from bs4 import BeautifulSoup

from utils.constants import (
    CRAWLER_CONCURRENCY,
    CRAWLER_HEADERS,
    ELEMENT_TYPES,
    TRASH_WORDS,
    WIKI_BASE_URL,
    WIKI_LIST_URL,
)

# 禁用 SSL 告警（Bwiki 的证书可能不完全符合标准）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 18 系战斗属性（不含"无"），用于匹配精灵图标 alt 文本
# 来源：ELEMENT_TYPES 包含全部 19 种（含"无"），取 [1:] 排除"无"
ELEMENT_FILTER = ELEMENT_TYPES[1:]


# --- 2. 【解析工具：克制/抵抗关系】 ---
def get_elements_from_section(soup, label_text):
    """
    从页面的克制/抵抗区域提取属性列表。

    功能：按标签文本（如"克制"、"被克制"）找到对应段落，从其后的 img 标签
          alt 属性中匹配属性名称。

    外部参数：
    - soup (BeautifulSoup):
        来源文件：本模块 fetch_one_pet() 中创建
        含义：单精灵详情页的 HTML 解析对象
    - label_text (str):
        来源文件：本模块 fetch_one_pet() 中调用时传入"克制"/"被克制"/"抵抗"/"被抵抗"
        含义：要查找的标签文本

    内部参数：
    - result: 提取到的属性名称列表
    - label_p: 标签文本对应的 p 元素
    - sibling: 标签后面的兄弟节点
    - alt_text: img 元素的 alt 属性值

    返回值：
    - list: 去重后的属性名称列表
    """
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
    """
    解析技能卡片区域，提取技能列表。

    功能：在技能容器中查找所有 class="rocom_sprite_skill_box" 的元素，
          逐个提取等级、属性、名称、消耗、类型、威力、描述字段。

    外部参数：
    - container (BeautifulSoup element):
        来源文件：本模块 fetch_one_pet() 中传入对应 id 的 div
        含义：精灵技能/血脉技能/可学技能石区域的 HTML 容器

    内部参数：
    - skills: 解析得到的技能列表
    - box: 单个技能卡片 div
    - lv/name/cost/s_type/power/desc: 技能各字段对应的 HTML 元素
    - s_attr: 技能属性（从 img alt 匹配）
    - attr_img: 技能属性的 img 元素

    返回值：
    - list: 技能 dict 列表，每项含"等级""属性""技能名称""消耗""类型""威力""描述"
    """
    skills = []
    if not container:
        return skills

    boxes = container.find_all("div", class_="rocom_sprite_skill_box")
    for box in boxes:
        lv = box.find("div", class_="rocom_sprite_skill_level")
        name = box.find("div", class_="rocom_sprite_skillName")
        cost = box.find("div", class_="rocom_sprite_skillDamage")
        s_type = box.find("div", class_="rocom_sprite_skillType")
        power = box.find("div", class_="rocom_sprite_skill_power")
        desc = box.find("div", class_="rocom_sprite_skillContent")

        s_attr = ""
        attr_img = box.select_one(
            ".rocom_sprite_skill_img img.rocom_sprite_skill_attr"
        )
        if attr_img:
            alt = attr_img.get("alt", "")
            for e in ELEMENT_FILTER:
                if e in alt:
                    s_attr = e
                    break

        skills.append(
            {
                "等级": lv.get_text(strip=True) if lv else "",
                "属性": s_attr,
                "技能名称": name.get_text(strip=True) if name else "未知",
                "消耗": cost.get_text(strip=True) if cost else "0",
                "类型": s_type.get_text(strip=True) if s_type else "未知",
                "威力": power.get_text(strip=True) if power else "0",
                "描述": desc.get_text(strip=True).replace("✦", "") if desc else "无描述",
            }
        )
    return skills


# --- 4. 【核心：抓取单精灵详情】 ---
async def fetch_one_pet(client, semaphore, pet_info):
    """
    异步抓取单只精灵的完整详情页数据。

    功能：对每只精灵的详情 URL 发起 GET 请求，解析页面结构，提取元素属性、
          种族值、基础属性、克制表、特性、各分类技能列表。最多重试 3 次。

    外部参数：
    - client (httpx.AsyncClient):
        来源文件：本模块 start_crawl() 中创建的异步 HTTP 客户端
        含义：共享的异步 HTTP 客户端连接池
    - semaphore (asyncio.Semaphore):
        来源文件：本模块 start_crawl() 中创建的信号量
        含义：并发限制信号量，控制同时进行的请求数
    - pet_info (dict):
        来源文件：本模块 start_crawl() 中从精灵列表页解析得到
        含义：单精灵的基础信息，含 "编号"、"名字"、"详情连接" 键

    内部参数：
    - attempt: 当前重试次数（0-2）
    - resp: HTTP 响应对象
    - soup: 页面 HTML 的 BeautifulSoup 解析对象
    - title_div: 页面的标题 div（用于判断页面是否被风控）
    - detail: 精灵完整数据 dict
    - attr_div: 元素属性 div
    - stats_p: 基础属性值 p 元素列表
    - char_title / char_desc: 特性名称和描述的 p 元素

    返回值：
    - dict: 精灵完整数据，包含 精灵ID / 名字 / 详情连接 / 元素 / 种族值 /
            基础属性 / 克制表 / 特性 / 各技能列表
    - None: 三次重试均失败
    """
    async with semaphore:
        for attempt in range(3):
            try:
                if attempt > 0:
                    print(f"[重试 {attempt}/2] {pet_info['名字']} 等待避开风控...")
                    await asyncio.sleep(2 + attempt)
                else:
                    print(f"[爬取中] {pet_info['名字']}")

                resp = await client.get(pet_info["详情连接"], follow_redirects=True)

                # 检测 HTTP 状态码
                if resp.status_code != 200:
                    print(
                        f"!!! HTTP拦截 {pet_info['名字']} 状态码: {resp.status_code}"
                    )
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # 检测页面结构是否异常（被风控时可能返回空结构）
                title_div = soup.find("div", class_="rocom_sprite_info_title")
                if not title_div:
                    print(f"!!! 页面结构异常(疑似被风控) {pet_info['名字']}")
                    continue

                # --- 组装初始数据结构 ---
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
                        "被抵抗": get_elements_from_section(soup, "被抵抗"),
                    },
                    "特性": {"名称": "", "效果描述": ""},
                    "精灵技能列表": parse_skill_boxes(
                        soup.find("div", id="精灵技能")
                        or soup.select_one(".tabbertab[title='精灵技能']")
                    ),
                    "血脉技能列表": parse_skill_boxes(
                        soup.find("div", id="血脉技能")
                        or soup.select_one(".tabbertab[title='血脉技能']")
                    ),
                    "可学技能石列表": parse_skill_boxes(
                        soup.find("div", id="可学技能石")
                        or soup.select_one(".tabbertab[title='可学技能石']")
                    ),
                }

                # 提取元素属性
                attr_div = soup.find("div", class_="rocom_sprite_grament_attributes")
                if attr_div:
                    detail["元素"] = [
                        p.get_text(strip=True) for p in attr_div.find_all("p")
                    ]

                # 提取种族值
                if title_div and len(title_div.find_all("p")) >= 2:
                    detail["种族值"] = title_div.find_all("p")[1].get_text(strip=True)

                # 提取六维基础属性
                stats_p = soup.find_all(
                    "p", class_="rocom_sprite_info_qualification_value"
                )
                if len(stats_p) >= 6:
                    keys = ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]
                    detail["基础属性"] = {
                        keys[i]: stats_p[i].get_text(strip=True) for i in range(6)
                    }

                # 提取特性信息
                char_title = soup.find(
                    "p", class_="rocom_sprite_info_characteristic_title"
                )
                char_desc = soup.find(
                    "p", class_="rocom_sprite_info_characteristic_text"
                )
                if char_title:
                    detail["特性"]["名称"] = char_title.get_text(strip=True)
                if char_desc:
                    detail["特性"]["效果描述"] = char_desc.get_text(strip=True)

                return detail

            except Exception as e:
                print(f"!!! 无法抓取 {pet_info['名字']} (第{attempt+1}次): {e}")

        print(f"XXX 彻底失败 {pet_info['名字']}，放弃抓取。")
        return None


# --- 5. 【核心入口：start_crawl 异步函数】 ---
async def start_crawl():
    """
    异步爬虫主入口：获取精灵名单 → 并发抓取详情 → 保存到 all_pets_data.json。

    功能：完成以下流程：
          1. 请求 Bwiki 精灵图鉴列表页，解析所有精灵链接
          2. 按 TRASH_WORDS 过滤，去重，生成精灵基本信息列表
          3. 使用信号量限制并发（CRAWLER_CONCURRENCY），批量抓取详情
          4. 过滤失败的条目，将结果写入 data/all_pets_data.json

    外部参数：无（从 constants.py 获取 WIKI_LIST_URL / WIKI_BASE_URL / CRAWLER_HEADERS 等）

    内部参数：
    - client: httpx.AsyncClient 实例
    - soup_list: 精灵列表页的 BeautifulSoup 对象
    - pet_links: 解析得到的精灵基本信息列表
    - seen_urls: URL 去重集合
    - all_a_tags: 页面中所有 a 标签
    - a: 当前遍历的 a 标签
    - name / href: a 标签的 title 和 href 属性
    - count: 精灵计数（用于生成编号）
    - semaphore: 并发限制信号量
    - tasks: 所有精灵的异步抓取任务列表
    - results: 所有任务的执行结果
    - final_data: 过滤掉 None 后的有效数据
    - current_dir: 当前脚本所在目录
    - project_root: 项目根目录
    - data_dir: data/ 目录路径
    - save_path: 输出文件完整路径

    返回值：无（结果写入 data/all_pets_data.json）
    """
    async with httpx.AsyncClient(
        headers=CRAWLER_HEADERS, verify=False, timeout=30.0
    ) as client:
        print("--- 步骤1：正在获取过滤后的精灵名单 ---")
        resp = await client.get(WIKI_LIST_URL)
        soup_list = BeautifulSoup(resp.text, "html.parser")

        pet_links = []
        seen_urls = set()
        all_a_tags = soup_list.find_all("a", href=True)
        count = 1
        for a in all_a_tags:
            name = a.get("title")
            href = a.get("href")
            if name and href and href.startswith("/rocom/") and href not in seen_urls:
                if not any(word in name for word in TRASH_WORDS):
                    if len(name) < 20:
                        pet_links.append(
                            {
                                "编号": f"{count:03d}",
                                "名字": name,
                                "详情连接": f"{WIKI_BASE_URL}{href}",
                            }
                        )
                        seen_urls.add(href)
                        count += 1

        print(f"筛选完毕，合法精灵共计 {len(pet_links)} 个。")

        semaphore = asyncio.Semaphore(CRAWLER_CONCURRENCY)
        tasks = [fetch_one_pet(client, semaphore, link) for link in pet_links]
        results = await asyncio.gather(*tasks)

        final_data = [r for r in results if r is not None]

        # 确定输出路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        data_dir = os.path.join(project_root, "data")

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        save_path = os.path.join(data_dir, "all_pets_data.json")

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)

        print(f"\n任务圆满结束！数据已存入 {save_path}")


# 兼容直接运行（python crawler.py）
if __name__ == "__main__":
    asyncio.run(start_crawl())
