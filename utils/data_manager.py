import json
import os

class DataManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.db_file = os.path.join(base_dir, "data", "all_pets_data.json")
        self.lineup_file = os.path.join(self.data_dir, "all_lineups.json")
        self.legacy_lineup_file = os.path.join(base_dir, "all_lineups.json")

    def ensure_data_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_json_file(self, file_path, default_value):
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
        self.ensure_data_dir()
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {p['名字']: p for p in data if '名字' in p}
            return {}
        except Exception as e:
            print(f"读取精灵数据库失败: {e}")
            return {}

    def load_lineups(self):
        self.ensure_data_dir()
        default_lineups = {"己方": {"阵容1": [], "阵容2": [], "阵容3": []}, "对方": {"阵容1": [], "阵容2": [], "阵容3": []}}

        if os.path.exists(self.lineup_file):
            loaded = self._load_json_file(self.lineup_file, default_lineups)
            # 检查是否是旧格式（直接是阵容字典）
            if isinstance(loaded, dict) and "阵容1" in loaded and "己方" not in loaded:
                # 迁移旧数据到己方
                migrated = {"己方": loaded, "对方": {"阵容1": [], "阵容2": [], "阵容3": []}}
                self.save_lineups(migrated)
                return migrated
            else:
                # 确保新格式完整
                for side in ["己方", "对方"]:
                    if side not in loaded:
                        loaded[side] = {"阵容1": [], "阵容2": [], "阵容3": []}
                    for name in ["阵容1", "阵容2", "阵容3"]:
                        if name not in loaded[side]:
                            loaded[side][name] = []
                return loaded

        if os.path.exists(self.legacy_lineup_file):
            legacy_data = self._load_json_file(self.legacy_lineup_file, {"阵容1": [], "阵容2": [], "阵容3": []})
            if isinstance(legacy_data, dict) and "阵容1" in legacy_data:
                migrated = {"己方": legacy_data, "对方": {"阵容1": [], "阵容2": [], "阵容3": []}}
                self.save_lineups(migrated)
                return migrated

        return default_lineups

    def save_lineups(self, data):
        self.ensure_data_dir()
        with open(self.lineup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
