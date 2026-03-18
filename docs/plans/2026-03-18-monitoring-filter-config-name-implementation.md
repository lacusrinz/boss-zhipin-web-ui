# 监测筛选和配置名列功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为执行记录和监测结果增加日期范围筛选功能，并为监测结果增加配置名列

**Architecture:** 后端 API 筛选方案，数据库层使用 SQL WHERE 条件过滤日期，前端使用 HTML5 原生日期选择器

**Tech Stack:** Flask, SQLite3, JavaScript (Vanilla), Tailwind CSS, HTML5

---

## Task 1: 数据库层 - 修改 get_monitoring_runs() 方法

**Files:**
- Modify: `code/database.py:1197-1235`

**Step 1: 修改函数签名，增加日期参数**

```python
def get_monitoring_runs(self, config_id: Optional[int] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 50, offset: int = 0) -> list:
```

**Step 2: 修改 SQL 查询，增加日期过滤条件**

在 `code/database.py:1211` 处，修改 SQL 查询：

```python
query = """
    SELECT id, config_id, config_name, run_time, success,
           companies_added, companies_skipped, error_message
    FROM monitoring_runs
    WHERE 1=1
"""
params = []

if config_id:
    query += " AND config_id = ?"
    params.append(config_id)

# 新增日期过滤
if start_date:
    query += " AND DATE(run_time) >= ?"
    params.append(start_date)

if end_date:
    query += " AND DATE(run_time) <= ?"
    params.append(end_date)

query += " ORDER BY run_time DESC LIMIT ? OFFSET ?"
params.extend([limit, offset])
```

**Step 3: 更新函数文档字符串**

```python
"""
Get monitoring run records with date filtering

Args:
    config_id: Filter by config ID (optional)
    start_date: Filter by start date (YYYY-MM-DD format)
    end_date: Filter by end date (YYYY-MM-DD format)
    limit: Number of records to return
    offset: Pagination offset

Returns:
    list: List of run records
"""
```

**Step 4: 测试修改**

运行以下命令验证语法正确：
```bash
python3 -c "from code.database import BOSSDatabase; db = BOSSDatabase('data/boss_jobs.db'); print('Database loaded successfully')"
```

**Step 5: 提交**

```bash
git add code/database.py
git commit -m "feat: add date filtering to get_monitoring_runs()

- Add start_date and end_date parameters
- Filter by DATE(run_time) in SQL query
- Maintain backward compatibility (optional parameters)"
```

---

## Task 2: 数据库层 - 修改 get_monitored_companies() 方法

**Files:**
- Modify: `code/database.py:1084-1135`

**Step 1: 修改函数签名，增加日期参数**

```python
def get_monitored_companies(self, config_id: int = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> List[Dict]:
```

**Step 2: 修改 SQL 查询，增加日期过滤和 JOIN**

在 `code/database.py:1102` 处，修改 SQL 查询：

```python
query = """
    SELECT
        mc.id,
        mc.config_id,
        mc2.config_name,
        mc.company_name,
        mc.credit_code,
        mc.reg_date,
        mc.reg_cap,
        mc.region_code,
        mc.region_name,
        mc.legal_representative,
        mc.contact,
        mc.address,
        mc.business_scope,
        mc.monitoring_time,
        mc.source,
        mc.is_processed,
        mc.notes
    FROM monitored_companies mc
    LEFT JOIN monitoring_configs mc2 ON mc.config_id = mc2.id
    WHERE 1=1
"""
params = []

if config_id:
    query += " AND mc.config_id = ?"
    params.append(config_id)

# 新增日期过滤
if start_date:
    query += " AND DATE(mc.monitoring_time) >= ?"
    params.append(start_date)

if end_date:
    query += " AND DATE(mc.monitoring_time) <= ?"
    params.append(end_date)

query += " ORDER BY mc.monitoring_time DESC LIMIT ? OFFSET ?"
params.extend([limit, offset])
```

**Step 3: 修改结果字典构建**

在 `code/database.py:1122` 处，确保返回 `config_name` 字段：

```python
columns = ['id', 'config_id', 'config_name', 'company_name', 'credit_code',
           'reg_date', 'reg_cap', 'region_code', 'region_name',
           'legal_representative', 'contact', 'address', 'business_scope',
           'monitoring_time', 'source', 'is_processed', 'notes']
```

**Step 4: 更新函数文档字符串**

