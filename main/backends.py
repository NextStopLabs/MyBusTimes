from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from main.models import CustomUser
from django.db import IntegrityError

class CustomOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def filter_users_by_claims(self, claims):
        """Find existing users by OIDC subject or email."""
        sub = claims.get('sub')
        email = claims.get('email')

        if sub:
            return CustomUser.objects.filter(oidc_sub=sub)
        elif email:
            return CustomUser.objects.filter(email__iexact=email)
        return CustomUser.objects.none()

    def create_user(self, claims):
        """Create a user or link to an existing one."""
        sub = claims.get('sub')
        email = claims.get('email')
        username = claims.get('preferred_username') or email

        # Check if there's already a user with this email
        existing_user = CustomUser.objects.filter(email__iexact=email).first()
        if existing_user:
            # Link OpenID identity to existing account
            existing_user.oidc_sub = sub
            existing_user.save()
            print(f"Linked existing user {existing_user.username} to OIDC sub {sub}")
            return existing_user

        try:
            # Otherwise, create a new user
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
            )
            user.oidc_sub = sub
            user.save()
            print(f"Created new user {user.username} for OIDC sub {sub}")
            return user
        except IntegrityError:
            # Handle rare race conditions (two users with same username/email)
            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.oidc_sub = sub
                user.save()
                return user
            raise

    def login_user(self, user, claims):
        """Fetch or create (link) a user on login."""
        sub = claims.get('sub')
        email = claims.get('email')

        # Try by sub first
        user = CustomUser.objects.filter(oidc_sub=sub).first()

        # If not found, fall back to email and link
        if not user and email:
            existing_user = CustomUser.objects.filter(email__iexact=email).first()
            if existing_user:
                existing_user.oidc_sub = sub
                existing_user.save()
                user = existing_user

        # Create if nothing exists
        if not user:
            user = self.create_user(claims)

        return user
