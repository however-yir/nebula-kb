# coding=utf-8
"""
Knowledge operations dashboard API.
"""
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.views import APIView

from common import result
from common.auth import TokenAuth
from common.auth.authentication import has_permissions
from common.constants.permission_constants import PermissionConstants, RoleConstants
from common.log.log import log
from system_manage.serializers.knowledge_ops import KnowledgeOpsDashboardSerializer


class KnowledgeOpsDashboardView(APIView):
    authentication_classes = [TokenAuth]

    @extend_schema(
        methods=["GET"],
        description=_("Get knowledge operations dashboard"),
        summary=_("Get knowledge operations dashboard"),
        operation_id=_("Get knowledge operations dashboard"),  # type: ignore
        parameters=[
            OpenApiParameter("workspace_id", OpenApiTypes.STR, OpenApiParameter.PATH, required=True),
            OpenApiParameter("range", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        tags=[_("Knowledge Operations")],  # type: ignore
    )
    @has_permissions(PermissionConstants.OPERATION_LOG_READ, RoleConstants.WORKSPACE_MANAGE.get_workspace_role())
    @log(menu="Knowledge Operations", operate="Get knowledge operations dashboard")
    def get(self, request: Request, workspace_id: str):
        payload = KnowledgeOpsDashboardSerializer(
            data={
                "workspace_id": workspace_id,
                "range": request.query_params.get("range", "30D"),
            }
        ).get_dashboard()
        return result.success(payload)