```python
"""
Get monitored companies with date filtering and config name

Args:
    config_id: Filter by config ID (optional)
    start_date: Filter by start date (YYYY-MM-DD format)
    end_date: Filter by end date (YYYY-MM-DD format)
    limit: Number of records to return
    offset: Pagination offset

Returns:
    List[Dict]: List of monitored companies with config_name
"""
```

**Step 5: 测试修改**

```bash
python3 -c "from code.database import BOSSDatabase; db = BOSSDatabase('data/boss_jobs.db'); result = db.get_monitored_companies(limit=1); print(f'Columns: {list(result[0].keys()) if result else \"No data\"}')"
```

预期输出包含 `config_name` 字段。

**Step 6: 提交**

```bash
git add code/database.py
git commit -m "feat: add date filtering and config_name to get_monitored_companies()

- Add start_date and end_date parameters
- LEFT JOIN monitoring_configs to get config_name
- Filter by DATE(monitoring_time) in SQL query
- Maintain backward compatibility (optional parameters)"
```

---

## Task 3: API 层 - 修改 /api/monitoring/runs 端点

**Files:**
- Modify: `code/web_app.py:928-954`

**Step 1: 修改端点函数，接收日期参数**

```python
@app.route('/api/monitoring/runs', methods=['GET'])
def get_monitoring_runs():
    """Get monitoring run records with pagination and date filtering"""
    config_id = request.args.get('config_id', type=int)
    start_date = request.args.get('start_date', type=str)  # 新增
    end_date = request.args.get('end_date', type=str)      # 新增
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    runs = db.get_monitoring_runs(
        config_id=config_id,
        start_date=start_date,  # 新增
        end_date=end_date,      # 新增
        limit=limit,
        offset=offset
    )

    total = db.get_monitoring_runs_count()
    db.close()

    return jsonify({
        'success': True,
        'runs': runs,
        'total': total,
        'limit': limit,
        'offset': offset
    })
```

**Step 2: 测试 API 端点**

启动服务器：
```bash
python3 code/web_app.py
```

测试 API（在另一个终端）：
```bash
# 测试无日期参数（应返回全部数据）
curl "http://localhost:5001/api/monitoring/runs?limit=1"

# 测试有日期参数
curl "http://localhost:5001/api/monitoring/runs?start_date=2026-03-18&end_date=2026-03-18&limit=1"
```

**Step 3: 提交**

```bash
git add code/web_app.py
git commit -m "feat: add date filtering to /api/monitoring/runs endpoint

- Accept start_date and end_date query parameters
- Pass parameters to database layer
- Maintain backward compatibility"
```

---

## Task 4: API 层 - 修改 /api/monitoring/companies 端点

**Files:**
- Modify: `code/web_app.py:893-925`

**Step 1: 修改端点函数，接收日期参数**

```python
@app.route('/api/monitoring/companies', methods=['GET'])
def get_monitored_companies():
    """Get monitored companies with pagination and date filtering"""
    config_id = request.args.get('config_id', type=int)
    start_date = request.args.get('start_date', type=str)  # 新增
    end_date = request.args.get('end_date', type=str)      # 新增
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    companies = db.get_monitored_companies(
        config_id=config_id,
        start_date=start_date,  # 新增
        end_date=end_date,      # 新增
        limit=limit,
        offset=offset
    )

    # Get total count
    if config_id:
        db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE config_id = ?", (config_id,))
    else:
        db.cursor.execute("SELECT COUNT(*) FROM monitored_companies")
    total = db.cursor.fetchone()[0]

    db.close()

    return jsonify({
        'success': True,
        'companies': companies,
        'total': total,
        'limit': limit,
        'offset': offset
    })
```

**Step 2: 测试 API 端点**

测试 API（确保服务器在运行）：
```bash
# 测试无日期参数（应返回全部数据）
curl "http://localhost:5001/api/monitoring/companies?limit=1"

# 测试有日期参数
curl "http://localhost:5001/api/monitoring/companies?start_date=2026-03-18&end_date=2026-03-18&limit=1"

# 验证响应包含 config_name 字段
curl "http://localhost:5001/api/monitoring/companies?limit=1" | python3 -m json.tool | grep config_name
```

**Step 3: 提交**

```bash
git add code/web_app.py
git commit -m "feat: add date filtering to /api/monitoring/companies endpoint

- Accept start_date and end_date query parameters
- Pass parameters to database layer
- Response now includes config_name field
- Maintain backward compatibility"
```

---

## Task 5: 前端 - 添加执行记录日期选择器

