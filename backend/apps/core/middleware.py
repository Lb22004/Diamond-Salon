from typing import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.services.audit import (
    clear_audit_context,
    log_audit,
    set_audit_context,
    was_request_logged,
)


def _extract_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditMiddleware:
    """Populates audit context (user, IP) and logs unhandled API mutations as fallback (RF-SEG-03)."""

    METHOD_ACTION_MAP = {
        "POST": "CREATE",
        "PUT": "UPDATE",
        "PATCH": "UPDATE",
        "DELETE": "DELETE",
    }

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        ip = _extract_ip(request)
        set_audit_context(getattr(request, "user", None), ip)
        try:
            response = self.get_response(request)
            # Re-bind user after DRF JWT authentication has run inside the view
            user = getattr(request, "user", None)
            if (
                request.path.startswith("/api/")
                and not request.path.startswith("/api/auth/token/refresh")
                and request.method in self.METHOD_ACTION_MAP
                and 200 <= response.status_code < 300
                and not was_request_logged()
                and user
                and getattr(user, "is_authenticated", False)
            ):
                action = self.METHOD_ACTION_MAP[request.method]
                path_lower = request.path.lower()
                if path_lower.endswith("/post/"):
                    action = "POST"
                elif path_lower.endswith("/reverse/"):
                    action = "REVERSE"
                elif path_lower.endswith("/void/"):
                    action = "VOID"
                elif path_lower.endswith("/close/"):
                    action = "CLOSE"
                elif path_lower.endswith("/reopen/"):
                    action = "REOPEN"

                log_audit(
                    action=action,
                    table_name=request.path.strip("/"),
                    after_data={"method": request.method, "path": request.path, "status": response.status_code},
                    user=user,
                    ip_address=ip,
                )
            return response
        finally:
            clear_audit_context()
