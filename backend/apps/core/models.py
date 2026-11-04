from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user. Defined from day one so AUTH_USER_MODEL never has to change."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        ACCOUNTANT = "ACCOUNTANT", "Contador"
        AUDITOR = "AUDITOR", "Auditor"
        PURCHASING = "PURCHASING", "Compras y almacén"
        CASHIER = "CASHIER", "Caja / recepción"
        READONLY = "READONLY", "Solo lectura"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.READONLY)

    class Meta:
        db_table = "core_user"
