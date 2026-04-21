# coding=utf-8
"""Base service marker for domain use-cases."""


class BaseService:
    """Marker base class for services.

    Services own business transactions and workflow orchestration. They may be
    called by serializers during the migration period, and by views afterwards.
    """

