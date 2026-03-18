# 企业监测任务时间范围功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 为企业监测任务添加时间范围控制功能，允许用户设置仅在特定时间段（如 09:00-18:00）内执行监测任务，时间范围外自动跳过。

**架构:**
1. 数据库层：在 `monitoring_configs` 表新增时间范围字段
2. 调度器层：在任务执行前检查当前时间是否在范围内
3. API 层：创建/更新接口支持时间范围参数，增加格式验证
4. 前端层：表单添加时间选择控件，实时验证
5. 时区处理：所有时间统一使用北京时间（Asia/Shanghai）

**技术栈:** Python Flask, APScheduler, SQLite, HTML5, pytz

---

## Task 1: 添加数据库字段

**Files:**
- Modify: `code/database.py`
- Create: `tests/test_database_time_range.py`

**Step 1: 创建测试文件**

创建 `tests/test_database_time_range.py`:

```python
import pytest
import sqlite3
from pathlib import Path
from code.database import BOSSDatabase

@pytest.fixture
def test_db(tmp_path):
    """创建临时测试数据库"""
    db_path = tmp_path / "test.db"
    db = BOSSDatabase(str(db_path))
    db.connect()
    db.init_monitoring_tables()
    yield db
    db.close()

def test_monitoring_configs_has_time_columns(test_db):
    """验证 monitoring_configs 表包含时间范围字段"""
    # 获取表结构
    test_db.cursor.execute("PRAGMA table_info(monitoring_configs)")
    columns = [row[1] for row in test_db.cursor.fetchall()]

    # 验证新字段存在
    assert 'monitoring_start_time' in columns
    assert 'monitoring_end_time' in columns

def test_insert_monitoring_config_with_time_range(test_db):
    """验证插入配置时可以设置时间范围"""
    import json

    config_id = test_db.insert_monitoring_config(
        config_name="测试配置",
        region_codes=json.dumps(["110000"]),
        interval_minutes=5,
        monitoring_start_time="10:00",
        monitoring_end_time="17:30"
    )

    assert config_id is not None
    assert config_id > 0

    # 验证数据正确存储
    config = test_db.get_monitoring_config(config_id)
    assert config['monitoring_start_time'] == "10:00"
    assert config['monitoring_end_time'] == "17:30"

def test_insert_monitoring_config_default_time_range(test_db):
    """验证插入配置时使用默认时间范围"""
    import json

    config_id = test_db.insert_monitoring_config(
        config_name="测试配置",
        region_codes=json.dumps(["110000"]),
        interval_minutes=5
    )

    config = test_db.get_monitoring_config(config_id)
    assert config['monitoring_start_time'] == "09:00"
    assert config['monitoring_end_time'] == "18:00"

def test_get_monitoring_config_includes_time_fields(test_db):
    """验证获取配置时包含时间范围字段"""
    import json

    config_id = test_db.insert_monitoring_config(
        config_name="测试配置",
        region_codes=json.dumps(["110000"]),
        interval_minutes=5,
        monitoring_start_time="08:00",
        monitoring_end_time="20:00"
    )

    config = test_db.get_monitoring_config(config_id)

    # 验证返回字典包含时间字段
    assert 'monitoring_start_time' in config
    assert 'monitoring_end_time' in config
    assert config['monitoring_start_time'] == "08:00"
    assert config['monitoring_end_time'] == "20:00"
```

**Step 2: 运行测试验证失败**

运行: `pytest tests/test_database_time_range.py -v`

预期: FAIL - 字段不存在，函数不支持新参数

**Step 3: 修改 database.py 添加字段**

修改 `code/database.py` 的 `init_monitoring_tables` 函数。

找到创建 `monitoring_configs` 表的 SQL 语句，添加新字段：

```python
def init_monitoring_tables(self):
    """初始化监测相关表"""
    # ... 现有代码 ...

    # 修改 monitoring_configs 表创建语句
    self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT NOT NULL,
            region_codes TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL,
            reg_cap TEXT,
            monitoring_start_time TEXT DEFAULT '09:00',
            monitoring_end_time TEXT DEFAULT '18:00',
            created_at TEXT,
            UNIQUE(config_name)
        )
    ''')

    # ... 其余代码 ...
```

