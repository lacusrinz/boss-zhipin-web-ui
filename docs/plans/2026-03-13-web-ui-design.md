# BOSS 直聘 Web 管理界面设计文档

**日期**: 2026-03-13
**作者**: Claude + 用户协作设计
**状态**: 设计阶段

## 1. 概述

### 1.1 目标

为现有 BOSS 直聘职位采集项目添加一个轻量级 Web 管理界面，实现：

- 通过网页粘贴 HTML 源码进行数据采集（替代手动保存文件）
- 可视化展示岗位明细信息
- 管理企业清单，支持标记"已入库"用于 CRM 跟进

### 1.2 约束条件

- **部署方式**: 本地运行，单用户使用
- **技术栈**: Python Flask + Tailwind CSS，复用现有代码
- **数据存储**: 复用现有 SQLite 数据库，最小化改动
- **UI 风格**: 现代简洁，使用 Tailwind CSS

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────┐
│                 Browser                      │
│  ┌──────────────┐  ┌──────────────────┐    │
│  │ Paste Page   │  │ Job List /       │    │
│  │              │  │ Company List     │    │
│  └──────────────┘  └──────────────────┘    │
└─────────────┬───────────────────────────────┘
              │ HTTP
              ▼
┌─────────────────────────────────────────────┐
│              Flask Web App                   │
│  ┌────────────┐  ┌──────────────────────┐   │
│  │ Routes     │  │ Templates (Jinja2)   │   │
│  └────────────┘  └──────────────────────┘   │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         Database Module (复用)               │
│  ┌────────────┐  ┌──────────────────────┐   │
│  │ Parse HTML │  │ SQLite Operations    │   │
│  └────────────┘  └──────────────────────┘   │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         SQLite Database                      │
│  companies 表 (新增 is_imported 字段)        │
│  jobs 表 (不变)                              │
└─────────────────────────────────────────────┘
```

### 2.2 文件结构

```
code/
├── web_app.py              # Flask 主应用（新建）
├── templates/              # Jinja2 模板目录（新建）
│   ├── base.html          # 基础模板 + Tailwind 引入
│   ├── paste.html         # HTML 粘贴页面
│   ├── jobs.html          # 岗位明细页面
│   └── companies.html     # 企业清单页面
├── static/                 # 静态资源（新建）
│   └── custom.js          # 自定义 JS（批量操作、Toast）
├── extract_jobs_v6.py     # 现有脚本（需重构）
└── database.py            # 数据库模块（需扩展）
```

## 3. 数据库设计

### 3.1 表结构修改

**companies 表新增字段：**

```sql
ALTER TABLE companies ADD COLUMN is_imported BOOLEAN DEFAULT 0;
```

**字段说明：**
- `is_imported`: 布尔值，0=未入库，1=已入库
- 默认值为 0（未入库）
- 可逆操作，支持切换状态

### 3.2 数据库函数扩展

在 `database.py` 中新增以下函数：

```python
def toggle_company_imported(company_id: int) -> bool:
    """切换企业入库状态"""

def batch_import_companies(company_ids: List[int]) -> int:
    """批量标记企业为已入库，返回成功数量"""

def get_companies_with_import_status(
    filter_type: str = 'all'
) -> List[Dict]:
    """获取企业列表，支持按入库状态筛选
    filter_type: 'all' | 'imported' | 'unimported'
    """
