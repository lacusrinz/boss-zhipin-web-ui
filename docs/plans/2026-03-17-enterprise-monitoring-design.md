# 新企业监测模块设计文档

**创建日期：** 2026-03-17
**作者：** Claude + 用户
**状态：** 待实施

## 1. 概述

在现有BOSS直聘岗位管理系统基础上，添加一个基于RiskBird API的新企业自动监测模块，实现对当天成立企业的定时监测和数据管理。

## 2. 核心需求

- **监测标准：** 查询当天成立的企业
- **地区范围：** 可配置地区（支持多选）
- **数据存储：** 存储到新表（monitored_companies）
- **页面展示：** 独立监测管理页面（/monitoring）
- **调度方式：** APScheduler集成到Flask，每5分钟执行一次
- **Token管理：** 页面可配置和更新RiskBird API Token

## 3. 整体架构

```
用户界面层（/monitoring）
    ├── Token配置管理
    ├── 监测任务配置
    ├── 任务控制面板
    └── 数据展示与统计

应用层（Flask + APScheduler）
    ├── API路由
    ├── 任务调度器
    ├── Token管理服务
    └── 监测任务执行

数据层（SQLite）
    ├── riskbird_config（Token配置）
    ├── monitoring_configs（监测配置）
    └── monitored_companies（监测结果）

外部服务
    └── RiskBird API（企业查询）
```

## 4. 数据库设计

### 4.1 riskbird_config - Token配置表

```sql
CREATE TABLE riskbird_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,     -- 配置键名
    config_value TEXT,                    -- 配置值（加密存储）
    is_active BOOLEAN DEFAULT 1,          -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT DEFAULT 'system'      -- 更新者标识
);
```

**初始配置项：**
- `token`: JWT Token
- `app_uuid`: App设备UUID
- `userinfo`: 用户信息JSON（可选）

### 4.2 monitoring_configs - 监测配置表

```sql
CREATE TABLE monitoring_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name TEXT NOT NULL,            -- 配置名称
    region_codes TEXT NOT NULL,           -- 地区代码（JSON数组）
    is_active BOOLEAN DEFAULT 1,          -- 是否启用
    interval_minutes INTEGER DEFAULT 5,   -- 监测间隔（分钟）
    reg_cap TEXT,                         -- 注册资本筛选（可选）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 monitored_companies - 监测结果表

```sql
CREATE TABLE monitored_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER,                    -- 关联配置ID
    company_name TEXT NOT NULL,           -- 企业名称
    credit_code TEXT UNIQUE,              -- 统一社会信用代码（去重）
    reg_date TEXT,                        -- 成立日期
    reg_cap TEXT,                         -- 注册资本
    region_code TEXT,                     -- 地区代码
    region_name TEXT,                     -- 地区名称
    legal_representative TEXT,            -- 法人代表
    contact TEXT,                         -- 联系方式
    address TEXT,                         -- 企业地址
    business_scope TEXT,                  -- 经营范围
    monitoring_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'riskbird',       -- 数据来源
    is_processed BOOLEAN DEFAULT 0,       -- 是否已处理
    notes TEXT,                           -- 备注
    FOREIGN KEY (config_id) REFERENCES monitoring_configs (id)
);
```

**索引：**
```sql
CREATE INDEX idx_company_name ON monitored_companies(company_name);
CREATE INDEX idx_monitoring_time ON monitored_companies(monitoring_time);
CREATE INDEX idx_config_time ON monitored_companies(config_id, monitoring_time);
CREATE UNIQUE INDEX idx_credit_code ON monitored_companies(credit_code);
```

## 5. API端点设计

### 5.1 Token管理

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/monitoring/token` | GET | 获取Token配置（脱敏） |
| `/api/monitoring/token` | POST | 保存/更新Token |
| `/api/monitoring/token/test` | POST | 测试Token连接性 |

### 5.2 监测配置管理

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/monitoring/configs` | GET | 获取所有配置 |
| `/api/monitoring/configs` | POST | 创建新配置 |
| `/api/monitoring/configs/<id>` | PUT | 更新配置 |
| `/api/monitoring/configs/<id>` | DELETE | 删除配置 |

### 5.3 任务控制

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/monitoring/jobs` | GET | 获取任务状态列表 |
| `/api/monitoring/jobs/<id>/toggle` | POST | 暂停/恢复任务 |
| `/api/monitoring/jobs/<id>/run-now` | POST | 立即执行一次 |

