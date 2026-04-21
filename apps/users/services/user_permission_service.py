# coding=utf-8
"""User role and default resource permission orchestration."""

from collections import defaultdict

import uuid_utils.compat as uuid
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.constants.cache_version import Cache_Version
from common.constants.permission_constants import ResourceAuthType, ResourcePermission, RoleConstants
from common.database_model_manage.database_model_manage import DatabaseModelManage
from common.exception.app_exception import AppApiException
from system_manage.models import AuthTargetType, WorkspaceUserResourcePermission


def update_user_role(instance, user, user_id=None):
    workspace_user_role_mapping_model = DatabaseModelManage.get_model("workspace_user_role_mapping")
    if workspace_user_role_mapping_model:
        role_setting = instance.get('role_setting')
        license_is_valid = DatabaseModelManage.get_model('license_is_valid') or (lambda: False)
        license_is_valid = license_is_valid() if license_is_valid() is not None else False
        if not role_setting or (len(role_setting) == 1
                                and role_setting[0].get('role_id') == ''
                                and len(role_setting[0].get('workspace_ids', [])) == 0):
            if not license_is_valid:
                workspace_user_role_mapping_model.objects.create(
                    id=uuid.uuid7(),
                    user_id=user.id,
                    role_id=RoleConstants.USER.name,
                    workspace_id='default'
                )
            return

        is_admin = workspace_user_role_mapping_model.objects.filter(user_id=user_id,
                                                                    role_id=RoleConstants.ADMIN.name).exists()

        if str(user.id) == 'f0dd8f71-e4ee-11ee-8c84-a8a1595801ab':
            admin_role_id = RoleConstants.ADMIN.name
            workspace_manage_role_id = RoleConstants.WORKSPACE_MANAGE.name
            current_role_ids = {item['role_id'] for item in role_setting}
            initial_role = [admin_role_id, workspace_manage_role_id, RoleConstants.USER.name]
            if not set(initial_role).issubset(current_role_ids):
                raise AppApiException(1004, _("Cannot delete built-in role"))

            if not any(item['role_id'] == str(admin_role_id) for item in role_setting):
                raise AppApiException(1004, _("Cannot delete built-in role"))

            default_workspace_id = 'default'

            for item in role_setting:
                role_id = item['role_id']
                workspace_ids = item.get('workspace_ids', [])

                if role_id == str(workspace_manage_role_id) or role_id == str(RoleConstants.USER.value):
                    if default_workspace_id not in workspace_ids:
                        raise AppApiException(1004, _("Cannot delete built-in role"))
        if is_admin:
            workspace_user_role_mapping_model.objects.filter(user_id=user.id).delete()
        else:
            workspace_user_role_mapping_model.objects.filter(user_id=user.id).exclude(
                role__type=RoleConstants.ADMIN.name).delete()

        relations = set()
        for item in role_setting:
            role_id = item['role_id']
            workspace_ids = item['workspace_ids'] if item['workspace_ids'] else ['None']
            for workspace_id in workspace_ids:
                relations.add((role_id, workspace_id))
        for role_id, workspace_id in relations:
            workspace_user_role_mapping_model.objects.create(
                id=uuid.uuid7(),
                role_id=role_id,
                workspace_id=workspace_id,
                user_id=user.id
            )
        permission_version, permission_get_key = Cache_Version.PERMISSION_LIST.value
        cache.delete(permission_get_key(str(user.id)), version=permission_version)


def set_default_permission(user_id, instance):
    """Set root and resource-level default permissions for a new user."""
    default_permission = instance.get('defaultPermission', 'NOT_AUTH')

    workspace_ids = _get_workspace_ids(instance, default_permission)
    if not workspace_ids:
        return

    auth_type = (ResourceAuthType.ROLE
                 if default_permission == ResourceAuthType.ROLE
                 else ResourceAuthType.RESOURCE_PERMISSION_GROUP)

    _set_root_permissions(user_id, workspace_ids)

    if default_permission == 'NOT_AUTH':
        return

    _set_resource_permissions(user_id, workspace_ids, default_permission, auth_type)


def _get_workspace_ids(instance, default_permission):
    role_setting_model = DatabaseModelManage.get_model("role_model")

    if not role_setting_model:
        return ['default']

    license_is_valid = DatabaseModelManage.get_model('license_is_valid') or (lambda: False)
    if default_permission == ResourceAuthType.ROLE and not license_is_valid():
        return []

    role_setting = instance.get('role_setting')
    if not role_setting:
        return ['default']

    all_role_ids = [item['role_id'] for item in role_setting]
    user_role_ids = set(role_setting_model.objects.filter(
        id__in=all_role_ids,
        type=RoleConstants.USER.name
    ).values_list('id', flat=True))

    workspace_ids = set()
    for item in role_setting:
        role_id = item['role_id']
        if role_id in user_role_ids:
            workspace_ids.update(item.get('workspace_ids', []))

    return list(workspace_ids) if workspace_ids else []


