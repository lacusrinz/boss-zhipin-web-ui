# 51job 解析器开发进度

**日期**: 2026-03-25
**状态**: ✅ 已完成

---

## 功能概述

实现前程无忧（51job）职位信息解析器，完善多站点架构，支持自动识别平台。

---

## 完成的工作

### 1. 创建 51job 解析器

**文件**: `code/parsers/fiftyone_job.py`

- 实现 `FiftyOneJobParser` 类，继承 `BaseParser`
- 支持提取字段：
  - 职位名称 (`job_name`)
  - 薪资 (`salary`)
  - 公司名称 (`company`)
  - 公司 URL (`company_url`)
  - 工作地点 (`location`)
  - 平台标识 (`platform: '51job'`)

**HTML 选择器映射**:
| 字段 | 选择器 |
|------|--------|
| 职位名称 | `.jname` |
| 薪资 | `.sal` |
| 地点 | `.area .shrink-0` |
| 公司名称 | `.cname` |
| 公司 URL | `.comp[href]` |

### 2. 更新解析器注册表

**文件**: `code/parsers/__init__.py`

```python
from .fiftyone_job import FiftyOneJobParser

PARSERS = {
    'boss_zhipin': BossZhipinParser,
    '51job': FiftyOneJobParser,  # 新增
}

SUPPORTED_SITES = [
    {'code': 'boss_zhipin', 'name': 'BOSS直聘', 'enabled': True},
    {'code': '51job', 'name': '前程无忧', 'enabled': True},  # 已启用
    # ...
]
```

### 3. 修复 werkzeug 413 错误

**问题**: werkzeug 的 FormDataParser 有默认的内存限制（约 512KB），导致大表单数据被拒绝

**解决方案**:

**文件**: `code/web_app.py`

```python
# Monkey patch werkzeug 的 FormDataParser
from werkzeug.formparser import FormDataParser, default_stream_factory

original_init = FormDataParser.__init__

def patched_init(self, stream_factory=None, max_form_memory_size=None,
                 max_content_length=None, cls=None, max_form_parts=None):
    if max_form_memory_size is None:
        max_form_memory_size = 100 * 1024 * 1024  # 100MB
    if stream_factory is None:
        stream_factory = default_stream_factory
    original_init(self, stream_factory, max_form_memory_size,
                  max_content_length, cls, max_form_parts)

FormDataParser.__init__ = patched_init
```

### 4. 实现自动识别平台

**文件**:
- `code/parsers/base.py` - 添加 `detect()` 和 `detect_site()` 方法
- `code/parsers/boss_zhipin.py` - 添加 BOSS直聘检测逻辑
- `code/parsers/fiftyone_job.py` - 添加 51job 检测逻辑

**检测特征**:

BOSS直聘:
- `job-card-box` - 职位卡片 class
- `zhipin.com` - 域名
- `boss-name` - 企业名称 class

51job:
- `joblist-item` - 职位列表项 class
- `51job.com` - 域名
- `jname` - 职位名称简写

### 5. 修复模板表单问题

**文件**: `code/templates/paste.html`

**问题**: 站点选择框在 `<form>` 标签外部，导致 `site_code` 不被提交

**修复**: 将站点选择框移到 `<form>` 标签内部

### 6. 添加站点偏好记忆

**文件**: `code/templates/paste.html`

使用 `localStorage` 记住用户上次选择的站点，提升用户体验。

### 7. 更新 Web 界面

- 默认选择 "🔍 自动识别"
- 用户可选择手动指定平台
- 更新使用说明，强调自动识别功能

---

## 技术要点

### 解析器架构

```
code/parsers/
├── __init__.py           # 解析器注册表
├── base.py              # 基类，定义接口
├── boss_zhipin.py       # BOSS直聘解析器
└── fiftyone_job.py      # 51job解析器 (新增)
```

### 数据格式

所有解析器返回统一格式：
```python
{
    'job_name': str,
    'salary': str,
    'company': str,
    'company_url': str,
    'location': str,
    'experience': str,
    'education': str,
    'platform': str,     # 自动添加
    'source': str,       # 搜索关键词
    'collection_time': str  # 采集时间
}
```

---

## 测试结果

### 51job 解析器测试

- 测试文件: `data/51job.html` (1MB)
- 成功解析: 20 个职位
- 提取字段: 职位名称、薪资、公司、地点、公司URL
- 平台标识: `51job`

### Web 界面测试

- ✅ 自动识别 51job 数据
- ✅ 自动识别 BOSS直聘数据
- ✅ 手动选择平台功能正常
- ✅ 站点偏好记忆功能正常
- ✅ 大文件（1MB+）上传正常

---

## 已知限制

1. **51job 经验/学历字段**: HTML 中不直接显示，需要从 sensorsdata JSON 中提取（当前未实现）
2. **浏览器兼容性**: 需要现代浏览器支持 localStorage

---

## 后续优化建议

1. 实现 sensorsdata JSON 解析，获取完整的 51job 字段
2. 添加更多平台支持（智联招聘、猎聘等）
3. 添加数据验证和错误处理
4. 添加批量上传功能

---

## 代码变更摘要

### 新增文件
- `code/parsers/fiftyone_job.py` - 51job 解析器

### 修改文件
- `code/parsers/__init__.py` - 注册 51job 解析器
- `code/parsers/base.py` - 添加 detect() 方法
- `code/parsers/boss_zhipin.py` - 添加 detect() 方法
- `code/web_app.py` - 添加自动识别、修复 413 错误
- `code/templates/paste.html` - 修复表单、添加偏好记忆

---

## 部署说明

无需特殊部署步骤，代码已集成到现有系统：
- 解析器自动注册
- Web 界面自动更新
- 数据库表结构无需变更（已支持 platform 字段）

---

**文档版本**: 1.0
**最后更新**: 2026-03-25
