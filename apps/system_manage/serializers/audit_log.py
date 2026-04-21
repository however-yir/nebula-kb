# coding=utf-8
"""
    @project: LZKB
    @file： audit_log.py
    @desc: 审计事件契约查询
"""
import datetime

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.db.search import page_search
from system_manage.models import Log


class AuditLogSerializerModel(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = [
            "id",
            "event_name",
            "actor",
            "resource",
            "timestamp",
            "result",
            "workspace_id",
            "menu",
            "operate",
            "operation_object",
            "user",
            "status",
            "ip_address",
            "details",
            "create_time",
        ]


class AuditLogQuerySerializer(serializers.Serializer):
    workspace_id = serializers.CharField(required=True, label=_("Workspace ID"))
    event_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, label=_("Event name"))
    actor_id = serializers.CharField(required=False, allow_blank=True, allow_null=True, label=_("Actor ID"))
    result = serializers.ChoiceField(required=False, allow_null=True, allow_blank=True,
                                     choices=["success", "failure"], label=_("Result"))
    start_time = serializers.CharField(required=False, allow_blank=True, allow_null=True, label=_("Start time"))
    end_time = serializers.CharField(required=False, allow_blank=True, allow_null=True, label=_("End time"))

    @staticmethod
    def _parse_boundary(value, end_of_day=False):
        if not value:
            return None
        try:
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
        except ValueError:
            return None

    def page(self, current_page: int, page_size: int):
        self.is_valid(raise_exception=True)
        data = self.validated_data
        query_set = QuerySet(Log).filter(workspace_id=data.get("workspace_id"))

        event_name = data.get("event_name")
        if event_name:
            query_set = query_set.filter(event_name__icontains=event_name)

        actor_id = data.get("actor_id")
        if actor_id:
            query_set = query_set.filter(actor__id=actor_id)

        query_result = data.get("result")
        if query_result == "success":
            query_set = query_set.filter(status__lt=400)
        elif query_result == "failure":
            query_set = query_set.filter(status__gte=400)

        start_time = self._parse_boundary(data.get("start_time"))
        if start_time is not None:
            query_set = query_set.filter(timestamp__gte=start_time)

        end_time = self._parse_boundary(data.get("end_time"), end_of_day=True)
        if end_time is not None:
            query_set = query_set.filter(timestamp__lte=end_time)

        return page_search(
            current_page,
            page_size,
            query_set.order_by("-timestamp"),
            post_records_handler=lambda log: AuditLogSerializerModel(log).data,
        )
