# NebulaKB 产品视觉设计系统

NebulaKB 的产品定位是：知识运营中枢。

## 品牌资产锁定

- 产品名：NebulaKB
- 仓库名：nebula-kb
- 前端包名：nebula-ui
- Docker 镜像命名空间：nebulakb/*
- 官网域名：https://nebulakb.ai
- 文档域名：https://docs.nebulakb.ai
- 域名契约：[domain-contract.md](./domain-contract.md)

## 字体

- 中文界面：PingFang SC、AlibabaPuHuiTi
- 英文与数字：Inter、system-ui
- 代码与哈希：ui-monospace、SFMono-Regular、Menlo、Monaco

## 色板

| Token | Value | 用途 |
| --- | --- | --- |
| nebula-teal | `#14b8a6` | 主品牌、健康、成功 |
| nebula-blue | `#3370ff` | 主要操作、链接、可点击状态 |
| nebula-orange | `#f97316` | 风险、提醒、待处理 |
| nebula-violet | `#7c3aed` | 实验、版本、智能能力 |
| nebula-ink | `#111827` | 标题与关键数值 |
| nebula-surface | `#f5f6f7` | 页面背景 |

## 图标规范

- 通用操作优先使用 Element Plus 线性图标。
- 业务图标统一注册到 `ui/src/components/app-icon`，禁止在业务页面复制临时 SVG。
- 顶部导航图标保持 16px，工具按钮图标保持 14-16px。

## 界面原则

- 运营后台优先保证扫描效率、状态密度和可操作性。
- 卡片只用于重复项、模块面板和数据看板，不把页面区块套进装饰容器。
- 新能力入口先进入「知识运营」顶层模块，再按后端 API 成熟度拆成独立页面。
