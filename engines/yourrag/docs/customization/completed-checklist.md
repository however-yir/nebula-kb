# YourRAG Customization Checklist (Completed)

1. [x] 新仓库初始化并公开发布到 GitHub。
2. [x] 项目主品牌名替换为 `YourRAG`。
3. [x] 默认管理员邮箱改为 `admin@yourrag.local`。
4. [x] 默认管理员密码改为 `change_me_please`。
5. [x] Docker 默认镜像仓库改为 `however-yir/yourrag`。
6. [x] Docker Compose 项目名改为 `yourrag`。
7. [x] 默认注册开关改为生产更安全的 `REGISTER_ENABLED=0`。
8. [x] MySQL 默认数据库名改为 `yourrag`。
9. [x] OceanBase/SeekDB 默认业务库名改为 `yourrag_doc`。
10. [x] Helm Chart 名称改为 `yourrag`。
11. [x] Python 主包名称调整为 `yourrag`。
12. [x] Python SDK 包名称调整为 `yourrag-sdk`。
13. [x] Admin CLI 包名称调整为 `yourrag-cli`。
14. [x] Go module 从 `ragflow` 迁移为 `yourrag`。
15. [x] Go 内部 import 路径完成批量迁移到 `yourrag/...`。
16. [x] 管理端/服务端 token 前缀切换为 `yourrag-`。
17. [x] 保留旧 token 前缀 `ragflow-` 的兼容解析。
18. [x] Redis 系统密钥命名空间切换为 `yourrag:system:secret_key`。
19. [x] `service_conf.yaml` 顶层服务键从 `ragflow` 改为 `yourrag`。
20. [x] 保留旧配置键 `ragflow` 的兼容读取能力。
21. [x] 私钥硬编码口令 `Welcome` 改为环境变量优先策略。
22. [x] 私钥路径改为环境变量可配置。
23. [x] 公钥路径改为环境变量可配置。
24. [x] 新增 RSA 密钥一键生成脚本 `tools/scripts/generate_rsa_keys.sh`。
25. [x] `conf/private.pem` 与 `conf/public.pem` 从仓库移除并加入 `.gitignore`。
26. [x] 新增 `conf/private.pem.example` 与 `conf/public.pem.example` 模板占位。
27. [x] 前端登录加密改为“RSA 可选 + base64 回退”模式。
28. [x] Admin CLI 登录加密改为“RSA 可选 + base64 回退”模式。
29. [x] CI 工作流重构为 GitHub Hosted Runner 通用流水线。
30. [x] 新增部署文档：单机部署。
31. [x] 新增部署文档：Docker Compose。
32. [x] 新增部署文档：Kubernetes/Helm。
33. [x] README 重写为项目化说明（用途、差异、部署入口）。
34. [x] 清理 README 中机器式“继续第二阶段”提示语。
35. [x] 保留上游许可证与归属文件，补充二次开发说明。
