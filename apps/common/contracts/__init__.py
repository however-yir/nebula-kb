# coding=utf-8
"""Stable API contract primitives shared by views, serializers, and clients."""

from .api_contract import (
    API_CONTRACT_VERSION,
    ERROR_CODE_RANGES,
    FIELD_NAMING,
    PAGINATION_FIELDS,
    QUERY_CONTRACT,
    RESPONSE_FIELDS,
    SORT_DESC_PREFIX,
    VERSIONING_STRATEGY,
)
from .module_boundaries import FROZEN_MODULE_BOUNDARIES, REQUIRED_LAYER_PACKAGES
