# 企业监测任务时间范围功能设计

**日期：** 2026-03-18
**状态：** 设计阶段
**优先级：** 中

## 需求概述

为企业的监测任务添加时间范围控制功能，允许用户设置监测任务只在特定时间段内执行（如 09:00-18:00），避免在非工作时间调用 API，节省资源并提高效率。

## 功能需求

### 核心需求

1. **时间范围设置**
   - 精确到分钟（如 10:00-17:30）
   - 可选字段，不设置则全天24小时执行
   - 默认工作时间：09:00-18:00
   - 不支持跨天（开始时间必须小于结束时间）

2. **执行行为**
   - 在时间范围内：按设定间隔正常执行
   - 在时间范围外：跳过执行，不调用 API

3. **时区要求**
   - 所有时间统一使用北京时间（Asia/Shanghai）
   - 日志、数据库记录、前端显示均需标注时区

## 技术架构

### 1. 数据库架构

#### monitoring_configs 表新增字段

```sql
ALTER TABLE monitoring_configs
ADD COLUMN monitoring_start_time TEXT DEFAULT '09:00';

ALTER TABLE monitoring_configs
ADD COLUMN monitoring_end_time TEXT DEFAULT '18:00';
```

**字段说明：**
- `monitoring_start_time`: 开始时间，格式 HH:MM，允许 NULL
- `monitoring_end_time`: 结束时间，格式 HH:MM，允许 NULL
- NULL 值表示全天24小时执行

**数据验证：**
- 时间格式：`^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$`
- 不支持跨天：`start_time < end_time`

### 2. 调度器修改

#### 文件：`code/web_app.py`

**新增时间范围检查函数：**

```python
import pytz
from datetime import datetime

def is_within_monitoring_hours(start_time: str, end_time: str) -> bool:
    """
    检查当前时间是否在监测时间范围内（北京时间）

    Args:
        start_time: 开始时间字符串 HH:MM，None 表示无限制
        end_time: 结束时间字符串 HH:MM，None 表示无限制

    Returns:
        bool: True 表示在范围内，False 表示在范围外
    """
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    current_time = now.strftime('%H:%M')

    # 无时间限制
    if not start_time or not end_time:
        return True

    # 检查是否在范围内
    return start_time <= current_time <= end_time
```

**修改 `run_monitoring_task_wrapper` 函数：**

```python
def run_monitoring_task_wrapper(config_id: int):
    """执行监测任务包装函数（增加时间范围检查）"""
    from riskbird_monitor import RiskBirdMonitor

    job_id = f'monitoring_{config_id}'
    db = get_db()

    if db.conn:
        try:
            # 获取配置
            config = db.get_monitoring_config(config_id)
            if not config:
                logging.error(f"Config {config_id} not found")
                return

            # 检查时间范围
            start_time = config.get('monitoring_start_time')
            end_time = config.get('monitoring_end_time')

            if not is_within_monitoring_hours(start_time, end_time):
                beijing_now = datetime.now(pytz.timezone('Asia/Shanghai'))
                logging.info(
                    f"[{beijing_now.strftime('%Y-%m-%d %H:%M:%S +08:00')}] "
                    f"Job {job_id} skipped (outside time range {start_time}-{end_time})"
                )
                return

            # 执行监测任务
            monitor = RiskBirdMonitor(db)
            result = monitor.run_monitoring_task(config_id)

            # 记录执行结果
            config_name = config['config_name']
            db.insert_monitoring_run(
                config_id=config_id,
                config_name=config_name,
                success=result['success'],
                companies_added=result['companies_added'],
                companies_skipped=result['companies_skipped'],
                error_message=result.get('error')
            )
        finally:
            db.close()
```

### 3. API 接口修改

#### 创建配置接口

**路由：** `POST /api/monitoring/configs`

**新增参数：**
```json
{
  "config_name": "北京地区监测",
  "region_codes": ["110000"],
  "interval_minutes": 5,
  "reg_cap": "",
  "monitoring_start_time": "09:00",  // 可选，默认 "09:00"
  "monitoring_end_time": "18:00"      // 可选，默认 "18:00"
}
```

