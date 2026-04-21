# coding=utf-8
"""
    @project: LZKB
    @file： log_management.py
    @desc: 审计日志查询
"""
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.request import Request
from rest_framework.views import APIView

from common import result
from common.auth import TokenAuth
from common.auth.authentication import has_permissions
from common.constants.permission_constants import PermissionConstants, RoleConstants
from common.log.log import log
from system_manage.serializers.audit_log import AuditLogQuerySerializer


class AuditLogView(APIView):
    authentication_classes = [TokenAuth]

    @extend_schema(
        methods=['GET'],
        description=_('Query audit events by workspace'),
        summary=_('Query audit events by workspace'),
        operation_id=_('Query audit events by workspace'),  # type: ignore
        parameters=[
            OpenApiParameter("workspace_id", OpenApiTypes.STR, OpenApiParameter.PATH, required=True),
            OpenApiParameter("current_page", OpenApiTypes.INT, OpenApiParameter.PATH, required=True),
            OpenApiParameter("page_size", OpenApiTypes.INT, OpenApiParameter.PATH, required=True),
            OpenApiParameter("event_name", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("actor_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("result", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("start_time", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("end_time", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        tags=[_('Operation Log')]  # type: ignore
    )
    @has_permissions(PermissionConstants.OPERATION_LOG_READ, RoleConstants.WORKSPACE_MANAGE.get_workspace_role())
    @log(menu='System', operate='Query audit events')
    def get(self, request: Request, workspace_id: str, current_page: int, page_size: int):
        return result.success(AuditLogQuerySerializer(data={
            'workspace_id': workspace_id,
            'event_name': request.query_params.get('event_name'),
            'actor_id': request.query_params.get('actor_id'),
            'result': request.query_params.get('result'),
            'start_time': request.query_params.get('start_time'),
            'end_time': request.query_params.get('end_time'),
        }).page(current_page, page_size))
