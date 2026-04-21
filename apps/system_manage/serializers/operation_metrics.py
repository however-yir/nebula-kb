# coding=utf-8
"""
    @project: LZKB
    @file： operation_metrics.py
    @desc: 工作空间运营指标
"""
import datetime

from django.db.models import Count, Max, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from application.models import ChatRecord
from system_manage.models import Log


class WorkspaceOperationMetricsResponseSerializer(serializers.Serializer):
    workspace_id = serializers.CharField(required=True, label=_("Workspace ID"))
    start_time = serializers.DateTimeField(required=True, label=_("Start time"))
    end_time = serializers.DateTimeField(required=True, label=_("End time"))
    call_count = serializers.IntegerField(required=True, label=_("Call count"))
    total_cost = serializers.IntegerField(required=True, label=_("Total cost"))
    active_user_count = serializers.IntegerField(required=True, label=_("Active user count"))
    operation_count = serializers.IntegerField(required=True, label=_("Operation count"))
    failed_operation_count = serializers.IntegerField(required=True, label=_("Failed operation count"))
    failure_rate = serializers.FloatField(required=True, label=_("Failure rate"))
    last_activity_at = serializers.DateTimeField(required=False, allow_null=True, label=_("Last activity time"))


class WorkspaceOperationMetricsSerializer(serializers.Serializer):
    workspace_id = serializers.CharField(required=True, label=_("Workspace ID"))
    start_time = serializers.CharField(required=True, label=_("Start time"))
    end_time = serializers.CharField(required=True, label=_("End time"))

    @staticmethod
    def _parse_boundary(value, end_of_day=False):
        if len(value) == 10:
            parsed_date = datetime.datetime.strptime(value, "%Y-%m-%d").date()
            parsed = datetime.datetime.combine(
                parsed_date, datetime.time.max if end_of_day else datetime.time.min
            )
        else:
            parsed = datetime.datetime.fromisoformat(value)
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_default_timezone())
        return parsed

    def get_metrics(self):
        self.is_valid(raise_exception=True)
        workspace_id = self.validated_data.get("workspace_id")
        start_time = self._parse_boundary(self.validated_data.get("start_time"))
        end_time = self._parse_boundary(self.validated_data.get("end_time"), end_of_day=True)

        chat_record_query = ChatRecord.objects.filter(
            chat__application__workspace_id=workspace_id,
            create_time__gte=start_time,
            create_time__lte=end_time,
        )
        log_query = Log.objects.filter(
            workspace_id=workspace_id,
            timestamp__gte=start_time,
            timestamp__lte=end_time,
        )

        chat_aggs = chat_record_query.aggregate(
            call_count=Count("id"),
            total_cost=Sum("const"),
            last_activity_at=Max("create_time"),
        )
        active_user_count = chat_record_query.exclude(chat__chat_user_id__isnull=True).exclude(
            chat__chat_user_id=""
        ).values(
            "chat__chat_user_type", "chat__chat_user_id"
        ).distinct().count()
        operation_count = log_query.count()
        failed_operation_count = log_query.filter(status__gte=400).count()

        return {
            "workspace_id": workspace_id,
            "start_time": start_time,
            "end_time": end_time,
            "call_count": chat_aggs.get("call_count") or 0,
            "total_cost": chat_aggs.get("total_cost") or 0,
            "active_user_count": active_user_count,
            "operation_count": operation_count,
            "failed_operation_count": failed_operation_count,
            "failure_rate": round(failed_operation_count / operation_count, 4) if operation_count else 0,
            "last_activity_at": chat_aggs.get("last_activity_at"),
        }
