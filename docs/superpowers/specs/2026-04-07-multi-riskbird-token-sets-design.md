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

```sql
CREATE TABLE riskbird_token_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    token TEXT NOT NULL,
    app_uuid TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- `token` — 使用 TokenService 加密存储
- `app_uuid` — 明文存储（与现有逻辑一致）
- `name` — 备注名称，用于在监测配置下拉框中区分不同套餐

### `monitoring_configs` 表新增字段

```sql
ALTER TABLE monitoring_configs ADD COLUMN token_set_id INTEGER REFERENCES riskbird_token_sets(id);
```

- `token_set_id` — 关联的 token 套餐 ID，为 NULL 时使用旧的 `riskbird_config` 中的 token（向后兼容过渡期）

### 数据库操作（database.py 新增）

- `insert_token_set(name, token, app_uuid)` — 新增 token 套餐
- `get_token_set(id)` — 获取单个 token 套餐（返回加密值）
- `get_all_token_sets()` — 获取所有 token 套餐列表（token 脱敏）
- `get_token_set_decrypted(id)` — 获取解密后的 token 套餐
- `update_token_set(id, name, token, app_uuid)` — 更新 token 套餐
- `delete_token_set(id)` — 删除 token 套餐

## API 层

### 新增/修改的路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitoring/token-sets` | 获取所有 token 套餐列表（token 脱敏） |
| POST | `/api/monitoring/token-sets` | 新增 token 套餐 |
| PUT | `/api/monitoring/token-sets/<id>` | 更新 token 套餐 |
| DELETE | `/api/monitoring/token-sets/<id>` | 删除 token 套餐 |
| POST | `/api/monitoring/token-sets/<id>/test` | 测试指定 token 套餐连通性 |

### 监测配置 API 修改

创建/编辑监测配置时，新增 `token_set_id` 参数。返回监测配置时包含关联的 token 套餐名称。

## UI 层

### Token 配置模态框改动

现有模态框中 Token 配置区域改为列表形式：

- 每行显示：名称、token（脱敏）、app_uuid、操作按钮（编辑/测试/删除）
- 底部「添加 token 套餐」按钮，点击弹出内联表单填写 name/token/app_uuid
- 编辑时同样使用内联表单

### 监测配置表单改动

编辑监测配置的表单中，新增一个下拉框「Token 套餐」，选项来自 `riskbird_token_sets` 表，显示套餐名称。

## 执行层

`riskbird_monitor.py` 执行监测任务时：

1. 从 `monitoring_configs` 获取 `token_set_id`
2. 若 `token_set_id` 存在，从 `riskbird_token_sets` 取对应套餐的 token（解密）和 app_uuid
3. 若 `token_set_id` 为空，回退到旧的 `riskbird_config` 取值（向后兼容）
4. 后续 API 调用逻辑不变

## 迁移策略

- 旧的 `riskbird_config` 表和 `/api/monitoring/token` 相关路由保留不动，不删除
- 用户在新的 token 套餐管理界面手动添加后，编辑监测配置选择对应套餐即可
- 过渡期两种方式并存
