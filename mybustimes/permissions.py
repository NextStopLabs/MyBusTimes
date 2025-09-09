from rest_framework import permissions

class ReadOnlyOrAuthenticatedCreate(permissions.BasePermission):
    """
    Allow anyone to GET, but require authentication for POST requests.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return request.user and request.user.is_authenticated  # Require login for POST, PUT, DELETE

class ReadOnly(permissions.BasePermission):
    """
    Allow anyone to GET, but require authentication for POST requests.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return False
