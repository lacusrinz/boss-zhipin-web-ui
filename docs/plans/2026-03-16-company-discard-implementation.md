# 企业废弃功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在企业清单页面添加废弃功能，支持标记企业为已废弃、恢复废弃状态、按废弃状态筛选

**Architecture:** 在 companies 表添加 is_discarded 字段，通过数据库层 toggle_company_discarded() 方法实现状态切换，前端添加废弃/恢复按钮和筛选选项

**Tech Stack:** Python Flask, SQLite, Jinja2 templates, JavaScript fetch API, Tailwind CSS

---

## Task 1: 添加数据库字段

**Files:**
- Modify: `code/database.py`
- Create: `code/add_discarded_column.py`

**Step 1: 在 database.py 添加 add_discarded_column() 方法**

在 `database.py` 的 `BOSSDatabase` 类中，在 `add_platform_column()` 方法后添加新方法：

```python
def add_discarded_column(self):
    """
    为现有的 companies 表添加 is_discarded 列
    用于数据库升级
    """
    try:
        # 检查列是否已存在
        self.cursor.execute("PRAGMA table_info(companies)")
        columns = [col[1] for col in self.cursor.fetchall()]

        if 'is_discarded' not in columns:
            self.cursor.execute("""
                ALTER TABLE companies ADD COLUMN is_discarded BOOLEAN DEFAULT 0
            """)
            self.conn.commit()
            logging.info("已添加 is_discarded 列到 companies 表")
            return True
        else:
            logging.info("is_discarded 列已存在，无需添加")
            return True

    except Exception as e:
        logging.error(f"添加 is_discarded 列失败: {e}")
        return False
```

插入位置：在 `add_platform_column()` 方法后（约第438行后）

**Step 2: 创建数据库迁移脚本**

创建文件 `code/add_discarded_column.py`：

```python
#!/usr/bin/env python3
"""
添加企业废弃状态字段
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from database import BOSSDatabase


def add_discarded_column():
    """添加 is_discarded 列"""
    db = BOSSDatabase()

    if not db.connect():
        print("❌ 数据库连接失败")
        return False

    print("=" * 60)
    print(" 添加企业废弃状态字段")
    print("=" * 60)

    # 添加列
    if not db.add_discarded_column():
        print("❌ 添加 is_discarded 列失败")
        db.close()
        return False

    print("✅ is_discarded 列添加成功")
    print("\n" + "=" * 60)
    print(" 迁移完成！")
    print("=" * 60)

    # 验证
    db.cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in db.cursor.fetchall()]
    print(f"\n当前 companies 表字段: {', '.join(columns)}")

    db.close()
    return True


if __name__ == '__main__':
    try:
        success = add_discarded_column()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

**Step 3: 运行迁移脚本**

运行: `python3 code/add_discarded_column.py`
预期输出:
```
============================================================
 添加企业废弃状态字段
============================================================
✅ is_discarded 列添加成功

============================================================
 迁移完成！
============================================================

当前 companies 表字段: id, name, url, is_imported, created_at, is_discarded
```

**Step 4: 验证数据库字段**

运行: `sqlite3 data/boss_jobs.db "PRAGMA table_info(companies);"`
预期输出: 包含 `is_discarded` 字段

**Step 5: 提交**

```bash
git add code/database.py code/add_discarded_column.py
git commit -m "feat: add is_discarded column to companies table

- Add add_discarded_column() method to BOSSDatabase
- Create migration script to add is_discarded field
- Set default value to 0 (not discarded)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: 添加数据库操作方法

**Files:**
- Modify: `code/database.py`

**Step 1: 添加 toggle_company_discarded() 方法**

在 `database.py` 的 `toggle_company_imported()` 方法后添加新方法：

```python
def toggle_company_discarded(self, company_id: int) -> Optional[bool]:
    """
    切换企业废弃状态

    未废弃 → 已废弃（同时取消已入库状态）
    已废弃 → 未废弃（恢复为未入库状态）

    Args:
        company_id: 企业 ID

    Returns:
        bool: 新的废弃状态，失败返回 None
    """
    try:
        # 获取当前状态
        self.cursor.execute("""
            SELECT is_discarded, is_imported FROM companies WHERE id = ?
        """, (company_id,))

        result = self.cursor.fetchone()
        if result is None:
            logging.warning(f"企业 ID {company_id} 不存在")
            return None

        current_discarded = result[0]
        current_imported = result[1]

        if current_discarded:
            # 当前已废弃 → 恢复为未废弃
            new_discarded = 0
            new_imported = 0  # 恢复为未入库状态
        else:
            # 当前未废弃 → 标记为已废弃
            new_discarded = 1
            new_imported = 0  # 取消已入库状态

        # 更新状态
        self.cursor.execute("""
            UPDATE companies
            SET is_discarded = ?, is_imported = ?
            WHERE id = ?
        """, (new_discarded, new_imported, company_id))

        self.conn.commit()
        logging.info(f"企业 ID {company_id} 废弃状态已切换为 {new_discarded}")
        return bool(new_discarded)

    except Exception as e:
        logging.error(f"切换企业废弃状态失败: {e}")
        return None
```

