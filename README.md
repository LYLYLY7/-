# 洛克王国 AI 对战工具

这是一个基于 `Tkinter` 的本地桌面工具，用来管理精灵数据、维护阵容，并做简化版实战伤害推演。

## 功能

- 从本地 `data/all_pets_data.json` 加载精灵数据库
- 在界面中搜索精灵并计算六维实战属性
- 维护阵容列表，阵容数据固定保存在 `data/all_lineups.json`
- 打开独立的伤害推演窗口，输入攻防参数进行估算
- 按需运行爬虫更新精灵数据库

## 项目结构

- `main.py`：程序入口
- `ui/main_window.py`：主窗口与阵容管理
- `ui/damage_window.py`：伤害计算窗口
- `utils/data_manager.py`：JSON 数据读写
- `utils/calculator.py`：属性与伤害公式
- `utils/crawler.py`：精灵数据爬虫
- `utils/check.py`：数据检查工具
- `data/all_pets_data.json`：精灵数据库
- `data/all_lineups.json`：阵容数据

## 运行环境

- Python 3.10+
- 需要安装 `tkinter`

安装依赖：

```bash
pip install -r requirements.txt
```

启动程序：

```bash
python3 main.py
```

单独打开伤害计算窗口：

```bash
python3 damage.py
```

## 数据说明

- 精灵数据库默认从 `data/all_pets_data.json` 读取
- 阵容文件固定保存在 `data/all_lineups.json`
- 如果项目根目录下存在旧版 `all_lineups.json`，程序会在读取时自动迁移到 `data/` 目录
