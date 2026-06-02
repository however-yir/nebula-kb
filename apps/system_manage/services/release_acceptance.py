from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from common.contracts import (
    API_CONTRACT_VERSION,
    API_V1_ENDPOINTS,
    API_V1_PREFIX,
    AUTH_SCHEMES,
    E2E_MAIN_PATH,
    ERROR_CODE_RANGES,
    OPENAPI_VERSION,
    PAGINATION_FIELDS,
    RESPONSE_FIELDS,
)
from common.middleware.security_headers import DEFAULT_CONTENT_SECURITY_POLICY
from knowledge.services.asset_lifecycle_demo import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_UPLOAD_MIME_TYPES,
    KnowledgeAssetPlatform,
)
from system_manage.services.platform_governance_demo import PlatformGovernanceDemo


@dataclass
class ReleaseAcceptanceSnapshot:
    api: Dict[str, object]
    e2e: Dict[str, object]
    permission: Dict[str, object]
    security: Dict[str, object]
    deployment: Dict[str, object]
    observability: Dict[str, object]


class ReleaseAcceptanceDemo:
    """Acceptance model for API, security, deployment, and observability P0s."""

    def api_contract(self) -> Dict[str, object]:
        return {
            "contract_version": API_CONTRACT_VERSION,
            "api_v1_prefix": API_V1_PREFIX,
            "openapi_version": OPENAPI_VERSION,
            "response_fields": RESPONSE_FIELDS,
            "pagination_fields": PAGINATION_FIELDS,
            "auth_schemes": sorted(AUTH_SCHEMES.keys()),
            "error_code_ranges": ERROR_CODE_RANGES,
            "endpoints": list(API_V1_ENDPOINTS),
        }

    def run_e2e_main_path(self) -> Dict[str, object]:
        platform = KnowledgeAssetPlatform()
        tenant_id = "tenant-release"
        kb = platform.create_knowledge_base(
            tenant_id=tenant_id,
            knowledge_base_id="kb-release",
            name="Release knowledge base",
            owner="release-ops",
        )
        document = platform.upload_document(
            tenant_id,
            kb.id,
            "release-runbook.md",
            "# Release Runbook\n\nRollback requires health checks, citations, and feedback closure.",
            content_type="text/markdown",
        )
        platform.parse_document(tenant_id, document.id)
        platform.index_document(tenant_id, document.id)
        answer = platform.ask(tenant_id, kb.id, "How should release rollback be validated?")
        feedback = platform.vote_answer(
            tenant_id,
            kb.id,
            answer.question,
            answer.answer,
            "thumbs_down",
            citations=answer.citations,
            reason="needs clearer rollback evidence",
        )

        return {
            "path": E2E_MAIN_PATH,
            "login": "token-issued",
            "knowledge_base_id": kb.id,
            "document_status": document.status,
            "document_content_type": document.content_type,
            "retrieval_hit_count": len(answer.hits),
            "citation_count": len(answer.citations),
            "feedback_rating": feedback.rating,
            "governance_task_id": feedback.governance_task_id,
        }

    def run_permission_acceptance(self) -> Dict[str, object]:
        platform = PlatformGovernanceDemo()
        admin = platform.create_user("admin@example.com", "admin", "workspace-a")
        operator = platform.create_user("operator@example.com", "operator", "workspace-a")
        platform.authorize_resource(operator.id, "kb-release", {"view", "search"}, admin.id)

        workspace_blocked = False
        try:
            platform.ensure_workspace_access(operator, "workspace-b")
        except PermissionError:
            workspace_blocked = True

        return {
            "matrix": platform.permission_matrix(),
            "resource_grant": sorted(platform.resource_grants[(operator.id, "kb-release")]),
            "workspace_isolation_blocked": workspace_blocked,
        }

    def security_baseline(self) -> Dict[str, object]:
        return {
            "headers": {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Content-Security-Policy": DEFAULT_CONTENT_SECURITY_POLICY,
            },
            "upload": {
                "allowed_mime_types": {
                    suffix: sorted(mime_types)
                    for suffix, mime_types in SUPPORTED_UPLOAD_MIME_TYPES.items()
                },
                "max_upload_bytes": MAX_UPLOAD_BYTES,
            },
            "production_check_command": "scripts/production-security-check.sh",
        }

    def deployment_baseline(self) -> Dict[str, object]:
        return {
            "docs": [
                "docs/enterprise/deployment-guide.md",
                "docs/ops/operability.md",
            ],
            "compose": "deploy/docker-compose.operational.yml",
            "health": ["/healthz", "/readyz"],
            "release_commands": [
                "python apps/manage.py check",
                "python apps/manage.py migrate --plan",
                "scripts/production-security-check.sh",
            ],
        }

    def observability_baseline(self) -> Dict[str, object]:
        return {
            "metrics": [
                "nebula_kb_answer_total",
                "nebula_kb_answer_with_citation_total",
                "nebula_kb_feedback_total",
                "nebula_kb_document_indexed_total",
            ],
            "trace": "OpenTelemetry",
            "dashboard": "deploy/grafana/dashboards/nebula-kb-overview.json",
            "request_id_header": "X-Request-ID",
            "log_fields": ["tenant_id", "request_id", "trace_id", "status", "error_code"],
        }

    def snapshot(self) -> ReleaseAcceptanceSnapshot:
        return ReleaseAcceptanceSnapshot(
            api=self.api_contract(),
            e2e=self.run_e2e_main_path(),
            permission=self.run_permission_acceptance(),
            security=self.security_baseline(),
            deployment=self.deployment_baseline(),
            observability=self.observability_baseline(),
        )
