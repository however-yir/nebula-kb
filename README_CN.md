# LZKB

LZKB 是一个面向私有化部署和二次开发的企业级智能体与知识库平台（基于上游项目定制化 fork）。

## 这个 Fork 的定位

本仓库用于：
- 构建企业内部知识问答与智能助手；
- 基于业务场景定制模型路由与工具工作流；
- 去除上游品牌与默认配置耦合；
- 建立可长期独立演进的技术底座。

## 已完成的改造

### 1) 命名与命名空间
- 后端 Django 命名空间从 `maxkb` 迁移为 `lzkb`；
- 运行时 settings 模块改为 `lzkb.settings`；
- 前端全局对象从 `window.MaxKB` 改为 `window.LZKB`；
- 本地语言缓存键从 `MaxKB-locale` 改为 `LZKB-locale`；
- 前端默认标题改为 `LZKB`。

### 2) 配置去敏与安全加固
- 将敏感默认值改为占位符：
  - `CHANGE_ME_DB_PASSWORD`
  - `CHANGE_ME_REDIS_PASSWORD`
- 内置默认用户密码改为 `ChangeMe@1234!`（生产必须覆盖）；
- 在 `installer/start-all.sh` 增加占位密码启动拦截，防止误上线。

### 3) 配置模板补齐
- 新增根目录 [`config_example.yml`](./config_example.yml)（文件方式配置）；
- 新增根目录 [`.env.example`](./.env.example)（环境变量方式配置）；
- 推荐使用 `LZKB_` 前缀，同时兼容旧 `MAXKB_` 前缀，降低迁移成本。

### 4) 品牌与链接替换
- 已替换前端默认品牌字段和主要外链；
- 文档改写为 fork 项目视角，便于后续独立维护。

## 快速部署（Docker）

```bash
docker run -d \
  --name=lzkb \
  --restart=always \
  -p 8080:8080 \
  -e POSTGRES_PASSWORD='你的强密码' \
  -e REDIS_PASSWORD='你的强密码' \
  -e LZKB_CONFIG_TYPE=ENV \
  -e LZKB_DB_NAME=lzkb \
  -e LZKB_DB_HOST=127.0.0.1 \
  -e LZKB_DB_PORT=5432 \
  -e LZKB_DB_USER=root \
  -e LZKB_DB_PASSWORD='你的强密码' \
  -e LZKB_REDIS_HOST=127.0.0.1 \
  -e LZKB_REDIS_PORT=6379 \
  -e LZKB_REDIS_PASSWORD='你的强密码' \
  -v ~/.lzkb:/opt/maxkb \
  your-dockerhub-or-registry/lzkb:latest
```

访问地址：
- 管理端：`http://<你的地址>:8080/admin`
- 对话端：`http://<你的地址>:8080/chat`

## 本地开发

### 后端

```bash
python -m uv pip install -r pyproject.toml
python apps/manage.py migrate
python main.py dev web
```

### 前端

```bash
cd ui
npm install
npm run dev
```

## 与上游版本的主要差异

当前 fork 重点差异：
- 核心运行包命名去耦（`maxkb` -> `lzkb`）；
- 默认凭据与启动安全策略强化；
- 前端运行时品牌键值与文档替换；
- 面向独立仓库运营的部署与维护说明。

后续计划：
- 按业务域拆分与重构核心模块；
- 完善模型提供商抽象与插件治理；
- 补齐测试、质量门禁、依赖锁定和 CI 稳定性。

## 仓库描述与 Topics（建议）

建议仓库描述：

> LZKB - 面向私有化部署的企业级智能体与知识库平台。

建议 Topics：

`rag`, `agent`, `knowledge-base`, `django`, `vue`, `langchain`, `llm`, `self-hosted`, `enterprise-ai`, `workflow`

## 许可证

本项目基于 GPLv3 上游项目 fork，继续遵循 GPLv3 义务。

请参考：
- [LICENSE](./LICENSE)
- [NOTICE-LZKB.md](./NOTICE-LZKB.md)
