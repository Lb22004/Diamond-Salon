from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.core.models import User


class IsAdminRole(BasePermission):
    """Allows access only to users with the ADMIN role (RF-SEG-04, RF-SEG-05)."""

    message = "Se requiere rol de Administrador para realizar esta acción."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == User.Role.ADMIN or request.user.is_superuser)
        )


class IsAdminOrReadOnly(BasePermission):
    """Allows read access to any authenticated user, write access only to ADMIN."""

    message = "Solo un Administrador puede modificar este recurso."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == User.Role.ADMIN or request.user.is_superuser


class IsAccountantOrAdmin(BasePermission):
    """Allows write access to ACCOUNTANT and ADMIN, read access to authenticated users."""

    message = "Se requiere rol de Contador o Administrador."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in (User.Role.ADMIN, User.Role.ACCOUNTANT) or request.user.is_superuser


class IsPurchasingOrAdmin(BasePermission):
    """Allows write access to PURCHASING, ACCOUNTANT, and ADMIN."""

    message = "Se requiere rol de Compras y almacén o Administrador."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user.role in (User.Role.ADMIN, User.Role.PURCHASING, User.Role.ACCOUNTANT)
            or request.user.is_superuser
        )


class IsCashierOrAdmin(BasePermission):
    """Allows write access to CASHIER, ACCOUNTANT, and ADMIN."""

    message = "Se requiere rol de Caja / recepción o Administrador."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user.role in (User.Role.ADMIN, User.Role.CASHIER, User.Role.ACCOUNTANT)
            or request.user.is_superuser
        )


class CanViewAuditLog(BasePermission):
    """Allows viewing the audit log to ADMIN, AUDITOR, and ACCOUNTANT (SRS §2.3)."""

    message = "Solo Administradores, Auditores y Contadores pueden consultar la bitácora de auditoría."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method not in SAFE_METHODS:
            return False
        return (
            request.user.role in (User.Role.ADMIN, User.Role.AUDITOR, User.Role.ACCOUNTANT)
            or request.user.is_superuser
        )


ROLE_PERMISSIONS_MATRIX = {
    User.Role.ADMIN: {
        "views": ["panel", "catalogo", "inventario", "ventas", "compras", "diario", "mayor", "usuarios", "configuracion", "auditoria"],
        "can_write_accounting": True,
        "can_close_period": True,
        "can_reopen_period": True,
        "can_write_sales": True,
        "can_write_purchases": True,
        "can_write_inventory": True,
        "can_manage_users": True,
        "can_view_audit": True,
        "can_export": True,
    },
    User.Role.ACCOUNTANT: {
        "views": ["panel", "catalogo", "inventario", "ventas", "compras", "diario", "mayor", "auditoria"],
        "can_write_accounting": True,
        "can_close_period": True,
        "can_reopen_period": False,
        "can_write_sales": True,
        "can_write_purchases": True,
        "can_write_inventory": True,
        "can_manage_users": False,
        "can_view_audit": True,
        "can_export": True,
    },
    User.Role.AUDITOR: {
        "views": ["panel", "catalogo", "inventario", "ventas", "compras", "diario", "mayor", "auditoria"],
        "can_write_accounting": False,
        "can_close_period": False,
        "can_reopen_period": False,
        "can_write_sales": False,
        "can_write_purchases": False,
        "can_write_inventory": False,
        "can_manage_users": False,
        "can_view_audit": True,
        "can_export": True,
    },
    User.Role.PURCHASING: {
        "views": ["panel", "inventario", "compras"],
        "can_write_accounting": False,
        "can_close_period": False,
        "can_reopen_period": False,
        "can_write_sales": False,
        "can_write_purchases": True,
        "can_write_inventory": True,
        "can_manage_users": False,
        "can_view_audit": False,
        "can_export": True,
    },
    User.Role.CASHIER: {
        "views": ["panel", "inventario", "ventas"],
        "can_write_accounting": False,
        "can_close_period": False,
        "can_reopen_period": False,
        "can_write_sales": True,
        "can_write_purchases": False,
        "can_write_inventory": False,
        "can_manage_users": False,
        "can_view_audit": False,
        "can_export": False,
    },
    User.Role.READONLY: {
        "views": ["panel", "catalogo", "inventario", "ventas", "compras", "diario", "mayor"],
        "can_write_accounting": False,
        "can_close_period": False,
        "can_reopen_period": False,
        "can_write_sales": False,
        "can_write_purchases": False,
        "can_write_inventory": False,
        "can_manage_users": False,
        "can_view_audit": False,
        "can_export": True,
    },
}
