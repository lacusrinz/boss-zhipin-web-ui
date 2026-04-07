# 多 RiskBird Token 套餐支持 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持配置多个 RiskBird token 套餐（token + app_uuid + name），并在监测配置中手动选择使用哪个套餐。

**Architecture:** 新增 `riskbird_token_sets` 表管理多套餐，`monitoring_configs` 新增 `token_set_id` 字段关联。数据库层只做存取，加密/解密在 API 路由和 monitor 层处理。UI 在现有模态框内扩展。

**Tech Stack:** Flask, SQLite, SQLAlchemy, Jinja2 + Tailwind CSS, Fernet encryption

**Spec:** `docs/superpowers/specs/2026-04-07-multi-riskbird-token-sets-design.md`

---

## Files

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `code/database.py` | 新表创建、迁移、token sets CRUD、ALLOWED_COLUMNS 更新 |
| Modify | `code/web_app.py` | 5 个新 API 路由 + 监测配置路由修改 |
| Modify | `code/riskbird_monitor.py` | 执行时从 token_set 取凭证，回退旧逻辑 |
| Modify | `code/templates/monitoring.html` | token 套餐列表 UI + 监测配置下拉框 |
| Create | `tests/test_token_sets.py` | 数据库 CRUD 和 API 路由测试 |

---

### Task 1: 数据库层 — 建表、迁移、CRUD

**Files:**
- Modify: `code/database.py:716-829` (init_monitoring_tables)
- Modify: `code/database.py:831-890` (_migrate_monitoring_tables)
- Modify: `code/database.py:1078-1080` (ALLOWED_COLUMNS)
- Test: `tests/test_token_sets.py`

- [ ] **Step 1: 写失败测试 — 建表验证**

```python
# tests/test_token_sets.py
#!/usr/bin/env python3
"""Tests for riskbird_token_sets table and CRUD"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from database import BOSSDatabase
import tempfile
import os


def test_token_sets_table_created():
    """Test riskbird_token_sets table is created"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riskbird_token_sets'")
        assert cursor.fetchone() is not None, "riskbird_token_sets table should exist"
        db.close()


def test_token_sets_crud():
    """Test token sets CRUD operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert
        token_set_id = db.insert_token_set("主账号", "encrypted_token_1", "uuid-1")
        assert token_set_id is not None

        # Get single
        ts = db.get_token_set(token_set_id)
        assert ts['name'] == "主账号"
        assert ts['token'] == "encrypted_token_1"
        assert ts['app_uuid'] == "uuid-1"

        # Get all
        db.insert_token_set("备用账号", "encrypted_token_2", "uuid-2")
        all_ts = db.get_all_token_sets()
        assert len(all_ts) == 2

        # Update
        db.update_token_set(token_set_id, name="主账号-更新", token="new_encrypted", app_uuid="new-uuid")
        updated = db.get_token_set(token_set_id)
        assert updated['name'] == "主账号-更新"
        assert updated['token'] == "new_encrypted"

        # Delete
        db.delete_token_set(token_set_id)
        assert db.get_token_set(token_set_id) is None
        db.close()


def test_token_set_name_unique():
    """Test that duplicate names are rejected"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        db.insert_token_set("主账号", "token1", "uuid1")
        try:
            db.insert_token_set("主账号", "token2", "uuid2")
            assert False, "Should have raised an error for duplicate name"
        except Exception:
            pass
        db.close()


def test_migration_adds_token_set_id():
    """Test that migration adds token_set_id to monitoring_configs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Create a monitoring config before migration
        config_id = db.insert_monitoring_config(
            config_name="Test",
            region_codes='["110000"]',
            interval_minutes=5
        )

        # Run migration
        db._migrate_monitoring_tables()

        # Verify token_set_id column exists
        cursor = db.conn.cursor()
        cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [row[1] for row in cursor.fetchall()]
        assert 'token_set_id' in columns, "token_set_id column should exist after migration"

        # Verify existing config still works (backward compatible)
        config = db.get_monitoring_config(config_id)
        assert config['token_set_id'] is None

        # Verify ALLOWED_COLUMNS includes token_set_id
        db.update_monitoring_config(config_id, token_set_id=1)
        config = db.get_monitoring_config(config_id)
        assert config['token_set_id'] == 1
        db.close()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python -m pytest tests/test_token_sets.py -v`
