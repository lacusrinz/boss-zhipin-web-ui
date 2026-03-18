# 监测功能增强设计文档

**日期**: 2026-03-18
**功能**: 执行记录和监测结果增加日期筛选 + 监测结果增加配置名列
**方案**: 后端 API 筛选（方案 B）

---

## 需求概述

### 功能需求

1. **执行记录页面**：增加日期范围筛选功能，默认选中当天
2. **监测结果页面**：
   - 增加日期范围筛选功能，默认选中当天
   - 增加配置名列（显示配置名称），放在最后一列

### 用户故事

作为用户，我希望能够：
- 按日期范围查看执行记录，快速定位特定时间段的监测情况
- 按日期范围查看监测结果，筛选出特定时间的数据
- 在监测结果中直接看到是哪个配置监测的，无需切换页面查看

---

## 技术方案

### 方案选择：后端 API 筛选

**选择理由：**
1. **性能考虑**：监测功能可能积累大量数据，前端筛选会越来越慢
2. **扩展性**：后续可能需要导出筛选后的数据，后端筛选更灵活
3. **用户体验**：加载速度更快，界面响应更流畅
4. **最佳实践**：数据筛选应该在数据库层面完成

---

## 架构设计

### 整体架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   前端 UI       │     │   后端 API      │     │   数据库层      │
│                 │     │                 │     │                 │
│ - 日期选择器    │────▶│ - 接收日期参数  │────▶│ - SQL WHERE过滤 │
│ - 表格展示      │     │ - 参数验证      │     │ - JOIN获取配置名│
│ - 默认今天      │     │ - 调用数据库    │     │ - 索引优化      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 数据流

1. **用户选择日期** → 前端获取 `start_date` 和 `end_date`
2. **前端调用 API** → 传递日期参数：`/api/monitoring/runs?start_date=2026-03-18&end_date=2026-03-18`
3. **后端接收参数** → 验证格式（可选），传递给数据库层
4. **数据库查询** → 使用 `DATE()` 函数和索引进行日期筛选
5. **返回结果** → 前端渲染表格

---

## API 设计

### 1. 执行记录 API

**端点**: `GET /api/monitoring/runs`

**新增参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| start_date | string | 否 | 开始日期 (YYYY-MM-DD) | 2026-03-18 |
| end_date | string | 否 | 结束日期 (YYYY-MM-DD) | 2026-03-18 |

**请求示例**:
```http
GET /api/monitoring/runs?start_date=2026-03-18&end_date=2026-03-18&limit=50&offset=0
```

