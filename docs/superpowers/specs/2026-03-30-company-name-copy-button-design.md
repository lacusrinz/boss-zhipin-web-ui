# 企业名称一键复制按钮

## 目标

在企业清单页（companies），为企业名称添加一键复制到剪贴板的功能。

## 改动范围

仅涉及 `code/templates/companies.html` 一个文件。

## 设计

在企业名称链接右侧添加一个小的复制图标按钮：

- **位置**：紧跟 `{{ company.name }}` 的 `</a>` 标签之后
- **图标**：内联 SVG clipboard 图标，Tailwind 样式，灰色小图标，hover 变深
- **行为**：点击时调用 `navigator.clipboard.writeText(company.name)`，成功后图标短暂变为勾号（1.5秒后恢复）作为视觉反馈
- **实现**：添加一个 `copyCompany(el, name)` JS 函数，按钮通过 `onclick` 调用，不引入任何新依赖
