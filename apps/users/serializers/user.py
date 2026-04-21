# coding=utf-8
"""
    @project: LZKB
    @Author：虎虎
    @file： user.py
    @date：2025/4/14 19:18
    @desc:
"""
import re
from collections import defaultdict

from django.core import validators
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _
import uuid_utils.compat as uuid
from rest_framework import serializers

from common.constants.exception_code_constants import ExceptionCodeConstants
from common.constants.permission_constants import Auth, RoleConstants
from common.auth.tokens import revoke_user_sessions
from common.database_model_manage.database_model_manage import DatabaseModelManage
from common.db.search import page_search
from common.exception.app_exception import AppApiException
from common.utils.common import password_encrypt, password_matches
from common.utils.rsa_util import decrypt
from lzkb.const import CONFIG
from users.models import User
from users.serializers.account import CheckCodeSerializer, RePasswordSerializer, ResetCurrentUserPassword, \
    SendEmailSerializer, SwitchLanguageSerializer
from users.serializers.password_policy import PASSWORD_REGEX
from users.services.user_permission_service import set_default_permission, update_user_role


class UserProfileResponse(serializers.ModelSerializer):
    is_edit_password = serializers.BooleanField(required=True, label=_('Is Edit Password'))
    permissions = serializers.ListField(required=True, label=_('permissions'))

    class Meta:
        model = User
        fields = ['id', 'username', 'nick_name', 'email', 'role', 'permissions', 'language', 'is_edit_password']


class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, label=_('Username'))
    password = serializers.CharField(required=True, label=_('Password'))
    email = serializers.EmailField(required=True, label=_('Email'))
    nick_name = serializers.CharField(required=False, label=_('Nick name'))
    phone = serializers.CharField(required=False, label=_('Phone'))
    source = serializers.CharField(required=False, label=_('Source'), default='LOCAL')
    defaultPermission = serializers.CharField(required=False, label=_('defaultPermission'))


def is_workspace_manage(user_id: str, workspace_id: str):
    workspace_user_role_mapping_model = DatabaseModelManage.get_model("workspace_user_role_mapping")
    role_permission_mapping_model = DatabaseModelManage.get_model("role_permission_mapping_model")
    is_x_pack_ee = workspace_user_role_mapping_model is not None and role_permission_mapping_model is not None
    if is_x_pack_ee:
        return QuerySet(workspace_user_role_mapping_model).select_related('role', 'user').filter(
            workspace_id=workspace_id, user_id=user_id,
            role__type=RoleConstants.WORKSPACE_MANAGE.value.__str__()).exists()
    return QuerySet(User).filter(id=user_id, role=RoleConstants.ADMIN.value.__str__()).exists()


def get_workspace_list_by_user(user_id):
    get_workspace_list = DatabaseModelManage.get_model('get_workspace_list_by_user')
    license_is_valid = DatabaseModelManage.get_model('license_is_valid') or (lambda: False)
    if get_workspace_list is not None and license_is_valid():
        return get_workspace_list(user_id)
    return [{'id': 'default', 'name': 'default'}]


class UserProfileSerializer(serializers.Serializer):
    @staticmethod
    def profile(user: User, auth: Auth):
        """
          获取用户详情
        @param user: 用户对象
        @param auth: 认证对象
        @return:
        """
        workspace_list = get_workspace_list_by_user(user.id)
        user_role_relation_model = DatabaseModelManage.get_model("workspace_user_role_mapping")
        role_name = [user.role]
        if user_role_relation_model:
            user_role_relations = (
                user_role_relation_model.objects
                .filter(user_id=user.id)
                .select_related('role')
                .distinct('role_id')
            )
            role_name = [relation.role.role_name for relation in user_role_relations]

        return {
            'id': user.id,
            'username': user.username,
            'nick_name': user.nick_name,
            'email': user.email,
            'source': user.source,
            'role': auth.role_list,
            'permissions': auth.permission_list,
            'is_edit_password': password_matches(
                CONFIG.get('DEFAULT_PASSWORD', 'ChangeMe@1234!'),
                user.password
            ) if user.source == 'LOCAL' else False,
            'language': user.language,
            'workspace_list': workspace_list,
            'role_name': role_name
        }


class UserInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'is_active', 'role', 'nick_name', 'create_time', 'update_time',
                  'source']


class UserManageSerializer(serializers.Serializer):
    class UserInstance(serializers.Serializer):
        email = serializers.EmailField(
            required=True,
            label=_("Email"),
            validators=[validators.EmailValidator(
                message=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.message,
                code=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.code
            )]
        )
        username = serializers.CharField(
            required=True,
            label=_("Username"),
            max_length=64,
            min_length=4,
            validators=[
                validators.RegexValidator(
                    regex=re.compile("^.{4,64}$"),
                    message=_('Username must be 4-64 characters long')
                )
            ]
        )
        password = serializers.CharField(
            required=True,
            label=_("Password"),
            max_length=20,
            min_length=6,
            validators=[
                validators.RegexValidator(
                    regex=PASSWORD_REGEX,
                    message=_(
                        "The password must be 6-20 characters long and must be a combination of letters, numbers, and special characters."
                    )
                )
            ]
        )
        nick_name = serializers.CharField(
            required=True,
            label=_("Nick name"),
            max_length=64,
        )
        phone = serializers.CharField(
            required=False,
            label=_("Phone"),
            max_length=20,
            allow_null=True,
            allow_blank=True
        )
        source = serializers.CharField(
            required=False,
            label=_("Source"),
            max_length=20,
            default="LOCAL"
        )

        def is_valid(self, *, raise_exception=True):
            super().is_valid(raise_exception=True)
            self._check_unique_username_and_email()

        def _check_unique_username_and_email(self):
            username = self.data.get('username')
            email = self.data.get('email')
            nick_name = self.data.get('nick_name')
            user = User.objects.filter(Q(username=username) | Q(email=email) | Q(nick_name=nick_name)).first()
            if user:
                if user.email == email:
                    raise ExceptionCodeConstants.EMAIL_IS_EXIST.value.to_app_api_exception()
                if user.username == username:
                    raise ExceptionCodeConstants.USERNAME_IS_EXIST.value.to_app_api_exception()
                if user.nick_name == nick_name:
                    raise ExceptionCodeConstants.NICKNAME_IS_EXIST.value.to_app_api_exception()

    class Query(serializers.Serializer):
        username = serializers.CharField(
            required=False,
            label=_("Username"),
            max_length=64,
            allow_blank=True
        )
        nick_name = serializers.CharField(
            required=False,
            label=_("Nick Name"),
            max_length=64,
            allow_blank=True
        )
        email = serializers.CharField(
            required=False,
            label=_("Email"),
            allow_blank=True,
        )
        is_active = serializers.BooleanField(
            required=False,
            label=_("Is active"),
        )
        source = serializers.CharField(
            required=False,
            label=_("Source"),
            allow_blank=True,
        )

        def get_query_set(self):
            username = self.data.get('username')
            nick_name = self.data.get('nick_name')
            email = self.data.get('email')
            is_active = self.data.get('is_active', None)
            source = self.data.get('source', None)
            query_set = QuerySet(User)
            if username is not None:
                query_set = query_set.filter(username__contains=username)
            if nick_name is not None:
                query_set = query_set.filter(nick_name__contains=nick_name)
            if email is not None:
                query_set = query_set.filter(email__contains=email)
            if is_active is not None:
                query_set = query_set.filter(is_active=is_active)
            if source is not None:
                query_set = query_set.filter(source=source)
            query_set = query_set.order_by("-create_time")
            return query_set

        def list(self, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
            return [{'id': user_model.id, 'username': user_model.username, 'email': user_model.email} for user_model in
                    self.get_query_set()]

        def page(self, current_page: int, page_size: int, user_id: str, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
            result = page_search(current_page, page_size,
                                 self.get_query_set(),
                                 post_records_handler=lambda u: UserInstanceSerializer(u).data)
            role_model = DatabaseModelManage.get_model("role_model")
            user_role_relation_model = DatabaseModelManage.get_model("workspace_user_role_mapping")

            def _get_user_roles(user_ids, is_admin=True):
                workspace_model = DatabaseModelManage.get_model("workspace_model")
                if not (role_model and user_role_relation_model and workspace_model):
                    return {}

                workspace_mapping = {str(workspace_model.id): workspace_model.name for workspace_model in
                                     workspace_model.objects.all()}

                # 获取所有相关角色关系，并预加载角色信息
                user_role_relations = (
                    user_role_relation_model.objects
                    .filter(user_id__in=user_ids)
                    .select_related('role')
                    .distinct('user_id', 'role_id', 'workspace_id')  # 确保组合唯一性
                )

                # 构建用户ID到角色名称列表的映射
                user_role_mapping = defaultdict(set)  # 使用 set 去重
                # 构建用户ID到角色ID与工作空间ID映射
                user_role_setting_mapping = defaultdict(lambda: defaultdict(list))
                user_role_workspace_mapping = defaultdict(lambda: defaultdict(list))

                for relation in user_role_relations:
                    user_id = str(relation.user_id)
                    role_id = relation.role_id
                    workspace_id = relation.workspace_id
                    if not is_admin and relation.role.type == RoleConstants.ADMIN.name:
                        continue
                    user_role_mapping[user_id].add(relation.role.role_name)
                    user_role_setting_mapping[user_id][role_id].append(workspace_id)
                    user_role_workspace_mapping[user_id][relation.role.role_name].append(
                        workspace_mapping.get(workspace_id, workspace_id))

                    # 将 set 转换为 list 以符合返回格式
                user_role_mapping = {uid: list(roles) for uid, roles in user_role_mapping.items()}

                # 转换为所需的结构
                result_user_role_setting_mapping = {
                    user_id: [{"role_id": role_id, "workspace_ids": workspace_ids}
                              for role_id, workspace_ids in roles.items()]
                    for user_id, roles in user_role_setting_mapping.items()
                }
                result_user_role_workspace_mapping = {
                    user_id: {role_name: workspace_names
                              for role_name, workspace_names in roles.items()}
                    for user_id, roles in user_role_workspace_mapping.items()
                }

                return user_role_mapping, result_user_role_setting_mapping, result_user_role_workspace_mapping

            if role_model and user_role_relation_model:
                # 获取当前用户的所有角色 判断是不是内置的系统管理员
                is_admin = user_role_relation_model.objects.filter(user_id=user_id,
                                                                   role_id=RoleConstants.ADMIN.name).exists()
                user_ids = [user['id'] for user in result['records']]
                user_role_mapping, user_role_setting_mapping, user_role_workspace_mapping = _get_user_roles(user_ids,
                                                                                                            is_admin)

                # 将角色信息添加回用户数据中
                for user in result['records']:
                    user_id = str(user['id'])
                    user['role_name'] = user_role_mapping.get(user_id, [])
                    user['role_setting'] = user_role_setting_mapping.get(user_id, [])
                    user['role_workspace'] = user_role_workspace_mapping.get(user_id, [])
            return result

    @transaction.atomic
    def save(self, instance, user_id, with_valid=True):
        if with_valid:
            if instance.get('encrypted'):
                instance['password'] = decrypt(instance.get('password'))
            self.UserInstance(data=instance).is_valid(raise_exception=True)

        user = User(
            id=uuid.uuid7(),
            email=instance.get('email'),
            phone=instance.get('phone', ''),
            nick_name=instance.get('nick_name', ''),
            username=instance.get('username'),
            password=password_encrypt(instance.get('password')),
            role=RoleConstants.USER.name,
            source=instance.get('source', 'LOCAL'),
            is_active=True
        )
        update_user_role(instance, user, user_id)
        set_default_permission(user.id, instance)
        user.save()
        return UserInstanceSerializer(user).data

    class UserEditInstance(serializers.Serializer):
        email = serializers.EmailField(
            required=False,
            label=_("Email"),
            validators=[validators.EmailValidator(
                message=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.message,
                code=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.code
            )]
        )
        nick_name = serializers.CharField(
            required=False,
            label=_("Name"),
            max_length=64,
        )
        phone = serializers.CharField(
            required=False,
            label=_("Phone"),
            max_length=20,
            allow_null=True,
            allow_blank=True
        )
        is_active = serializers.BooleanField(
            required=False,
            label=_("Is Active")
        )

        def is_valid(self, *, user_id=None, raise_exception=False):
            super().is_valid(raise_exception=True)
            self._check_unique_email(user_id)
            self._check_unique_nick_name(user_id)

        def _check_unique_nick_name(self, user_id):
            nick_name = self.data.get('nick_name')
            if nick_name and User.objects.filter(nick_name=nick_name).exclude(id=user_id).exists():
                raise AppApiException(1008, _('Nickname is already in use'))

        def _check_unique_email(self, user_id):
            email = self.data.get('email')
            if email and User.objects.filter(email=email).exclude(id=user_id).exists():
                raise AppApiException(1004, _('Email is already in use'))

    class RePasswordInstance(serializers.Serializer):
        password = serializers.CharField(
            required=True,
            label=_("Password"),
            max_length=20,
            min_length=6,
            validators=[
                validators.RegexValidator(
                    regex=PASSWORD_REGEX,
                    message=_(
                        "The password must be 6-20 characters long and must be a combination of letters, numbers, and special characters."
                    )
                )
            ]
        )
        re_password = serializers.CharField(
            required=True,
            label=_("Re Password"),
            validators=[
                validators.RegexValidator(
                    regex=PASSWORD_REGEX,
                    message=_(
                        "The confirmation password must be 6-20 characters long and must be a combination of letters, numbers, and special characters."
                    )
                )
            ]
        )

        def is_valid(self, *, raise_exception=False):
            super().is_valid(raise_exception=True)
            self._check_passwords_match()

        def _check_passwords_match(self):
            if self.data.get('password') != self.data.get('re_password'):
                raise ExceptionCodeConstants.PASSWORD_NOT_EQ_RE_PASSWORD.value.to_app_api_exception()

    class Operate(serializers.Serializer):
        id = serializers.UUIDField(required=True, label=_('User ID'))

        def is_valid(self, *, raise_exception=False):
            super().is_valid(raise_exception=True)
            self._check_user_exists()

        def _check_user_exists(self):
            if not User.objects.filter(id=self.data.get('id')).exists():
                raise AppApiException(1004, _('User does not exist'))

        @transaction.atomic
        def delete(self, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
                self._check_not_admin()
            user_id = self.data.get('id')
            # TODO  需要删除授权关系
            User.objects.filter(id=user_id).delete()
            return True

        def _check_not_admin(self):
            user = User.objects.filter(id=self.data.get('id')).first()
            if user.role == RoleConstants.ADMIN.name or str(user.id) == 'f0dd8f71-e4ee-11ee-8c84-a8a1595801ab':
                raise AppApiException(1004, _('Unable to delete administrator'))

        def edit(self, instance, user_id, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
                UserManageSerializer.UserEditInstance(data=instance).is_valid(user_id=self.data.get('id'),
                                                                              raise_exception=True)
            user = User.objects.filter(id=self.data.get('id')).first()
            self._check_admin_modification(user, instance)
            self._update_user_fields(user, instance)
            update_user_role(instance, user, user_id)
            user.save()
            return UserInstanceSerializer(user).data

        @staticmethod
        def _check_admin_modification(user, instance):
            if user.role == RoleConstants.ADMIN.name and 'is_active' in instance and instance.get(
                    'is_active') is not None:
                raise AppApiException(1004, _('Cannot modify administrator status'))

        @staticmethod
        def _update_user_fields(user, instance):
            update_keys = ['email', 'nick_name', 'phone', 'is_active']
            for key in update_keys:
                if key in instance and instance.get(key) is not None:
                    setattr(user, key, instance.get(key))

        def one(self, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
            user = User.objects.filter(id=self.data.get('id')).first()
            workspace_user_role_mapping_model = DatabaseModelManage.get_model("workspace_user_role_mapping")
            if workspace_user_role_mapping_model:
                role_setting = {}
                workspace_user_role_mapping_list = QuerySet(workspace_user_role_mapping_model).filter(
                    user_id=user.id)
                for workspace_user_role_mapping in workspace_user_role_mapping_list:
                    role_id = workspace_user_role_mapping.role_id
                    workspace_id = workspace_user_role_mapping.workspace_id
                    if role_id not in role_setting:
                        role_setting[role_id] = []
                    role_setting[role_id].append(workspace_id)
                return {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone,
                    'nick_name': user.nick_name,
                    'is_active': user.is_active,
                    'role_setting': role_setting
                }
            return UserInstanceSerializer(user).data

        def re_password(self, instance, with_valid=True):
            if with_valid:
                self.is_valid(raise_exception=True)
                UserManageSerializer.RePasswordInstance(data=instance).is_valid(raise_exception=True)
            user = User.objects.filter(id=self.data.get('id')).first()
            user.password = password_encrypt(instance.get('password'))
            user.save()
            revoke_user_sessions(user.id, reason="password_changed")
            return True

    def get_user_list(self, workspace_id):
        """
        获取用户列表
        :param workspace_id: 工作空间ID
        :return: 用户列表
        """
        workspace_user_role_mapping_model = DatabaseModelManage.get_model("workspace_user_role_mapping")
        if workspace_user_role_mapping_model:
            user_ids = (
                workspace_user_role_mapping_model.objects
                .filter(workspace_id=workspace_id)
                .values_list('user_id', flat=True)
                .distinct()
            )
        else:
            user_ids = User.objects.values_list('id', flat=True)

        users = User.objects.filter(id__in=user_ids).values('id', 'nick_name')
        return list(users)

    def get_user_members(self, workspace_id):
        """
        获取工作空间成员列表
        :param workspace_id: 工作空间ID
        :return: 成员列表
        """
        role_model = DatabaseModelManage.get_model("role_model")
        user_role_relation_model = DatabaseModelManage.get_model("workspace_user_role_mapping")

        if user_role_relation_model and role_model:
            user_role_relations = (
                user_role_relation_model.objects
                .filter(workspace_id=workspace_id, role__type='USER')
                .select_related('role', 'user')
            )
            user_dict = {}
            for relation in user_role_relations:
                user_id = relation.user.id
                if user_id not in user_dict:
                    user_dict[user_id] = {
                        'id': user_id,
                        'nick_name': relation.user.nick_name,
                        'email': relation.user.email,
                        'roles': [relation.role.role_name]
                    }
                else:
                    user_dict[user_id]['roles'].append(relation.role.role_name)

            # 将字典值转换为列表形式
            return list(user_dict.values())
        user_list = User.objects.exclude(role=RoleConstants.ADMIN.name)
        return [
            {
                'id': user.id,
                'nick_name': user.nick_name,
                'email': user.email,
                'roles': [RoleConstants.USER.name]
            } for user in user_list
        ]

    class BatchDelete(serializers.Serializer):
        ids = serializers.ListField(required=True, label=_('User IDs'))

        def batch_delete(self, with_valid=True):
            user_ids = self.data.get('ids')
            if not user_ids:
                raise AppApiException(1004, _('User IDs cannot be empty'))
            User.objects.filter(id__in=user_ids).exclude(id='f0dd8f71-e4ee-11ee-8c84-a8a1595801ab').delete()
            return True

    def get_all_user_list(self):
        users = User.objects.all().values('id', 'nick_name', 'username')
        return list(users)

