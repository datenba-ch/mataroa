"""
Custom OIDC authentication backend for Mataroa.

Extends mozilla-django-oidc to:
- Look up users by OIDCConnection (issuer + subject)
- Fall back to email matching for account linking
- Auto-create users with username from email/preferred_username
- Respect username denylist
- Create OIDCConnection records
"""

import uuid

from django.conf import settings
from django.utils import timezone
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from main import denylist, text_processing
from main.models import OIDCConnection, User


class MataroaOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Custom OIDC backend that integrates with Mataroa's user model."""

    def get_issuer(self, claims):
        """Extract the issuer from claims or settings."""
        # The 'iss' claim contains the issuer URL
        return claims.get("iss", getattr(settings, "OIDC_OP_ISSUER", ""))

    def filter_users_by_claims(self, claims):
        """
        Look up users by OIDCConnection (issuer + subject).
        Falls back to email matching for account linking.
        """
        subject = claims.get("sub")
        issuer = self.get_issuer(claims)
        email = claims.get("email")

        if not subject or not issuer:
            return self.UserModel.objects.none()

        # First, try to find user by existing OIDCConnection
        try:
            connection = OIDCConnection.objects.get(issuer=issuer, subject=subject)
            # Update last login time
            connection.last_login_at = timezone.now()
            connection.save(update_fields=["last_login_at"])
            return [connection.user]
        except OIDCConnection.DoesNotExist:
            pass

        # Fall back to email matching for account linking
        if email:
            users = list(User.objects.filter(email__iexact=email))
            if users:
                # Create OIDCConnection for existing user (account linking)
                user = users[0]
                OIDCConnection.objects.create(
                    user=user,
                    issuer=issuer,
                    subject=subject,
                    email=email,
                    last_login_at=timezone.now(),
                )
                return [user]

        return self.UserModel.objects.none()

    def create_user(self, claims):
        """
        Create a new user from OIDC claims.

        Generates username from preferred_username or email prefix.
        Respects the username denylist.
        """
        subject = claims.get("sub")
        issuer = self.get_issuer(claims)
        email = claims.get("email")
        preferred_username = claims.get("preferred_username")

        # Generate username from preferred_username or email
        username = None
        if preferred_username:
            username = text_processing.slugify_username(preferred_username)

        if not username and email:
            # Extract local part of email
            email_prefix = email.split("@")[0]
            username = text_processing.slugify_username(email_prefix)

        if not username:
            # Generate a random username as last resort
            username = f"user-{uuid.uuid4().hex[:8]}"

        # Check if username is in denylist or already exists
        base_username = username
        counter = 1
        while (
            denylist.is_disallowed(username)
            or User.objects.filter(username=username).exists()
        ):
            username = f"{base_username}-{counter}"
            counter += 1
            # Safety check to prevent infinite loop
            if counter > 1000:
                username = f"user-{uuid.uuid4().hex[:12]}"
                break

        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
        )

        # Create the OIDCConnection
        OIDCConnection.objects.create(
            user=user,
            issuer=issuer,
            subject=subject,
            email=email,
            last_login_at=timezone.now(),
        )

        return user

    def update_user(self, user, claims):
        """
        Update user information from OIDC claims on subsequent logins.

        Updates the OIDCConnection's last_login_at timestamp.
        """
        subject = claims.get("sub")
        issuer = self.get_issuer(claims)
        email = claims.get("email")

        # Update or create OIDCConnection
        connection, created = OIDCConnection.objects.get_or_create(
            issuer=issuer,
            subject=subject,
            defaults={
                "user": user,
                "email": email,
                "last_login_at": timezone.now(),
            },
        )

        if not created:
            connection.last_login_at = timezone.now()
            if email:
                connection.email = email
            connection.save(update_fields=["last_login_at", "email"])

        return user