def _set_root_permissions(user_id, workspace_ids):
    root_permissions = []
    for workspace_id in workspace_ids:
        root_permissions.extend([
            WorkspaceUserResourcePermission(
                target=workspace_id,
                auth_target_type=auth_target_type,
                permission_list=[ResourcePermission.VIEW],
                workspace_id=workspace_id,
                user_id=user_id,
                auth_type=ResourceAuthType.RESOURCE_PERMISSION_GROUP
            )
            for auth_target_type in [
                AuthTargetType.APPLICATION.value,
                AuthTargetType.KNOWLEDGE.value,
                AuthTargetType.TOOL.value
            ]
        ])

    _batch_create_permissions(root_permissions)


def _set_resource_permissions(user_id, workspace_ids, default_permission, auth_type):
    resource_maps = _get_resource_maps(workspace_ids)

    instances = []
    for workspace_id in workspace_ids:
        instances.extend(_create_resource_permission_instances(
            workspace_id, resource_maps, user_id, default_permission, auth_type))

    _batch_create_permissions(instances)


def _get_resource_maps(workspace_ids):
    from application.models import Application, ApplicationFolder
    from knowledge.models import Knowledge, KnowledgeFolder
    from models_provider.models import Model
    from tools.models import Tool, ToolFolder

    resource_maps = {
        'apps': defaultdict(list),
        'app_folders': defaultdict(list),
        'knowledge': defaultdict(list),
        'knowledge_folders': defaultdict(list),
        'tools': defaultdict(list),
        'tool_folders': defaultdict(list),
        'models': defaultdict(list)
    }

    for workspace_id, resource_id in Application.objects.filter(
            workspace_id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['apps'][workspace_id].append(resource_id)

    for workspace_id, folder_id in ApplicationFolder.objects.filter(workspace_id__in=workspace_ids).exclude(
            id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['app_folders'][workspace_id].append(folder_id)

    for workspace_id, knowledge_id in Knowledge.objects.filter(
            workspace_id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['knowledge'][workspace_id].append(knowledge_id)

    for workspace_id, folder_id in KnowledgeFolder.objects.filter(workspace_id__in=workspace_ids).exclude(
            id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['knowledge_folders'][workspace_id].append(folder_id)

    for workspace_id, tool_id in Tool.objects.filter(workspace_id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['tools'][workspace_id].append(tool_id)

    for workspace_id, folder_id in ToolFolder.objects.filter(workspace_id__in=workspace_ids).exclude(
            id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['tool_folders'][workspace_id].append(folder_id)

    for workspace_id, model_id in Model.objects.filter(
            workspace_id__in=workspace_ids).values_list('workspace_id', 'id'):
        resource_maps['models'][workspace_id].append(model_id)

    return resource_maps


def _create_resource_permission_instances(workspace_id, resource_maps, user_id, permission, auth_type):
    instances = []
    if permission == ResourcePermission.MANAGE:
        permission = [ResourcePermission.VIEW, ResourcePermission.MANAGE]
    else:
        permission = [permission]

    for resource_id in resource_maps['apps'].get(workspace_id, []):
        instances.append(_build_permission(resource_id, AuthTargetType.APPLICATION.value, permission, workspace_id,
                                           user_id, auth_type))

    for folder_id in resource_maps['app_folders'].get(workspace_id, []):
        instances.append(_build_permission(folder_id, AuthTargetType.APPLICATION.value, permission, workspace_id,
                                           user_id, auth_type))

    for knowledge_id in resource_maps['knowledge'].get(workspace_id, []):
        instances.append(_build_permission(knowledge_id, AuthTargetType.KNOWLEDGE.value, permission, workspace_id,
                                           user_id, auth_type))

    for folder_id in resource_maps['knowledge_folders'].get(workspace_id, []):
        instances.append(_build_permission(folder_id, AuthTargetType.KNOWLEDGE.value, permission, workspace_id,
                                           user_id, auth_type))

    for tool_id in resource_maps['tools'].get(workspace_id, []):
        instances.append(_build_permission(tool_id, AuthTargetType.TOOL.value, permission, workspace_id, user_id,
                                           auth_type))

    for folder_id in resource_maps['tool_folders'].get(workspace_id, []):
        instances.append(_build_permission(folder_id, AuthTargetType.TOOL.value, permission, workspace_id, user_id,
                                           auth_type))

    for model_id in resource_maps['models'].get(workspace_id, []):
        instances.append(_build_permission(model_id, AuthTargetType.MODEL.value, permission, workspace_id, user_id,
                                           auth_type))

    return instances


def _build_permission(target, auth_target_type, permission, workspace_id, user_id, auth_type):
    return WorkspaceUserResourcePermission(
        target=target,
        auth_target_type=auth_target_type,
        permission_list=permission,
        workspace_id=workspace_id,
        user_id=user_id,
        auth_type=auth_type
    )


def _batch_create_permissions(instances, batch_size=500):
    if not instances:
        return

    objs = WorkspaceUserResourcePermission.objects
    for i in range(0, len(instances), batch_size):
        objs.bulk_create(instances[i:i + batch_size])