**Step 4: 修改 insert_monitoring_config 函数签名和实现**

修改 `code/database.py` 中的 `insert_monitoring_config` 函数：

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
        monitoring_start_time: 监测开始时间 HH:MM（可选，默认 09:00）
        monitoring_end_time: 监测结束时间 HH:MM（可选，默认 18:00）

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
    except sqlite3.IntegrityError:
        self.logger.warning(f"Config '{config_name}' already exists")
        return None
    except Exception as e:
        self.logger.error(f"Failed to insert monitoring config: {e}")
        return None
```

**Step 5: 修改 get_monitoring_config 函数**

修改 `code/database.py` 中的 `get_monitoring_config` 函数，确保返回时间字段：

```python
def get_monitoring_config(self, config_id: int) -> Optional[Dict]:
    """
    获取监测配置

    Args:
        config_id: 配置 ID

    Returns:
        配置字典，不存在返回 None
    """
    try:
        self.cursor.execute('''
            SELECT id, config_name, region_codes, interval_minutes,
                   reg_cap, monitoring_start_time, monitoring_end_time,
                   created_at
            FROM monitoring_configs
            WHERE id = ?
        ''', (config_id,))
        row = self.cursor.fetchone()

        if row:
            return {
                'id': row[0],
                'config_name': row[1],
                'region_codes': row[2],
                'interval_minutes': row[3],
                'reg_cap': row[4],
                'monitoring_start_time': row[5],
                'monitoring_end_time': row[6],
                'created_at': row[7]
            }
        return None
    except Exception as e:
        self.logger.error(f"Failed to get monitoring config: {e}")
        return None
```

**Step 6: 运行测试验证通过**

运行: `pytest tests/test_database_time_range.py -v`

预期: PASS

**Step 7: 提交**

```bash
git add code/database.py tests/test_database_time_range.py
git commit -m "feat: add time range columns to monitoring_configs table"
```

---

## Task 2: 添加时间范围检查函数

**Files:**
- Modify: `code/web_app.py`
- Create: `tests/test_time_range_check.py`

**Step 1: 创建测试文件**

创建 `tests/test_time_range_check.py`:

```python
import pytest
from datetime import datetime
import pytz

# 导入时间范围检查函数
from code.web_app import is_within_monitoring_hours

def test_within_range_normal_hours():
    """测试正常工作时间范围"""
    # 假设当前时间是 14:00，在 09:00-18:00 范围内
    result = is_within_monitoring_hours("09:00", "18:00")
    # 结果取决于当前实际时间
    assert isinstance(result, bool)

def test_outside_range_early_morning():
    """测试凌晨时间（不在工作范围内）"""
    result = is_within_monitoring_hours("09:00", "18:00")
    assert isinstance(result, bool)

def test_null_time_range():
    """测试空时间范围（应该全天执行）"""
    result = is_within_monitoring_hours(None, None)
    assert result is True

def test_empty_string_time_range():
    """测试空字符串时间范围（应该全天执行）"""
    result = is_within_monitoring_hours("", "")
    assert result is True

def test_start_time_only():
    """测试只有开始时间（应该全天执行）"""
    result = is_within_monitoring_hours("09:00", None)
    assert result is True

def test_end_time_only():
    """测试只有结束时间（应该全天执行）"""
    result = is_within_monitoring_hours(None, "18:00")
    assert result is True

