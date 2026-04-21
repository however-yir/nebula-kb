# coding=utf-8
"""
    @project: LZKB
    @file： operation_metrics.py
    @desc: 工作空间运营指标
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
from system_manage.serializers.operation_metrics import WorkspaceOperationMetricsSerializer


class WorkspaceOperationMetricsView(APIView):
    authentication_classes = [TokenAuth]

    @extend_schema(
        methods=['GET'],
        description=_('Get workspace operation metrics'),
        summary=_('Get workspace operation metrics'),
        operation_id=_('Get workspace operation metrics'),  # type: ignore
        parameters=[
            OpenApiParameter("workspace_id", OpenApiTypes.STR, OpenApiParameter.PATH, required=True),
            OpenApiParameter("start_time", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("end_time", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
        ],
        tags=[_('Overview')]  # type: ignore
    )
    @has_permissions(PermissionConstants.OPERATION_LOG_READ, RoleConstants.WORKSPACE_MANAGE.get_workspace_role())
    @log(menu='System', operate='Get workspace operation metrics')
    def get(self, request: Request, workspace_id: str):
        return result.success(WorkspaceOperationMetricsSerializer(data={
            'workspace_id': workspace_id,
            'start_time': request.query_params.get('start_time'),
            'end_time': request.query_params.get('end_time'),
        }).get_metrics())