**响应示例**:
```json
{
  "success": true,
  "runs": [
    {
      "id": 1,
      "config_id": 1,
      "config_name": "苏州企业监测",
      "run_time": "2026-03-18 10:30:00",
      "success": true,
      "companies_added": 5,
      "companies_skipped": 2,
      "error_message": null
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### 2. 监测结果 API

**端点**: `GET /api/monitoring/companies`

**新增参数**:
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| start_date | string | 否 | 开始日期 (YYYY-MM-DD) | 2026-03-18 |
| end_date | string | 否 | 结束日期 (YYYY-MM-DD) | 2026-03-18 |

**响应新增字段**:
| 字段 | 类型 | 说明 |
|------|------|------|
| config_name | string | 配置名称（可能为 null） |

**请求示例**:
```http
GET /api/monitoring/companies?start_date=2026-03-18&end_date=2026-03-18&limit=50&offset=0
```

**响应示例**:
```json
{
  "success": true,
  "companies": [
    {
      "id": 1,
      "config_id": 1,
      "config_name": "苏州企业监测",
      "company_name": "某某科技有限公司",
      "credit_code": "91320500MA1XXXXXX",
      "monitoring_time": "2026-03-18 10:30:00",
      "region_name": "江苏省",
      "reg_cap": "1000万人民币",
      "legal_representative": "张三"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

## 数据库层设计

### 1. get_monitoring_runs() 方法

**修改前**:
```python
def get_monitoring_runs(self, config_id: Optional[int] = None,
                       limit: int = 50, offset: int = 0) -> list:
```

**修改后**:
```python
def get_monitoring_runs(self, config_id: Optional[int] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 50, offset: int = 0) -> list:
    """
    Get monitoring run records with date filtering

    Args:
        config_id: Filter by config ID (optional)
        start_date: Filter by start date (YYYY-MM-DD format)
        end_date: Filter by end date (YYYY-MM-DD format)
        limit: Number of records to return
        offset: Pagination offset
    """
```

**SQL 查询**:
```sql
SELECT id, config_id, config_name, run_time, success,
       companies_added, companies_skipped, error_message
FROM monitoring_runs
WHERE 1=1
  AND (:config_id IS NULL OR config_id = :config_id)
  AND (:start_date IS NULL OR DATE(run_time) >= :start_date)
  AND (:end_date IS NULL OR DATE(run_time) <= :end_date)
ORDER BY run_time DESC
LIMIT ? OFFSET ?
```

### 2. get_monitored_companies() 方法

**修改前**:
```python
def get_monitored_companies(self, config_id: int = None,
                           limit: int = 100, offset: int = 0) -> List[Dict]:
```

**修改后**:
```python
def get_monitored_companies(self, config_id: int = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Get monitored companies with date filtering

    Args:
        config_id: Filter by config ID (optional)
        start_date: Filter by start date (YYYY-MM-DD format)
        end_date: Filter by end date (YYYY-MM-DD format)
        limit: Number of records to return
        offset: Pagination offset
    """
```

**SQL 查询**:
```sql
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
  AND (:config_id IS NULL OR mc.config_id = :config_id)
  AND (:start_date IS NULL OR DATE(mc.monitoring_time) >= :start_date)
  AND (:end_date IS NULL OR DATE(mc.monitoring_time) <= :end_date)
ORDER BY mc.monitoring_time DESC
LIMIT ? OFFSET ?
```

### 索引利用

现有索引（已存在，无需创建）:
- `idx_monitoring_time`: `monitoring_time` 字段
- `idx_config_time`: `(config_id, monitoring_time)` 组合索引

这些索引会被日期筛选查询自动利用，保证查询性能。

---

## 前端设计

### UI 组件

#### 1. 日期选择器组件

**位置**:
- 执行记录表格上方
- 监测结果表格上方

**HTML 结构**:
```html
<!-- 执行记录日期筛选 -->
<div class="flex items-center gap-4 mb-4">
  <div class="flex items-center gap-2">
    <label class="text-sm font-medium">开始日期:</label>
    <input type="date" id="runs-start-date"
           class="border rounded px-3 py-2 text-sm">
  </div>
  <div class="flex items-center gap-2">
    <label class="text-sm font-medium">结束日期:</label>
    <input type="date" id="runs-end-date"
           class="border rounded px-3 py-2 text-sm">
  </div>
  <button onclick="applyRunsFilter()"
          class="bg-blue-500 text-white px-4 py-2 rounded text-sm hover:bg-blue-600">
    筛选
  </button>
  <button onclick="resetRunsFilter()"
          class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300">
    重置
  </button>
</div>

<!-- 监测结果日期筛选（类似） -->
<div class="flex items-center gap-4 mb-4">
  <!-- 相同结构，ID 改为 results-start-date / results-end-date -->
</div>
```

#### 2. 监测结果表格新增列

**表头**:
```html
<thead>
  <tr class="bg-gray-50">
    <!-- 现有列... -->
    <th class="px-4 py-3 text-left text-sm font-medium">配置名称</th>
  </tr>
</thead>
```

**表格数据行**:
```html
<td class="px-4 py-3 text-sm">
  ${company.config_name || '<span class="text-gray-400">已删除</span>'}
</td>
```

### JavaScript 逻辑

#### 1. 初始化默认值

```javascript
// 页面加载时设置默认值为今天
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('runs-start-date').value = today;
    document.getElementById('runs-end-date').value = today;
    document.getElementById('results-start-date').value = today;
    document.getElementById('results-end-date').value = today;

    // 自动触发筛选
    loadMonitoringRuns();
    loadMonitoringResults();
});
```

#### 2. 筛选函数

```javascript
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

// 监测结果类似
function applyResultsFilter() { /* 同上逻辑 */ }
function resetResultsFilter() { /* 同上逻辑 */ }
```

#### 3. 加载数据函数

```javascript
async function loadMonitoringRuns(offset = 0) {
    const startDate = document.getElementById('runs-start-date')?.value;
    const endDate = document.getElementById('runs-end-date')?.value;
    const limit = 50;

    let url = `/api/monitoring/runs?limit=${limit}&offset=${offset}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderMonitoringRunsTable(data.runs);
            updatePagination(data.total, limit, offset, 'loadMonitoringRuns');
        }
    } catch (error) {
        console.error('加载执行记录失败:', error);
    }
}