```

## 4. Web 应用设计

### 4.1 路由设计

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 粘贴页面（首页） |
| `/parse` | POST | 解析 HTML，存储数据，跳转 |
| `/jobs` | GET | 岗位明细列表 |
| `/companies` | GET | 企业清单（带筛选） |
| `/companies/toggle` | POST | 切换单个企业入库状态 |
| `/companies/batch-import` | POST | 批量标记已入库 |

### 4.2 页面设计

#### 4.2.1 首页（粘贴页面）- `/`

**布局：**
```
┌──────────────────────────────────────┐
│  🔗 粘贴数据 | 📋 岗位明细 | 🏢 企业清单  │  ← 导航栏
├──────────────────────────────────────┤
│                                      │
│      粘贴 BOSS 直聘 HTML 源码         │
│  ┌────────────────────────────────┐  │
│  │                                │  │
│  │   [大文本框]                    │  │
│  │                                │  │
│  └────────────────────────────────┘  │
│                                      │
│         [🔍 解析数据]                 │
│                                      │
└──────────────────────────────────────┘
```

**交互：**
- 文本框 placeholder: "粘贴完整的 HTML 源码（右键查看源代码复制）..."
- 点击"解析数据"提交表单

#### 4.2.2 岗位明细页面 - `/jobs`

**布局：**
```
┌──────────────────────────────────────┐
│  🔗 粘贴数据 | 📋 岗位明细 | 🏢 企业清单  │
├──────────────────────────────────────┤
│  共 15 个职位，来自 8 家企业          │  ← 统计信息
├──────────────────────────────────────┤
│  ┌────────────────────────────────┐  │
│  │ 职位名称 │ 公司 │ 薪资 │ 地区... │  │  ← 响应式表格
│  ├────────────────────────────────┤  │
│  │ Python开发 │ XX科技│ 20-30K│ 北京│  │
│  │ ...                             │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

**表格列：**
- 职位名称
- 公司名称
- 薪资
- 地区
- 经验要求
- 学历
- 发布时间

#### 4.2.3 企业清单页面 - `/companies`

**布局：**
```
┌──────────────────────────────────────┐
│  🔗 粘贴数据 | 📋 岗位明细 | 🏢 企业清单  │
├──────────────────────────────────────┤
│  筛选: ○全部 ○仅未入库 ●仅已入库      │  ← 筛选栏
├──────────────────────────────────────┤
│  ┌────────────────────────────────┐  │
│  │☑ │ XX科技   │ 北京 │ 3个职位 │ ✅│  │  ← 企业列表
│  │☑ │ YY信息   │ 上海 │ 2个职位 │ ❌│  │
│  │☐ │ ZZ网络   │ 深圳 │ 1个职位 │ ❌│  │
│  └────────────────────────────────┘  │
│                                      │
│                      [✓ 标记已入库 2] │  ← 浮动按钮
└──────────────────────────────────────┘
```

**表格列：**
- 复选框（用于批量操作）
- 企业名称
- 地区
- 招聘职位数
- 入库状态（✅/❌）

**批量操作：**
- 勾选企业后，按钮显示"标记已入库 X"
- 点击后批量更新，显示 Toast 提示

**筛选：**
- URL 参数：`?filter=unimported`
- 单选按钮切换筛选条件

## 5. 技术实现

### 5.1 Flask 应用骨架

```python
# web_app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import init_db, insert_company, insert_job, get_companies, get_jobs, toggle_company_imported, batch_import_companies

app = Flask(__name__)
app.secret_key = 'dev-key'

@app.route('/')
def index():
    return render_template('paste.html')

@app.route('/parse', methods=['POST'])
def parse():
    html = request.form.get('html_content')
    if not html:
        flash('请粘贴 HTML 内容', 'error')
        return redirect(url_for('index'))

    try:
        # 调用解析逻辑
        # 存入数据库
        flash(f'成功解析 {job_count} 个职位，{company_count} 家企业', 'success')
        return redirect(url_for('jobs'))
    except Exception as e:
        flash(f'解析失败: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/jobs')
def jobs():
    jobs = get_jobs()
    return render_template('jobs.html', jobs=jobs)

@app.route('/companies')
def companies():
    filter_type = request.args.get('filter', 'all')
    companies = get_companies_with_import_status(filter_type)
    return render_template('companies.html', companies=companies, filter=filter_type)

@app.route('/companies/toggle', methods=['POST'])
def toggle():
    company_id = request.json.get('company_id')
    new_status = toggle_company_imported(company_id)
    return jsonify({'success': True, 'is_imported': new_status})

@app.route('/companies/batch-import', methods=['POST'])
def batch_import():
    company_ids = request.form.getlist('company_ids')
    count = batch_import_companies(company_ids)
    return jsonify({'success': True, 'count': count})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 5.2 前端技术栈

- **模板引擎**: Jinja2（Flask 内置）
- **CSS 框架**: Tailwind CSS（CDN 引入）
- **JavaScript**: 原生 JS（无需构建）
  - 批量选择逻辑
  - Toast 提示
  - AJAX 请求

### 5.3 Tailwind 集成

在 `base.html` 中引入：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BOSS 直聘管理</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    {% block content %}{% endblock %}
</body>
</html>
```

