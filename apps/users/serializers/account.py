# coding=utf-8
"""Account recovery, email verification, and language serializers."""

import os
import random
import re

from django.core import validators
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.db.models import QuerySet
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _, to_locale
from rest_framework import serializers

from common.constants.cache_version import Cache_Version
from common.constants.exception_code_constants import ExceptionCodeConstants
from common.auth.tokens import revoke_user_sessions
from common.exception.app_exception import AppApiException
from common.utils.common import password_encrypt
from lzkb.conf import PROJECT_DIR
from system_manage.models import SettingType, SystemSetting
from users.models import User
from users.serializers.password_policy import PASSWORD_REGEX

version, get_key = Cache_Version.SYSTEM.value


class RePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        label=_("Email"),
        validators=[validators.EmailValidator(message=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.message,
                                              code=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.code)])

    code = serializers.CharField(required=True, label=_("Code"))
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

    class Meta:
        model = User
        fields = '__all__'

    def is_valid(self, *, raise_exception=False):
        super().is_valid(raise_exception=True)
        email = self.data.get("email")
        cache_code = cache.get(get_key(email + ':reset_password'), version=version)
        if self.data.get('password') != self.data.get('re_password'):
            raise AppApiException(ExceptionCodeConstants.PASSWORD_NOT_EQ_RE_PASSWORD.value.code,
                                  ExceptionCodeConstants.PASSWORD_NOT_EQ_RE_PASSWORD.value.message)
        if cache_code != self.data.get('code'):
            raise AppApiException(ExceptionCodeConstants.CODE_ERROR.value.code,
                                  ExceptionCodeConstants.CODE_ERROR.value.message)
        return True

    def reset_password(self):
        if self.is_valid():
            email = self.data.get("email")
            QuerySet(User).filter(email=email).update(
                password=password_encrypt(self.data.get('password')))
            user = QuerySet(User).filter(email=email).first()
            if user:
                revoke_user_sessions(user.id, reason="password_changed")
            code_cache_key = email + ":reset_password"
            cache.delete(get_key(code_cache_key), version=version)
            return True


class ResetCurrentUserPassword(serializers.Serializer):
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

    class Meta:
        model = User
        fields = '__all__'

    def is_valid(self, *, raise_exception=False):
        super().is_valid(raise_exception=True)
        if self.data.get('password') != self.data.get('re_password'):
            raise AppApiException(ExceptionCodeConstants.PASSWORD_NOT_EQ_RE_PASSWORD.value.code,
                                  ExceptionCodeConstants.PASSWORD_NOT_EQ_RE_PASSWORD.value.message)
        return True

    def reset_password(self, user_id: str):
        if self.is_valid():
            QuerySet(User).filter(id=user_id).update(
                password=password_encrypt(self.data.get('password')))
            revoke_user_sessions(user_id, reason="password_changed")
            return True


class SendEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True
        , label=_("Email"),
        validators=[validators.EmailValidator(message=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.message,
                                              code=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.code)])

    type = serializers.CharField(required=True, label=_("Type"), validators=[
        validators.RegexValidator(regex=re.compile("^register|reset_password$"),
                                  message=_("The type only supports register|reset_password"), code=500)
    ])

    class Meta:
        model = User
        fields = '__all__'

    def is_valid(self, *, raise_exception=False):
        super().is_valid(raise_exception=raise_exception)
        code_cache_key = self.data.get('email') + ":" + self.data.get("type")
        code_cache_key_lock = code_cache_key + "_lock"
        ttl = cache.ttl(code_cache_key_lock, version=version)
        if ttl is not None and ttl > 0:
            raise AppApiException(500, _("Do not send emails again within {seconds} seconds").format(
                seconds=int(ttl.total_seconds())))
        return True

    def send(self):
        email = self.data.get("email")
        state = self.data.get("type")
        code = "".join(list(map(lambda i: random.choice(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
                                                         ]), range(6))))
        language = get_language()
        file = open(
            os.path.join(PROJECT_DIR, "apps", "common", 'template', f'email_template_{to_locale(language)}.html'), "r",
            encoding='utf-8')
        content = file.read()
        file.close()
        code_cache_key = email + ":" + state
        code_cache_key_lock = code_cache_key + "_lock"
        cache.set(get_key(code_cache_key_lock), code, timeout=60, version=version)
        system_setting = QuerySet(SystemSetting).filter(type=SettingType.EMAIL.value).first()
        if system_setting is None:
            cache.delete(get_key(code_cache_key_lock), version=version)
            raise AppApiException(1004,
                                  _("The email service has not been set up. Please contact the administrator to set up the email service in [Email Settings]."))
        try:
            connection = EmailBackend(system_setting.meta.get("email_host"),
                                      system_setting.meta.get('email_port'),
                                      system_setting.meta.get('email_host_user'),
                                      system_setting.meta.get('email_host_password'),
                                      system_setting.meta.get('email_use_tls'),
                                      False,
                                      system_setting.meta.get('email_use_ssl')
                                      )
            send_mail(_('【Intelligent knowledge base question and answer system-{action}】').format(
                action=_('User registration') if state == 'register' else _('Change password')),
                '',
                html_message=f'{content.replace("${code}", code)}',
                from_email=system_setting.meta.get('from_email'),
                recipient_list=[email], fail_silently=False, connection=connection)
        except Exception:
            cache.delete(get_key(code_cache_key_lock))
            return True
        cache.set(get_key(code_cache_key), code, timeout=60 * 30, version=version)
        return True


class CheckCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        label=_("Email"),
        validators=[validators.EmailValidator(message=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.message,
                                              code=ExceptionCodeConstants.EMAIL_FORMAT_ERROR.value.code)])
    code = serializers.CharField(required=True, label=_("Verification code"))

    type = serializers.CharField(required=True,
                                 label=_("Type"),
                                 validators=[
                                     validators.RegexValidator(regex=re.compile("^register|reset_password$"),
                                                               message=_(
                                                                   "The type only supports register|reset_password"),
                                                               code=500)
                                 ])

    def is_valid(self, *, raise_exception=False):
        super().is_valid()
        value = cache.get(get_key(self.data.get("email") + ":" + self.data.get("type")), version=version)
        if value is None or value != self.data.get("code"):
            raise ExceptionCodeConstants.CODE_ERROR.value.to_app_api_exception()
        return True


class SwitchLanguageSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True, label=_('user id'))
    language = serializers.CharField(required=True, label=_('language'))

    def switch(self):
        self.is_valid(raise_exception=True)
        language = self.data.get('language')
        support_language_list = ['zh-CN', 'zh-Hant', 'en-US']
        if not support_language_list.__contains__(language):
            raise AppApiException(500, _('language only support:') + ','.join(support_language_list))
        QuerySet(User).filter(id=self.data.get('user_id')).update(language=language)
