# 企业废弃功能设计文档

**日期**: 2026-03-16
**功能**: 企业清单页面增加废弃功能

---

## 需求概述

在企业清单页面，为每条企业记录增加废弃功能，支持：
- 每条企业记录增加废弃按钮
- 增加废弃筛选选项
- 废弃可以取消（恢复）

---

## 设计决策

### 1. 状态关系
企业与入库状态是**互斥关系**：
- 未入库（`is_imported=0, is_discarded=0`）
- 已入库（`is_imported=1, is_discarded=0`）
- 已废弃（`is_imported=0, is_discarded=1`）

### 2. 筛选选项
四个独立的筛选选项：
- 全部
- 未入库
- 已入库
- 已废弃

### 3. 交互方式
在"入库状态"列旁边新增"操作"列，包含废弃/恢复按钮。

### 4. 视觉样式
- 已废弃：红色背景标签 "🗑️ 已废弃"
- 废弃按钮：红色背景
- 恢复按钮：绿色背景

### 5. 批量操作
只需要单个操作，不需要批量废弃功能。

---

## 数据库设计

### 表结构修改

在 `companies` 表中添加字段：

```sql
ALTER TABLE companies ADD COLUMN is_discarded BOOLEAN DEFAULT 0;
```

### 状态规则

- `is_discarded = 1` 时，`is_imported` 必须为 0
- `is_imported = 1` 时，`is_discarded` 必须为 0
- 两者都为 0 时表示"未入库"状态

---

## 后端 API 设计

### database.py 新增方法

#### 1. add_discarded_column()
```python
def add_discarded_column(self):
    """为现有的 companies 表添加 is_discarded 列"""
    # 检查列是否已存在
    # 如果不存在，添加该列
    # 返回成功/失败
```

#### 2. toggle_company_discarded(company_id)
```python
def toggle_company_discarded(self, company_id: int) -> Optional[bool]:
    """
    切换企业废弃状态

    未废弃 → 已废弃（同时取消已入库状态）
    已废弃 → 未废弃（恢复为未入库状态）

    返回新的废弃状态，失败返回 None
    """
```

#### 3. 修改 get_companies_with_import_status()
```python
def get_companies_with_import_status(self, filter_type: str = 'all') -> List[Dict]:
    """
    新增筛选选项：
    - 'all': 全部
    - 'unimported': 仅未入库（且未废弃）
    - 'imported': 仅已入库
    - 'discarded': 仅已废弃
    - 'undiscarded': 仅未废弃（包括未入库和已入库）
    """
```

### web_app.py 路由

#### /companies/toggle-discard
```python
@app.route('/companies/toggle-discard', methods=['POST'])
def toggle_company_discarded():
    """切换企业废弃状态"""
    company_id = request.json.get('company_id')

    if not company_id:
        return jsonify({'success': False, 'error': '缺少企业 ID'})

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    new_status = db.toggle_company_discarded(company_id)
    db.close()

    if new_status is None:
        return jsonify({'success': False, 'error': '更新失败'})

    return jsonify({'success': True, 'is_discarded': new_status})
```

#### 修改 /companies 路由
```python
@app.route('/companies')
def companies_list():
    """企业清单页面"""
    filter_type = request.args.get('filter', 'all')

    # 支持新的筛选选项：discarded, undiscarded
    companies = db.get_companies_with_import_status(filter_type)
    # ...
```

---

## 前端 UI 设计

### 筛选栏

```html
<div class="flex items-center space-x-6">
    <span class="text-sm font-medium text-gray-700">筛选：</span>
    <label><!-- 全部 --></label>
    <label><!-- 仅未入库 --></label>
    <label><!-- 仅已入库 --></label>
    <label><!-- 新增：仅已废弃 --></label>
</div>
```

### 表格结构