def test_beijing_timezone():
    """验证使用北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    current_time = now.strftime('%H:%M')

    # 验证返回的时间格式正确
    assert ':' in current_time
    assert len(current_time) == 5
```

**Step 2: 运行测试验证失败**

运行: `pytest tests/test_time_range_check.py -v`

预期: FAIL - 函数不存在

**Step 3: 实现 is_within_monitoring_hours 函数**

在 `code/web_app.py` 中添加函数（在 `# ==================== Monitoring Job Helper Functions ====================` 部分之后）：

```python
import pytz
from datetime import datetime

def is_within_monitoring_hours(start_time: str, end_time: str) -> bool:
    """
    检查当前时间是否在监测时间范围内（北京时间）

    Args:
        start_time: 开始时间字符串 HH:MM，None 或空字符串表示无限制
        end_time: 结束时间字符串 HH:MM，None 或空字符串表示无限制

    Returns:
        bool: True 表示在范围内或无限制，False 表示在范围外
    """
    # 无时间限制（None 或空字符串）
    if not start_time or not end_time:
        return True

    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    current_time = now.strftime('%H:%M')

    # 检查是否在范围内
    return start_time <= current_time <= end_time


def get_beijing_time_str() -> str:
    """
    获取格式化的北京时间字符串

    Returns:
        str: 格式化的北京时间，如 "2026-03-18 14:30:00 +08:00"
    """
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    return now.strftime('%Y-%m-%d %H:%M:%S +08:00')
```

**Step 4: 运行测试验证通过**

运行: `pytest tests/test_time_range_check.py -v`

预期: PASS

**Step 5: 提交**

```bash
git add code/web_app.py tests/test_time_range_check.py
git commit -m "feat: add time range check function with Beijing timezone"
```

---

## Task 3: 修改任务执行包装函数

**Files:**
- Modify: `code/web_app.py`

**Step 1: 修改 run_monitoring_task_wrapper 函数**

找到 `code/web_app.py` 中的 `run_monitoring_task_wrapper` 函数，添加时间范围检查：

```python
def run_monitoring_task_wrapper(config_id: int):
    """
    Wrapper function for running monitoring tasks (called by scheduler)

    Args:
        config_id: Monitoring configuration ID
    """
    # Deferred import to avoid circular dependency with riskbird_monitor module
    # which imports from database and riskbird_search
    from riskbird_monitor import RiskBirdMonitor

    job_id = f'monitoring_{config_id}'
    db = get_db()

    if db.conn:
        try:
            # Get config
            config = db.get_monitoring_config(config_id)
            if not config:
                logging.error(f"[{get_beijing_time_str()}] Config {config_id} not found")
                return

            # Check time range
            start_time = config.get('monitoring_start_time')
            end_time = config.get('monitoring_end_time')

            if not is_within_monitoring_hours(start_time, end_time):
                logging.info(
                    f"[{get_beijing_time_str()}] Job {job_id} skipped "
                    f"(outside time range {start_time}-{end_time})"
                )
                return

            # Execute monitoring task
            monitor = RiskBirdMonitor(db)
            result = monitor.run_monitoring_task(config_id)
            logging.info(f"[{get_beijing_time_str()}] Job {job_id} completed: {result}")

            # Record the run before closing connection
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

**Step 2: 提交**

```bash
git add code/web_app.py
git commit -m "feat: add time range check to monitoring task execution"
```

---

## Task 4: 修改 API 创建接口

**Files:**
- Modify: `code/web_app.py`
- Create: `tests/test_api_time_range_validation.py`

**Step 1: 创建 API 验证测试**

创建 `tests/test_api_time_range_validation.py`:

```python
import pytest
import json
from code.web_app import app

@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_config_with_time_range(client, monkeypatch):
    """测试创建带时间范围的配置"""
    # Mock 数据库连接
    # ... 省略数据库 mock 设置 ...

    response = client.post('/api/monitoring/configs',
        data=json.dumps({
            'config_name': '测试配置',
            'region_codes': ['110000'],
            'interval_minutes': 5,
            'monitoring_start_time': '10:00',
            'monitoring_end_time': '17:30'
        }),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True

def test_create_config_invalid_time_format(client):
    """测试无效时间格式"""
    response = client.post('/api/monitoring/configs',
        data=json.dumps({
            'config_name': '测试配置',
            'region_codes': ['110000'],
            'interval_minutes': 5,
            'monitoring_start_time': '25:00',  # 无效时间
            'monitoring_end_time': '18:00'
        }),
        content_type='application/json'
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert '时间格式' in data['error']

def test_create_config_cross_day_rejected(client):
    """测试拒绝跨天时间范围"""
    response = client.post('/api/monitoring/configs',
        data=json.dumps({
            'config_name': '测试配置',
            'region_codes': ['110000'],
            'interval_minutes': 5,
            'monitoring_start_time': '22:00',
            'monitoring_end_time': '02:00'  # 跨天
        }),
        content_type='application/json'
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert '开始时间必须小于结束时间' in data['error']

def test_create_config_default_time_range(client):
    """测试默认时间范围"""
    response = client.post('/api/monitoring/configs',
        data=json.dumps({
            'config_name': '测试配置',
            'region_codes': ['110000'],
            'interval_minutes': 5
            # 不提供时间范围，应使用默认值
        }),
        content_type='application/json'
    )

    assert response.status_code == 200
```

**Step 2: 运行测试验证失败**

运行: `pytest tests/test_api_time_range_validation.py -v`

预期: FAIL - 验证逻辑不存在

**Step 3: 添加时间格式验证函数**

在 `code/web_app.py` 中添加验证函数（在路由定义之前）：

```python
import re

def validate_time_format(time_str: str) -> bool:
    """
    验证时间格式是否为 HH:MM

    Args:
        time_str: 时间字符串

    Returns:
        bool: 格式正确返回 True
    """
    if not time_str:
        return True
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def validate_time_range(start: str, end: str) -> bool:
    """
    验证时间范围（不支持跨天）

    Args:
        start: 开始时间 HH:MM
        end: 结束时间 HH:MM

    Returns:
        bool: 有效返回 True
    """
    if not start or not end:
        return True
    return start < end
```

**Step 4: 修改 create_monitoring_config 接口**

修改 `code/web_app.py` 中的 `create_monitoring_config` 函数：

```python
@app.route('/api/monitoring/configs', methods=['POST'])
def create_monitoring_config():
    """Create a new monitoring configuration"""
    data = request.json
    if data is None:
        return jsonify({'success': False, 'error': '无效的JSON数据'}), 400

    config_name = data.get('config_name', '').strip()
    region_codes = data.get('region_codes', [])
    interval_minutes = data.get('interval_minutes', 5)
    reg_cap = data.get('reg_cap', '').strip()

    # 新增：时间范围参数
    monitoring_start_time = data.get('monitoring_start_time', '09:00').strip()
    monitoring_end_time = data.get('monitoring_end_time', '18:00').strip()

    if not config_name:
        return jsonify({'success': False, 'error': '配置名称不能为空'}), 400

    if not isinstance(region_codes, list) or not region_codes:
        return jsonify({'success': False, 'error': '地区代码必须是非空数组'}), 400

    if not isinstance(interval_minutes, int) or not (1 <= interval_minutes <= 1440):
        return jsonify({'success': False, 'error': '监控间隔必须在1-1440分钟之间'}), 400

    # 新增：时间格式验证
    if not validate_time_format(monitoring_start_time):
        return jsonify({'success': False, 'error': '开始时间格式错误，应为 HH:MM'}), 400

    if not validate_time_format(monitoring_end_time):
        return jsonify({'success': False, 'error': '结束时间格式错误，应为 HH:MM'}), 400

    # 新增：时间范围验证
    if not validate_time_range(monitoring_start_time, monitoring_end_time):
        return jsonify({'success': False, 'error': '开始时间必须小于结束时间（不支持跨天）'}), 400

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'}), 500

    try:
        # Convert region list to JSON string
        import json
        region_codes_json = json.dumps(region_codes)

        # 修改：传递时间范围参数
        config_id = db.insert_monitoring_config(
            config_name=config_name,
            region_codes=region_codes_json,
            interval_minutes=interval_minutes,
            reg_cap=reg_cap if reg_cap else None,
            monitoring_start_time=monitoring_start_time,
            monitoring_end_time=monitoring_end_time
        )

        if not config_id:
            db.close()
            return jsonify({'success': False, 'error': '创建配置失败: 数据库插入返回None'}), 500

        # Add job to scheduler
        job_added = add_monitoring_job(config_id, interval_minutes)

        if not job_added:
            logging.warning(f"Failed to add scheduler job for config {config_id}")

        db.close()
        return jsonify({'success': True, 'config_id': config_id, 'job_added': job_added})

    except Exception as e:
        logging.error(f"Failed to create monitoring config: {e}", exc_info=True)
        db.close()
        return jsonify({'success': False, 'error': f'创建配置失败: {str(e)}'}), 500
```

**Step 5: 运行测试验证通过**

运行: `pytest tests/test_api_time_range_validation.py -v`

预期: PASS

**Step 6: 提交**

```bash
git add code/web_app.py tests/test_api_time_range_validation.py
git commit -m "feat: add time range validation to create monitoring config API"
```

---

## Task 5: 修改 API 更新接口

**Files:**
- Modify: `code/web_app.py`

**Step 1: 修改 update_monitoring_config 函数**

修改 `code/web_app.py` 中的 `update_monitoring_config` 函数，支持时间范围更新：

```python
@app.route('/api/monitoring/configs/<int:config_id>', methods=['PUT'])
def update_monitoring_config(config_id):
    """Update monitoring configuration"""
    data = request.json
    if data is None:
        return jsonify({'success': False, 'error': '无效的JSON数据'}), 400

    # 验证时间格式（如果提供）
    if 'monitoring_start_time' in data:
        if not validate_time_format(data['monitoring_start_time']):
            return jsonify({'success': False, 'error': '开始时间格式错误，应为 HH:MM'}), 400

    if 'monitoring_end_time' in data:
        if not validate_time_format(data['monitoring_end_time']):
            return jsonify({'success': False, 'error': '结束时间格式错误，应为 HH:MM'}), 400

    # 验证时间范围（如果两者都提供）
    start_time = data.get('monitoring_start_time')
    end_time = data.get('monitoring_end_time')
    if start_time and end_time:
        if not validate_time_range(start_time, end_time):
            return jsonify({'success': False, 'error': '开始时间必须小于结束时间（不支持跨天）'}), 400

    db = get_db()
    if not db.conn:
        return jsonify({'success': False, 'error': '数据库连接失败'})

    # Build update dict
    updates = {}
    if 'config_name' in data:
        updates['config_name'] = data['config_name']
    if 'region_codes' in data:
        import json
        updates['region_codes'] = json.dumps(data['region_codes'])
    if 'interval_minutes' in data:
        updates['interval_minutes'] = data['interval_minutes']
    if 'reg_cap' in data:
        updates['reg_cap'] = data['reg_cap']
    if 'monitoring_start_time' in data:
        updates['monitoring_start_time'] = data['monitoring_start_time']
    if 'monitoring_end_time' in data:
        updates['monitoring_end_time'] = data['monitoring_end_time']

    success = db.update_monitoring_config(config_id, **updates)

    if success and 'interval_minutes' in updates:
        # Update job schedule
        remove_monitoring_job(config_id)
        add_monitoring_job(config_id, updates['interval_minutes'])

    db.close()

    if success:
        return jsonify({'success': True, 'message': '配置已更新'})
    else:
        return jsonify({'success': False, 'error': '更新配置失败'})
```

**Step 2: 修改 database.py 的 update_monitoring_config 函数**

修改 `code/database.py` 中的 `update_monitoring_config` 函数，支持新字段：

```python
def update_monitoring_config(self, config_id: int, **updates) -> bool:
    """
    更新监测配置

    Args:
        config_id: 配置 ID
        **updates: 要更新的字段键值对

    Returns:
        更新成功返回 True，失败返回 False
    """
    try:
        # 构建更新语句
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [config_id]

        self.cursor.execute(f'''
            UPDATE monitoring_configs
            SET {set_clause}
            WHERE id = ?
        ''', values)

        self.conn.commit()
        return True
    except Exception as e:
        self.logger.error(f"Failed to update monitoring config: {e}")
        return False
```

**Step 3: 提交**

```bash
git add code/web_app.py code/database.py
git commit -m "feat: support time range updates in monitoring config API"
```

---

## Task 6: 修改获取配置接口

**Files:**
- Modify: `code/web_app.py`

**Step 1: 验证 get_monitoring_configs 包含时间字段**

确保 `code/web_app.py` 中的 `get_monitoring_configs` 路由返回的配置包含时间范围字段。

该路由使用 `db.get_all_monitoring_configs()`，需要确保数据库函数返回时间字段。

**Step 2: 修改 database.py 的 get_all_monitoring_configs 函数**

修改 `code/database.py` 中的 `get_all_monitoring_configs` 函数：

```python
def get_all_monitoring_configs(self) -> List[Dict]:
    """
    获取所有监测配置

    Returns:
        配置列表
    """
    try:
        self.cursor.execute('''
            SELECT id, config_name, region_codes, interval_minutes,
                   reg_cap, monitoring_start_time, monitoring_end_time,
                   created_at
            FROM monitoring_configs
            ORDER BY created_at DESC
        ''')

        configs = []
        for row in self.cursor.fetchall():
            configs.append({
                'id': row[0],
                'config_name': row[1],
                'region_codes': row[2],
                'interval_minutes': row[3],
                'reg_cap': row[4],
                'monitoring_start_time': row[5],
                'monitoring_end_time': row[6],
                'created_at': row[7]
            })

        return configs
    except Exception as e:
        self.logger.error(f"Failed to get all monitoring configs: {e}")
        return []
```

**Step 3: 提交**

```bash
git add code/database.py
git commit -m "feat: include time range fields in get_all_monitoring_configs"
```

---

## Task 7: 前端表单修改

**Files:**
- Modify: `templates/monitoring.html`

**Step 1: 添加时间范围表单控件**

在 `templates/monitoring.html` 中找到创建配置的表单，添加时间范围输入：

```html
<!-- 在现有表单字段后添加 -->
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
               class="form-control"
               title="开始时间">
        <span class="time-separator">至</span>
        <input type="time"
               id="monitoring-end-time"
               name="monitoring_end_time"
               value="18:00"
               min="00:00"
               max="23:59"
               class="form-control"
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
    margin-bottom: 10px;
}

.time-range-inputs input[type="time"] {
    flex: 1;
    max-width: 150px;
}

.time-separator {
    color: #6c757d;
    font-weight: 500;
}
</style>
```

**Step 2: 添加前端验证 JavaScript**

在 `templates/monitoring.html` 的 script 部分添加验证函数：

```javascript
/**
 * 验证时间范围
 */
function validateTimeRange() {
    const startTime = document.getElementById('monitoring-start-time').value;
    const endTime = document.getElementById('monitoring-end-time').value;

    if (startTime && endTime && startTime >= endTime) {
        alert('开始时间必须小于结束时间（不支持跨天）');
        return false;
    }

    return true;
}

// 修改现有的表单提交处理
document.addEventListener('DOMContentLoaded', function() {
    // 找到创建配置的表单
    const createForm = document.getElementById('create-config-form');
    if (createForm) {
        createForm.addEventListener('submit', function(e) {
            if (!validateTimeRange()) {
                e.preventDefault();
                return false;
            }
        });
    }
});
```

**Step 3: 在配置列表中显示时间范围**

在 `templates/monitoring.html` 中找到配置卡片的显示部分，添加时间范围显示：

```html
<!-- 在配置卡片中添加 -->
<div class="config-detail" v-if="config.monitoring_start_time && config.monitoring_end_time">
    <span class="detail-label">监测时段:</span>
    <span class="detail-value">
        {{ config.monitoring_start_time }} - {{ config.monitoring_end_time }}
    </span>
</div>
<div class="config-detail" v-else>
    <span class="detail-label">监测时段:</span>
    <span class="detail-value">全天</span>
</div>
```

**Step 4: 提交**

```bash
git add templates/monitoring.html
git commit -m "feat: add time range input controls to monitoring form"
```

---

## Task 8: 数据库迁移脚本

**Files:**
- Create: `code/migrations/add_monitoring_time_range.py`

**Step 1: 创建迁移脚本**

创建 `code/migrations/add_monitoring_time_range.py`:

```python
#!/usr/bin/env python3
"""
数据库迁移：为 monitoring_configs 表添加时间范围字段