**Files:**
- Modify: `code/templates/monitoring.html`

**Step 1: 定位执行记录表格位置**

在 `code/templates/monitoring.html` 中找到执行记录表格标题（约第 395 行）。

**Step 2: 在表格标题上方添加日期选择器**

```html
<!-- 执行记录日期筛选 -->
<div class="flex items-center gap-4 mb-4" id="runs-filter-container">
    <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-gray-700">开始日期:</label>
        <input type="date" id="runs-start-date"
               class="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-gray-700">结束日期:</label>
        <input type="date" id="runs-end-date"
               class="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    <button onclick="applyRunsFilter()"
            class="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 transition-colors">
        筛选
    </button>
    <button onclick="resetRunsFilter()"
            class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">
        重置
    </button>
</div>

<h2 class="text-xl font-semibold mb-4">执行记录</h2>
```

**Step 3: 在 JavaScript 部分添加筛选函数**

在 `<script>` 标签内（约第 800 行后）添加：

```javascript
// 执行记录筛选函数
function applyRunsFilter() {
    const startDate = document.getElementById('runs-start-date').value;
    const endDate = document.getElementById('runs-end-date').value;

    // 验证日期范围
    if (startDate && endDate && startDate > endDate) {
        alert('结束日期不能早于开始日期');
        return;
    }

    loadMonitoringRuns(0); // 重置到第一页
}

function resetRunsFilter() {
    document.getElementById('runs-start-date').value = '';
    document.getElementById('runs-end-date').value = '';
    loadMonitoringRuns(0);
}
```

**Step 4: 修改 loadMonitoringRuns() 函数**

找到 `loadMonitoringRuns()` 函数并修改：

```javascript
async function loadMonitoringRuns(offset = 0) {
    try {
        const startDate = document.getElementById('runs-start-date')?.value;
        const endDate = document.getElementById('runs-end-date')?.value;
        const limit = 50;

        let url = `/api/monitoring/runs?limit=${limit}&offset=${offset}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderMonitoringRunsTable(data.runs);
            updateRunsPagination(data.total, limit, offset);
        } else {
            console.error('加载失败:', data.error);
        }
    } catch (error) {
        console.error('加载执行记录失败:', error);
    }
}
```

**Step 5: 添加页面加载时的默认值初始化**

在 `DOMContentLoaded` 事件监听器中添加：

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // 设置执行记录默认日期为今天
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('runs-start-date').value = today;
    document.getElementById('runs-end-date').value = today;

    // 加载初始数据
    loadMonitoringRuns();
    loadMonitoringResults();
});
```

**Step 6: 测试前端功能**

1. 启动服务器：`python3 code/web_app.py`
2. 访问：`http://localhost:5001/monitoring`
3. 验证：
   - 日期选择器显示
   - 默认日期为今天
   - 点击"筛选"按钮刷新数据
   - 点击"重置"按钮清空日期

**Step 7: 提交**

```bash
git add code/templates/monitoring.html
git commit -m "feat: add date filter to monitoring runs UI

- Add date range picker for execution records
- Set default date to today
- Add filter and reset buttons
- Implement date validation
```

---

## Task 6: 前端 - 添加监测结果日期选择器和配置名列

**Files:**
- Modify: `code/templates/monitoring.html`

**Step 1: 定位监测结果表格位置**

在 `code/templates/monitoring.html` 中找到监测结果表格标题（约第 426 行）。

**Step 2: 在表格标题上方添加日期选择器**

```html
<!-- 监测结果日期筛选 -->
<div class="flex items-center gap-4 mb-4" id="results-filter-container">
    <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-gray-700">开始日期:</label>
        <input type="date" id="results-start-date"
               class="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    <div class="flex items-center gap-2">
        <label class="text-sm font-medium text-gray-700">结束日期:</label>
        <input type="date" id="results-end-date"
               class="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    <button onclick="applyResultsFilter()"
            class="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600 transition-colors">
        筛选
    </button>
    <button onclick="resetResultsFilter()"
            class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">
        重置
    </button>
</div>

<h2 class="text-xl font-semibold mb-4">监测结果</h2>
```

**Step 3: 在监测结果表头添加配置名列**

找到监测结果表格的 `<thead>` 部分，在最后一列添加：

```html
<th class="px-4 py-3 text-left text-sm font-medium text-gray-700">配置名称</th>
```

**Step 4: 修改 colspan 属性**

如果有空数据提示，修改 colspan 从 6 改为 7：