**验证逻辑：**
```python
def validate_time_format(time_str: str) -> bool:
    """验证时间格式 HH:MM"""
    if not time_str:
        return True
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def validate_time_range(start: str, end: str) -> bool:
    """验证时间范围（不支持跨天）"""
    if not start or not end:
        return True
    return start < end

# 在 create_monitoring_config 中添加验证
start_time = data.get('monitoring_start_time', '09:00')
end_time = data.get('monitoring_end_time', '18:00')

if not validate_time_format(start_time) or not validate_time_format(end_time):
    return jsonify({'success': False, 'error': '时间格式错误，应为 HH:MM'}), 400

if not validate_time_range(start_time, end_time):
    return jsonify({'success': False, 'error': '开始时间必须小于结束时间'}), 400
```

#### 更新配置接口

**路由：** `PUT /api/monitoring/configs/<int:config_id>`

**支持更新时间范围，并重启调度器任务**

### 4. 数据库层修改

#### 文件：`code/database.py`

**修改 `insert_monitoring_config` 函数：**

```python
def insert_monitoring_config(
    self,
    config_name: str,
    region_codes: str,
    interval_minutes: int,
    reg_cap: str = None,
    monitoring_start_time: str = '09:00',
    monitoring_end_time: str = '18:00'
) -> Optional[int]:
    """
    插入监测配置

    Args:
        config_name: 配置名称
        region_codes: 地区代码 JSON 字符串
        interval_minutes: 监测间隔（分钟）
        reg_cap: 注册资本（可选）
        monitoring_start_time: 监测开始时间 HH:MM（可选）
        monitoring_end_time: 监测结束时间 HH:MM（可选）

    Returns:
        插入的配置 ID，失败返回 None
    """
    try:
        self.cursor.execute('''
            INSERT INTO monitoring_configs (
                config_name, region_codes, interval_minutes, reg_cap,
                monitoring_start_time, monitoring_end_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (
            config_name, region_codes, interval_minutes, reg_cap,
            monitoring_start_time, monitoring_end_time
        ))
        self.conn.commit()
        return self.cursor.lastrowid
    except Exception as e:
        self.logger.error(f"Failed to insert monitoring config: {e}")
        return None
```

**修改 `update_monitoring_config` 函数：**

```python
def update_monitoring_config(self, config_id: int, **updates) -> bool:
    """
    更新监测配置

    Args:
        config_id: 配置 ID
        **updates: 要更新的字段

    Returns:
        更新成功返回 True，失败返回 False
    """
    # ... 实现支持 monitoring_start_time 和 monitoring_end_time
```

**修改 `get_monitoring_config` 函数：**

返回结果中包含新字段：
```python
return {
    'id': row[0],
    'config_name': row[1],
    # ... 其他字段
    'monitoring_start_time': row[8],  # 新增
    'monitoring_end_time': row[9],    # 新增
}
```

### 5. 前端 UI 修改

#### 文件：`templates/monitoring.html`

**新增表单控件：**

```html
<div class="form-group">
    <label for="monitoring-time-range">
        监测时间范围（可选）
    </label>
    <div class="time-range-inputs">
        <input type="time"
               id="monitoring-start-time"
               name="monitoring_start_time"
               value="09:00"
               min="00:00"
               max="23:59"
               title="开始时间">
        <span>至</span>
        <input type="time"
               id="monitoring-end-time"
               name="monitoring_end_time"
               value="18:00"
               min="00:00"
               max="23:59"
               title="结束时间">
    </div>
    <small class="form-text text-muted">
        仅在设定时间范围内执行监测任务（精确到分钟）。
        不设置则全天24小时执行。默认工作时间：09:00-18:00
    </small>
</div>

<style>
.time-range-inputs {
    display: flex;
    align-items: center;
    gap: 10px;
}

.time-range-inputs input {
    flex: 1;
    max-width: 150px;
}

.time-range-inputs span {
    color: #6c757d;
}
</style>
```

**JavaScript 验证：**

```javascript
function validateTimeRange() {
    const startTime = document.getElementById('monitoring-start-time').value;
    const endTime = document.getElementById('monitoring-end-time').value;

    if (startTime && endTime && startTime >= endTime) {
        alert('开始时间必须小于结束时间（不支持跨天）');
        return false;
    }

    return true;
}

// 在表单提交前调用
document.getElementById('create-config-form').addEventListener('submit', function(e) {
    if (!validateTimeRange()) {
        e.preventDefault();
    }
});
```

