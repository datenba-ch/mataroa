from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0113_post_owner_published_at_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="OIDCConnection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "issuer",
                    models.URLField(
                        help_text="OIDC provider issuer URL, e.g., https://accounts.google.com"
                    ),
                ),
                (
                    "subject",
                    models.CharField(
                        help_text="The 'sub' claim - unique user ID from the provider",
                        max_length=255,
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        help_text="Email from the OIDC provider at time of login",
                        max_length=254,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oidc_connections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("issuer", "subject")},
            },
        ),
    ]