### 5.4 数据查询

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/monitoring/companies` | GET | 获取监测企业列表 |
| `/api/monitoring/stats` | GET | 获取统计数据 |
| `/api/monitoring/regions` | GET | 获取地区列表 |

## 6. 监测任务流程

### 6.1 执行流程

```
调度器触发
    ↓
读取监测配置（monitoring_configs）
    ↓
读取Token配置（riskbird_config）
    ↓
构建RiskBird请求参数
    ↓
调用RiskBird API
    ↓
解析响应JSON
    ↓
检查credit_code去重
    ↓
批量插入新数据（monitored_companies）
    ↓
记录本次统计日志
    ↓
更新下次执行时间
```

### 6.2 核心函数

**`riskbird_monitor.py`**
```python
def run_monitoring_task(config_id):
    """执行单次监测任务"""

def build_search_params_from_config(config):
    """从配置构建搜索参数"""

def parse_riskbird_response(response):
    """解析API响应"""

def save_companies_to_db(companies, config_id):
    """保存企业数据到数据库"""

def test_token_connection(token, app_uuid):
    """测试Token连接性"""
```

## 7. 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| Token过期/无效 | 标记token无效，暂停任务，页面显示警告 |
| API请求超时 | 3次重试（间隔5秒），仍失败则跳过本次 |
| API返回错误 | 记录日志，根据错误码决定是否暂停 |
| 数据库连接失败 | 发送告警，暂停所有任务 |
| 重复数据 | 通过credit_code去重，跳过已存在记录 |
| 响应格式变化 | 保存原始响应，任务继续运行 |

## 8. 前端页面设计

### 8.1 页面结构（monitoring.html）

```
┌─────────────────────────────────────────┐
│  导航栏：首页 | 岗位 | 企业 | 监测        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Token配置卡                             │
│  - Token输入框                           │
│  - App UUID输入框                        │
│  - 保存/测试连接按钮                     │
│  - 状态显示                              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  监测配置卡                              │
│  - 配置名称                              │
│  - 地区多选                              │
│  - 时间间隔                              │
│  - 创建配置按钮                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  任务控制面板                            │
│  - 任务列表（配置名、状态、下次执行时间） │
│  - 启动/暂停/执行按钮                    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  数据展示区                              │
│  - 统计卡片（总数、今日新增、待处理）     │
│  - 企业列表表格                          │
│  - 筛选和分页                            │
└─────────────────────────────────────────┘
```

### 8.2 安全措施

- Token加密存储（cryptography库）
- 页面显示脱敏（只显示前8位和后4位）
- 记录Token更新历史
- CSRF保护

## 9. 部署清单

### 9.1 新增依赖

```
APScheduler==3.10.4
cryptography==41.0.7
```

### 9.2 新增文件

```
code/riskbird_monitor.py          # 监测任务核心逻辑
code/templates/monitoring.html    # 监测管理页面
tests/test_monitoring.py          # 测试文件
```

### 9.3 修改文件

```
code/web_app.py                   # 集成调度器和路由
code/database.py                  # 添加新表操作方法
requirements.txt                  # 添加新依赖
```

## 10. 测试计划

### 10.1 单元测试

- API请求构建测试
- 数据库CRUD测试
- 去重逻辑测试
- Token加密/解密测试

### 10.2 集成测试

- 端到端流程测试
- Token失效场景测试
- 重复数据处理测试

### 10.3 手动测试清单

- [ ] Token保存和更新
- [ ] Token连接测试
- [ ] 创建监测配置
- [ ] 启动/暂停任务
- [ ] 手动触发监测
- [ ] 查看监测结果
- [ ] Token过期提示
- [ ] 数据去重验证
- [ ] 地区筛选功能
- [ ] 分页查询功能

## 11. 性能优化

- 数据库连接池
- 批量插入操作
- 建立合适索引
- 支持分页查询
- 定期清理历史数据（可选）

## 12. 后续扩展

- 支持多种监测条件（行业、注册资本等）
- 支持数据导出（Excel）
- 添加企业详情查看
- 邮件/微信告警通知
- 数据可视化图表
