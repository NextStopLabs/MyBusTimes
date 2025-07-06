# auth_backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password, make_password
from main.models import CustomUser
import bcrypt

class PHPFallbackBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return None

        # First try Django's normal password check
        if user.check_password(password):
            return user

        # Fallback: try verifying with PHP's bcrypt hashes (starts with $2y$)
        # Django uses $2b$, but PHP uses $2y$ -- convert to $2b$ to check
        if user.password and user.password.startswith("$2y$"):
            php_hash = user.password
            django_compatible_hash = "$2b$" + php_hash[4:]
            if bcrypt.checkpw(password.encode('utf-8'), django_compatible_hash.encode('utf-8')):
                # Password matches the PHP hash - upgrade to Django hash
                user.password = make_password(password)
                user.save(update_fields=["password"])
                return user

        return None
