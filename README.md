# LZKB - 本地知识库与检索增强平台 | Local Knowledge Base & Retrieval Platform

[![Build](https://github.com/however-yir/LZKB/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/however-yir/LZKB/actions/workflows/build-and-push.yml)
[![Docs](https://img.shields.io/badge/docs-README-0A7EFA)](https://github.com/however-yir/LZKB#readme)
[![License](https://img.shields.io/badge/license-GPL--3.0-16A34A)](./LICENSE)
[![Status](https://img.shields.io/badge/status-active-2563EB)](https://github.com/however-yir/LZKB)

> Status: `active`
>
> Upstream family: `MaxKB`

> **非官方声明（Non-Affiliation）**  
> 本仓库为社区维护的衍生/二次开发版本，与上游项目及其权利主体不存在官方关联、授权背书或从属关系。  
> **商标声明（Trademark Notice）**  
> 相关项目名称、Logo 与商标归其各自权利人所有。本仓库仅用于说明兼容/来源，不主张任何商标权利。
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

相对同系列仓库的职责边界：

- `Local AI Hub` 更像工作台与统一入口。
- `LZKB` 更像知识入库、知识运营与检索问答平台。
- `YourRAG` 更偏企业级私有化交付与 Agent 组合能力。

## 3. 核心能力

- 支持知识入库、索引、检索与问答闭环。
- 支持本地化部署与可控的数据边界。
- 支持持续扩展知识源与应用场景。

### 3.1 典型用例

| 场景 | 主要模块 | 目标结果 |
|---|---|---|
| 文档入库与解析 | `apps/knowledge` | 把资料转为可检索知识资产 |
| 检索问答与运营 | `apps/chat`, `ui/` | 形成知识问答与后台运营闭环 |
| 模型接入与切换 | `apps/models_provider`, `apps/local_model` | 对接本地或远端模型 |
| 安装与部署 | `installer/` | 本地快速起服与依赖初始化 |
| 应用扩展 | `apps/application`, `appstore/lzkb.json` | 面向后续插件化或应用化拓展 |

### 3.2 模块职责矩阵

| 路径 | 角色 |
|---|---|
| `apps/knowledge` | 知识库核心、入库与检索相关能力 |
| `apps/chat` | 问答交互与知识调用入口 |
| `apps/models_provider` | 模型提供方接入层 |
| `apps/common` / `apps/system_manage` | 平台公共与系统管理能力 |
| `installer/` | 本地部署、数据库与 Redis 启动辅助 |
| `ui/` | 管理后台与交互前端 |

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

### 6.1 本地依赖一键准备（PostgreSQL / Redis / 可选 Ollama）

首次启动建议先执行：

```bash
cp .env.example .env
# 修改 .env 中所有 CHANGE_ME_* 密码

./scripts/bootstrap-local.sh --start
# 如需一起拉起 Ollama:
# ./scripts/bootstrap-local.sh --start --with-ollama
```

该脚本会：

1. 校验 `.env` 是否存在并阻止占位密码直接启动；
2. 按 `docker-compose.dev.yml` 拉起 PostgreSQL / Redis；
3. 自动确保 `pgvector` 扩展已启用；
4. 可选拉起本地 Ollama，降低首次联调门槛。

### 6.2 极速安装脚本（macOS / Windows）

macOS:

```bash
./scripts/quick-install-mac.sh
# 如需一起拉起 Ollama:
# ./scripts/quick-install-mac.sh --with-ollama
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-install-win.ps1
# 如需一起拉起 Ollama:
# powershell -ExecutionPolicy Bypass -File .\scripts\quick-install-win.ps1 -WithOllama
```

快速脚本会自动完成：

1. 初始化 `.env` 并替换 `CHANGE_ME_*` 占位密钥；
2. 创建 `.venv` 并安装 Python 依赖；
3. 拉起 PostgreSQL / Redis（可选 Ollama）并确保 `pgvector`；
4. 执行数据库迁移。

## 7. 配置建议

建议按 `dev / staging / prod` 分层配置，并将密钥类信息放入环境变量或密钥管理系统。

### 7.1 部署形态矩阵

| 形态 | 入口 | 适合场景 |
|---|---|---|
| 开发模式 | `python main.py dev web` | 本地功能开发 |
| 一键本地启动 | `installer/start-all.sh` | 演示与快速验证 |
| 分组件启动 | `installer/start-postgres.sh` / `installer/start-redis.sh` / `installer/start-maxkb.sh` | 更接近生产的联调环境 |
| 可运维分离部署 | `docker compose -f deploy/docker-compose.operational.yml up -d` | web / worker / scheduler / PostgreSQL / Redis / object storage 独立部署 |

运维部署、环境变量契约、健康检查、备份恢复和回滚流程见 [docs/ops/operability.md](docs/ops/operability.md) 与 [docs/ops/postgres-backup-restore.md](docs/ops/postgres-backup-restore.md)。

## 8. 开发与测试

推荐流程：

1. 基于默认分支创建功能分支。
2. 小步提交并保持提交目标单一。
3. 本地完成构建与测试后再推送。
4. 通过 Pull Request 完成评审与合并。

### 8.1 评测与验收路径

建议把以下链路作为最小验收闭环：

1. 导入一组真实文档并验证索引完成。
2. 对同一问题做检索命中检查与答案可解释性检查。
3. 验证不同模型提供方下的响应一致性与延迟。
4. 校验后台管理入口、知识集管理与权限边界是否稳定。

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
