# coding=utf-8
"""Frozen domain boundaries for the gradual maintainability refactor."""

FROZEN_MODULE_BOUNDARIES = (
    {
        "domain": "users_auth",
        "label": "用户与认证",
        "owns": ("apps/users", "apps/common/auth"),
        "api_roots": ("user", "user_manage", "workspace/<workspace_id>/user"),
    },
    {
        "domain": "knowledge",
        "label": "知识库",
        "owns": ("apps/knowledge",),
        "api_roots": ("workspace/<workspace_id>/knowledge",),
    },
    {
        "domain": "retrieval_qa",
        "label": "检索问答",
        "owns": ("apps/chat", "apps/application/chat_pipeline"),
        "api_roots": ("chat_message", "chat", "historical_conversation"),
    },
    {
        "domain": "application_workflow",
        "label": "应用/工作流",
        "owns": ("apps/application", "apps/trigger"),
        "api_roots": ("workspace/<workspace_id>/application", "workspace/<workspace_id>/trigger"),
    },
    {
        "domain": "files_connectors",
        "label": "文件与连接器",
        "owns": ("apps/oss", "apps/tools", "apps/models_provider", "apps/local_model"),
        "api_roots": ("oss/file", "workspace/<workspace_id>/tool", "workspace/<workspace_id>/model"),
    },
)

REQUIRED_LAYER_PACKAGES = ("views", "serializers", "services", "repositories", "policies")