| 复选框 | 企业名称 | 地区 | 招聘职位数 | 来源平台 | 入库状态 | **操作** |
|--------|----------|------|------------|----------|----------|----------|
| ✓ | XX公司 | 上海 | 5个职位 | BOSS直聘 | ❌ 未入库 | [废弃] |
 | XX公司 | 北京 | 3个职位 | 前程无忧 | ✅ 已入库 | [废弃] |
 | YY公司 | 深圳 | 2个职位 | BOSS直聘 | 🗑️ 已废弃 | **[恢复]** |

### 入库状态列显示逻辑

- **已废弃**：`<span class="bg-red-100 text-red-800">🗑️ 已废弃</span>`
- **已入库**：`<span class="bg-green-100 text-green-800">✅ 已入库</span>`
- **未入库**：`<span class="bg-gray-100 text-gray-800">❌ 未入库</span>`

### 操作列按钮

**废弃按钮**（未废弃状态显示）：
```html
<button class="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
        onclick="toggleDiscardStatus({{ company.id }})">
    🗑️ 废弃
</button>
```

**恢复按钮**（已废弃状态显示）：
```html
<button class="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
        onclick="toggleDiscardStatus({{ company.id }})">
    ↩️ 恢复
</button>
```

### 已废弃行的样式

```html
<tr class="bg-red-50 hover:bg-red-100 transition-colors">
    <!-- 整行淡红色背景 -->
</tr>
```

### 复选框逻辑

- **已废弃**：不显示复选框
- **已入库**：不显示复选框
- **未入库且未废弃**：显示复选框，可批量标记

---

## 前端交互逻辑

### JavaScript 函数

#### toggleDiscardStatus(company_id)
```javascript
function toggleDiscardStatus(companyId) {
    fetch('/companies/toggle-discard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_id: companyId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            showToast(data.error || '操作失败', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('操作失败', 'error');
    });
}
```

### 视觉反馈

- **废弃按钮**：红色 `bg-red-600`，hover `bg-red-700`
- **恢复按钮**：绿色 `bg-green-600`，hover `bg-green-700`
- **已废弃行**：淡红色背景 `bg-red-50`，hover 变深 `bg-red-100`

### 错误处理

- API 调用失败时显示红色 Toast 提示
- 复选框逻辑自动排除已废弃企业

---

## 实现顺序

### 步骤 1：数据库层
1. 在 `database.py` 添加 `add_discarded_column()` 方法
2. 在 `database.py` 添加 `toggle_company_discarded(company_id)` 方法
3. 修改 `get_companies_with_import_status()` 支持废弃筛选
4. 创建迁移脚本并运行

### 步骤 2：后端 API
1. 在 `web_app.py` 添加 `/companies/toggle-discard` 路由
2. 修改 `companies_list()` 路由传递废弃筛选参数

### 步骤 3：前端模板
1. 修改 `companies.html` 添加"仅已废弃"筛选选项
2. 添加"操作"列
3. 修改入库状态列显示三种状态
4. 添加废弃/恢复按钮
5. 添加废弃行的样式

### 步骤 4：前端脚本
1. 添加 `toggleDiscardStatus()` 函数
2. 修改复选框显示逻辑（排除已废弃）
3. 添加废弃行的视觉样式

---

## 测试策略

### 数据库测试
- 添加 `is_discarded` 列后，验证默认值为 0
- 测试状态切换：未入库 → 已废弃（is_imported 应保持 0）
- 测试状态切换：已入库 → 已废弃（is_imported 应变为 0）
- 测试状态切换：已废弃 → 未废弃（恢复为未入库状态）

### 功能测试
- 筛选功能：验证四个筛选选项是否正确显示
- 废弃操作：点击"废弃"按钮后，企业状态变为已废弃，复选框消失
- 恢复操作：点击"恢复"按钮后，企业恢复为未入库状态
- 互斥验证：已入库的企业点击"废弃"后，不再显示为已入库
- 视觉验证：已废弃的行显示红色背景，状态标签正确

### 边界情况
- 已废弃的企业不能被批量标记为已入库
- 刷新页面后废弃状态保持不变
- API 调用失败时的错误处理

### 数据完整性
- 切换状态时数据库事务完整性
- 并发操作的处理
