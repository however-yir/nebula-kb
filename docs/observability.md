# NebulaKB 运营指标与可观测基线

NebulaKB 的可观测重点不是模型调用次数，而是知识资产是否被有效使用、是否持续变好、反馈是否闭环。

## 核心指标

| 指标 | 口径 | 运营动作 |
|---|---|---|
| 知识命中率 | 有有效引用的问答次数 / 总问答次数 | 低于阈值时排查知识缺失、切片和召回策略 |
| 低质答案率 | 评分小于等于 2 的反馈数 / 全部反馈数 | 高于阈值时进入低质答案回看 |
| 未命中问题 | 没有有效检索结果的问题集合 | 聚类后决定补充知识或优化同义词 |
| 热门知识 | 按引用次数排序的文档或切片 | 高频知识缩短复核周期 |
| 待更新知识 | 过期、失败、高低评、高未命中的知识 | 生成治理任务并分派负责人 |
| 反馈闭环状态 | open、assigned、fixed、closed 的数量 | 长期 open 需要运营负责人介入 |

## 建议事件

| 事件 | 关键字段 |
|---|---|
| `knowledge.document_uploaded` | tenant_id、knowledge_base_id、document_id、filename、operator |
| `knowledge.document_parse_failed` | tenant_id、document_id、filename、reason |
| `knowledge.document_indexed` | tenant_id、document_id、chunk_count、duration_ms |
| `knowledge.answer_generated` | tenant_id、knowledge_base_id、question_id、hit_count、citation_count、fallback_reason |
| `knowledge.feedback_submitted` | tenant_id、question_id、rating、reason、citation_count |
| `knowledge.feedback_closed` | tenant_id、feedback_id、owner、duration_hours |

## 建议日志字段

所有结构化日志建议包含：

- `tenant_id`
- `knowledge_base_id`
- `document_id`
- `question_id`
- `feedback_id`
- `operator`
- `request_id`
- `trace_id`
- `status`
- `error_code`
- `duration_ms`
- `slow_query_ms`
- `slow_retrieval_ms`

`X-Request-ID` 是跨网关、后端、worker 和客户端排查的主关联字段；如果请求未携带，后端由 `common.middleware.tracing.OTelTracingMiddleware` 生成并回写到响应头。

## OpenTelemetry 与追踪

默认追踪边界：

| Span | 关键属性 |
| --- | --- |
| HTTP 请求 | `http.method`、`http.url`、`http.status_code`、`correlation_id` |
| 文档解析 | `tenant_id`、`document_id`、`status`、`duration_ms` |
| 检索 | `tenant_id`、`knowledge_base_id`、`hit_count`、`slow_retrieval_ms` |
| 反馈闭环 | `tenant_id`、`feedback_id`、`status`、`duration_ms` |

OpenTelemetry exporter 可按部署环境接入 Collector、Tempo、Jaeger 或云厂商链路系统。没有安装 OpenTelemetry 包时，中间件保持 no-op，但仍生成 `X-Request-ID`。

## 建议告警

| 告警 | 阈值示例 | 说明 |
|---|---|---|
| 知识命中率下降 | 24 小时低于 70% | 可能出现新业务问题或知识缺失 |
| 低质答案率升高 | 24 小时高于 10% | 需要质检回看 |
| 解析失败积压 | failed 文档超过 20 个 | 可能是格式兼容或 OCR 问题 |
| 反馈未闭环 | open 超过 7 天 | 运营处理超时 |
| 无引用答案异常 | citation_count 为 0 且未触发兜底 | 可能存在回答策略风险 |

## 指标命名建议

```text
nebula_kb_answer_total
nebula_kb_answer_with_citation_total
nebula_kb_answer_fallback_total
nebula_kb_feedback_total
nebula_kb_feedback_low_quality_total
nebula_kb_document_uploaded_total
nebula_kb_document_parse_failed_total
nebula_kb_document_indexed_total
nebula_kb_feedback_open_total
nebula_kb_feedback_closed_total
nebula_kb_request_duration_seconds
nebula_kb_slow_query_total
nebula_kb_slow_retrieval_total
nebula_kb_celery_task_total
nebula_kb_celery_task_failed_total
```

Prometheus 拉取目标：

```text
GET /metrics
```

Grafana 基线看板：`deploy/grafana/dashboards/nebula-kb-overview.json`。

## 健康看板

第一版看板建议分成四块：

1. 入库健康：上传量、解析失败、索引成功、平均处理时长。
2. 检索健康：总问答、命中问答、空结果兜底、引用数量。
3. 反馈健康：反馈量、低质答案率、回看队列、闭环时长。
4. 知识治理：热门知识、待更新知识、未命中问题聚类。

## 验证方式

本仓库的最小 demo 引擎通过 `KnowledgeAssetPlatform.metrics()` 输出同名业务指标快照。运行：

```bash
python3 scripts/demo_lifecycle.py
```

输出中应包含：

- `knowledge_hit_rate`
- `low_quality_answer_rate`
- `unanswered_questions`
- `hot_knowledge`
- `stale_knowledge`
- `feedback_closure_status`

发布验收同时运行：

```bash
bash scripts/quality-gate.sh api-security-release
```

该 gate 会检查 API v1、OpenAPI、主路径 E2E、安全头、上传 MIME/大小、生产安全检查命令、部署文档、Prometheus、OpenTelemetry、Grafana 和 `X-Request-ID` 基线。
