from django.conf import settings
from django.db import models

from orders.models import TimeStampedModel


class Role(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True, default='')
    actions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')

    def __str__(self):
        return f'Profile<{self.user.username}>'


class AuditLog(models.Model):
    """One row per API request. Written synchronously in the same request/
    connection (see accounts/middleware.py) - deliberately not offloaded to a
    background thread, since a thread-per-request DB write would open its own
    unmanaged connection on every single API call and risk exhausting Neon's
    connection limit."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    username = models.CharField(max_length=150, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255, db_index=True)
    status_code = models.PositiveIntegerField()
    user_agent = models.CharField(max_length=255, blank=True, default='')
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.method} {self.path} ({self.status_code}) by {self.username or "anonymous"}'
