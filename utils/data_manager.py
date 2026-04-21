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
        default_lineups = {"阵容1": [], "阵容2": [], "阵容3": []}

        if os.path.exists(self.lineup_file):
            return self._load_json_file(self.lineup_file, default_lineups)

        if os.path.exists(self.legacy_lineup_file):
            legacy_data = self._load_json_file(self.legacy_lineup_file, default_lineups)
            self.save_lineups(legacy_data)
            return legacy_data

        return {"阵容1": [], "阵容2": [], "阵容3": []}

    def save_lineups(self, data):
        self.ensure_data_dir()
        with open(self.lineup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