async function loadMonitoringResults(offset = 0) {
    const startDate = document.getElementById('results-start-date')?.value;
    const endDate = document.getElementById('results-end-date')?.value;
    const limit = 50;

    let url = `/api/monitoring/companies?limit=${limit}&offset=${offset}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderMonitoringResultsTable(data.companies);
            updatePagination(data.total, limit, offset, 'loadMonitoringResults');
        }
    } catch (error) {
        console.error('加载监测结果失败:', error);
    }
}

function renderMonitoringResultsTable(companies) {
    const tbody = document.getElementById('monitoring-results-body');
    if (!companies || companies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-gray-500">暂无监测结果</td></tr>';
        return;
    }

    tbody.innerHTML = companies.map(company => `
        <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 text-sm">${company.company_name}</td>
            <td class="px-4 py-3 text-sm">${company.credit_code || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.region_name || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.reg_cap || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.legal_representative || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.monitoring_time || '-'}</td>
            <td class="px-4 py-3 text-sm">${company.source || '-'}</td>
            <td class="px-4 py-3 text-sm">
                ${company.config_name || '<span class="text-gray-400">已删除</span>'}
            </td>
        </tr>
    `).join('');
}
```

---

## 错误处理和边界情况

### 1. 日期范围验证

**前端验证**:
```javascript
if (startDate && endDate && startDate > endDate) {
    alert('结束日期不能早于开始日期');
    return;
}
```

**后端处理**:
- 日期参数为可选，不传则返回全部数据
- 日期格式由 HTML5 date input 保证正确性（YYYY-MM-DD）

### 2. 时区处理

- **数据存储**: `run_time` 和 `monitoring_time` 已存储为北京时间
- **日期比较**: SQL 使用 `DATE()` 函数提取日期部分，避免时间部分干扰
- **一致性**: 前端和后端都使用相同日期格式

### 3. 空值处理

| 场景 | 处理方式 |
|------|----------|
| config_name 为 null | 显示 `<span class="text-gray-400">已删除</span>` |
| 日期参数为空 | 返回全部数据（向后兼容） |
| 无筛选结果 | 显示 "暂无数据" 提示 |

### 4. 性能考虑

| 操作 | 索引使用 |
|------|----------|
| 日期筛选 | `idx_monitoring_time` |
| 配置+日期筛选 | `idx_config_time` |
| 配置名称 JOIN | 主键索引（自动） |

---

## 向后兼容性

### API 兼容

- 日期参数为**可选参数**
- 不传日期参数时，行为与之前完全一致
- 现有 API 调用无需修改

### 前端兼容

- 新增的日期选择器不影响现有功能
- 用户可以选择不使用筛选功能

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `code/database.py` | `get_monitoring_runs()` 增加日期参数<br>`get_monitored_companies()` 增加日期参数和 JOIN |
| `code/web_app.py` | `/api/monitoring/runs` 增加日期参数传递<br>`/api/monitoring/companies` 增加日期参数传递 |
| `code/templates/monitoring.html` | 增加日期选择器 UI<br>增加配置名列<br>修改 JavaScript 加载逻辑 |

---

## 测试计划

### 单元测试

1. **数据库层测试**
   - 测试无日期参数时返回全部数据
   - 测试只有 start_date 时的筛选
   - 测试只有 end_date 时的筛选
   - 测试完整日期范围的筛选
   - 测试 config_name 字段正确返回

2. **API 层测试**
   - 测试参数正确传递到数据库层
   - 测试可选参数的默认行为
   - 测试响应格式正确性

### 集成测试

1. **前端 UI 测试**
   - 测试默认日期设置为今天
   - 测试日期选择器交互
   - 测试筛选按钮功能
   - 测试重置按钮功能
   - 测试日期范围验证（结束日期早于开始日期）

2. **端到端测试**
   - 测试完整的筛选流程
   - 测试跨日期的筛选
   - 测试配置名列显示
   - 测试配置删除后的显示

### 边界测试

| 测试场景 | 预期结果 |
|----------|----------|
| 筛选无数据的日期 | 显示"暂无数据" |
| 选择相同日期 | 只显示当天数据 |
| 跨日期筛选 | 显示范围内所有数据 |
| 不选日期直接筛选 | 显示全部数据 |
| 删除配置后查看结果 | config_name 显示"已删除" |

---

## 实施计划

### 阶段划分

**阶段 1: 数据库层** (预计修改点: 2 处)
1. 修改 `get_monitoring_runs()` 方法
2. 修改 `get_monitored_companies()` 方法

**阶段 2: API 层** (预计修改点: 2 处)
1. 修改 `/api/monitoring/runs` 端点
2. 修改 `/api/monitoring/companies` 端点

**阶段 3: 前端 UI** (预计修改点: 1 处)
1. 修改 `monitoring.html` 模板

**阶段 4: 测试验证**
1. 单元测试
2. 集成测试
3. 手动验证

### 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| SQL 查询性能 | 中 | 已有索引，影响较小 |
| 日期时区问题 | 低 | 统一使用北京时间 |
| 向后兼容性 | 低 | 参数为可选，不破坏现有功能 |
| 配置删除处理 | 低 | 前端显示"已删除" |

---

## 验收标准

### 功能验收

- [ ] 执行记录页面显示日期选择器
- [ ] 监测结果页面显示日期选择器
- [ ] 默认日期设置为今天
- [ ] 点击筛选按钮后数据正确过滤
- [ ] 点击重置按钮后显示全部数据
- [ ] 监测结果表格最后一列显示配置名称
- [ ] 已删除配置显示"已删除"

### 性能验收

- [ ] 日期筛选查询时间 < 1 秒（1000 条数据）
- [ ] 页面加载时间无明显增加
- [ ] 筛选操作响应流畅

### 兼容性验收

- [ ] 现有功能不受影响
- [ ] API 调用向后兼容
- [ ] 浏览器兼容性（Chrome, Firefox, Safari）

---

## 总结

本设计通过后端 API 筛选的方式，为执行记录和监测结果增加了日期范围筛选功能，并为监测结果增加了配置名列。方案考虑了性能、扩展性、用户体验和向后兼容性，预计实现简单、风险可控。

**主要优势**:
1. 性能优化：数据库层筛选，利用现有索引
2. 用户友好：默认今天，操作简单直观
3. 信息完整：配置名列让用户无需切换页面
4. 向后兼容：不破坏现有功能

**下一步**:
进入实施计划阶段，创建详细的实现计划文档。
