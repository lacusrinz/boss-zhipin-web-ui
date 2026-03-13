# BOSS 直聘岗位信息提取任务

**任务日期**: 2026-03-10 ~ 2026-03-12
**状态**: ✅ 已完成（支持数据库存储）

---

## 📁 项目结构

```
2026-03-10-boss直聘搜索/
├── data/                          # 数据目录
│   ├── 智能制造-2026-3-10.txt     # 历史搜索结果（手动保存）
│   ├── 医疗器械-2026-3-10.txt     # 历史搜索结果（手动保存）
│   ├── 机器人-2026-3-11.txt       # 历史搜索结果（手动保存）
│   ├── collected/                 # 手动收集的 HTML 文件目录
│   └── boss_jobs.db               # SQLite 数据库（自动生成）
├── code/                          # 脚本目录
│   ├── extract_jobs_v6.py         # 提取脚本（支持数据库存储）
│   ├── collect_jobs_manual.py     # 收集引导脚本
│   ├── import_excel_to_db.py      # Excel 数据导入工具
│   ├── database.py                # 数据库操作模块
│   └── query_database.py          # 数据库查询工具
├── reports/                       # Excel 报告目录
│   ├── BOSS直聘岗位信息_20260310-1513.xlsx  # 历史报告
│   ├── BOSS直聘岗位信息_机器人_20260311-0928.xlsx  # 历史报告
│   └── BOSS直聘岗位信息_新能源汽车_*.xlsx  # 历史报告
├── requirements.txt               # Python 依赖
└── docs/                          # 文档
    └── BOSS直聘提取经验总结.md    # 详细经验总结
```

---

## 📊 提取结果

### 数据库结构

#### 企业表 (companies)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| name | TEXT | 企业名称（唯一） |
| url | TEXT | 企业 URL |
| created_at | TIMESTAMP | 创建时间 |

#### 岗位表 (jobs)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| company_id | INTEGER | 企业 ID（外键） |
| job_name | TEXT | 岗位名称 |
| salary | TEXT | 薪资 |
| location | TEXT | 工作地点 |
| experience | TEXT | 经验要求 |
| education | TEXT | 学历要求 |
| source | TEXT | 数据来源 |
| collection_time | TEXT | 采集时间 |
| created_at | TIMESTAMP | 创建时间 |

### Excel 报告字段
1. 序号
2. 岗位名称
3. 薪资
4. 公司名称
5. 公司链接
6. 工作地点
7. 经验要求
8. 学历要求
9. 采集时间
10. 数据来源

---

## 🚀 快速使用

### 方式一：提取数据 + 保存到数据库（推荐）

#### 1. 手动收集 HTML 文件

在浏览器中打开 BOSS 直聘，登录后搜索以下行业，将每个搜索结果页面保存为 HTML：
- 智能制造
- 机器人
- 医疗器械
- 新能源
- 芯片
- 光伏

保存到 `data/collected/` 目录，文件命名格式：`{行业名称}.html`

#### 2. 提取数据并保存到数据库

```bash
python3 code/extract_jobs_v6.py
```

这个脚本会：
- 从 HTML 文件中提取岗位信息
- 去重数据
- **自动插入到 SQLite 数据库**（data/boss_jobs.db）
- 生成 Excel 报告到 `reports/` 目录
- 显示统计信息

#### 3. 查询数据库

```bash
python3 code/query_database.py
```

提供交互式查询界面：
- 查看总体统计
- 按来源统计
- 查看岗位最多的企业
- 搜索岗位
- 查看所有企业
- 导出数据为 JSON

---

### 方式二：导入历史 Excel 数据

如果已有 Excel 报告，可以导入数据库：

```bash
python3 code/import_excel_to_db.py
```

会自动导入 `reports/` 目录下的所有 Excel 文件。

---

### 方式三：半自动化引导

```bash
python3 code/collect_jobs_manual.py
```

按照提示手动收集数据，然后自动提取。

---

## 📖 详细文档

- [BOSS 直聘提取经验总结](docs/BOSS直聘提取经验总结.md)
  - Unicode 私有区字符解码
  - BeautifulSoup vs 正则表达式
  - 数据清洗技巧
  - 常见坑点

---

## ⚙️ 依赖安装

### Python 依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install beautifulsoup4 openpyxl lxml python-dateutil
```

---

## 📝 备注

- **采集时间**: 2026-03-10 14:50
- **数据来源**: BOSS 直聘网页版
- **注意事项**: 薪资字段已自动解码 Unicode 私有区字符

---

## 📤 数据存储

- **飞书表格**: [BOSS直聘岗位信息](https://rcn28gxothxt.feishu.cn/wiki/MrPxwMItgiwBjbkoDVsc1u0JnQe?sheet=e31508)
- **操作原则**: 新数据追加到表格末尾，不创建新表格
