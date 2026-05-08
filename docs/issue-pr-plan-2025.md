# 2025 Issue and PR Plan

## Project Complexity
- high

## Milestone Strategy
- M1(1-3月): 初始化与首批核心能力
- M2(4-7月): 核心扩展
- M3(8-10月): 修复与测试
- M4(11-12月): 文档与部署

## Issue Backlog
| # | Title | Labels | Milestone | Planned |
|---|---|---|---|---|
| #1 | 初始化 RAG 服务骨架与规范 | type:feature,priority:P2,area:init | M1(1-3月) | 2025-01 |
| #2 | 建立配置校验与环境分层 | type:feature,priority:P2,area:init | M1(1-3月) | 2025-01 |
| #3 | 实现文档摄取与分块管道 | type:feature,priority:P1,area:core | M1(1-3月) | 2025-02 |
| #4 | 实现向量索引与混合召回 | type:feature,priority:P2,area:core | M2(4-7月) | 2025-04 |
| #5 | 实现重排与引用生成能力 | type:feature,priority:P2,area:core | M2(4-7月) | 2025-06 |
| #6 | 修复长文档召回质量退化问题 | type:bug,priority:P1,area:bugfix | M3(8-10月) | 2025-08 |
| #7 | 补齐评测基线与引用回归测试 | type:test,priority:P2,area:test | M3(8-10月) | 2025-09 |
| #8 | 完善运维文档与定时重建部署 | type:docs,priority:P3,area:deploy | M4(11-12月) | 2025-11 |

## PR Cadence
- PR1 Foundation Setup: Closes #1, #2
- PR2 Core Chain A: Closes #3
- PR3 Core Chain B: Closes #4
- PR4 Core Hardening: Closes #5, #6
- PR5 Quality Gate: Closes #7
- PR6 Docs & Deploy: Closes #8

## Standard PR Template Fields
- Summary
- Linked Issue
- Test Evidence
- Risk
- Rollback
