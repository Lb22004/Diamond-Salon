import contextvars
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import models
from django.forms.models import model_to_dict

from apps.core.models import AuditLog, User

_current_user: contextvars.ContextVar[User | None] = contextvars.ContextVar("current_user", default=None)
_current_ip: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_ip", default=None)
_request_logged: contextvars.ContextVar[bool] = contextvars.ContextVar("request_logged", default=False)


def set_audit_context(user: User | None, ip_address: str | None) -> None:
    _current_user.set(user if (user and getattr(user, "is_authenticated", False)) else None)
    _current_ip.set(ip_address)
    _request_logged.set(False)


def clear_audit_context() -> None:
    _current_user.set(None)
    _current_ip.set(None)
    _request_logged.set(False)


def get_current_user() -> User | None:
    return _current_user.get()


def get_current_ip() -> str | None:
    return _current_ip.get()


def was_request_logged() -> bool:
    return _request_logged.get()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return value


def serialize_instance(instance: models.Model | None, exclude: tuple[str, ...] = ("password",)) -> dict[str, Any] | None:
    if instance is None:
        return None
    raw = model_to_dict(instance)
    for field in exclude:
        raw.pop(field, None)
    return _json_safe(raw)


def log_audit(
    *,
    action: str,
    table_name: str,
    record_id: int | None = None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    user: User | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Append-only audit logger used across all domain modules (RF-SEG-03, RNF-05)."""
    resolved_user = user if (user and getattr(user, "is_authenticated", False)) else get_current_user()
    resolved_ip = ip_address or get_current_ip()
    _request_logged.set(True)
    return AuditLog.objects.create(
        user=resolved_user,
        action=action,
        table_name=table_name,
        record_id=record_id,
        before_data=_json_safe(before_data) if before_data is not None else None,
        after_data=_json_safe(after_data) if after_data is not None else None,
        ip_address=resolved_ip,
    )
