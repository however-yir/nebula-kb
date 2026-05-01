import uuid_utils.compat as uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auth_sessions'),
    ]

    operations = [
        migrations.CreateModel(
            name='SSOProvider',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=256, verbose_name='Provider Name')),
                ('provider_type', models.CharField(choices=[('OIDC', 'OpenID Connect'), ('SAML', 'SAML 2.0')], default='OIDC', max_length=10)),
                ('client_id', models.CharField(default='', max_length=512, verbose_name='Client ID')),
                ('client_secret', models.CharField(default='', max_length=512, verbose_name='Client Secret')),
                ('discovery_url', models.URLField(default='', max_length=1024, verbose_name='Discovery URL')),
                ('redirect_uri', models.URLField(default='', max_length=1024, verbose_name='Redirect URI')),
                ('scopes', models.CharField(default='openid email profile', max_length=512, verbose_name='Scopes')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('create_time', models.DateTimeField(auto_now_add=True, null=True)),
                ('update_time', models.DateTimeField(auto_now=True, null=True)),
            ],
            options={
                'db_table': 'sso_provider',
            },
        ),
    ]