插入位置：在 `toggle_company_imported()` 方法后（约第475行后）

**Step 2: 修改 get_companies_with_import_status() 方法**

修改现有的 `get_companies_with_import_status()` 方法，添加废弃筛选逻辑：

在筛选条件部分添加新的 case：

找到这段代码（约第537-541行）：
```python
# 添加筛选条件
if filter_type == 'imported':
    query += " AND c.is_imported = 1"
elif filter_type == 'unimported':
    query += " AND c.is_imported = 0"
```

替换为：
```python
# 添加筛选条件
if filter_type == 'imported':
    query += " AND c.is_imported = 1 AND c.is_discarded = 0"
elif filter_type == 'unimported':
    query += " AND c.is_imported = 0 AND c.is_discarded = 0"
elif filter_type == 'discarded':
    query += " AND c.is_discarded = 1"
elif filter_type == 'undiscarded':
    query += " AND c.is_discarded = 0"
```

**Step 3: 修改查询结果包含 is_discarded 字段**

修改 `get_companies_with_import_status()` 方法的 SELECT 语句（约第523-532行）：

找到这段代码：
```python
query = """
    SELECT
        c.id,
        c.name,
        c.url,
        c.is_imported,
        COUNT(j.id) as job_count,
        GROUP_CONCAT(DISTINCT j.location) as locations,
        GROUP_CONCAT(DISTINCT j.platform) as platforms
    FROM companies c
    LEFT JOIN jobs j ON c.id = j.company_id
    WHERE c.url IS NOT NULL AND c.url != ''
"""
```

替换为：
```python
query = """
    SELECT
        c.id,
        c.name,
        c.url,
        c.is_imported,
        c.is_discarded,
        COUNT(j.id) as job_count,
        GROUP_CONCAT(DISTINCT j.location) as locations,
        GROUP_CONCAT(DISTINCT j.platform) as platforms
    FROM companies c
    LEFT JOIN jobs j ON c.id = j.company_id
    WHERE c.url IS NOT NULL AND c.url != ''
"""
```

同时修改 columns 列表（约第548行）：
```python
columns = ['id', 'name', 'url', 'is_imported', 'is_discarded', 'job_count', 'locations', 'platforms']
```

**Step 4: 提交**

```bash
git add code/database.py
git commit -m "feat: add discard status methods to database

- Add toggle_company_discarded() method
- Update get_companies_with_import_status() to support discarded filter
- Include is_discarded in query results

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: 添加后端 API 路由

**Files:**
- Modify: `code/web_app.py`

**Step 1: 添加 /companies/toggle-discard 路由**

在 `web_app.py` 的 `toggle_company()` 路由后添加新路由（约第153行后）：

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

**Step 2: 提交**

```bash
git add code/web_app.py
git commit -m "feat: add toggle-discard API endpoint

- Add /companies/toggle-discard route for discard status
- Return JSON response with new discard status

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: 修改前端筛选栏

**Files:**
- Modify: `code/templates/companies.html`

**Step 1: 添加"仅已废弃"筛选选项**

在筛选栏中添加第四个选项（约第30行后）：

找到这段代码：
```html
<label class="inline-flex items-center">
    <input type="radio" name="filter" value="imported" {% if filter == 'imported' %}checked{% endif %}
           onchange="window.location.href='{{ url_for('companies_list') }}?filter=imported'"
           class="form-radio h-4 w-4 text-blue-600 focus:ring-blue-500">
    <span class="ml-2 text-sm text-gray-700">仅已入库</span>
</label>
```

在这段代码后添加：
```html
<label class="inline-flex items-center">
    <input type="radio" name="filter" value="discarded" {% if filter == 'discarded' %}checked{% endif %}
           onchange="window.location.href='{{ url_for('companies_list') }}?filter=discarded'"
           class="form-radio h-4 w-4 text-blue-600 focus:ring-blue-500">
    <span class="ml-2 text-sm text-gray-700">仅已废弃</span>
</label>
```

**Step 2: 提交**

