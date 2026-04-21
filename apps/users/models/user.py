# coding=utf-8
"""
    @project: LZKB
    @Author：虎虎
    @file： user.py
    @date：2025/4/14 10:20
    @desc:
"""
import uuid_utils.compat as uuid

from django.db import models

from common.utils.common import password_encrypt


class User(models.Model):
    id = models.UUIDField(primary_key=True, max_length=128, default=uuid.uuid7, editable=False, verbose_name="主键id")
    email = models.EmailField(unique=True, null=True, blank=True, verbose_name="邮箱", db_index=True)
    phone = models.CharField(max_length=20, verbose_name="电话", default="", db_index=True)
    nick_name = models.CharField(max_length=150, verbose_name="昵称", unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, verbose_name="用户名", db_index=True)
    password = models.CharField(max_length=256, verbose_name="密码")
    role = models.CharField(max_length=150, verbose_name="角色")
    source = models.CharField(max_length=10, verbose_name="来源", default="LOCAL", db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    language = models.CharField(max_length=10, verbose_name="语言", null=True, default=None)
    last_login = models.DateTimeField(verbose_name="最后登录时间", null=True, blank=True, db_index=True)
    last_active = models.DateTimeField(verbose_name="最后活跃时间", null=True, blank=True, db_index=True)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True, null=True, db_index=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True, null=True, db_index=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"

    def set_password(self, row_password):
        self.password = password_encrypt(row_password)
        self._password = row_password


class DeviceSession(models.Model):
    id = models.UUIDField(primary_key=True, max_length=128, default=uuid.uuid7, editable=False, verbose_name="会话id")
    user = models.ForeignKey(User, related_name="device_sessions", on_delete=models.CASCADE, verbose_name="用户")
    device_id = models.CharField(max_length=128, db_index=True, verbose_name="设备id")
    access_token_hash = models.CharField(max_length=128, unique=True, db_index=True, verbose_name="访问令牌摘要")
    refresh_token_hash = models.CharField(max_length=128, unique=True, db_index=True, verbose_name="刷新令牌摘要")
    password_hash = models.CharField(max_length=256, verbose_name="登录时密码摘要")
    login_method = models.CharField(max_length=32, default="LOCAL", db_index=True, verbose_name="登录方式")
    ip_address = models.CharField(max_length=64, default="", blank=True, verbose_name="登录IP")
    user_agent = models.TextField(default="", blank=True, verbose_name="User-Agent")
    access_expires_at = models.DateTimeField(db_index=True, verbose_name="访问令牌过期时间")
    refresh_expires_at = models.DateTimeField(db_index=True, verbose_name="刷新令牌过期时间")
    last_login = models.DateTimeField(verbose_name="登录时间", null=True, blank=True, db_index=True)
    last_active = models.DateTimeField(verbose_name="最后活跃时间", null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(verbose_name="吊销时间", null=True, blank=True, db_index=True)
    revoke_reason = models.CharField(max_length=128, default="", blank=True, verbose_name="吊销原因")
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True, null=True, db_index=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True, null=True, db_index=True)

    class Meta:
        db_table = "user_device_session"
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["refresh_expires_at", "revoked_at"]),
        ]