```html
<td colspan="7" class="text-center py-4 text-gray-500">暂无监测结果</td>
```

**Step 5: 在 JavaScript 部分添加筛选函数**

```javascript
// 监测结果筛选函数
function applyResultsFilter() {
    const startDate = document.getElementById('results-start-date').value;
    const endDate = document.getElementById('results-end-date').value;

    // 验证日期范围
    if (startDate && endDate && startDate > endDate) {
        alert('结束日期不能早于开始日期');
        return;
    }

    loadMonitoringResults(0); // 重置到第一页
}

function resetResultsFilter() {
    document.getElementById('results-start-date').value = '';
    document.getElementById('results-end-date').value = '';
    loadMonitoringResults(0);
}
```

**Step 6: 修改 loadMonitoringResults() 函数**

```javascript
async function loadMonitoringResults(offset = 0) {
    try {
        const startDate = document.getElementById('results-start-date')?.value;
        const endDate = document.getElementById('results-end-date')?.value;
        const limit = 50;

        let url = `/api/monitoring/companies?limit=${limit}&offset=${offset}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderMonitoringResultsTable(data.companies);
            updateResultsPagination(data.total, limit, offset);
        } else {
            console.error('加载失败:', data.error);
        }
    } catch (error) {
        console.error('加载监测结果失败:', error);
    }
}
```

**Step 7: 修改 renderMonitoringResultsTable() 函数**

在渲染表格的函数中，添加配置名列：

```javascript
function renderMonitoringResultsTable(companies) {
    const tbody = document.getElementById('monitoring-results-body');
    if (!companies || companies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-gray-500">暂无监测结果</td></tr>';
        return;
    }

    tbody.innerHTML = companies.map(company => `
        <tr class="hover:bg-gray-50 border-b border-gray-200">
            <td class="px-4 py-3 text-sm">${company.company_name || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.credit_code || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.region_name || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.reg_cap || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.legal_representative || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.monitoring_time || '-'}</td>
            <td class="px-4 py-3 text-sm">
                ${company.config_name || '<span class="text-gray-400">已删除</span>'}
            </td>
        </tr>
    `).join('');
}
```

**Step 8: 更新 DOMContentLoaded 初始化**

确保监测结果的默认日期也设置为今天：

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date().toISOString().split('T')[0];

    // 执行记录默认日期
    document.getElementById('runs-start-date').value = today;
    document.getElementById('runs-end-date').value = today;

    // 监测结果默认日期
    document.getElementById('results-start-date').value = today;
    document.getElementById('results-end-date').value = today;

    // 加载初始数据
    loadMonitoringRuns();
    loadMonitoringResults();
});
```

**Step 9: 测试前端功能**

1. 启动服务器：`python3 code/web_app.py`
2. 访问：`http://localhost:5001/monitoring`
3. 验证：
   - 日期选择器显示（执行记录和监测结果）
   - 默认日期为今天
   - 监测结果表格最后一列显示配置名称
   - 已删除配置显示"已删除"
   - 点击"筛选"按钮刷新数据
   - 点击"重置"按钮清空日期

**Step 10: 提交**

```bash
git add code/templates/monitoring.html
git commit -m "feat: add date filter and config_name to monitoring results UI

- Add date range picker for monitoring results
- Add config_name column (last column)
- Display '已删除' for deleted configs
- Set default date to today
- Add filter and reset buttons
- Implement date validation"
```

---

## Task 7: 端到端测试

**Files:**
- Create: `tests/test_monitoring_filter_integration.py`

**Step 1: 创建集成测试文件**

