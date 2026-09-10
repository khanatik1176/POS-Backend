import time

EXCLUDED_PREFIXES = ('/admin/', '/static/', '/swagger', '/redoc', '/ws/')


class AuditLogMiddleware:
    """Logs every /api/ request: who called it, from which IP, which
    endpoint, and the outcome. Written synchronously on the request's own
    DB connection (not a background thread) so it never leaks connections.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)

        if request.path.startswith('/api/') and not request.path.startswith(EXCLUDED_PREFIXES):
            duration_ms = int((time.monotonic() - start) * 1000)
            self._write_log(request, response, duration_ms)

        return response

    def _write_log(self, request, response, duration_ms):
        from .models import AuditLog

        user = getattr(request, 'user', None)
        is_authenticated = bool(user and getattr(user, 'is_authenticated', False))

        try:
            AuditLog.objects.create(
                user_id=user.id if is_authenticated else None,
                username=user.username if is_authenticated else '',
                ip_address=self._client_ip(request),
                method=request.method,
                path=request.path[:255],
                status_code=response.status_code,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                duration_ms=duration_ms,
            )
        except Exception:
            # Audit logging must never break the actual response.
            pass

    def _client_ip(self, request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