**配置列表显示：**

在配置卡片中显示时间范围：
```html
<div class="config-detail">
    <span class="label">监测时段:</span>
    <span class="value">
        {{ config.monitoring_start_time || '--:--' }} -
        {{ config.monitoring_end_time || '--:--' }}
    </span>
</div>
```

### 6. 日志与监控

#### 日志格式化

```python
import pytz
from datetime import datetime

def get_beijing_time_str() -> str:
    """获取格式化的北京时间字符串"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    return now.strftime('%Y-%m-%d %H:%M:%S +08:00')

# 使用示例
logging.info(f"[{get_beijing_time_str()}] Job monitoring_1 started")
logging.info(f"[{get_beijing_time_str()}] Job monitoring_1 skipped (outside time range)")
```

#### 监测运行记录

在 `monitoring_runs` 表中记录时添加时区信息：
- `executed_at` 字段存储时带时区标识
- 前端显示时格式化为：`2026-03-18 14:30:00 (北京时间)`

## 测试计划

### 单元测试

**文件：** `tests/test_monitoring_time_range.py`

1. **时间格式验证**
   - 测试有效格式：09:00, 18:30, 00:00, 23:59
   - 测试无效格式：25:00, 9:00, abc, NULL

2. **时间范围逻辑**
   - 测试正常范围：09:00 < 18:00 ✓
   - 测试跨天拒绝：22:00 >= 02:00 ✗
   - 测试相等时间：10:00 >= 10:00 ✗

3. **时区检查函数**
   - 测试北京时间获取
   - 测试时间范围判断

### 集成测试

1. **创建配置**
   - 使用默认时间范围创建
   - 使用自定义时间范围创建
   - 使用无效时间范围创建（应失败）

2. **调度器行为**
   - 在时间范围内：任务正常执行
   - 在时间范围外：任务被跳过
   - 边界时间测试

3. **配置更新**
   - 更新时间范围后调度器行为变化
   - 从全天变为限时
   - 从限时变为全天

4. **数据库记录**
   - 验证时间字段正确存储
   - 验证时区信息正确记录

### 手动测试场景

1. **场景一：工作时间监测**
   - 设置 09:00-18:00
   - 08:59 检查：任务应跳过
   - 09:00 检查：任务应执行
   - 18:01 检查：任务应跳过

2. **场景二：全天监测**
   - 时间范围设为 NULL
   - 任何时间都应执行

3. **场景三：更新时间范围**
   - 创建配置 09:00-18:00
   - 更新为 10:00-17:00
   - 09:30 检查：任务应跳过
   - 10:30 检查：任务应执行

## 部署计划

### 1. 数据库迁移

```sql
-- 添加新字段（允许现有配置使用默认值）
ALTER TABLE monitoring_configs
ADD COLUMN monitoring_start_time TEXT DEFAULT '09:00';

ALTER TABLE monitoring_configs
ADD COLUMN monitoring_end_time TEXT DEFAULT '18:00';

-- 验证字段已添加
SELECT id, config_name, monitoring_start_time, monitoring_end_time
FROM monitoring_configs;
```

### 2. 代码部署顺序

1. 更新 `code/database.py` - 数据库层
2. 更新 `code/web_app.py` - API 和调度器
3. 更新 `templates/monitoring.html` - 前端 UI
4. 添加 `tests/test_monitoring_time_range.py` - 测试

### 3. 回滚计划

如果出现问题：
1. 数据库：删除新增列 `ALTER TABLE monitoring_configs DROP COLUMN ...`
2. 代码：Git revert 到之前版本
3. 调度器：重启服务

## 依赖项

- Python: `pytz` （时区处理，可能已存在）
- 前端: 原生 HTML5 `<input type="time">` 支持

## 注意事项

1. **时区一致性**：确保所有时间操作使用 `Asia/Shanghai` 时区
2. **向后兼容**：现有配置自动使用默认值 09:00-18:00
3. **性能影响**：时间检查操作轻量，对性能影响可忽略
4. **用户沟通**：前端提示清楚说明时间范围的作用和默认值