Expected: FAIL（表和方法不存在）

- [ ] **Step 3: 在 `init_monitoring_tables()` 末尾添加建表语句**

在 `code/database.py` 的 `init_monitoring_tables()` 方法中（`return True` 之前），添加：

```python
# Create riskbird_token_sets table
self.cursor.execute("""
    CREATE TABLE IF NOT EXISTS riskbird_token_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        token TEXT NOT NULL,
        app_uuid TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

- [ ] **Step 4: 在 `_migrate_monitoring_tables()` 中添加迁移**

在 `code/database.py` 的 `_migrate_monitoring_tables()` 方法的 try 块末尾添加：

```python
# Add token_set_id column if not exists
if 'token_set_id' not in columns:
    self.cursor.execute("""
        ALTER TABLE monitoring_configs
        ADD COLUMN token_set_id INTEGER REFERENCES riskbird_token_sets(id) ON DELETE SET NULL
    """)
    logging.info("Added token_set_id column to monitoring_configs")
```

- [ ] **Step 5: 在 ALLOWED_COLUMNS 中添加 `token_set_id`**

修改 `code/database.py:1078-1080`：

```python
ALLOWED_COLUMNS = {'config_name', 'region_codes', 'is_active', 'interval_minutes', 'reg_cap',
                  'monitoring_start_time', 'monitoring_end_time', 'feishu_enabled',
                  'feishu_target_type', 'feishu_group_id', 'token_set_id'}
```

- [ ] **Step 6: 添加 token sets CRUD 方法**

在 `code/database.py` 的 `update_riskbird_config` 方法之后添加：

```python
def insert_token_set(self, name: str, token: str, app_uuid: str) -> Optional[int]:
    """Insert a new token set"""
    try:
        self.cursor.execute("""
            INSERT INTO riskbird_token_sets (name, token, app_uuid)
            VALUES (?, ?, ?)
        """, (name, token, app_uuid))
        self.conn.commit()
        return self.cursor.lastrowid
    except Exception as e:
        logging.error(f"Failed to insert token set: {e}")
        self.conn.rollback()
        raise

def get_token_set(self, token_set_id: int) -> Optional[Dict]:
    """Get a single token set by ID"""
    try:
        self.cursor.execute("""
            SELECT id, name, token, app_uuid, created_at, updated_at
            FROM riskbird_token_sets
            WHERE id = ?
        """, (token_set_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0], 'name': row[1], 'token': row[2],
                'app_uuid': row[3], 'created_at': row[4], 'updated_at': row[5]
            }
        return None
    except Exception as e:
        logging.error(f"Failed to get token set: {e}")
        return None

def get_all_token_sets(self) -> List[Dict]:
    """Get all token sets"""
    try:
        self.cursor.execute("""
            SELECT id, name, token, app_uuid, created_at, updated_at
            FROM riskbird_token_sets
            ORDER BY created_at ASC
        """)
        rows = self.cursor.fetchall()
        return [
            {'id': r[0], 'name': r[1], 'token': r[2], 'app_uuid': r[3],
             'created_at': r[4], 'updated_at': r[5]}
            for r in rows
        ]
    except Exception as e:
        logging.error(f"Failed to get token sets: {e}")
        return []

