# coding=utf-8
"""Base repository marker for domain data access classes."""


class BaseRepository:
    """Marker base class for repositories.

    Repositories may depend on Django models/querysets and low-level clients,
    but must not import views or HTTP response helpers.
    """