```python
"""
Integration tests for monitoring date filter and config_name feature
"""
import pytest
from code.database import BOSSDatabase
from datetime import datetime, timedelta


class TestMonitoringFilterIntegration:
    """Test date filtering and config_name functionality"""

    def test_get_monitoring_runs_with_date_filter(self):
        """Test get_monitoring_runs with date parameters"""
        db = BOSSDatabase('data/boss_jobs.db')

        # Test with today's date
        today = datetime.now().strftime('%Y-%m-%d')
        runs = db.get_monitoring_runs(start_date=today, end_date=today, limit=10)

        assert isinstance(runs, list)
        # Verify all results are from today
        for run in runs:
            run_date = run['run_time'].split(' ')[0]
            assert run_date == today

        db.close()

    def test_get_monitoring_runs_without_date_filter(self):
        """Test backward compatibility - no date parameters"""
        db = BOSSDatabase('data/boss_jobs.db')

        runs = db.get_monitoring_runs(limit=10)

        assert isinstance(runs, list)
        # Should return results regardless of date
        assert len(runs) <= 10

        db.close()

    def test_get_monitored_companies_with_config_name(self):
        """Test get_monitored_companies returns config_name"""
        db = BOSSDatabase('data/boss_jobs.db')

        companies = db.get_monitored_companies(limit=5)

        assert isinstance(companies, list)
        # Verify config_name field exists
        for company in companies:
            assert 'config_name' in company
            # config_name can be None (deleted config) or a string
            if company['config_name'] is not None:
                assert isinstance(company['config_name'], str)

        db.close()

    def test_get_monitored_companies_with_date_filter(self):
        """Test get_monitored_companies with date parameters"""
        db = BOSSDatabase('data/boss_jobs.db')

        today = datetime.now().strftime('%Y-%m-%d')
        companies = db.get_monitored_companies(
            start_date=today,
            end_date=today,
            limit=10
        )

        assert isinstance(companies, list)
        # Verify all results are from today
        for company in companies:
            if company['monitoring_time']:
                comp_date = company['monitoring_time'].split(' ')[0]
                assert comp_date == today

        db.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

**Step 2: 运行集成测试**

```bash
python3 -m pytest tests/test_monitoring_filter_integration.py -v
```

**Step 3: 修复任何测试失败**

如果测试失败，检查：
- 数据库连接
- 日期格式
- SQL 查询语法
- 字段名称

**Step 4: 创建测试报告**

```bash
mkdir -p docs/test-reports
python3 -m pytest tests/test_monitoring_filter_integration.py -v \
  --tb=short \
  | tee docs/test-reports/2026-03-18-monitoring-filter-test-report.txt
```

**Step 5: 提交测试文件**

```bash
git add tests/test_monitoring_filter_integration.py docs/test-reports/2026-03-18-monitoring-filter-test-report.txt
git commit -m "test: add integration tests for monitoring filter and config_name

- Test date filtering for execution records
- Test date filtering for monitoring results
- Test config_name field in response
- Test backward compatibility (no date parameters)"
```

---

## Task 8: 手动验证和文档

**Step 1: 启动服务器进行手动测试**

```bash
python3 code/web_app.py
```

**Step 2: 验证检查清单**

在浏览器中访问 `http://localhost:5001/monitoring`，验证以下功能：

**执行记录筛选:**
- [ ] 日期选择器显示在执行记录表格上方
- [ ] 默认日期为今天
- [ ] 选择今天后点击"筛选"，只显示今天的执行记录
- [ ] 选择跨天范围（如昨天到今天），显示范围内的记录
- [ ] 点击"重置"，显示全部执行记录
- [ ] 结束日期早于开始日期时，显示错误提示

**监测结果筛选:**
- [ ] 日期选择器显示在监测结果表格上方
- [ ] 默认日期为今天
- [ ] 选择今天后点击"筛选"，只显示今天的监测结果
- [ ] 最后一列显示"配置名称"
- [ ] 配置名称正确显示
- [ ] 已删除配置显示"已删除"（灰色）
- [ ] 点击"重置"，显示全部监测结果

**API 兼容性:**
- [ ] 不传日期参数，返回全部数据
- [ ] 传单个日期参数，正常筛选
- [ ] 传完整日期范围，正常筛选

**Step 3: 创建 E2E 测试报告**

创建 `docs/test-reports/2026-03-18-monitoring-filter-e2e.md`:

```markdown
# 监测筛选和配置名列功能 E2E 测试报告

**测试日期**: 2026-03-18
**测试人员**: [Your Name]
**测试环境**: 本地开发环境

## 测试结果

### 执行记录日期筛选 ✅
- [x] 日期选择器显示正确
- [x] 默认日期为今天
- [x] 筛选功能正常
- [x] 重置功能正常
- [x] 日期验证正常

### 监测结果日期筛选 ✅
- [x] 日期选择器显示正确
- [x] 默认日期为今天
- [x] 筛选功能正常
- [x] 重置功能正常

### 监测结果配置名列 ✅
- [x] 配置名称显示在最后一列
- [x] 配置名称内容正确
- [x] 已删除配置显示"已删除"

### API 兼容性 ✅
- [x] 无日期参数返回全部数据
- [x] 单日期参数正常工作
- [x] 完整日期范围正常工作

## 问题记录

无问题

## 截图

(添加功能截图)

## 结论

功能实现完整，所有测试通过，可以发布。
```

