# coding=utf-8
"""Stable API contract primitives shared by views, serializers, and clients."""

from .api_contract import (
    API_CONTRACT_VERSION,
    API_V1_ENDPOINTS,
    API_V1_PREFIX,
    AUTH_SCHEMES,
    E2E_MAIN_PATH,
    ERROR_CODE_RANGES,
    ERROR_RESPONSE_SCHEMA,
    FIELD_NAMING,
    OPENAPI_VERSION,
    PAGINATION_FIELDS,
    QUERY_CONTRACT,
    RESPONSE_FIELDS,
    SORT_DESC_PREFIX,
    VERSIONING_STRATEGY,
)
from .module_boundaries import FROZEN_MODULE_BOUNDARIES, REQUIRED_LAYER_PACKAGES
