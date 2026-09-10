from rest_framework.permissions import BasePermission


def user_has_action(user, action_key):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    role = getattr(profile, 'role', None) if profile else None
    if not role:
        return False
    return action_key in (role.actions or [])


def require_action(action_key):
    """Returns a DRF permission class that grants access when the requesting
    user is a superuser or their role includes `action_key`."""

    class _HasAction(BasePermission):
        def has_permission(self, request, view):
            return user_has_action(request.user, action_key)

    _HasAction.__name__ = f'HasAction_{action_key.replace(".", "_")}'
    return _HasAction


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