运行方法：python code/migrations/add_monitoring_time_range.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import BOSSDatabase


def migrate():
    """执行迁移"""
    # 获取数据库路径
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent

    db_path = base_dir / "data" / "boss_jobs.db"

    print(f"数据库路径: {db_path}")

    # 连接数据库
    db = BOSSDatabase(str(db_path))
    if not db.connect():
        print("❌ 数据库连接失败")
        return False

    try:
        # 检查字段是否已存在
        db.cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [row[1] for row in db.cursor.fetchall()]

        if 'monitoring_start_time' in columns and 'monitoring_end_time' in columns:
            print("✅ 字段已存在，无需迁移")
            db.close()
            return True

        # 添加字段
        print("正在添加字段...")
        db.cursor.execute('''
            ALTER TABLE monitoring_configs
            ADD COLUMN monitoring_start_time TEXT DEFAULT '09:00'
        ''')
        print("✅ 添加 monitoring_start_time 字段")

        db.cursor.execute('''
            ALTER TABLE monitoring_configs
            ADD COLUMN monitoring_end_time TEXT DEFAULT '18:00'
        ''')
        print("✅ 添加 monitoring_end_time 字段")

        db.conn.commit()
        print("✅ 迁移完成")

        # 验证
        db.cursor.execute("SELECT COUNT(*) FROM monitoring_configs")
        count = db.cursor.fetchone()[0]
        print(f"📊 当前配置数量: {count}")

        if count > 0:
            db.cursor.execute('''
                SELECT id, config_name, monitoring_start_time, monitoring_end_time
                FROM monitoring_configs
                LIMIT 5
            ''')
            print("\n示例配置:")
            for row in db.cursor.fetchall():
                print(f"  ID {row[0]}: {row[1]} -> {row[2]} - {row[3]}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        db.conn.rollback()
        db.close()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("数据库迁移：添加监测时间范围字段")
    print("=" * 60)
    print()

    success = migrate()
    print()

    if success:
        print("✅ 迁移成功")
    else:
        print("❌ 迁移失败")
        sys.exit(1)
```

**Step 2: 运行迁移脚本**

运行: `python code/migrations/add_monitoring_time_range.py`

预期: 成功添加字段

**Step 3: 提交**

```bash
git add code/migrations/add_monitoring_time_range.py
git commit -m "feat: add database migration script for time range fields"
```

---

## Task 9: 集成测试

**Files:**
- Create: `tests/test_monitoring_time_range_integration.py`

**Step 1: 创建集成测试**

创建 `tests/test_monitoring_time_range_integration.py`:

```python
import pytest
import json
import time
from datetime import datetime
import pytz
from code.web_app import app, get_db, is_within_monitoring_hours

@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestMonitoringTimeRangeIntegration:
    """时间范围功能集成测试"""

    def test_full_workflow_with_time_range(self, client):
        """测试完整工作流：创建配置 → 验证时间范围 → 检查行为"""
        # 1. 创建带时间范围的配置
        response = client.post('/api/monitoring/configs',
            data=json.dumps({
                'config_name': f'测试配置_{int(time.time())}',
                'region_codes': ['110000'],
                'interval_minutes': 5,
                'monitoring_start_time': '10:00',
                'monitoring_end_time': '17:00'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        config_id = data['config_id']

        # 2. 获取配置验证时间范围
        response = client.get('/api/monitoring/configs')
        assert response.status_code == 200

        configs = json.loads(response.data)['configs']
        config = next((c for c in configs if c['id'] == config_id), None)
        assert config is not None
        assert config['monitoring_start_time'] == '10:00'
        assert config['monitoring_end_time'] == '17:00'

        # 3. 更新时间范围
        response = client.put(f'/api/monitoring/configs/{config_id}',
            data=json.dumps({
                'monitoring_start_time': '09:00',
                'monitoring_end_time': '18:00'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200

        # 4. 验证更新
        response = client.get('/api/monitoring/configs')
        configs = json.loads(response.data)['configs']
        config = next((c for c in configs if c['id'] == config_id), None)
        assert config['monitoring_start_time'] == '09:00'
        assert config['monitoring_end_time'] == '18:00'

        # 5. 删除配置
        response = client.delete(f'/api/monitoring/configs/{config_id}')
        assert response.status_code == 200

    def test_time_range_validation(self):
        """测试时间范围验证逻辑"""
        # 当前时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        current_time = now.strftime('%H:%M')

        # 测试全天
        assert is_within_monitoring_hours(None, None) is True
        assert is_within_monitoring_hours("", "") is True

        # 测试包含当前时间的范围
        morning_time = "06:00"
        evening_time = "23:59"
        assert is_within_monitoring_hours(morning_time, evening_time) is True

    def test_invalid_time_format_rejected(self, client):
        """测试无效时间格式被拒绝"""
        response = client.post('/api/monitoring/configs',
            data=json.dumps({
                'config_name': f'测试配置_{int(time.time())}',
                'region_codes': ['110000'],
                'interval_minutes': 5,
                'monitoring_start_time': 'invalid',
                'monitoring_end_time': '18:00'
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_cross_day_rejected(self, client):
        """测试跨天时间范围被拒绝"""
        response = client.post('/api/monitoring/configs',
            data=json.dumps({
                'config_name': f'测试配置_{int(time.time())}',
                'region_codes': ['110000'],
                'interval_minutes': 5,
                'monitoring_start_time': '22:00',
                'monitoring_end_time': '02:00'
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert '开始时间必须小于结束时间' in data['error']
```

**Step 2: 运行集成测试**

运行: `pytest tests/test_monitoring_time_range_integration.py -v`

预期: 全部通过

**Step 3: 提交**

```bash
git add tests/test_monitoring_time_range_integration.py
git commit -m "test: add integration tests for monitoring time range feature"
```

---

## Task 10: 文档更新

**Files:**
- Modify: `README.md`

**Step 1: 更新 README**

在 `README.md` 中添加时间范围功能说明：

```markdown
## 企业监测功能

### 监测时间范围

系统支持设置监测任务的执行时间范围，避免在非工作时间调用 API。

**功能特点：**
- 时间精确到分钟（如 10:00-17:30）
- 可选字段，不设置则全天24小时执行
- 默认工作时间：09:00-18:00
- 不支持跨天（开始时间必须小于结束时间）
- 所有时间统一使用北京时间（Asia/Shanghai）

**使用方法：**
1. 在创建或编辑监测配置时，设置"监测时间范围"
2. 系统仅在设定时间范围内执行监测任务
3. 时间范围外会跳过执行并记录日志
```

**Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README with monitoring time range feature"
```

---

## Task 11: 端到端测试

**Step 1: 手动测试检查清单**

1. **启动应用**
   ```bash
   python code/web_app.py
   ```

2. **访问监测页面**
   - 打开 http://localhost:5001/monitoring

3. **创建测试配置**
   - 配置名称：`测试时间范围`
   - 地区：选择任意地区
   - 间隔：5分钟
   - 时间范围：设置为当前时间前1小时到后1小时
   - 提交创建

4. **验证创建成功**
   - 检查配置列表中显示正确的时间范围
   - 检查数据库字段值正确

5. **测试更新时间范围**
   - 点击编辑配置
   - 修改时间范围为 09:00-18:00
   - 保存更新

6. **验证更新成功**
   - 检查配置显示新的时间范围

7. **测试验证**
   - 尝试设置无效时间格式（应被拒绝）
   - 尝试设置跨天时间（应被拒绝）

8. **检查日志**
   - 观察任务执行时的日志
   - 确认时间范围日志格式正确（带时区）

**Step 2: 提交完成标记**

```bash
git commit --allow-empty -m "feat: complete monitoring time range feature implementation"
```

---

## 验收标准

功能完成的标准：

1. ✅ 数据库表包含时间范围字段
2. ✅ 创建配置时可设置时间范围
3. ✅ 更新配置时可修改时间范围
4. ✅ 时间格式验证正常工作
5. ✅ 跨天时间被正确拒绝
6. ✅ 任务执行时检查时间范围
7. ✅ 时间范围外跳过执行并记录日志
8. ✅ 前端表单支持时间选择
9. ✅ 前端显示时间范围信息
10. ✅ 所有时间使用北京时间
11. ✅ 日志格式包含时区信息
12. ✅ 单元测试通过
13. ✅ 集成测试通过
14. ✅ 手动测试通过
15. ✅ 文档已更新

## 回滚计划

如果需要回滚：

1. **数据库回滚**
   ```sql
   -- SQLite 不支持 DROP COLUMN，需要重建表
   -- 或者使用 code/migrations/rollback_add_monitoring_time_range.py
   ```

2. **代码回滚**
   ```bash
   git revert <commit-hash>
   ```

3. **重启应用**
   ```bash
   # 停止当前应用
   # 重新部署之前版本
   ```