```bash
git add code/templates/companies.html
git commit -m "feat: add discarded filter option to companies page

- Add '仅已废弃' radio button to filter bar
- Allow filtering by discarded status

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: 修改表格列和入库状态显示

**Files:**
- Modify: `code/templates/companies.html`

**Step 1: 添加"操作"列表头**

在表头添加新列（约第48行后）：

找到这段代码：
```html
<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">入库状态</th>
```

在这段代码后添加：
```html
<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
```

**Step 2: 修改入库状态列显示逻辑**

找到入库状态列的代码（约第104-118行）：
```html
<td class="px-4 py-4 whitespace-nowrap">
    {% if company.is_imported %}
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 cursor-pointer hover:bg-green-200"
          onclick="toggleImportStatus({{ company.id }})"
          id="status-{{ company.id }}">
        ✅ 已入库
    </span>
    {% else %}
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 cursor-pointer hover:bg-gray-200"
          onclick="toggleImportStatus({{ company.id }})"
          id="status-{{ company.id }}">
        ❌ 未入库
    </span>
    {% endif %}
</td>
```

替换为：
```html
<td class="px-4 py-4 whitespace-nowrap">
    {% if company.is_discarded %}
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"
          id="status-{{ company.id }}">
        🗑️ 已废弃
    </span>
    {% elif company.is_imported %}
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 cursor-pointer hover:bg-green-200"
          onclick="toggleImportStatus({{ company.id }})"
          id="status-{{ company.id }}">
        ✅ 已入库
    </span>
    {% else %}
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 cursor-pointer hover:bg-gray-200"
          onclick="toggleImportStatus({{ company.id }})"
          id="status-{{ company.id }}">
        ❌ 未入库
    </span>
    {% endif %}
</td>
```

**Step 3: 修改复选框逻辑**

修改复选框显示逻辑（约第54-59行），已废弃的企业不显示复选框：

找到这段代码：
```html
<td class="px-4 py-4 whitespace-nowrap">
    {% if not company.is_imported %}
    <input type="checkbox" name="company_ids" value="{{ company.id }}"
           class="company-checkbox form-checkbox h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
           onchange="updateBatchButton()">
    {% endif %}
</td>
```

替换为：
```html
<td class="px-4 py-4 whitespace-nowrap">
    {% if not company.is_imported and not company.is_discarded %}
    <input type="checkbox" name="company_ids" value="{{ company.id }}"
           class="company-checkbox form-checkbox h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
           onchange="updateBatchButton()">
    {% endif %}
</td>
```

**Step 4: 为已废弃行添加样式**

修改 tr 标签（约第52行）：

找到：
```html
<tr class="hover:bg-gray-50 transition-colors">
```

替换为：
```html
<tr class="{% if company.is_discarded %}bg-red-50 hover:bg-red-100{% else %}hover:bg-gray-50{% endif %} transition-colors">
```

**Step 5: 提交**

```bash
git add code/templates/companies.html
git commit -m "feat: update status column with discard display

- Modify status column to show three states: discarded/imported/unimported
- Hide checkbox for discarded companies
- Add red background for discarded rows
- Remove click handler from discarded status label

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: 添加操作列

**Files:**
- Modify: `code/templates/companies.html`

**Step 1: 添加操作列单元格**

在入库状态列后添加操作列（入库状态列的 `</td>` 后，约第119行后）：

找到：
```html
</td>
{% endfor %}
```

在 `</td>` 和 `{% endfor %}` 之间添加：
```html
<td class="px-4 py-4 whitespace-nowrap">
    {% if company.is_discarded %}
    <button class="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
            onclick="toggleDiscardStatus({{ company.id }})">
        ↩️ 恢复
    </button>
    {% else %}
    <button class="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
            onclick="toggleDiscardStatus({{ company.id }})">
        🗑️ 废弃
    </button>
    {% endif %}
</td>
```

**Step 2: 提交**