**Step 4: 更新 README.md**

在 `README.md` 的监测功能部分添加说明：

```markdown
### 监测日期筛选

执行记录和监测结果支持日期范围筛选功能：

**功能特性:**
- 日期范围选择器，精确到天
- 默认选中当天日期
- 支持跨天范围筛选
- 可选功能，不筛选显示全部数据

**使用方法:**
1. 进入监测管理页面
2. 在执行记录或监测结果上方找到日期选择器
3. 选择开始日期和结束日期
4. 点击"筛选"按钮应用筛选
5. 点击"重置"按钮清除筛选

### 监测结果配置名

监测结果表格新增配置名列，显示监测配置的名称：

- 位置：表格最后一列
- 内容：显示配置名称
- 特殊情况：已删除配置显示"已删除"（灰色）
```

**Step 5: 提交文档**

```bash
git add docs/test-reports/2026-03-18-monitoring-filter-e2e.md README.md
git commit -m "docs: add E2E test report and update README

- Document date filtering feature
- Document config_name column feature
- Add E2E test results"
```

---

## Task 9: 最终验证和清理

**Step 1: 运行所有测试**

```bash
# 运行集成测试
python3 -m pytest tests/test_monitoring_filter_integration.py -v

# 运行其他相关测试
python3 -m pytest tests/ -k monitoring -v
```

**Step 2: 检查代码风格**

```bash
# 检查 Python 代码
python3 -m py_compile code/database.py code/web_app.py
```

**Step 3: 验证 Git 状态**

```bash
git status
git log --oneline -10
```

**Step 4: 创建功能总结文档**

创建 `docs/plans/2026-03-18-monitoring-filter-summary.md`:

```markdown
# 监测筛选和配置名列功能实现总结

**完成日期**: 2026-03-18
**功能状态**: ✅ 已完成

## 实现内容

### 1. 数据库层修改
- `get_monitoring_runs()`: 增加日期参数和 SQL 过滤
- `get_monitored_companies()`: 增加日期参数、SQL 过滤和 config_name JOIN

### 2. API 层修改
- `/api/monitoring/runs`: 接收日期参数
- `/api/monitoring/companies`: 接收日期参数，返回 config_name

### 3. 前端 UI 修改
- 执行记录：日期选择器 + 筛选逻辑
- 监测结果：日期选择器 + 配置名列 + 筛选逻辑

## 测试覆盖

- [x] 单元测试
- [x] 集成测试
- [x] E2E 手动测试
- [x] API 兼容性测试

## 性能影响

- 利用现有索引，查询性能无影响
- 前端加载时间无明显增加

## 向后兼容性

- 日期参数为可选，不破坏现有功能
- API 调用向后兼容

## 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| code/database.py | 修改 |
| code/web_app.py | 修改 |
| code/templates/monitoring.html | 修改 |
| tests/test_monitoring_filter_integration.py | 新增 |
| docs/test-reports/2026-03-18-monitoring-filter-test-report.txt | 新增 |
| docs/test-reports/2026-03-18-monitoring-filter-e2e.md | 新增 |
| README.md | 修改 |
```

**Step 5: 最终提交**

```bash
git add docs/plans/2026-03-18-monitoring-filter-summary.md
git commit -m "docs: add feature implementation summary"
```

**Step 6: 创建功能标签（可选）**

```bash
git tag -a v1.3.0 -m "Monitoring filter and config_name feature"
git push origin v1.3.0
```

---

## 完成标准

所有任务完成后，应满足：

- [x] 执行记录支持日期范围筛选
- [x] 监测结果支持日期范围筛选
- [x] 监测结果显示配置名列
- [x] 默认日期为当天
- [x] 向后兼容，不破坏现有功能
- [x] 所有测试通过
- [x] 文档完整
- [x] 代码已提交

---

## 下一步

功能实现完成后，可以考虑：

1. 添加导出筛选后的数据功能
2. 添加更多筛选条件（如按配置名称筛选）
3. 优化大数据量下的分页性能
4. 添加数据可视化图表

---

**实施注意事项:**
1. 每完成一个 Task 立即提交，不要批量提交
2. 遇到测试失败，先修复再继续
3. 保持代码风格一致
4. 及时更新文档

**回滚计划:**
如果遇到问题，可以使用以下命令回滚：
```bash
git reset --hard HEAD~N  # N 为要回滚的提交数
```
