import uuid_utils.compat as uuid

from django.db import models


class SSOProvider(models.Model):
    PROVIDER_TYPES = [
        ('OIDC', 'OpenID Connect'),
        ('SAML', 'SAML 2.0'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=256, verbose_name="Provider Name")
    provider_type = models.CharField(max_length=10, choices=PROVIDER_TYPES, default='OIDC')
    client_id = models.CharField(max_length=512, verbose_name="Client ID", default='')
    client_secret = models.CharField(max_length=512, verbose_name="Client Secret", default='')
    discovery_url = models.URLField(max_length=1024, verbose_name="Discovery URL", default='')
    redirect_uri = models.URLField(max_length=1024, verbose_name="Redirect URI", default='')
    scopes = models.CharField(max_length=512, verbose_name="Scopes", default='openid email profile')
    is_active = models.BooleanField(default=True, db_index=True)
    create_time = models.DateTimeField(auto_now_add=True, null=True)
    update_time = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "sso_provider"
