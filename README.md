# LZKB - 本地知识库与检索增强平台 | Local Knowledge Base & Retrieval Platform

[![Build](https://github.com/however-yir/LZKB/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/however-yir/LZKB/actions/workflows/build-and-push.yml)
[![Docs](https://img.shields.io/badge/docs-README-0A7EFA)](https://github.com/however-yir/LZKB#readme)
[![License](https://img.shields.io/badge/license-GPL--3.0-16A34A)](./LICENSE)
[![Status](https://img.shields.io/badge/status-active-2563EB)](https://github.com/however-yir/LZKB)

> Status: `active`
>
> Upstream family: `MaxKB`
>
> Series: [local-ai-hub](https://github.com/however-yir/local-ai-hub) · [yourrag](https://github.com/however-yir/yourrag)

项目聚焦知识沉淀、检索问答与本地化部署，适合作为企业或个人知识中台能力底座。

## 项目快照

- 定位：知识库平台，而不是通用聊天工作台。
- 亮点：Django + PostgreSQL + Redis、多模型接入、知识运营、智能体工作流扩展。
- 最短运行路径：`python apps/manage.py migrate && python main.py dev web`
- 系列分工：`Local AI Hub` 管工作台体验，`LZKB` 管知识平台，`YourRAG` 管企业级 RAG/Agent 交付。

## AI 平台分工矩阵

| Repo | 主要角色 | 部署形态 | 最适合的场景 |
| --- | --- | --- | --- |
| `Local AI Hub` | 本地 AI 工作台 | 自托管工作台 | 模型接入、团队日用、统一入口 |
| `LZKB` | 知识库平台 | 本地优先平台 | 文档入库、知识运营、检索问答 |
| `YourRAG` | 企业 RAG/Agent 平台 | 企业交付导向 | 私有化部署、RAG + Agent 交付 |

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 目标与场景](#2-目标与场景)
- [3. 核心能力](#3-核心能力)
- [4. 技术栈](#4-技术栈)
- [5. 仓库结构](#5-仓库结构)
- [6. Quick Start](#6-quick-start)
- [7. 配置建议](#7-配置建议)
- [8. 开发与测试](#8-开发与测试)
- [9. 协作与发布](#9-协作与发布)
- [10. 路线图](#10-路线图)
- [11. 贡献指南](#11-贡献指南)
- [12. License](#12-license)

## 1. 项目概述

本仓库以工程化可维护为目标，强调文档清晰、结构稳定、可持续迭代。

## 2. 目标与场景

适用场景：

- 作为业务功能开发与验证的基础仓库。
- 作为团队内部协作与知识沉淀的载体。
- 作为后续扩展和二次开发的起点。

## 3. 核心能力

- 支持知识入库、索引、检索与问答闭环。
- 支持本地化部署与可控的数据边界。
- 支持持续扩展知识源与应用场景。

## 4. 技术栈

- Python
- Django
- PostgreSQL
- Redis

## 5. 仓库结构

建议优先阅读：

- `README.md`：项目入口与整体说明。
- `README_CN.md`：更细化的中文交付说明。
- `apps/`、`ui/`：后端与界面主目录。
- `installer/`：安装、初始化与部署辅助脚本。

## 6. Quick Start

1. 克隆仓库并进入目录：

```bash
git clone https://github.com/however-yir/LZKB.git
cd LZKB
```

2. 安装依赖并初始化：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f pyproject.toml ] && pip install -e .
python apps/manage.py migrate
```

3. 启动开发环境：

```bash
python main.py dev web
```

## 7. 配置建议

建议按 `dev / staging / prod` 分层配置，并将密钥类信息放入环境变量或密钥管理系统。

## 8. 开发与测试

推荐流程：

1. 基于默认分支创建功能分支。
2. 小步提交并保持提交目标单一。
3. 本地完成构建与测试后再推送。
4. 通过 Pull Request 完成评审与合并。

## 9. 协作与发布

建议使用语义化版本，发布说明应包含新增、修复与兼容性说明。

## 10. 路线图

建议按以下顺序推进：

1. 稳定主流程与关键接口。
2. 优化模块边界与可观测性。
3. 完善自动化测试与文档体系。

## 11. 贡献指南

提交建议包含：变更背景、实现说明、验证结果、风险评估。

## 12. License

请以仓库内现有 License 文件为准。
