"""
数据管理器模块。

功能：负责精灵数据库（all_pets_data.json）和阵容数据（all_lineups.json）的
      读取、写入、迁移。所有数据文件统一存放在 data/ 目录下。
外部依赖：
- utils/constants.py: DATA_DIR, PET_DB_FILE, LINEUP_FILE, DEFAULT_LINEUPS
"""

import json
import os
from utils.constants import DATA_DIR, PET_DB_FILE, LINEUP_FILE, DEFAULT_LINEUPS


class DataManager:
    """
    数据管理器类：管理 data/*.json 文件的读写与旧格式迁移。

    功能：提供精灵数据库加载（load_pet_db）、阵容数据加载/保存
          （load_lineups / save_lineups）、目录自动创建（ensure_data_dir）等能力。
          支持从旧格式（data 目录外部的 all_lineups.json）自动迁移到新格式。

    外部参数：
    - base_dir:
        来源文件：main.py 中 main() 传入 os.path.dirname(os.path.abspath(__file__))
        含义：项目根目录的绝对路径，用于定位 data/ 目录

    内部参数：
    - self.data_dir: data/ 目录路径（os.path.join(base_dir, DATA_DIR)）
    - self.db_file: 精灵数据库文件完整路径
    - self.lineup_file: 阵容数据文件完整路径
    - self.legacy_lineup_file: 旧版阵容文件（根目录下），用于迁移
    """

    def __init__(self, base_dir):
        """
        初始化数据管理器，设置各文件路径。

        外部参数：
        - base_dir (str):
            来源文件：main.py 中 main() 函数第 40 行传入
            含义：项目根目录绝对路径，由 os.path.abspath(__file__) 自动获取

        内部参数：
        - self.base_dir: 保存传入的项目根目录
        - self.data_dir: data/ 子目录完整路径
        - self.db_file: all_pets_data.json 完整路径
        - self.lineup_file: data/all_lineups.json 完整路径
        - self.legacy_lineup_file: 根目录下旧版 all_lineups.json（兼容迁移）
        """
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, DATA_DIR)
        self.db_file = os.path.join(base_dir, PET_DB_FILE)
        self.lineup_file = os.path.join(base_dir, LINEUP_FILE)
        self.legacy_lineup_file = os.path.join(base_dir, "all_lineups.json")

    def ensure_data_dir(self):
        """
        确保 data/ 目录存在，不存在则创建。

        功能：调用 os.makedirs 创建 data/ 目录，exist_ok=True 避免重复创建。
        外部参数：无
        内部参数：无
        返回值：无
        """
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_json_file(self, file_path, default_value):
        """
        通用 JSON 文件加载器，统一处理各类读取异常。

        功能：尝试以 UTF-8 编码读取 JSON 文件，如文件不存在、格式损坏
              或 IO 异常则返回默认值。

        外部参数：
        - file_path (str): 要读取的 JSON 文件完整路径
        - default_value: 读取失败时返回的默认值（通常是空 dict 或 list）

        内部参数：无

        返回值：
        - dict/list: 解析成功的 JSON 数据，或 default_value（失败时）
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default_value
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败 {file_path}: {e}")
            return default_value
        except OSError as e:
            print(f"读取文件失败 {file_path}: {e}")
            return default_value

    def load_pet_db(self):
        """
        加载精灵数据库（all_pets_data.json），以精灵名称为键建立字典。

        功能：读取 all_pets_data.json（爬虫输出），将列表数据转换为
              以"名字"字段为键的字典，方便按名称快速查找。

        外部参数：无（从 self.db_file 路径读取）

        内部参数：
        - data: 从 JSON 加载的原始列表数据
        - p: 列表中的每个精灵 dict

        返回值：
        - dict: {精灵名称(str): 精灵数据(dict)}，空字典表示无数据或读取失败
        """
        self.ensure_data_dir()
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {p["名字"]: p for p in data if "名字" in p}
            return {}
        except Exception as e:
            print(f"读取精灵数据库失败: {e}")
            return {}

    def load_lineups(self):
        """
        加载阵容数据（all_lineups.json），兼容旧格式自动迁移。

        功能：读取 data/all_lineups.json，如果不存在则尝试从根目录下读取
              旧版 all_lineups.json 并迁移。旧格式是单层 {"阵容1": [...], ...}
              结构，新格式是两层 {"己方": {...}, "对方": {...}} 结构。
              迁移时将旧数据作为"己方"，"对方"置空。

        外部参数：无（从 self.lineup_file 和 self.legacy_lineup_file 读取）

        内部参数：
        - default_lineups: 从 constants.DEFAULT_LINEUPS 获取的默认空阵容结构
        - loaded: 从文件加载的原始数据
        - migrated: 迁移后的新格式数据结构
        - legacy_data: 从旧版文件读取的数据
        - side: "己方" 或 "对方"
        - name: 阵容名称（"阵容1"/"阵容2"/"阵容3"）

        返回值：
        - dict: 标准阵容数据 {"己方": {...}, "对方": {...}}
        """
        self.ensure_data_dir()
        default_lineups = DEFAULT_LINEUPS

        if os.path.exists(self.lineup_file):
            loaded = self._load_json_file(self.lineup_file, default_lineups)
            # 检查是否是旧格式（直接是阵容字典，没有"己方"键）
            if isinstance(loaded, dict) and "阵容1" in loaded and "己方" not in loaded:
                migrated = {
                    "己方": loaded,
                    "对方": {"阵容1": [], "阵容2": [], "阵容3": []},
                }
                self.save_lineups(migrated)
                return migrated
            else:
                # 确保新格式完整性：双方都有 3 个阵容槽位
                for side in ["己方", "对方"]:
                    if side not in loaded:
                        loaded[side] = {"阵容1": [], "阵容2": [], "阵容3": []}
                    for name in ["阵容1", "阵容2", "阵容3"]:
                        if name not in loaded[side]:
                            loaded[side][name] = []
                return loaded

        # 尝试从根目录下的旧版文件迁移
        if os.path.exists(self.legacy_lineup_file):
            legacy_data = self._load_json_file(
                self.legacy_lineup_file, {"阵容1": [], "阵容2": [], "阵容3": []}
            )
            if isinstance(legacy_data, dict) and "阵容1" in legacy_data:
                migrated = {
                    "己方": legacy_data,
                    "对方": {"阵容1": [], "阵容2": [], "阵容3": []},
                }
                self.save_lineups(migrated)
                return migrated

        return default_lineups

    def save_lineups(self, data):
        """
        保存阵容数据到 data/all_lineups.json。

        功能：将当前内存中的阵容数据写入 JSON 文件，确保 data/ 目录存在。

        外部参数：
        - data (dict):
            来源文件：utils/main_window_logic.py 中 save_to_disk() / add_pet_to_*() 方法
            含义：标准阵容数据字典，格式见 DEFAULT_LINEUPS

        内部参数：无
        返回值：无
        """
        self.ensure_data_dir()
        with open(self.lineup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