def update_token_set(self, token_set_id: int, **kwargs) -> bool:
    """Update a token set"""
    try:
        allowed = {'name', 'token', 'app_uuid'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [token_set_id]

        self.cursor.execute(f"""
            UPDATE riskbird_token_sets
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)
        self.conn.commit()
        return self.cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Failed to update token set: {e}")
        self.conn.rollback()
        return False

def delete_token_set(self, token_set_id: int) -> bool:
    """Delete a token set"""
    try:
        self.cursor.execute("DELETE FROM riskbird_token_sets WHERE id = ?", (token_set_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Failed to delete token set: {e}")
        self.conn.rollback()
        return False
```

- [ ] **Step 7: 运行测试确认通过**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python -m pytest tests/test_token_sets.py -v`
Expected: ALL PASS

- [ ] **Step 8: 提交**

```bash
git add code/database.py tests/test_token_sets.py
git commit -m "feat: add riskbird_token_sets table and CRUD operations"
```

---

### Task 2: API 层 — Token 套餐路由 + 监测配置关联

**Files:**
- Modify: `code/web_app.py:669-773` (在现有 token 路由之后添加新路由)
- Modify: `code/web_app.py:812-990` (监测配置 CREATE/UPDATE 路由，传入 token_set_id)
- Test: `tests/test_token_sets.py`（追加 API 测试）

- [ ] **Step 1: 写失败测试 — API 路由**

在 `tests/test_token_sets.py` 末尾追加：

```python
import json


def test_api_get_token_sets_empty(client):
    """Test GET /api/monitoring/token-sets returns empty list"""
    response = client.get('/api/monitoring/token-sets')
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['token_sets'] == []


def test_api_create_and_get_token_sets(client):
    """Test POST and GET token sets"""
    # Create
    response = client.post('/api/monitoring/token-sets',
        data=json.dumps({'name': '主账号', 'token': 'test-jwt-token', 'app_uuid': 'WEB-123'}),
        content_type='application/json')
    data = json.loads(response.data)
    assert data['success'] is True

    # Get list
    response = client.get('/api/monitoring/token-sets')
    data = json.loads(response.data)
    assert len(data['token_sets']) == 1
    ts = data['token_sets'][0]
    assert ts['name'] == '主账号'
    # Token should be masked
    assert 'test-jwt' not in ts['token']  # raw token should not appear


def test_api_update_token_set(client):
    """Test PUT /api/monitoring/token-sets/<id>"""
    # Create first
    response = client.post('/api/monitoring/token-sets',
        data=json.dumps({'name': '主账号', 'token': 'token-1', 'app_uuid': 'uuid-1'}),
        content_type='application/json')
    token_set_id = json.loads(response.data)['id']

    # Update
    response = client.put(f'/api/monitoring/token-sets/{token_set_id}',
        data=json.dumps({'name': '主账号-更新', 'token': 'new-token', 'app_uuid': 'new-uuid'}),
        content_type='application/json')
    data = json.loads(response.data)
    assert data['success'] is True


def test_api_delete_token_set(client):
    """Test DELETE /api/monitoring/token-sets/<id>"""
    response = client.post('/api/monitoring/token-sets',
        data=json.dumps({'name': '待删除', 'token': 'token-x', 'app_uuid': 'uuid-x'}),
        content_type='application/json')
    token_set_id = json.loads(response.data)['id']

    response = client.delete(f'/api/monitoring/token-sets/{token_set_id}')
    data = json.loads(response.data)
    assert data['success'] is True
```

注意：以上测试需要 Flask test client fixture。在文件顶部添加：

```python
import pytest
from web_app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python -m pytest tests/test_token_sets.py::test_api_get_token_sets_empty -v`
Expected: FAIL（路由不存在）

- [ ] **Step 3: 在 web_app.py 中添加 token sets API 路由**

在 `code/web_app.py` 的 `test_token_connection` 路由（约 line 773）之后添加：

```python
# ==================== Token Sets API ====================

@app.route('/api/monitoring/token-sets', methods=['GET'])
def get_token_sets():
    """Get all token sets (with masked tokens)"""
    try:
        db = BOSSDatabase()
        db.connect()
        token_sets = db.get_all_token_sets()

        # Decrypt and mask tokens for display
        from token_service import TokenService
        token_service = TokenService()

        for ts in token_sets:
            try:
                decrypted = token_service.decrypt(ts['token'])
                ts['token'] = token_service.mask_token(decrypted)
            except:
                ts['token'] = '****'

        db.close()
        return jsonify({'success': True, 'token_sets': token_sets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/token-sets', methods=['POST'])
def create_token_set():
    """Create a new token set"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        token = data.get('token', '').strip()
        app_uuid = data.get('app_uuid', '').strip()

        if not name or not token or not app_uuid:
            return jsonify({'success': False, 'error': '名称、Token 和 App UUID 不能为空'}), 400

        # Encrypt token before storage
        from token_service import TokenService
        token_service = TokenService()
        encrypted_token = token_service.encrypt(token)

        db = BOSSDatabase()
        db.connect()
        token_set_id = db.insert_token_set(name, encrypted_token, app_uuid)
        db.close()

        return jsonify({'success': True, 'id': token_set_id, 'message': 'Token 套餐创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/token-sets/<int:token_set_id>', methods=['PUT'])
def update_token_set_route(token_set_id):
    """Update a token set"""
    try:
        data = request.get_json()
        updates = {}

        if 'name' in data:
            updates['name'] = data['name'].strip()
        if 'app_uuid' in data:
            updates['app_uuid'] = data['app_uuid'].strip()
        if 'token' in data and data['token'].strip():
            # Encrypt new token
            from token_service import TokenService
            token_service = TokenService()
            updates['token'] = token_service.encrypt(data['token'].strip())

        if not updates:
            return jsonify({'success': False, 'error': '没有需要更新的字段'}), 400

        db = BOSSDatabase()
        db.connect()
        success = db.update_token_set(token_set_id, **updates)
        db.close()

        if success:
            return jsonify({'success': True, 'message': '更新成功'})
        else:
            return jsonify({'success': False, 'error': 'Token 套餐不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/token-sets/<int:token_set_id>', methods=['DELETE'])
def delete_token_set_route(token_set_id):
    """Delete a token set"""
    try:
        db = BOSSDatabase()
        db.connect()
        success = db.delete_token_set(token_set_id)
        db.close()

        if success:
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'success': False, 'error': 'Token 套餐不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/token-sets/<int:token_set_id>/test', methods=['POST'])
def test_token_set_connection(token_set_id):
    """Test a specific token set's connection"""
    try:
        db = BOSSDatabase()
        db.connect()
        token_set = db.get_token_set(token_set_id)
        db.close()

        if not token_set:
            return jsonify({'success': False, 'error': 'Token 套餐不存在'}), 404

        # Decrypt token
        from token_service import TokenService
        token_service = TokenService()
        token = token_service.decrypt(token_set['token'])
        app_uuid = token_set['app_uuid']

        # Test with a minimal API call (same pattern as existing test route)
        from riskbird_search import call_riskbird_search_api
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        search_params = {
            'startDate': today,
            'endDate': today,
            'page': 1,
            'pageSize': 1
        }

        result = call_riskbird_search_api(token, app_uuid, search_params)
        if 'error' in result:
            return jsonify({'success': False, 'error': result.get('message', '连接测试失败')})

        return jsonify({'success': True, 'message': '连接测试成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 4: 修改监测配置路由，传入 token_set_id**

在 `code/web_app.py` 的 `create_monitoring_config` 路由（POST /api/monitoring/configs）中，`data` 对象构建部分添加：

```python
token_set_id = data.get('token_set_id') or None
```

并在传给 `db.insert_monitoring_config()` 的参数中添加 `token_set_id=token_set_id`。

同理在 `update_monitoring_config` 路由（PUT /api/monitoring/configs/<id>）中，`update_data` 对象构建部分确保包含 `token_set_id`。由于 ALLOWED_COLUMNS 已包含它，kwargs 传递即可。

- [ ] **Step 5: 修改监测配置查询，返回 token_set_name**

修改 `code/web_app.py` 的 `get_monitoring_configs` 路由（GET /api/monitoring/configs），在返回 configs 列表后为每个 config 附加 token_set_name：

```python
# After getting configs from db
db = BOSSDatabase()
db.connect()
configs = db.get_all_monitoring_configs()

# Enrich with token set names
for config in configs:
    if config.get('token_set_id'):
        ts = db.get_token_set(config['token_set_id'])
        config['token_set_name'] = ts['name'] if ts else None
    else:
        config['token_set_name'] = None
```

同理修改 `get_monitoring_config_detail` 路由（GET /api/monitoring/configs/<id>），为单个 config 附加 `token_set_name`。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python -m pytest tests/test_token_sets.py -v`
Expected: ALL PASS

- [ ] **Step 7: 提交**

```bash
git add code/web_app.py tests/test_token_sets.py
git commit -m "feat: add token sets API routes and monitoring config integration"
```

---

### Task 3: 执行层 — riskbird_monitor 改用 token_set

**Files:**
- Modify: `code/riskbird_monitor.py:148-170`（token 获取逻辑）

- [ ] **Step 1: 修改 `_execute_single_config` 方法中的 token 获取逻辑**

在 `code/riskbird_monitor.py` 中，找到以下代码（约 line 155-157，在 `# Get API credentials` 注释后）：

```python
# Get API credentials
encrypted_token = self.db.get_riskbird_config('token')
app_uuid = self.db.get_riskbird_config('app_uuid')
```

仅替换这 3 行为：

```python
# Get API credentials
if config.get('token_set_id'):
    # Use token from token set
    token_set = self.db.get_token_set(config['token_set_id'])
    if token_set:
        encrypted_token = token_set['token']
        app_uuid = token_set['app_uuid']
    else:
        # Token set was deleted, fall back
        encrypted_token = self.db.get_riskbird_config('token')
        app_uuid = self.db.get_riskbird_config('app_uuid')
else:
    # Fall back to legacy config
    encrypted_token = self.db.get_riskbird_config('token')
    app_uuid = self.db.get_riskbird_config('app_uuid')
```

注意：后续的 `TokenService.decrypt()` 解密块（约 line 163-170）保持不变，因为它操作的是 `encrypted_token` 变量。

- [ ] **Step 2: 验证 — 运行全部测试**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: 提交**

```bash
git add code/riskbird_monitor.py
git commit -m "feat: monitoring execution uses token_set_id with fallback"
```

---

### Task 4: UI 层 — Token 套餐管理 + 监测配置下拉框

**Files:**
- Modify: `code/templates/monitoring.html:106-147`（token modal HTML）
- Modify: `code/templates/monitoring.html:351-407`（monitoring config form 中添加下拉框）
- Modify: `code/templates/monitoring.html` JavaScript 部分

- [ ] **Step 1: 替换 token 配置模态框内容**

将 `monitoring.html` 中 lines 106-147 的 token modal 替换为：

```html
<!-- Token Configuration Modal -->
<div id="token-modal" class="modal">
    <div class="modal-content" style="max-width: 700px;">
        <span class="close" onclick="closeTokenModal()">&times;</span>
        <h2 class="text-xl font-semibold mb-4">RiskBird API 配置</h2>

        <!-- Token 套餐列表 -->
        <div id="token-sets-list" class="space-y-2 mb-4">
            <!-- 动态填充 -->
        </div>

        <!-- 添加/编辑表单 -->
        <div id="token-set-form" class="hidden border rounded p-4 bg-gray-50 space-y-3 mb-4">
            <h3 id="token-set-form-title" class="font-medium">添加 Token 套餐</h3>
            <input type="hidden" id="edit-token-set-id" value="">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">备注名称</label>
                <input type="text" id="ts-name-input" class="w-full border rounded px-3 py-2" placeholder="如：主账号">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Token</label>
                <input type="text" id="ts-token-input" class="w-full border rounded px-3 py-2" placeholder="输入 JWT Token">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">App UUID</label>
                <input type="text" id="ts-uuid-input" class="w-full border rounded px-3 py-2" placeholder="如：WEB-B411E1DF...">
            </div>
            <div class="flex space-x-2">
                <button type="button" onclick="saveTokenSet()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 text-sm">保存</button>
                <button type="button" onclick="cancelTokenSetForm()" class="bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500 text-sm">取消</button>
            </div>
        </div>

        <button type="button" onclick="showAddTokenSetForm()" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 text-sm">+ 添加 Token 套餐</button>
        <button type="button" onclick="closeTokenModal()" class="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 text-sm ml-2">关闭</button>
    </div>
</div>
```

- [ ] **Step 2: 在监测配置表单中添加 Token 套餐下拉框**

在 `monitoring.html` 的监测配置表单中，飞书配置区域之前（约 line 351 `<div class="border-t pt-4 mt-4">` 之前）添加：

```html
<div>
    <label for="token-set-select" class="block text-sm font-medium text-gray-700 mb-1">Token 套餐</label>
    <select name="token_set_id" id="token-set-select"
            class="w-full border rounded px-3 py-2">
        <option value="">默认（旧配置）</option>
    </select>
    <p class="text-xs text-gray-500 mt-1">选择该监测任务使用的 API Token</p>
</div>
```

- [ ] **Step 3: 替换 token 相关 JavaScript**

在 `monitoring.html` 的 `<script>` 部分：

a) 替换 `loadTokenConfig` 函数（约 lines 905-933）为：

```javascript
async function loadTokenSets() {
    try {
        const response = await fetch('/api/monitoring/token-sets');
        const result = await response.json();
        if (!result.success) return;

        const list = document.getElementById('token-sets-list');
        if (result.token_sets.length === 0) {
            list.innerHTML = '<p class="text-sm text-gray-500">暂无 Token 套餐，请点击下方按钮添加</p>';
        } else {
            list.innerHTML = result.token_sets.map(ts => `
                <div class="flex items-center justify-between border rounded p-3 bg-white">
                    <div>
                        <span class="font-medium">${ts.name}</span>
                        <span class="text-xs text-gray-500 ml-2">${ts.token}</span>
                        <span class="text-xs text-gray-400 ml-2">${ts.app_uuid}</span>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="testTokenSet(${ts.id})" class="text-xs bg-green-500 text-white px-2 py-1 rounded hover:bg-green-600">测试</button>
                        <button onclick="editTokenSet(${ts.id}, '${ts.name}', '${ts.app_uuid}')" class="text-xs bg-yellow-500 text-white px-2 py-1 rounded hover:bg-yellow-600">编辑</button>
                        <button onclick="deleteTokenSet(${ts.id})" class="text-xs bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600">删除</button>
                    </div>
                </div>
            `).join('');
        }

        // Also update the dropdown in monitoring config form
        updateTokenSetDropdown(result.token_sets);
    } catch (error) {
        console.error('Error loading token sets:', error);
    }
}

function updateTokenSetDropdown(tokenSets) {
    const select = document.getElementById('token-set-select');
    if (!select) return;
    const currentVal = select.value;
    select.innerHTML = '<option value="">默认（旧配置）</option>';
    tokenSets.forEach(ts => {
        const opt = document.createElement('option');
        opt.value = ts.id;
        opt.textContent = ts.name;
        select.appendChild(opt);
    });
    select.value = currentVal;
}

function showAddTokenSetForm() {
    document.getElementById('token-set-form').classList.remove('hidden');
    document.getElementById('token-set-form-title').textContent = '添加 Token 套餐';
    document.getElementById('edit-token-set-id').value = '';
    document.getElementById('ts-name-input').value = '';
    document.getElementById('ts-token-input').value = '';
    document.getElementById('ts-uuid-input').value = '';
    document.getElementById('ts-name-input').focus();
}

function cancelTokenSetForm() {
    document.getElementById('token-set-form').classList.add('hidden');
}

function editTokenSet(id, name, appUuid) {
    document.getElementById('token-set-form').classList.remove('hidden');
    document.getElementById('token-set-form-title').textContent = '编辑 Token 套餐';
    document.getElementById('edit-token-set-id').value = id;
    document.getElementById('ts-name-input').value = name;
    document.getElementById('ts-token-input').value = '';
    document.getElementById('ts-token-input').placeholder = '留空则不修改';
    document.getElementById('ts-uuid-input').value = appUuid;
}

async function saveTokenSet() {
    const editId = document.getElementById('edit-token-set-id').value;
    const name = document.getElementById('ts-name-input').value.trim();
    const token = document.getElementById('ts-token-input').value.trim();
    const appUuid = document.getElementById('ts-uuid-input').value.trim();

    if (!name || !appUuid) {
        alert('名称和 App UUID 不能为空');
        return;
    }
    if (!editId && !token) {
        alert('Token 不能为空');
        return;
    }

    const url = editId ? `/api/monitoring/token-sets/${editId}` : '/api/monitoring/token-sets';
    const method = editId ? 'PUT' : 'POST';
    const body = { name, app_uuid: appUuid };
    if (token) body.token = token;

    try {
        const response = await fetch(url, {
            method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const result = await response.json();
        if (result.success) {
            cancelTokenSetForm();
            loadTokenSets();
        } else {
            alert('操作失败: ' + result.error);
        }
    } catch (error) {
        alert('请求失败');
    }
}

async function testTokenSet(id) {
    try {
        const response = await fetch(`/api/monitoring/token-sets/${id}/test`, { method: 'POST' });
        const result = await response.json();
        alert(result.success ? result.message : '测试失败: ' + result.error);
    } catch (error) {
        alert('请求失败');
    }
}

async function deleteTokenSet(id) {
    if (!confirm('确定删除该 Token 套餐？')) return;
    try {
        const response = await fetch(`/api/monitoring/token-sets/${id}`, { method: 'DELETE' });
        const result = await response.json();
        if (result.success) {
            loadTokenSets();
        } else {
            alert('删除失败: ' + result.error);
        }
    } catch (error) {
        alert('请求失败');
    }
}
```

b) 删除旧的 token-form submit handler（lines 649-690）和 test-connection-btn handler（lines 692-718）

c) 在 `openTokenModal` 函数中调用 `loadTokenSets()` 替代 `loadTokenConfig()`

d) 在页面加载时（DOMContentLoaded 或现有的初始化逻辑中）调用 `loadTokenSets()` 以填充监测配置表单中的下拉框

e) 在 `openEditConfigModal` 函数中，填充表单后设置 `token-set-select` 的值：

```javascript
// 在 openEditConfigModal 填充其他字段之后添加
const tokenSetSelect = document.getElementById('token-set-select');
if (config.token_set_id) {
    tokenSetSelect.value = config.token_set_id;
} else {
    tokenSetSelect.value = '';
}
```

f) 在 monitoring-config-form 的 submit handler 中，`data` 对象添加：

```javascript
token_set_id: formData.get('token_set_id') || null
```

- [ ] **Step 4: 手动验证**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python code/web_app.py`

打开浏览器访问监测页面，验证：
1. 点击 Token 配置，可以添加/编辑/删除/测试 token 套餐
2. 创建/编辑监测配置时可以选择 token 套餐

- [ ] **Step 5: 运行全部测试**

Run: `cd /Users/rinz/Coding/boss-zhipin-web-ui && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: 提交**

```bash
git add code/templates/monitoring.html
git commit -m "feat: add token sets management UI and monitoring config dropdown"
```
