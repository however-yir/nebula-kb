# coding=utf-8
"""
Knowledge operations dashboard contract.

The payload is intentionally explicit: each product capability has a stable
shape so the UI, docs, and future persistence layer can evolve independently.
"""
from django.utils import timezone
from rest_framework import serializers


class KnowledgeOpsDashboardSerializer(serializers.Serializer):
    workspace_id = serializers.CharField(required=True)
    range = serializers.CharField(required=False, default="30D")

    def get_dashboard(self):
        self.is_valid(raise_exception=True)
        workspace_id = self.validated_data["workspace_id"]
        now = timezone.localtime(timezone.now())

        return {
            "workspace_id": workspace_id,
            "generated_at": now.isoformat(),
            "positioning": {
                "product": "NebulaKB",
                "one_liner": "知识运营中枢",
                "promise": "把分散知识从接入、治理、检索、回答到反馈迭代纳入同一套可观测闭环。",
            },
            "metrics": [
                {"label": "知识新鲜度", "value": "86%", "trend": 7.4},
                {"label": "冲突待处理", "value": "12", "trend": -18.2},
                {"label": "问答命中率", "value": "78.4%", "trend": 5.1},
                {"label": "错误预算", "value": "72%", "trend": 2.6},
            ],
            "lifecycle": [
                {"name": "接入", "desc": "文件、网页、数据库、业务系统接入", "progress": 92},
                {"name": "治理", "desc": "脱敏、去重、冲突、可信度评分", "progress": 81},
                {"name": "发布", "desc": "灰度、验收、回滚、版本留痕", "progress": 76},
                {"name": "问答", "desc": "召回、重排、生成全链路可观测", "progress": 88},
                {"name": "反馈", "desc": "低质量回答回流标注与评测", "progress": 69},
            ],
            "freshness": [
                {"name": "制度文档", "value": 91, "color": "#14b8a6", "stale_count": 3},
                {"name": "客服知识", "value": 84, "color": "#3370ff", "stale_count": 9},
                {"name": "制造工艺", "value": 73, "color": "#f97316", "stale_count": 17},
                {"name": "法务条款", "value": 89, "color": "#7c3aed", "stale_count": 4},
            ],
            "conflicts": [
                {
                    "title": "退款时效口径不一致",
                    "source": "客服知识库 vs 法务条款",
                    "level": "高",
                    "status": "triage",
                },
                {"title": "质检抽样比例存在旧版本", "source": "制造 SOP", "level": "中", "status": "assigned"},
                {"title": "API 计费说明出现重复定义", "source": "官网文档", "level": "中", "status": "queued"},
            ],
            "source_credibility": [
                {"name": "合同主库", "score": 4.5, "evidence_count": 128, "owner": "Legal"},
                {"name": "客服 SOP", "score": 4, "evidence_count": 342, "owner": "CS Ops"},
                {"name": "生产工艺 Wiki", "score": 3.5, "evidence_count": 214, "owner": "MFG"},
            ],
            "expiring_documents": [
                {"name": "Q2 退款政策", "owner": "CS Ops", "expiresIn": "3 天", "action": "自动催办"},
                {"name": "供应商 NDA 模板", "owner": "Legal", "expiresIn": "5 天", "action": "发起复核"},
                {"name": "CNC 点检 SOP", "owner": "MFG", "expiresIn": "7 天", "action": "班组确认"},
            ],
            "qa_hit_rate_daily": [
                {"day": "Mon", "rate": 73},
                {"day": "Tue", "rate": 76},
                {"day": "Wed", "rate": 75},
                {"day": "Thu", "rate": 81},
                {"day": "Fri", "rate": 78},
            ],
            "feedback_loop": ["用户差评", "人工标注", "样本回流", "再次评测"],
            "department_permission_templates": [
                {"name": "法务部", "template": "合同/合规只读 + 审批"},
                {"name": "客服部", "template": "FAQ 编辑 + 发布申请"},
                {"name": "制造部", "template": "SOP 只读 + 异常标注"},
            ],
            "tenant_branding": [
                {"name": "Nebula Core", "color": "#14b8a6", "domain": "core.nebulakb.ai"},
                {"name": "Acme White-label", "color": "#3370ff", "domain": "kb.acme.com"},
                {"name": "Factory Desk", "color": "#f97316", "domain": "qa.factory.internal"},
            ],
            "tenant_isolation": {
                "enabled": True,
                "strategies": ["租户级索引", "对象存储前缀", "审计链路隔离", "密钥作用域隔离"],
            },
            "assistant_templates": [
                {"name": "合同审阅助手", "industry": "法务", "desc": "条款冲突、引用追溯、风险边界。"},
                {"name": "售后坐席助手", "industry": "客服", "desc": "命中率日报、低质回答回流、渠道知识同步。"},
                {"name": "工艺异常助手", "industry": "制造", "desc": "SOP 追溯、设备告警关联、班组权限模板。"},
            ],
            "industry_template_packs": ["法务", "客服", "制造"],
            "ingestion_wizard": [
                {"title": "连接数据源", "status": "finish"},
                {"title": "选择权限模板", "status": "finish"},
                {"title": "运行首轮评测", "status": "process"},
                {"title": "发布知识助手", "status": "wait"},
            ],
            "data_source_health": [
                {"name": "Confluence / CS Handbook", "latency": "230ms", "lastSync": "4 分钟前", "status": "健康"},
                {"name": "SharePoint / Legal", "latency": "410ms", "lastSync": "12 分钟前", "status": "健康"},
                {"name": "MES 工艺库", "latency": "1.8s", "lastSync": "42 分钟前", "status": "需关注"},
            ],
            "retrieval_observability": [
                {"name": "召回 Recall@20", "value": 82},
                {"name": "重排 NDCG@5", "value": 76},
                {"name": "生成引用完整率", "value": 91},
            ],
            "prompt_versions": [
                {"name": "v4.8 引用优先", "time": "今天 09:20", "rollback_ready": True},
                {"name": "v4.7 降低幻觉", "time": "昨天 18:04", "rollback_ready": True},
                {"name": "v4.6 行业术语增强", "time": "04-21 11:30", "rollback_ready": True},
            ],
            "workflow_gray_release": {"enabled": True, "percent": 20, "cohort": "tenant"},
            "ab_experiments": [
                {"name": "客服助手重排阈值", "winner": "B 组 +6.1%", "status": "running"},
                {"name": "法务拒答策略", "winner": "A 组稳定", "status": "completed"},
            ],
            "quality_evaluation": {
                "score": 88,
                "tasks": ["事实一致性", "引用完整性", "拒答边界"],
                "schedule": "daily",
            },
            "rag_benchmarks": [
                {"name": "客服 Top 200 问法", "cases": 200, "score": "86.7", "owner": "CS Ops"},
                {"name": "法务红线问答", "cases": 88, "score": "91.4", "owner": "Legal"},
                {"name": "制造异常处置", "cases": 132, "score": "79.2", "owner": "MFG"},
            ],
            "pii_policy": {"enabled": True, "rules": ["手机号", "身份证", "邮箱"]},
            "tamper_proof_audit": [
                {"action": "policy.updated", "hash": "0x9a31...c8f2"},
                {"action": "prompt.rollback", "hash": "0x1bc4...87d0"},
                {"action": "dataset.exported", "hash": "0xae90...b13a"},
            ],
            "api_key_scopes": [
                {"scope": "knowledge:read", "level": "只读"},
                {"scope": "answer:evaluate", "level": "任务"},
                {"scope": "tenant:brand", "level": "管理"},
            ],
            "sso_role_mapping": [
                {"group": "okta-legal", "role": "法务知识管理员"},
                {"group": "okta-cs-lead", "role": "客服运营负责人"},
                {"group": "okta-mfg-user", "role": "制造现场用户"},
            ],
            "slo_error_budget": {
                "remaining_percent": 72,
                "availability_24h": "99.93%",
                "status": "healthy",
            },
            "release_acceptance": {
                "score": 94,
                "checks": ["Schema", "权限", "检索", "生成质量", "回滚点"],
                "status": "passed",
            },
            "backup_drill": {"status": "success", "rto": "18m", "rpo": "4m"},
            "citation_chain": [
                {
                    "title": "回答片段",
                    "detail": "“保修期内的设备异常优先走快速换新流程。”",
                    "owner": "售后助手",
                    "time": "生成于 10:42",
                },
                {
                    "title": "引用段落",
                    "detail": "售后政策 v2026.04 / 第 3.2 节 / 段落 #184",
                    "owner": "CS Ops",
                    "time": "召回于 10:42",
                },
                {
                    "title": "源文件版本",
                    "detail": "Warranty_Policy_2026Q2.pdf / sha256: 9a31c8f2",
                    "owner": "法务部",
                    "time": "同步于 09:55",
                },
                {
                    "title": "审批记录",
                    "detail": "Legal-approval-4821 / 双人复核 / 不可变更审计链",
                    "owner": "Legal",
                    "time": "04-22 16:10",
                },
            ],
            "visual_system": {
                "fonts": "PingFang SC / AlibabaPuHuiTi / Inter fallback",
                "palette": ["#14b8a6", "#3370ff", "#f97316", "#7c3aed", "#111827", "#f5f6f7"],
                "icon_rule": "Element Plus 线性图标优先，业务图标纳入 AppIcon 注册表。",
            },
        }