## 6. 数据流

### 6.1 数据采集流程

```
用户操作           Web App              Database
   │                 │                    │
   ├─粘贴HTML ──────>│                    │
   │                 ├─解析HTML ──────>   │
   │                 │                    ├─插入公司
   │                 │                    ├─插入职位
   │                 │<─返回结果 ──────    │
   │<─跳转到岗位 ────│                    │
   │                 │                    │
```

### 6.2 企业标记流程

```
用户操作           Web App              Database
   │                 │                    │
   ├─勾选企业 ──────>│                    │
   ├─点击标记 ──────>│                    │
   │                 ├─批量更新 ──────>   │
   │                 │                    ├─UPDATE is_imported=1
   │                 │<─成功数量 ──────   │
   │<─显示Toast ──── │                    │
```

## 7. 代码复用

### 7.1 解析逻辑重构

将 `extract_jobs_v6.py` 中的解析代码抽取为独立函数：

```python
# 在 extract_jobs_v6.py 中新增
def parse_html_content(html: str) -> Tuple[List[Dict], List[Dict]]:
    """
    解析 HTML 内容，返回 (职位列表, 企业列表)

    Returns:
        (jobs, companies): 职位和企业数据列表
    """
    soup = BeautifulSoup(html, 'lxml')
    # ... 现有解析逻辑 ...
    return jobs, companies
```

### 7.2 数据库模块扩展

复用现有的：
- `init_db()`
- `insert_company()`
- `insert_job()`

新增（见 3.2）：
- `toggle_company_imported()`
- `batch_import_companies()`
- `get_companies_with_import_status()`

## 8. 错误处理

### 8.1 输入验证

| 场景 | 处理方式 |
|------|----------|
| 空内容 | Flash 提示"请粘贴 HTML 内容" |
| 无效 HTML | 捕获异常，提示"无法识别的页面格式" |
| 无数据 | 提示"未找到职位信息" |

### 8.2 解析失败

- HTML 结构变化：记录错误日志，返回友好提示
- Unicode 解码失败：降级处理，保留原始字符

### 8.3 数据库操作

- 批量操作使用事务，全部成功或全部回滚
- 重复数据：复用现有去重逻辑

## 9. 开发计划

### 9.1 第一阶段：核心功能（MVP）

**目标**: 实现端到端的基本流程

1. ✅ 数据库修改：添加 `is_imported` 字段
2. ✅ 创建 Flask 应用骨架
3. ✅ 实现粘贴页面和解析逻辑
4. ✅ 实现岗位明细页面（表格展示）
5. ✅ 实现企业清单页面（列表 + 单个勾选）

**验收标准**:
- 能粘贴 HTML 并成功解析
- 能查看岗位明细
- 能查看企业列表并切换单个企业的入库状态

### 9.2 第二阶段：批量操作和筛选

**目标**: 提升用户体验

1. ✅ 实现批量标记功能
2. ✅ 添加入库状态筛选
3. ✅ 添加操作反馈（Toast 提示）

**验收标准**:
- 能批量选择和标记企业
- 能按状态筛选企业列表
- 操作后有明确反馈

### 9.3 第三阶段：优化完善

**目标**: 打磨细节

1. ✅ 完善错误处理和用户提示
2. ✅ 响应式布局调整
3. ✅ 代码重构和测试

## 10. 部署和运行

### 10.1 本地运行

```bash
# 安装依赖
pip install flask

# 初始化数据库（如果需要）
python -c "from database import init_db; init_db()"

# 启动应用
python code/web_app.py
```

### 10.2 访问地址

```
http://localhost:5000
```

### 10.3 依赖更新

在 `requirements.txt` 中新增：

```
flask>=3.0.0
```

## 11. 未来扩展（可选）

- [ ] 添加导出功能（导出筛选后的企业列表为 Excel）
- [ ] 添加搜索功能（按企业名、职位名搜索）
- [ ] 添加统计图表（薪资分布、地区分布）
- [ ] 支持多用户（添加登录和权限管理）
- [ ] 部署到内网服务器供团队使用
