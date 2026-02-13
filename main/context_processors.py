from django.conf import settings


def oidc_settings(request):
    """
    Context processor to expose OIDC settings to templates.

    Makes OIDC configuration available in templates for conditional rendering
    of SSO login buttons and other OIDC-related UI elements.
    """
    return {
        "oidc_enabled": getattr(settings, "OIDC_ENABLED", False),
        "oidc_provider_name": getattr(settings, "OIDC_PROVIDER_NAME", "Single Sign-On"),
    }