```bash
git add code/templates/companies.html
git commit -m "feat: add action column with discard/restore buttons

- Add 操作 column with discard/restore buttons
- Show '恢复' button for discarded companies (green)
- Show '废弃' button for active companies (red)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: 添加前端 JavaScript 函数

**Files:**
- Modify: `code/templates/companies.html`

**Step 1: 添加 toggleDiscardStatus() 函数**

在 JavaScript 部分添加新函数（约第194行后，在 `toggleImportStatus()` 函数后）：

```javascript
// 切换企业废弃状态
function toggleDiscardStatus(companyId) {
    fetch('/companies/toggle-discard', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ company_id: companyId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 重新加载页面以更新状态
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

**Step 2: 提交**

```bash
git add code/templates/companies.html
git commit -m "feat: add toggleDiscardStatus JavaScript function

- Add toggleDiscardStatus() function to handle discard button clicks
- Call /companies/toggle-discard API
- Reload page on success, show error toast on failure

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: 测试功能

**Step 1: 启动服务器**

运行: `python3 code/web_app.py`
预期输出: 服务器启动在 http://127.0.0.1:5001

**Step 2: 测试数据库迁移**

打开浏览器访问 http://127.0.0.1:5001/companies

检查点：
- 页面正常加载
- 所有企业显示正常
- 未废弃的企业显示"❌ 未入库"或"✅ 已入库"

**Step 3: 测试废弃功能**

操作：
1. 点击某个企业的"🗑️ 废弃"按钮
2. 观察页面刷新

检查点：
- 企业状态变为"🗑️ 已废弃"（红色标签）
- 整行背景变为淡红色
- 复选框消失
- 操作列显示"↩️ 恢复"按钮（绿色）

**Step 4: 测试恢复功能**

操作：
1. 点击已废弃企业的"↩️ 恢复"按钮
2. 观察页面刷新

检查点：
- 企业状态变为"❌ 未入库"（灰色标签）
- 整行背景恢复正常
- 复选框重新出现
- 操作列显示"🗑️ 废弃"按钮（红色）

**Step 5: 测试筛选功能**

操作：
1. 点击"仅已废弃"筛选选项
2. 观察页面变化

检查点：
- 只显示已废弃的企业
- URL 包含 `?filter=discarded`

操作：
1. 点击"全部"筛选选项
2. 观察页面变化

检查点：
- 显示所有企业
- URL 不包含 filter 参数或包含 `?filter=all`

**Step 6: 测试互斥状态**

操作：
1. 选择一个已入库的企业
2. 点击"🗑️ 废弃"按钮
3. 观察状态变化

检查点：
- 企业从"✅ 已入库"变为"🗑️ 已废弃"
- is_imported 状态被清除

**Step 7: 测试批量操作**

操作：
1. 勾选几个未入库的企业
2. 点击"✓ 标记已入库"按钮
3. 观察结果

检查点：
- 被选中的企业变为"✅ 已入库"
- 已废弃的企业无法被勾选

**Step 8: 测试错误处理**

操作：
1. 打开浏览器开发者工具（F12）
2. 切换到 Network 标签
3. 点击"废弃"按钮
4. 观察请求

检查点：
- 请求发送到 `/companies/toggle-discard`
- 响应包含 `{"success": true, "is_discarded": true}`

**Step 9: 验证数据库**

运行: `sqlite3 data/boss_jobs.db "SELECT id, name, is_imported, is_discarded FROM companies LIMIT 5;"`

检查点：
- 查询结果包含 is_discarded 列
- 废弃的企业 is_discarded=1, is_imported=0
- 未废弃的企业 is_discarded=0

**Step 10: 提交测试结果文档**

创建 `docs/plans/2026-03-16-company-discard-testing.md`：

```markdown
# 企业废弃功能测试报告

**测试日期**: 2026-03-16
**测试人员**: [Your Name]

## 测试环境
- 数据库: SQLite
- 浏览器: Chrome/Firefox
- 服务器地址: http://127.0.0.1:5001

## 测试结果

### 数据库迁移测试
- ✅ is_discarded 列添加成功
- ✅ 默认值为 0

### 废弃功能测试
- ✅ 点击"废弃"按钮后状态正确更新
- ✅ 已废弃企业显示红色背景
- ✅ 复选框正确隐藏

### 恢复功能测试
- ✅ 点击"恢复"按钮后状态正确恢复
- ✅ 恢复后显示"未入库"状态
- ✅ 复选框正确显示

### 筛选功能测试
- ✅ "仅已废弃"筛选正确显示
- ✅ "全部"筛选显示所有企业

### 互斥状态测试
- ✅ 已入库企业废弃后取消入库状态
- ✅ 未入库企业废弃后保持未入库状态

### 批量操作测试
- ✅ 已废弃企业无法被批量勾选
- ✅ 批量标记已入库功能正常

## 结论
所有测试通过，功能符合设计要求。
```

提交：
```bash
git add docs/plans/2026-03-16-company-discard-testing.md
git commit -m "test: add discard feature testing report

- Document all test cases and results
- Verify all functionality works as expected

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 完成检查清单

- [ ] 数据库字段已添加
- [ ] 数据库迁移脚本已运行
- [ ] toggle_company_discarded() 方法已实现
- [ ] get_companies_with_import_status() 已修改
- [ ] /companies/toggle-discard 路由已添加
- [ ] 筛选栏已添加"仅已废弃"选项
- [ ] 表格已添加"操作"列
- [ ] 入库状态列支持三种状态显示
- [ ] 复选框逻辑已更新
- [ ] 已废弃行样式已添加
- [ ] toggleDiscardStatus() 函数已实现
- [ ] 所有功能已测试
- [ ] 测试报告已编写
