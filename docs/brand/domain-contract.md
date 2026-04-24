# NebulaKB 域名与链接契约

NebulaKB 使用独立官网域名和文档域名：

| 用途 | 域名 | 说明 |
| --- | --- | --- |
| 官网 | `https://nebulakb.ai` | 产品首页、定价、联系入口、品牌资产入口 |
| 文档 | `https://docs.nebulakb.ai` | 部署、API、企业交付、安全和运维文档 |
| GitHub | `https://github.com/however-yir/nebula-kb` | 源码、Issue、Release 和安全公告 |
| App Store 清单 | `https://raw.githubusercontent.com/however-yir/nebula-kb/main/appstore/nebula.json` | 场景化助手与扩展清单 |

## 路由要求

- 官网首页必须突出产品定位：知识运营中枢。
- 文档站首页必须提供部署、API、企业交付、安全、运维五个入口。
- 旧的 LZKB 链接应使用 301 跳转到对应 NebulaKB 链接，不再在新页面暴露旧品牌。
- 站内产品链接统一读取 `NEBULA_OFFICIAL_SITE_URL`、`NEBULA_DOCS_URL`、`NEBULA_PROJECT_URL`。

## 发布要求

- GitHub 仓库 description 指向知识运营中枢。
- Release notes、镜像说明、README 和文档站导航必须使用 NebulaKB。
- 安全联系邮箱使用 `security@nebulakb.ai`。
