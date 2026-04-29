# NebulaKB 演示脚本

本脚本用于 15 到 20 分钟内讲清 NebulaKB 的边界和价值：它不是 Spring AI 企业后端项目，而是知识资产的入库、治理、检索、反馈和运营后台。

## 演示目标

- 证明 NebulaKB 有清晰产品定位：知识资产生命周期平台。
- 证明演示链路完整：导入、解析、切片、索引、检索问答、人工反馈、低质答案回看。
- 证明运营指标可解释：命中率、低质答案率、未命中问题、热门知识、待更新知识、反馈闭环。

## 准备

```bash
cd nebula-kb
python3 scripts/demo_lifecycle.py
PYTHONPATH=apps DJANGO_SETTINGS_MODULE=nebula.settings.test python3 apps/manage.py test knowledge --noinput
```

## 讲解顺序

### 1. 开场定位

打开 README 首屏，说明 NebulaKB 的核心句子：

> NebulaKB 负责让知识资产持续变好，knowledgeops-agent 负责提供 Spring AI 企业后端工程基线。

强调边界：

- NebulaKB 面向知识运营、客服质检、内容治理。
- knowledgeops-agent 面向 Spring AI 后端、鉴权、队列、观测和部署。

### 2. 运营后台

展示 `docs/assets/screenshots/admin-dashboard.svg`。

讲解四个核心卡片：

- 知识命中率：回答是否有可靠引用。
- 低质答案率：人工反馈中 1 到 2 分占比。
- 未命中问题：检索没有可靠结果的问题。
- 反馈闭环：低质答案是否被处理完成。

### 3. 知识库列表

展示 `docs/assets/screenshots/knowledge-base-list.svg`。

讲解每个知识库都需要有业务域、负责人、文档数、命中率和治理状态。这里的重点是资产责任，而不是模型调用。

### 4. 文档入库

展示 `docs/assets/screenshots/document-ingestion.svg`。

按流程讲：

1. 文件上传。
2. 解析正文。
3. 按章节和段落切片。
4. 写入索引。
5. 解析失败进入治理队列。

使用 `demo-data/knowledge-sample/99-broken-scan.txt` 说明解析失败：扫描件缺少文本层，状态应标记为 `failed`，并保留失败原因。

### 5. 检索问答

运行：

```bash
python3 scripts/demo_lifecycle.py
```

重点观察三个命中问题：

- 解析失败后应该如何处理？
- 问答答案为什么必须返回引用？
- 低质答案率如何计算？

每个答案都应返回引用，例如 `01-import-governance.md#3`。引用是运营人员判断答案可靠性的入口。

### 6. 空结果兜底

脚本中的问题：

```text
火星基地餐饮报销规则是什么？
```

预期结果是空命中兜底。讲解重点：

- 不编造规则。
- 明确未找到可靠知识。
- 将问题沉淀到未命中问题池。

### 7. 人工反馈和低质答案回看

展示 `docs/assets/screenshots/qa-feedback.svg`。

讲解反馈闭环：

1. 低评分答案进入回看队列。
2. 运营人员判断原因：知识缺失、知识过期、切片不合理、召回不足或生成失败。
3. 修正知识或策略后关闭反馈。

### 8. 质量验证

运行：

```bash
PYTHONPATH=apps DJANGO_SETTINGS_MODULE=nebula.settings.test python3 apps/manage.py test knowledge --noinput
```

测试覆盖：

- 文件上传
- 解析失败
- 索引成功
- 权限隔离
- 检索命中
- 引用返回
- 空结果兜底
- 反馈记录

## 结束语

NebulaKB 的第一条健康基线已经具备“能讲、能跑、能测、能度量”的闭环。后续可以把轻量 demo 链路升级为真实后端 API 级验证，但产品边界保持在知识资产运营。
