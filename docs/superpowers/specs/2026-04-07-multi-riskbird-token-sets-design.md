# 多 Token 套餐支持设计

## 背景

企业监测模块通过 RiskBird API 进行监测，当前仅支持配置单个 token（含 app_uuid）。由于接口限制，单 token 不足以支撑监测任务，需要支持配置多个 token 套餐，并在监测配置中指定使用哪个套餐。

## 需求

1. 支持配置多个「token 套餐」，每个套餐包含：备注名称、token、app_uuid
2. 在监测配置中手动选择使用哪个 token 套餐
3. Token 管理界面继续放在现有的监测页面模态框内
4. 现有单个 token 不做自动迁移，由用户手动重新配置

## 数据层

### 新表 `riskbird_token_sets`

在 `database.py` 的 `init_monitoring_tables()` 中，跟随现有建表逻辑一起创建。

```sql
CREATE TABLE IF NOT EXISTS riskbird_token_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    token TEXT NOT NULL,
    app_uuid TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `name` — 备注名称，UNIQUE 约束防止重名导致下拉框混淆
- `token` — 调用方负责加密/解密（TokenService），数据库层只做存储，与现有 `riskbird_config` 模式一致
- `app_uuid` — 明文存储（与现有逻辑一致）
- 不设 `is_active` 字段，不需要禁用功能，保持简单

### `monitoring_configs` 表新增字段

在 `database.py` 的 `_migrate_monitoring_tables()` 中通过 ALTER TABLE 添加（与现有迁移模式一致）：

```sql
ALTER TABLE monitoring_configs ADD COLUMN token_set_id INTEGER REFERENCES riskbird_token_sets(id) ON DELETE SET NULL;
```

- `token_set_id` — 关联的 token 套餐 ID
- `ON DELETE SET NULL` — 若 token 套餐被删除，自动置 NULL，回退到旧 token
- `update_monitoring_config` 的 `ALLOWED_COLUMNS` 需新增 `'token_set_id'`

### 数据库操作（database.py 新增）

数据库层只负责存取，不处理加密/解密：

- `insert_token_set(name, token, app_uuid)` — 新增 token 套餐（token 参数已经是加密后的值）
- `get_token_set(id)` — 获取单个 token 套餐（返回原始加密值）
- `get_all_token_sets()` — 获取所有 token 套餐（返回原始加密值，由调用方脱敏）
- `update_token_set(id, **kwargs)` — 更新 token 套餐（显式设置 `updated_at = CURRENT_TIMESTAMP`）
- `delete_token_set(id)` — 删除 token 套餐
- `get_monitoring_configs_with_token_set()` — JOIN 查询，返回监测配置及关联的 token 套餐名称

## API 层

### 新增路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitoring/token-sets` | 获取所有 token 套餐列表（解密后脱敏显示） |
| POST | `/api/monitoring/token-sets` | 新增 token 套餐（加密后存储） |
| PUT | `/api/monitoring/token-sets/<id>` | 更新 token 套餐 |
| DELETE | `/api/monitoring/token-sets/<id>` | 删除 token 套餐 |
| POST | `/api/monitoring/token-sets/<id>/test` | 测试连通性（解密后调用 `call_riskbird_search_api`，与现有 `/api/monitoring/token/test` 模式一致） |

### Token 脱敏方式

GET 列表接口中：从数据库取出加密 token → `TokenService.decrypt()` → `TokenService.mask_token()` → 返回脱敏值。与现有 `GET /api/monitoring/token` 处理方式一致。

### 监测配置 API 修改

- 创建/编辑监测配置：新增 `token_set_id` 参数
- `update_monitoring_config` 的 `ALLOWED_COLUMNS` 新增 `'token_set_id'`
- 查询监测配置列表时 JOIN `riskbird_token_sets`，返回关联的 `token_set_name`

## UI 层

### Token 配置模态框改动

现有模态框中 Token 配置区域改为列表形式：

- 每行显示：名称、token（脱敏）、app_uuid、操作按钮（编辑/测试/删除）
- 底部「添加 token 套餐」按钮，点击弹出内联表单填写 name/token/app_uuid
- 编辑时同样使用内联表单
- 保留原有的单 token 配置区域不动（向后兼容）

### 监测配置表单改动

编辑监测配置的表单中，新增一个下拉框「Token 套餐」：

- 选项来自 `riskbird_token_sets` 表，显示套餐名称
- 包含一个「默认（旧配置）」选项，对应 `token_set_id = NULL`，使用旧的 `riskbird_config` 中的 token
- 已有配置若 `token_set_id` 为 NULL，默认选中「默认（旧配置）」

## 执行层

`riskbird_monitor.py` 执行监测任务时：

1. 从 `monitoring_configs` 获取 `token_set_id`
2. 若 `token_set_id` 存在，从 `riskbird_token_sets` 取 token 和 app_uuid，用 `TokenService.decrypt()` 解密 token
3. 若 `token_set_id` 为空，回退到旧的 `riskbird_config` 取值（与现有逻辑完全一致）
4. 后续 API 调用逻辑不变

## 迁移策略

- 新表创建放在 `init_monitoring_tables()` 中
- 字段迁移放在 `_migrate_monitoring_tables()` 中（与现有迁移模式一致）
- 不需要独立的迁移脚本
- 旧的 `riskbird_config` 表和 `/api/monitoring/token` 相关路由保留不动
- 过渡期两种方式并存
