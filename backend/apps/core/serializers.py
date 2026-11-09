from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.models import AccountingPeriod, AuditLog, Company, Employee, FiscalYear, User
from apps.core.permissions import ROLE_PERMISSIONS_MATRIX
from apps.core.services.audit import log_audit


class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(read_only=True)
    full_display_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, min_length=6)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "full_display_name",
            "email",
            "role",
            "role_label",
            "is_active",
            "is_staff",
            "last_login",
            "date_joined",
            "permissions",
        ]
        read_only_fields = ["id", "last_login", "date_joined", "role_label", "full_display_name", "permissions"]

    def get_permissions(self, obj: User) -> dict:
        return ROLE_PERMISSIONS_MATRIX.get(obj.role, ROLE_PERMISSIONS_MATRIX[User.Role.READONLY])

    def create(self, validated_data):
        password = validated_data.pop("password", "diamond2026")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Returns JWT tokens along with the authenticated user profile and logs LOGIN in AuditLog."""

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        log_audit(
            action=AuditLog.Action.LOGIN,
            table_name="core_user",
            record_id=self.user.pk,
            after_data={"username": self.user.username, "role": self.user.role},
            user=self.user,
        )
        return data


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "legal_name",
            "trade_name",
            "nit",
            "nrc",
            "economic_activity",
            "address",
            "iva_rate",
            "currency",
            "allow_negative_stock",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    position_label = serializers.CharField(source="get_position_display", read_only=True)

    class Meta:
        model = Employee
        fields = ["id", "full_name", "position", "position_label", "is_active"]
        read_only_fields = ["id", "position_label"]


class FiscalYearSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FiscalYear
        fields = ["id", "year", "start_date", "end_date", "status", "status_label"]
        read_only_fields = ["id", "status_label"]


class AccountingPeriodSerializer(serializers.ModelSerializer):
    month_name = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    closed_by_username = serializers.CharField(source="closed_by.username", read_only=True, default=None)

    class Meta:
        model = AccountingPeriod
        fields = [
            "id",
            "fiscal_year",
            "year",
            "month",
            "month_name",
            "label",
            "code",
            "start_date",
            "end_date",
            "status",
            "status_label",
            "is_active",
            "closed_at",
            "closed_by",
            "closed_by_username",
        ]
        read_only_fields = [
            "id",
            "month_name",
            "label",
            "code",
            "status_label",
            "closed_at",
            "closed_by",
            "closed_by_username",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="sistema")
    user_role = serializers.CharField(source="user.role", read_only=True, default="")
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "username",
            "user_role",
            "action",
            "action_label",
            "table_name",
            "record_id",
            "before_data",
            "after_data",
            "ip_address",
            "created_at",
        ]
        read_only_fields = fields
